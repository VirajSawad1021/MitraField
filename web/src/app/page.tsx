import Link from "next/link";
import { ArrowRight, Check, Minus, Plus } from "lucide-react";
import { SiteShell } from "@/components/marketing/Chrome";
import { Reveal } from "@/components/marketing/Reveal";
import { Showcase } from "@/components/marketing/Showcase";
import { ENGINES } from "@/lib/engines";

const BUILT_ON = ["Gemini 3.1 Pro", "Veo 3.1", "Nano Banana", "Lyria", "Gemini TTS", "Manim", "Natural Earth", "FastAPI", "Next.js", "Cloud Run"];

const ENGINE_COPY: Record<string, { name: string; for: string; how: string }> = {
  manim: { name: "Math animation", for: "Equations, graphs, geometry, algorithms", how: "Gemini writes Manim code for the exact narration length, renders it, then inspects the frames and repairs anything that overlaps." },
  globe: { name: "Globe & maps", for: "Places, routes, empires, migrations", how: "Natural Earth borders on a real orthographic globe. Camera flights, highlighted countries, pins and great-circle routes." },
  whiteboard: { name: "Whiteboard", for: "Processes, cause and effect, comparisons", how: "Nano Banana sketches clean line art, then MitraField draws it on stroke by stroke like a teacher at the board." },
  chart: { name: "Data chart", for: "Comparisons, shares, rankings, trends", how: "Bars that grow and count up, or a line that draws the trend, from numbers taken from your sources. Every value is typeset by code." },
  timeline: { name: "Timeline", for: "History, discoveries, sequences", how: "A time axis draws in and each event lands at its real date. Crowded dates spread out evenly so labels stay readable." },
  flow: { name: "Flow diagram", for: "Processes, cycles, cause and effect", how: "Steps appear one at a time with arrows drawing between them, as a sequence, a loop or a branching tree." },
  title: { name: "Kinetic type", for: "Hooks, numbers, definitions", how: "One strong line, set in type that lands word by word on the beat. Always available as a safe fallback." },
  character: { name: "Presenter", for: "Human moments, experts, the person the story follows", how: "One real-looking person, cast once and filmed like a documentary, with the same face in every beat." },
  image: { name: "Cinematic shots", for: "Places, objects, history, metaphor", how: "Photographic film stills in one consistent grade, with smooth camera moves, cut into two or three shots on long beats." },
  veo: { name: "Veo shots", for: "Hero moments with real motion", how: "Cinematic eight-second clips for at most two moments per video, with an automatic fallback if a clip is refused." },
};

const STEPS = [
  ["Tell it what to explain", "You", "A question, a lesson plan, an article or a PDF. Sources become the director's source of truth."],
  ["Storyboard", "Director agent", "Writes narration for the ear, beat by beat: hook first, one idea per scene, a payoff that closes the question."],
  ["Routing", "Director agent", "Sends each beat to the engine that can show it truthfully. Exact engines for facts, generative ones for mood."],
  ["Narration", "Gemini TTS", "Every beat is voiced first, so each visual is rendered to the real length of its sentence."],
  ["Render and self-check", "Engines", "Scenes render in parallel. Code-driven scenes are inspected by Gemini vision and repaired before you see them."],
  ["Edit one beat", "You + director", "Rewrite a line, switch an engine, or ask for 'simpler' or 'show it on a map'. Only that scene re-renders."],
  ["Finish and translate", "Assembler", "Lyria music bed, loudness to broadcast level, subtitles, and one-click versions in other languages."],
];

const VS: [string, string, string][] = [
  ["Numbers on screen", "Drawn by a diffusion model, often wrong", "Computed and typeset by code"],
  ["Maps", "Approximate coastlines, invented borders", "Natural Earth data, exact borders"],
  ["Math and graphs", "Pretty squiggles", "Real Manim animation of the actual function"],
  ["Changing one moment", "Re-roll the whole clip", "Edit or regenerate a single beat"],
  ["Length", "Seconds per clip", "Full narrated explainers, 1 to 6 minutes"],
  ["Languages", "Re-prompt and hope", "Same visuals, re-voiced in each language"],
];

const FAQ = [
  ["Is this just a video generator?", "No. Video generation is one of ten engines and is used sparingly. Most of an explainer is built by engines that cannot get facts wrong: code-driven math, real map data and typeset text."],
  ["Who is it for?", "Teachers turning a lesson into a video, creators running explainer channels, NGOs and newsrooms explaining a story in several languages, and anyone who learns better by watching."],
  ["Can I control what it makes?", "Every beat is editable: the line, the engine, the visual brief and the engine's own parameters. You can also just ask the director to rework a scene in plain words."],
  ["Which Google technology does it use?", "Gemini for directing, code and vision checks; Nano Banana for images and characters; Veo for video; Gemini TTS for narration; Lyria for music. The prototype runs on one server and is built to move to Cloud Run with media in Cloud Storage."],
];

