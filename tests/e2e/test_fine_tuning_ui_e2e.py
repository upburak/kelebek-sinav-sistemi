"""İnce ayar isteği (13 Kasım 2026): plan düzenleyici, derslik kapat/sil, pasif süzgeci, yenilikler.

Kullanıcı bildirdi: plan oluşturulduktan sonra satır/sütun eklenemiyor, masa
tekli/çiftli yapılamıyor; planı olan derslik silinemiyor ya da kapatılamıyor;
"Pasif kayıtları göster" tüm öğrencileri listeliyor; açılıştaki yenilikler
penceresi kapatılamayacak kadar uzun.
"""

from __future__ import annotations

import pytest
import requests
from _ui import BASE_URL, api, current_year_id, make_exam, make_room, open_app

if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)

expect = pytest.importorskip("playwright.sync_api").expect


def open_classroom(page, name: str):
    open_app(page, "Derslikler")
    page.locator("[data-testid^=classroom-card-]", has_text=name).locator("button").first.click()


def test_row_and_column_can_be_added_to_a_generated_plan(page):
    room = make_room("İNCE-EKLE", rows=2, columns=2)
    open_classroom(page, room["name"])
    expect(page.locator(".layout-canvas .plan-seat")).to_have_count(8)
    page.get_by_test_id("plan-edit-btn").click()
    page.get_by_test_id("plan-add-row").click()
    expect(page.locator(".layout-canvas .plan-seat")).to_have_count(12)
    expect(page.get_by_test_id("plan-row-3")).to_be_visible()
    page.get_by_test_id("plan-add-column").click()
    expect(page.locator(".layout-canvas .plan-seat")).to_have_count(18)
    expect(page.get_by_test_id("plan-column-3")).to_be_visible()
    expect(page.get_by_test_id("plan-status")).to_contain_text("18 koltuk")


def test_desk_menu_switches_single_double_and_deletes(page):
    room = make_room("İNCE-MASA", rows=2, columns=2)
    open_classroom(page, room["name"])
    page.get_by_test_id("plan-edit-btn").click()
    desk = page.get_by_test_id("plan-desk-S1-M1")
    desk.get_by_role("button", name="S1-M1 masası seçenekleri").click()
    page.get_by_test_id("plan-desk-menu").get_by_role("menuitem", name="Tekli yap").click()
    expect(page.get_by_test_id("plan-desk-S1-M1").locator(".plan-seat")).to_have_count(1)
    expect(page.locator(".layout-canvas .plan-seat")).to_have_count(7)
    # Sağ tuş da aynı menüyü açar.
    page.get_by_test_id("plan-desk-S2-M2").click(button="right")
    page.get_by_test_id("plan-desk-menu").get_by_role("menuitem", name="Masayı sil").click()
    expect(page.locator(".layout-canvas .plan-desk-position")).to_have_count(3)
    expect(page.locator(".layout-canvas .plan-seat")).to_have_count(5)
    page.get_by_test_id("plan-edit-btn").click()
    expect(page.get_by_test_id("notification").filter(has_text="Plan kaydedildi")).to_be_visible()


def test_corridor_is_added_and_removed_from_the_column_menu(page):
    # Kullanıcı isteği: sütun eklenince koridor kendiliğinden gelmiyor; elle eklenebilsin.
    room = make_room("İNCE-KORİDOR", rows=2, columns=2)
    open_classroom(page, room["name"])
    page.get_by_test_id("plan-edit-btn").click()
    page.get_by_test_id("plan-add-column").click()
    expect(page.get_by_test_id("plan-column-3")).to_be_visible()
    expect(page.locator(".layout-canvas .plan-corridor-label")).to_have_count(2)  # 2 satır × 1 koridor
    page.get_by_test_id("plan-column-2").click()
    page.get_by_test_id("plan-column-menu").get_by_role("menuitem", name="Sağına koridor ekle").click()
    expect(page.locator(".layout-canvas .plan-corridor-label")).to_have_count(4)
    expect(page.locator(".layout-canvas .plan-seat")).to_have_count(12)
    page.get_by_test_id("plan-column-1").click()
    page.get_by_test_id("plan-column-menu").get_by_role("menuitem", name="Sağındaki koridoru kaldır").click()
    expect(page.locator(".layout-canvas .plan-corridor-label")).to_have_count(2)
    # En sağdaki sütunda koridor seçeneği yerine açıklama çıkar.
    page.get_by_test_id("plan-column-3").click()
    expect(page.get_by_test_id("plan-column-menu")).to_contain_text("Önce sağına sütun ekle")
    expect(page.get_by_test_id("plan-column-menu").get_by_role("menuitem")).to_have_count(0)


def test_row_handle_drag_moves_the_whole_row(page):
    room = make_room("İNCE-SÜRÜKLE", rows=2, columns=2)
    open_classroom(page, room["name"])
    page.get_by_test_id("plan-edit-btn").click()
    # Sürükleme sırasında sayfa kaymasın diye tuval önce görünür alanın ortasına alınır.
    page.locator(".layout-canvas").evaluate("node => node.scrollIntoView({ block: 'center' })")
    before = page.get_by_test_id("plan-desk-S2-M1").bounding_box()
    canvas = page.locator(".layout-canvas").bounding_box()
    handle = page.get_by_test_id("plan-row-2")
    # İkinci satırı iki ızgara hücresi (180 piksel) aşağı bırak.
    handle.drag_to(page.locator(".layout-canvas"),
                   target_position={"x": 30, "y": before["y"] - canvas["y"] + 190})
    # Konum, sayfa kaydırmasından etkilenmesin diye kayıttan okunur.
    rows = []
    for _attempt in range(40):
        layout = requests.get(api(f"/classrooms/{room['classroom_id']}/plan"),
                              params={"academic_year_id": current_year_id()}, timeout=30).json()["plan"]
        rows = sorted({desk["y"] for desk in layout["desks"]})
        if rows == [0.0, 6.0]:
            break
        page.wait_for_timeout(250)
    assert rows == [0.0, 6.0]
    expect(page.get_by_test_id("plan-row-2")).to_be_visible()


