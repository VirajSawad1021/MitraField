"use client";

import { Download, FileText, X } from "lucide-react";
import type { Project } from "@/lib/api";

export function FinalPlayer({ p, close }: { p: Project; close: () => void }) {
  const tall = p.aspect === "9:16";
  const srt = p.render_url!.replace(/[^/]+\.mp4$/, "subtitles.srt");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/70 p-4 backdrop-blur-sm animate-fade-in" onClick={close}>
      <div className={`w-full overflow-hidden rounded-3xl bg-white shadow-2xl ${tall ? "max-w-[420px]" : "max-w-[1080px]"}`} onClick={(e) => e.stopPropagation()}>
        <video src={`${p.render_url}?v=${Math.round(p.updated)}`} controls autoPlay playsInline className="max-h-[78vh] w-full bg-black" />
        <div className="flex flex-wrap items-center gap-2 px-5 py-4">
          <p className="mr-auto text-[15px] font-semibold tracking-tight">{p.title}</p>
          <a href={p.render_url!} download className="inline-flex h-9 items-center gap-1.5 rounded-full bg-ink px-4 text-[13px] font-semibold text-white hover:bg-ink-soft"><Download className="h-4 w-4" />MP4</a>
          <a href={srt} download className="inline-flex h-9 items-center gap-1.5 rounded-full border border-line-strong px-4 text-[13px] font-semibold hover:border-ink/40"><FileText className="h-4 w-4" />Subtitles</a>
          <button onClick={close} className="flex h-9 w-9 items-center justify-center rounded-full text-muted hover:bg-panel-2 hover:text-ink"><X className="h-4 w-4" /></button>
        </div>
      </div>
    </div>
  );
}
