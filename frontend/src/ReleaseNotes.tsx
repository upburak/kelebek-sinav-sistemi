import { useEffect, useState } from 'react'

type Note = { version: string; date: string; items: string[] }

// Tüm sürüm notları: açılış penceresi yalnızca son sürümü gösterir, gerisi burada durur.
export default function ReleaseNotes() {
  const [notes, setNotes] = useState<Note[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    fetch('/api/app/release-notes').then((response) => response.json())
      .then((data) => setNotes(data.notes as Note[]))
      .catch(() => setFailed(true))
  }, [])

  return <article className="backup-card release-notes" id="release-notes" data-testid="release-notes" aria-labelledby="release-notes-title">
    <h2 id="release-notes-title">Sürüm notları</h2>
    {failed && <p className="backup-feedback error" role="alert">Sürüm notları yüklenemedi. Sayfayı yenileyip yeniden dene.</p>}
    {!failed && !notes && <p>Sürüm notları yükleniyor…</p>}
    {notes?.map((note) => <section key={note.version} data-testid={`release-note-${note.version}`}>
      <h3>Sürüm {note.version}{note.date ? <small>{new Date(note.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })}</small> : null}</h3>
      <ul>{note.items.map((item) => <li key={item}>{item}</li>)}</ul>
    </section>)}
  </article>
}