def test_classroom_can_be_closed_and_disappears_from_new_exams(page):
    room = make_room("İNCE-KAPAT", rows=2, columns=2)
    open_classroom(page, room["name"])
    page.get_by_test_id("classroom-close-btn").click()
    expect(page.get_by_test_id("classroom-closed-tag")).to_be_visible()
    expect(page.get_by_test_id("notification").filter(has_text="kapatıldı")).to_be_visible()
    exam_id = make_exam("İNCE KAPALI SINAVI", group_limit=1)
    page.locator("nav button", has_text="Sınav").click()
    page.get_by_test_id(f"exam-open-{exam_id}").click()
    expect(page.locator(".exam-room-option").first).to_be_visible()
    expect(page.locator(".exam-room-option", has_text="İNCE-KAPAT")).to_have_count(0)
    # Yeniden açınca geri gelir.
    done = requests.patch(api(f"/classrooms/{room['classroom_id']}"), json={"is_closed": False}, timeout=30)
    assert done.status_code == 200, done.text


def test_classroom_with_a_plan_can_be_deleted_but_not_when_used(page):
    free = make_room("İNCE-SİL", rows=2, columns=2)
    used = make_room("İNCE-KULLANILDI", rows=2, columns=2)
    make_exam("İNCE KULLANAN SINAV", layout_ids=[used["layout_id"]], group_limit=1)
    open_classroom(page, used["name"])
    expect(page.get_by_test_id("classroom-delete-btn")).to_be_disabled()
    page.locator("[data-testid^=classroom-card-]", has_text="İNCE-SİL").locator("button").first.click()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_test_id("classroom-delete-btn").click()
    expect(page.locator("[data-testid^=classroom-card-]", has_text="İNCE-SİL")).to_have_count(0)
    listed = requests.get(api("/classrooms"), timeout=30).json()["classrooms"]
    assert not any(item["id"] == free["classroom_id"] for item in listed)


def test_inactive_toggle_lists_only_inactive_students(page):
    year = current_year_id()
    created = requests.post(api("/students"), timeout=30, json={
        "academic_year_id": year, "school_number": "PASIF-901", "first_name": "SENTETİK",
        "last_name": "PASİF ÖĞRENCİ", "class_level": "9", "section": "A"})
    assert created.status_code in (201, 409), created.text
    students = requests.get(api("/students"), params={"academic_year_id": year, "include_inactive": "true"},
                            timeout=30).json()["students"]
    target = next(item for item in students if item["school_number"] == "PASIF-901")
    if target.get("is_active", True):
        done = requests.post(api(f"/students/{target['id']}/deactivate"), timeout=30,
                             json={"confirmed": True, "academic_year_id": year})
        assert done.status_code == 200, done.text
    open_app(page, "Öğrenci kay")
    expect(page.locator(".student-table-scroll tbody tr").first).to_be_visible()
    expect(page.locator(".student-table-scroll tbody tr", has_text="PASIF-901")).to_have_count(0)
    page.get_by_test_id("student-inactive-toggle").click()
    rows = page.locator(".student-table-scroll tbody tr")
    expect(rows.filter(has_text="PASIF-901")).to_have_count(1)
    expect(page.locator(".student-table-scroll tbody tr:not(.inactive-student-row)")).to_have_count(0)
    expect(page.get_by_test_id("student-filter-count")).to_contain_text("pasif kayıt")
    expect(page.get_by_test_id("student-inactive-toggle")).to_have_text("Aktif öğrencilere dön")


def test_release_notes_page_lists_every_version(page):
    notes = requests.get(api("/app/release-notes"), timeout=30).json()
    assert notes["notes"][0]["version"] == notes["current_version"]
    open_app(page, "Yedek")
    expect(page.get_by_test_id("release-notes")).to_be_visible()
    expect(page.locator("[data-testid^=release-note-]")).to_have_count(len(notes["notes"]))


def test_whats_new_dialog_shows_only_the_latest_version(page):
    notes = requests.get(api("/app/release-notes"), timeout=30).json()
    latest = notes["notes"][0]
    page.route("**/api/app/whats-new", lambda route: route.fulfill(json={
        "show": True, "current_version": notes["current_version"], "previous_version": "0.1.0",
        "notes": notes["notes"]}))
    page.route("**/api/app/whats-new/seen", lambda route: route.fulfill(json={"seen": notes["current_version"]}))
    page.goto(BASE_URL)
    dialog = page.get_by_test_id("whats-new-dialog")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_test_id("whats-new-items").locator("li")).to_have_count(len(latest["items"]))
    close = dialog.get_by_test_id("whats-new-close")
    expect(close).to_be_in_viewport()
    dialog.get_by_test_id("whats-new-all").click()
    expect(dialog).to_have_count(0)
    expect(page.get_by_test_id("release-notes")).to_be_visible()
