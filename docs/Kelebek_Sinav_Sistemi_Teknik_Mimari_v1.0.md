# KELEBEK SINAV SİSTEMİ
## Teknik Mimari ve Geliştirme Planı

**Belge sürümü:** 1.0  
**Dayanak:** Ana Proje Karar Dokümanı v4.3  
**Geliştirme önceliği:** Apple Silicon MacBook  
**Hedef işletim sistemleri:** macOS ve Windows  
**Uygulama türü:** Çevrimdışı çalışabilen yerel web uygulaması

---

## 1. Mimari hedefler

1. Aynı kaynak kod tabanı macOS ve Windows üzerinde çalışmalı.
2. Kullanıcı uygulamayı masaüstü kısayolundan başlatmalı; yerel servis açılmalı ve varsayılan tarayıcı otomatik açılmalı.
3. İnternet bağlantısı temel işlevler için gerekli olmamalı.
4. Ana veri tarayıcı depolamasında değil, işletim sistemine ait kullanıcı veri dizininde SQLite veritabanında tutulmalı.
5. Uygulama güncellemeleri kullanıcı verisini silmemeli.
6. Tam kurulum paketinin yanında doğrulanmış artımlı güncelleme paketi hazırlanabilmeli.
7. Sınav organizasyonu, öğrenci, fiziksel derslik, dağıtım adayı, işlem geçmişi ve raporların sorumlulukları birbirinden ayrılmalı.
8. İlk sürüm tek kullanıcıya göre tasarlanmalı; iş katmanı ileride çok kullanıcılı sunucu mimarisine taşınabilecek şekilde ayrıştırılmalı.

## 2. Teknoloji seçimi

| Katman | Seçim | Gerekçe |
|---|---|---|
| Backend | Python + Flask | Önceden kararlaştırılmış yerel web servis yaklaşımı; Python ekosistemi |
| Yerel HTTP sunucusu | Waitress | Geliştirme sunucusu yerine paketlenmiş uygulamada kullanılacak WSGI sunucusu |
| Frontend | React + TypeScript + Vite | Çok pencereli çalışma alanı, sürükle-bırak sınıf editörü ve karmaşık görsel durum yönetimi |
| Veri erişimi | SQLAlchemy | Veritabanı erişimini iş mantığından ayırmak |
| Veritabanı | SQLite | Tek kullanıcı/tek bilgisayar, çevrimdışı ve taşınabilir veri |
| Şema geçişi | Alembic | Sürümler arasında güvenli veritabanı güncellemesi |
| Dağıtım optimizasyonu | OR-Tools CP-SAT + sezgisel iyileştirme | Kısıtlı yerleştirme ve çok amaçlı optimizasyon |
| PDF | ReportLab | Yerel PDF üretimi ve sayfa yerleşimi kontrolü |
| Excel | OpenPyXL | XLSX içe/dışa aktarma |
| Paketleme | PyInstaller tabanlı ayrı platform derlemeleri; OS'ye uygun installer | Aynı kaynak koddan macOS ve Windows paketleri üretmek |
| Kaynak/sürüm kontrolü | Git | Dosya geçmişi, değişiklik karşılaştırma, geri dönüş ve sürüm etiketi |

Teknik prototipte seçilen kütüphanelerin macOS ARM64 ve Windows üzerinde paketlenebilirliği doğrulanır. Bir platforma özgü kod, mümkün olduğunca `platform` adaptörleri arkasında tutulur.

## 3. Uygulamanın çalışma modeli

### 3.1 Başlatma

- macOS için `.app`/DMG, Windows için kurulum paketi hazırlanır.
- Masaüstü kısayolu küçük bir başlatıcıyı çalıştırır.
- Başlatıcı mevcut uygulama örneğini kontrol eder; zaten çalışıyorsa yeni servis başlatmak yerine açık uygulama adresini kullanır.
- Servis boş bir yerel portta, yalnızca `127.0.0.1` üzerinde başlar.
- Uygulama tarayıcıda açılır. Uygulama penceresi kapatıldığında kullanıcıya göre servis sonlandırılır veya sistem tepsisinde çalışır; bu davranış prototip testinde kesinleştirilir.
- Servis dış ağ arayüzlerine bağlanmaz. İsteklerde Host/Origin doğrulaması ve yerel oturum token'ı kullanılır.

### 3.2 Kapanış

