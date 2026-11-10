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

from kelebek.distribution.neighbors import build_neighbor_pairs
from kelebek.distribution.seating import BOS_GRUP, assign_students, solve_group_layout
from kelebek.distribution.solver import DistributionError, evaluate_assignments, solve_candidate

TUM_KURALLAR = {
    name: True
    for name in (
        "prevent_same_section_adjacent", "prevent_same_section_front_back",
        "prevent_different_grade_same_area_adjacent", "prevent_different_grade_same_area_front_back",
        "prevent_same_grade_area_adjacent", "prevent_same_grade_area_front_back",
        "prevent_same_grade_adjacent", "prevent_same_grade_front_back",
    )
}

SUBELER = [
    ("9", "A", ""), ("9", "B", ""), ("10", "A", ""), ("10", "B", ""),
    ("11", "A", "sayısal"), ("11", "B", "eşit ağırlık"), ("12", "A", "sözel"), ("12", "B", "dil"),
]


def derslik_kur(oda_index: int, koltuk_sayisi: int, bloklar: int = 3, satir: int = 6):
    """Gerçek sınıf düzeni: bloklar halinde çiftli masalar ve aralarında koridor.

    Okulun bildirdiği düzen: 36 kişilik sınıfta 6 satır çiftli masa ve iki koridor.
    Üç blok × altı satır × iki kişilik masa = 36 koltuk.

    Koridor, ızgarada bir sütun atlanarak temsil edilir (masa x'i 2 yerine 4
    artar); ``build_neighbor_pairs`` bu boşluğu görünce koridorun iki yanını
    komşu saymaz. Komşuluk grafiği bu yüzden elle değil, uygulamanın kendi
    hesabıyla üretilir.
    """
    desks, seat_id = [], 0
    kalan = koltuk_sayisi
    for satir_index in range(satir):
        for blok in range(bloklar):
            if kalan <= 0:
                break
            masadaki = min(2, kalan)
            kalan -= masadaki
            seats = []
            for seat_index in range(1, masadaki + 1):
                seat_id += 1
                seats.append({
                    "id": f"r{oda_index}s{seat_id}", "seat_index": seat_index,
                    "seat_number": seat_id, "is_available": True,
                    "classroom_id": f"r{oda_index}",
                })
            desks.append({
                "id": f"r{oda_index}d{satir_index}_{blok}",
                # Blok başına 4 birim: aradaki boş ızgara sütunu koridordur.
                "x": float(blok * 4), "y": float(satir_index * 2), "seats": seats,
            })
    room = {"id": f"r{oda_index}", "name": f"Derslik {oda_index}",
            "seats": [seat for desk in desks for seat in desk["seats"]]}
    return room, desks


def okul_kur(ogrenci_sayisi: int, koltuk_sayisi: int | None = None, derslik_kapasitesi: int = 36):
    """Koltuk sayısı varsayılan olarak öğrenci sayısına eşittir (okulun gerçek durumu)."""
    koltuk_sayisi = ogrenci_sayisi if koltuk_sayisi is None else koltuk_sayisi
    rooms = []
    adjacent, front_back, diagonal = [], [], []
    kalan, oda_index = koltuk_sayisi, 0
    while kalan > 0:
        kapasite = min(derslik_kapasitesi, kalan)
        kalan -= kapasite
        room, desks = derslik_kur(oda_index, kapasite)
        rooms.append(room)
        # Komşuluk, uygulamadaki gibi her derslik için ayrı hesaplanır:
        # ızgara koordinatları derslikler arasında yeniden kullanılır.
        oda_pairs = build_neighbor_pairs(desks)
        adjacent.extend(oda_pairs["adjacent"])
        front_back.extend(oda_pairs["front_back"])
        diagonal.extend(oda_pairs["diagonal"])
        oda_index += 1
    pairs = {"adjacent": sorted(adjacent), "front_back": sorted(front_back),
             "diagonal": sorted(diagonal)}
    participants = [
        {"id": f"p{i}", "class_level": SUBELER[i % 8][0], "section": SUBELER[i % 8][1],
         "area": SUBELER[i % 8][2] or None}
        for i in range(ogrenci_sayisi)
    ]
    return participants, rooms, pairs


