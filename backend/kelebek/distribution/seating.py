"""Koltuk dağıtımının ölçeklenebilir çekirdeği: önce grup yerleşimi, sonra öğrenci eşleme.

Neden iki aşama:

Altı komşuluk kuralının tamamı yalnızca öğrencinin **grubuna** bakar
(sınıf seviyesi, şube, alan). Aynı gruptaki iki öğrenci kurallar açısından
birbirinin yerine geçebilir. Doğrudan "hangi öğrenci hangi koltukta" modeli
kurmak bu yüzden devasa ve simetrik bir arama uzayı üretiyordu:

* değişken sayısı öğrenci × koltuk (236 öğrenci için ~56.000),
* ihlal değişkenleri öğrenci çifti × koltuk çifti (236 öğrenci için milyonlarca),
* ve aynı gruptaki öğrencilerin her permütasyonu çözücüye farklı bir çözüm gibi
  göründüğü için arama kendini tekrar ediyordu.

Bunun yerine birinci aşama yalnızca **hangi koltukta hangi grup oturacak**
sorusunu çözer. Değişken sayısı koltuk × grup olur (236 koltuk, 8 grup → ~1.900)
ve ihlal değişkenleri koltuk çifti × çakışan grup çifti kadardır. İkinci aşama
saf Python'dur: her grubun kazandığı koltuklara o gruptaki öğrencileri yerleştirir.
Kurallar gruba bağlı olduğu için bu eşleme ihlal sayısını değiştiremez.

Kapasite öğrenci sayısına eşit olduğunda (okulun olağan durumu) boş koltuk
kalmaz; artan koltuklar "boş" sanal grubuyla temsil edilir ve hiçbir kuralı
ihlal etmez.
"""

from __future__ import annotations

import threading
from math import ceil

from ortools.sat.python import cp_model

BOS_GRUP = ("", "", "")  # koltuk boş kalacaksa kullanılan sanal grup


def group_key(participant: dict) -> tuple[str, str, str]:
    """Kuralların baktığı tek şey: sınıf seviyesi, şube ve alan."""
    return (
        str(participant["class_level"]),
        str(participant["section"]).casefold(),
        str(participant.get("area") or "").casefold(),
    )


def _groups_conflict(first: tuple[str, str, str], second: tuple[str, str, str],
                     rules: dict, relation: str) -> bool:
    """İki grup yan yana / önlü-arkalı oturduğunda kural ihlali oluşur mu?"""
    if first == BOS_GRUP or second == BOS_GRUP:
        return False
    suffix = "_adjacent" if relation == "adjacent" else "_front_back"
    same_section = first[0] == second[0] and first[1] == second[1]
    same_area = bool(first[2]) and first[2] == second[2]
    if same_section and rules["prevent_same_section" + suffix]:
        return True
    if same_area and first[0] == second[0] and rules["prevent_same_grade_area" + suffix]:
        return True
    if same_area and first[0] != second[0] and rules["prevent_different_grade_same_area" + suffix]:
        return True
    # Kural 7-8: aynı sınıf seviyesindeki öğrenciler aynı sınav kağıdını alır.
    # Alan bilgisi olmayan 9 ve 10. sınıflarda tek koruma bu kuraldır.
    return bool(first[0] == second[0] and rules.get("prevent_same_grade" + suffix))


class _ProgressCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, progress, affected_vars):
        super().__init__()
        self._progress = progress
        self._affected = affected_vars

    def on_solution_callback(self):
        self._progress.record_solution(
            self.objective_value, sum(self.boolean_value(v) for v in self._affected)
        )


