"""Derslikler: karta tıklayınca doğrudan o dersliğin oturma planı açılmalı.

Gerileme: dersliğe tıklayınca düzen listesi, sürümler ve şablon seçenekleri
çıkıyor; planı değiştirmek için "Kopyala ve düzenle" ile yeni sürüm açmak
gerekiyordu. Kullanıcı "parçaların ilişkisini çözemedim" dedi.
"""

from __future__ import annotations

import pytest
import requests
from _ui import BASE_URL, api, make_exam, make_room, open_app

if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)

expect = pytest.importorskip("playwright.sync_api").expect


def open_classroom(page, name: str):
    open_app(page, "Derslikler")
    page.locator("[data-testid^=classroom-card-]", has_text=name).locator("button").first.click()


def test_classroom_card_opens_its_plan_directly(page):
    room = make_room("PLAN-UI SALONU")
    open_classroom(page, room["name"])
    expect(page.get_by_test_id("plan-status")).to_contain_text("48 koltuk")
    expect(page.get_by_test_id("plan-edit-btn")).to_have_text("Planı düzenle")
    expect(page.locator(".layout-canvas .plan-seat")).to_have_count(48)


def test_normal_view_hides_internal_words(page):
    room = make_room("PLAN-UI SALONU")
    open_classroom(page, room["name"])
    expect(page.get_by_test_id("plan-status")).to_be_visible()
    visible = page.evaluate("""() => {
        const root = document.querySelector('.classroom-manager').cloneNode(true)
        root.querySelectorAll('[data-testid=classroom-advanced]').forEach((node) => node.remove())
        return root.innerText.toLowerCase()
    }""")
    for word in ("sürüm", "şablon", "kopyala ve düzenle", "aktif yap", " v1"):
        assert word not in visible, word


def test_classroom_without_a_plan_offers_to_create_one(page):
    requests.post(api("/classrooms"), json={"name": "PLANSIZ SALON"}, timeout=30)
    open_classroom(page, "PLANSIZ SALON")
    expect(page.get_by_test_id("plan-empty")).to_be_visible()
    expect(page.get_by_test_id("plan-empty").get_by_role("button", name="Planı oluştur")).to_be_visible()


def test_plan_is_edited_directly_and_the_effect_on_draft_exams_is_announced(page):
    room = make_room("PLAN-UI DÜZENLEME SALONU")
    make_exam("PLAN-UI TASLAK SINAV", layout_ids=[room["layout_id"]], group_limit=2)
    open_classroom(page, room["name"])
    page.get_by_test_id("plan-edit-btn").click()
    seat = page.locator(".layout-canvas .plan-seat").first
    seat.click()
    expect(page.get_by_test_id("notification").filter(has_text="taslak sınav")).to_contain_text(
        "1 taslak sınav yeni planı kullanacak")
    expect(page.get_by_test_id("plan-status")).to_contain_text("47 koltuk")
    # Aynı plan yerinde değişti; ikinci bir plan oluşmadı.
    layouts = requests.get(api(f"/classrooms/{room['classroom_id']}/layouts"), timeout=30).json()["layouts"]
    assert len(layouts) == 1
    seat.click()   # geri aç: diğer testler için 48 koltuk kalsın
    expect(page.get_by_test_id("plan-status")).to_contain_text("48 koltuk")
    page.get_by_test_id("plan-edit-btn").click()
    expect(page.get_by_test_id("notification").filter(has_text="Plan kaydedildi")).to_be_visible()


def test_other_plans_live_under_advanced(page):
    room = make_room("PLAN-UI SALONU")
    open_classroom(page, room["name"])
    advanced = page.get_by_test_id("classroom-advanced")
    expect(advanced.locator(".layout-list")).not_to_be_visible()
    advanced.locator("summary").click()
    expect(advanced.locator(".layout-list li")).to_have_count(1)


def test_activating_another_plan_switches_the_view_and_says_what_changed(page):
    room = make_room("PLAN-UI AKTİF SALONU")
    year = requests.get(api("/academic-years"), timeout=30).json()["selected_academic_year_id"]
    layouts = requests.get(api(f"/classrooms/{room['classroom_id']}/layouts"), timeout=30).json()["layouts"]
    if len(layouts) == 1:
        second = requests.post(api(f"/classrooms/{room['classroom_id']}/layouts"), timeout=30,
                               json={"name": "Küçük plan", "academic_year_id": year}).json()["layout"]
        requests.post(api(f"/classrooms/{room['classroom_id']}/layouts/{second['id']}/generate"), timeout=60,
                      json={"columns": 2, "column_lengths": [2, 2], "cell_seats": [[2, 2], [2, 2]],
                            "aisle_after": [True]})
    make_exam("PLAN-UI AKTİF TASLAK", layout_ids=[room["layout_id"]], group_limit=1)
    open_classroom(page, room["name"])
    expect(page.get_by_test_id("plan-status")).to_contain_text("48 koltuk")
    page.get_by_test_id("classroom-advanced").locator("summary").click()
    page.locator("[data-testid^=layout-activate-]").first.click()
    expect(page.get_by_test_id("plan-status")).to_contain_text("8 koltuk")
    expect(page.get_by_test_id("notification").filter(has_text="aktif")).to_contain_text("taslak sınav")
    # geri al: diğer testler için büyük plan aktif kalsın
    page.locator("[data-testid^=layout-activate-]").first.click()
    expect(page.get_by_test_id("plan-status")).to_contain_text("48 koltuk")
