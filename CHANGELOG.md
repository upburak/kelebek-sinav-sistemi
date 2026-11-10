# Değişiklik günlüğü

## Geliştirme sürümü (0.3.0 sonrası)

### Dağıtım çözücüsü gerçek okul mevcutlarında çalışıyor (kritik)

Gerçek bir e-Okul sınıf listesiyle (236 öğrenci, 8 şube) denendiğinde uygulamanın
**ana işini yapamadığı** ortaya çıktı: dağıtım 50 saniyede sonuç vermeden
"geçerli aday bulunamadı" diyordu. 48 sentetik öğrenciyle yapılan önceki tüm
testler geçtiği için sorun görünmüyordu. Koltuk sayısı öğrenci sayısına eşit
olduğundan (okulun olağan durumu) kapasite artırmak çözüm değildi; kapasite
%125'e çıkarıldığında da çözülemedi.

**Kök neden.** Model "hangi öğrenci hangi koltukta" sorusunu kuruyordu:
değişken sayısı öğrenci × koltuk, ihlal değişkenleri öğrenci çifti × koltuk çifti
kadardı. Üstelik altı kuralın tamamı yalnızca sınıf/şube/alan üçlüsüne baktığı için
aynı gruptaki öğrencilerin her permütasyonu çözücüye farklı bir çözüm gibi
görünüyor, arama kendini tekrar ediyordu.

**Çözüm.** Model artık öğrenci değil **grup** üzerinden kuruluyor
(`kelebek/distribution/seating.py`): önce hangi koltukta hangi grubun oturacağı
çözülür (değişken sayısı koltuk × grup), sonra her grubun kazandığı koltuklara o
gruptaki öğrenciler saf Python'la yerleştirilir. Kurallar gruba bağlı olduğu için
bu eşleme ihlal sayısını değiştiremez.

| Öğrenci | Önce | Sonra |
|---|---|---|
| 236 | 50 sn, çözülemedi | **2,5 sn, optimal, 0 ihlal** |
| 600 | — | 5,8 sn, optimal, 0 ihlal |
| 1000 | — | 12 sn içinde 0 ihlalli çözüm |
| 1500 | — | 12 sn içinde 0 ihlalli çözüm |

Hepsi koltuk sayısı öğrenci sayısına **tam eşitken** ölçüldü.

**Davranış değişikliği:** eskiden modelde "etkilenen öğrenci sayısı ≤ 5" katı bir
kısıttı; sağlanamadığında kullanıcıya hiç aday üretilmiyor, yalnızca hata
gösteriliyordu. Artık bu bir eniyileme hedefi: en az ihlalli aday her durumda
üretilir, kullanıcı ihlalleri görüp "Tümünü düzelt" ile giderebilir.
Kesinleştirme aşaması etkilenen öğrenci sayısını zaten ayrıca denetliyor.

Testler: `backend/tests/test_seating_scale.py` (9 test) doğruluğu ve ölçeği
birlikte sabitler. Çözücü hızlandığı için ilerleme/durdurma uçtan uca testleri de
güncellendi: 48 öğrencilik dağıtım artık arama aşaması yakalanamayacak kadar
hızlı bitiyor.


### Tasarım ve ergonomi turu

Arayüz ölçülerek incelendi (üç pencere genişliği, yedi ekran, gerçek zemine göre
kontrast hesabı) ve bulunan sorunlar giderildi:

- **Dar pencerede yatay taşma.** 820 piksel genişlikte "Uygulamayı kapat" düğmesi
  ekranın dışına taşıyordu; kenar çubuğu sabit genişlikte olduğu için içerik alanı
  beklenenden çok daralıyordu. Üst çubuk artık taşmak yerine alt satıra geçiyor.
- **Okunamayacak kadar küçük yazılar.** Stil dosyasında 11 pikselin altında
  146 kural vardı (3 tanesi 7 piksel). 13 inç ekranda çalışan bir yönetici için
  bu ciddi bir sorun. Genel arayüzde taban 11–12 piksele, yoğun oturma krokisinde
  10 piksele çekildi. Ayrıca tarayıcı `<small>` etiketini %83'e küçülttüğü için
  11 piksellik yazılar 9,17 piksele düşüyordu; taban açıkça sabitlendi.
