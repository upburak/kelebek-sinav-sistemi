# KELEBEK SINAV SİSTEMİ

## Ana Proje Gereksinimleri ve Karar Dokümanı

**Doküman türü:** Ana proje gereksinimleri (Markdown)\
**Sürüm:** 4.3\
**Durum:** Ana kararlar denetlendi; çapraz platform teknik mimariye geçildi\
**Kullanım:** Bu doküman, Kelebek Sınav Sistemi ile ilgili sonraki
çalışmaların temel referansıdır.

------------------------------------------------------------------------

## Sürüm geçmişi

  -----------------------------------------------------------------------
  Sürüm                   Değişiklik              Durum
  ----------------------- ----------------------- -----------------------
  1.0                     İlk ana karar ve        Önceki sürüm; korunuyor
                          gereksinim dokümanı     

  1.1                     Dağıtım kuralları 3--6  Güncel
                          arasındaki örtüşme      
                          giderildi. Kural 3--4   
                          farklı seviyelerdeki    
                          aynı alan               
                          öğrencilerini, Kural    
                          5--6 aynı seviyedeki    
                          aynı alan öğrencilerini 
                          kapsayacak şekilde      
                          tanımlandı.             
  -----------------------------------------------------------------------

  **1.4**  Teknik denetimde Karar 38 ve 39 eklendi: çok dersli tek bir
  dağıtımda komşuluk kurallarının tüm öğrenci havuzuna uygulanması;
  geçmiş dağıtımlar açıldığında öğrenci verilerinin güncel listeyle
  karşılaştırılması ve değişikliklerin kullanıcı onayıyla havuza
  alınması. Önceki sürüm korunur.

  **1.5**  Karar 40 eklendi: aynı dağıtımın birden fazla sekme veya
  pencerede açılması durumunda tek düzenleme oturumu; diğer oturumların
  salt okunur önizleme modunda çalışması. Önceki sürüm korunur.

------------------------------------------------------------------------

## 1. Dokümanın amacı ve değişiklik ilkesi

Bu doküman, Kelebek Sınav Sistemi için bugüne kadar alınan kararları tek
yerde toplar. Amaç, uygulamanın kapsamını, kullanıcı akışlarını, veri
modeline ilişkin temel kuralları, dağıtım davranışını, arayüzü,
raporları ve saklama yaklaşımını tutarlı biçimde korumaktır.

Bu doküman nihai ve değiştirilemez bir şartname değildir. Gerçek
geliştirme ve kullanım sırasında yeni ihtiyaçlar görülebilir.
Değişiklikler kontrollü biçimde yapılır:

1.  Mevcut gereksinim ve kararlar korunur.
2.  Yeni ihtiyaç veya sorun açıkça tanımlanır.
3.  Etkilenen kararlar belirlenir.
4.  Değişiklik kullanıcıyla değerlendirilip onaylanır.
5.  Dokümanın yeni sürümü oluşturulur; önceki sürüm kaybolmaz.
6.  Uygulama ve doküman aynı kararlarla uyumlu tutulur.

Kesinleşmiş sınav dağıtımında her işlem değişiklik geçmişine kaydedilir; zorunlu ayrı revizyon nesnesi oluşturulmaz. Kullanıcı geri alma/ileri alma ile geçmiş durumlara dönebilir. Raporların güncelliği ayrıca izlenir. Proje karar dokümanındaki değişiklikler ise doküman sürüm geçmişinde izlenir.

## 2. Projenin amacı ve kapsamı

Kelebek Sınav Sistemi, okul sınav organizasyonunu planlamak ve yürütmek
için geliştirilecek yerel bir uygulamadır.

**Sistem soru hazırlama, soru havuzu oluşturma, cevap anahtarı hazırlama
veya sınav değerlendirme yazılımı değildir.** Temel görevi sınava
girecek öğrencileri seçmek, derslikleri ve fiziksel oturma düzenlerini
tanımlamak, öğrencileri kurallara göre dağıtmak, dağıtımı kontrol etmek
ve organizasyon çıktıları üretmektir.

### 2.1. Temel işlevler

-   Okul, öğrenci, sınıf ve şube verilerini yönetmek.
-   Derslikleri ve fiziksel masa/oturma düzenlerini tanımlamak.
-   Farklı sınıf, şube, seviye ve alanlardan esnek sınav grupları
    oluşturmak.
-   Öğrencileri seçilen dersliklere ve oturma yerlerine otomatik
    dağıtmak.
-   Dağıtımı görsel olarak incelemek ve manuel düzenlemek.
-   Alternatif dağıtımlar üretmek, karşılaştırmak ve seçmek.
-   Dağıtım geçmişini, sürümleri ve revizyonları saklamak.
-   Oturma planı, derslik kapı krokisi, öğrenci listesi, yoklama
    çizelgesi ve genel raporlar üretmek.
-   PDF ve Excel dışa aktarma sağlamak.
-   Yedekleme, geri yükleme ve arşivleme yapmak.

### 2.2. Kullanıcı ve genişlemeye açıklık

İlk sürüm tek kullanıcı tarafından kullanılacaktır. Şu aşamada çok
kullanıcılı yapı, öğretmen hesapları ve gelişmiş rol/yetki ekranları
kapsam dışıdır.

Bununla birlikte mimari, ileride öğretmenlerin kendi hesaplarıyla giriş
yapabilmesine, kendi sınav listelerini oluşturmasına ve yetkilendirme
sistemine geçişe engel olmayacak şekilde tasarlanmalıdır. Bu olasılık
bugünkü kapsamı gereksiz yere büyütmek için gerekçe değildir.

## 3. Öğrenci ve sınıf verileri

### 3.1. Kayıt ve aktarım

-   Öğrenciler Excel ile toplu aktarılabilir.
-   Öğrenciler uygulama içinden manuel olarak da eklenebilir veya
    düzenlenebilir.
-   Excel üzerinden toplu güncelleme desteklenir.
-   Aktarım öncesinde hatalı, eksik ve çakışan kayıtlar kontrol edilir.
-   Kullanıcıya aktarım öncesi doğrulama özeti ve hatalar gösterilir.

### 3.2. Öğrenci alanları

Temel öğrenci bilgileri:

-   Okul numarası
-   Ad
-   Soyad
-   Sınıf seviyesi
-   Şube
-   Varsa alan

**Okul numarası okul genelinde benzersizdir ve öğrencinin tekil
tanımlayıcısıdır.** Aynı okulda farklı şubelerde tekrar edemez.

Sınıf/şube bilgisi, öğrencinin tekil kimliğinden ayrı olarak dağıtım ve
grup kurallarında kullanılır.

### 3.3. Sınıf seviyesi ve alan

-   9.  ve 10. sınıflarda alan bilgisi bulunmaz.
-   11. ve 12. sınıflarda alan bilgisi kullanılır.
-   Alan seçenekleri: Sayısal, Eşit Ağırlık, Sözel ve Dil.
-   9.  ve 10. sınıflarda alan alanı boş bırakılır; 11. ve 12.
        sınıflarda gerekli kabul edilir.

## 4. Esnek sınav grubu ve öğrenci havuzu

Kullanıcı sınava girecek öğrencileri sınıf seviyesi, şube ve alan
kombinasyonlarıyla seçebilir.

Örnekler:

-   Yalnızca belirli şubeleri seçmek.
-   Tüm 10. sınıfları seçmek.
-   11. sınıf Sayısal ve Eşit Ağırlık gruplarını seçmek.
-   Birden fazla seviyeden belirli şubeleri bir araya getirmek.
-   Aynı gün farklı derslere girecek farklı öğrenci gruplarını tek
    organizasyonda toplamak.

Seçilen öğrenciler tek bir dağıtım havuzunda birleştirilir. Aynı
öğrencinin yanlışlıkla havuza iki kez eklenmesi engellenir.

Aynı gün farklı ders ve seviyelerden öğrenciler bir arada organize
edilebilir. Sınava girmeyen öğrenciler normal derslerine devam edebilir.

## 5. Ders ve sınav organizasyonu

### 5.1. Ders seçiminin isteğe bağlı olması

Kullanıcı önceden zorunlu bir ders havuzu oluşturmak zorunda değildir.

Yeni bir sınav dağıtımı oluşturulurken:

-   Dağıtım/sınav adı ve tarihi girilir.
-   Kullanıcı isterse "Ders seçmek istiyorum" seçeneğini işaretler.
-   Ders, mevcut listeden seçilebilir.
-   Listede yoksa o anda yeni ders eklenebilir.
-   Eklenen ders sonraki kullanımlar için ders listesine eklenir.
-   Ders seçilmezse genel sınav dağıtımı oluşturulabilir.

Bir dağıtım birden fazla dersi kapsayabilir. Her ders için ilgili sınıf,
şube ve öğrenciler seçilebilir. Örneğin aynı organizasyonda 9. sınıflar
matematik, 11. sınıflar fizik, 12. sınıflar seçmeli felsefe sınavına
girebilir.

Ders listesi kullanım sırasında kendiliğinden oluşur; önceden kapsamlı
ders havuzu kurmak zorunlu değildir.

## 6. Derslik ve fiziksel oturma düzeni

### 6.1. Derslik şablonları

Her derslik bir kez tanımlanır ve sonraki sınavlarda şablon olarak
kullanılabilir. Kapasite ve fiziksel masa düzeni derslikten dersliğe
farklı olabilir. Yönetici gerektiğinde derslik şablonunu değiştirebilir.

### 6.2. Fiziksel sıra ve oturma yeri ayrımı

Fiziksel masa/sıra ile öğrencinin oturduğu koltuk/oturma yeri ayrı
kavramlardır.

Örnek 9/A dersliği:

-   36 kişilik kapasite.
-   3 blok.
-   Her blokta önden arkaya 6 fiziksel ikili masa.
-   Toplam 18 fiziksel ikili masa.
-   Her masada 2 ayrı oturma yeri.
-   Toplam 36 ayrı oturma yeri.

### 6.3. Oturma yeri numaralandırması

Her ikili masadaki iki oturma yeri ayrı numaralandırılır:

-   İlk fiziksel masanın iki oturma yeri: 1 ve 2.
-   İkinci fiziksel masanın iki oturma yeri: 3 ve 4.
-   Bu şekilde devam eder.
-   Örnek düzende sol blok 1--12, orta blok 13--24, sağ blok 25--36
    olur.

Bir fiziksel masa taşındığında üzerindeki oturma yerleri ve numaraları
birlikte taşınır. Öğrenci kartındaki numara oturma yeri numarasıdır.

### 6.4. Sınıf çizim editörü

CAD seviyesinde serbest çizim aracı yapılmayacaktır.

Önce kullanıcı satır/sütun sayısı, tekli/ikili masa tipi ve gerekirse
blok/koridor boşlukları gibi parametrelerle standart bir şablon
oluşturur. Ardından şablondaki fiziksel masaları sürükleyerek
yerleştirebilir ve konumlarını değiştirebilir.

Masa/oturma yerleri arasındaki "yan yana" ve "önlü arkalı" komşuluk
ilişkileri yalnızca sıra veya masa numarasından çıkarılmaz; çizim
editöründeki gerçek fiziksel konumlarına göre hesaplanır. Masalar
taşındığında komşuluk ilişkileri yeni konumlarına göre yeniden
değerlendirilir. Böylece otomatik dağıtım algoritması güncel yerleşime
uyum sağlar.

Sınıfın ekrandaki fiziksel görünümü sade ve işlevsel olmalıdır.
Ayrıntılı, gerçekçi, yoğun renkli mimari plan veya CAD görünümü
istenmemektedir. Basit masa/oturma yeri şekilleri, anlaşılır oturma yeri
numaraları, tahta yönü ve gerekli koridor boşlukları yeterlidir. Görsel
süs yerine okunabilirlik ve kolay düzenleme önceliklidir.

Tahta ve öğretmen masası, sınıfın başlangıç yönünü göstermeye yardımcı
olabilir.

### 6.5. Öğrenci kartı görünümü

Dijital oturma planında ve kapı krokisinde her oturma yerindeki öğrenci
kartı şu sırayı aynen korur:

1.  Üstte öğrencinin kendi sınıfı/şubesi.
2.  Ortada öğrencinin adı ve soyadı.
3.  Altta okul numarası.

Boş koltuk da fiziksel planda görünür; öğrenci bilgileri boş olur.

## 7. Dağıtım kuralları

Sınav bazında aşağıdaki sekiz kural ayrı ayrı açılıp kapatılabilir:

1.  Aynı şubedeki öğrenciler yan yana oturamaz.

2.  Aynı şubedeki öğrenciler önlü arkalı oturamaz.

3.  **Farklı sınıf seviyelerindeki aynı alan öğrencileri yan yana
    oturamaz.** Bu kural, örneğin 11. sınıf Sayısal ile 12. sınıf
    Sayısal öğrencilerinin yan yana oturmasını engeller.

4.  **Farklı sınıf seviyelerindeki aynı alan öğrencileri önlü arkalı
    oturamaz.**

5.  **Aynı sınıf seviyesindeki ve aynı alandaki öğrenciler yan yana
    oturamaz.** Bu kural, örneğin 11. sınıf Sayısal öğrencilerinin kendi
    aralarında yan yana oturmasını engeller.

6.  **Aynı sınıf seviyesindeki ve aynı alandaki öğrenciler önlü arkalı
    oturamaz.**

7.  **Aynı sınıf seviyesindeki öğrenciler yan yana oturamaz.** Şube ve
    alan ayrımı gözetilmez; örneğin 9/A ile 9/B öğrencisinin yan yana
    oturmasını engeller.

8.  **Aynı sınıf seviyesindeki öğrenciler önlü arkalı oturamaz.**

9.  ve 10. sınıflarda alan bilgisi bulunmadığı için 3--6 numaralı alan
    kuralları bu öğrencilere uygulanmaz; bu sınıflarda koruma 1--2 ve
    7--8 numaralı kurallarla sağlanır.

**Teknik anlam ayrımı:** 3--4 numaralı kurallar farklı sınıf seviyeleri
arasındaki aynı alan eşleşmelerini; 5--6 numaralı kurallar aynı sınıf
seviyesi içindeki aynı alan eşleşmelerini denetler. Böylece bu
kuralların kapsamı birbirinden ayrılır. Bu ayrım kullanıcı tarafından
onaylanmıştır.

**Kural 7--8 hakkında (10 Kasım 2026, kullanıcı onayı):** 9 ve 10. sınıflarda
alan bilgisi bulunmadığından, 7--8 numaralı kurallar eklenmeden önce bu
öğrenciler için tek koruma "aynı şube" kuralıydı. Farklı şubelerden iki 9. sınıf
öğrencisi yan yana oturabiliyordu; oysa ikisi de aynı sınav kağıdını alır.
Kullanıcı gerçek bir dağıtım krokisinde bu durumu fark edip kuralın eklenmesini
onayladı. Yeni sınavlarda ve mevcut kayıtlarda varsayılan olarak açık gelir.
Kural 7--8, 1--2 ve 5--6 numaralı kuralların kapsadığı durumları da içerir;
kurallar yine de ayrı seçenekler olarak korunur.

Bu sekiz kural ayrı seçenekler olarak korunacaktır; uygulama tasarımında
kullanıcı onayı olmadan birleştirilmemeli veya kaldırılmamalıdır.

## 8. Kapasite kontrolü

Dağıtım başlamadan önce:

1.  Sınava girecek öğrenci sayısı hesaplanır.
2.  Kullanılacak derslikler seçilir.
3.  Seçilen dersliklerin gerçek kullanılabilir kapasitesi hesaplanır.
4.  Kullanım dışı işaretlenmiş oturma yerleri kapasiteden çıkarılır.
5.  Öğrenci sayısının kullanılabilir toplam kapasiteyi aşmadığı
    doğrulanır.

Temel koşul:

`Öğrenci sayısı <= Kullanılabilir toplam kapasite`

Kapasite yetersizse otomatik dağıtım başlatılmaz; kullanıcıya açık bir
uyarı verilir.

## 9. Akıllı ve dengeli otomatik dağıtım

