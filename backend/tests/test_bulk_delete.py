"""Toplu silme: sınavlar, öğrenciler ve derslikler (Karar 73, kullanıcı onayı 12 Kasım 2026)."""

import unittest

from _plan_support import PlanTestMixin
from sqlalchemy import func, select

from kelebek.config import get_data_dir
from kelebek.models import (
    Classroom,
    ClassroomLayout,
    DistributionCandidate,
    DistributionRun,
    ExamOrganization,
    ExamParticipant,
    Seat,
    SeatAssignment,
    Student,
    StudentYearEnrollment,
)


class BulkDeleteTests(PlanTestMixin, unittest.TestCase):
    def _count(self, model):
        with self.factory() as session:
            return session.scalar(select(func.count()).select_from(model)) or 0

    def _delete(self, scope, **extra):
        return self.client.post("/api/bulk-delete", json={
            "scope": scope, "academic_year_id": self.year_id, "confirm": True, **extra})

    def _school_with_exams(self):
        """Bir kesinleşmiş, bir dağıtılmış taslak sınav."""
        classroom_id = self.make_classroom()
        layout_id = self.make_layout(classroom_id)["id"]
        done = self.make_exam("KESİN SINAV", layout_ids=[layout_id])
        self.distribute(done)
        self.finalize(done)
        self.client.get(f"/api/exam-organizations/{done}/reports/seating-plan.pdf")
        draft = self.make_exam("TASLAK SINAV", layout_ids=[layout_id])
        self.distribute(draft)
        return classroom_id, layout_id

    def test_confirmation_and_known_scope_are_required(self):
        self.assertEqual(self.client.post("/api/bulk-delete", json={
            "scope": "exams", "academic_year_id": self.year_id}).status_code, 400)
        self.assertEqual(self._delete("her-sey").status_code, 400)
        self.assertEqual(self.client.post("/api/bulk-delete", json={
            "scope": "exams", "confirm": True}).status_code, 400)

    def test_preview_counts_what_would_be_deleted_without_deleting(self):
        self._school_with_exams()
        response = self.client.get(f"/api/bulk-delete/preview?scope=students&academic_year_id={self.year_id}")
        self.assertEqual(response.status_code, 200, response.get_json())
        counts = response.get_json()["counts"]
        self.assertEqual((counts["exams"], counts["students"]), (2, self._count(StudentYearEnrollment)))
        self.assertEqual(self._count(ExamOrganization), 2)

    def test_all_exams_are_deleted_including_finalized_ones(self):
        _classroom_id, layout_id = self._school_with_exams()
        students = self._count(StudentYearEnrollment)
        response = self._delete("exams")
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data["deleted"]["exams"], 2)
        for model in (ExamOrganization, ExamParticipant, DistributionRun, DistributionCandidate, SeatAssignment):
            self.assertEqual(self._count(model), 0, model.__name__)
        # Öğrenciler ve derslik planı yerinde kalır.
        self.assertEqual(self._count(StudentYearEnrollment), students)
        self.assertEqual(self.seat_count(layout_id), 8)
        listed = self.client.get(f"/api/exam-organizations?academic_year_id={self.year_id}").get_json()
        self.assertEqual(listed["organizations"], [])

    def test_a_safety_backup_is_taken_first(self):
        self._school_with_exams()
        data = self._delete("exams").get_json()
        self.assertTrue(data["safety_backup"].startswith("safety-bulk-delete-"))
        self.assertTrue((get_data_dir() / "backups" / data["safety_backup"]).is_file())

    def test_deleting_students_also_deletes_the_exams_they_are_in(self):
        _classroom_id, layout_id = self._school_with_exams()
        data = self._delete("students").get_json()
        self.assertEqual((data["deleted"]["exams"], data["deleted"]["students"] > 0), (2, True))
        for model in (ExamOrganization, StudentYearEnrollment, Student):
            self.assertEqual(self._count(model), 0, model.__name__)
        self.assertEqual(self.seat_count(layout_id), 8)
        groups = self.client.get(f"/api/student-groups?academic_year_id={self.year_id}").get_json()["groups"]
        self.assertEqual(groups, [])

    def test_deleting_classrooms_also_deletes_exams_but_keeps_students(self):
        self._school_with_exams()
        students = self._count(StudentYearEnrollment)
        data = self._delete("classrooms").get_json()
        self.assertEqual(data["deleted"]["exams"], 2)
        self.assertGreaterEqual(data["deleted"]["classrooms"], 2)
        for model in (ExamOrganization, Classroom, ClassroomLayout, Seat):
            self.assertEqual(self._count(model), 0, model.__name__)
        self.assertEqual(self._count(StudentYearEnrollment), students)
        self.assertEqual(self.client.get("/api/classrooms").get_json()["classrooms"], [])

    def test_app_still_works_after_everything_is_deleted(self):
        self._school_with_exams()
        self._delete("students")
        self._delete("classrooms")
        added = self.client.post("/api/students", json={
            "academic_year_id": self.year_id, "school_number": "YENİ-1", "first_name": "YENİ",
            "last_name": "SENTETİK", "class_level": "9", "section": "A"})
        self.assertEqual(added.status_code, 201, added.get_json())
        classroom_id = self.make_classroom("YENİ SALON")
        layout_id = self.make_layout(classroom_id)["id"]
        exam_id = self.make_exam("YENİ SINAV", layout_ids=[layout_id])
        self.distribute(exam_id)
        self.assertEqual(self.exam(exam_id)["stage"], "review")

    def test_archive_year_cannot_be_bulk_deleted(self):
        classroom_id = self.make_classroom()
        self.make_archive_layout(classroom_id)
        from kelebek.models import AcademicYear

        with self.factory() as session:
            archive_year = session.scalar(
                select(AcademicYear.id).where(AcademicYear.id != self.year_id))
        response = self.client.post("/api/bulk-delete", json={
            "scope": "classrooms", "academic_year_id": archive_year, "confirm": True})
        self.assertEqual(response.status_code, 403, response.get_json())
        self.assertGreaterEqual(self._count(ClassroomLayout), 1)

    def test_other_years_data_is_untouched(self):
        classroom_id = self.make_classroom("ARŞİVLİ SALON")
        archive_layout = self.make_archive_layout(classroom_id)
        self.make_layout(classroom_id)
        self._delete("classrooms")
        # Arşiv yılında planı olan derslik ve o plan korunur.
        self.assertEqual(self._count(Classroom), 1)
        self.assertEqual(self.seat_count(archive_layout), 1)


if __name__ == "__main__":
    unittest.main()
