# Sade arayüz: derslikler, sınavlar ve sonuç bildirimi — tasarım

Tarih: 11 Kasım 2026 · Durum: kullanıcı incelemesi bekliyor · Hedef sürüm: 0.7.0

## Amaç

Uygulamayı sıradan bir öğretmen, kimseye sormadan kullanabilmeli: listeyi
aktarır, sınavı dağıtır, krokiyi yazdırır.

Başarı ölçütü: okulda uygulamayı ilk kez gören bir öğretmen, öğrenci listesi
aktarılmış bir kurulumda yeni bir sınavı oluşturup kesinleştirir ve kapı
krokisini yazdırır; bunu yaparken "düzen sürümü", "şablon", "aday",
"sabitleme" kavramlarından hiçbirini öğrenmesi gerekmez.

## Kullanıcının bildirdiği sorun

İlk gerçek kullanımda (0.5.0 öncesi sürüm, Windows) üç şey zorladı:

1. **Parçaların ilişkisi çözülemedi.** Sınıf, derslik, oturma düzeni, düzen
   sürümü, sınav, dönem ve dağıtım adayının birbirine nasıl bağlandığı
   anlaşılmadı.
2. **Ekranlar çok kalabalıktı.** Hangi düğmenin önemli, hangisinin isteğe bağlı
   olduğu ayırt edilemedi.
3. **Yapılan işin sonucu görülmedi.** Bir düğmeye basınca ne olduğu, işin bitip
   bitmediği belli olmadı.

"Nereden başlayacağımı bilemedim" şikâyeti **yok**; bu yüzden ayrı bir kurulum
sihirbazı kapsam dışı.

Kök neden: uygulama iç veri yapısını olduğu gibi ekrana döküyor. Somut örnek:
bir dersliğin planını değiştirmek için "Kopyala ve düzenle" ile yeni sürüm
açmak gerekiyor; taslak sınavlar eski sürüme bağlı kalıyor, plan düzeltildiği
hâlde sınav eski planla dağıtılıyor.

## Yaklaşım

Kullanıcının gördüğü kavram sayısını azalt, her ekrana tek iş ver, her işlemin
sonucunu aynı yerde göster. Veritabanı şeması değişmez; değişen sunum ve iki
arka uç kuralıdır.

Reddedilen seçenekler: ayrı bir "Sınav hazırla" sihirbazı (aynı işi yapan iki
arayüz, çift bakım) ve yalnızca menüyü yeniden gruplamak (ilişkiyi anlatır ama
azaltmaz).

## Bölüm 1 — Derslikler

### Görünen

- Derslik kartına tıklanınca doğrudan o dersliğin oturma planı açılır; arada
  düzen listesi yoktur. Her dersliğin planı kendine özgüdür.
- Planın üstünde tek durum satırı (örnek: "36 koltuk · 2 sınavda kullanılıyor")
  ve tek ana düğme: **Planı düzenle**.
- "Kopyala ve düzenle", "sürüm", "şablon", "aktif yap" normal görünümde yer
  almaz.

### Düzenleme kuralı (arka uç)

- Plan hiçbir **kesinleşmiş** ya da arşivlenmiş sınavda kullanılmıyorsa
  değişiklik yerinde kaydedilir.
- Kullanılıyorsa uygulama planın o anki hâlini kendiliğinden saklar, değişikliği
  yeni hâle yazar ve yeni hâli dersliğin aktif planı yapar. Kesinleşmiş sınavın
  krokisi ve raporları değişmez. Kullanıcıya soru sorulmaz.
- **Taslak sınavlar dersliğin aktif planını izler.** Plan değişince o dersliği
  kullanan taslak sınavlar yeni plana bağlanır; varsa dağıtımları geçersiz
  sayılır ve sınav sayfası "Derslik planı değişti, yeniden dağıt" der.
- Arşiv yıllarının planları salt okunur kalır.

### İleri düzey (kapalı bölüm)

