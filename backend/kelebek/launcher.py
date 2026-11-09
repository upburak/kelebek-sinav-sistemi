"""Masaüstü başlatıcısı: yerel servisi açar, tarayıcıyı başlatır, tek örnek çalıştırır."""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from kelebek.config import get_data_dir

IDLE_SHUTDOWN_SECONDS = 10 * 60
logger = logging.getLogger("kelebek.launcher")


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def frontend_dist() -> Path:
    override = os.environ.get("KELEBEK_FRONTEND_DIST")
    if override:
        return Path(override)
    root = _resource_root()
    bundled = root / "frontend_dist"
    return bundled if bundled.is_dir() else root / "frontend" / "dist"


def _instance_file() -> Path:
    return get_data_dir() / "instance.json"


def _running_instance_url() -> str | None:
    try:
        info = json.loads(_instance_file().read_text(encoding="utf-8"))
        url = f"http://127.0.0.1:{int(info['port'])}"
        with urllib.request.urlopen(f"{url}/api/health", timeout=1.5) as response:
            if response.status == 200:
                return url
    except (OSError, ValueError, KeyError):
        return None
    return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> None:
    existing = _running_instance_url()
    if existing:
        webbrowser.open(existing)
        return

    from waitress.server import create_server

    from kelebek import create_app

    port = int(os.environ.get("KELEBEK_PORT") or _free_port())
    allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
    app = create_app(frontend_dist=frontend_dist(), allowed_hosts=allowed)
    app.config["KELEBEK_DESKTOP"] = True
    state = {"last_request": time.monotonic()}

    @app.before_request
    def _touch():
        state["last_request"] = time.monotonic()

    server = create_server(app, host="127.0.0.1", port=port, threads=4)
    app.extensions["kelebek_shutdown"] = server.close
    verify_file = os.environ.pop("KELEBEK_UPDATE_VERIFY", None)
    if verify_file:
        from kelebek.services.app_update import write_verification

        write_verification(verify_file)

    @app.post("/api/app/shutdown")
    def _shutdown():
        threading.Timer(0.5, server.close).start()
        return {"stopping": True}

    def _idle_watch():
        while True:
            time.sleep(30)
            if time.monotonic() - state["last_request"] > IDLE_SHUTDOWN_SECONDS:
                logger.info("Uzun süre kullanılmadığı için yerel servis kapatılıyor.")
                server.close()
                return

    instance = _instance_file()
    instance.parent.mkdir(parents=True, exist_ok=True)
    instance.write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")
    threading.Thread(target=_idle_watch, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    if not os.environ.get("KELEBEK_NO_BROWSER"):
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    if sys.stdout is not None:
        try:
            print(f"Kelebek Sınav Sistemi çalışıyor: {url}  (kapatmak için bu pencereyi kapatın)", flush=True)
        except (UnicodeEncodeError, OSError):
            pass
    try:
        server.run()
    except (KeyboardInterrupt, OSError):
        pass
    finally:
        app.extensions["kelebek_engine"].dispose()
        try:
            if json.loads(instance.read_text(encoding="utf-8")).get("pid") == os.getpid():
                instance.unlink()
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    main()
