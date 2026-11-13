"""Plan yapısı düzenleme: satır/sütun ekle, taşı, masa türü, masa sil; derslik kapat/sil."""

import unittest

from _plan_support import PlanTestMixin


class LayoutStructureTests(PlanTestMixin, unittest.TestCase):
    def _room(self):
        classroom_id = self.make_classroom()
        return classroom_id, self.make_layout(classroom_id)["id"]

    def _op(self, classroom_id, layout_id, **operation):
        return self.client.post(f"/api/classrooms/{classroom_id}/layouts/{layout_id}/structure", json=operation)

    def _numbers(self, detail):
        return sorted(seat["seat_number"] for desk in detail["desks"] for seat in desk["seats"])

    def test_add_row_adds_a_desk_under_every_column_and_renumbers(self):
        classroom_id, layout_id = self._room()
        response = self._op(classroom_id, layout_id, op="add_row")
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(len(data["desks"]), 6)
        self.assertEqual(self._numbers(data), list(range(1, 13)))
        self.assertEqual({desk["label"] for desk in data["desks"]},
                         {"S1-M1", "S2-M1", "S3-M1", "S1-M2", "S2-M2", "S3-M2"})
        self.assertFalse(data["copied"])

    def test_add_column_extends_the_last_block(self):
        classroom_id, layout_id = self._room()
        data = self._op(classroom_id, layout_id, op="add_column").get_json()
        self.assertEqual(len(data["desks"]), 6)
        new = [desk for desk in data["desks"] if desk["label"].endswith("M3")]
        self.assertEqual({desk["block_label"] for desk in new}, {"B2"})
        self.assertEqual(self._numbers(data), list(range(1, 13)))

    def test_move_column_opens_a_corridor_and_refuses_an_occupied_target(self):
        classroom_id, layout_id = self._room()
        self._op(classroom_id, layout_id, op="add_column")
        moved = self._op(classroom_id, layout_id, **{"op": "move_column", "from": 6, "to": 8})
        self.assertEqual(moved.status_code, 200, moved.get_json())
        blocks = {desk["label"]: desk["block_label"] for desk in moved.get_json()["desks"]}
        self.assertEqual(blocks["S1-M3"], "B3")
        clash = self._op(classroom_id, layout_id, **{"op": "move_column", "from": 8, "to": 0})
        self.assertEqual(clash.status_code, 409)

    def test_move_row_keeps_seats_with_their_desks(self):
        classroom_id, layout_id = self._room()
        moved = self._op(classroom_id, layout_id, **{"op": "move_row", "from": 0, "to": 6}).get_json()
        rows = sorted({desk["y"] for desk in moved["desks"]})
        self.assertEqual(rows, [2.0, 6.0])
        for desk in moved["desks"]:
            self.assertTrue(all(seat["y"] == desk["y"] for seat in desk["seats"]))

    def test_desk_can_become_single_and_double_again(self):
        classroom_id, layout_id = self._room()
        single = self._op(classroom_id, layout_id, op="set_desk_seats", label="S1-M1", count=1).get_json()
        self.assertEqual(self._numbers(single), list(range(1, 8)))
        desk = next(item for item in single["desks"] if item["label"] == "S1-M1")
        self.assertEqual(len(desk["seats"]), 1)
        double = self._op(classroom_id, layout_id, op="set_desk_seats", label="S1-M1", count=2).get_json()
        self.assertEqual(self._numbers(double), list(range(1, 9)))
        self.assertEqual(self._op(classroom_id, layout_id, op="set_desk_seats", label="S1-M1", count=5).status_code, 409)

    def test_delete_desk_and_last_desk_guard(self):
        classroom_id, layout_id = self._room()
        data = self._op(classroom_id, layout_id, op="delete_desk", label="S2-M2").get_json()
        self.assertEqual(len(data["desks"]), 3)
        self.assertEqual(self._numbers(data), list(range(1, 7)))
        for label in ("S2-M1", "S1-M2"):
            self.assertEqual(self._op(classroom_id, layout_id, op="delete_desk", label=label).status_code, 200)
        self.assertEqual(self._op(classroom_id, layout_id, op="delete_desk", label="S1-M1").status_code, 409)

    def test_removing_seats_from_a_distributed_draft_copies_the_plan(self):
        classroom_id, layout_id = self._room()
        exam_id = self.make_exam("TASLAK", layout_ids=[layout_id])
        self.distribute(exam_id)
        response = self._op(classroom_id, layout_id, op="delete_desk", label="S2-M2")
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertTrue(data["copied"])
        self.assertNotEqual(data["layout_id"], layout_id)
        self.assertEqual(self.seat_count(layout_id), 8)  # eski plan ve dağıtım kayıtları yerinde
        self.assertEqual(data["affected_draft_exam_count"], 1)

    def test_finalized_plan_is_copied_and_archive_plan_is_read_only(self):
        classroom_id, layout_id = self._room()
        exam_id = self.make_exam("KESİN", layout_ids=[layout_id])
        self.distribute(exam_id)
        self.finalize(exam_id)
        data = self._op(classroom_id, layout_id, op="add_row").get_json()
        self.assertTrue(data["copied"])
        self.assertEqual(self.seat_count(layout_id), 8)
        archive_id = self.make_archive_layout(classroom_id)
        self.assertEqual(self._op(classroom_id, archive_id, op="add_row").status_code, 403)

    def test_corridor_can_be_added_between_columns_and_removed(self):
        classroom_id, layout_id = self._room()  # sütunlar x=0 ve x=4: arada koridor var
        self._op(classroom_id, layout_id, op="add_column")  # x=6, x=4'e bitişik
        already = self._op(classroom_id, layout_id, op="add_corridor", after=0)
        self.assertEqual(already.status_code, 409)
        added = self._op(classroom_id, layout_id, op="add_corridor", after=4)
        self.assertEqual(added.status_code, 200, added.get_json())
        data = added.get_json()
        self.assertEqual(sorted({desk["x"] for desk in data["desks"]}), [0.0, 4.0, 8.0])
        self.assertEqual({desk["block_label"] for desk in data["desks"]}, {"B1", "B2", "B3"})
        self.assertEqual(self._numbers(data), list(range(1, 13)))
        for desk in data["desks"]:
            self.assertTrue(all(desk["x"] <= seat["x"] < desk["x"] + 2 for seat in desk["seats"]))
        removed = self._op(classroom_id, layout_id, op="remove_corridor", after=0).get_json()
        self.assertEqual(sorted({desk["x"] for desk in removed["desks"]}), [0.0, 2.0, 6.0])
        self.assertEqual({desk["block_label"] for desk in removed["desks"]}, {"B1", "B2"})
        self.assertEqual(self._op(classroom_id, layout_id, op="remove_corridor", after=0).status_code, 409)
        self.assertEqual(self._op(classroom_id, layout_id, op="add_corridor", after=6).status_code, 409)
        self.assertEqual(self._op(classroom_id, layout_id, op="add_corridor", after=3).status_code, 409)

    def test_unknown_operation_is_rejected(self):
        classroom_id, layout_id = self._room()
        self.assertEqual(self._op(classroom_id, layout_id, op="explode").status_code, 409)
        self.assertEqual(self.client.post(
            f"/api/classrooms/{classroom_id}/layouts/{layout_id}/structure", json={}).status_code, 400)


