"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Mic, Square, Trash2, Upload } from "lucide-react";
import { Badge, Button, Card, ErrorNote, Eyebrow, Field, inputCls } from "@/components/ui";
import { api, type Meta, type VoiceProfile } from "@/lib/api";

const LANGS = ["English", "Hindi", "Nepali", "Japanese", "Indonesian", "Korean", "Spanish", "Tamil", "Vietnamese"];
const SCRIPT = "Learning is an important part of life. Every day we learn something new, a new idea, a new skill, or a simple fact, step by step.";

export function VoiceLab() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(() => api.voices().then(setVoices).catch((e) => setErr(String(e.message || e))), []);
  useEffect(() => { api.meta().then(setMeta).catch(() => {}); refresh(); }, [refresh]);
  const pending = voices.some((v) => v.status === "pending");
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [pending, refresh]);

  const mine = voices.filter((v) => !v.builtin);
  return (
    <main className="mx-auto max-w-[1080px] px-5 pb-24 pt-10 sm:px-8">
      <Eyebrow>Voices</Eyebrow>
      <h1 className="mt-1.5 text-[32px] font-semibold tracking-tight sm:text-[36px]">Narrate in your own voice</h1>
      <p className="mt-1.5 max-w-xl text-[14px] leading-relaxed text-body">
        Record or upload 10 to 20 seconds of clear speech. The voice is cloned once, then available as a narrator for every video.
      </p>

      {meta && !meta.cloning && (
        <div className="mt-6"><ErrorNote message="Voice cloning is not enabled on this deployment. Gemini voices are available." /></div>
      )}

      <div className="mt-8 grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        <Card className="p-5">
          <p className="text-[15px] font-semibold">Your voices</p>
          {mine.length === 0 && <p className="mt-3 text-[13px] text-muted">None yet. Create your first voice on the right.</p>}
          <ul className="mt-3 space-y-2">
            {mine.map((v) => (
              <li key={v.id} className="flex items-center gap-3 rounded-xl bg-panel px-3.5 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-medium">{v.name}</p>
                  {v.status === "error" && <p className="mt-0.5 text-[12px] text-bad">{v.error}</p>}
                </div>
                <Badge tone={v.status === "ready" ? "good" : v.status === "error" ? "bad" : "warn"}>
                  {v.status === "ready" ? "Ready" : v.status === "error" ? "Failed" : "Building…"}
                </Badge>
                <button title="Delete voice" onClick={async () => {
                  if (!window.confirm(`Delete the voice "${v.name}"? Videos using it will fall back to a Gemini voice.`)) return;
                  try { await api.deleteVoice(v.id); refresh(); } catch (e) { setErr(e instanceof Error ? e.message : "Could not delete"); }
                }} className="text-muted hover:text-bad"><Trash2 className="h-4 w-4" /></button>
              </li>
            ))}
          </ul>
          {voices.some((v) => v.builtin) && (
            <p className="mt-4 text-[12px] text-muted">Channel voices: {voices.filter((v) => v.builtin).map((v) => v.name).join(", ")}</p>
          )}
        </Card>

        {meta?.cloning && <Create onDone={refresh} />}
      </div>
      {err && <div className="mt-4"><ErrorNote message={err} /></div>}
    </main>
  );
}

function Create({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("English");
  const [text, setText] = useState("");
  const [file, setFile] = useState<Blob | null>(null);
  const [fileName, setFileName] = useState("");
  const [consent, setConsent] = useState(false);
  const [rec, setRec] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);

  const start = async () => {
    setErr(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const r = new MediaRecorder(stream);
      r.ondataavailable = (e) => chunks.push(e.data);
      r.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        setFile(new Blob(chunks, { type: r.mimeType })); setFileName("Recording");
      };
      r.start();
      recorder.current = r;
      setRec(true);
    } catch { setErr("The microphone is not available. Upload a recording instead."); }
  };
  const stop = () => { recorder.current?.stop(); setRec(false); };

  const submit = async () => {
    if (!file) return;
    setBusy(true); setErr(null); setDone(false);
    try {
      await api.createVoice(() => {
        const fd = new FormData();
        fd.append("name", name); fd.append("language", language); fd.append("reference_text", text); fd.append("consent", String(consent));
        fd.append("file", file, fileName === "Recording" ? "recording.webm" : fileName);
        return fd;
      });
      setName(""); setText(""); setFile(null); setFileName(""); setConsent(false); setDone(true);
      onDone();
    } catch (e) {
      let m = e instanceof Error ? e.message : "Something went wrong";
      try { m = JSON.parse(m).detail ?? m; } catch {}
      setErr(m);
    }
    setBusy(false);
  };

  return (
    <Card className="p-5">
      <p className="text-[15px] font-semibold">Create a voice</p>
      <div className="mt-4 space-y-4">
        <Field label="Name"><input value={name} onChange={(e) => setName(e.target.value)} maxLength={40} placeholder="e.g. My voice" className={inputCls} /></Field>

        <Field label="Sample" hint={<>Read this aloud, or say anything clearly: <span className="italic">“{SCRIPT}”</span></>}>
          <div className="flex flex-wrap items-center gap-2">
            {rec
              ? <Button variant="danger" size="sm" onClick={stop}><Square className="h-3.5 w-3.5" />Stop</Button>
              : <Button variant="secondary" size="sm" onClick={start}><Mic className="h-3.5 w-3.5" />Record</Button>}
            <label className="inline-flex h-8 cursor-pointer items-center gap-2 rounded-full border border-line-strong bg-white px-3.5 text-[12px] font-semibold hover:border-ink/40">
              <Upload className="h-3.5 w-3.5" />Upload
              <input type="file" accept="audio/*" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) { setFile(f); setFileName(f.name); } }} />
            </label>
            {file && <span className="flex items-center gap-1 text-[12px] text-body"><Check className="h-3.5 w-3.5 text-good" />{fileName}</span>}
          </div>
          {file && fileName === "Recording" && <audio className="mt-2 h-9 w-full" controls src={URL.createObjectURL(file)} />}
        </Field>

        <Field label="Language">
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className={inputCls}>{LANGS.map((l) => <option key={l}>{l}</option>)}</select>
        </Field>
        <Field label="What was said" hint="Optional. Leave empty and it is transcribed for you; typing it improves the match.">
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} className={`${inputCls} resize-none text-[13px]`} />
        </Field>

        <label className="flex items-start gap-2.5 text-[12px] leading-snug text-body">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5" />
          <span>This is my own voice, or I have the speaker&apos;s permission to clone it. I will not use it to impersonate anyone.</span>
        </label>

        <Button onClick={submit} loading={busy} disabled={!name.trim() || !file || !consent || rec}>Create voice</Button>
        {done && <p className="text-[12px] text-good">Saved. It is being built and will be ready in a few seconds.</p>}
        {err && <ErrorNote message={err} />}
      </div>
    </Card>
  );
}
