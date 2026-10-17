"use client";

import { useState } from "react";
import { Box, Loader2, MapPin, Palette, Plus, RefreshCw, Trash2, User, X } from "lucide-react";
import { Button, Segmented, inputCls } from "@/components/ui";
import { api, type CastItem, type Project } from "@/lib/api";

export const CAST_KIND = {
  style: { label: "Style", icon: Palette },
  character: { label: "Character", icon: User },
  location: { label: "Location", icon: MapPin },
  object: { label: "Object", icon: Box },
} as const;

/** Flow-style ingredients: defined once, reused by every generated beat they appear in. */
export function CastStrip({ p, setP }: { p: Project; setP: (p: Project) => void }) {
  const [open, setOpen] = useState<string | "new" | null>(null);
  const item = p.cast.find((c) => c.id === open) ?? null;
  const uses = (id: string) => p.scenes.filter((s) => s.cast?.includes(id)).length;

  return (
    <div className="mt-5 rounded-2xl border border-line bg-white p-3">
      <div className="flex items-center gap-3 overflow-x-auto scrollbar-thin">
        <div className="shrink-0 pl-1 pr-2">
          <p className="text-[13px] font-semibold">Cast &amp; sets</p>
          <p className="text-[11px] text-muted">Same look in every beat</p>
        </div>
        {p.cast.map((c) => {
          const K = CAST_KIND[c.kind];
          const busy = c.status === "generating" || c.status === "pending";
          return (
            <button key={c.id} onClick={() => setOpen(open === c.id ? null : c.id)}
              className={`group flex shrink-0 items-center gap-2.5 rounded-xl border p-1.5 pr-3 text-left transition-all ${open === c.id ? "border-ink bg-panel" : "border-line hover:border-line-strong"}`}>
              <span className="relative h-11 w-11 shrink-0 overflow-hidden rounded-lg bg-panel-2">
                {c.image_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={c.image_url} alt={c.name} className={`h-full w-full object-cover ${busy ? "opacity-40" : ""}`} />
                )}
                {busy && <Loader2 className="absolute inset-0 m-auto h-4 w-4 animate-spin text-body" />}
                {!c.image_url && !busy && <K.icon className="absolute inset-0 m-auto h-4 w-4 text-muted" />}
              </span>
              <span className="min-w-0">
                <span className="block max-w-[140px] truncate text-[12.5px] font-semibold">{c.name}</span>
                <span className="flex items-center gap-1 text-[11px] text-muted">
                  <K.icon className="h-3 w-3" />{K.label}{c.kind !== "style" && ` · ${uses(c.id)} beats`}
                  {c.status === "error" && <span className="text-bad"> · failed</span>}
                </span>
              </span>
            </button>
          );
        })}
        <button onClick={() => setOpen(open === "new" ? null : "new")}
          className="flex h-[58px] shrink-0 items-center gap-1.5 rounded-xl border border-dashed border-line-strong px-4 text-[12.5px] font-medium text-body hover:bg-panel">
          <Plus className="h-4 w-4" />Add
        </button>
      </div>
      {open === "new" && <CastEditor key="new" p={p} setP={setP} close={() => setOpen(null)} />}
      {item && <CastEditor key={item.id} p={p} item={item} setP={setP} close={() => setOpen(null)} />}
    </div>
  );
}

function CastEditor({ p, item, setP, close }: { p: Project; item?: CastItem; setP: (p: Project) => void; close: () => void }) {
  const [kind, setKind] = useState<CastItem["kind"]>(item?.kind ?? "character");
  const [name, setName] = useState(item?.name ?? "");
  const [desc, setDesc] = useState(item?.description ?? "");
  const [busy, setBusy] = useState(false);
  const changed = !item || name !== item.name || desc !== item.description || kind !== item.kind;

  const save = async () => {
    setBusy(true);
    try {
      setP(item ? await api.editCast(p.id, item.id, { name, description: desc, kind }) : await api.addCast(p.id, { name, description: desc, kind }));
      if (!item) close();
    } finally { setBusy(false); }
  };

  return (
    <div className="mt-3 grid gap-4 border-t border-line pt-4 animate-fade-in md:grid-cols-[200px_1fr]">
      <div className="aspect-square overflow-hidden rounded-xl bg-panel-2">
        {item?.image_url
          // eslint-disable-next-line @next/next/no-img-element
          ? <img src={item.image_url} alt={item.name} className="h-full w-full object-cover" />
          : <div className="flex h-full items-center justify-center p-4 text-center text-[12px] text-muted">The reference image is drawn when you save.</div>}
      </div>
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <Segmented size="sm" value={kind} onChange={setKind}
            options={(Object.keys(CAST_KIND) as CastItem["kind"][]).map((k) => ({ value: k, label: CAST_KIND[k].label }))} />
          <button onClick={close} className="ml-auto rounded-full p-1 text-muted hover:bg-panel-2 hover:text-ink"><X className="h-4 w-4" /></button>
        </div>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name, e.g. Captain Smith" className={inputCls} />
        <textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={3} className={`${inputCls} resize-none text-[13px] leading-relaxed`}
          placeholder="What it looks like: age, clothing, colours, materials, era. For a style: medium, lighting, palette." />
        {item?.error && <p className="text-[12px] text-bad">{item.error}</p>}
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={save} loading={busy} disabled={!name.trim() || !changed}>{item ? "Save and redraw" : "Add to cast"}</Button>
          {item && <Button size="sm" variant="secondary" onClick={() => api.regenCast(p.id, item.id).then(setP)}><RefreshCw className="h-3.5 w-3.5" />Redraw</Button>}
          {item && (
            <Button size="sm" variant="ghost" className="ml-auto hover:text-bad"
              onClick={() => confirm(`Remove ${item.name} from the cast?`) && api.delCast(p.id, item.id).then((np) => { setP(np); close(); })}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
        <p className="text-[11px] leading-snug text-muted">
          {kind === "style" ? "Every generated beat is drawn in this style." : "Beats that include this item get its reference image, so it looks the same every time."}
          {" "}Re-render a beat to apply changes.
        </p>
      </div>
    </div>
  );
}
