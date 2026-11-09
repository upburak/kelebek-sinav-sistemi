# E2E API regression (public URL) for: pinned redistribution, finalize, edit locks (Karar 40),
# student changes (Karar 39), report header/title/scale, complete/archive + copy (Karar 68-70).
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)
API = f"{BASE_URL}/api"
TAB_A = "tab-TEST-A-" + uuid.uuid4().hex[:8]
TAB_B = "tab-TEST-B-" + uuid.uuid4().hex[:8]

state: dict = {}


def hdr(tab=None):
    return {"X-Kelebek-Tab": tab} if tab else {}


@pytest.fixture(scope="module")
def year_id():
    r = requests.get(f"{API}/academic-years", timeout=20)
    assert r.status_code == 200
    return r.json()["selected_academic_year_id"]


@pytest.fixture(scope="module")
def org(year_id):
    groups = requests.get(f"{API}/student-groups", params={"academic_year_id": year_id}, timeout=20).json()["groups"]
    payload = {"academic_year_id": year_id, "name": f"TEST_API_{uuid.uuid4().hex[:6]}", "exam_date": "2026-03-15",
               "participant_groups": [{"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups]}
    r = requests.post(f"{API}/exam-organizations", json=payload, timeout=30)
    assert r.status_code == 201, r.text
    o = r.json()["organization"]
    rooms = requests.get(f"{API}/exam-room-options", params={"academic_year_id": year_id}, timeout=20).json()["rooms"]
    demo = [x for x in rooms if x["classroom_name"] in ("DEMO-101", "DEMO-102")]
    assert len(demo) == 2
    r = requests.put(f"{API}/exam-organizations/{o['id']}/classrooms", json={"layout_ids": [x["layout_id"] for x in demo]}, timeout=20)
    assert r.status_code == 200, r.text
    state["rooms"] = demo
    return {"id": o["id"], "year_id": year_id, "name": payload["name"]}


class TestPinnedAndFinalize:
    def test_first_candidate(self, org):
        r = requests.post(f"{API}/exam-organizations/{org['id']}/distribution-candidates", json={}, timeout=120)
        assert r.status_code == 201, r.text
        c = r.json()["candidate"]
        assert len(c["assignments"]) == 48
        assert c["summary"]["waiting_count"] == 0
        state["base"] = c

    def test_pin_all_rooms_rejected(self, org):
        base = state["base"]
        r = requests.post(f"{API}/exam-organizations/{org['id']}/distribution-candidates", json={
            "run_id": base["run_id"], "base_candidate_id": base["candidate_id"],
            "pinned_classroom_ids": [x["classroom_id"] for x in state["rooms"]]}, timeout=60)
        assert r.status_code == 409

    def test_pinned_without_base_rejected(self, org):
        r = requests.post(f"{API}/exam-organizations/{org['id']}/distribution-candidates", json={
            "pinned_classroom_ids": [state["rooms"][0]["classroom_id"]]}, timeout=30)
        assert r.status_code == 400

    def test_pin_one_room_keeps_seats(self, org):
        base = state["base"]
        pinned = state["rooms"][0]["classroom_id"]
        r = requests.post(f"{API}/exam-organizations/{org['id']}/distribution-candidates", json={
            "run_id": base["run_id"], "base_candidate_id": base["candidate_id"],
            "pinned_classroom_ids": [pinned]}, timeout=120)
        assert r.status_code == 201, r.text
        c = r.json()["candidate"]
        assert c["pinned_classroom_ids"] == [pinned]
        assert c["derived_from_candidate_id"] == base["candidate_id"]
        before = {a["participant_id"]: a["seat_id"] for a in base["assignments"] if a["classroom_id"] == pinned}
        after = {a["participant_id"]: a["seat_id"] for a in c["assignments"]}
        assert before and all(after[p] == s for p, s in before.items())
        assert c["summary"]["waiting_count"] == 0
        state["pinned"] = c

    def test_select_and_finalize(self, org):
        cid = state["pinned"]["candidate_id"]
        r = requests.put(f"{API}/exam-organizations/{org['id']}/selected-candidate", json={"candidate_id": cid}, timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{API}/exam-organizations/{org['id']}/finalize", json={"confirm": True, "physical_layouts_confirmed": True}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["organization"]["status"] == "completed"


class TestEditLocks:
    def _move(self, org, tab):
        c = state["pinned"]
        a = c["assignments"][0]
        free = [s for s in c["available_seats"] if s["seat_id"] not in {x["seat_id"] for x in c["assignments"]}]
        target = free[0]["seat_id"] if free else c["assignments"][1]["seat_id"]
        return requests.post(f"{API}/exam-organizations/{org['id']}/distribution-candidates/{c['candidate_id']}/moves",
                             json={"participant_id": a["participant_id"], "target_seat_id": target}, headers=hdr(tab), timeout=30)

    def test_invalid_tab_header_lock_endpoint(self, org):
        r = requests.post(f"{API}/exam-organizations/{org['id']}/edit-lock", json={}, headers=hdr("short"), timeout=20)
        assert r.status_code == 400

    def test_a_takes_lock(self, org):
        r = requests.post(f"{API}/exam-organizations/{org['id']}/edit-lock", json={}, headers=hdr(TAB_A), timeout=20)
        assert r.status_code == 200
        assert r.json()["locks"][org["id"]]["mine"] is True
        r = requests.get(f"{API}/edit-locks", headers=hdr(TAB_B), timeout=20)
        assert r.json()["locks"][org["id"]]["mine"] is False
        assert r.json()["ttl_seconds"] == 30

    def test_b_write_gets_423(self, org):
        r = self._move(org, TAB_B)
        assert r.status_code == 423
        assert r.json().get("edit_locked") is True
        r = requests.post(f"{API}/exam-organizations/{org['id']}/edit-lock", json={}, headers=hdr(TAB_B), timeout=20)
        assert r.status_code == 423

    def test_a_write_ok_and_undo(self, org):
        r = self._move(org, TAB_A)
        assert r.status_code == 201, r.text
        state["pinned"] = r.json()["candidate"]
        c = state["pinned"]
        r = requests.post(f"{API}/exam-organizations/{org['id']}/distribution-candidates/{c['candidate_id']}/history/undo", headers=hdr(TAB_A), timeout=30)
        assert r.status_code == 200, r.text
        state["pinned"] = r.json()["candidate"]

    def test_heartbeat_and_takeover(self, org):
        r = requests.post(f"{API}/edit-locks/heartbeat", headers=hdr(TAB_A), timeout=20)
        assert r.status_code == 200 and r.json()["locks"][org["id"]]["mine"] is True
        r = requests.post(f"{API}/exam-organizations/{org['id']}/edit-lock", json={"takeover": True}, headers=hdr(TAB_B), timeout=20)
        assert r.status_code == 200
        assert r.json()["locks"][org["id"]]["mine"] is True
        r = requests.get(f"{API}/edit-locks", headers=hdr(TAB_A), timeout=20)
        assert r.json()["locks"][org["id"]]["mine"] is False

    def test_release(self, org):
        r = requests.post(f"{API}/edit-locks/release", params={"tab": TAB_B}, timeout=20)
        assert r.status_code == 200 and r.json()["released"] is True
        r = requests.get(f"{API}/edit-locks", timeout=20)
        assert org["id"] not in r.json()["locks"]


class TestReports:
    def test_attendance_with_header_title_scale(self, org):
        r = requests.get(f"{API}/exam-organizations/{org['id']}/reports/attendance.pdf",
                         params={"header": "school,title,exam", "title": "TEST Başlık", "scale": "120"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith("application/pdf") and r.content[:4] == b"%PDF"

    def test_invalid_scale(self, org):
        r = requests.get(f"{API}/exam-organizations/{org['id']}/reports/attendance.pdf", params={"scale": "200"}, timeout=30)
        assert r.status_code == 400

    def test_invalid_header_part(self, org):
        r = requests.get(f"{API}/exam-organizations/{org['id']}/reports/room-students.pdf", params={"header": "bogus"}, timeout=30)
        assert r.status_code == 400

    def test_seating_plan_scale(self, org):
        r = requests.get(f"{API}/exam-organizations/{org['id']}/reports/seating-plan.pdf", params={"scale": "80", "title": "X"}, timeout=60)
        assert r.status_code == 200 and r.content[:4] == b"%PDF"


class TestStudentChanges:
    def test_none_then_change_and_apply(self, org):
        r = requests.get(f"{API}/exam-organizations/{org['id']}/student-changes", timeout=30)
        assert r.status_code == 200 and r.json()["changes"] == []
        students = requests.get(f"{API}/students", params={"academic_year_id": org["year_id"]}, timeout=20).json()["students"]
        s = next(x for x in students if x["school_number"] == "DEMO-003")
        state["student"] = s
        patch = {k: s[k] for k in ("school_number", "first_name", "last_name", "class_level", "section", "area") if s[k] is not None}
        patch.update({"academic_year_id": org["year_id"], "section": "B" if s["section"] == "A" else "A"})
        r = requests.patch(f"{API}/students/{s['id']}", json=patch, timeout=20)
        assert r.status_code == 200, r.text
        try:
            r = requests.get(f"{API}/exam-organizations/{org['id']}/student-changes", timeout=30)
            changes = r.json()["changes"]
            assert len(changes) == 1 and changes[0]["kind"] == "changed"
            assert changes[0]["changes"][0]["field"] == "section"
            pid = changes[0]["participant_id"]
            r = requests.post(f"{API}/exam-organizations/{org['id']}/student-changes/apply", json={"participant_ids": [pid]}, timeout=30)
            assert r.status_code == 400
            r = requests.post(f"{API}/exam-organizations/{org['id']}/student-changes/apply", json={"confirm": True, "participant_ids": ["nope"]}, timeout=30)
            assert r.status_code == 409
            r = requests.post(f"{API}/exam-organizations/{org['id']}/student-changes/apply", json={"confirm": True, "participant_ids": [pid]}, timeout=30)
            assert r.status_code == 200 and r.json()["applied"] == 1
            rv = requests.get(f"{API}/exam-organizations/{org['id']}/final-review", timeout=30)
            assert rv.status_code == 200 and rv.json()["review"]["unassigned_count"] == 1
            rp = requests.get(f"{API}/exam-organizations/{org['id']}/reports/attendance.pdf", timeout=30)
            assert rp.status_code == 409
            # re-seat the waiting student into a free seat
            cands = requests.get(f"{API}/exam-organizations/{org['id']}/distribution-candidates", timeout=30).json()["candidates"]
            c = next(x for x in cands if x["candidate_id"] == state["pinned"]["candidate_id"])
            used = {a["seat_id"] for a in c["assignments"] if a["seat_id"]}
            free = next(s for s in c["available_seats"] if s["seat_id"] not in used)
            r = requests.post(f"{API}/exam-organizations/{org['id']}/distribution-candidates/{c['candidate_id']}/moves",
                              json={"participant_id": pid, "target_seat_id": free["seat_id"]}, timeout=30)
            assert r.status_code == 201, r.text
            rp = requests.get(f"{API}/exam-organizations/{org['id']}/reports/attendance.pdf", timeout=60)
            assert rp.status_code == 200, rp.text[:200]
        finally:
            restore = {k: s[k] for k in ("school_number", "first_name", "last_name", "class_level", "section", "area") if s[k] is not None}
            restore["academic_year_id"] = org["year_id"]
            requests.patch(f"{API}/students/{s['id']}", json=restore, timeout=20)


class TestArchiveCopy:
    def test_complete_requires_confirm(self, org):
        r = requests.post(f"{API}/exam-organizations/{org['id']}/complete", json={}, timeout=20)
        assert r.status_code == 400

    def test_complete_and_read_only(self, org):
        r = requests.post(f"{API}/exam-organizations/{org['id']}/complete", json={"confirm": True}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["organization"]["archived_at"]
        c = state["pinned"]
        r = requests.post(f"{API}/exam-organizations/{org['id']}/distribution-candidates/{c['candidate_id']}/moves",
                          json={"participant_id": c["assignments"][0]["participant_id"], "target_seat_id": None}, timeout=30)
        assert r.status_code == 403
        r = requests.post(f"{API}/exam-organizations/{org['id']}/complete", json={"confirm": True}, timeout=30)
        assert r.status_code == 403
        # reports still readable
        r = requests.get(f"{API}/exam-organizations/{org['id']}/reports/attendance.pdf", timeout=60)
        assert r.status_code == 200

    def test_copy(self, org):
        r = requests.post(f"{API}/exam-organizations/{org['id']}/copy", json={"name": "", "exam_date": "2026-04-01"}, timeout=30)
        assert r.status_code == 400
        r = requests.post(f"{API}/exam-organizations/{org['id']}/copy", json={"name": "TEST_copy", "exam_date": "bad"}, timeout=30)
        assert r.status_code == 400
        r = requests.post(f"{API}/exam-organizations/{org['id']}/copy", json={"name": f"{org['name']} kopya", "exam_date": "2026-04-01"}, timeout=30)
        assert r.status_code == 201, r.text
        data = r.json()
        copy = data["organization"]
        assert copy["status"] == "draft" and data["skipped_students"] == 0 and data["skipped_rooms"] == 0
        assert len(copy["room_selections"]) == 2
        orgs = requests.get(f"{API}/exam-organizations", params={"academic_year_id": org["year_id"]}, timeout=20).json()["organizations"]
        src = next(o for o in orgs if o["id"] == org["id"])
        assert src["status"] == "completed" and src["archived_at"]
        print("copy org keys:", sorted(copy.keys()))
