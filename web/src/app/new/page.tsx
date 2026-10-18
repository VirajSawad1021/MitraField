"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, FileText, Monitor, Smartphone, Upload, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button, Card, ErrorNote, Eyebrow, Field, Segmented, inputCls } from "@/components/ui";
import { api, MAX_INSTRUCTIONS, type Meta } from "@/lib/api";
import { NarratorPicker } from "@/components/NarratorPicker";
import { LookPicker } from "@/components/LookPicker";

const EXAMPLES = [
  "Why does Japan have so few babies?",
  "What is a Fourier transform, really?",
  "How does a vaccine teach your body to fight a virus?",
  "Why the Strait of Hormuz matters to the whole world",
  "How does GPS know exactly where you are?",
];
const DIRECTIONS = [
  "Only math animations, no AI images or video.",
  "Text only: title cards, no images or video.",
  "Charts, diagrams and whiteboard sketches only.",
];
const LANGS = ["English", "Hindi", "Nepali", "Japanese", "Indonesian", "Korean", "Spanish", "Tamil", "Vietnamese"];
const AUDIENCES = ["curious general audience", "school students (age 12-15)", "university students", "busy professionals"];

export default function NewPage() {
  return (
    <AppShell>
      <Suspense>
        <NewVideo />
      </Suspense>
    </AppShell>
  );
}

