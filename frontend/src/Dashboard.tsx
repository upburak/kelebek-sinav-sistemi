import { useEffect, useState } from 'react'

type Group = { class_level: string; section: string; area: string | null; student_count: number }
type Room = { classroom_id: string; available_seats: number; is_latest: boolean; can_select: boolean }
type Organization = {
  id: string; name: string; exam_date: string; status: string; archived_at: string | null
  exam_period_name: string | null; participant_count: number; selected_candidate_id: string | null
  room_selections: unknown[]; capacity_sufficient: boolean
}
type BackupStatus = { daily_backup_today: boolean; latest_daily_backup_at: string | null; stored_daily_backups: number }
type Section = 'school' | 'students' | 'classrooms' | 'exams' | 'backup' | 'reports'

type Props = {
  academicYearId: string | null
  readOnly: boolean
  schoolName: string
  schoolPlace: string
  principalName: string
  schoolConfigured: boolean
  onNavigate: (section: Section) => void
}

const MONTHS = ['OCA', 'ŞUB', 'MAR', 'NİS', 'MAY', 'HAZ', 'TEM', 'AĞU', 'EYL', 'EKİ', 'KAS', 'ARA']

function daysUntil(isoDate: string): number {
  const [year, month, day] = isoDate.split('-').map(Number)
  const target = new Date(year, month - 1, day).getTime()
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  return Math.round((target - today) / 86_400_000)
}

function relativeDay(days: number): string {
  if (days === 0) return 'Bugün'
  if (days === 1) return 'Yarın'
  if (days > 1) return `${days} gün sonra`
  if (days === -1) return 'Dün'
  return `${-days} gün önce`
}

function examState(item: Organization): { label: string; tone: 'done' | 'warn' | 'todo'; next: string } {
  if (item.archived_at) return { label: 'Arşivde', tone: 'done', next: 'Raporlar hazır' }
  if (item.status === 'completed') return { label: 'Kesinleşti', tone: 'done', next: 'Raporları yazdır' }
  if (item.room_selections.length === 0) return { label: 'Taslak', tone: 'todo', next: 'Derslik seç' }
  if (!item.capacity_sufficient) return { label: 'Taslak', tone: 'warn', next: 'Kapasite yetersiz' }
  if (!item.selected_candidate_id) return { label: 'Taslak', tone: 'todo', next: 'Dağıtımı oluştur' }
  return { label: 'Taslak', tone: 'todo', next: 'Kontrol et ve kesinleştir' }
}

