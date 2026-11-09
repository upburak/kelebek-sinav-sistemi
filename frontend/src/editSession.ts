// Karar 40: her sekmeye kimlik ver; aynı sınavı yalnızca bir sekme düzenleyebilir.
export type EditLocks = Record<string, { mine: boolean }>

const TAB_HEADER = 'X-Kelebek-Tab'
const tabId = `tab-${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)}`

let locks: EditLocks = {}
const listeners = new Set<(value: EditLocks) => void>()
const nativeFetch = window.fetch.bind(window)

function publish(value: EditLocks) {
  locks = value
  listeners.forEach((listener) => listener(locks))
}

function isApiRequest(input: RequestInfo | URL) {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
  return url.startsWith('/api/') || url.startsWith(`${window.location.origin}/api/`)
}

window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
  if (!isApiRequest(input)) return nativeFetch(input, init)
  const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined))
  headers.set(TAB_HEADER, tabId)
  return nativeFetch(input, { ...init, headers })
}

export async function refreshLocks(path = '/api/edit-locks/heartbeat') {
  try {
    const response = await nativeFetch(path, { method: path.endsWith('heartbeat') ? 'POST' : 'GET', headers: { [TAB_HEADER]: tabId } })
    if (response.ok) publish((await response.json()).locks as EditLocks)
  } catch {
    // Yerel servis kısa süreli kapalıysa bir sonraki denemede yenilenir.
  }
}

export async function takeOverEditing(organizationId: string) {
  const response = await nativeFetch(`/api/exam-organizations/${encodeURIComponent(organizationId)}/edit-lock`, {
    method: 'POST', headers: { [TAB_HEADER]: tabId, 'Content-Type': 'application/json' }, body: JSON.stringify({ takeover: true }),
  })
  if (response.ok) publish((await response.json()).locks as EditLocks)
  return response.ok
}

export function subscribeLocks(listener: (value: EditLocks) => void) {
  listeners.add(listener)
  listener(locks)
  return () => { listeners.delete(listener) }
}

window.setInterval(() => void refreshLocks(), 10_000)
window.addEventListener('pagehide', () => {
  navigator.sendBeacon(`/api/edit-locks/release?tab=${encodeURIComponent(tabId)}`)
})
void refreshLocks()
