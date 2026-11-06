import { useEffect, useState, type FormEvent } from 'react'

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
type Desk = {
  id: string
  label: string
  block_label: string | null
  x: number
  y: number
  seats: { id: string; seat_number: number; seat_index: number; is_available: boolean }[]
}
type LayoutDetail = { layout: ClassroomLayout; desks: Desk[] }

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
  const [selectedLayout, setSelectedLayout] = useState<LayoutDetail | null>(null)
  const [classroomName, setClassroomName] = useState('')
  const [layoutName, setLayoutName] = useState('Ana düzen')
  const [rowCount, setRowCount] = useState('')
  const [blockSizes, setBlockSizes] = useState('')
  const [seatsPerDesk, setSeatsPerDesk] = useState('')
  const [isTemplate, setIsTemplate] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const selectedClassroom = classrooms.find((item) => item.id === selectedClassroomId)
  const planRows = selectedLayout
    ? [...new Set(selectedLayout.desks.map((desk) => desk.y))].sort((a, b) => a - b).map((y) => {
      const rowDesks = selectedLayout.desks.filter((desk) => desk.y === y)
      const blocks = [...new Set(rowDesks.map((desk) => desk.block_label ?? ''))].map((blockLabel) => ({
        label: blockLabel,
        desks: rowDesks.filter((desk) => (desk.block_label ?? '') === blockLabel),
      }))
      return { y, blocks }
    })
    : []

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

  async function openLayout(classroomId: string, layoutId: string) {
    setError('')
    try {
      const response = await fetch(`/api/classrooms/${classroomId}/layouts/${layoutId}`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Düzen açılamadı.')
      setSelectedLayout(data as LayoutDetail)
      setRowCount('')
      setBlockSizes('')
      setSeatsPerDesk('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Düzen açılamadı.')
    }
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
      setSelectedLayout(null)
      await loadLayouts(data.classroom.id as string)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Derslik eklenemedi.')
    } finally {
      setSaving(false)
    }
  }

  async function selectClassroom(classroomId: string) {
    setSelectedClassroomId(classroomId)
    setSelectedLayout(null)
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
      await openLayout(selectedClassroomId, data.layout.id as string)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Düzen oluşturulamadı.')
    } finally {
      setSaving(false)
    }
  }

  async function generateLayout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClassroomId || !selectedLayout) return
    setSaving(true)
    setError('')
    try {
      const parsedBlocks = blockSizes.split(',').map((value) => Number(value.trim()))
      const response = await fetch(
        `/api/classrooms/${selectedClassroomId}/layouts/${selectedLayout.layout.id}/generate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rows: Number(rowCount),
            block_sizes: parsedBlocks,
            seats_per_desk: Number(seatsPerDesk),
          }),
        },
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Başlangıç düzeni oluşturulamadı.')
      await Promise.all([loadLayouts(selectedClassroomId), openLayout(selectedClassroomId, selectedLayout.layout.id)])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Başlangıç düzeni oluşturulamadı.')
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
                  <span className="layout-actions">
                    <small>{layout.available_seats}/{layout.total_seats} kullanılabilir oturma yeri</small>
                    <button type="button" className="layout-open" onClick={() => openLayout(selectedClassroom.id, layout.id)}>Düzeni aç</button>
                  </span>
                </li>
              ))}
            </ul>
          )}
          {selectedLayout && (
            <div className="layout-editor">
              <h4>{selectedLayout.layout.name} · v{selectedLayout.layout.version}</h4>
              {selectedLayout.desks.length === 0 ? (
                <form className="layout-generator" onSubmit={generateLayout}>
                  <p>Fiziksel sınıfa göre satırları ve blok başına masa sayılarını gir.</p>
                  <label>Satır sayısı<input type="number" min="1" max="40" required value={rowCount} onChange={(event) => setRowCount(event.target.value)} disabled={readOnly || saving} /></label>
                  <label>Her bloktaki masa sayısı<input inputMode="numeric" placeholder="Örneğin: 6, 6, 6" required value={blockSizes} onChange={(event) => setBlockSizes(event.target.value)} disabled={readOnly || saving} /></label>
                  <label>Masa başına oturma yeri<select required value={seatsPerDesk} onChange={(event) => setSeatsPerDesk(event.target.value)} disabled={readOnly || saving}>
                    <option value="">Seç</option><option value="1">Tekli</option><option value="2">İkili</option><option value="3">Üçlü</option>
                  </select></label>
                  <button type="submit" disabled={readOnly || saving}>{saving ? 'Oluşturuluyor…' : 'Başlangıç planını oluştur'}</button>
                  <small>Örneğin 6, 6, 6 üç blok ve aralarında koridor boşluğu oluşturur.</small>
                </form>
              ) : (
                <div className="layout-plan" aria-label="Derslik oturma planı">
                  <div className="board-label">TAHTA</div>
                  {planRows.map((row) => (
                    <div className="plan-row" key={row.y}>
                      {row.blocks.map((block) => (
                        <div className="plan-block" key={`${row.y}-${block.label}`}>
                          <span className="plan-block-label">{block.label}</span>
                          <div className="plan-desks">
                            {block.desks.map((desk) => (
                              <div className="plan-desk" key={desk.id}>
                                <small>{desk.label}</small>
                                <div className="plan-seats">
                                  {desk.seats.map((seat) => (
                                    <span className={seat.is_available ? '' : 'unavailable'} key={seat.id}>{seat.seat_number}</span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                  <p className="privacy-note">Masa taşıma ve oturma yeri kapatma kontrolleri sıradaki düzenleme adımında eklenecek.</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
