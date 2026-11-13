"""Uygulama içi "Yenilikler" notları. `scripts/release.py --notes` yeni sürümün notlarını başa ekler."""

RELEASE_NOTES = [
  {
    "version": "0.10.0",
    "date": "2026-11-13",
    "items": [
      "Uygulama artık tarayıcı sekmesinde değil, adres çubuğu olmayan kendi penceresinde açılır; pencereyi kapatınca uygulama da kapanır",
      "Bunun için Edge ya da Chrome kullanılır (Windows'ta Edge hazır gelir); yoksa eskisi gibi tarayıcı sekmesinde açılır",
      "Yedek ve arşiv bölümündeki \"Uygulamayı kendi penceresinde aç\" ayarıyla eski davranışa dönülebilir",
      "\"Uygulamayı kapat\" düğmesi artık uygulamayı hemen kapatır; arka planda açık kalmaz"
    ]
  },
  {
    "version": "0.9.3",
    "date": "2026-11-13",
    "items": [
      "Windows'ta uygulama açılırken siyah komut penceresi artık görünmez; kapatmak için sağ üstteki \"Uygulamayı kapat\" düğmesi kullanılır",
      "Uygulama açılamazsa nedeni bir ileti kutusunda gösterilir"
    ]
  },
  {
    "version": "0.9.2",
    "date": "2026-11-13",
    "items": [
      "Pardus ve Debian tabanlı Linux için kurulum paketi (.deb): uygulama menüsüne kısayol ekler, veriler ev dizininde kalır",
      "Linux'ta da yeni sürüm denetlenir; indirilen paket sistemin paket kurucusuyla açılır"
    ]
  },
  {
    "version": "0.9.1",
    "date": "2026-11-13",
    "items": [
      "Oturma planı: sütun numarasına tıklayınca sağına koridor eklenir ya da var olan koridor kaldırılır; diğer sütunlar kendiliğinden kayar"
    ]
  },
  {
    "version": "0.9.0",
    "date": "2026-11-13",
    "items": [
      "Yeni görünüm: kara tahta yeşili, daha büyük yazı ve her ekranda aynı düğme ve kart dili",
      "Oturma planı düzenleyici: satır ve sütun ekle, satır ya da sütunu başlığından sürükle, masayı tekli/çiftli/üçlü yap ya da sil",
      "Derslik kapatılabilir (yeni sınavlarda görünmez) ve sınavda kullanılmamışsa planıyla birlikte silinebilir",
      "\"Pasif kayıtları göster\" artık yalnızca pasife alınan öğrencileri listeler",
      "Bu pencere yalnızca son sürümü gösterir; önceki sürümler Yedek ve arşiv bölümündeki Sürüm notları'nda"
    ]
  },
  {
    "version": "0.8.1",
    "date": "2026-11-12",
    "items": [
      "Uygulama açılırken tarayıcıda \"Not Found\" sayfası çıkması giderildi: başlatıcı artık yalnızca gerçekten çalışan uygulamaya yönlenir, değilse yenisini açar"
    ]
  },
  {
    "version": "0.8.0",
    "date": "2026-11-12",
    "items": [
      "Toplu silme: Sınavlar, Öğrenci kayıtları ve Derslikler bölümlerinde içeriğin tamamı tek düğmeyle silinebilir",
      "Silmeden önce silinecek kayıt sayıları gösterilir ve veriler kendiliğinden yedeklenir"
    ]
  },
  {
    "version": "0.7.0",
    "date": "2026-11-12",
    "items": [
      "Derslikler: bir dersliğe tıklayınca doğrudan oturma planı açılır; planı düzenlemek için ayrı kopya açmak gerekmez",
      "Sınavlar: yalın liste ve her sınavın kendi sayfası; sayfada yalnızca sıradaki adım görünür, raporlar son adımdır",
      "Sınava giren sınıflar öğrenci sayılarıyla her zaman görünür; oluşturma bildirimi sınıf ve öğrenci sayısını yazar",
      "Her kaydetme ve aktarma işleminin sonucu sağ altta aynı yerde bildirilir",
      "Derslik planı değişince taslak sınavlar yeni planı kullanır ve yeniden dağıtım gerektiği söylenir"
    ]
  },
  {
    "version": "0.6.1",
    "date": "2026-11-11",
    "items": [
      "Yeni sınavda yalnızca sınava giren sınıfların kendi derslikleri seçilir; artık bütün derslikler gelmez",
      "Sınıf seçiminde \"Tüm sınıfları seç\" düğmesi"
    ]
  },
  {
    "version": "0.6.0",
    "date": "2026-11-11",
    "items": [
      "Yeni sürüm denetimi: uygulama açılışta ve istenince son sürümü sorar, yeni sürüm varsa bildirir",
      "Yeni sürüm tek tıkla indirilir, doğrulanır ve kurulum penceresi açılır; önce güvenlik yedeği alınır",
      "Denetim kapatılabilir; internet yoksa uygulama aynen çalışır, hiçbir okul verisi gönderilmez"
    ]
  },
  {
    "version": "0.5.0",
    "date": "2026-11-11",
    "items": [
      "Sınav hazırlığı adım adım: her sınav kartı sıradaki adımı ve basılacak tek düğmeyi gösterir",
      "Yeni sınavda derslikler kendiliğinden seçilir; dağıtım sonucu doğrudan kullanıma alınır",
      "Oturma planı derslik derslik sekmelerle gezilir; ileri düzey seçenekler ayrı bölümde",
      "Derslikte hangi oturma düzeninin kullanılacağı \"Aktif yap\" ile belirlenir; sınavda o düzen gelir",
      "Kullanılmayan oturma düzenleri silinebilir; bir sınavda kullanılmış düzenler korunur",
      "Liste aktarımında alan seçiminin hemen altına \"Alanları uygula ve devam et\" düğmesi eklendi"
    ]
  },
  {
    "version": "0.4.2",
    "date": "2026-11-11",
    "items": [
      "Liste aktarımında alan seçiminin hemen altına \"Alanları uygula ve devam et\" düğmesi eklendi"
    ]
  },
  {
    "version": "0.4.1",
    "date": "2026-11-11",
    "items": [
      "Derslikler sınav seçiminde de sınıf sırasına göre listelenir (9-A, 10-A'dan önce)",
      "Kesinleşen sınavların durum etiketi yeşil gösterilir",
      "Menüde etkin bölümün rengi fare üzerindeyken değişmez"
    ]
  },
  {
    "version": "0.4.0",
    "date": "2026-11-10",
    "items": [
      "Genel Bakış yenilendi: öğrenci, koltuk, sınav ve yedek durumu ile sıradaki adım canlı gösteriliyor",
      "Sınav dönemleri: Güz 1/2 ve Bahar 1/2 hazır gelir; adları değiştirilebilir, dönem eklenip silinebilir",
      "Yeni kurallar: aynı sınıf seviyesindeki öğrenciler yan yana ve önlü arkalı oturmaz",
      "Koridorun iki yanındaki öğrenciler de yan yana sayılır; çapraz komşuluk ayrıca denetlenir",
      "Dağıtım, koltuk sayısı öğrenci sayısına eşit olan büyük okullarda saniyeler içinde sonuç verir",
      "Excel'den içe aktarma düzeltildi; başlangıç derslik düzeni üç blok ve iki koridorla kurulur",
      "Öğrenci listesinde arama ve sınıf filtresi; dersliklerde koltuk sayısı ve doğal sıralama"
    ]
  },
  {
    "version": "0.3.0",
    "date": "2026-11-09",
    "items": [
      "macOS kurulumunda arayüzün hiç açılmamasına yol açan statik dosya hatası giderildi",
      "Rapor PDF'lerinde Türkçe harfler yazı tipi bulunamadığında da doğru yazılıyor",
      "macOS'ta artımlı güncelleme sonrası uygulama paketi yeniden imzalanıyor",
      "Kurulum betikleri Python 3.12 ve üzeri tüm sürümleri kabul ediyor",
      "Her değişiklikte Mac, Windows ve Linux'ta otomatik test çalışıyor"
    ]
  },
  {
    "version": "0.2.0",
    "date": "2026-11-09",
    "items": [
      "Derslik sabitleyerek yeniden dağıtım ve sınavı tamamlayıp arşivleme",
      "Güncel öğrenci listesiyle karşılaştırma ve tek sekmede düzenleme",
      "İhlal krokisi, çözüm önerisi ve \"Tümünü düzelt\"",
      "Dağıtım ilerleme ekranı ve durdurma",
      "İmzalı artımlı güncelleme ve otomatik geri dönüş"
    ]
  }
]
