"""Uçtan uca testler için yerel sunucu ve sentetik okul verisi.

``KELEBEK_PUBLIC_URL`` verilmişse o adrese dokunulmaz (bulut önizlemesi gibi hazır
ortamlar için). Verilmemişse bu dosya testlerden önce geçici bir veri klasöründe
yerel servisi açar, sentetik okul verisini kurar ve adresi aynı değişkene yazar.
Böylece ``python -m pytest tests/e2e`` macOS, Windows ve Linux'ta elle hazırlık
yapılmadan çalışır.

Burada yalnızca gerçek dışı sentetik veri kullanılır; gerçek öğrenci bilgisi
hiçbir biçimde testlere girmez.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
LAUNCH = ROOT / "packaging" / "launch.py"
STARTUP_TIMEOUT_SECONDS = 120

_server: subprocess.Popen | None = None
_data_dir: str | None = None
_log_handle = None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Yerel servis açılamadı (çıkış kodu {process.returncode}).")
        try:
            if requests.get(f"{base_url}/api/health", timeout=2).status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError(f"Yerel servis {STARTUP_TIMEOUT_SECONDS} saniyede açılmadı.")


def _synthetic_students() -> list[dict[str, str]]:
    """Sekiz sınıf/şube grubunda 48 gerçek dışı öğrenci üret."""
    sys.path.insert(0, str(ROOT / "backend"))
    from kelebek.demo_data import build_demo_student_records

    return build_demo_student_records()


def _seed(base_url: str) -> None:
    """Sınav organizasyonu testleri için gereken en küçük okul verisini kur."""
    api = f"{base_url}/api"
    year_id = requests.get(f"{api}/academic-years", timeout=30).json()["selected_academic_year_id"]

    response = requests.put(f"{api}/school-profile", timeout=30, json={
        "school_name": "SENTETİK TEST LİSESİ",
        "province": "Test İli",
        "district": "Test İlçesi",
        "administrators": [{"role": "principal", "full_name": "SENTETİK MÜDÜR"}],
    })
    if response.status_code >= 400:
        raise RuntimeError(f"Okul profili kurulamadı: {response.text}")

    for record in _synthetic_students():
        response = requests.post(f"{api}/students", timeout=30, json={**record, "academic_year_id": year_id})
        if response.status_code not in (201, 409):
            raise RuntimeError(f"Sentetik öğrenci eklenemedi: {response.text}")

    # İki derslik × 40 oturma yeri; 48 öğrenci için yeterli boşluk bırakır.
    # Adlar testlerin beklediği DEMO-101/DEMO-102 olmalıdır.
    for name in ("DEMO-101", "DEMO-102"):
        response = requests.post(f"{api}/classrooms", json={"name": name}, timeout=30)
        if response.status_code == 409:
            continue
        if response.status_code != 201:
            raise RuntimeError(f"Derslik eklenemedi: {response.text}")
        classroom_id = response.json()["classroom"]["id"]

        response = requests.post(f"{api}/classrooms/{classroom_id}/layouts", timeout=30,
                                 json={"name": "Varsayılan düzen", "academic_year_id": year_id})
        if response.status_code != 201:
            raise RuntimeError(f"Derslik düzeni eklenemedi: {response.text}")
        layout_id = response.json()["layout"]["id"]

        columns = 4
        response = requests.post(f"{api}/classrooms/{classroom_id}/layouts/{layout_id}/generate", timeout=60,
                                 json={"columns": columns, "column_lengths": [5] * columns,
                                       "cell_seats": [[2] * 5 for _ in range(columns)],
                                       "aisle_after": [True, False, True]})
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Oturma planı üretilemedi: {response.text}")

    groups = requests.get(f"{api}/student-groups", params={"academic_year_id": year_id}, timeout=30).json()["groups"]
    if not groups:
        raise RuntimeError("Sentetik öğrenci grupları oluşmadı.")


def pytest_configure(config) -> None:
    """Test modülleri içe alınmadan önce yerel servisi hazırla."""
    global _server, _data_dir, _log_handle
    if os.environ.get("KELEBEK_PUBLIC_URL"):
        return

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    _data_dir = tempfile.mkdtemp(prefix="kelebek-e2e-")
    log_path = Path(_data_dir) / "server.log"
    _log_handle = log_path.open("w", encoding="utf-8")
    environment = {
        **os.environ,
        "KELEBEK_DATA_DIR": _data_dir,
        "KELEBEK_NO_BROWSER": "1",
        "KELEBEK_PORT": str(port),
        "PYTHONPATH": str(ROOT / "backend"),
        "PYTHONUTF8": "1",
    }
    _server = subprocess.Popen([sys.executable, str(LAUNCH)], env=environment,
                               stdout=_log_handle, stderr=subprocess.STDOUT)
    try:
        _wait_for_health(base_url, _server)
        _seed(base_url)
    except Exception:
        sys.stderr.write(log_path.read_text(encoding="utf-8", errors="replace"))
        pytest_unconfigure(config)
        raise
    os.environ["KELEBEK_PUBLIC_URL"] = base_url
    # ui_state.json gibi dosyaları okuyan testler servisin veri klasörünü bilsin.
    os.environ["KELEBEK_DATA_DIR"] = _data_dir


def pytest_unconfigure(config) -> None:
    """Testlerden sonra yerel servisi kapat ve geçici veri klasörünü sil."""
    global _server, _data_dir, _log_handle
    if _server is not None:
        if _server.poll() is None:
            _server.terminate()
            try:
                _server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                _server.kill()
                _server.wait(timeout=10)
        _server = None
    if _log_handle is not None:
        _log_handle.close()
        _log_handle = None
    if _data_dir is not None:
        shutil.rmtree(_data_dir, ignore_errors=True)
        _data_dir = None
        os.environ.pop("KELEBEK_DATA_DIR", None)
    os.environ.pop("KELEBEK_PUBLIC_URL", None)
