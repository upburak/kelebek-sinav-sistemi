"""Sürüm denetimi bölümü arayüzde görünmeli ve açılış denetimi ayarı kalıcı olmalı.

Ağ sonucu ortama göre değişir (internet yok, depo gizli, güncel); bu yüzden
yalnızca ağdan bağımsız davranış sınanır.
"""

from __future__ import annotations

import os

import pytest
import requests

expect = pytest.importorskip("playwright.sync_api").expect

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)


def _open_backup(page):
    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid=dashboard]")
    closer = page.locator("[data-testid=whats-new-close]")
    if closer.count() and closer.is_visible():
        closer.click()
    page.locator("nav button", has_text="Yedek ve arşiv").click()
    page.get_by_test_id("online-update").wait_for()


def test_update_section_shows_status_and_remembers_the_startup_setting(page):
    try:
        _open_backup(page)
        page.get_by_test_id("online-update-check").wait_for()
        assert page.get_by_test_id("online-update-status").inner_text().strip()

        toggle = page.get_by_test_id("online-update-auto")
        expect(toggle).to_be_enabled()
        expect(toggle).to_be_checked()
        toggle.uncheck()
        page.wait_for_timeout(400)
        # Ayar kapalıyken açılış denetimi internete çıkmaz.
        data = requests.get(f"{BASE_URL}/api/updates/online", params={"auto": "1"}, timeout=30).json()
        assert data == {"checked": False, "auto_check": False, "current_version": data["current_version"]}

        _open_backup(page)
        # Kutu, yerel ayar okunana kadar kapalıdır; okununca doğru durumu gösterir.
        expect(page.get_by_test_id("online-update-auto")).to_be_enabled()
        expect(page.get_by_test_id("online-update-auto")).not_to_be_checked()
    finally:
        requests.put(f"{BASE_URL}/api/updates/online/settings", json={"auto_check": True}, timeout=30)
