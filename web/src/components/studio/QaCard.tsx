"use client";

import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import { Badge, Card, Eyebrow } from "@/components/ui";
import { api, type Project } from "@/lib/api";

/** The automatic quality check of the last render: technical checks, flagged beats, contact sheet. */
export function QaCard({ p, setP, select }: { p: Project; setP: (p: Project) => void; select: (sid: string) => void }) {
  const qa = p.qa;
  if (!p.render_url) return null;
  const busy = qa?.status === "queued" || qa?.status === "checking";
  const idx = (sid: string) => p.scenes.findIndex((s) => s.id === sid);

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <Eyebrow>Quality check</Eyebrow>
        {!busy && qa && (
          <button onClick={() => api.runQa(p.id).then(setP)} title="Check again"
            className="rounded-full p-1 text-muted hover:bg-panel-2 hover:text-ink"><RefreshCw className="h-3.5 w-3.5" /></button>
        )}
      </div>

      {!qa ? (
        <div className="mt-2">
          <p className="text-[12px] text-body">Not checked yet. Gemini reviews every beat, and ffmpeg checks the picture and sound.</p>
          <button onClick={() => api.runQa(p.id).then(setP)}
            className="mt-2.5 inline-flex h-8 items-center gap-1.5 rounded-full bg-ink px-3.5 text-[12px] font-semibold text-white hover:bg-ink-soft">
            <ShieldCheck className="h-3.5 w-3.5" />Check this video
          </button>
        </div>
      ) : busy ? (
        <p className="mt-3 flex items-center gap-2 text-[13px] text-body"><Loader2 className="h-4 w-4 animate-spin" />Gemini is reviewing every beat…</p>
      ) : qa.status === "error" ? (
        <p className="mt-3 text-[13px] text-bad">{qa.summary}</p>
      ) : (
        <>
          <div className="mt-3 flex items-start gap-2.5">
            {qa.status === "passed"
              ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-good" />
              : <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warn" />}
            <div>
              <p className="text-[14px] font-semibold">{qa.status === "passed" ? "Passed" : "Needs a look"}</p>
              <p className="text-[12px] text-body">{qa.summary}</p>
            </div>
            {qa.stale && <Badge tone="warn" className="ml-auto">older render</Badge>}
          </div>

          {(qa.flagged ?? []).length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {qa.flagged!.map((sid) => {
                const issue = qa.beats?.[sid]?.issues.find((x) => x.severity !== "minor");
                return (
                  <li key={sid}>
                    <button onClick={() => select(sid)} className="flex w-full items-start gap-2 rounded-xl bg-warn-bg px-3 py-2 text-left text-[12px] text-warn hover:brightness-[0.98]">
                      <span className="font-mono font-semibold">b{idx(sid) + 1}</span>
                      <span className="line-clamp-2 flex-1">{issue?.detail ?? "Flagged"}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          <ul className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1">
            {(qa.technical ?? []).map((c) => (
              <li key={c.check} title={c.detail} className="flex items-center gap-1.5 text-[11.5px] text-body">
                <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${c.ok ? "bg-good" : "bg-bad"}`} />
                <span className="capitalize">{c.check}</span>
              </li>
            ))}
          </ul>

          {qa.sheet_url && (
            <a href={qa.sheet_url} target="_blank" rel="noreferrer" className="mt-3 block overflow-hidden rounded-xl border border-line">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={qa.sheet_url} alt="Contact sheet of the finished video" className="w-full" />
            </a>
          )}
          <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted"><ShieldCheck className="h-3.5 w-3.5" />Every render is checked automatically before you see it.</p>
        </>
      )}
    </Card>
  );
}
