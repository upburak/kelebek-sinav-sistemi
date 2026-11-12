import { useEffect, useState } from 'react'

type Note = { version: string; date: string; items: string[] }

// Güncellemeden sonraki ilk açılışta yalnızca son sürümün kısa notlarını göster;
// önceki sürümler "Yedek ve arşiv" bölümündeki tam listede durur.
export default function WhatsNewDialog({ onShowAll }: { onShowAll: () => void }) {
  const [notes, setNotes] = useState<Note[]>([])
  const [version, setVersion] = useState('')

  useEffect(() => {
    fetch('/api/app/whats-new').then((response) => response.json()).then((data) => {
      if (data.show) { setNotes(data.notes); setVersion(data.current_version) }
    }).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!notes.length) return
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') close() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  if (!notes.length) return null
  const latest = notes.find((note) => note.version === version) ?? notes[0]
  const olderCount = notes.length - 1
  function close() {
    void fetch('/api/app/whats-new/seen', { method: 'POST' }).catch(() => undefined)
    setNotes([])
  }
  return <div className="whats-new-backdrop" role="dialog" aria-modal="true" aria-labelledby="whats-new-title" data-testid="whats-new-dialog">
    <div className="whats-new-card">
      <h2 id="whats-new-title">Sürüm {latest.version} ile gelenler</h2>
      <ul className="whats-new-items" data-testid="whats-new-items">{latest.items.map((item) => <li key={item}>{item}</li>)}</ul>
      <p>Verilerin korunarak güncellendi; güncelleme öncesi güvenlik yedeği Yedek ve arşiv bölümünde.</p>
      <div className="whats-new-actions">
        <button type="button" data-testid="whats-new-close" onClick={close}>Tamam, başlayalım</button>
        <button type="button" className="whats-new-all" data-testid="whats-new-all" onClick={() => { close(); onShowAll() }}>
          {olderCount > 0 ? `Önceki ${olderCount} sürümün yeniliklerini gör` : 'Tüm sürüm notlarını gör'}
        </button>
      </div>
    </div>
  </div>
}