class ClassroomCloseDeleteTests(PlanTestMixin, unittest.TestCase):
    def _classroom(self, classroom_id):
        return next(item for item in self.client.get("/api/classrooms").get_json()["classrooms"]
                    if item["id"] == classroom_id)

    def test_closed_classroom_cannot_be_selected_and_can_reopen(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        closed = self.client.patch(f"/api/classrooms/{classroom_id}", json={"is_closed": True})
        self.assertEqual(closed.status_code, 200, closed.get_json())
        self.assertTrue(self._classroom(classroom_id)["is_closed"])
        with self.factory() as session:
            from kelebek.services.exam_organizer import list_room_options
            option = next(item for item in list_room_options(session, self.year_id) if item["layout_id"] == layout["id"])
        self.assertFalse(option["can_select"])
        self.assertTrue(option["classroom_closed"])
        self.client.patch(f"/api/classrooms/{classroom_id}", json={"is_closed": False})
        self.assertFalse(self._classroom(classroom_id)["is_closed"])

    def test_classroom_with_plans_is_deleted_when_no_exam_uses_it(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        self.assertTrue(self._classroom(classroom_id)["can_delete"])
        deleted = self.client.delete(f"/api/classrooms/{classroom_id}")
        self.assertEqual(deleted.status_code, 200, deleted.get_json())
        self.assertEqual(self.seat_count(layout["id"]), 0)
        self.assertFalse(any(item["id"] == classroom_id
                             for item in self.client.get("/api/classrooms").get_json()["classrooms"]))

    def test_classroom_used_in_an_exam_is_not_deleted(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        self.make_exam(layout_ids=[layout["id"]])
        self.assertFalse(self._classroom(classroom_id)["can_delete"])
        response = self.client.delete(f"/api/classrooms/{classroom_id}")
        self.assertEqual(response.status_code, 409)
        self.assertIn("kapat", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