### 9.1. Dağıtım hedefi

Sınav grubundaki öğrenciler tek havuzda toplanır. Sistem, seçilen
kuralları sağlarken şube, sınıf seviyesi ve alan dağılımını derslikler
arasında mümkün olduğunca dengeli tutar.

Sabit öğrenci sayısı varsayılmaz. Her şube ve alan grubunun öğrenci
sayısı gerçek veriden hesaplanır.

Kullanıcı istemedikçe önce bir seviyeyi/şubeyi tamamen bir dersliğe
doldurup diğer derslikleri farklı seviyelere bırakacak bir dağıtım
yapılmamalıdır. Farklı sınıf ve şubeler, öğrenci sayıları ve kapasiteler
elverdiği ölçüde tüm dersliklere dengeli yayılmalıdır.

### 9.2. Optimizasyon ölçütleri

Algoritma birlikte değerlendirir:

-   Toplam öğrenci sayısı ve derslik kapasiteleri.
-   Şube, seviye ve alan gruplarının dersliklere dağılımı.
-   Kullanılabilir oturma yerleri.
-   Seçilen yan yana/önlü arkalı oturma kısıtları.
-   Boş koltukların dersliklere dengeli dağılımı.

Sadece sabit round-robin veya rastgele karıştırma yeterli kabul edilmez.
Uygun optimizasyon/constraint-solving yaklaşımı teknik tasarım
aşamasında seçilir.

Tüm koşullar aynı anda sağlanamıyorsa sistem sonucu başarılıymış gibi
göstermemeli; karşılanamayan kısıtları ve nedenlerini raporlamalıdır.

Aksi söylenmedikçe boş yerler dersliklere mümkün olduğunca dengeli
dağıtılır.

## 10. Otomatik dağıtım sonrası değerlendirme ve manuel müdahale

Her otomatik dağıtımın ardından değerlendirme ekranı açılır.

### 10.1. Değerlendirme içeriği

-   Toplam öğrenci sayısı.
-   Toplam ve kullanılabilir kapasite.
-   Boş koltuk sayısı.
-   Kullanılan derslikler.
-   Şube başına dersliklere dağılım.
-   9, 10, 11 ve 12. sınıf dağılımı.
-   Alan bazında dağılım.
-   Seçilen kuralların ihlal durumu.
-   Dersliklerin doluluk/boşluk durumu.
-   Manuel müdahale ihtiyacı.

### 10.2. Manuel düzenleme

Kullanıcı:

-   Bir veya daha fazla öğrenciyi seçip bulunduğu yerden kaldırabilir.
-   Öğrenciyi bekleyen öğrenci havuzuna alabilir.
-   Başka derslikteki bir öğrenciyi kaldırıp havuzdan başka bir
    öğrenciyi aynı koltuğa yerleştirebilir.
-   Birden fazla öğrenciyi toplu olarak taşıyabilir.
-   Belirli masa veya oturma yerlerini kullanım dışı bırakabilir.
-   Hedef derslik/sıra/oturma yerini seçebilir.
-   Öğrenci havuzunu sınıf, seviye, şube veya alanla filtreleyebilir.
-   Belirli bölgeye örneğin 10. sınıf veya 11. sınıf Eşit Ağırlık ya
    da 12. sınıf Sayısal öğrencisi yerleştirebilir.

Havuza alınan öğrencinin kaynak sınıfı ve önceki koltuk bilgisi korunur.

Kullanım dışı bırakılan koltuklar kapasiteden düşülür. Manuel işlem
sonrasında sistem dağılımı ve kuralları yeniden kontrol eder. Kural
ihlali varsa hangi öğrenci ve kuralla ilgili olduğunu açıklar; kullanıcı
uyarıdan sonra onaylarsa işlem gerçekleşir.

## 11. Kısmi ve tam yeniden dağıtım

Kullanıcı hem tüm dağıtımı hem de seçili bölümleri yeniden
oluşturabilir.

-   Beğendiği bir veya birden fazla dersliği sabitleyebilir.
-   Sabitlenen dersliklerdeki öğrenci yerleşimleri korunur.
-   Sabitlenmeyen derslikler yeniden optimize edilir.
-   İstenirse derslik yerine belirli öğrenci grupları yeniden dağıtıma
    dahil edilebilir.
-   Tam dağıtımı yeniden oluşturma seçeneği de bulunur.
-   Sabitlenen derslikler yeni dağıtımda korunur; diğer öğrenciler kalan
    kullanılabilir yerlere dağıtılır.
-   Kapasite ve oturma kuralları her yeniden dağıtımda yeniden kontrol
    edilir.

## 12. Alternatif dağıtımlar ve karşılaştırma

### 12.1. Alternatiflerin saklanması

Kullanıcı ihtiyacına göre bir veya daha fazla alternatif üretebilir.
Alternatif sayısı sabit değildir; örneğin bir, iki, üç veya daha fazla
olabilir.

İlk dağıtım ve daha sonra oluşturulan her alternatif ayrı bir seçenek
olarak saklanır. Yeni alternatif oluşturulması önceki dağıtımların
üzerine yazmaz veya onları silmez.

Örnek: İlk dağıtım + üç alternatif oluşturulmuşsa kullanıcı dört
seçeneğin tamamını görebilir.

Her alternatif için: - Bağımsız kayıt tutulur. - Hangi dağıtımdan
türetildiği izlenir. - Sabitlenen derslikler ve uygulanan koşullar
kaydedilir. - Önceki alternatifler açılabilir ve incelenebilir.

### 12.2. Karşılaştırma raporu

Alternatifler yan yana karşılaştırılabilir. Karşılaştırma, yalnızca
oturma planı görüntüsü değil, dağıtım değerlendirme raporunu da kapsar.

Her alternatif için: - Sınıf/şube bazında öğrenci sayıları. - Sınıf
seviyesi ve alan dağılımı. - Toplam öğrenci. - Kullanılan derslikler. -
Boş koltuklar. - Kapasite durumu. - Kural ihlalleri. - Dağılım dengesi
ve değerlendirme sonucu.

gösterilir.

Kullanıcı alternatifleri inceleyerek uygun olanı seçer. Önceki
dağıtımlar korunur.

## 13. Son kontrol ve kesinleştirme akışı

Dağıtım üretmek ile sınav organizasyonunu kesinleştirmek ayrı
aşamalardır.

İş akışı:

1.  Otomatik dağıtım ve alternatiflerin oluşturulması.
2.  Alternatiflerin karşılaştırılması ve uygun olanın seçilmesi.
3.  Son kontrol ekranı.
4.  Gerekirse manuel düzenleme ve yeniden analiz.
5.  Kullanıcının açık onayı.
6.  Dağıtımın kesinleştirilmesi ve kalıcı olarak kaydedilmesi.
7.  Rapor ve PDF/Excel çıktılarının oluşturulması.

Onaylanmamış alternatifler taslak durumunda kalır. Kesinleştirilen
dağıtım sınav organizasyonunun ana kaydı olur. Kesinleştirme öncesinde
raporların yanlışlıkla resmî/son çıktı olarak üretilmesi önlenir.

## 14. Kesinleşmiş dağıtımda doğrudan düzenleme ve kayıt geçmişi

Kesinleşmiş dağıtım kullanıcı tarafından doğrudan düzenlenebilir. Öğrenci taşıma, koltuk değiştirme, öğrenciyi bekleyen havuza alma veya diğer yerleşim değişiklikleri için ayrıca zorunlu bir revizyon nesnesi oluşturulmaz.

- Her işlem tarih/saat ve işlem ayrıntılarıyla değişiklik geçmişine kaydedilir.
- Geri alma/ileri alma ile önceki ve sonraki durumlara geçilebilir; yeni bir işlem geçmişteki bir noktadan başlatılsa da işlem geçmişi korunur.
- Dağıtımın güncel durumu esas alınır; raporlar bu durumdan üretilir.
- Dağıtımda raporu etkileyen değişiklik yapıldığında raporlar güncel değil olarak işaretlenir.
- Bu bölüm Karar 66 ve Karar 67 ile güncellenmiştir; eski sürümlerdeki zorunlu revizyon yaklaşımı artık geçerli değildir.

## 15. İşlem geçmişi, geri alma ve sürümleme

Önemli işlemler kayıt altına alınır:

-   Otomatik dağıtım.
-   Öğrenciyi havuza alma.
-   Öğrenci yerini değiştirme.
-   Derslik değiştirme.
-   Sınıf düzenini değiştirme.
-   Öğrenci ekleme/çıkarma.
-   Alternatif oluşturma.
-   Kesinleştirme ve revizyon.

Kayıtlarda tarih/saat ve mümkün olduğunda öğrencinin hangi
derslik/oturma yerinden nereye taşındığı tutulur.

Geçmiş zaman çizelgesi biçiminde görüntülenebilir. Kullanıcı geçmişteki
bir duruma dönebilir ve daha sonra ileri sürümlere yeniden gidebilir.
İleri sürümler silinmemelidir. Dallanabilen sürüm geçmişi/checkpoint
yaklaşımı teknik tasarımda değerlendirilir.

## 16. Arşiv ve eski dağıtımı kopyalama

Çok sayıda dağıtım saklanabilir. Arşiv kayıtlarında mümkün olduğunca şu
bilgiler bulunur:

-   Dağıtım adı ve tarihi.
-   Ders/konu bilgisi.
-   Sınıf seviyeleri, alanlar ve şubeler.
-   Derslikler ve öğrenci listesi.
-   Uygulanan kurallar.
-   Oluşturulma ve değişiklik tarihleri.
-   Oturma planları.
-   Değişiklik geçmişi.

Eski dağıtım yeniden açılıp başlangıç olarak kullanılabilir. Öğrenci
nakli, ayrılma veya yeni öğrenci gibi değişiklikler yapılabilir.

Eski kayıt kesinlikle değiştirilmez. Eski dağıtımdan kopya alınarak yeni
ve bağımsız bir dağıtım oluşturulur. Yeni dağıtıma yeni isim ve tarih
verilir; eski isim önerilebilir. Yeni dağıtım kendi sürüm geçmişine
sahip olur.

## 17. Çok günlük sınavlarda oturma yeri çeşitliliği

İleri geliştirme özelliği olarak, birden fazla gün süren sınavlarda
öğrencilerin her gün farklı yerlerde oturması desteklenebilir.

Sistem önceki günlerin koltuk ve komşuluk bilgilerini dikkate alarak
aynı koltuk ve komşu kombinasyonlarının tekrarını mümkün olduğunca
azaltmaya çalışır.

Bu özellik sınav güvenliğini destekler; kopyayı tek başına önlediği
iddia edilmez.

## 18. Uygulama mimarisi ve çalışma biçimi

### 18.1. Yerel web uygulaması ve çapraz platform hedefi

Uygulama masaüstü tarayıcısında çalışan yerel web uygulaması olacaktır. Öncelikli geliştirme ve test ortamı kullanıcının Apple Silicon MacBook bilgisayarıdır. Bununla birlikte aynı kaynak kod tabanı macOS ve Windows üzerinde çalışmalıdır.

- Uygulama internet bağlantısı olmadan temel işlevlerini yerine getirmelidir.
- macOS ve Windows için ayrı kurulum/çalıştırma paketleri hazırlanır; işletim sistemine özgü paketler aynı kaynak kodundan üretilir.
- Masaüstü kısayolu uygulamanın yerel servisini başlatır ve varsayılan tarayıcıda uygulamayı açar.
- Chrome, Edge, Firefox ve Safari gibi güncel tarayıcılar desteklenir; arayüz belirli bir tarayıcıya bağımlı tasarlanmaz.
- Yerel servis yalnızca kullanıcının bilgisayarındaki loopback arayüzüne (127.0.0.1/localhost) bağlanır; ağdaki diğer cihazlara kendiliğinden açılmaz.
- Uygulama kapatıldığında veriler kalıcı kalır.

### 18.2. Önerilen teknoloji mimarisi

- **Backend:** Python ve Flask tabanlı yerel HTTP/API servisi.
- **Servis sunucusu:** Geliştirme sunucusu yerine paketlenmiş uygulamada çapraz platform WSGI sunucusu (ör. Waitress).
- **Frontend:** TypeScript tabanlı React arayüzü; özel sekmeli/pencereli çalışma alanı, sürükle-bırak sınıf editörü ve görsel oturma planları.
- **Veritabanı:** SQLite; veri erişimi SQLAlchemy üzerinden.
- **Şema geçişleri:** Alembic migration dosyaları.
- **PDF:** ReportLab.
- **Excel:** OpenPyXL.
- **Dağıtım optimizasyonu:** OR-Tools CP-SAT birincil kısıt optimizasyon adayı; sezgisel başlangıç ve yerel iyileştirme katmanlarıyla birlikte değerlendirilecektir.
- **Paketleme:** Python uygulaması ve derlenmiş frontend varlıkları macOS ve Windows için ayrı ayrı paketlenir. PyInstaller ve işletim sistemine uygun kurulum üreticileri teknik prototipte doğrulanır.

Teknoloji seçimi, bu gereksinimleri karşılayan teknik mimari kararıdır; uygulama geliştirme sırasında ölçülebilir testlerle doğrulanır. Kullanıcı onayı olmadan temel kullanıcı iş akışları değiştirilmez.

### 18.3. Veri saklama ve işletim sistemi dizinleri

Ana veriler tarayıcı cookie, cache veya localStorage içinde tutulmaz. Kalıcı veriler işletim sisteminin kullanıcıya ait uygulama veri dizininde saklanır; kurulum klasöründen ayrı tutulur.

