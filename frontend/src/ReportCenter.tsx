import { useEffect, useState } from 'react'

type ReportKind = 'seating_plan_pdf' | 'attendance_pdf' | 'room_student_list_pdf' | 'general_distribution_pdf' | 'class_student_list_pdf'
type ReportStatus = 'not_generated' | 'current' | 'stale'
type FieldProfile = 'attendance' | 'room' | 'general_pdf' | 'general_excel' | 'class'
const fieldProfiles: Record<FieldProfile, { title: string; fields: { key: string; label: string }[] }> = {
  attendance: { title: 'Yoklama çizelgesi', fields: [
    { key: 'seat', label: 'Koltuk' }, { key: 'school_number', label: 'Okul numarası' },
    { key: 'name', label: 'Adı soyadı' }, { key: 'class', label: 'Sınıf/şube' }, { key: 'area', label: 'Alan' },
  ] },
  room: { title: 'Derslik öğrenci listesi', fields: [
    { key: 'seat', label: 'Koltuk' }, { key: 'school_number', label: 'Okul numarası' },
    { key: 'name', label: 'Adı soyadı' }, { key: 'class', label: 'Sınıf/şube' },
    { key: 'area', label: 'Alan' }, { key: 'status', label: 'Dolu/boş durumu' },
  ] },
  general_pdf: { title: 'Genel dağıtım PDF', fields: [
    { key: 'room', label: 'Derslik' }, { key: 'seat', label: 'Koltuk' },
    { key: 'school_number', label: 'Okul numarası' }, { key: 'name', label: 'Adı soyadı' },
    { key: 'class', label: 'Sınıf/şube' }, { key: 'area', label: 'Alan' },
  ] },
  general_excel: { title: 'Genel dağıtım Excel', fields: [
    { key: 'room', label: 'Derslik' }, { key: 'seat', label: 'Koltuk' },
    { key: 'school_number', label: 'Okul numarası' }, { key: 'name', label: 'Adı soyadı' },
    { key: 'class', label: 'Sınıf/şube' }, { key: 'area', label: 'Alan' }, { key: 'courses', label: 'Dersler' },
  ] },
  class: { title: 'Sınıf bazlı öğrenci listesi', fields: [
    { key: 'room', label: 'Derslik' }, { key: 'seat', label: 'Koltuk' },
    { key: 'school_number', label: 'Okul numarası' }, { key: 'name', label: 'Adı soyadı' },
    { key: 'class', label: 'Sınıf/şube' }, { key: 'area', label: 'Alan' },
  ] },
}
type Exam = {
  id: string
  name: string
  exam_date: string
  status: 'draft' | 'completed'
  participant_count: number
  course_names: string[]
  room_selections: { classroom_name: string }[]
  report_statuses: Partial<Record<ReportKind, { report_status: ReportStatus; report_updated_at: string | null }>>
}

const pdfReports: { kind: ReportKind; title: string; path: string; profile?: FieldProfile }[] = [
  { kind: 'seating_plan_pdf', title: 'Derslik kapı krokisi · PDF', path: 'seating-plan.pdf' },
  { kind: 'attendance_pdf', title: 'Yoklama çizelgesi · PDF', path: 'attendance.pdf', profile: 'attendance' },
  { kind: 'room_student_list_pdf', title: 'Derslik öğrenci listesi · PDF', path: 'room-students.pdf', profile: 'room' },
  { kind: 'general_distribution_pdf', title: 'Genel sınav dağıtımı · PDF', path: 'distribution.pdf', profile: 'general_pdf' },
  { kind: 'class_student_list_pdf', title: 'Sınıf bazlı öğrenci listesi · PDF', path: 'class-students.pdf', profile: 'class' },
]

const excelReports = [
  { title: 'Derslik öğrenci listesi · Excel', path: 'room-students.xlsx', profile: 'room' as const },
  { title: 'Genel sınav dağıtımı · Excel', path: 'distribution.xlsx', profile: 'general_excel' as const },
  { title: 'Sınıf bazlı öğrenci listesi · Excel', path: 'class-students.xlsx', profile: 'class' as const },
]