class RealClassroomGeometryTests(unittest.TestCase):
    """Okulun bildirdiği düzen: 36 kişilik sınıfta 6 satır çiftli masa, iki koridor."""

    def test_thirty_six_seat_room_is_three_blocks_of_double_desks(self):
        room, desks = derslik_kur(0, 36)
        self.assertEqual(len(room["seats"]), 36)
        self.assertEqual(len(desks), 18, "6 satır × 3 blok = 18 çiftli masa olmalı.")
        self.assertTrue(all(len(desk["seats"]) == 2 for desk in desks), "Her masa iki kişilik olmalı.")
        bloklar = sorted({desk["x"] for desk in desks})
        self.assertEqual(bloklar, [0.0, 4.0, 8.0], "Üç blok ve aralarında iki koridor olmalı.")
        self.assertEqual(len({desk["y"] for desk in desks}), 6, "Altı satır olmalı.")

    def test_corridor_allows_only_side_by_side_neighbourhood(self):
        """Koridorun karşısı yan yana sayılır; önlü arkalı ve çapraz koridoru aşmaz."""
        _room, desks = derslik_kur(0, 36)
        pairs = build_neighbor_pairs(desks)

        # Yan yana: 18 masa içi çift + 6 satır × 2 koridor.
        self.assertEqual(len(pairs["adjacent"]), 30)
        # Önlü arkalı (doğrudan): 3 blok × 5 satır aralığı × 2 koltuk.
        self.assertEqual(len(pairs["front_back"]), 30)
        # Çapraz: blok içinde, her satır aralığında 2 çift.
        self.assertEqual(len(pairs["diagonal"]), 30)

        def masa(x, y):
            return next(d for d in desks if d["x"] == x and d["y"] == y)

        def cift(a, b):
            return tuple(sorted((a["id"], b["id"])))

        sol, sag, sag_arka = masa(0.0, 0.0), masa(4.0, 0.0), masa(4.0, 2.0)
        # Koridorun iki kenarındaki koltuklar yan yanadır.
        self.assertIn(cift(sol["seats"][-1], sag["seats"][0]), pairs["adjacent"])
        # Koridor üzerinden önlü arkalı ya da çapraz komşuluk yoktur.
        karsi = {cift(a, b) for a in sol["seats"] for b in sag_arka["seats"]}
        self.assertFalse(karsi & (set(pairs["front_back"]) | set(pairs["diagonal"])),
                         "Önlü arkalı/çapraz komşuluk koridoru aşmış.")

    def test_legacy_mode_can_still_cut_side_by_side_at_corridor(self):
        _room, desks = derslik_kur(0, 36)
        pairs = build_neighbor_pairs(desks, side_by_side_crosses_corridor=False)
        self.assertEqual(len(pairs["adjacent"]), 18)

    def test_same_grade_rule_skips_diagonal_but_other_rules_apply(self):
        """Kural 8 çapraza uygulanmaz; şube/alan kuralları çaprazda da geçerlidir."""
        from kelebek.distribution.seating import _groups_conflict
        dokuz_a, dokuz_b = ("9", "a", ""), ("9", "b", "")
        self.assertTrue(_groups_conflict(dokuz_a, dokuz_b, TUM_KURALLAR, "front_back"))
        self.assertTrue(_groups_conflict(dokuz_a, dokuz_b, TUM_KURALLAR, "adjacent"))
        self.assertFalse(_groups_conflict(dokuz_a, dokuz_b, TUM_KURALLAR, "diagonal"))
        self.assertTrue(_groups_conflict(dokuz_a, dokuz_a, TUM_KURALLAR, "diagonal"))
        self.assertTrue(_groups_conflict(("11", "a", "sayısal"), ("12", "c", "sayısal"),
                                         TUM_KURALLAR, "diagonal"))

    def test_single_room_of_thirty_six_seats_at_exact_capacity(self):
        participants, rooms, pairs = okul_kur(36)
        self.assertEqual(len(rooms), 1)
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        self.assertEqual(len(sonuc["assignments"]), 36)
        self.assertEqual(sonuc["affected_student_count"], 0)

    def test_eight_real_rooms_match_the_school_that_reported_the_problem(self):
        """Sorunun çıktığı okul: 8 derslik, 236 öğrenci, koltuk sayısı tam eşit."""
        participants, rooms, pairs = okul_kur(236)
        basladi = time.monotonic()
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        sure = time.monotonic() - basladi
        self.assertLess(sure, 20, f"236 öğrencilik dağıtım {sure:.1f} saniye sürdü.")
        self.assertEqual(len(sonuc["assignments"]), 236)
        self.assertEqual(sonuc["affected_student_count"], 0)

        eslesme = {item["participant_id"]: item["seat_id"] for item in sonuc["assignments"]}
        denetim = evaluate_assignments(participants, pairs, TUM_KURALLAR, eslesme)
        self.assertEqual(denetim["affected_student_count"], 0,
                         "Bağımsız denetim ihlal buldu.")


