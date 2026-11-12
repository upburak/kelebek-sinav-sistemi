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


def test_a_success_never_pushes_out_an_open_error(page):
    open_app(page)
    for index in range(4):
        page.evaluate(f"window.__kelebekNotify.error('Hata {index}')")
    page.evaluate("window.__kelebekNotify.success('Sonradan gelen başarı')")
    notes = page.get_by_test_id("notification")
    expect(notes).to_have_count(4)
    expect(page.locator("[data-testid=notification][data-kind=error]")).to_have_count(4)
    expect(notes.first).to_contain_text("Hata 0")


def test_saving_school_profile_is_announced(page):
    open_app(page, "Okul ve yöneticiler")
    page.locator(".school-form-card button[type=submit]").click()
    expect(page.get_by_test_id("notification").filter(has_text="Okul bilgileri kaydedildi")).to_be_visible()


def test_renaming_a_classroom_is_announced(page):
    from _ui import make_room

    room = make_room("BİLDİRİM AD SALONU")
    open_app(page, "Derslikler")
    card = page.locator("[data-testid^=classroom-card-]", has_text=room["name"])
    card.get_by_role("button", name="Adını düzenle").click()
    page.locator("#classroom-name-edit").fill("BİLDİRİM AD SALONU")
    page.get_by_role("button", name="Adı kaydet").click()
    expect(page.get_by_test_id("notification").filter(has_text="Derslik adı kaydedildi")).to_be_visible()


def test_saving_room_selection_is_announced(page):
    from _ui import make_exam, make_room

    room = make_room("BİLDİRİM SEÇİM SALONU")
    make_exam("BİLDİRİM SEÇİM SINAVI", group_limit=2)
    open_app(page, "Sınav organizasyonlar")
    page.locator("[data-testid^=exam-row-]", has_text="BİLDİRİM SEÇİM SINAVI").locator(
        "[data-testid^=exam-open-]").click()
    page.locator(".exam-room-option", has_text=room["name"]).locator("input[type=checkbox]").check()
    page.locator("[data-testid^=exam-room-save-]").click()
    expect(page.get_by_test_id("notification").filter(has_text="Derslik seçimi kaydedildi")).to_be_visible()


def test_backup_download_is_announced(page):
    open_app(page, "Yedek ve arşiv")
    with page.expect_download(timeout=60_000):
        page.get_by_role("button", name="Yedek paketini oluştur ve indir").click()
    expect(page.get_by_test_id("notification").filter(has_text="Yedek")).to_be_visible()
