"""Plan düzenleme kuralı: kesinleşmiş sınavda kullanılıyorsa kopyala, değilse yerinde kaydet."""

import unittest

from _plan_support import PlanTestMixin

from kelebek.models import ClassroomLayout
from kelebek.services.layouts import LayoutReadOnlyError, prepare_layout_for_edit


class LayoutEditRuleTests(PlanTestMixin, unittest.TestCase):
    def _prepare(self, layout_id):
        with self.factory.begin() as session:
            edited, moved = prepare_layout_for_edit(session, session.get(ClassroomLayout, layout_id))
            return edited.id, edited.version, bool(edited.is_active), moved

    def test_unused_layout_is_edited_in_place(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        edited_id, _version, _active, moved = self._prepare(layout["id"])
        self.assertEqual((edited_id, moved), (layout["id"], 0))
        self.assertEqual(len(self.layouts(classroom_id)), 1)

    def test_layout_used_only_by_a_draft_exam_is_edited_in_place(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        self.make_exam(layout_ids=[layout["id"]])
        edited_id, _version, _active, moved = self._prepare(layout["id"])
        self.assertEqual((edited_id, moved), (layout["id"], 0))

    def test_layout_of_a_finalized_exam_is_copied_and_copy_becomes_active(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        exam_id = self.make_exam(layout_ids=[layout["id"]])
        self.distribute(exam_id)
        self.finalize(exam_id)
        edited_id, version, active, _moved = self._prepare(layout["id"])
        self.assertNotEqual(edited_id, layout["id"])
        self.assertTrue(active)
        self.assertEqual(version, 2)
        self.assertEqual(self.seat_count(edited_id), self.seat_count(layout["id"]))
        self.assertEqual([item["is_active"] for item in self.layouts(classroom_id)
                          if item["id"] == layout["id"]], [False])

    def test_finalized_exam_keeps_its_original_seats(self):
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        exam_id = self.make_exam(layout_ids=[layout["id"]])
        self.distribute(exam_id)
        self.finalize(exam_id)
        before = self.candidates(exam_id)
        self.assertTrue(before)
        self._prepare(layout["id"])
        self.assertEqual(self.candidates(exam_id), before)
        self.assertEqual([room["layout_id"] for room in self.exam(exam_id)["room_selections"]], [layout["id"]])

    def test_draft_exam_follows_the_copy_and_loses_its_selection(self):
        """Aynı plan hem kesinleşmiş hem taslak sınavda kullanılıyor."""
        classroom_id = self.make_classroom()
        layout = self.make_layout(classroom_id)
        done_id = self.make_exam("KESİN SINAV", layout_ids=[layout["id"]])
        self.distribute(done_id)
        self.finalize(done_id)
        draft_id = self.make_exam("TASLAK SINAV", layout_ids=[layout["id"]])
        self.distribute(draft_id)
        self.assertIsNotNone(self.exam(draft_id)["selected_candidate_id"])

        edited_id, _version, _active, moved = self._prepare(layout["id"])
        self.assertEqual(moved, 1)
        draft = self.exam(draft_id)
        self.assertEqual([room["layout_id"] for room in draft["room_selections"]], [edited_id])
        self.assertIsNone(draft["selected_candidate_id"])
        self.assertEqual([room["layout_id"] for room in self.exam(done_id)["room_selections"]], [layout["id"]])

    def test_archive_year_layout_cannot_be_prepared(self):
        classroom_id = self.make_classroom()
        archive_id = self.make_archive_layout(classroom_id)
        before = len(self.layouts(classroom_id))
        with self.assertRaises(LayoutReadOnlyError):
            self._prepare(archive_id)
        self.assertEqual(len(self.layouts(classroom_id)), before)

    def test_template_is_edited_in_place(self):
        classroom_id = self.make_classroom()
        template = self.make_layout(classroom_id, "Şablon", seats=False, is_template=True, academic_year_id=None)
        self.assertEqual(self._prepare(template["id"])[0], template["id"])


if __name__ == "__main__":
    unittest.main()
