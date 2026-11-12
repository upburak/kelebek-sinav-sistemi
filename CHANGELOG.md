# Değişiklik günlüğü

## 0.8.0 — 12 Kasım 2026

### Toplu silme (Karar 73)

Kullanıcı isteği: her bölümde içeriğin komple silinebilmesi. Karar belgesi tek tek
kayıtların silinmemesini öngördüğü için bu, kullanıcının açık onayıyla **yeni bir
karar** olarak eklendi (Karar 73); mevcut kararların metni değişmedi.

- Sınavlar, Öğrenci kayıtları ve Derslikler bölümlerinde "Tümünü sil" düğmesi.
  Kesinleşmiş ve arşivlenmiş sınavlar da silinir.
- Öğrenciler ve derslik planları sınavlara bağlı olduğu için ikisinin silinmesi o
  yılın sınavlarını da siler; onay sorusu sayıları ayrı ayrı yazar.
- Her silmeden önce güvenlik yedeği alınır (`safety-bulk-delete-…zip`); yanlış
  silme Yedek ve arşiv bölümünden geri yüklenebilir.
- Yalnızca güncel eğitim yılında çalışır; arşiv yılları ve başka yılların
  kayıtları etkilenmez. Üretilmiş rapor PDF dosyaları da silinir.
- Testler: `backend/tests/test_bulk_delete.py` (9 test) ve
  `tests/e2e/test_zz_bulk_delete_ui_e2e.py` (ortak veriyi sildiği için en son koşar).

## 0.7.0 — 12 Kasım 2026

### Sade arayüz: derslikler, sınavlar ve sonuç bildirimi

İlk gerçek kullanımda üç şey zorladı: parçaların ilişkisi çözülemedi, ekranlar
çok kalabalıktı, yapılan işin sonucu görülmedi. Kök neden uygulamanın iç veri
yapısını (düzen sürümü, şablon, aday) olduğu gibi ekrana dökmesiydi. Tasarım:
`docs/superpowers/specs/2026-11-11-sade-arayuz-design.md`.

**Derslikler**

- Derslik kartına tıklayınca doğrudan o dersliğin oturma planı açılır.
  "Kopyala ve düzenle" adımı kalktı; "Planı düzenle" doğrudan düzenler.
- Plan kesinleşmiş bir sınavda kullanılıyorsa uygulama eski hâli kendiliğinden
  saklar ve değişikliği yeni hâle yazar; kesinleşmiş sınavın krokisi değişmez.
  Değilse plan yerinde kaydedilir. **Kapatılan açık:** kesinleşmiş sınavın planı
  arka uçta doğrudan değiştirilebiliyordu; koruma yalnızca arayüzdeydi.
- Taslak sınavlar dersliğin aktif planını izler. Plan değişince sınav sayfası
  "Derslik planı değişti, yeniden dağıt" der; koltuk öğrenci sayısının altına
  düşerse sınav derslik adımına döner.
- İkinci plan, şablon, aktif yapma, eski hâller ve silme "İleri düzey" altında.

**Sınavlar**

- Sınav listesi yalın satırlardır (tarih, ad, sınıf ve öğrenci sayısı, durum,
  "Aç"). Her sınavın kendi sayfası vardır; sayfada yalnızca geçerli adımın
  içeriği görünür. Tamamlanmış adımlara şeritten dönülebilir.
- Raporlar sınav sayfasının son adımıdır; menüdeki Raporlar bölümü aynı
  bileşeni kullanır. Listeden PDF düğmeleri kalktı.
- "Aday" kelimesi kalktı; önceki yerleşime dönmek için tek "Önceki dağıtıma dön".
- **Sınava giren sınıflar her zaman görünür** (öğrenci sayılarıyla). Kullanıcı
  beş sınıf seçtiğini düşündüğü bir sınavın dört sınıfla oluştuğunu ancak
  dağıtımdan sonra fark etmişti. Oluşturma formu ve bildirimi artık
  "5 sınıf · 166 öğrenci" yazar; sınıfın kendi dersliğinde koltuk yetmediği
  için eklenen derslik varsa adı ve nedeni söylenir. Sınıf işaretleme, art arda
  tıklamada işaret kaybetmeyecek biçimde sağlamlaştırıldı. İşaretin neden kayda
  geçmediği yeniden üretilemedi; kök neden doğrulanmış değildir.

