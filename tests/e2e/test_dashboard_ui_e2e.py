"""Genel Bakış panosu ve öğrenci listesi filtresi gerçek tarayıcıda doğru çalışmalı.

Gerileme: eski "Kurulum adımları" kartı sabit yazılmıştı; öğrenciler ve
derslikler kayıtlı olsa bile "1 / 3 hazır" gösteriyordu. Pano artık sayıları
ve adımları canlı veriden hesaplar.
"""

from __future__ import annotations

import os

import pytest
import requests

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)


def _open(page, section: str | None = None):
    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid=dashboard]")
    closer = page.locator(".whats-new-backdrop button").first
    if closer.count() and closer.is_visible():
        closer.click()
    if section:
        page.locator("nav button", has_text=section).click()


def test_dashboard_numbers_come_from_live_data(page):
    api = f"{BASE_URL}/api"
    year = requests.get(f"{api}/academic-years", timeout=30).json()["selected_academic_year_id"]
    groups = requests.get(f"{api}/student-groups", params={"academic_year_id": year}, timeout=30).json()["groups"]
    expected_students = sum(group["student_count"] for group in groups)
    assert expected_students > 0

    _open(page)
    stat = page.get_by_test_id("stat-students")
    stat.get_by_text(str(expected_students), exact=True).wait_for()
    # Okul, öğrenci ve derslik adımları sentetik veriyle tamamlanmış olmalı.
    for key in ("school", "students", "classrooms"):
        assert "complete" in (page.get_by_test_id(f"setup-step-{key}").get_attribute("class") or ""), key
    assert "1 / 3" not in page.get_by_test_id("setup-progress").inner_text()


def test_dashboard_tiles_navigate(page):
    _open(page)
    page.get_by_test_id("stat-students").click()
    page.wait_for_selector("[data-testid=student-search]")


def test_student_list_can_be_searched_and_filtered(page):
    api = f"{BASE_URL}/api"
    year = requests.get(f"{api}/academic-years", timeout=30).json()["selected_academic_year_id"]
    students = [item for item in requests.get(f"{api}/students", params={"academic_year_id": year},
                                              timeout=30).json()["students"] if item.get("is_active", True)]
    target = students[0]
    same_class = [item for item in students
                  if (item["class_level"], item["section"]) == (target["class_level"], target["section"])]

    _open(page, "Öğrenci kay")
    page.wait_for_selector("[data-testid=student-search]")
    page.get_by_test_id("student-class-filter").select_option(f"{target['class_level']}/{target['section']}")
    assert page.get_by_test_id("student-filter-count").inner_text().startswith(f"{len(same_class)} /")

    page.get_by_test_id("student-search").fill(target["school_number"])
    assert page.locator(".student-table-scroll tbody tr").count() >= 1
    assert target["last_name"] in page.locator(".student-table-scroll tbody").inner_text()

    page.get_by_test_id("student-search").fill("böyle-bir-öğrenci-yok")
    page.get_by_text("Aramayla eşleşen öğrenci yok.").wait_for()
