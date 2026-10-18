"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Download, Film, Languages, Mic, Play, RefreshCw, Sparkles, Wand2 } from "lucide-react";
import { AgentWorking, Badge, Button, ErrorNote, Segmented, Skeleton, fmtTime } from "@/components/ui";
import { api, type Meta, type Project } from "@/lib/api";
import { PROJECT_BUSY, SCENE_BUSY, statusTone } from "@/lib/status";
import { VoiceSelect } from "@/components/VoiceSelect";
import { CastStrip } from "./CastStrip";
import { Inspector } from "./Inspector";
import { Overview } from "./Overview";
import { SceneRow } from "./SceneRow";
import { FinalPlayer } from "./FinalPlayer";

const TRANSLATE = ["Hindi", "Nepali", "Japanese", "Indonesian", "Korean", "Spanish", "Tamil", "Vietnamese", "English"];

export function Studio({ id }: { id: string }) {
  const [p, setP] = useState<Project | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [watch, setWatch] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const refresh = useCallback(() => api.get(id).then(setP).catch((e) => setErr(String(e))), [id]);
  useEffect(() => { refresh(); api.meta().then(setMeta); }, [refresh]);

  const busy = !!p && (PROJECT_BUSY.includes(p.render_status) || p.scenes.some((s) => SCENE_BUSY.includes(s.status))
    || p.qa?.status === "queued" || p.qa?.status === "checking"
    || p.factcheck?.status === "queued" || p.factcheck?.status === "checking"
    || (p.cast ?? []).some((c) => c.status === "generating" || c.status === "pending"));
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, [busy, refresh]);

  const prev = useRef("");
  useEffect(() => {
    if (p && prev.current === "assembling" && p.render_status === "done") setWatch(true);
    if (p) prev.current = p.render_status;
  }, [p]);

  const run = (f: () => Promise<Project>) => f().then(setP).catch((e) => setErr(e instanceof Error ? e.message : String(e)));


  if (!p || !meta) {
    return (
      <main className="mx-auto max-w-[1400px] space-y-4 px-6 py-10">
        <Skeleton className="h-4 w-32" /><Skeleton className="h-9 w-96" />
        <div className="grid gap-4 pt-4 lg:grid-cols-[1fr_400px]"><Skeleton className="h-[520px]" /><Skeleton className="h-[520px]" /></div>
      </main>
    );
  }

  const scene = p.scenes.find((s) => s.id === sel) ?? null;
  const total = p.scenes.reduce((a, s) => a + (s.duration || 0), 0);
  const ready = p.scenes.filter((s) => s.status === "ready").length;
  const working = PROJECT_BUSY.includes(p.render_status);
  const stale = !!p.render_url && (!!p.outdated || p.scenes.some((s) => s.status !== "ready"));
  const [tone, label] = statusTone(p.render_status);

  return (
    <main className="mx-auto max-w-[1400px] px-5 pb-24 pt-8 sm:px-6">
      {/* header */}
      <Link href="/projects" className="text-[12px] font-medium text-muted hover:text-ink">← Projects</Link>
      <Title p={p} onSave={(title) => run(() => api.patch(p.id, { title }))} />
      {p.topic.trim().toLowerCase() !== p.title.trim().toLowerCase() && <p className="mt-1 max-w-2xl truncate text-[13px] text-body">{p.topic}</p>}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge tone={tone}>{label === "Rendering" ? `Rendering ${ready}/${p.scenes.length}` : label}</Badge>
        {p.scenes.length > 0 && <Badge>{p.scenes.length} scenes{total ? ` · ${fmtTime(total)}` : ""}</Badge>}
        {stale && !working && <Badge tone="warn">Changed since the last export</Badge>}
      </div>

      {/* toolbar: settings on the left, the one next step on the right */}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-y border-line py-3">
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex h-10 items-center gap-1.5 rounded-full border border-line-strong bg-white pl-3.5 pr-1 text-[13px]" title="Who narrates this video">
            <Mic className="h-4 w-4 text-body" /><span className="text-muted">Narrator</span>
            <VoiceSelect meta={meta} value={p.voice} onChange={(voice) => run(() => api.patch(p.id, { voice }))}
              className="h-9 max-w-[180px] bg-transparent pr-2 font-semibold focus:outline-none" />
          </label>
          <div className="flex items-center gap-1.5" title="Draft renders video clips with a cheaper model, for trying ideas">
            <span className="text-[12px] text-muted">Quality</span>
            <Segmented size="sm" value={p.quality ?? "final"} onChange={(v) => run(() => api.patch(p.id, { quality: v }))}
              options={[{ value: "draft", label: "Draft" }, { value: "final", label: "Final" }]} />
          </div>
          <TranslateMenu disabled={!p.scenes.length} exclude={p.language} onPick={async (l) => {
            await api.translate(p.id, l);
            setNote(`A ${l} version is being made. It reuses these visuals and appears in Projects when it is done.`);
          }} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {p.render_url && !working && <Button variant="secondary" onClick={() => setWatch(true)}><Play className="h-4 w-4" />Watch</Button>}
          <Primary p={p} working={working} stale={stale} ready={ready} run={run} />
        </div>
      </div>

      {err && <div className="mt-4"><ErrorNote message={err} onRetry={() => { setErr(null); refresh(); }} /></div>}
      {p.render_status === "error" && p.render_error && <div className="mt-4"><ErrorNote message={p.render_error} /></div>}
      {note && (
        <div className="mt-4 flex items-start justify-between gap-3 rounded-xl bg-info-bg px-4 py-3 text-[13px] text-info">
          <span className="flex items-center gap-2"><Languages className="h-4 w-4" />{note}</span>
          <button onClick={() => setNote(null)} className="font-semibold">OK</button>
        </div>
      )}

      {p.scenes.length > 0 && <CastStrip p={p} setP={setP} />}

      <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_400px]">
        <section className="min-w-0">
          {p.render_url && !scene && (
            <button onClick={() => setWatch(true)} className="group relative mb-4 block w-full overflow-hidden rounded-2xl bg-ink lg:hidden">
              {p.scenes[0]?.thumb_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={p.scenes[0].thumb_url} alt="" className="aspect-video w-full object-cover opacity-90" />
              )}
              <span className="absolute inset-0 flex items-center justify-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-ink shadow-lg"><Play className="ml-0.5 h-5 w-5" /></span>
              </span>
              <span className="absolute bottom-3 left-3 rounded-full bg-black/55 px-2.5 py-0.5 text-[11px] font-semibold text-white">Finished video</span>
            </button>
          )}
          {p.render_status === "directing" ? (
            <div className="space-y-3">
              <AgentWorking agent="Director agent" task="Reading your sources, writing the script scene by scene and choosing the right visual for each" />
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[132px]" />)}
            </div>
          ) : p.scenes.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-line-strong bg-panel/50 px-6 py-14 text-center">
              <Sparkles className="mx-auto h-5 w-5 text-body" />
              <p className="mt-3 text-[16px] font-semibold">No storyboard yet</p>
              <p className="mx-auto mt-1 max-w-sm text-[13px] text-body">The director writes one from your topic and sources. Nothing renders until you approve it.</p>
              <Button className="mt-5" onClick={() => run(() => api.storyboard(p.id))}><Wand2 className="h-4 w-4" />Write storyboard</Button>
            </div>
          ) : (
            <Board p={p} sel={sel} setSel={setSel} setP={setP} />
          )}
        </section>

        <aside className="lg:sticky lg:top-20">
          {scene
            ? <Inspector key={scene.id} p={p} s={scene} meta={meta} setP={setP} close={() => setSel(null)} />
            : <Overview p={p} meta={meta} setP={setP} onWatch={() => setWatch(true)} select={setSel} />}
        </aside>
      </div>

      {watch && p.render_url && <FinalPlayer p={p} close={() => setWatch(false)} />}
    </main>
  );
}

