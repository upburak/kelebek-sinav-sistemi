"""Çevrim içi sürüm denetimi ve kurulum paketi indirme (ağ taklit edilir)."""

import hashlib
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import test_exam_flow

from kelebek.services import online_update
from kelebek.version import APP_VERSION

PAYLOAD = b"sentetik kurulum paketi" * 100
PREFIX = online_update.DOWNLOAD_PREFIX


def _release(version: str, digest: str | None = None) -> dict:
    digest = digest or hashlib.sha256(PAYLOAD).hexdigest()
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/{online_update.REPOSITORY}/releases/tag/v{version}",
        "published_at": "2026-11-11T12:00:00Z",
        "assets": [
            {"name": f"KelebekSinavSistemi-{version}-windows-x64-kurulum.exe",
             "browser_download_url": f"{PREFIX}v{version}/KelebekSinavSistemi-{version}-windows-x64-kurulum.exe",
             "size": len(PAYLOAD), "digest": f"sha256:{digest}"},
            {"name": f"KelebekSinavSistemi-{version}-macos-arm64.dmg",
             "browser_download_url": f"{PREFIX}v{version}/KelebekSinavSistemi-{version}-macos-arm64.dmg",
             "size": len(PAYLOAD), "digest": f"sha256:{digest}"},
            {"name": f"KelebekSinavSistemi-{version}-linux-x64.deb",
             "browser_download_url": f"{PREFIX}v{version}/KelebekSinavSistemi-{version}-linux-x64.deb",
             "size": len(PAYLOAD), "digest": f"sha256:{digest}"},
            {"name": f"KelebekSinavSistemi-{version}-linux-x64.tar.gz",
             "browser_download_url": f"{PREFIX}v{version}/KelebekSinavSistemi-{version}-linux-x64.tar.gz",
             "size": len(PAYLOAD), "digest": f"sha256:{digest}"},
            {"name": "SHA256SUMS.txt", "browser_download_url": f"{PREFIX}v{version}/SHA256SUMS.txt", "size": 10},
        ],
    }


def _opener(release: dict, body: bytes = PAYLOAD):
    def opener(url):
        if url == online_update.LATEST_RELEASE_URL:
            return io.BytesIO(json.dumps(release).encode("utf-8"))
        return io.BytesIO(body)
    return opener


def _offline(_url):
    raise urllib.error.URLError("ağ yok")


class OnlineUpdateServiceTests(unittest.TestCase):
    def test_newer_release_is_reported_with_platform_package(self):
        with mock.patch.object(online_update, "platform_kind", return_value="windows"):
            result = online_update.check_latest(_opener(_release("99.0.0")))
        self.assertTrue(result["update_available"])
        self.assertEqual(result["latest_version"], "99.0.0")
        self.assertEqual(result["current_version"], APP_VERSION)
        self.assertTrue(result["asset"]["name"].endswith("-kurulum.exe"))
        self.assertEqual(len(result["asset"]["sha256"]), 64)

    def test_same_or_older_release_is_not_an_update(self):
        for version in (APP_VERSION, "0.0.1"):
            self.assertFalse(online_update.check_latest(_opener(_release(version)))["update_available"], version)

    def test_version_comparison_is_numeric(self):
        self.assertGreater(online_update.parse_version("0.10.0"), online_update.parse_version("0.9.9"))
        self.assertEqual(online_update.parse_version("v1.2.3"), (1, 2, 3))

    def test_offline_gives_a_readable_error_instead_of_crashing(self):
        with self.assertRaises(online_update.OnlineUpdateError) as caught:
            online_update.check_latest(_offline)
        self.assertIn("internet", str(caught.exception).casefold())

    def test_private_or_missing_release_source_is_explained(self):
        def not_found(url):
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        with self.assertRaises(online_update.OnlineUpdateError) as caught:
            online_update.check_latest(not_found)
        self.assertIn("herkese açık", str(caught.exception))

    def test_linux_gets_the_deb_package_on_x64_only(self):
        assets = _release("99.0.0")["assets"]
        with mock.patch.object(online_update.platform, "machine", return_value="x86_64"):
            asset = online_update.pick_asset(assets, "linux")
        self.assertTrue(asset["name"].endswith("-linux-x64.deb"))
        with mock.patch.object(online_update.platform, "machine", return_value="aarch64"):
            self.assertIsNone(online_update.pick_asset(assets, "linux"))

    def test_linux_package_is_opened_with_the_desktop_handler(self):
        with mock.patch.object(online_update.sys, "platform", "linux"), \
                mock.patch.object(online_update.shutil, "which", return_value="/usr/bin/xdg-open"), \
                mock.patch.object(online_update.subprocess, "Popen") as popen:
            self.assertTrue(online_update.open_package(Path("/tmp/paket.deb")))
        # Yol, testin koştuğu işletim sisteminin ayracıyla yazılır.
        self.assertEqual(popen.call_args.args[0], ["xdg-open", str(Path("/tmp/paket.deb"))])
        with mock.patch.object(online_update.sys, "platform", "linux"), \
                mock.patch.object(online_update.shutil, "which", return_value=None):
            self.assertFalse(online_update.open_package(Path("/tmp/paket.deb")))

    def test_package_is_downloaded_and_verified(self):
        asset = online_update.pick_asset(_release("99.0.0")["assets"], "windows")
        with tempfile.TemporaryDirectory() as folder:
            path = online_update.download_package(asset, Path(folder), _opener({}, PAYLOAD))
            self.assertEqual(path.read_bytes(), PAYLOAD)
            self.assertEqual([item.name for item in Path(folder).iterdir()], [asset["name"]])

    def test_tampered_package_is_rejected_and_removed(self):
        asset = online_update.pick_asset(_release("99.0.0")["assets"], "windows")
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(online_update.OnlineUpdateError):
                online_update.download_package(asset, Path(folder), _opener({}, PAYLOAD + b"x"))
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_package_from_another_address_or_without_digest_is_refused(self):
        good = online_update.pick_asset(_release("99.0.0")["assets"], "windows")
        with tempfile.TemporaryDirectory() as folder:
            for bad in ({**good, "url": "https://example.com/KelebekSinavSistemi-99.exe"},
                        {**good, "sha256": ""},
                        {**good, "name": "../../baska.exe"}):
                with self.assertRaises(online_update.OnlineUpdateError):
                    online_update.download_package(bad, Path(folder), _opener({}, PAYLOAD))
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_foreign_asset_url_is_never_picked(self):
        assets = [{"name": "KelebekSinavSistemi-9-windows-x64-kurulum.exe",
                   "browser_download_url": "https://example.com/x-kurulum.exe", "digest": "sha256:" + "a" * 64}]
        self.assertIsNone(online_update.pick_asset(assets, "windows"))


