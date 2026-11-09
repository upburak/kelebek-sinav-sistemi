import { useEffect, useState } from 'react'

type Summary = {
  from_version: string; to_version: string; platform: string; changed_file_count: number; removed_file_count: number
  changed_bytes: number; migration_required: boolean; migration_from: string | null; migration_to: string | null
  notes: string; package_sha256: string
}
type Status = {
  current_version: string; platform: string; can_apply: boolean
  last_result: { status: string; from_version: string; to_version: string; finished_at: string; message: string } | null
}

const resultLabels: Record<string, string> = { success: 'Başarılı', rolled_back: 'Geri alındı', failed: 'Uygulanmadı' }

export default function UpdateManager() {
  const [status, setStatus] = useState<Status | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [token, setToken] = useState('')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [applying, setApplying] = useState('')

  useEffect(() => {
    fetch('/api/updates/status').then((response) => response.json()).then(setStatus).catch(() => undefined)
  }, [])

  async function inspect() {
    if (!file) return
    setBusy(true); setError(''); setSummary(null); setConfirmed(false)
    const body = new FormData()
    body.append('package', file)
    try {
      const response = await fetch('/api/updates/inspect', { method: 'POST', body })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error ?? 'Paket doğrulanamadı.')
      setToken(data.token); setSummary(data.summary)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Paket doğrulanamadı.') } finally { setBusy(false) }
  }
  async function cancel() {
    await fetch('/api/updates/cancel', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }) })
    setToken(''); setSummary(null); setFile(null); setConfirmed(false)
  }
  async function apply() {
    setBusy(true); setError('')
    try {
      const response = await fetch('/api/updates/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true, token }) })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error ?? 'Güncelleme başlatılamadı.')
      setApplying(`Güvenlik yedeği alındı (${data.safety_backup}). Uygulama kapanıp ${data.to_version} sürümüyle yeniden açılacak; bu sekmeyi kapatabilirsiniz.`)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Güncelleme başlatılamadı.') } finally { setBusy(false) }
  }

  return <article className="backup-card update-card" data-testid="update-manager">
    <div className="backup-card-heading"><span className="backup-icon" aria-hidden="true">⟳</span><div><h3>Uygulama güncellemesi</h3><p>Kurulu sürüm <strong data-testid="update-current-version">{status?.current_version ?? '…'}</strong> · {status?.platform ?? ''}. Yalnızca değişen dosyaları içeren paketle güncelle; önce güvenlik yedeği alınır, sorun çıkarsa önceki sürüm ve veriler geri yüklenir.</p></div></div>
    {status?.last_result && <p className={`backup-feedback ${status.last_result.status === 'success' ? 'success' : 'error'}`} data-testid="update-last-result">Son güncelleme ({status.last_result.from_version} → {status.last_result.to_version}): <strong>{resultLabels[status.last_result.status] ?? status.last_result.status}</strong> · {status.last_result.message}</p>}
    {applying ? <p className="backup-feedback success" role="status" data-testid="update-applying">{applying}</p> : <>
      <div className="update-pick"><input type="file" accept=".zip,application/zip" data-testid="update-file-input" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setSummary(null); setError('') }} /><button type="button" className="backup-create-button" data-testid="update-inspect-btn" disabled={!file || busy} onClick={() => void inspect()}>{busy && !summary ? 'Doğrulanıyor…' : 'Paketi doğrula'}</button></div>
      {summary && <div className="update-summary" data-testid="update-summary">
        <strong>{summary.from_version} → {summary.to_version}</strong>
        <ul><li>{summary.changed_file_count} dosya değişecek ({(summary.changed_bytes / 1048576).toFixed(1)} MB), {summary.removed_file_count} dosya kaldırılacak</li><li>{summary.migration_required ? `Veritabanı güncellemesi gerekiyor (${summary.migration_from ?? '—'} → ${summary.migration_to ?? '—'})` : 'Veritabanı yapısı değişmiyor'}</li><li>Tüm dosyaların SHA-256 doğrulaması geçti</li><li>Paket özeti: <code data-testid="update-package-sha">{summary.package_sha256}</code> — yayımlanan .sha256 değeriyle karşılaştırın</li></ul>
        {summary.notes && <p>{summary.notes}</p>}
        {!status?.can_apply && <p className="backup-feedback error">Bu çalışma geliştirme modunda; güncelleme yalnızca kurulu uygulamada uygulanır.</p>}
        <label><input type="checkbox" data-testid="update-confirm-checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />Güvenlik yedeği alınsın, uygulama kapanıp güncellensin. Açık işlerimi kaydettim.</label>
        <div className="update-actions"><button type="button" data-testid="update-cancel-btn" onClick={() => void cancel()}>Vazgeç</button><button type="button" className="backup-create-button" data-testid="update-apply-btn" disabled={!confirmed || busy || !status?.can_apply} onClick={() => void apply()}>Güncellemeyi uygula</button></div>
      </div>}
    </>}
    {error && <p className="backup-feedback error" role="alert" data-testid="update-error">{error}</p>}
  </article>
}
