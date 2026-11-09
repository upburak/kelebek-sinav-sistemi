# E2E API (public URL) for iteration 4: "Tümünü düzelt" (fix-violations) and "Yenilikler" (whats-new).
import json
import os
import uuid
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)
API = f"{BASE_URL}/api"
UI_STATE = Path("/root/.local/share/kelebek-sinav-sistemi/ui_state.json")
state: dict = {}


def _affected(violations):
    return {v["first_participant_id"] for v in violations} | {v["second_participant_id"] for v in violations}


def make_violation(org, cand):
    """Move a same-section student next to someone (via moves endpoint); returns child candidate."""
    used = state.setdefault("used_pids", set())
    for room in cand["plan"]:
        for desk in room["desks"]:
            occ = [s for s in desk["seats"] if s["student"] and s["student"]["participant_id"] not in used]
            empty = [s for s in desk["seats"] if not s["student"] and s["is_available"]]
            if not (occ and empty):
                continue
            neighbour = occ[0]["student"]
            mover = next((a for a in cand["assignments"] if a["section"] == neighbour["section"]
                          and a["class_level"] == neighbour["class_level"]
                          and a["participant_id"] != neighbour["participant_id"]
                          and a["participant_id"] not in used), None)
            if mover is None:
                continue
            r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{cand['candidate_id']}/moves",
                              json={"participant_id": mover["participant_id"], "target_seat_id": empty[0]["seat_id"]}, timeout=60)
            assert r.status_code == 201, r.text
            used.update({mover["participant_id"], neighbour["participant_id"]})
            return r.json()["candidate"]
    raise AssertionError("no slot for violation")


