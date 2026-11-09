# Kelebek Sınav Sistemi — devam notu

Son güncelleme: 9 Kasım 2026 (sürüm 0.3.0)

Kapsam ve kararlar için ana karar belgesi v4.3 ile teknik mimari v1.0 esas alınır; 72 karar
değiştirilmedi. Bu oturumda yeni özellik eklenmedi; amaç projeyi macOS ve Windows'ta güvenle
çalıştırmadan önce bütün olarak test edip bulunan hataları gidermekti.

## Bu oturumda yapılan testler

- Birim testleri: 29 → 38 test (yeni gerileme testleri eklendi), tamamı geçiyor.
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

## Açık kalanlar

- macOS ve Windows paketlerinin gerçek cihazlarda veya CI'da üretilip denenmesi. Paketleme yolu
  bu oturumda Linux'ta uçtan uca denendi; iki platformun kendi iş akışı hazır ama henüz çalıştırılmadı.
- Apple geliştirici kimliğiyle kod imzalama ve notarization (isteğe bağlı; ad-hoc imza hazır).
- Uygulama simgesi: `packaging/macos` klasörü yok, `packaging/windows` içinde `.ico` yok; paketler
  varsayılan simgeyle çıkıyor.
- Hibrit çoklu pencere çalışma alanı (Karar 18–19).
- Kural ihlali kabulünün işlem geçmişine yazılması (Karar 50).
- `backend/server.py` yalnızca bulut önizleme adaptörüdür; yerel çalışmayı etkilemez.