function Title({ p, onSave }: { p: Project; onSave: (t: string) => void }) {
  const [t, setT] = useState(p.title);
  const [seen, setSeen] = useState(p.title);
  if (p.title !== seen) { setSeen(p.title); setT(p.title); }   // follow server-side renames
  return (
    <textarea value={t} rows={1} onChange={(e) => setT(e.target.value.replace(/\n/g, ""))} onBlur={() => t.trim() && t !== p.title && onSave(t)}
      onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); (e.target as HTMLTextAreaElement).blur(); } }}
      className="mt-2 block w-full max-w-[760px] resize-none rounded-lg bg-transparent text-[28px] font-semibold leading-tight tracking-tight text-ink outline-none [field-sizing:content] hover:bg-white/60 focus:bg-white sm:text-[30px]" />
  );
}

function TranslateMenu({ onPick, exclude, disabled }: { onPick: (l: string) => void; exclude: string; disabled?: boolean }) {
  return (
    <div className="relative">
      <select disabled={disabled} value="" onChange={(e) => e.target.value && onPick(e.target.value)}
        className="h-10 appearance-none rounded-full border border-line-strong bg-white pl-9 pr-4 text-[13px] font-semibold focus:outline-none disabled:opacity-50">
        <option value="">Translate</option>
        {TRANSLATE.filter((l) => l !== exclude).map((l) => <option key={l}>{l}</option>)}
      </select>
      <Languages className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-ink" />
    </div>
  );
}