Aynı dersliğe ikinci plan tanımlama, planlar arasında geçiş (aktif yapma),
başka dersliğe kopyalama, şablon, eski hâlleri görme ve kullanılmayanları
silme. Bugünkü yeteneklerin tamamı burada kalır.

### Bilinen sonuç

Taslak sınavda derslik başına farklı plan seçmek normal akıştan çıkar; taslak
sınav her zaman dersliğin aktif planını kullanır. Sınava özel plan seçimi
sınav sayfasının ileri düzey bölümünde kalır.

## Bölüm 2 — Sınavlar

### Sınav listesi

- Her sınav tek satır: tarih, ad, sınava giren sınıf sayısı, durum ve **Aç**
  düğmesi. Durumlar: "Derslik seçilecek", "Dağıtılacak", "Kontrol bekliyor",
  "Kesinleşti", "Arşivde".
- Dönemler başlık olarak kalır; listede ayar durmaz. Dönem yönetimi listenin
  altında küçük bir bağlantıdır.
- Üstte tek belirgin düğme: **+ Yeni sınav**.
- Listede PDF düğmesi yoktur (kullanıcı onayı: raporlar sınav sayfasına taşınır).

### Sınav sayfası

- Bir seferde tek sınav gösterilir; üstte "← Sınavlara dön".
- Tepede beş adımlı şerit ve tek ana düğme. Altında **yalnızca geçerli adımın**
  içeriği durur:
  1. **Derslikler** — sınavın yapılacağı derslikler ve kapasite durumu.
  2. **Dağıtım** — "Dağıtımı başlat" ve ilerleme.
  3. **Kontrol** — derslik sekmeli oturma planı, varsa ihlal listesi, iki
     tıkla yer değiştirme.
  4. **Kesinleştirme** — özet ve onay kutusu.
  5. **Raporlar** — kroki, yoklama, listeler ve yazdırma.
- Tamamlanmış adımlara şeritten tıklayıp geri bakılabilir; ilerideki adımlar
  tıklanamaz.
- Yeni sınav oluşturulunca doğrudan o sınavın sayfası açılır.

### Kavram azaltma

- "Aday" kelimesi arayüzden kalkar; yalnızca "dağıtım" vardır.
- "Yeniden dağıt" yeni bir yerleşim üretir. Öncekine dönmek için tek bir
  "Önceki dağıtıma dön" düğmesi vardır; aday listesi gösterilmez.
- Raporlar sınavın son adımıdır. Menüdeki "Raporlar" bölümü kalır ve aynı
  bileşeni kullanır; iki ayrı rapor arayüzü olmaz.

### İleri düzey (sınav sayfasının altında kapalı bölüm)

Oturma kuralları, derslik sabitleyerek yeniden dağıtma, dönem değiştirme,
sınava özel plan seçimi, güncel öğrenci listesiyle karşılaştırma, kopyalama,
arşivleme ("Tamamlandı olarak işaretle").

## Bölüm 3 — Sonuç bildirimi

- Her kaydetme, silme, aktarma ve dağıtım işleminden sonra ekranın sağ altında
  aynı biçimde bir bildirim çıkar: ne oldu ve varsa sıradaki adım. Örnek:
  "9-A planı kaydedildi. 2 taslak sınav yeni planı kullanacak."
- Hata bildirimi aynı yerde çıkar ve ne yapılacağını söyler. Başarı bildirimi
  birkaç saniye sonra kendiliğinden kapanır; hata bildirimi kullanıcı kapatana
  kadar kalır.
- Süren işlerde düğme durumunu yazar ("Kaydediliyor…") ve iş bitene kadar
  tıklanamaz.
- Liste aktarımı bitince bildirim öğrenci ve derslik sayısını söyler ve
  Derslikler'e götüren bir bağlantı içerir.

## Teknik yapı

Bugün `ExamOrganizer.tsx` 1086, `ClassroomManager.tsx` 608 satır; 0.5.0'daki
iki gerileme sınav dosyasından çıktı. Bu çalışmada bileşenler tek amaçlı
parçalara ayrılır.

