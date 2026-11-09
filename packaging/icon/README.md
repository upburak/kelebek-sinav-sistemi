# Uygulama simgesi

`kelebek.svg` simgenin tek kaynağıdır. Paketlerde kullanılan dosyalar bundan üretilir:

- `packaging/macos/kelebek.icns` — macOS uygulama paketi (16–1024 px)
- `packaging/windows/kelebek.ico` — Windows `.exe` ve kurulum sihirbazı (16–256 px)

`packaging/kelebek.spec` bu iki dosyayı kendiliğinden bulur; yol vermek gerekmez.

Simgeyi değiştirmek için `kelebek.svg` dosyasını düzenleyin, 1024×1024 PNG olarak
dışa aktarın ve iki dosyayı yeniden üretin:

```python
from PIL import Image
master = Image.open("icon-1024.png").convert("RGBA")
master.save("packaging/windows/kelebek.ico", format="ICO",
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
master.save("packaging/macos/kelebek.icns", format="ICNS")
```

Pillow yalnızca bu üretim adımında gerekir; uygulamanın çalışma zamanı bağımlılığı değildir.
