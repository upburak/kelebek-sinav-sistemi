"""Paketlenmiş uygulamayı geçici veri klasörüyle açıp temel uçları doğrular (CI ve yerel deneme)."""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 18765


def executable() -> Path:
    override = os.environ.get("KELEBEK_SMOKE_EXECUTABLE")  # kurulu paketi sınamak için
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return ROOT / "dist" / "Kelebek Sınav Sistemi.app" / "Contents" / "MacOS" / "KelebekSinavSistemi"
    name = "KelebekSinavSistemi.exe" if sys.platform == "win32" else "KelebekSinavSistemi"
    return ROOT / "dist" / "KelebekSinavSistemi" / name


def get(path: str, method: str = "GET"):
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, response.read()


def main() -> int:
    with tempfile.TemporaryDirectory() as data_dir:
        env = {**os.environ, "KELEBEK_DATA_DIR": data_dir, "KELEBEK_NO_BROWSER": "1", "KELEBEK_PORT": str(PORT)}
        process = subprocess.Popen([str(executable())], env=env)
        try:
            for _ in range(120):
                try:
                    status, body = get("/api/health")
                    if status == 200:
                        break
                except OSError:
                    time.sleep(1)
            else:
                raise SystemExit("Uygulama 120 sn içinde açılmadı.")
            assert json.loads(body)["desktop"] is True
            status, page = get("/")
            assert status == 200 and b'id="root"' in page, "Arayüz sunulmadı."
            status, years = get("/api/academic-years")
            assert status == 200 and json.loads(years)["years"], "Veritabanı hazırlanmadı."
            status, update = get("/api/updates/status")
            print("Sürüm:", json.loads(update)["current_version"], "·", json.loads(update)["platform"])
            assert (Path(data_dir) / "kelebek.sqlite3").is_file(), "Veritabanı veri klasöründe değil."
            get("/api/app/shutdown", "POST")
            process.wait(timeout=30)
            print("Duman testi geçti.")
            return 0
        finally:
            if process.poll() is None:
                process.kill()


def window_check() -> int:
    """Uygulama penceresi kipi: pencere açılmalı, "Uygulamayı kapat" hem uygulamayı hem pencereyi kapatmalı."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as data_dir:
        env = {**os.environ, "KELEBEK_DATA_DIR": data_dir, "KELEBEK_PORT": str(PORT)}
        env.pop("KELEBEK_NO_BROWSER", None)
        env.pop("KELEBEK_BROWSER_TAB", None)
        process = subprocess.Popen([str(executable())], env=env)
        try:
            health = {}
            for _ in range(90):
                try:
                    health = json.loads(get("/api/health")[1])
                    if health.get("window"):
                        break
                except OSError:
                    pass
                time.sleep(1)
            assert health.get("window") is True, f"Uygulama penceresi açılmadı: {health}"
            # Tarayıcı gerçekten başladıysa birkaç saniye içinde kendi profil klasörünü doldurur.
            profile = Path(data_dir) / "window-profile"
            for _ in range(30):
                if profile.is_dir() and any(profile.iterdir()):
                    break
                time.sleep(1)
            assert profile.is_dir() and any(profile.iterdir()), "Pencere kendi profilini kullanmadı."
            assert process.poll() is None, "Uygulama, pencere açıkken kendiliğinden kapandı."
            get("/api/app/shutdown", "POST")
            process.wait(timeout=30)
            print("Pencere testi geçti.")
            return 0
        finally:
            if process.poll() is None:
                process.kill()


if __name__ == "__main__":
    sys.exit(window_check() if os.environ.get("KELEBEK_SMOKE_WINDOW") else main())
