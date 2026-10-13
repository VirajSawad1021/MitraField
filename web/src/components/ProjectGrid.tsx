"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Clapperboard } from "lucide-react";
import { Badge, Empty, LinkButton, Skeleton, fmtTime } from "@/components/ui";
import { api, type ProjectRow } from "@/lib/api";
import { engineStyle } from "@/lib/engines";
import { statusTone } from "@/lib/status";

function ago(t: number) {
  const s = Date.now() / 1000 - t;
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

/** Every project as a card that opens it in the studio. */
export function ProjectGrid() {
  const [rows, setRows] = useState<ProjectRow[] | null>(null);
  useEffect(() => { api.list().then(setRows).catch(() => setRows([])); }, []);

  if (rows === null) {
    return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-72" />)}</div>;
  }
  if (rows.length === 0) {
    return (
      <Empty icon={<Clapperboard className="h-5 w-5" />} title="No videos yet" body="Ask a question and the director will storyboard it for you."
        action={<LinkButton href="/new">Start a video</LinkButton>} />
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {rows.map((r) => {
        const [tone, label] = statusTone(r.render_status);
        return (
          <Link key={r.id} href={`/studio?p=${r.id}`} className="group overflow-hidden rounded-3xl border border-line bg-white transition-shadow hover:shadow-[0_18px_50px_-30px_rgba(20,20,19,0.35)]">
            <div className={`relative aspect-video overflow-hidden ${r.cover ? "bg-ink" : "art-charcoal grain"}`}>
              {r.cover && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={r.cover} alt="" className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]" />
              )}
              <span className="absolute left-3 top-3"><Badge tone={tone}>{label}</Badge></span>
              {r.duration > 0 && <span className="absolute bottom-3 right-3 rounded-full bg-black/55 px-2 py-0.5 text-[11px] font-medium text-white">{fmtTime(r.duration)}</span>}
            </div>
            <div className="p-5">
              <p className="line-clamp-1 text-[16px] font-semibold tracking-tight">{r.title}</p>
              <p className="mt-1 text-[12px] text-muted">{r.aspect === "9:16" ? "Short" : "Landscape"} · {r.language || "English"} · {r.scenes} beats · {ago(r.updated)}</p>
              <div className="mt-3 flex gap-1">
                {r.engines.map((e) => {
                  const s = engineStyle(e);
                  return <span key={e} title={s.short} className="flex h-6 w-6 items-center justify-center rounded-lg text-white" style={{ background: s.color }}><s.icon className="h-3 w-3" /></span>;
                })}
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
