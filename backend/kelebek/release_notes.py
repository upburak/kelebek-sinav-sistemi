"""Uygulama içi "Yenilikler" notları. `scripts/release.py --notes` yeni sürümün notlarını başa ekler."""

RELEASE_NOTES = [
  {
    "version": "0.3.0",
    "date": "2026-11-09",
    "items": [
      "macOS kurulumunda arayüzün hiç açılmamasına yol açan statik dosya hatası giderildi",
      "Rapor PDF'lerinde Türkçe harfler yazı tipi bulunamadığında da doğru yazılıyor",
      "macOS'ta artımlı güncelleme sonrası uygulama paketi yeniden imzalanıyor",
      "Kurulum betikleri Python 3.12 ve üzeri tüm sürümleri kabul ediyor",
      "Her değişiklikte Mac, Windows ve Linux'ta otomatik test çalışıyor"
    ]
  },
  {
    "version": "0.2.0",
    "date": "2026-11-09",
    "items": [
      "Derslik sabitleyerek yeniden dağıtım ve sınavı tamamlayıp arşivleme",
      "Güncel öğrenci listesiyle karşılaştırma ve tek sekmede düzenleme",
      "İhlal krokisi, çözüm önerisi ve \"Tümünü düzelt\"",
      "Dağıtım ilerleme ekranı ve durdurma",
      "İmzalı artımlı güncelleme ve otomatik geri dönüş"
    ]
  }
]
