#!/usr/bin/env python3
"""Güncelleme imzalama anahtarı yönetimi.

  python scripts/update_signing.py init   # bir kez: gizli anahtarı üretir, açık anahtarı uygulamaya ekler
  python scripts/update_signing.py show   # açık anahtarı ve parmak izini gösterir

Gizli anahtar varsayılan olarak ~/.kelebek-signing/update_signing_key.pem dosyasında durur.
Bu dosyayı Git'e eklemeyin, kimseyle paylaşmayın ve güvenli bir yere yedekleyin; kaybolursa
mevcut kurulumlar yeni güncellemeleri kabul etmez (tam kurulum paketi gerekir).
"""

import argparse
import base64
import hashlib
import os
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
TRUST_FILE = ROOT / "backend" / "kelebek" / "update_trust.py"
DEFAULT_KEY = Path(os.environ.get("KELEBEK_SIGNING_KEY", Path.home() / ".kelebek-signing" / "update_signing_key.pem"))


def load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("İmzalama anahtarı Ed25519 değil.")
    return key


def public_key_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode()


def fingerprint(public_b64: str) -> str:
    return hashlib.sha256(base64.b64decode(public_b64)).hexdigest()[:16]


def sign(key_path: Path, data: bytes) -> str:
    return base64.b64encode(load_private_key(key_path).sign(data)).decode()


def trust(public_b64: str, trust_file: Path = TRUST_FILE) -> bool:
    text = trust_file.read_text(encoding="utf-8")
    match = re.search(r"TRUSTED_PUBLIC_KEYS: list\[str\] = \[(.*?)\]", text, re.S)
    keys = re.findall(r'"([A-Za-z0-9+/=]+)"', match.group(1)) if match else []
    if public_b64 in keys:
        return False
    keys.append(public_b64)
    body = "".join(f'\n    "{item}",' for item in keys) + "\n"
    trust_file.write_text(text[:match.start()] + f"TRUSTED_PUBLIC_KEYS: list[str] = [{body}]" + text[match.end():], encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["init", "show"])
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY)
    args = parser.parse_args()
    if args.command == "init":
        if not args.key.exists():
            args.key.parent.mkdir(parents=True, exist_ok=True)
            pem = Ed25519PrivateKey.generate().private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
            args.key.write_bytes(pem)
            if os.name != "nt":
                args.key.chmod(0o600)
            print(f"Yeni gizli anahtar oluşturuldu: {args.key}")
        else:
            print(f"Mevcut gizli anahtar kullanılıyor: {args.key}")
    if not args.key.exists():
        sys.exit(f"Gizli anahtar bulunamadı: {args.key}. Önce 'init' çalıştırın.")
    public_b64 = public_key_b64(load_private_key(args.key))
    print(f"Açık anahtar: {public_b64}\nParmak izi: {fingerprint(public_b64)}")
    if args.command == "init":
        added = trust(public_b64)
        print("Açık anahtar uygulamaya eklendi; değişikliği kaydedip yeni tam paketi üretin." if added
              else "Açık anahtar zaten uygulamada tanımlı.")


if __name__ == "__main__":
    main()
