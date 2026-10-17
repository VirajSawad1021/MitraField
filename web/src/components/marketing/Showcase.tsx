"use client";

import { useEffect, useState } from "react";
import { Check, Languages, ShieldCheck, Sparkles } from "lucide-react";
import { EngineChip } from "@/components/EngineChip";
import { engineStyle } from "@/lib/engines";

/* Real storyboard from the Strait of Hormuz project the director wrote. */
const BOARD = [
  { e: "title", n: "Twenty percent of the world's oil passes through a channel just twenty one miles wide.", d: 11.1 },
  { e: "globe", n: "This is the Strait of Hormuz. It separates Iran from the Arabian Peninsula.", d: 11.3 },
  { e: "veo", n: "Giant supertankers carry crude oil from the Persian Gulf to the open ocean every single day.", d: 12.6 },
  { e: "whiteboard", n: "Countries like Saudi Arabia and Iraq rely heavily on this single exit door.", d: 10.9 },
  { e: "manim", n: "That adds up to around twenty one million barrels of oil daily.", d: 7.5 },
  { e: "character", n: "Imagine trying to empty a giant swimming pool through a garden hose.", d: 13.3 },
];

const TABS = ["Direct", "Route", "Render", "Translate"] as const;
type Tab = (typeof TABS)[number];

export function Showcase() {
  const [tab, setTab] = useState<Tab>("Direct");
  const [hold, setHold] = useState(false);

  useEffect(() => {
    if (hold) return;
    const t = setInterval(() => setTab((x) => TABS[(TABS.indexOf(x) + 1) % TABS.length]), 5200);
    return () => clearInterval(t);
  }, [hold]);

  return (
    <div className="relative overflow-hidden rounded-[28px] grain" onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/art/warm.webp" alt="" className="absolute inset-0 h-full w-full object-cover animate-drift" />
      <div className="relative px-4 pb-8 pt-8 sm:px-10 sm:pb-10">
        <div className="mx-auto flex w-fit gap-1 rounded-full bg-white/70 p-1 backdrop-blur-md">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`relative h-9 rounded-full px-4 text-[13px] font-medium transition-all ${tab === t ? "bg-white text-ink shadow-sm" : "text-body hover:text-ink"}`}>
              {t}
            </button>
          ))}
        </div>

        <div className="mx-auto mt-6 max-w-[880px] overflow-hidden rounded-2xl bg-white shadow-[0_30px_80px_-30px_rgba(60,30,10,0.45)]">
          <div className="flex items-center justify-between border-b border-line px-5 py-3 text-[12px] text-muted">
            <span>{tab === "Direct" ? "Director agent" : tab === "Route" ? "Routing" : tab === "Render" ? "Render queue" : "Translate"}</span>
            <span>The bottleneck of the world · 16:9</span>
          </div>
          <div key={tab} className="min-h-[360px] p-5 animate-fade-in">
            {tab === "Direct" && <DirectPane />}
            {tab === "Route" && <RoutePane />}
            {tab === "Render" && <RenderPane />}
            {tab === "Translate" && <TranslatePane />}
          </div>
        </div>
      </div>
    </div>
  );
}

