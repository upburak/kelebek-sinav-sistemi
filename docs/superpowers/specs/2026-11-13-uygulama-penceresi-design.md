# Uygulama penceresi — kısa tasarım

**Tarih:** 13 Kasım 2026 · **Durum:** kullanıcı onayladı ("çok hafif yolu seçerek aynı işi yapabiliyor olmak daha iyi olur, bunu yap")

## Amaç

Uygulama tarayıcı sekmesinde değil, kendi penceresinde çalışsın: görev çubuğunda ayrı dursun,
pencere kapanınca uygulama da kapansın. Kullanıcı Electron'u sordu; hafif bir yol tercih etti.

## Hedef olmayanlar

- Arayüzü yeniden yazmak, tarayıcı desteğini bırakmak.
- Pakete tarayıcı ya da ek çalışma zamanı gömmek.

## Yaklaşımlar

1. **Electron:** her pakete Chromium ve Node gömülür; kurulum ~70 MB'tan ~170 MB'a çıkar, üç
   işletim sistemi için ayrı derleme ve güncelleme düzeni gerekir. Reddedildi (ağır).
2. **pywebview (işletim sisteminin görüntüleyicisi):** Windows'ta pythonnet + WebView2, macOS'ta
   pyobjc, Linux'ta paketlenmesi zor GTK/WebKit bağımlılıkları. İndirme, yazdırma ve yeni pencere
   davranışları tarayıcıdan farklı; burada sınanamıyor. Reddedildi (risk).
3. **Kurulu Chromium tabanlı tarayıcıyı uygulama kipinde açmak (seçilen):** Windows'ta Edge her
   zaman var. Sıfır yeni bağımlılık, paket boyutu aynı, indirme/yazdırma/onay pencereleri bugünkü
   gibi çalışır. Zayıf yanı: yalnızca Safari ya da Firefox olan bilgisayarda pencere açılamaz;
   orada bugünkü davranışa (sekme) düşülür.

## Tasarım (benim kararlarım)

- `kelebek/app_window.py`: tarayıcıyı bulur, `--app=<adres>` ve veri klasöründeki ayrı profille
  (`window-profile`) başlatır.
- Başlatıcı: pencere açıldıysa süreci izler; süreç kapanınca servisi durdurur. İlk 4 saniyede çıkan
  süreç "devir" sayılır ve uygulamayı kapatmaz. Uygulama kapanırken açık pencere sonlandırılır.
- Ayar: `ui_state.json` içinde `app_window` (varsayılan açık); `GET/PUT /api/app/window-mode`;
  Yedek ve arşiv bölümünde onay kutusu. `KELEBEK_BROWSER_TAB=1` da sekmeye zorlar.
- `/api/health` yanıtına `window` alanı (sınama için).
- Karar belgesine Karar 74.

## Sınama

Birim testleri (tarayıcı bulma, komut, ayar, yaşam döngüsü), tarayıcı testi (ayar), gerçek
Chromium ile yerel deneme ve paketleme iş akışında Windows/macOS pencere testi.