function NewVideo() {
  const router = useRouter();
  const q = useSearchParams();
  const [topic, setTopic] = useState("");
  const [notes, setNotes] = useState("");
  const [instructions, setInstructions] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [aspect, setAspect] = useState<"16:9" | "9:16">(q.get("aspect") === "9:16" ? "9:16" : "16:9");
  const [length, setLength] = useState<"short" | "medium" | "long">(q.get("aspect") === "9:16" ? "short" : "medium");
  const [language, setLanguage] = useState("English");
  const [audience, setAudience] = useState(AUDIENCES[0]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [voice, setVoice] = useState("");
  const [look, setLook] = useState("cinematic");
  useEffect(() => {
    const load = () => api.meta().then((m) => { setMeta(m); setVoice((v) => v || m.default_voice); }).catch(() => {});
    load();
    window.addEventListener("focus", load);   // a voice cloned in another tab shows up on return
    return () => window.removeEventListener("focus", load);
  }, []);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const go = async () => {
    if (!topic.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const p = await api.create({ topic, notes, instructions: instructions.trim(), aspect, length, language, audience, ...(voice ? { voice } : {}), look });
      for (const f of files) await api.addFile(p.id, f);
      await api.storyboard(p.id);
      router.push(`/studio?p=${p.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-[1080px] px-5 pt-10 sm:px-8">
      <Eyebrow>New video</Eyebrow>
      <h1 className="mt-1.5 text-[32px] font-semibold tracking-tight sm:text-[36px]">What should it explain?</h1>
      <p className="mt-1.5 max-w-xl text-[14px] leading-relaxed text-body">
        Ask a question or paste what you know. The director writes a storyboard you can edit before anything renders.
      </p>

      <div className="mt-8 grid gap-5 lg:grid-cols-[1.35fr_1fr]">
        <Card className="p-5">
          <textarea autoFocus value={topic} onChange={(e) => setTopic(e.target.value)} rows={3}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) go(); }}
            placeholder="e.g. Why do we procrastinate, and how do you actually stop?"
            className="w-full resize-none bg-transparent text-[22px] font-medium leading-snug tracking-tight placeholder:text-[#b5b2aa] focus:outline-none" />
          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLES.map((x) => (
              <button key={x} onClick={() => setTopic(x)} className="rounded-full border border-line px-3 py-1 text-[12px] text-body transition-colors hover:border-line-strong hover:text-ink">{x}</button>
            ))}
          </div>

          <div className="mt-6 border-t border-line pt-5">
            <p className="text-[12px] font-semibold">Instructions for the director <span className="font-normal text-muted">(optional)</span></p>
            <p className="mb-3 mt-0.5 text-[11px] text-muted">Anything it must follow, in your own words. It takes these over its own defaults.</p>
            <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={2} maxLength={MAX_INSTRUCTIONS}
              placeholder="e.g. Only math animations, no AI images or video." className={`${inputCls} resize-none text-[13px]`} />
            <div className="mt-2 flex flex-wrap gap-2">
              {DIRECTIONS.map((x) => (
                <button key={x} type="button" onClick={() => setInstructions(x)} className="rounded-full border border-line px-3 py-1 text-[12px] text-body transition-colors hover:border-line-strong hover:text-ink">{x}</button>
              ))}
            </div>
          </div>

          <div className="mt-6 grid gap-5 border-t border-line pt-5 sm:grid-cols-2">
            <Field label="Format">
              <Segmented value={aspect} onChange={setAspect} options={[
                { value: "16:9", label: <span className="flex items-center gap-1.5"><Monitor className="h-3.5 w-3.5" />Landscape</span> },
                { value: "9:16", label: <span className="flex items-center gap-1.5"><Smartphone className="h-3.5 w-3.5" />Short</span> },
              ]} />
            </Field>
            <Field label="Length">
              <Segmented value={length} onChange={setLength} options={[
                { value: "short", label: "~1 min" }, { value: "medium", label: "~3 min" }, { value: "long", label: "~6 min" },
              ]} />
            </Field>
            <Field label="Narration language">
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className={inputCls}>
                {LANGS.map((l) => <option key={l}>{l}</option>)}
              </select>
            </Field>
            <Field label="Audience" hint="The director adjusts vocabulary, pace and examples.">
              <input list="aud" value={audience} onChange={(e) => setAudience(e.target.value)} className={inputCls} />
              <datalist id="aud">{AUDIENCES.map((a) => <option key={a} value={a} />)}</datalist>
            </Field>
          </div>

          <div className="mt-6 border-t border-line pt-5">
            <p className="text-[12px] font-semibold">Narrator</p>
            <p className="mb-3 mt-0.5 text-[11px] text-muted">Cloned voices sound like a real person and can narrate in other languages too. Gemini voices are an alternative.</p>
            <NarratorPicker meta={meta} value={voice} onChange={setVoice} />
          </div>

          {meta?.looks && (
            <div className="mt-6 border-t border-line pt-5">
              <p className="text-[12px] font-semibold">Look</p>
              <p className="mb-3 mt-0.5 text-[11px] text-muted">The art style for AI-generated pictures and characters. Charts, maps and math stay accurate in any look.</p>
              <LookPicker looks={meta.looks} value={look} onChange={setLook} />
            </div>
          )}
        </Card>

        <Card className="p-5" id="sources">
          <p className="text-[15px] font-semibold">Sources <span className="font-normal text-muted">(optional)</span></p>
          <p className="mt-1 text-[12px] leading-relaxed text-body">The director treats these as the source of truth over its own memory.</p>
          <label
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); setFiles((f) => [...f, ...Array.from(e.dataTransfer.files)]); }}
            className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-4 py-7 text-center transition-colors ${drag ? "border-ink bg-panel-2" : "border-line-strong bg-panel/60 hover:bg-panel"}`}>
            <Upload className="h-5 w-5 text-body" />
            <span className="mt-2 text-[13px] font-medium">Drop PDFs, images or notes</span>
            <span className="mt-0.5 text-[11px] text-muted">Lesson plans, articles, reports, screenshots</span>
            <input type="file" multiple hidden onChange={(e) => setFiles((f) => [...f, ...Array.from(e.target.files || [])])} />
          </label>
          {files.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {files.map((f, i) => (
                <li key={i} className="flex items-center gap-2 rounded-xl bg-panel px-3 py-2 text-[12px]">
                  <FileText className="h-3.5 w-3.5 text-muted" /><span className="flex-1 truncate">{f.name}</span>
                  <button onClick={() => setFiles(files.filter((_, j) => j !== i))} className="text-muted hover:text-ink"><X className="h-3.5 w-3.5" /></button>
                </li>
              ))}
            </ul>
          )}
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={5}
            placeholder="Or paste notes, facts, a lesson outline…" className={`${inputCls} mt-4 resize-none text-[13px]`} />
        </Card>
      </div>

      {err && <div className="mt-4"><ErrorNote message={err} /></div>}

      {/* the one action, always in view however long the form gets */}
      <div className="sticky bottom-0 z-20 -mx-5 mt-6 border-t border-line bg-cream/90 px-5 py-3 backdrop-blur-md sm:-mx-8 sm:px-8">
        <div className="flex items-center justify-between gap-4">
          <p className="min-w-0 text-[12px] text-muted">
            {topic.trim() ? "Nothing renders until you approve the storyboard." : "Type a question above to start."}
          </p>
          <Button size="lg" onClick={go} loading={busy} disabled={!topic.trim()} className="shrink-0">
            Write storyboard <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </main>
  );
}
