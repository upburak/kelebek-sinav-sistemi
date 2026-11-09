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


if __name__ == "__main__":
    sys.exit(main())
