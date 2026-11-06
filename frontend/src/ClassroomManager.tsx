import { useEffect, useState, type DragEvent, type FormEvent } from 'react'

type Classroom = { id: string; name: string; layout_count: number }
type ClassroomLayout = {
  id: string
  name: string
  version: number
  academic_year_id: string | null
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
  const [editingLayout, setEditingLayout] = useState(false)
  const [draggingDeskId, setDraggingDeskId] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [isTemplate, setIsTemplate] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const selectedClassroom = classrooms.find((item) => item.id === selectedClassroomId)
  const maxDeskX = selectedLayout?.desks.length
    ? Math.max(...selectedLayout.desks.map((desk) => desk.x))
    : 0
  const maxDeskY = selectedLayout?.desks.length
    ? Math.max(...selectedLayout.desks.map((desk) => desk.y))
    : 0
  const canvasWidth = Math.max(500, 100 + (maxDeskX + 2.5) * 45)
  const canvasHeight = Math.max(160, 100 + (maxDeskY + 1.5) * 45)
  const selectedLatestVersion = selectedLayout
    ? Math.max(
      ...layouts
        .filter((layout) => layout.name === selectedLayout.layout.name && layout.academic_year_id === selectedLayout.layout.academic_year_id)
        .map((layout) => layout.version),
    )
    : 0
  const selectedIsLatest = selectedLayout?.layout.version === selectedLatestVersion

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
      setEditingLayout(false)
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
    setEditingLayout(false)
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

  async function beginLayoutEdit() {
    if (!selectedClassroomId || !selectedLayout) return
    setSaving(true)
    setError('')
    try {
      const response = await fetch(
        `/api/classrooms/${selectedClassroomId}/layouts/${selectedLayout.layout.id}/versions`,
        { method: 'POST' },
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Yeni düzen sürümü oluşturulamadı.')
      setSelectedLayout(data as LayoutDetail)
      setEditingLayout(true)
      await loadLayouts(selectedClassroomId)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Yeni düzen sürümü oluşturulamadı.')
    } finally {
      setSaving(false)
    }
  }

  async function moveDesk(deskId: string, x: number, y: number) {
    if (!selectedClassroomId || !selectedLayout || !editingLayout) return
    try {
      const response = await fetch(
        `/api/classrooms/${selectedClassroomId}/layouts/${selectedLayout.layout.id}/desks/${deskId}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ x, y }),
        },
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Masa taşınamadı.')
      await openLayout(selectedClassroomId, selectedLayout.layout.id)
      setEditingLayout(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Masa taşınamadı.')
    }
  }

  async function toggleSeatAvailability(seat: Desk['seats'][number]) {
    if (!selectedClassroomId || !selectedLayout || !editingLayout) return
    try {
      const response = await fetch(
        `/api/classrooms/${selectedClassroomId}/layouts/${selectedLayout.layout.id}/seats/${seat.id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            is_available: !seat.is_available,
            unavailable_reason: seat.is_available ? 'Kullanım dışı' : '',
          }),
        },
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Oturma yeri durumu değiştirilemedi.')
      setSelectedLayout((current) => current ? {
        ...current,
        desks: current.desks.map((desk) => ({
          ...desk,
          seats: desk.seats.map((item) => item.id === seat.id ? { ...item, is_available: data.seat.is_available } : item),
        })),
        layout: {
          ...current.layout,
          available_seats: current.layout.available_seats + (data.seat.is_available ? 1 : -1),
        },
      } : current)
      await loadLayouts(selectedClassroomId)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Oturma yeri durumu değiştirilemedi.')
    }
  }

  function dropDesk(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    if (!selectedLayout || !editingLayout) return
    const deskId = event.dataTransfer.getData('text/plain') || draggingDeskId
    if (!deskId) return
    const bounds = event.currentTarget.getBoundingClientRect()
    const x = Math.max(0, Math.round(((event.clientX - bounds.left - dragOffset.x - 20) / 45) * 10) / 10)
    const y = Math.max(0, Math.round(((event.clientY - bounds.top - dragOffset.y - 50) / 45) * 10) / 10)
    setDraggingDeskId(null)
    void moveDesk(deskId, x, y)
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
              <div className="layout-editor-heading">
                <h4>{selectedLayout.layout.name} · v{selectedLayout.layout.version}</h4>
                {selectedLayout.desks.length > 0 && !readOnly && selectedIsLatest && (
                  <button
                    type="button"
                    className="layout-edit-button"
                    disabled={saving}
                    onClick={() => editingLayout ? setEditingLayout(false) : void beginLayoutEdit()}
                  >
                    {editingLayout ? 'Düzenlemeyi bitir' : 'Kopyala ve düzenle'}
                  </button>
                )}
              </div>
              {!selectedIsLatest && <p className="privacy-note">Bu eski sürüm salt okunur; düzenleme için en son sürümü aç.</p>}
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
                  <p className="privacy-note">
                    {editingLayout
                      ? 'Masaları sürükleyerek taşı. Koltuğa tıklayarak kullanıma kapat veya yeniden aç; değişiklikler anında kaydedilir.'
                      : 'Önce “Kopyala ve düzenle” ile yeni sürüm aç. Önceki düzen korunur.'}
                  </p>
                  <div
                    className={`layout-canvas ${editingLayout ? 'editable' : ''}`}
                    style={{ width: canvasWidth, height: canvasHeight }}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={dropDesk}
                  >
                    <div className="board-label" style={{ left: canvasWidth / 2 - 70 }}>TAHTA</div>
                    {[...new Set(selectedLayout.desks.map((desk) => desk.block_label ?? ''))].map((blockLabel) => {
                      const firstDesk = selectedLayout.desks.find((desk) => (desk.block_label ?? '') === blockLabel)
                      if (!firstDesk) return null
                      return <span className="plan-block-label" style={{ left: 20 + firstDesk.x * 45 }} key={blockLabel}>{blockLabel}</span>
                    })}
                    {selectedLayout.desks.map((desk) => (
                      <div
                        className={`plan-desk-position ${draggingDeskId === desk.id ? 'dragging' : ''}`}
                        key={desk.id}
                        draggable={editingLayout}
                        style={{ left: 20 + desk.x * 45, top: 50 + desk.y * 45 }}
                        onDragStart={(event) => {
                          setDraggingDeskId(desk.id)
                          const bounds = event.currentTarget.getBoundingClientRect()
                          setDragOffset({ x: event.clientX - bounds.left, y: event.clientY - bounds.top })
                          event.dataTransfer.setData('text/plain', desk.id)
                          event.dataTransfer.effectAllowed = 'move'
                        }}
                        onDragEnd={() => setDraggingDeskId(null)}
                      >
                        <small>{desk.label}</small>
                        <div className="plan-seats">
                          {desk.seats.map((seat) => (
                            <button
                              className={`plan-seat ${seat.is_available ? '' : 'unavailable'}`}
                              type="button"
                              key={seat.id}
                              disabled={!editingLayout}
                              aria-label={`Koltuk ${seat.seat_number}${seat.is_available ? ' kullanılabilir' : ' kullanım dışı'}`}
                              onClick={() => void toggleSeatAvailability(seat)}
                            >
                              {seat.seat_number}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
