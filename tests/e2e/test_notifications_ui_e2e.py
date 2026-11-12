"""Her işlemin sonucu aynı yerde, aynı biçimde bildirilmeli.

Gerileme: ekranlar sonucu kendi köşelerinde, kendi biçimlerinde gösteriyor,
bazıları hiç göstermiyordu; kullanıcı "yaptığımın sonucunu göremedim" dedi.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _ui import BASE_URL, open_app

if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)

expect = pytest.importorskip("playwright.sync_api").expect

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "frontend" / "public" / "downloads" / "kelebek_sentetik_demo_48_ogrenci.xlsx"


def test_import_completion_is_announced_with_a_link_to_classrooms(page):
    open_app(page, "Öğrenci kay")
    page.set_input_files("#student-import input[type=file]", str(SAMPLE))
    page.locator("#import-preview-title").wait_for(timeout=30_000)
    page.locator("button.validate-import").click()
    commit = page.locator("button.commit-import").last
    commit.wait_for(timeout=30_000)
    commit.click()

    note = page.get_by_test_id("notification").filter(has_text="öğrenci")
    expect(note).to_have_attribute("data-kind", "success", timeout=30_000)
    expect(note).to_contain_text("48 öğrenci")
    note.get_by_role("button", name="Derslik planlarını kontrol et").click()
    expect(page.locator("h1")).to_have_text("Derslikler")


def test_error_stays_until_closed_and_survives_a_later_success(page):
    open_app(page)
    page.evaluate("window.__kelebekNotify.error('Deneme hatası')")
    page.evaluate("window.__kelebekNotify.success('Deneme başarısı')")
    expect(page.get_by_test_id("notification")).to_have_count(2)
    page.wait_for_timeout(7000)
    expect(page.get_by_test_id("notification")).to_have_count(1)
    expect(page.get_by_test_id("notification")).to_have_attribute("data-kind", "error")
    expect(page.get_by_test_id("notification")).to_have_attribute("role", "alert")
    page.get_by_label("Bildirimi kapat").click()
    expect(page.get_by_test_id("notification")).to_have_count(0)


def test_at_most_four_notifications_are_shown(page):
    open_app(page)
    for index in range(6):
        page.evaluate(f"window.__kelebekNotify.error('Hata {index}')")
    notes = page.get_by_test_id("notification")
    expect(notes).to_have_count(4)
    expect(notes.last).to_contain_text("Hata 5")
