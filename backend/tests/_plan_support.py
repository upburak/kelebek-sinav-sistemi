"""Derslik planı ve sınav testleri için ortak yardımcılar (yalnızca sentetik veri)."""

import test_exam_flow
from sqlalchemy import func, select

from kelebek.models import AcademicYear, ClassroomLayout, Seat


class PlanTestMixin:
    setUp = test_exam_flow.ExamFlowTests.setUp
    tearDown = test_exam_flow.ExamFlowTests.tearDown
    _seed_synthetic_school = test_exam_flow.ExamFlowTests._seed_synthetic_school

    def make_classroom(self, name="PLAN TEST SALONU"):
        response = self.client.post("/api/classrooms", json={"name": name})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["classroom"]["id"]

    def make_layout(self, classroom_id, name="Sınıf planı", seats=True, **extra):
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

    def layouts(self, classroom_id):
        return self.client.get(f"/api/classrooms/{classroom_id}/layouts").get_json()["layouts"]

    def layout_detail(self, classroom_id, layout_id):
        return self.client.get(f"/api/classrooms/{classroom_id}/layouts/{layout_id}").get_json()

    def make_exam(self, name="PLAN SINAVI", layout_ids=None):
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        period = self.client.get(f"/api/exam-periods?academic_year_id={self.year_id}").get_json()["periods"][0]
        created = self.client.post("/api/exam-organizations", json={
            "academic_year_id": self.year_id, "name": name, "exam_date": "2026-12-01",
            "exam_period_id": period["id"],
            "participant_groups": [
                {"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups
            ],
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        exam_id = created.get_json()["organization"]["id"]
        if layout_ids is not None:
            self.select_rooms(exam_id, layout_ids)
        return exam_id

    def select_rooms(self, exam_id, layout_ids):
        saved = self.client.put(f"/api/exam-organizations/{exam_id}/classrooms", json={"layout_ids": layout_ids})
        self.assertEqual(saved.status_code, 200, saved.get_json())

    def distribute(self, exam_id):
        response = self.client.post(f"/api/exam-organizations/{exam_id}/distribution-candidates", json={})
        self.assertEqual(response.status_code, 201, response.get_json())
        candidate_id = response.get_json()["candidate"]["candidate_id"]
        chosen = self.client.put(f"/api/exam-organizations/{exam_id}/selected-candidate",
                                 json={"candidate_id": candidate_id})
        self.assertEqual(chosen.status_code, 200, chosen.get_json())
        return candidate_id

    def finalize(self, exam_id):
        response = self.client.post(f"/api/exam-organizations/{exam_id}/finalize",
                                    json={"confirm": True, "physical_layouts_confirmed": True})
        self.assertEqual(response.status_code, 200, response.get_json())

    def exam(self, exam_id):
        items = self.client.get(f"/api/exam-organizations?academic_year_id={self.year_id}").get_json()["organizations"]
        return next(item for item in items if item["id"] == exam_id)

    def candidates(self, exam_id):
        return self.client.get(f"/api/exam-organizations/{exam_id}/distribution-candidates").get_json()["candidates"]

    def seat_count(self, layout_id, available_only=False):
        with self.factory() as session:
            query = select(func.count(Seat.id)).where(Seat.layout_id == layout_id)
            if available_only:
                query = query.where(Seat.is_available.is_(True))
            return session.scalar(query) or 0

    def make_archive_layout(self, classroom_id):
        """Geçmiş bir eğitim yılına ait plan (salt okunur olmalı)."""
        with self.factory.begin() as session:
            current = session.get(AcademicYear, self.year_id)
            old = AcademicYear(start_year=current.start_year - 1, end_year=current.start_year, is_selected=False)
            session.add(old)
            session.flush()
            layout = ClassroomLayout(classroom_id=classroom_id, academic_year_id=old.id,
                                     name="Arşiv planı", version=1)
            session.add(layout)
            session.flush()
            return layout.id
