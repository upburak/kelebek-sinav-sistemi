import { useEffect, useMemo, useState, type FormEvent } from 'react'

type GroupOption = {
  class_level: string
  section: string
  area: string | null
  student_count: number
}

type CourseOption = { id: string; name: string }
type CourseDraft = { id: number; name: string; groupKeys: string[] }
type RuleKey = 'prevent_same_section_adjacent' | 'prevent_same_section_front_back' | 'prevent_different_grade_same_area_adjacent' | 'prevent_different_grade_same_area_front_back' | 'prevent_same_grade_area_adjacent' | 'prevent_same_grade_area_front_back'
type RuleSet = Record<RuleKey, boolean>
type CandidatePreview = { candidate_id: string; run_id: string; generation_index: number; derived_from_candidate_id: string | null; status: string; affected_student_count: number; events: { event_type: string; participant_id: string; displaced_participant_id: string | null; from_seat_id: string; to_seat_id: string; created_at: string }[]; available_seats: { seat_id: string; seat_number: number; classroom_id: string; classroom_name: string }[]; summary: { groups: { class_level: string; section: string; area: string | null; student_count: number }[]; rooms: { classroom_id: string; classroom_name: string; available_seats: number; assigned_students: number; empty_seats: number }[] }; assignments: { participant_id: string; seat_id: string; seat_number: number; classroom_id: string; classroom_name: string; first_name: string; last_name: string; school_number: string; class_level: string; section: string }[] }
type FinalReview = { candidate_id: string; participant_count: number; available_capacity: number; empty_seats: number; affected_student_count: number; violation_count: number; can_finalize: boolean; rooms: { classroom_id: string; classroom_name: string; available_seats: number; assigned_students: number; empty_seats: number }[] }
const ruleLabels: { key: RuleKey; title: string; position: string }[] = [
  { key: 'prevent_same_section_adjacent', title: 'Aynı şubedeki öğrenciler', position: 'Yan yana' },
  { key: 'prevent_same_section_front_back', title: 'Aynı şubedeki öğrenciler', position: 'Önlü arkalı' },
  { key: 'prevent_different_grade_same_area_adjacent', title: 'Farklı sınıf seviyelerinde aynı alan öğrencileri', position: 'Yan yana' },
  { key: 'prevent_different_grade_same_area_front_back', title: 'Farklı sınıf seviyelerinde aynı alan öğrencileri', position: 'Önlü arkalı' },
  { key: 'prevent_same_grade_area_adjacent', title: 'Aynı sınıf seviyesi ve alandaki öğrenciler', position: 'Yan yana' },
  { key: 'prevent_same_grade_area_front_back', title: 'Aynı sınıf seviyesi ve alandaki öğrenciler', position: 'Önlü arkalı' },
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
}
type ExamOrganization = {
  id: string
  name: string
  exam_date: string
  status: 'draft' | 'completed'
  course_names: string[]
  course_count: number
  participant_count: number
  room_selections: { classroom_id: string; classroom_name: string; layout_id: string; layout_name: string; version: number; available_seats: number }[]
  available_capacity: number
  capacity_sufficient: boolean
  capacity_deficit: number
  rules: RuleSet
  selected_candidate_id: string | null
}