**Sonuç bildirimi**

- Ortak bildirim (`frontend/src/notify.tsx`): başarı kendiliğinden kapanır, hata
  kullanıcı kapatana kadar kalır. Liste aktarımı, okul bilgileri, derslik adı,
  plan düzenleme, derslik seçimi ve yedek indirme bunu kullanır.

**Bağımsız incelemede bulunup düzeltilenler**

- "Sınıf" üç yerde üç farklı biçimde sayılıyordu (formda kutu başına, sınav
  sayfasında sınıf/şube başına). Aynı sınıfta alanı farklı öğrenciler iki ayrı
  kutu olduğu için birini seçmek sınıfın geri kalanını sessizce dışarıda
  bırakıyordu. Sayım artık her yerde sınıf/şube; sınıfın tamamı sınavda değilse
  "12/Z 2 öğrenci (sınıfta 3)" ve bir uyarı görünür. Bildirimdeki sayı sunucunun
  oluşturduğu kayıttan gelir.
- "Aktif yap" ve plan silme sonrası derslik ekranı eski planı göstermeye devam
  ediyordu; koltuğu olmayan plan aktif yapılabiliyordu; aktif olmayan bir planı
  düzenlemek dersliğin aktif plan seçimini değiştiriyordu.
- Başarı bildirimi açık bir hata bildirimini düşürebiliyordu.
- İki test yanlış nedenle geçiyordu (arşiv yılı düzenlemesi, hızlı tıklama).

**Bu sürümde yapılmayanlar**

- Tasarımdaki bileşenlere ayırma (`ExamOrganizer.tsx`, `ClassroomManager.tsx`)
  yapılmadı; davranışlar aynı dosyalarda yeniden düzenlendi. Kod sağlığı işi
  ayrı bir sürüme kaldı.
- Dağıtım, yer değiştirme ve kesinleştirme sonuçları hâlâ kendi yerlerinde
  gösteriliyor; ortak bildirime taşınmadı.

Testler: 4 yeni birim test modülü (plan düzenleme kuralı, derslik planı ucu,
sınavın plan izlemesi), 3 yeni tarayıcı test dosyası (bildirimler, derslik
planı, sınav sayfası).

## 0.6.1 — 11 Kasım 2026

- **İki sınıf seçilince bütün derslikler seçiliyordu.** 0.5.0'da gelen
  "derslikler kendiliğinden seçilsin" kolaylığı sınava kaç sınıfın girdiğine
  bakmıyor, koltuk yetiyorsa okulun bütün dersliklerini seçiyordu; dağıtım da
  iki sınıfın öğrencilerini sekiz dersliğe yayıyordu. Artık yalnızca sınava
  giren sınıfların kendi derslikleri ("9-A Derslik" gibi) seçilir. Koltuk
  yetmezse sırayla başka derslik eklenir; yine yetmezse seçim kullanıcıya
  bırakılır. Bildirimde hangi dersliklerin seçildiği yazar.
- Sınıf seçiminde "Tüm sınıfları seç / Seçimi temizle" düğmesi.
- Gerileme testi: `tests/e2e/test_exam_guided_flow_ui_e2e.py`.

## 0.6.0 — 11 Kasım 2026

### Çevrim içi sürüm denetimi ve tek tıkla güncelleme

- Uygulama açılışta (kapatılabilir) ve "Şimdi denetle" ile GitHub'daki son
  sürümü sorar. Yeni sürüm varsa her ekranda bir bildirim ve Yedek ve arşiv
  bölümünde "Sürüm X'i indir ve kur" düğmesi görünür.
