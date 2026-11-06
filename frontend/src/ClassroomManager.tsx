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
  const [blockCount, setBlockCount] = useState('1')
  const [blockSizes, setBlockSizes] = useState<string[]>([''])
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
  const canvasWidth = Math.max(520, 150 + (maxDeskX + 2.5) * 45)
  const canvasHeight = Math.max(160, 100 + (maxDeskY + 1.5) * 45)
  const planRows = selectedLayout
    ? [...new Set(selectedLayout.desks.map((desk) => desk.y))].sort((a, b) => a - b)
    : []
  const planBlocks = selectedLayout
    ? [...new Set(selectedLayout.desks.map((desk) => desk.block_label ?? ''))]
      .map((label) => ({
        label,
        desks: selectedLayout.desks.filter((desk) => (desk.block_label ?? '') === label),
      }))
      .sort((a, b) => (a.desks[0]?.x ?? 0) - (b.desks[0]?.x ?? 0))
    : []
  const selectedLatestVersion = selectedLayout
    ? Math.max(
      ...layouts
        .filter((layout) => layout.name === selectedLayout.layout.name && layout.academic_year_id === selectedLayout.layout.academic_year_id)
        .map((layout) => layout.version),
    )
    : 0
  const selectedIsLatest = selectedLayout?.layout.version === selectedLatestVersion
  const validBlockSizes = blockSizes.length === Number(blockCount)
    && blockSizes.length > 0
    && blockSizes.every((size) => /^\d+$/.test(size) && Number(size) > 0)
  const generatedSeatCount = Number(rowCount) * blockSizes.reduce((total, size) => total + Number(size || 0), 0) * Number(seatsPerDesk)

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
      setBlockCount('1')
      setBlockSizes([''])
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
      const parsedBlocks = blockSizes.map((value) => Number(value))
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

  function changeBlockCount(value: string) {
    setBlockCount(value)
    const count = Number(value)
    if (Number.isInteger(count) && count >= 1 && count <= 8) {
      setBlockSizes((current) => Array.from({ length: count }, (_, index) => current[index] ?? ''))
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
    const x = Math.max(0, Math.round(((event.clientX - bounds.left - dragOffset.x - 70) / 45) * 10) / 10)
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
                  <div className="generator-intro">
                    <strong>Önce sınıfın plan ölçülerini gir</strong>
                    <p><b>Satır</b>, tahtadan arkaya doğru kaç masa dizisi olduğunu söyler. <b>Blok</b>, koridorla ayrılan yan yana masa grubudur. Her blok için bir satırdaki masa sayısını gir.</p>
                  </div>
                  <div className="generator-fields">
                    <label>
                      <span>Satır sayısı</span><small>Önden arkaya</small>
                      <input type="number" min="1" max="40" required value={rowCount} onChange={(event) => setRowCount(event.target.value)} disabled={readOnly || saving} />
                    </label>
                    <label>
                      <span>Blok sayısı</span><small>Koridorla ayrılan gruplar</small>
                      <input type="number" min="1" max="8" required value={blockCount} onChange={(event) => changeBlockCount(event.target.value)} disabled={readOnly || saving} />
                    </label>
                    <label>
                      <span>Her masadaki oturma yeri</span><small>Masalar aynı tipteyse</small>
                      <select required value={seatsPerDesk} onChange={(event) => setSeatsPerDesk(event.target.value)} disabled={readOnly || saving}>
                        <option value="">Oturma biçimi seç</option>
                        <option value="1">Tekli · 1 öğrenci</option>
                        <option value="2">İkili · 2 öğrenci</option>
                        <option value="3">Üçlü · 3 öğrenci</option>
                      </select>
                    </label>
                  </div>
                  <div className="block-count-fields">
                    {blockSizes.map((size, index) => (
                      <label key={index}>
                        <span>Blok {index + 1}</span><small>Bir satırdaki masa sayısı</small>
                        <input
                          type="number"
                          min="1"
                          max="80"
                          required
                          value={size}
                          onChange={(event) => setBlockSizes((values) => values.map((item, itemIndex) => itemIndex === index ? event.target.value : item))}
                          disabled={readOnly || saving}
                        />
                      </label>
                    ))}
                  </div>
                  {Number(rowCount) > 0 && validBlockSizes && Number(seatsPerDesk) > 0 && (
                    <div className="layout-scheme" aria-label="Plan ölçülerinin şeması">
                      <span className="scheme-board">TAHTA / ÖN</span>
                      <div className="scheme-row">
                        {blockSizes.map((size, index) => (
                          <div className="scheme-group" key={index}>
                            {index > 0 && <span className="scheme-aisle">KORİDOR</span>}
                            <div className="scheme-block">
                              <strong>Blok {index + 1}</strong>
                              <span>{size} masa / satır</span>
                              <div className="scheme-desks">
                                {Array.from({ length: Math.min(Number(size), 8) }, (_, deskIndex) => <i key={deskIndex} />)}
                                {Number(size) > 8 && <small>+{Number(size) - 8}</small>}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                      <p>{rowCount} satır × {blockSizes.reduce((total, size) => total + Number(size), 0)} masa / satır × {seatsPerDesk} öğrenci / masa = <b>{generatedSeatCount} oturma yeri</b></p>
                      <small>Bu şema bir satırı gösterir; aynı sıra {rowCount} kez arkaya doğru devam eder.</small>
                    </div>
                  )}
                  <button type="submit" disabled={readOnly || saving || !validBlockSizes || Number(rowCount) < 1 || !seatsPerDesk}>
                    {saving ? 'Oluşturuluyor…' : 'Bu ölçülerle planı oluştur'}
                  </button>
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
                    {planRows.map((rowY, rowIndex) => (
                      <span className="plan-row-label" style={{ top: 50 + rowY * 45 + 13 }} key={rowY}>Satır {rowIndex + 1}</span>
                    ))}
                    {planBlocks.map((block) => {
                      const firstDesk = block.desks.reduce((first, desk) => desk.x < first.x ? desk : first)
                      return <span className="plan-block-label" style={{ left: 70 + firstDesk.x * 45 }} key={block.label}>{block.label || 'Blok'}</span>
                    })}
                    {planRows.flatMap((rowY, rowIndex) => planBlocks.slice(0, -1).flatMap((block, blockIndex) => {
                      const nextBlock = planBlocks[blockIndex + 1]
                      const lastDesk = block.desks.filter((desk) => desk.y === rowY).reduce((last, desk) => !last || desk.x > last.x ? desk : last, null as typeof block.desks[number] | null)
                      const firstDesk = nextBlock.desks.filter((desk) => desk.y === rowY).reduce((first, desk) => !first || desk.x < first.x ? desk : first, null as typeof nextBlock.desks[number] | null)
                      if (!lastDesk || !firstDesk || firstDesk.x - lastDesk.x < 1.1) return []
                      return [<span className="plan-corridor-label" style={{ left: 70 + ((lastDesk.x + firstDesk.x) / 2) * 45, top: 50 + rowY * 45 + 14 }} key={`${rowIndex}-${blockIndex}`}>KORİDOR</span>]
                    }))}
                    {selectedLayout.desks.map((desk) => (
                      <div
                        className={`plan-desk-position ${draggingDeskId === desk.id ? 'dragging' : ''}`}
                        key={desk.id}
                        draggable={editingLayout}
                        style={{ left: 70 + desk.x * 45, top: 50 + desk.y * 45 }}
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
                  <p className="plan-legend"><b>Satır</b>: tahtadan arkaya doğru masa dizisi · <b>Blok</b>: koridorun bir tarafındaki masa grubu · <b>S1-M1</b>: Satır 1, Masa 1 · Koltuk numaraları sınıf genelinde verilir.</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
