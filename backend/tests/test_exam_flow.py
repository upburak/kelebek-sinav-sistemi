"""Synthetic acceptance tests for creating and completing an exam seating plan."""

import json
import os
import re
import tempfile
import unittest
from io import BytesIO
from urllib.parse import urlencode

import pdfplumber
from _support import release_app_resources
from openpyxl import load_workbook
from sqlalchemy import select

from kelebek import create_app
from kelebek.models import (
    AcademicYear,
    Classroom,
    ClassroomLayout,
    Desk,
    ExamParticipant,
    SchoolProfile,
    Seat,
    Student,
    StudentYearEnrollment,
)


class ExamFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="kelebek-exam-flow-")
        self.previous_data_dir = os.environ.get("KELEBEK_DATA_DIR")
        os.environ["KELEBEK_DATA_DIR"] = self.temp_dir.name
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.factory = self.app.extensions["kelebek_session_factory"]
        self._seed_synthetic_school()

    def tearDown(self):
        release_app_resources(self.app)
        if self.previous_data_dir is None:
            os.environ.pop("KELEBEK_DATA_DIR", None)
        else:
            os.environ["KELEBEK_DATA_DIR"] = self.previous_data_dir
        self.temp_dir.cleanup()

    def _seed_synthetic_school(self):
        with self.factory.begin() as session:
            year = session.scalar(select(AcademicYear).where(AcademicYear.is_selected.is_(True)))
            self.year_id = year.id
            session.add(SchoolProfile(id=1, school_name="SENTETİK OKUL"))
            for index, section in enumerate(("A", "B"), start=1):
                student = Student()
                session.add(student)
                session.flush()
                session.add(StudentYearEnrollment(
                    academic_year_id=year.id,
                    student_id=student.id,
                    school_number=f"SENTETIK-{index:03d}",
                    first_name=("ÇOK UZUN SENTETİK ÖĞRENCİ ADI " * 4) if index == 1 else f"ÖRNEK AD {index}",
                    last_name=f"KORUNAN SOYAD {index}",
                    class_level="9",
                    section=section,
                ))

            classroom = Classroom(name="SENTETİK DERSLİK")
            session.add(classroom)
            session.flush()
            layout = ClassroomLayout(
                classroom_id=classroom.id,
                academic_year_id=year.id,
                name="Sentetik fiziksel plan",
                version=1,
            )
            session.add(layout)
            session.flush()
            self.classroom_id = classroom.id
            self.layout_id = layout.id
            self.seat_ids = []
            for index, x_position in enumerate((0.0, 10.0, 20.0, 30.0), start=1):
                desk = Desk(
                    layout_id=layout.id,
                    label=f"S{index}",
                    block_label="A",
                    x=x_position,
                    y=0.0,
                )
                session.add(desk)
                session.flush()
                seat = Seat(
                    layout_id=layout.id,
                    desk_id=desk.id,
                    seat_number=99 if index == 4 else index,
                    seat_index=1,
                    x=x_position,
                    y=0.0,
                    is_available=index != 4,
                )
                session.add(seat)
                session.flush()
                self.seat_ids.append(seat.id)

    def _create_organization(self):
        response = self.client.post("/api/exam-organizations", json={
            "academic_year_id": self.year_id,
            "name": "SENTETİK DENEME SINAVI",
            "exam_date": "2026-11-08",
            "participant_groups": [
                {"class_level": "9", "section": "A", "area": ""},
                {"class_level": "9", "section": "B", "area": ""},
            ],
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["organization"]

    def _select_room(self, organization_id):
        response = self.client.put(
            f"/api/exam-organizations/{organization_id}/classrooms",
            json={"layout_ids": [self.layout_id]},
        )
        self.assertEqual(response.status_code, 200, response.get_json())

    def test_synthetic_exam_can_be_distributed_confirmed_and_reported(self):
        organization = self._create_organization()
        self.assertEqual(organization["participant_count"], 2)
        self._select_room(organization["id"])
        for report_path in ("distribution.pdf", "room-students.xlsx"):
            blocked_report = self.client.get(
                f"/api/exam-organizations/{organization['id']}/reports/{report_path}"
            )
            self.assertEqual(blocked_report.status_code, 409)

        generated = self.client.post(
            f"/api/exam-organizations/{organization['id']}/distribution-candidates",
            json={},
        )
        self.assertEqual(generated.status_code, 201, generated.get_json())
        candidate = generated.get_json()["candidate"]
        self.assertEqual(len(candidate["assignments"]), 2)
        self.assertTrue(all(item["seat_id"] for item in candidate["assignments"]))
        self.assertEqual(candidate["summary"]["waiting_count"], 0)

        selected = self.client.put(
            f"/api/exam-organizations/{organization['id']}/selected-candidate",
            json={"candidate_id": candidate["candidate_id"]},
        )
        self.assertEqual(selected.status_code, 200, selected.get_json())

        review = self.client.get(
            f"/api/exam-organizations/{organization['id']}/final-review"
        )
        self.assertEqual(review.status_code, 200, review.get_json())
        self.assertTrue(review.get_json()["review"]["can_finalize"])
        self.assertEqual(review.get_json()["review"]["affected_student_count"], 0)

        without_confirmation = self.client.post(
            f"/api/exam-organizations/{organization['id']}/finalize",
            json={"confirm": False},
        )
        self.assertEqual(without_confirmation.status_code, 400)

        without_room_confirmation = self.client.post(
            f"/api/exam-organizations/{organization['id']}/finalize",
            json={"confirm": True, "physical_layouts_confirmed": False},
        )
        self.assertEqual(without_room_confirmation.status_code, 400)

        finalized = self.client.post(
            f"/api/exam-organizations/{organization['id']}/finalize",
            json={"confirm": True, "physical_layouts_confirmed": True},
        )
        self.assertEqual(finalized.status_code, 200, finalized.get_json())
        self.assertEqual(finalized.get_json()["organization"]["status"], "completed")

        report = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/seating-plan.pdf"
        )
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.mimetype, "application/pdf")
        self.assertTrue(report.data.startswith(b"%PDF-"))
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", report.data)), 1)

        for path, expected in (
            ("attendance.pdf", ("YOKLAMA ÇİZELGESİ", "SENTETİK DERSLİK", "SENTETIK-001", "+", "−")),
            ("room-students.pdf", ("DERSLİK BAZLI ÖĞRENCİ LİSTESİ", "SENTETİK DERSLİK", "SENTETIK-002", "Boş", "SOYAD 1")),
            ("distribution.pdf", ("GENEL SINAV DAĞITIM LİSTESİ", "SENTETİK DERSLİK", "SENTETIK-001", "SENTETIK-002")),
            ("class-students.pdf", ("SINIF BAZLI ÖĞRENCİ LİSTESİ", "Sınıf 9/A", "SENTETIK-001", "SOYAD 1")),
        ):
            response = self.client.get(
                f"/api/exam-organizations/{organization['id']}/reports/{path}"
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertEqual(response.mimetype, "application/pdf")
            self.assertTrue(response.data.startswith(b"%PDF-"))
            with pdfplumber.open(BytesIO(response.data)) as document:
                text = "\n".join(page.extract_text() or "" for page in document.pages)
                self.assertEqual(len(document.pages), 2 if path == "class-students.pdf" else 1)
            for marker in expected:
                self.assertIn(marker, text)
            self.assertNotRegex(text, r"(?m)^99$")  # disabled physical seat is omitted

        for path, expected_sheet in (("room-students.xlsx", "SENTETİK DERSLİK"),
                                     ("distribution.xlsx", "Genel dağıtım"),
                                     ("class-students.xlsx", "9-A")):
            response = self.client.get(
                f"/api/exam-organizations/{organization['id']}/reports/{path}"
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertEqual(response.mimetype, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            workbook = load_workbook(BytesIO(response.data), read_only=True, data_only=True)
            self.assertEqual(workbook.sheetnames[0], expected_sheet)
            excel_text = "\n".join(
                str(value) for row in workbook.active.iter_rows(values_only=True) for value in row
                if value is not None
            )
            self.assertIn("SENTETIK-001", excel_text)
            self.assertNotIn("99", excel_text)
            workbook.close()

        custom_page = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/class-students.pdf"
            "?paper=A5&orientation=landscape&margin_mm=18"
        )
        self.assertEqual(custom_page.status_code, 200, custom_page.get_json())
        with pdfplumber.open(BytesIO(custom_page.data)) as document:
            self.assertGreater(document.pages[0].width, document.pages[0].height)
            self.assertAlmostEqual(document.pages[0].width, 595.28, delta=1)
        invalid_page = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/class-students.pdf?margin_mm=40"
        )
        self.assertEqual(invalid_page.status_code, 400)

        customization_query = urlencode({
            "fields": "name,school_number",
            "labels": json.dumps({"name": "Öğrenci", "school_number": "No"}, ensure_ascii=False),
        })
        custom_pdf = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/room-students.pdf?{customization_query}"
        )
        self.assertEqual(custom_pdf.status_code, 200, custom_pdf.get_json())
        with pdfplumber.open(BytesIO(custom_pdf.data)) as document:
            custom_text = "\n".join(page.extract_text() or "" for page in document.pages)
        self.assertIn("Öğrenci", custom_text)
        self.assertIn("No", custom_text)
        self.assertNotIn("Adı soyadı", custom_text)
        customized_header = next(
            line for line in custom_text.splitlines() if "Öğrenci" in line and "No" in line
        )
        self.assertLess(customized_header.index("Öğrenci"), customized_header.index("No"))
        self.assertIn("SENTETIK-001", custom_text)
        self.assertNotIn("Koltuk", custom_text)
        self.assertNotIn("Sınıf/şube", custom_text)
        empty_fields = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/room-students.pdf?fields="
        )
        self.assertEqual(empty_fields.status_code, 400)
        unsupported_field = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/room-students.pdf?fields=unknown"
        )
        self.assertEqual(unsupported_field.status_code, 400)
        hidden_column_label = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/room-students.pdf?"
            f"{urlencode({'fields': 'name', 'labels': json.dumps({'area': 'Alanım'})})}"
        )
        self.assertEqual(hidden_column_label.status_code, 400)
        too_long_label = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/room-students.pdf?"
            f"{urlencode({'fields': 'name', 'labels': json.dumps({'name': 'X' * 41})})}"
        )
        self.assertEqual(too_long_label.status_code, 400)
        customized_excel = self.client.get(
            f"/api/exam-organizations/{organization['id']}/reports/distribution.xlsx"
            f"?{customization_query}"
        )
        self.assertEqual(customized_excel.status_code, 200, customized_excel.get_json())
        custom_workbook = load_workbook(BytesIO(customized_excel.data), read_only=True, data_only=True)
        self.assertEqual(custom_workbook.active.max_column, 2)
        excel_headers = [cell.value for cell in next(custom_workbook.active.iter_rows())]
        self.assertEqual(excel_headers, ["Öğrenci", "No"])
        custom_workbook.close()

        listing = self.client.get(f"/api/exam-organizations?academic_year_id={self.year_id}")
        self.assertEqual(listing.status_code, 200, listing.get_json())
        self.assertEqual(listing.get_json()["organizations"][0]["report_status"], "current")
        statuses = listing.get_json()["organizations"][0]["report_statuses"]
        self.assertEqual(statuses["attendance_pdf"]["report_status"], "current")
        self.assertEqual(statuses["room_student_list_pdf"]["report_status"], "current")
        self.assertEqual(statuses["general_distribution_pdf"]["report_status"], "current")
        manual_change = self.client.post(
            f"/api/exam-organizations/{organization['id']}/distribution-candidates/"
            f"{candidate['candidate_id']}/moves",
            json={
                "participant_id": candidate["assignments"][0]["participant_id"],
                "target_seat_id": self.seat_ids[2],
            },
        )
        self.assertEqual(manual_change.status_code, 201, manual_change.get_json())
        self.assertTrue(all(
            value["report_status"] == "stale"
            for value in manual_change.get_json()["candidate"]["report_statuses"].values()
        ))
        with self.factory.begin() as session:
            participant = session.scalar(select(ExamParticipant).where(
                ExamParticipant.school_number == "SENTETIK-001"
            ))
            participant.area = "SENTETİK ALAN DEĞİŞİKLİĞİ"
        stale_listing = self.client.get(f"/api/exam-organizations?academic_year_id={self.year_id}")
        stale_statuses = stale_listing.get_json()["organizations"][0]["report_statuses"]
        self.assertTrue(all(value["report_status"] == "stale" for value in stale_statuses.values()))

    def test_insufficient_physical_capacity_blocks_distribution(self):
        with self.factory.begin() as session:
            for seat_id in self.seat_ids[:2]:
                session.get(Seat, seat_id).is_available = False

        organization = self._create_organization()
        self._select_room(organization["id"])
        generated = self.client.post(
            f"/api/exam-organizations/{organization['id']}/distribution-candidates",
            json={},
        )
        self.assertEqual(generated.status_code, 409)
        self.assertIn("Kapasite yetersiz", generated.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
