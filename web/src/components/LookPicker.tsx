"use client";

import { Check } from "lucide-react";
import type { LookInfo } from "@/lib/api";

/** Grid of art-direction presets with a sample frame of the same subject in each look. */
export function LookPicker({ looks, value, onChange, cols = 3 }: { looks: LookInfo[]; value: string; onChange: (id: string) => void; cols?: 2 | 3 }) {
  return (
    <div className={`grid gap-2.5 ${cols === 3 ? "grid-cols-2 sm:grid-cols-3" : "grid-cols-2"}`}>
      {looks.map((l) => {
        const on = l.id === value;
        return (
          <button key={l.id} type="button" onClick={() => onChange(l.id)} title={l.blurb}
            className={`group overflow-hidden rounded-xl border text-left transition-all ${on ? "border-ink shadow-[0_0_0_1px_#141413]" : "border-line hover:border-line-strong"}`}>
            <span className="relative block aspect-video overflow-hidden bg-panel-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`/looks/${l.id}.jpg`} alt={l.label} className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]" />
              {on && <span className="absolute right-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-ink text-white"><Check className="h-3 w-3" /></span>}
            </span>
            <span className="block px-2.5 py-2">
              <span className="block text-[12.5px] font-semibold">{l.label}</span>
              <span className="block truncate text-[11px] text-muted">{l.blurb}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
