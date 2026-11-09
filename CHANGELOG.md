# Değişiklik günlüğü

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
