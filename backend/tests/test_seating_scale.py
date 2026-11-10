"""Oturma dağıtımının gerçek okul mevcutlarında çalışması.

Gerileme: çözücü "hangi öğrenci hangi koltukta" modelini kuruyordu. Değişken
sayısı öğrenci × koltuk, ihlal değişkenleri ise öğrenci çifti × koltuk çifti
kadardı; üstelik aynı şubedeki öğrenciler birbirinin yerine geçebildiği için
arama aynı çözümü permütasyonlar halinde tekrar tekrar geziyordu.

Sonuç: 48 öğrenci 2 saniyede çözülürken 236 öğrencilik gerçek bir okul listesi
50 saniyede çözülemiyordu. Koltuk sayısı öğrenci sayısına eşit olduğu için
(okulun olağan durumu) kapasite artırmak da seçenek değildi.

Model artık grup üzerinden kuruluyor. Bu testler hem doğruluğu hem de ölçeği
sabitler; ölçek testi olmadan aynı hata sessizce geri gelebilir.
"""

import time
import unittest

from kelebek.distribution.seating import BOS_GRUP, assign_students, solve_group_layout
from kelebek.distribution.solver import DistributionError, evaluate_assignments, solve_candidate

TUM_KURALLAR = {
    name: True
    for name in (
        "prevent_same_section_adjacent", "prevent_same_section_front_back",
        "prevent_different_grade_same_area_adjacent", "prevent_different_grade_same_area_front_back",
        "prevent_same_grade_area_adjacent", "prevent_same_grade_area_front_back",
    )
}

SUBELER = [
    ("9", "A", ""), ("9", "B", ""), ("10", "A", ""), ("10", "B", ""),
    ("11", "A", "sayısal"), ("11", "B", "eşit ağırlık"), ("12", "A", "sözel"), ("12", "B", "dil"),
]


def okul_kur(ogrenci_sayisi: int, koltuk_sayisi: int | None = None, satir: int = 5, sutun: int = 6):
    """Koltuk sayısı varsayılan olarak öğrenci sayısına eşittir (okulun gerçek durumu)."""
    koltuk_sayisi = ogrenci_sayisi if koltuk_sayisi is None else koltuk_sayisi
    rooms, adjacent, front_back = [], set(), set()
    seat_id = 0
    kalan, oda_index = koltuk_sayisi, 0
    while kalan > 0:
        kapasite = min(satir * sutun, kalan)
        kalan -= kapasite
        izgara, seats = {}, []
        for i in range(kapasite):
            x, y = i % sutun, i // sutun
            seat_id += 1
            key = f"s{seat_id}"
            izgara[(x, y)] = key
            seats.append({"id": key, "is_available": True, "seat_number": i + 1,
                          "classroom_id": f"r{oda_index}"})
        for (x, y), key in izgara.items():
            if (x + 1, y) in izgara:
                adjacent.add(tuple(sorted((key, izgara[(x + 1, y)]))))
            if (x, y + 1) in izgara:
                front_back.add(tuple(sorted((key, izgara[(x, y + 1)]))))
        rooms.append({"id": f"r{oda_index}", "name": f"Derslik {oda_index}", "seats": seats})
        oda_index += 1
    participants = [
        {"id": f"p{i}", "class_level": SUBELER[i % 8][0], "section": SUBELER[i % 8][1],
         "area": SUBELER[i % 8][2] or None}
        for i in range(ogrenci_sayisi)
    ]
    return participants, rooms, {"adjacent": sorted(adjacent), "front_back": sorted(front_back)}


