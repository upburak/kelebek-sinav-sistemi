"""Sınavın aşaması ve taslak sınavların dersliğin aktif planını izlemesi."""

import unittest

from _plan_support import PlanTestMixin


class ExamPlanFollowTests(PlanTestMixin, unittest.TestCase):
    def _room(self):
        classroom_id = self.make_classroom()
        return classroom_id, self.make_layout(classroom_id)["id"]

    def _toggle_seat(self, classroom_id, layout_id, index=0, available=False):
        seats = [s for d in self.layout_detail(classroom_id, layout_id)["desks"] for s in d["seats"]]
        response = self.client.patch(
            f"/api/classrooms/{classroom_id}/layouts/{layout_id}/seats/{seats[index]['id']}",
            json={"is_available": available})
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def test_stage_follows_the_exam_through_its_life(self):
        _classroom_id, layout_id = self._room()
        exam_id = self.make_exam()
        self.assertEqual(self.exam(exam_id)["stage"], "rooms")
        self.select_rooms(exam_id, [layout_id])
        self.assertEqual(self.exam(exam_id)["stage"], "distribute")
        self.distribute(exam_id)
        self.assertEqual(self.exam(exam_id)["stage"], "review")
        self.finalize(exam_id)
        self.assertEqual(self.exam(exam_id)["stage"], "done")
        archived = self.client.post(f"/api/exam-organizations/{exam_id}/complete", json={"confirm": True})
        self.assertEqual(archived.status_code, 200, archived.get_json())
        self.assertEqual(self.exam(exam_id)["stage"], "archived")

    def test_new_exam_response_already_carries_the_new_fields(self):
        exam_id = self.make_exam()
        exam = self.exam(exam_id)
        self.assertEqual((exam["stage"], exam["needs_redistribution"]), ("rooms", False))

    def test_plan_change_marks_the_draft_for_redistribution(self):
        classroom_id, layout_id = self._room()
        exam_id = self.make_exam(layout_ids=[layout_id])
        self.assertFalse(self.exam(exam_id)["needs_redistribution"])
        self.distribute(exam_id)
        self.assertFalse(self.exam(exam_id)["needs_redistribution"])
        self._toggle_seat(classroom_id, layout_id)
        exam = self.exam(exam_id)
        self.assertTrue(exam["needs_redistribution"])
        self.assertEqual(exam["stage"], "distribute")
        self.assertEqual(self.candidates(exam_id), [])

    def test_redistributing_clears_the_flag(self):
        classroom_id, layout_id = self._room()
        exam_id = self.make_exam(layout_ids=[layout_id])
        self.distribute(exam_id)
        self._toggle_seat(classroom_id, layout_id)
        self.distribute(exam_id)
        exam = self.exam(exam_id)
        self.assertEqual((exam["needs_redistribution"], exam["stage"]), (False, "review"))

    def test_plan_shrinking_below_student_count_sends_exam_back_to_rooms(self):
        classroom_id, layout_id = self._room()
        exam_id = self.make_exam(layout_ids=[layout_id])
        self.distribute(exam_id)
        participants = self.exam(exam_id)["participant_count"]
        for index in range(8 - participants + 1):   # 8 koltuktan, öğrenci sayısının bir eksiğine in
            self._toggle_seat(classroom_id, layout_id, index)
        exam = self.exam(exam_id)
        self.assertEqual((exam["stage"], exam["capacity_deficit"]), ("rooms", 1))

    def test_activating_another_plan_moves_draft_exams_to_it(self):
        classroom_id, first_id = self._room()
        second_id = self.make_layout(classroom_id, "İkinci plan")["id"]
        exam_id = self.make_exam(layout_ids=[first_id])
        response = self.client.post(f"/api/classrooms/{classroom_id}/layouts/{second_id}/activate")
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["affected_draft_exam_count"], 1)
        self.assertEqual(self.exam(exam_id)["room_selections"][0]["layout_id"], second_id)

    def test_activating_does_not_touch_finalized_exams(self):
        classroom_id, first_id = self._room()
        second_id = self.make_layout(classroom_id, "İkinci plan")["id"]
        exam_id = self.make_exam(layout_ids=[first_id])
        self.distribute(exam_id)
        self.finalize(exam_id)
        data = self.client.post(f"/api/classrooms/{classroom_id}/layouts/{second_id}/activate").get_json()
        self.assertEqual(data["affected_draft_exam_count"], 0)
        self.assertEqual(self.exam(exam_id)["room_selections"][0]["layout_id"], first_id)

    def test_exam_lists_its_classes_with_student_counts(self):
        """Sınava giren sınıflar her zaman görülebilmeli; eksik bir sınıf gözden kaçmamalı."""
        exam_id = self.make_exam()
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        expected = sorted((g["class_level"], g["section"], g["student_count"]) for g in groups)
        listed = sorted((g["class_level"], g["section"], g["student_count"]) for g in self.exam(exam_id)["groups"])
        self.assertEqual(listed, expected)
        self.assertEqual(sum(g["student_count"] for g in self.exam(exam_id)["groups"]),
                         self.exam(exam_id)["participant_count"])

    def test_partially_included_class_is_exposed(self):
        """Sınıfın yalnızca bir bölümü sınava alındıysa (alanı farklı öğrenciler dışarıda) bu görünmeli."""
        from kelebek.models import Student, StudentYearEnrollment

        with self.factory.begin() as session:
            for index, area in enumerate(("Sayısal", "Sayısal", None)):
                student = Student()
                session.add(student)
                session.flush()
                session.add(StudentYearEnrollment(
                    academic_year_id=self.year_id, student_id=student.id, school_number=f"ALAN-{index}",
                    first_name=f"ALAN AD {index}", last_name="SENTETİK", class_level="11", section="A", area=area))
        period = self.client.get(f"/api/exam-periods?academic_year_id={self.year_id}").get_json()["periods"][0]
        created = self.client.post("/api/exam-organizations", json={
            "academic_year_id": self.year_id, "name": "KISMİ SINIF", "exam_date": "2026-12-01",
            "exam_period_id": period["id"],
            "participant_groups": [{"class_level": "11", "section": "A", "area": "Sayısal"}],
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        for exam in (created.get_json()["organization"], self.exam(created.get_json()["organization"]["id"])):
            self.assertEqual(exam["group_count"], 1)
            self.assertEqual(
                [(g["class_level"], g["section"], g["student_count"], g["class_total"]) for g in exam["groups"]],
                [("11", "A", 2, 3)])

    def test_group_count_matches_the_listed_classes(self):
        exam = self.exam(self.make_exam())
        self.assertEqual(exam["group_count"], len(exam["groups"]))
        self.assertTrue(all(g["student_count"] == g["class_total"] for g in exam["groups"]))

    def test_group_count_counts_class_sections(self):
        exam_id = self.make_exam()
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        self.assertEqual(self.exam(exam_id)["group_count"], len(groups))


if __name__ == "__main__":
    unittest.main()
