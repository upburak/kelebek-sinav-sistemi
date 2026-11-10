"""CP-SAT engine for a first, capacity-safe seating candidate."""


from ortools.sat.python import cp_model

from kelebek.distribution.seating import assign_students, solve_group_layout

RULES = {
    "adjacent": ("prevent_same_section_adjacent", "prevent_different_grade_same_area_adjacent",
                 "prevent_same_grade_area_adjacent", "prevent_same_grade_adjacent"),
    "front_back": ("prevent_same_section_front_back", "prevent_different_grade_same_area_front_back",
                   "prevent_same_grade_area_front_back", "prevent_same_grade_front_back"),
}


REASONS = {
    "prevent_same_section": "Aynı şube",
    "prevent_same_grade_area": "Aynı sınıf seviyesi ve alan",
    "prevent_different_grade_same_area": "Farklı sınıf seviyesi, aynı alan",
    "prevent_same_grade": "Aynı sınıf seviyesi",
}
RELATION_LABELS = {"adjacent": "yan yana", "front_back": "önlü-arkalı"}


class DistributionError(ValueError):
    pass


class _ProgressCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, progress, affected):
        super().__init__()
        self._progress = progress
        self._affected = affected

    def on_solution_callback(self):
        self._progress.record_solution(self.objective_value, sum(self.boolean_value(item) for item in self._affected))


def _conflict_reason(first: dict, second: dict, rules: dict, relation: str) -> str | None:
    same_section = first["class_level"] == second["class_level"] and first["section"].casefold() == second["section"].casefold()
    same_area = bool(first.get("area")) and (first.get("area") or "").casefold() == (second.get("area") or "").casefold()
    suffix = "_adjacent" if relation == "adjacent" else "_front_back"
    if same_section and rules["prevent_same_section" + suffix]:
        return "prevent_same_section"
    if same_area and first["class_level"] == second["class_level"] and rules["prevent_same_grade_area" + suffix]:
        return "prevent_same_grade_area"
    if same_area and first["class_level"] != second["class_level"] and rules["prevent_different_grade_same_area" + suffix]:
        return "prevent_different_grade_same_area"
    # Kural 7-8: aynı sınıf seviyesi (şube ve alan ayrımı olmadan). Daha dar olan
    # kurallar yukarıda ele alındığı için gerekçe olarak en sonda denenir.
    if first["class_level"] == second["class_level"] and rules.get("prevent_same_grade" + suffix):
        return "prevent_same_grade"
    return None


def _participants_conflict(first: dict, second: dict, rules: dict, relation: str) -> bool:
    same_section = first["class_level"] == second["class_level"] and first["section"].casefold() == second["section"].casefold()
    same_area = bool(first.get("area")) and (first.get("area") or "").casefold() == (second.get("area") or "").casefold()
    if first["class_level"] == second["class_level"] and rules.get("prevent_same_grade" + ("_adjacent" if relation == "adjacent" else "_front_back")):
        return True
    if relation == "adjacent":
        return (same_section and rules["prevent_same_section_adjacent"]) or (
            same_area and first["class_level"] == second["class_level"] and rules["prevent_same_grade_area_adjacent"]
        ) or (same_area and first["class_level"] != second["class_level"] and rules["prevent_different_grade_same_area_adjacent"])
    return (same_section and rules["prevent_same_section_front_back"]) or (
        same_area and first["class_level"] == second["class_level"] and rules["prevent_same_grade_area_front_back"]
    ) or (same_area and first["class_level"] != second["class_level"] and rules["prevent_different_grade_same_area_front_back"])


def evaluate_assignments(participants: list[dict], seat_pairs: dict, rules: dict, assignments: dict[str, str]) -> dict:
    """Recompute active rule violations from a persisted participant/seat mapping."""
    by_seat = {seat_id: participant_id for participant_id, seat_id in assignments.items()}
    by_participant = {item["id"]: item for item in participants}
    affected = set()
    violations = {}
    for relation in ("adjacent", "front_back"):
        for first_seat, second_seat in seat_pairs[relation]:
            first_id, second_id = by_seat.get(first_seat), by_seat.get(second_seat)
            if not first_id or not second_id:
                continue
            reason = _conflict_reason(by_participant[first_id], by_participant[second_id], rules, relation)
            if reason:
                key = (min(first_id, second_id), max(first_id, second_id), relation)
                violations.setdefault(key, {
                    "first_participant_id": first_id, "second_participant_id": second_id,
                    "first_seat_id": first_seat, "second_seat_id": second_seat, "relation": relation,
                    "reason": f"{REASONS[reason]} · {RELATION_LABELS[relation]}",
                })
                affected.update((first_id, second_id))
    return {"affected_student_count": len(affected), "violation_count": len(violations),
            "violations": list(violations.values())}