- Devam eden yazma işlemleri tamamlanır veya güvenli biçimde iptal edilir.
- SQLite bağlantıları kapatılır.
- Oturum/düzenleme kilitleri serbest bırakılır.
- Veriler otomatik kaydedilmiş ve kalıcı olmalıdır; tarayıcı cache temizliği veriyi etkilemez.

## 4. Önerilen depo ve klasör yapısı

```text
kelebek-sinav-sistemi/
├── AGENTS.md
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── backend/
│   ├── kelebek/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── domain/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/
│   │   ├── distribution/
│   │   ├── reporting/
│   │   ├── imports/
│   │   ├── backup/
│   │   └── platform/
│   ├── migrations/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── workspace/
│   │   ├── modules/
│   │   ├── components/
│   │   ├── api/
│   │   └── styles/
│   └── package.json
├── packaging/
│   ├── macos/
│   └── windows/
├── scripts/
│   ├── dev-macos.sh
│   ├── dev-windows.ps1
│   ├── build-macos.sh
│   └── build-windows.ps1
├── docs/
│   ├── decisions.md
│   ├── technical-architecture.md
│   └── release-process.md
└── tools/
    └── release/
```

**Kural:** Kaynak kod, testler ve migration'lar Git deposunda; gerçek okul verisi, yedekler ve dışa aktarılan raporlar ise kullanıcı veri dizininde tutulur. Gerçek öğrenci verileri Git'e veya Codex'e gönderilen kaynak paketlerine eklenmez.

## 5. Modül sınırları

| Modül | Sorumluluk |
|---|---|
| Academic Year | Eğitim öğretim yılı seçimi, aktif yıl ve geçmiş yıl erişimi |
| Student Registry | Öğrenci kimliği, yıl bazlı kayıt, sınıf/şube/alan, e-Okul aktarımı ve karşılaştırma |
| Classroom Designer | Derslik şablonu, sıra/masa, oturma yeri, blok/koridor, koordinatlar ve fiziksel komşuluk grafiği |
| Exam Organizer | Sınav adı/tarihi, isteğe bağlı ders, öğrenci grupları, seçilen derslikler ve kurallar |
| Distribution Engine | Başlangıç çözümü, kapasite, denge, komşuluk kısıtları, alternatif ve kısmi yeniden dağıtım |
| Distribution Workspace | Alternatif inceleme, manuel düzenleme, tek düzenleme kilidi ve geri/ileri alma |
| History | Olay günlüğü, checkpoint, dallanma ve geçmiş duruma dönme |
| Reporting | PDF/Excel raporları, güncellik durumu, yeniden oluşturma |
| Backup & Restore | Otomatik/manuel yedek, taşınabilir paket, doğrulama ve geri yükleme |
| Release & Update | Sürüm kontrolü, migration, artımlı paket ve güvenli geri dönüş |
| Platform Adapter | macOS/Windows veri dizini, başlatma, açılış ve kapatma işlemleri |

İş mantığı Flask route'larının içine yazılmaz. API katmanı isteği doğrular ve ilgili service/domain işlevini çağırır.

## 6. Temel veri modeli

Aşağıdaki model ilk veritabanı tasarımının temelidir; tablo/kolon ayrıntıları DB-001 teknik tasarımında kesinleştirilir.

- `academic_years`: 2026-2027 gibi eğitim öğretim yılı kayıtları ve aktiflik bilgisi.
- `students`: Uygulama içi değişmez UUID kimliği ve kişiye ait temel kimlik kaydı.
- `student_year_enrollments`: Öğrencinin ilgili yıldaki okul numarası, ad/soyad, sınıf, şube, alan ve aktif/pasif durumu.
- `courses`: Kullanım sırasında oluşan ders listesi.
- `classrooms`: Okulun fiziksel derslik tanımları.
- `classroom_layouts`: Dersliğin yıl/şablon bazlı fiziksel düzen sürümü.
- `desks`: Fiziksel masa/sıra; blok ve geometrik konum bilgisi.
- `seats`: Masaya bağlı tekil oturma yerleri; numara, koordinat, kullanılabilirlik.
- `exam_organizations`: Sınav organizasyonu; yıl, ad, tarih, durum.
- `exam_courses`: Organizasyon içindeki isteğe bağlı bir veya daha fazla ders.
- `exam_participants`: Organizasyona katılacak öğrenciler ve ilgili ders/grup ilişkisi.
- `distribution_runs`: Otomatik dağıtım çalışmaları ve algoritma parametreleri.
- `distribution_candidates`: İlk çözüm ve alternatifler.
- `seat_assignments`: Bir aday/çalışma sürümündeki öğrenci-oturma yeri eşleşmeleri.
- `distribution_constraints`: Altı komşuluk kuralının organizasyon bazlı ayarları.
- `distribution_events`: Öğrenci taşıma, koltuk kapatma, yeniden dağıtım, onay ve benzeri değişiklik olayları.
- `distribution_checkpoints`: Geri/ileri alma ve dallanma için durum görüntüleri.
- `report_status`: Güncel rapor setinin dağıtım durumuyla eşleşip eşleşmediği ve üretilme zamanı.
- `backup_records`: Yedek paketinin tarihi, sürümü, kapsamı ve bütünlük bilgileri.

