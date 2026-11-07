import { useState } from 'react'

type BackupDetails = {
  createdAt: string
  fileCount: number
  schemaRevision: string
}

export default function BackupManager() {
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [backup, setBackup] = useState<BackupDetails | null>(null)

  async function createBackup() {
    setCreating(true)
    setError('')
    setBackup(null)
    try {
      const response = await fetch('/api/backups', { method: 'POST' })
      const contentType = response.headers.get('content-type')?.toLocaleLowerCase('en-US') ?? ''
      if (!response.ok) {
        const body = contentType.includes('application/json')
          ? await response.json() as { error?: string }
          : {}
        throw new Error(body.error ?? 'Yedek paketi oluşturulamadı.')
      }
      if (!contentType.includes('application/zip')) {
        throw new Error('Yedek yerine beklenmeyen bir yanıt geldi. Yerel servisi yeniden başlatıp tekrar deneyin.')
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      const disposition = response.headers.get('content-disposition') ?? ''
      const fileName = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? 'kelebek-yedek.zip'
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setBackup({
        createdAt: response.headers.get('x-backup-created-at') ?? new Date().toISOString(),
        fileCount: Number(response.headers.get('x-backup-file-count') ?? '1'),
        schemaRevision: response.headers.get('x-backup-schema-revision') ?? '—',
      })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Yedek paketi oluşturulamadı.')
    } finally {
      setCreating(false)
    }
  }

  return <section className="backup-workspace" aria-labelledby="backup-title">
    <article className="backup-card">
      <div className="backup-card-heading">
        <span className="backup-icon" aria-hidden="true">↧</span>
        <div><span className="eyebrow">TAŞINABİLİR YEDEK</span><h2 id="backup-title">Okul verilerini güvenle yedekleyin</h2></div>
      </div>
      <p>ZIP paketi, veritabanının tutarlı bir kopyasını ve oluşturulmuş oturma planı PDF’lerini içerir. Dosyalar SHA-256 özetiyle listelenir ve veritabanı bütünlüğü paketlenmeden önce denetlenir.</p>
      <div className="backup-includes"><strong>Paket kapsamı</strong><ul><li>Okul profili, öğrenciler ve eğitim yılı kayıtları</li><li>Derslik düzenleri, sınav dağıtımları ve işlem geçmişi</li><li>Oluşturulmuş PDF raporları</li></ul></div>
      <div className="backup-callout">Paket öğrenci ve okul bilgileri içerir. İndirme tamamlanınca ZIP dosyasını güvenli bir konumda saklayın.</div>
      <button className="backup-create-button" type="button" disabled={creating} onClick={() => void createBackup()}>{creating ? 'Yedek hazırlanıyor…' : 'Yedek paketini oluştur ve indir'}</button>
      {error && <p className="backup-feedback error" role="alert">{error}</p>}
      {backup && <div className="backup-feedback success" role="status"><strong>Yedek paketi oluşturuldu.</strong><span>{new Date(backup.createdAt).toLocaleString('tr-TR')} · {backup.fileCount} dosya · Şema {backup.schemaRevision}</span><small>ZIP dosyası tarayıcının indirme konumuna kaydedildi.</small></div>}
    </article>
    <aside className="backup-side-note"><span className="eyebrow">GERİ YÜKLEME</span><h3>Bir sonraki adım</h3><p>Geri yüklemeden önce paket bütünlüğü ve sürüm uyumluluğu kontrol edilecek, mevcut veriler güvenlik yedeğine alınacak ve son işlem için açık onay istenecek.</p></aside>
  </section>
}
