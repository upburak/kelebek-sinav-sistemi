"""Sınavlar: yalın liste ve her sınavın kendi sayfası.

Gerileme: bütün sınavlar, her biri kendi düğmeleri ve panelleriyle aynı sayfada
duruyordu; kullanıcı "ekranlar çok kalabalıktı" dedi. Ayrıca sınava giren
sınıflar görünmediği için bir sınıfın sınava dahil edilmediği fark edilmedi.
"""

from __future__ import annotations

import pytest
import requests
from _ui import BASE_URL, api, distribute, finalize, make_exam, make_room, open_app

if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)

expect = pytest.importorskip("playwright.sync_api").expect

TITLE = "[data-testid^=exam-guide-title-]"


def open_exam(page, name: str):
    open_app(page, "Sınav organizasyonlar")
    page.locator("[data-testid^=exam-row-]", has_text=name).locator("[data-testid^=exam-open-]").click()
    expect(page.get_by_test_id("exam-back")).to_be_visible()


def toggle_seat(room: dict, index: int, available: bool) -> None:
    detail = requests.get(api(f"/classrooms/{room['classroom_id']}/plan"),
                          params={"academic_year_id": requests.get(api("/academic-years"), timeout=30)
                                  .json()["selected_academic_year_id"]}, timeout=30).json()["plan"]
    seats = [seat for desk in detail["desks"] for seat in desk["seats"]]
    response = requests.patch(
        api(f"/classrooms/{room['classroom_id']}/layouts/{detail['layout']['id']}/seats/{seats[index]['id']}"),
        json={"is_available": available}, timeout=30)
    assert response.status_code == 200, response.text


def test_list_shows_one_row_per_exam_and_no_inline_controls(page):
    make_exam("SAYFA LİSTE SINAVI")
    open_app(page, "Sınav organizasyonlar")
    row = page.locator("[data-testid^=exam-row-]", has_text="SAYFA LİSTE SINAVI")
    expect(row.locator("button")).to_have_count(1)
    expect(row.locator("[data-testid^=exam-stage-]")).to_have_text("Derslik seçilecek")
    expect(row).to_contain_text("8 sınıf · 48 öğrenci")
    expect(page.locator(".exam-guide")).to_have_count(0)
    assert "PDF" not in row.inner_text()


def test_opening_an_exam_shows_only_that_exam_with_its_classes(page):
    make_exam("SAYFA TEK SINAV", group_limit=3)
    open_exam(page, "SAYFA TEK SINAV")
    expect(page.locator("[data-testid^=exam-card-]")).to_have_count(1)
    classes = page.get_by_test_id("exam-classes")
    expect(classes.locator("li")).to_have_count(3)
    expect(classes.locator("li").first).to_contain_text("6 öğrenci")
    expect(page.locator("[data-testid^=exam-card-] .exam-organization-copy")).to_contain_text("18 öğrenci")
    page.get_by_test_id("exam-back").click()
    expect(page.locator("[data-testid^=exam-row-]").first).to_be_visible()


def test_new_exam_opens_its_own_page_and_states_what_was_created(page):
    open_app(page, "Sınav organizasyonlar")
    page.get_by_test_id("exam-new-btn").click()
    form = page.locator(".exam-create-form")
    form.locator('input[maxlength="160"]').fill("SAYFA AÇILIŞ SINAVI")
    form.locator("input[type=date]").fill("2026-12-24")
    boxes = form.locator(".exam-general-groups input[type=checkbox]")
    for index in range(4):
        boxes.nth(index).check()
    expect(page.get_by_test_id("exam-create-summary")).to_have_text("4 sınıf · 24 öğrenci")
    page.get_by_test_id("exam-create-submit").click()
    expect(page.get_by_test_id("exam-back")).to_be_visible()
    expect(page.get_by_test_id("exam-notice")).to_contain_text("4 sınıf · 24 öğrenci")
    expect(page.get_by_test_id("exam-classes").locator("li")).to_have_count(4)


def test_quick_clicks_on_class_boxes_all_register(page):
    """Art arda hızlı tıklamada hiçbir sınıf işareti kaybolmamalı."""
    open_app(page, "Sınav organizasyonlar")
    page.get_by_test_id("exam-new-btn").click()
    page.evaluate("""() => {
        document.querySelectorAll('.exam-create-form .exam-general-groups input[type=checkbox]')
            .forEach((box, index) => { if (index < 5) box.click() })
    }""")
    expect(page.locator(".exam-create-form .exam-general-groups input[type=checkbox]:checked")).to_have_count(5)
    expect(page.get_by_test_id("exam-create-summary")).to_have_text("5 sınıf · 30 öğrenci")


def test_exam_short_of_seats_stays_on_rooms_step(page):
    room = make_room("SAYFA KÜÇÜK SALON", rows=2, columns=2)      # 8 koltuk
    make_exam("SAYFA KOLTUK EKSİK SINAVI", layout_ids=[room["layout_id"]], group_limit=2)   # 12 öğrenci
    open_exam(page, "SAYFA KOLTUK EKSİK SINAVI")
    expect(page.locator(TITLE)).to_have_text("4 koltuk eksik")
    expect(page.locator("[data-testid^=candidate-create-]")).to_have_count(0)
    expect(page.locator(".exam-room-panel")).to_be_visible()


