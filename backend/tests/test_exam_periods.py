"""Sınav dönemleri: hazır gelen dönemler, adlandırma, ekleme, silme ve sınav bağlama."""

import unittest

import test_exam_flow

from kelebek.models.exam_period import DEFAULT_PERIOD_NAMES


class ExamPeriodTests(unittest.TestCase):
    # setUp sentetik okulu ve self.year_id değerini kendisi hazırlar.
    setUp = test_exam_flow.ExamFlowTests.setUp
    tearDown = test_exam_flow.ExamFlowTests.tearDown
    _seed_synthetic_school = test_exam_flow.ExamFlowTests._seed_synthetic_school

    def _periods(self):
        response = self.client.get(f"/api/exam-periods?academic_year_id={self.year_id}")
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()["periods"]

    def test_four_default_periods_are_ready_for_a_new_year(self):
        names = [item["name"] for item in self._periods()]
        self.assertEqual(names, list(DEFAULT_PERIOD_NAMES))
        self.assertTrue(all(item["exam_count"] == 0 for item in self._periods()))

    def test_period_can_be_renamed(self):
        period = self._periods()[0]
        response = self.client.patch(f"/api/exam-periods/{period['id']}", json={"name": "1. Yazılılar"})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["period"]["name"], "1. Yazılılar")
        self.assertEqual(self._periods()[0]["name"], "1. Yazılılar")

    def test_duplicate_name_is_rejected(self):
        periods = self._periods()
        response = self.client.patch(f"/api/exam-periods/{periods[1]['id']}", json={"name": periods[0]["name"]})
        self.assertEqual(response.status_code, 409)

    def test_blank_name_is_rejected(self):
        for payload in ({"name": "   "}, {"name": ""}, {}):
            response = self.client.post(
                "/api/exam-periods", json={"academic_year_id": self.year_id, **payload}
            )
            self.assertEqual(response.status_code, 400, payload)

    def test_period_can_be_added_and_empty_one_deleted(self):
        response = self.client.post(
            "/api/exam-periods", json={"academic_year_id": self.year_id, "name": "Telafi Sınavları"}
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        created = response.get_json()["period"]
        self.assertEqual(len(self._periods()), len(DEFAULT_PERIOD_NAMES) + 1)

        deleted = self.client.delete(f"/api/exam-periods/{created['id']}")
        self.assertEqual(deleted.status_code, 200, deleted.get_json())
        self.assertEqual(len(self._periods()), len(DEFAULT_PERIOD_NAMES))

    def test_exam_requires_a_period(self):
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        payload = {
            "academic_year_id": self.year_id,
            "name": "DÖNEMSİZ SINAV",
            "exam_date": "2026-12-01",
            "participant_groups": [
                {"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups
            ],
        }
        response = self.client.post("/api/exam-organizations", json=payload)
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertIn("dönem", response.get_json()["error"].casefold())

        payload["exam_period_id"] = self._periods()[0]["id"]
        response = self.client.post("/api/exam-organizations", json=payload)
        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(response.get_json()["organization"]["exam_period_name"], DEFAULT_PERIOD_NAMES[0])

    def test_period_with_exams_cannot_be_deleted_and_exam_can_be_moved(self):
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        periods = self._periods()
        response = self.client.post("/api/exam-organizations", json={
            "academic_year_id": self.year_id,
            "name": "GÜZ YAZILISI",
            "exam_date": "2026-12-01",
            "exam_period_id": periods[0]["id"],
            "participant_groups": [
                {"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups
            ],
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        organization_id = response.get_json()["organization"]["id"]

        full = next(item for item in self._periods() if item["id"] == periods[0]["id"])
        self.assertEqual(full["exam_count"], 1)
        self.assertFalse(full["can_delete"])
        self.assertEqual(self.client.delete(f"/api/exam-periods/{periods[0]['id']}").status_code, 409)

        moved = self.client.patch(
            f"/api/exam-organizations/{organization_id}/period",
            json={"exam_period_id": periods[2]["id"]},
        )
        self.assertEqual(moved.status_code, 200, moved.get_json())
        self.assertEqual(moved.get_json()["organization"]["exam_period_name"], periods[2]["name"])
        # Taşıdıktan sonra eski dönem boşalır ve silinebilir olur.
        self.assertTrue(next(item for item in self._periods() if item["id"] == periods[0]["id"])["can_delete"])

    def test_copy_keeps_the_period_of_the_source_exam(self):
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        periods = self._periods()
        created = self.client.post("/api/exam-organizations", json={
            "academic_year_id": self.year_id,
            "name": "KAYNAK SINAV",
            "exam_date": "2026-12-01",
            "exam_period_id": periods[1]["id"],
            "participant_groups": [
                {"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups
            ],
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        source_id = created.get_json()["organization"]["id"]

        copied = self.client.post(f"/api/exam-organizations/{source_id}/copy",
                                  json={"name": "KAYNAK SINAV kopya", "exam_date": "2026-12-15"})
        self.assertEqual(copied.status_code, 201, copied.get_json())

        organizations = self.client.get(
            f"/api/exam-organizations?academic_year_id={self.year_id}").get_json()["organizations"]
        copy = next(item for item in organizations if item["name"] == "KAYNAK SINAV kopya")
        self.assertEqual(copy["exam_period_id"], periods[1]["id"],
                         "Kopyalanan sınav kaynağının dönemini kaybetmemeli.")

    def test_unknown_period_is_rejected(self):
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        response = self.client.post("/api/exam-organizations", json={
            "academic_year_id": self.year_id,
            "name": "HATALI",
            "exam_date": "2026-12-01",
            "exam_period_id": "00000000-0000-0000-0000-000000000000",
            "participant_groups": [
                {"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups
            ],
        })
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