def solve_group_layout(participants: list[dict], rooms: list[dict], seat_pairs: dict, rules: dict,
                       time_limit: float, fixed_assignments: dict[str, str], progress=None) -> dict:
    """Birinci aşama: her koltuğa bir grup ata, etkilenen öğrenci sayısını enazla."""
    seats = [seat for room in rooms for seat in room["seats"] if seat["is_available"]]
    seat_ids = [seat["id"] for seat in seats]
    seat_index = {seat_id: i for i, seat_id in enumerate(seat_ids)}

    sizes: dict[tuple[str, str, str], int] = {}
    for item in participants:
        key = group_key(item)
        sizes[key] = sizes.get(key, 0) + 1
    bos_sayisi = len(seat_ids) - len(participants)
    if bos_sayisi:
        sizes[BOS_GRUP] = bos_sayisi
    groups = sorted(sizes)

    model = cp_model.CpModel()
    x = {(s, g): model.new_bool_var(f"x_{s}_{g}") for s in range(len(seat_ids)) for g in range(len(groups))}
    for s in range(len(seat_ids)):
        model.add_exactly_one(x[s, g] for g in range(len(groups)))
    for g, key in enumerate(groups):
        model.add(sum(x[s, g] for s in range(len(seat_ids))) == sizes[key])

    # Sabitlenen derslikler: o koltuklardaki grup değişemez.
    by_participant = {item["id"]: item for item in participants}
    for participant_id, seat_id in (fixed_assignments or {}).items():
        if participant_id not in by_participant or seat_id not in seat_index:
            raise ValueError("Sabitlenen derslikteki bir yerleşim artık geçerli değil; sabitlemeyi yenileyin.")
        model.add(x[seat_index[seat_id], groups.index(group_key(by_participant[participant_id]))] == 1)

    # İhlaller: koltuk çifti × çakışan grup çifti. Öğrenci sayısından bağımsızdır.
    seat_affected = [model.new_bool_var(f"aff_{s}") for s in range(len(seat_ids))]
    violations = []
    for relation in ("adjacent", "front_back"):
        for first_seat, second_seat in seat_pairs.get(relation, ()):
            if first_seat not in seat_index or second_seat not in seat_index:
                continue
            a, b = seat_index[first_seat], seat_index[second_seat]
            for gi, first in enumerate(groups):
                for gj, second in enumerate(groups):
                    if not _groups_conflict(first, second, rules, relation):
                        continue
                    v = model.new_bool_var(f"v_{a}_{b}_{gi}_{gj}_{relation}")
                    model.add(v >= x[a, gi] + x[b, gj] - 1)
                    model.add(seat_affected[a] >= v)
                    model.add(seat_affected[b] >= v)
                    violations.append(v)

    # Denge: hem derslik doluluğu hem de her grubun dersliklere yayılması.
    toplam_kapasite = len(seat_ids)
    balance_terms = []
    for room in rooms:
        room_seats = [seat_index[seat["id"]] for seat in room["seats"] if seat["is_available"]]
        if not room_seats:
            raise ValueError("Her seçilmiş derslikte en az bir kullanılabilir koltuk bulunmalı.")
        kapasite = len(room_seats)
        for g, key in enumerate(groups):
            if key == BOS_GRUP:
                continue
            sayi = model.new_int_var(0, min(sizes[key], kapasite), f"n_{g}_{room['id']}")
            model.add(sayi == sum(x[s, g] for s in room_seats))
            fark = model.new_int_var(0, sizes[key] * max(1, toplam_kapasite), f"d_{g}_{room['id']}")
            model.add_abs_equality(fark, sayi * toplam_kapasite - sizes[key] * kapasite)
            balance_terms.append(fark)

    # Etkilenen öğrenci sayısı her zaman dengeden ağır basar.
    agirlik = len(balance_terms) * len(participants) * max(1, toplam_kapasite) + 1
    model.minimize(sum(seat_affected) * agirlik + sum(balance_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    if progress is not None:
        progress.set_stage("search")
    callback = _ProgressCallback(progress, seat_affected) if progress is not None else None
    done = threading.Event()
    if progress is not None:
        def _watch_stop():
            while not done.wait(0.2):
                if progress.stop_event.is_set():
                    solver.stop_search()
                    return
        threading.Thread(target=_watch_stop, daemon=True).start()
    try:
        status = solver.solve(model, callback) if callback else solver.solve(model)
    finally:
        done.set()

    stopped = progress is not None and progress.stop_event.is_set()
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"ok": False, "status": status, "stopped": stopped}

    layout: dict[str, tuple[str, str, str]] = {}
    for s, seat_id in enumerate(seat_ids):
        layout[seat_id] = next(groups[g] for g in range(len(groups)) if solver.boolean_value(x[s, g]))
    return {
        "ok": True,
        "layout": layout,
        "affected_student_count": sum(solver.boolean_value(v) for v in seat_affected),
        "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
        "objective": int(solver.objective_value),
        "stopped": stopped,
    }


def assign_students(participants: list[dict], layout: dict[str, tuple[str, str, str]],
                    fixed_assignments: dict[str, str] | None = None,
                    previous_assignments: list[dict] | None = None) -> dict[str, str]:
    """İkinci aşama: grubun kazandığı koltuklara o gruptaki öğrencileri yerleştir.

    Kurallar yalnızca gruba baktığı için bu eşleme ihlal sayısını değiştiremez;
    bu yüzden çözücüye gerek yoktur. Önceki dağıtımdan belirgin biçimde farklı
    bir alternatif istendiğinde öğrenciler grup içinde kaydırılır.
    """
    fixed_assignments = fixed_assignments or {}
    koltuklar: dict[tuple[str, str, str], list[str]] = {}
    for seat_id, key in layout.items():
        if key != BOS_GRUP:
            koltuklar.setdefault(key, []).append(seat_id)
    for seat_list in koltuklar.values():
        seat_list.sort()

    ogrenciler: dict[tuple[str, str, str], list[str]] = {}
    for item in participants:
        ogrenciler.setdefault(group_key(item), []).append(item["id"])
    for ids in ogrenciler.values():
        ids.sort()

    sonuc: dict[str, str] = {}
    for participant_id, seat_id in fixed_assignments.items():
        sonuc[participant_id] = seat_id

    # previous_assignments, önceki adayların listesidir (her biri yerleşim listesi).
    # Yeni adayın onlardan farklı olması için varlığı yeterli; hangisi olduğu değil.
    onceki = bool(previous_assignments)

    for key, seat_list in koltuklar.items():
        kalan_koltuk = [s for s in seat_list if s not in set(fixed_assignments.values())]
        kalan_ogrenci = [p for p in ogrenciler.get(key, []) if p not in fixed_assignments]
        if len(kalan_koltuk) != len(kalan_ogrenci):
            raise ValueError("Grup yerleşimi ile öğrenci sayısı örtüşmedi.")
        if onceki:
            # Önceki yerleşimden farklı bir alternatif üret: grup içinde kaydır.
            kaydirma = max(1, ceil(len(kalan_ogrenci) * 0.5))
            kalan_ogrenci = kalan_ogrenci[kaydirma:] + kalan_ogrenci[:kaydirma]
        for participant_id, seat_id in zip(kalan_ogrenci, kalan_koltuk, strict=True):
            sonuc[participant_id] = seat_id
    return sonuc