const headerParts = [
  { key: 'school', label: 'Okul adı' }, { key: 'title', label: 'Rapor başlığı' },
  { key: 'exam', label: 'Sınav adı' }, { key: 'date', label: 'Tarih' },
  { key: 'course', label: 'Ders' }, { key: 'room', label: 'Derslik / sınıf' },
]

function statusLabel(status: ReportStatus) {
  if (status === 'current') return 'Güncel rapor · yenile'
  if (status === 'stale') return 'Dağıtım değişti · yeniden oluştur'
  return 'Oluştur'
}

export default function ReportCenter({ academicYearId, academicYearLabel, onExams }: {
  academicYearId: string | null
  academicYearLabel: string
  onExams: () => void
}) {
  const [exams, setExams] = useState<Exam[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)
  const [working, setWorking] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [paper, setPaper] = useState('A4')
  const [orientation, setOrientation] = useState('auto')
  const [margin, setMargin] = useState('12')
  const [visibleHeader, setVisibleHeader] = useState<string[]>(headerParts.map((part) => part.key))
  const [customTitle, setCustomTitle] = useState('')
  const [scale, setScale] = useState('100')
  const [readyExamId, setReadyExamId] = useState('')
  const [violationsAccepted, setViolationsAccepted] = useState(false)
  const [review, setReview] = useState<{ affected_student_count: number; violation_count: number; unassigned_count: number } | null>(null)
  const [fieldProfile, setFieldProfile] = useState<FieldProfile>('room')
  const [selectedFields, setSelectedFields] = useState<Record<FieldProfile, string[]>>(() =>
    Object.fromEntries(Object.entries(fieldProfiles).map(([key, profile]) => [
      key, profile.fields.map((field) => field.key),
    ])) as Record<FieldProfile, string[]>,
  )
  const [fieldLabels, setFieldLabels] = useState<Record<FieldProfile, Record<string, string>>>(() =>
    Object.fromEntries(Object.entries(fieldProfiles).map(([key, profile]) => [
      key, Object.fromEntries(profile.fields.map((field) => [field.key, field.label])),
    ])) as Record<FieldProfile, Record<string, string>>,
  )

  useEffect(() => {
    let active = true
    async function load() {
      if (!academicYearId) {
        setExams([])
        return
      }
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`/api/exam-organizations?academic_year_id=${encodeURIComponent(academicYearId)}`)
        const data = await response.json()
        if (!response.ok) throw new Error(data.error ?? 'Sınav organizasyonları yüklenemedi.')
        if (!active) return
        const completed = (data.organizations as Exam[]).filter((exam) => exam.status === 'completed')
        setExams(completed)
        setSelectedId((current) => completed.some((exam) => exam.id === current) ? current : completed[0]?.id ?? '')
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : 'Rapor listesi yüklenemedi.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => { active = false }
  }, [academicYearId])

  const exam = exams.find((item) => item.id === selectedId)
  const ready = Boolean(exam) && readyExamId === exam?.id && !review?.unassigned_count && (!review?.violation_count || violationsAccepted)

  useEffect(() => {
    setReview(null)
    setReadyExamId('')
    setViolationsAccepted(false)
    if (!selectedId) return
    let active = true
    fetch(`/api/exam-organizations/${encodeURIComponent(selectedId)}/final-review`)
      .then(async (response) => { const data = await response.json(); if (active && response.ok) setReview(data.review) })
      .catch(() => undefined)
    return () => { active = false }
  }, [selectedId])
  const profileFields = fieldProfiles[fieldProfile].fields
  const orderedProfileFields = [
    ...selectedFields[fieldProfile].map((key) => profileFields.find((field) => field.key === key)!),
    ...profileFields.filter((field) => !selectedFields[fieldProfile].includes(field.key)),
  ]

  function pdfOptionsQuery() {
    const params = new URLSearchParams({ paper, margin_mm: margin })
    if (orientation !== 'auto') params.set('orientation', orientation)
    return params.toString()
  }

  function fieldQuery(profile: FieldProfile) {
    const fields = selectedFields[profile]
    return new URLSearchParams({
      fields: fields.join(','),
      labels: JSON.stringify(Object.fromEntries(fields.map((key) => [key, fieldLabels[profile][key]]))),
    }).toString()
  }

  function hasValidHeaders(profile: FieldProfile) {
    return selectedFields[profile].every((key) => {
      const label = fieldLabels[profile][key]?.trim() ?? ''
      return label.length > 0 && label.length <= 40
    })
  }

  function moveField(profile: FieldProfile, fieldKey: string, direction: -1 | 1) {
    setSelectedFields((current) => {
      const fields = [...current[profile]]
      const index = fields.indexOf(fieldKey)
      const targetIndex = index + direction
      if (index < 0 || targetIndex < 0 || targetIndex >= fields.length) return current
      ;[fields[index], fields[targetIndex]] = [fields[targetIndex], fields[index]]
      return { ...current, [profile]: fields }
    })
  }

  function pdfReportQuery(profile?: FieldProfile) {
    const query = new URLSearchParams(pdfOptionsQuery())
    if (profile) {
      query.set('header', visibleHeader.join(','))
      query.set('scale', scale)
      if (customTitle.trim()) query.set('title', customTitle.trim())
      const fields = selectedFields[profile]
      query.set('fields', fields.join(','))
      query.set('labels', JSON.stringify(Object.fromEntries(fields.map((key) => [key, fieldLabels[profile][key]]))))
    }
    return query.toString()
  }

  async function openPdf(path: string, kind: ReportKind, profile?: FieldProfile) {
    if (!exam) return
    setError('')
    setMessage('')
    const preview = window.open('about:blank', '_blank')
    if (!preview) {
      setError('PDF ön izlemesi açılamadı. Tarayıcıda açılır pencereye izin verip tekrar deneyin.')
      return
    }
    setWorking(path)
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(exam.id)}/reports/${path}?${pdfReportQuery(profile)}`)
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error ?? 'PDF oluşturulamadı.')
      }
      const url = URL.createObjectURL(await response.blob())
      preview.location.href = url
      window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
      setExams((items) => items.map((item) => item.id === exam.id ? {
        ...item,
        report_statuses: { ...item.report_statuses, [kind]: { report_status: 'current', report_updated_at: new Date().toISOString() } },
      } : item))
      setMessage('PDF ön izlemesi yeni sekmede açıldı.')
    } catch (reason) {
      preview.close()
      setError(reason instanceof Error ? reason.message : 'PDF oluşturulamadı.')
    } finally {
      setWorking('')
    }
  }

  async function downloadExcel(path: string, profile: FieldProfile) {
    if (!exam) return
    setError('')
    setMessage('')
    setWorking(path)
    try {
      const response = await fetch(`/api/exam-organizations/${encodeURIComponent(exam.id)}/reports/${path}?${fieldQuery(profile)}`)
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error ?? 'Excel dosyası oluşturulamadı.')
      }
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = url
      link.download = response.headers.get('Content-Disposition')?.match(/filename="?([^";]+)"?/)?.[1] ?? path
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
      setMessage('Excel dosyası indirildi. Dosyadaki düzenlemeler uygulamadaki sınavı değiştirmez.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Excel dosyası oluşturulamadı.')
    } finally {
      setWorking('')
    }
  }

  return <section className="report-center" aria-labelledby="report-center-title">
    <header className="report-center-heading">
      <div><span className="eyebrow">KESİNLEŞMİŞ DAĞITIMLAR</span><h2 id="report-center-title">Raporlar</h2><p>Raporlar seçtiğin güncel dağıtımdan hazırlanır. Excel kopyasını kendi ihtiyacına göre düzenleyebilirsin.</p></div>
      <span className="report-year">{academicYearLabel}</span>
    </header>
    {loading ? <div className="exam-empty">Kesinleşmiş sınavlar yükleniyor…</div> : exams.length === 0 ? <div className="report-empty"><strong>Bu eğitim yılında kesinleşmiş sınav yok.</strong><span>Rapor oluşturmak için önce bir sınav dağıtımını son kontrolden geçirip kesinleştir.</span><button type="button" onClick={onExams}>Sınav organizasyonlarına git</button></div> : <>
      <label className="report-exam-select"><span>Raporlanacak sınav</span><select data-testid="report-exam-select" value={selectedId} onChange={(event) => { setSelectedId(event.target.value); setError(''); setMessage('') }}>{exams.map((item) => <option key={item.id} value={item.id}>{item.name} · {new Date(`${item.exam_date}T12:00:00`).toLocaleDateString('tr-TR')}</option>)}</select></label>
      {exam && <>
        <div className="report-exam-summary"><strong>{exam.name}</strong><span>{exam.course_names.length ? exam.course_names.join(' · ') : 'Genel sınav'} · {exam.participant_count} öğrenci · {exam.room_selections.map((room) => room.classroom_name).join(', ') || 'Derslik bilgisi yok'}</span></div>
        <section className="report-settings" aria-label="PDF sayfa ayarları"><div><strong>PDF sayfa ayarları</strong><small>Otomatik yön, raporun varsayılan yönünü kullanır.</small></div><label><span>Kâğıt boyutu</span><select value={paper} onChange={(event) => setPaper(event.target.value)}><option value="A4">A4</option><option value="A3">A3</option><option value="A5">A5</option><option value="LETTER">Letter</option><option value="LEGAL">Legal</option></select></label><label><span>Sayfa yönü</span><select value={orientation} onChange={(event) => setOrientation(event.target.value)}><option value="auto">Otomatik</option><option value="portrait">Dikey</option><option value="landscape">Yatay</option></select></label><label><span>Kenar boşluğu (mm)</span><input type="number" min="5" max="30" step="1" value={margin} onChange={(event) => setMargin(event.target.value)} /></label></section>
        <section className="report-settings report-header-settings" aria-label="Rapor üst bilgisi" data-testid="report-header-settings"><div><strong>Üst bilgi ve ölçek</strong><small>Liste ve yoklama PDF'lerinde görünecek başlık bilgilerini seç. Kapı krokisi sabit kalır.</small></div><div className="report-header-parts">{headerParts.map((part) => <label key={part.key}><input type="checkbox" data-testid={`report-header-${part.key}`} checked={visibleHeader.includes(part.key)} onChange={(event) => setVisibleHeader((current) => event.target.checked ? [...current, part.key] : current.filter((key) => key !== part.key))} /><span>{part.label}</span></label>)}</div><label><span>Özel rapor başlığı</span><input data-testid="report-custom-title" maxLength={80} placeholder="Boş bırakılırsa varsayılan" value={customTitle} onChange={(event) => setCustomTitle(event.target.value)} /></label><label><span>Yazı ölçeği</span><select data-testid="report-scale" value={scale} onChange={(event) => setScale(event.target.value)}>{['80', '90', '100', '110', '120', '130'].map((value) => <option key={value} value={value}>%{value}</option>)}</select></label></section>
        <section className="report-ready" data-testid="report-ready-panel"><strong>Rapor öncesi son kontrol</strong>{review ? <span>{review.violation_count} komşuluk ihlali · {review.affected_student_count} öğrenci etkileniyor{review.unassigned_count ? ` · ${review.unassigned_count} bekleyen öğrenci` : ''}</span> : <span>Kontrol bilgisi yükleniyor…</span>}{Boolean(review?.unassigned_count) && <p className="exam-error" data-testid="report-blocked-waiting">Bekleyen öğrenciler koltuğa yerleşmeden rapor oluşturulamaz. Sınav organizasyonlarında yerleşimi tamamla.</p>}{Boolean(review?.violation_count) && <label><input type="checkbox" data-testid="report-accept-violations" checked={violationsAccepted} onChange={(event) => setViolationsAccepted(event.target.checked)} />Listelenen komşuluk ihlallerini bilerek kabul ediyorum.</label>}<label><input type="checkbox" data-testid="report-ready-confirm" checked={readyExamId === exam.id} onChange={(event) => setReadyExamId(event.target.checked ? exam.id : '')} />Dağıtım düzenlemeleri tamamlandı; raporları oluşturmaya hazırım.</label></section>
        <section className="report-field-settings" aria-label="Rapor sütunları"><div className="report-field-settings-heading"><div><strong>Rapor alanları</strong><small>Alan seçimleri rapor türüne göre ayrı uygulanır. Sütun adını ve sırasını düzenleyebilirsin. Kapı krokisinin temel alanları sabittir.</small></div><label><span>Rapor türü</span><select value={fieldProfile} onChange={(event) => setFieldProfile(event.target.value as FieldProfile)}>{Object.entries(fieldProfiles).map(([key, profile]) => <option key={key} value={key}>{profile.title}</option>)}</select></label></div><div className="report-field-list">{orderedProfileFields.map((field) => {
          const checked = selectedFields[fieldProfile].includes(field.key)
          const selectedIndex = selectedFields[fieldProfile].indexOf(field.key)
          return <div className={`report-field-row ${checked ? 'selected' : ''}`} key={field.key}><label className="report-field-toggle"><input type="checkbox" checked={checked} disabled={checked && selectedFields[fieldProfile].length === 1} onChange={(event) => setSelectedFields((current) => ({ ...current, [fieldProfile]: event.target.checked ? [...current[fieldProfile], field.key] : current[fieldProfile].filter((key) => key !== field.key) }))} /><span>{field.label}</span></label>{checked && <><input className="report-field-title" required maxLength={40} aria-label={`${field.label} sütun başlığı`} value={fieldLabels[fieldProfile][field.key]} onChange={(event) => setFieldLabels((current) => ({ ...current, [fieldProfile]: { ...current[fieldProfile], [field.key]: event.target.value } }))} /><span className="report-field-order"><button type="button" aria-label={`${field.label} sütununu yukarı taşı`} title="Yukarı taşı" disabled={selectedIndex === 0} onClick={() => moveField(fieldProfile, field.key, -1)}>↑</button><button type="button" aria-label={`${field.label} sütununu aşağı taşı`} title="Aşağı taşı" disabled={selectedIndex === selectedFields[fieldProfile].length - 1} onClick={() => moveField(fieldProfile, field.key, 1)}>↓</button></span></>}</div>
        })}</div></section>
        <section className="report-group"><div><h3>PDF raporları</h3><p>Ön izleme yeni sekmede açılır.</p></div><div className="report-grid">{pdfReports.map((report) => {
          const status = exam.report_statuses?.[report.kind]?.report_status ?? 'not_generated'
          return <article className="report-option" key={report.kind}><div><strong>{report.title}</strong><small>{report.kind === 'seating_plan_pdf' ? 'Sabit kapı krokisi düzeni' : `${selectedFields[report.profile!].length} alan seçili · ${status === 'current' ? 'Son oluşturma güncel' : status === 'stale' ? 'Dağıtım son rapordan sonra değişti' : 'Henüz oluşturulmadı'}`}</small></div><button type="button" data-testid={`report-open-${report.kind}`} disabled={!ready || Boolean(working) || Boolean(report.profile && !hasValidHeaders(report.profile))} onClick={() => void openPdf(report.path, report.kind, report.profile)}>{working === report.path ? 'Hazırlanıyor…' : statusLabel(status)}</button></article>
        })}</div></section>
        <section className="report-group"><div><h3>Excel çıktıları</h3><p>İndirilen dosyada yapacağın değişiklikler uygulamadaki dağıtımı etkilemez.</p></div><div className="report-grid">{excelReports.map((report) => <article className="report-option" key={report.path}><div><strong>{report.title}</strong><small>{selectedFields[report.profile].length} alan seçili · güncel dağıtımdan oluşturulur</small></div><button type="button" data-testid={`report-excel-${report.profile}`} disabled={!ready || Boolean(working) || !hasValidHeaders(report.profile)} onClick={() => void downloadExcel(report.path, report.profile)}>{working === report.path ? 'Hazırlanıyor…' : 'Excel indir'}</button></article>)}</div></section>
      </>}
    </>}
    {error && <p className="exam-error" role="alert">{error}</p>}{message && <p className="report-message" role="status">{message}</p>}
  </section>
}
