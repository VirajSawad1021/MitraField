"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { BadgeCheck, FileVideo, ScanSearch, SearchX } from "lucide-react";
import { Button, Card, ErrorNote, Eyebrow } from "@/components/ui";
import { api, type Verification } from "@/lib/api";

const MAX_MB = 300;
const when = (t: number) => new Date(t * 1000).toLocaleString(undefined, { dateStyle: "long", timeStyle: "short" });

/** Upload a video and find out whether it was exported from this platform. */
export function VerifyLab() {
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(0);
  const [res, setRes] = useState<Verification | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval>>(undefined);
  useEffect(() => () => clearInterval(timer.current), []);

  const pick = (f?: File | null) => {
    if (!f) return;
    setRes(null); setErr(null);
    if (f.size > MAX_MB * 1048576) { setFile(null); setErr(`Videos are limited to ${MAX_MB} MB.`); return; }
    setFile(f);
  };

  const check = async () => {
    if (!file) return;
    setBusy(true); setErr(null); setRes(null); setSent(0);
    try {
      const id = await api.verify(file, setSent);
      timer.current = setInterval(async () => {
        try {
          const v = await api.verification(id);
          if (v.status === "done" || v.status === "error") {
            clearInterval(timer.current); setBusy(false);
            if (v.status === "error") setErr(v.error || "The check failed."); else setRes(v);
          }
        } catch (e) { clearInterval(timer.current); setBusy(false); setErr(e instanceof Error ? e.message : "The check failed."); }
      }, 2500);
    } catch (e) { setBusy(false); setErr(e instanceof Error ? e.message : "The upload failed."); }
  };

  return (
    <main className="mx-auto max-w-[760px] px-5 pb-24 pt-10 sm:px-8">
      <Eyebrow>Verify</Eyebrow>
      <h1 className="mt-1.5 text-[32px] font-semibold tracking-tight sm:text-[36px]">Was this video made on mitrafield?</h1>
      <p className="mt-1.5 max-w-xl text-[14px] leading-relaxed text-body">
        Every video we export carries an invisible mark in its picture. Upload a video and we look for it. The file is read once and deleted.
      </p>

      <Card className="mt-8 p-5">
        <label onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-4 py-10 text-center transition-colors ${drag ? "border-ink bg-panel-2" : "border-line-strong bg-panel/60 hover:bg-panel"}`}>
          <FileVideo className="h-6 w-6 text-body" />
          <span className="mt-2 text-[14px] font-medium">{file ? file.name : "Drop a video here, or click to choose one"}</span>
          <span className="mt-0.5 text-[12px] text-muted">{file ? `${(file.size / 1048576).toFixed(1)} MB` : `MP4, MOV or WebM, up to ${MAX_MB} MB`}</span>
          <input type="file" accept="video/*" hidden disabled={busy} onChange={(e) => pick(e.target.files?.[0])} />
        </label>
        <div className="mt-4 flex items-center justify-between gap-4">
          <p className="text-[12px] text-muted">
            {busy ? (sent < 1 ? `Uploading ${Math.round(sent * 100)}%` : "Looking for the mark…") : "Checking takes under a minute."}
          </p>
          <Button onClick={check} loading={busy} disabled={!file}><ScanSearch className="h-4 w-4" />Check video</Button>
        </div>
      </Card>

      {err && <div className="mt-4"><ErrorNote message={err} /></div>}
      {res && <Verdict v={res} />}

      <div className="mt-10 space-y-2 text-[12px] leading-relaxed text-muted">
        <p className="font-semibold text-body">What this can and cannot tell you</p>
        <p>The mark survives re-uploading, compression, resizing, a different frame rate and trimming the start. Heavy cropping, filters or deliberately removing it can defeat it.</p>
        <p>Finding no mark is not proof a video is not ours. It only means we could not find one.</p>
      </div>
    </main>
  );
}

function Verdict({ v }: { v: Verification }) {
  const found = v.verdict === "exact" || v.verdict === "mark";
  return (
    <Card className="mt-4 p-5 animate-fade-in">
      <div className="flex items-start gap-3">
        {found ? <BadgeCheck className="mt-0.5 h-6 w-6 shrink-0 text-good" /> : <SearchX className="mt-0.5 h-6 w-6 shrink-0 text-muted" />}
        <div className="min-w-0">
          <p className="text-[18px] font-semibold tracking-tight">
            {v.verdict === "exact" && "This is an original mitrafield export"}
            {v.verdict === "mark" && "Made on mitrafield"}
            {v.verdict === "none" && "No mitrafield mark found"}
          </p>
          <p className="mt-1 text-[13px] leading-relaxed text-body">
            {v.verdict === "exact" && "This is the exact file we exported, byte for byte, and it carries our mark."}
            {v.verdict === "mark" && `Our invisible mark is in this video${v.trimmed ? ", which has been trimmed" : ""}. It was re-encoded or edited after we exported it.`}
            {v.verdict === "none" && (v.note || "We could not find our mark. The video may come from somewhere else, or it may have been edited too heavily for the mark to survive.")}
          </p>
          {found && v.origin && (
            <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-5 gap-y-1.5 text-[13px]">
              <dt className="text-muted">Exported</dt><dd>{when(v.origin.created)}</dd>
              <dt className="text-muted">Length</dt><dd>{Math.round(v.origin.seconds)} seconds, {v.origin.aspect}</dd>
              <dt className="text-muted">Built with</dt><dd className="capitalize">{v.origin.engines.join(", ")}</dd>
              <dt className="text-muted">Project</dt><dd><Link href={`/studio?p=${v.origin.project}`} className="font-mono text-[12px] underline underline-offset-2">{v.origin.project}</Link></dd>
              {v.snr !== undefined && <><dt className="text-muted">Signal</dt><dd>{v.snr} (above 3 is a reliable read)</dd></>}
            </dl>
          )}
        </div>
      </div>
    </Card>
  );
}
