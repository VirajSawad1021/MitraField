"use client";

import { useState } from "react";
import { ChevronDown, CopyPlus, RefreshCw, Send, Trash2, X, Wrench } from "lucide-react";
import { Badge, Button, Card, Eyebrow, inputCls } from "@/components/ui";
import { api, type Meta, type Project, type Scene } from "@/lib/api";
import { EngineTile } from "@/components/EngineChip";
import { engineStyle } from "@/lib/engines";
import { SCENE_BUSY } from "@/lib/status";

const QUICK = ["Simpler, for a 12 year old", "Show it on a map", "Make it a math animation", "Draw it on the whiteboard", "Use the presenter", "Shorter", "More dramatic"];

export function Inspector({ p, s, meta, setP, close }: { p: Project; s: Scene; meta: Meta; setP: (p: Project) => void; close: () => void }) {
  const [narr, setNarr] = useState(s.narration);
  const [brief, setBrief] = useState(s.brief);
  const [ask, setAsk] = useState("");
  const [adv, setAdv] = useState(false);
  const [params, setParams] = useState(JSON.stringify(s.params, null, 2));
  const [paramErr, setParamErr] = useState(false);
  // follow server-side changes (e.g. the director rewrote this scene)
  const sig = JSON.stringify([s.narration, s.brief, s.params]);
  const [seen, setSeen] = useState(sig);
  if (sig !== seen) {
    setSeen(sig);
    setNarr(s.narration);
    setBrief(s.brief);
    setParams(JSON.stringify(s.params, null, 2));
  }

  const busy = SCENE_BUSY.includes(s.status);
  const qaIssues = (!p.qa?.stale && p.qa?.beats?.[s.id]?.issues) || [];
  const dirty = narr !== s.narration || brief !== s.brief;
  const idx = p.scenes.findIndex((x) => x.id === s.id);
  const st = engineStyle(s.engine);
  const tall = p.aspect === "9:16";

  const save = async () => { if (dirty) setP(await api.editScene(p.id, s.id, { narration: narr, brief })); };
  const render = async () => {
    await save();
    setP(await api.renderScene(p.id, s.id, s.status === "ready" && !dirty ? { force: true, replan: true } : {}));
  };
  const instruct = (text: string) => { if (text.trim()) { api.rewrite(p.id, s.id, text).then(setP); setAsk(""); } };

  return (
    <div className="space-y-3 animate-fade-in">
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-semibold">Scene {idx + 1} of {p.scenes.length}</span>
            {s.duration ? <Badge>{s.duration.toFixed(1)}s</Badge> : null}
          </div>
          <button onClick={close} className="rounded-full p-1 text-muted hover:bg-panel-2 hover:text-ink"><X className="h-4 w-4" /></button>
        </div>
        <div className={`bg-ink ${tall ? "mx-auto aspect-[9/16] max-h-[380px]" : "aspect-video"}`}>
          {s.clip_url ? (
            <video key={s.clip_url} src={s.clip_url} poster={s.thumb_url ?? undefined} controls playsInline className="h-full w-full" />
          ) : (
            <div className={`flex h-full w-full flex-col items-center justify-center gap-2 text-white/85 grain ${st.art}`}>
              <st.icon className="h-7 w-7" />
              <span className="text-[12px]">{busy ? `${s.status}…` : "Not rendered yet"}</span>
            </div>
          )}
        </div>
        {s.error && (
          <p className={`border-t border-line px-4 py-2.5 text-[12px] ${s.status === "error" ? "bg-bad-bg text-bad" : "bg-warn-bg text-warn"}`}>{s.error}</p>
        )}
        {qaIssues.length > 0 && (
          <div className="border-t border-line bg-warn-bg px-4 py-3">
            <p className="text-[12px] font-semibold text-warn">Quality check</p>
            <ul className="mt-1 space-y-1">
              {qaIssues.map((x, k) => (
                <li key={k} className="text-[12px] leading-snug text-warn"><span className="font-semibold">{x.severity === "minor" ? "Minor" : "Major"}:</span> {x.detail}</li>
              ))}
            </ul>
            {p.qa?.flagged?.includes(s.id) && (
              <button onClick={() => api.fixScene(p.id, s.id).then(setP)} disabled={busy}
                className="mt-2.5 inline-flex h-8 items-center gap-1.5 rounded-full bg-ink px-3.5 text-[12px] font-semibold text-white hover:bg-ink-soft disabled:bg-[#b9b6ae]">
                <Wrench className="h-3.5 w-3.5" />Fix this scene
              </button>
            )}
          </div>
        )}
      </Card>

      <Card className="space-y-4 p-4">
        <div>
          <Eyebrow>Narration</Eyebrow>
          <textarea value={narr} onChange={(e) => setNarr(e.target.value)} onBlur={save} rows={3} className={`${inputCls} mt-2 resize-none leading-relaxed`} />
        </div>
        <div>
          <Eyebrow>Visual</Eyebrow>
          <div className="mt-2 grid grid-cols-4 gap-1.5">
            {meta.engines.map((e) => {
              const es = engineStyle(e.name);
              const on = e.name === s.engine;
              return (
                <button key={e.name} title={e.blurb} onClick={() => api.editScene(p.id, s.id, { engine: e.name }).then(setP)}
                  className={`flex flex-col items-center gap-1.5 rounded-xl border px-1 py-2.5 text-[10.5px] font-medium leading-tight transition-all ${on ? "border-ink bg-panel text-ink" : "border-line text-body hover:border-line-strong"}`}>
                  <EngineTile engine={e.name} className="h-7 w-7" solid={on} />
                  {es.short}
                </button>
              );
            })}
          </div>
          <p className="mt-2 text-[12px] leading-relaxed text-body">{meta.engines.find((e) => e.name === s.engine)?.blurb}</p>
        </div>
        {st.kind === "generated" && (p.cast ?? []).some((c) => c.kind !== "style") && (
          <div>
            <Eyebrow>In this scene</Eyebrow>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {p.cast.filter((c) => c.kind !== "style").map((c) => {
                const on = s.cast?.includes(c.id);
                return (
                  <button key={c.id} onClick={() => api.editScene(p.id, s.id, { cast: on ? (s.cast ?? []).filter((x) => x !== c.id) : [...(s.cast ?? []), c.id] }).then(setP)}
                    className={`flex items-center gap-1.5 rounded-full border py-0.5 pl-0.5 pr-2.5 text-[12px] transition-all ${on ? "border-ink bg-panel font-semibold text-ink" : "border-line text-body hover:border-line-strong"}`}>
                    {c.image_url
                      // eslint-disable-next-line @next/next/no-img-element
                      ? <img src={c.image_url} alt="" className="h-6 w-6 rounded-full object-cover" />
                      : <span className="h-6 w-6 rounded-full bg-panel-2" />}
                    {c.name}
                  </button>
                );
              })}
            </div>
            <p className="mt-1.5 text-[11px] text-muted">Selected characters and places are drawn from their reference images.</p>
          </div>
        )}
        <div>
          <Eyebrow>What the viewer sees</Eyebrow>
          <textarea value={brief} onChange={(e) => setBrief(e.target.value)} onBlur={save} rows={3} className={`${inputCls} mt-2 resize-none text-[13px] leading-relaxed`} />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={render} loading={busy}>{!busy && <RefreshCw className="h-4 w-4" />}{s.status === "ready" ? "Regenerate" : "Render scene"}</Button>
          <Button variant="secondary" onClick={() => api.addScene(p.id, s.id).then(setP)}><CopyPlus className="h-4 w-4" />Insert after</Button>
          <Button variant="ghost" className="ml-auto hover:text-bad" onClick={() => confirm("Delete this scene?") && api.delScene(p.id, s.id).then((np) => { setP(np); close(); })}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </Card>

      <Card className="p-4">
        <Eyebrow>Ask the director</Eyebrow>
        <div className="mt-2 flex gap-2">
          <input value={ask} onChange={(e) => setAsk(e.target.value)} onKeyDown={(e) => e.key === "Enter" && instruct(ask)}
            placeholder="e.g. Explain it with a pizza analogy" className={inputCls} disabled={busy} />
          <button onClick={() => instruct(ask)} disabled={!ask.trim() || busy}
            className="flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-full bg-ink text-white disabled:bg-[#c9c6be]"><Send className="h-4 w-4" /></button>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {QUICK.map((q) => (
            <button key={q} disabled={busy} onClick={() => instruct(q)}
              className="rounded-full border border-line px-2.5 py-1 text-[11.5px] text-body transition-colors hover:border-line-strong hover:text-ink disabled:opacity-50">{q}</button>
          ))}
        </div>
        <p className="mt-3 text-[11px] leading-snug text-muted">Only this scene changes. The director keeps it consistent with the scenes around it.</p>
      </Card>

      <Card className="overflow-hidden">
        <button onClick={() => setAdv(!adv)} className="flex w-full items-center justify-between px-4 py-3 text-[13px] font-semibold">
          Advanced: raw parameters <ChevronDown className={`h-4 w-4 text-muted transition-transform ${adv ? "rotate-180" : ""}`} />
        </button>
        {adv && (
          <div className="space-y-2 border-t border-line p-4">
            <textarea value={params} onChange={(e) => { setParams(e.target.value); setParamErr(false); }} rows={12}
              className={`${inputCls} resize-y font-mono text-[11.5px] leading-relaxed ${paramErr ? "border-bad" : ""}`} />
            <Button size="sm" variant="secondary" onClick={async () => {
              try { setP(await api.editScene(p.id, s.id, { params: JSON.parse(params) })); } catch { setParamErr(true); }
            }}>Save parameters</Button>
          </div>
        )}
      </Card>
    </div>
  );
}
