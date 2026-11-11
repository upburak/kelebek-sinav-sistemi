import { useEffect, useRef, useState } from 'react'

type Summary = {
  from_version: string; to_version: string; platform: string; changed_file_count: number; removed_file_count: number
  changed_bytes: number; migration_required: boolean; migration_from: string | null; migration_to: string | null
  notes: string; package_sha256: string; signature_key_id: string
}
type Status = {
  current_version: string; platform: string; can_apply: boolean; trusted_key_ids: string[]
  last_result: { status: string; from_version: string; to_version: string; finished_at: string; message: string } | null
}

type OnlineCheck = {
  checked: boolean; auto_check: boolean; current_version: string; latest_version?: string; update_available?: boolean
  release_url?: string; platform?: string; error?: string; asset?: { name: string; size: number } | null
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
  const [inputKey, setInputKey] = useState(0)
  const [online, setOnline] = useState<OnlineCheck | null>(null)
  const [onlineBusy, setOnlineBusy] = useState('')
  const [autoCheck, setAutoCheckState] = useState(true)
  // Kullanıcı kutuya dokunduysa, o sırada süren denetimin yanıtı seçimini ezmemeli.
  const autoTouched = useRef(false)
  const [autoLoaded, setAutoLoaded] = useState(false)
  const [onlineMessage, setOnlineMessage] = useState('')
  const [onlineError, setOnlineError] = useState('')

  async function checkOnline(auto = false) {
    setOnlineBusy('check'); setOnlineError(''); setOnlineMessage('')
    try {
      const response = await fetch(`/api/updates/online${auto ? '?auto=1' : ''}`)
      const data = await response.json() as OnlineCheck
      setOnline(data)
      if (data.error && !auto) setOnlineError(data.error)
    } catch { if (!auto) setOnlineError('Sürüm denetimi yapılamadı.') } finally { setOnlineBusy('') }
  }
  async function setAutoCheck(enabled: boolean) {
    autoTouched.current = true
    setAutoCheckState(enabled)
    await fetch('/api/updates/online/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ auto_check: enabled }) }).catch(() => undefined)
  }
  async function downloadOnline() {
    if (!window.confirm(`Sürüm ${online?.latest_version} indirilecek ve kurulum penceresi açılacak. Önce verilerin güvenlik yedeği alınır. Devam edilsin mi?`)) return
    setOnlineBusy('download'); setOnlineError(''); setOnlineMessage('')
    try {
      const response = await fetch('/api/updates/online/download', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true }) })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error ?? 'Paket indirilemedi.')
      setOnlineMessage(data.opened
        ? `Sürüm ${data.version} indirildi ve kurulum penceresi açıldı. Kurulum isterse sağ üstteki "Uygulamayı kapat" düğmesiyle uygulamayı kapat, kurulumu tamamla; verilerin korunur.`
        : `Sürüm ${data.version} indirildi: ${data.path}. Dosyayı açıp kurulumu başlat; verilerin korunur.`)
    } catch (reason) { setOnlineError(reason instanceof Error ? reason.message : 'Paket indirilemedi.') } finally { setOnlineBusy('') }
  }

  useEffect(() => {
    fetch('/api/updates/status').then((response) => response.json()).then((data: Status & { auto_update_check?: boolean }) => {
      setStatus(data)
      if (!autoTouched.current) setAutoCheckState(data.auto_update_check !== false)
      setAutoLoaded(true)
    }).catch(() => setAutoLoaded(true))
    void checkOnline(true)
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
    setToken(''); setSummary(null); setFile(null); setConfirmed(false); setInputKey((key) => key + 1)
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
    <div className="backup-card-heading"><span className="backup-icon" aria-hidden="true">⟳</span><div><span className="eyebrow">UYGULAMA GÜNCELLEMESİ</span><h2>Sürüm {status?.current_version ?? '…'}</h2></div></div>
    <p>Kurulu sürüm <strong data-testid="update-current-version">{status?.current_version ?? '…'}</strong> · {status?.platform ?? ''}. Yeni sürüm çıktığında buradan indirip kurabilirsin; önce güvenlik yedeği alınır ve verilerin korunur.</p>
    <div className={`online-update ${online?.update_available ? 'has-update' : ''}`} data-testid="online-update">
      <strong data-testid="online-update-status">{onlineBusy === 'check' ? 'Yeni sürüm denetleniyor…' : !online?.checked ? 'Yeni sürüm denetlenmedi' : online.update_available ? `Yeni sürüm hazır: ${online.latest_version}` : `Uygulama güncel (son sürüm ${online.latest_version})`}</strong>
      <small>Denetim yalnızca sürüm numarasını sorar; okul ve öğrenci verisi hiçbir yere gönderilmez. İnternet yoksa uygulama aynen çalışır.</small>
      <div className="update-actions">
        <button type="button" className="update-secondary-button" data-testid="online-update-check" disabled={Boolean(onlineBusy)} onClick={() => void checkOnline()}>Şimdi denetle</button>
        {online?.update_available && online.asset && <button type="button" className="backup-create-button" data-testid="online-update-download" disabled={Boolean(onlineBusy)} onClick={() => void downloadOnline()}>{onlineBusy === 'download' ? 'İndiriliyor… (1-2 dakika sürebilir)' : `Sürüm ${online.latest_version}'i indir ve kur`}</button>}
        {online?.update_available && online.release_url && <a className="update-secondary-button" href={online.release_url} target="_blank" rel="noreferrer">İndirme sayfasını aç</a>}
      </div>
      <label className="online-update-toggle"><input type="checkbox" data-testid="online-update-auto" disabled={!autoLoaded} checked={autoCheck} onChange={(event) => void setAutoCheck(event.target.checked)} />Uygulama açılırken yeni sürümü kendiliğinden denetle</label>
      {onlineMessage && <p className="backup-feedback success" role="status" data-testid="online-update-message">{onlineMessage}</p>}
      {onlineError && <p className="backup-feedback error" role="alert" data-testid="online-update-error">{onlineError}</p>}
    </div>
    <details className="update-manual"><summary>Elle güncelleme paketi yükle (ileri düzey)</summary>
    <p data-testid="update-trust-status">{status && (status.trusted_key_ids.length ? `Yalnızca yayıncı anahtarınızla imzalanmış paketler kabul edilir (anahtar ${status.trusted_key_ids.join(', ')}).` : 'Bu kurulumda yayıncı anahtarı tanımlı değil; güncelleme paketleri kabul edilmez. Tam kurulum paketiyle güncelleyin.')}</p>
    {status?.last_result && <p className={`backup-feedback ${status.last_result.status === 'success' ? 'success' : 'error'}`} data-testid="update-last-result">Son güncelleme ({status.last_result.from_version} → {status.last_result.to_version}): <strong>{resultLabels[status.last_result.status] ?? status.last_result.status}</strong> · {status.last_result.message}</p>}
    {applying ? <p className="backup-feedback success" role="status" data-testid="update-applying">{applying}</p> : status && !status.trusted_key_ids.length ? null : <>
      <label className="restore-file-label" htmlFor="update-package-file">Kelebek güncelleme paketi (ZIP)</label><div className="update-pick"><input key={inputKey} id="update-package-file" className="restore-file-input" type="file" accept=".zip,application/zip" data-testid="update-file-input" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setSummary(null); setError('') }} /><button type="button" className="backup-create-button" data-testid="update-inspect-btn" disabled={!file || busy} onClick={() => void inspect()}>{busy && !summary ? 'Doğrulanıyor…' : 'Paketi doğrula'}</button></div>
      {summary && <div className="update-summary" data-testid="update-summary">
        <strong>{summary.from_version} → {summary.to_version}</strong>
        <ul><li>{summary.changed_file_count} dosya değişecek ({summary.changed_bytes < 1048576 ? `${Math.max(1, Math.round(summary.changed_bytes / 1024))} KB` : `${(summary.changed_bytes / 1048576).toFixed(1)} MB`}), {summary.removed_file_count} dosya kaldırılacak</li><li>{summary.migration_required ? `Veritabanı güncellemesi gerekiyor (${summary.migration_from ?? '—'} → ${summary.migration_to ?? '—'})` : 'Veritabanı yapısı değişmiyor'}</li><li>Tüm dosyaların SHA-256 doğrulaması geçti</li><li data-testid="update-signature">Yayıncı imzası doğrulandı · anahtar {summary.signature_key_id}</li><li>Paket özeti: <code data-testid="update-package-sha">{summary.package_sha256}</code> — yayımlanan .sha256 değeriyle karşılaştırın</li></ul>
        {summary.notes && <p>{summary.notes}</p>}
        {!status?.can_apply && <p className="backup-feedback error">Bu çalışma geliştirme modunda; güncelleme yalnızca kurulu uygulamada uygulanır.</p>}
        <label><input type="checkbox" data-testid="update-confirm-checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />Güvenlik yedeği alınsın, uygulama kapanıp güncellensin. Açık işlerimi kaydettim.</label>
        <div className="update-actions"><button type="button" className="update-secondary-button" data-testid="update-cancel-btn" onClick={() => void cancel()}>Vazgeç</button><button type="button" className="backup-create-button" data-testid="update-apply-btn" disabled={!confirmed || busy || !status?.can_apply} onClick={() => void apply()}>Güncellemeyi uygula</button></div>
      </div>}
    </>}
    {error && <p className="backup-feedback error" role="alert" data-testid="update-error">{error}</p>}
    </details>
  </article>
}