type Props = {
  academicYearId: string | null
  academicYearLabel: string
  readOnly: boolean
  onStudents: () => void
  onClassrooms: () => void
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

function GroupSelector({
  groups,
  selected,
  onChange,
}: {
  groups: GroupOption[]
  selected: string[]
  onChange: (keys: string[]) => void
}) {
  function toggle(key: string) {
    onChange(selected.includes(key) ? selected.filter((item) => item !== key) : [...selected, key])
  }

  return <div className="exam-group-options">
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

export default function ExamOrganizer({ academicYearId, academicYearLabel, readOnly, onStudents, onClassrooms }: Props) {
  const [organizations, setOrganizations] = useState<ExamOrganization[]>([])
  const [groups, setGroups] = useState<GroupOption[]>([])
  const [courseCatalog, setCourseCatalog] = useState<CourseOption[]>([])
  const [roomOptions, setRoomOptions] = useState<RoomOption[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
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
  const [finalReviews, setFinalReviews] = useState<Record<string, FinalReview>>({})
  const [reviewLoadingId, setReviewLoadingId] = useState<string | null>(null)
  const [reviewError, setReviewError] = useState('')
  const [finalizeConfirmId, setFinalizeConfirmId] = useState<string | null>(null)
  const [finalizeConfirmed, setFinalizeConfirmed] = useState(false)
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
    ])
      .then(async ([organizationResponse, groupResponse, courseResponse, roomResponse]) => {
        const [organizationData, groupData, courseData, roomData] = await Promise.all([
          organizationResponse.json(), groupResponse.json(), courseResponse.json(), roomResponse.json(),
        ])
        if (!organizationResponse.ok) throw new Error(organizationData.error ?? 'Organizasyonlar yüklenemedi.')
        if (!groupResponse.ok) throw new Error(groupData.error ?? 'Öğrenci grupları yüklenemedi.')
        if (!courseResponse.ok) throw new Error(courseData.error ?? 'Ders listesi yüklenemedi.')
        if (!roomResponse.ok) throw new Error(roomData.error ?? 'Derslik düzenleri yüklenemedi.')
        const loadedOrganizations = organizationData.organizations as ExamOrganization[]
        setOrganizations(loadedOrganizations)
        setGroups(groupData.groups as GroupOption[])
        setCourseCatalog(courseData.courses as CourseOption[])
        setRoomOptions(roomData.rooms as RoomOption[])
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
  }, [academicYearId])

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
      const organization = data.organization as ExamOrganization
      setOrganizations((items) => [organization, ...items].sort((a, b) => b.exam_date.localeCompare(a.exam_date)))
      setActiveRoomOrganizationId(organization.id)
      setSelectedLayoutByClassroom({})
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
      setCandidates((current) => ({ ...current, [organizationId]: [...(current[organizationId] ?? []), data.candidate as CandidatePreview] }))
    } catch (reason) {
      setCandidateError(reason instanceof Error ? reason.message : 'Dağıtım adayı oluşturulamadı.')
      setCandidateErrorId(organizationId)
    } finally {
      setCandidateSavingId(null)
    }
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
    } catch (reason) {
      setCandidateError(reason instanceof Error ? reason.message : 'Aday seçilemedi.')
      setCandidateErrorId(organizationId)
    }
  }

  async function moveCandidateStudent(organizationId: string, candidateId: string, participantId: string, targetSeatId: string) {
    setCandidateError('')
    setCandidateErrorId(null)
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/distribution-candidates/${encodeURIComponent(candidateId)}/moves`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ participant_id: participantId, target_seat_id: targetSeatId }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Öğrenci taşınamadı.')
      const child = data.candidate as CandidatePreview
      setCandidates((current) => ({ ...current, [organizationId]: [...(current[organizationId] ?? []), child] }))
      setOrganizations((items) => items.map((item) => item.id === organizationId ? { ...item, selected_candidate_id: child.candidate_id } : item))
      setFinalReviews((current) => { const next = { ...current }; delete next[organizationId]; return next })
    } catch (reason) {
      setCandidateError(reason instanceof Error ? reason.message : 'Öğrenci taşınamadı.')
      setCandidateErrorId(organizationId)
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
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/finalize`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Organizasyon kesinleştirilemedi.')
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

  return <section className="exam-organizer" aria-labelledby="exam-organizer-title">
    <div className="exam-organizer-heading">
      <div>
        <span className="eyebrow">SINAV HAZIRLIĞI · {academicYearLabel || 'EĞİTİM YILI'}</span>
        <h2 id="exam-organizer-title">Sınav organizasyonları</h2>
        <p>Önce sınavı ve katılacak öğrenci gruplarını belirle. Ders seçmek isteğe bağlıdır.</p>
      </div>
      {!readOnly && <button type="button" className="exam-new-button" disabled={!groups.length} onClick={() => { setFormOpen((open) => !open); setError('') }}>
        {formOpen ? 'Formu kapat' : '+ Yeni organizasyon'}
      </button>}
    </div>

    {readOnly && <p className="exam-archive-note">Bu eğitim yılı arşiv olarak açıldı. Organizasyonlar görüntülenebilir; yeni kayıt oluşturulamaz.</p>}
    {!loading && groups.length === 0 && organizations.length > 0 && <div className="exam-empty"><strong>Bu eğitim yılında yeni sınava alınabilecek aktif öğrenci grubu yok.</strong><span>Mevcut organizasyon kayıtları aşağıda görüntülenebilir.</span><button type="button" onClick={onStudents}>Öğrenci kayıtlarına git</button></div>}

    {formOpen && <form className="exam-create-form" onSubmit={createOrganization}>
      <div className="exam-form-title"><span className="exam-step-number">01</span><div><strong>Organizasyon bilgileri</strong><small>İsim ve sınav tarihi, taslak kaydına eklenir.</small></div></div>
      <div className="exam-form-fields">
        <label><span>Organizasyon / sınav adı *</span><input required maxLength={160} value={name} onChange={(event) => setName(event.target.value)} placeholder="Örn. 1. dönem ortak sınavları" /></label>
        <label><span>Sınav tarihi *</span><input required type="date" value={examDate} onChange={(event) => setExamDate(event.target.value)} /></label>
      </div>
      <label className="exam-course-toggle"><input type="checkbox" checked={withCourses} onChange={(event) => toggleCourseMode(event.target.checked)} /><span><strong>Ders seçmek istiyorum</strong><small>Ders ekleyebilir veya daha önce kullanılan bir dersi yazabilirsin.</small></span></label>

      {withCourses ? <div className="exam-course-list">
        <datalist id="known-course-names">{courseCatalog.map((course) => <option key={course.id} value={course.name} />)}</datalist>
        {courses.map((course, index) => <article className="exam-course-card" key={course.id}>
          <div className="exam-course-heading"><strong>Ders {index + 1}</strong>{courses.length > 1 && <button type="button" onClick={() => setCourses((items) => items.filter((item) => item.id !== course.id))}>Kaldır</button>}</div>
          <label className="exam-course-name"><span>Ders adı *</span><input required maxLength={120} list="known-course-names" value={course.name} onChange={(event) => updateCourse(course.id, { name: event.target.value })} placeholder="Örn. Matematik" /></label>
          <div className="exam-group-label"><span>Bu derse girecek sınıf grupları *</span><small>Birden fazla grup seçebilirsin.</small></div>
          <GroupSelector groups={groups} selected={course.groupKeys} onChange={(keys) => updateCourse(course.id, { groupKeys: keys })} />
        </article>)}
        <button type="button" className="exam-add-course" onClick={addCourse}>+ Başka ders ekle</button>
      </div> : <div className="exam-general-groups">
        <div className="exam-group-label"><span>Sınava katılacak sınıf grupları *</span><small>Ders seçmeden genel organizasyon oluşturabilirsin.</small></div>
        <GroupSelector groups={groups} selected={generalGroupKeys} onChange={setGeneralGroupKeys} />
      </div>}

      <div className="exam-selection-summary"><span>Katılımcı ön izlemesi</span><strong>{selectedStudentCount} farklı öğrenci</strong></div>
      {error && <p className="exam-error" role="alert">{error}</p>}
      <div className="exam-form-footer"><span>Bu adım taslak oluşturur; derslik ve oturma düzeni sonraki aşamada seçilir.</span><button type="submit" disabled={saving || !selectedStudentCount || !selectionsComplete || !name.trim()}>{saving ? 'Taslak oluşturuluyor…' : 'Organizasyon taslağı oluştur'}</button></div>
    </form>}

    {error && !formOpen && <p className="exam-error" role="alert">{error}</p>}
    {loading ? <div className="exam-empty">Organizasyonlar yükleniyor…</div> : organizations.length === 0 && !formOpen ? <div className="exam-empty"><strong>{groups.length ? 'Henüz sınav organizasyonu yok.' : 'Bu eğitim yılında öğrenci grubu bulunamadı.'}</strong><span>{groups.length ? 'İlk taslağı oluştur; ders seçmek zorunlu değil.' : 'Önce öğrenci listesini içe aktar veya örnek verilerle başlangıç yap.'}</span>{groups.length ? !readOnly && <button type="button" onClick={() => setFormOpen(true)}>İlk organizasyonu oluştur</button> : <button type="button" onClick={onStudents}>Öğrenci kayıtlarına git</button>}</div> : <div className="exam-organization-list">
      {organizations.map((organization) => {
        const selectedRoomCount = organization.room_selections?.length ?? 0
        const roomEditorOpen = activeRoomOrganizationId === organization.id
        return <article className="exam-organization-card-wrap" key={organization.id}>
          <div className="exam-organization-card">
            <div className="exam-date-block"><strong>{new Date(`${organization.exam_date}T12:00:00`).toLocaleDateString('tr-TR', { day: '2-digit' })}</strong><span>{new Date(`${organization.exam_date}T12:00:00`).toLocaleDateString('tr-TR', { month: 'short' })}</span></div>
            <div className="exam-organization-copy"><span className="exam-status">{organization.status === 'completed' ? 'Tamamlandı' : 'Taslak'}</span><h3>{organization.name}</h3><p>{organization.course_names.length ? organization.course_names.join(' · ') : 'Genel sınav'} · {organization.participant_count} öğrenci</p></div>
            <div className="exam-organization-meta"><small>{organization.course_count} ders</small><small>{organization.exam_date}</small><small>{selectedRoomCount ? `${selectedRoomCount} derslik · ${organization.available_capacity} kullanılabilir yer` : 'Derslik seçilmedi'}</small></div>
            <button className="exam-room-open" type="button" disabled={readOnly || organization.status !== 'draft'} onClick={() => toggleRoomEditor(organization)}>{roomEditorOpen ? 'Derslik seçimini kapat' : selectedRoomCount ? 'Derslikleri düzenle' : 'Derslik seç'}</button>
          </div>
          {roomEditorOpen && <div className="exam-room-panel">
            <div className="exam-room-panel-heading"><div><strong>Adım 02 · Derslik ve kapasite</strong><small>Her fiziksel derslikten bir düzen seç. Kullanım dışı yerler kapasiteye sayılmaz.</small></div><span>{organization.participant_count} öğrenci</span></div>
            {!roomOptionsByClassroom.length ? <div className="exam-empty room-empty"><strong>Bu eğitim yılı için oturma düzeni yok.</strong><span>Derslik oluşturup bu eğitim yılına ait masa ve oturma yeri düzeni hazırlamalısın.</span><button type="button" onClick={onClassrooms}>Derslik düzenlerine git</button></div> : <div className="exam-room-options">
              {roomOptionsByClassroom.map((layouts) => {
                const classroomId = layouts[0].classroom_id
                const classroomName = layouts[0].classroom_name
                const selectedLayoutId = selectedLayoutByClassroom[classroomId] ?? ''
                const selectedLayout = layouts.find((layout) => layout.layout_id === selectedLayoutId)
                const canSelect = layouts.some((layout) => layout.can_select)
                return <article className={`exam-room-option ${selectedLayoutId ? 'selected' : ''}`} key={classroomId}>
                  <label className="exam-room-check"><input type="checkbox" checked={Boolean(selectedLayoutId)} disabled={!canSelect && !selectedLayoutId} onChange={(event) => toggleRoom(classroomId, event.target.checked)} /><span><strong>{classroomName}</strong><small>{selectedLayout ? `${selectedLayout.available_seats} / ${selectedLayout.total_seats} kullanılabilir` : `${layouts.length} düzen seçeneği`}</small></span></label>
                  {selectedLayoutId && <label className="exam-layout-choice"><span>Oturma düzeni</span><select value={selectedLayoutId} onChange={(event) => { setSelectedLayoutByClassroom((selected) => ({ ...selected, [classroomId]: event.target.value })); setRoomMessage('') }}>{layouts.map((layout) => <option key={layout.layout_id} value={layout.layout_id} disabled={!layout.can_select}>{layout.layout_name} · v{layout.version}{layout.is_latest ? ' · Güncel' : ' · Önceki sürüm'} · {layout.available_seats} yer</option>)}</select></label>}
                  {!canSelect && <small className="exam-layout-empty">Bu dersliğin düzeninde henüz oturma yeri yok.</small>}
                </article>
              })}
            </div>}
            <div className={`exam-capacity-check ${selectedRoomCapacity >= organization.participant_count && selectedRoomCapacity > 0 ? 'enough' : 'short'}`}><span>Toplam kullanılabilir kapasite</span><strong>{selectedRoomCapacity} / {organization.participant_count}</strong><small>{selectedRoomCapacity >= organization.participant_count && selectedRoomCapacity > 0 ? 'Kapasite yeterli. Dağıtım aşamasında yeniden doğrulanacak.' : `${Math.max(0, organization.participant_count - selectedRoomCapacity)} kişilik kapasite eksiği var.`}</small></div>
            {roomError && <p className="exam-error" role="alert">{roomError}</p>}{roomMessage && <p className="exam-room-success" role="status">{roomMessage}</p>}
            <div className="exam-room-footer"><span>Bu seçim taslakta saklanır. Öğrenciler koltuklara henüz dağıtılmaz.</span><button type="button" disabled={roomSaving || !roomOptionsByClassroom.length} onClick={() => saveRoomSelection(organization.id)}>{roomSaving ? 'Kaydediliyor…' : 'Derslik seçimini kaydet'}</button></div>
          </div>}
          <div className="exam-rule-toolbar"><button type="button" disabled={readOnly || organization.status !== 'draft'} onClick={() => toggleRuleEditor(organization)}>{activeRuleOrganizationId === organization.id ? 'Kuralları kapat' : 'Dağıtım kuralları'}</button><span>Altı komşuluk kuralı bu sınava özeldir.</span></div>
          <div className="exam-rule-toolbar"><button type="button" disabled={readOnly || organization.status !== 'draft' || candidateSavingId === organization.id || !organization.capacity_sufficient} onClick={() => void createCandidate(organization.id)}>{candidateSavingId === organization.id ? 'Aday hesaplanıyor…' : (candidates[organization.id]?.length ? 'Yeni alternatif üret' : 'İlk dağıtım adayını oluştur')}</button><span>{organization.capacity_sufficient ? `${candidates[organization.id]?.length ?? 0} kayıtlı aday · kapasite yeterli` : `${organization.capacity_deficit} kişilik kapasite eksiği var`}</span></div>
          {candidateError && candidateErrorId === organization.id && <p className="exam-error" role="alert">{candidateError}</p>}
          {(candidates[organization.id] ?? []).map((candidate, candidateIndex) => <div className={`exam-candidate-result ${organization.selected_candidate_id === candidate.candidate_id ? 'selected' : ''}`} key={candidate.candidate_id}><strong>Aday {candidateIndex + 1}{candidate.derived_from_candidate_id ? ' · Manuel sürüm' : candidateIndex === 0 ? ' · İlk dağıtım' : ' · Alternatif'}</strong><span>{candidate.assignments.length} öğrenci · {candidate.affected_student_count} kural ihlalinden etkilenen öğrenci · {candidate.status === 'optimal' ? 'Denge açısından en iyi bulundu' : candidate.status === 'manual' ? 'Manuel değişiklik' : 'Geçerli aday'}</span><div className="candidate-room-summary">{candidate.summary.rooms.map((room) => <small key={room.classroom_id}>{room.classroom_name}: {room.assigned_students} öğrenci / {room.available_seats} yer · {room.empty_seats} boş</small>)}</div><div className="candidate-group-summary">{candidate.summary.groups.map((group) => <small key={`${group.class_level}-${group.section}-${group.area ?? ''}`}>{group.class_level}/{group.section}{group.area ? ` · ${group.area}` : ''}: {group.student_count} öğrenci</small>)}</div><details><summary>Oturma listesini gör{candidate.events.length ? ` · ${candidate.events.length} işlem` : ''}</summary><div>{candidate.assignments.map((assignment) => <label className="candidate-seat-row" key={assignment.participant_id}><span>{assignment.class_level}/{assignment.section} · {assignment.first_name} {assignment.last_name} · {assignment.school_number}</span><select value={assignment.seat_id} disabled={readOnly || organization.status !== 'draft' || organization.selected_candidate_id !== candidate.candidate_id} onChange={(event) => void moveCandidateStudent(organization.id,candidate.candidate_id,assignment.participant_id,event.target.value)}>{candidate.available_seats.map((seat) => <option key={seat.seat_id} value={seat.seat_id}>{seat.classroom_name} · Koltuk {seat.seat_number}</option>)}</select></label>)}</div></details><button type="button" disabled={readOnly || organization.status !== 'draft'} onClick={() => void selectCandidate(organization.id,candidate.candidate_id)}>{organization.selected_candidate_id === candidate.candidate_id ? 'Seçili aday' : 'Bu adayı incelemeye al'}</button>{organization.selected_candidate_id === candidate.candidate_id && <button type="button" className="candidate-review-button" disabled={reviewLoadingId === organization.id} onClick={() => void openFinalReview(organization.id)}>{reviewLoadingId === organization.id ? 'Son kontrol…' : 'Son kontrolü aç'}</button>}</div>)}
          {reviewError && !finalizeConfirmId && <p className="exam-error" role="alert">{reviewError}</p>}
          {finalizeConfirmId === organization.id && finalReviews[organization.id] && <div className="final-review-panel"><strong>Son kontrol · kesinleştirme öncesi</strong><span>{finalReviews[organization.id].participant_count} öğrenci · {finalReviews[organization.id].available_capacity} kullanılabilir koltuk · {finalReviews[organization.id].empty_seats} boş koltuk</span><span>{finalReviews[organization.id].violation_count} komşuluk ihlali · {finalReviews[organization.id].affected_student_count} öğrenci etkileniyor</span><div>{finalReviews[organization.id].rooms.map((room) => <small key={room.classroom_id}>{room.classroom_name}: {room.assigned_students}/{room.available_seats} dolu · {room.empty_seats} boş</small>)}</div>{!finalReviews[organization.id].can_finalize && <p className="exam-error">Beş kişilik kesin sınır aşıldı; bu dağıtım kesinleştirilemez.</p>}<label><input type="checkbox" checked={finalizeConfirmed} onChange={(event) => setFinalizeConfirmed(event.target.checked)} />Kontrol ettim; bu sınav dağıtımını kesinleştirmek istiyorum.</label>{reviewError && <p className="exam-error" role="alert">{reviewError}</p>}<div><button type="button" onClick={() => setFinalizeConfirmId(null)}>Vazgeç</button><button type="button" disabled={!finalizeConfirmed || !finalReviews[organization.id].can_finalize || finalizing} onClick={() => void finalizeOrganization(organization.id)}>{finalizing ? 'Kesinleştiriliyor…' : 'Onayla ve kesinleştir'}</button></div></div>}
          {activeRuleOrganizationId === organization.id && ruleDraft && <div className="exam-rule-panel"><div className="exam-room-panel-heading"><div><strong>Adım 03 · Oturma kuralları</strong><small>Kuralları birbirinden bağımsız açıp kapatabilirsin. Kurallar yalnızca kullanılabilir fiziksel koltuklar arasında değerlendirilir.</small></div></div><div className="exam-rule-list">{ruleLabels.map((rule) => <label key={rule.key}><span><strong>{rule.title}</strong><small>{rule.position}</small></span><input type="checkbox" checked={ruleDraft[rule.key]} onChange={(event) => setRuleDraft((current) => current ? { ...current, [rule.key]: event.target.checked } : current)} /></label>)}</div>{ruleError && <p className="exam-error" role="alert">{ruleError}</p>}{ruleMessage && <p className="exam-room-success" role="status">{ruleMessage}</p>}<div className="exam-room-footer"><span>Dağıtım adayı oluşturulurken bu ayarlar kullanılacak.</span><button type="button" disabled={ruleSaving} onClick={() => saveRules(organization.id)}>{ruleSaving ? 'Kaydediliyor…' : 'Kuralları kaydet'}</button></div></div>}
        </article>
      })}
    </div>}
  </section>
}
