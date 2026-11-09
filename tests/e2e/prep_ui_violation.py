# Prep helper for UI test: fresh candidate + same-section adjacent violation via move (prints ids as JSON).
import json
import os
import sys

import requests

API = os.environ["KELEBEK_PUBLIC_URL"].rstrip("/") + "/api"
org = sys.argv[1]
r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates", json={}, timeout=120)
assert r.status_code == 201, r.text
c1 = r.json()["candidate"]
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
neighbour, seat_id = target
mover = next(a for a in c1["assignments"] if a["section"] == neighbour["section"]
             and a["class_level"] == neighbour["class_level"] and a["participant_id"] != neighbour["participant_id"])
r = requests.post(f"{API}/exam-organizations/{org}/distribution-candidates/{c1['candidate_id']}/moves",
                  json={"participant_id": mover["participant_id"], "target_seat_id": seat_id}, timeout=60)
assert r.status_code == 201, r.text
child = r.json()["candidate"]
print(json.dumps({"c1": c1["candidate_id"], "child": child["candidate_id"], "mover": mover["participant_id"],
                  "neighbour": neighbour["participant_id"], "suggestions": child["violation_suggestions"],
                  "violations": child["violations"]}))
