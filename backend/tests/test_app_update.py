"""Artımlı güncelleme: paket üretimi, doğrulama, uygulama ve başarısızlıkta geri dönüş (sentetik)."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import release_app_resources
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from kelebek import create_app, update_trust
from kelebek.services import app_update
from kelebek.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_update_package", ROOT / "scripts" / "make_update_package.py")
make_update_package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_update_package)

LAUNCH_OK = "#!/bin/bash\n[ -n \"${KELEBEK_UPDATE_VERIFY:-}\" ] && echo ok > \"$KELEBEK_UPDATE_VERIFY\"\nsleep 5\n"
LAUNCH_BROKEN = "#!/bin/bash\nexit 3\n"


@unittest.skipIf(sys.platform == "win32", "POSIX güncelleyici testi")
class AppUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        os.environ["KELEBEK_DATA_DIR"] = str(base / "data")
        self.old, self.new, self.install = base / "old", base / "new", base / "install"
        for root in (self.old, self.new, self.install):
            (root / "lib").mkdir(parents=True)
        for root in (self.old, self.install):
            (root / "lib" / "same.txt").write_text("aynı")
            (root / "lib" / "changed.txt").write_text("eski")
            (root / "lib" / "obsolete.txt").write_text("kaldırılacak")
        (self.new / "lib" / "same.txt").write_text("aynı")
        (self.new / "lib" / "changed.txt").write_text("yeni")
        (self.new / "lib" / "added.txt").write_text("eklendi")
        self.key_path = base / "signing.pem"
        self._write_key(self.key_path)
        self.other_key = base / "other.pem"
        self._write_key(self.other_key)
        self.original_keys = update_trust.TRUSTED_PUBLIC_KEYS
        update_trust.TRUSTED_PUBLIC_KEYS = [make_update_package.update_signing.public_key_b64(
            make_update_package.update_signing.load_private_key(self.key_path))]
        self.app = create_app()
        self.client = self.app.test_client()
        os.environ["KELEBEK_INSTALL_ROOT"] = str(self.install)

    @staticmethod
    def _write_key(path):
        path.write_bytes(Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))

    def tearDown(self):
        update_trust.TRUSTED_PUBLIC_KEYS = self.original_keys
        release_app_resources(self.app)
        os.environ.pop("KELEBEK_INSTALL_ROOT", None)
        os.environ.pop("KELEBEK_DATA_DIR", None)
        self.temp.cleanup()

    def _package(self, launcher: str, from_version=APP_VERSION, key=None) -> Path:
        (self.new / "KelebekSinavSistemi").write_text(launcher)
        (self.new / "KelebekSinavSistemi").chmod(0o755)
        (self.install / "KelebekSinavSistemi").write_text(LAUNCH_OK)
        (self.install / "KelebekSinavSistemi").chmod(0o755)
        (self.old / "KelebekSinavSistemi").write_text(LAUNCH_OK)
        return make_update_package.build(self.old, self.new, app_update.current_platform(), from_version, "9.9.9",
                                         Path(self.temp.name) / "out", sign_key=key or self.key_path)

    def _inspect(self, package: Path):
        with package.open("rb") as handle:
            return self.client.post("/api/updates/inspect", data={"package": (handle, package.name)},
                                    content_type="multipart/form-data")

    def _run_updater(self, token: str) -> dict:
        job = app_update.prepare_apply(token, Path(self.temp.name) / "safety.zip")
        env_file = Path(job["staged"]) / "job.env"
        env_file.write_text(env_file.read_text().replace(f"APP_PID={job['app_pid']}", "APP_PID=999999").replace("TIMEOUT=120", "TIMEOUT=10"))
        script = Path(job["staged"]) / "apply-update.sh"
        script.write_text(app_update.POSIX_SCRIPT)
        subprocess.run(["/bin/bash", str(script), str(env_file)], timeout=60, check=False)
        return json.loads(Path(job["result_file"]).read_text())

    def test_package_contains_only_changes_and_applies_successfully(self):
        package = self._package(LAUNCH_OK)
        response = self._inspect(package)
        self.assertEqual(response.status_code, 200, response.get_json())
        summary = response.get_json()["summary"]
        self.assertEqual(summary["changed_file_count"], 2)
        self.assertEqual(summary["removed_file_count"], 1)
        self.assertEqual(len(summary["signature_key_id"]), 16)
        result = self._run_updater(response.get_json()["token"])
        self.assertEqual(result["status"], "success", result)
        self.assertEqual((self.install / "lib" / "changed.txt").read_text(), "yeni")
        self.assertEqual((self.install / "lib" / "added.txt").read_text(), "eklendi")
        self.assertFalse((self.install / "lib" / "obsolete.txt").exists())
        self.assertEqual(self.client.get("/api/updates/status").get_json()["last_result"]["status"], "success")

    def test_failed_start_rolls_back_files_and_database(self):
        package = self._package(LAUNCH_BROKEN)
        token = self._inspect(package).get_json()["token"]
        database = Path(os.environ["KELEBEK_DATA_DIR"]) / "kelebek.sqlite3"
        before = database.read_bytes()
        result = self._run_updater(token)
        self.assertEqual(result["status"], "rolled_back", result)
        self.assertEqual((self.install / "lib" / "changed.txt").read_text(), "eski")
        self.assertTrue((self.install / "lib" / "obsolete.txt").exists())
        self.assertFalse((self.install / "lib" / "added.txt").exists())
        self.assertEqual((self.install / "KelebekSinavSistemi").read_text(), LAUNCH_OK)
        self.assertEqual(database.read_bytes(), before)

    def test_wrong_version_and_tampered_files_are_rejected(self):
        wrong = self._package(LAUNCH_OK, from_version="0.0.1")
        response = self._inspect(wrong)
        self.assertEqual(response.status_code, 400)
        self.assertIn("sürümünden", response.get_json()["error"])
        import zipfile
        package = self._package(LAUNCH_OK)
        tampered = package.with_name("tampered.zip")
        with zipfile.ZipFile(package) as source, zipfile.ZipFile(tampered, "w") as target:
            for item in source.infolist():
                data = source.read(item)
                target.writestr(item, b"bozuk" if item.filename == "files/lib/changed.txt" else data)
        response = self._inspect(tampered)
        self.assertEqual(response.status_code, 400)
        self.assertIn("doğrulaması", response.get_json()["error"])



@unittest.skipIf(sys.platform == "win32", "POSIX güncelleyici testi")
class UpdateSignatureTests(AppUpdateTests):
    test_package_contains_only_changes_and_applies_successfully = None
    test_failed_start_rolls_back_files_and_database = None
    test_wrong_version_and_tampered_files_are_rejected = None

    def test_foreign_key_unsigned_and_untrusted_install_are_rejected(self):
        foreign = self._package(LAUNCH_OK, key=self.other_key)
        response = self._inspect(foreign)
        self.assertEqual(response.status_code, 400)
        self.assertIn("İmza doğrulanamadı", response.get_json()["error"])
        import zipfile
        signed = self._package(LAUNCH_OK)
        unsigned = signed.with_name("unsigned.zip")
        with zipfile.ZipFile(signed) as source, zipfile.ZipFile(unsigned, "w") as target:
            for item in source.infolist():
                if item.filename != "manifest.sig":
                    target.writestr(item, source.read(item))
        self.assertIn("imzasız", self._inspect(unsigned).get_json()["error"])
        update_trust.TRUSTED_PUBLIC_KEYS = []
        self.assertIn("güvenilir yayıncı anahtarı", self._inspect(signed).get_json()["error"])


if __name__ == "__main__":
    unittest.main()
