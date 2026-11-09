"""Synthetic-data coverage for portable backup inspection and restore."""

import io
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select

from kelebek import create_app
from kelebek.models import AcademicYear, SchoolProfile, Student, StudentYearEnrollment
from kelebek.services.backup import build_backup_package
from kelebek.services.backup_restore import recover_interrupted_restore


class BackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="kelebek-restore-tests-")
        self.previous_data_dir = os.environ.get("KELEBEK_DATA_DIR")
        os.environ["KELEBEK_DATA_DIR"] = self.temp_dir.name
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.data_dir = Path(self.temp_dir.name)
        self.reports_dir = self.data_dir / "Exports" / "PDF"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.synthetic_report = self.reports_dir / "synthetic-plan.pdf"
        self.synthetic_report.write_bytes(b"%PDF-1.4 synthetic test report\n")
        factory = self.app.extensions["kelebek_session_factory"]
        with factory.begin() as session:
            session.add(SchoolProfile(
                id=1,
                school_name="SENTETİK YEDEK OKULU",
                province="ÖRNEK İL",
                district="ÖRNEK İLÇE",
            ))
            student = Student()
            session.add(student)
            session.flush()
            year = session.scalar(select(AcademicYear).limit(1))
            session.add(StudentYearEnrollment(
                academic_year_id=year.id,
                student_id=student.id,
                school_number="SENTETİK-001",
                first_name="SENTETİK AD",
                last_name="SENTETİK SOYAD",
                class_level="9",
                section="A",
            ))
        stream, _filename, _manifest = build_backup_package()
        self.package_bytes = stream.read()
        stream.close()

    def tearDown(self):
        self.app.extensions["kelebek_engine"].dispose()
        if self.previous_data_dir is None:
            os.environ.pop("KELEBEK_DATA_DIR", None)
        else:
            os.environ["KELEBEK_DATA_DIR"] = self.previous_data_dir
        self.temp_dir.cleanup()

    def _inspect(self, package_bytes=None):
        return self.client.post(
            "/api/backups/restore/inspect",
            data={"backup": (io.BytesIO(package_bytes or self.package_bytes), "synthetic.zip")},
            content_type="multipart/form-data",
        )

    def _set_current_synthetic_school(self, name):
        factory = self.app.extensions["kelebek_session_factory"]
        with factory.begin() as session:
            session.get(SchoolProfile, 1).school_name = name

    def _school_name(self):
        factory = self.app.extensions["kelebek_session_factory"]
        with factory() as session:
            return session.get(SchoolProfile, 1).school_name

    def _set_synthetic_student_name(self, name):
        factory = self.app.extensions["kelebek_session_factory"]
        with factory.begin() as session:
            enrollment = session.scalar(select(StudentYearEnrollment).where(
                StudentYearEnrollment.school_number == "SENTETİK-001"
            ))
            enrollment.first_name = name

    def _synthetic_student_name(self):
        factory = self.app.extensions["kelebek_session_factory"]
        with factory() as session:
            enrollment = session.scalar(select(StudentYearEnrollment).where(
                StudentYearEnrollment.school_number == "SENTETİK-001"
            ))
            return enrollment.first_name

    def test_confirmed_restore_replaces_synthetic_data_and_keeps_safety_copy(self):
        self._set_current_synthetic_school("SENTETİK GÜNCEL OKULU")
        self._set_synthetic_student_name("SENTETİK GÜNCEL AD")
        self.synthetic_report.write_bytes(b"%PDF-1.4 newer synthetic report\n")
        response = self._inspect()
        self.assertEqual(response.status_code, 200, response.get_json())
        preview = response.get_json()["preview"]
        self.assertTrue(preview["sha256_verified"])
        self.assertEqual(preview["database_integrity"], "ok")
        self.assertEqual(preview["report_count"], 1)
        self.assertEqual(preview["schema_revision"], preview["target_schema_revision"])

        token = response.get_json()["token"]
        without_confirmation = self.client.post(
            "/api/backups/restore/confirm",
            json={"token": token, "confirmed": False},
        )
        self.assertEqual(without_confirmation.status_code, 400)
        self.assertEqual(self._school_name(), "SENTETİK GÜNCEL OKULU")

        restored = self.client.post(
            "/api/backups/restore/confirm",
            json={"token": token, "confirmed": True},
        )
        self.assertEqual(restored.status_code, 200, restored.get_json())
        self.assertEqual(self._school_name(), "SENTETİK YEDEK OKULU")
        self.assertEqual(self._synthetic_student_name(), "SENTETİK AD")
        self.assertEqual(self.synthetic_report.read_bytes(), b"%PDF-1.4 synthetic test report\n")
        safety_files = list((self.data_dir / "backups").glob("safety-restore-*.zip"))
        self.assertEqual(len(safety_files), 1)
        with zipfile.ZipFile(safety_files[0]) as safety_zip:
            manifest = json.loads(safety_zip.read("manifest.json"))
            database_bytes = safety_zip.read("database/kelebek.sqlite3")
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as safety_database:
            safety_database.write(database_bytes)
            safety_database.flush()
            safety_uri = Path(safety_database.name).as_uri() + "?mode=ro"
            with sqlite3.connect(safety_uri, uri=True) as database:
                self.assertEqual(database.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(database.execute(
                    "SELECT school_name FROM school_profiles WHERE id=1"
                ).fetchone()[0], "SENTETİK GÜNCEL OKULU")
                self.assertEqual(database.execute(
                    "SELECT first_name FROM student_year_enrollments WHERE school_number=?",
                    ("SENTETİK-001",),
                ).fetchone()[0], "SENTETİK GÜNCEL AD")
        self.assertEqual(manifest["format"], "kelebek-portable-backup")

    def test_hash_mismatch_is_rejected_before_confirmation(self):
        altered = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(self.package_bytes), "r") as source:
            entries = [(item.filename, source.read(item.filename)) for item in source.infolist()]
        with zipfile.ZipFile(altered, "w", compression=zipfile.ZIP_DEFLATED) as destination:
            for name, data in entries:
                if name == "database/kelebek.sqlite3":
                    data = data[:-1] + bytes([data[-1] ^ 0x01])
                destination.writestr(name, data)
        response = self._inspect(altered.getvalue())
        self.assertEqual(response.status_code, 400)
        self.assertIn("SHA-256", response.get_json()["error"])
        self.assertEqual(self._school_name(), "SENTETİK YEDEK OKULU")

    def test_unsafe_archive_path_is_rejected(self):
        malicious_package = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(self.package_bytes), "r") as source:
            entries = {item.filename: source.read(item.filename) for item in source.infolist()}
        manifest = json.loads(entries["manifest.json"])
        manifest["files"][0]["path"] = "files/../../outside.sqlite3"
        entries["manifest.json"] = json.dumps(manifest).encode("utf-8")
        with zipfile.ZipFile(
            malicious_package, "w", compression=zipfile.ZIP_DEFLATED
        ) as destination:
            for name, data in entries.items():
                destination.writestr(name, data)
        response = self._inspect(malicious_package.getvalue())
        self.assertEqual(response.status_code, 400)
        self.assertIn("güvenli olmayan", response.get_json()["error"])
        self.assertEqual(self._school_name(), "SENTETİK YEDEK OKULU")

    def test_cancel_preview_removes_staged_synthetic_backup(self):
        response = self._inspect()
        self.assertEqual(response.status_code, 200, response.get_json())
        token = response.get_json()["token"]
        staged = self.data_dir / ".restore-staging" / token
        self.assertTrue(staged.exists())

        cancelled = self.client.post(
            "/api/backups/restore/cancel",
            json={"token": token},
        )
        self.assertTrue(cancelled.get_json()["cancelled"])
        self.assertFalse(staged.exists())

    def test_older_supported_schema_is_migrated_in_staging_before_restore(self):
        older_package = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(self.package_bytes), "r") as source:
            entries = {item.filename: source.read(item.filename) for item in source.infolist()}
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as older_database:
            older_database.write(entries["database/kelebek.sqlite3"])
            older_database.flush()
            with sqlite3.connect(older_database.name) as database:
                database.execute("ALTER TABLE distribution_reports DROP COLUMN file_sha256")
                database.execute("ALTER TABLE exam_participants DROP COLUMN is_active")
                database.execute("ALTER TABLE exam_organizations DROP COLUMN archived_at")
                database.execute("ALTER TABLE exam_organizations DROP COLUMN copied_from_organization_id")
                database.execute("ALTER TABLE distribution_candidates DROP COLUMN pinned_classroom_ids")
                database.execute(
                    "UPDATE alembic_version SET version_num=?",
                    ("0014_completed_distribution_edits",),
                )
            older_database.seek(0)
            entries["database/kelebek.sqlite3"] = older_database.read()
        manifest = json.loads(entries["manifest.json"])
        manifest["schema_revision"] = "0014_completed_distribution_edits"
        manifest_file = next(item for item in manifest["files"]
                             if item["path"] == "database/kelebek.sqlite3")
        database_bytes = entries["database/kelebek.sqlite3"]
        manifest_file["size_bytes"] = len(database_bytes)
        import hashlib
        manifest_file["sha256"] = hashlib.sha256(database_bytes).hexdigest()
        entries["manifest.json"] = json.dumps(manifest).encode("utf-8")
        with zipfile.ZipFile(older_package, "w", compression=zipfile.ZIP_DEFLATED) as destination:
            for name, data in entries.items():
                destination.writestr(name, data)

        response = self._inspect(older_package.getvalue())
        self.assertEqual(response.status_code, 200, response.get_json())
        preview = response.get_json()["preview"]
        self.assertTrue(preview["migration_required"])
        self.assertEqual(preview["schema_revision"], "0014_completed_distribution_edits")
        self.assertEqual(preview["target_schema_revision"], "0017_exam_archive_and_pins")

        restored = self.client.post(
            "/api/backups/restore/confirm",
            json={"token": response.get_json()["token"], "confirmed": True},
        )
        self.assertEqual(restored.status_code, 200, restored.get_json())
        database_uri = (self.data_dir / "kelebek.sqlite3").as_uri() + "?mode=ro"
        with sqlite3.connect(database_uri, uri=True) as database:
            self.assertEqual(
                database.execute("SELECT version_num FROM alembic_version").fetchone()[0],
                "0017_exam_archive_and_pins",
            )
            self.assertIn("file_sha256", {
                row[1] for row in database.execute("PRAGMA table_info(distribution_reports)")
            })

    def test_failed_install_rolls_back_to_current_synthetic_database(self):
        self._set_current_synthetic_school("SENTETİK KORUNACAK OKULU")
        self._set_synthetic_student_name("SENTETİK KORUNACAK AD")
        self.synthetic_report.write_bytes(b"%PDF-1.4 newer synthetic report\n")
        response = self._inspect()
        token = response.get_json()["token"]
        with patch(
            "kelebek.services.backup_restore._integrity_check",
            side_effect=RuntimeError("synthetic failure"),
        ):
            with self.assertLogs("kelebek", level="ERROR"):
                restored = self.client.post(
                    "/api/backups/restore/confirm",
                    json={"token": token, "confirmed": True},
                )
        self.assertEqual(restored.status_code, 500)
        self.assertEqual(self._school_name(), "SENTETİK KORUNACAK OKULU")
        self.assertEqual(self._synthetic_student_name(), "SENTETİK KORUNACAK AD")
        self.assertEqual(self.synthetic_report.read_bytes(), b"%PDF-1.4 newer synthetic report\n")

    def test_startup_recovery_rolls_back_interrupted_file_swaps(self):
        self._set_current_synthetic_school("SENTETİK KORUNACAK OKULU")
        self._set_synthetic_student_name("SENTETİK KORUNACAK AD")
        engine = self.app.extensions["kelebek_engine"]
        engine.dispose()
        token = "synthetic-recovery-001"
        database_path = self.data_dir / "kelebek.sqlite3"
        old_database = self.data_dir / f".restore-old-database-{token}.sqlite3"
        os.replace(database_path, old_database)
        with zipfile.ZipFile(io.BytesIO(self.package_bytes)) as package:
            partial_database = package.read("database/kelebek.sqlite3")
        database_path.write_bytes(partial_database)

        old_reports = self.reports_dir.with_name(f".restore-old-pdf-{token}")
        os.replace(self.reports_dir, old_reports)
        self.reports_dir.mkdir(parents=True)
        (self.reports_dir / "synthetic-plan.pdf").write_bytes(b"partial replacement")
        (self.data_dir / ".restore-staging" / token).mkdir(parents=True)
        (self.data_dir / ".restore-transaction.json").write_text(json.dumps({
            "transaction_id": token,
            "state": "prepared",
            "reports_existed": True,
        }), encoding="utf-8")

        self.assertTrue(recover_interrupted_restore(self.data_dir))
        self.assertEqual(self._school_name(), "SENTETİK KORUNACAK OKULU")
        self.assertEqual(self._synthetic_student_name(), "SENTETİK KORUNACAK AD")
        self.assertEqual(self.synthetic_report.read_bytes(), b"%PDF-1.4 synthetic test report\n")
        self.assertFalse((self.data_dir / ".restore-transaction.json").exists())

    def test_app_startup_cleans_stale_staging_without_following_symlinks(self):
        startup_data = Path(tempfile.mkdtemp(prefix="kelebek-staging-restart-"))
        staging = startup_data / ".restore-staging"
        stale_preview = staging / "expired-preview"
        stale_preview.mkdir(parents=True)
        (stale_preview / "synthetic.sqlite3").write_bytes(b"synthetic temp only")
        stale_upload = staging / "abandoned.upload"
        stale_upload.write_bytes(b"synthetic upload only")

        outside = startup_data / "outside-staging"
        outside.mkdir()
        sentinel = outside / "keep.txt"
        sentinel.write_text("leave this file alone", encoding="utf-8")
        symlink = staging / "external-link"
        try:
            symlink.symlink_to(outside, target_is_directory=True)
        except OSError:
            symlink = None

        os.environ["KELEBEK_DATA_DIR"] = str(startup_data)
        restarted_app = create_app()
        try:
            self.assertFalse(stale_preview.exists())
            self.assertFalse(stale_upload.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "leave this file alone")
            if symlink is not None:
                self.assertTrue(symlink.is_symlink())
        finally:
            restarted_app.extensions["kelebek_engine"].dispose()
            import shutil
            shutil.rmtree(startup_data)


if __name__ == "__main__":
    unittest.main()
