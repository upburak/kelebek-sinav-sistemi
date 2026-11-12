# Kelebek Sınav Sistemi — devam notu

Son güncelleme: 9 Kasım 2026 (sürüm 0.3.0)

Kapsam ve kararlar için ana karar belgesi v4.3 ile teknik mimari v1.0 esas alınır; 72 karar
değiştirilmedi. Bu oturumda yeni özellik eklenmedi; amaç projeyi macOS ve Windows'ta güvenle
çalıştırmadan önce bütün olarak test edip bulunan hataları gidermekti.

## Bu oturumda yapılan testler

- Birim testleri: 29 → 43 benzersiz test (yeni gerileme testleri; çifte koşum giderildi), tamamı geçiyor.
- Uçtan uca API testleri: 53 test, elle hazırlık gerekmeden geçiyor.
- Arayüz: `npm run build` (TypeScript + Vite) başarılı.
- Lint: `ruff` ile 117 bulgu vardı, tamamı giderildi; kural kümesi `pyproject.toml` içinde sabitlendi.
- Paketleme: PyInstaller ile paket üretildi, `packaging/smoke_test.py` geçti; paketlenmiş uygulama
  sembolik bağ içeren bir yoldan açılıp statik dosya sunumu ayrıca doğrulandı.

## Bulunan ve giderilen hatalar

