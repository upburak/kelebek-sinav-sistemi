# Kelebek Sınav Sistemi

macOS ve Windows'ta çevrimdışı çalışacak yerel sınav organizasyonu uygulaması.
Proje kapsamı için [ana karar belgesine](docs/Kelebek_Sinav_Sistemi_Ana_Proje_Karar_Dokumani_v4.3.md),
teknik seçimler için [teknik mimariye](docs/Kelebek_Sinav_Sistemi_Teknik_Mimari_v1.0.md) bakın.

## Geliştirme ortamı

Gereksinimler: Python 3.12, Node.js 22.12 veya üzeri ve npm.

### macOS

```bash
./scripts/setup-macos.sh
./scripts/dev-macos.sh
```

### Windows (PowerShell)

```powershell
./scripts/setup-windows.ps1
./scripts/dev-windows.ps1
```

Vite arayüzü `http://127.0.0.1:5173`, Flask API'si yalnızca `127.0.0.1:5000` adresinde açılır.
Geliştirme sunucusu API sağlık kontrolünü `/api/health` üzerinden sağlar.

## Veri güvenliği

Öğrenci verileri ve SQLite veritabanı kaynak kod klasöründe tutulmaz. Uygulama verileri
macOS'ta `~/Library/Application Support/Kelebek Sinav Sistemi`, Windows'ta
`%APPDATA%\Kelebek Sinav Sistemi` altına yazılır. Geliştirme sırasında `KELEBEK_DATA_DIR`
değişkeni veri klasörünü proje içindeki Git tarafından yoksayılan `.local-data/` dizinine yönlendirir.

Gerçek öğrenci listeleri, veritabanları, yedekler, dışa aktarımlar ve sırlar Git'e eklenmez.
Sentetik örnek verileri kullanın. `.gitignore` güvenli varsayılanları içerir.

## Faz A kapsamı

- Flask uygulama fabrikası ve yerel sağlık kontrolü.
- React + TypeScript + Vite geliştirme arayüzü ve API proxy'si.
- macOS/Windows kullanıcı veri dizini çözümlemesi ve günlük altyapısı.
- Her iki işletim sistemi için kurulum ve geliştirme başlatma betikleri.

SQLite şeması ve migration'lar, öğrenci aktarımı ve diğer işlevler mimarideki sıraya göre sonraki fazlarda eklenecektir.
