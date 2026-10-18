"use client";

import { useState } from "react";
import Link from "next/link";
import { FileText, Play, ShieldCheck, StickyNote, Upload, X } from "lucide-react";
import { Button, Card, Eyebrow, inputCls } from "@/components/ui";
import { api, MAX_INSTRUCTIONS, type Meta, type Project } from "@/lib/api";
import { LookPicker } from "@/components/LookPicker";
import { CostCard } from "./CostCard";
import { QaCard } from "./QaCard";
import { FactCheckCard } from "./FactCheckCard";

/** The sidebar when no scene is selected: the result first, then the checks on it, then the inputs. */
export function Overview({ p, meta, setP, onWatch, select }: { p: Project; meta: Meta; setP: (p: Project) => void; onWatch: () => void; select: (sid: string) => void }) {
  const [note, setNote] = useState("");
  const [dir, setDir] = useState(p.instructions ?? "");
  const [saving, setSaving] = useState(false);
  const [lookOpen, setLookOpen] = useState(false);
  const dirty = dir.trim() !== (p.instructions ?? "");
  const look = meta.looks?.find((l) => l.id === (p.look ?? "cinematic"));

  return (
    <div className="space-y-3 animate-fade-in">
      {p.render_url && (
        <Card className="hidden overflow-hidden lg:block">
          <button onClick={onWatch} className="group relative block w-full" aria-label="Watch the finished video">
            {p.scenes[0]?.thumb_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={p.scenes[0].thumb_url} alt="" className="aspect-video w-full object-cover" />
            )}
            <span className="absolute inset-0 flex items-center justify-center bg-ink/25 transition-colors group-hover:bg-ink/40">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white text-ink shadow-lg"><Play className="ml-0.5 h-5 w-5" /></span>
            </span>
          </button>
          {p.mark_id && (
            <p className="flex items-start gap-2 px-4 py-3 text-[11.5px] leading-snug text-muted">
              <ShieldCheck className="mt-px h-3.5 w-3.5 shrink-0 text-good" />
              <span>Carries an invisible mitrafield watermark. Anyone can <Link href="/verify" className="underline underline-offset-2 hover:text-ink">verify a copy</Link>.</span>
            </p>
          )}
        </Card>
      )}

      <QaCard p={p} setP={setP} select={select} />
      <FactCheckCard p={p} setP={setP} select={select} />
      <CostCard p={p} />

      <Card className="p-4">
        <Eyebrow>Instructions for the director</Eyebrow>
        <textarea value={dir} onChange={(e) => setDir(e.target.value)} rows={3} maxLength={MAX_INSTRUCTIONS}
          placeholder="Optional. e.g. Only math animations, no AI images or video." className={`${inputCls} mt-2 resize-none text-[13px]`} />
        <div className="mt-2 flex items-center justify-between gap-3">
          <p className="text-[11px] leading-snug text-muted">Followed whenever the storyboard is written or a scene is rewritten.</p>
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
              <button onClick={() => api.delSource(p.id, s.id).then(setP)} className="text-muted hover:text-ink" aria-label="Remove source"><X className="h-3.5 w-3.5" /></button>
            </li>
          ))}
          {p.sources.length === 0 && <li className="text-[12px] text-muted">None. The director works from its own knowledge.</li>}
        </ul>
        <div className="mt-3 flex gap-2">
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a fact or note" className={`${inputCls} py-2 text-[13px]`}
            onKeyDown={async (e) => { if (e.key === "Enter" && note.trim()) { setP(await api.addNote(p.id, note)); setNote(""); } }} />
          <label className="flex h-[38px] w-[38px] shrink-0 cursor-pointer items-center justify-center rounded-full border border-line-strong text-ink hover:border-ink/40" title="Upload a file">
            <Upload className="h-4 w-4" />
            <input type="file" hidden onChange={async (e) => { const f = e.target.files?.[0]; if (f) setP(await api.addFile(p.id, f)); }} />
          </label>
        </div>
        <p className="mt-2 text-[11px] text-muted">New sources are used the next time the storyboard is written.</p>
      </Card>

      {meta.looks && (
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              {look && <img src={`/looks/${look.id}.jpg`} alt="" className="h-10 w-16 shrink-0 rounded-lg object-cover" />}
              <div className="min-w-0">
                <Eyebrow>Look</Eyebrow>
                <p className="truncate text-[13px] font-semibold">{look?.label ?? p.look}</p>
              </div>
            </div>
            <Button size="sm" variant="secondary" onClick={() => setLookOpen(!lookOpen)}>{lookOpen ? "Close" : "Change"}</Button>
          </div>
          {lookOpen && (
            <div className="mt-3">
              <LookPicker looks={meta.looks} cols={2} value={p.look ?? "cinematic"}
                onChange={(id) => id !== p.look && confirm("Switch the look? Characters and places are redrawn in it; update the video to apply it to every scene.")
                  && api.patch(p.id, { look: id }).then((np) => { setP(np); setLookOpen(false); })} />
            </div>
          )}
        </Card>
      )}

      {p.character_url && !(p.cast ?? []).length && (
        <Card className="flex items-center gap-3 p-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={p.character_url} alt="Presenter" className="h-16 w-16 rounded-xl object-cover" />
          <div>
            <p className="text-[13px] font-semibold">Presenter</p>
            <p className="text-[12px] text-body">Looks the same in every scene they appear in.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
