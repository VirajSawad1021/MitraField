"use client";

import { useEffect, useState } from "react";
import { Card, Eyebrow } from "@/components/ui";
import { api, type Cost, type CostLine, type Project } from "@/lib/api";

const LABEL: Record<string, string> = { text: "Script and direction", image: "Images", video: "Video clips", voice: "Narration", music: "Music" }
const usd = (v: number) => (v > 0 && v < 0.01 ? "<$0.01" : `$${v.toFixed(2)}`)

/** What this video cost, line by line. The ledger is fetched when the total changes, not with every poll. */
export function CostCard({ p }: { p: Project }) {
  const [c, setC] = useState<(Cost & { lines: CostLine[] }) | null>(null)
  const total = p.cost?.total ?? 0
  useEffect(() => { if (total) api.costs(p.id).then(setC).catch(() => {}) }, [p.id, total])
  if (!total) return null
  const seconds = p.scenes.reduce((a, s) => a + (s.duration ?? 0), 0)

  return (
    <Card className="p-4">
      <Eyebrow>Cost of this video</Eyebrow>
      <p className="mt-2 text-[13px] text-body">
        <span className="text-[28px] font-semibold tracking-tight text-ink">${total.toFixed(2)}</span> across {p.cost!.calls} calls
        {seconds > 0 && <> · about ${((total / seconds) * 60).toFixed(2)} per minute of video</>}
      </p>
      <ul className="mt-3 divide-y divide-line">
        {(c?.lines ?? []).map((l) => (
          <li key={`${l.kind}/${l.model}`} className="flex items-baseline gap-2 py-1.5 text-[12px]">
            <span className="min-w-0 flex-1">
              <span className="block text-ink">{LABEL[l.kind] ?? l.kind}</span>
              <code className="block truncate font-mono text-[10.5px] text-muted">{l.model || "-"}</code>
            </span>
            <span className="shrink-0 text-muted tabular-nums">{l.calls} {l.calls === 1 ? "call" : "calls"}</span>
            <span className="w-14 shrink-0 text-right font-medium tabular-nums text-ink">{usd(l.usd)}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11px] leading-snug text-muted">Estimated from Google&apos;s published rates, plus the GPU seconds each cloned-voice line used. Draft mode renders Veo shots with Veo Lite at half the price.</p>
    </Card>
  )
}