function Board({ p, sel, setSel, setP }: {
  p: Project; sel: string | null; setSel: (s: string | null) => void; setP: (p: Project) => void;
}) {
  const [dragId, setDragId] = useState<string | null>(null);
  const drop = (target: string) => {
    if (!dragId || dragId === target) return;
    const ids = p.scenes.map((s) => s.id).filter((i) => i !== dragId);
    ids.splice(ids.indexOf(target), 0, dragId);
    api.reorder(p.id, ids).then(setP);
  };
  return (
    <div className="space-y-3">
      {p.scenes.map((s, i) => (
        <SceneRow key={s.id} s={s} i={i} aspect={p.aspect} on={sel === s.id}
          cast={(p.cast ?? []).filter((c) => c.kind !== "style" && s.cast?.includes(c.id))}
          flagged={!!p.qa?.flagged?.includes(s.id) && !p.qa?.stale}
          factFlag={!!p.factcheck?.flagged?.includes(s.id)}
          onClick={() => setSel(sel === s.id ? null : s.id)}
          onRender={() => api.renderScene(p.id, s.id).then(setP)}
          drag={{ draggable: true, onDragStart: () => setDragId(s.id), onDragOver: (e) => e.preventDefault(), onDrop: () => drop(s.id) }} />
      ))}
      <button onClick={() => api.addScene(p.id).then(setP)}
        className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-line-strong py-4 text-[13px] font-medium text-body hover:bg-panel">
        + Add a scene
      </button>
    </div>
  );
}

const primaryCls = "inline-flex h-10 items-center justify-center gap-2 rounded-full bg-ink px-4.5 text-[13px] font-semibold text-white transition-all hover:bg-ink-soft active:scale-[0.98]";

/** The single next step, which depends on where the project is: write, render, update or download. */
function Primary({ p, working, stale, ready, run }: {
  p: Project; working: boolean; stale: boolean; ready: number; run: (f: () => Promise<Project>) => void;
}) {
  if (working) {
    const what = p.render_status === "directing" ? "Writing storyboard" : p.render_status === "assembling" ? "Finishing video" : `Rendering ${ready}/${p.scenes.length}`;
    return <Button loading>{what}</Button>;
  }
  if (!p.scenes.length) return <Button onClick={() => run(() => api.storyboard(p.id))}><Wand2 className="h-4 w-4" />Write storyboard</Button>;
  if (!p.render_url) return <Button onClick={() => run(() => api.render(p.id))}><Film className="h-4 w-4" />Render video</Button>;
  if (stale) return <Button onClick={() => run(() => api.render(p.id))} title="Re-renders only the scenes that changed, then exports again"><RefreshCw className="h-4 w-4" />Update video</Button>;
  return <a href={p.render_url} download className={primaryCls}><Download className="h-4 w-4" />Download</a>;
}