/** Genel Bakış: okulun güncel durumu ve sıradaki adım, canlı veriden. */
export function Dashboard({ academicYearId, readOnly, schoolName, schoolPlace, principalName, schoolConfigured, onNavigate }: Props) {
  const [groups, setGroups] = useState<Group[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [backup, setBackup] = useState<BackupStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!academicYearId) return
    const controller = new AbortController()
    const query = `academic_year_id=${encodeURIComponent(academicYearId)}`
    const read = async <T,>(url: string): Promise<T> => {
      const response = await fetch(url, { signal: controller.signal })
      if (!response.ok) throw new Error('Özet bilgileri alınamadı.')
      return await response.json() as T
    }
    setLoading(true)
    setError('')
    Promise.all([
      read<{ groups: Group[] }>(`/api/student-groups?${query}`),
      read<{ rooms: Room[] }>(`/api/exam-room-options?${query}`),
      read<{ organizations: Organization[] }>(`/api/exam-organizations?${query}`),
      read<BackupStatus>('/api/backups/status').catch(() => null),
    ])
      .then(([groupData, roomData, organizationData, backupData]) => {
        setGroups(groupData.groups)
        setRooms(roomData.rooms)
        setOrganizations(organizationData.organizations)
        setBackup(backupData)
      })
      .catch((caught: unknown) => {
        if (caught instanceof Error && caught.name === 'AbortError') return
        setError('Özet bilgileri yüklenemedi. Sayfayı yenileyip tekrar deneyin.')
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [academicYearId])

  const studentCount = groups.reduce((total, group) => total + group.student_count, 0)
  const latestRooms = rooms.filter((room) => room.is_latest)
  const roomCount = new Set(latestRooms.map((room) => room.classroom_id)).size
  const seatCount = latestRooms.reduce((total, room) => total + room.available_seats, 0)
  const completedCount = organizations.filter((item) => item.status === 'completed' || item.archived_at).length
  const draftCount = organizations.length - completedCount
  const seatGap = studentCount - seatCount

  const steps = [
    { key: 'school', title: 'Okul bilgileri', hint: 'Okul adı ve müdür bilgisi raporlarda görünür.', done: schoolConfigured, action: 'Bilgileri gir', section: 'school' as Section },
    { key: 'students', title: 'Öğrenci listesi', hint: studentCount ? `${studentCount} öğrenci · ${groups.length} şube kayıtlı.` : 'e-Okul listesini Excel veya PDF olarak içe aktar.', done: studentCount > 0, action: 'Listeyi aktar', section: 'students' as Section },
    { key: 'classrooms', title: 'Derslik düzenleri', hint: roomCount ? `${roomCount} derslik · ${seatCount} kullanılabilir koltuk.` : 'Sıraları, koridorları ve koltukları gerçek sınıfa göre tanımla.', done: roomCount > 0 && seatGap <= 0, action: roomCount ? 'Düzenleri kontrol et' : 'Derslik ekle', section: 'classrooms' as Section },
    { key: 'exam', title: 'Sınav organizasyonu', hint: organizations.length ? `${organizations.length} sınav oluşturuldu.` : 'Sınavı oluştur, derslikleri seç ve dağıtımı başlat.', done: organizations.length > 0, action: 'Sınav oluştur', section: 'exams' as Section },
    { key: 'final', title: 'Kesinleştirme ve raporlar', hint: completedCount ? `${completedCount} sınav kesinleşti; raporlar hazır.` : 'Dağıtımı kontrol edip kesinleştir, krokileri ve listeleri yazdır.', done: completedCount > 0, action: 'Sınavlara git', section: 'exams' as Section },
  ]
  const doneCount = steps.filter((step) => step.done).length
  const currentIndex = steps.findIndex((step) => !step.done)

  const upcoming = [...organizations]
    .filter((item) => !item.archived_at)
    .sort((first, second) => first.exam_date.localeCompare(second.exam_date))
  const future = upcoming.filter((item) => daysUntil(item.exam_date) >= 0)
  const shown = (future.length ? future : upcoming.slice(-4)).slice(0, 5)

  const byLevel = new Map<string, number>()
  for (const group of groups) byLevel.set(group.class_level, (byLevel.get(group.class_level) ?? 0) + group.student_count)
  const levels = [...byLevel.entries()].sort((first, second) => Number(first[0]) - Number(second[0]))
  const largest = Math.max(1, ...levels.map(([, count]) => count))

  const backupText = !backup ? '—' : backup.daily_backup_today ? 'Bugün alındı' : backup.latest_daily_backup_at ? new Date(backup.latest_daily_backup_at).toLocaleDateString('tr-TR') : 'Henüz yok'

  return (
    <div className="dash" data-testid="dashboard">
      {error && <p className="exam-error" role="alert">{error}</p>}

      <section className="dash-school" aria-label="Okul kimliği">
        <span className="school-avatar large">{schoolName ? schoolName.slice(0, 1).toLocaleUpperCase('tr-TR') : '?'}</span>
        <div>
          <strong>{schoolName || 'Okul adı girilmedi'}</strong>
          <small>{[schoolPlace, principalName && `Müdür: ${principalName}`].filter(Boolean).join(' · ') || 'Okul bilgilerini girerek başlayın.'}</small>
        </div>
        <button type="button" className="dash-link" onClick={() => onNavigate('school')}>{schoolConfigured ? 'Düzenle' : 'Okul kurulumunu başlat'}</button>
      </section>

      <div className="dash-stats" aria-busy={loading}>
        <button type="button" className="dash-stat" data-testid="stat-students" onClick={() => onNavigate('students')}>
          <span>Aktif öğrenci</span><strong>{loading ? '…' : studentCount}</strong><small>{groups.length ? `${groups.length} şube` : 'Liste aktarılmadı'}</small>
        </button>
        <button type="button" className={`dash-stat ${seatGap > 0 && roomCount > 0 ? 'warn' : ''}`} data-testid="stat-seats" onClick={() => onNavigate('classrooms')}>
          <span>Koltuk kapasitesi</span><strong>{loading ? '…' : seatCount}</strong>
          <small>{roomCount === 0 ? 'Derslik tanımlanmadı' : seatGap > 0 ? `${roomCount} derslik · ${seatGap} koltuk eksik` : seatGap === 0 ? `${roomCount} derslik · öğrenci sayısına eşit` : `${roomCount} derslik · ${-seatGap} boş koltuk`}</small>
        </button>
        <button type="button" className="dash-stat" data-testid="stat-exams" onClick={() => onNavigate('exams')}>
          <span>Sınav</span><strong>{loading ? '…' : organizations.length}</strong><small>{organizations.length ? `${completedCount} kesinleşti · ${draftCount} taslak` : 'Henüz sınav yok'}</small>
        </button>
        <button type="button" className={`dash-stat ${backup && !backup.latest_daily_backup_at ? 'warn' : ''}`} data-testid="stat-backup" onClick={() => onNavigate('backup')}>
          <span>Son yedek</span><strong className="dash-stat-text">{backupText}</strong><small>{backup ? `${backup.stored_daily_backups} günlük yedek saklanıyor` : 'Yedek durumu okunamadı'}</small>
        </button>
      </div>

      <div className="dash-columns">
        <section className="dash-card" aria-labelledby="dash-steps-title">
          <header><div><span className="eyebrow">YOL HARİTASI</span><h2 id="dash-steps-title">{doneCount === steps.length ? 'Her şey hazır' : 'Sıradaki adım'}</h2></div><span className="step-count" data-testid="setup-progress">{doneCount} / {steps.length} tamam</span></header>
          <div className="dash-progress" role="progressbar" aria-valuemin={0} aria-valuemax={steps.length} aria-valuenow={doneCount}><i style={{ width: `${(doneCount / steps.length) * 100}%` }} /></div>
          <ol className="dash-steps">
            {steps.map((step, index) => {
              const state = step.done ? 'complete' : index === currentIndex ? 'current' : ''
              return <li key={step.key} className={state} data-testid={`setup-step-${step.key}`}>
                <span aria-hidden="true">{step.done ? '✓' : index + 1}</span>
                <div><strong>{step.title}</strong><small>{step.hint}</small></div>
                {step.done
                  ? <b>Tamam</b>
                  : index === currentIndex && !readOnly
                    ? <button type="button" className="dash-primary" onClick={() => onNavigate(step.section)}>{step.action}</button>
                    : <b>Bekliyor</b>}
              </li>
            })}
          </ol>
        </section>

        <section className="dash-card" aria-labelledby="dash-exams-title">
          <header><div><span className="eyebrow">TAKVİM</span><h2 id="dash-exams-title">{future.length || !upcoming.length ? 'Yaklaşan sınavlar' : 'Son sınavlar'}</h2></div><button type="button" className="dash-link" onClick={() => onNavigate('exams')}>Tümünü aç</button></header>
          {shown.length === 0
            ? <div className="dash-empty"><strong>Henüz sınav oluşturulmadı.</strong><span>Öğrenci listesi ve derslikler hazır olduğunda ilk sınavını birkaç adımda oluşturabilirsin.</span>{!readOnly && <button type="button" className="dash-primary" onClick={() => onNavigate('exams')}>Sınav oluştur</button>}</div>
            : <ul className="dash-exams">
              {shown.map((item) => {
                const [, month, day] = item.exam_date.split('-')
                const state = examState(item)
                const days = daysUntil(item.exam_date)
                return <li key={item.id}>
                  <button type="button" onClick={() => onNavigate(state.tone === 'done' ? 'reports' : 'exams')}>
                    <span className="dash-date"><b>{day}</b>{MONTHS[Number(month) - 1]}</span>
                    <span className="dash-exam-copy"><strong>{item.name}</strong><small>{[item.exam_period_name, `${item.participant_count} öğrenci`, relativeDay(days)].filter(Boolean).join(' · ')}</small></span>
                    <span className={`dash-pill ${state.tone}`}>{state.label}</span>
                    <span className="dash-next">{state.next} →</span>
                  </button>
                </li>
              })}
            </ul>}
        </section>
      </div>

      {levels.length > 0 && <section className="dash-card" aria-labelledby="dash-levels-title">
        <header><div><span className="eyebrow">ÖĞRENCİ DAĞILIMI</span><h2 id="dash-levels-title">Sınıf seviyelerine göre mevcut</h2></div><button type="button" className="dash-link" onClick={() => onNavigate('students')}>Öğrenci kayıtları</button></header>
        <div className="dash-levels">
          {levels.map(([level, count]) => <div key={level} className="dash-level">
            <span>{level}. sınıf</span>
            <div className="dash-bar"><i style={{ width: `${(count / largest) * 100}%` }} /></div>
            <strong>{count}</strong>
            <small>{groups.filter((group) => group.class_level === level).map((group) => `${group.section} (${group.student_count})`).join(' · ')}</small>
          </div>)}
        </div>
      </section>}
    </div>
  )
}
