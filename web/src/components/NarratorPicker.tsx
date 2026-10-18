"use client";

import Link from "next/link";
import { Check, Mic, Plus } from "lucide-react";
import type { Meta } from "@/lib/api";

/** Narrator choice with cloned voices up front: the channel's, the person's own, and a way to make one. Gemini voices
 *  stay one select away, since they cover more languages. */
export function NarratorPicker({ meta, value, onChange }: { meta: Meta | null; value: string; onChange: (v: string) => void }) {
  const cloned = (meta?.voice_profiles ?? []).filter((p) => p.status === "ready");
  const gemini = meta?.voices ?? [];
  const isGemini = gemini.includes(value);
  return (
    <div>
      <div className="grid gap-2 sm:grid-cols-3">
        {cloned.map((v) => {
          const on = v.id === value;
          return (
            <button key={v.id} type="button" onClick={() => onChange(v.id)}
              className={`flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left transition-all ${on ? "border-ink bg-white shadow-[0_0_0_1px_#141413]" : "border-line bg-white hover:border-line-strong"}`}>
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${on ? "bg-ink text-white" : "bg-panel-2 text-body"}`}>
                {on ? <Check className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-semibold">{v.name}</span>
                <span className="block text-[11px] text-muted">{v.builtin ? "Cloned voice" : "Your cloned voice"}</span>
              </span>
            </button>
          );
        })}
        {meta?.cloning && (
          <Link href="/voices" target="_blank"
            className="flex items-center gap-2.5 rounded-xl border border-dashed border-line-strong px-3 py-2.5 text-left transition-colors hover:border-ink/40 hover:bg-white">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#efe7f6] text-[#6b4f8a]"><Plus className="h-4 w-4" /></span>
            <span className="min-w-0">
              <span className="block text-[13px] font-semibold">Clone your voice</span>
              <span className="block text-[11px] text-muted">15 seconds of speech</span>
            </span>
          </Link>
        )}
      </div>
      {gemini.length > 0 && (
        <label className={`mt-2 flex items-center gap-2 rounded-xl border px-3 py-1.5 text-[13px] ${isGemini ? "border-ink bg-white" : "border-line bg-white/60"}`}>
          <span className="shrink-0 text-muted">Gemini voice</span>
          <select value={isGemini ? value : ""} onChange={(e) => e.target.value && onChange(e.target.value)}
            className="h-8 min-w-0 flex-1 bg-transparent font-semibold focus:outline-none">
            <option value="">{isGemini ? value : "Choose…"}</option>
            {gemini.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </label>
      )}
    </div>
  );
}
