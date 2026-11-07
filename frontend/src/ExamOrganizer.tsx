import { useEffect, useMemo, useState, type FormEvent } from 'react'

type GroupOption = {
  class_level: string
  section: string
  area: string | null
  student_count: number
}

type CourseOption = { id: string; name: string }
type CourseDraft = { id: number; name: string; groupKeys: string[] }
type ExamOrganization = {
  id: string
  name: string
  exam_date: string
  status: 'draft' | 'completed'
  course_names: string[]
  course_count: number
  participant_count: number
}

type Props = {
  academicYearId: string | null
  academicYearLabel: string
  readOnly: boolean
  onStudents: () => void
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

export default function ExamOrganizer({ academicYearId, academicYearLabel, readOnly, onStudents }: Props) {
  const [organizations, setOrganizations] = useState<ExamOrganization[]>([])
  const [groups, setGroups] = useState<GroupOption[]>([])
  const [courseCatalog, setCourseCatalog] = useState<CourseOption[]>([])
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
    ])
      .then(async ([organizationResponse, groupResponse, courseResponse]) => {
        const [organizationData, groupData, courseData] = await Promise.all([
          organizationResponse.json(), groupResponse.json(), courseResponse.json(),
        ])
        if (!organizationResponse.ok) throw new Error(organizationData.error ?? 'Organizasyonlar yüklenemedi.')
        if (!groupResponse.ok) throw new Error(groupData.error ?? 'Öğrenci grupları yüklenemedi.')
        if (!courseResponse.ok) throw new Error(courseData.error ?? 'Ders listesi yüklenemedi.')
        setOrganizations(organizationData.organizations as ExamOrganization[])
        setGroups(groupData.groups as GroupOption[])
        setCourseCatalog(courseData.courses as CourseOption[])
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
    {loading ? <div className="exam-empty">Organizasyonlar yükleniyor…</div> : !groups.length ? <div className="exam-empty"><strong>Bu eğitim yılında öğrenci grubu bulunamadı.</strong><span>Önce öğrenci listesini içe aktar veya örnek verilerle başlangıç yap.</span><button type="button" onClick={onStudents}>Öğrenci kayıtlarına git</button></div> : organizations.length === 0 && !formOpen ? <div className="exam-empty"><strong>Henüz sınav organizasyonu yok.</strong><span>İlk taslağı oluştur; ders seçmek zorunlu değil.</span>{!readOnly && <button type="button" onClick={() => setFormOpen(true)}>İlk organizasyonu oluştur</button>}</div> : <div className="exam-organization-list">
      {organizations.map((organization) => <article className="exam-organization-card" key={organization.id}>
        <div className="exam-date-block"><strong>{new Date(`${organization.exam_date}T12:00:00`).toLocaleDateString('tr-TR', { day: '2-digit' })}</strong><span>{new Date(`${organization.exam_date}T12:00:00`).toLocaleDateString('tr-TR', { month: 'short' })}</span></div>
        <div className="exam-organization-copy"><span className="exam-status">{organization.status === 'completed' ? 'Tamamlandı' : 'Taslak'}</span><h3>{organization.name}</h3><p>{organization.course_names.length ? organization.course_names.join(' · ') : 'Genel sınav'} · {organization.participant_count} öğrenci</p></div>
        <div className="exam-organization-meta"><small>{organization.course_count} ders</small><small>{organization.exam_date}</small></div>
      </article>)}
    </div>}
  </section>
}
