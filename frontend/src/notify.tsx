import { useEffect, useState } from 'react'

/**
 * Ortak sonuç bildirimi: her işlemden sonra aynı yerde "ne oldu, sırada ne var".
 * Başarı bildirimi kendiliğinden kapanır; hata, kullanıcı kapatana kadar kalır.
 */
export type NotifyAction = { label: string; onClick: () => void }
type Kind = 'success' | 'error'
type Item = { id: number; kind: Kind; message: string; action?: NotifyAction; testId?: string }

const SUCCESS_MS = 6000
const MAX_VISIBLE = 4

let items: Item[] = []
let nextId = 1
const listeners = new Set<(current: Item[]) => void>()

function publish() {
  for (const listener of listeners) listener(items)
}

function dismiss(id: number) {
  items = items.filter((item) => item.id !== id)
  publish()
}

function push(kind: Kind, message: string, action?: NotifyAction, testId?: string) {
  const item: Item = { id: nextId++, kind, message, action, testId }
  // En fazla MAX_VISIBLE bildirim: yer açmak gerekirse önce en eski başarı, yoksa en eski hata gider.
  const next = [...items, item]
  while (next.length > MAX_VISIBLE) {
    const oldestSuccess = next.findIndex((entry) => entry.kind === 'success' && entry.id !== item.id)
    next.splice(oldestSuccess >= 0 ? oldestSuccess : 0, 1)
  }
  items = next
  publish()
  if (kind === 'success') window.setTimeout(() => dismiss(item.id), SUCCESS_MS)
}

export const notify = {
  success(message: string, action?: NotifyAction, testId?: string) { push('success', message, action, testId) },
  error(message: string) { push('error', message) },
}

declare global {
  interface Window { __kelebekNotify?: typeof notify }
}
// Tarayıcı testleri bildirimi doğrudan tetikleyebilsin.
if (typeof window !== 'undefined') window.__kelebekNotify = notify

export function Notifications() {
  const [current, setCurrent] = useState<Item[]>(items)
  useEffect(() => {
    listeners.add(setCurrent)
    return () => { listeners.delete(setCurrent) }
  }, [])
  return <div className="notifications" data-testid="notifications" aria-live="polite">
    {current.map((item) => <div key={item.id} className={`notification ${item.kind}`} data-testid="notification" data-kind={item.kind} data-note={item.testId} role={item.kind === 'error' ? 'alert' : 'status'}>
      <span className="notification-mark" aria-hidden="true">{item.kind === 'error' ? '!' : '✓'}</span>
      <p>{item.message}</p>
      {item.action && <button type="button" className="notification-action" onClick={() => { item.action!.onClick(); dismiss(item.id) }}>{item.action.label}</button>}
      <button type="button" className="notification-close" aria-label="Bildirimi kapat" onClick={() => dismiss(item.id)}>×</button>
    </div>)}
  </div>
}
