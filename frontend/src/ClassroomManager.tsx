import { FormEvent, useEffect, useState } from 'react'

type Classroom = { id: string; name: string; layout_count: number }
type ClassroomLayout = {
  id: string
  name: string
  version: number
  academic_year_label: string | null
  is_template: boolean
  total_seats: number
  available_seats: number
}

type Props = {
  academicYearId: string | null
  academicYearLabel: string
  readOnly: boolean
  onClose: () => void
}

export default function ClassroomManager({ academicYearId, academicYearLabel, readOnly, onClose }: Props) {
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [selectedClassroomId, setSelectedClassroomId] = useState<string | null>(null)
  const [layouts, setLayouts] = useState<ClassroomLayout[]>([])
  const [classroomName, setClassroomName] = useState('')
  const [layoutName, setLayoutName] = useState('Ana düzen')
  const [isTemplate, setIsTemplate] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const selectedClassroom = classrooms.find((item) => item.id === selectedClassroomId)

  async function loadClassrooms() {
    const response = await fetch('/api/classrooms')
    const data = await response.json()
    if (!response.ok) throw new Error(data.error ?? 'Derslikler yüklenemedi.')
    setClassrooms(data.classrooms as Classroom[])
  }

  async function loadLayouts(classroomId: string) {
    const response = await fetch(`/api/classrooms/${classroomId}/layouts`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.error ?? 'Derslik düzenleri yüklenemedi.')
    setLayouts(data.layouts as ClassroomLayout[])
  }

  useEffect(() => {
    loadClassrooms()
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Derslikler yüklenemedi.'))
      .finally(() => setLoading(false))
  }, [])

  async function addClassroom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const response = await fetch('/api/classrooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: classroomName }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Derslik eklenemedi.')
      setClassroomName('')
      await loadClassrooms()
      setSelectedClassroomId(data.classroom.id as string)
      await loadLayouts(data.classroom.id as string)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Derslik eklenemedi.')
    } finally {
      setSaving(false)
    }
  }

  async function selectClassroom(classroomId: string) {
    setSelectedClassroomId(classroomId)
    setError('')
    try {
      await loadLayouts(classroomId)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Derslik düzenleri yüklenemedi.')
    }
  }

  async function addLayout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClassroomId) return
    setSaving(true)
    setError('')
    try {
      const response = await fetch(`/api/classrooms/${selectedClassroomId}/layouts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: layoutName,
          is_template: isTemplate,
          academic_year_id: isTemplate ? null : academicYearId,
        }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Düzen oluşturulamadı.')
      setLayoutName('Ana düzen')
      await Promise.all([loadLayouts(selectedClassroomId), loadClassrooms()])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Düzen oluşturulamadı.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="classroom-manager" aria-labelledby="classroom-manager-title">
      <div className="classroom-manager-heading">
        <div>
          <span className="eyebrow">DERSLİKLER</span>
          <h2 id="classroom-manager-title">Derslik ve düzen kayıtları</h2>
          <p>Fiziksel dersliği bir kez ekle; yıllara özel düzen veya tekrar kullanılabilir şablon oluştur.</p>
        </div>
        <button className="panel-close" type="button" onClick={onClose}>Kapat</button>
      </div>

      {readOnly && <p className="archive-banner">Arşiv yılı seçili. Bu ekranda kayıt eklenemez.</p>}
      {error && <p className="import-error" role="alert">{error}</p>}

      <form className="room-create-form" onSubmit={addClassroom}>
        <label htmlFor="new-classroom-name">Yeni derslik adı</label>
        <div>
          <input
            id="new-classroom-name"
            value={classroomName}
            onChange={(event) => setClassroomName(event.target.value)}
            placeholder="Örneğin: 9/A Salonu"
            maxLength={120}
            required
            disabled={readOnly || saving}
          />
          <button type="submit" disabled={readOnly || saving}>{saving ? 'Kaydediliyor…' : 'Derslik ekle'}</button>
        </div>
      </form>

      {loading ? <p>Derslikler yükleniyor…</p> : classrooms.length === 0 ? (
        <p className="empty-classrooms">Henüz derslik eklenmedi.</p>
      ) : (
        <div className="classroom-list">
          {classrooms.map((classroom) => (
            <button
              className={`classroom-list-item ${selectedClassroomId === classroom.id ? 'selected' : ''}`}
              type="button"
              key={classroom.id}
              onClick={() => selectClassroom(classroom.id)}
            >
              <span>{classroom.name}</span>
              <small>{classroom.layout_count} düzen</small>
            </button>
          ))}
        </div>
      )}

      {selectedClassroom && (
        <div className="classroom-layout-panel">
          <h3>{selectedClassroom.name} · Düzenler</h3>
          {!readOnly && (
            <form className="layout-create-form" onSubmit={addLayout}>
              <label htmlFor="layout-name">Düzen adı</label>
              <input
                id="layout-name"
                value={layoutName}
                onChange={(event) => setLayoutName(event.target.value)}
                maxLength={120}
                required
                disabled={saving}
              />
              <label className="template-check">
                <input type="checkbox" checked={isTemplate} onChange={(event) => setIsTemplate(event.target.checked)} disabled={saving} />
                Tekrar kullanılabilir şablon
              </label>
              {!isTemplate && <span className="layout-year-hint">{academicYearLabel} yılına kaydedilecek</span>}
              <button type="submit" disabled={saving || (!isTemplate && !academicYearId)}>
                {saving ? 'Oluşturuluyor…' : 'Boş düzen oluştur'}
              </button>
            </form>
          )}
          {layouts.length === 0 ? <p>Bu derslik için henüz düzen yok.</p> : (
            <ul className="layout-list">
              {layouts.map((layout) => (
                <li key={layout.id}>
                  <span><strong>{layout.name} · v{layout.version}</strong><small>{layout.is_template ? 'Şablon' : layout.academic_year_label}</small></span>
                  <small>{layout.available_seats}/{layout.total_seats} kullanılabilir oturma yeri</small>
                </li>
              ))}
            </ul>
          )}
          <p className="privacy-note">Bu adım boş düzen kaydı oluşturur. Masa ve oturma yeri çizim aracı sonraki geliştirme adımıdır.</p>
        </div>
      )}
    </section>
  )
}
