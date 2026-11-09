"""İhlal çözüm önerisi: kendi ihlalini gideren ve yeni ihlal yaratmayan boş yerler önerilir."""

import unittest

from kelebek.distribution.solver import evaluate_assignments, suggest_violation_fixes

RULES = {name: True for name in (
    "prevent_same_section_adjacent", "prevent_same_section_front_back",
    "prevent_different_grade_same_area_adjacent", "prevent_different_grade_same_area_front_back",
    "prevent_same_grade_area_adjacent", "prevent_same_grade_area_front_back",
)}


class ViolationSuggestionTests(unittest.TestCase):
    def test_suggests_nearest_conflict_free_seat_in_same_room(self):
        participants = [
            {"id": "a", "class_level": "9", "section": "A", "area": None},
            {"id": "b", "class_level": "9", "section": "A", "area": None},
            {"id": "c", "class_level": "10", "section": "B", "area": None},
        ]
        # s1-s2 yan yana, s2-s3 yan yana, s3-s4 yan yana; s5 ayrı.
        pairs = {"adjacent": [("s1", "s2"), ("s2", "s3"), ("s3", "s4")], "front_back": []}
        seat_info = {seat: {"classroom_id": "r1", "classroom_name": "R1", "seat_number": index + 1, "x": float(index), "y": 0.0}
                     for index, seat in enumerate(["s1", "s2", "s3", "s4", "s5"])}
        assignments = {"a": "s1", "b": "s2", "c": "s4"}
        evaluation = evaluate_assignments(participants, pairs, RULES, assignments)
        self.assertEqual(evaluation["affected_student_count"], 2)
        self.assertEqual(evaluation["violations"][0]["reason"], "Aynı şube · yan yana")
        suggestions = suggest_violation_fixes(participants, pairs, RULES, assignments, seat_info, evaluation["violations"])
        # a için s3 (b'nin yanı) olmaz; en yakın uygun boş yer s5'tir.
        self.assertEqual([item["seat_id"] for item in suggestions["a"]], ["s5"])
        self.assertEqual(suggestions["b"][0]["seat_id"], "s3")
        moved = {**assignments, "b": suggestions["b"][0]["seat_id"]}
        self.assertEqual(evaluate_assignments(participants, pairs, RULES, moved)["violation_count"], 0)


if __name__ == "__main__":
    unittest.main()
