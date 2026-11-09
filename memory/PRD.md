# Kelebek Sınav Sistemi — PRD özeti
Orijinal istek: "bu uygulamaya devam etmeye çalışıyorum md leri oku öncelikle" → kullanıcı seçimi: kalan rapor seçenekleri, güncel liste karşılaştırma (K39), derslik sabitleyip yeniden dağıtım (K25), tek sekmede düzenleme (K40), tamamlama/arşiv/kopya (K68-70); "projeyi tamamlayıp mac ve windows ortamından bir an önce".
Mimari: Flask + SQLite/Alembic + OR-Tools CP-SAT + ReportLab/OpenPyXL; React+TS+Vite; çevrimdışı yerel (127.0.0.1). Önizleme için backend/server.py (a2wsgi) + frontend `start` betiği.
Kullanıcı: tek okul yöneticisi (giriş yok).
## 2026-11-09 yapılanlar (v0.2.0)
- Rapor üst bilgi/başlık/ölçek, hazır onayı, ihlal kabulü, bekleyen öğrenci engeli
- Sabitlemeli yeniden dağıtım; öğrenci farkı karşılaştırma/uygulama; sekme düzenleme kilidi; arşiv + çalışma kopyası (migration 0017)
- Masaüstü launcher, PyInstaller spec, build-macos.sh (DMG), build-windows.ps1 (ZIP+Inno Setup), GitHub Actions
- 22 unit test + e2e test geçti
## 2026-11-09 (2) yapılanlar
- İhlal krokisi (K55), dağıtım ilerleme + durdurma (K58), artımlı güncelleme + rollback, CI duman testi, çözücü grup dengesi hatası düzeltildi, yalnız ad değişikliğinde taslak adaylar korunuyor
## Backlog
P0: Mac/Windows paketlerini gerçek cihazda/CI'da üretip denemek
P1: Güncelleme paketi imzası; erken durdurulan adayın kartta etiketlenmesi; ExamOrganizer bileşen bölme
P2: Hibrit çoklu pencere çalışma alanı (K18-19); ihlal kabulünün geçmişe yazılması (K50)
