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


def api(path: str) -> str:
    return f"{BASE_URL}/api{path}"


def current_year_id() -> str:
    import requests

    return requests.get(api("/academic-years"), timeout=30).json()["selected_academic_year_id"]


def make_room(name: str, rows: int = 6, columns: int = 4) -> dict:
    """Sentetik derslik + plan kur (varsayılan 48 koltuk). Zaten varsa mevcut olanı döndür."""
    import requests

    year = current_year_id()
    created = requests.post(api("/classrooms"), json={"name": name}, timeout=30)
    if created.status_code == 409:
        room = next(item for item in requests.get(api("/classrooms"), timeout=30).json()["classrooms"]
                    if item["name"] == name)
        plan = requests.get(api(f"/classrooms/{room['id']}/plan"), params={"academic_year_id": year},
                            timeout=30).json()["plan"]
        return {"classroom_id": room["id"], "layout_id": plan["layout"]["id"], "name": name}
    assert created.status_code == 201, created.text
    classroom_id = created.json()["classroom"]["id"]
    layout = requests.post(api(f"/classrooms/{classroom_id}/layouts"), timeout=30,
                           json={"name": "Sınıf planı", "academic_year_id": year}).json()["layout"]
    generated = requests.post(
        api(f"/classrooms/{classroom_id}/layouts/{layout['id']}/generate"), timeout=60,
        json={"columns": columns, "column_lengths": [rows] * columns,
              "cell_seats": [[2] * rows for _ in range(columns)], "aisle_after": [True] * (columns - 1)})
    assert generated.status_code in (200, 201), generated.text
    return {"classroom_id": classroom_id, "layout_id": layout["id"], "name": name}


def make_exam(name: str, layout_ids: list[str] | None = None, group_limit: int | None = None) -> str:
    """Sentetik sınav oluştur; istenirse derslikleri seç."""
    import requests

    year = current_year_id()
    groups = requests.get(api("/student-groups"), params={"academic_year_id": year}, timeout=30).json()["groups"]
    if group_limit:
        groups = groups[:group_limit]
    period = requests.get(api("/exam-periods"), params={"academic_year_id": year}, timeout=30).json()["periods"][0]
    created = requests.post(api("/exam-organizations"), timeout=30, json={
        "academic_year_id": year, "name": name, "exam_date": "2026-12-22", "exam_period_id": period["id"],
        "participant_groups": [{"class_level": g["class_level"], "section": g["section"], "area": g["area"] or ""}
                               for g in groups]})
    assert created.status_code == 201, created.text
    exam_id = created.json()["organization"]["id"]
    if layout_ids is not None:
        saved = requests.put(api(f"/exam-organizations/{exam_id}/classrooms"), json={"layout_ids": layout_ids},
                             timeout=30)
        assert saved.status_code == 200, saved.text
    return exam_id


def distribute(exam_id: str) -> str:
    import requests

    response = requests.post(api(f"/exam-organizations/{exam_id}/distribution-candidates"), json={}, timeout=120)
    assert response.status_code == 201, response.text
    candidate_id = response.json()["candidate"]["candidate_id"]
    chosen = requests.put(api(f"/exam-organizations/{exam_id}/selected-candidate"),
                          json={"candidate_id": candidate_id}, timeout=30)
    assert chosen.status_code == 200, chosen.text
    return candidate_id


def finalize(exam_id: str) -> None:
    import requests

    response = requests.post(api(f"/exam-organizations/{exam_id}/finalize"),
                             json={"confirm": True, "physical_layouts_confirmed": True}, timeout=60)
    assert response.status_code == 200, response.text
