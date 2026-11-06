import { useEffect, useState } from 'react'

type HealthState = 'checking' | 'online' | 'offline'

export default function App() {
  const [health, setHealth] = useState<HealthState>('checking')

  useEffect(() => {
    const controller = new AbortController()

    fetch('/api/health', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API yanıt vermedi')
        return response.json()
      })
      .then(() => setHealth('online'))
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === 'AbortError') return
        setHealth('offline')
      })

    return () => controller.abort()
  }, [])

  const statusText = {
    checking: 'Bağlantı kontrol ediliyor',
    online: 'Yerel servis çalışıyor',
    offline: 'Yerel servisle bağlantı kurulamadı',
  }[health]

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Kelebek Sınav Sistemi ana sayfa">
          <span className="brand-mark" aria-hidden="true">K</span>
          <span>Kelebek <strong>Sınav Sistemi</strong></span>
        </a>
        <span className={`service-status ${health}`} role="status">
          <span className="status-dot" />
          {statusText}
        </span>
      </header>

      <section className="welcome-card" aria-labelledby="welcome-title">
        <div className="eyebrow">YEREL SINAV ORGANİZASYONU</div>
        <h1 id="welcome-title">Sınav planlaması için çalışma alanınız</h1>
        <p className="welcome-copy">
          Öğrencileri, derslikleri ve oturma düzenlerini tek bir güvenli çalışma alanında yönetin.
          Uygulama verileri bu bilgisayarda saklanır.
        </p>

        <div className="setup-notice">
          <span className="notice-icon" aria-hidden="true">✦</span>
          <div>
            <strong>Başlangıç ortamı hazır</strong>
            <p>Bu ilk geliştirme sürümünde modüller sırayla eklenecek.</p>
          </div>
        </div>

        <div className="feature-grid">
          <article className="feature-card">
            <span className="feature-number">01</span>
            <h2>Öğrenci kayıtları</h2>
            <p>Okul ve sınıf listeleri için güvenli yerel kayıt alanı.</p>
            <span className="feature-state">Hazırlanıyor</span>
          </article>
          <article className="feature-card">
            <span className="feature-number">02</span>
            <h2>Derslik düzeni</h2>
            <p>Fiziksel masa ve oturma yerlerini tanımlama.</p>
            <span className="feature-state">Hazırlanıyor</span>
          </article>
          <article className="feature-card">
            <span className="feature-number">03</span>
            <h2>Sınav dağıtımı</h2>
            <p>Öğrenci gruplarını seçilen dersliklere dengeli yerleştirme.</p>
            <span className="feature-state">Hazırlanıyor</span>
          </article>
        </div>
      </section>

      <footer className="page-footer">
        Çevrimdışı çalışmak üzere tasarlanmıştır <span aria-hidden="true">·</span> Veriler bu bilgisayarda kalır
      </footer>
    </main>
  )
}