- **Yetersiz renk kontrastı.** Ölçümde WCAG AA eşiğini geçemeyen 130 renk kullanımı
  bulundu (en kötüsü 1,6:1 — ayraç karakterleri neredeyse görünmezdi). Tonlar korunarak
  koyulaştırıldı; gerçek zemine göre yeniden ölçüldü. Kalan tek uyarı pasif bir düğme
  (WCAG pasif denetimleri kapsam dışı bırakır) ve iki yanlış pozitif.
- **Sınav listesinde asıl iş katlamanın altında kalıyordu.** Beş boş dönem başlığı
  ekranın üst yarısını dolduruyor, kullanıcının tek sınavı aşağıda kalıyordu. Sınavı
  olmayan dönemler artık tek satırda özetleniyor, dolu dönemler üstte.
- **Başlık tekrarı.** "Sınav organizasyonları" aynı ekranda iki kez, eğitim yılı üç
  yerde yazıyordu. Kart başlığı kaldırıldı (ekran okuyucu için gizli başlık korundu).
- **Küçük tıklama hedefleri.** 14 piksel yüksekliğindeki düğmeler vardı; taban 28 piksel.
- Dönem seçim kutusu karttan kopuk duruyordu; kartın üstüne yapışık şeride dönüştü.


### Sınav dönemleri (yeni)

Sınavlar düz bir liste halindeydi; hangi sınavın ne için yapıldığı belli olmuyordu.
Artık her eğitim-öğretim yılında dört sınav dönemi hazır gelir: **Güz 1. Sınavları,
Güz 2. Sınavları, Bahar 1. Sınavları, Bahar 2. Sınavları.**

- Dönem adları okulun kendi diline göre değiştirilebilir ("1. Dönem 1. Yazılılar" gibi).
- Yeni dönem eklenebilir (telafi, deneme vb.); içinde sınav olmayan dönem silinebilir,
  dolu dönem silinemez ve uygulama bunu açıkça söyler.
- Yeni sınav oluştururken dönem seçmek zorunludur; sınav listesi dönem başlıkları
  altında gruplanır.
- Önceden oluşturulmuş sınavlar "Dönem atanmamış" başlığı altında görünür ve kartın
  üstündeki kutudan bir döneme taşınabilir; hiçbir kayıt kaybolmaz.
- Bir sınavın kopyası kaynağının dönemini sürdürür.

Karar belgesi v4.3'te sınav dönemi kavramı tanımlı değildi; bu ekleme mevcut 72 kararın
hiçbiriyle çelişmez, belge değiştirilmedi. Migration: `0018_exam_periods`.


- **Excel'den öğrenci listesi içe aktarılamıyordu.** Dosya okunuyor, sütunlar
  eşleşiyor, kontrol raporu çıkıyor; ama **"İçe aktarmayı onayla" düğmesi hiç
  görünmediği için liste kaydedilemiyordu.** Arka uç fark raporunu (`diff`)
  yanıtın en üst düzeyinde döndürüyor, arayüz ise onu `validation` nesnesinin
  içinde arıyordu; düğme `validation.diff` dolu olduğunda çizildiği için hiç
  çizilmiyordu. `as` tip dönüşümü uyumsuzluğu TypeScript'ten gizlediği için
  hata derleme sırasında da görünmüyordu.
- Bu hata uçtan uca API testlerinden kaçmıştı: her uç tek tek doğru yanıt
  veriyordu, kopukluk arayüzle arka uç arasındaydı. Bu yüzden gerçek tarayıcıda
  akışı tıklayan bir arayüz testi eklendi
  (`tests/e2e/test_student_import_ui_e2e.py`): dosya seçilir, kontrol çalıştırılır
  ve onay düğmesinin göründüğü doğrulanır. Test, düzeltme geri alındığında
  düşmektedir (doğrulandı). CI'nın uçtan uca işi artık Playwright kuruyor.

## 0.3.0

Bu sürüm yeni özellik eklemez; projeyi macOS ve Windows'ta güvenle çalıştırmak için
yapılan testlerde bulunan hataları giderir ve doğrulamayı sürekli hale getirir.

### Düzeltmeler

