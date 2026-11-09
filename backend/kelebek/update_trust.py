"""Güncelleme paketlerini imzalayan yayıncı anahtarları (Ed25519 açık anahtarları, base64).

Bu listeyi elle düzenlemeyin; `python scripts/update_signing.py init` komutu kendi anahtarınızı ekler.
Liste boşsa uygulama hiçbir güncelleme paketini kabul etmez.
"""

TRUSTED_PUBLIC_KEYS: list[str] = []
