"""Synthetic tests for edit locks, archive/copy, student changes, pinned rooms and report options."""

import unittest

from sqlalchemy import select

from kelebek.models import Classroom, ClassroomLayout, Desk, Seat, StudentYearEnrollment
from test_exam_flow import ExamFlowTests


class ExamLifecycleTests(unittest.TestCase):
    setUp = ExamFlowTests.setUp
    tearDown = ExamFlowTests.tearDown
    _seed_synthetic_school = ExamFlowTests._seed_synthetic_school
    _create_organization = ExamFlowTests._create_organization

    def _finalized(self, layout_ids=None):
        organization = self._create_organization()
        org_id = organization["id"]
        response = self.client.put(f"/api/exam-organizations/{org_id}/classrooms",
                                   json={"layout_ids": layout_ids or [self.layout_id]})
        self.assertEqual(response.status_code, 200, response.get_json())
        candidate = self.client.post(f"/api/exam-organizations/{org_id}/distribution-candidates", json={}).get_json()["candidate"]
        self.client.put(f"/api/exam-organizations/{org_id}/selected-candidate", json={"candidate_id": candidate["candidate_id"]})
        return org_id, candidate

    def _finalize(self, org_id):
        response = self.client.post(f"/api/exam-organizations/{org_id}/finalize",
                                    json={"confirm": True, "physical_layouts_confirmed": True})
        self.assertEqual(response.status_code, 200, response.get_json())

    def test_edit_lock_keeps_other_tab_read_only_until_takeover(self):
        org_id, candidate = self._finalized()
        free_seat = next(seat["seat_id"] for seat in candidate["available_seats"]
                         if not any(item["seat_id"] == seat["seat_id"] for item in candidate["assignments"]))
        move = {"participant_id": candidate["assignments"][0]["participant_id"], "target_seat_id": free_seat}
        url = f"/api/exam-organizations/{org_id}/distribution-candidates/{candidate['candidate_id']}/moves"
        first = self.client.post(url, json=move, headers={"X-Kelebek-Tab": "tab-aaaaaaaa"})
        self.assertEqual(first.status_code, 201, first.get_json())
        blocked = self.client.put(f"/api/exam-organizations/{org_id}/rules", json={}, headers={"X-Kelebek-Tab": "tab-bbbbbbbb"})
        self.assertEqual(blocked.status_code, 423)
        locks = self.client.get("/api/edit-locks", headers={"X-Kelebek-Tab": "tab-bbbbbbbb"}).get_json()["locks"]
        self.assertFalse(locks[org_id]["mine"])
        taken = self.client.post(f"/api/exam-organizations/{org_id}/edit-lock", json={"takeover": True},
                                 headers={"X-Kelebek-Tab": "tab-bbbbbbbb"})
        self.assertEqual(taken.status_code, 200)
        self.assertEqual(self.client.put(f"/api/exam-organizations/{org_id}/rules", json={},
                                         headers={"X-Kelebek-Tab": "tab-aaaaaaaa"}).status_code, 423)
        self.client.post("/api/edit-locks/release?tab=tab-bbbbbbbb")
        self.assertEqual(self.client.get("/api/edit-locks").get_json()["locks"], {})

    def test_student_changes_archive_and_copy(self):
        org_id, _candidate = self._finalized()
        self._finalize(org_id)
        with self.factory.begin() as session:
            enrollment = session.scalar(select(StudentYearEnrollment).where(StudentYearEnrollment.section == "B"))
            enrollment.section = "C"
        changes = self.client.get(f"/api/exam-organizations/{org_id}/student-changes").get_json()["changes"]
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["changes"][0]["field"], "section")
        applied = self.client.post(f"/api/exam-organizations/{org_id}/student-changes/apply",
                                   json={"confirm": True, "participant_ids": [changes[0]["participant_id"]]})
        self.assertEqual(applied.status_code, 200, applied.get_json())
        review = self.client.get(f"/api/exam-organizations/{org_id}/final-review").get_json()["review"]
        self.assertEqual(review["unassigned_count"], 1)
        self.assertFalse(review["can_finalize"])
        self.assertEqual(self.client.get(f"/api/exam-organizations/{org_id}/student-changes").get_json()["changes"], [])

        completed = self.client.post(f"/api/exam-organizations/{org_id}/complete", json={"confirm": True})
        self.assertEqual(completed.status_code, 200, completed.get_json())
        self.assertIsNotNone(completed.get_json()["organization"]["archived_at"])
        self.assertEqual(self.client.put(f"/api/exam-organizations/{org_id}/rules", json={}).status_code, 403)

        copy = self.client.post(f"/api/exam-organizations/{org_id}/copy",
                                json={"name": "SENTETİK KOPYA", "exam_date": "2026-12-01"})
        self.assertEqual(copy.status_code, 201, copy.get_json())
        copied = copy.get_json()["organization"]
        self.assertEqual(copied["status"], "draft")
        self.assertEqual(copied["participant_count"], 2)
        self.assertEqual(copied["copied_from_organization_id"], org_id)
        self.assertEqual(len(copied["room_selections"]), 1)

    def test_pinned_room_keeps_placements_and_redistributes_the_rest(self):
        with self.factory.begin() as session:
            classroom = Classroom(name="SENTETİK DERSLİK 2")
            session.add(classroom)
            session.flush()
            layout = ClassroomLayout(classroom_id=classroom.id, academic_year_id=self.year_id, name="Plan 2", version=1)
            session.add(layout)
            session.flush()
            for index in range(3):
                desk = Desk(layout_id=layout.id, label=f"D{index}", block_label=f"B{index}", x=index * 10.0, y=0.0)
                session.add(desk)
                session.flush()
                session.add(Seat(layout_id=layout.id, desk_id=desk.id, seat_number=index + 1, seat_index=1,
                                 x=index * 10.0, y=0.0, is_available=True))
            second_layout_id, second_room_id = layout.id, classroom.id
        org_id, candidate = self._finalized([self.layout_id, second_layout_id])
        pinned_room = next(item["classroom_id"] for item in candidate["assignments"] if item["classroom_id"])
        fixed = {item["participant_id"]: item["seat_id"] for item in candidate["assignments"] if item["classroom_id"] == pinned_room}
        response = self.client.post(f"/api/exam-organizations/{org_id}/distribution-candidates", json={
            "run_id": candidate["run_id"], "base_candidate_id": candidate["candidate_id"],
            "pinned_classroom_ids": [pinned_room],
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        pinned = response.get_json()["candidate"]
        self.assertEqual(pinned["pinned_classroom_ids"], [pinned_room])
        self.assertEqual(pinned["derived_from_candidate_id"], candidate["candidate_id"])
        for item in pinned["assignments"]:
            if item["participant_id"] in fixed:
                self.assertEqual(item["seat_id"], fixed[item["participant_id"]])
        everything = self.client.post(f"/api/exam-organizations/{org_id}/distribution-candidates", json={
            "run_id": candidate["run_id"], "base_candidate_id": candidate["candidate_id"],
            "pinned_classroom_ids": [self.classroom_id, second_room_id],
        })
        self.assertEqual(everything.status_code, 409)

    def test_progress_snapshot_and_violation_details(self):
        org_id, candidate = self._finalized()
        self.assertIsInstance(candidate["violations"], list)
        progress = self.client.get(f"/api/exam-organizations/{org_id}/distribution-progress").get_json()["progress"]
        self.assertFalse(progress["active"])
        self.assertEqual(progress["outcome"], "created")
        self.assertGreaterEqual(progress["solutions_found"], 1)
        self.assertEqual([step["key"] for step in progress["steps"]], ["prepare", "model", "search", "save"])
        self.assertEqual(self.client.post(f"/api/exam-organizations/{org_id}/distribution-progress/stop").status_code, 409)

    def test_report_header_title_and_scale_options(self):
        org_id, _candidate = self._finalized()
        self._finalize(org_id)
        ok = self.client.get(f"/api/exam-organizations/{org_id}/reports/attendance.pdf"
                             "?header=title,date&title=OZEL%20BASLIK&scale=120")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.mimetype, "application/pdf")
        bad = self.client.get(f"/api/exam-organizations/{org_id}/reports/attendance.pdf?scale=200")
        self.assertEqual(bad.status_code, 400)
        bad_header = self.client.get(f"/api/exam-organizations/{org_id}/reports/attendance.pdf?header=logo")
        self.assertEqual(bad_header.status_code, 400)


if __name__ == "__main__":
    unittest.main()