class SameGradeRuleTests(unittest.TestCase):
    """Kural 7-8: aynı sınıf seviyesindeki öğrenciler yan yana/önlü arkalı oturamaz.

    Kullanıcı gerçek bir krokide 9/A ile 9/B öğrencisini yan yana görüp bunu
    bildirdi. Alan bilgisi olmayan 9 ve 10. sınıflarda tek koruma "aynı şube"
    kuralıydı; farklı şubeler yan yana oturabiliyordu, oysa ikisi de aynı sınav
    kağıdını alır.
    """

    def _ayni_seviye_yan_yana(self, participants, rooms, pairs, sonuc) -> list[tuple[str, str]]:
        """Yan yana oturup aynı sınıf seviyesinde olan öğrenci çiftlerini bul."""
        by_participant = {item["id"]: item for item in participants}
        by_seat = {item["seat_id"]: item["participant_id"] for item in sonuc["assignments"]}
        bulunan = []
        for first_seat, second_seat in pairs["adjacent"]:
            first, second = by_seat.get(first_seat), by_seat.get(second_seat)
            if not first or not second:
                continue
            if by_participant[first]["class_level"] == by_participant[second]["class_level"]:
                bulunan.append((first, second))
        return bulunan

    def test_same_grade_students_do_not_sit_side_by_side(self):
        participants, rooms, pairs = okul_kur(236)
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=20.0)
        self.assertEqual(len(sonuc["assignments"]), 236)
        self.assertEqual(sonuc["affected_student_count"], 0)
        self.assertEqual(self._ayni_seviye_yan_yana(participants, rooms, pairs, sonuc), [],
                         "Aynı sınıf seviyesinden iki öğrenci yan yana oturuyor.")

    def test_rule_can_be_switched_off(self):
        """Kurallar ayrı seçenekler olarak kalır; kapatıldığında uygulanmaz."""
        participants, rooms, pairs = okul_kur(72)
        kurallar = dict(TUM_KURALLAR)
        kurallar["prevent_same_grade_adjacent"] = False
        kurallar["prevent_same_grade_front_back"] = False
        sonuc = solve_candidate(participants, rooms, pairs, kurallar, time_limit=12.0)
        self.assertEqual(len(sonuc["assignments"]), 72)

    def test_violation_is_reported_with_a_clear_reason(self):
        """Tek masa, iki koltuk, iki farklı şubeden 9. sınıf: ihlal bildirilmeli."""
        participants, rooms, pairs = okul_kur(2, derslik_kapasitesi=2)
        participants[0].update(class_level="9", section="A", area=None)
        participants[1].update(class_level="9", section="B", area=None)
        sonuc = solve_candidate(participants, rooms, pairs, TUM_KURALLAR, time_limit=12.0)
        self.assertEqual(sonuc["affected_student_count"], 2)

        eslesme = {item["participant_id"]: item["seat_id"] for item in sonuc["assignments"]}
        denetim = evaluate_assignments(participants, pairs, TUM_KURALLAR, eslesme)
        self.assertEqual(denetim["affected_student_count"], 2)
        self.assertTrue(denetim["violations"])
        self.assertIn("Aynı sınıf seviyesi", denetim["violations"][0]["reason"])


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
        participants, rooms, pairs = okul_kur(4, derslik_kapasitesi=4)
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
