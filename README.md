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

Vite arayüzü varsayılan olarak `http://127.0.0.1:5173` adresinde açılır. Geliştirme başlatıcısı Flask API'si için önce `127.0.0.1:5000` portunu dener, doluysa `5001–5100` aralığındaki ilk boş porta geçer; seçilen porta Vite API proxy'sini kendisi yönlendirir. Her iki adres de yalnızca yerel bilgisayarda dinler. Arayüz portu gerekirse `KELEBEK_UI_PORT` ile değiştirilebilir. Geliştirme sunucusu API sağlık kontrolünü `/api/health` üzerinden sağlar.

## Veri güvenliği

Öğrenci verileri ve SQLite veritabanı kaynak kod klasöründe tutulmaz. Uygulama verileri macOS kullanıcı hesabında `~/Library/Application Support/Kelebek Sinav Sistemi`, Windows kullanıcı hesabında `%APPDATA%\Kelebek Sinav Sistemi` altında saklanır. Geliştirme betikleri de bu işletim sistemi veri konumlarını kullanır; uygulama verileri proje klasörünün dışında kalır. `KELEBEK_DATA_DIR` yalnızca özel, yerel denemelerde geçici bir veri dizini seçmek için kullanılabilir.

Gerçek öğrenci listeleri, veritabanları, yedekler, dışa aktarımlar ve sırlar Git'e eklenmez.
Sentetik örnek verileri kullanın. `.gitignore` güvenli varsayılanları içerir.

## Faz A kapsamı

- Flask uygulama fabrikası, yerel sağlık kontrolü ve eğitim-öğretim yılı seçimi.
- React + TypeScript + Vite geliştirme arayüzü ve API proxy'si.
- macOS/Windows kullanıcı veri dizini çözümlemesi ve günlük altyapısı.
- Her iki işletim sistemi için kurulum ve geliştirme başlatma betikleri.

SQLite ve Alembic migration altyapısı eklendi. Eğitim-öğretim yılı ilk açılışta oluşturulur ve başlangıçta güncel yıl seçilir. Faz C kapsamında e-Okul XLSX önizleme ve aktarım akışı hazırlandı; sonraki işlevler mimarideki sıraya göre eklenecektir.

e-Okul aktarım başlangıcı `.xlsx` dosyasını yalnızca bellekte önizler; kullanıcı sütunları eşler, teknik kontrolleri ve seçili yılın fark raporunu inceler. Veritabanına aktarım ayrı bir açık onay düğmesiyle yapılır. Eksik listeden ayrılan öğrenciler silinmez, pasif duruma alınır.

Derslik verisi için sürümlü düzen, fiziksel masa ve ayrı koltuk tabloları eklendi. Kullanılabilir kapasite, düzende açık olan oturma yerlerinden hesaplanır.

Derslik ekranında satır sayısı, blok başına masa sayısı ve masa başına tekli/ikili/üçlü oturma yeri seçilerek başlangıç planı oluşturulabilir. Plan numaralı koltuklarla bloklar halinde görüntülenir; gerçek sınıf ölçüleri kullanıcı tarafından girilir.

Mevcut bir plan düzenlenirken yeni sürüm kopyalanır; eski sürüm korunur. Yeni sürümde masalar sürüklenebilir ve oturma yerleri kullanılabilir/kullanım dışı olarak işaretlenebilir. Değişiklikler yerel veritabanına kaydedilir.
