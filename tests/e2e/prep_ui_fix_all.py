# Prep helper for UI test (iter4): new TEST_FIXUI draft org (DEMO-101/102), candidate + N same-section violations via moves API.
import json
import os
import sys
import uuid

import requests

API = os.environ["KELEBEK_PUBLIC_URL"].rstrip("/") + "/api"
n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
year_id = requests.get(f"{API}/academic-years", timeout=20).json()["selected_academic_year_id"]
groups = requests.get(f"{API}/student-groups", params={"academic_year_id": year_id}, timeout=20).json()["groups"]
r = requests.post(f"{API}/exam-organizations", json={"academic_year_id": year_id, "name": f"TEST_FIXUI_{uuid.uuid4().hex[:6]}",
                  "exam_date": "2026-03-19", "participant_groups": [{"class_level": g["class_level"], "section": g["section"], "area": g["area"]} for g in groups]}, timeout=30)
assert r.status_code == 201, r.text
org = r.json()["organization"]["id"]
rooms = requests.get(f"{API}/exam-room-options", params={"academic_year_id": year_id}, timeout=20).json()["rooms"]
requests.put(f"{API}/exam-organizations/{org}/classrooms", json={"layout_ids": [x["layout_id"] for x in rooms if x["classroom_name"] in ("DEMO-101", "DEMO-102")]}, timeout=20).raise_for_status()
cand = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates", json={}, timeout=120).json()["candidate"]
requests.put(f"{API}/exam-organizations/{org}/selected-candidate", json={"candidate_id": cand["candidate_id"]}, timeout=20).raise_for_status()
used = set()
for _ in range(n):
    done = False
    for room in cand["plan"]:
        for desk in room["desks"]:
            occ = [s for s in desk["seats"] if s["student"] and s["student"]["participant_id"] not in used]
            empty = [s for s in desk["seats"] if not s["student"] and s["is_available"]]
            if not (occ and empty):
                continue
            nb = occ[0]["student"]
            mover = next((a for a in cand["assignments"] if a["section"] == nb["section"] and a["class_level"] == nb["class_level"]
                          and a["participant_id"] not in used | {nb["participant_id"]}), None)
            if not mover:
                continue
            r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{cand['candidate_id']}/moves",
                              json={"participant_id": mover["participant_id"], "target_seat_id": empty[0]["seat_id"]}, timeout=60)
            assert r.status_code == 201, r.text
            cand = r.json()["candidate"]
            used |= {mover["participant_id"], nb["participant_id"]}
            done = True
            break
        if done:
            break
print(json.dumps({"org": org, "candidate": cand["candidate_id"], "affected": cand["affected_student_count"], "violations": len(cand["violations"])}))