@pytest.fixture(scope="module")
def org():
    year_id = requests.get(f"{API}/academic-years", timeout=20).json()["selected_academic_year_id"]
    groups = requests.get(f"{API}/student-groups", params={"academic_year_id": year_id}, timeout=20).json()["groups"]
    payload = {"academic_year_id": year_id, "name": f"TEST_FIX_{uuid.uuid4().hex[:6]}", "exam_date": "2026-03-18",
               "participant_groups": [{"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups]}
    r = requests.post(f"{API}/exam-organizations", json=payload, timeout=30)
    assert r.status_code == 201, r.text
    o = r.json()["organization"]
    rooms = requests.get(f"{API}/exam-room-options", params={"academic_year_id": year_id}, timeout=20).json()["rooms"]
    demo = [x for x in rooms if x["classroom_name"] in ("DEMO-101", "DEMO-102")]
    r = requests.put(f"{API}/exam-organizations/{o['id']}/classrooms", json={"layout_ids": [x["layout_id"] for x in demo]}, timeout=20)
    assert r.status_code == 200, r.text
    return o["id"]


class TestFixAll:
    def test_setup_two_violations(self, org):
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates", json={}, timeout=120)
        assert r.status_code == 201, r.text
        c1 = r.json()["candidate"]
        state["c1"] = c1
        r = requests.put(f"{API}/exam-organizations/{org}/selected-candidate", json={"candidate_id": c1["candidate_id"]}, timeout=20)
        assert r.status_code == 200, r.text
        child1 = make_violation(org, c1)
        child2 = make_violation(org, child1)
        state["child1"], state["child2"] = child1, child2
        assert len(child2["violations"]) >= 2, child2["violations"]
        assert len(_affected(child2["violations"])) >= 4

    def test_fix_non_selected_409(self, org):
        cid = state["child1"]["candidate_id"]
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{cid}/fix-violations", json={}, timeout=60)
        assert r.status_code == 409, r.text
        assert r.json()["error"] == "Önce bu adayı incelemeye alın."

    def test_fix_all(self, org):
        child2 = state["child2"]
        before = len(_affected(child2["violations"]))
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{child2['candidate_id']}/fix-violations", json={}, timeout=120)
        assert r.status_code == 201, r.text
        c = r.json()["candidate"]
        state["fixed"] = c
        fs = c["fix_summary"]
        print("fix_summary", fs, "violations after", len(c["violations"]))
        assert fs["moved"] >= 1
        assert fs["affected_before"] == before
        assert fs["affected_after"] < fs["affected_before"]
        assert fs["affected_after"] == len(_affected(c["violations"]))
        assert c["status"] == "manual"
        assert c["candidate_id"] != child2["candidate_id"]
        # all students still seated / count preserved
        assert len(c["assignments"]) == len(child2["assignments"])
        seats = [a["seat_id"] for a in c["assignments"] if a.get("seat_id")]
        assert len(seats) == len(set(seats)), "duplicate seat"

    def test_fixed_candidate_selected_and_persisted(self, org):
        orgs = requests.get(f"{API}/exam-organizations", params={"academic_year_id": requests.get(f"{API}/academic-years").json()["selected_academic_year_id"]}, timeout=20).json()["organizations"]
        o = next(x for x in orgs if x["id"] == org)
        assert o["selected_candidate_id"] == state["fixed"]["candidate_id"]
        r = requests.get(f"{API}/exam-organizations/{org}/distribution-candidates", timeout=60)
        assert r.status_code == 200
        cands = r.json()["candidates"]
        got = next(x for x in cands if x["candidate_id"] == state["fixed"]["candidate_id"])
        assert len(_affected(got["violations"])) == state["fixed"]["fix_summary"]["affected_after"]
        old = next(x for x in cands if x["candidate_id"] == state["child2"]["candidate_id"])
        assert len(old["violations"]) == len(state["child2"]["violations"]), "parent mutated"

    def test_fix_without_violations_409(self, org):
        c = state["fixed"]
        if c["violations"]:
            pytest.skip("fixed candidate still has violations")
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{c['candidate_id']}/fix-violations", json={}, timeout=60)
        assert r.status_code == 409, r.text
        assert r.json()["error"] == "Bu adayda düzeltilecek komşuluk ihlali yok."

    def test_fix_unknown_404(self, org):
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/nope/fix-violations", json={}, timeout=30)
        assert r.status_code == 404


class TestWhatsNew:
    def test_show_after_update(self):
        original = UI_STATE.read_text(encoding="utf-8") if UI_STATE.exists() else None
        try:
            UI_STATE.write_text(json.dumps({"last_seen_version": "0.1.0"}), encoding="utf-8")
            d = requests.get(f"{API}/app/whats-new", timeout=20).json()
            assert d["show"] is True
            assert d["current_version"] == "0.2.0"
            assert d["previous_version"] == "0.1.0"
            assert [n["version"] for n in d["notes"]] == ["0.2.0"]
            assert any("Tümünü düzelt" in i for i in d["notes"][0]["items"])
            r = requests.post(f"{API}/app/whats-new/seen", timeout=20)
            assert r.status_code == 200 and r.json()["seen"] == "0.2.0"
            assert json.loads(UI_STATE.read_text())["last_seen_version"] == "0.2.0"
            d = requests.get(f"{API}/app/whats-new", timeout=20).json()
            assert d["show"] is False and d["notes"] == []
        finally:
            UI_STATE.write_text(json.dumps({"last_seen_version": "0.2.0"}), encoding="utf-8")

    def test_fresh_install_no_show(self):
        UI_STATE.write_text(json.dumps({"other": 1}), encoding="utf-8")
        try:
            d = requests.get(f"{API}/app/whats-new", timeout=20).json()
            assert d["show"] is False
            st = json.loads(UI_STATE.read_text())
            assert st["last_seen_version"] == "0.2.0" and st["other"] == 1
        finally:
            UI_STATE.write_text(json.dumps({"last_seen_version": "0.2.0"}), encoding="utf-8")

    def test_corrupt_file(self):
        UI_STATE.write_text("{not json", encoding="utf-8")
        try:
            r = requests.get(f"{API}/app/whats-new", timeout=20)
            assert r.status_code == 200 and r.json()["show"] is False
        finally:
            UI_STATE.write_text(json.dumps({"last_seen_version": "0.2.0"}), encoding="utf-8")
