import { Dashboard } from './Dashboard'
import { Notifications, notify } from './notify'
import { useEffect, useState, type FormEvent } from 'react'
import ClassroomManager from './ClassroomManager'
import BackupManager from './BackupManager'
import UpdateManager from './UpdateManager'
import WhatsNewDialog from './WhatsNewDialog'
import ExamOrganizer from './ExamOrganizer'
import ReportCenter from './ReportCenter'

type HealthState = 'checking' | 'online' | 'offline'
type WorkspaceIconName = 'overview' | 'school' | 'students' | 'classroom' | 'exams' | 'reports' | 'backup'

function WorkspaceIcon({ name, size = 17 }: { name: WorkspaceIconName; size?: number }) {
  const paths: Record<WorkspaceIconName, string> = {
    overview: 'M3 10.5 12 3l9 7.5M5.5 9v11h13V9M9 20v-6h6v6',
    school: 'M3 21h18M5 21V5h14v16M9 9h2m2 0h2M9 13h2m2 0h2M9 17h2m2 0h2',
    students: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m11 10v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
    classroom: 'M3 4h18v16H3zM3 10h18M9 10v10m6-10v10M6 7h.01M12 7h.01M18 7h.01',
    exams: 'M8 3v4m8-4v4M4 9h16M5 5h14a1 1 0 0 1 1 1v14H4V6a1 1 0 0 1 1-1m4 8h3m-3 4h6',
    reports: 'M6 3h9l4 4v14H6zM14 3v5h5m-9 4h6m-6 4h6m-6 4h4',
    backup: 'M12 3v12m0 0 4-4m-4 4-4-4M5 16v4h14v-4',
  }
  return <svg className="workspace-icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}

type AcademicYear = {
  id: string
  label: string
  start_year: number
  end_year: number
  is_selected: boolean
  is_current: boolean
  is_archive: boolean
}

type AcademicYearsResponse = {
  years: AcademicYear[]
  selected_academic_year_id: string | null
  current_label: string
}

type StudentImportPreview = {
  filename: string
  sheet_name: string
  sheet_names: string[]
  sources?: { name: string; header_row: number; class_level: string | null; section: string | null; auto_mapping: Record<string, number | string> }[]
  header_row: number
  headers: (string | number | boolean | null)[]
  preview_rows: (string | number | boolean | null)[][]
  auto_mapping: Record<string, number | string>
  saved: false
}

type StudentImportValidation = {
  total_rows: number
  valid: boolean
  issue_count: number
  issues: { row: number; source?: string; fields: string[]; issue: string }[]
  issues_truncated: boolean
  upper_grade_missing_area: number
  missing_area_by_class: { class_level: string; section: string; student_count: number }[]
  area_assignment_complete: boolean
  classes: { class_level: string; section: string; student_count: number }[]
  diff: {
    new_students: { school_number: string; name: string; class_level: string; section: string }[]
    departed_students: { school_number: string; name: string; class_level: string; section: string }[]
    changed_students: { school_number: string; name: string; class_level: string; section: string; changed_fields: string[] }[]
    reassigned_numbers: { school_number: string; previous_name: string; incoming_name: string }[]
    unchanged_count: number
  } | null
}

type StudentImportCommitResult = {
  saved: true
  created: number
  updated: number
  unchanged: number
  deactivated: number
  reassigned_school_numbers: number
  safety_backup: string
  classes: { class_level: string; section: string; student_count: number }[]
  classrooms?: { name: string; class_level: string; section: string; requested_capacity: number; capacity?: number; created: boolean; layout_created?: boolean; needs_review: boolean; message: string }[]
}

type StudentRecord = {
  id: string
  school_number: string
  first_name: string
  last_name: string
  class_level: string
  section: string
  area: string | null
  is_active?: boolean
}

function sortStudentRecords(items: StudentRecord[]) {
  return [...items].sort((a, b) =>
    Number(a.class_level) - Number(b.class_level)
    || a.section.localeCompare(b.section, 'tr')
    || a.last_name.localeCompare(b.last_name, 'tr')
    || a.first_name.localeCompare(b.first_name, 'tr'),
  )
}

type StudentDraft = Omit<StudentRecord, 'id' | 'area'> & { area: string }

type SchoolAdministrator = { id: string; role: 'principal' | 'vice_principal'; full_name: string; title: string; display_order: number }
type SchoolProfile = {
  school_name: string
  province: string
  district: string
  address: string
  phone: string
  email: string
  is_configured: boolean
  is_saved: boolean
  administrators: SchoolAdministrator[]
}

const blankSchoolProfile: SchoolProfile = {
  school_name: '', province: '', district: '', address: '', phone: '', email: '', is_configured: false, is_saved: false, administrators: [],
}

const importFields = [
  { key: 'school_number', label: 'Okul numarası', required: true },
  { key: 'first_name', label: 'Ad', required: true },
  { key: 'last_name', label: 'Soyad', required: true },
  { key: 'class_level', label: 'Sınıf seviyesi', required: true },
  { key: 'section', label: 'Şube', required: true },
  { key: 'area', label: 'Alan (isteğe bağlı)', required: false },
] as const

const areaOptions = ['Sayısal', 'Eşit Ağırlık', 'Sözel', 'Dil']

export default function App() {
  const [health, setHealth] = useState<HealthState>('checking')
  const [desktop, setDesktop] = useState(false)
  const [stopped, setStopped] = useState(false)
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([])
  const [activeYearId, setActiveYearId] = useState<string | null>(null)
  const [draftYearId, setDraftYearId] = useState<string | null>(null)
  const [yearsLoading, setYearsLoading] = useState(true)
  const [savingYear, setSavingYear] = useState(false)
  const [yearMessage, setYearMessage] = useState('')
  const [yearError, setYearError] = useState('')
  const [importPreview, setImportPreview] = useState<StudentImportPreview | null>(null)
  const [selectedStudentFile, setSelectedStudentFile] = useState<File | null>(null)
  const [importMapping, setImportMapping] = useState<Record<string, string>>({})
  const [areaAssignments, setAreaAssignments] = useState<Record<string, string>>({})
  const [importValidation, setImportValidation] = useState<StudentImportValidation | null>(null)
  const [importCommitResult, setImportCommitResult] = useState<StudentImportCommitResult | null>(null)
  const [importError, setImportError] = useState('')
  const [importLoading, setImportLoading] = useState(false)
  const [workbookDownload, setWorkbookDownload] = useState<'template' | 'sample' | null>(null)
  const [students, setStudents] = useState<StudentRecord[]>([])
  const [showInactiveStudents, setShowInactiveStudents] = useState(false)
  const [studentsLoading, setStudentsLoading] = useState(false)
  const [studentsError, setStudentsError] = useState('')
  const [studentFormOpen, setStudentFormOpen] = useState(false)
  const [studentSaving, setStudentSaving] = useState(false)
  const [studentMessage, setStudentMessage] = useState('')
  const [studentDraft, setStudentDraft] = useState<StudentDraft>({ school_number: '', first_name: '', last_name: '', class_level: '9', section: 'A', area: '' })
  const [editingStudentId, setEditingStudentId] = useState<string | null>(null)
  const [studentEditDraft, setStudentEditDraft] = useState<StudentDraft | null>(null)
  const [classroomPanelOpen, setClassroomPanelOpen] = useState(false)
  const [newVersion, setNewVersion] = useState('')
  const [studentQuery, setStudentQuery] = useState('')
  const [studentClassFilter, setStudentClassFilter] = useState('')
  const [activeSection, setActiveSection] = useState('overview')
  const [schoolProfile, setSchoolProfile] = useState<SchoolProfile>(blankSchoolProfile)
  const [schoolLoading, setSchoolLoading] = useState(true)
  const [schoolSaving, setSchoolSaving] = useState(false)
  const [schoolError, setSchoolError] = useState('')
  const [schoolMessage, setSchoolMessage] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    fetch('/api/health', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API yanıt vermedi')
        return response.json()
      })
      .then((data: { desktop?: boolean }) => { setHealth('online'); setDesktop(Boolean(data.desktop)) })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === 'AbortError') return
        setHealth('offline')
      })

    // Açılışta yeni sürüm denetimi: ayar kapalıysa ya da internet yoksa sessizce geçilir.
    fetch('/api/updates/online?auto=1', { signal: controller.signal })
      .then((response) => response.json())
      .then((data: { update_available?: boolean; latest_version?: string }) => { if (data.update_available && data.latest_version) setNewVersion(data.latest_version) })
      .catch(() => undefined)

    fetch('/api/academic-years', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Eğitim yılları alınamadı')
        return (await response.json()) as AcademicYearsResponse
      })
      .then((data) => {
        setAcademicYears(data.years)
        setActiveYearId(data.selected_academic_year_id)
        setDraftYearId(data.selected_academic_year_id)
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === 'AbortError') return
        setYearError('Eğitim-öğretim yılı bilgisi yüklenemedi.')
      })
      .finally(() => setYearsLoading(false))

    fetch('/api/school-profile', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Okul profili alınamadı.')
        const data = await response.json() as { profile: SchoolProfile }
        setSchoolProfile(data.profile)
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === 'AbortError') return
        setSchoolError(error instanceof Error ? error.message : 'Okul profili alınamadı.')
      })
      .finally(() => setSchoolLoading(false))

    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (activeSection !== 'students' || !activeYearId) return
    const controller = new AbortController()
    setStudentsLoading(true)
    setStudentsError('')
    fetch(`/api/students?academic_year_id=${encodeURIComponent(activeYearId)}${showInactiveStudents ? '&include_inactive=true' : ''}`, { signal: controller.signal })
      .then(async (response) => {
        const data = await response.json()
        if (!response.ok) throw new Error(data.error ?? 'Öğrenci listesi alınamadı.')
        setStudents(data.students as StudentRecord[])
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === 'AbortError') return
        setStudentsError(error instanceof Error ? error.message : 'Öğrenci listesi alınamadı.')
      })
      .finally(() => setStudentsLoading(false))
    return () => controller.abort()
  }, [activeSection, activeYearId, showInactiveStudents])

  const activeYear = academicYears.find((year) => year.id === activeYearId)
  const studentClassOptions = [...new Set(students.map((student) => `${student.class_level}/${student.section}`))]
    .sort((first, second) => first.localeCompare(second, 'tr-TR', { numeric: true }))
  const normalizedStudentQuery = studentQuery.trim().toLocaleLowerCase('tr-TR')
  const filteredStudents = students.filter((student) => {
    if (studentClassFilter && `${student.class_level}/${student.section}` !== studentClassFilter) return false
    if (!normalizedStudentQuery) return true
    return `${student.school_number} ${student.first_name} ${student.last_name}`.toLocaleLowerCase('tr-TR').includes(normalizedStudentQuery)
  })
  const hasDraftChange = Boolean(draftYearId && draftYearId !== activeYearId)
  const requiredMappingsComplete = importFields
    .filter((field) => field.required)
    .every((field) => Boolean(importMapping[field.key]))
  const areaAssignmentsComplete = importValidation?.missing_area_by_class.every(
    (item) => Boolean(areaAssignments[`${item.class_level}/${item.section}`]),
  ) ?? true

  async function confirmAcademicYear() {
    if (!draftYearId || !hasDraftChange) return

    setSavingYear(true)
    setYearError('')
    setYearMessage('')
    try {
      const response = await fetch('/api/academic-years/active', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ academic_year_id: draftYearId }),
      })
      if (!response.ok) {
        throw new Error(response.status === 404 ? 'Seçilen yıl bulunamadı.' : 'Yıl seçimi kaydedilemedi.')
      }

      const data = (await response.json()) as { selected_year: AcademicYear }
      setAcademicYears((years) =>
        years.map((year) => ({ ...year, is_selected: year.id === data.selected_year.id })),
      )
      setActiveYearId(data.selected_year.id)
      setDraftYearId(data.selected_year.id)
      setImportValidation(null)
      setImportCommitResult(null)
      setYearMessage(data.selected_year.label + ' çalışma yılı seçildi.')
    } catch (error) {
      setYearError(error instanceof Error ? error.message : 'Yıl seçimi kaydedilemedi.')
    } finally {
      setSavingYear(false)
    }
  }

  async function previewStudentFile(file: File | undefined) {
    setActiveSection('students')
    setImportPreview(null)
    setImportValidation(null)
    setImportCommitResult(null)
    setImportError('')
    setSelectedStudentFile(file ?? null)
    setImportMapping({})
    setAreaAssignments({})
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)
    setImportLoading(true)
    try {
      const response = await fetch('/api/student-import/preview', { method: 'POST', body: formData })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Dosya önizlemesi oluşturulamadı.')
      const preview = data as StudentImportPreview
      setImportPreview(preview)
      setImportMapping(Object.fromEntries(
        Object.entries(preview.auto_mapping ?? {}).map(([field, column]) => [field, String(column)]),
      ))
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Dosya önizlemesi oluşturulamadı.')
    } finally {
      setImportLoading(false)
    }
  }

  async function downloadStudentWorkbook(kind: 'template' | 'sample') {
    setWorkbookDownload(kind)
    setImportError('')
    try {
      const fileName = kind === 'template'
        ? 'kelebek_ogrenci_sablonu_ornek_verili.xlsx'
        : 'kelebek_sentetik_demo_48_ogrenci.xlsx'
      const response = await fetch(`/downloads/${fileName}`)
      const contentType = response.headers.get('content-type')?.toLocaleLowerCase('en-US') ?? ''
      if (!response.ok) {
        if (contentType.includes('text/html')) {
          throw new Error('Excel servisi yanıt vermedi. Uygulamayı kapatıp yeniden başlatın; sonra tekrar indirin.')
        }
        const body = await response.json().catch(() => ({})) as { error?: string }
        throw new Error(body.error ?? 'Excel dosyası oluşturulamadı.')
      }
      if (!contentType.includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) {
        throw new Error('Excel dosyası yerine web sayfası yanıt verdi. Yerel servis kapalı olabilir; uygulamayı yeniden başlatıp tekrar deneyin.')
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      setImportError(error instanceof TypeError
        ? 'Yerel Excel servisine bağlanılamadı. Uygulamayı yeniden başlatıp tekrar deneyin.'
        : error instanceof Error ? error.message : 'Excel dosyası indirilemedi.')
    } finally {
      setWorkbookDownload(null)
    }
  }

  async function saveManualStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!activeYearId || activeYear?.is_archive) return
    setStudentSaving(true)
    setStudentsError('')
    setStudentMessage('')
    try {
      const response = await fetch('/api/students', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...studentDraft, academic_year_id: activeYearId }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Öğrenci eklenemedi.')
      setStudents((current) => sortStudentRecords([...current, data.student as StudentRecord]))
      setStudentDraft({ school_number: '', first_name: '', last_name: '', class_level: studentDraft.class_level, section: studentDraft.section, area: studentDraft.area })
      setStudentMessage('Öğrenci seçili eğitim yılına eklendi.')
      setStudentFormOpen(false)
    } catch (error) {
      setStudentsError(error instanceof Error ? error.message : 'Öğrenci eklenemedi.')
    } finally {
      setStudentSaving(false)
    }
  }

  function startStudentEdit(student: StudentRecord) {
    setEditingStudentId(student.id)
    setStudentEditDraft({
      school_number: student.school_number,
      first_name: student.first_name,
      last_name: student.last_name,
      class_level: student.class_level,
      section: student.section,
      area: student.area ?? '',
    })
    setStudentsError('')
    setStudentMessage('')
  }

  async function saveStudentEdit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    if (!editingStudentId || !studentEditDraft || !activeYearId || activeYear?.is_archive) return
    setStudentSaving(true)
    setStudentsError('')
    try {
      const response = await fetch(`/api/students/${encodeURIComponent(editingStudentId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...studentEditDraft, academic_year_id: activeYearId }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Öğrenci bilgileri kaydedilemedi.')
      setStudents((items) => sortStudentRecords(items.map((item) => item.id === editingStudentId ? data.student as StudentRecord : item)))
      setEditingStudentId(null)
      setStudentEditDraft(null)
      setStudentMessage('Öğrenci bilgileri güncellendi. Açık sınav taslakları yeniden dağıtım isteyecek; tamamlanmış kayıtlar korunur.')
    } catch (error) {
      setStudentsError(error instanceof Error ? error.message : 'Öğrenci bilgileri kaydedilemedi.')
    } finally {
      setStudentSaving(false)
    }
  }

  async function changeStudentActive(student: StudentRecord, activate: boolean) {
    if (!activeYearId || activeYear?.is_archive) return
    if (!window.confirm(activate
      ? 'Öğrenci yeniden etkinleştirilecek ve yeni dağıtımlarda seçilebilir olacak. Devam edilsin mi?'
      : 'Öğrenci silinmeden pasife alınacak. Açık sınav taslaklarından çıkarılacak; tamamlanmış sınav geçmişi korunacak. Devam edilsin mi?')) return
    setStudentSaving(true)
    setStudentsError('')
    setStudentMessage('')
    try {
      const response = await fetch(`/api/students/${encodeURIComponent(student.id)}/${activate ? 'reactivate' : 'deactivate'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ academic_year_id: activeYearId, confirmed: true }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Öğrenci durumu değiştirilemedi.')
      if (showInactiveStudents) {
        const listResponse = await fetch(`/api/students?academic_year_id=${encodeURIComponent(activeYearId)}&include_inactive=true`)
        const listData = await listResponse.json()
        if (listResponse.ok) setStudents(listData.students as StudentRecord[])
      } else {
        setStudents((items) => items.filter((item) => item.id !== student.id))
      }
      setEditingStudentId(null)
      setStudentEditDraft(null)
      setStudentMessage(activate ? 'Öğrenci yeniden etkinleştirildi.' : 'Öğrenci pasife alındı; geçmiş kayıtları korundu.')
    } catch (error) {
      setStudentsError(error instanceof Error ? error.message : 'Öğrenci durumu değiştirilemedi.')
    } finally {
      setStudentSaving(false)
    }
  }

  async function validateStudentFile() {
    if (!selectedStudentFile || !importPreview) return
    const formData = new FormData()
    formData.append('file', selectedStudentFile)
    formData.append('mapping', JSON.stringify(importMapping))
    formData.append('area_assignments', JSON.stringify(areaAssignments))
    if (activeYearId) formData.append('academic_year_id', activeYearId)
    setImportLoading(true)
    setImportError('')
    setImportValidation(null)
    setImportCommitResult(null)
    try {
      const response = await fetch('/api/student-import/preview', { method: 'POST', body: formData })
      const data = await response.json() as { error?: string; validation?: StudentImportValidation; diff?: StudentImportValidation['diff'] }
      if (!response.ok) throw new Error(data.error ?? 'Dosya doğrulanamadı.')
      if (!data.validation) throw new Error('Dosya kontrol sonucu alınamadı.')
      // API fark raporunu üst düzeyde döndürür; arayüz onu kontrol sonucuyla
      // birlikte tutar. Birleştirilmezse "İçe aktarmayı onayla" düğmesi hiç
      // görünmez ve liste içe aktarılamaz.
      setImportValidation({ ...data.validation, diff: data.diff ?? null })
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Dosya doğrulanamadı.')
    } finally {
      setImportLoading(false)
    }
  }

  async function commitStudentFile() {
    if (!selectedStudentFile || !activeYearId || activeYear?.is_archive || !importValidation?.valid || !importValidation.diff) return
    const confirmed = window.confirm(
      'Öğrenci listesi seçili yıla kaydedilecek; dosyada bulunmayanlar geçmiş kayıtları korunarak pasife alınacak. Yeni sınıf/şubeler için öğrenci sayısına göre başlangıç kapasiteli derslik planı oluşturulacak. Fiziksel sıra düzenini daha sonra kontrol edip düzenleyebilirsiniz. Devam edilsin mi?',
    )
    if (!confirmed) return

    const formData = new FormData()
    formData.append('file', selectedStudentFile)
    formData.append('mapping', JSON.stringify(importMapping))
    formData.append('academic_year_id', activeYearId)
    formData.append('confirm', 'true')
    formData.append('area_assignments', JSON.stringify(areaAssignments))
    setImportLoading(true)
    setImportError('')
    try {
      const response = await fetch('/api/student-import/commit', { method: 'POST', body: formData })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Öğrenci listesi kaydedilemedi.')
      setImportCommitResult(data as StudentImportCommitResult)
      const committed = data as StudentImportCommitResult
      const importedStudents = committed.classes.reduce((total, item) => total + item.student_count, 0)
      const roomCount = committed.classrooms?.length ?? 0
      notify.success(
        `${importedStudents} öğrenci${roomCount ? ` ve ${roomCount} derslik` : ''} hazır. Dersliklerin oturma planlarını gerçek sınıflarla karşılaştır.`,
        { label: 'Derslik planlarını kontrol et', onClick: () => { setActiveSection('classrooms'); setClassroomPanelOpen(true) } },
      )
      if (activeYearId) {
        const listResponse = await fetch(`/api/students?academic_year_id=${encodeURIComponent(activeYearId)}`)
        const listData = await listResponse.json()
        if (listResponse.ok) setStudents(listData.students as StudentRecord[])
      }
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Öğrenci listesi kaydedilemedi.')
      notify.error(error instanceof Error ? error.message : 'Öğrenci listesi kaydedilemedi. Dosyayı kontrol edip tekrar deneyin.')
    } finally {
      setImportLoading(false)
    }
  }

  async function saveSchoolProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (duplicateAdministrator) {
      setSchoolError(`${duplicateAdministrator} birden fazla görevde görünüyor. Aynı kişiyi yalnızca bir görevde ekleyin.`)
      return
    }
    setSchoolSaving(true)
    setSchoolError('')
    setSchoolMessage('')
    try {
      const response = await fetch('/api/school-profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(schoolProfile),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Okul bilgileri kaydedilemedi.')
      setSchoolProfile(data.profile as SchoolProfile)
      setSchoolMessage('Okul bilgileri bu bilgisayara kaydedildi.')
      notify.success('Okul bilgileri kaydedildi. Raporlarda bu bilgiler görünecek.')
    } catch (error) {
      setSchoolError(error instanceof Error ? error.message : 'Okul bilgileri kaydedilemedi.')
    } finally {
      setSchoolSaving(false)
    }
  }

  async function retrySchoolProfile() {
    setSchoolLoading(true)
    setSchoolError('')
    try {
      const response = await fetch('/api/school-profile')
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Okul profili alınamadı.')
      setSchoolProfile(data.profile as SchoolProfile)
    } catch (error) {
      setSchoolError(error instanceof Error ? error.message : 'Okul profili alınamadı.')
    } finally {
      setSchoolLoading(false)
    }
  }

  function updateSchoolField(field: keyof Omit<SchoolProfile, 'is_configured' | 'administrators'>, value: string) {
    setSchoolProfile((profile) => ({ ...profile, [field]: value }))
    setSchoolMessage('')
  }

  function addSchoolAdministrator(role: SchoolAdministrator['role']) {
    setSchoolProfile((profile) => ({
      ...profile,
      administrators: [...profile.administrators, { id: `new-${Date.now()}`, role, full_name: '', title: role === 'principal' ? 'Okul Müdürü' : 'Müdür Yardımcısı', display_order: profile.administrators.length }],
    }))
    setSchoolMessage('')
  }

  function updateSchoolAdministrator(index: number, field: 'role' | 'full_name' | 'title', value: string) {
    setSchoolProfile((profile) => ({
      ...profile,
      administrators: profile.administrators.map((item, itemIndex) => {
        if (itemIndex !== index) return item
        if (field === 'role') {
          const oldDefault = item.role === 'principal' ? 'Okul Müdürü' : 'Müdür Yardımcısı'
          const nextDefault = value === 'principal' ? 'Okul Müdürü' : 'Müdür Yardımcısı'
          return { ...item, role: value as SchoolAdministrator['role'], title: !item.title || item.title === oldDefault ? nextDefault : item.title }
        }
        return { ...item, [field]: value }
      }),
    }))
    setSchoolMessage('')
  }

  function removeSchoolAdministrator(index: number) {
    setSchoolProfile((profile) => ({ ...profile, administrators: profile.administrators.filter((_, itemIndex) => itemIndex !== index) }))
    setSchoolMessage('')
  }

  const statusText = {
    checking: 'Bağlantı kontrol ediliyor',
    online: 'Yerel servis çalışıyor',
    offline: 'Yerel servisle bağlantı kurulamadı',
  }[health]
  const sectionTitle = activeSection === 'school'
    ? 'Okul ve yöneticiler'
    : activeSection === 'students'
      ? 'Öğrenci kayıtları'
      : activeSection === 'classrooms'
        ? 'Derslikler'
        : activeSection === 'exams'
          ? 'Sınav organizasyonları'
          : activeSection === 'reports'
            ? 'Raporlar'
            : activeSection === 'backup'
              ? 'Yedek ve arşiv'
              : 'Genel Bakış'
  const principal = schoolProfile.administrators.find((person) => person.role === 'principal')
  const duplicateAdministrator = schoolProfile.administrators.reduce<string | null>((duplicate, person, index, list) => {
    if (duplicate) return duplicate
    const normalize = (value: string) => value.trim().replace(/\s+/g, ' ').toLocaleLowerCase('tr-TR')
    const name = normalize(person.full_name)
    if (!name) return null
    return list.slice(0, index).some((other) => normalize(other.full_name) === name) ? person.full_name.trim() : null
  }, null)

  return (
    <main className="app-shell">
      <aside className="app-sidebar">
        <a className="brand" href="/" aria-label="Kelebek Sınav Sistemi ana sayfa" onClick={() => { setActiveSection('overview'); setClassroomPanelOpen(false) }}>
          <span className="brand-mark" aria-hidden="true">K</span>
          <span>Kelebek <strong>Sınav Sistemi</strong></span>
        </a>
        <div className="sidebar-school">
          <span className="school-avatar">{schoolProfile.school_name ? schoolProfile.school_name.slice(0, 1).toLocaleUpperCase('tr-TR') : 'O'}</span>
          <span><strong>{schoolProfile.school_name || 'Okul profili'}</strong><small>{schoolProfile.is_configured ? 'Kurulum tamamlandı' : schoolProfile.is_saved ? 'Eksik bilgiler var' : 'Bilgiler bekleniyor'}</small></span>
          <span className={`profile-status ${schoolProfile.is_configured ? 'configured' : ''}`} aria-label={schoolProfile.is_configured ? 'Kurulum tamamlandı' : 'Bilgiler bekleniyor'} />
        </div>
        <div className="sidebar-caption">ÇALIŞMA ALANI</div>
        <nav className="main-navigation" aria-label="Ana gezinme">
          <button className={activeSection === 'overview' ? 'active' : ''} type="button" onClick={() => { setActiveSection('overview'); setClassroomPanelOpen(false) }}><WorkspaceIcon name="overview" /> Genel Bakış</button>
          <button className={activeSection === 'school' ? 'active' : ''} type="button" onClick={() => { setActiveSection('school'); setClassroomPanelOpen(false) }}><WorkspaceIcon name="school" /> Okul ve yöneticiler</button>
          <button className={activeSection === 'students' ? 'active' : ''} type="button" onClick={() => { setActiveSection('students'); setClassroomPanelOpen(false) }}><WorkspaceIcon name="students" /> Öğrenci kayıtları</button>
          <button className={activeSection === 'classrooms' ? 'active' : ''} type="button" onClick={() => { setActiveSection('classrooms'); setClassroomPanelOpen(true) }}><WorkspaceIcon name="classroom" /> Derslikler</button>
          <button className={activeSection === 'exams' ? 'active' : ''} type="button" onClick={() => { setActiveSection('exams'); setClassroomPanelOpen(false) }}><WorkspaceIcon name="exams" /> Sınav organizasyonları</button>
          <button className={activeSection === 'backup' ? 'active' : ''} type="button" onClick={() => { setActiveSection('backup'); setClassroomPanelOpen(false) }}><WorkspaceIcon name="backup" /> Yedek ve arşiv</button>
          <button className={activeSection === 'reports' ? 'active' : ''} type="button" onClick={() => { setActiveSection('reports'); setClassroomPanelOpen(false) }}><WorkspaceIcon name="reports" /> Raporlar</button>
        </nav>
        <div className="sidebar-footer"><span className={`status-dot ${health}`} /><span>{statusText}</span><small>Veriler bu bilgisayarda</small></div>
      </aside>

      <div className="app-main">
      <header className="topbar">
        <div className="breadcrumb"><span>Çalışma alanı</span><b>/</b><strong>{sectionTitle}</strong></div>
        <div className="topbar-actions">
          <div className="year-control">
            <label htmlFor="academic-year-select">Eğitim-öğretim yılı</label>
            <div className="year-control-row">
              <select
                id="academic-year-select"
                value={draftYearId ?? ''}
                disabled={yearsLoading || academicYears.length === 0 || savingYear}
                onChange={(event) => {
                  setDraftYearId(event.target.value)
                  setYearMessage('')
                  setYearError('')
                }}
              >
                {yearsLoading && <option value="">Yükleniyor…</option>}
                {academicYears.map((year) => (
                  <option key={year.id} value={year.id}>
                    {year.label}{year.is_current ? ' · Güncel' : year.is_archive ? ' · Arşiv' : ''}
                  </option>
                ))}
              </select>
              <button
                className="confirm-year"
                type="button"
                onClick={confirmAcademicYear}
                disabled={!hasDraftChange || savingYear}
              >
                {savingYear ? 'Kaydediliyor…' : 'Onayla'}
              </button>
            </div>
            {yearError && <span className="year-feedback error" role="alert">{yearError}</span>}
            {yearMessage && <span className="year-feedback success" role="status">{yearMessage}</span>}
          </div>

          <span className={`service-status ${health}`} role="status">
            <span className="status-dot" />
            {statusText}
          </span>
          {desktop && <button type="button" className="confirm-year" data-testid="app-shutdown-btn" disabled={stopped} onClick={() => { if (window.confirm('Uygulama kapatılsın mı? Tüm veriler kaydedildi.')) void fetch('/api/app/shutdown', { method: 'POST' }).then(() => setStopped(true)) }}>{stopped ? 'Kapatıldı · sekmeyi kapatabilirsiniz' : 'Uygulamayı kapat'}</button>}
        </div>
      </header>

      <section className="welcome-card" aria-labelledby="welcome-title">
        <div className="page-heading">
          <div><div className="eyebrow">KELEBEK <span>·</span> OKUL YÖNETİMİ</div><h1 id="welcome-title">{sectionTitle}</h1><p>{activeSection === 'school' ? 'Okul kimliği ve yönetici bilgileri.' : activeSection === 'students' ? 'Öğrenci listesini içeri aktarın ve kayıt farklarını inceleyin.' : activeSection === 'classrooms' ? 'Derslikleri ve fiziksel oturma düzenlerini yönetin.' : activeSection === 'exams' ? 'Farklı ders ve sınıf gruplarını tek sınav planında bir araya getirin.' : activeSection === 'backup' ? 'Okul verilerini taşınabilir pakette koruyun ve bilgisayarlar arasında aktarın.' : activeSection === 'reports' ? 'Kesinleşen sınavların krokilerini, yoklama ve dağıtım listelerini yazdırın.' : 'Okulunuzu ve sınav hazırlık sürecinizi tek çalışma alanından yönetin.'}</p></div>
          <div className="current-year-pill"><small>ÇALIŞMA YILI</small><strong>{activeYear?.label ?? 'Yıl bilgisi yükleniyor'}</strong></div>
        </div>

        {newVersion && activeSection !== 'backup' && (
          <div className="new-version-banner" role="status" data-testid="new-version-banner">
            <span><strong>Yeni sürüm hazır: {newVersion}</strong> Tek tıkla indirip kurabilirsin; verilerin korunur.</span>
            <button type="button" onClick={() => { setActiveSection('backup'); setClassroomPanelOpen(false) }}>Güncellemeyi göster</button>
            <button type="button" className="new-version-dismiss" aria-label="Bildirimi kapat" onClick={() => setNewVersion('')}>×</button>
          </div>
        )}

        {activeYear?.is_archive && (
          <div className="archive-banner" role="status">
            {activeYear.label} arşiv yılını görüntülüyorsunuz. Bu yılın kayıtları salt okunur açılacaktır.
          </div>
        )}

        {activeSection === 'overview' && <Dashboard
          academicYearId={activeYearId}
          readOnly={Boolean(activeYear?.is_archive)}
          schoolName={schoolProfile.school_name}
          schoolPlace={[schoolProfile.district, schoolProfile.province].filter(Boolean).join(' · ')}
          principalName={principal?.full_name ?? ''}
          schoolConfigured={schoolProfile.is_configured}
          onNavigate={(section) => { setActiveSection(section); setClassroomPanelOpen(section === 'classrooms') }}
        />}

        {activeSection === 'school' && <form className="school-form-card" onSubmit={saveSchoolProfile}>
          <div className="form-card-heading"><span className="form-icon"><WorkspaceIcon name="school" size={19} /></span><div><span className="eyebrow">OKUL PROFİLİ</span><h2>Genel bilgiler</h2><p>Bu bilgiler uygulamanın kendi bilgisayarınızda saklanır ve okul belgelerinde kullanılır.</p></div></div>
          {schoolLoading ? <p className="school-loading">Okul profili yükleniyor…</p> : <>
            <div className="school-fields-grid">
              <label className="field-wide"><span>Okulun adı <b>*</b></span><input required maxLength={160} value={schoolProfile.school_name} onChange={(event) => updateSchoolField('school_name', event.target.value)} placeholder="Okulun resmi adını girin" /></label>
              <label><span>İl</span><input maxLength={100} value={schoolProfile.province} onChange={(event) => updateSchoolField('province', event.target.value)} placeholder="İl adı" /></label>
              <label><span>İlçe</span><input maxLength={100} value={schoolProfile.district} onChange={(event) => updateSchoolField('district', event.target.value)} placeholder="İlçe adı" /></label>
              <label className="field-wide"><span>Adres</span><textarea maxLength={500} rows={2} value={schoolProfile.address} onChange={(event) => updateSchoolField('address', event.target.value)} placeholder="Okulun açık adresi" /></label>
              <label><span>Telefon</span><input type="tel" maxLength={40} value={schoolProfile.phone} onChange={(event) => updateSchoolField('phone', event.target.value)} placeholder="(0___) ___ __ __" /></label>
              <label><span>E-posta</span><input type="email" maxLength={254} value={schoolProfile.email} onChange={(event) => updateSchoolField('email', event.target.value)} placeholder="Kurumsal e-posta adresi" /></label>
            </div>
            <div className="administrator-section">
              <div className="section-heading"><div><span className="eyebrow">İMZA VE YÖNETİM</span><h3>Yönetici bilgileri</h3></div><div className="admin-add-actions"><button type="button" onClick={() => addSchoolAdministrator('principal')} disabled={schoolProfile.administrators.some((item) => item.role === 'principal')}>+ Okul müdürü</button><button type="button" onClick={() => addSchoolAdministrator('vice_principal')} disabled={schoolProfile.administrators.length >= 21}>+ Müdür yardımcısı</button></div></div>
              <p>Bir okul müdürü ve birden fazla müdür yardımcısı ekleyebilirsiniz. Belge unvanı görevden varsayılan gelir; gerekirse düzenleyebilirsiniz.</p>
              {schoolProfile.administrators.length === 0 && <div className="empty-admins">Henüz yönetici eklenmedi. Müdür veya müdür yardımcısı ekleyebilirsiniz.</div>}
              <div className="administrator-list">{schoolProfile.administrators.map((person, index) => <div className="administrator-row" key={person.id || `${person.role}-${index}`}>
                <label><span>Görev</span><select value={person.role} onChange={(event) => updateSchoolAdministrator(index, 'role', event.target.value)}><option value="principal">Okul müdürü · tek kayıt</option><option value="vice_principal">Müdür yardımcısı · çoklu</option></select></label>
                <label><span>Adı soyadı</span><input required maxLength={160} value={person.full_name} onChange={(event) => updateSchoolAdministrator(index, 'full_name', event.target.value)} placeholder="Yöneticinin gerçek adını girin" /></label>
                <label><span>Belge imza unvanı</span><input maxLength={120} value={person.title} onChange={(event) => updateSchoolAdministrator(index, 'title', event.target.value)} placeholder={person.role === 'principal' ? 'Okul Müdürü' : 'Müdür Yardımcısı'} /></label>
                <button className="remove-admin" type="button" aria-label={`${person.full_name || 'Yönetici'} kaydını kaldır`} onClick={() => removeSchoolAdministrator(index)}>Kaldır</button>
              </div>)}</div>
            </div>
            {duplicateAdministrator && <p className="school-form-error" role="status">“{duplicateAdministrator}” birden fazla görevde görünüyor. Aynı kişiyi yalnızca bir kez ekleyin.</p>}
            {schoolError && <p className="school-form-error" role="alert">{schoolError} <button className="retry-school-profile" type="button" onClick={() => void retrySchoolProfile()}>Tekrar dene</button></p>}
            {schoolMessage && <p className="school-form-success" role="status">{schoolMessage}</p>}
            <div className="school-form-footer"><span><b>*</b> Zorunlu alan</span><button className="school-save-button" type="submit" disabled={schoolSaving || !schoolProfile.school_name.trim() || Boolean(duplicateAdministrator)}>{schoolSaving ? 'Kaydediliyor…' : 'Bilgileri kaydet'}</button></div>
          </>}
        </form>}

        {activeSection === 'students' && <div className="section-heading module-heading"><div><span className="eyebrow">{activeSection === 'students' ? 'ÖĞRENCİ İŞLEMLERİ' : 'MODÜLLER'}</span><h2>{activeSection === 'students' ? 'Liste aktarımı' : 'Yönetim alanları'}</h2></div><span className="module-caption">{activeSection === 'students' ? 'Liste önizlemesi kaydetmeden önce kontrol edilir.' : 'Hazır bölümler kullanılabilir; diğerleri geliştirme aşamasında.'}</span></div>}

        {activeSection !== 'overview' && activeSection !== 'school' && activeSection !== 'classrooms' && activeSection !== 'exams' && <div className={`feature-grid ${activeSection === 'students' ? 'single-module' : ''}`}>
          {(activeSection === 'overview' || activeSection === 'students') && <article className="feature-card">
            <span className="feature-number">01</span>
            <h2>Öğrenci kayıtları</h2>
            <p>Okul ve sınıf listeleri için güvenli yerel kayıt alanı.</p>
            <label className="file-picker" id="student-import">
              <span>{importLoading ? 'Dosya okunuyor…' : 'Excel veya PDF listesi seç'}</span>
              <input
                type="file"
                accept=".xlsx,.pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/pdf"
                disabled={importLoading}
                onChange={(event) => previewStudentFile(event.target.files?.[0])}
              />
            </label>
            <button className="template-download" type="button" disabled={workbookDownload !== null} onClick={() => downloadStudentWorkbook('template')}>
              <WorkspaceIcon name="reports" size={15} /> {workbookDownload === 'template' ? 'Şablon hazırlanıyor…' : 'Örnekli Excel şablonunu indir'}
            </button>
            <button className="template-download demo-download" type="button" disabled={workbookDownload !== null} onClick={() => downloadStudentWorkbook('sample')}>
              <WorkspaceIcon name="students" size={15} /> {workbookDownload === 'sample' ? 'Örnekler hazırlanıyor…' : '48 sentetik öğrenci örneğini indir'}
            </button>
            <p className="template-caption">Excel sekmeleri ve PDF sayfaları başlık satırından bağımsız taranır. Taranmış görüntü PDF'leri desteklenmez.</p>
            {importError && <p className="import-error" role="alert">{importError}</p>}
          </article>}
          {activeSection === 'overview' && <article className="feature-card">
            <span className="feature-number">02</span>
            <h2>Derslik düzeni</h2>
            <p>Fiziksel masa ve oturma yerlerini tanımlama.</p>
            <button className="manager-open" type="button" onClick={() => { setActiveSection('classrooms'); setClassroomPanelOpen(true) }}>
              Derslikleri yönet
            </button>
          </article>}
          {activeSection === 'overview' && <article className="feature-card muted-card">
            <span className="feature-number">03</span>
            <h2>Sınav dağıtımı</h2>
            <p>Dersleri ve öğrenci gruplarını seçerek sınav organizasyonu taslağı oluştur.</p>
            <button className="manager-open" type="button" onClick={() => setActiveSection('exams')}>Organizasyonları aç</button>
          </article>}
        </div>}

        {classroomPanelOpen && activeSection === 'classrooms' && (
          <ClassroomManager
            academicYearId={activeYearId}
            academicYearLabel={activeYear?.label ?? ''}
            readOnly={activeYear?.is_archive ?? false}
            onClose={() => { setClassroomPanelOpen(false); setActiveSection('overview') }}
          />
        )}

        {activeSection === 'exams' && <ExamOrganizer
          academicYearId={activeYearId}
          readOnly={activeYear?.is_archive ?? false}
          onStudents={() => setActiveSection('students')}
          onClassrooms={() => { setActiveSection('classrooms'); setClassroomPanelOpen(true) }}
          onReports={() => setActiveSection('reports')}
        />}

        {activeSection === 'backup' && <><BackupManager /><UpdateManager /></>}
        <WhatsNewDialog />

        {activeSection === 'reports' && <ReportCenter
          academicYearId={activeYearId}
          academicYearLabel={activeYear?.label ?? ''}
          onExams={() => setActiveSection('exams')}
        />}

        {activeSection === 'students' && importPreview && (
          <section className="import-preview" aria-labelledby="import-preview-title">
            <div className="import-preview-heading">
              <div>
                <span className="eyebrow">DOSYA ÖNİZLEMESİ</span>
                <h2 id="import-preview-title">{importPreview.filename}</h2>
              </div>
              <span className="preview-badge">Henüz kaydedilmedi</span>
            </div>
            <p>
              {importPreview.sheet_names.length} liste bölümü bulundu · Örnek: “{importPreview.sheet_name}”, başlık satırı {importPreview.header_row} ·{' '}
              {importPreview.preview_rows.length} örnek satır gösteriliyor
            </p>
            {importPreview.sources && <div className="import-source-list">{importPreview.sources.map((source, index) => <span key={`${source.name}-${index}`}>{source.name}{source.class_level && source.section ? ` · ${source.class_level}/${source.section}` : ''}{source.header_row ? ` · başlık ${source.header_row}` : ' · önceki sayfanın başlığı sürüyor'}</span>)}</div>}
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {importPreview.headers.map((header, index) => (
                      <th key={index}>{header ?? `Sütun ${index + 1}`}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {importPreview.preview_rows.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {importPreview.headers.map((_, columnIndex) => (
                        <td key={columnIndex}>{row[columnIndex] ?? '—'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mapping-panel">
              <div>
                <span className="eyebrow">SÜTUN EŞLEŞTİRME</span>
                <p>{Object.keys(importPreview.auto_mapping ?? {}).length ? 'Başlıklar otomatik eşleştirildi. İstersen seçimleri değiştirebilirsin.' : 'Başlıklar tanınmadı; her bilgi için dosyadaki sütunu seç.'}</p>
              </div>
              <div className="mapping-grid">
                {importFields.map((field) => (
                  <label key={field.key}>
                    <span>{field.label}{field.required ? ' *' : ''}</span>
                    <select
                      value={importMapping[field.key] ?? ''}
                      onChange={(event) => {
                        setImportMapping((mapping) => ({ ...mapping, [field.key]: event.target.value }))
                        setAreaAssignments({})
                        setImportValidation(null)
                        setImportCommitResult(null)
                      }}
                    >
                      <option value="">Sütun seç</option>
                      {(field.key === 'class_level' || field.key === 'section') && importPreview.auto_mapping[field.key] === '__context__' && (
                        <option value="__context__">Sınıf sayfası / başlığından al</option>
                      )}
                      {importPreview.headers.map((header, index) => (
                        <option key={index} value={String(index)}>
                          {header ?? `Sütun ${index + 1}`}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              <button
                className="validate-import"
                type="button"
                disabled={importLoading || !requiredMappingsComplete || !areaAssignmentsComplete}
                onClick={validateStudentFile}
              >
                {importLoading
                  ? 'Kontrol ediliyor…'
                  : importValidation?.missing_area_by_class.length
                    ? 'Alan atamalarını uygula ve fark raporunu oluştur'
                    : 'Eşleştir ve dosyayı kontrol et'}
              </button>
            </div>
            {importValidation && (
              <div className="validation-report" role="status">
                <strong>{importValidation.valid ? 'Dosya yapısı uygun' : 'Düzeltme gereken satırlar var'}</strong>
                <p>{importValidation.total_rows} satır incelendi · {importValidation.issue_count} sorun bulundu</p>
                {importValidation.missing_area_by_class.length > 0 && (
                  <div className="area-assignment-panel">
                    <strong>11–12. sınıflar için alan ata</strong>
                    <p>Her sınıf/şube için bir başlangıç alanı seç. Bu seçim o gruptaki alanı boş öğrencileri doldurur.</p>
                    {importValidation.missing_area_by_class.map((item) => {
                      const groupKey = `${item.class_level}/${item.section}`
                      return (
                        <label key={groupKey}>
                          <span>{item.class_level}/{item.section} · {item.student_count} öğrenci</span>
                          <select
                            value={areaAssignments[groupKey] ?? ''}
                            onChange={(event) => setAreaAssignments((values) => ({ ...values, [groupKey]: event.target.value }))}
                          >
                            <option value="">Alan seç</option>
                            {areaOptions.map((area) => <option key={area} value={area}>{area}</option>)}
                          </select>
                        </label>
                      )
                    })}
                    <p className="privacy-note">Bu toplu atama yalnızca alanı boş öğrencileri doldurur. Dolu alan değerleri korunur.</p>
                    <button
                      className="commit-import"
                      type="button"
                      data-testid="apply-areas-btn"
                      disabled={importLoading || !requiredMappingsComplete || !areaAssignmentsComplete}
                      onClick={validateStudentFile}
                    >
                      {importLoading ? 'Kontrol ediliyor…' : areaAssignmentsComplete ? 'Alanları uygula ve devam et' : 'Devam etmek için tüm alanları seç'}
                    </button>
                  </div>
                )}
                {importValidation.issues.length > 0 && (
                  <ul>
                    {importValidation.issues.map((issue, index) => (
                      <li key={index}>{issue.source ? `${issue.source} · ` : ''}Satır {issue.row}: {issue.issue} — {issue.fields.join(', ')}</li>
                    ))}
                  </ul>
                )}
                {importValidation.issues_truncated && <p>İlk 50 sorun gösteriliyor.</p>}
                {importValidation.classes.length > 0 && (
                  <div className="table-scroll">
                    <table>
                      <thead><tr><th>Sınıf</th><th>Şube</th><th>Öğrenci sayısı</th></tr></thead>
                      <tbody>
                        {importValidation.classes.map((item) => (
                          <tr key={`${item.class_level}-${item.section}`}>
                            <td>{item.class_level}</td><td>{item.section}</td><td>{item.student_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {importValidation.diff && (
                  <div className="diff-report">
                    <strong>Seçili eğitim yılıyla karşılaştırma</strong>
                    <div className="diff-counts">
                      <span>Yeni: {importValidation.diff.new_students.length}</span>
                      <span>Ayrılan: {importValidation.diff.departed_students.length}</span>
                      <span>Bilgisi değişen: {importValidation.diff.changed_students.length}</span>
                      <span>Numarası farklı kişiye geçmiş: {importValidation.diff.reassigned_numbers.length}</span>
                      <span>Aynı: {importValidation.diff.unchanged_count}</span>
                    </div>
                    {importValidation.diff.new_students.length > 0 && (
                      <details>
                        <summary>Yeni öğrenciler ({importValidation.diff.new_students.length})</summary>
                        <ul>{importValidation.diff.new_students.slice(0, 50).map((item) => (
                          <li key={item.school_number}>{item.school_number} · {item.name} · {item.class_level}/{item.section}</li>
                        ))}</ul>
                      </details>
                    )}
                    {importValidation.diff.departed_students.length > 0 && (
                      <details>
                        <summary>Ayrılan öğrenciler ({importValidation.diff.departed_students.length})</summary>
                        <ul>{importValidation.diff.departed_students.slice(0, 50).map((item) => (
                          <li key={item.school_number}>{item.school_number} · {item.name} · {item.class_level}/{item.section}</li>
                        ))}</ul>
                      </details>
                    )}
                    {importValidation.diff.changed_students.length > 0 && (
                      <details>
                        <summary>Bilgisi değişen öğrenciler ({importValidation.diff.changed_students.length})</summary>
                        <ul>{importValidation.diff.changed_students.slice(0, 50).map((item) => (
                          <li key={item.school_number}>{item.school_number} · {item.name} · {item.changed_fields.join(', ')}</li>
                        ))}</ul>
                      </details>
                    )}
                    {importValidation.diff.reassigned_numbers.map((item) => (
                      <p className="diff-warning" key={item.school_number}>
                        Okul no {item.school_number}: “{item.previous_name}” → “{item.incoming_name}”
                      </p>
                    ))}
                    <p className="privacy-note">
                      {importCommitResult ? 'İçe aktarma tamamlandı.' : 'Bu rapor henüz veritabanında değişiklik yapmaz.'}
                    </p>
                    {!importCommitResult && activeYear?.is_archive && (
                      <p className="area-note">Arşiv yılı salt okunur; bu yıla öğrenci listesi aktarılamaz.</p>
                    )}
                    {!importCommitResult && importValidation.valid && !activeYear?.is_archive && (
                      <button
                        className="commit-import"
                        type="button"
                        disabled={importLoading}
                        onClick={commitStudentFile}
                      >
                        {importLoading ? 'Kaydediliyor…' : 'İçe aktarmayı onayla'}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
            {importCommitResult && (
              <div className="commit-success" role="status">
                <p>Aktarım tamamlandı: {importCommitResult.created} yeni öğrenci, {importCommitResult.updated} değişen, {importCommitResult.unchanged} aynı kalan, {importCommitResult.deactivated} pasif kayıt. İşlem öncesi güvenlik yedeği de alındı.</p>
                {importCommitResult.classrooms?.length ? <details className="import-classroom-results"><summary>{importCommitResult.classrooms.length} derslik başlangıç planı</summary><ul>{importCommitResult.classrooms.map((room) => <li key={`${room.class_level}-${room.section}`}>{room.name}: {room.capacity ?? 0}/{room.requested_capacity} yer{room.needs_review ? ' · kontrol gerekli' : ''} — {room.message}</li>)}</ul><p>Düzen fiziksel sınıfın kesin çizimi değildir; manuel derslik ekranında sıra sayısı, oturma biçimi, koridor ve yerleşimi düzenleyin.</p></details> : null}
              </div>
            )}
            <p className="privacy-note">Dosya bu adımda veritabanına kaydedilmez.</p>
          </section>
        )}

        {activeSection === 'students' && (
          <section className="student-registry" aria-labelledby="student-registry-title">
            <div className="student-registry-heading">
              <div>
                <span className="eyebrow">{activeYear?.label ?? 'EĞİTİM YILI'}</span>
                <h2 id="student-registry-title">Kayıtlı öğrenci listesi</h2>
                <p>Excel aktarımını ve tekil öğrenci eklemelerini bu yıl için burada görebilirsin.</p>
              </div>
              <div className="student-registry-actions">
                <span className="student-total"><strong>{students.filter((student) => student.is_active !== false).length}</strong> aktif öğrenci</span>
                <button type="button" className="student-add-button" onClick={() => setShowInactiveStudents((shown) => !shown)}>{showInactiveStudents ? 'Pasifleri gizle' : 'Pasif kayıtları göster'}</button>
                <button type="button" className="student-add-button" disabled={!activeYearId || activeYear?.is_archive} onClick={() => { setStudentFormOpen((open) => !open); setStudentMessage('') }}>
                  {studentFormOpen ? 'Formu kapat' : '+ Öğrenci ekle'}
                </button>
              </div>
            </div>
            {activeYear?.is_archive && <p className="student-archive-note">Arşiv yılı salt okunur; bu yıla öğrenci eklenemez.</p>}
            {studentFormOpen && <form className="student-entry-form" onSubmit={saveManualStudent}>
              <label><span>Okul numarası *</span><input required maxLength={64} value={studentDraft.school_number} onChange={(event) => setStudentDraft({ ...studentDraft, school_number: event.target.value })} /></label>
              <label><span>Ad *</span><input required maxLength={120} value={studentDraft.first_name} onChange={(event) => setStudentDraft({ ...studentDraft, first_name: event.target.value })} /></label>
              <label><span>Soyad *</span><input required maxLength={120} value={studentDraft.last_name} onChange={(event) => setStudentDraft({ ...studentDraft, last_name: event.target.value })} /></label>
              <label><span>Sınıf *</span><select value={studentDraft.class_level} onChange={(event) => setStudentDraft({ ...studentDraft, class_level: event.target.value, area: ['9', '10'].includes(event.target.value) ? '' : studentDraft.area || 'Sayısal' })}><option value="9">9. sınıf</option><option value="10">10. sınıf</option><option value="11">11. sınıf</option><option value="12">12. sınıf</option></select></label>
              <label><span>Şube *</span><input required maxLength={32} value={studentDraft.section} onChange={(event) => setStudentDraft({ ...studentDraft, section: event.target.value })} /></label>
              {['11', '12'].includes(studentDraft.class_level) && <label><span>Alan *</span><select required value={studentDraft.area} onChange={(event) => setStudentDraft({ ...studentDraft, area: event.target.value })}><option value="">Alan seç</option>{areaOptions.map((area) => <option key={area}>{area}</option>)}</select></label>}
              <div className="student-entry-footer"><small>* Zorunlu alan · Okul numarası seçili yılda benzersiz olmalı.</small><button type="submit" disabled={studentSaving}>{studentSaving ? 'Kaydediliyor…' : 'Öğrenciyi kaydet'}</button></div>
            </form>}
            {studentsError && <p className="student-error" role="alert">{studentsError}</p>}
            {studentMessage && <p className="student-success" role="status">{studentMessage}</p>}
            {editingStudentId && studentEditDraft && <form className="student-entry-form student-edit-form" onSubmit={saveStudentEdit}>
              <label><span>Okul numarası *</span><input required maxLength={64} value={studentEditDraft.school_number} onChange={(event) => setStudentEditDraft({ ...studentEditDraft, school_number: event.target.value })} /></label>
              <label><span>Ad *</span><input required maxLength={120} value={studentEditDraft.first_name} onChange={(event) => setStudentEditDraft({ ...studentEditDraft, first_name: event.target.value })} /></label>
              <label><span>Soyad *</span><input required maxLength={120} value={studentEditDraft.last_name} onChange={(event) => setStudentEditDraft({ ...studentEditDraft, last_name: event.target.value })} /></label>
              <label><span>Sınıf *</span><select value={studentEditDraft.class_level} onChange={(event) => setStudentEditDraft({ ...studentEditDraft, class_level: event.target.value, area: ['9', '10'].includes(event.target.value) ? '' : studentEditDraft.area || 'Sayısal' })}><option value="9">9. sınıf</option><option value="10">10. sınıf</option><option value="11">11. sınıf</option><option value="12">12. sınıf</option></select></label>
              <label><span>Şube *</span><input required maxLength={32} value={studentEditDraft.section} onChange={(event) => setStudentEditDraft({ ...studentEditDraft, section: event.target.value })} /></label>
              {['11', '12'].includes(studentEditDraft.class_level) && <label><span>Alan *</span><select required value={studentEditDraft.area} onChange={(event) => setStudentEditDraft({ ...studentEditDraft, area: event.target.value })}><option value="">Alan seç</option>{areaOptions.map((area) => <option key={area}>{area}</option>)}</select></label>}
              <div className="student-entry-footer"><small>Düzenleme açık sınav taslaklarını geçersiz kılar; yeni dağıtım üretin. Tamamlananlar değişmez.</small><div><button type="button" onClick={() => { setEditingStudentId(null); setStudentEditDraft(null) }}>Vazgeç</button><button type="submit" disabled={studentSaving}>{studentSaving ? 'Kaydediliyor…' : 'Değişiklikleri kaydet'}</button></div></div>
            </form>}
            {studentsLoading ? <p className="student-empty">Öğrenci listesi yükleniyor…</p> : students.length === 0 ? <div className="student-empty"><strong>Bu eğitim yılında henüz öğrenci yok.</strong><span>Excel şablonunu kullanabilir veya yukarıdan tek öğrenci ekleyebilirsin. İndirilen demo kayıtları yalnızca sen içe aktarırsan kaydedilir.</span></div> : <><div className="student-filter-bar">
              <label><span>Ara</span><input type="search" data-testid="student-search" placeholder="Ad, soyad veya okul no" value={studentQuery} onChange={(event) => setStudentQuery(event.target.value)} /></label>
              <label><span>Sınıf / şube</span><select data-testid="student-class-filter" value={studentClassFilter} onChange={(event) => setStudentClassFilter(event.target.value)}><option value="">Tüm sınıflar</option>{studentClassOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <span className="student-filter-count" data-testid="student-filter-count" role="status">{filteredStudents.length === students.length ? `${students.length} kayıt` : `${filteredStudents.length} / ${students.length} kayıt`}</span>
              {(studentQuery || studentClassFilter) && <button type="button" className="student-add-button" onClick={() => { setStudentQuery(''); setStudentClassFilter('') }}>Filtreyi temizle</button>}
            </div>
            {filteredStudents.length === 0 ? <div className="student-empty"><strong>Aramayla eşleşen öğrenci yok.</strong><span>Yazımı kontrol et veya filtreyi temizle.</span></div> : <div className="table-scroll student-table-scroll">
              <table>
                <thead><tr><th>Okul no</th><th>Ad soyad</th><th>Sınıf / şube</th><th>Alan</th><th>İşlemler</th></tr></thead>
                <tbody>{filteredStudents.map((student) => <tr className={student.is_active === false ? 'inactive-student-row' : ''} key={student.id}><td>{student.school_number}</td><td>{student.first_name} {student.last_name}{student.is_active === false && <small className="inactive-student-label">Pasif · geçmiş kayıt korunuyor</small>}</td><td>{student.class_level}/{student.section}</td><td>{student.area || '—'}</td><td className="student-row-actions">{student.is_active === false ? <button type="button" disabled={activeYear?.is_archive || studentSaving} onClick={() => void changeStudentActive(student, true)}>Yeniden etkinleştir</button> : <><button type="button" disabled={activeYear?.is_archive || studentSaving} onClick={() => startStudentEdit(student)}>Düzenle</button><button type="button" disabled={activeYear?.is_archive || studentSaving} onClick={() => void changeStudentActive(student, false)}>Pasife al</button></>}</td></tr>)}</tbody>
              </table>
            </div>}</>}
          </section>
        )}
      </section>

      <Notifications />
      <footer className="page-footer">
        Çevrimdışı çalışmak üzere tasarlanmıştır <span aria-hidden="true">·</span> Veriler bu bilgisayarda kalır
      </footer>
      </div>
    </main>
  )
}
