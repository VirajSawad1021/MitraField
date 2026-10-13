"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Download, Film, Languages, Play, Sparkles, Wand2 } from "lucide-react";
import { AgentWorking, Badge, Button, ErrorNote, Skeleton, fmtTime } from "@/components/ui";
import { api, type Meta, type Project } from "@/lib/api";
import { engineStyle } from "@/lib/engines";
import { PROJECT_BUSY, SCENE_BUSY, statusTone } from "@/lib/status";
import { voiceGroups, voiceLabel } from "@/lib/voices";
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

  const busy = !!p && (PROJECT_BUSY.includes(p.render_status) || p.scenes.some((s) => SCENE_BUSY.includes(s.status)));
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

  const engines = useMemo(() => Object.fromEntries((meta?.engines ?? []).map((e) => [e.name, e])), [meta]);

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
  const exact = p.scenes.filter((s) => engineStyle(s.engine).kind === "exact").length;
  const working = PROJECT_BUSY.includes(p.render_status);
  const [tone, label] = statusTone(p.render_status);

  return (
    <main className="mx-auto max-w-[1400px] px-5 pb-24 pt-8 sm:px-6">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <Link href="/projects" className="text-[12px] font-medium text-muted hover:text-ink">← Projects</Link>
          <Title p={p} onSave={(title) => run(() => api.patch(p.id, { title }))} />
          <p className="mt-1 max-w-2xl truncate text-[13px] text-body">{p.topic}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 pt-5">
          <Badge tone={tone}>{label === "Rendering" ? `Rendering ${ready}/${p.scenes.length}` : label}</Badge>
          {p.scenes.length > 0 && <Badge>{p.scenes.length} beats{total ? ` · ${fmtTime(total)}` : ""}</Badge>}
          {p.scenes.length > 0 && <Badge tone="good">{exact} exact</Badge>}
          <select value={p.voice} onChange={(e) => run(() => api.patch(p.id, { voice: e.target.value }))}
            className="h-10 rounded-full border border-line-strong bg-white px-3.5 text-[13px] font-medium focus:outline-none" title="Narrator voice">
            {voiceGroups(meta.voices, meta.channel_voices).map((g) => (
              <optgroup key={g.label} label={g.label}>{g.items.map((v) => <option key={v} value={v}>{voiceLabel(v)}</option>)}</optgroup>
            ))}
          </select>
          <TranslateMenu disabled={!p.scenes.length} exclude={p.language} onPick={async (l) => {
            await api.translate(p.id, l);
            setNote(`A ${l} version is being made. It reuses these visuals and appears in Projects when it is done.`);
          }} />
          {p.render_url && !working && <Button variant="secondary" onClick={() => setWatch(true)}><Play className="h-4 w-4" />Watch</Button>}
          {p.scenes.length === 0
            ? <Button onClick={() => run(() => api.storyboard(p.id))} loading={working}><Wand2 className="h-4 w-4" />Direct storyboard</Button>
            : <Button onClick={() => run(() => api.render(p.id))} loading={working}>
                {working ? (p.render_status === "assembling" ? "Assembling" : p.render_status === "directing" ? "Directing" : "Rendering") : <><Film className="h-4 w-4" />{p.render_url ? "Re-render video" : "Render video"}</>}
              </Button>}
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

      {/* routing bar */}
      {p.scenes.length > 0 && <RouteBar p={p} sel={sel} setSel={setSel} />}

      <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_400px]">
        <section className="min-w-0">
          {p.render_status === "directing" ? (
            <div className="space-y-3">
              <AgentWorking agent="Director agent" task="Reading your sources, writing the story beat by beat and choosing an engine for each one" />
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[132px]" />)}
            </div>
          ) : p.scenes.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-line-strong bg-panel/50 px-6 py-14 text-center">
              <Sparkles className="mx-auto h-5 w-5 text-body" />
              <p className="mt-3 text-[16px] font-semibold">No storyboard yet</p>
              <p className="mx-auto mt-1 max-w-sm text-[13px] text-body">Ask the director to write one from your topic and sources.</p>
              <Button className="mt-5" onClick={() => run(() => api.storyboard(p.id))}><Wand2 className="h-4 w-4" />Direct storyboard</Button>
            </div>
          ) : (
            <Board p={p} sel={sel} setSel={setSel} setP={setP} engines={engines} />
          )}
        </section>

        <aside className="lg:sticky lg:top-20">
          {scene
            ? <Inspector key={scene.id} p={p} s={scene} meta={meta} setP={setP} close={() => setSel(null)} />
            : <Overview p={p} meta={meta} setP={setP} onWatch={() => setWatch(true)} />}
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
    <input value={t} onChange={(e) => setT(e.target.value)} onBlur={() => t.trim() && t !== p.title && onSave(t)}
      onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
      className="mt-2 w-full max-w-[640px] rounded-lg bg-transparent text-[28px] font-semibold tracking-tight text-ink outline-none hover:bg-white/60 focus:bg-white sm:text-[30px]" />
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

function RouteBar({ p, sel, setSel }: { p: Project; sel: string | null; setSel: (s: string) => void }) {
  const est = (d?: number | null, n?: string) => d || Math.max(3, (n?.split(/\s+/).length ?? 10) / 2.6);
  const sum = p.scenes.reduce((a, s) => a + est(s.duration, s.narration), 0);
  return (
    <div className="mt-6">
      <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full">
        {p.scenes.map((s, i) => (
          <button key={s.id} title={`b${i + 1} · ${engineStyle(s.engine).short}`} onClick={() => setSel(s.id)}
            className={`min-w-[6px] transition-opacity ${sel && sel !== s.id ? "opacity-35" : "opacity-100"}`}
            style={{ flexGrow: est(s.duration, s.narration) / sum, background: engineStyle(s.engine).color }} />
        ))}
      </div>
    </div>
  );
}

function Board({ p, sel, setSel, setP, engines }: {
  p: Project; sel: string | null; setSel: (s: string | null) => void; setP: (p: Project) => void; engines: Record<string, { label: string }>;
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
        <SceneRow key={s.id} s={s} i={i} aspect={p.aspect} on={sel === s.id} label={engines[s.engine]?.label}
          onClick={() => setSel(sel === s.id ? null : s.id)}
          onRender={() => api.renderScene(p.id, s.id).then(setP)}
          drag={{ draggable: true, onDragStart: () => setDragId(s.id), onDragOver: (e) => e.preventDefault(), onDrop: () => drop(s.id) }} />
      ))}
      <button onClick={() => api.addScene(p.id).then(setP)}
        className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-line-strong py-4 text-[13px] font-medium text-body hover:bg-panel">
        + Add a beat
      </button>
      {p.render_url && (
        <a href={p.render_url} download className="flex items-center justify-center gap-2 py-2 text-[12px] font-medium text-muted hover:text-ink">
          <Download className="h-3.5 w-3.5" /> Download the last render
        </a>
      )}
    </div>
  );
}
