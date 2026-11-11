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
    closer = page.locator(".whats-new-backdrop button").last
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

    # 4) Raporlar.
    card.locator("[data-testid^=exam-reports-]").click()
    page.get_by_text("Sınav raporları").wait_for()