def test_plan_change_asks_for_redistribution(page):
    room = make_room("SAYFA PLAN DEĞİŞEN SALON")
    exam_id = make_exam("SAYFA PLAN DEĞİŞEN SINAV", layout_ids=[room["layout_id"]], group_limit=2)
    distribute(exam_id)
    toggle_seat(room, 0, False)
    try:
        open_exam(page, "SAYFA PLAN DEĞİŞEN SINAV")
        expect(page.locator(TITLE)).to_have_text("Derslik planı değişti, yeniden dağıt")
        expect(page.locator("[data-testid^=candidate-create-]")).to_be_visible()
    finally:
        toggle_seat(room, 0, True)


def test_finished_steps_can_be_revisited_and_later_steps_cannot(page):
    room = make_room("SAYFA ADIM SALONU")
    exam_id = make_exam("SAYFA ADIM SINAVI", layout_ids=[room["layout_id"]], group_limit=2)
    distribute(exam_id)
    open_exam(page, "SAYFA ADIM SINAVI")
    steps = page.locator(".exam-guide-steps button")
    expect(steps).to_have_count(5)
    expect(steps.nth(4)).to_be_disabled()
    steps.nth(0).click()
    expect(page.get_by_test_id("exam-rooms-summary")).to_contain_text("SAYFA ADIM SALONU")
    steps.nth(2).click()
    expect(page.locator("[data-testid^=candidate-result-]")).to_be_visible()


def test_reports_are_the_last_step_and_archive_lives_under_advanced(page):
    room = make_room("SAYFA RAPOR SALONU")
    exam_id = make_exam("SAYFA RAPOR SINAVI", layout_ids=[room["layout_id"]], group_limit=2)
    distribute(exam_id)
    finalize(exam_id)
    open_exam(page, "SAYFA RAPOR SINAVI")
    step = page.get_by_test_id("exam-reports-step")
    expect(step).to_be_visible()
    expect(step.get_by_text("PDF raporları")).to_be_visible()
    expect(step.get_by_test_id("report-exam-select")).to_have_count(0)
    expect(page.locator("[data-testid^=archive-btn-]")).not_to_be_visible()
    page.locator("[data-testid^=exam-advanced-] > summary").click()
    expect(page.locator("[data-testid^=archive-btn-]")).to_be_visible()


def test_previous_distribution_is_one_button_and_the_word_aday_is_gone(page):
    room = make_room("SAYFA GERİ DÖN SALONU")
    exam_id = make_exam("SAYFA GERİ DÖN SINAVI", layout_ids=[room["layout_id"]], group_limit=2)
    distribute(exam_id)
    open_exam(page, "SAYFA GERİ DÖN SINAVI")
    card = page.locator("[data-testid^=exam-card-]")
    first_id = card.locator("[data-testid^=candidate-result-]").get_attribute("data-testid")
    expect(card.locator("[data-testid^=distribution-back-]")).to_have_count(0)
    card.locator("[data-testid^=candidate-recreate-]").click()
    back = card.locator("[data-testid^=distribution-back-]")
    expect(back).to_have_text("Önceki dağıtıma dön", timeout=60_000)
    expect(card.locator(".exam-previous")).to_have_count(0)
    assert card.locator("[data-testid^=candidate-result-]").get_attribute("data-testid") != first_id
    back.click()
    expect(card.locator(f"[data-testid={first_id}]")).to_be_visible()
    visible = page.evaluate("""() => {
        const root = document.querySelector('[data-testid^=exam-card-]').cloneNode(true)
        root.querySelectorAll('[data-testid^=exam-advanced-]').forEach((node) => node.remove())
        return root.innerText.toLowerCase()
    }""")
    assert "aday" not in visible


def test_reports_menu_still_lists_finalized_exams(page):
    open_app(page, "Raporlar")
    expect(page.get_by_test_id("report-exam-select")).to_be_visible()


def test_notice_says_why_an_extra_room_was_added(page):
    """Sınıfın kendi dersliğinde koltuk yetmezse eklenen derslik ve nedeni açıkça yazılmalı.

    Gerileme: 9-B dersliğinde 2 koltuk eksikti; uygulama sessizce 11-A dersliğini
    ekledi ve kullanıcı bunu "5 sınıf seçtim" diye okudu.
    """
    year = requests.get(api("/academic-years"), timeout=30).json()["selected_academic_year_id"]
    groups = requests.get(api("/student-groups"), params={"academic_year_id": year}, timeout=30).json()["groups"]
    first, second = groups[2], groups[3]   # başka testlerin kurduğu dersliklerle çakışmasın
    own = make_room(f"{first['class_level']}-{first['section']} Derslik", rows=1, columns=2)   # 4 koltuk < 6 öğrenci
    make_room(f"{second['class_level']}-{second['section']} Derslik", rows=2, columns=2)
    open_app(page, "Sınav organizasyonlar")
    page.get_by_test_id("exam-new-btn").click()
    form = page.locator(".exam-create-form")
    form.locator('input[maxlength="160"]').fill("SAYFA EK DERSLİK SINAVI")
    form.locator("input[type=date]").fill("2026-12-26")
    form.locator(".exam-general-groups label", has_text=f"{first['class_level']}/{first['section']}").first.locator(
        "input").check()
    page.get_by_test_id("exam-create-submit").click()
    notice = page.get_by_test_id("exam-notice")
    expect(notice).to_contain_text("1 sınıf · 6 öğrenci")
    expect(notice).to_contain_text("koltuk yetmediği için")
    expect(notice).to_contain_text(own["name"])