- **Arayüz açılmıyordu (macOS):** Kurulum yolu bir sembolik bağ içerdiğinde (bağlı
  *Applications* klasörleri, taşınmış kullanıcı klasörleri, `/var` gibi yollar)
  JavaScript, CSS ve Excel indirme istekleri dosya yerine `index.html` döndürüyordu;
  uygulama boş ekranla açılıyordu. Yol karşılaştırması artık iki tarafı da çözümlüyor;
  klasör dışına çıkan istekler yine reddediliyor.
- **Raporlarda Türkçe harfler bozuluyordu:** Türkçe destekleyen sistem yazı tipi
  bulunamadığında raporlar sessizce Helvetica'ya dönüyor ve `Çağrı Işık Şükrü İpek`
  çıktıya `Çanrn Innk nükrü npek` olarak düşüyordu. Yazı tipi adayları her iki
  platform için genişletildi, seçilen yazı tipinde Türkçe harflerin gerçekten
  bulunduğu doğrulanıyor; hiçbiri yoksa metin yanlış harf yerine okunabilir ASCII
  karşılığına sadeleştiriliyor ve günlüğe uyarı yazılıyor.
- **macOS'ta artımlı güncelleme uygulamayı çalışmaz hale getiriyordu:** `.app`
  paketinin içindeki dosyalar değişince paketin imzası geçersiz kalıyor, Apple
  Silicon çekirdeği de imzası bozuk ikili dosyayı hiç çalıştırmıyordu; güncelleme
  her seferinde geri dönüşe düşüyordu. Güncelleyici dosyaları yerleştirdikten ve
  geri aldıktan sonra karantinayı temizleyip paketi yeniden ad-hoc imzalıyor;
  `build-macos.sh` de ürettiği paketi açıkça imzalayıp doğruluyor.
- **Kurulum yalnızca Python 3.12 ile çalışıyordu:** `pyproject.toml` 3.12 ve üzerini
  desteklemesine karşın kurulum betikleri tam olarak `python3.12` ya da Windows
  Python Launcher'ı arıyor, bulamayınca duruyordu. Her iki betik artık 3.12 ve üzeri
  herhangi bir sürümü buluyor; Windows derlemesi de aynı kurulum yolunu kullanıyor.
- Raporlarda ölü değişken ve kod temizliği; tüm depoda `ruff` uyarısı kalmadı.

### CI'ın yakaladığı Windows hataları

Yeni test iş akışının ilk koşusu Windows'ta kırmızı yandı; macOS, Ubuntu, uçtan uca
ve arayüz işleri geçti. Çıkan iki sorun giderildi:

- **İptal edilen geri yükleme önizlemesi veri klasöründe kopya bırakıyordu.**
  `discard_pending_restore` silme işlemini `ignore_errors=True` ile yapıyor ve
  silemese bile kullanıcıya "iptal edildi" diyordu. Windows, dosyayı açık tutan
  tutamak serbest kalana kadar silmeye izin vermediği için klasör kalıyordu — içinde
  kullanıcının veritabanının bir kopyası vardı. Silme artık kısa aralıklarla yeniden
  denenir, başarısız olursa günlüğe yazılır ve bir sonraki açılışta temizlenir.
- **Kapatılmayan SQLite bağlantıları.** `with sqlite3.connect(...)` bağlantıyı
  kapatmaz, yalnızca işlemi tamamlar. Üç yerde (geri yükleme şema doğrulaması,
  geri yüklenen veritabanının bütünlük kontrolü ve migration öncesi yedek)
  bağlantılar açık kalıyordu; Windows'ta dosya kilidi, her yerde tutamak sızıntısı
  anlamına geliyordu. Hepsi `contextlib.closing` ile kapatıldı.
- **Uygulama kapandıktan sonra dosya tutamağı bırakıyordu:** SQLite veritabanı ve
  `logs/application.log` açık kalıyordu; Windows açık dosyanın silinmesine izin
  vermediği için geçici veri klasörüyle çalışan testler düşüyordu. Ortak
  `backend/tests/_support.py` yardımcısı her testin sonunda motoru ve günlük
  işleyicisini kapatıyor; `backend/tests/test_file_handles.py` bunu ölçerek sabitliyor.
- Günlük dosyası artık güncel veri klasörünü izliyor: `app.logger` Flask'ta modül adına
  bağlı olduğu için süreç içinde paylaşılıyor ve veri klasörü değiştiğinde eski dosyaya
  yazmaya devam ediyordu.
