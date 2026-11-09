import { useState } from 'react'

type Room = { classroom_id: string; classroom_name: string }
type Candidate = { candidate_id: string; run_id: string; pinned_classroom_ids?: string[] }
type Change = { participant_id: string; school_number: string; name: string; class: string; seat_number: number | null; kind: 'left' | 'changed'; changes: { field: string; label: string; old: string | null; new: string | null }[] }
type Organization = { id: string; name: string; status: 'draft' | 'completed'; archived_at: string | null; selected_candidate_id: string | null; room_selections: Room[] }

type Props = {
  organization: Organization
  candidates: Candidate[]
  readOnly: boolean
  yearReadOnly: boolean
  onReload: () => void
}

async function post(url: string, body: unknown) {
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error ?? 'İşlem tamamlanamadı.')
  return data
}

function PinnedRedistribution({ organization, candidates, onReload }: Props) {
  const [pinned, setPinned] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const base = candidates.find((item) => item.candidate_id === organization.selected_candidate_id) ?? candidates[candidates.length - 1]
  if (!base || organization.room_selections.length < 2) return null
  async function run() {
    setBusy(true); setError('')
    try {
      await post(`/api/exam-organizations/${encodeURIComponent(organization.id)}/distribution-candidates`, { run_id: base.run_id, base_candidate_id: base.candidate_id, pinned_classroom_ids: pinned })
      setPinned([]); onReload()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Yeniden dağıtım yapılamadı.') } finally { setBusy(false) }
  }
  return <div className="lifecycle-block" data-testid={`pinned-redistribution-${organization.id}`}>
    <strong>Derslik sabitleyerek yeniden dağıt</strong>
    <small>Beğendiğin dersliklerdeki yerleşim aynen korunur; diğer derslikler yeniden optimize edilir. Kaynak aday değişmez.</small>
    <div className="lifecycle-chips">{organization.room_selections.map((room) => <label key={room.classroom_id} className={pinned.includes(room.classroom_id) ? 'selected' : ''}><input type="checkbox" data-testid={`pin-room-${room.classroom_id}`} checked={pinned.includes(room.classroom_id)} onChange={(event) => setPinned((current) => event.target.checked ? [...current, room.classroom_id] : current.filter((id) => id !== room.classroom_id))} />{room.classroom_name}</label>)}</div>
    {error && <p className="exam-error" role="alert">{error}</p>}
    <button type="button" data-testid={`pinned-redistribute-btn-${organization.id}`} disabled={busy || !pinned.length || pinned.length === organization.room_selections.length} onClick={() => void run()}>{busy ? 'Hesaplanıyor…' : `${pinned.length} dersliği sabitle · kalanları yeniden dağıt`}</button>
  </div>
}

function StudentChanges({ organization, readOnly, yearReadOnly, onReload }: Props) {
  const [changes, setChanges] = useState<Change[] | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const canApply = !readOnly && !yearReadOnly && !organization.archived_at
  async function load() {
    setBusy(true); setError('')
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organization.id)}/student-changes`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Karşılaştırma yapılamadı.')
      setChanges(data.changes); setSelected([])
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Karşılaştırma yapılamadı.') } finally { setBusy(false) }
  }
  async function apply() {
    setBusy(true); setError('')
    try {
      await post(`/api/exam-organizations/${encodeURIComponent(organization.id)}/student-changes/apply`, { confirm: true, participant_ids: selected })
      setChanges(null); onReload()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Değişiklikler uygulanamadı.') } finally { setBusy(false) }
  }
  return <div className="lifecycle-block" data-testid={`student-changes-${organization.id}`}>
    <strong>Güncel öğrenci listesiyle karşılaştır</strong>
    <small>Okul numarası ve ad-soyad birlikte eşleştirilir. Onay vermeden hiçbir öğrenci yerinden çıkarılmaz.</small>
    <button type="button" data-testid={`student-changes-check-${organization.id}`} disabled={busy} onClick={() => void load()}>{busy && !changes ? 'Karşılaştırılıyor…' : 'Karşılaştır'}</button>
    {changes && (changes.length === 0 ? <span className="lifecycle-ok" data-testid={`student-changes-none-${organization.id}`}>Dağıtımdaki öğrenci bilgileri güncel listeyle aynı.</span> : <>
      <ul className="lifecycle-changes">{changes.map((change) => <li key={change.participant_id}><label><input type="checkbox" data-testid={`student-change-${change.participant_id}`} disabled={!canApply} checked={selected.includes(change.participant_id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, change.participant_id] : current.filter((id) => id !== change.participant_id))} /><span><b>{change.class} · {change.name} · {change.school_number}</b>{change.seat_number ? ` · Koltuk ${change.seat_number}` : ' · Bekleyen havuz'}<small>{change.kind === 'left' ? 'Güncel listede bulunmuyor (ayrılmış veya numara başka öğrenciye verilmiş)' : change.changes.map((item) => `${item.label}: ${item.old ?? '—'} → ${item.new ?? '—'}`).join(' · ')}</small></span></label></li>)}</ul>
      {canApply ? <button type="button" data-testid={`student-changes-apply-${organization.id}`} disabled={busy || !selected.length} onClick={() => void apply()}>{selected.length} öğrenciyi güncelle ve bekleyen havuza al</button> : <small>Bu kayıt salt okunur. Değişiklikleri uygulamak için çalışma kopyası oluştur.</small>}
    </>)}
    {error && <p className="exam-error" role="alert">{error}</p>}
  </div>
}

function ArchiveAndCopy({ organization, readOnly, onReload }: Props) {
  const [confirming, setConfirming] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const [name, setName] = useState(`${organization.name} (kopya)`)
  const [examDate, setExamDate] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  async function complete() {
    setBusy(true); setError('')
    try { await post(`/api/exam-organizations/${encodeURIComponent(organization.id)}/complete`, { confirm: true }); onReload() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Sınav tamamlanamadı.') } finally { setBusy(false) }
  }
  async function copy() {
    setBusy(true); setError(''); setMessage('')
    try {
      const data = await post(`/api/exam-organizations/${encodeURIComponent(organization.id)}/copy`, { name, exam_date: examDate })
      setMessage(`Çalışma kopyası güncel eğitim yılında taslak olarak oluşturuldu.${data.skipped_students ? ` ${data.skipped_students} öğrenci güncel listede bulunamadığı için eklenmedi.` : ''}${data.skipped_rooms ? ` ${data.skipped_rooms} derslik için bu yıla ait düzen yok.` : ''}`)
      setCopyOpen(false); onReload()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Kopya oluşturulamadı.') } finally { setBusy(false) }
  }
  return <div className="lifecycle-block" data-testid={`archive-copy-${organization.id}`}>
    <strong>{organization.archived_at ? 'Arşivlenmiş sınav · salt okunur' : 'Sınavı tamamla ve arşivle'}</strong>
    <small>{organization.archived_at ? `Tamamlandı: ${new Date(organization.archived_at).toLocaleString('tr-TR')}. Yerleşim, geçmiş ve son raporlar korunur.` : 'Tamamlanan sınav geçmiş sınavlarda saklanır ve artık düzenlenemez. Silme yapılmaz.'}</small>
    {!organization.archived_at && !readOnly && (confirming ? <div className="lifecycle-row"><span>Sınav yapıldı ve kayıt arşive alınsın mı?</span><button type="button" onClick={() => setConfirming(false)}>Vazgeç</button><button type="button" data-testid={`archive-confirm-${organization.id}`} disabled={busy} onClick={() => void complete()}>Evet, tamamlandı</button></div> : <button type="button" data-testid={`archive-btn-${organization.id}`} onClick={() => setConfirming(true)}>Tamamlandı olarak işaretle</button>)}
    {copyOpen ? <div className="lifecycle-row"><input data-testid={`copy-name-${organization.id}`} maxLength={160} value={name} onChange={(event) => setName(event.target.value)} /><input data-testid={`copy-date-${organization.id}`} type="date" value={examDate} onChange={(event) => setExamDate(event.target.value)} /><button type="button" onClick={() => setCopyOpen(false)}>Vazgeç</button><button type="button" data-testid={`copy-confirm-${organization.id}`} disabled={busy || !name.trim() || !examDate} onClick={() => void copy()}>Kopyayı oluştur</button></div> : <button type="button" data-testid={`copy-btn-${organization.id}`} onClick={() => setCopyOpen(true)}>Yeni çalışma kopyası oluştur</button>}
    {error && <p className="exam-error" role="alert">{error}</p>}{message && <p className="exam-room-success" role="status">{message}</p>}
  </div>
}

export default function ExamLifecyclePanel(props: Props) {
  const { organization, readOnly } = props
  if (organization.status === 'draft') return readOnly ? null : <PinnedRedistribution {...props} />
  return <div className="lifecycle-panel"><StudentChanges {...props} /><ArchiveAndCopy {...props} /></div>
}
