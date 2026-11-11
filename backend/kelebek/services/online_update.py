"""Çevrim içi sürüm denetimi: GitHub'daki son sürümü sorar, kurulum paketini indirir.

Uygulama çevrimdışı çalışmaya devam eder; bu modül yalnızca kullanıcı isterse ya
da açılış denetimi açıksa internete çıkar. Gönderilen tek şey sürüm sorgusudur:
okul, öğrenci ya da kullanım verisi hiçbir yere gönderilmez.

İndirilen paket yalnızca projenin kendi sürüm adresinden kabul edilir ve
GitHub'ın bildirdiği SHA-256 özetiyle doğrulanır. Kurulumu kullanıcı başlatır;
kullanıcı verisi kurulum klasöründen ayrı durduğu için güncellemede korunur.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from kelebek.version import APP_VERSION

logger = logging.getLogger(__name__)

REPOSITORY = "upburak/kelebek-sinav-sistemi"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_PAGE_URL = f"https://github.com/{REPOSITORY}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/"
TIMEOUT_SECONDS = 8
MAX_PACKAGE_BYTES = 400 * 1024 * 1024


class OnlineUpdateError(Exception):
    """Kullanıcıya gösterilebilecek, beklenen bir güncelleme hatası."""


def parse_version(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(value).lstrip("vV").split("."))
    except ValueError:
        return (0,)


def _ssl_contexts() -> list[ssl.SSLContext]:
    """Önce işletim sisteminin sertifika deposu, olmazsa paketle gelen kök sertifikalar.

    Okul ağlarında trafik denetleyen vekil sunucuların sertifikası yalnızca sistem
    deposunda bulunur; paketlenmiş macOS uygulamasında ise sistem deposu boş olabilir.
    """
    contexts = [ssl.create_default_context()]
    try:
        import certifi

        contexts.append(ssl.create_default_context(cafile=certifi.where()))
    except Exception:  # pragma: no cover - certifi yoksa yalnızca sistem deposu
        pass
    return contexts


def _open(url: str):
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "KelebekSinavSistemi-surum-denetimi",
    })
    last_error: Exception | None = None
    for context in _ssl_contexts():
        try:
            return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=context)
        except urllib.error.URLError as error:
            last_error = error
            if not isinstance(error.reason, ssl.SSLError):
                raise
    raise last_error or urllib.error.URLError("bağlantı kurulamadı")


def platform_kind() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "other"


def pick_asset(assets: list[dict], kind: str | None = None) -> dict | None:
    """Bu bilgisayara uygun kurulum paketini seç."""
    kind = kind or platform_kind()
    if kind == "macos" and platform.machine().lower() not in ("arm64", "aarch64"):
        return None  # yalnızca Apple Silicon paketi yayımlanıyor
    suffix = {"windows": "-kurulum.exe", "macos": ".dmg"}.get(kind)
    if not suffix:
        return None
    for asset in assets:
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if name.endswith(suffix) and url.startswith(DOWNLOAD_PREFIX):
            digest = str(asset.get("digest") or "")
            return {
                "name": name,
                "url": url,
                "size": int(asset.get("size") or 0),
                "sha256": digest.split(":", 1)[1] if digest.startswith("sha256:") else "",
            }
    return None


def check_latest(opener=None) -> dict:
    """Son yayımlanan sürümü sor ve kurulu sürümle karşılaştır."""
    opener = opener or _open
    try:
        with opener(LATEST_RELEASE_URL) as response:
            release = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        logger.info("Sürüm denetimi yapılamadı: HTTP %s", error.code)
        if error.code in (401, 403, 404):
            # Depo herkese açık değilse ya da henüz sürüm yoksa GitHub 404 döndürür.
            raise OnlineUpdateError(
                "Sürüm kaynağına erişilemiyor. Sürümler herkese açık yayımlanmadıysa çevrim içi "
                "denetim çalışmaz; yeni sürümü indirme sayfasından alabilirsiniz."
            ) from error
        raise OnlineUpdateError("Sürüm bilgisi alınamadı; daha sonra tekrar deneyin.") from error
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        logger.info("Sürüm denetimi yapılamadı: %s", error)
        raise OnlineUpdateError(
            "Sürüm bilgisi alınamadı. İnternet bağlantısını kontrol edip tekrar deneyin; "
            "uygulama internet olmadan da çalışmaya devam eder."
        ) from error
    latest = str(release.get("tag_name", "")).lstrip("vV")
    if not latest:
        raise OnlineUpdateError("Yayımlanmış sürüm bilgisi okunamadı.")
    asset = pick_asset(release.get("assets") or [])
    return {
        "current_version": APP_VERSION,
        "latest_version": latest,
        "update_available": parse_version(latest) > parse_version(APP_VERSION),
        "published_at": release.get("published_at"),
        "release_url": release.get("html_url") or RELEASES_PAGE_URL,
        "asset": asset,
        "platform": platform_kind(),
    }


def downloads_dir() -> Path:
    candidate = Path.home() / "Downloads"
    if candidate.is_dir():
        return candidate
    from kelebek.config import get_data_dir

    fallback = get_data_dir() / "downloads"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def download_package(asset: dict, target_dir: Path | None = None, opener=None) -> Path:
    """Kurulum paketini indir, özetini doğrula ve dosya yolunu döndür."""
    url, name = str(asset.get("url", "")), os.path.basename(str(asset.get("name", "")))
    if not url.startswith(DOWNLOAD_PREFIX) or not name or not name.startswith("KelebekSinavSistemi-"):
        raise OnlineUpdateError("Güncelleme paketi beklenen adresten gelmiyor; indirme yapılmadı.")
    expected = str(asset.get("sha256") or "").lower()
    if len(expected) != 64:
        raise OnlineUpdateError("Paketin doğrulama özeti bulunamadı; güvenlik nedeniyle indirilmedi.")
    opener = opener or _open
    target_dir = target_dir or downloads_dir()
    target = target_dir / name
    partial = target_dir / (name + ".indiriliyor")
    digest, total = hashlib.sha256(), 0
    try:
        with opener(url) as response, partial.open("wb") as output:
            while True:
                block = response.read(1024 * 256)
                if not block:
                    break
                total += len(block)
                if total > MAX_PACKAGE_BYTES:
                    raise OnlineUpdateError("Paket beklenenden büyük; indirme durduruldu.")
                digest.update(block)
                output.write(block)
        if digest.hexdigest() != expected:
            raise OnlineUpdateError("İndirilen paket doğrulanamadı (özet uyuşmuyor). Dosya silindi; tekrar deneyin.")
        os.replace(partial, target)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise OnlineUpdateError("Paket indirilemedi. İnternet bağlantısını kontrol edip tekrar deneyin.") from error
    finally:
        partial.unlink(missing_ok=True)
    return target


def open_package(path: Path) -> bool:
    """Kurulum paketini işletim sisteminin kendi yöntemiyle aç."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
            return True
    except OSError as error:
        logger.warning("Kurulum paketi açılamadı: %s", error)
    return False