- **Testlerin bir bölümü iki kez çalışıyordu:** iki test dosyası başka bir test
  sınıfını modül düzeyinde içe aktardığı için `unittest` onları ikinci kez topluyordu
  (`BackupRestoreTests`'in 8 testi her koşuda 16 kez çalışıyordu). Giderildi;
  süit 41 benzersiz test.

### Test ve doğrulama

- **Otomatik test iş akışı eklendi** (`.github/workflows/tests.yml`): her gönderimde
  ve birleştirme isteğinde Ubuntu, macOS ve Windows'ta lint + birim testleri, ayrıca
  arayüz derlemesi ve uçtan uca API testleri çalışır. Önceden hiçbir test kendiliğinden
  çalışmıyordu.
- **Paket iş akışına duman testi eklendi:** README'nin söz verdiği
  `packaging/smoke_test.py` adımı iş akışında yoktu; artık her iki platformun paketi
  üretildikten sonra çalışır.
- **Uçtan uca testler kendi kendine çalışıyor:** `tests/e2e/conftest.py` geçici veri
  klasöründe yerel servisi açıp sentetik okul verisini kuruyor. Testler eskiden elle
  hazırlanmış bir ortam ve `KELEBEK_PUBLIC_URL` olmadan hiç çalışmıyordu.
- "Yenilikler" testi Linux'a özel sabit bir yol (`/root/.local/share/...`) ve sabit
  sürüm numarası kullanıyordu; artık platformdan ve sürümden bağımsız.
- Düzeltilen iki hata için gerileme testleri: `test_frontend_serving.py` ve
  `test_report_fonts.py`.
- `ruff` kural kümesi `pyproject.toml` içinde sabitlendi; sonuçlar sürümden sürüme kaymaz.

### Depo temizliği

- Kullanılmayan klasörler çıkarıldı: `.emergent/` (derleme platformu artığı), `.screenshots/`,
  `test_reports/` (eski koşuların üretilmiş çıktıları), `memory/` (güncelliğini yitirmiş notlar).
- `backend/server.py` (bulut önizlemesi için ASGI adaptörü) çıkarıldı; bağımlılığı `a2wsgi`
  projede tanımlı değildi, yerel çalışmada kullanılmıyordu.
- Arayüzdeki önizlemeye özel `npm start` betiği ve `allowedHosts` kaçağı kaldırıldı; geliştirme
  sunucusu yalnızca `127.0.0.1` üzerinde dinler.
- Üretilen test ve araç çıktıları `.gitignore` kapsamına alındı.

## Geliştirme sürümü

- Faz A başlangıç iskeleti: Flask sağlık API'si, React/TypeScript arayüzü, platforma uygun veri dizini ve geliştirme betikleri.
- Faz B başlangıcı: SQLite/Alembic şeması, yedekli migration başlangıcı ve güncel eğitim-öğretim yılı seçimi.
- Faz C başlangıcı: e-Okul XLSX önizleme, sütun eşleştirme, teknik doğrulama, yıl bazlı fark raporu ve kullanıcı onaylı yerel aktarım.
- Faz D veri temeli: sürümlü derslik düzenleri, fiziksel masalar ve ayrı oturma yerleri; SQLite yabancı anahtar denetimi etkin.
- Faz D ilk ekranı: derslik/düzen yönetimi, blok bazlı başlangıç planı üretimi ve numaralı oturma yeri önizlemesi.
- Faz D düzenleme: yeni sürüme kopyalama, sürükle-bırak masa taşıma ve oturma yerini kullanıma kapatma/açma.
- Faz H ilk raporu: kesinleşmiş sınavlardan derslik başına tek sayfalık, gerçek masa/koridor düzenini koruyan Türkçe oturma planı PDF ön izlemesi.
- Kesinleşmiş dağıtım düzenlemesi: güncel eğitim yılında koltuk taşıma ve takasları aynı aday üzerinde, geri al/yinele geçmişiyle kaydetme; arşiv dağıtımlarını salt okunur tutma.
- PDF durumu: dağıtım değiştiğinde mevcut oturma planını eski olarak işaretleme, yenilenince içerik parmak iziyle güncelliğini doğrulama.
- Faz I başlangıcı: SQLite tutarlı anlık görüntüsü ve mevcut PDF raporlarını sürümlü, manifestli ve SHA-256 özetli ZIP paketi olarak elle oluşturup indirme; geri yükleme güvenlik kontrolleri ayrı adımda.
- Otomatik koruma: uygulama açılışında ve yeni günün ilk kullanımında günlük paket; en yeni 30 otomatik yedeği tutma ve öğrenci listesi aktarımından hemen önce ayrı güvenlik paketi.
- Rapor doğruluğu: aynı adlı sınavlara ayrı PDF dosya adları; yeni PDF için dosya SHA-256 özetiyle içerik bütünlüğü ve önceki ortak adların eski olarak işaretlenmesi.
- Yedek durumu: bugünkü günlük yedek ve son otomatik yedek zamanı ekranda görünür; yedek alınmadıysa kullanıcıya bildirilir.
- Yedek kalite kontrolü: ZIP paketi oluşturulmadan önce SQLite bütünlüğü ve yabancı anahtar bağlantıları doğrulanır.
- Geri yükleme: taşınabilir ZIP için SHA-256, ZIP, uygulama ve şema uyumluluğu önizlemesi; kullanıcı onayından sonra geçici şema geçişi, işlem öncesi doğrulanmış güvenlik yedeği ve başarısızlıkta veritabanı/PDF geri alma.
- Öğrenci listeleri: farklı satırlardaki başlıkları kendisi bulan, çok sayfalı Excel ve metin tabanlı PDF listelerini önizleyen; sınıf/şube sayfalarından grupları anlayıp kapasite taslağı oluşturan aktarım.
- Öğrenci düzeltmeleri: tekil ekleme, düzenleme, pasife alma ve yeniden etkinleştirme; taslak sınav dağıtımlarından çıkarma ve tamamlanmış sınav geçmişini koruma.
- Derslik yönetimi: elle derslik ve sıra planı düzenlemeye devam; boş kullanılmamış dersliği silme ve sınav geçmişi olmayan dersliğin adını değiştirme.
- Geliştirme başlatıcısı: API portu 5000 doluysa 127.0.0.1 üzerindeki 5001–5100 aralığından boş port seçilir ve Vite proxy'si aynı porta yönlendirilir.
- Sınav güvenliği: kesinleştirme öncesi dağıtım özetiyle birlikte fiziksel derslik planlarının doğrulanması da açıkça onaylanır.
- Faz H raporları: kesinleşmiş güncel dağıtımdan derslik bazlı yoklama çizelgesi ve oturma yeri durumlu derslik öğrenci listesi PDF ön izlemesi; SHA-256/parmak iziyle rapor güncelliği izlenir.
- Rapor merkezi: kesinleşmiş sınav seçimi; kapı krokisi, yoklama, derslik listesi ve genel dağıtım PDF'leri ile derslik/genel dağıtım Excel dosyalarını oluşturma ve indirme.
- Rapor merkezi genişletmesi: sınıf/şube bazlı öğrenci listeleri PDF/Excel; PDF çıktılarında A4/A3/A5/Letter/Legal, dikey/yatay ve 5–30 mm kenar boşluğu seçimi.
- Rapor alanları: PDF/Excel listelerinde rapor türüne göre sütun göster/gizle; en az bir alan zorunlu, kapı krokisinin karar gereği sabit alanları korunur.
- Rapor şablonu ayarları: seçili rapor alanları için özel sütun başlığı ve yukarı/aşağı taşıma; başlıkların PDF/Excel çıktısında kullanılması ve API doğrulaması.

## 0.2.0

- Tek komutla sürüm: `scripts/release.py` sürüm/notları günceller, tam kurulum paketini ve önceki sürüme göre imzalı güncelleme paketini birlikte üretir.
- "Tümünü düzelt": ihlalli öğrencileri önerilen ihlalsiz yerlere tek seferde taşır (taslakta yeni manuel sürüm, kesinleşmişte işlem geçmişiyle).
- Yenilikler penceresi: güncellemeden sonraki ilk açılışta yeni sürümün notları gösterilir (`kelebek/release_notes.py`).

- Güncelleme imzası: paketler Ed25519 ile imzalanır (`scripts/update_signing.py`), uygulama yalnızca gömülü yayıncı anahtarıyla doğrulanan paketleri kabul eder; anahtar tanımlı değilse güncelleme reddedilir.
- İhlal çözüm önerisi: ihlalli her öğrenci için kendi ihlalini gideren ve yeni ihlal yaratmayan en yakın boş yer önerilir; "Taşı ve düzelt" tek dokunuşla uygular (işlem geçmişine yazılır, geri alınabilir).
- Erken durdurulan adaylar "Erken durduruldu" etiketiyle kaydedilir.
- Yalnız ad/numara değişikliğinde taslak sınav adayları artık silinmez.
- CI sağlamlaştırma: Windows'ta Python Launcher olmadan sanal ortam, UTF-8 konsol, DMG için yeniden deneme.

- İhlal krokisi (Karar 55): kural ihlalinden etkilenen öğrenciler aday kartında bir kez listelenir, ihlal nedeni ve komşu öğrenci gösterilir; öğrenciye dokununca krokide yeri ve ihlale neden olan komşu yerler vurgulanır.
- Dağıtım ilerlemesi (Karar 58): hesaplama sırasında aşamalar, geçen süre, en fazla kalan süre, bulunan çözüm sayısı ve en iyi çözümde etkilenen öğrenci sayısı gösterilir; "Durdur ve en iyi çözümü kullan" o ana kadarki en iyi geçerli çözümü aday olarak kaydeder. İlerleme ve durdurma istekleri uzun hesaplama sırasında beklemez.
- Çözücüde grup dengesinin yanlış dersliğin koltuklarıyla hesaplanması düzeltildi.
- Artımlı güncelleme (Faz J): `scripts/make_update_package.py`, uygulama içi paket doğrulama/özet, güvenlik yedeği, dış güncelleyici (macOS bash / Windows PowerShell), açılış doğrulaması ve başarısızlıkta dosya + veritabanı geri dönüşü. Tek sürüm kaynağı `kelebek/version.py`.
- CI duman testi: paketlenmiş uygulama açılıp sağlık, arayüz ve veritabanı doğrulanır.

- Rapor seçenekleri: liste/yoklama PDF'lerinde üst bilgi alanlarını (okul, başlık, sınav, tarih, ders, derslik) göster/gizle, özel rapor başlığı ve %80–%130 yazı ölçeği. Rapor öncesi "düzenlemeler tamamlandı" onayı (Karar 49), ihlal varsa ayrı kabul (Karar 50), bekleyen öğrenci varken rapor engeli.
- Derslik sabitleyerek yeniden dağıtım (Karar 25): seçilen adaydaki derslik yerleşimleri aynen korunur, kalan derslikler CP-SAT ile yeniden optimize edilir; yeni aday kaynak adaydan türetilmiş ve sabitlenen derslikleri kayıtlı bağımsız alternatif olarak saklanır.
- Güncel öğrenci listesiyle karşılaştırma (Karar 39/47/48): kesinleşmiş dağıtımda okul numarası + ad-soyad eşleştirmesiyle değişen ve ayrılan öğrenciler listelenir; kullanıcı onayıyla güncel bilgiye geçirilip bekleyen havuza alınır, işlem geçmişe yazılır.
- Tek düzenleme oturumu (Karar 40): her sekmeye kimlik; bir sınavı yalnızca bir sekme düzenler, diğerleri önizleme modunda salt okunur kalır; "Düzenlemeyi bu sekmeye al" ile devir; kilit 30 sn yanıt gelmezse kendiliğinden düşer.
- Sınavı tamamlama ve arşiv (Karar 68–70): kesinleşmiş sınav "Tamamlandı" olarak arşivlenir ve salt okunur olur; kaynağı değiştirmeden güncel yılda bağımsız çalışma kopyası oluşturulur. Silme yoktur. Migration 0017.
- Masaüstü paketleme (Faz J başlangıcı): `kelebek.launcher` boş yerel portta Waitress ile servis açar, tarayıcıyı başlatır, tek örnek çalıştırır, Host/Origin denetler, "Uygulamayı kapat" düğmesi ve 10 dk boşta kapanma. PyInstaller tarifi, `build-macos.sh` (.app + DMG), `build-windows.ps1` (ZIP + Inno Setup kurulum) ve GitHub Actions iş akışı.
