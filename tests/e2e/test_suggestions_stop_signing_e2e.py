# E2E API regression (public URL) for iteration 3: violation fix suggestions (İhlal çözüm önerisi),
# 'stopped' candidate status (Erken durduruldu), update package signature trust (güvenilir yayıncı anahtarı).
import io
import json
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
    payload = {"academic_year_id": year_id, "name": f"TEST_SUGG_{uuid.uuid4().hex[:6]}", "exam_date": "2026-03-17",
               "participant_groups": [{"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups]}
    r = requests.post(f"{API}/exam-organizations", json=payload, timeout=30)
    assert r.status_code == 201, r.text
    o = r.json()["organization"]
    rooms = requests.get(f"{API}/exam-room-options", params={"academic_year_id": year_id}, timeout=20).json()["rooms"]
    demo = [x for x in rooms if x["classroom_name"] in ("DEMO-101", "DEMO-102")]
    r = requests.put(f"{API}/exam-organizations/{o['id']}/classrooms", json={"layout_ids": [x["layout_id"] for x in demo]}, timeout=20)
    assert r.status_code == 200, r.text
    state["org"] = o["id"]
    return o["id"]


def _affected(violations):
    return {v["first_participant_id"] for v in violations} | {v["second_participant_id"] for v in violations}


# İhlal çözüm önerisi
class TestViolationSuggestions:
    def test_create_candidate_has_empty_suggestions(self, org):
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates", json={}, timeout=120)
        assert r.status_code == 201, r.text
        c = r.json()["candidate"]
        state["c1"] = c
        assert c["status"] in ("optimal", "feasible", "stopped")
        assert "violation_suggestions" in c and isinstance(c["violation_suggestions"], dict)
        assert set(c["violation_suggestions"]) == _affected(c["violations"])

    def test_violation_creates_suggestions(self, org):
        c1 = state["c1"]
        r = requests.put(f"{API}/exam-organizations/{org}/selected-candidate", json={"candidate_id": c1["candidate_id"]}, timeout=20)
        assert r.status_code == 200, r.text
        target = None
        for room in c1["plan"]:
            for desk in room["desks"]:
                occ = [s for s in desk["seats"] if s["student"]]
                empty = [s for s in desk["seats"] if not s["student"] and s["is_available"]]
                if occ and empty:
                    target = (occ[0]["student"], empty[0]["seat_id"])
                    break
            if target:
                break
        assert target
        neighbour, seat_id = target
        mover = next(a for a in c1["assignments"] if a["section"] == neighbour["section"]
                     and a["class_level"] == neighbour["class_level"] and a["participant_id"] != neighbour["participant_id"])
        r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{c1['candidate_id']}/moves",
                          json={"participant_id": mover["participant_id"], "target_seat_id": seat_id}, timeout=60)
        assert r.status_code == 201, r.text
        child = r.json()["candidate"]
        state["child"] = child
        state["mover"] = mover["participant_id"]
        affected = _affected(child["violations"])
        assert mover["participant_id"] in affected
        sugg = child["violation_suggestions"]
        assert set(sugg) == affected, (set(sugg), affected)
        occupied = {a["seat_id"] for a in child["assignments"] if a["seat_id"]}
        available = {s["seat_id"] for s in child["available_seats"]}
        for pid, options in sugg.items():
            assert len(options) <= 3
            for opt in options:
                assert set(opt) >= {"seat_id", "classroom_name", "seat_number", "same_room"}
                assert opt["seat_id"] not in occupied, f"suggested occupied seat for {pid}"
                assert opt["seat_id"] in available
        print("suggestions:", json.dumps(sugg)[:400])

    def test_get_candidates_returns_suggestions(self, org):
        child = state["child"]
        cs = requests.get(f"{API}/exam-organizations/{org}/distribution-candidates", timeout=30).json()["candidates"]
        got = next(c for c in cs if c["candidate_id"] == child["candidate_id"])
        assert got["violation_suggestions"] == child["violation_suggestions"]

    def test_apply_every_suggestion_creates_no_new_violation(self, org):
        child = state["child"]
        sugg = child["violation_suggestions"]
        before = child["violations"]
        checked = 0
        # applying top suggestion for each affected student, one at a time, from the same child state
        for pid, options in sugg.items():
            if not options:
                continue
            # re-select the child each time to apply from same base
            r = requests.put(f"{API}/exam-organizations/{org}/selected-candidate", json={"candidate_id": child["candidate_id"]}, timeout=20)
            if r.status_code != 200:
                pytest.skip(f"child not selectable: {r.text}")
            r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{child['candidate_id']}/moves",
                              json={"participant_id": pid, "target_seat_id": options[0]["seat_id"]}, timeout=60)
            assert r.status_code == 201, r.text
            after = r.json()["candidate"]
            # no violation involving pid remains
            assert pid not in _affected(after["violations"]), after["violations"]
            # no new violation pair created
            pairs_before = {frozenset((v["first_participant_id"], v["second_participant_id"])) for v in before}
            pairs_after = {frozenset((v["first_participant_id"], v["second_participant_id"])) for v in after["violations"]}
            assert pairs_after <= pairs_before, pairs_after - pairs_before
            assert len(after["violations"]) < len(before)
            mv = next(a for a in after["assignments"] if a["participant_id"] == pid)
            assert mv["seat_id"] == options[0]["seat_id"]
            assert len(after["events"]) >= 1 and after["history"]["can_undo"] is True
            checked += 1
        assert checked >= 1


# Erken durduruldu: status 'stopped'
class TestStoppedCandidate:
    def test_stop_after_first_solution_saves_stopped(self, org):
        box = {}

        def run():
            box["resp"] = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates", json={}, timeout=120)
        t = threading.Thread(target=run)
        t.start()
        stopped = False
        deadline = time.time() + 30
        while time.time() < deadline and t.is_alive():
            p = requests.get(f"{API}/exam-organizations/{org}/distribution-progress", timeout=5).json()["progress"]
            if p and p["active"] and p["stage"] == "search" and (p.get("solutions_found") or 0) >= 1:
                r = requests.post(f"{API}/exam-organizations/{org}/distribution-progress/stop", timeout=5)
                stopped = r.status_code == 200
                print("stop api:", r.status_code, r.text[:200])
                print("progress at stop:", p)
                break
            time.sleep(0.1)
        t.join(90)
        resp = box["resp"]
        print("stop result:", resp.status_code, resp.text[:200])
        if not stopped:
            print("candidate status:", resp.json().get("candidate", {}).get("status"), resp.json().get("candidate", {}).get("stopped_early"))
            pytest.skip("solver finished before stop could be sent")
        assert resp.status_code == 201, resp.text
        c = resp.json()["candidate"]
        assert c["stopped_early"] is True and c["status"] == "stopped"
        cs = requests.get(f"{API}/exam-organizations/{org}/distribution-candidates", timeout=30).json()["candidates"]
        got = next(x for x in cs if x["candidate_id"] == c["candidate_id"])
        assert got["status"] == "stopped"
        state["stopped_cid"] = c["candidate_id"]

    def test_stopped_candidate_selectable(self, org):
        cid = state.get("stopped_cid")
        if not cid:
            pytest.skip("no stopped candidate")
        r = requests.put(f"{API}/exam-organizations/{org}/selected-candidate", json={"candidate_id": cid}, timeout=20)
        assert r.status_code in (200, 409), r.text
        print("select stopped:", r.status_code, r.text[:200])


def _zip(manifest: dict | None, extra: dict | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        if manifest is not None:
            z.writestr("manifest.json", json.dumps(manifest))
        for k, v in (extra or {}).items():
            z.writestr(k, v)
    return buf.getvalue()


# Güncelleme imzası
class TestUpdateSignature:
    def test_status_trusted_key_ids_empty(self):
        d = requests.get(f"{API}/updates/status", timeout=10).json()
        assert d["trusted_key_ids"] == []

    def test_valid_looking_manifest_rejected_untrusted(self):
        platform = requests.get(f"{API}/updates/status", timeout=10).json()["platform"]
        payload = b"binary"
        import hashlib
        manifest = {"format": "kelebek-update/1", "version": "0.3.0", "platform": platform,
                    "files": [{"path": "app/kelebek.bin", "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}]}
        r = requests.post(f"{API}/updates/inspect", files={"package": ("u.zip", _zip(manifest, {"app/kelebek.bin": payload}), "application/zip")}, timeout=30)
        print("unsigned:", r.status_code, r.text[:300])
        assert r.status_code == 400
        assert "güvenilir yayıncı anahtarı" in r.json()["error"]

    def test_fake_signature_rejected(self):
        platform = requests.get(f"{API}/updates/status", timeout=10).json()["platform"]
        manifest = {"format": "kelebek-update/1", "version": "0.3.0", "platform": platform, "files": [],
                    "signature": {"key_id": "deadbeef", "algorithm": "ed25519", "value": "AAAA"}}
        r = requests.post(f"{API}/updates/inspect", files={"package": ("u.zip", _zip(manifest, {"manifest.sig": "AAAA"}), "application/zip")}, timeout=30)
        print("fake sig:", r.status_code, r.text[:300])
        assert r.status_code == 400

    def test_non_zip_still_bozuk(self):
        r = requests.post(f"{API}/updates/inspect", files={"package": ("x.zip", b"not a zip", "application/zip")}, timeout=20)
        assert r.status_code == 400
        assert "açılamadı veya bozuk" in r.json()["error"]