- İndirme: önce güvenlik yedeği alınır; paket yalnızca projenin kendi sürüm
  adresinden kabul edilir, GitHub'ın bildirdiği SHA-256 özetiyle doğrulanır,
  İndirilenler klasörüne yazılır ve kurulum penceresi açılır. Özeti uyuşmayan
  dosya silinir.
- **Gizlilik ve çevrimdışı çalışma:** yalnızca sürüm numarası sorulur; okul,
  öğrenci ya da kullanım verisi gönderilmez. İnternet yoksa ya da denetim
  kapalıysa uygulama aynen çalışır (karar belgesi 18: temel işlevler internet
  gerektirmez).
- Sertifikalar önce işletim sisteminin deposundan, olmazsa paketle gelen kök
  sertifikalardan doğrulanır (okul ağlarındaki vekil sunucular için).
- **Ön koşul:** sürümlerin herkese açık yayımlanması gerekir. Depo gizliyken
  GitHub kimliksiz isteğe 404 döndürür; uygulama bunu açıklayan bir ileti
  gösterir ve çalışmaya devam eder.
- Eski "elle güncelleme paketi yükle" bölümü "ileri düzey" başlığı altına alındı.
- Testler: `backend/tests/test_online_update.py` (13 test, ağ taklit edilir).
  Gerçek GitHub yanıtıyla sürüm karşılaştırması ve paket seçimi ayrıca denendi.

## 0.5.0 — 11 Kasım 2026

### Sınav hazırlığı adım adım

İlk gerçek kullanımda sınav dağıtımı "inanılmaz zorlayıcı" bulundu: bir sınav
kartında derslik seçimi, kurallar, aday üretme, derslik sabitleme, "incelemeye
al", "son kontrol", karşılaştırma ve kopyalama aynı anda görünüyor, hangisinin
sıradaki adım olduğu anlaşılmıyordu. İşlevler değişmedi; sunum değişti.

- Her sınav kartında beş adımlı bir şerit (Derslikler → Dağıtım → Kontrol →
  Kesinleştirme → Raporlar), sıradaki adımın tek cümlelik açıklaması ve **tek
  ana düğme** var.
- **Daha az tıklama:** yeni sınavda her dersliğin aktif düzeni kendiliğinden
  seçilir (kapasite yetiyorsa); dağıtım sonucu ayrıca "incelemeye alınmadan"
  geçerli dağıtım olur. Sıfırdan kesinleşmiş sınava dört tıkla ulaşılır:
  oluştur → Dağıtımı başlat → Kontrol et ve kesinleştir → onayla.
- Oturma planı sekiz dersliği alt alta dizmek yerine **derslik sekmeleriyle**
  gezilir; ihlal bulunan dersliğin sekmesi işaretlenir, ihlalli öğrenciye
  tıklanınca ilgili sekmeye geçilir.
- Yalnızca geçerli dağıtım gösterilir; öncekiler "Önceki dağıtımlar" altında
  durur ve "Buna dön" ile geri alınabilir.
- Kurallar, derslik sabitleme, dönem değiştirme, liste karşılaştırma, arşivleme
  ve kopyalama "Diğer seçenekler" altına taşındı.
- Derslik seçiminde "Tüm derslikleri seç" düğmesi ve her dersliğin koltuk sayısı.
- Dil sadeleşti: "organizasyon taslağı" → "sınav", "aday" → "dağıtım",
  "incelemeye al" kalktı.
- Test: `tests/e2e/test_exam_guided_flow_ui_e2e.py` bu yolu tarayıcıda yürür.

### Aktif oturma düzeni ve düzen silme

Kullanıcı isteği: oluşturulmuş ama kullanılmayacak düzenler silinebilsin ve
hangi düzenin kullanılacağı belirlenebilsin.

- **Aktif düzen:** her derslik ve eğitim yılı için tek bir düzen "Aktif"tir.
  Derslikler ekranında "Aktif yap" ile değiştirilir. Sınav için derslik
  seçildiğinde varsayılan olarak aktif düzen gelir; Genel Bakış ve derslik
  kartlarındaki koltuk sayısı da aktif düzenden hesaplanır. Daha önce
  oluşturulmuş sınavların seçili düzeni değişmez.
