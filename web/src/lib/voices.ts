import type { Meta } from "./api";

export const voiceLabel = (v: string, meta?: Meta | null) =>
  meta?.voice_profiles.find((p) => p.id === v)?.name ?? v.replace("_v", " v").replace("_", " ");

/** The channel's own voices, the person's cloned voices, then Gemini voices. Unfinished clones are not selectable. */
export function voiceGroups(meta?: Meta | null) {
  const ready = (meta?.voice_profiles ?? []).filter((p) => p.status === "ready");
  return [
    { label: "Cloned voices", items: ready.filter((p) => p.builtin).map((p) => ({ id: p.id, name: p.name })) },
    { label: "Your cloned voices", items: ready.filter((p) => !p.builtin).map((p) => ({ id: p.id, name: p.name })) },
    { label: "Gemini voices", items: (meta?.voices ?? ["Charon"]).map((v) => ({ id: v, name: v })) },
  ].filter((g) => g.items.length);
}
