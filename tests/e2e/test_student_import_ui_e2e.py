"""Öğrenci listesi içe aktarma akışının arayüzde sonuna kadar çalışması.

Gerileme: arka uç fark raporunu (`diff`) yanıtın en üst düzeyinde döndürüyor,
arayüz ise onu `validation` nesnesinin içinde arıyordu. `as` tip dönüşümü
uyumsuzluğu derleyiciden gizlediği için hata sessizdi: dosya okunuyor, kontrol
raporu çıkıyor, ama **"İçe aktarmayı onayla" düğmesi hiç görünmüyordu** —
yani Excel'den öğrenci listesi hiç içe aktarılamıyordu.

API testleri bu hatayı göremez; uçları tek tek doğru yanıt veriyordu. Bu yüzden
test gerçek tarayıcıda akışı tıklar. Playwright kurulu değilse atlanır. Tarayıcı ikilisi standart yerde değilse
``KELEBEK_CHROMIUM`` ortam değişkeniyle yolu verilebilir.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)

sync_playwright = pytest.importorskip(
    "playwright.sync_api", reason="Playwright kurulu değil; arayüz testi atlanıyor."
).sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "frontend" / "public" / "downloads" / "kelebek_sentetik_demo_48_ogrenci.xlsx"


@pytest.fixture(scope="module")
def page():
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        pytest.skip("Arayüz derlenmemiş (frontend/dist yok).")
    if requests.get(BASE_URL, timeout=20).headers.get("content-type", "").find("html") < 0:
        pytest.skip("Bu adres derlenmiş arayüzü sunmuyor.")
    with sync_playwright() as playwright:
        browser = None
        for options in ({}, {"executable_path": os.environ.get("KELEBEK_CHROMIUM", "")}):
            if "executable_path" in options and not options["executable_path"]:
                continue
            try:
                browser = playwright.chromium.launch(**options)
                break
            except Exception as error:  # tarayıcı indirilmemiş olabilir
                last_error = error
        if browser is None:
            pytest.skip(f"Chromium başlatılamadı: {last_error}")
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        tab = context.new_page()
        tab.on("dialog", lambda dialog: dialog.accept())
        yield tab
        context.close()
        browser.close()


def test_import_flow_reaches_the_confirm_button(page):
    assert SAMPLE.is_file(), f"Sentetik örnek dosya yok: {SAMPLE}"
    page.goto(BASE_URL, wait_until="networkidle")

    page.set_input_files("#student-import input[type=file]", str(SAMPLE))
    page.locator("#import-preview-title").wait_for(timeout=30_000)

    validate = page.locator("button.validate-import")
    assert validate.is_enabled(), "Eşleştirme tamamken kontrol düğmesi kapalı kaldı."
    validate.click()

    page.locator(".validation-report").first.wait_for(timeout=30_000)

    # Asıl gerileme noktası: fark raporu ve ona bağlı onay düğmesi görünmeli.
    commit = page.locator("button.commit-import")
    commit.wait_for(timeout=20_000)
    assert commit.is_enabled(), "İçe aktarma onay düğmesi görünür ama kapalı."
