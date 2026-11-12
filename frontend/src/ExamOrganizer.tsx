import { useEffect, useMemo, useState, type FormEvent } from 'react'
import ReportCenter from './ReportCenter'
import ExamLifecyclePanel from './ExamLifecyclePanel'
import DistributionProgressOverlay from './DistributionProgressOverlay'
import { subscribeLocks, takeOverEditing, type EditLocks } from './editSession'

type GroupOption = {
  class_level: string
  section: string
  area: string | null
  student_count: number
}

type CourseOption = { id: string; name: string }
type CourseDraft = { id: number; name: string; groupKeys: string[] }
type RuleKey = 'prevent_same_section_adjacent' | 'prevent_same_section_front_back' | 'prevent_different_grade_same_area_adjacent' | 'prevent_different_grade_same_area_front_back' | 'prevent_same_grade_area_adjacent' | 'prevent_same_grade_area_front_back' | 'prevent_same_grade_adjacent' | 'prevent_same_grade_front_back'
type RuleSet = Record<RuleKey, boolean>
type CandidateAssignment = { participant_id: string; seat_id: string | null; seat_number: number | null; classroom_id: string | null; classroom_name: string | null; first_name: string; last_name: string; school_number: string; class_level: string; section: string; area: string | null }
type Violation = { first_participant_id: string; second_participant_id: string; first_seat_id: string; second_seat_id: string; relation: string; reason: string }
type CandidatePreview = { violations?: Violation[]; violation_suggestions?: Record<string, { seat_id: string; classroom_name: string; seat_number: number; same_room: boolean }[]>; candidate_id: string; run_id: string; generation_index: number; derived_from_candidate_id: string | null; pinned_classroom_ids?: string[]; status: string; affected_student_count: number; events: { id: string; event_type: string; participant_id: string; participant_name: string; school_number: string; displaced_participant_id: string | null; from_seat_id: string | null; to_seat_id: string | null; related_event_id: string | null; created_at: string }[]; history: { can_undo: boolean; can_redo: boolean; undo_count: number; redo_count: number; undo_event_id: string | null; redo_event_id: string | null }; report_status?: 'not_generated' | 'current' | 'stale'; report_statuses?: Partial<Record<ReportKind, { report_status: ReportStatus; report_updated_at: string | null }>>; available_seats: { seat_id: string; seat_number: number; classroom_id: string; classroom_name: string }[]; summary: { groups: { class_level: string; section: string; area: string | null; student_count: number }[]; rooms: { classroom_id: string; classroom_name: string; available_seats: number; assigned_students: number; empty_seats: number }[]; waiting_count: number }; assignments: CandidateAssignment[]; plan: { classroom_id: string; classroom_name: string; layout_id: string; layout_name: string; desks: { desk_id: string; label: string; block_label: string; x: number; y: number; seats: { seat_id: string; seat_number: number; seat_index: number; x: number | null; y: number | null; is_available: boolean; student: CandidateAssignment | null }[] }[] }[] }
type ReportStatus = 'not_generated' | 'current' | 'stale'
type ReportKind = 'seating_plan_pdf' | 'attendance_pdf' | 'room_student_list_pdf'
type FinalReview = { candidate_id: string; participant_count: number; seated_count: number; unassigned_count: number; available_capacity: number; empty_seats: number; affected_student_count: number; violation_count: number; can_finalize: boolean; rooms: { classroom_id: string; classroom_name: string; available_seats: number; assigned_students: number; empty_seats: number }[] }
const ruleLabels: { key: RuleKey; title: string; position: string }[] = [
  { key: 'prevent_same_section_adjacent', title: 'Aynı şubedeki öğrenciler', position: 'Yan yana' },
  { key: 'prevent_same_section_front_back', title: 'Aynı şubedeki öğrenciler', position: 'Önlü arkalı' },
  { key: 'prevent_different_grade_same_area_adjacent', title: 'Farklı sınıf seviyelerinde aynı alan öğrencileri', position: 'Yan yana' },
  { key: 'prevent_different_grade_same_area_front_back', title: 'Farklı sınıf seviyelerinde aynı alan öğrencileri', position: 'Önlü arkalı' },
  { key: 'prevent_same_grade_area_adjacent', title: 'Aynı sınıf seviyesi ve alandaki öğrenciler', position: 'Yan yana' },
  { key: 'prevent_same_grade_area_front_back', title: 'Aynı sınıf seviyesi ve alandaki öğrenciler', position: 'Önlü arkalı' },
  { key: 'prevent_same_grade_adjacent', title: 'Aynı sınıf seviyesindeki öğrenciler', position: 'Yan yana' },
  { key: 'prevent_same_grade_front_back', title: 'Aynı sınıf seviyesindeki öğrenciler', position: 'Önlü arkalı' },
]
type RoomOption = {
  classroom_id: string
  classroom_name: string
  layout_id: string
  layout_name: string
  version: number
  total_seats: number
  available_seats: number
  can_select: boolean
  is_latest: boolean
  is_active?: boolean
}
type ExamPeriod = {
  id: string
  academic_year_id: string
  name: string
  display_order: number
  exam_count: number
  can_delete: boolean
}

type ExamOrganization = {
  id: string
  name: string
  exam_period_id: string | null
  exam_period_name: string | null
  exam_date: string
  status: 'draft' | 'completed'
  report_status: ReportStatus
  report_updated_at: string | null
  report_statuses: Partial<Record<ReportKind, { report_status: ReportStatus; report_updated_at: string | null }>>
  course_names: string[]
  course_count: number
  participant_count: number
  room_selections: { classroom_id: string; classroom_name: string; layout_id: string; layout_name: string; version: number; available_seats: number }[]
  available_capacity: number
  capacity_sufficient: boolean
  capacity_deficit: number
  rules: RuleSet
  selected_candidate_id: string | null
  archived_at: string | null
  copied_from_organization_id: string | null
  needs_redistribution?: boolean
  group_count?: number
  groups?: { class_level: string; section: string; area: string | null; student_count: number }[]
}

type Props = {
  academicYearId: string | null
    readOnly: boolean
  onStudents: () => void
  onClassrooms: () => void
  /** Raporlar artık sınav sayfasının son adımı; geriye dönük uyum için kabul edilir. */
  onReports?: () => void
}

function groupKey(group: GroupOption) {
  return `${group.class_level}|${group.section}|${group.area ?? ''}`
}

function localDateValue() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function groupLabel(group: GroupOption) {
  const area = group.area ? ` · ${group.area}` : Number(group.class_level) >= 11 ? ' · Alan belirtilmemiş' : ''
  return `${group.class_level}/${group.section}${area}`
}

function historyEventLabel(eventType: string) {
  if (eventType === 'seat_move') return 'Taşıma'
  if (eventType === 'seat_swap') return 'Takas'
  if (eventType === 'seat_to_pool') return 'Havuza alma'
  if (eventType === 'undo') return 'Geri alma'
  if (eventType === 'redo') return 'Yineleme'
  if (eventType === 'student_refresh') return 'Güncel bilgiyle havuza alma'
  if (eventType === 'participant_removed') return 'Listeden çıkarma'
  return 'Değişiklik'
}

function GroupSelector({
  groups,
  selected,
  onChange,
}: {
  groups: GroupOption[]
  selected: string[]
  onChange: (update: (current: string[]) => string[]) => void
}) {
  function toggle(key: string) {
    onChange((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key])
  }

  const allKeys = groups.map(groupKey)
  const allSelected = allKeys.length > 0 && allKeys.every((key) => selected.includes(key))
  return <div className="exam-group-options">
    {groups.length > 1 && <button type="button" className="exam-group-all" data-testid="exam-group-select-all" onClick={() => onChange(() => allSelected ? [] : allKeys)}>{allSelected ? 'Seçimi temizle' : 'Tüm sınıfları seç'}</button>}
    {groups.map((group) => {
      const key = groupKey(group)
      return <label className={selected.includes(key) ? 'selected' : ''} key={key}>
        <input type="checkbox" checked={selected.includes(key)} onChange={() => toggle(key)} />
        <span>{groupLabel(group)}</span>
        <small>{group.student_count} öğrenci</small>
      </label>
    })}
  </div>
}

const GUIDE_STEPS = ['Derslikler', 'Dağıtım', 'Kontrol', 'Kesinleştirme', 'Raporlar']