- İlk oluşturulan düzen kendiliğinden aktif olur; düzenlemek için açılan yeni
  sürüm, kaynağı aktifse aktifliği devralır. Şablonlar aktif yapılamaz.
- **Silme:** hiçbir sınavda kullanılmayan düzen masaları ve koltuklarıyla
  silinir. Bir sınavda kullanılan düzen silinemez (düğme kapalı gelir, kaç
  sınavda kullanıldığı yazar). Aktif düzen silinirse kalan en yeni düzen aktif
  olur. Arşiv yıllarının düzenleri salt okunurdur.
- Migration `0020_active_layout`: mevcut verilerde her derslik/yıl için en son
  oluşturulan düzen aktif yapılır; güncelleme sonrası davranış değişmez.
- Testler: `backend/tests/test_layout_active_delete.py` (8 test).

## 0.4.2 — 11 Kasım 2026

İlk gerçek Windows denemesinde kullanıcı, 11–12. sınıfların alanlarını seçtikten
sonra nasıl devam edeceğini bulamadı: devam düğmesi alan kutularının *üstünde*,
ekranın dışında kalıyordu. Alan seçim panelinin altına "Alanları uygula ve devam
et" düğmesi eklendi; eksik seçim varken düğme neyin beklendiğini söyler.

## 0.4.1 — 11 Kasım 2026

Arayüzde daha önce elle denenmemiş akışlar gerçek tarayıcıda, 236 öğrencilik
sentetik okulla uçtan uca yürütüldü: taslakta koltuk değiştirme (yeni "manuel
sürüm" adayı ve ihlal listesi), kesinleşmiş sınavda koltuk değiştirme ile geri
al / yinele, sınavı kopyalama, tamamlayıp arşivleme, yedek paketini indirme ve
aynı paketle geri yükleme önizlemesi. Hepsi hatasız çalıştı; bu turda işlev
hatası bulunmadı.

Küçük düzeltmeler:

- Sınav için derslik seçenekleri de doğal sırayla gelir ("9-A", "10-A"dan önce);
  yeni sınavlarda rapor sayfaları bu sırayı izler.
- "Kesinleşti" ve "Tamamlandı · Arşiv" etiketleri taslakla aynı sarı yerine yeşil.
- Etkin menü öğesi fare üzerindeyken renk değiştiriyordu.
- Yeni test: yedek indirme ve geri yükleme önizlemesi tarayıcıda (onaysız geri
  yükleme başlatılamadığı dahil).

## 0.4.0 — 10 Kasım 2026

### Genel Bakış panosu ve kullanılabilirlik

- **Genel Bakış canlı veriden çalışıyor.** Eski "Kurulum adımları" kartı sabit
  yazılmıştı: 236 öğrenci ve 8 derslik kayıtlıyken bile "1 / 3 hazır" diyor,
  "Öğrenci ve sınıflar: Bekliyor" gösteriyordu. Yeni pano öğrenci, koltuk
  kapasitesi (öğrenci sayısıyla karşılaştırmalı), sınav ve son yedek durumunu,
  beş adımlı yol haritasını ve yaklaşan sınavları sıradaki işlemle birlikte
  gösterir. Kutular ilgili bölüme götürür.
- Öğrenci listesine arama ve sınıf/şube filtresi eklendi; tablo başlığı sabit.
- Derslik kartları kullanılabilir koltuk sayısını gösterir; "9-A" artık "10-A"dan
  önce sıralanır.
- Raporlar ekranındaki yanlış alt başlık ve çift başlık, sınav ekranındaki
  "Altı komşuluk kuralı" metni (artık sekiz) ve alt bilgi hizası düzeltildi.
- Paketler artık `main` dalına her birleştirmede kendiliğinden üretilir ve
  GitHub Releases altında yayımlanır.


### Koridor ve çapraz komşuluk (Karar 37 güncellendi)

Kullanıcı onayıyla komşuluk modeli üç ilişkiye ayrıldı:

- **Yan yana** artık koridoru aşar: koridorun iki kenarındaki öğrenciler de
  yan yana sayılır ve yan yana kuralları onlara da uygulanır.
- **Önlü arkalı** (doğrudan hizalı) ve **çapraz** koridoru aşmaz.
- Çapraz, önlü/arkalı kurallarına tabidir; tek istisna kural 8'dir (aynı sınıf
  seviyesi). Ölçüm: kural 8 çapraza da uygulanınca 236 öğrenci / 236 koltukta
  en iyi çözüm bile ~54 öğrenciyi etkiliyor (2×2'lik her pencere dört ayrı
  seviye ister). Çapraz dışarıda tutulunca 0 ihlal.