1. **Arayüz hiç açılmıyordu (macOS'ta gerçekçi senaryo).** Kurulum yolu sembolik bağ içerdiğinde
   `_register_frontend` içindeki yol karşılaştırması çözümlenmemiş yolu çözümlenmiş üst klasörlerle
   kıyaslıyordu; JavaScript, CSS ve Excel indirme istekleri dosya yerine `index.html` döndürüyordu.
   Artık iki taraf da çözümleniyor, `is_relative_to` ile kontrol ediliyor; klasör dışı istekler
   reddedilmeye devam ediyor. Gerileme testi: `backend/tests/test_frontend_serving.py`.
2. **Rapor PDF'lerinde Türkçe harfler bozuluyordu.** Türkçe destekli sistem yazı tipi bulunamadığında
   sessizce Helvetica'ya dönülüyor, `Çağrı Işık Şükrü İpek` çıktıya `Çanrn Innk nükrü npek` olarak
   düşüyordu (ölçülerek doğrulandı). Yazı tipi adayları Windows/macOS/Linux için genişletildi, seçilen
   yazı tipinde Türkçe harflerin varlığı doğrulanıyor, hiçbiri yoksa metin okunabilir ASCII karşılığına
   sadeleştiriliyor ve günlüğe uyarı yazılıyor. Gerileme testi: `backend/tests/test_report_fonts.py`.
3. **macOS'ta artımlı güncelleme uygulamayı çalışmaz hale getiriyordu.** `.app` içindeki dosyalar
   değişince paket imzası geçersiz kalıyor, Apple Silicon çekirdeği imzası bozuk ikiliyi hiç
   çalıştırmıyor, güncelleme her seferinde geri dönüşe düşüyordu. Güncelleyici artık dosyaları
   yerleştirdikten ve geri aldıktan sonra karantinayı temizleyip paketi yeniden ad-hoc imzalıyor;
   `build-macos.sh` ürettiği paketi açıkça imzalayıp doğruluyor.
4. **Kurulum yalnızca Python 3.12 ile çalışıyordu.** `pyproject.toml` ">=3.12" demesine karşın
   betikler tam olarak `python3.12` veya Windows Python Launcher'ı arıyordu. İki betik de artık
   3.12 ve üzeri herhangi bir sürümü buluyor; `build-windows.ps1` aynı kurulum yolunu kullanıyor.

## CI'ın yakaladığı Windows hataları

Yeni iş akışının ilk koşusunda macOS, Ubuntu, uçtan uca ve arayüz işleri geçti;
**Windows birim testleri kırmızı yandı.** Yani iş akışı ilk gününde işini yaptı.

5. **İptal edilen geri yükleme önizlemesi kullanıcının veritabanı kopyasını geride
   bırakıyordu.** `discard_pending_restore` `ignore_errors=True` ile siliyor, silemese
   bile "iptal edildi" diyordu. Silme artık yeniden denenir ve sonucu dürüstçe günlüğe
   yazılır. Gerileme testi: `backend/tests/test_restore_staging_cleanup.py`.
6. **Üç yerde SQLite bağlantısı kapatılmıyordu.** `with sqlite3.connect(...)` bağlantıyı
   kapatmaz, yalnızca işlemi tamamlar; Windows'ta bu dosya kilidi demek. Geri yükleme
   şema doğrulaması, bütünlük kontrolü ve migration öncesi yedek `contextlib.closing`
   ile düzeltildi.
7. **Uygulama kapandıktan sonra dosya tutamağı bırakıyordu.** SQLite veritabanı ve
   `logs/application.log` açık kalıyordu; Windows'ta geçici veri klasörü silinemiyordu.
   Ortak `_support.release_app_resources` yardımcısı eklendi, `test_file_handles.py`
   açık tutamakları ölçerek sabitliyor. Günlük dosyası da artık güncel veri klasörünü izler.
8. **Testlerin bir bölümü iki kez çalışıyordu.** İki dosya başka bir test sınıfını modül
   düzeyinde içe aktardığı için `unittest` onları ikinci kez topluyordu; `BackupRestoreTests`
   her koşuda 8 yerine 16 test çalıştırıyordu. Süit artık 41 benzersiz test.

## Kullanışsız olup düzeltilen bölümler

- **Otomatik test yoktu.** Depoda yalnızca elle başlatılan paket iş akışı vardı; hiçbir test
  kendiliğinden çalışmıyordu. `.github/workflows/tests.yml` eklendi: her gönderimde ve birleştirme
  isteğinde Ubuntu/macOS/Windows'ta lint + birim testleri, ayrıca arayüz derlemesi ve uçtan uca testler.
- **README'nin söz verdiği CI duman testi iş akışında yoktu.** İki platformun paket işine eklendi.
- **Uçtan uca testler çalıştırılamıyordu.** `KELEBEK_PUBLIC_URL` yoksa atlanıyor, varsa da elle
  hazırlanmış veri beklediği için hata veriyordu. `tests/e2e/conftest.py` geçici veri klasöründe
  yerel servisi açıp sentetik okul verisini kuruyor; testler her üç platformda hazırlıksız çalışıyor.
- **"Yenilikler" testi tek bir bilgisayara bağlıydı.** Linux'a özel sabit yol
  (`/root/.local/share/...`) ve sabit `0.2.0` sürümü kullanıyordu; Mac ve Windows'ta çalışması
  mümkün değildi ve her sürümde bozulacaktı. Artık veri klasörünü ve sürümü çalışan servisten alıyor.
- Raporlardaki ölü değişken ve dağınık kod temizlendi.
- **Kullanılmayan klasörler ve bulut önizleme kalıntıları depodan çıkarıldı:** `.emergent/`
  (derleme platformu artığı), `.screenshots/` (başıboş görsel), `test_reports/` (eski ajan
  koşularının üretilmiş çıktıları), `memory/` (güncelliğini yitirmiş not ve artık var olmayan
  bir yolu gösteren `test_credentials.md`) ve `backend/server.py` (bulut önizlemesi için ASGI
  adaptörü; bağımlılığı `a2wsgi` projede tanımlı bile değildi). Arayüzdeki önizlemeye özel
  `npm start` betiği de kaldırıldı: `--host 0.0.0.0` ile dinliyordu ve yalnızca-yerel çalışma
  kararına aykırıydı. Üretilen çıktılar `.gitignore` ile geri gelmeyecek biçimde kapatıldı.

## 0.3.0 sonrası (aynı gün, ikinci bölüm)

- **Excel'den öğrenci içe aktarma çalışmıyordu.** Dosya okunuyor, kontrol raporu çıkıyor, ama
  "İçe aktarmayı onayla" düğmesi hiç görünmüyordu: arka uç fark raporunu (`diff`) yanıtın en üst
  düzeyinde döndürüyor, arayüz ise `validation` nesnesinin içinde arıyordu. `as` tip dönüşümü
  uyumsuzluğu TypeScript'ten gizlemişti. Düzeltildi; tarayıcıda akış sonuna kadar yürütülüp
  48 sentetik öğrencinin veritabanına girdiği doğrulandı.
- Bu hata API testlerinden kaçmıştı (her uç tek tek doğruydu, kopukluk arada). Gerçek tarayıcıda
  akışı tıklayan `tests/e2e/test_student_import_ui_e2e.py` eklendi; düzeltme geri alındığında
  düştüğü doğrulandı. CI'nın uçtan uca işi Playwright kuruyor.
- Uygulama simgesi eklendi: `packaging/icon/kelebek.svg` kaynak, `packaging/macos/kelebek.icns`
  ve `packaging/windows/kelebek.ico` üretildi, Inno Setup'a bağlandı. Simgenin pakete gerçekten
  gömülmesi **henüz doğrulanmadı** (Linux derlemesi simgeyi atlar).
- Otomatik yedekleme: `scripts/auto-push.sh` çalışma klasörünün anlık görüntüsünü ayrı bir dala
  gönderir; kullanıcının dalına, HEAD'ine, index'ine ve çalışma dizinine dokunmaz. macOS
  zamanlayıcısı `scripts/com.kelebek.autopush.plist` (15 dk). Yedek dalları CI tetiklemez.

## Sınav dönemleri (0.3.0 sonrası, yeni özellik)

Kullanıcı isteği: sınavların ne için oluşturulduğu belli değildi. Her yılda dört dönem
hazır gelir (Güz 1/2, Bahar 1/2), adları değiştirilebilir, dönem eklenip silinebilir.
Yeni sınavda dönem seçimi zorunlu; liste dönem başlıklarına göre gruplanır. Eski kayıtlar
"Dönem atanmamış" altında görünür ve taşınabilir.

- Migration `0018_exam_periods`. **Not:** `exam_period_id` sütunu veritabanı düzeyinde
  yabancı anahtar taşımaz. SQLite ALTER ile kısıt eklemeye izin vermiyor, batch kipi ise
  `exam_organizations` tablosunu silip yeniden kurmayı gerektiriyor ve bu tabloya bağlı
  başka tablolar olduğundan silme reddediliyor (0017 de aynı nedenle kısıtsız sütun
  eklemişti). Bağlantı uygulama katmanında doğrulanır.
- Yan düzeltme: sınav kopyalama kaynağın dönemini kaybediyordu.
- Testler: `backend/tests/test_exam_periods.py` (9 test). Mevcut testler ve uçtan uca
  testler dönem zorunluluğuna göre güncellendi; `test_backup_restore` içindeki sabit
  şema sürümü Alembic head'inden okunur hale getirildi.

## Bundan sonra Mac'te çalışırken

Bu belge bulut oturumundan devralma notudur. Mac'te klasörün içinde `claude` ile açılan oturum
için başlangıç noktası: `main` dalı 0.3.0, beş CI işi (Ubuntu/macOS/Windows birim testleri,
arayüz derlemesi, uçtan uca testler) geçiyor. Çalıştırma komutları README'de.

**Arayüz tarafı hâlâ en zayıf halka.** Yukarıdaki içe aktarma hatası bunu gösterdi: arka uç
testleri sağlam ama arayüzle arka uç arasındaki sözleşme kopabiliyor ve bu sessiz oluyor.
Dağıtım oluşturma, rapor merkezi ve yedekleme akışları bu gözle elle denenmeli.

## 0.4.0 – 0.4.1 (10–11 Kasım 2026)

- Sürümler artık `main` dalına her birleştirmede CI tarafından üretilir ve GitHub
  Releases altında yayımlanır (macOS `.dmg`, Windows kurulum `.exe` ve `.zip`).
  0.4.0 paketleri iki platformda da derlendi ve duman testinden geçti.
- Çözücü grup modeline taşındı; koltuk sayısı öğrenci sayısına eşitken 236 öğrenci
  birkaç saniyede 0 ihlalle dağıtılıyor.
- Kural 7–8 (aynı sınıf seviyesi) ve Karar 37 güncellemesi (koridorda yan yana
  sayılır; çapraz ayrı ilişki, kural 8 çapraza uygulanmaz) karar belgesine işlendi.
- Genel Bakış canlı veriden çalışıyor; öğrenci listesinde arama ve filtre var.
- Arayüz akışlarının tamamı tarayıcıda denendi (ayrıntı: CHANGELOG 0.4.1).

## 0.5.0 – 0.7.0 (11–12 Kasım 2026)

- 0.5.0: adım adım sınav hazırlığı, derslik başına aktif plan, plan silme.
- 0.6.0: çevrim içi sürüm denetimi ve tek tıkla güncelleme (depo herkese açık).
- 0.6.1: yalnızca sınava giren sınıfların derslikleri kendiliğinden seçilir.
- 0.7.0: sade arayüz (tasarım ve plan `docs/superpowers/` altında): derslik doğrudan
  planını açar, her sınavın kendi sayfası, ortak sonuç bildirimi.

## Açık kalanlar

- **Doğrulanmamış hata:** bir sınav, kullanıcının işaretlediğini söylediği bir sınıf
  olmadan oluştu. Yeniden üretilemedi; 0.7.0 sınıf dökümünü her zaman gösterir ve
  işaretlemeyi sağlamlaştırır, ama kök neden bilinmiyor.
- `ExamOrganizer.tsx` ve `ClassroomManager.tsx` hâlâ büyük tek dosyalar.
- Kural 8'in çapraza uygulanmaması kullanıcı onayı bekliyor.
- Kullanıcı isteği (beklemede): her bölümde içeriğin toplu silinmesi; karar
  belgesindeki "kayıt silinmez" kurallarıyla ilişkisi kullanıcıyla netleştirilecek.

- Paketlerin gerçek bir Mac ve Windows bilgisayarda elle kurulup denenmesi; simgenin
  göründüğünün doğrulanması.
- CI paketlerinde yayıncı anahtarı yok; artımlı güncelleme paketleri kabul edilmez,
  güncelleme tam kurulum paketiyle yapılır (kullanıcı verisi ayrı klasörde korunur).

- macOS ve Windows paketlerinin gerçek cihazlarda veya CI'da üretilip denenmesi. Paketleme yolu
  bu oturumda Linux'ta uçtan uca denendi; iki platformun kendi iş akışı hazır ama henüz çalıştırılmadı.
- Apple geliştirici kimliğiyle kod imzalama ve notarization (isteğe bağlı; ad-hoc imza hazır).
- Uygulama simgesi: `packaging/macos` klasörü yok, `packaging/windows` içinde `.ico` yok; paketler
  varsayılan simgeyle çıkıyor.
- Hibrit çoklu pencere çalışma alanı (Karar 18–19).
- Kural ihlali kabulünün işlem geçmişine yazılması (Karar 50).