export default function ExamOrganizer({ academicYearId, readOnly: yearReadOnly, onStudents, onClassrooms }: Props) {
  const readOnly = yearReadOnly
  const [reloadKey, setReloadKey] = useState(0)
  const [notice, setNotice] = useState('')
  const [locks, setLocks] = useState<EditLocks>({})
  useEffect(() => subscribeLocks(setLocks), [])
  const [organizations, setOrganizations] = useState<ExamOrganization[]>([])
  const [groups, setGroups] = useState<GroupOption[]>([])
  const [courseCatalog, setCourseCatalog] = useState<CourseOption[]>([])
  const [roomOptions, setRoomOptions] = useState<RoomOption[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [periods, setPeriods] = useState<ExamPeriod[]>([])
  const [periodId, setPeriodId] = useState('')
  const [periodPanelOpen, setPeriodPanelOpen] = useState(false)
  const [newPeriodName, setNewPeriodName] = useState('')
  const [periodError, setPeriodError] = useState('')
  const [periodBusy, setPeriodBusy] = useState(false)
  const [name, setName] = useState('')
  const [examDate, setExamDate] = useState(localDateValue)
  const [withCourses, setWithCourses] = useState(false)
  const [generalGroupKeys, setGeneralGroupKeys] = useState<string[]>([])
  const [courses, setCourses] = useState<CourseDraft[]>([])
  const [nextCourseId, setNextCourseId] = useState(1)
  const [activeRoomOrganizationId, setActiveRoomOrganizationId] = useState<string | null>(null)
  const [selectedLayoutByClassroom, setSelectedLayoutByClassroom] = useState<Record<string, string>>({})
  const [roomSaving, setRoomSaving] = useState(false)
  const [roomError, setRoomError] = useState('')
  const [roomMessage, setRoomMessage] = useState('')
  const [activeRuleOrganizationId, setActiveRuleOrganizationId] = useState<string | null>(null)
  const [ruleDraft, setRuleDraft] = useState<RuleSet | null>(null)
  const [ruleSaving, setRuleSaving] = useState(false)
  const [ruleError, setRuleError] = useState('')
  const [ruleMessage, setRuleMessage] = useState('')
  const [candidateSavingId, setCandidateSavingId] = useState<string | null>(null)
  const [candidateError, setCandidateError] = useState('')
  const [candidateErrorId, setCandidateErrorId] = useState<string | null>(null)
  const [candidates, setCandidates] = useState<Record<string, CandidatePreview[]>>({})
  const [selectedPlanStudentByCandidate, setSelectedPlanStudentByCandidate] = useState<Record<string, string>>({})
  const [focusedViolation, setFocusedViolation] = useState<Record<string, string>>({})
  function focusViolation(candidateId: string, participantId: string, seatId: string | null) {
    setFocusedViolation((current) => ({ ...current, [candidateId]: current[candidateId] === participantId ? '' : participantId }))
    // İhlalli koltuk başka bir derslikteyse önce o dersliğin sekmesine geç.
    if (seatId) {
      const owner = Object.values(candidates).flat().find((item) => item.candidate_id === candidateId)
      const room = owner?.plan.find((item) => item.desks.some((desk) => desk.seats.some((seat) => seat.seat_id === seatId)))
      if (room) setPlanRoomByCandidate((current) => ({ ...current, [candidateId]: room.layout_id }))
    }
    const details = document.getElementById(`plan-details-${candidateId}`) as HTMLDetailsElement | null
    if (details) details.open = true
    if (seatId) window.setTimeout(() => document.getElementById(`plan-details-${candidateId}`)?.querySelector(`[data-seat-id="${seatId}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' }), 120)
  }
  const [movingCandidateId, setMovingCandidateId] = useState<string | null>(null)
  const [finalReviews, setFinalReviews] = useState<Record<string, FinalReview>>({})
  const [reviewLoadingId, setReviewLoadingId] = useState<string | null>(null)
  const [reviewError, setReviewError] = useState('')
  const [finalizeConfirmId, setFinalizeConfirmId] = useState<string | null>(null)
  const [finalizeConfirmed, setFinalizeConfirmed] = useState(false)
  // Açık sınav sayfası; null iken sınav listesi görünür.
  const [pageExamId, setPageExamId] = useState<string | null>(null)
  // Kullanıcının geri dönüp baktığı adım; sınav ilerleyince kendiliğinden sıfırlanır.
  const [viewStep, setViewStep] = useState<{ examId: string; step: number; at: number } | null>(null)
  const [planRoomByCandidate, setPlanRoomByCandidate] = useState<Record<string, string>>({})
  const [finalizing, setFinalizing] = useState(false)

  useEffect(() => {
    if (!academicYearId) {
      setOrganizations([])
      setGroups([])
      setLoading(false)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    setError('')
    Promise.all([
      fetch(`/api/exam-organizations?academic_year_id=${encodeURIComponent(academicYearId)}`, { signal: controller.signal }),
      fetch(`/api/student-groups?academic_year_id=${encodeURIComponent(academicYearId)}`, { signal: controller.signal }),
      fetch('/api/courses', { signal: controller.signal }),
      fetch(`/api/exam-room-options?academic_year_id=${encodeURIComponent(academicYearId)}`, { signal: controller.signal }),
      fetch(`/api/exam-periods?academic_year_id=${encodeURIComponent(academicYearId)}`, { signal: controller.signal }),
    ])
      .then(async ([organizationResponse, groupResponse, courseResponse, roomResponse, periodResponse]) => {
        const [organizationData, groupData, courseData, roomData, periodData] = await Promise.all([
          organizationResponse.json(), groupResponse.json(), courseResponse.json(), roomResponse.json(), periodResponse.json(),
        ])
        if (!periodResponse.ok) throw new Error(periodData.error ?? 'Sınav dönemleri yüklenemedi.')
        if (!organizationResponse.ok) throw new Error(organizationData.error ?? 'Organizasyonlar yüklenemedi.')
        if (!groupResponse.ok) throw new Error(groupData.error ?? 'Öğrenci grupları yüklenemedi.')
        if (!courseResponse.ok) throw new Error(courseData.error ?? 'Ders listesi yüklenemedi.')
        if (!roomResponse.ok) throw new Error(roomData.error ?? 'Derslik düzenleri yüklenemedi.')
        const loadedOrganizations = organizationData.organizations as ExamOrganization[]
        setOrganizations(loadedOrganizations)
        setGroups(groupData.groups as GroupOption[])
        setCourseCatalog(courseData.courses as CourseOption[])
        setRoomOptions(roomData.rooms as RoomOption[])
        const loadedPeriods = periodData.periods as ExamPeriod[]
        setPeriods(loadedPeriods)
        setPeriodId((current) => current || loadedPeriods[0]?.id || '')
        const candidateLists = await Promise.all(loadedOrganizations.map(async (organization) => {
          const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organization.id)}/distribution-candidates`, { signal: controller.signal })
          const data = await response.json()
          if (!response.ok) throw new Error(data.error ?? 'Kayıtlı dağıtım adayları yüklenemedi.')
          return [organization.id, data.candidates as CandidatePreview[]] as const
        }))
        setCandidates(Object.fromEntries(candidateLists.filter(([, items]) => items.length)))
      })
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name === 'AbortError') return
        setError(reason instanceof Error ? reason.message : 'Sınav verileri yüklenemedi.')
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [academicYearId, reloadKey])

  const selectedGroupKeys = useMemo(() => withCourses
    ? Array.from(new Set(courses.flatMap((course) => course.groupKeys)))
    : generalGroupKeys,
  [withCourses, courses, generalGroupKeys])
  const selectedStudentCount = useMemo(() => {
    const counts = new Map(groups.map((group) => [groupKey(group), group.student_count]))
    return selectedGroupKeys.reduce((total, key) => total + (counts.get(key) ?? 0), 0)
  }, [groups, selectedGroupKeys])
  const selectionsComplete = withCourses
    ? courses.length > 0 && courses.every((course) => Boolean(course.name.trim()) && course.groupKeys.length > 0)
    : generalGroupKeys.length > 0
  const roomOptionsByClassroom = useMemo(() => {
    const result = new Map<string, RoomOption[]>()
    for (const room of roomOptions) {
      result.set(room.classroom_id, [...(result.get(room.classroom_id) ?? []), room])
    }
    return Array.from(result.values())
  }, [roomOptions])
  const selectedRoomCapacity = Object.values(selectedLayoutByClassroom).reduce((total, layoutId) => {
    const room = roomOptions.find((item) => item.layout_id === layoutId)
    return total + (room?.available_seats ?? 0)
  }, 0)

  function toggleCourseMode(enabled: boolean) {
    setWithCourses(enabled)
    setError('')
    if (enabled && courses.length === 0) {
      setCourses([{ id: nextCourseId, name: '', groupKeys: [] }])
      setNextCourseId((id) => id + 1)
    }
  }

  function updateCourse(id: number, change: Partial<CourseDraft>) {
    setCourses((items) => items.map((course) => course.id === id ? { ...course, ...change } : course))
  }

  function addCourse() {
    setCourses((items) => [...items, { id: nextCourseId, name: '', groupKeys: [] }])
    setNextCourseId((id) => id + 1)
  }

  // Sınavlar dönemlere göre gruplanır; dönemi olmayan eski kayıtlar en sonda
  // ayrı bir başlık altında toplanır ve oradan bir döneme taşınabilir.
  const groupedOrganizations = useMemo(() => {
    const byPeriod = new Map<string, ExamOrganization[]>()
    const orphans: ExamOrganization[] = []
    for (const organization of organizations) {
      if (organization.exam_period_id && periods.some((item) => item.id === organization.exam_period_id)) {
        const bucket = byPeriod.get(organization.exam_period_id) ?? []
        bucket.push(organization)
        byPeriod.set(organization.exam_period_id, bucket)
      } else {
        orphans.push(organization)
      }
    }
    const sections = periods.map((period) => ({
      key: period.id,
      title: period.name,
      items: byPeriod.get(period.id) ?? [],
      orphan: false,
    }))
    if (orphans.length) {
      sections.push({ key: '__orphan__', title: 'Dönem atanmamış', items: orphans, orphan: true })
    }
    // İçinde sınav olan dönemler önce gelir. Aksi halde dört boş dönem başlığı
    // ekranı doldurup kullanıcının asıl işini katlamanın altına itiyordu.
    return {
      dolu: sections.filter((item) => item.items.length > 0),
      bos: sections.filter((item) => item.items.length === 0),
    }
  }, [organizations, periods])

  async function periodRequest(path: string, method: string, body?: unknown) {
    setPeriodBusy(true)
    setPeriodError('')
    try {
      const response = await fetch(path, {
        method,
        headers: { 'Content-Type': 'application/json' },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Dönem işlemi tamamlanamadı.')
      const refreshed = await fetch(`/api/exam-periods?academic_year_id=${encodeURIComponent(academicYearId ?? '')}`)
      const refreshedData = await refreshed.json()
      if (refreshed.ok) setPeriods(refreshedData.periods as ExamPeriod[])
      return true
    } catch (reason) {
      setPeriodError(reason instanceof Error ? reason.message : 'Dönem işlemi tamamlanamadı.')
      return false
    } finally {
      setPeriodBusy(false)
    }
  }

  async function renamePeriod(period: ExamPeriod) {
    const next = window.prompt('Dönem adı', period.name)
    if (next === null || next.trim() === period.name) return
    await periodRequest(`/api/exam-periods/${encodeURIComponent(period.id)}`, 'PATCH', { name: next })
  }

  async function addPeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!newPeriodName.trim()) return
    const ok = await periodRequest('/api/exam-periods', 'POST', {
      academic_year_id: academicYearId, name: newPeriodName,
    })
    if (ok) setNewPeriodName('')
  }

  async function deletePeriod(period: ExamPeriod) {
    if (!window.confirm(`"${period.name}" dönemi silinsin mi? Bu işlem yalnızca dönemi siler, sınavları silmez.`)) return
    await periodRequest(`/api/exam-periods/${encodeURIComponent(period.id)}`, 'DELETE')
  }

  async function moveOrganizationToPeriod(organizationId: string, nextPeriodId: string) {
    if (!nextPeriodId) return
    const ok = await periodRequest(
      `/api/exam-organizations/${encodeURIComponent(organizationId)}/period`, 'PATCH',
      { exam_period_id: nextPeriodId },
    )
    if (ok) setReloadKey((key) => key + 1)
  }

  async function createOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!academicYearId || readOnly) return
    setSaving(true)
    setError('')
    const groupFromKey = (key: string) => {
      const group = groups.find((item) => groupKey(item) === key)
      return group ? { class_level: group.class_level, section: group.section, area: group.area ?? '' } : null
    }
    const payload = {
      academic_year_id: academicYearId,
      name,
      exam_period_id: periodId,
      exam_date: examDate,
      ...(withCourses
        ? { courses: courses.map((course) => ({ name: course.name, groups: course.groupKeys.map(groupFromKey).filter(Boolean) })) }
        : { participant_groups: generalGroupKeys.map(groupFromKey).filter(Boolean) }),
    }
    try {
      const response = await fetch('/api/exam-organizations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Organizasyon oluşturulamadı.')
      let organization = data.organization as ExamOrganization
      // Yalnızca sınava giren sınıfların kendi derslikleri kendiliğinden seçilir
      // (içe aktarma her sınıf/şube için "9-A Derslik" adında bir derslik kurar).
      // Koltuk yetmezse sırayla başka derslik eklenir; yine yetmezse seçim
      // kullanıcıya bırakılır. Sınava girmeyen sınıfların dersliği boşuna dolmaz.
      const selectedGroupNames = (withCourses ? courses.flatMap((course) => course.groupKeys) : generalGroupKeys)
        .map(groupFromKey)
        .filter((group): group is NonNullable<ReturnType<typeof groupFromKey>> => Boolean(group))
        .map((group) => `${group.class_level}-${group.section}`.toLocaleLowerCase('tr-TR'))
      const defaultLayouts = roomOptionsByClassroom
        .map((layouts) => layouts.find((item) => item.is_active && item.can_select) ?? layouts.find((item) => item.can_select))
        .filter((item): item is RoomOption => Boolean(item))
      const ownsSelectedGroup = (room: RoomOption) => {
        const roomName = room.classroom_name.toLocaleLowerCase('tr-TR')
        return selectedGroupNames.some((prefix) => roomName === prefix || roomName.startsWith(`${prefix} `))
      }
      const autoLayouts = defaultLayouts.filter(ownsSelectedGroup)
      let autoCapacity = autoLayouts.reduce((total, item) => total + item.available_seats, 0)
      for (const room of defaultLayouts) {
        if (autoCapacity >= organization.participant_count) break
        if (autoLayouts.includes(room)) continue
        autoLayouts.push(room)
        autoCapacity += room.available_seats
      }
      let autoSelected = false
      if (autoLayouts.length && autoCapacity >= organization.participant_count) {
        const roomResponse = await fetch(`/api/exam-organizations/${encodeURIComponent(organization.id)}/classrooms`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ layout_ids: autoLayouts.map((item) => item.layout_id) }),
        })
        if (roomResponse.ok) {
          organization = (await roomResponse.json()).organization as ExamOrganization
          autoSelected = true
        }
      }
      const created = organization
      setOrganizations((items) => [created, ...items].sort((a, b) => b.exam_date.localeCompare(a.exam_date)))
      setActiveRoomOrganizationId(autoSelected ? null : created.id)
      setSelectedLayoutByClassroom({})
      const ownRoomCount = defaultLayouts.filter(ownsSelectedGroup).length
      const createdSummary = `${selectedGroupNames.length} sınıf · ${created.participant_count} öğrenci`
      setNotice(autoSelected
        ? `«${created.name}» oluşturuldu: ${createdSummary}. ${autoLayouts.length} derslik kendiliğinden seçildi${autoLayouts.length <= 6 ? `: ${autoLayouts.map((item) => item.classroom_name).join(', ')}` : ''}${ownRoomCount > 0 && autoLayouts.length > ownRoomCount ? ` (sınıfların kendi dersliklerinde koltuk yetmediği için ${autoLayouts.slice(ownRoomCount).map((item) => item.classroom_name).join(', ')} eklendi)` : ''}. Sıradaki adım dağıtım.`
        : `«${created.name}» oluşturuldu: ${createdSummary}. Sıradaki adım derslik seçimi.`)
      setPageExamId(created.id)
      setViewStep(null)
      const newCourses = organization.course_names.map((courseName) => ({ id: 0, name: courseName }))
      setCourseCatalog((items) => {
        const names = new Set(items.map((item) => item.name.toLocaleLowerCase('tr-TR')))
        return [...items, ...newCourses.filter((item) => !names.has(item.name.toLocaleLowerCase('tr-TR'))).map((item) => ({ id: item.name, name: item.name }))]
      })
      setFormOpen(false)
      setName('')
      setWithCourses(false)
      setGeneralGroupKeys([])
      setCourses([])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Organizasyon oluşturulamadı.')
    } finally {
      setSaving(false)
    }
  }

  function toggleRoomEditor(organization: ExamOrganization) {
    if (activeRoomOrganizationId === organization.id) {
      setActiveRoomOrganizationId(null)
      setRoomError('')
      return
    }
    setActiveRoomOrganizationId(organization.id)
    setSelectedLayoutByClassroom(Object.fromEntries(
      (organization.room_selections ?? []).map((room) => [room.classroom_id, room.layout_id]),
    ))
    setRoomError('')
    setRoomMessage('')
  }

  function toggleRoom(classroomId: string, checked: boolean) {
    setSelectedLayoutByClassroom((selected) => {
      const next = { ...selected }
      if (!checked) {
        delete next[classroomId]
      } else {
        const defaultLayout = roomOptionsByClassroom
          .find((items) => items[0]?.classroom_id === classroomId)
          ?.find((item) => item.can_select)
        if (defaultLayout) next[classroomId] = defaultLayout.layout_id
      }
      return next
    })
    setRoomMessage('')
  }

  async function saveRoomSelection(organizationId: string) {
    setRoomSaving(true)
    setRoomError('')
    setRoomMessage('')
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/classrooms`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layout_ids: Object.values(selectedLayoutByClassroom) }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Derslik seçimi kaydedilemedi.')
      const updated = data.organization as ExamOrganization
      setOrganizations((items) => items.map((item) => item.id === updated.id ? updated : item))
      setCandidates((current) => { const next = { ...current }; delete next[organizationId]; return next })
      setSelectedLayoutByClassroom(Object.fromEntries(
        updated.room_selections.map((room) => [room.classroom_id, room.layout_id]),
      ))
      setRoomMessage('Derslik seçimi kaydedildi.')
      // Kapasite yetiyorsa panel kapanır ve rehber dağıtım adımını gösterir.
      if (updated.capacity_sufficient && updated.room_selections.length) setActiveRoomOrganizationId(null)
    } catch (reason) {
      setRoomError(reason instanceof Error ? reason.message : 'Derslik seçimi kaydedilemedi.')
    } finally {
      setRoomSaving(false)
    }
  }

  function toggleRuleEditor(organization: ExamOrganization) {
    if (activeRuleOrganizationId === organization.id) {
      setActiveRuleOrganizationId(null)
      setRuleError('')
      return
    }
    setActiveRuleOrganizationId(organization.id)
    setRuleDraft({ ...organization.rules })
    setRuleError('')
    setRuleMessage('')
  }

  async function saveRules(organizationId: string) {
    if (!ruleDraft) return
    setRuleSaving(true)
    setRuleError('')
    setRuleMessage('')
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/rules`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rules: ruleDraft }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Dağıtım kuralları kaydedilemedi.')
      const updated = data.organization as ExamOrganization
      setOrganizations((items) => items.map((item) => item.id === updated.id ? updated : item))
      setCandidates((current) => { const next = { ...current }; delete next[organizationId]; return next })
      setRuleDraft({ ...updated.rules })
      setRuleMessage('Dağıtım kuralları kaydedildi.')
    } catch (reason) {
      setRuleError(reason instanceof Error ? reason.message : 'Dağıtım kuralları kaydedilemedi.')
    } finally {
      setRuleSaving(false)
    }
  }

  async function createCandidate(organizationId: string) {
    setCandidateSavingId(organizationId)
    setCandidateError('')
    setCandidateErrorId(null)
    try {
      const existing = candidates[organizationId] ?? []
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/distribution-candidates`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(existing.length ? { run_id: existing[0].run_id } : {}),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Dağıtım adayı oluşturulamadı.')
      const created = data.candidate as CandidatePreview
      setCandidates((current) => ({ ...current, [organizationId]: [...(current[organizationId] ?? []), created] }))
      setOrganizations((items) => items.map((item) => item.id === organizationId ? { ...item, needs_redistribution: false } : item))
      // Yeni dağıtım doğrudan geçerli dağıtım olur; öncekiler "Önceki dağıtımlar"da kalır.
      await selectCandidate(organizationId, created.candidate_id)
    } catch (reason) {
      setCandidateError(reason instanceof Error ? reason.message : 'Dağıtım oluşturulamadı.')
      setCandidateErrorId(organizationId)
    } finally {
      setCandidateSavingId(null)
    }
  }

  function clearFinalReview(organizationId: string) {
    setFinalReviews((current) => { const next = { ...current }; delete next[organizationId]; return next })
    setFinalizeConfirmId((current) => current === organizationId ? null : current)
    setFinalizeConfirmed(false)
    setReviewError('')
  }

  async function selectCandidate(organizationId: string, candidateId: string) {
    setCandidateError('')
    setCandidateErrorId(null)
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/selected-candidate`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: candidateId }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Aday seçilemedi.')
      setOrganizations((items) => items.map((item) => item.id === organizationId ? { ...item, selected_candidate_id: candidateId } : item))
      clearFinalReview(organizationId)
    } catch (reason) {
      setCandidateError(reason instanceof Error ? reason.message : 'Aday seçilemedi.')
      setCandidateErrorId(organizationId)
    }
  }

  async function moveCandidateStudent(organizationId: string, candidateId: string, participantId: string, targetSeatId: string, fixAll = false) {
    setMovingCandidateId(candidateId)
    setCandidateError('')
    setCandidateErrorId(null)
    try {
      const base = `/api/exam-organizations/${encodeURIComponent(organizationId)}/distribution-candidates/${encodeURIComponent(candidateId)}`
      const response = await fetch(fixAll ? `${base}/fix-violations` : `${base}/moves`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fixAll ? {} : { participant_id: participantId, target_seat_id: targetSeatId }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Öğrenci taşınamadı.')
      if (data.candidate.fix_summary) {
        const summary = data.candidate.fix_summary as { moved: number; affected_before: number; affected_after: number }
        setNotice(`${summary.moved} öğrenci taşındı · ihlalden etkilenen öğrenci ${summary.affected_before} → ${summary.affected_after}.${summary.affected_after ? ' Kalanlar için ihlalsiz boş yer yok; krokiden yer değiştirin.' : ''}`)
      }
      const child = data.candidate as CandidatePreview
      setCandidates((current) => {
        const existing = current[organizationId] ?? []
        return { ...current, [organizationId]: existing.some((item) => item.candidate_id === child.candidate_id)
          ? existing.map((item) => item.candidate_id === child.candidate_id ? child : item)
          : [...existing, child] }
      })
      setOrganizations((items) => items.map((item) => item.id === organizationId ? {
        ...item, selected_candidate_id: child.candidate_id,
        ...(child.report_status ? { report_status: child.report_status } : {}),
        ...(child.report_statuses ? { report_statuses: child.report_statuses } : {}),
      } : item))
      clearFinalReview(organizationId)
      setSelectedPlanStudentByCandidate((current) => { const next = { ...current }; delete next[candidateId]; return next })
    } catch (reason) {
      setCandidateError(reason instanceof Error ? reason.message : 'Öğrenci taşınamadı.')
      setCandidateErrorId(organizationId)
    } finally {
      setMovingCandidateId(null)
    }
  }

  function selectPlanStudent(candidateId: string, participantId: string) {
    setSelectedPlanStudentByCandidate((current) => ({
      ...current,
      [candidateId]: current[candidateId] === participantId ? '' : participantId,
    }))
  }

  async function moveCandidateToPool(organizationId: string, candidateId: string, participantId: string) {
    setMovingCandidateId(candidateId)
    setCandidateError('')
    setCandidateErrorId(null)
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/distribution-candidates/${encodeURIComponent(candidateId)}/moves`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ participant_id: participantId, target_seat_id: null }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Öğrenci bekleyen havuza alınamadı.')
      const child = data.candidate as CandidatePreview
      setCandidates((current) => {
        const existing = current[organizationId] ?? []
        return { ...current, [organizationId]: existing.some((item) => item.candidate_id === child.candidate_id)
          ? existing.map((item) => item.candidate_id === child.candidate_id ? child : item)
          : [...existing, child] }
      })
      setOrganizations((items) => items.map((item) => item.id === organizationId ? {
        ...item, selected_candidate_id: child.candidate_id,
        ...(child.report_status ? { report_status: child.report_status } : {}),
        ...(child.report_statuses ? { report_statuses: child.report_statuses } : {}),
      } : item))
      clearFinalReview(organizationId)
      setSelectedPlanStudentByCandidate((current) => { const next = { ...current }; delete next[candidateId]; return next })
    } catch (reason) {
      setCandidateError(reason instanceof Error ? reason.message : 'Öğrenci bekleyen havuza alınamadı.')
      setCandidateErrorId(organizationId)
    } finally {
      setMovingCandidateId(null)
    }
  }

  async function changeCompletedHistory(organizationId: string, candidateId: string, action: 'undo' | 'redo') {
    setMovingCandidateId(candidateId)
    setCandidateError('')
    setCandidateErrorId(null)
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/distribution-candidates/${encodeURIComponent(candidateId)}/history/${action}`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'İşlem geçmişi güncellenemedi.')
      const updated = data.candidate as CandidatePreview
      setCandidates((current) => ({
        ...current,
        [organizationId]: (current[organizationId] ?? []).map((item) => item.candidate_id === updated.candidate_id ? updated : item),
      }))
      setOrganizations((items) => items.map((item) => item.id === organizationId ? {
        ...item, report_status: updated.report_status ?? item.report_status,
        ...(updated.report_statuses ? { report_statuses: updated.report_statuses } : {}),
      } : item))
      setSelectedPlanStudentByCandidate((current) => { const next = { ...current }; delete next[candidateId]; return next })
      clearFinalReview(organizationId)
    } catch (reason) {
      setCandidateError(reason instanceof Error ? reason.message : 'İşlem geçmişi güncellenemedi.')
      setCandidateErrorId(organizationId)
    } finally {
      setMovingCandidateId(null)
    }
  }

  async function openFinalReview(organizationId: string) {
    setReviewLoadingId(organizationId)
    setReviewError('')
    setFinalizeConfirmId(null)
    setFinalizeConfirmed(false)
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/final-review`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Son kontrol yapılamadı.')
      setFinalReviews((current) => ({ ...current, [organizationId]: data.review as FinalReview }))
      setFinalizeConfirmId(organizationId)
    } catch (reason) {
      setReviewError(reason instanceof Error ? reason.message : 'Son kontrol yapılamadı.')
    } finally {
      setReviewLoadingId(null)
    }
  }

  async function finalizeOrganization(organizationId: string) {
    setFinalizing(true)
    setReviewError('')
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/finalize`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true, physical_layouts_confirmed: true }) })
      const data = await response.json()
      if (!response.ok) {
        if (data.review) {
          setFinalReviews((current) => ({ ...current, [organizationId]: data.review as FinalReview }))
          setFinalizeConfirmId(organizationId)
          setFinalizeConfirmed(false)
        }
        throw new Error(data.error ?? 'Organizasyon kesinleştirilemedi.')
      }
      const updated = data.organization as ExamOrganization
      setOrganizations((items) => items.map((item) => item.id === organizationId ? updated : item))
      setFinalizeConfirmId(null)
      setFinalizeConfirmed(false)
    } catch (reason) {
      setReviewError(reason instanceof Error ? reason.message : 'Organizasyon kesinleştirilemedi.')
    } finally {
      setFinalizing(false)
    }
  }

  const pageExam = pageExamId ? organizations.find((item) => item.id === pageExamId) ?? null : null

  function openExamPage(organization: ExamOrganization) {
    setPageExamId(organization.id)
    setViewStep(null)
    setFormOpen(false)
    // Derslik adımındaki sınavda seçim paneli doğrudan açılır.
    const needsRooms = organization.status === 'draft' && !organization.archived_at
      && !((organization.room_selections?.length ?? 0) && organization.capacity_sufficient)
    if (needsRooms && activeRoomOrganizationId !== organization.id) toggleRoomEditor(organization)
    else if (!needsRooms) setActiveRoomOrganizationId(null)
    window.scrollTo({ top: 0 })
  }

  return <section className="exam-organizer" aria-labelledby="exam-organizer-title">
    {!pageExam && <div className="exam-organizer-heading">
      <div>
        {/* Sayfa başlığı ve eğitim yılı üstte zaten yazıyor; burada tekrar
            etmek yerine yalnızca ne yapılacağını anlatan tek satır kalır. */}
        <h2 id="exam-organizer-title" className="visually-hidden">Sınav organizasyonları</h2>
        <p>Sınavı oluştur, öğrencileri dağıt, kontrol edip kesinleştir. Her sınav kartı sıradaki adımı ve basman gereken düğmeyi gösterir.</p>
      </div>
      {!readOnly && <div className="exam-header-actions">
        <button type="button" className="exam-period-manage-btn" data-testid="exam-period-manage-btn" onClick={() => { setPeriodPanelOpen((open) => !open); setPeriodError('') }}>
          {periodPanelOpen ? 'Dönem düzenlemeyi kapat' : 'Sınav dönemleri'}
        </button>
        <button type="button" className="exam-new-button" data-testid="exam-new-btn" disabled={!groups.length || !periods.length} onClick={() => { setFormOpen((open) => !open); setError('') }}>
          {formOpen ? 'Formu kapat' : '+ Yeni sınav'}
        </button>
      </div>}
    </div>}

    {!pageExam && periodPanelOpen && !readOnly && <section className="exam-period-panel" data-testid="exam-period-panel">
      <div className="exam-form-title"><span className="exam-step-number">00</span><div><strong>Sınav dönemleri</strong><small>Her yıl dört dönem hazır gelir. Adlarını kendi okuluna göre değiştirebilir, yeni dönem ekleyebilir, içinde sınav olmayan dönemi silebilirsin.</small></div></div>
      <ul className="exam-period-manage-list">
        {periods.map((period) => <li key={period.id}>
          <span className="exam-period-manage-name">{period.name}</span>
          <small>{period.exam_count} sınav</small>
          <button type="button" disabled={periodBusy} onClick={() => void renamePeriod(period)}>Adını değiştir</button>
          <button type="button" disabled={periodBusy || !period.can_delete} title={period.can_delete ? 'Dönemi sil' : 'Bu dönemde sınav var; önce sınavları taşıyın.'} onClick={() => void deletePeriod(period)}>Sil</button>
        </li>)}
      </ul>
      <form className="exam-period-add" onSubmit={addPeriod}>
        <label><span>Yeni dönem adı</span><input maxLength={80} value={newPeriodName} onChange={(event) => setNewPeriodName(event.target.value)} placeholder="Örn. Telafi sınavları" /></label>
        <button type="submit" disabled={periodBusy || !newPeriodName.trim()}>Dönem ekle</button>
      </form>
      {periodError && <p className="exam-error" role="alert">{periodError}</p>}
    </section>}

    {readOnly && <p className="exam-archive-note">Bu eğitim yılı arşiv olarak açıldı. Organizasyonlar görüntülenebilir; yeni kayıt oluşturulamaz.</p>}
    {!loading && groups.length === 0 && organizations.length > 0 && <div className="exam-empty"><strong>Bu eğitim yılında yeni sınava alınabilecek aktif öğrenci grubu yok.</strong><span>Mevcut organizasyon kayıtları aşağıda görüntülenebilir.</span><button type="button" onClick={onStudents}>Öğrenci kayıtlarına git</button></div>}

    {!pageExam && formOpen && <form className="exam-create-form" onSubmit={createOrganization}>
      <div className="exam-form-title"><span className="exam-step-number">01</span><div><strong>Yeni sınav</strong><small>Dönemi, adı, tarihi ve sınava girecek sınıfları seç.</small></div></div>
      <div className="exam-form-fields">
        <label><span>Sınav dönemi *</span><select required value={periodId} onChange={(event) => setPeriodId(event.target.value)}>
          {periods.length === 0 && <option value="">Dönem bulunamadı</option>}
          {periods.map((period) => <option key={period.id} value={period.id}>{period.name}</option>)}
        </select></label>
        <label><span>Sınav adı *</span><input required maxLength={160} value={name} onChange={(event) => setName(event.target.value)} placeholder="Örn. Matematik ortak sınavı" /></label>
        <label><span>Sınav tarihi *</span><input required type="date" value={examDate} onChange={(event) => setExamDate(event.target.value)} /></label>
      </div>
      <label className="exam-course-toggle"><input type="checkbox" checked={withCourses} onChange={(event) => toggleCourseMode(event.target.checked)} /><span><strong>Ders seçmek istiyorum</strong><small>Ders ekleyebilir veya daha önce kullanılan bir dersi yazabilirsin.</small></span></label>

      {withCourses ? <div className="exam-course-list">
        <datalist id="known-course-names">{courseCatalog.map((course) => <option key={course.id} value={course.name} />)}</datalist>
        {courses.map((course, index) => <article className="exam-course-card" key={course.id}>
          <div className="exam-course-heading"><strong>Ders {index + 1}</strong>{courses.length > 1 && <button type="button" onClick={() => setCourses((items) => items.filter((item) => item.id !== course.id))}>Kaldır</button>}</div>
          <label className="exam-course-name"><span>Ders adı *</span><input required maxLength={120} list="known-course-names" value={course.name} onChange={(event) => updateCourse(course.id, { name: event.target.value })} placeholder="Örn. Matematik" /></label>
          <div className="exam-group-label"><span>Bu derse girecek sınıf grupları *</span><small>Birden fazla grup seçebilirsin.</small></div>
          <GroupSelector groups={groups} selected={course.groupKeys} onChange={(update) => setCourses((items) => items.map((item) => item.id === course.id ? { ...item, groupKeys: update(item.groupKeys) } : item))} />
        </article>)}
        <button type="button" className="exam-add-course" onClick={addCourse}>+ Başka ders ekle</button>
      </div> : <div className="exam-general-groups">
        <div className="exam-group-label"><span>Sınava katılacak sınıf grupları *</span><small>Ders seçmeden genel organizasyon oluşturabilirsin.</small></div>
        <GroupSelector groups={groups} selected={generalGroupKeys} onChange={(update) => setGeneralGroupKeys(update)} />
      </div>}

      <div className="exam-selection-summary"><span>Sınava girecekler</span><strong data-testid="exam-create-summary">{new Set(withCourses ? courses.flatMap((course) => course.groupKeys) : generalGroupKeys).size} sınıf · {selectedStudentCount} öğrenci</strong></div>
      {error && <p className="exam-error" role="alert">{error}</p>}
      <div className="exam-form-footer"><span>Derslikler kendiliğinden seçilir; sonraki adımda değiştirebilirsin.</span><button type="submit" data-testid="exam-create-submit" disabled={saving || !selectedStudentCount || !selectionsComplete || !name.trim()}>{saving ? 'Oluşturuluyor…' : 'Sınavı oluştur'}</button></div>
    </form>}

    {notice && <p className="exam-room-success exam-notice-toast" role="status" data-testid="exam-notice">{notice} <button type="button" onClick={() => setNotice('')}>Kapat</button></p>}
    {error && !formOpen && <p className="exam-error" role="alert">{error}</p>}
    {loading ? <div className="exam-empty">Sınavlar yükleniyor…</div> : organizations.length === 0 && !formOpen ? <div className="exam-empty"><strong>{groups.length ? 'Henüz sınav yok.' : 'Bu eğitim yılında öğrenci grubu bulunamadı.'}</strong><span>{groups.length ? 'İlk sınavını oluştur; gerisini adım adım birlikte yaparız.' : 'Önce öğrenci listesini içe aktar veya örnek verilerle başlangıç yap.'}</span>{groups.length ? !readOnly && <button type="button" onClick={() => setFormOpen(true)}>İlk sınavı oluştur</button> : <button type="button" onClick={onStudents}>Öğrenci kayıtlarına git</button>}</div> : <div className="exam-organization-groups">
      {pageExam && <button type="button" className="exam-back" data-testid="exam-back" onClick={() => { setPageExamId(null); setViewStep(null); setActiveRoomOrganizationId(null) }}>← Sınavlara dön</button>}
      {!pageExam && groupedOrganizations.bos.length > 0 && <p className="exam-period-idle" data-testid="exam-period-idle">
        <span>Sınavı olmayan dönemler:</span> {groupedOrganizations.bos.map((item) => item.title).join(' · ')}
      </p>}
      {groupedOrganizations.dolu.map((section) => pageExam && !section.items.some((item) => item.id === pageExam.id) ? null : <section className="exam-period-section" key={section.key} data-testid={`exam-period-${section.key}`}>
        {!pageExam && <header className="exam-period-header">
          <h3>{section.title}</h3>
          <span className="exam-period-count">{section.items.length} sınav</span>
        </header>}
        <div className={pageExam ? 'exam-page' : 'exam-rows'}>{section.items.map((organization) => {
        const selectedRoomCount = organization.room_selections?.length ?? 0
        if (!pageExam) {
          // Liste: sınav başına tek yalın satır; bütün işlemler sınavın kendi sayfasında.
          const rowStage = organization.archived_at ? 'Arşivde'
            : organization.status === 'completed' ? 'Kesinleşti'
              : !(selectedRoomCount && organization.capacity_sufficient) ? 'Derslik seçilecek'
                : (candidates[organization.id]?.length ? 'Kontrol bekliyor' : 'Dağıtılacak')
          const rowDate = new Date(`${organization.exam_date}T12:00:00`)
          return <div className="exam-row" key={organization.id} data-testid={`exam-row-${organization.id}`}>
            <div className="exam-date-block"><strong>{rowDate.toLocaleDateString('tr-TR', { day: '2-digit' })}</strong><span>{rowDate.toLocaleDateString('tr-TR', { month: 'short' })}</span></div>
            <div className="exam-row-copy"><strong>{organization.name}</strong><small>{organization.group_count ?? organization.groups?.length ?? 0} sınıf · {organization.participant_count} öğrenci</small></div>
            <span className={`exam-row-stage ${organization.status === 'completed' || organization.archived_at ? 'done' : ''}`} data-testid={`exam-stage-${organization.id}`}>{rowStage}</span>
            <button type="button" className="exam-row-open" data-testid={`exam-open-${organization.id}`} onClick={() => openExamPage(organization)}>Aç</button>
          </div>
        }
        if (organization.id !== pageExam.id) return null
        const roomEditorOpen = activeRoomOrganizationId === organization.id
        const lockedByOther = Boolean(locks[organization.id] && !locks[organization.id].mine)
        const readOnly = yearReadOnly || lockedByOther || Boolean(organization.archived_at)
        const allCandidates = candidates[organization.id] ?? []
        const currentCandidate = allCandidates.find((item) => item.candidate_id === organization.selected_candidate_id) ?? allCandidates[allCandidates.length - 1]
        const isDone = organization.status === 'completed' || Boolean(organization.archived_at)
        const distributing = candidateSavingId === organization.id
        const guideStep = isDone ? 4 : finalizeConfirmId === organization.id ? 3 : currentCandidate ? 2 : selectedRoomCount && organization.capacity_sufficient ? 1 : 0
        // Görüntülenen adım: kullanıcı tamamlanmış bir adıma dönmediyse sıradaki adım.
        const shownStep = viewStep && viewStep.examId === organization.id && viewStep.at === guideStep && (isDone || viewStep.step <= guideStep) ? viewStep.step : guideStep
        const previousCandidate = currentCandidate ? allCandidates[allCandidates.indexOf(currentCandidate) - 1] ?? allCandidates.filter((item) => item !== currentCandidate).at(-1) : undefined
        const guideTitle = organization.archived_at ? 'Sınav tamamlandı ve arşivlendi'
          : isDone ? 'Sınav kesinleşti'
            : guideStep === 3 ? 'Son kontrol'
              : guideStep === 2 ? (currentCandidate!.affected_student_count === 0 && currentCandidate!.summary.waiting_count === 0 ? 'Dağıtım hazır, kural ihlali yok' : currentCandidate!.summary.waiting_count > 0 ? `${currentCandidate!.summary.waiting_count} öğrenci yer bekliyor` : `${currentCandidate!.affected_student_count} öğrenci kural ihlalinden etkileniyor`)
                : guideStep === 1 ? (organization.needs_redistribution ? 'Derslik planı değişti, yeniden dağıt' : 'Öğrencileri dersliklere dağıt')
                  : selectedRoomCount ? `${organization.capacity_deficit} koltuk eksik` : 'Derslikleri seç'
        const guideText = isDone ? 'Kapı krokilerini, yoklama çizelgelerini ve öğrenci listelerini aşağıdan yazdırabilirsin.'
          : guideStep === 3 ? 'Aşağıdaki özeti oku, onay kutusunu işaretle ve kesinleştir.'
            : guideStep === 2 ? 'Oturma planına göz at; istersen iki koltuğa sırayla tıklayarak öğrencilerin yerini değiştir. Uygunsa kesinleştir.'
              : guideStep === 1 && organization.needs_redistribution ? 'Dersliklerden birinin oturma planı değiştiği için önceki dağıtım geçersiz. Yeniden dağıtınca öğrenciler güncel plana yerleşir.'
              : guideStep === 1 ? `${selectedRoomCount} derslik ve ${organization.available_capacity} koltuk hazır. Program öğrencileri kurallara göre kendisi yerleştirir; birkaç saniye sürer.`
                : selectedRoomCount ? 'Seçili dersliklerdeki koltuk sayısı öğrenci sayısına yetmiyor. Derslik ekle ya da derslik düzenlerini kontrol et.'
                  : `Sınavın yapılacağı derslikleri işaretle. ${organization.participant_count} öğrenci için en az o kadar koltuk gerekir.`
        return <article className="exam-organization-card-wrap" key={organization.id} data-testid={`exam-card-${organization.id}`}>
          <div className="exam-organization-card">
            <div className="exam-date-block"><strong>{new Date(`${organization.exam_date}T12:00:00`).toLocaleDateString('tr-TR', { day: '2-digit' })}</strong><span>{new Date(`${organization.exam_date}T12:00:00`).toLocaleDateString('tr-TR', { month: 'short' })}</span></div>
            <div className="exam-organization-copy"><span className={`exam-status${organization.status === 'completed' || organization.archived_at ? ' done' : ''}`} data-testid={`exam-status-${organization.id}`}>{organization.archived_at ? 'Tamamlandı · Arşiv' : organization.status === 'completed' ? 'Kesinleşti' : organization.copied_from_organization_id ? 'Taslak · Kopya' : 'Taslak'}</span><h3>{organization.name}</h3><p>{organization.course_names.length ? organization.course_names.join(' · ') : 'Genel sınav'} · {organization.participant_count} öğrenci</p></div>
            <div className="exam-organization-meta">{organization.course_count > 0 && <small>{organization.course_count} ders</small>}<small>{new Date(`${organization.exam_date}T12:00:00`).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })}</small><small>{selectedRoomCount ? `${selectedRoomCount} derslik · ${organization.available_capacity} koltuk` : 'Derslik seçilmedi'}</small></div>
          </div>
          <div className="exam-classes" data-testid="exam-classes">
            <span>Sınava giren sınıflar</span>
            <ul>{(organization.groups ?? []).map((group) => <li key={`${group.class_level}-${group.section}`}><b>{group.class_level}/{group.section}</b> {group.student_count} öğrenci</li>)}</ul>
          </div>
          <div className={`exam-guide step-${guideStep}${isDone ? ' done' : ''}`} data-testid={`exam-guide-${organization.id}`}>
            <ol className="exam-guide-steps" aria-label="Sınav hazırlık adımları">
              {GUIDE_STEPS.map((label, index) => <li key={label} className={`${index < guideStep || isDone ? 'complete' : index === guideStep ? 'current' : ''} ${index === shownStep ? 'shown' : ''}`} aria-current={index === guideStep && !isDone ? 'step' : undefined}>
                <button type="button" disabled={index > guideStep && !isDone} onClick={() => setViewStep({ examId: organization.id, step: index, at: guideStep })}><span aria-hidden="true">{index < guideStep || isDone ? '✓' : index + 1}</span>{label}</button>
              </li>)}
            </ol>
            <div className="exam-guide-body">
              <div className="exam-guide-copy">
                <small>{isDone ? 'Hazır' : `Sıradaki adım · ${guideStep + 1} / ${GUIDE_STEPS.length}`}</small>
                <strong data-testid={`exam-guide-title-${organization.id}`}>{guideTitle}</strong>
                <p>{guideText}</p>
              </div>
              <div className="exam-guide-actions">
                {!readOnly && guideStep === 0 && !roomEditorOpen && shownStep === 0 && <button type="button" className="exam-guide-primary" data-testid={`exam-room-open-${organization.id}`} onClick={() => toggleRoomEditor(organization)}>{selectedRoomCount ? 'Derslikleri düzenle' : 'Derslikleri seç'}</button>}
                {!readOnly && guideStep === 1 && <button type="button" className="exam-guide-primary" data-testid={`candidate-create-${organization.id}`} disabled={distributing} onClick={() => void createCandidate(organization.id)}>{distributing ? 'Dağıtılıyor…' : 'Dağıtımı başlat'}</button>}
                {!readOnly && guideStep === 2 && currentCandidate && <>
                  <button type="button" className="exam-guide-primary" data-testid={`final-review-open-${organization.id}`} disabled={reviewLoadingId === organization.id || distributing} onClick={() => void (async () => { if (organization.selected_candidate_id !== currentCandidate.candidate_id) await selectCandidate(organization.id, currentCandidate.candidate_id); await openFinalReview(organization.id) })()}>{reviewLoadingId === organization.id ? 'Kontrol ediliyor…' : 'Kontrol et ve kesinleştir'}</button>
                  <button type="button" className="exam-guide-secondary" data-testid={`candidate-recreate-${organization.id}`} disabled={distributing || !organization.capacity_sufficient} title="Aynı dersliklerle farklı bir yerleşim üretir; şimdiki dağıtım silinmez." onClick={() => void createCandidate(organization.id)}>{distributing ? 'Dağıtılıyor…' : 'Yeniden dağıt'}</button>
                </>}
                {isDone && shownStep !== 4 && <button type="button" className="exam-guide-primary" data-testid={`exam-reports-${organization.id}`} onClick={() => setViewStep({ examId: organization.id, step: 4, at: guideStep })}>Raporları göster</button>}
              </div>
            </div>
          </div>
          {lockedByOther && <div className="edit-lock-banner" role="status" data-testid={`edit-lock-banner-${organization.id}`}><span><strong>Önizleme modu · salt okunur</strong>Bu sınav başka bir sekmede düzenleniyor. Burada yalnızca görüntüleyebilirsin.</span><button type="button" data-testid={`edit-lock-takeover-${organization.id}`} onClick={() => void takeOverEditing(organization.id)}>Düzenlemeyi bu sekmeye al</button></div>}
          {shownStep === 0 && guideStep > 0 && !roomEditorOpen && <div className="exam-rooms-summary" data-testid="exam-rooms-summary">
            <strong>Sınavın yapılacağı derslikler</strong>
            <ul>{organization.room_selections.map((room) => <li key={room.layout_id}>{room.classroom_name} · {room.available_seats} koltuk</li>)}</ul>
            {!readOnly && organization.status === 'draft' && <button type="button" className="exam-guide-secondary" onClick={() => toggleRoomEditor(organization)}>Derslikleri değiştir</button>}
          </div>}
          {roomEditorOpen && <div className="exam-room-panel">
            <div className="exam-room-panel-heading"><div><strong>1. adım · Derslikler</strong><small>Sınavın yapılacağı derslikleri işaretle. Her derslikte aktif oturma düzeni kullanılır.</small></div><span>{organization.participant_count} öğrenci</span><button type="button" className="exam-room-select-all" data-testid={`exam-room-select-all-${organization.id}`} onClick={() => { setSelectedLayoutByClassroom(Object.fromEntries(roomOptionsByClassroom.map((layouts) => layouts.find((item) => item.is_active && item.can_select) ?? layouts.find((item) => item.can_select)).filter((item): item is RoomOption => Boolean(item)).map((item) => [item.classroom_id, item.layout_id]))); setRoomMessage('') }}>Tüm derslikleri seç</button></div>
            {!roomOptionsByClassroom.length ? <div className="exam-empty room-empty"><strong>Bu eğitim yılı için oturma düzeni yok.</strong><span>Derslik oluşturup bu eğitim yılına ait masa ve oturma yeri düzeni hazırlamalısın.</span><button type="button" onClick={onClassrooms}>Derslik düzenlerine git</button></div> : <div className="exam-room-options">
              {roomOptionsByClassroom.map((layouts) => {
                const classroomId = layouts[0].classroom_id
                const classroomName = layouts[0].classroom_name
                const selectedLayoutId = selectedLayoutByClassroom[classroomId] ?? ''
                const selectedLayout = layouts.find((layout) => layout.layout_id === selectedLayoutId)
                const canSelect = layouts.some((layout) => layout.can_select)
                return <article className={`exam-room-option ${selectedLayoutId ? 'selected' : ''}`} key={classroomId}>
                  <label className="exam-room-check"><input type="checkbox" checked={Boolean(selectedLayoutId)} disabled={!canSelect && !selectedLayoutId} onChange={(event) => toggleRoom(classroomId, event.target.checked)} /><span><strong>{classroomName}</strong><small>{selectedLayout ? `${selectedLayout.available_seats} / ${selectedLayout.total_seats} kullanılabilir` : `${(layouts.find((item) => item.is_active && item.can_select) ?? layouts.find((item) => item.can_select))?.available_seats ?? 0} koltuk`}</small></span></label>
                  {selectedLayoutId && <label className="exam-layout-choice"><span>Oturma düzeni</span><select value={selectedLayoutId} onChange={(event) => { setSelectedLayoutByClassroom((selected) => ({ ...selected, [classroomId]: event.target.value })); setRoomMessage('') }}>{layouts.map((layout) => <option key={layout.layout_id} value={layout.layout_id} disabled={!layout.can_select}>{layout.layout_name} · v{layout.version}{layout.is_active ? ' · Aktif' : layout.is_latest ? '' : ' · Önceki sürüm'} · {layout.available_seats} yer</option>)}</select></label>}
                  {!canSelect && <small className="exam-layout-empty">Bu dersliğin düzeninde henüz oturma yeri yok.</small>}
                </article>
              })}
            </div>}
            <div className={`exam-capacity-check ${selectedRoomCapacity >= organization.participant_count && selectedRoomCapacity > 0 ? 'enough' : 'short'}`}><span>Toplam kullanılabilir kapasite</span><strong>{selectedRoomCapacity} / {organization.participant_count}</strong><small>{selectedRoomCapacity >= organization.participant_count && selectedRoomCapacity > 0 ? 'Kapasite yeterli. Dağıtım aşamasında yeniden doğrulanacak.' : `${Math.max(0, organization.participant_count - selectedRoomCapacity)} kişilik kapasite eksiği var.`}</small></div>
            {roomError && <p className="exam-error" role="alert">{roomError}</p>}{roomMessage && <p className="exam-room-success" role="status">{roomMessage}</p>}
            <div className="exam-room-footer"><span>Kaydedince sıradaki adım dağıtım olur.</span><button type="button" data-testid={`exam-room-save-${organization.id}`} disabled={roomSaving || !roomOptionsByClassroom.length} onClick={() => saveRoomSelection(organization.id)}>{roomSaving ? 'Kaydediliyor…' : 'Derslik seçimini kaydet'}</button></div>
          </div>}
          {candidateError && candidateErrorId === organization.id && <p className="exam-error" role="alert">{candidateError}</p>}
          <DistributionProgressOverlay organizationId={organization.id} active={candidateSavingId === organization.id} />
          {shownStep === 2 && allCandidates.map((candidate, candidateIndex) => {
            if (candidate.candidate_id !== currentCandidate?.candidate_id) return null
            const selectedPlanParticipantId = selectedPlanStudentByCandidate[candidate.candidate_id] || null
            const selectedPlanStudent = candidate.assignments.find((assignment) => assignment.participant_id === selectedPlanParticipantId) ?? null
            const violations = candidate.violations ?? []
            const focusedId = focusedViolation[candidate.candidate_id] || ''
            const violationSeatIds = new Set(violations.flatMap((item) => [item.first_seat_id, item.second_seat_id]))
            const focusedNeighborSeats = new Set(violations.filter((item) => item.first_participant_id === focusedId || item.second_participant_id === focusedId).map((item) => item.first_participant_id === focusedId ? item.second_seat_id : item.first_seat_id))
            const violatingStudents = [...new Set(violations.flatMap((item) => [item.first_participant_id, item.second_participant_id]))].map((participantId) => ({
              assignment: candidate.assignments.find((item) => item.participant_id === participantId),
              details: violations.filter((item) => item.first_participant_id === participantId || item.second_participant_id === participantId).map((item) => {
                const otherId = item.first_participant_id === participantId ? item.second_participant_id : item.first_participant_id
                const other = candidate.assignments.find((entry) => entry.participant_id === otherId)
                return `${item.reason}: ${other ? `${other.first_name} ${other.last_name} (K${other.seat_number})` : 'komşu öğrenci'}`
              }),
            })).filter((item) => item.assignment)
            const planEditingEnabled = !readOnly
              && (organization.status === 'draft' || organization.status === 'completed')
              && organization.selected_candidate_id === candidate.candidate_id
            // Sekmeler sınıf sırasıyla gelir: "9-A", "10-A"dan önce.
            const planRooms = [...candidate.plan].sort((first, second) => first.classroom_name.localeCompare(second.classroom_name, 'tr-TR', { numeric: true }))
            const activePlanRoomId = planRooms.some((room) => room.layout_id === planRoomByCandidate[candidate.candidate_id]) ? planRoomByCandidate[candidate.candidate_id] : planRooms[0]?.layout_id
            return <div className={`exam-candidate-result ${organization.selected_candidate_id === candidate.candidate_id ? 'selected' : ''}`} key={candidate.candidate_id}>
            <strong>Dağıtım {candidateIndex + 1}{candidate.pinned_classroom_ids?.length ? ` · ${candidate.pinned_classroom_ids.length} derslik sabitlenerek` : candidate.derived_from_candidate_id ? ' · Elle düzenlendi' : candidateIndex === 0 ? '' : ' · Yeniden dağıtım'}{candidate.status === 'stopped' && <em className="candidate-stopped-badge" data-testid={`candidate-stopped-badge-${candidate.candidate_id}`} title="Hesaplama kullanıcı tarafından durduruldu; o ana kadar bulunan en iyi geçerli çözüm kaydedildi.">Erken durduruldu</em>}</strong>
            <span className={`candidate-result-line ${candidate.affected_student_count === 0 && candidate.summary.waiting_count === 0 ? 'ok' : 'warn'}`} data-testid={`candidate-result-${candidate.candidate_id}`}>{candidate.assignments.length - candidate.summary.waiting_count} öğrenci yerleşti{candidate.summary.waiting_count > 0 ? ` · ${candidate.summary.waiting_count} öğrenci yer bekliyor` : ''} · {candidate.affected_student_count === 0 ? 'kural ihlali yok' : `${candidate.affected_student_count} öğrenci kural ihlalinden etkileniyor`}{candidate.status === 'stopped' ? ' · hesaplama erken durduruldu' : ''}</span>
            <details className="candidate-breakdown"><summary>Derslik ve sınıf dökümü</summary>
            <div className="candidate-room-summary">{candidate.summary.rooms.map((room) => <small key={room.classroom_id}>{room.classroom_name}: {room.assigned_students} öğrenci / {room.available_seats} yer · {room.empty_seats} boş</small>)}</div>
            <div className="candidate-group-summary">{candidate.summary.groups.map((group) => <small key={`${group.class_level}-${group.section}-${group.area ?? ''}`}>{group.class_level}/{group.section}{group.area ? ` · ${group.area}` : ''}: {group.student_count} öğrenci</small>)}</div>
            </details>
            {violatingStudents.length > 0 && <div className="candidate-violations" data-testid={`candidate-violations-${candidate.candidate_id}`}>
              <strong>Kural ihlalinden etkilenen öğrenciler · {violatingStudents.length}</strong>
              {planEditingEnabled && violatingStudents.some(({ assignment }) => candidate.violation_suggestions?.[assignment!.participant_id]?.length) && <button type="button" className="violation-fix-all" data-testid={`violation-fix-all-${candidate.candidate_id}`} disabled={movingCandidateId === candidate.candidate_id} onClick={() => void moveCandidateStudent(organization.id, candidate.candidate_id, '', '', true)}>{movingCandidateId === candidate.candidate_id ? 'Düzeltiliyor…' : 'Tümünü düzelt'}</button>}
              <small>Öğrenciye dokun: krokide yeri ve ihlale neden olan komşu yerler vurgulanır. Çiftteki öğrencilerden birini taşımak diğerinin ihlalini de giderir.</small>
              <div>{violatingStudents.map(({ assignment, details }) => {
                const suggestion = candidate.violation_suggestions?.[assignment!.participant_id]?.[0]
                return <div className="candidate-violation-item" key={assignment!.participant_id}><button type="button" data-testid={`violation-student-${assignment!.participant_id}`} className={focusedId === assignment!.participant_id ? 'active' : ''} aria-pressed={focusedId === assignment!.participant_id} onClick={() => focusViolation(candidate.candidate_id, assignment!.participant_id, assignment!.seat_id)}><b>{assignment!.class_level}/{assignment!.section} · {assignment!.first_name} {assignment!.last_name}</b><span>{assignment!.classroom_name} · Koltuk {assignment!.seat_number}</span>{details.map((detail) => <small key={detail}>{detail}</small>)}</button>
                  {suggestion ? <div className="violation-suggestion" data-testid={`violation-suggestion-${assignment!.participant_id}`}><span>Öneri: {suggestion.same_room ? '' : `${suggestion.classroom_name} · `}Koltuk {suggestion.seat_number}</span>{planEditingEnabled ? <button type="button" data-testid={`violation-fix-${assignment!.participant_id}`} disabled={movingCandidateId === candidate.candidate_id} onClick={() => void moveCandidateStudent(organization.id, candidate.candidate_id, assignment!.participant_id, suggestion.seat_id)}>Taşı ve düzelt</button> : <small>Uygulamak için adayı incelemeye al</small>}</div> : <div className="violation-suggestion none" data-testid={`violation-suggestion-none-${assignment!.participant_id}`}><span>İhlalsiz boş yer yok; yer değiştirmeyi krokiden yapın.</span></div>}
                </div>
              })}</div>
            </div>}
            <details id={`plan-details-${candidate.candidate_id}`} open>
              <summary>Oturma planı{candidate.events.length ? ` · ${candidate.events.length} işlem` : ''}</summary>
              <div className={`candidate-plan-instructions ${selectedPlanStudent ? 'has-selection' : ''}`} aria-live="polite">
                {selectedPlanStudent ? <><span><strong>{selectedPlanStudent.first_name} {selectedPlanStudent.last_name}</strong> seçildi. {selectedPlanStudent.seat_id ? 'Hedef koltuğa tıklayın; dolu koltukta öğrenciler yer değiştirir.' : 'Boş koltuğa tıklayın; dolu bir hedef seçerseniz oradaki öğrenci bekleyen havuza geçer.'}</span><button type="button" disabled={movingCandidateId === candidate.candidate_id} onClick={() => selectPlanStudent(candidate.candidate_id, selectedPlanStudent.participant_id)}>Seçimi kaldır</button></> : <span>{planEditingEnabled ? 'Yer değiştirmek için önce bir öğrencinin koltuğuna, sonra gitmesini istediğin koltuğa tıkla.' : 'Bu görünüm salt okunur.'}</span>}
              </div>
              {candidate.plan.length > 1 && <div className="plan-room-tabs" role="tablist" aria-label="Derslik seç">
                {planRooms.map((room) => {
                  const roomHasViolation = room.desks.some((desk) => desk.seats.some((seat) => violationSeatIds.has(seat.seat_id)))
                  const active = room.layout_id === activePlanRoomId
                  return <button type="button" role="tab" aria-selected={active} className={`${active ? 'active' : ''} ${roomHasViolation ? 'has-violation' : ''}`} key={room.layout_id} data-testid={`plan-room-tab-${room.layout_id}`} onClick={() => setPlanRoomByCandidate((current) => ({ ...current, [candidate.candidate_id]: room.layout_id }))}>{room.classroom_name}{roomHasViolation && <i title="Bu derslikte kural ihlali var" />}</button>
                })}
              </div>}
              {candidate.plan.filter((room) => room.layout_id === activePlanRoomId).map((room) => {
                const maxX = room.desks.length ? Math.max(...room.desks.map((desk) => desk.x)) : 0
                const maxY = room.desks.length ? Math.max(...room.desks.map((desk) => desk.y)) : 0
                const canvasWidth = Math.max(520, 150 + (maxX + 2.5) * 45)
                const canvasHeight = Math.max(160, 100 + (maxY + 1.5) * 45)
                return <section className="candidate-plan-room" key={room.layout_id}>
                  <div className="candidate-plan-heading"><strong>{room.classroom_name}</strong><span>{room.layout_name}</span></div>
                  <div className="candidate-plan-scroll"><div className="layout-canvas candidate-layout-canvas" style={{ width: canvasWidth, height: canvasHeight }}>
                    <div className="board-label" style={{ left: canvasWidth / 2 - 70 }}>TAHTA</div>
                    {room.desks.map((desk) => <div className="plan-desk-position candidate-plan-desk" style={{ left: 70 + desk.x * 45, top: 50 + desk.y * 45 }} key={desk.desk_id}>
                      <small>{desk.label}</small><div className="plan-seats">{desk.seats.map((seat) => {
                        const seatStudent = seat.student
                        const isSelectedStudent = seatStudent?.participant_id === selectedPlanParticipantId
                        const seatIsTarget = Boolean(selectedPlanParticipantId && seat.is_available && seatStudent?.participant_id !== selectedPlanParticipantId)
                        const seatClassName = `candidate-plan-seat ${!seat.is_available ? 'unavailable' : seatStudent ? 'occupied' : 'empty'} ${isSelectedStudent ? 'selected-student' : ''} ${seatIsTarget ? 'target-seat' : ''} ${violationSeatIds.has(seat.seat_id) ? 'has-violation' : ''} ${focusedId && seatStudent?.participant_id === focusedId ? 'violation-focus' : ''} ${focusedNeighborSeats.has(seat.seat_id) ? 'violation-neighbor' : ''}`
                        const seatDescription = seatStudent ? `${seatStudent.class_level}/${seatStudent.section} · ${seatStudent.first_name} ${seatStudent.last_name} · ${seatStudent.school_number}` : seat.is_available ? 'Boş kullanılabilir koltuk' : 'Kullanım dışı koltuk'
                        return <button className={seatClassName} type="button" key={seat.seat_id} data-seat-id={seat.seat_id} disabled={!planEditingEnabled || movingCandidateId === candidate.candidate_id || !seat.is_available} aria-pressed={isSelectedStudent} aria-label={`Koltuk ${seat.seat_number}: ${seatDescription}`} title={`Koltuk ${seat.seat_number} · ${seatDescription}`} onClick={() => {
                          if (selectedPlanParticipantId) {
                            if (seatStudent?.participant_id === selectedPlanParticipantId) selectPlanStudent(candidate.candidate_id, selectedPlanParticipantId)
                            else void moveCandidateStudent(organization.id, candidate.candidate_id, selectedPlanParticipantId, seat.seat_id)
                          } else if (seatStudent) selectPlanStudent(candidate.candidate_id, seatStudent.participant_id)
                        }}>{seat.seat_number}</button>
                      })}</div>
                      {desk.seats.some((seat) => seat.student) && <div className="candidate-plan-students">{desk.seats.filter((seat) => seat.student).map((seat) => <span key={seat.seat_id}>K{seat.seat_number} · {seat.student!.class_level}/{seat.student!.section} {seat.student!.first_name} {seat.student!.last_name}</span>)}</div>}
                    </div>)}
                  </div></div>
                </section>
              })}
              <div className="candidate-plan-legend"><span><i className="occupied" /> Dolu</span><span><i className="empty" /> Boş kullanılabilir</span><span><i className="unavailable" /> Kullanım dışı</span>{violations.length > 0 && <><span><i className="has-violation" /> İhlalli yer</span><span><i className="violation-focus" /> Seçilen öğrenci</span><span><i className="violation-neighbor" /> İhlale neden olan komşu</span></>}</div>
              <div className="candidate-waiting-pool"><strong>Bekleyen öğrenci havuzu · {candidate.summary.waiting_count}</strong>
                {candidate.assignments.filter((assignment) => !assignment.seat_id).length ? candidate.assignments.filter((assignment) => !assignment.seat_id).map((assignment) => <div className={`candidate-waiting-student ${selectedPlanParticipantId === assignment.participant_id ? 'selected' : ''}`} key={assignment.participant_id}><span>{assignment.class_level}/{assignment.section} · {assignment.first_name} {assignment.last_name} · {assignment.school_number}<small>Henüz koltuğa yerleşmedi</small></span><button type="button" disabled={!planEditingEnabled || movingCandidateId === candidate.candidate_id} aria-pressed={selectedPlanParticipantId === assignment.participant_id} onClick={() => selectPlanStudent(candidate.candidate_id, assignment.participant_id)}>{selectedPlanParticipantId === assignment.participant_id ? 'Seçildi' : 'Öğrenciyi seç'}</button><label><span className="sr-only">Boş koltuk seç</span><select value="" disabled={!planEditingEnabled || movingCandidateId === candidate.candidate_id} onChange={(event) => { if (event.target.value) void moveCandidateStudent(organization.id,candidate.candidate_id,assignment.participant_id,event.target.value) }}><option value="">Boş koltuğa yerleştir…</option>{candidate.available_seats.filter((seat) => !candidate.assignments.some((assigned) => assigned.seat_id === seat.seat_id)).map((seat) => <option key={seat.seat_id} value={seat.seat_id}>{seat.classroom_name} · Koltuk {seat.seat_number}</option>)}</select></label></div>) : <span className="candidate-pool-empty">Bekleyen öğrenci yok.</span>}
              </div>
              <details className="candidate-assignment-details"><summary>Tüm öğrencileri düzenle</summary><div>{candidate.assignments.map((assignment) => <label className="candidate-seat-row" key={assignment.participant_id}><span>{assignment.class_level}/{assignment.section} · {assignment.first_name} {assignment.last_name} · {assignment.school_number}<small>{assignment.seat_id ? `${assignment.classroom_name} · Koltuk ${assignment.seat_number}` : 'Bekleyen öğrenci havuzu'}</small></span><div><select value={assignment.seat_id ?? ''} disabled={!planEditingEnabled || movingCandidateId === candidate.candidate_id} onChange={(event) => { if (event.target.value) void moveCandidateStudent(organization.id,candidate.candidate_id,assignment.participant_id,event.target.value); else if (assignment.seat_id) void moveCandidateToPool(organization.id,candidate.candidate_id,assignment.participant_id) }}><option value="">Bekleyen havuz</option>{candidate.available_seats.map((seat) => <option key={seat.seat_id} value={seat.seat_id}>{seat.classroom_name} · Koltuk {seat.seat_number}</option>)}</select>{assignment.seat_id && organization.selected_candidate_id === candidate.candidate_id && <button type="button" disabled={!planEditingEnabled || movingCandidateId === candidate.candidate_id} onClick={() => void moveCandidateToPool(organization.id,candidate.candidate_id,assignment.participant_id)}>Havuza al</button>}</div></label>)}</div></details>
            </details>
            {organization.status === 'completed' && organization.selected_candidate_id === candidate.candidate_id && <div className="candidate-history-panel">
              <div className="candidate-history-toolbar"><strong>Değişiklik geçmişi · {candidate.events.length} işlem</strong><div><button type="button" disabled={readOnly || !candidate.history.can_undo || movingCandidateId === candidate.candidate_id} onClick={() => void changeCompletedHistory(organization.id,candidate.candidate_id,'undo')}>Geri al</button><button type="button" disabled={readOnly || !candidate.history.can_redo || movingCandidateId === candidate.candidate_id} onClick={() => void changeCompletedHistory(organization.id,candidate.candidate_id,'redo')}>Yinele</button></div></div>
              {candidate.events.length ? <ol>{[...candidate.events].reverse().map((event) => {
                const from = event.from_seat_id ? candidate.available_seats.find((seat) => seat.seat_id === event.from_seat_id)?.seat_number : null
                const to = event.to_seat_id ? candidate.available_seats.find((seat) => seat.seat_id === event.to_seat_id)?.seat_number : null
                const movement = `Koltuk ${from ?? 'Havuz'} → ${to ?? 'Havuz'}`
                return <li key={event.id}><span><strong>{historyEventLabel(event.event_type)}</strong> · {event.participant_name} · {movement}{event.displaced_participant_id ? ' · Takas' : ''}</span><time>{new Date(event.created_at).toLocaleString('tr-TR')}</time></li>
              })}</ol> : <span>Henüz manuel değişiklik yapılmadı.</span>}
            </div>}
            {organization.status === 'draft' && !readOnly && organization.selected_candidate_id !== candidate.candidate_id && <button type="button" data-testid={`candidate-select-${candidate.candidate_id}`} onClick={() => void selectCandidate(organization.id, candidate.candidate_id)}>Bu dağıtımı düzenlemeye aç</button>}
          </div>
          })}
          {shownStep === 2 && previousCandidate && organization.status === 'draft' && !readOnly && <button type="button" className="exam-guide-secondary distribution-back" data-testid={`distribution-back-${organization.id}`} onClick={() => void selectCandidate(organization.id, previousCandidate.candidate_id)}>Önceki dağıtıma dön</button>}
          {isDone && shownStep === 4 && <div className="exam-reports-step" data-testid="exam-reports-step"><ReportCenter academicYearId={academicYearId} academicYearLabel="" onExams={() => undefined} organizationId={organization.id} /></div>}
          {reviewError && !finalizeConfirmId && <p className="exam-error" role="alert">{reviewError}</p>}
          {finalizeConfirmId === organization.id && finalReviews[organization.id] && <div className="final-review-panel"><strong>Son kontrol · kesinleştirme öncesi</strong><span>{finalReviews[organization.id].seated_count}/{finalReviews[organization.id].participant_count} öğrenci oturuyor · {finalReviews[organization.id].unassigned_count} bekleyen · {finalReviews[organization.id].available_capacity} kullanılabilir koltuk · {finalReviews[organization.id].empty_seats} boş koltuk</span><span>{finalReviews[organization.id].violation_count} komşuluk ihlali · {finalReviews[organization.id].affected_student_count} öğrenci etkileniyor</span><div>{finalReviews[organization.id].rooms.map((room) => <small key={room.classroom_id}>{room.classroom_name}: {room.assigned_students}/{room.available_seats} dolu · {room.empty_seats} boş</small>)}</div><p>Başlangıç kapasitesi fiziksel sınıf planının yerine geçmez. Masa, sıra, koridor ve kullanılabilir koltukları gerçek derslikle karşılaştırın.</p>{!finalReviews[organization.id].can_finalize && <p className="exam-error">Bekleyen öğrenci kalmamalı ve kural ihlalinden etkilenen öğrenci sayısı beşi aşmamalı.</p>}<label><input type="checkbox" data-testid="finalize-confirm-checkbox" checked={finalizeConfirmed} onChange={(event) => setFinalizeConfirmed(event.target.checked)} />Dağıtımı kontrol ettim; seçilen dersliklerin fiziksel planlarını doğruladım ve sınavı kesinleştirmek istiyorum.</label>{reviewError && <p className="exam-error" role="alert">{reviewError}</p>}<div><button type="button" onClick={() => setFinalizeConfirmId(null)}>Vazgeç</button><button type="button" data-testid="finalize-submit-btn" disabled={!finalizeConfirmed || !finalReviews[organization.id].can_finalize || finalizing} onClick={() => void finalizeOrganization(organization.id)}>{finalizing ? 'Kesinleştiriliyor…' : 'Onayla ve kesinleştir'}</button></div></div>}
          <details className="exam-advanced" data-testid={`exam-advanced-${organization.id}`}>
            <summary>{isDone ? 'İleri düzey: arşivle, kopyala, öğrenci listesini karşılaştır' : 'İleri düzey: kurallar, derslik sabitleme, dönem'}</summary>
            <div className="exam-advanced-body">
          {!readOnly && periods.length > 0 && <label className="exam-card-period" data-testid={`exam-period-select-${organization.id}`}>
            <span>Dönem</span>
            <select
              value={organization.exam_period_id ?? ''}
              disabled={periodBusy}
              onChange={(event) => void moveOrganizationToPeriod(organization.id, event.target.value)}
            >
              {!organization.exam_period_id && <option value="">Dönem atanmamış</option>}
              {periods.map((period) => <option key={period.id} value={period.id}>{period.name}</option>)}
            </select>
          </label>}
              {!readOnly && organization.status === 'draft' && guideStep > 0 && <div className="exam-rule-toolbar"><button type="button" data-testid={`exam-room-edit-${organization.id}`} onClick={() => toggleRoomEditor(organization)}>{roomEditorOpen ? 'Derslik seçimini kapat' : 'Derslikleri değiştir'}</button><span>Derslik seçimi değişirse dağıtım yeniden yapılır.</span></div>}
          {organization.status === 'draft' && <div className="exam-rule-toolbar"><button type="button" disabled={readOnly || organization.status !== 'draft'} onClick={() => toggleRuleEditor(organization)}>{activeRuleOrganizationId === organization.id ? 'Kuralları kapat' : 'Oturma kurallarını değiştir'}</button><span>Kimlerin yan yana ya da önlü arkalı oturamayacağını belirler. Hepsi açık gelir.</span></div>}
          {activeRuleOrganizationId === organization.id && ruleDraft && <div className="exam-rule-panel"><div className="exam-room-panel-heading"><div><strong>Oturma kuralları</strong><small>Kuralları birbirinden bağımsız açıp kapatabilirsin. Kurallar yalnızca kullanılabilir fiziksel koltuklar arasında değerlendirilir.</small></div></div><div className="exam-rule-list">{ruleLabels.map((rule) => <label key={rule.key}><span><strong>{rule.title}</strong><small>{rule.position}</small></span><input type="checkbox" checked={ruleDraft[rule.key]} onChange={(event) => setRuleDraft((current) => current ? { ...current, [rule.key]: event.target.checked } : current)} /></label>)}</div>{ruleError && <p className="exam-error" role="alert">{ruleError}</p>}{ruleMessage && <p className="exam-room-success" role="status">{ruleMessage}</p>}<div className="exam-room-footer"><span>Dağıtım adayı oluşturulurken bu ayarlar kullanılacak.</span><button type="button" disabled={ruleSaving} onClick={() => saveRules(organization.id)}>{ruleSaving ? 'Kaydediliyor…' : 'Kuralları kaydet'}</button></div></div>}
          <ExamLifecyclePanel organization={organization} candidates={candidates[organization.id] ?? []} readOnly={readOnly} yearReadOnly={yearReadOnly} onReload={(text) => { setNotice(text ?? ''); setReloadKey((key) => key + 1) }} />
            </div>
          </details>
        </article>
      })}</div>
        {!pageExam && section.orphan && <p className="exam-period-empty">Bu sınavlar bir dönem seçilmeden oluşturulmuş. Kartın üstündeki dönem kutusundan taşıyabilirsin.</p>}
      </section>)}
    </div>}
  </section>
}
