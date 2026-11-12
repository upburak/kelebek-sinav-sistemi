"""Tarayıcı testleri için ortak yardımcılar."""

from __future__ import annotations

import os

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")


def open_app(page, section: str | None = None):
    """Uygulamayı aç, varsa "Yenilikler" penceresini kapat, istenen bölüme geç."""
    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid=dashboard]")
    closer = page.locator(".whats-new-backdrop button").last
    if closer.count() and closer.is_visible():
        closer.click()
    if section:
        page.locator("nav button", has_text=section).click()