class SeatingScaleTests(unittest.TestCase):
    def test_real_school_size_solves_quickly_at_exact_capacity(self):
        """236 öğrenci, 236 koltuk: eski model çözemiyordu."""
        participants, rooms, pairs = okul_kur(236)
        basladi = time.monotonic()
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        sure = time.monotonic() - basladi

        self.assertLess(sure, 20, f"236 öğrencilik dağıtım {sure:.1f} saniye sürdü.")
        self.assertEqual(len(sonuc["assignments"]), 236)
        self.assertEqual(sonuc["affected_student_count"], 0)

    def test_every_student_gets_exactly_one_seat(self):
        participants, rooms, pairs = okul_kur(236)
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        ogrenciler = [item["participant_id"] for item in sonuc["assignments"]]
        koltuklar = [item["seat_id"] for item in sonuc["assignments"]]
        self.assertEqual(len(set(ogrenciler)), 236, "Bir öğrenci birden fazla kez yerleştirilmiş.")
        self.assertEqual(len(set(koltuklar)), 236, "Bir koltuğa birden fazla öğrenci oturtulmuş.")
        self.assertEqual(set(ogrenciler), {item["id"] for item in participants})

    def test_reported_violation_count_matches_independent_check(self):
        """Çözücünün bildirdiği sayı, uygulamanın kendi denetleyicisiyle doğrulanır."""
        participants, rooms, pairs = okul_kur(120)
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        eslesme = {item["participant_id"]: item["seat_id"] for item in sonuc["assignments"]}
        denetim = evaluate_assignments(participants, pairs, TUM_KURALLAR, eslesme)
        self.assertEqual(denetim["affected_student_count"], sonuc["affected_student_count"])

    def test_scales_to_a_large_school(self):
        """600 öğrenci: eski modelde imkânsızdı."""
        participants, rooms, pairs = okul_kur(600)
        basladi = time.monotonic()
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        sure = time.monotonic() - basladi
        self.assertLess(sure, 25, f"600 öğrencilik dağıtım {sure:.1f} saniye sürdü.")
        self.assertEqual(len(sonuc["assignments"]), 600)
        self.assertEqual(sonuc["affected_student_count"], 0)

    def test_candidate_is_returned_even_when_violations_are_unavoidable(self):
        """Tek sıra, dört koltuk, dördü de aynı şube: ihlalsiz yerleşim imkânsız.

        Eski model bu durumda hiç aday üretmiyor, kullanıcıya yalnızca hata
        gösteriyordu. Artık en iyi aday üretilir; kesinleştirme aşaması zaten
        etkilenen öğrenci sayısını ayrıca denetliyor.
        """
        participants, rooms, pairs = okul_kur(4, satir=1, sutun=4)
        for item in participants:
            item.update(class_level="9", section="A", area=None)
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        self.assertEqual(len(sonuc["assignments"]), 4)
        self.assertGreater(sonuc["affected_student_count"], 0)

    def test_pinned_seats_are_preserved(self):
        participants, rooms, pairs = okul_kur(60)
        ilk = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        sabit = {item["participant_id"]: item["seat_id"] for item in ilk["assignments"][:10]}
        ikinci = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0,
                                 fixed_assignments=sabit)
        yerlesim = {item["participant_id"]: item["seat_id"] for item in ikinci["assignments"]}
        for participant_id, seat_id in sabit.items():
            self.assertEqual(yerlesim[participant_id], seat_id, "Sabitlenen yerleşim korunmadı.")

    def test_spare_seats_stay_empty_when_capacity_exceeds_students(self):
        participants, rooms, pairs = okul_kur(50, koltuk_sayisi=60)
        sonuc = solve_group_layout(participants, rooms, pairs, TUM_KURALLAR, 12.0, {}, None)
        self.assertTrue(sonuc["ok"])
        bos = [seat for seat, key in sonuc["layout"].items() if key == BOS_GRUP]
        self.assertEqual(len(bos), 10)
        eslesme = assign_students(participants, sonuc["layout"])
        self.assertEqual(len(eslesme), 50)
        self.assertFalse(set(eslesme.values()) & set(bos), "Boş kalması gereken koltuğa öğrenci oturtulmuş.")

    def test_capacity_shortfall_is_reported_clearly(self):
        participants, rooms, pairs = okul_kur(60, koltuk_sayisi=40)
        with self.assertRaises(DistributionError) as hata:
            solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=5.0)
        self.assertIn("Kapasite yetersiz", str(hata.exception))

    def test_disabled_rules_are_not_enforced(self):
        participants, rooms, pairs = okul_kur(30)
        kapali = dict.fromkeys(TUM_KURALLAR, False)
        sonuc = solve_candidate(participants, rooms, pairs, kapali, time_limit=12.0)
        self.assertEqual(sonuc["affected_student_count"], 0)
        self.assertEqual(len(sonuc["assignments"]), 30)


if __name__ == "__main__":
    unittest.main()
