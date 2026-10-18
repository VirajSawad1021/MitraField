"use client";

import { useState } from "react";
import Link from "next/link";
import { FileText, Play, StickyNote, Upload, X } from "lucide-react";
import { Button, Card, Eyebrow, inputCls } from "@/components/ui";
import { api, MAX_INSTRUCTIONS, type Meta, type Project } from "@/lib/api";
import { engineStyle } from "@/lib/engines";
import { LookPicker } from "@/components/LookPicker";
import { CostCard } from "./CostCard";
import { QaCard } from "./QaCard";
import { FactCheckCard } from "./FactCheckCard";

export function Overview({ p, meta, setP, onWatch, select }: { p: Project; meta: Meta; setP: (p: Project) => void; onWatch: () => void; select: (sid: string) => void }) {
  const [note, setNote] = useState("");
  const [dir, setDir] = useState(p.instructions ?? "");
  const [saving, setSaving] = useState(false);
  const dirty = dir.trim() !== (p.instructions ?? "");
  const counts = p.scenes.reduce<Record<string, number>>((a, s) => ({ ...a, [s.engine]: (a[s.engine] || 0) + 1 }), {});
  const exact = p.scenes.filter((s) => engineStyle(s.engine).kind === "exact").length;
  const max = Math.max(1, ...Object.values(counts));

  return (
    <div className="space-y-3 animate-fade-in">
      {p.render_url && (
        <Card className="overflow-hidden">
          <button onClick={onWatch} className="group relative block w-full">
            {p.scenes[0]?.thumb_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={p.scenes[0].thumb_url} alt="" className="aspect-video w-full object-cover" />
            )}
            <span className="absolute inset-0 flex items-center justify-center bg-ink/25 transition-colors group-hover:bg-ink/40">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white text-ink shadow-lg"><Play className="ml-0.5 h-5 w-5" /></span>
            </span>
          </button>
          <div className="flex items-center justify-between px-4 py-3">
            <p className="text-[13px] font-semibold">Finished video</p>
            <a href={p.render_url} download className="text-[12px] font-semibold text-body underline underline-offset-2 hover:text-ink">Download</a>
          </div>
          {p.mark_id && (
            <p className="border-t border-line px-4 py-2.5 text-[11px] leading-snug text-muted">
              Carries an invisible mitrafield mark (<span className="font-mono">{p.mark_id}</span>). <Link href="/verify" className="underline underline-offset-2 hover:text-ink">Verify a video</Link>
            </p>
          )}
        </Card>
      )}

      <QaCard p={p} setP={setP} select={select} />
      <FactCheckCard p={p} setP={setP} select={select} />

      {meta.looks && (
        <Card className="p-4">
          <Eyebrow>Look</Eyebrow>
          <div className="mt-3">
            <LookPicker looks={meta.looks} cols={2} value={p.look ?? "cinematic"}
              onChange={(id) => id !== p.look && confirm("Switch the look? The cast is redrawn in it; re-render the video to apply it to every beat.") && api.patch(p.id, { look: id }).then(setP)} />
          </div>
        </Card>
      )}

      <Card className="p-4">
        <Eyebrow>Routing</Eyebrow>
        {p.scenes.length === 0 ? (
          <p className="mt-2 text-[13px] text-body">The director&apos;s routing appears here once the storyboard is written.</p>
        ) : (
          <>
            <p className="mt-2 text-[13px] text-body"><span className="text-[28px] font-semibold tracking-tight text-ink">{exact}</span> of {p.scenes.length} beats on exact engines</p>
            <div className="mt-3 space-y-2">
              {Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([e, n]) => {
                const s = engineStyle(e);
                return (
                  <div key={e} className="flex items-center gap-2.5 text-[12px]">
                    <s.icon className="h-3.5 w-3.5 shrink-0" style={{ color: s.color }} />
                    <span className="w-28 shrink-0 text-ink">{s.short}</span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-panel-2">
                      <span className="block h-full rounded-full" style={{ width: `${(n / max) * 100}%`, background: s.color }} />
                    </span>
                    <span className="w-4 text-right font-medium tabular-nums">{n}</span>
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-[11px] leading-snug text-muted">Select a beat to edit its line, switch its engine or instruct the director. Only the beats you change re-render.</p>
          </>
        )}
      </Card>

      <CostCard p={p} />

      <Card className="p-4">
        <Eyebrow>Direction</Eyebrow>
        <textarea value={dir} onChange={(e) => setDir(e.target.value)} rows={3} maxLength={MAX_INSTRUCTIONS}
          placeholder="Optional. e.g. Use only manim animations. No generated images or video." className={`${inputCls} mt-2 resize-none text-[13px]`} />
        <div className="mt-2 flex items-center justify-between gap-3">
          <p className="text-[11px] leading-snug text-muted">The director follows this when it writes or rewrites the storyboard. Re-direct to apply it to every beat.</p>
          <Button size="sm" disabled={!dirty} loading={saving}
            onClick={async () => { setSaving(true); try { setP(await api.patch(p.id, { instructions: dir.trim() })); } finally { setSaving(false); } }}>Save</Button>
        </div>
      </Card>

      <Card className="p-4">
        <Eyebrow>Sources</Eyebrow>
        <ul className="mt-2 space-y-1.5">
          {p.sources.map((s) => (
            <li key={s.id} className="flex items-start gap-2 rounded-xl bg-panel px-3 py-2 text-[12px]">
              {s.kind === "file" ? <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" /> : <StickyNote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" />}
              <span className="line-clamp-2 flex-1 text-body">{s.kind === "file" ? s.name : s.text}</span>
              <button onClick={() => api.delSource(p.id, s.id).then(setP)} className="text-muted hover:text-ink"><X className="h-3.5 w-3.5" /></button>
            </li>
          ))}
          {p.sources.length === 0 && <li className="text-[12px] text-muted">No sources. The director works from its own knowledge.</li>}
        </ul>
        <div className="mt-3 flex gap-2">
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a fact or note" className={`${inputCls} py-2 text-[13px]`}
            onKeyDown={async (e) => { if (e.key === "Enter" && note.trim()) { setP(await api.addNote(p.id, note)); setNote(""); } }} />
          <label className="flex h-[38px] w-[38px] shrink-0 cursor-pointer items-center justify-center rounded-full border border-line-strong text-ink hover:border-ink/40" title="Upload a file">
            <Upload className="h-4 w-4" />
            <input type="file" hidden onChange={async (e) => { const f = e.target.files?.[0]; if (f) setP(await api.addFile(p.id, f)); }} />
          </label>
        </div>
        <p className="mt-2 text-[11px] text-muted">New sources apply the next time you re-direct.</p>
      </Card>

      {p.character_url && !(p.cast ?? []).length && (
        <Card className="flex items-center gap-3 p-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={p.character_url} alt="Presenter" className="h-16 w-16 rounded-xl object-cover" />
          <div>
            <p className="text-[13px] font-semibold">Presenter</p>
            <p className="text-[12px] text-body">Same look in every beat it appears in.</p>
          </div>
        </Card>
      )}

      <Card className="p-4">
        <Eyebrow>Models</Eyebrow>
        <ul className="mt-2 space-y-1.5">
          {Object.entries(meta.models).map(([k, v]) => (
            <li key={k} className="flex items-center justify-between text-[12px]"><span className="capitalize text-body">{k}</span><code className="font-mono text-[11px] text-ink">{v}</code></li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
