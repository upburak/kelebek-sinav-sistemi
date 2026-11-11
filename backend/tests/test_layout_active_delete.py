"""Aktif oturma düzeni seçimi ve kullanılmayan düzenlerin silinmesi."""

import unittest

import test_exam_flow


class LayoutActiveDeleteTests(unittest.TestCase):
    setUp = test_exam_flow.ExamFlowTests.setUp
    tearDown = test_exam_flow.ExamFlowTests.tearDown
    _seed_synthetic_school = test_exam_flow.ExamFlowTests._seed_synthetic_school

    def _classroom(self, name="SİLME TEST SALONU"):
        response = self.client.post("/api/classrooms", json={"name": name})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["classroom"]["id"]

    def _layout(self, classroom_id, name, seats=True, **extra):
        payload = {"name": name, "academic_year_id": self.year_id, **extra}
        response = self.client.post(f"/api/classrooms/{classroom_id}/layouts", json=payload)
        self.assertEqual(response.status_code, 201, response.get_json())
        layout = response.get_json()["layout"]
        if seats:
            generated = self.client.post(
                f"/api/classrooms/{classroom_id}/layouts/{layout['id']}/generate",
                json={"columns": 2, "column_lengths": [2, 2], "cell_seats": [[2, 2], [2, 2]],
                      "aisle_after": [True]},
            )
            self.assertIn(generated.status_code, (200, 201), generated.get_json())
        return layout

    def _layouts(self, classroom_id):
        return self.client.get(f"/api/classrooms/{classroom_id}/layouts").get_json()["layouts"]

    def test_first_layout_becomes_active_and_second_does_not_steal_it(self):
        classroom_id = self._classroom()
        first = self._layout(classroom_id, "Sınav düzeni")
        second = self._layout(classroom_id, "Ders düzeni")
        self.assertTrue(first["is_active"])
        self.assertFalse(second["is_active"])
        active = [item["id"] for item in self._layouts(classroom_id) if item["is_active"]]
        self.assertEqual(active, [first["id"]])

    def test_activating_a_layout_deactivates_the_other(self):
        classroom_id = self._classroom()
        first = self._layout(classroom_id, "Sınav düzeni")
        second = self._layout(classroom_id, "Ders düzeni")
        response = self.client.post(f"/api/classrooms/{classroom_id}/layouts/{second['id']}/activate")
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertTrue(response.get_json()["layout"]["is_active"])
        state = {item["id"]: item["is_active"] for item in self._layouts(classroom_id)}
        self.assertEqual(state, {first["id"]: False, second["id"]: True})

    def test_active_layout_comes_first_in_exam_room_options(self):
        classroom_id = self._classroom()
        self._layout(classroom_id, "Sınav düzeni")
        second = self._layout(classroom_id, "Ders düzeni")
        self.client.post(f"/api/classrooms/{classroom_id}/layouts/{second['id']}/activate")
        rooms = self.client.get(f"/api/exam-room-options?academic_year_id={self.year_id}").get_json()["rooms"]
        mine = [room for room in rooms if room["classroom_id"] == classroom_id]
        self.assertEqual(mine[0]["layout_id"], second["id"])
        self.assertEqual([room["is_active"] for room in mine], [True, False])

    def test_template_cannot_be_activated(self):
        classroom_id = self._classroom()
        template = self._layout(classroom_id, "Şablon", seats=False, is_template=True, academic_year_id=None)
        self.assertFalse(template["is_active"])
        response = self.client.post(f"/api/classrooms/{classroom_id}/layouts/{template['id']}/activate")
        self.assertEqual(response.status_code, 409)

    def test_new_version_inherits_active_state(self):
        classroom_id = self._classroom()
        first = self._layout(classroom_id, "Sınav düzeni")
        response = self.client.post(f"/api/classrooms/{classroom_id}/layouts/{first['id']}/versions")
        self.assertEqual(response.status_code, 201, response.get_json())
        active = [item for item in self._layouts(classroom_id) if item["is_active"]]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["version"], 2)

    def test_unused_layout_is_deleted_with_its_seats(self):
        classroom_id = self._classroom()
        first = self._layout(classroom_id, "Sınav düzeni")
        second = self._layout(classroom_id, "Ders düzeni")
        response = self.client.delete(f"/api/classrooms/{classroom_id}/layouts/{second['id']}")
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual([item["id"] for item in self._layouts(classroom_id)], [first["id"]])
        self.assertEqual(
            self.client.get(f"/api/classrooms/{classroom_id}/layouts/{second['id']}").status_code, 404
        )

    def test_deleting_the_active_layout_promotes_the_remaining_one(self):
        classroom_id = self._classroom()
        first = self._layout(classroom_id, "Sınav düzeni")
        second = self._layout(classroom_id, "Ders düzeni")
        self.assertEqual(
            self.client.delete(f"/api/classrooms/{classroom_id}/layouts/{first['id']}").status_code, 200
        )
        remaining = self._layouts(classroom_id)
        self.assertEqual([(item["id"], item["is_active"]) for item in remaining], [(second["id"], True)])

    def test_layout_used_by_an_exam_cannot_be_deleted(self):
        classroom_id = self._classroom()
        layout = self._layout(classroom_id, "Sınav düzeni")
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        period = self.client.get(f"/api/exam-periods?academic_year_id={self.year_id}").get_json()["periods"][0]
        created = self.client.post("/api/exam-organizations", json={
            "academic_year_id": self.year_id, "name": "DÜZEN KULLANAN SINAV", "exam_date": "2026-12-01",
            "exam_period_id": period["id"],
            "participant_groups": [
                {"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups[:1]
            ],
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        organization_id = created.get_json()["organization"]["id"]
        saved = self.client.put(f"/api/exam-organizations/{organization_id}/classrooms",
                                json={"layout_ids": [layout["id"]]})
        self.assertEqual(saved.status_code, 200, saved.get_json())

        listed = next(item for item in self._layouts(classroom_id) if item["id"] == layout["id"])
        self.assertEqual(listed["exam_count"], 1)
        self.assertFalse(listed["can_delete"])
        response = self.client.delete(f"/api/classrooms/{classroom_id}/layouts/{layout['id']}")
        self.assertEqual(response.status_code, 409)
        self.assertIn("sınav", response.get_json()["error"].casefold())
        self.assertEqual(len(self._layouts(classroom_id)), 1)


if __name__ == "__main__":
    unittest.main()