| Birim | Görevi | Bağımlılığı |
|---|---|---|
| `notify` (ortak bildirim) | Başarı/hata bildirimi gösterir | yok |
| `ExamList` | Sınavları dönem başlıklarıyla listeler | sınav API'si |
| `ExamPage` | Tek sınavın şeridini ve geçerli adımı gösterir | adım bileşenleri |
| `steps/RoomsStep`, `DistributeStep`, `ReviewStep`, `FinalizeStep`, `ReportsStep` | Her biri tek adımın içeriği | sınav API'si, `notify` |
| `SeatingPlan` | Derslik sekmeli oturma planı ve yer değiştirme | yok (veri prop ile gelir) |
| `ExamAdvanced` | İleri düzey sınav işlemleri | sınav API'si |
| `ClassroomList` | Derslik kartları | derslik API'si |
| `ClassroomPlan` | Bir dersliğin planı ve durum satırı | derslik API'si |
| `PlanEditor` | Plan düzenleme (mevcut düzenleyici, taşınır) | derslik API'si |
| `ClassroomAdvanced` | İkinci plan, kopyalama, eski hâller, silme | derslik API'si |

Arka uç:

- `services/layouts.py`: "kesinleşmiş sınavda kullanılıyorsa kopyala, değilse
  yerinde kaydet" kuralı ve taslak sınavların aktif plana yeniden bağlanması
  tek bir işlevde toplanır; masa/koltuk düzenleme uçları onu çağırır.
- Taslak sınav yeni plana bağlanınca dağıtımı geçersizleşir; sınav yanıtına
  bunu bildiren bir alan eklenir.
- Veritabanı şeması değişmez; migration yoktur.

## Hata durumları

- Plan değişince taslak sınavda koltuk sayısı öğrenci sayısının altına düşerse
  sınav "Derslikler" adımına döner ve eksik koltuk sayısını gösterir.
- Başka sekmede düzenlenen sınav (mevcut düzenleme kilidi) salt okunur açılır;
  davranış değişmez.
- Bildirim gösterilemese bile işlem sonucu ekranın durumuna yansır; bildirim
  tek bilgi kaynağı değildir.

## Test

Her davranış için önce düşen bir test yazılır, sonra kod.

- Birim: kullanılmayan plan yerinde kaydedilir; kesinleşmiş sınavda kullanılan
  plan kopyalanır ve eski kroki değişmez; taslak sınav yeni plana bağlanır ve
  dağıtımı geçersizleşir; kapasite düşünce sınav derslik adımına döner.
- Tarayıcı: derslik kartı doğrudan planı açar; plan değişince taslak sınav
  "yeniden dağıt" der; sınav sayfasında oluştur → dağıt → kontrol → kesinleştir
  → rapor yürünür; her işlemden sonra bildirim çıkar; normal görünümde "sürüm",
  "şablon", "aday" kelimeleri geçmez.
- Mevcut 96 birim testi ve 61 uçtan uca test geçmeye devam eder; arayüz
  metnine bağlı olanlar yeni metne göre güncellenir.

## Yayım

Kullanıcı kararı: üç parça ayrı sürümler hâlinde değil, **tek sürümde** (0.7.0)
yayımlanır. Geliştirme sırası yine bildirim → derslikler → sınavlar olur; her
parça kendi testleriyle `main` dışında tamamlanır, yayım hepsi bitince yapılır.

## Kapsam dışı

- Plan düzenleyicinin kendisi (masa sürükleme, üst üste binen masalar).
- Çıktıların baskı kalitesi ve rapor ayarları ekranı.
- Ayrı kurulum sihirbazı.
- Kural 8'in çapraza uygulanmaması kararı (ayrıca kullanıcı onayı bekliyor).

## Karar belgesiyle ilişki

Karar belgesi v4.3'teki kararlarla çelişen bir değişiklik yoktur: düzen
sürümleri ve geçmiş kayıtlar korunur (yalnızca sunumdan gizlenir), kesinleşmiş
dağıtımlar değişmez, kullanıcı verisi ve çevrimdışı çalışma etkilenmez.
