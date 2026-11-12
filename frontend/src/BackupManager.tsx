import { notify } from './notify'
import { useEffect, useState } from 'react'

type BackupDetails = {
  createdAt: string
  fileCount: number
  schemaRevision: string
}

type AutomaticBackupStatus = {
  daily_backup_today: boolean
  latest_daily_backup_at: string | null
  stored_daily_backups: number
  retention_limit: number
}

type RestorePreview = {
  created_at: string
  application_version: string
  schema_revision: string
  target_schema_revision: string
  migration_required: boolean
  file_count: number
  report_count: number
  database_integrity: string
  sha256_verified: boolean
}

export default function BackupManager() {
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [backup, setBackup] = useState<BackupDetails | null>(null)
  const [automaticStatus, setAutomaticStatus] = useState<AutomaticBackupStatus | null>(null)
  const [restoreFile, setRestoreFile] = useState<File | null>(null)
  const [restoreToken, setRestoreToken] = useState('')
  const [restorePreview, setRestorePreview] = useState<RestorePreview | null>(null)
  const [restoreConfirmed, setRestoreConfirmed] = useState(false)
  const [restoreLoading, setRestoreLoading] = useState(false)
  const [restoreError, setRestoreError] = useState('')
  const [restoreResult, setRestoreResult] = useState('')
  const [restoreFileInputKey, setRestoreFileInputKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/backups/status', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Yedek durumu alınamadı.')
        setAutomaticStatus(await response.json() as AutomaticBackupStatus)
      })
      .catch((cause: unknown) => {
        if (cause instanceof Error && cause.name === 'AbortError') return
        setAutomaticStatus(null)
      })
    return () => controller.abort()
  }, [])

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
      notify.success(`Yedek indirildi: ${fileName}. Dosyayı güvenli bir yerde sakla.`)
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

  async function inspectRestoreBackup() {
    if (!restoreFile) return
    setRestoreLoading(true)
    setRestoreError('')
    setRestoreResult('')
    setRestorePreview(null)
    setRestoreToken('')
    setRestoreConfirmed(false)
    try {
      if (restoreToken) {
        await fetch('/api/backups/restore/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: restoreToken }),
        })
      }
      const form = new FormData()
      form.append('backup', restoreFile)
      const response = await fetch('/api/backups/restore/inspect', { method: 'POST', body: form })
      const body = await response.json() as { error?: string; token?: string; preview?: RestorePreview }
      if (!response.ok || !body.token || !body.preview) {
        throw new Error(body.error ?? 'Yedek önizlemesi oluşturulamadı.')
      }
      setRestoreToken(body.token)
      setRestorePreview(body.preview)
    } catch (cause) {
      setRestoreError(cause instanceof Error ? cause.message : 'Yedek önizlemesi oluşturulamadı.')
    } finally {
      setRestoreLoading(false)
    }
  }

  async function confirmRestore() {
    if (!restoreToken || !restoreConfirmed) return
    setRestoreLoading(true)
    setRestoreError('')
    setRestoreResult('')
    try {
      const response = await fetch('/api/backups/restore/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: restoreToken, confirmed: true }),
      })
      const body = await response.json() as { error?: string; safety_backup?: string }
      if (!response.ok) throw new Error(body.error ?? 'Geri yükleme tamamlanamadı.')
      setRestoreResult(
        `Geri yükleme tamamlandı. Mevcut verinin güvenlik kopyası alındı ` +
        `(${body.safety_backup}). Uygulamadaki verileri yenilemek için sayfayı yenileyin.`,
      )
      setRestoreToken('')
      setRestorePreview(null)
      setRestoreConfirmed(false)
      setRestoreFile(null)
      setRestoreFileInputKey((key) => key + 1)
    } catch (cause) {
      setRestoreError(cause instanceof Error ? cause.message : 'Geri yükleme tamamlanamadı.')
      setRestoreToken('')
      setRestorePreview(null)
      setRestoreConfirmed(false)
    } finally {
      setRestoreLoading(false)
    }
  }

  async function cancelRestorePreview() {
    setRestoreError('')
    try {
      if (restoreToken) {
        await fetch('/api/backups/restore/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: restoreToken }),
        })
      }
    } catch {
      setRestoreError('Önizleme temizlenemedi; geçici dosyalar en geç 15 dakika içinde kaldırılır.')
    } finally {
      setRestoreToken('')
      setRestorePreview(null)
      setRestoreConfirmed(false)
      setRestoreFile(null)
      setRestoreFileInputKey((key) => key + 1)
    }
  }

  return (
    <section className="backup-workspace" aria-labelledby="backup-title">
      <article className="backup-card">
        <div className="backup-card-heading">
          <span className="backup-icon" aria-hidden="true">↧</span>
          <div>
            <span className="eyebrow">TAŞINABİLİR YEDEK</span>
            <h2 id="backup-title">Okul verilerini güvenle yedekleyin</h2>
          </div>
        </div>
        <p>
          ZIP paketi, veritabanının tutarlı bir kopyasını ve oluşturulmuş oturma planı PDF’lerini
          içerir. Dosyalar SHA-256 özetiyle listelenir ve veritabanı bütünlüğü paketlenmeden önce
          denetlenir.
        </p>
        <div className="backup-includes">
          <strong>Paket kapsamı</strong>
          <ul>
            <li>Okul profili, öğrenciler ve eğitim yılı kayıtları</li>
            <li>Derslik düzenleri, sınav dağıtımları ve işlem geçmişi</li>
            <li>Oluşturulmuş PDF raporları</li>
          </ul>
        </div>
        <div className="backup-callout">
          Paket öğrenci ve okul bilgileri içerir. İndirme tamamlanınca ZIP dosyasını güvenli bir
          konumda saklayın.
        </div>
        <button
          className="backup-create-button"
          type="button"
          disabled={creating}
          onClick={() => void createBackup()}
        >
          {creating ? 'Yedek hazırlanıyor…' : 'Yedek paketini oluştur ve indir'}
        </button>
        {error && <p className="backup-feedback error" role="alert">{error}</p>}
        {backup && (
          <div className="backup-feedback success" role="status">
            <strong>Yedek paketi oluşturuldu.</strong>
            <span>
              {new Date(backup.createdAt).toLocaleString('tr-TR')} · {backup.fileCount} dosya ·
              {' '}Şema {backup.schemaRevision}
            </span>
            <small>ZIP dosyası tarayıcının indirme konumuna kaydedildi.</small>
          </div>
        )}

        <div className="backup-note-divider" />
        <div className="restore-heading">
          <span className="eyebrow">YEDEKTEN GERİ YÜKLEME</span>
          <h3>Taşınabilir paketi doğrulayın</h3>
        </div>
        <p>
          Önizleme dosyanın SHA-256 özetlerini, ZIP bütünlüğünü ve şema uyumluluğunu denetler. Bu
          aşamada mevcut veriler değiştirilmez.
        </p>
        <label className="restore-file-label" htmlFor="restore-backup-file">Kelebek ZIP yedeği</label>
        <input
          key={restoreFileInputKey}
          id="restore-backup-file"
          className="restore-file-input"
          type="file"
          accept=".zip,application/zip"
          disabled={restoreLoading}
          onChange={(event) => {
            if (restoreToken) {
              void fetch('/api/backups/restore/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: restoreToken }),
              }).catch(() => undefined)
            }
            setRestoreFile(event.target.files?.[0] ?? null)
            setRestorePreview(null)
            setRestoreToken('')
            setRestoreConfirmed(false)
            setRestoreError('')
            setRestoreResult('')
          }}
        />
        <small className="restore-size-note">Yedek dosyası en fazla 512 MB olabilir.</small>
        <button
          className="backup-create-button restore-preview-button"
          type="button"
          disabled={!restoreFile || restoreLoading}
          onClick={() => void inspectRestoreBackup()}
        >
          {restoreLoading ? 'Yedek denetleniyor…' : 'Yedeği doğrula ve önizle'}
        </button>
        {restoreError && <p className="backup-feedback error" role="alert">{restoreError}</p>}
        {restoreResult && (
          <div className="backup-feedback success" role="status">
            <strong>Geri yükleme tamamlandı.</strong>
            <span>{restoreResult}</span>
            <button
              className="restore-reload-button"
              type="button"
              onClick={() => window.location.reload()}
            >
              Uygulamayı yenile
            </button>
          </div>
        )}
        {restorePreview && (
          <div className="restore-preview" role="region" aria-label="Yedek önizlemesi">
            <strong>Güvenli önizleme</strong>
            <dl>
              <div>
                <dt>Oluşturulma</dt>
                <dd>{new Date(restorePreview.created_at).toLocaleString('tr-TR')}</dd>
              </div>
              <div>
                <dt>Uygulama / şema</dt>
                <dd>{restorePreview.application_version} · {restorePreview.schema_revision}</dd>
              </div>
              <div>
                <dt>İşlem</dt>
                <dd>
                  {restorePreview.migration_required
                    ? `${restorePreview.schema_revision} → ${restorePreview.target_schema_revision} geçişi`
                    : 'Şema geçişi gerekmiyor'}
                </dd>
              </div>
              <div>
                <dt>Dosyalar</dt>
                <dd>Veritabanı ve {restorePreview.report_count} PDF · {restorePreview.file_count} dosya</dd>
              </div>
              <div>
                <dt>Kontroller</dt>
                <dd>
                  SHA-256 doğrulandı · SQLite bütünlüğü {restorePreview.database_integrity}
                </dd>
              </div>
            </dl>
            <p className="restore-warning">
              Onaydan sonra mevcut okul ve öğrenci verileri seçilen yedekle değiştirilir. İşlem
              öncesi mevcut verinin güvenlik kopyası alınır.
            </p>
            <label className="restore-confirm-label">
              <input
                type="checkbox"
                checked={restoreConfirmed}
                onChange={(event) => setRestoreConfirmed(event.target.checked)}
              />
              Seçtiğim yedeğin mevcut verilerin yerini almasını onaylıyorum.
            </label>
            <button
              className="restore-final-button"
              type="button"
              disabled={!restoreConfirmed || restoreLoading}
              onClick={() => void confirmRestore()}
            >
              {restoreLoading ? 'Güvenli geri yükleme yapılıyor…' : 'Geri yüklemeyi son kez onayla'}
            </button>
            <button
              className="restore-cancel-button"
              type="button"
              disabled={restoreLoading}
              onClick={() => void cancelRestorePreview()}
            >
              Önizlemeyi iptal et
            </button>
          </div>
        )}
      </article>

      <aside className="backup-side-note">
        <span className="eyebrow">OTOMATİK KORUMA</span>
        <h3>
          {automaticStatus
            ? automaticStatus.daily_backup_today ? 'Bugünkü yedek hazır' : 'Bugünkü yedek alınmadı'
            : 'Yedek durumu alınamadı'}
        </h3>
        <p>
          {automaticStatus
            ? `${automaticStatus.stored_daily_backups} / ${automaticStatus.retention_limit} günlük otomatik paket saklanıyor. Uygulama yeni günün ilk kullanımında yedek alır.`
            : 'Yerel servisle bağlantıyı kontrol edin; yedek alınmadıysa bu ekranda durum görünür.'}
        </p>
        {automaticStatus?.latest_daily_backup_at && (
          <small className="backup-latest-time">
            Son otomatik yedek: {new Date(automaticStatus.latest_daily_backup_at).toLocaleString('tr-TR')}
          </small>
        )}
        {!automaticStatus?.daily_backup_today && (
          <p className="backup-status-warning" role="status">
            Bugünün otomatik yedeği hazır değil. Bir sonraki API isteğinde yeniden denenecek.
          </p>
        )}
        <p>Öğrenci listesi aktarılmadan önce ayrıca güvenlik kopyası oluşturulur.</p>
        <div className="backup-note-divider" />
        <span className="eyebrow">GÜVENLİ KULLANIM</span>
        <h3>Yedek dosyasını koruyun</h3>
        <p>ZIP paketi okul ve öğrenci bilgileri içerebilir. Dosyayı erişimi sınırlı, güvenli bir konumda saklayın.</p>
      </aside>
    </section>
  )
}
