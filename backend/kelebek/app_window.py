"""Uygulama penceresi: arayüzü tarayıcı sekmesi yerine adres çubuksuz, bağımsız bir pencerede açar.

Ek bir kütüphane ya da gömülü tarayıcı kullanılmaz. Bilgisayarda zaten bulunan
Chromium tabanlı tarayıcı (Windows'ta sistemle gelen Edge) "uygulama kipinde"
ve kendi profiliyle başlatılır; böylece pencere kullanıcının tarayıcı oturumundan
bağımsızdır ve kapanması uygulamanın kapanması demektir. Uygun tarayıcı yoksa
başlatıcı eskisi gibi varsayılan tarayıcıda sekme açar (Karar 74).
"""

from __future__ import annotations

import contextlib
import json
import logging
import ntpath
import os
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger("kelebek.app_window")

WINDOW_CLASS = "kelebek-sinav-sistemi"
PROFILE_DIRECTORY = "window-profile"
SETTING_KEY = "app_window"

_WINDOWS_BROWSERS = (
    ("ProgramFiles(x86)", r"Microsoft\Edge\Application\msedge.exe"),
    ("ProgramFiles", r"Microsoft\Edge\Application\msedge.exe"),
    ("LOCALAPPDATA", r"Microsoft\Edge\Application\msedge.exe"),
    ("ProgramFiles", r"Google\Chrome\Application\chrome.exe"),
    ("ProgramFiles(x86)", r"Google\Chrome\Application\chrome.exe"),
    ("LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe"),
    ("ProgramFiles", r"BraveSoftware\Brave-Browser\Application\brave.exe"),
)
_MAC_BROWSERS = (
    "Google Chrome.app/Contents/MacOS/Google Chrome",
    "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "Brave Browser.app/Contents/MacOS/Brave Browser",
    "Chromium.app/Contents/MacOS/Chromium",
)
_LINUX_BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
                   "microsoft-edge", "microsoft-edge-stable", "brave-browser")


def find_app_browser(platform: str, env: dict, which: Callable[[str], str | None] = shutil.which,
                     exists: Callable[[str], bool] = os.path.exists) -> str | None:
    """Uygulama kipini destekleyen kurulu tarayıcının yolunu döndür; yoksa ``None``."""
    if platform == "win32":
        for variable, relative in _WINDOWS_BROWSERS:
            base = env.get(variable)
            if base and exists(candidate := ntpath.join(base, relative)):
                return candidate
        return None
    if platform == "darwin":
        roots = ["/Applications"]
        if env.get("HOME"):
            roots.append(f"{env['HOME']}/Applications")
        for root in roots:
            for relative in _MAC_BROWSERS:
                if exists(candidate := f"{root}/{relative}"):
                    return candidate
        return None
    for name in _LINUX_BROWSERS:
        if found := which(name):
            return found
    return None


def build_command(executable: str, url: str, profile_dir: Path, platform: str = sys.platform) -> list[str]:
    command = [
        executable,
        f"--app={url}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        "--disable-features=Translate",  # arayüz Türkçe; çeviri önerisi açılmasın
        "--window-size=1360,900",
    ]
    if platform.startswith("linux"):
        command.append(f"--class={WINDOW_CLASS}")  # .desktop dosyasındaki StartupWMClass ile eşleşir
    return command


def _read_state(data_dir: Path) -> dict:
    try:
        state = json.loads((data_dir / "ui_state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def window_mode_enabled(data_dir: Path, env: dict) -> bool:
    """Kendi penceresinde açma açık mı? Varsayılan açık; ayar ya da ortam değişkeni kapatır."""
    if env.get("KELEBEK_BROWSER_TAB"):
        return False
    return _read_state(data_dir).get(SETTING_KEY, True) is not False


def set_window_mode(data_dir: Path, enabled: bool) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    state = {**_read_state(data_dir), SETTING_KEY: bool(enabled)}
    (data_dir / "ui_state.json").write_text(json.dumps(state), encoding="utf-8")


def open_app_window(url: str, data_dir: Path, platform: str = sys.platform, env: dict | None = None,
                    which: Callable[[str], str | None] = shutil.which,
                    exists: Callable[[str], bool] = os.path.exists,
                    popen: Callable[..., object] = subprocess.Popen):
    """Pencereyi aç ve tarayıcı sürecini döndür; açılamazsa ``None`` (çağıran sekmeye düşer)."""
    executable = find_app_browser(platform, os.environ if env is None else env, which, exists)
    if not executable:
        return None
    profile_dir = data_dir / PROFILE_DIRECTORY
    try:
        profile_dir.mkdir(parents=True, exist_ok=True)
        return popen(build_command(executable, url, profile_dir, platform),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as error:
        logger.warning("Uygulama penceresi açılamadı: %s", error)
        return None


def watch_window(process, on_closed: Callable[[], None], handoff_seconds: float = 4.0,
                 background: bool = True) -> None:
    """Pencere kapanınca ``on_closed`` çağır.

    Tarayıcı ilk birkaç saniyede çıkarsa pencere kapatılmamış, adres aynı profildeki
    açık bir sürece devredilmiştir; bu durumda uygulama kapatılmaz (boşta kalma
    süresi yine geçerlidir).
    """
    def run() -> None:
        try:
            process.wait(timeout=handoff_seconds)
            return
        except subprocess.TimeoutExpired:
            pass
        process.wait()
        on_closed()

    if background:
        threading.Thread(target=run, daemon=True, name="kelebek-pencere").start()
    else:
        run()


def close_window(process) -> None:
    """Uygulama kapanırken pencere açık kaldıysa onu da kapat."""
    if process is None:
        return
    with contextlib.suppress(Exception):
        if process.poll() is None:
            process.terminate()