### 6.1 Öğrenci kimliği ve okul numarası

Veritabanında değişmez iç kimlik UUID olur. Okul numarası, aktif eğitim öğretim yılı öğrenci listesinde benzersiz olmalıdır. Öğrenci listesi güncellemesinde okul numarası ve ad-soyad birlikte karşılaştırılır. Aynı okul numarası daha sonraki bir tarihte başka öğrenciye verilmişse yeni kişi eski öğrencinin kaydıyla birleştirilmez; eski kişi pasif/historik kayıtta kalır, yeni kişi yeni iç kimlikle eklenir. Böylece geçmiş sınav katılımı bozulmaz.

## 7. Fiziksel komşuluk ve dağıtım motoru

### 7.1 Fiziksel model

Sınıf editörü her oturma yerini fiziksel koordinat, sıra yönü, blok kimliği ve kullanılabilirlik bilgisiyle kaydeder. Yan yana ve önlü/arkalı ilişkiler masa numarasından türetilmez; koordinatlar ve aynı blok/koridor koşulu kullanılarak komşuluk grafiği oluşturulur. Grafik, sınıf düzeni değişince yeniden hesaplanır.

### 7.2 Optimizasyon öncelikleri

1. Kapasite aşımı olmaması ve her katılımcının tam bir kez yerleşmesi kesin koşuldur.
2. Seçilmiş dersliklerin tamamını kullanma ve kapasite oranlarına göre denge hedeflenir.
3. Şube, seviye ve alan dağılımı kapasite oranlarıyla uyumlu tutulur.
4. Komşuluk ihlali sıfır hedeflenir; sıfır mümkün değilse etkilenen benzersiz öğrenci sayısı minimize edilir.
5. Kesin üst sınır beş benzersiz öğrencidir. Beşten fazla etkilenen aday kesinleştirilemez.
6. Alternatifler farklı geçerli çözümler üretir; aynı yerleşimin küçük rastgele değişikliklerle çoğaltılması engellenir.

### 7.3 Aşamalı çözüm

- Hızlı sezgisel başlangıç çözümü.
- CP-SAT ile kısıt ve denge optimizasyonu.
- Yerel arama/takas ile iyileştirme.
- Farklı adayların çeşitlilik kontrolü ve sıralanması.
- İlk geçerli adayın hemen kullanıcıya sunulması; arama sürüyorsa sonraki alternatiflerin üretilmesi.

Dağıtım çalışması kullanıcıya özel ekranda görünür; kullanıcıdan başka bir arka plan işi yürütmesi beklenmez. Tahmini kalan süre kesin vaat olarak gösterilmez.

## 8. İşlem geçmişi ve geri/ileri alma

- Her kullanıcı işlemi bir olay kaydı üretir.
- Olaylar organizasyon kimliği, zaman damgası, işlem türü, etkilenen öğrenci/koltuklar ve önceki/yeni değerleri taşır.
- Belirli aralıklarla checkpoint alınır; geri/ileri alma checkpoint ile olayların yeniden uygulanması üzerinden yürütülür.
- Kullanıcı geçmişteki bir noktadan yeni işlem başlatırsa eski gelecek dalı silinmez; yeni dal oluşturulur.
- Alternatif üzerinde manuel düzenleme, kaynak alternatifi değiştirmeden child candidate oluşturur.
- Kesinleşmiş ana dağıtım doğrudan düzenlenebilir; her işlem geçmişe yazılır, zorunlu revizyon nesnesi yoktur.

## 9. Rapor üretimi

