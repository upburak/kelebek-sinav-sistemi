import { bulkDelete } from './bulkDelete'
import { useEffect, useRef, useState, type DragEvent, type FormEvent } from 'react'

// Plan tuvalinde ızgaranın başladığı nokta; üstte sütun, solda satır tutamakları için yer bırakır.
const PLAN_LEFT = 86
const PLAN_TOP = 84
const CELL = 45
type StructureOp =
  | { op: 'add_row' | 'add_column' }
  | { op: 'move_row' | 'move_column'; from: number; to: number }
  | { op: 'set_desk_seats'; label: string; count: number }
  | { op: 'delete_desk'; label: string }
import { notify } from './notify'

type Classroom = { id: string; name: string; layout_count: number; seat_count?: number; is_closed?: boolean; exam_count?: number; can_delete?: boolean }
type ClassroomLayout = {
  id: string
  name: string
  version: number
  academic_year_id: string | null
  academic_year_label: string | null
  is_template: boolean
  is_active?: boolean
  exam_count?: number
  can_delete?: boolean
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
  const [renamingClassroom, setRenamingClassroom] = useState(false)
  const [classroomNameDraft, setClassroomNameDraft] = useState('')
  const [layoutName, setLayoutName] = useState('Ana düzen')
  const [columnCount, setColumnCount] = useState('3')
  const [columnLengths, setColumnLengths] = useState<string[]>(['5', '6', '6'])
  const [cellSeats, setCellSeats] = useState<string[][]>([Array(5).fill('2'), Array(6).fill('2'), Array(6).fill('2')])
  const [aisleAfter, setAisleAfter] = useState<boolean[]>([false, false])
  const [editingLayout, setEditingLayout] = useState(false)
  const [draggingDeskId, setDraggingDeskId] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  // Sürüklenen satır ya da sütun tutamağı; masa sürüklemesinden ayrı tutulur.
  const [draggingLine, setDraggingLine] = useState<{ axis: 'row' | 'column'; value: number } | null>(null)
  const [menuDeskId, setMenuDeskId] = useState<string | null>(null)
  const [isTemplate, setIsTemplate] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  // Dersliğin aktif planına ait kullanım bilgisi; plan yoksa null.
  const [planInfo, setPlanInfo] = useState<{ layoutId: string; examCount: number; otherLayoutCount: number } | null>(null)
  const [planLoaded, setPlanLoaded] = useState(false)
  // Taslak sınav / kopya bilgisi düzenleme oturumunda bir kez duyurulur.
  const editAnnounced = useRef(false)
  const editChanged = useRef(false)
  const editBusy = useRef(false)
  const selectedClassroom = classrooms.find((item) => item.id === selectedClassroomId)
  const maxDeskX = selectedLayout?.desks.length
    ? Math.max(...selectedLayout.desks.map((desk) => desk.x))
    : 0
  const maxDeskY = selectedLayout?.desks.length
    ? Math.max(...selectedLayout.desks.map((desk) => desk.y))
    : 0
  // Düzenlerken sağda ve altta iki hücrelik boşluk bırakılır; satır ve sütun oraya sürüklenebilir.
  const editRoom = editingLayout ? CELL * 4 : 0
  const canvasWidth = Math.max(520, PLAN_LEFT + 170 + (maxDeskX + 2.5) * CELL + editRoom)
  const canvasHeight = Math.max(190, PLAN_TOP + 80 + (maxDeskY + 1.5) * CELL + editRoom)
  const planColumns = selectedLayout
    ? [...new Set(selectedLayout.desks.map((desk) => desk.x))].sort((a, b) => a - b)
    : []
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
  const viewingActivePlan = Boolean(selectedLayout && planInfo && selectedLayout.layout.id === planInfo.layoutId)
  const validGrid = columnLengths.length === Number(columnCount)
    && cellSeats.length === Number(columnCount)
    && columnLengths.every((length, index) => /^\d+$/.test(length) && Number(length) > 0 && cellSeats[index]?.length === Number(length))
    && cellSeats.flat().every((count) => ['1', '2', '3'].includes(count))
  const generatedSeatCount = cellSeats.flat().reduce((total, count) => total + Number(count || 0), 0)

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
      setColumnCount('3')
      setColumnLengths(['5', '6', '6'])
      setCellSeats([Array(5).fill('2'), Array(6).fill('2'), Array(6).fill('2')])
      setAisleAfter([false, false])
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
    setPlanInfo(null)
    setPlanLoaded(false)
    try {
      await Promise.all([loadLayouts(classroomId), loadPlan(classroomId)])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Derslik planı yüklenemedi.')
    }
  }

  /** Dersliğin aktif planını doğrudan aç; arada plan listesi gösterilmez. */
  async function loadPlan(classroomId: string) {
    if (!academicYearId) { setPlanLoaded(true); return }
    const response = await fetch(`/api/classrooms/${classroomId}/plan?academic_year_id=${encodeURIComponent(academicYearId)}`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.error ?? 'Derslik planı yüklenemedi.')
    if (data.plan) {
      setSelectedLayout({ layout: data.plan.layout, desks: data.plan.desks } as LayoutDetail)
      setPlanInfo({ layoutId: data.plan.layout.id as string, examCount: data.plan.exam_count as number, otherLayoutCount: data.other_layout_count as number })
    } else {
      setSelectedLayout(null)
      setPlanInfo(null)
    }
    setPlanLoaded(true)
  }

  /** Plansız derslik için ilk planı oluştur; ölçü formu açılır. */
  async function createFirstPlan() {
    if (!selectedClassroomId || !academicYearId) return
    setSaving(true)
    setError('')
    try {
      const response = await fetch(`/api/classrooms/${selectedClassroomId}/layouts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Sınıf planı', is_template: false, academic_year_id: academicYearId }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Plan oluşturulamadı.')
      await Promise.all([loadLayouts(selectedClassroomId), loadClassrooms(), loadPlan(selectedClassroomId)])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Plan oluşturulamadı.')
    } finally {
      setSaving(false)
    }
  }

  /** Düzenleme sonucunu duyur: kopyalandıysa ya da taslak sınavları etkiliyorsa oturumda bir kez. */
  function announceEdit(data: { copied?: boolean; affected_draft_exam_count?: number }) {
    editChanged.current = true
    if (editAnnounced.current) return
    const drafts = data.affected_draft_exam_count ?? 0
    if (!data.copied && !drafts) return
    editAnnounced.current = true
    notify.success([
      data.copied ? 'Kesinleşmiş sınavların krokisi korundu; değişiklik planın yeni hâline yazılıyor.' : '',
      drafts ? `${drafts} taslak sınav yeni planı kullanacak; o sınavları yeniden dağıtman gerekir.` : '',
    ].filter(Boolean).join(' '))
  }

  function toggleEditing() {
    if (editingLayout) {
      setEditingLayout(false)
      setMenuDeskId(null)
      if (editChanged.current) notify.success('Plan kaydedildi.')
    } else {
      editAnnounced.current = false
      editChanged.current = false
      setEditingLayout(true)
    }
  }

  async function saveClassroomName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClassroomId) return
    setSaving(true)
    setError('')
    try {
      const response = await fetch(`/api/classrooms/${selectedClassroomId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: classroomNameDraft }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Derslik adı değiştirilemedi.')
      setRenamingClassroom(false)
      notify.success('Derslik adı kaydedildi.')
      await loadClassrooms()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Derslik adı değiştirilemedi.')
    } finally {
      setSaving(false)
    }
  }

  async function activateLayout(classroomId: string, layout: ClassroomLayout) {
    setSaving(true)
    setError('')
    try {
      const response = await fetch(`/api/classrooms/${classroomId}/layouts/${layout.id}/activate`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Düzen aktif yapılamadı.')
      setEditingLayout(false)
      await Promise.all([loadLayouts(classroomId), loadClassrooms(), loadPlan(classroomId)])
      const drafts = (data.affected_draft_exam_count as number | undefined) ?? 0
      notify.success(`“${layout.name}” dersliğin aktif planı oldu.${drafts ? ` ${drafts} taslak sınav bu planı kullanacak; o sınavları yeniden dağıtman gerekir.` : ''}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Düzen aktif yapılamadı.')
    } finally {
      setSaving(false)
    }
  }

  async function deleteLayout(classroomId: string, layout: ClassroomLayout) {
    const warning = layout.is_active
      ? `“${layout.name} · v${layout.version}” şu an aktif düzen. Silinirse kalan en yeni düzen aktif olur. Silinsin mi?`
      : `“${layout.name} · v${layout.version}” düzeni masaları ve koltuklarıyla birlikte silinsin mi? Bu işlem geri alınamaz.`
    if (!window.confirm(warning)) return
    setSaving(true)
    setError('')
    try {
      const response = await fetch(`/api/classrooms/${classroomId}/layouts/${layout.id}`, { method: 'DELETE' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Düzen silinemedi.')
      setEditingLayout(false)
      // Aktif plan silindiyse kalan plan aktif olur; görünüm onu göstermeli.
      await Promise.all([loadLayouts(classroomId), loadClassrooms(), loadPlan(classroomId)])
      notify.success(`“${layout.name}” planı silindi.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Düzen silinemedi.')
    } finally {
      setSaving(false)
    }
  }

  async function deleteClassroom(classroom: Classroom) {
    if (classroom.can_delete === false) return
    const plans = classroom.layout_count > 0 ? ` Oturma planı da silinir (${classroom.seat_count ?? 0} koltuk).` : ''
    if (!window.confirm(`“${classroom.name}” dersliği silinsin mi?${plans} Bu işlem geri alınamaz.`)) return
    setSaving(true)
    setError('')
    try {
      const response = await fetch(`/api/classrooms/${classroom.id}`, { method: 'DELETE' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Derslik silinemedi.')
      if (selectedClassroomId === classroom.id) {
        setSelectedClassroomId(null)
        setSelectedLayout(null)
        setLayouts([])
        setPlanInfo(null)
        setEditingLayout(false)
      }
      await loadClassrooms()
      notify.success(`“${classroom.name}” silindi.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Derslik silinemedi.')
    } finally {
      setSaving(false)
    }
  }

  /** Dersliği kapat ya da yeniden aç. Kapalı derslik yeni sınavlarda seçilemez. */
  async function setClassroomClosed(classroom: Classroom, closed: boolean) {
    setSaving(true)
    setError('')
    try {
      const response = await fetch(`/api/classrooms/${classroom.id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_closed: closed }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Derslik durumu değiştirilemedi.')
      await loadClassrooms()
      notify.success(closed
        ? `“${classroom.name}” kapatıldı; yeni sınavlarda seçilemez. Eski sınavlardaki yeri korunur.`
        : `“${classroom.name}” yeniden açıldı.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Derslik durumu değiştirilemedi.')
    } finally {
      setSaving(false)
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
      const response = await fetch(
        `/api/classrooms/${selectedClassroomId}/layouts/${selectedLayout.layout.id}/generate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            columns: Number(columnCount),
            column_lengths: columnLengths.map(Number),
            cell_seats: cellSeats.map((column) => column.map(Number)),
            aisle_after: aisleAfter,
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

  function changeColumnCount(value: string) {
    setColumnCount(value)
    const count = Number(value)
    if (Number.isInteger(count) && count >= 1 && count <= 12) {
      setColumnLengths((current) => Array.from({ length: count }, (_, index) => current[index] ?? '5'))
      setCellSeats((current) => Array.from({ length: count }, (_, index) => current[index] ?? Array(5).fill('2')))
      setAisleAfter((current) => Array.from({ length: Math.max(0, count - 1) }, (_, index) => current[index] ?? false))
    }
  }

  function changeColumnLength(columnIndex: number, value: string) {
    setColumnLengths((current) => current.map((length, index) => index === columnIndex ? value : length))
    const count = Number(value)
    if (Number.isInteger(count) && count >= 1 && count <= 40) {
      setCellSeats((current) => current.map((column, index) => index === columnIndex
        ? Array.from({ length: count }, (_, cellIndex) => column[cellIndex] ?? '2')
        : column))
    }
  }

  async function moveDesk(deskId: string, x: number, y: number) {
    if (!selectedClassroomId || !selectedLayout || !editingLayout || editBusy.current) return
    editBusy.current = true
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
      announceEdit(data)
      // Plan kopyalandıysa bundan sonra kopya (dersliğin yeni aktif planı) düzenlenir.
      await Promise.all([loadPlan(selectedClassroomId), loadLayouts(selectedClassroomId), loadClassrooms()])
      setEditingLayout(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Masa taşınamadı.')
    } finally {
      editBusy.current = false
    }
  }

  async function toggleSeatAvailability(seat: Desk['seats'][number]) {
    // Önceki kayıt bitmeden gelen tıklama eski plan kimliğiyle giderdi (plan kopyalanmış olabilir).
    if (!selectedClassroomId || !selectedLayout || !editingLayout || editBusy.current) return
    editBusy.current = true
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
      announceEdit(data)
      await Promise.all([loadPlan(selectedClassroomId), loadLayouts(selectedClassroomId), loadClassrooms()])
      setEditingLayout(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Oturma yeri durumu değiştirilemedi.')
    } finally {
      editBusy.current = false
    }
  }

  /** Planın yapısını değiştir: satır/sütun ekle ya da taşı, masayı tekli/çiftli yap, masayı sil. */
  async function structureOp(operation: StructureOp) {
    if (!selectedClassroomId || !selectedLayout || !editingLayout || editBusy.current) return
    editBusy.current = true
    setMenuDeskId(null)
    setError('')
    try {
      const response = await fetch(
        `/api/classrooms/${selectedClassroomId}/layouts/${selectedLayout.layout.id}/structure`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(operation) },
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Plan değiştirilemedi.')
      announceEdit(data)
      await Promise.all([loadPlan(selectedClassroomId), loadLayouts(selectedClassroomId), loadClassrooms()])
      setEditingLayout(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Plan değiştirilemedi.')
    } finally {
      editBusy.current = false
    }
  }

  function dropOnPlan(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    if (!selectedLayout || !editingLayout) return
    const bounds = event.currentTarget.getBoundingClientRect()
    const cellX = Math.max(0, Math.round((event.clientX - bounds.left - dragOffset.x - PLAN_LEFT) / (CELL * 2)) * 2)
    const cellY = Math.max(0, Math.round((event.clientY - bounds.top - dragOffset.y - PLAN_TOP) / (CELL * 2)) * 2)
    if (draggingLine) {
      const line = draggingLine
      setDraggingLine(null)
      const target = line.axis === 'row' ? cellY : cellX
      if (target !== line.value) void structureOp({ op: line.axis === 'row' ? 'move_row' : 'move_column', from: line.value, to: target })
      return
    }
    const deskId = event.dataTransfer.getData('text/plain') || draggingDeskId
    if (!deskId) return
    setDraggingDeskId(null)
    void moveDesk(deskId, cellX, cellY)
  }

  useEffect(() => {
    if (!menuDeskId) return
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setMenuDeskId(null) }
    const onClick = (event: MouseEvent) => {
      if (!(event.target as HTMLElement).closest('.plan-desk-menu, .plan-desk-menu-btn')) setMenuDeskId(null)
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('mousedown', onClick)
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('mousedown', onClick) }
  }, [menuDeskId])

  return (
    <section className="classroom-manager" aria-labelledby="classroom-manager-title">
      <div className="classroom-manager-heading">
        <div>
          <span className="eyebrow">DERSLİKLER</span>
          <h2 id="classroom-manager-title">Derslikler ve oturma planları</h2>
          <p>Bir dersliğe tıkla; oturma planı açılır. Planı gerçek sınıfa göre düzenleyebilirsin.</p>
        </div>
        <div className="classroom-heading-actions">
          {!readOnly && classrooms.length > 0 && academicYearId && <button type="button" className="bulk-delete-button" data-testid="bulk-delete-classrooms" onClick={() => void bulkDelete('classrooms', academicYearId).then(async (done) => {
            if (!done) return
            setSelectedClassroomId(null); setSelectedLayout(null); setLayouts([]); setPlanInfo(null); setEditingLayout(false)
            await loadClassrooms()
          })}>Tüm derslikleri sil</button>}
          <button className="panel-close" type="button" onClick={onClose}>Kapat</button>
        </div>
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
            <div className={`classroom-list-item ${selectedClassroomId === classroom.id ? 'selected' : ''} ${classroom.is_closed ? 'closed' : ''}`} key={classroom.id} data-testid={`classroom-card-${classroom.id}`}>
              <button type="button" className="classroom-list-select" aria-pressed={selectedClassroomId === classroom.id} onClick={() => void selectClassroom(classroom.id)}>
                <span>{classroom.name}</span>
                <small>{classroom.layout_count === 0 ? 'Plan yok' : `${classroom.seat_count ?? 0} koltuk`}{classroom.is_closed ? ' · Kapalı' : ''}</small>
              </button>
            </div>
          ))}
        </div>
      )}

      {selectedClassroom && (
        <div className="classroom-layout-panel">
          <div className="classroom-panel-title">
            <h3>{selectedClassroom.name}{selectedClassroom.is_closed && <span className="classroom-closed-tag" data-testid="classroom-closed-tag">Kapalı</span>}</h3>
            {!readOnly && <div className="classroom-panel-actions">
              <button type="button" disabled={saving} onClick={() => {
                setClassroomNameDraft(selectedClassroom.name)
                setRenamingClassroom((open) => !open)
              }}>{renamingClassroom ? 'Ad düzenlemesini kapat' : 'Adını düzenle'}</button>
              <button type="button" data-testid="classroom-close-btn" disabled={saving} onClick={() => void setClassroomClosed(selectedClassroom, !selectedClassroom.is_closed)}>
                {selectedClassroom.is_closed ? 'Dersliği aç' : 'Dersliği kapat'}
              </button>
              <button type="button" className="danger" data-testid="classroom-delete-btn" disabled={saving || selectedClassroom.can_delete === false}
                title={selectedClassroom.can_delete === false ? 'Bir sınavda kullanıldığı için silinemez; kapatabilirsin.' : undefined}
                onClick={() => void deleteClassroom(selectedClassroom)}>Dersliği sil</button>
            </div>}
          </div>
          {selectedClassroom.is_closed && <p className="privacy-note">Bu derslik kapalı: yeni sınavlarda seçilemez. Eski sınavlardaki yeri ve planı korunur.</p>}
          {!readOnly && selectedClassroom.can_delete === false && <p className="classroom-delete-hint">{selectedClassroom.exam_count} sınavda kullanıldığı için silinemez. Yeni sınavlarda görünmesin istersen kapat.</p>}
          {renamingClassroom && !readOnly && <form className="layout-create-form" onSubmit={saveClassroomName}>
            <label htmlFor="classroom-name-edit">Derslik adı</label>
            <input id="classroom-name-edit" value={classroomNameDraft} onChange={(event) => setClassroomNameDraft(event.target.value)} maxLength={120} required disabled={saving} />
            <button type="submit" disabled={saving}>{saving ? 'Kaydediliyor…' : 'Adı kaydet'}</button>
          </form>}
          {planLoaded && !selectedLayout && (
            <div className="plan-empty" data-testid="plan-empty">
              <strong>Bu dersliğin oturma planı yok.</strong>
              <span>Sıra ve koltukları tanımlayınca derslik sınavlarda kullanılabilir.</span>
              {!readOnly && <button type="button" className="layout-edit-button" disabled={saving || !academicYearId} onClick={() => void createFirstPlan()}>{saving ? 'Oluşturuluyor…' : 'Planı oluştur'}</button>}
            </div>
          )}
          {selectedLayout && (
            <div className="layout-editor">
              <div className="layout-editor-heading">
                <div>
                  <h4>{viewingActivePlan ? 'Oturma planı' : `${selectedLayout.layout.name} · eski ya da ikinci plan`}</h4>
                  {viewingActivePlan && <p className="plan-status" data-testid="plan-status">{selectedLayout.layout.available_seats} koltuk{selectedLayout.layout.available_seats !== selectedLayout.layout.total_seats ? ` (${selectedLayout.layout.total_seats - selectedLayout.layout.available_seats} koltuk kullanım dışı)` : ''} · {planInfo?.examCount ? `${planInfo.examCount} sınavda kullanılıyor` : 'henüz bir sınavda kullanılmıyor'}</p>}
                </div>
                {selectedLayout.desks.length > 0 && !readOnly && viewingActivePlan && (
                  <button type="button" className="layout-edit-button" data-testid="plan-edit-btn" disabled={saving} onClick={toggleEditing}>
                    {editingLayout ? 'Düzenlemeyi bitir' : 'Planı düzenle'}
                  </button>
                )}
              </div>
              {!viewingActivePlan && <p className="privacy-note">Bu plan yalnızca görüntülenir. Sınavlarda dersliğin aktif planı kullanılır; bunu kullanmak için ileri düzey bölümünden aktif yap.</p>}
              {selectedLayout.desks.length === 0 ? (
                <form className="layout-generator" onSubmit={generateLayout}>
                  <div className="generator-intro"><strong>Sınıf planını sütun ve hücrelerle kur</strong><p>Sütunlar tahtadan arkaya uzanır. Uzunlukları değişebilir; sütun aralarına koridor ekleyebilir, her hücreye 1–3 koltuk verebilirsin.</p></div>
                  <div className="generator-fields"><label><span>Sütun sayısı</span><small>Soldan sağa</small><input type="number" min="1" max="12" required value={columnCount} onChange={(event) => changeColumnCount(event.target.value)} disabled={readOnly || saving} /></label></div>
                  <div className="grid-column-config">
                    {columnLengths.map((length, columnIndex) => <fieldset key={columnIndex}><legend>Sütun {columnIndex + 1}</legend><label>Hücre sayısı <input type="number" min="1" max="40" value={length} onChange={(event) => changeColumnLength(columnIndex, event.target.value)} disabled={readOnly || saving} /></label><div className="grid-cell-config">{cellSeats[columnIndex]?.map((seatCount, rowIndex) => <label key={rowIndex}>Satır {rowIndex + 1}<select value={seatCount} onChange={(event) => setCellSeats((current) => current.map((column, index) => index === columnIndex ? column.map((value, cellIndex) => cellIndex === rowIndex ? event.target.value : value) : column))} disabled={readOnly || saving}><option value="1">1 kişi</option><option value="2">2 kişi</option><option value="3">3 kişi</option></select></label>)}</div></fieldset>)}
                  </div>
                  {Number(columnCount) > 1 && <div className="aisle-config"><strong>Koridorlar</strong>{columnCount && Array.from({ length: Number(columnCount) - 1 }, (_, index) => <label key={index}><input type="checkbox" checked={aisleAfter[index] ?? false} onChange={(event) => setAisleAfter((current) => current.map((item, itemIndex) => itemIndex === index ? event.target.checked : item))} /> Sütun {index + 1} ile {index + 2} arasına koridor</label>)}</div>}
                  {validGrid && <div className="layout-scheme" aria-label="Plan ölçülerinin şeması"><span className="scheme-board">TAHTA / ÖN</span><div className="grid-scheme">{columnLengths.map((length, columnIndex) => <div className="grid-scheme-column" key={columnIndex}><strong>Sütun {columnIndex + 1} · {length} hücre</strong>{cellSeats[columnIndex]?.map((count, rowIndex) => <span key={rowIndex}>S{rowIndex + 1} · {count} koltuk</span>)}</div>)}</div><p>{columnLengths.reduce((sum, item) => sum + Number(item), 0)} hücre · <b>{generatedSeatCount} kullanılabilir koltuk</b></p></div>}
                  <button type="submit" disabled={readOnly || saving || !validGrid || generatedSeatCount > 600}>
                    {saving ? 'Oluşturuluyor…' : 'Bu ölçülerle planı oluştur'}
                  </button>
                </form>
              ) : (
                <div className="layout-plan" aria-label="Derslik oturma planı">
                  <p className="privacy-note" data-testid="plan-hint">
                    {editingLayout
                      ? 'Masayı, satır ya da sütun başlığını sürükleyerek taşı. Masanın adına tıklayınca tekli/çiftli yapma ve silme seçenekleri açılır. Koltuğa tıklayınca kullanıma kapanır ya da açılır. Her değişiklik anında kaydedilir.'
                      : 'Sıraları ya da koltukları değiştirmek için “Planı düzenle”ye bas.'}
                  </p>
                  <div
                    className={`layout-canvas ${editingLayout ? 'editable' : ''}`}
                    style={{ width: canvasWidth, height: canvasHeight }}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={dropOnPlan}
                  >
                    <div className="board-label" style={{ left: PLAN_LEFT + (maxDeskX * CELL) / 2 - 40 }}>TAHTA</div>
                    {planBlocks.map((block) => {
                      const firstDesk = block.desks.reduce((first, desk) => desk.x < first.x ? desk : first)
                      return <span className="plan-block-label" style={{ left: PLAN_LEFT + firstDesk.x * CELL }} key={block.label}>{block.label || 'Blok'}</span>
                    })}
                    {planColumns.map((columnX, columnIndex) => (
                      <span
                        className={`plan-line-handle column ${draggingLine?.axis === 'column' && draggingLine.value === columnX ? 'dragging' : ''}`}
                        style={{ left: PLAN_LEFT + columnX * CELL, top: PLAN_TOP - 30 }}
                        key={`c${columnX}`}
                        data-testid={`plan-column-${columnIndex + 1}`}
                        draggable={editingLayout}
                        title={editingLayout ? 'Sütunu taşımak için sürükle' : undefined}
                        onDragStart={(event) => {
                          setDraggingLine({ axis: 'column', value: columnX })
                          const bounds = event.currentTarget.getBoundingClientRect()
                          setDragOffset({ x: event.clientX - bounds.left, y: 0 })
                          event.dataTransfer.setData('text/plain', '')
                          event.dataTransfer.effectAllowed = 'move'
                        }}
                        onDragEnd={() => setDraggingLine(null)}
                      >{columnIndex + 1}</span>
                    ))}
                    {planRows.map((rowY, rowIndex) => (
                      <span
                        className={`plan-line-handle row ${draggingLine?.axis === 'row' && draggingLine.value === rowY ? 'dragging' : ''}`}
                        style={{ top: PLAN_TOP + rowY * CELL + 4 }}
                        key={`r${rowY}`}
                        data-testid={`plan-row-${rowIndex + 1}`}
                        draggable={editingLayout}
                        title={editingLayout ? 'Satırı taşımak için sürükle' : undefined}
                        onDragStart={(event) => {
                          setDraggingLine({ axis: 'row', value: rowY })
                          const bounds = event.currentTarget.getBoundingClientRect()
                          setDragOffset({ x: 0, y: event.clientY - bounds.top - 4 })
                          event.dataTransfer.setData('text/plain', '')
                          event.dataTransfer.effectAllowed = 'move'
                        }}
                        onDragEnd={() => setDraggingLine(null)}
                      >Satır {rowIndex + 1}</span>
                    ))}
                    {editingLayout && <>
                      <button type="button" className="plan-add-line column" data-testid="plan-add-column"
                        style={{ left: PLAN_LEFT + (maxDeskX + 2) * CELL, top: PLAN_TOP - 34 }}
                        onClick={() => void structureOp({ op: 'add_column' })}>Sütun ekle</button>
                      <button type="button" className="plan-add-line row" data-testid="plan-add-row"
                        style={{ top: PLAN_TOP + (maxDeskY + 2) * CELL }}
                        onClick={() => void structureOp({ op: 'add_row' })}>Satır ekle</button>
                    </>}
                    {planRows.flatMap((rowY, rowIndex) => planBlocks.slice(0, -1).flatMap((block, blockIndex) => {
                      const nextBlock = planBlocks[blockIndex + 1]
                      const lastDesk = block.desks.filter((desk) => desk.y === rowY).reduce((last, desk) => !last || desk.x > last.x ? desk : last, null as typeof block.desks[number] | null)
                      const firstDesk = nextBlock.desks.filter((desk) => desk.y === rowY).reduce((first, desk) => !first || desk.x < first.x ? desk : first, null as typeof nextBlock.desks[number] | null)
                      if (!lastDesk || !firstDesk || firstDesk.x - lastDesk.x < 1.1) return []
                      return [<span className="plan-corridor-label" style={{ left: PLAN_LEFT + ((lastDesk.x + firstDesk.x) / 2) * CELL, top: PLAN_TOP + rowY * CELL + 14 }} key={`${rowIndex}-${blockIndex}`}>KORİDOR</span>]
                    }))}
                    {selectedLayout.desks.map((desk) => (
                      <div
                        className={`plan-desk-position ${draggingDeskId === desk.id ? 'dragging' : ''} ${menuDeskId === desk.id ? 'menu-open' : ''}`}
                        key={desk.id}
                        data-testid={`plan-desk-${desk.label}`}
                        draggable={editingLayout}
                        style={{ left: PLAN_LEFT + desk.x * CELL, top: PLAN_TOP + desk.y * CELL }}
                        onContextMenu={(event) => { if (editingLayout) { event.preventDefault(); setMenuDeskId(desk.id) } }}
                        onDragStart={(event) => {
                          setMenuDeskId(null)
                          setDraggingDeskId(desk.id)
                          const bounds = event.currentTarget.getBoundingClientRect()
                          setDragOffset({ x: event.clientX - bounds.left, y: event.clientY - bounds.top })
                          event.dataTransfer.setData('text/plain', desk.id)
                          event.dataTransfer.effectAllowed = 'move'
                        }}
                        onDragEnd={() => setDraggingDeskId(null)}
                      >
                        {editingLayout
                          ? <button type="button" className="plan-desk-menu-btn" aria-haspopup="menu" aria-expanded={menuDeskId === desk.id}
                              aria-label={`${desk.label} masası seçenekleri`} onClick={() => setMenuDeskId((open) => open === desk.id ? null : desk.id)}>{desk.label}</button>
                          : <small>{desk.label}</small>}
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
                        {editingLayout && menuDeskId === desk.id && (
                          <div className="plan-desk-menu" role="menu" data-testid="plan-desk-menu">
                            {([[1, 'Tekli yap'], [2, 'Çiftli yap'], [3, 'Üçlü yap']] as const).filter(([count]) => count !== desk.seats.length).map(([count, label]) => (
                              <button type="button" role="menuitem" key={count} onClick={() => void structureOp({ op: 'set_desk_seats', label: desk.label, count })}>{label}</button>
                            ))}
                            <button type="button" role="menuitem" className="danger" disabled={selectedLayout.desks.length === 1} onClick={() => void structureOp({ op: 'delete_desk', label: desk.label })}>Masayı sil</button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  <p className="plan-legend"><b>Satır</b>: tahtadan arkaya doğru masa dizisi · <b>Sütun</b>: soldan sağa masa dizisi · <b>Blok</b>: koridorun bir tarafındaki sütunlar · <b>S1-M1</b>: Satır 1, Masa 1 · Koltuk numaraları sınıf genelinde verilir.</p>
                </div>
              )}
            </div>
          )}
          <details className="classroom-advanced" data-testid="classroom-advanced">
            <summary>İleri düzey: ikinci plan, şablon, eski hâller{planInfo && planInfo.otherLayoutCount > 0 ? ` (${planInfo.otherLayoutCount})` : ''}</summary>
            <div className="classroom-advanced-body">
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
          {layouts.length > 1 && <p className="layout-active-hint">Sınav için derslik seçildiğinde <b>Aktif</b> işaretli düzen kullanılır. Kullanılmayan düzenleri silebilirsin; bir sınavda kullanılmış düzenler korunur.</p>}
          {layouts.length === 0 ? <p>Bu derslik için kayıtlı plan yok.</p> : (
            <ul className="layout-list">
              {layouts.map((layout) => (
                <li key={layout.id} className={layout.is_active ? 'active-layout' : ''} data-testid={`layout-row-${layout.id}`}>
                  <span>
                    <strong>{layout.name} · v{layout.version}{layout.is_active && <b className="layout-active-badge" data-testid="layout-active-badge">Aktif</b>}</strong>
                    <small>{layout.is_template ? 'Şablon' : layout.academic_year_label}{layout.exam_count ? ` · ${layout.exam_count} sınavda kullanılıyor` : ''}</small>
                  </span>
                  <span className="layout-actions">
                    <small>{layout.available_seats}/{layout.total_seats} kullanılabilir oturma yeri</small>
                    <button type="button" className="layout-open" onClick={() => openLayout(selectedClassroom.id, layout.id)}>Düzeni aç</button>
                    {!readOnly && !layout.is_template && !layout.is_active && <button type="button" className="layout-open" data-testid={`layout-activate-${layout.id}`} disabled={saving} title="Sınav için derslik seçildiğinde bu düzen gelsin" onClick={() => void activateLayout(selectedClassroom.id, layout)}>Aktif yap</button>}
                    {!readOnly && <button type="button" className="layout-open layout-delete" data-testid={`layout-delete-${layout.id}`} disabled={saving || layout.can_delete === false} title={layout.can_delete === false ? 'Bir sınavda kullanılan düzen silinemez' : 'Kullanılmayan düzeni sil'} onClick={() => void deleteLayout(selectedClassroom.id, layout)}>Sil</button>}
                  </span>
                </li>
              ))}
            </ul>
          )}
            </div>
          </details>
        </div>
      )}
    </section>
  )
}
