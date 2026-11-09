"""CP-SAT engine for a first, capacity-safe seating candidate."""

from itertools import combinations
from math import ceil

from ortools.sat.python import cp_model


RULES = {
    "adjacent": ("prevent_same_section_adjacent", "prevent_different_grade_same_area_adjacent", "prevent_same_grade_area_adjacent"),
    "front_back": ("prevent_same_section_front_back", "prevent_different_grade_same_area_front_back", "prevent_same_grade_area_front_back"),
}


class DistributionError(ValueError):
    pass


def _participants_conflict(first: dict, second: dict, rules: dict, relation: str) -> bool:
    same_section = first["class_level"] == second["class_level"] and first["section"].casefold() == second["section"].casefold()
    same_area = bool(first.get("area")) and (first.get("area") or "").casefold() == (second.get("area") or "").casefold()
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
    violations = set()
    for relation in ("adjacent", "front_back"):
        for first_seat, second_seat in seat_pairs[relation]:
            first_id, second_id = by_seat.get(first_seat), by_seat.get(second_seat)
            if not first_id or not second_id:
                continue
            if _participants_conflict(by_participant[first_id], by_participant[second_id], rules, relation):
                violations.add((min(first_id, second_id), max(first_id, second_id), relation))
                affected.update((first_id, second_id))
    return {"affected_student_count": len(affected), "violation_count": len(violations)}