Rapor üretimi ayrı bir reporting service üzerinden yürütülür. Her rapor üretiminde dağıtımın durum/checkpoint kimliği kaydedilir. Yerleşim değiştiğinde rapor durumu `stale` olur. Kullanıcı hazır olduğunda raporlar güncel durumdan yeniden oluşturulur; eski PDF/XLSX dosyalarının ayrı arşivlenmesi zorunlu değildir. Organizasyon tamamlandığında o anki son rapor seti organizasyon arşivinin parçası olarak korunur.

Kapı krokisi tek sayfa olmak zorundadır. Kâğıt boyutu/yönü otomatik seçilebilir; ad sığdırma kuralı soyadı koruyarak ilk isim kısaltma ve ardından yazı tipini küçültme şeklindedir.

## 10. Yedekleme ve platformlar arası taşıma

Yedek paketi ZIP tabanlı, manifest ve SHA-256 checksum içeren sürümlü bir paket olur. İçeriği en az şunları kapsar:

- SQLite veritabanı tutarlı snapshot'ı.
- Gerekli kullanıcı ayarları ve derslik şablon/çizim dosyaları.
- Yedek format sürümü, uygulama sürümü, şema sürümü ve oluşturulma zamanı.
- Her dosyanın hash ve boyut bilgisi.

Geri yükleme öncesinde mevcut veri yedeklenir; paket bütünlüğü ve migration uyumluluğu kontrol edilir; kullanıcı onayı alınır. Aynı veritabanı dosyası iki bilgisayarda canlı ve eş zamanlı kullanılmaz. MacBook ile Windows arasında veri taşımak için yedek oluşturulur, diğer bilgisayara aktarılır ve doğrulanarak geri yüklenir.

## 11. Sürümleme ve artımlı güncelleme

### 11.1 Kaynak kod

Git ana kaynak deposudur. Her sürüm için tag, changelog, test raporu ve release manifest oluşturulur. İki bilgisayarda kaynak kodla çalışmak için tercihen özel (private) bir uzak Git deposu kullanılır; MacBook ve Windows bu depoyu clone/pull/push ile eşitler. Depoda yalnızca kaynak kod ve sentetik test verisi bulunur, gerçek öğrenci verileri bulunmaz. Codex değişiklikleri aynı Git deposunda yapar; kullanıcı diff'i inceler ve testler geçmeden sürüm yayımlanmaz.

### 11.2 Release manifest

Artımlı güncelleme paketi aşağıdaki bilgileri taşır:

- `from_version` ve `to_version`.
- Hedef platform (`macos-arm64`, `windows-x64` gibi).
- Değişen dosyaların göreli yolları, boyutları ve SHA-256 hash'leri.
- Çalıştırılacak Alembic migration aralığı.
- Gerekli minimum uygulama ve yedek şema sürümü.
- Paket checksum/imza bilgisi.

### 11.3 Güncelleme akışı

1. Uygulama ve veritabanı sürümü kontrol edilir.
2. Kullanıcıya güncelleme özeti gösterilir.
3. Güncelleme öncesi otomatik güvenlik yedeği alınır.
4. Dosyalar geçici dizine açılır ve hash doğrulaması yapılır.
5. Veritabanı migration'ları kontrollü uygulanır.
6. Başlangıç sağlık kontrolü/testi yapılır.
7. Başarılıysa yeni sürüm etkinleştirilir; başarısızsa önceki dosya seti ve yedek DB geri yüklenir.

Kullanıcıya hem tam kurulum paketi hem artımlı güncelleme sunulabilir. Kullanıcı yalnızca tek tek rastgele dosya kopyalamak zorunda bırakılmaz; patch paketi hangi dosyaların değiştiğini ve migration gerekip gerekmediğini açıkça bildirir.

## 12. Güvenlik ve veri koruma

- Servis yalnızca localhost üzerinde dinler.
- Öğrenci verisi, loglara gereksiz yere yazılmaz.
- Gerçek öğrenci listeleri kaynak kod deposuna eklenmez.
- Yedek paketleri okul verisi içerdiğinden kullanıcı seçtiği güvenli konumda saklar.
- Güncelleme öncesi ve geri yükleme öncesi güvenlik yedeği zorunludur.
- Kullanıcı onayı olmadan geçmiş organizasyon, öğrenci veya dağıtım kaydı silinmez.

## 13. Test ve kalite planı

