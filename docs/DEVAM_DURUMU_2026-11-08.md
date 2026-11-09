# Kelebek Sınav Sistemi — devam notu

Son güncelleme: 9 Kasım 2026 (sürüm 0.2.0)

Kapsam ve kararlar için ana karar belgesi v4.3 ile teknik mimari v1.0 esas alınır; 72 karar değiştirilmedi.

## Bu oturumda tamamlananlar

- Kalan rapor seçenekleri: üst bilgi alanları göster/gizle, özel başlık, yazı ölçeği; rapor öncesi hazır onayı, ihlal kabulü, bekleyen öğrenci engeli. Arşivlenmiş sınavda rapor durumu değiştirilmez.
- Derslik sabitleyerek yeniden dağıtım (Karar 25) — `pinned_classroom_ids`, `base_candidate_id`.
- Güncel öğrenci listesiyle karşılaştırma ve onaylı havuza alma (Karar 39).
- Tek düzenleme oturumu / önizleme modu (Karar 40) — bellekte kilit, 30 sn TTL, `X-Kelebek-Tab` başlığı.
- Tamamlandı/arşiv ve çalışma kopyası (Karar 68–70) — migration `0017_exam_archive_and_pins`.
- Masaüstü başlatıcı, PyInstaller tarifi, macOS/Windows paketleme betikleri ve GitHub Actions iş akışı. Linux'ta PyInstaller derlemesi denendi: dondurulmuş uygulama migration'ları uyguladı, arayüzü ve API'yi sundu.

## Son doğrulama

- `PYTHONPATH=backend:backend/tests .venv/bin/python -m unittest discover -s backend/tests` — 22 test geçti.
- `frontend/` içinde `npm run build` — başarılı. Uçtan uca tarayıcı testi sentetik veriyle geçti.

## Açık kalanlar

- macOS ve Windows paketlerinin gerçek cihazlarda/CI'da üretilip denenmesi; kod imzalama ve notarization (isteğe bağlı).
- Artımlı güncelleme paketi (manifest, hash, migration aralığı, rollback) — Faz J'nin kalan kısmı.
- Hibrit çoklu pencere çalışma alanı (Karar 18–19), dağıtım ilerleme ekranı/durdurma (Karar 58), ihlal listesi ve krokide vurgulama (Karar 55), kural ihlali kabulünün işlem geçmişine yazılması (Karar 50).
- Önizleme ortamı için eklenen `backend/server.py` yalnızca bulut önizleme adaptörüdür; yerel çalışmayı etkilemez.
