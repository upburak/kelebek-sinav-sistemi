import { useEffect, useState } from 'react'
import ClassroomManager from './ClassroomManager'

type HealthState = 'checking' | 'online' | 'offline'

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
  header_row: number
  headers: (string | number | boolean | null)[]
  preview_rows: (string | number | boolean | null)[][]
  saved: false
}

type StudentImportValidation = {
  total_rows: number
  valid: boolean
  issue_count: number
  issues: { row: number; fields: string[]; issue: string }[]
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
  classes: { class_level: string; section: string; student_count: number }[]
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
  const [classroomPanelOpen, setClassroomPanelOpen] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    fetch('/api/health', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API yanıt vermedi')
        return response.json()
      })
      .then(() => setHealth('online'))
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === 'AbortError') return
        setHealth('offline')
      })

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

    return () => controller.abort()
  }, [])

  const activeYear = academicYears.find((year) => year.id === activeYearId)
  const hasDraftChange = Boolean(draftYearId && draftYearId !== activeYearId)
  const requiredMappingsComplete = importFields
    .filter((field) => field.required)
    .every((field) => importMapping[field.key] !== undefined)
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
      setImportPreview(data as StudentImportPreview)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Dosya önizlemesi oluşturulamadı.')
    } finally {
      setImportLoading(false)
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
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Dosya doğrulanamadı.')
      setImportValidation(data.validation as StudentImportValidation)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Dosya doğrulanamadı.')
    } finally {
      setImportLoading(false)
    }
  }

  async function commitStudentFile() {
    if (!selectedStudentFile || !activeYearId || activeYear?.is_archive || !importValidation?.valid || !importValidation.diff) return
    const confirmed = window.confirm(
      'Bu liste seçili eğitim yılına kaydedilecek. Dosyada bulunmayan öğrenciler silinmeden pasif yapılacak. Devam edilsin mi?',
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
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Öğrenci listesi kaydedilemedi.')
    } finally {
      setImportLoading(false)
    }
  }

  const statusText = {
    checking: 'Bağlantı kontrol ediliyor',
    online: 'Yerel servis çalışıyor',
    offline: 'Yerel servisle bağlantı kurulamadı',
  }[health]

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Kelebek Sınav Sistemi ana sayfa">
          <span className="brand-mark" aria-hidden="true">K</span>
          <span>Kelebek <strong>Sınav Sistemi</strong></span>
        </a>

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
        </div>
      </header>

      <section className="welcome-card" aria-labelledby="welcome-title">
        <div className="eyebrow">YEREL SINAV ORGANİZASYONU</div>
        <h1 id="welcome-title">Sınav planlaması için çalışma alanınız</h1>
        <p className="welcome-copy">
          Öğrencileri, derslikleri ve oturma düzenlerini tek bir güvenli çalışma alanında yönetin.
          Uygulama verileri bu bilgisayarda saklanır.
        </p>

        {activeYear?.is_archive && (
          <div className="archive-banner" role="status">
            {activeYear.label} arşiv yılını görüntülüyorsunuz. Bu yılın kayıtları salt okunur açılacaktır.
          </div>
        )}

        <div className="setup-notice">
          <span className="notice-icon" aria-hidden="true">✦</span>
          <div>
            <strong>{activeYear ? activeYear.label + ' çalışma yılı seçili' : 'Başlangıç ortamı hazır'}</strong>
            <p>
              {academicYears.length <= 1
                ? 'Geçmiş yıl kayıtları oluştukça yıl seçicisinde görünecek.'
                : 'Yıl seçimini sağ üstten değiştirebilirsiniz.'}
            </p>
          </div>
        </div>

        <div className="feature-grid">
          <article className="feature-card">
            <span className="feature-number">01</span>
            <h2>Öğrenci kayıtları</h2>
            <p>Okul ve sınıf listeleri için güvenli yerel kayıt alanı.</p>
            <label className="file-picker">
              <span>{importLoading ? 'Dosya okunuyor…' : 'e-Okul .xlsx dosyası seç'}</span>
              <input
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                disabled={importLoading}
                onChange={(event) => previewStudentFile(event.target.files?.[0])}
              />
            </label>
            {importError && <p className="import-error" role="alert">{importError}</p>}
          </article>
          <article className="feature-card">
            <span className="feature-number">02</span>
            <h2>Derslik düzeni</h2>
            <p>Fiziksel masa ve oturma yerlerini tanımlama.</p>
            <button className="manager-open" type="button" onClick={() => setClassroomPanelOpen(true)}>
              Derslikleri yönet
            </button>
          </article>
          <article className="feature-card">
            <span className="feature-number">03</span>
            <h2>Sınav dağıtımı</h2>
            <p>Öğrenci gruplarını seçilen dersliklere dengeli yerleştirme.</p>
            <span className="feature-state">Hazırlanıyor</span>
          </article>
        </div>

        {classroomPanelOpen && (
          <ClassroomManager
            academicYearId={activeYearId}
            academicYearLabel={activeYear?.label ?? ''}
            readOnly={activeYear?.is_archive ?? false}
            onClose={() => setClassroomPanelOpen(false)}
          />
        )}

        {importPreview && (
          <section className="import-preview" aria-labelledby="import-preview-title">
            <div className="import-preview-heading">
              <div>
                <span className="eyebrow">DOSYA ÖNİZLEMESİ</span>
                <h2 id="import-preview-title">{importPreview.filename}</h2>
              </div>
              <span className="preview-badge">Henüz kaydedilmedi</span>
            </div>
            <p>
              “{importPreview.sheet_name}” sayfası · Başlık satırı {importPreview.header_row} ·{' '}
              {importPreview.preview_rows.length} örnek satır gösteriliyor
            </p>
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
                <p>Her bilgi için dosyadaki karşılık gelen sütunu seç.</p>
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
                  </div>
                )}
                {importValidation.issues.length > 0 && (
                  <ul>
                    {importValidation.issues.map((issue, index) => (
                      <li key={index}>Satır {issue.row}: {issue.issue} — {issue.fields.join(', ')}</li>
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
              <p className="commit-success" role="status">
                Aktarım tamamlandı: {importCommitResult.created} yeni öğrenci, {importCommitResult.updated} değişen, {importCommitResult.unchanged} aynı kalan, {importCommitResult.deactivated} pasif kayıt.
              </p>
            )}
            <p className="privacy-note">Dosya bu adımda veritabanına kaydedilmez.</p>
          </section>
        )}
      </section>

      <footer className="page-footer">
        Çevrimdışı çalışmak üzere tasarlanmıştır <span aria-hidden="true">·</span> Veriler bu bilgisayarda kalır
      </footer>
    </main>
  )
}