- macOS: `~/Library/Application Support/KelebekSinavSistemi/`
- Windows: `%LOCALAPPDATA%\KelebekSinavSistemi\`

Her iki platformda aynı mantıksal klasör yapısı kullanılır: `Database/`, `Backups/`, `Exports/PDF/`, `Exports/Excel/`, `Settings/` ve `Logs/`. İşletim sistemine göre gerçek kök dizin değişir.

Tarayıcı geçmişi/cache/cookie temizliği, uygulama güncellemesi veya uygulamanın yeniden kurulması ana verileri silmemelidir. Uygulama veritabanı ve kullanıcı dosyaları kurulum paketinin içine yazılmaz.

### 18.4. Sürümleme ve artımlı güncelleme

Kaynak kod Git deposunda tutulur. Her yayımlanan sürüm etiketlenir; sürüm notları, değişen dosyalar, platform paketleri ve veritabanı migration'ları birlikte tanımlanır.

- Kullanıcıya gerektiğinde tam kurulum paketi ve yalnızca değişen dosyaları içeren artımlı güncelleme paketi sunulur.
- Artımlı paket, değişen kod/arayüz dosyaları yanında gerekiyorsa sıralı veritabanı migration dosyalarını da içerir.
- Güncelleme öncesi otomatik güvenlik yedeği alınır; uygulama ve veritabanı sürüm uyumluluğu kontrol edilir.
- Paket içindeki dosyaların bütünlüğü kontrol edilir; migration başarısız olursa güvenli geri dönüş sağlanır.
- macOS ve Windows çalıştırılabilir paketleri ayrı üretilir. Ortak Python/TypeScript kaynak kodu ve ortak iş mantığı korunur.
- Kullanıcıya her küçük değişiklikte bütün projeyi elle yeniden kurdurmak yerine, doğrulanmış artımlı güncelleme akışı sağlanır.

Aynı SQLite veritabanı dosyası iki bilgisayarda eş zamanlı olarak bulut klasörü üzerinden paylaşılmaz. MacBook ve Windows arasında veri taşımak için Karar 17 ve 44'teki doğrulanmış taşınabilir yedek paketi kullanılır.

## 19. Yedekleme ve geri yükleme

Hem otomatik hem manuel yedekleme desteklenir.

### 19.1. Otomatik yedek

-   Günlük otomatik yedek.
-   Önemli işlemler öncesi güvenlik yedeği.
-   Tarih/saat bilgisi.
-   Eski yedeklerin kontrollü temizliği.

### 19.2. Manuel yedek

Kullanıcı istediği zaman yedek oluşturabilir ve hedef konumu seçebilir.
USB bellek, harici disk veya başka bilgisayara aktarım desteklenmelidir.

### 19.3. Yedek kapsamı

Yedek yalnızca veritabanını değil, gerekli uygulama ayarlarını, sınıf
şablonlarını, derslik çizimlerini, dağıtım geçmişini ve ilgili dosyaları
da içermelidir. Taşınabilir ZIP veya sürümlü yedek paketi yaklaşımı
tercih edilir.

### 19.4. Geri yükleme

-   Yedek bütünlüğü doğrulanır.
-   Mevcut veritabanı geri yükleme öncesinde güvenlik yedeğine alınır.
-   Kullanıcıdan açık onay alınır.
-   Geri yükleme işlemi kontrollü biçimde gerçekleştirilir.

## 20. Arayüz ve çalışma alanı

Hazır ve birbirine benzeyen standart AI admin dashboard tasarımı
istenmemektedir.

Arayüz, masaüstü çalışma alanı hissi veren özgün bir tasarıma sahip
olmalıdır.

**Hibrit çalışma alanı kararı:** - Sekmeli görünüm. - Serbest
taşınabilir ve boyutlandırılabilir pencereler. - Küçültülmüş pencereler
için alt çalışma çubuğu. - Aynı anda öğrenci havuzu, farklı derslik
oturma planları ve değişiklik geçmişi gibi modüllerin açık olabilmesi. -
Pencere kapatılması veriyi silmez. - Kaydedilmemiş değişiklik varsa
kullanıcı uyarılır.

## 21. Raporlama ve dışa aktarma

### 21.1. Temel çıktı türleri

Aşağıdaki çıktıların tümü desteklenmelidir:

-   Sınıf bazlı görsel oturma planı PDF.
-   Sınıf bazlı öğrenci listesi PDF/Excel.
-   Derslik kapı listesi/krokisi PDF.
-   Öğrenci yoklama listesi PDF.
-   Genel sınav dağıtım listesi PDF/Excel.
-   Salon bazlı öğrenci listesi PDF/Excel.

Çıktılarda uygun olduğu ölçüde dağıtım adı, sınav tarihi, ders bilgisi
ve derslik numarası bulunur.

Yoklama listesinde +/− işaretlenebilecek geniş bir boş yoklama alanı
bulunur. Şu an için imza alanı zorunlu değildir.

### 21.2. Kapı krokisi

Derslik kapısına asılacak oturma planı basit isim listesi veya şematik
eskiz değildir. Sınıf çizim editöründe oluşturulan fiziksel masa
düzenini esas alan gerçek bir derslik krokisi olmalıdır.

Krokide: - Tahta/öğretmen masası yönü. - Fiziksel masa blokları ve
koridor boşlukları. - Masalar ve ayrı oturma yerleri. - Her oturma
yerinin numarası. - Öğrenci kartları. - Boş koltuklar.

gösterilir.

Öğrenci kartı sırası aynen korunur: üstte öğrencinin kendi
sınıfı/şubesi, altında ad soyadı, onun altında okul numarası.

### 21.3. Kâğıt boyutu ve sayfa ayarları

-   Varsayılan kâğıt boyutu A4 olur.
-   Kullanıcı A3, A5, Letter, Legal ve desteklenen diğer boyutları
    seçebilir.
-   Dikey/yatay yön seçilebilir.
-   Kenar boşlukları ve ölçeklendirme ayarlanabilir.
-   PDF ön izlemesi sunulur.
-   İçerik ve yazı boyutları seçilen sayfa düzenine uyarlanır.

A4 zorunlu değildir; yalnızca varsayılan başlangıç tercihidir.

### 21.4. Rapor içeriğini özelleştirme

Raporlama ekranında kullanıcı rapor türünü seçer ve görünmesini istediği
bilgileri ayarlayabilir. Örneğin başlık, tarih, ders, sınıf, derslik ve
öğrenci kartı alanları gösterilip gizlenebilir.

### 21.5. Dağıtım bazlı raporlara erişim

Her kesinleşmiş dağıtım kendi raporlarına ve oturma planlarına sahip
olur. Kullanıcı geçmiş bir dağıtımı açtığında o dağıtımın raporlarına
doğrudan ulaşabilir.

Raporlar PDF veya Excel olarak indirilebilir. İndirilen Excel dosyasında
kullanıcı başlıkları, sütunları ve diğer içerikleri kendi ihtiyacına
göre değiştirebilir. Bu değişiklikler uygulamadaki dağıtım kaydını
etkilemez.

Dağıtımın kendisi değiştirildiğinde mevcut rapor seti güncel değil olarak
işaretlenir. Kullanıcı son yerleşimi kabul edip raporları yeniden
oluşturduğunda yeni raporlar güncel dağıtım durumundan üretilir. Önceki
rapor dosyalarının ayrıca tarihsel arşiv olarak tutulması zorunlu
değildir; yeni raporlar eski dosyaların yerini alabilir. Değişiklik
günlüğü ve geri/ileri alma geçmişi raporlardan bağımsız olarak korunur.

Rapor şablonlarını ayrıca arşivlemek zorunlu bir iş akışı değildir.

------------------------------------------------------------------------

## 22. Teknik denetim kararları

### Karar 35 -- Dağıtım kurallarının teknik ayrımı

Altı dağıtım kuralının kapsamı şu şekilde ayrılmıştır:

1.  Aynı şubedeki öğrenciler yan yana oturamaz.
2.  Aynı şubedeki öğrenciler önlü/arkalı oturamaz.
3.  Farklı sınıf seviyelerinde bulunan, aynı alandaki öğrenciler yan
    yana oturamaz.
4.  Farklı sınıf seviyelerinde bulunan, aynı alandaki öğrenciler
    önlü/arkalı oturamaz.
5.  Aynı sınıf seviyesinde ve aynı alanda bulunan öğrenciler yan yana
    oturamaz.
6.  Aynı sınıf seviyesinde ve aynı alanda bulunan öğrenciler önlü/arkalı
    oturamaz.

Böylece 3--4. kurallar farklı seviyelerdeki aynı alan öğrencilerini;
5--6. kurallar aynı seviyedeki aynı alan öğrencilerini kapsar. Bu ayrım
kullanıcı tarafından onaylanmıştır.

### Karar 36 -- Fiziksel komşuluk hesabı ve sınıf görünümünün sadeliği

-   "Yan yana" ve "önlü/arkalı" ilişkileri masa numarasına veya sabit
    sıra indeksine göre değil, sınıf çizim editöründeki gerçek fiziksel
    konumlara göre belirlenir.
-   Masa veya blok taşındığında komşuluk ilişkileri yeni yerleşime göre
    yeniden hesaplanır.
-   Sınıf görünümü sade ve işlevsel olur; ayrıntılı, gerçekçi, yoğun
    renkli mimari çizim/CAD görünümü yapılmaz.
-   Basit masa ve oturma yeri şekilleri, oturma yeri numaraları, tahta
    yönü ve gerekli koridor boşlukları yeterlidir.
-   Öncelik görsel süsten ziyade okunabilirlik, anlaşılabilirlik ve
    kolay düzenlemedir.

Komşuluğun geometrik olarak hangi mesafe/eşik ve yön toleranslarıyla
hesaplanacağı teknik tasarım ve prototip testinde netleştirilecektir; bu
ayrıntı kullanıcıyla ayrıca kararlaştırılacaktır.

### Karar 37 -- Koridor sınırları ve çapraz önlü/arkalı komşuluk

-   Koridorla birbirinden ayrılmış masa blokları arasında komşuluk
    ilişkisi kurulmaz. Koridorun karşı tarafındaki masalar yan yana,
    önlü/arkalı veya çapraz komşu kabul edilmez.
-   Aynı blok içinde, ardışık ön/arka sıralarda doğrudan hizalı oturma
    yerlerinin yanı sıra çapraz konumdaki oturma yerleri de önlü/arkalı
    komşuluk kapsamında değerlendirilir.
-   Çapraz komşuluk, önlü/arkalı oturma kuralına eklenir; ayrı bir kural
    seçeneği olarak sunulmaz.
-   Yan yana kuralı yalnızca aynı sıradaki yatay komşuluğu kapsar.
    Çapraz komşuluk yan yana kuralına dahil edilmez.
-   Çapraz komşuluk hesabı da masaların gerçek fiziksel konumuna ve
    blok/ koridor sınırlarına göre yapılır.

### Karar 38 -- Farklı ders gruplarında komşuluk kurallarının uygulanması

- Aynı sınav organizasyonu birden fazla dersi ve farklı sınıf seviyelerini
  kapsayabilir.
- Her öğrenci yalnızca kendi sınavına katılır; ancak ders bilgisinin farklı
  olması, öğrenciler arasındaki fiziksel komşuluk kurallarını değiştirmez.
- Daha önce tanımlanan altı komşuluk kuralı, ders ayrımı yapılmaksızın
  dağıtıma katılan bütün öğrenciler üzerinde uygulanır.
- Öğrencinin sınıf/şube, seviye ve alan bilgileri ilgili kuralların
  değerlendirilmesinde esas alınır.

### Karar 39 -- Güncel öğrenci verilerinin geçmiş dağıtımlarla karşılaştırılması

- Geçmiş bir dağıtım açıldığında sistem, dağıtımda kayıtlı öğrenci
  bilgilerini güncel öğrenci listesiyle okul numarası üzerinden
  karşılaştırır.
- Okul numarası öğrencinin sabit ve benzersiz kimliğidir. Sınıf seviyesi,
  şube ve özellikle 11-12. sınıflardaki alan bilgisi zaman içinde
  değişebilir. Öğrencinin adı gibi diğer bilgilerdeki değişiklikler de
  karşılaştırmada tespit edilir.
- 9 ve 10. sınıflarda alan değişikliği kontrolü uygulanmaz; bu seviyelerde
  alan bilgisi bulunmadığından sınıf/şube ve diğer kayıt değişiklikleri
  kontrol edilir.
- Sistem tespit ettiği değişiklikleri kullanıcıya belirgin biçimde
  bildirir; geçmiş dağıtımın kayıtlı hâlini kendiliğinden değiştirmez.
- Kullanıcı değişikliği onaylarsa ilgili öğrenci mevcut oturma yerinden
  çıkarılarak bekleyen öğrenci havuzuna alınır ve eski oturma yeri boş
  bırakılır. Böylece öğrenci güncel sınıf/şube/alan bilgileri ve geçerli
  komşuluk kuralları dikkate alınarak yeniden yerleştirilebilir.
- Kullanıcı onayı olmadan öğrenci otomatik olarak yerinden çıkarılmaz.
- Bu işlem, geçmiş dağıtımın önceki sürümünü silmez veya üzerine yazmaz;
  yapılan işlem dağıtımın değişiklik/revizyon geçmişinde izlenir.

## 23. Kesinleşen kararların kısa özeti

  ---------------------------------------------------------------------
                           No Karar başlığı        Durum
  --------------------------- -------------------- --------------------
                           01 Öğrenci verisi:      Kesinleşti
                              Excel ve manuel      
                              kayıt                

                           02 Sınıf seviyesi ve    Kesinleşti
                              alan yapısı          

                           03 Esnek sınav grubu ve Kesinleşti
                              öğrenci havuzu       

                       04--05 Derslik fiziksel     Kesinleşti
                              düzeni ve            
                              numaralandırma       

                           06 Altı dağıtım kuralı  Kesinleşti

                           07 Kapasite kontrolü    Kesinleşti

                           08 Öğrenci havuzu       Kesinleşti
                              anahtarları          

                           09 Kaydetme ve manuel   Kesinleşti
                              müdahale             

                       10--11 İşlem geçmişi,       Kesinleşti
                              geri/ileri alma ve   
                              kural kontrolü       

                           12 Arşiv ve eski        Kesinleşti
                              dağıtımı kopyalama   

                       13--14 İsteğe bağlı ve      Kesinleşti
                              esnek ders seçimi    

                           15 Çok günlük           İleri geliştirme
                              sınavlarda koltuk    
                              çeşitliliği          

                           16 Yerel web uygulaması Tercih edildi
                              mimarisi             

                           17 Otomatik ve manuel   Kesinleşti
                              yedekleme            

                       18--19 Hibrit çoklu pencere Kesinleşti
                              çalışma alanı        

                           20 Sınıf çizim editörü  Kesinleşti

                           21 PDF/Excel raporları  Kesinleşti
                              ve çıktılar          

                       22--23 Dengeli ve akıllı    Kesinleşti
                              otomatik dağıtım     

                           24 Dağıtım              Kesinleşti
                              değerlendirme ve     
                              manuel kontrol       

                           25 Kısmi ve tam yeniden Kesinleşti
                              dağıtım              

                           26 Alternatif           Kesinleşti
                              dağıtımların         
                              saklanması           

                           27 Alternatiflerin      Kesinleşti
                              karşılaştırmalı      
                              raporlanması         

                           28 Son kontrol,         Kesinleşti
                              kesinleştirme ve     
                              rapor üretimi        

                           29 Kesinleşmiş          Kesinleşti
                              dağıtımda revizyon   

                       30--31 Kapı krokisi ve      Kesinleşti
                              öğrenci kartı        
                              görünümü             

                           32 Esnek kâğıt boyutu   Kesinleşti
                              ve sayfa ayarları    

                       33--34 Özelleştirilebilir   Kesinleşti
                              ve dağıtım bazlı     
                              raporlar             
                           35 Dağıtım kurallarının Kesinleşti
                              teknik ayrımı        
                           36 Fiziksel komşuluk   Kesinleşti
                              ve sade sınıf        
                              görünümü             
                           37 Koridor sınırları   Kesinleşti
                              ve çapraz komşuluk   
                           38 Çok dersli          Kesinleşti
                              dağıtımda komşuluk   
                              kuralları            
                           39 Güncel öğrenci      Kesinleşti
                              verisi kontrolü ve  
                              onaylı havuza alma   
                           40 Tek düzenleme       Kesinleşti
                              oturumu ve salt     
                              okunur önizleme     
                           41 Çok günlük oturum  Kapsamı ertelendi;
                              ve takvimden        isteğe bağlı / gelecek
                              otomatik oluşturma  geliştirme
  ---------------------------------------------------------------------

**Teknik denetim kapsamında eklenen kararlar:**

-   **35:** Kural 3--4 farklı seviyelerdeki aynı alan öğrencilerini;
    Kural 5--6 aynı seviyedeki aynı alan öğrencilerini kapsar.
-   **36:** Yan yana/önlü-arkalı ilişkileri masaların çizim editöründeki
    gerçek konumlarına göre hesaplanır. Sınıf görünümü sade, az renkli
    ve işlevsel tutulur.

### 23.1. Karar kayıtlarının tamamlanması ve güncel karar önceliği

Bu dokümanın önceki sürümlerinde bazı kararlar yalnızca değişiklik özeti veya konuşma kaydı içinde yer aldığından, aşağıdaki kararlar bu sürümde ana karar metnine açık biçimde eklenmiştir:

- **Karar 58 – Dağıtım sırasında kullanıcı deneyimi:** Dağıtım motoru çalışırken kullanıcı özel işlem ekranında kalır; aşama, geçen süre, tahmini kalan süre ve bulunan en iyi çözüm gösterilir. Kullanıcıdan arka planda başka iş yapması beklenmez.
- **Karar 59 – 11/12 alan verisinin kaynağı:** e-Okul listesinde alan bilgisi bulunmayabileceğinden 11 ve 12. sınıfların alan bilgisi ayrıca tanımlanır.
- **Karar 61 – Öğrenci listesi güncellemesi:** Yeni e-Okul listesi yalnızca liste değiştiğinde aktarılır; sistem önceki listeyle karşılaştırıp yeni, ayrılan ve bilgisi değişen öğrencileri gösterir. Kullanıcı onayıyla güncellenir. Değişmemiş listeyi her sınav öncesi tekrar yüklemek gerekmez.

**Karar önceliği:** Aynı konu hakkında eski ana bölüm ile daha sonra alınmış numaralı karar farklı hükümler içeriyorsa, daha yeni ve açıkça onaylanmış karar geçerlidir. Bu nedenle özellikle Karar 66-67, eski bölüm 14 ve 21.5'teki zorunlu revizyon/rapor saklama ifadelerini güncellemiştir.

## 24. Geliştirme sırasında ayrıca netleştirilecek konular

Ana kullanıcı işleyişi ve temel kararlar belirlenmiştir. Bundan sonraki maddeler yeni kullanıcı kararı değil, teknik tasarım ve test işidir:

- Veritabanı tabloları, ilişkiler, indeksler ve veri bütünlüğü.
- Değişiklik geçmişi, dallanma, checkpoint ve geri/ileri alma veri modeli.
- Fiziksel komşuluk geometrisi için mesafe/eşik ve yön toleranslarının prototip testleri.
- OR-Tools/CP-SAT ile sezgisel yöntemlerin gerçek sınıf verilerinde performans karşılaştırması.
- macOS Apple Silicon ve Windows için ayrı paketleme/kurulum, servis başlatma ve kapatma testleri.
- PDF sayfa yerleşimleri, Türkçe fontlar, yazdırma ve tek sayfalık kroki testleri.
- e-Okul dosyası aktarımı, alan atama ve liste karşılaştırma doğrulaması.
- Taşınabilir yedek paketi, sürüm uyumluluğu ve iki işletim sistemi arasında geri yükleme testleri.
- Artımlı güncelleme manifesti, dosya hash kontrolü, veritabanı migration ve geri dönüş testi.
- Hibrit çoklu pencere arayüzü, sürükle-bırak ve tek düzenleme oturumu testi.

Bu teknik çalışmalar, kesinleşmiş kullanıcı kararlarını sessizce değiştirme yetkisi vermez. Gereksinimi etkileyen gerçek bir değişiklik gerekiyorsa kullanıcıya yalnızca ilgili konu sorulur.

## 25. Sonraki çalışma yöntemi

Sonraki aşamalarda bu dosya ana referans olarak kullanılacaktır.

Yeni bir özellik veya değişiklik talebinde: 1. İlgili mevcut karar
bulunur. 2. Talebin yeni özellik mi, düzeltme mi, kapsam değişikliği mi
olduğu belirlenir. 3. Etkilenen iş akışları değerlendirilir. 4.
Gerekirse tek tek açıklayıcı sorular sorulur. 5. Kullanıcı onayıyla
karar güncellenir. 6. Ana dokümanın yeni sürümü hazırlanır ve önceki
sürüm korunur.

**Temel ilke:** Önce doğru çalışan sınav organizasyonu sistemi; ardından
gerçek kullanım geri bildirimleriyle kontrollü iyileştirme. Gereksiz
özelliklerle kapsam büyütülmez, alınmış kararlar unutulmaz ve kullanıcı
onayı olmadan değiştirilmez.


## 26. Karar 40 – Sekmeler ve pencereler arasında düzenleme çakışmasının önlenmesi

Aynı sınav dağıtımı birden fazla tarayıcı sekmesinde veya uygulama penceresinde açıldığında eş zamanlı düzenleme yapılmasına izin verilmez.

- Aynı dağıtım için aynı anda yalnızca bir etkin düzenleme oturumu bulunur.
- Düzenleme oturumu dışında aynı dağıtımı açan sekme veya pencereler **Önizleme Modu (salt okunur)** olarak çalışır.
- Önizleme modunda oturma planları ve dağıtım bilgileri görüntülenebilir; öğrenci taşıma, koltuk değiştirme, dağıtım veya başka veri değişikliği yapılamaz.
- Böylece aynı dağıtım üzerinde farklı sekme/pencerelerden eş zamanlı değişiklik yapılması ve veri çakışması önlenir.
- Düzenleme yetkisinin başka bir sekme/pencereye devredilmesi, mevcut düzenleme oturumunun güvenli biçimde bırakılması ve yeni oturumun etkinleştirilmesiyle yapılır. Teknik uygulamada oturum kilidi ve beklenmeyen kapanma durumunda kilidin güvenli biçimde serbest bırakılması sağlanır.


## 27. Karar 41 – Çok günlük sınav oturumları ve sınav takviminden otomatik oluşturma

Çok günlük sınavlarda her günün oturma planını ayrı bir sınav oturumu olarak oluşturma, mevcut aşamada zorunlu bir iş akışı değildir. Kullanıcı ihtiyaç duyarsa bu yöntemi isteğe bağlı olarak kullanabilir. Bu konu, ilk sürümün temel kapsamını büyütmeden sonraki geliştirmeler için kenarda tutulacaktır.

Gelecek geliştirme hedefi olarak, sınav programı/takvimi sisteme aktarılabildiğinde sistemin takvim verisini okuyarak sınav organizasyonlarını otomatik oluşturabilmesi planlanır. Bu kapsamda takvimdeki tarih, ders, sınıf ve şube bilgileri okunarak ilgili sınav organizasyonları ve oturumları taslak olarak hazırlanabilir. Kullanıcı oluşturulan programı inceleyip gerekli düzeltmeleri yaptıktan sonra onaylayabilir.

- Şimdiki kullanımda kullanıcı çok günlük oturumları isterse ayrı ayrı oluşturabilir; bu zorunlu değildir.
- Sınav takviminden otomatik okuma ve bütün programı otomatik oluşturma, gelecek geliştirme olarak değerlendirilir; mevcut sürümün tamamlanması için ön koşul değildir.
- Takvimden oluşturulan organizasyonların kullanıcı kontrolü ve onayı olmadan kesinleştirilmemesi esastır.
- Takvim aktarımının dosya biçimi ve veri eşleştirme ayrıntıları (ör. Excel sütunları, tarih/ders/sınıf/şube eşleştirmesi) geliştirme aşamasında ayrıca netleştirilecektir.


## 28. Karar 42 – Uzun öğrenci adlarının rapor ve oturma planı kartlarına otomatik sığdırılması

PDF oturma planlarında ve öğrenci kartlarında uzun adların kutu dışına taşması veya kart düzenini bozması engellenir. Öğrenci adları mümkün olduğunca eksiksiz ve okunabilir gösterilir.

- Birden fazla isimden oluşan uzun adlarda, kutuya sığdırmak için gerektiğinde ilk isim kısaltılır. Örneğin **Mehmet Akif Ersoy**, **M. Akif Ersoy** biçiminde gösterilebilir.
- Soyadı kısaltılmaz.
- İsim ve soyadı bu işlemden sonra da kartın alanına sığmıyorsa yazı tipi, okunabilirliği koruyacak ölçüde otomatik küçültülür.
- Otomatik sığdırma, kartın ve oturma planının yerleşimini bozmayacak şekilde uygulanır.
- Bu düzenleme sunum/çıktı amaçlıdır; öğrencinin veritabanındaki kayıtlı adı değiştirilmez.

## 29. Sürüm 1.7 değişiklik kaydı

Karar 42 eklendi: uzun öğrenci adlarının rapor ve oturma planı kartlarına otomatik sığdırılması; gerektiğinde ilk ismin baş harfle kısaltılması, soyadının korunması ve son aşamada yazı tipinin otomatik küçültülmesi. Önceki sürüm 1.6 korunur.


## 30. Karar 43 – Derslik krokisinin kesin olarak tek sayfaya sığdırılması

Kapıya asılacak fiziksel derslik krokisi PDF çıktısı **kesinlikle tek sayfa** olacak şekilde hazırlanır. Krokide ayrıntılı, renkli veya gerçekçi sıra çizimlerine ihtiyaç yoktur; öğrenci yerlerini ve numaralarını anlaşılır biçimde gösteren sade, küçük hücreler kullanılabilir. Tek sayfaya sığdırma, çıktı düzeninin temel ve değiştirilemez gereksinimidir.

- Derslik krokisi hiçbir koşulda birden fazla sayfaya bölünmez.
- Kenar boşlukları, yazıcının/yazdırma alanının izin verdiği en düşük düzeye indirilir; dijital PDF yerleşiminde mümkün olan en geniş kullanılabilir alan değerlendirilir.
- Sıra ve oturma yeri gösterimleri sade, küçük ve işlevsel hücreler biçiminde tasarlanabilir; gereksiz renk, süsleme ve ayrıntılı çizim kullanılmaz.
- Hücre boyutları, sayfa yönü ve desteklenen kâğıt boyutu tek sayfaya uygun olacak şekilde otomatik düzenlenir.
- Öğrenci adlarının sığdırılmasında Karar 42'deki isim kısaltma ve yazı tipi küçültme kuralları uygulanır.
- Tek sayfaya sığdırma sırasında öğrenci bilgileri ve oturma yeri numaraları kaybolmamalı; mümkün olan en iyi okunabilirlik korunmalıdır.
- Bu karar, kapıya asılacak fiziksel derslik krokisi içindir. Diğer rapor türlerinin sayfa düzeni kendi çıktı gereksinimlerine göre belirlenir.

## 31. Sürüm 1.8 değişiklik kaydı

Karar 43 eklendi: Kapıya asılacak derslik krokisi kesinlikle tek sayfaya sığdırılacak; kenar boşlukları en aza indirilecek, sıra gösterimleri sade hücreler olarak tasarlanabilecek ve sayfa/hücre/yazı yerleşimi otomatik ayarlanacaktır. Önceki sürüm 1.7 korunur.


## 32. Karar 44 – Yedek geri yüklemede güvenlik kontrolü ve kullanıcı onayı

Yedekten geri yükleme işlemi, güncel verilerin yanlışlıkla kaybolmasını önleyecek kontrollü bir akışla gerçekleştirilir. Kullanıcı geri yüklemeyi başlatmadan önce seçilen yedeğin tarihi, saati ve içeriğine ilişkin anlaşılır bir özet gösterilir.

- Geri yükleme öncesinde mevcut veritabanının otomatik güvenlik yedeği alınır.
- Seçilen yedeğin dosya bütünlüğü ve uygulama/veri sürümüyle uyumluluğu kontrol edilir.
- Kullanıcıya yedeğin tarih ve saat bilgisi ile geri yüklenecek verilerin kapsamı gösterilir.
- Geri yükleme, kullanıcının açık ve son onayı olmadan başlatılmaz.
- İşlem başarısız olursa mevcut veriler korunur; mümkünse işlem öncesi alınan güvenlik yedeğinden geri dönüş sağlanır.
- Geri yükleme tamamlandığında sonuç kullanıcıya bildirilir.

Bu kontrol, yanlış veya eski bir yedeğin seçilmesi nedeniyle güncel sınav organizasyonlarının, öğrenci verilerinin ya da dağıtım geçmişinin kaybolması riskini azaltır.

## 33. Sürüm 1.9 değişiklik kaydı

Karar 44 eklendi: Yedek geri yükleme öncesinde mevcut veritabanının otomatik güvenlik yedeği alınacak; seçilen yedeğin tarihi, içeriği, bütünlüğü ve uyumluluğu kontrol edilerek kullanıcıya gösterilecek; açık son onay olmadan geri yükleme yapılmayacaktır. Önceki sürüm 1.8 korunur.


## 34. Karar 45 – İlk kurulumda e-Okul kaynaklı öğrenci ve sınıf verilerinin aktarılması

Öğrenci ve sınıf verilerinin temel kaynağı e-Okul'dan alınan resmî listelerdir. İlk kurulum sırasında bu listeler sisteme aktarılır; sınıf, şube ve öğrenci kayıtları bu aktarım üzerinden oluşturulur. Her sınav organizasyonundan önce öğrenci listesinin yeniden hazırlanması veya elle tekrar girilmesi gerekmez.

- İlk kurulumda e-Okul'dan alınan öğrenci listesi sisteme aktarılır.
- Aktarılan bilgilerle sınıf ve şube kayıtları oluşturulur; her sınıf/şubenin öğrenci mevcudu sistem tarafından hesaplanır.
- Öğrenci kayıtlarında okul numarası sabit ve okul genelinde benzersiz kimlik olarak kullanılır. Ad, soyad, sınıf seviyesi, şube ve 11-12. sınıflar için alan bilgisi ilgili e-Okul listelerinden alınır.
- Derslikler ve fiziksel kapasiteleri ilk kurulum aşamasında tanımlanır; bu bilgiler sonraki sınav organizasyonlarında tekrar kullanılabilir.
- Sınav organizasyonu oluşturulurken sistem mevcut öğrenci, sınıf/şube ve derslik kayıtlarını kullanır.
- e-Okul verisinin kendisi esas alınır. Aktarım sırasında yalnızca dosyanın okunabilirliği, beklenen sütunların bulunması ve aktarımın eksiksiz tamamlanması gibi teknik kontroller yapılır; bu kontroller e-Okul verisinin doğruluğunu yeniden sorgulamak anlamına gelmez.
- İleride öğrenci veya sınıf bilgilerinin güncellenmesi gerektiğinde yeni e-Okul listesi üzerinden güncelleme akışı ayrıca kullanılabilir. Geçmişte kesinleşmiş dağıtımların güncellenmiş bilgilerle karşılaştırılması ve kullanıcı onayıyla değişen öğrencilerin havuza alınması Karar 39'a göre yürütülür.

## 35. Sürüm 2.0 değişiklik kaydı

Karar 45 eklendi: İlk kurulumda e-Okul kaynaklı öğrenci ve sınıf listeleri aktarılacak; sınıf/şube kayıtları ve mevcutları otomatik oluşturulacak, derslikler ilk kurulumda tanımlanacak ve sonraki sınav organizasyonlarında mevcut kayıtlar kullanılacaktır. Aktarım kontrolleri yalnızca dosya/format/eksiksiz aktarım gibi teknik doğrulamalarla sınırlıdır. Önceki sürüm 1.9 korunur.


## 36. Karar 46 – Sınıf mevcutlarından başlangıç derslik/oturma kapasitesinin oluşturulması

İlk kurulumda e-Okul'dan aktarılan sınıf/şube mevcutları, başlangıç derslik ve oturma yeri kapasitesini oluşturmak için temel alınır. Sınıf mevcutları çoğunlukla derslik kapasitelerine yakın olduğundan, kullanıcıya her dersliği ve oturma yerini sıfırdan tek tek tanımlatma yerine sistem mevcut sayılara göre başlangıç düzeni oluşturur.

- Her sınıf/şubenin e-Okul listesinden hesaplanan öğrenci mevcudu esas alınarak başlangıç oturma yeri kapasitesi oluşturulur.
- Oluşturulan kapasite ve oturma yeri sayıları kesin/değiştirilemez değildir; kullanıcı fiziksel duruma göre düzenleyebilir.
- Kullanıcı oturma yeri ekleyerek veya çıkararak kapasiteyi **+1 / -1** şeklinde kolayca değiştirebilir.
- Sonradan yapılan kapasite değişiklikleri ilgili derslik/oturma düzeni kaydına işlenir ve sonraki sınav organizasyonlarında kullanılabilir.
- Oturma yeri sayısı değiştirilirken fiziksel sıra düzeni, sıra başına oturma yeri sayısı ve koridor/blok yapısı korunacak şekilde arayüz gerekli düzenlemeyi yapar; kullanıcı gerektiğinde görsel yerleşimi ayrıca düzenleyebilir.
- Bu otomatik oluşturma, fiziksel kapasitenin kesin olarak e-Okul mevcuduna eşit olduğu varsayımı değildir. Başlangıç taslağıdır; son fiziksel uygunluk kullanıcı tarafından kontrol edilip ayarlanır.

## 37. Sürüm 2.1 değişiklik kaydı

Karar 46 eklendi: İlk kurulumda e-Okul'dan alınan sınıf/şube mevcutlarına göre başlangıç derslik ve oturma yeri kapasitesi oluşturulacak; kullanıcı fiziksel duruma göre oturma yerlerini +1 / -1 şeklinde ekleyip çıkararak kolayca düzenleyebilecektir. Önceki sürüm 2.0 korunur.


## 38. Karar 47 – e-Okul listesi aktarımında okul numarası ve ad-soyad eşleştirmesi

Yeni e-Okul listesi aktarılırken öğrenci eşleştirmesi yalnızca okul numarasına göre yapılmaz. Okul numarası ile ad-soyad birlikte kontrol edilir. Bunun nedeni, nakil/ayrılma sonrasında eski öğrencinin okul numarasının başka bir öğrenciye verilmesi ihtimalidir.

- Okul numarası ve ad-soyad eşleşiyorsa kayıt aynı öğrenci olarak değerlendirilir; sınıf, şube ve alan gibi güncel bilgiler yeni listeye göre güncellenebilir.
- Okul numarası aynı, ad-soyad farklıysa bu kayıt aynı öğrenci kabul edilmez. Eski öğrenci kaydı pasif/ayrılmış duruma alınır; yeni öğrenci ayrı bir öğrenci kaydı olarak oluşturulur.
- Eski öğrencinin kesinleşmiş dağıtımlardaki geçmiş kaydı ve kimlik bilgileri korunur. Güncelleme, geçmiş dağıtım kayıtlarını geriye dönük değiştirmez.
- Eski öğrenci güncel dağıtımda bir oturma yerindeyse, değişiklik kullanıcıya bildirilir. Kullanıcı onayıyla eski öğrencinin oturma yeri boşaltılır.
- Yeni öğrenci, aktarım nedeniyle otomatik olarak eski öğrencinin yerine oturtulmaz; bekleyen öğrenci havuzunda bırakılır. Kullanıcı daha sonra uygun bir oturma yerine yerleştirir.
- Aynı okul numarasıyla farklı ad-soyad tespit edildiğinde sistem bunu sessizce birleştirmez veya üzerine yazmaz; değişikliği belirgin biçimde bildirir.
- Ad-soyad karşılaştırması, büyük/küçük harf ve baştaki/sondaki fazladan boşluk gibi biçim farklarını normalize ederek yapabilir; ancak farklı kişileri aynı kişi sayacak aşırı esnek benzerlik eşleştirmesi uygulamaz. Emin olunamayan kayıtlar kullanıcı kontrolüne sunulur.

## 39. Sürüm 2.2 değişiklik kaydı

Karar 47 eklendi: e-Okul listesi güncellenirken okul numarası ve ad-soyad birlikte karşılaştırılacaktır. Aynı okul numarası farklı bir öğrenciye geçmişse eski öğrenci pasife alınacak, geçmiş dağıtım bilgileri korunacak, eski öğrencinin mevcut oturma yeri kullanıcı onayıyla boşaltılacak ve yeni öğrenci otomatik olarak bu yere yerleştirilmeyip bekleyen öğrenci havuzunda tutulacaktır. Önceki sürüm 2.1 korunur.


## 40. Karar 48 – Yeni e-Okul listesinde bulunmayan öğrencilerin onaylı biçimde dağıtımdan ve oturma planından çıkarılması

Yeni e-Okul listesi mevcut öğrenci kayıtlarıyla karşılaştırıldığında, önceki listede bulunup yeni listede bulunmayan öğrenciler kullanıcıya ayrı bir kontrol/inceleme listesinde gösterilir. Kullanıcı bu listeyi gördükten ve işlemi onayladıktan sonra ilgili öğrenciler güncel öğrenci havuzundan ve aktif dağıtım organizasyonundan çıkarılır; oturma planında bu öğrencilere ayrılmış koltuklar da aynı işlem kapsamında boşaltılır. İki işlem birlikte yürütülür; yalnızca öğrenciyi listeden çıkarmak veya yalnızca koltuğunu boşaltmak yeterli değildir.

- Yeni listede bulunmayan öğrenciler aktarım sırasında doğrudan ve sessizce silinmez; önce kullanıcıya kimlik bilgileri ve varsa mevcut derslik/oturma yeriyle birlikte gösterilir.
- Kullanıcı onayından sonra öğrenci aktif öğrenci havuzundan/dağıtım katılımcılarından çıkarılır ve oturma planındaki yeri boşaltılır.
- Öğrenci kaydı fiziksel olarak/veritabanından silinmez; pasif veya ayrılmış duruma alınır. Böylece geçmiş sınav kayıtları, eski oturma planları ve değişiklik geçmişi korunur.
- İşlem yalnızca güncel/aktif dağıtımı etkiler. Daha önce kesinleştirilmiş geçmiş dağıtımlar, oluşturuldukları zamanki öğrenci ve oturma bilgileriyle aynen saklanır.
- Bir öğrenci yeni listede bulunmadığı halde nakil, geçici liste farkı veya aktarım hatası gibi nedenlerle durum belirsizse kullanıcı onayı olmadan çıkarma yapılmaz; kayıt incelemede bırakılabilir.
- İşlem geçmişine hangi öğrencilerin çıkarıldığı, hangi oturma yerlerinin boşaltıldığı, tarih/saat ve kullanıcı onayı kaydedilir; geri alma/revizyon mekanizmasıyla önceki aktif durum geri getirilebilir.

## 41. Sürüm 2.3 değişiklik kaydı

Karar 48 eklendi: Yeni e-Okul listesinde bulunmayan öğrenciler önce kullanıcıya mevcut yerleşimleriyle birlikte gösterilecek; kullanıcı onayladıktan sonra öğrenciler güncel öğrenci havuzundan/aktif dağıtımdan çıkarılacak ve oturma planındaki yerleri aynı işlemde boşaltılacaktır. Öğrenci kayıtları silinmeyecek, pasif/ayrılmış olarak saklanacak; geçmiş kesinleşmiş dağıtımlar değiştirilmeyecektir. Önceki sürüm 2.2 korunur.

## 42. Karar 49 – Raporların yalnızca son düzenleme tamamlandıktan sonra oluşturulması

Öğrenci listesi güncellemesi veya dağıtım üzerinde yapılan manuel müdahaleler sonrasında sistem raporları her işlemde otomatik olarak yeniden oluşturmaz. Kullanıcı, dağıtımın son hâlini hazırlayıp kontrol ettikten sonra rapor üretimini başlatır. Böylece raporlar ara düzenlemeleri değil, kullanıcının onayladığı nihai oturma planını yansıtır.

- Öğrenci ekleme/çıkarma, öğrenciyi bekleyen havuza alma, boşalan yere başka öğrenci yerleştirme, öğrencilerin yerlerini değiştirme ve derslikler arasında taşıma işlemleri çalışma süresince yapılabilir.
- Bu işlemlerin tamamı tarih/saat ve işlem ayrıntılarıyla değişiklik geçmişine kaydedilir; geri alma/ileri alma mekanizması geçerliliğini korur.
- Düzenleme devam ederken PDF/Excel raporları otomatik olarak üretilmez veya her değişiklikte yeniden oluşturulmaz. Ekrandaki oturma planı güncel çalışma durumunu göstermeye devam eder.
- Kullanıcı dağıtımı tamamladığında “Raporları Oluştur” işlemini başlatır.
- Rapor üretiminden önce sistem “Dağıtım düzenlemeleri tamamlandı mı? Raporları oluşturmaya hazır mısınız?” şeklinde açık bir onay ister.
- Kullanıcı onay verirse raporlar o andaki güncel ve son oturma planı, öğrenci listesi ve dağıtım bilgileri esas alınarak oluşturulur.
- Kullanıcı henüz hazır değilse rapor üretimi yapılmaz; düzenlemeye devam edebilir.
- Rapor oluşturulduktan sonra dağıtımda yeni bir değişiklik yapılırsa mevcut raporların eski sürüme ait olduğu belirtilir; nihai raporlar kullanıcı yeniden rapor oluşturduğunda güncellenir.

## 43. Sürüm 2.4 değişiklik kaydı

Karar 49 eklendi: Dağıtım üzerinde öğrenci/oturma yeri düzenlemeleri sürerken raporlar otomatik oluşturulmayacak veya her değişiklikte yenilenmeyecektir. Kullanıcı düzenlemeleri tamamladığında sistem raporları oluşturmaya hazır olup olmadığını soracak; onay verilirse PDF/Excel raporları son oturma planına göre üretilecektir. Değişiklik geçmişi ile geri alma/ileri alma mekanizması korunacaktır. Önceki sürüm 2.3 korunur.

## 44. Karar 50 – Komşuluk kuralı ihlallerinde uyarı, kullanıcı onayı ve rapor üretimi

Dağıtımın son kontrolünde seçilmiş komşuluk kurallarına aykırı yerleşimler bulunursa sistem bu durumu mutlaka kullanıcıya bildirir. Komşuluk kuralı ihlali tek başına rapor üretimini otomatik olarak ve kesin biçimde engellemez; ancak daha sonra alınan Karar 54 ile belirlenen kesin üst sınır geçerlidir. Kullanıcı yalnızca ihlalden etkilenen benzersiz öğrenci sayısı en fazla 5 ise uyarıları değerlendirerek dağıtımı kabul edebilir. Beşten fazla öğrenci etkileniyorsa dağıtım kesinleştirilemez ve rapor üretimi onaylanamaz.

- Rapor üretimi öncesinde sistem seçilmiş komşuluk kurallarını yeniden kontrol eder.
- İhlal varsa genel bir uyarıyla yetinmez; ihlal edilen kuralı ve mümkün olduğu ölçüde ilgili öğrencileri, dersliği ve oturma yerlerini açıkça gösterir.
- Kullanıcıya ihlaller giderilmeden devam etmek isteyip istemediği sorulur.
- Kullanıcı kabul etmezse rapor üretimi başlatılmaz; oturma planını düzenlemeye geri dönebilir.
- Kullanıcı, Karar 54 sınırı içinde kalan ihlalleri açıkça onaylarsa raporlar mevcut son oturma planına göre oluşturulur. Beşten fazla benzersiz öğrenci etkileniyorsa kullanıcı onayı bu sınırı aşamaz.
- Onaylanan ihlaller rapor öncesi kontrol sonucunda ve dağıtımın işlem geçmişinde kayıt altına alınır. Böylece daha sonra hangi kural ihlalinin bilinçli olarak kabul edildiği görülebilir.
- Bu karar komşuluk kurallarına ilişkindir. Öğrenci sayısının kullanılabilir kapasiteyi aşması gibi fiziksel kapasite güvenliği kontrolleri, ayrı ve daha önce belirlenmiş kapasite kurallarına göre değerlendirilir; komşuluk ihlalini kabul etme seçeneği kapasite aşımına izin vermez.

## 45. Sürüm 2.5 değişiklik kaydı

Karar 50 eklendi: Son kontrolde komşuluk kuralı ihlali varsa sistem ihlalleri ve ilgili öğrencileri açıkça gösterecek ve kullanıcıyı mutlaka uyaracaktır. Kullanıcı ihlalleri kabul ederek devam ederse raporlar oluşturulabilecek; kabul etmezse düzenlemeye dönülecektir. Onaylanan ihlaller işlem geçmişinde kaydedilecek; bu onay kapasite aşımı gibi ayrı güvenlik kontrollerini geçersiz kılmayacaktır. Önceki sürüm 2.4 korunur.


## 46. Karar 51 – Seçilen dersliklerin tamamına dengeli dağıtım yapılması

Kullanıcı bir sınav organizasyonu için kullanılacak derslikleri seçtiğinde, sistem seçilmiş derslikleri dağıtımın tamamında değerlendirmelidir. Öğrencileri ilk dersliklere doldurup seçilmiş diğer derslikleri boş bırakmak veya kapasite fazlasını birkaç derslikte yığmak kabul edilmez. Amaç, seçilen dersliklerin tamamını kullanarak öğrencileri dersliklere mümkün olduğunca dengeli dağıtmak ve boş kapasiteyi de dengeli yaymaktır.

- Okul genelindeki tüm öğrenci ve sınıfları kapsayan bir dağıtımda, öğrenci sayısı ve fiziksel koşullar elverdiği sürece hiçbir uygun derslik boş bırakılmaz.
- Kullanıcı okulun tüm dersliklerini değil, örneğin 15 derslikten yalnızca 10 tanesini seçmişse dağıtım yalnızca bu 10 derslik üzerinden yapılır; seçilmeyen 5 derslik kullanılmaz.
- Seçilmiş dersliklerin tamamına öğrenci yerleştirilmesi hedeflenir. Örneğin 10 dersliğe dağıtılacak 100 öğrenci varsa, kapasite ve diğer dağıtım kısıtları elverdiği ölçüde yaklaşık 10'ar öğrenciyle dengeli kullanım amaçlanır.
- Derslik kapasiteleri farklıysa dengeleme yalnızca eşit öğrenci sayısına göre yapılmaz; kapasite oranları, kullanılabilir oturma yerleri, sınıf/şube/alan dağılımı ve etkin komşuluk kuralları birlikte dikkate alınır.
- Boş oturma yerleri seçilmiş dersliklere mümkün olduğunca dengeli yayılır; öğrenciler sırayla birkaç dersliği doldurup diğerlerini boş bırakacak biçimde yerleştirilmez.
- Seçilmiş derslik sayısı öğrenci sayısından fazla olduğunda veya fiziksel/dağıtım kısıtları bütün derslikleri kullanmayı imkânsız kıldığında sistem bunu açıkça belirtir; gerçekleşmeyen hedefi sağlanmış gibi göstermez.
- Bu karar, kullanıcının derslik seçme yetkisini ortadan kaldırmaz. Sistem yalnızca kullanıcının seçtiği derslikler arasında dengeleme yapar.

## 47. Sürüm 2.6 değişiklik kaydı

Karar 51 eklendi: Kullanıcının seçtiği dersliklerin tamamı, öğrenci sayısı ve fiziksel/dağıtım kısıtları elverdiği sürece kullanılacak; öğrenciler ve boş kapasite bu dersliklere mümkün olduğunca dengeli dağıtılacaktır. Tüm okulun kapsandığı dağıtımlarda uygun dersliklerin boş kalmaması hedeflenir. Kullanıcının seçmediği derslikler kullanılmaz. Önceki sürüm 2.5 korunur.

## 48. Karar 52 – Çok aşamalı akıllı dağıtım ve optimizasyon motoru

Kelebek Sınav Sistemi'nin dağıtım bileşeni, tek seferlik basit bir karıştırma veya yerleştirme işlemi olmayacaktır. Ayrı bir Akıllı Dağıtım ve Optimizasyon Motoru olarak tasarlanacak; seçilmiş dersliklere katılacak bütün öğrenciler için kapasite elverdiği sürece eksiksiz bir yerleşim üretmek amacıyla birden fazla algoritma, arama stratejisi ve iyileştirme aşaması uygulayacaktır. Motorun hedefi yalnızca ilk geçerli sonucu bulmak değil, süre ve kaynak sınırları içinde mümkün olan en dengeli ve en az ihlalli sonucu bulmaktır.

### 48.1. Dağıtımın temel garantileri ve sınırları

- Kullanılabilir toplam oturma yeri sayısı öğrenci sayısına eşit veya daha fazlaysa, her öğrenciye tam olarak bir oturma yeri atanması temel hedeftir. Hiçbir öğrenci sessizce atlanamaz veya iki kez yerleştirilemez.
- Fiziksel kapasite, kapalı/kullanım dışı koltuklar ve seçilmiş derslikler kesin kısıtlardır. Sistem kapasiteyi aşan veya fiziksel olarak mevcut olmayan koltukları varmış gibi gösteremez.
- Altı komşuluk kuralı, motorun önce tamamını sağlamaya çalışacağı optimizasyon hedefleridir. Kullanıcının daha önce verdiği karar doğrultusunda, bu kuralların ihlali açıkça raporlanır ve kullanıcı onayıyla kabul edilebilir. Dolayısıyla motor, komşuluk kurallarının tümünü aynı anda sağlayamadığı için öğrenci yerleştirmeyi bırakmaz; ihlalleri en aza indiren yerleşimi arar.
- Seçilmiş dersliklerin tamamının kullanılması, öğrenci sayısı ve koltukların dağılımı buna elverdiğinde hedeflenir. Öğrenci sayısı seçilmiş derslik sayısından azsa veya fiziksel/diğer kesin kısıtlar tüm dersliklerin kullanılmasını imkânsız kılıyorsa bu matematiksel sınır kullanıcıya açıklanır; sistem gerçekleşmeyen bir hedefi sağlanmış gibi sunmaz.
- Kullanılabilir toplam kapasite öğrenci sayısından azsa, bütün öğrencileri fiziksel olarak yerleştirmek mümkün değildir. Sistem bu durumda kapasite açığı miktarını ve gerekli ek oturma yeri/derslik sayısını bildirir; kapasite aşımı yaparak sahte bir başarı üretmez.

### 48.2. Çok aşamalı çözüm stratejisi

Motor, probleme göre aşağıdaki yöntemleri tek tek veya birlikte kullanabilecek şekilde modüler tasarlanacaktır:

1. **Başlangıç yerleşimi:** Hızlı sezgisel yöntemlerle tüm öğrencileri uygun koltuklara yerleştiren ilk çözüm oluşturulur.
2. **Dengeli dağıtım:** Sınıf seviyesi, şube, alan, öğrenci sayısı, derslik kapasitesi ve boş koltuk dengesi optimize edilir.
3. **Kısıt optimizasyonu:** Yan yana, önlü-arkalı ve çapraz komşuluk ilişkileri fiziksel konum ve koridor sınırları dikkate alınarak değerlendirilir.
4. **Alternatif çözüm üretimi:** Öğrenci sıraları, derslikler ve yerleştirme stratejileri değiştirilerek farklı aday dağıtımlar oluşturulur.
5. **Yerel iyileştirme ve yeniden arama:** Öğrenci takası, koltuk değişimi, grup değişimi ve uygun arama/optimizasyon yöntemleriyle ihlal sayısı azaltılır ve denge artırılır.
6. **Sonuç sıralama:** Bulunan çözümler; bütün öğrencilerin yerleştirilmesi, kapasiteye uyum, seçilmiş dersliklerin kullanımı, şube/seviye/alan dengesi, boş koltukların dağılımı ve komşuluk ihlallerinin sayısı/önemi ölçütleriyle karşılaştırılır.
7. **En iyi adayın sunulması:** Kullanıcıya bulunan en iyi aday ve varsa diğer alternatifler sunulur. Kullanıcı karşılaştırma ve onay akışını kullanır.

Tek bir algoritmaya bağlı kalınmayacak; farklı problem büyüklükleri ve kısıt yoğunlukları için uygun yöntemler seçilebilecek, gerektiğinde birden fazla yöntem ardışık veya hibrit biçimde çalıştırılabilecektir. Teknik uygulamada kısıt programlama/tamsayılı optimizasyon, sezgisel yöntemler ve yerel arama gibi yaklaşımlar değerlendirilecektir.

### 48.3. İşlem süresi, ilerleme ve tahmini kalan süre

- Dağıtım işlemi sırasında ayrı bir ilerleme ekranı gösterilir.
- Ekranda mevcut aşama, geçen süre, denenmiş/üretilmiş aday sayısı, bulunan en iyi çözümün kalitesi ve tahmini kalan süre gösterilir.
- Tahmini kalan süre kesin bir vaat olarak değil, o ana kadarki işlem hızına ve arama davranışına göre sürekli güncellenen yaklaşık bir tahmin olarak sunulur. İlk aşamada yeterli veri yoksa sistem yanıltıcı bir kesin süre vermek yerine tahminin henüz oluşmadığını veya geniş bir aralık olduğunu belirtir.
- Kullanıcı, arama sürerken bulunan en iyi geçerli adayı inceleyebilir; aramayı durdurmayı seçerse o ana kadar bulunan en iyi aday kaybedilmeden sunulur.
- Arama durdurulduğunda bunun tüm olası çözümlerin denendiği anlamına gelmediği açıkça belirtilir.

### 48.4. Sonuç ve kullanıcı onayı

- Motor, kapasite elverdiği hâlde öğrenci bırakılmış bir sonucu başarılı dağıtım olarak sunamaz.
- Komşuluk kurallarında kalan ihlaller tek tek gösterilir; ilgili öğrenciler, derslikler ve oturma yerleri mümkün olduğunca belirtilir. Kullanıcı bu ihlalleri kabul edebilir veya düzenlemeye dönebilir.
- Kapasite yetersizliği gibi kesin fiziksel engeller komşuluk ihlaliyle aynı kategoride değerlendirilmez ve kullanıcı onayıyla yok sayılmaz.
- Dağıtımın kesinleştirilmesi, önceki kararlarda tanımlanan alternatif karşılaştırma, son kontrol, kullanıcı onayı ve rapor oluşturma adımlarına bağlı kalır.

## 49. Sürüm 2.7 değişiklik kaydı

Karar 52 eklendi: Dağıtım tek aşamalı basit bir işlem olmayacak; farklı algoritma ve optimizasyon stratejilerini kullanan modüler bir motorla yürütülecektir. Kapasite elverdiğinde hiçbir öğrenci yerleşim dışında bırakılmayacak; komşuluk kuralları önce sağlanmaya çalışılacak, sağlanamayanlar en aza indirilerek kullanıcıya açıkça bildirilecek ve kullanıcı onayıyla kabul edilebilecektir. İşlem sırasında aşama, geçen süre, aday sayısı, en iyi çözüm ve yaklaşık kalan süre gösterilecek; kullanıcı aramayı durdurursa o ana kadarki en iyi aday korunacaktır. Fiziksel kapasite yetersizliği veya tüm seçilmiş derslikleri kullanmanın matematiksel olarak mümkün olmaması gizlenmeyecek ve imkânsız bir sonuç vaat edilmeyecektir. Önceki sürüm 2.6 korunur.

## 50. Karar 53 – Komşuluk ihlallerini en aza indirme ve beş öğrenci hedefi

Akıllı Dağıtım ve Optimizasyon Motorunun birincil hedefi, bütün öğrencileri seçilmiş dersliklerdeki kullanılabilir koltuklara yerleştirirken seçilmiş altı komşuluk kuralının tamamını ihlal etmeyen bir çözüm bulmaktır. Sıfır ihlalli çözüm bulunamazsa motor farklı algoritma ve yerleşim varyasyonlarını deneyerek ihlallerin sayısını mümkün olan en düşük düzeye indirecektir.

- Öncelikli hedef sıfır komşuluk ihlalidir.
- Sıfır ihlal mümkün değilse motor, komşuluk kuralı ihlali bulunan konumda oturmak zorunda kalan öğrenci sayısını en aza indirmeye çalışır.
- Optimizasyon hedefi, ihlalden etkilenen öğrenci sayısını en fazla **5 öğrenci** düzeyinde tutmaktır.
- İhlal sayısı değerlendirilirken aynı öğrencinin birden fazla komşuluk ihlali bulunması ayrıca ayrıntılandırılır; hem etkilenen öğrenci sayısı hem de ihlal ilişkilerinin toplamı raporda birbirinden ayrı gösterilir. Böylece beş öğrenci hedefi, ihlal ilişkilerinin sayısıyla karıştırılmaz.
- Motor beş veya daha az öğrencinin ihlalden etkilendiği bir çözüm bulursa bu çözümü öncelikli aday olarak sunar. Daha az öğrencinin etkilendiği çözüm, diğer denge ölçütleri de dikkate alınarak daha yüksek öncelik alır.
- Beş öğrenci veya daha az etkilenen bir çözüm henüz bulunamazsa motor aramayı sürdürür ve bulduğu en iyi adayı yalnızca geçici/inceleme adayı olarak gösterebilir. Daha sonra alınan Karar 54 uyarınca beşten fazla benzersiz öğrencinin etkilendiği aday kesinleştirilemez; kullanıcı bu sınırı kabul ederek aşamaz. Kullanıcıya gerçek ihlal sayısı ve sınırın karşılanmadığı açıkça gösterilir.
- Sonuç raporunda ihlalden etkilenen her öğrenci ayrı ayrı listelenir: ad-soyad, sınıf/şube, derslik, oturma yeri, ihlal edilen kural ve komşuluk ilişkisi kurduğu diğer öğrenci/öğrenciler gösterilir.
- Kullanıcı ihlalleri kabul ederek devam ederse bu onay ve kabul edilen ihlal listesi dağıtımın işlem geçmişine kaydedilir.
- Bu hedef yalnızca komşuluk kuralı ihlalleri içindir. Kullanılabilir fiziksel kapasiteyi aşmaya veya bir öğrenciyi yerleştirmeden bırakmaya izin vermez.

## 51. Sürüm 2.8 değişiklik kaydı

Karar 53 eklendi: Akıllı dağıtım motorunun birincil hedefi sıfır komşuluk ihlalidir. Sıfır ihlal bulunamazsa ihlalden etkilenen öğrenci sayısı en aza indirilecek ve hedef en fazla 5 öğrenci olacaktır. Beş veya daha az öğrencinin etkilendiği çözüm bulunamazsa sistem aramayı sürdürüp bulunan en iyi sonucu ve gerçek ihlal sayısını açıkça gösterecek; ihlalden etkilenen öğrencileri, oturma yerlerini ve ihlal ilişkilerini tek tek raporlayacaktır. Kullanıcı ihlalleri kabul edebilir veya düzenlemeye dönebilir. Kapasite ve bütün öğrencilerin yerleştirilmesi temel zorunlulukları değişmez. Önceki sürüm 2.7 korunur.

## 52. Karar 54 – Komşuluk ihlallerinde kesin üst sınır

Karar 53'te belirtilen beş öğrenci hedefi, bu kararla kesin üst sınıra dönüştürülmüştür. Motorun birincil hedefi yine sıfır komşuluk ihlalidir.

- Öncelik sırası: sıfır ihlal; sıfır mümkün değilse ihlalden etkilenen öğrenci sayısını en aza indirmek.
- İhlalden etkilenen öğrenci sayısı **5'i geçemez**. Beş öğrenci dahi istenmeyen, yalnızca sıfır ihlal bulunamadığında izin verilen son üst sınırdır.
- Motor beş veya daha az öğrencinin etkilendiği bir çözüm bulana kadar farklı algoritma ve yerleşim varyasyonlarını denemeye devam eder.
- Beşten fazla öğrencinin ihlalden etkilendiği aday, fiziksel yerleşim önerisi olarak incelenebilir; ancak başarılı/uygun dağıtım olarak sunulamaz ve kesinleştirilemez.
- Arama devam ederken bulunan en iyi aday ve gerçek ihlal sayısı kullanıcıya gösterilir. Arama sürerken veya durdurulduğunda beş sınırının karşılanmadığı açıkça belirtilir.
- Kullanıcıya hiçbir koşulda beşten fazla ihlalli bir dağıtım, beş sınırı sağlanmış gibi onaylatılmaz.
- Beş veya daha az öğrencinin etkilendiği bir çözüm bulunduğunda, ihlaller öğrenci ve oturma yeri bazında listelenir; kullanıcı önceki kararlarda tanımlandığı şekilde uyarıları inceleyip onay verebilir veya düzenlemeye dönebilir.
- Bütün öğrencilerin fiziksel olarak yerleştirilmesi ile dağıtımın kabul edilip kesinleştirilmesi ayrı aşamalardır. Kapasite yeterliyse motor öğrencileri yerleştirmeye devam eder; ancak ihlal üst sınırı sağlanmadan dağıtım kesinleştirilemez.

## 53. Sürüm 2.9 değişiklik kaydı

Karar 54 eklendi ve Karar 53'teki beş öğrenci hedefi kesin üst sınır olarak güncellendi. Sıfır ihlal birincil hedeftir; sıfır mümkün değilse en fazla beş öğrencinin ihlalden etkilenmesine izin verilir. Beşten fazla öğrencinin etkilendiği aday başarılı veya kesinleştirilebilir dağıtım sayılmaz. Motor aramayı sürdürür, bulunan en iyi adayı ve gerçek ihlal sayısını açıkça gösterir. Önceki sürüm 2.8 korunur.


## 54. Karar 55 – İhlalden etkilenen öğrenci listesi ve görsel inceleme

Komşuluk ihlallerinin değerlendirilmesinde temel ölçüt, ihlal ilişkisinin toplam sayısı değil, **ihlalden etkilenen benzersiz öğrenci sayısıdır**. Beş öğrenci üst sınırı bu sayıya göre hesaplanır. Aynı öğrenci birden fazla komşuluk kuralını ihlal etse veya birden fazla öğrenciyle ihlal ilişkisi içinde olsa da etkilenen öğrenci sayısında bir kez sayılır.

- Dağıtım değerlendirme ekranında komşuluk ihlali bulunan öğrenciler ayrı bir listede gösterilir.
- Her öğrenci listede tek kayıt olarak yer alır; ad-soyad, sınıf/şube, derslik ve oturma yeri bilgileri gösterilir.
- Kullanıcı listedeki bir öğrenciye tıkladığında ilgili dersliğin oturma planı/krokisi açılır.
- Krokide ilgili öğrencinin oturduğu yer ve ihlale neden olan komşu oturma yeri/yerleri görsel olarak belirginleştirilir. Böylece kullanıcı ihlalin nerede ve hangi öğrenci(ler) arasında oluştuğunu doğrudan görebilir.
- Aynı öğrencinin birden fazla ihlali varsa hepsi o öğrencinin ayrıntısında ayrı ayrı açıklanır; ancak öğrenci sayısı hesabında tekrar sayılmaz.
- İhlal ilişkilerinin ayrıntılı dökümü teknik inceleme ve açıklama amacıyla tutulabilir; fakat beş kişilik kesin üst sınırın hesabında ihlal ilişkisi adedi değil, etkilenen benzersiz öğrenci sayısı esas alınır.
- Kullanıcı görsel incelemeden sonra dağıtımı düzenlemeye dönebilir veya daha önce kararlaştırılan uyarı ve onay süreciyle ihlalleri kabul edebilir.

## 55. Sürüm 3.0 değişiklik kaydı

Karar 55 eklendi: Beş öğrenci sınırı, komşuluk ihlallerinden etkilenen benzersiz öğrenci sayısına göre hesaplanır; ihlal ilişkilerinin toplam sayısı temel ölçüt değildir. İhlal bulunan öğrenciler ayrı listelenir. Kullanıcı bir öğrenciyi seçtiğinde ilgili derslik krokisi açılır ve öğrencinin yeri ile ihlale neden olan komşu yerler görsel olarak vurgulanır. Aynı öğrencinin birden fazla ihlali varsa ayrıntıları gösterilir ancak öğrenci sayısında bir kez sayılır. Önceki sürüm 2.9 korunur.

## 56. Karar 56 – Derslik dengesi ve komşuluk kurallarının eş zamanlı optimizasyonu

Kullanıcı C seçeneğini onaylamıştır: Akıllı dağıtım motoru, öğrencileri dersliklere dengeli dağıtma hedefi ile komşuluk kurallarını sağlama hedefini birbirinden kopuk iki ardışık işlem olarak ele almayacak; ikisini aynı optimizasyon sürecinde birlikte değerlendirecektir.

- Motor, her aday yerleşimde derslikler arasındaki öğrenci sayısı ve sınıf/şube/seviye/alan dağılımı dengesini değerlendirirken aynı anda yan yana, önlü-arkalı ve çapraz komşuluk kısıtlarını da dikkate alır.
- Öğrencilerin yalnızca birkaç dersliğe yığılması veya komşuluk kurallarını sağlamak uğruna seçilmiş dersliklerin gereksiz biçimde boş bırakılması hedeflenen çözüm değildir.
- Seçilmiş dersliklerin tamamının kullanılması ve öğrenci/boş koltuk dağılımının mümkün olduğunca dengeli olması optimizasyon hedefidir. Derslik kapasiteleri farklıysa denge, kapasite oranları ve kullanılabilir oturma yerleri dikkate alınarak hesaplanır.
- Önceden kesinleştirilen temel koşullar korunur: bütün öğrenciler yerleştirilir ve fiziksel kapasite aşılmaz. Komşuluk ihlallerinde sıfır ihlal önceliklidir; sıfır mümkün değilse etkilenen benzersiz öğrenci sayısı en aza indirilir ve beş kişilik kesin üst sınır uygulanır.
- Motor, derslik dengesi ile komşuluk kuralları arasındaki ödünleşimleri aynı çözüm aramasında değerlendirir; tek bir ölçütü erken sabitleyip diğer ölçütü sonradan düzeltmeye çalışmaz.
- Alternatif dağıtımlar, hem derslikler arası denge hem de ihlalden etkilenen öğrenci sayısı ve diğer önceden belirlenmiş ölçütler birlikte dikkate alınarak karşılaştırılır.

## 57. Sürüm 3.1 değişiklik kaydı

Karar 56 eklendi: Derslikler arasındaki öğrenci dağılım dengesi ile komşuluk kurallarının sağlanması aynı optimizasyon sürecinde eş zamanlı değerlendirilecektir. Motor, iki hedefi birbirinden kopuk ardışık aşamalar olarak çözmeyecek; seçilmiş dersliklerin kullanımı, kapasite oranları, öğrenci gruplarının dengesi ve komşuluk kısıtlarını birlikte değerlendirecektir. Bütün öğrencilerin yerleştirilmesi, fiziksel kapasitenin aşılmaması, sıfır ihlal önceliği ve en fazla beş benzersiz öğrencinin ihlalden etkilenmesi yönündeki önceki kararlar geçerliliğini korur. Önceki sürüm 3.0 korunur.

## 58. Karar 57 – Derslik kapasitesine göre oransal öğrenci dağıtımı

Kullanıcı, farklı kapasitedeki seçilmiş dersliklere öğrenci dağıtımının sabit öğrenci sayıları belirlenerek değil, dersliklerin gerçek kullanılabilir kapasitelerine göre oransal yapılmasını onaylamıştır.

- Her seçilmiş dersliğin kullanılabilir kapasitesi esas alınır. Kullanım dışı bırakılmış oturma yerleri kapasite hesabına katılmaz.
- Öğrencilerin dersliklere dağılım hedefi, her dersliğin kullanılabilir kapasitesinin seçilmiş dersliklerin toplam kullanılabilir kapasitesine oranına göre hesaplanır.
- Örneğin 36, 30 ve 24 kullanılabilir koltuğu olan üç derslikte dağıtım oranı 36:30:24 olur; sistem baştan sabit öğrenci sayıları tanımlamaz.
- Gerçek öğrenci sayıları tam sayılı olmak zorunda olduğundan, oranların tam sayıya dönüştürülmesi ve kalan öğrencilerin yerleştirilmesi optimizasyon motorunca yapılır. Bu işlem kapasiteyi aşmadan ve mümkün olduğunca dengeli sonuç verecek şekilde gerçekleştirilir.
- Seçilmiş dersliklerin tamamı kullanılmaya çalışılır; öğrenciler birkaç büyük dersliğe yığılmaz ve diğer seçilmiş derslikler gereksiz yere boş bırakılmaz.
- Kapasite oranına göre öğrenci sayısı dağıtımı, sınıf/şube/seviye/alan gruplarının oransal dağılımı ve komşuluk kurallarıyla birlikte aynı optimizasyon sürecinde değerlendirilir.
- Dağıtımda sabit “her dersliğe şu kadar öğrenci” hedefi kullanılmaz; gerçek kapasite ve mevcut öğrenci gruplarının sayıları esas alınır.

## 59. Sürüm 3.2 değişiklik kaydı

Karar 57 eklendi: Farklı kapasitedeki seçilmiş dersliklere öğrenci dağıtımı sabit öğrenci sayılarıyla değil, kullanılabilir kapasite oranlarıyla yapılacaktır. Örneğin 36, 30 ve 24 kişilik derslikler 36:30:24 oranında değerlendirilir. Tam sayıya dönüştürme, kalan öğrencilerin yerleştirilmesi, sınıf/şube/alan dengesi ve komşuluk kuralları optimizasyon motorunca birlikte ele alınır. Önceki sürüm 3.1 korunur.

## 60. Karar 60 – 11 ve 12. sınıflarda önce sınıf geneli alan ataması, gerektiğinde öğrenci bazında düzeltme

İlk e-Okul öğrenci listesi aktarımında 11 ve 12. sınıfların alan bilgisi ayrıca tanımlanacaktır. Kullanıcı, ilk kurulumun kolay ve hızlı tamamlanabilmesi için her 11. veya 12. sınıf/şube listesine önce toplu olarak tek bir alan atayacaktır.

- Alan seçenekleri: Sayısal, Eşit Ağırlık, Sözel ve Dil.
- Örneğin 11/A sınıfı ilk aşamada topluca Sayısal olarak işaretlenebilir. Bu seçim, listedeki bütün öğrencilere başlangıç alan bilgisi olarak uygulanır.
- Toplu alan atamasından sonra kullanıcı gerekli görürse tek tek öğrencilerin alan bilgisini değiştirebilir. Öğrenci bazındaki düzeltme, sınıfın varsayılan/toplu alan bilgisinden bağımsız olarak o öğrencinin kaydına işlenir.
- Bu esneklik, aynı şube içinde farklı alan veya seçmeli ders gruplarına ayrılan öğrencilerin bulunabileceği okul yapılarında da kullanılabilir. Bu tür karma kullanım şu an öncelikli senaryo olmasa da veri modeli ve arayüz buna engel olmayacaktır.
- 9 ve 10. sınıflarda alan bilgisi bulunmaz ve alan seçimi yapılmaz.
- Alan bilgisi, öğrenci kaydında tutulur; komşuluk kuralları ve dağıtım analizleri öğrencinin kendi kayıtlı alanını esas alır.
- İlk kurulumda 11 ve 12. sınıfların her biri için toplu alan seçimi tamamlanır; ardından ihtiyaç duyulan öğrenci bazlı istisnalar düzenlenebilir.

## 61. Sürüm 3.3 değişiklik kaydı

Karar 60 eklendi: İlk e-Okul aktarımı sırasında 11 ve 12. sınıflarda alan bilgisi, öncelikle sınıf/şube bazında toplu olarak atanacaktır. Kullanıcı örneğin 11/A listesinin tamamını tek işlemle Sayısal, Eşit Ağırlık, Sözel veya Dil olarak belirleyebilir. Daha sonra ihtiyaç halinde tek tek öğrencilerin alan bilgisi değiştirilebilir; öğrenci bazındaki değer toplu varsayılanın üzerine yazılır. Böylece aynı şubede farklı alan/seçmeli ders gruplarında bulunan öğrenciler de desteklenir. 9 ve 10. sınıflarda alan bilgisi kullanılmaz. Önceki sürüm 3.2 korunur.

## 62. Karar 62 – Dağıtım öncesi özet ekranı

Dağıtım başlamadan önce sistem, sınav organizasyonunun kapsamını tek ekranda özetleyecektir. Bu ekran zorunlu bir onay kapısı değil, kullanıcının isteğe bağlı olarak inceleyebileceği bir kontrol ekranıdır.

- Sınav adı ve tarihi, seçilmiş ders veya dersler, seçilmiş sınıf/şube/öğrenci grupları, toplam öğrenci sayısı, kullanılacak derslikler ve kullanılabilir kapasiteleri gösterilir.
- Aktif komşuluk kuralları ve varsa eksik/bekleyen öğrenci bilgileri de özette yer alır.
- Kullanıcı isterse özeti inceleyip seçimlerini değiştirmek için önceki adıma dönebilir.
- Özeti incelemek veya ayrıca onaylamak zorunlu değildir; kullanıcı doğrudan dağıtımı başlatabilir.

## 63. Karar 63 – İlk geçerli dağıtımın hemen sunulması ve alternatiflerin sırayla incelenmesi

Dağıtım motoru ilk geçerli ve kabul koşullarını sağlayan yerleşimi bulduğunda, daha fazla arama yapıp sonucu geciktirmeden bu yerleşimi kullanıcıya sunacaktır. Kullanıcı ilk sonucu inceleyebilecek; uygun bulmazsa sonraki alternatif dağıtımı isteyerek alternatifler arasında ilerleyebilecektir.

- İlk bulunan geçerli dağıtım kullanıcıya hemen gösterilir; motorun bütün olası yerleşimleri tüketmesi veya teorik olarak en iyi sonucu kanıtlaması beklenmez.
- Kullanıcı ilk dağıtımı uygun bulmazsa daha önce kararlaştırıldığı gibi sonraki alternatifleri oluşturabilir ve inceleyebilir. Alternatif sayısı kullanıcı tarafından belirlenebilir.
- Her alternatif bağımsız olarak saklanır; önceki alternatiflerin üzerine yazılmaz.
- Alternatifler, daha önce kararlaştırılan dağıtım değerlendirme ölçütleriyle karşılaştırılabilir. Kullanıcı beğendiği alternatifi seçer.
- Bir alternatifin geçerli sayılması için fiziksel kapasite aşılmamalı, bütün öğrenciler yerleştirilmeli ve komşuluk ihlallerinden etkilenen benzersiz öğrenci sayısı belirlenmiş kesin üst sınırı (5) aşmamalıdır.
- Beş kişilik üst sınırı aşan bir yerleşim, ilk sonuç veya sonraki alternatif olarak başarılı/geçerli dağıtım şeklinde sunulmaz.
- Motorun çalışma ekranında işlem aşaması, geçen süre ve tahmini kalan süre gösterilebilir; ancak kullanıcıya ilk geçerli sonucu sunmak için tüm aramanın bitmesi beklenmez.

## 64. Sürüm 3.4 değişiklik kaydı

Karar 62 eklendi: Dağıtım öncesinde sınav kapsamı, öğrenci grupları, derslikler, kapasiteler ve aktif kuralların görülebildiği isteğe bağlı bir özet ekranı bulunacaktır. Kullanıcı bu ekranı inceleyebilir veya zorunlu ek onay olmadan doğrudan dağıtımı başlatabilir.

Karar 63 eklendi: Optimizasyon motoru ilk geçerli dağıtımı bulduğunda kullanıcıya hemen sunacaktır; teorik olarak en iyi sonucu bulana kadar kullanıcı bekletilmeyecektir. Kullanıcı uygun bulmazsa sonraki alternatifleri isteyerek inceleyebilir. Alternatifler bağımsız saklanır. Bütün öğrencilerin yerleştirilmesi, kapasitenin aşılmaması ve ihlalden etkilenen benzersiz öğrenci sayısının en fazla beş olması geçerlilik koşullarıdır. Önceki sürüm 3.3 korunur.


## 65. Karar 64 – Alternatif dağıtım üzerinde yapılan manuel değişikliklerin ayrı sürüm olarak saklanması

Kullanıcı, alternatif dağıtımlardan biri üzerinde manuel düzenleme yaptığında bu değişiklikler seçilen alternatifin üzerine yazılmayacaktır. Manuel düzenleme sonucunda o alternatiften türetilmiş yeni ve bağımsız bir sürüm oluşturulacaktır.

- İlk otomatik dağıtım ve oluşturulan bütün alternatifler değişmeden korunur.
- Kullanıcı bir alternatifi seçip öğrenci taşıma, koltuk değiştirme, öğrenciyi havuza alma veya başka bir manuel düzenleme yaptığında sistem bu işlemi seçilen alternatiften türetilen yeni bir sürüm olarak kaydeder.
- Yeni sürümün hangi alternatiften türetildiği, hangi manuel işlemlerin yapıldığı, işlem tarih/saat bilgisi ve değişiklik geçmişi tutulur.
- Kullanıcı önceki alternatiflere geri dönebilir; manuel düzenleme yapılmış sürüm de bağımsız olarak açılıp incelenebilir.
- Bir sürüm üzerinde yapılan sonraki manuel değişiklikler de sürüm geçmişine eklenir; önceki sürümler silinmez veya üzerine yazılmaz.
- Alternatiflerin ve bunlardan türetilen manuel sürümlerin karşılaştırılabilmesi ve geçmiş durumlarına geri dönülebilmesi sağlanır.

## 66. Sürüm 3.5 değişiklik kaydı

Karar 64 eklendi: Kullanıcı bir alternatif dağıtım üzerinde manuel değişiklik yaptığında, değişiklikler mevcut alternatifin üzerine yazılmaz; seçilen alternatiften türetilen yeni ve bağımsız bir sürüm olarak saklanır. İlk dağıtım ve diğer alternatifler korunur. Türetilme ilişkisi, yapılan işlemler ve tarih/saat bilgileri değişiklik geçmişinde tutulur. Kullanıcı alternatifler ve manuel düzenlenmiş sürümler arasında geçiş yapabilir ve önceki durumlara geri dönebilir. Önceki sürüm 3.4 korunur.


## 67. Karar 65 – Alternatif seçimi sonrası son kontrol, düzenleme ve kesinleştirme akışı

Kullanıcı beğendiği alternatif dağıtımı seçtiğinde dağıtım hemen kesinleştirilmez. Önce taslak/çalışma durumunda kalır ve kullanıcıya son kontrol ile manuel düzenleme imkânı verilir.

- Kullanıcı seçtiği alternatifi inceleyebilir ve gerekli manuel düzenlemeleri yapabilir.
- Manuel işlemler, Karar 64 uyarınca seçilen alternatiften türetilen bağımsız sürümler olarak saklanır; ilk dağıtım ve diğer alternatifler korunur.
- Kullanıcı düzenlemeleri tamamladığında son kontrol aşamasına geçer.
- Son kontrolde kapasite, bütün öğrencilerin yerleştirilmiş olması ve komşuluk ihlallerinden etkilenen benzersiz öğrenci sayısı yeniden denetlenir.
- Komşuluk ihlalleri varsa etkilenen öğrenciler ve oturma planındaki konumları gösterilir; kullanıcı daha önce belirlenen uyarı ve kabul sürecini izler. Beş kişilik kesin üst sınır aşılmışsa dağıtım kesinleştirilemez.
- Kullanıcı açıkça kesinleştirme işlemini onayladığında seçilen ve son kontrolü geçen sürüm, sınav organizasyonunun kesinleşmiş ana dağıtımı olur.
- Kesinleştirme öncesindeki alternatifler ve taslak sürümler silinmez; geçmişten erişilebilir kalır.

## 68. Sürüm 3.6 değişiklik kaydı

Karar 65 eklendi: Kullanıcı bir alternatif dağıtımı seçtiğinde sistem bu dağıtımı hemen kesinleştirmez. Alternatif taslak/çalışma durumunda açılır; kullanıcı manuel düzenlemelerini tamamlar ve son kontrolü başlatır. Kapasite, öğrenci yerleşimi ve komşuluk ihlalleri yeniden denetlenir. Gerekli uyarılar ve kullanıcı onayı tamamlandıktan sonra dağıtım açık onayla kesinleştirilir. Alternatifler ve taslak sürümler korunur. Önceki sürüm 3.5 korunur.


## 69. Karar 66 – Kesinleşmiş dağıtımda doğrudan düzenleme ve raporların güncelliği

Kesinleşmiş bir dağıtım, kullanıcı tarafından gerektiğinde doğrudan düzenlenebilir. Öğrenci taşıma, koltuk değiştirme, öğrenciyi bekleyen havuza alma veya diğer yerleşim değişiklikleri için ayrıca zorunlu bir revizyon oluşturma adımı bulunmayacaktır.

- Kesinleşmiş dağıtım üzerinde yapılan her işlem, sistemin mevcut değişiklik geçmişine tarih/saat ve işlem ayrıntılarıyla kaydedilir.
- Kullanıcı değişiklikleri geri alma ve ileri alma mekanizmasıyla yönetebilir.
- Dağıtımın kesinleşmiş olması manuel düzenlemeyi engellemez.
- Dağıtımda raporları etkileyen değişiklik olduğunda mevcut PDF/Excel raporları güncel değil olarak işaretlenir. Daha sonra alınan Karar 67 uyarınca eski raporların ayrıca saklanması zorunlu değildir; yeni rapor oluşturulurken eski rapor dosyaları değiştirilebilir veya kaldırılabilir.
- Dağıtımda raporları etkileyen bir değişiklik yapıldığında sistem raporların artık güncel olmadığını belirtir ve kullanıcıya güncel raporları yeniden oluşturması gerektiğini bildirir.
- Örnek uyarı: “Dağıtım üzerinde değişiklik yaptınız. Mevcut PDF ve Excel raporlarınız önceki yerleşimi göstermektedir. Güncel raporları yeniden oluşturmanız gerekmektedir.”
- Kullanıcı düzenlemeye devam edebilir; raporları yeniden oluşturma işlemi, kullanıcı hazır olduğunda başlatılır.
- Raporların yeniden oluşturulması, daha önceki değişiklik geçmişini veya geri/ileri alma kayıtlarını silmez.

## 70. Sürüm 3.7 değişiklik kaydı

Karar 66 eklendi: Kesinleşmiş dağıtımda kullanıcı doğrudan düzenleme yapabilir; ayrıca revizyon oluşturması zorunlu değildir. Tüm işlemler mevcut değişiklik geçmişine kaydedilir ve geri/ileri alma mekanizması kullanılabilir. Dağıtım değiştiğinde PDF/Excel raporları güncel değil olarak işaretlenir ve kullanıcıya yeniden oluşturma uyarısı verilir. Bu sürüm kaydındaki eski raporları koruma ifadesi, daha sonra alınan Karar 67 ile değiştirilmiştir: eski raporların ayrıca saklanması zorunlu değildir ve yeni raporlarla değiştirilebilir. Önceki sürüm 3.6 korunur.

## 71. Karar 67 – Raporların güncel dağıtım durumuna göre yeniden oluşturulması

PDF ve Excel raporları, dağıtımın kalıcı tarihsel arşivi olarak saklanmak zorunda değildir. Dağıtım üzerinde geri alma/ileri alma yapılarak farklı bir işlem geçmişi veya yerleşim durumuna geçilebilir. Kullanıcı bu farklı durumu kabul edip raporları yeniden oluşturduğunda:

- Yeni raporlar, kullanıcının o anda kabul ettiği güncel dağıtım durumundan üretilir.
- Önceki rapor dosyalarının saklanması zorunlu değildir; yeni raporlar oluşturulurken eski raporlar değiştirilebilir veya kaldırılabilir.
- Uygulamanın esas aldığı kayıt, rapor dosyası değil dağıtımın güncel veri durumu ve değişiklik geçmişidir.
- Geri alma/ileri alma geçmişi korunur; raporların yenilenmesi bu geçmişi silmez.
- Dağıtımda raporu etkileyen yeni bir değişiklik yapılırsa raporlar yeniden güncel değil durumuna geçer ve kullanıcıya tekrar rapor oluşturma uyarısı gösterilir.
- Rapor oluşturma, kullanıcı son düzenlemeleri kabul edip hazır olduğunu belirttiğinde yapılır.

Bu kararla önceki raporların ayrıca arşivlenmesi zorunluluğu kaldırılmıştır. Güncel rapor seti, kullanıcının kabul ettiği son dağıtım durumunu temsil eder. Bu hüküm, Karar 66 metnindeki eski raporların korunmasına ilişkin önceki ifadeyi günceller.

## 72. Sürüm 3.8 değişiklik kaydı

Karar 67 eklendi: PDF/Excel raporlarının eski sürümlerini ayrıca saklamak zorunlu değildir. Kullanıcı geri/ileri alma ile farklı bir dağıtım durumuna geçip bunu kabul ettiğinde raporlar o anki güncel dağıtım üzerinden yeniden oluşturulur; eski raporlar değiştirilebilir veya kaldırılabilir. Asıl geçmiş, rapor dosyalarında değil dağıtımın değişiklik geçmişinde korunur. Yeni bir düzenleme raporları yeniden güncel değil durumuna getirir. Önceki sürüm 3.7 korunur.

## 73. Karar 68 – Tamamlanan sınav organizasyonunun arşivlenmesi

Sınav organizasyonu tamamlandığında kullanıcı organizasyonu **Tamamlandı** durumuna alabilir. Tamamlanan organizasyon, geçmiş sınavlar bölümünde saklanır ve daha sonra görüntülenebilir.

- Tamamlanan organizasyonun sınav bilgileri, öğrenci yerleşimleri, derslik planları, değişiklik geçmişi ve son oluşturulan PDF/Excel raporları birlikte korunur.
- Arşivlenen organizasyon geçmiş kayıt olarak açılabilir ve incelenebilir.
- Eski organizasyon üzerinde doğrudan değişiklik yapılarak geçmiş kayıt bozulmaz. Yeniden kullanılmak istenirse bu organizasyondan **yeni ve bağımsız bir kopya** oluşturulur.
- Kopya organizasyon kendi adı, tarihi, çalışma durumu ve değişiklik geçmişiyle ilerler; kaynak organizasyon değişmeden kalır.
- Böylece geçmiş sınav kayıtları korunurken benzer bir sınav organizasyonu sonraki dönemlerde başlangıç noktası olarak kullanılabilir.

## 74. Sürüm 3.9 değişiklik kaydı

Karar 68 eklendi: Sınav organizasyonu tamamlandığında kullanıcı tarafından **Tamamlandı** durumuna alınarak geçmiş sınavlar bölümünde arşivlenir. Organizasyonun öğrenci yerleşimleri, derslik planları, değişiklik geçmişi ve son raporları korunur. Geçmiş organizasyon görüntülenebilir; yeniden kullanılacaksa kaynak kaydı değiştirilmeden yeni ve bağımsız bir kopya oluşturulur. Önceki sürüm 3.8 korunur.

## 75. Karar 69 – Arşivlenmiş organizasyonun salt okunur açılması ve yeniden çalışma kopyası

Arşivlenmiş ve **Tamamlandı** durumuna alınmış bir sınav organizasyonu varsayılan olarak salt okunur açılır. Kullanıcı geçmiş organizasyonu görüntüleyebilir ve inceleyebilir; kaynak arşiv kaydı üzerinde doğrudan düzenleme yapamaz.

- Kullanıcı arşivlenmiş organizasyonda değişiklik yapmak veya onu yeni bir sınav için başlangıç noktası olarak kullanmak isterse sistem kaynak kaydı değiştirmeden yeni bir çalışma kopyası oluşturur.
- Yeni çalışma kopyası bağımsız bir organizasyondur; kendi adı, tarihi, durumu ve değişiklik geçmişi bulunur.
- Kaynak arşiv organizasyonun öğrenci yerleşimleri, derslik planları, raporları ve geçmiş işlem kayıtları aynen korunur.
- Kullanıcı yeni çalışma kopyası üzerinde normal düzenleme, dağıtım, kontrol ve rapor oluşturma adımlarını yürütebilir.
- Böylece geçmiş sınav kaydı yanlışlıkla değiştirilemez; eski organizasyon gerektiğinde güvenli biçimde yeniden kullanılabilir.

## 76. Sürüm 4.0 değişiklik kaydı

Karar 69 eklendi: Tamamlandı durumundaki arşivlenmiş organizasyon varsayılan olarak salt okunur açılır. Düzenleme veya yeniden kullanım gerektiğinde kaynak arşiv kaydı korunarak yeni ve bağımsız bir çalışma kopyası oluşturulur. Yeni kopya kendi adı, tarihi, durumu ve değişiklik geçmişiyle ilerler. Önceki sürüm 3.9 korunur.


## 77. Karar 70 – Eğitim öğretim yılı bazında arşivleme ve kalıcı silme yapılmaması

Sınav organizasyonları eğitim öğretim yılına göre ayrılarak saklanır. Tamamlanmış organizasyonlar ilgili eğitim öğretim yılının arşivinde korunur. Olağan kullanımda organizasyonları kalıcı olarak silme özelliği bulunmayacaktır.

- Her eğitim öğretim yılına ait sınav organizasyonları kendi yılı altında listelenir (ör. 2026-2027).
- Bir eğitim öğretim yılında oluşan organizasyonlar, sonraki yıllarda da geçmiş kayıt olarak saklanır ve gerektiğinde görüntülenebilir.
- Yıllık organizasyon sayısının sınırlı olması nedeniyle çöp kutusu, saklama süresi ve kalıcı silme iş akışı geliştirilmez.
- Yeni eğitim öğretim yılı başlatıldığında o yılın çalışma verileri ve organizasyonları yeni yıl için oluşturulur; önceki eğitim öğretim yılının arşivi korunur.
- Yeni yılın öğrenci/sınıf verileri ve gerekli başlangıç tanımları yeni döneme göre hazırlanır. Önceki yılın tamamlanmış organizasyonları yeni yılın aktif çalışma alanına otomatik olarak taşınmaz.
- Geçmiş bir organizasyondan yararlanılması gerekirse Karar 69 uyarınca kaynak arşiv kaydı değiştirilmeden yeni ve bağımsız çalışma kopyası oluşturulur.

## 78. Sürüm 4.1 değişiklik kaydı

Karar 70 eklendi: Sınav organizasyonları eğitim öğretim yılı bazında ayrılarak saklanır; olağan sistem işleyişinde kalıcı silme özelliği bulunmaz. Yeni eğitim öğretim yılı başlatıldığında yeni yılın çalışma verileri ve organizasyonları oluşturulur, önceki yılın arşivi korunur. Geçmiş organizasyonlar gerektiğinde salt okunur görüntülenir veya Karar 69'a uygun biçimde bağımsız çalışma kopyasına dönüştürülür. Önceki sürüm 4.0 korunur.


## 79. Karar 71 – Eğitim öğretim yılı seçimi ve yeni yılın sınıf/derslik hazırlığı

Kullanıcı sisteme giriş yaptığında varsayılan olarak içinde bulunulan eğitim öğretim yılı seçili gelir. Ana çalışma alanının sağ tarafında eğitim öğretim yılı seçimi bulunur. Kullanıcı seçili yılı onaylayarak o yılın sınav organizasyonlarına geçer; isterse geçmiş eğitim öğretim yıllarını seçerek ilgili yılın arşivindeki organizasyonları görüntüleyebilir.

- Eğitim öğretim yılı seçimi, sisteme girişte güncel yıl varsayılan olacak şekilde sunulur; kullanıcı başka bir yılı seçip onaylayabilir.
- Geçmiş yılların organizasyonları kendi arşivlerinde korunur. Kullanıcı bu yıllara geçebilir; geçmiş organizasyonları salt okunur inceleyebilir ve gerektiğinde Karar 69 uyarınca yeni, bağımsız bir çalışma kopyası oluşturabilir.
- Yeni eğitim öğretim yılı için e-Okul öğrenci listesi içeri aktarıldığında sınıf/şube listeleri ve öğrenci mevcutları otomatik oluşturulur. Bu mevcutlara göre sınıf/derslik başlangıç kapasitesi sistem tarafından hazırlanır.
- Kullanıcıdan öğrenci listelerini veya sınıf mevcutlarını elle yeniden oluşturması beklenmez.
- Kullanıcının esas düzenleyeceği bölüm fiziksel oturma düzenidir: sıraların tekli, ikili veya üçlü olması, sınıftaki fiziksel yerleşim, bloklar ve koridorlar gibi gerçek derslik düzeni kullanıcı tarafından kontrol edilip düzenlenir. Bu düzen sınıftan sınıfa değişebilir.
- Sistem, e-Okul'dan gelen öğrenci mevcudunu başlangıç kapasitesi için esas alır; fiziksel oturma düzeni ve kullanılabilir koltuk sayısı kullanıcı tarafından tanımlanıp doğrulanır. Fiziksel düzenin gerçek kapasitesi öğrenci mevcudundan farklıysa kullanıcı gerekli düzeltmeyi yapabilir.
- Geçmiş yıldan derslik/oturma düzeni kopyalama, kullanıcı isterse başlangıç kolaylığı olarak sunulabilir; ancak yeni yılın e-Okul öğrenci listesi ve mevcutları esas alınır, fiziksel düzen yeni yılın sınıf koşullarına göre kullanıcı tarafından kontrol edilip onaylanır. Kopyalama geçmiş yıl kayıtlarını değiştirmez.

## 80. Sürüm 4.2 değişiklik kaydı

Karar 71 eklendi: Sisteme girişte güncel eğitim öğretim yılı varsayılan seçili gelir; kullanıcı sağ taraftaki yıl seçicisinden yılı onaylayarak o yılın organizasyonlarına geçer veya geçmiş yılların arşivlerini açabilir. Yeni yılın e-Okul listesi aktarıldığında sınıf/şube listeleri ve mevcutlar otomatik oluşturulur; başlangıç kapasitesi bu mevcutlara göre hazırlanır. Kullanıcı esas olarak fiziksel oturma düzenini (tekli/ikili/üçlü sıralar, bloklar, koridorlar ve yerleşim) düzenler ve doğrular. Geçmiş yıldaki fiziksel düzen isteğe bağlı olarak yeni yıla başlangıç şablonu şeklinde kopyalanabilir; yeni yılın öğrenci verisi ve fiziksel koşulları ayrıca kontrol edilir. Önceki sürüm 4.1 korunur.


## 81. Karar 72 – macOS ve Windows çapraz platform geliştirme, sürümleme ve artımlı güncelleme

Kullanıcı öncelikli olarak Apple Silicon MacBook üzerinde çalışacaktır. Kelebek Sınav Sistemi aynı kaynak kod tabanıyla hem macOS hem Windows üzerinde çalışacak şekilde geliştirilecektir. Windows desteği sonradan eklenecek bir uyarlama değil, ilk mimariden itibaren kabul kriteridir.

- Ortak iş mantığı, veritabanı şeması, kullanıcı arayüzü ve rapor üretim kodu platformdan bağımsız tutulur.
- macOS ve Windows için ayrı çalıştırılabilir/kurulum paketleri üretilir; aynı paketin iki işletim sisteminde de çalışması beklenmez.
- Öncelikli geliştirme ve günlük kullanım ortamı MacBook'tur; Windows üzerinde düzenli test ve paket doğrulaması yapılır.
- Uygulama yerel web uygulaması olarak çalışır; işletim sistemine özgü başlatıcı yerel servisi başlatır ve varsayılan tarayıcıyı açar.
- Kullanıcı verileri işletim sistemine uygun kullanıcı veri dizininde, kurulum dosyalarından ayrı saklanır.
- Her sürüm Git üzerinden izlenir; sürüm etiketi, değişiklik günlüğü, test sonucu ve dağıtım paketi bulunur.
- Tam kurulum paketine ek olarak, yalnızca değişen dosyaları ve gerekiyorsa veritabanı migration'larını içeren artımlı güncelleme paketi hazırlanır.
- Her güncelleme öncesinde otomatik güvenlik yedeği alınır; dosya bütünlüğü ve şema uyumluluğu doğrulanır. Başarısız güncellemede güvenli geri dönüş sağlanır.
- MacBook ve Windows bilgisayar arasında veri aktarımı, canlı SQLite dosyasını eş zamanlı paylaşarak değil, doğrulanmış taşınabilir yedek paketiyle yapılır.
- Kod geliştirme, dosya değişiklikleri, testlerin çalıştırılması, Git diff incelemesi ve sürüm hazırlama için Codex kullanılacaktır. ChatGPT bu süreçte gereksinim denetimi, mimari kararlar, test senaryoları ve teknik değerlendirmede kullanılabilir.

## 82. Sürüm 4.3 değişiklik kaydı

Karar 72 eklendi: Uygulama öncelikli olarak Apple Silicon MacBook üzerinde geliştirilecek; aynı kaynak kod tabanıyla macOS ve Windows'u destekleyecektir. İşletim sistemlerine özgü kurulum paketleri ayrı üretilecek, kullanıcı verileri kurulum dizininden ayrı tutulacak, Git tabanlı sürümleme ve veritabanı migration'ları kullanılacaktır. Tam paket yanında değişen dosyaları ve gerekli migration'ları içeren artımlı güncelleme paketleri hazırlanacaktır. Güncelleme öncesi yedek, bütünlük kontrolü ve başarısızlıkta geri dönüş zorunludur. Önceki sürüm 4.2 korunur.
