import { useEffect, useState } from 'react'

type Note = { version: string; date: string; items: string[] }

// Güncellemeden sonraki ilk açılışta yeni sürümün kısa notlarını göster.
export default function WhatsNewDialog() {
  const [notes, setNotes] = useState<Note[]>([])
  const [version, setVersion] = useState('')

  useEffect(() => {
    fetch('/api/app/whats-new').then((response) => response.json()).then((data) => {
      if (data.show) { setNotes(data.notes); setVersion(data.current_version) }
    }).catch(() => undefined)
  }, [])

  if (!notes.length) return null
  function close() {
    void fetch('/api/app/whats-new/seen', { method: 'POST' }).catch(() => undefined)
    setNotes([])
  }
  return <div className="whats-new-backdrop" role="dialog" aria-modal="true" aria-labelledby="whats-new-title" data-testid="whats-new-dialog">
    <div className="whats-new-card">
      <span className="eyebrow">GÜNCELLEME TAMAMLANDI</span>
      <h2 id="whats-new-title">Sürüm {version} ile gelenler</h2>
      {notes.map((note) => <section key={note.version}>
        <strong>{note.version}{note.date ? ` · ${new Date(note.date).toLocaleDateString('tr-TR')}` : ''}</strong>
        <ul>{note.items.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>)}
      <p>Verileriniz korunarak güncellendi; güncelleme öncesi güvenlik yedeği Yedek ve arşiv bölümünde.</p>
      <button type="button" data-testid="whats-new-close" onClick={close}>Tamam, başlayalım</button>
    </div>
  </div>
}
