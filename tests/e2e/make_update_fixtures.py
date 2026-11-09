# Builds test fixture files for the update-manager UI test (no real app build involved).
import hashlib
import json
import sys
import zipfile
from pathlib import Path

out = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
platform_name = sys.argv[2] if len(sys.argv) > 2 else "linux-arm64"
Path(f"{out}/bad.zip").write_bytes(b"this is not a zip")
with zipfile.ZipFile(f"{out}/nomanifest.zip", "w") as z:
    z.writestr("readme.txt", "x")
payload = b"TEST update payload\n"
manifest = {"format": "kelebek-update/1", "from_version": "0.2.0", "to_version": "0.2.1-test", "platform": platform_name,
            "files": [{"path": "TEST_dummy.txt", "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}],
            "removed": [], "notes": "TEST paket notu", "migrations": {"required": False}}
with zipfile.ZipFile(f"{out}/valid.zip", "w") as z:
    z.writestr("manifest.json", json.dumps(manifest))
    z.writestr("files/TEST_dummy.txt", payload)
print("ok")
