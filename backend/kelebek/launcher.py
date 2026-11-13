"""Masaüstü başlatıcısı: yerel servisi açar, tarayıcıyı başlatır, tek örnek çalıştırır."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

from kelebek.config import get_data_dir

IDLE_SHUTDOWN_SECONDS = 10 * 60
logger = logging.getLogger("kelebek.launcher")
MISSING_FRONTEND_PAGE = """<!doctype html><html lang="tr"><meta charset="utf-8">
<title>Kelebek Sınav Sistemi</title>
<body style="font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem;line-height:1.5">
<h1>Uygulama dosyaları eksik</h1>
<p>Kelebek Sınav Sistemi açıldı ama arayüz dosyalarını bulamadı. Verileriniz yerinde duruyor.</p>
<p>Uygulamayı kapatıp en güncel kurulum paketini yeniden kurun; sorun sürerse paketi yeniden indirin.</p>
</body></html>"""


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


def _serves_app(url: str) -> bool:
    """Adresteki servis bu uygulamanın masaüstü örneği mi ve arayüzü sunuyor mu?"""
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=1.5) as response:
            health = json.loads(response.read().decode("utf-8"))
        if health.get("service") != "kelebek-sinav-sistemi" or not health.get("desktop"):
            return False
        with urllib.request.urlopen(f"{url}/", timeout=1.5) as response:
            return response.status == 200 and b'id="root"' in response.read()
    except (OSError, ValueError, AttributeError):
        return False


def _running_instance_url() -> str | None:
    """Kayıtlı örnek gerçekten çalışan uygulamaysa adresini döndür.

    Kayıt eski kalmış ya da aynı portu arayüzsüz bir geliştirme sunucusu almış
    olabilir; öyleyse tarayıcı boş bir "Not Found" sayfasına gider. Bu durumda
    kayıt yok sayılır ve yeni örnek başlatılır.
    """
    try:
        info = json.loads(_instance_file().read_text(encoding="utf-8"))
        url = f"http://127.0.0.1:{int(info['port'])}"
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return url if _serves_app(url) else None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _ensure_standard_streams() -> None:
    """Pencereli kipte (komut penceresi yok) çıktı akışları ``None`` olur; yazan kod çökmesin."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115 - süreç boyunca açık kalır


def _report_fatal(error: BaseException) -> None:
    """Açılış hatasını günlüğe yaz; komut penceresi olmadığı için Windows'ta ileti kutusu göster."""
    log_path = get_data_dir() / "logs" / "launcher-error.log"
    with contextlib.suppress(OSError):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            traceback.print_exception(type(error), error, error.__traceback__, file=handle)
    if sys.platform == "win32":
        with contextlib.suppress(Exception):
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                f"Uygulama açılamadı.\n\n{error}\n\nAyrıntılar şu dosyaya yazıldı:\n{log_path}",
                "Kelebek Sınav Sistemi", 0x10)


def main() -> None:
    _ensure_standard_streams()
    try:
        _run()
    except Exception as error:
        # Sessiz kapanma yerine neden gösterilir; ikinci bir sistem hata penceresi açılmasın diye
        # süreç hata koduyla düzgün sonlandırılır.
        _report_fatal(error)
        raise SystemExit(1) from error


def _run() -> None:
    existing = _running_instance_url()
    if existing:
        webbrowser.open(existing)
        return

    from waitress.server import create_server

    from kelebek import create_app

    port = int(os.environ.get("KELEBEK_PORT") or _free_port())
    allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
    dist = frontend_dist()
    app = create_app(frontend_dist=dist, allowed_hosts=allowed)
    app.config["KELEBEK_DESKTOP"] = True
    if not (dist / "index.html").is_file():
        logger.error("Arayüz dosyaları bulunamadı: %s", dist)

        @app.get("/")
        def _missing_frontend():
            return MISSING_FRONTEND_PAGE, 500, {"Content-Type": "text/html; charset=utf-8"}
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
    # Terminalden başlatıldıysa adres yazılır; kod sayfası Türkçe harfleri basamazsa uygulama durmasın.
    with contextlib.suppress(UnicodeEncodeError, OSError, ValueError):
        print(f"Kelebek Sınav Sistemi çalışıyor: {url}  (kapatmak için arayüzdeki \"Uygulamayı kapat\" düğmesini kullanın)", flush=True)
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
