"use client";

import { useRef } from "react";
import { AlertTriangle, GripVertical, Loader2, Play } from "lucide-react";
import { Badge } from "@/components/ui";
import type { Scene } from "@/lib/api";
import { engineStyle } from "@/lib/engines";
import { SCENE_BUSY } from "@/lib/status";

export function SceneRow({ s, i, aspect, on, label, onClick, onRender, drag }: {
  s: Scene; i: number; aspect: string; on: boolean; label?: string;
  onClick: () => void; onRender: () => void; drag: React.HTMLAttributes<HTMLDivElement> & { draggable: boolean };
}) {
  const v = useRef<HTMLVideoElement>(null);
  const st = engineStyle(s.engine);
  const busy = SCENE_BUSY.includes(s.status);
  const tall = aspect === "9:16";

  return (
    <div {...drag} onClick={onClick}
      onMouseEnter={() => v.current?.play().catch(() => {})}
      onMouseLeave={() => v.current?.load()}  // load() resets to the poster frame
      className={`group flex cursor-pointer gap-4 rounded-2xl border bg-white p-3 transition-all ${on ? "border-ink shadow-[0_0_0_1px_#141413]" : "border-line hover:border-line-strong"}`}>
      <div className={`relative shrink-0 overflow-hidden rounded-xl bg-ink ${tall ? "h-[132px] w-[74px]" : "aspect-video w-[200px] sm:w-[220px]"}`}>
        {s.clip_url ? (
          <video ref={v} src={s.clip_url} poster={s.thumb_url ?? undefined} muted loop playsInline preload="none" className="h-full w-full object-cover" />
        ) : (
          <div className={`flex h-full w-full items-center justify-center grain ${st.art}`}>
            {busy ? <Loader2 className="h-5 w-5 animate-spin text-white/90" /> : <st.icon className="h-6 w-6 text-white/80" />}
          </div>
        )}
        {busy && s.clip_url && <div className="absolute inset-0 flex items-center justify-center bg-black/50"><Loader2 className="h-5 w-5 animate-spin text-white" /></div>}
        {s.clip_url && !busy && <Play className="absolute bottom-2 left-2 h-4 w-4 text-white opacity-0 drop-shadow transition-opacity group-hover:opacity-100" />}
        {s.duration ? <span className="absolute bottom-1.5 right-1.5 rounded-full bg-black/55 px-1.5 py-px text-[10px] font-medium text-white">{s.duration.toFixed(1)}s</span> : null}
      </div>

      <div className="min-w-0 flex-1 py-0.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] text-muted">b{i + 1}</span>
          <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold text-white" style={{ background: st.color }}>
            <st.icon className="h-3 w-3" />{label ?? st.short}
          </span>
          {st.kind === "exact" ? <Badge tone="good">exact</Badge> : <Badge>generated</Badge>}
          {s.status === "error" && <Badge tone="bad"><AlertTriangle className="h-3 w-3" />error</Badge>}
          {s.error && s.status === "ready" && <Badge tone="warn" title={s.error}>fallback used</Badge>}
          {busy && <Badge tone="warn">{s.status}</Badge>}
          <GripVertical className="ml-auto h-4 w-4 text-line-strong opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
        <p className="mt-2 line-clamp-2 text-[14px] leading-snug text-ink">{s.narration}</p>
        <p className="mt-1 line-clamp-1 text-[12px] text-muted">{s.brief}</p>
        {s.status === "draft" && s.clip_url === null && (
          <button onClick={(e) => { e.stopPropagation(); onRender(); }} className="mt-2 text-[12px] font-semibold text-ink underline underline-offset-2">Render this beat</button>
        )}
      </div>
    </div>
  );
}
