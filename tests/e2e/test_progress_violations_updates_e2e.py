# E2E API regression (public URL) for: distribution progress + stop (Karar 58),
# violation details on candidates (ihlal krokisi), app update API (status/inspect/apply).
import io
import os
import threading
import time
import uuid
import zipfile

import pytest
import requests

BASE_URL = os.environ.get("KELEBEK_PUBLIC_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("KELEBEK_PUBLIC_URL not set", allow_module_level=True)
API = f"{BASE_URL}/api"
state: dict = {}


@pytest.fixture(scope="module")
def org():
    year_id = requests.get(f"{API}/academic-years", timeout=20).json()["selected_academic_year_id"]
    groups = requests.get(f"{API}/student-groups", params={"academic_year_id": year_id}, timeout=20).json()["groups"]
    payload = {"academic_year_id": year_id, "name": f"TEST_PROG_{uuid.uuid4().hex[:6]}", "exam_date": "2026-03-16",
               "participant_groups": [{"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups]}
    r = requests.post(f"{API}/exam-organizations", json=payload, timeout=30)
    assert r.status_code == 201, r.text
    o = r.json()["organization"]
    rooms = requests.get(f"{API}/exam-room-options", params={"academic_year_id": year_id}, timeout=20).json()["rooms"]
    demo = [x for x in rooms if x["classroom_name"] in ("DEMO-101", "DEMO-102")]
    r = requests.put(f"{API}/exam-organizations/{o['id']}/classrooms", json={"layout_ids": [x["layout_id"] for x in demo]}, timeout=20)
    assert r.status_code == 200, r.text
    return o["id"]


def _create_in_thread(org_id, payload=None):
    box = {}

    def run():
        box["resp"] = requests.post(f"{API}/exam-organizations/{org_id}/distribution-candidates", json=payload or {}, timeout=120)
    t = threading.Thread(target=run)
    t.start()
    return t, box


# Progress endpoints
class TestProgress:
    def test_progress_idle(self, org):
        r = requests.get(f"{API}/exam-organizations/{org}/distribution-progress", timeout=10)
        assert r.status_code == 200 and r.json()["progress"] is None

    def test_stop_idle_409(self, org):
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-progress/stop", timeout=10)
        assert r.status_code == 409 and "error" in r.json()

    def test_progress_while_solving_not_blocked(self, org):
        t, box = _create_in_thread(org)
        snaps = []
        deadline = time.time() + 30
        while t.is_alive() and time.time() < deadline:
            t0 = time.time()
            r = requests.get(f"{API}/exam-organizations/{org}/distribution-progress", timeout=5)
            assert r.status_code == 200
            assert time.time() - t0 < 3, "progress endpoint blocked by solve"
            p = r.json()["progress"]
            if p and p["active"]:
                snaps.append(p)
            time.sleep(0.3)
        t.join(60)
        assert box["resp"].status_code == 201, box["resp"].text
        c = box["resp"].json()["candidate"]
        state["c1"] = c
        assert len(c["assignments"]) == 48
        assert snaps, "no active progress snapshot observed"
        stages = {s["stage"] for s in snaps}
        assert "search" in stages, stages
        s = snaps[-1]
        assert [x["key"] for x in s["steps"]] == ["prepare", "model", "search", "save"]
        assert s["time_limit_seconds"] == 12.0
        search = [x for x in snaps if x["stage"] == "search"]
        assert search[0]["remaining_max_seconds"] is not None
        # final snapshot is finished
        p = requests.get(f"{API}/exam-organizations/{org}/distribution-progress", timeout=5).json()["progress"]
        assert p["active"] is False and p["outcome"] == "created"
        print("snapshots:", len(snaps), "stages:", stages, "last:", s)

    def test_concurrent_create_409(self, org):
        c1 = state["c1"]
        t, box = _create_in_thread(org, {"run_id": c1["run_id"]})
        time.sleep(0.6)
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates", json={"run_id": c1["run_id"]}, timeout=60)
        t.join(60)
        # second request is either serialized by global lock (then 201) or rejected 409
        print("concurrent second:", r.status_code, r.text[:120])
        assert r.status_code in (201, 409)
        assert box["resp"].status_code == 201

    def test_stop_during_search(self, org):
        c1 = state["c1"]
        t, box = _create_in_thread(org, {"run_id": c1["run_id"]})
        stopped = None
        deadline = time.time() + 20
        while time.time() < deadline:
            p = requests.get(f"{API}/exam-organizations/{org}/distribution-progress", timeout=5).json()["progress"]
            if p and p["active"] and p["stage"] == "search":
                r = requests.post(f"{API}/exam-organizations/{org}/distribution-progress/stop", timeout=5)
                assert r.status_code == 200, r.text
                stopped = r.json()["progress"]
                break
            time.sleep(0.15)
        t.join(60)
        assert stopped is not None and stopped["stop_requested"] is True
        resp = box["resp"]
        print("stop result:", resp.status_code, resp.text[:200])
        if resp.status_code == 201:
            assert resp.json()["candidate"]["stopped_early"] is True
        else:
            assert resp.status_code == 409
            assert "Dağıtım durduruldu" in resp.json()["error"]
        p = requests.get(f"{API}/exam-organizations/{org}/distribution-progress", timeout=5).json()["progress"]
        assert p["active"] is False
        assert p["outcome"] in ("stopped", "error")

    def test_progress_unknown_org(self):
        r = requests.get(f"{API}/exam-organizations/nope-{uuid.uuid4().hex}/distribution-progress", timeout=5)
        assert r.status_code == 200 and r.json()["progress"] is None


# Violations detail on candidate
class TestViolations:
    def test_create_violation_by_move(self, org):
        c1 = state["c1"]
        r = requests.put(f"{API}/exam-organizations/{org}/selected-candidate", json={"candidate_id": c1["candidate_id"]}, timeout=20)
        assert r.status_code == 200, r.text
        # find desk with one student and one empty seat, then move another same-section student there
        target = None
        for room in c1["plan"]:
            for desk in room["desks"]:
                seats = desk["seats"]
                occ = [s for s in seats if s["student"]]
                empty = [s for s in seats if not s["student"] and s["is_available"]]
                if occ and empty:
                    target = (occ[0]["student"], empty[0]["seat_id"])
                    break
            if target:
                break
        assert target, "no half-empty desk"
        neighbour, seat_id = target
        mover = next(a for a in c1["assignments"] if a["section"] == neighbour["section"]
                     and a["class_level"] == neighbour["class_level"] and a["participant_id"] != neighbour["participant_id"])
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{c1['candidate_id']}/moves",
                          json={"participant_id": mover["participant_id"], "target_seat_id": seat_id}, timeout=30)
        assert r.status_code == 201, r.text
        child = r.json()["candidate"]
        v = child["violations"]
        assert len(v) >= 1
        pair = [x for x in v if {x["first_participant_id"], x["second_participant_id"]} == {mover["participant_id"], neighbour["participant_id"]}]
        assert pair, v
        assert "Aynı şube" in pair[0]["reason"] and "yan yana" in pair[0]["reason"]
        assert {pair[0]["first_seat_id"], pair[0]["second_seat_id"]} == {seat_id, neighbour["seat_id"]}
        assert child["affected_student_count"] >= 2
        # persisted: GET candidates shows violations
        cs = requests.get(f"{API}/exam-organizations/{org}/distribution-candidates", timeout=20).json()["candidates"]
        got = next(c for c in cs if c["candidate_id"] == child["candidate_id"])
        assert len(got["violations"]) == len(v)


# App update API
class TestUpdates:
    def test_status(self):
        d = requests.get(f"{API}/updates/status", timeout=10).json()
        assert d["current_version"] == "0.2.0" and d["can_apply"] is False and d["last_result"] is None
        assert isinstance(d["platform"], str) and d["platform"]

    def test_inspect_no_file(self):
        r = requests.post(f"{API}/updates/inspect", timeout=10)
        assert r.status_code == 400 and "error" in r.json()

    def test_inspect_non_zip(self):
        r = requests.post(f"{API}/updates/inspect", files={"package": ("x.zip", b"not a zip at all", "application/zip")}, timeout=20)
        assert r.status_code == 400
        print("non-zip:", r.json()["error"])

    def test_inspect_zip_without_manifest(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("hello.txt", "hi")
        r = requests.post(f"{API}/updates/inspect", files={"package": ("u.zip", buf.getvalue(), "application/zip")}, timeout=20)
        assert r.status_code == 400
        print("no manifest:", r.json()["error"])

    def test_inspect_zip_path_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("../evil.txt", "x")
            z.writestr("manifest.json", "{}")
        r = requests.post(f"{API}/updates/inspect", files={"package": ("u.zip", buf.getvalue(), "application/zip")}, timeout=20)
        assert r.status_code == 400
        print("traversal:", r.json()["error"])

    def test_apply_without_confirm(self):
        r = requests.post(f"{API}/updates/apply", json={}, timeout=10)
        assert r.status_code == 400

    def test_apply_confirm_dev_409(self):
        r = requests.post(f"{API}/updates/apply", json={"confirm": True, "token": "x"}, timeout=10)
        assert r.status_code == 409 and "paketlenmiş" in r.json()["error"]

    def test_cancel_unknown(self):
        r = requests.post(f"{API}/updates/cancel", json={"token": "nope"}, timeout=10)
        assert r.status_code == 200 and r.json()["cancelled"] is False
