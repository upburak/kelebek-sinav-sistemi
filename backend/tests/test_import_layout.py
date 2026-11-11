"""İçe aktarmanın ürettiği başlangıç düzeni gerçek derslikle uyuşmalı.

Okulun bildirdiği düzen: her derslikte iki koridor var ve 36 kişilik sınıfta
6 satır çiftli masa bulunuyor. Önceki kural karekök temelliydi; 36 koltuk için
5 sütun × 4 satır, **tek koridorlu** bir taslak üretiyordu. Bu hem fiziksel
sınıfa uymuyor hem de komşuluk grafiğini değiştirdiği için dağıtımı yanlış
zemine oturtuyordu (koridorun iki yanı yan yana sayılmaz).

Test gerçek içe aktarma ucunu kullanır: bellekte bir sınıf listesi üretilir,
uygulamaya aktarılır ve oluşan taslak düzenin geometrisi denetlenir.
"""

import io
import unittest
from itertools import pairwise

import test_exam_flow
from openpyxl import Workbook
from sqlalchemy import select

from kelebek.distribution.neighbors import build_neighbor_pairs
from kelebek.models import ClassroomLayout, Desk, Seat

LISTE_BASLIK = "liste başlangıç düzeni"


def sinif_listesi(ogrenci_sayisi: int, sinif: str, sube: str) -> bytes:
    """e-Okul çıktısına benzeyen, tek sayfalık sentetik sınıf listesi."""
    wb = Workbook()
    ws = wb.active
    ws.title = f"{sinif}-{sube}"
    ws.append(["Okul No", "Adı", "Soyadı"])
    for index in range(1, ogrenci_sayisi + 1):
        ws.append([f"{sinif}{sube}{index:03d}", f"ÖRNEK AD {index:03d}", "SENTETİK SOYAD"])
    akis = io.BytesIO()
    wb.save(akis)
    return akis.getvalue()


class ImportLayoutTests(unittest.TestCase):
    setUp = test_exam_flow.ExamFlowTests.setUp
    tearDown = test_exam_flow.ExamFlowTests.tearDown
    _seed_synthetic_school = test_exam_flow.ExamFlowTests._seed_synthetic_school

    def _aktar(self, ogrenci_sayisi: int, sinif: str = "9", sube: str = "Z"):
        icerik = sinif_listesi(ogrenci_sayisi, sinif, sube)
        response = self.client.post("/api/student-import/commit", data={
            "file": (io.BytesIO(icerik), "liste.xlsx"),
            "mapping": '{"school_number":0,"first_name":1,"last_name":2,'
                       '"class_level":"__context__","section":"__context__"}',
            "area_assignments": "{}",
            "academic_year_id": self.year_id,
            "confirm": "true",
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def _taslak_duzenler(self) -> list[tuple[str, list[dict]]]:
        """İçe aktarmanın oluşturduğu düzenleri masalarıyla birlikte getir."""
        sonuc = []
        with self.factory() as session:
            layouts = session.scalars(
                select(ClassroomLayout).where(ClassroomLayout.name.like(f"%{LISTE_BASLIK}%"))
            ).all()
            for layout in layouts:
                desks = session.scalars(select(Desk).where(Desk.layout_id == layout.id)).all()
                hazir = []
                for desk in desks:
                    seats = session.scalars(
                        select(Seat).where(Seat.desk_id == desk.id).order_by(Seat.seat_index)
                    ).all()
                    hazir.append({
                        "id": desk.id, "x": desk.x, "y": desk.y,
                        "seats": [{"id": s.id, "seat_index": s.seat_index,
                                   "is_available": s.is_available} for s in seats],
                    })
                if hazir:
                    sonuc.append((layout.name, hazir))
        return sonuc

    def test_thirty_six_seat_room_becomes_three_blocks_of_six_rows(self):
        """36 kişilik sınıf: 3 blok × 6 satır çiftli masa, iki koridor."""
        self._aktar(36)
        duzenler = self._taslak_duzenler()
        self.assertTrue(duzenler, "İçe aktarma taslak düzen üretmedi.")
        _ad, desks = duzenler[0]

        self.assertEqual(sum(len(d["seats"]) for d in desks), 36)
        self.assertEqual(len(desks), 18, "6 satır × 3 blok = 18 çiftli masa olmalı.")
        self.assertEqual(sorted({d["x"] for d in desks}), [0.0, 4.0, 8.0],
                         "Üç blok ve aralarında iki koridor olmalı.")
        self.assertEqual(len({d["y"] for d in desks}), 6, "Altı satır olmalı.")
        self.assertTrue(all(len(d["seats"]) == 2 for d in desks), "Masalar çiftli olmalı.")

    def test_blocks_are_separated_by_a_corridor(self):
        self._aktar(36)
        for ad, desks in self._taslak_duzenler():
            bloklar = sorted({d["x"] for d in desks})
            self.assertLessEqual(len(bloklar), 3, f"{ad}: üçten fazla blok var.")
            for once, sonra in pairwise(bloklar):
                # Bloklar dört birim arayla durur; aradaki boş ızgara sütunu koridordur.
                self.assertEqual(sonra - once, 4.0, f"{ad}: bloklar arasında koridor yok.")

    def test_corridor_keeps_side_by_side_but_not_front_back(self):
        """Koridorun iki yanı yan yana sayılır; önlü arkalı ve çapraz koridoru aşmaz."""
        self._aktar(36)
        for ad, desks in self._taslak_duzenler():
            pairs = build_neighbor_pairs(desks)
            # 18 masa içi çift + 6 satır × 2 koridor.
            self.assertEqual(len(pairs["adjacent"]), 30, f"{ad}: koridor üstü yan yana eksik.")
            self.assertEqual(len(pairs["front_back"]), 30,
                             f"{ad}: 3 blok × 5 satır aralığı × 2 koltuk beklenir.")
            self.assertEqual(len(pairs["diagonal"]), 30,
                             f"{ad}: çapraz yalnızca blok içinde sayılmalı.")

    def test_small_room_still_keeps_corridors(self):
        """12 kişilik sınıf da üç bloklu olmalı; eski kural hiç koridor bırakmıyordu."""
        self._aktar(12, sinif="10", sube="Y")
        duzenler = [item for item in self._taslak_duzenler() if sum(len(d["seats"]) for d in item[1]) == 12]
        self.assertTrue(duzenler, "12 kişilik sınıf için taslak düzen üretilmedi.")
        _ad, desks = duzenler[0]
        self.assertEqual(sorted({d["x"] for d in desks}), [0.0, 4.0, 8.0])
        self.assertEqual(len({d["y"] for d in desks}), 2, "12 koltuk = 3 blok × 2 satır.")


if __name__ == "__main__":
    unittest.main()
