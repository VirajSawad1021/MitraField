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
export type Project = {
  pace?: number
  id: string; title: string; topic: string; audience: string; language: string; aspect: '16:9' | '9:16'
  length: 'short' | 'medium' | 'long'; voice: string; music: boolean
  sources: Source[]; scenes: Scene[]; cast: CastItem[]; render_status: string; render_url?: string | null; render_error?: string | null
  character_url?: string | null; updated: number
}
export type EngineInfo = { name: string; label: string; blurb: string; precise: boolean }
export type Meta = { engines: EngineInfo[]; voices: string[]; channel_voices: string[]; default_voice: string; models: Record<string, string> }
export type ProjectRow = { id: string; title: string; topic: string; aspect: string; language: string; updated: number; render_status: string; scenes: number; cover: string | null; duration: number; engines: string[] }

async function j<T>(r: Promise<Response>): Promise<T> {
  const res = await r
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
const H = { 'Content-Type': 'application/json' }
const send = (m: string, u: string, b?: unknown) => j<Project>(fetch(u, { method: m, headers: H, body: b ? JSON.stringify(b) : undefined }))

export const api = {
  meta: () => j<Meta>(fetch('/api/meta')),
  list: () => j<ProjectRow[]>(fetch('/api/projects')),
  get: (id: string) => j<Project>(fetch(`/api/projects/${id}`)),
  create: (b: Partial<Project> & { notes?: string }) => send('POST', '/api/projects', b),
  patch: (id: string, b: Partial<Project>) => send('PATCH', `/api/projects/${id}`, b),
  remove: (id: string) => fetch(`/api/projects/${id}`, { method: 'DELETE' }),
  storyboard: (id: string) => send('POST', `/api/projects/${id}/storyboard`),
  render: (id: string) => send('POST', `/api/projects/${id}/render`),
  assemble: (id: string) => send('POST', `/api/projects/${id}/assemble`),
  translate: (id: string, language: string) => fetch(`/api/projects/${id}/translate`, { method: 'POST', headers: H, body: JSON.stringify({ language }) }),
  addNote: (id: string, text: string, name = 'Note') => send('POST', `/api/projects/${id}/sources?text=${encodeURIComponent(text)}&name=${encodeURIComponent(name)}`),
  addFile: (id: string, f: File) => { const fd = new FormData(); fd.append('file', f); return j<Project>(fetch(`/api/projects/${id}/sources`, { method: 'POST', body: fd })) },
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
