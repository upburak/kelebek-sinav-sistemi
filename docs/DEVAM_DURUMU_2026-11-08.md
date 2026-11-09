# Kelebek Sınav Sistemi — devam notu

Son güncelleme: 9 Kasım 2026

Bu not, sonraki çalışma oturumunda bağlamı hızlıca geri yüklemek içindir. Proje kapsamı ve kesinleşmiş kararlar için ana karar belgesi v4.3 ile teknik mimari v1.0 esas alınır; onaylanmış 71 karar ve çapraz platform kararı değiştirilmemiştir.

## Bugün tamamlananlar

- Raporlar bölümü etkinleştirildi; kesinleşmiş sınav seçimiyle kapı krokisi, yoklama, derslik listesi, genel dağıtım ve sınıf/şube listesi çıktıları erişilebilir.
- PDF ve Excel listelerinde rapor türüne göre sütunları açıp kapatma eklendi. En az bir alan seçili kalır; kapı krokisinin zorunlu alanları sabittir.
- Seçili sütunların başlıkları düzenlenebilir ve yukarı/aşağı taşınabilir; yeni başlık ve sıra PDF ile Excel çıktılarına uygulanır. API yalnızca görünür sütunların 1–40 karakterlik başlıklarına izin verir.
- PDF sayfa ayarları A4, A3, A5, Letter ve Legal; otomatik/dikey/yatay yön; 5–30 mm kenar boşluğu seçeneklerini destekler.
- Raporlarda Türkçe karakter, sınıf gruplaması, boş/kullanım dışı koltuklar ve uzun adlarda soyadın korunması sentetik verilerle doğrulandı.
- Geliştirme API port seçimi, fiziksel derslik doğrulaması ve geri yükleme geçici alanı açılış temizliğiyle ilgili önceki oturum değişiklikleri çalışma ağacında korunuyor.

## Son doğrulama

- `PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v` — 16 test geçti; özel başlık/sıra PDF metni ve Excel başlık hücreleriyle doğrulandı.
- `frontend/` içinde `npm run build` — başarılı.
- `git diff --check` — başarılı.
- Chrome’da yerel sentetik sınavla Raporlar ekranı, sayfa ayarları ve sütun seçici kontrol edildi. Test sunucuları kapatıldı.
- Gerçek öğrenci verisi, okul listesi, gerçek yedek veya gerçek veritabanı bu doğrulamada kullanılmadı.

## Devam ederken dikkat

- Çalışma ağacında çok sayıda kasıtlı ve henüz commit edilmemiş değişiklik var. Bunları silme, üzerine yazma, commit veya push yapma.
- 0016 migration’ın daha önce uygulandığı kaydedilmiş durumda; tekrar çalıştırmadan önce çalışan süreci ve şema sürümünü kontrol et.
- Veritabanı, yedekler ve sırlar Git’e eklenmemeli.

## Açık kalanlar

- Rapor alanlarında göster/gizle, özel sütun başlığı ve sütun sırası kullanılabiliyor. Diğer şablon/içerik seçenekleri ve kalan karar belgesi çıktıları gözden geçirilmeli.
- Windows çalıştırma/dağıtım doğrulaması ve paketlenmiş masaüstü teslimi ayrıca tamamlanmalı.
