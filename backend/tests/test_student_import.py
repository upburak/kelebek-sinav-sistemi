"""Synthetic coverage for roster-table detection and validation."""

import unittest

from kelebek.api.student_import import _preview_mapping, _validate_rows
from kelebek.services.student_import import ImportTable


class StudentImportTests(unittest.TestCase):
    def _table(self, records, formula_cells=frozenset()):
        headers = ["Öğrenci No", "Adı", "Soyadı", "Sınıf", "Şube"]
        rows = [tuple(headers), *[tuple(row) for row in records]]
        return ImportTable(
            name="9-A",
            rows=rows,
            header_index=0,
            headers=headers,
            class_level="9",
            section="A",
            formula_cells=frozenset(formula_cells),
        )

    def test_internal_blank_gap_keeps_students_and_formula_tail_is_ignored(self):
        footer_row_index = 8
        table = self._table(
            [
                ["SENTETIK-001", "ÖRNEK AD 1", "ÖRNEK SOYAD 1", "9", "A"],
                ["SENTETIK-002", "ÖRNEK AD 2", "ÖRNEK SOYAD 2", "9", "A"],
                [None, None, None, None, None],
                [None, None, None, None, None],
                ["SENTETIK-003", "ÖRNEK AD 3", "ÖRNEK SOYAD 3", "9", "A"],
                [None, None, None, None, None],
                [None, None, None, None, None],
                ["SENTETIK-FOOTER", "ÖRNEK EK AD", "ÖRNEK EK SOYAD", "9", "A"],
            ],
            formula_cells={(footer_row_index, 1)},
        )

        result, status = _validate_rows([table], _preview_mapping(table))

        self.assertEqual(status, 200)
        self.assertEqual(result["validation"]["total_rows"], 3)
        self.assertEqual(result["validation"]["issue_count"], 0)

    def test_duplicate_school_number_in_roster_is_still_reported(self):
        table = self._table(
            [
                ["SENTETIK-001", "ÖRNEK AD 1", "ÖRNEK SOYAD 1", "9", "A"],
                ["SENTETIK-001", "ÖRNEK AD 2", "ÖRNEK SOYAD 2", "9", "A"],
            ]
        )

        result, status = _validate_rows([table], _preview_mapping(table))

        self.assertEqual(status, 200)
        self.assertEqual(result["validation"]["total_rows"], 2)
        self.assertEqual(result["validation"]["issue_count"], 1)
        self.assertIn("Okul numarası", result["validation"]["issues"][0]["issue"])


if __name__ == "__main__":
    unittest.main()
