"""Paketlenmiş arayüzün statik dosyalarını sunma kuralları.

Gerileme: kurulum yolu sembolik bağ içerdiğinde (macOS'ta ``/var`` ve bağlı
*Applications* klasörleri, taşınmış kullanıcı klasörleri) JavaScript/CSS
isteklerine ``index.html`` dönüyordu; arayüz hiç açılmıyordu.
"""

import os
import tempfile
import unittest
from pathlib import Path

from _support import release_app_resources

from kelebek import create_app


class FrontendServingTests(unittest.TestCase):
    def setUp(self):
        self.apps = []
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.previous_data_dir = os.environ.get("KELEBEK_DATA_DIR")
        os.environ["KELEBEK_DATA_DIR"] = str(base / "data")

        self.real_dist = base / "real" / "frontend_dist"
        (self.real_dist / "assets").mkdir(parents=True)
        (self.real_dist / "index.html").write_text(
            '<!doctype html><html><body><div id="root"></div>'
            '<script src="/assets/app.js"></script></body></html>',
            encoding="utf-8",
        )
        (self.real_dist / "assets" / "app.js").write_text("export const ready = true\n", encoding="utf-8")
        (self.real_dist / "downloads").mkdir()
        (self.real_dist / "downloads" / "ornek.xlsx").write_bytes(b"PK\x03\x04sentetik")
        self.secret_marker = "arayuz-klasoru-disinda-gizli"
        (base / "secret.txt").write_text(self.secret_marker, encoding="utf-8")

        # Sembolik bağ üzerinden erişim: macOS kurulumlarındaki durumu birebir taklit eder.
        # Windows'ta sembolik bağ oluşturmak yönetici yetkisi ister; o durumda test atlanır.
        self.linked_root = base / "link"
        try:
            self.linked_root.symlink_to(base / "real", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.linked_root = None

    def tearDown(self):
        for app in self.apps:
            release_app_resources(app)
        if self.previous_data_dir is None:
            os.environ.pop("KELEBEK_DATA_DIR", None)
        else:
            os.environ["KELEBEK_DATA_DIR"] = self.previous_data_dir
        self.temp_dir.cleanup()

    def _client(self, dist: Path):
        app = create_app(frontend_dist=dist)
        # Windows açık dosyanın silinmesine izin vermez; kaynaklar tearDown'da,
        # geçici klasör silinmeden önce bırakılır (addCleanup tearDown'dan SONRA çalışır).
        self.apps.append(app)
        return app.test_client()

    def _assert_serves_assets(self, dist: Path, label: str):
        client = self._client(dist)

        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200, label)
        self.assertIn("javascript", response.headers.get("Content-Type", ""), label)
        self.assertIn(b"ready", response.data, label)

        response = client.get("/downloads/ornek.xlsx")
        self.assertEqual(response.status_code, 200, label)
        self.assertEqual(response.data, b"PK\x03\x04sentetik", label)

        # Arayüz yönlendirmeleri (SPA) index.html almaya devam eder.
        response = client.get("/raporlar")
        self.assertEqual(response.status_code, 200, label)
        self.assertIn(b'id="root"', response.data, label)

    def test_serves_assets_from_direct_path(self):
        self._assert_serves_assets(self.real_dist, "doğrudan yol")

    def test_serves_assets_through_symlinked_install_path(self):
        if self.linked_root is None:
            self.skipTest("Bu bilgisayarda sembolik bağ oluşturma yetkisi yok.")
        self._assert_serves_assets(self.linked_root / "frontend_dist", "sembolik bağlı yol")

    def test_api_paths_are_not_captured_by_frontend(self):
        response = self._client(self.real_dist).get("/api/bilinmeyen-uc")
        self.assertEqual(response.status_code, 404)

    def test_paths_outside_frontend_folder_are_not_served(self):
        client = self._client(self.real_dist)
        for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
            response = client.get(path)
            self.assertNotIn(self.secret_marker.encode("utf-8"), response.data, path)


if __name__ == "__main__":
    unittest.main()
