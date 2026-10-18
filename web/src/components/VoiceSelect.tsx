"use client";

import type { Meta } from "@/lib/api";
import { voiceGroups } from "@/lib/voices";

export function VoiceSelect({ meta, value, onChange, className, title }: {
  meta: Meta | null; value: string; onChange: (v: string) => void; className?: string; title?: string
}) {
  const groups = voiceGroups(meta);
  const known = groups.some((g) => g.items.some((i) => i.id === value));
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={className} title={title}>
      {!known && <option value={value}>{value}</option>}
      {groups.map((g) => (
        <optgroup key={g.label} label={g.label}>{g.items.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</optgroup>
      ))}
    </select>
  );
}
