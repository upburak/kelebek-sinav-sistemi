"""Yedek alma ve geri yükleme önizlemesi arayüzde sonuna kadar çalışmalı.

Yedek paketi indirilir, aynı paket geri yükleme alanına verilir ve güvenli
önizlemenin doğrulama sonucunu gösterdiği kontrol edilir. Geri yükleme
onaylanmaz; önizleme iptal edilir ki diğer testlerin verisi değişmesin.
"""

from __future__ import annotations

import os

import pytest

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)


def test_backup_can_be_downloaded_and_previewed_for_restore(page, tmp_path):
    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid=dashboard]")
    closer = page.locator(".whats-new-backdrop button").last
    if closer.count() and closer.is_visible():
        closer.click()
    page.locator("nav button", has_text="Yedek ve arşiv").click()

    with page.expect_download(timeout=60_000) as download_info:
        page.get_by_role("button", name="Yedek paketini oluştur ve indir").click()
    package = tmp_path / download_info.value.suggested_filename
    download_info.value.save_as(package)
    assert package.suffix == ".zip" and package.stat().st_size > 1000

    page.set_input_files("input[type=file]", str(package))
    page.get_by_role("button", name="Yedeği doğrula ve önizle").click()
    page.get_by_text("Güvenli önizleme").wait_for(timeout=30_000)
    page.get_by_text("SHA-256 doğrulandı").wait_for()
    # Onay kutusu işaretlenmeden geri yükleme başlatılamamalı.
    assert page.get_by_role("button", name="Geri yüklemeyi son kez onayla").is_disabled()

    page.get_by_role("button", name="Önizlemeyi iptal et").click()
    page.get_by_text("Güvenli önizleme").wait_for(state="hidden")