class OnlineUpdateApiTests(unittest.TestCase):
    setUp = test_exam_flow.ExamFlowTests.setUp
    tearDown = test_exam_flow.ExamFlowTests.tearDown
    _seed_synthetic_school = test_exam_flow.ExamFlowTests._seed_synthetic_school

    def test_check_reports_update_and_survives_being_offline(self):
        with mock.patch.object(online_update, "_open", _opener(_release("99.0.0"))):
            data = self.client.get("/api/updates/online").get_json()
        self.assertTrue(data["checked"] and data["update_available"])
        with mock.patch.object(online_update, "_open", _offline):
            response = self.client.get("/api/updates/online")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["checked"])
        self.assertIn("error", response.get_json())

    def test_startup_check_does_not_touch_the_network_when_turned_off(self):
        saved = self.client.put("/api/updates/online/settings", json={"auto_check": False})
        self.assertEqual(saved.status_code, 200)
        with mock.patch.object(online_update, "_open", side_effect=AssertionError("ağa çıkıldı")):
            data = self.client.get("/api/updates/online?auto=1").get_json()
        self.assertEqual((data["checked"], data["auto_check"]), (False, False))
        # Elle denetim ayardan bağımsız çalışır.
        with mock.patch.object(online_update, "_open", _opener(_release("99.0.0"))):
            self.assertTrue(self.client.get("/api/updates/online").get_json()["checked"])

    def test_download_needs_confirmation_and_takes_a_safety_backup(self):
        self.assertEqual(self.client.post("/api/updates/online/download", json={}).status_code, 400)
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(online_update, "_open", _opener(_release("99.0.0"))), \
                mock.patch.object(online_update, "platform_kind", return_value="windows"), \
                mock.patch.object(online_update, "downloads_dir", return_value=Path(folder)), \
                mock.patch.object(online_update, "open_package", return_value=True) as opened:
            response = self.client.post("/api/updates/online/download", json={"confirm": True})
            data = response.get_json()
            self.assertEqual(response.status_code, 200, data)
            self.assertTrue(Path(data["path"]).is_file())
            self.assertTrue(data["safety_backup"].startswith("safety-app-update-"))
            opened.assert_called_once()

    def test_download_is_refused_when_already_current(self):
        with mock.patch.object(online_update, "_open", _opener(_release(APP_VERSION))):
            response = self.client.post("/api/updates/online/download", json={"confirm": True})
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
