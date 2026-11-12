"""Derslik planı ucu ve düzenleme uçlarının kopyala/yerinde kuralı."""

import unittest

from _plan_support import PlanTestMixin


class ClassroomPlanApiTests(PlanTestMixin, unittest.TestCase):
    def _plan(self, classroom_id):
        return self.client.get(f"/api/classrooms/{classroom_id}/plan?academic_year_id={self.year_id}")

    def _first_seat(self, classroom_id, layout_id):
        desk = self.layout_detail(classroom_id, layout_id)["desks"][0]
        return desk, desk["seats"][0]

    def _finalized(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        exam_id = self.make_exam("KESİN SINAV", layout_ids=[layout["id"]])
        self.distribute(exam_id)
        self.finalize(exam_id)
        return classroom_id, layout["id"], exam_id

    def test_plan_endpoint_returns_the_active_plan_with_usage(self):
        classroom_id = self.make_classroom()
        active = self.make_layout(classroom_id)
        self.make_layout(classroom_id, "İkinci plan")
        self.make_exam(layout_ids=[active["id"]])
        response = self._plan(classroom_id)
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data["plan"]["layout"]["id"], active["id"])
        self.assertTrue(data["plan"]["desks"])
        self.assertEqual((data["plan"]["exam_count"], data["plan"]["finalized_exam_count"]), (1, 0))
        self.assertEqual(data["other_layout_count"], 1)
        self.assertEqual(data["classroom"]["id"], classroom_id)

    def test_plan_endpoint_counts_finalized_exams(self):
        classroom_id, _layout_id, _exam_id = self._finalized()
        plan = self._plan(classroom_id).get_json()["plan"]
        self.assertEqual((plan["exam_count"], plan["finalized_exam_count"]), (1, 1))

    def test_classroom_without_any_plan_returns_null_plan(self):
        classroom_id = self.make_classroom("PLANSIZ SALON")
        response = self._plan(classroom_id)
        self.assertEqual((response.status_code, response.get_json()["plan"]), (200, None))

    def test_plan_endpoint_requires_a_year_and_a_known_classroom(self):
        classroom_id = self.make_classroom()
        self.assertEqual(self.client.get(f"/api/classrooms/{classroom_id}/plan").status_code, 400)
        self.assertEqual(
            self.client.get(f"/api/classrooms/yok/plan?academic_year_id={self.year_id}").status_code, 404)

    def test_seat_toggle_on_unused_plan_edits_in_place(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        _desk, seat = self._first_seat(classroom_id, layout["id"])
        response = self.client.patch(
            f"/api/classrooms/{classroom_id}/layouts/{layout['id']}/seats/{seat['id']}",
            json={"is_available": False, "unavailable_reason": "kırık"})
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual((data["copied"], data["layout_id"], data["affected_draft_exam_count"]),
                         (False, layout["id"], 0))
        self.assertEqual(self.seat_count(layout["id"], available_only=True), 7)

    def test_seat_toggle_on_finalized_plan_edits_the_copy(self):
        classroom_id, layout_id, _exam_id = self._finalized()
        _desk, seat = self._first_seat(classroom_id, layout_id)
        response = self.client.patch(
            f"/api/classrooms/{classroom_id}/layouts/{layout_id}/seats/{seat['id']}",
            json={"is_available": False, "unavailable_reason": "kırık"})
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertTrue(data["copied"])
        self.assertNotEqual(data["layout_id"], layout_id)
        # Kesinleşmiş sınavın planı aynen durur; değişiklik kopyaya yazılır.
        self.assertEqual(self.seat_count(layout_id, available_only=True), 8)
        self.assertEqual(self.seat_count(data["layout_id"], available_only=True), 7)
        copied_seats = [s for d in self.layout_detail(classroom_id, data["layout_id"])["desks"] for s in d["seats"]]
        closed = [s["seat_number"] for s in copied_seats if not s["is_available"]]
        self.assertEqual(closed, [seat["seat_number"]])

    def test_desk_move_on_finalized_plan_moves_the_matching_desk_of_the_copy(self):
        classroom_id, layout_id, _exam_id = self._finalized()
        desk, _seat = self._first_seat(classroom_id, layout_id)
        response = self.client.patch(
            f"/api/classrooms/{classroom_id}/layouts/{layout_id}/desks/{desk['id']}",
            json={"x": 20.0, "y": 20.0})
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertTrue(data["copied"])
        original = next(d for d in self.layout_detail(classroom_id, layout_id)["desks"] if d["id"] == desk["id"])
        self.assertEqual((original["x"], original["y"]), (desk["x"], desk["y"]))
        moved = next(d for d in self.layout_detail(classroom_id, data["layout_id"])["desks"]
                     if d["label"] == desk["label"])
        self.assertEqual((moved["x"], moved["y"]), (20.0, 20.0))

    def test_desk_move_reports_affected_draft_exams(self):
        classroom_id, layout_id, _exam_id = self._finalized()
        draft_id = self.make_exam("TASLAK SINAV", layout_ids=[layout_id])
        desk, _seat = self._first_seat(classroom_id, layout_id)
        data = self.client.patch(
            f"/api/classrooms/{classroom_id}/layouts/{layout_id}/desks/{desk['id']}",
            json={"x": 20.0, "y": 20.0}).get_json()
        self.assertEqual(data["affected_draft_exam_count"], 1)
        self.assertEqual([r["layout_id"] for r in self.exam(draft_id)["room_selections"]], [data["layout_id"]])

    def test_archive_year_edit_is_refused_without_side_effects(self):
        classroom_id = self.make_classroom()
        archive_id = self.make_archive_layout(classroom_id)
        before = len(self.layouts(classroom_id))
        response = self.client.patch(
            f"/api/classrooms/{classroom_id}/layouts/{archive_id}/seats/olmayan",
            json={"is_available": False})
        self.assertIn(response.status_code, (403, 404))
        self.assertEqual(len(self.layouts(classroom_id)), before)

    def test_older_plan_state_can_no_longer_be_edited_directly(self):
        """Eski hâl (aktif olmayan, daha yeni sürümü olan plan) düzenlenemez."""
        classroom_id, layout_id, _exam_id = self._finalized()
        _desk, seat = self._first_seat(classroom_id, layout_id)
        first = self.client.patch(
            f"/api/classrooms/{classroom_id}/layouts/{layout_id}/seats/{seat['id']}",
            json={"is_available": False}).get_json()
        again = self.client.patch(
            f"/api/classrooms/{classroom_id}/layouts/{layout_id}/seats/{seat['id']}",
            json={"is_available": True})
        self.assertEqual(again.status_code, 409, again.get_json())
        self.assertEqual(len(self.layouts(classroom_id)), 2)
        self.assertEqual(self.seat_count(first["layout_id"], available_only=True), 7)


if __name__ == "__main__":
    unittest.main()
