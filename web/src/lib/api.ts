export type CastItem = {
  id: string; kind: 'character' | 'location' | 'object' | 'style'; name: string; description: string
  status: 'pending' | 'generating' | 'ready' | 'error'; error?: string | null; image_url?: string | null
}
export type Scene = {
  cast?: string[]
  id: string; narration: string; engine: string; brief: string; params: Record<string, unknown>
  status: 'draft' | 'queued' | 'rendering' | 'ready' | 'error'; duration?: number | null; error?: string | null
  clip_url?: string | null; thumb_url?: string | null; audio_url?: string | null
}
export type Source = { id: string; kind: 'note' | 'file' | 'link'; name: string; text: string }
export type Cost = { total: number; by_kind: Record<string, number>; calls: number }
export type CostLine = { kind: string; model: string; calls: number; usd: number }
export type Project = {
  cost?: Cost; quality?: 'draft' | 'final'; look?: string
  pace?: number
  id: string; title: string; topic: string; audience: string; language: string; aspect: '16:9' | '9:16'
  length: 'short' | 'medium' | 'long'; voice: string; music: boolean
  sources: Source[]; scenes: Scene[]; cast: CastItem[]; render_status: string; render_url?: string | null; render_error?: string | null
  character_url?: string | null; updated: number
}
export type EngineInfo = { name: string; label: string; blurb: string; precise: boolean }
export type LookInfo = { id: string; label: string; blurb: string }
export type VoiceProfile = { id: string; name: string; language: string; status: 'pending' | 'ready' | 'error'; error?: string | null; builtin: boolean }
export type Meta = { locked?: boolean; looks?: LookInfo[]; engines: EngineInfo[]; voices: string[]; voice_profiles: Omit<VoiceProfile, 'language' | 'error'>[]; cloning: boolean; default_voice: string; models: Record<string, string> }
export type ProjectRow = { id: string; title: string; topic: string; aspect: string; language: string; updated: number; render_status: string; scenes: number; cover: string | null; duration: number; engines: string[] }

/* Public deployments ask for a passcode before anything that spends credits. */
const PASS_KEY = 'mitrafield-pass'
function pass(): string {
  try { return localStorage.getItem(PASS_KEY) || '' } catch { return '' }
}
function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const p = pass()
  return p ? { ...extra, 'X-Studio-Pass': p } : extra
}

async function j<T>(r: Promise<Response>, retry?: () => Promise<Response>): Promise<T> {
  let res = await r
  if (res.status === 401 && retry) {
    const p = typeof window !== 'undefined' ? window.prompt('This demo is view-only without the passcode. Enter it to create or edit videos:') : null
    if (p) {
      try { localStorage.setItem(PASS_KEY, p.trim()) } catch {}
      res = await retry()
    }
  }
  if (!res.ok) throw new Error(res.status === 401 ? 'Passcode required to create or edit videos.' : await res.text())
  return res.json()
}
const send = (m: string, u: string, b?: unknown) => {
  const go = () => fetch(u, { method: m, headers: authHeaders({ 'Content-Type': 'application/json' }), body: b ? JSON.stringify(b) : undefined })
  return j<Project>(go(), go)
}

const form = <T>(m: string, u: string, fd?: () => FormData) => {
  const go = () => fetch(u, { method: m, headers: authHeaders(), body: fd?.() })
  return j<T>(go(), go)
}

export const api = {
  voices: () => j<VoiceProfile[]>(fetch('/api/voices')),
  createVoice: (fd: () => FormData) => form<VoiceProfile>('POST', '/api/voices', fd),
  deleteVoice: (id: string) => form<{ ok: boolean }>('DELETE', `/api/voices/${id}`),
  meta: () => j<Meta>(fetch('/api/meta')),
  list: () => j<ProjectRow[]>(fetch('/api/projects')),
  get: (id: string) => j<Project>(fetch(`/api/projects/${id}`)),
  costs: (id: string) => j<Cost & { lines: CostLine[] }>(fetch(`/api/projects/${id}/costs`)),
  create: (b: Partial<Project> & { notes?: string }) => send('POST', '/api/projects', b),
  patch: (id: string, b: Partial<Project>) => send('PATCH', `/api/projects/${id}`, b),
  remove: (id: string) => fetch(`/api/projects/${id}`, { method: 'DELETE', headers: authHeaders() }),
  storyboard: (id: string) => send('POST', `/api/projects/${id}/storyboard`),
  render: (id: string) => send('POST', `/api/projects/${id}/render`),
  assemble: (id: string) => send('POST', `/api/projects/${id}/assemble`),
  translate: (id: string, language: string) => {
    const go = () => fetch(`/api/projects/${id}/translate`, { method: 'POST', headers: authHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify({ language }) })
    return j<{ ok: boolean }>(go(), go)
  },
  addNote: (id: string, text: string, name = 'Note') => send('POST', `/api/projects/${id}/sources?text=${encodeURIComponent(text)}&name=${encodeURIComponent(name)}`),
  addFile: (id: string, f: File) => {
    const go = () => { const fd = new FormData(); fd.append('file', f); return fetch(`/api/projects/${id}/sources`, { method: 'POST', headers: authHeaders(), body: fd }) }
    return j<Project>(go(), go)
  },
  delSource: (id: string, sid: string) => send('DELETE', `/api/projects/${id}/sources/${sid}`),
  editScene: (id: string, sid: string, b: Partial<Scene>) => send('PATCH', `/api/projects/${id}/scenes/${sid}`, b),
  addScene: (id: string, after?: string) => send('POST', `/api/projects/${id}/scenes`, { after }),
  delScene: (id: string, sid: string) => send('DELETE', `/api/projects/${id}/scenes/${sid}`),
  reorder: (id: string, ids: string[]) => send('POST', `/api/projects/${id}/order`, { ids }),
  renderScene: (id: string, sid: string, opts: { force?: boolean; replan?: boolean } = {}) => send('POST', `/api/projects/${id}/scenes/${sid}/render`, opts),
  addCast: (id: string, b: Partial<CastItem>) => send('POST', `/api/projects/${id}/cast`, b),
  editCast: (id: string, cid: string, b: Partial<CastItem>) => send('PATCH', `/api/projects/${id}/cast/${cid}`, b),
  regenCast: (id: string, cid: string) => send('POST', `/api/projects/${id}/cast/${cid}/generate`),
  delCast: (id: string, cid: string) => send('DELETE', `/api/projects/${id}/cast/${cid}`),
  rewrite: (id: string, sid: string, instruction: string) => send('POST', `/api/projects/${id}/scenes/${sid}/rewrite`, { instruction }),
}