def suggest_violation_fixes(participants: list[dict], seat_pairs: dict, rules: dict, assignments: dict[str, str],
                            seat_info: dict, violations: list[dict], limit: int = 3) -> dict:
    """İhlalli her öğrenci için, taşındığında kendi ihlallerini giderip yeni ihlal yaratmayan boş yerleri öner."""
    by_participant = {item["id"]: item for item in participants}
    by_seat = {seat_id: participant_id for participant_id, seat_id in assignments.items()}
    neighbors: dict[str, list[tuple[str, str]]] = {}
    for relation in ("adjacent", "front_back"):
        for first, second in seat_pairs[relation]:
            neighbors.setdefault(first, []).append((second, relation))
            neighbors.setdefault(second, []).append((first, relation))
    free_seats = [seat_id for seat_id in seat_info if seat_id not in by_seat]
    affected = {item["first_participant_id"] for item in violations} | {item["second_participant_id"] for item in violations}
    suggestions = {}
    for participant_id in sorted(affected):
        current = seat_info.get(assignments.get(participant_id), {})
        options = []
        for seat_id in free_seats:
            clash = any(
                (other := by_seat.get(neighbor)) and other != participant_id
                and _conflict_reason(by_participant[participant_id], by_participant[other], rules, relation)
                for neighbor, relation in neighbors.get(seat_id, [])
            )
            if clash:
                continue
            info = seat_info[seat_id]
            same_room = info["classroom_id"] == current.get("classroom_id")
            distance = ((info["x"] - current.get("x", 0)) ** 2 + (info["y"] - current.get("y", 0)) ** 2) ** 0.5 if same_room else 10_000
            options.append((not same_room, distance, info["classroom_name"], info["seat_number"], seat_id))
        suggestions[participant_id] = [
            {"seat_id": seat_id, "classroom_name": room, "seat_number": number, "same_room": not other_room}
            for other_room, _distance, room, number, seat_id in sorted(options)[:limit]
        ]
    return suggestions


def solve_candidate(participants: list[dict], rooms: list[dict], seat_pairs: dict, rules: dict, time_limit: float = 12.0, previous_assignments: list[dict] | None = None, fixed_assignments: dict[str, str] | None = None, progress=None) -> dict:
    """Kapasiteye uyan bir oturma adayı üret.

    Model öğrenci değil **grup** üzerinden kurulur (bkz. ``seating`` modülü):
    kuralların tamamı sınıf seviyesi/şube/alan üçlüsüne baktığı için aynı
    gruptaki öğrenciler birbirinin yerine geçebilir. Bu sayede değişken sayısı
    öğrenci×koltuk yerine koltuk×grup olur ve gerçek okul mevcutlarında
    (yüzlerce öğrenci) çözüm saniyeler içinde bulunur.
    """
    seats = [seat for room in rooms for seat in room["seats"] if seat["is_available"]]
    if len(seats) < len(participants):
        raise DistributionError(f"Kapasite yetersiz: {len(participants)} öğrenci, {len(seats)} kullanılabilir koltuk.")
    if not rooms or any(not any(seat["is_available"] for seat in room["seats"]) for room in rooms):
        raise DistributionError("Her seçilmiş derslikte en az bir kullanılabilir koltuk bulunmalı.")

    fixed_assignments = fixed_assignments or {}
    if fixed_assignments and len(participants) - len(fixed_assignments) <= 0:
        raise DistributionError("Yeniden dağıtılacak öğrenci kalmadı; en az bir dersliği sabitlemeden bırakın.")

    try:
        sonuc = solve_group_layout(participants, rooms, seat_pairs, rules, time_limit,
                                   fixed_assignments, progress)
    except ValueError as error:
        raise DistributionError(str(error)) from None

    if not sonuc["ok"]:
        if sonuc["stopped"]:
            raise DistributionError("Dağıtım durduruldu; henüz geçerli bir çözüm bulunmamıştı. Yeniden başlatabilirsiniz.")
        if sonuc["status"] == cp_model.INFEASIBLE:
            raise DistributionError("Seçilen derslikler bu öğrenci listesine yetmiyor veya sabitlenen yerleşim çelişkili.")
        if sonuc["status"] == cp_model.MODEL_INVALID:
            raise DistributionError("Dağıtım modeli doğrulanamadı; derslik düzeni ve kural verilerini kontrol edin.")
        raise DistributionError("Arama süresi içinde geçerli aday bulunamadı. Bu sonuç, adayın matematiksel olarak imkânsız olduğunu kanıtlamaz; süre artırılarak yeniden denenebilir.")

    try:
        eslesme = assign_students(participants, sonuc["layout"], fixed_assignments, previous_assignments)
    except ValueError as error:
        raise DistributionError(str(error)) from None

    seat_by_id = {seat["id"]: seat for seat in seats}
    assignments = [
        {"participant_id": item["id"], "seat_id": eslesme[item["id"]],
         "classroom_id": seat_by_id[eslesme[item["id"]]]["classroom_id"]}
        for item in participants
    ]
    return {
        "assignments": assignments,
        "affected_student_count": sonuc["affected_student_count"],
        "status": sonuc["status"],
        "objective": sonuc["objective"],
        "stopped": sonuc["stopped"],
    }