function DirectPane() {
  return (
    <div className="grid gap-5 md:grid-cols-[0.9fr_1.1fr]">
      <div>
        <p className="text-[12px] text-muted">Your prompt</p>
        <div className="mt-2 rounded-xl bg-panel px-4 py-3 text-[14px] leading-relaxed text-ink">
          Why does a tiny strip of water called the Strait of Hormuz matter to the whole world?<span className="ml-0.5 inline-block h-4 w-px translate-y-0.5 animate-pulse bg-ink" />
        </div>
        <p className="mt-5 text-[12px] text-muted">Sources</p>
        <div className="mt-2 space-y-2">
          {["EIA chokepoint factsheet.pdf", "Teacher notes: energy unit"].map((s) => (
            <div key={s} className="flex items-center gap-2 rounded-xl border border-line px-3 py-2 text-[12px] text-body">
              <span className="rounded-md bg-panel-2 px-1.5 py-0.5 font-mono text-[10px] text-muted">{s.endsWith(".pdf") ? "PDF" : "NOTE"}</span>{s}
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl border border-line">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <p className="text-[14px] font-semibold">Storyboard</p>
          <p className="text-[12px] text-muted">9 beats · 0:49</p>
        </div>
        <div className="space-y-2 p-3">
          {BOARD.slice(0, 5).map((b, i) => {
            return (
              <div key={i} className="flex items-start gap-3 rounded-xl border border-line px-3 py-2.5" style={{ animation: `rise .6s ${i * 90}ms both cubic-bezier(.2,.7,.2,1)` }}>
                <span className="mt-0.5 font-mono text-[10px] text-muted">b{i + 1}</span>
                <p className="flex-1 text-[12px] leading-snug text-ink">{b.n}</p>
                <EngineChip engine={b.e} size="sm" />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function RoutePane() {
  const total = BOARD.reduce((a, b) => a + b.d, 0);
  return (
    <div>
      <div className="flex h-3 gap-0.5 overflow-hidden rounded-full">
        {BOARD.map((b, i) => <div key={i} style={{ flexGrow: b.d / total, background: engineStyle(b.e).color, animation: `grow .8s ${i * 80}ms both`, transformOrigin: "left" }} />)}
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {BOARD.map((b, i) => {
          const s = engineStyle(b.e);
          return (
            <div key={i} className="flex items-start gap-3 rounded-xl border border-line p-3">
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-white ${s.art}`}><s.icon className="h-4 w-4" /></span>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-[13px] font-semibold">{s.short}</p>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${s.kind === "exact" ? "bg-good-bg text-good" : "bg-panel-2 text-body"}`}>{s.kind}</span>
                </div>
                <p className="mt-0.5 line-clamp-2 text-[12px] text-body">{b.n}</p>
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-4 flex items-center gap-2 rounded-xl bg-good-bg px-4 py-2.5 text-[12px] text-good">
        <ShieldCheck className="h-4 w-4" /> Numbers, maps and math go to exact engines. Generated pixels never carry a fact.
      </p>
    </div>
  );
}

function RenderPane() {
  const shots = ["title", "globe", "veo", "whiteboard", "manim", "character"];
  return (
    <div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {shots.map((e, i) => {
          const s = engineStyle(e);
          return (
            <div key={e} className="overflow-hidden rounded-xl border border-line" style={{ animation: `rise .6s ${i * 90}ms both cubic-bezier(.2,.7,.2,1)` }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`/showcase/${e}.jpg`} alt={s.short} className="aspect-video w-full object-cover" />
              <div className="flex items-center justify-between px-2.5 py-2 text-[11px]">
                <span className="flex items-center gap-1.5 font-medium"><i className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />{s.short}</span>
                <Check className="h-3.5 w-3.5 text-good" />
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-4 flex items-center gap-2 text-[12px] text-muted">
        <Sparkles className="h-3.5 w-3.5" /> Manim scenes are checked frame by frame by Gemini and repaired before you see them.
      </p>
    </div>
  );
}

function TranslatePane() {
  const langs = [
    ["Hindi", "दुनिया का बीस प्रतिशत तेल सिर्फ़ इक्कीस मील चौड़े रास्ते से गुज़रता है।"],
    ["Nepali", "संसारको बीस प्रतिशत तेल केवल एक्काइस माइल चौडा जलमार्गबाट जान्छ।"],
    ["Japanese", "世界の石油の二割が、幅わずか三十四キロの海峡を通ります。"],
    ["Indonesian", "Dua puluh persen minyak dunia melewati selat yang lebarnya hanya dua puluh satu mil."],
  ];
  return (
    <div className="grid gap-5 md:grid-cols-[0.8fr_1.2fr]">
      <div className="rounded-2xl bg-panel p-4">
        <Languages className="h-5 w-5 text-ink" />
        <p className="mt-3 text-[15px] font-semibold">Same visuals. New voice.</p>
        <p className="mt-1.5 text-[13px] leading-relaxed text-body">
          The director re-writes the narration for natural speech in each language. Generated shots are reused, and on-screen text in
          maps, math and titles is re-rendered in the new language.
        </p>
      </div>
      <div className="space-y-2">
        {langs.map(([l, t], i) => (
          <div key={l} className="rounded-xl border border-line px-4 py-3" style={{ animation: `rise .6s ${i * 90}ms both cubic-bezier(.2,.7,.2,1)` }}>
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">{l}</p>
            <p className="mt-1 text-[14px] text-ink">{t}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
