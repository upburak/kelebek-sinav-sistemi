"""Synthetic acceptance checks for the 0016 participant activation migration."""

import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "0016_exam_participant_active.py"
)
SPEC = importlib.util.spec_from_file_location("migration_0016", MIGRATION_PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


class Migration0016Tests(unittest.TestCase):
    def test_existing_participants_remain_and_default_to_active(self):
        engine = create_engine("sqlite:///:memory:")
        try:
            with engine.begin() as connection:
                connection.execute(text(
                    "CREATE TABLE exam_participants "
                    "(id TEXT PRIMARY KEY, student_id TEXT NOT NULL)"
                ))
                connection.execute(text(
                    "INSERT INTO exam_participants (id, student_id) "
                    "VALUES ('SYNTHETIC-PARTICIPANT', 'SYNTHETIC-STUDENT')"
                ))

                with Operations.context(MigrationContext.configure(connection)):
                    MIGRATION.upgrade()

                participant = connection.execute(text(
                    "SELECT id, student_id, is_active FROM exam_participants"
                )).one()
                self.assertEqual(tuple(participant), (
                    "SYNTHETIC-PARTICIPANT", "SYNTHETIC-STUDENT", 1
                ))

            column = next(
                item for item in inspect(engine).get_columns("exam_participants")
                if item["name"] == "is_active"
            )
            self.assertFalse(column["nullable"])
            self.assertIn("1", str(column["default"]))
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
