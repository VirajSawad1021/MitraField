"use client";

import { useState } from "react";
import { BadgeCheck, ChevronDown, Loader2, RefreshCw, SearchCheck, Wand2 } from "lucide-react";
import { Card, Eyebrow } from "@/components/ui";
import { api, type Project } from "@/lib/api";

const TONE: Record<string, string> = {
  supported: "bg-good-bg text-good", contradicted: "bg-bad-bg text-bad", unsupported: "bg-warn-bg text-warn", unverifiable: "bg-panel-2 text-body",
};

/** Claims in the storyboard checked against the person's sources and Google Search. */
export function FactCheckCard({ p, setP, select }: { p: Project; setP: (p: Project) => void; select: (sid: string) => void }) {
  const [open, setOpen] = useState(false);
  const fc = p.factcheck;
  if (!p.scenes.length) return null;
  const busy = fc?.status === "queued" || fc?.status === "checking";
  const claims = fc?.claims ?? [];
  const bad = claims.map((c, i) => ({ c, i })).filter(({ c }) => c.verdict === "contradicted" || c.verdict === "unsupported");
  const good = claims.filter((c) => c.verdict === "supported");

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <Eyebrow>Fact check</Eyebrow>
        {!busy && fc && (
          <button onClick={() => api.runFactcheck(p.id).then(setP)} title="Check again"
            className="rounded-full p-1 text-muted hover:bg-panel-2 hover:text-ink"><RefreshCw className="h-3.5 w-3.5" /></button>
        )}
      </div>
      {!fc ? (
        <div className="mt-2">
          <p className="text-[12px] text-body">Checks every number and claim against your sources and Google Search.</p>
          <button onClick={() => api.runFactcheck(p.id).then(setP)}
            className="mt-2.5 inline-flex h-8 items-center gap-1.5 rounded-full bg-ink px-3.5 text-[12px] font-semibold text-white hover:bg-ink-soft">
            <SearchCheck className="h-3.5 w-3.5" />Check the facts
          </button>
        </div>
      ) : busy ? (
        <p className="mt-3 flex items-center gap-2 text-[13px] text-body"><Loader2 className="h-4 w-4 animate-spin" />Checking claims with Google Search…</p>
      ) : fc.status === "error" ? (
        <p className="mt-3 text-[13px] text-bad">{fc.summary}</p>
      ) : (
        <>
          <div className="mt-3 flex items-start gap-2.5">
            {bad.length ? <SearchCheck className="mt-0.5 h-5 w-5 shrink-0 text-warn" /> : <BadgeCheck className="mt-0.5 h-5 w-5 shrink-0 text-good" />}
            <div>
              <p className="text-[14px] font-semibold">{bad.length ? "Claims to review" : "Facts check out"}</p>
              <p className="text-[12px] text-body">{fc.summary}</p>
            </div>
          </div>
          {bad.length > 0 && (
            <ul className="mt-3 space-y-2">
              {bad.map(({ c, i }) => (
                <li key={i} className="rounded-xl border border-line p-3">
                  <div className="flex items-center gap-2">
                    <button onClick={() => c.sid && select(c.sid)} className="font-mono text-[11px] font-semibold text-muted hover:text-ink">b{c.beat}</button>
                    <span className={`rounded-full px-2 py-px text-[10.5px] font-semibold ${TONE[c.verdict]}`}>{c.verdict}</span>
                  </div>
                  <p className="mt-1.5 text-[12.5px] leading-snug text-ink">&ldquo;{c.claim}&rdquo;</p>
                  <p className="mt-1 text-[12px] leading-snug text-body">{c.evidence}{c.source ? ` (${c.source})` : ""}</p>
                  {c.correction && <p className="mt-1 text-[12px] leading-snug text-good">Suggested: {c.correction}</p>}
                  <button disabled={c.applied} onClick={() => api.applyCorrection(p.id, i).then(setP)}
                    className="mt-2 inline-flex h-7 items-center gap-1.5 rounded-full bg-ink px-3 text-[11.5px] font-semibold text-white hover:bg-ink-soft disabled:bg-[#b9b6ae]">
                    <Wand2 className="h-3 w-3" />{c.applied ? "Correction applied" : "Apply correction"}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {(good.length > 0 || (fc.web ?? []).length > 0) && (
            <>
              <button onClick={() => setOpen(!open)} className="mt-3 flex items-center gap-1 text-[12px] font-medium text-muted hover:text-ink">
                <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} />{good.length} supported claims · {(fc.web ?? []).length} web sources
              </button>
              {open && (
                <div className="mt-2 space-y-1.5">
                  {good.map((c, k) => <p key={k} className="text-[11.5px] leading-snug text-body"><span className="font-mono text-muted">b{c.beat}</span> {c.claim}</p>)}
                  {(fc.web ?? []).map((w, k) => (
                    <a key={k} href={w.uri} target="_blank" rel="noreferrer" className="block truncate text-[11.5px] text-info underline underline-offset-2">{w.title}</a>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}
    </Card>
  );
}