İhlal açıklamalarında ilişki artık "çapraz" olarak da belirtilir.

### Kural 7-8: aynı sınıf seviyesi yan yana/önlü arkalı oturamaz

Kullanıcı gerçek bir dağıtım krokisine bakıp **9/A ile 9/B öğrencisinin yan yana
oturduğunu** fark etti. İnceleme, kodun karar belgesine birebir uyduğunu gösterdi:
belge "9 ve 10. sınıflarda alan bilgisi bulunmadığı için 3–6 numaralı alan
kuralları bu öğrencilere uygulanmaz" diyor, dolayısıyla bu sınıflarda tek koruma
"aynı şube" kuralıydı. Farklı şubeden iki 9. sınıf öğrencisi yan yana
oturabiliyordu; oysa ikisi de aynı sınav kağıdını alır.

Yazılım hatası değil, kural kümesindeki boşluktu. Kullanıcı onayıyla iki kural
eklendi (karar belgesi v4.3, kural 7–8): **aynı sınıf seviyesindeki öğrenciler
yan yana / önlü arkalı oturamaz.** Şube ve alan ayrımı gözetilmez. Mevcut altı
kural aynen korundu, yeni kurallar da ayrı seçenekler olarak açılıp kapatılabilir
ve varsayılan olarak açık gelir (migration `0019_same_grade_rules` mevcut
sınavlarda da açık yapar).

Uygulanabilirliği eklemeden önce ölçüldü: 236 öğrenci, koltuk sayısı tam eşit →
2,9 saniyede optimal, 0 ihlal. Gerçek krokide aynı seviyeden yan yana oturan
masa sayısı 4'ten 0'a indi.

### Başlangıç derslik düzeni gerçek sınıfa uyuyor

Okul bildirdi: her derslikte **iki koridor** var ve 36 kişilik sınıfta **6 satır
çiftli masa** bulunuyor. İçe aktarmanın ürettiği taslak düzen ise karekök
temelliydi; 36 koltuk için 5 sütun × 4 satır ve **tek koridor** çıkarıyordu.
12 kişilik sınıfta hiç koridor bırakmıyordu.

Bu yalnızca görsel bir uyumsuzluk değildi: koridor, komşuluk grafiğini doğrudan
etkiler (koridorun iki yanındaki öğrenciler yan yana sayılmaz). Yanlış geometriyle
hesaplanan dağıtım, fiziksel sınıfa taşındığında farklı bir komşuluk tablosuna
oturuyordu.

Taslak artık iki koridorla ayrılmış üç blok çiftli masa üretir: 36 koltuk →
3 blok × 6 satır, 24 → 3 × 4, 12 → 3 × 2. Bu yalnızca başlangıç taslağıdır;
kullanıcı gerçek sınıf ölçülerine göre düzenlemeye devam eder.

Testler: `backend/tests/test_import_layout.py` (4 test) gerçek içe aktarma ucunu
kullanarak geometriyi ve koridorun komşuluğu kırdığını doğrular.
`test_seating_scale.py` artık elle kurulmuş yoğun ızgara yerine bu gerçek
düzeni ve uygulamanın kendi komşuluk hesabını kullanır.

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
