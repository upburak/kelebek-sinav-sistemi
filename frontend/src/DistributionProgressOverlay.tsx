import { useEffect, useState } from 'react'

type Progress = {
  active: boolean; stage: string; steps: { key: string; label: string }[]
  elapsed_seconds: number; remaining_max_seconds: number | null; time_limit_seconds: number
  solutions_found: number; best_affected_student_count: number | null; stop_requested: boolean
}

// Karar 58: dağıtım sürerken kullanıcı özel işlem ekranında kalır.
export default function DistributionProgressOverlay({ organizationId, active }: { organizationId: string; active: boolean }) {
  const [progress, setProgress] = useState<Progress | null>(null)
  const [stopError, setStopError] = useState('')
  const [stopping, setStopping] = useState(false)

  useEffect(() => {
    if (!active) { setProgress(null); setStopError(''); setStopping(false); return }
    let cancelled = false
    const poll = async () => {
      try {
        const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/distribution-progress`)
        const data = await response.json()
        if (!cancelled && data.progress?.active) setProgress(data.progress)
      } catch { /* yerel servis yanıt vermezse bir sonraki turda denenir */ }
    }
    void poll()
    const timer = window.setInterval(() => void poll(), 500)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [active, organizationId])

  if (!active) return null
  const stageIndex = progress ? progress.steps.findIndex((step) => step.key === progress.stage) : 0
  async function stop() {
    setStopping(true)
    const response = await fetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/distribution-progress/stop`, { method: 'POST' })
    if (!response.ok) setStopError('Dağıtım zaten tamamlanmak üzere.')
  }
  return <div className="distribution-overlay" role="dialog" aria-modal="true" aria-labelledby="distribution-progress-title" data-testid="distribution-progress-overlay">
    <div className="distribution-overlay-card">
      <span className="distribution-spinner" aria-hidden="true" />
      <h3 id="distribution-progress-title">Dağıtım hesaplanıyor</h3>
      <ol className="distribution-steps">{(progress?.steps ?? [{ key: 'prepare', label: 'Öğrenci, derslik ve kurallar hazırlanıyor' }]).map((step, index) => <li key={step.key} className={index < stageIndex ? 'done' : index === stageIndex ? 'current' : ''} data-testid={`distribution-step-${step.key}`}>{step.label}</li>)}</ol>
      <dl className="distribution-metrics">
        <div><dt>Geçen süre</dt><dd data-testid="distribution-elapsed">{progress ? `${progress.elapsed_seconds.toFixed(0)} sn` : '—'}</dd></div>
        <div><dt>Tahmini kalan</dt><dd data-testid="distribution-remaining">{progress?.remaining_max_seconds != null ? `en fazla ${Math.ceil(progress.remaining_max_seconds)} sn` : 'hesaplanıyor'}</dd></div>
        <div><dt>Bulunan çözüm</dt><dd data-testid="distribution-solutions">{progress?.solutions_found ?? 0}</dd></div>
        <div><dt>En iyi çözümde etkilenen</dt><dd data-testid="distribution-best">{progress?.best_affected_student_count != null ? `${progress.best_affected_student_count} öğrenci` : 'henüz yok'}</dd></div>
      </dl>
      <p>Arama süresince daha dengeli yerleşimler denenir. Durdurursan o ana kadar bulunan en iyi geçerli çözüm aday olarak kaydedilir.</p>
      {stopError && <p className="exam-error" role="alert">{stopError}</p>}
      <button type="button" data-testid="distribution-stop-btn" disabled={stopping || !progress || progress.stop_requested || progress.stage !== 'search'} onClick={() => void stop()}>{stopping || progress?.stop_requested ? 'Durduruluyor…' : 'Durdur ve en iyi çözümü kullan'}</button>
    </div>
  </div>
}