| Test alanı | macOS Apple Silicon | Windows |
|---|---:|---:|
| Kaynak koddan geliştirme kurulumu | Zorunlu | Zorunlu |
| Yerel servis başlatma/kapatma | Zorunlu | Zorunlu |
| SQLite ve migration | Zorunlu | Zorunlu |
| e-Okul XLSX aktarımı | Zorunlu | Zorunlu |
| Sınıf editörü ve sürükle-bırak | Zorunlu | Zorunlu |
| Dağıtım algoritması aynı test verisi | Zorunlu | Zorunlu |
| PDF ve Excel üretimi | Zorunlu | Zorunlu |
| Yedek oluşturma/geri yükleme | Zorunlu | Zorunlu |
| Artımlı güncelleme ve rollback | Zorunlu | Zorunlu |
| Temiz kurulum ve kaldırma | Zorunlu | Zorunlu |

Dağıtım motoru için deterministik test veri setleri hazırlanır. Aynı girdi ve aynı algoritma sürümüyle testler tekrarlanabilir olmalıdır. Platform farkı yalnızca dosya yolu/kurulum/başlatıcı gibi platform adaptörlerinde kalmalıdır.

## 14. Uygulama geliştirme sırası

1. **Faz A – Çalışma iskeleti:** Git deposu, Flask API, React arayüzü, sağlık kontrolü, platforma göre veri dizini ve log altyapısı.
2. **Faz B – Veritabanı çekirdeği:** Eğitim öğretim yılı, öğrenci, sınıf/şube/alan, derslik ve migration sistemi.
3. **Faz C – e-Okul içe aktarma:** Dosya okuma, doğrulama, fark raporu, kullanıcı onayı ve alan ataması.
4. **Faz D – Derslik editörü:** Sıra/oturma yeri, blok/koridor, koordinat ve fiziksel komşuluk grafiği.
5. **Faz E – Sınav organizasyonu:** Ders/öğrenci seçimi, derslik seçimi, kurallar ve kapasite kontrolü.
6. **Faz F – Dağıtım motoru:** Başlangıç çözümü, CP-SAT, denge, beş öğrenci sınırı, alternatifler.
7. **Faz G – Çalışma alanı ve geçmiş:** Çok pencere, manuel düzenleme, tek düzenleme kilidi, undo/redo ve dallanma.
8. **Faz H – Raporlar:** PDF, Excel, tek sayfalık kroki, rapor güncelliği.
9. **Faz I – Yedekleme ve arşiv:** Eğitim öğretim yılı arşivi, taşınabilir yedek, geri yükleme.
10. **Faz J – Paketleme ve güncelleme:** macOS/Windows paketleri, tam kurulum, artımlı güncelleme, rollback.

Her faz sonunda çalışan, test edilmiş ve Git etiketi verilmiş bir ara sürüm oluşturulur. Büyük modüller tek seferde yazılmaz; küçük, test edilebilir parçalara ayrılır.

## 15. Codex ile çalışma yöntemi

- Ana repo MacBook üzerinde tutulur; Codex bu klasörü açarak dosyalar üzerinde çalışır.
- `AGENTS.md` proje kurallarını ve değiştirilemez gereksinimleri Codex'e bildirir.
- Her görev tek bir modül veya net bir işlevle sınırlandırılır.
- Codex'ten önce plan, sonra dosya değişikliği, sonra test ve Git diff özeti istenir.
- Kullanıcı onayı olmadan büyük mimari değişiklik, veritabanı silme/yeniden oluşturma veya kapsam değişikliği yapılmaz.
- Windows doğrulaması ayrı Windows makinede veya Windows CI runner üzerinde yapılır; macOS derlemesi Windows'ta, Windows derlemesi Mac'te üretilmeye çalışılmaz.
- Her release için `CHANGELOG`, migration listesi, test özeti ve platform paketleri birlikte sunulur.

---

## 16. Açık teknik doğrulama maddeleri

Bunlar kullanıcı kararını yeniden açmaz; prototip/test yoluyla doğrulanır:

- React masaüstü çalışma alanı için uygun pencere/sekme kütüphanesi ve erişilebilirlik.
- OR-Tools CP-SAT modelinin gerçek okul büyüklüğünde süre ve bellek performansı.
- PyInstaller ve kurulum üreticilerinin Apple Silicon/Windows paket uyumluluğu.
- Yerel servis yaşam döngüsü ve tarayıcı kapatıldığında servis davranışı.
- Migration rollback stratejisinin uygulanabilirliği.
- Artımlı güncelleme paketlerinin imzalanması ve çevrimdışı doğrulanması.
