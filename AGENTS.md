# Kelebek Sınav Sistemi — proje yönergeleri

## Temel kaynaklar

- `docs/Kelebek_Sinav_Sistemi_Ana_Proje_Karar_Dokumani_v4.3.md` içindeki onaylanmış kararları koru. Önceden kesinleşen 71 kararı ve bu sürümde ayrıca yer alan çapraz platform geliştirme kararı 72'yi değiştirme. Karar 73 (toplu silme) kullanıcının açık onayıyla 12 Kasım 2026'da eklenmiştir.
- `docs/Kelebek_Sinav_Sistemi_Teknik_Mimari_v1.0.md` teknik mimari ve geliştirme planının temelidir.
- Bu belgelerdeki kararlarla çelişen bir değişiklik yapmadan önce kullanıcıdan açık onay al. Yeni ihtiyaçları mevcut kararlardan ayır ve yalnızca etkilenen konuları gündeme getir.
- macOS ve Windows desteğini, çevrimdışı yerel çalışma modelini ve kullanıcı verisinin uygulama dosyalarından ayrı tutulmasını gözet.

## Veri güvenliği

- Gerçek öğrenci verilerini, kişisel bilgileri, okul listelerini, yerel SQLite veritabanlarını, yedekleri, dışa aktarılan raporları, sırları ve kimlik bilgilerini Git deposuna ekleme.
- Gerçek öğrenci verilerini kaynak kod, test, günlük, ekran görüntüsü veya Codex'e gönderilen dosyalara kopyalama.
- Test verisi gerektiğinde yalnızca sentetik veri kullan.
- `data/`, `instance/`, `backups/`, `backup/` ve `exports/` dizinleri kullanıcı verisi içindir; kaynak kod deposunda tutulmamalıdır.

## Geliştirme yaklaşımı

- Aynı kaynak kod tabanını macOS ve Windows'ta çalışabilir tut.
- Mimari belgede seçilen teknoloji ve modül sınırlarını izle; yeni bir karar gerektiren sapmayı önce kullanıcıyla değerlendir.
- Veritabanı şeması değişikliklerini migration ile yönet; kullanıcı verisini güncelleme sırasında koru.
- Dağıtım, geçmiş, raporlama ve yedekleme kurallarını karar belgesine uygun uygula.
- Belgeleri ve uygulamayı birlikte tutarlı tut; karar belgesini kullanıcının onayı olmadan değiştirme.
