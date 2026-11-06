# Veritabanı migration'ları

Alembic migration'ları uygulama açılışında uygulanır. Mevcut bir SQLite veritabanında şema değişikliği yapılmadan önce tutarlı yedek, kullanıcı veri klasöründeki backups dizinine alınır.

Migration'ları uygulama içinde veya yerel geliştirmede Alembic CLI ile yönetin; gerçek veritabanı dosyalarını kaynak deposuna kopyalamayın.
