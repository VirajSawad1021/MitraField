"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Clock, Layers, ShieldCheck } from "lucide-react";
import { SiteShell } from "@/components/marketing/Chrome";
import { Reveal } from "@/components/marketing/Reveal";
import { DEMOS, STEPS } from "@/lib/demo";
import { EngineChip } from "@/components/EngineChip";
import { engineStyle } from "@/lib/engines";

export default function DemoPage() {
  const [active, setActive] = useState(0);
  const d = DEMOS[active];
  const tall = d.aspect === "9:16";

  return (
    <SiteShell>
      <section className="mx-auto max-w-[1240px] px-5 pb-10 pt-14 sm:px-8 sm:pt-20">
        <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-muted animate-rise">Live demo</p>
        <h1 className="mt-3 max-w-[900px] text-[42px] font-medium leading-[1.03] tracking-[-0.035em] sm:text-[60px] animate-rise">
          One question in.<br /><span className="text-[#9b988f]">A finished explainer out.</span>
        </h1>
        <p className="mt-5 max-w-[620px] text-[16px] leading-relaxed text-body animate-rise [animation-delay:120ms]">
          Four videos made by MitraField from a single prompt each, with no manual editing. Below them, the exact steps
          the app went through, captured from the real workspace.
        </p>
      </section>

      {/* results */}
      <section className="mx-auto max-w-[1240px] px-5 sm:px-8">
        <div className="relative overflow-hidden rounded-[28px] grain">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/art/warm.webp" alt="" className="absolute inset-0 h-full w-full object-cover" />
          <div className="relative p-4 sm:p-8">
            <div className="mx-auto flex w-fit flex-wrap justify-center gap-1 rounded-full bg-white/70 p-1 backdrop-blur-md">
              {DEMOS.map((x, i) => (
                <button key={x.id} onClick={() => setActive(i)}
                  className={`h-9 rounded-full px-4 text-[13px] font-medium transition-all ${i === active ? "bg-white text-ink shadow-sm" : "text-body hover:text-ink"}`}>
                  {x.tab}
                </button>
              ))}
            </div>

            <div key={d.id} className={`mx-auto mt-6 grid gap-5 animate-fade-in ${tall ? "max-w-[920px] md:grid-cols-[360px_1fr]" : "max-w-[1080px] lg:grid-cols-[1.6fr_1fr]"}`}>
              <video src={d.video} poster={d.poster} controls playsInline preload="metadata"
                className={`w-full rounded-2xl bg-ink shadow-[0_30px_80px_-30px_rgba(60,30,10,0.5)] ${tall ? "aspect-[9/16]" : "aspect-video"}`} />
              <div className="rounded-2xl bg-white p-5">
                <p className="text-[12px] text-muted">Prompt</p>
                <p className="mt-1 text-[16px] font-medium leading-snug tracking-tight">&ldquo;{d.prompt}&rdquo;</p>
                <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                  <Stat icon={<Layers className="h-3.5 w-3.5" />} v={`${d.beats}`} l="beats" />
                  <Stat icon={<Clock className="h-3.5 w-3.5" />} v={d.length} l={tall ? "vertical Short" : "landscape"} />
                  <Stat icon={<ShieldCheck className="h-3.5 w-3.5" />} v={`${d.exact}/${d.beats}`} l="exact beats" />
                </div>
                <p className="mt-5 text-[12px] text-muted">How the director routed it</p>
                <div className="mt-2 flex h-2.5 gap-0.5 overflow-hidden rounded-full">
                  {d.route.map((e, i) => <span key={i} className="flex-1" style={{ background: engineStyle(e).color }} />)}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {[...new Set(d.route)].map((e) => <EngineChip key={e} engine={e} />)}
                </div>
                <p className="mt-5 text-[13px] leading-relaxed text-body">{d.note}</p>
                <p className="mt-4 text-[12px] text-muted">Narrated by {d.voice} · rendered in {d.renderTime} on one small server</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* walkthrough */}
      <section className="mx-auto max-w-[1240px] px-5 py-20 sm:px-8">
        <Reveal>
          <h2 className="text-[36px] font-medium leading-[1.05] tracking-[-0.03em] sm:text-[52px]">
            How the app made them.<br /><span className="text-[#9b988f]">Six steps, four of them automatic.</span>
          </h2>
        </Reveal>

        <div className="mt-14 space-y-20">
          {STEPS.map((s, i) => (
            <Reveal key={s.title}>
              <div className={`grid items-center gap-8 lg:grid-cols-[0.8fr_1.2fr] ${i % 2 ? "lg:[&>*:first-child]:order-2" : ""}`}>
                <div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-ink font-mono text-[12px] text-white">{i + 1}</span>
                    <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${s.who === "You" ? "bg-panel-2 text-body" : "bg-info-bg text-info"}`}>{s.who}</span>
                  </div>
                  <h3 className="mt-4 text-[26px] font-medium leading-tight tracking-[-0.02em]">{s.title}</h3>
                  <p className="mt-3 text-[15px] leading-relaxed text-body">{s.body}</p>
                  <ul className="mt-4 space-y-2">
                    {s.points.map((p) => (
                      <li key={p} className="flex gap-2 text-[13px] leading-snug text-ink"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-good" />{p}</li>
                    ))}
                  </ul>
                </div>
                <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-[0_30px_80px_-40px_rgba(20,20,19,0.35)]">
                  <div className="flex items-center gap-1.5 border-b border-line bg-panel px-4 py-2.5">
                    <i className="h-2.5 w-2.5 rounded-full bg-line-strong" /><i className="h-2.5 w-2.5 rounded-full bg-line-strong" /><i className="h-2.5 w-2.5 rounded-full bg-line-strong" />
                    <span className="ml-3 font-mono text-[11px] text-muted">mitrafield{s.path}</span>
                  </div>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={s.shot} alt={s.title} className="w-full" />
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-[1240px] px-5 pb-24 sm:px-8">
        <div className="relative overflow-hidden rounded-[28px] grain">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/art/sage.webp" alt="" className="absolute inset-0 h-full w-full object-cover" />
          <div className="relative flex flex-col items-start gap-6 p-6 sm:flex-row sm:items-end sm:justify-between sm:p-10">
            <div className="rounded-2xl bg-white/85 px-6 py-5 backdrop-blur-md">
              <h2 className="text-[30px] font-medium leading-[1.05] tracking-[-0.03em] sm:text-[40px]">Your turn.</h2>
              <p className="mt-2 text-[15px] text-ink/70">Open a demo project in the studio, or ask your own question.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href={`/studio?p=${DEMOS[active].id}`} className="inline-flex h-12 items-center rounded-full bg-white px-6 text-[15px] font-medium text-ink hover:bg-cream">Open in studio</Link>
              <Link href="/new" className="inline-flex h-12 items-center gap-2 rounded-full bg-ink px-6 text-[15px] font-medium text-white hover:bg-ink-soft">
                Start a video <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </SiteShell>
  );
}

function Stat({ icon, v, l }: { icon: React.ReactNode; v: string; l: string }) {
  return (
    <div className="rounded-xl bg-panel px-2 py-3">
      <p className="flex items-center justify-center gap-1 text-[17px] font-semibold tracking-tight">{icon}{v}</p>
      <p className="mt-0.5 text-[11px] text-muted">{l}</p>
    </div>
  );
}
