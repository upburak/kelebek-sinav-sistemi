"""Sınav hazırlığı arayüzde adım adım, dört tıkla tamamlanabilmeli.

Gerileme: sınav kartında derslik seçimi, kurallar, aday üretme, sabitleme,
"incelemeye al" ve "son kontrol" aynı anda görünüyordu; hangisinin sıradaki
adım olduğu belli değildi. Kart artık tek bir "sıradaki adım" ve tek ana düğme
gösterir. Bu test o yolu gerçek tarayıcıda yürür: oluştur → dağıt → kontrol →
kesinleştir → raporlar.
"""

from __future__ import annotations

import os

import pytest

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)

EXAM_NAME = "REHBER AKIŞ SINAVI"


def test_exam_is_prepared_by_following_the_single_next_step(page):
    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid=dashboard]")
    closer = page.locator("[data-testid=whats-new-close]")
    if closer.count() and closer.is_visible():
        closer.click()
    page.locator("nav button", has_text="Sınav organizasyonlar").click()

    # 1) Sınavı oluştur: derslikler kendiliğinden seçilmeli.
    page.get_by_test_id("exam-new-btn").click()
    form = page.locator(".exam-create-form")
    form.locator('input[maxlength="160"]').fill(EXAM_NAME)
    form.locator("input[type=date]").fill("2026-12-17")
    boxes = form.locator(".exam-general-groups input[type=checkbox]")
    for index in range(boxes.count()):
        boxes.nth(index).check()
    page.get_by_test_id("exam-create-submit").click()

    card = page.locator("[data-testid^=exam-card-]", has_text=EXAM_NAME)
    title = card.locator("[data-testid^=exam-guide-title-]")
    title.get_by_text("Öğrencileri dersliklere dağıt").wait_for(timeout=20_000)
    assert "kendiliğinden seçildi" in page.get_by_test_id("exam-notice").inner_text()
    # Sıradaki adımda tek ana düğme görünür.
    assert card.locator(".exam-guide-primary").count() == 1

    # 2) Dağıt: sonuç kendiliğinden geçerli dağıtım olur ve kroki açılır.
    card.locator("[data-testid^=candidate-create-]").click()
    result = card.locator("[data-testid^=candidate-result-]")
    result.wait_for(timeout=90_000)
    assert "kural ihlali yok" in result.inner_text()
    title.get_by_text("Dağıtım hazır, kural ihlali yok").wait_for()
    # Kroki derslik derslik gezilir; aynı anda tek derslik görünür.
    tabs = card.locator(".plan-room-tabs button")
    assert tabs.count() >= 2
    assert card.locator(".candidate-plan-room").count() == 1
    tabs.nth(1).click()
    assert card.locator(".candidate-plan-heading strong").inner_text() == tabs.nth(1).inner_text()

    # 3) Kontrol et ve kesinleştir.
    card.locator("[data-testid^=final-review-open-]").click()
    title.get_by_text("Son kontrol").wait_for()
    page.get_by_test_id("finalize-confirm-checkbox").check()
    page.get_by_test_id("finalize-submit-btn").click()
    title.get_by_text("Sınav kesinleşti").wait_for(timeout=30_000)

    # 4) Raporlar: kesinleşince sınav sayfasının son adımı olarak doğrudan açılır.
    step = page.get_by_test_id("exam-reports-step")
    step.wait_for(timeout=30_000)
    step.get_by_text("PDF raporları").wait_for()


def test_only_the_participating_classes_rooms_are_preselected(page):
    """İki sınıf seçilince bütün derslikler değil, yalnızca o iki sınıfın dersliği gelmeli.

    Gerileme (0.5.0): derslikler kendiliğinden seçilirken sınava kaç sınıfın
    girdiğine bakılmıyor, koltuk yetiyorsa okulun bütün derslikleri seçiliyordu.
    """
    import requests

    api = f"{BASE_URL}/api"
    year = requests.get(f"{api}/academic-years", timeout=30).json()["selected_academic_year_id"]
    groups = requests.get(f"{api}/student-groups", params={"academic_year_id": year}, timeout=30).json()["groups"][:2]
    room_names = [f"{group['class_level']}-{group['section']} Derslik" for group in groups]
    # İçe aktarmanın kurduğu gibi, her sınıfın kendi adını taşıyan dersliği.
    for name, group in zip(room_names, groups, strict=True):
        created = requests.post(f"{api}/classrooms", json={"name": name}, timeout=30)
        if created.status_code == 409:
            continue
        assert created.status_code == 201, created.text
        classroom_id = created.json()["classroom"]["id"]
        layout = requests.post(f"{api}/classrooms/{classroom_id}/layouts", timeout=30,
                               json={"name": "Sınıf düzeni", "academic_year_id": year}).json()["layout"]
        rows = (group["student_count"] + 3) // 4
        generated = requests.post(
            f"{api}/classrooms/{classroom_id}/layouts/{layout['id']}/generate", timeout=60,
            json={"columns": 2, "column_lengths": [rows, rows], "cell_seats": [[2] * rows, [2] * rows],
                  "aisle_after": [True]})
        assert generated.status_code in (200, 201), generated.text

    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid=dashboard]")
    closer = page.locator("[data-testid=whats-new-close]")
    if closer.count() and closer.is_visible():
        closer.click()
    page.locator("nav button", has_text="Sınav organizasyonlar").click()
    page.get_by_test_id("exam-new-btn").click()
    form = page.locator(".exam-create-form")
    form.locator('input[maxlength="160"]').fill("İKİ SINIFLI SINAV")
    form.locator("input[type=date]").fill("2026-12-18")
    for group in groups:
        label = f"{group['class_level']}/{group['section']}"
        form.locator(".exam-general-groups label", has_text=label).first.locator("input").check()
    page.get_by_test_id("exam-create-submit").click()

    card = page.locator("[data-testid^=exam-card-]", has_text="İKİ SINIFLI SINAV")
    card.locator("[data-testid^=exam-guide-title-]").get_by_text("Öğrencileri dersliklere dağıt").wait_for(timeout=20_000)
    organizations = requests.get(f"{api}/exam-organizations", params={"academic_year_id": year},
                                 timeout=30).json()["organizations"]
    exam = next(item for item in organizations if item["name"] == "İKİ SINIFLI SINAV")
    selected = sorted(room["classroom_name"] for room in exam["room_selections"])
    assert selected == sorted(room_names), selected
    notice = page.get_by_test_id("exam-notice").inner_text()
    assert all(name in notice for name in room_names), notice
