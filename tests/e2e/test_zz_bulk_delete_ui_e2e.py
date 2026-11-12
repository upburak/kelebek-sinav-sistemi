"""Toplu silme arayüzde çalışmalı (Karar 73).

Dosya adı bilerek "zz" ile başlar: ortak test verisini sildiği için en son koşar.
"""

from __future__ import annotations

import pytest
import requests
from _ui import BASE_URL, api, current_year_id, open_app

if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)

expect = pytest.importorskip("playwright.sync_api").expect


def _exam_count() -> int:
    return len(requests.get(api("/exam-organizations"), params={"academic_year_id": current_year_id()},
                            timeout=30).json()["organizations"])


def test_all_exams_can_be_deleted_from_the_exam_list(page):
    assert _exam_count() > 0
    open_app(page, "Sınav organizasyonlar")
    page.get_by_test_id("bulk-delete-exams").click()      # onay sorusu fixture tarafından kabul edilir
    note = page.get_by_test_id("notification").filter(has_text="sınav silindi")
    expect(note).to_be_visible(timeout=30_000)
    expect(note).to_contain_text("yedek")
    expect(page.locator("[data-testid^=exam-row-]")).to_have_count(0)
    assert _exam_count() == 0


def test_all_students_can_be_deleted_from_the_student_list(page):
    open_app(page, "Öğrenci kay")
    page.get_by_test_id("bulk-delete-students").click()
    expect(page.get_by_test_id("notification").filter(has_text="öğrenci silindi")).to_be_visible(timeout=30_000)
    expect(page.get_by_text("Bu eğitim yılında henüz öğrenci yok.")).to_be_visible()
    groups = requests.get(api("/student-groups"), params={"academic_year_id": current_year_id()}, timeout=30).json()
    assert groups["groups"] == []


def test_all_classrooms_can_be_deleted_from_the_classroom_screen(page):
    open_app(page, "Derslikler")
    page.get_by_test_id("bulk-delete-classrooms").click()
    expect(page.get_by_test_id("notification").filter(has_text="derslik silindi")).to_be_visible(timeout=30_000)
    expect(page.locator("[data-testid^=classroom-card-]")).to_have_count(0)
    assert requests.get(api("/classrooms"), timeout=30).json()["classrooms"] == []
