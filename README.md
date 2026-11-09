# Kelebek Sınav Sistemi

macOS ve Windows'ta çevrimdışı çalışacak yerel sınav organizasyonu uygulaması.
Proje kapsamı için [ana karar belgesine](docs/Kelebek_Sinav_Sistemi_Ana_Proje_Karar_Dokumani_v4.3.md),
teknik seçimler için [teknik mimariye](docs/Kelebek_Sinav_Sistemi_Teknik_Mimari_v1.0.md) bakın.

## Geliştirme ortamı

Gereksinimler: Python 3.12 veya üzeri, Node.js 22.12 veya üzeri ve npm. Kurulum betikleri bilgisayarda bulunan 3.12+ Python sürümünü kendisi seçer.

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

## Testler

```bash
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests   # birim testleri
PYTHONPATH=backend .venv/bin/python -m pytest tests/e2e                     # uçtan uca API testleri
.venv/bin/ruff check backend scripts packaging tests                        # lint
npm --prefix frontend run build                                             # arayüz derlemesi
```

(Windows'ta `.venv\Scripts\python.exe` kullanın; `PYTHONPATH` için `$env:PYTHONPATH = "backend"`.)

Uçtan uca testler hazırlık istemez: geçici bir veri klasöründe yerel servisi kendileri
açar ve sentetik okul verisini kurar. Gerçek öğrenci verisi hiçbir teste girmez. Hazır bir
ortama bağlanmak isterseniz `KELEBEK_PUBLIC_URL` verin; o zaman yerel servis açılmaz.

Her gönderimde ve birleştirme isteğinde GitHub Actions *Testler* iş akışı Ubuntu, macOS ve
Windows'ta lint ile birim testlerini, ayrıca arayüz derlemesini ve uçtan uca testleri çalıştırır.

## Kurulum paketleri (macOS ve Windows)

Paketler her işletim sisteminin kendisinde üretilir (Mac'te Windows paketi, Windows'ta Mac paketi üretilmez).

- **macOS (Apple Silicon):** `./scripts/build-macos.sh` → `dist/KelebekSinavSistemi-<sürüm>-macos-arm64.dmg`. DMG'yi açıp uygulamayı *Uygulamalar* klasörüne sürükleyin. Paket ad-hoc imzalanır (Apple Silicon imzasız ikili dosyayı çalıştırmaz); Apple geliştirici kimliğiyle imzalanmadığı için ilk açılışta Finder'da sağ tık → *Aç* ile onaylanır.
- **Windows (x64):** PowerShell'de `./scripts/build-windows.ps1` → `dist\KelebekSinavSistemi-<sürüm>-windows-x64.zip` ve Inno Setup kuruluysa `...-kurulum.exe`. Kurulum yönetici yetkisi istemez, masaüstü kısayolu oluşturur.
- **Bilgisayar kurmadan:** Depo GitHub'a gönderildiğinde *Actions → Paketleri oluştur → Run workflow* iki platform paketini birlikte üretir; çıktılar iş akışı sonuçlarından indirilir.

Uygulama açıldığında yerel servis `127.0.0.1` üzerinde boş bir portta başlar ve varsayılan tarayıcı açılır. Uygulama zaten çalışıyorsa yeni servis açılmaz, mevcut adres açılır. Kapatmak için üst çubuktaki **Uygulamayı kapat** düğmesini kullanın (Windows'ta konsol penceresini kapatmak da yeterlidir); tüm sekmeler kapandıktan 10 dakika sonra servis kendiliğinden kapanır. Kullanıcı verileri paket klasöründe değil, aşağıdaki veri konumunda kalır; güncelleme veya yeniden kurulum verileri silmez.

CI'da her paket üretildikten sonra `packaging/smoke_test.py` paketlenmiş uygulamayı geçici veri klasörüyle açar; sağlık kontrolü, arayüz, veritabanı oluşturma ve kapatma doğrulanmadan iş akışı başarılı sayılmaz. Aynı testi paketi ürettiğiniz bilgisayarda `python packaging/smoke_test.py` ile de çalıştırabilirsiniz.

## Artımlı güncelleme

**Tek komutla sürüm (önerilen):** Paketleri ürettiğiniz bilgisayarda

```bash
.venv/bin/python scripts/release.py --version 0.3.0 --notes "Yeni özellik" --notes "Düzeltme"
```

(Windows: `.venv\Scripts\python.exe scripts\release.py ...`). Komut sürüm numarasını ve uygulama içi "Yenilikler" notlarını günceller, testleri çalıştırıp tam kurulum paketini üretir, önceki sürüm kopyası `releases/<platform>/` altında varsa imzalı güncelleme paketini de hazırlar ve bu sürümü bir sonraki için saklar. Çıktılar `dist/` içindedir. `releases/` klasörünü silmeyin; Git'e girmez. Kullanıcılar güncellemeden sonraki ilk açılışta notları kısa bir pencerede görür.

**İlk kez (bir defa):** Paketleri ürettiğiniz bilgisayarda `python scripts/update_signing.py init` çalıştırın. Gizli imzalama anahtarı `~/.kelebek-signing/update_signing_key.pem` dosyasına yazılır, açık anahtar `backend/kelebek/update_trust.py` dosyasına eklenir. Bu değişikliği kaydedip yeni **tam kurulum paketini** üretin ve kurun; bundan sonra kurulum yalnızca bu anahtarla imzalanmış güncellemeleri kabul eder. Gizli anahtarı Git'e eklemeyin, kimseyle paylaşmayın ve güvenli bir yere yedekleyin; kaybolursa yeni anahtar için yine tam kurulum gerekir. Yayıncı anahtarı tanımlı olmayan kurulumlar hiçbir güncelleme paketini kabul etmez.

Yeni sürümün tam paketi üretildikten sonra yalnızca değişen dosyaları içeren, imzalı güncelleme paketi hazırlanır:

```bash
python scripts/make_update_package.py --old "<eski sürüm>/Kelebek Sınav Sistemi.app" --new "dist/Kelebek Sınav Sistemi.app" \
  --platform macos-arm64 --from-version 0.2.0 --to-version 0.3.0 --out dist
```

Windows için `--old`/`--new` olarak `KelebekSinavSistemi` klasörlerini ve `--platform windows-x64` verin. Paket `manifest.json` (sürümler, platform, değişen/kaldırılan dosyalar, SHA-256, migration aralığı), manifestin Ed25519 imzası `manifest.sig` ve yanında `.sha256` özet dosyası içerir. Uygulama imzayı gömülü açık anahtarla doğrular; imzasız, başka anahtarla imzalanmış veya sonradan değiştirilmiş paketleri reddeder.

Uygulamada **Yedek ve arşiv → Uygulama güncellemesi** bölümünde paket seçilir: sürüm ve platform kontrol edilir, tüm dosyalar geçici klasörde hash ile doğrulanır ve özet gösterilir. Onaydan sonra güvenlik yedeği alınır, uygulama kapanır; dış güncelleyici değişen dosyaların ve veritabanının kopyasını ayırıp yeni dosyaları yerleştirir. Yeni sürüm migration'ları uygulayıp açılış kontrolünü geçerse etkin kalır; geçemezse önceki dosyalar ve veritabanı otomatik geri yüklenir ve eski sürüm açılır. Sonuç aynı bölümde gösterilir. Uygulama klasör yapısı değiştiren büyük sürümlerde tam kurulum paketi kullanın.

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