def solve_candidate(participants: list[dict], rooms: list[dict], seat_pairs: dict, rules: dict, time_limit: float = 12.0, previous_assignments: list[dict] | None = None, fixed_assignments: dict[str, str] | None = None) -> dict:
    """Assign every participant uniquely, balancing room use and limiting conflicts to five people."""
    if not participants:
        raise DistributionError("Dağıtılacak öğrenci bulunamadı.")
    seats = [seat for room in rooms for seat in room["seats"] if seat["is_available"]]
    if len(seats) < len(participants):
        raise DistributionError(f"Kapasite yetersiz: {len(participants)} öğrenci, {len(seats)} kullanılabilir koltuk.")
    if not rooms or any(not any(seat["is_available"] for seat in room["seats"]) for room in rooms):
        raise DistributionError("Her seçilmiş derslikte en az bir kullanılabilir koltuk bulunmalı.")

    model = cp_model.CpModel()
    choices = {}
    seat_by_id = {seat["id"]: seat for seat in seats}
    for student_index, _student in enumerate(participants):
        for seat_id, seat in seat_by_id.items():
            choices[student_index, seat_id] = model.new_bool_var(f"x_{student_index}_{seat_id}")
        model.add_exactly_one(choices[student_index, seat_id] for seat_id in seat_by_id)
    for seat_id in seat_by_id:
        model.add_at_most_one(choices[student_index, seat_id] for student_index in range(len(participants)))

    participant_index = {item["id"]: index for index, item in enumerate(participants)}
    fixed_assignments = fixed_assignments or {}
    for participant_id, seat_id in fixed_assignments.items():
        if participant_id not in participant_index or seat_id not in seat_by_id:
            raise DistributionError("Sabitlenen derslikteki bir yerleşim artık geçerli değil; sabitlemeyi yenileyin.")
        model.add(choices[participant_index[participant_id], seat_id] == 1)
    free_count = len(participants) - len(fixed_assignments)
    if free_count <= 0:
        raise DistributionError("Yeniden dağıtılacak öğrenci kalmadı; en az bir dersliği sabitlemeden bırakın.")
    for prior in previous_assignments or []:
        retained = [
            choices[participant_index[item["participant_id"]], item["seat_id"]]
            for item in prior
            if item["participant_id"] in participant_index and item["seat_id"] in seat_by_id
            and item["participant_id"] not in fixed_assignments
        ]
        if retained:
            model.add(sum(retained) <= free_count - max(1, ceil(free_count * 0.2)))

    room_counts = {}
    for room_index, room in enumerate(rooms):
        room_seat_ids = [seat["id"] for seat in room["seats"] if seat["is_available"]]
        count = model.new_int_var(0, min(len(participants), len(room_seat_ids)), f"room_count_{room_index}")
        model.add(count == sum(choices[student_index, seat_id] for student_index in range(len(participants)) for seat_id in room_seat_ids))
        room_counts[room_index] = count

    group_keys = sorted({(item["class_level"], item["section"].casefold(), (item.get("area") or "").casefold()) for item in participants})
    student_indexes_by_group = {
        key: [index for index, item in enumerate(participants) if (item["class_level"], item["section"].casefold(), (item.get("area") or "").casefold()) == key]
        for key in group_keys
    }
    affected = [model.new_bool_var(f"affected_{index}") for index in range(len(participants))]
    pair_violations = []
    for first_index, second_index in combinations(range(len(participants)), 2):
        first, second = participants[first_index], participants[second_index]
        for relation, enabled_rules in RULES.items():
            if not any(rules[name] for name in enabled_rules):
                continue
            relation_conflict = False
            relation_conflict = _participants_conflict(first, second, rules, relation)
            pairs = seat_pairs[relation]
            if not relation_conflict:
                continue
            for first_seat, second_seat in pairs:
                if first_seat not in seat_by_id or second_seat not in seat_by_id:
                    continue
                violation = model.new_bool_var(f"v_{first_index}_{second_index}_{relation}_{first_seat}_{second_seat}")
                model.add(violation >= choices[first_index, first_seat] + choices[second_index, second_seat] - 1)
                model.add(violation >= choices[first_index, second_seat] + choices[second_index, first_seat] - 1)
                model.add(affected[first_index] >= violation)
                model.add(affected[second_index] >= violation)
                pair_violations.append(violation)
    model.add(sum(affected) <= 5)

    total_capacity = sum(len([seat for seat in room["seats"] if seat["is_available"]]) for room in rooms)
    balance_terms = []
    for room_index, room in enumerate(rooms):
        capacity = len([seat for seat in room["seats"] if seat["is_available"]])
        delta = model.new_int_var(0, len(participants) * max(1, total_capacity), f"balance_{room_index}")
        model.add_abs_equality(delta, room_counts[room_index] * total_capacity - len(participants) * capacity)
        balance_terms.append(delta)
        for group_index, key in enumerate(group_keys):
            group_students = student_indexes_by_group[key]
            group_count = model.new_int_var(0, min(len(group_students), capacity), f"group_{group_index}_room_{room_index}")
            model.add(group_count == sum(choices[student_index, seat_id] for student_index in group_students for seat_id in room_seat_ids))
            group_delta = model.new_int_var(0, len(group_students) * max(1, total_capacity), f"group_balance_{group_index}_{room_index}")
            model.add_abs_equality(group_delta, group_count * total_capacity - len(group_students) * capacity)
            balance_terms.append(group_delta)
    conflict_weight = len(balance_terms) * len(participants) * max(1, total_capacity) + 1
    model.minimize(sum(affected) * conflict_weight + sum(balance_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if status == cp_model.INFEASIBLE:
            raise DistributionError("Bu derslik ve kural birleşimiyle beş veya daha az öğrencinin etkilendiği bir aday mümkün görünmüyor.")
        if status == cp_model.MODEL_INVALID:
            raise DistributionError("Dağıtım modeli doğrulanamadı; derslik düzeni ve kural verilerini kontrol edin.")
        raise DistributionError("Arama süresi içinde geçerli aday bulunamadı. Bu sonuç, adayın matematiksel olarak imkânsız olduğunu kanıtlamaz; süre artırılarak yeniden denenebilir.")
    assignments = []
    for student_index, participant in enumerate(participants):
        seat_id = next(seat_id for seat_id in seat_by_id if solver.boolean_value(choices[student_index, seat_id]))
        assignments.append({"participant_id": participant["id"], "seat_id": seat_id, "classroom_id": seat_by_id[seat_id]["classroom_id"]})
    return {
        "assignments": assignments,
        "affected_student_count": sum(solver.boolean_value(item) for item in affected),
        "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
        "objective": int(solver.objective_value),
    }