export default function Landing() {
  return (
    <SiteShell>
      {/* hero */}
      <section className="mx-auto max-w-[1240px] px-5 pb-14 pt-14 sm:px-8 sm:pt-20">
        <div className="grid items-end gap-10 lg:grid-cols-[1.15fr_1fr]">
          <h1 className="text-[44px] font-medium leading-[1.02] tracking-[-0.035em] text-ink sm:text-[64px] lg:text-[76px] animate-rise">
            Explain it once.<br />Every beat finds<br />its engine.
          </h1>
          <div className="animate-rise [animation-delay:120ms]">
            <p className="max-w-[460px] text-[17px] leading-relaxed text-body">
              MitraField&apos;s director agent writes your explainer and sends each beat to the engine that can show it truthfully:
              exact math, real maps and hand-drawn sketches where accuracy matters, Veo and Nano Banana where mood does.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/new" className="inline-flex h-12 items-center gap-2 rounded-full bg-ink px-6 text-[15px] font-medium text-white hover:bg-ink-soft">
                Start a video <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/#watch" className="inline-flex h-12 items-center rounded-full border border-line-strong bg-white/60 px-6 text-[15px] font-medium text-ink hover:border-ink/40">
                Watch one
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section id="product" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 sm:px-8">
        <Reveal><Showcase /></Reveal>
      </section>

      {/* built on */}
      <section className="mx-auto max-w-[1240px] px-5 py-16 sm:px-8">
        <p className="text-center text-[13px] text-muted">Built on</p>
        <div className="mask-fade-x mt-5 overflow-hidden">
          <div className="flex w-max animate-marquee gap-14">
            {[...BUILT_ON, ...BUILT_ON].map((b, i) => (
              <span key={i} className="text-[20px] font-medium tracking-tight text-[#a3a099]">{b}</span>
            ))}
          </div>
        </div>
      </section>

      {/* engines */}
      <section id="engines" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-16 sm:px-8">
        <Reveal>
          <h2 className="text-[36px] font-medium leading-[1.05] tracking-[-0.03em] sm:text-[52px]">
            Ten engines, one director.<br /><span className="text-[#9b988f]">Exact where it matters.</span>
          </h2>
        </Reveal>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(ENGINE_COPY).map(([k, c], i) => {
            const s = ENGINES[k];
            return (
              <Reveal key={k} delay={i * 60}>
                <article className="group h-full overflow-hidden rounded-3xl border border-line bg-white">
                  <div className="relative aspect-video overflow-hidden bg-ink">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={`/showcase/${k}.jpg`} alt={c.name} className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]" />
                    <span className={`absolute left-3 top-3 rounded-full px-2.5 py-0.5 text-[11px] font-semibold backdrop-blur-md ${s.kind === "exact" ? "bg-good-bg/90 text-good" : "bg-white/85 text-body"}`}>
                      {s.kind === "exact" ? "Exact" : "Generated"}
                    </span>
                  </div>
                  <div className="p-5">
                    <div className="flex items-center gap-2.5">
                      <span className={`flex h-8 w-8 items-center justify-center rounded-xl text-white ${s.art}`}><s.icon className="h-4 w-4" /></span>
                      <h3 className="text-[16px] font-semibold tracking-tight">{c.name}</h3>
                    </div>
                    <p className="mt-3 text-[13px] font-medium text-ink">{c.for}</p>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-body">{c.how}</p>
                  </div>
                </article>
              </Reveal>
            );
          })}
          <Reveal delay={420} className="sm:col-span-2 lg:col-span-2">
            <article className="relative flex h-full min-h-[280px] flex-col justify-end overflow-hidden rounded-3xl p-6 text-white grain art-charcoal">
              <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-white/60">Plug-in engines</p>
              <p className="mt-2 text-[20px] font-medium leading-snug tracking-tight">A new visual style is one file.</p>
              <p className="mt-2 text-[13px] leading-relaxed text-white/70">Every engine shares one contract: plan the beat, render it to the exact length. The director discovers new engines automatically.</p>
            </article>
          </Reveal>
        </div>
      </section>

      {/* versus */}
      <section className="mx-auto max-w-[1240px] px-5 py-16 sm:px-8">
        <Reveal>
          <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
            <div>
              <h2 className="text-[32px] font-medium leading-[1.08] tracking-[-0.03em] sm:text-[40px]">Beautiful is easy.<br /><span className="text-[#9b988f]">Correct is the product.</span></h2>
              <p className="mt-4 max-w-sm text-[15px] leading-relaxed text-body">
                Text-to-video tools make gorgeous clips, but they cannot explain. A wrong number on screen is worse than no video at all.
              </p>
            </div>
            <div className="overflow-hidden rounded-3xl border border-line bg-white">
              <div className="grid grid-cols-[1fr_1fr_1fr] border-b border-line bg-panel px-5 py-3 text-[12px] font-semibold text-muted">
                <span /> <span>Text-to-video tools</span> <span className="text-ink">MitraField</span>
              </div>
              {VS.map(([k, a, b]) => (
                <div key={k} className="grid grid-cols-[1fr_1fr_1fr] gap-3 border-b border-line px-5 py-3.5 text-[13px] last:border-0">
                  <span className="font-medium text-ink">{k}</span>
                  <span className="flex gap-2 text-body"><Minus className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" />{a}</span>
                  <span className="flex gap-2 text-ink"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-good" />{b}</span>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </section>

      {/* how */}
      <section id="how" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-16 sm:px-8">
        <Reveal>
          <h2 className="text-[36px] font-medium leading-[1.05] tracking-[-0.03em] sm:text-[52px]">
            From a question to a finished video.<br /><span className="text-[#9b988f]">You only make the calls.</span>
          </h2>
        </Reveal>
        <Reveal delay={100}>
          <div className="mt-12 overflow-hidden rounded-3xl border border-line bg-white">
            {STEPS.map(([title, who, what], i) => (
              <div key={title} className="grid gap-2 border-b border-line px-6 py-5 last:border-0 sm:grid-cols-[48px_1fr_160px_2fr] sm:items-baseline sm:gap-6">
                <span className="font-mono text-[12px] text-muted">0{i + 1}</span>
                <span className="text-[15px] font-semibold tracking-tight">{title}</span>
                <span className="text-[12px] font-semibold text-bronze">{who}</span>
                <span className="text-[14px] leading-relaxed text-body">{what}</span>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      {/* watch */}
      <section id="watch" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-16 sm:px-8">
        <Reveal>
          <div className="relative overflow-hidden rounded-[28px] grain">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/art/sage.webp" alt="" className="absolute inset-0 h-full w-full object-cover" />
            <div className="relative grid gap-8 p-6 sm:p-10 lg:grid-cols-[0.75fr_1.25fr] lg:items-center">
              <div className="rounded-2xl bg-white/85 p-6 text-ink backdrop-blur-md">
                <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-olive">One prompt · no edits</p>
                <h2 className="mt-3 text-[30px] font-medium leading-[1.08] tracking-[-0.03em] sm:text-[38px]">The bottleneck of the world</h2>
                <p className="mt-3 max-w-sm text-[14px] leading-relaxed text-ink/75">
                  Nine beats across seven engines: a globe that knows where Hormuz is, a bar chart computed by code, a whiteboard sketch,
                  a recurring guide character and two Veo hero shots. Rendered unattended on a single small server.
                </p>
                <ul className="mt-5 space-y-1.5 text-[13px] text-ink/80">
                  {["Narration and visuals cut to the same beat", "Music bed ducked under the voice", "Subtitles exported alongside"].map((x) => (
                    <li key={x} className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-olive" />{x}</li>
                  ))}
                </ul>
              </div>
              <video src="/demo/hormuz.mp4" poster="/demo/hormuz.jpg" controls playsInline preload="none"
                className="w-full rounded-2xl bg-ink shadow-[0_30px_80px_-30px_rgba(20,30,10,0.55)]" />
            </div>
          </div>
        </Reveal>
      </section>

      {/* faq */}
      <section id="faq" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-16 sm:px-8">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          <h2 className="text-[32px] font-medium leading-[1.08] tracking-[-0.03em] sm:text-[40px]">Questions</h2>
          <div className="divide-y divide-line border-y border-line">
            {FAQ.map(([q, a]) => (
              <details key={q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[16px] font-medium tracking-tight">
                  {q}<Plus className="h-4 w-4 shrink-0 text-muted transition-transform group-open:rotate-45" />
                </summary>
                <p className="mt-3 max-w-2xl text-[14px] leading-relaxed text-body">{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* cta */}
      <section id="about" className="mx-auto max-w-[1240px] px-5 pb-24 pt-8 sm:px-8">
        <div className="relative overflow-hidden rounded-[28px] grain">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/art/dusk.webp" alt="" className="absolute inset-0 h-full w-full object-cover" />
          <div className="relative flex flex-col items-start gap-6 p-6 sm:flex-row sm:items-end sm:justify-between sm:p-10">
            <div className="rounded-2xl bg-white/85 px-6 py-5 backdrop-blur-md">
              <h2 className="text-[34px] font-medium leading-[1.05] tracking-[-0.03em] text-ink sm:text-[48px]">What should we explain?</h2>
              <p className="mt-2 text-[15px] text-ink/70">Built for the Google Cloud AI Builder Cup 2026.</p>
            </div>
            <Link href="/new" className="inline-flex h-12 items-center gap-2 rounded-full bg-ink px-6 text-[15px] font-medium text-white hover:bg-ink-soft">
              Start a video <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </SiteShell>
  );
}
