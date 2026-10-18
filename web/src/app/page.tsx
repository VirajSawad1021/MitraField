import Link from "next/link";
import { ArrowRight, Check, Mic, Minus, Plus, SearchCheck, ShieldCheck, Sparkles, Stamp } from "lucide-react";
import { SiteShell } from "@/components/marketing/Chrome";
import { Reveal } from "@/components/marketing/Reveal";
import { Showcase } from "@/components/marketing/Showcase";
import { ENGINES } from "@/lib/engines";
import { VoiceSamples } from "@/components/VoiceLab";

const LOOKS: [string, string, string][] = [
  ["cinematic", "Cinematic", "Photographic documentary realism, like a premium film series."],
  ["editorial", "Editorial flat", "Clean flat vector illustration, like a top explainer studio."],
  ["studio3d", "Premium 3D", "Polished stylised 3D, soft studio light, adult characters."],
  ["ink", "Ink & wash", "Hand-inked line with watercolour wash, like a quality newspaper."],
  ["motion", "Motion graphics", "Bold iconographic shapes, Swiss-design clean."],
  ["archival", "Archival", "Period photographs and engravings with authentic grain."],
  ["woodblock", "Woodblock", "Japanese woodblock print on aged paper: flat colour, fine line, calm."],
  ["collage", "Paper collage", "Paper cutouts, halftone dots and torn layers, crafted and tactile."],
  ["isometric", "Isometric", "Clean isometric 3D diagrams: systems, cities and machines explained."],
  ["blueprint", "Blueprint", "Technical line drawing on blueprint, precise and engineered."],
];

const BUILT_ON = ["Gemini 3.1 Pro", "Veo 3.1", "Nano Banana", "Lyria", "Gemini TTS", "Manim", "Natural Earth", "FastAPI", "Next.js", "Cloud Run"];

const ENGINE_COPY: Record<string, { for: string; how: string }> = {
  manim: { for: "Equations, graphs, geometry, algorithms", how: "Gemini writes Manim code for the exact narration length, renders it, then inspects the frames and repairs anything that overlaps." },
  globe: { for: "Places, routes, empires, migrations", how: "Natural Earth borders on a real orthographic globe. Camera flights, highlighted countries, pins and great-circle routes." },
  whiteboard: { for: "Processes, cause and effect, comparisons", how: "Nano Banana sketches clean line art, then MitraField draws it on stroke by stroke like a teacher at the board." },
  scene: { for: "Concepts, mechanisms, stylish chapter moments", how: "Gemini writes an animated HTML and SVG scene in the project's look: layered illustration, parallax and kinetic type, rendered frame-exact in headless Chrome." },
  chart: { for: "Comparisons, shares, rankings, trends", how: "Bars that grow and count up, or a line that draws the trend, from numbers taken from your sources. Every value is typeset by code." },
  timeline: { for: "History, discoveries, sequences", how: "A time axis draws in and each event lands at its real date. Crowded dates spread out evenly so labels stay readable." },
  flow: { for: "Processes, cycles, cause and effect", how: "Steps appear one at a time with arrows drawing between them, as a sequence, a loop or a branching tree." },
  title: { for: "Hooks, numbers, definitions", how: "One strong line, set in type that lands word by word with the voice. Always available as a safe fallback." },
  character: { for: "Human moments, experts, the person the story follows", how: "One real-looking person, cast once and filmed like a documentary, with the same face in every scene." },
  image: { for: "Places, objects, history, metaphor", how: "Photographic film stills in one consistent grade, with smooth camera moves, cut into two or three shots on long scenes." },
  veo: { for: "Hero moments with real motion", how: "Cinematic eight-second clips for at most two moments per video, with an automatic fallback if a clip is refused." },
};

const STEPS = [
  ["Tell it what to explain", "You", "A question, a lesson plan, an article or a PDF. Sources become the director's source of truth."],
  ["Storyboard", "Director agent", "Writes narration for the ear, scene by scene: hook first, one idea per scene, a payoff that closes the question."],
  ["Choosing visuals", "Director agent", "Picks the visual that can show each scene truthfully: data, maps and code for facts, AI imagery for mood."],
  ["Narration", "Your cloned voice", "Every scene is voiced first, in your cloned voice or a Gemini voice, so each visual is cut to the real length of its sentence."],
  ["Render and self-check", "Engines", "Scenes render in parallel. Gemini looks at every finished scene, flags problems and checks each claim against Google Search."],
  ["Edit one scene", "You + director", "Rewrite a line, switch the visual, or ask for 'simpler' or 'show it on a map'. Only that scene re-renders."],
  ["Finish and translate", "Assembler", "Lyria music bed, loudness to broadcast level, subtitles, an invisible watermark, and one-click versions in other languages."],
];

const VS: [string, string, string][] = [
  ["Numbers on screen", "Drawn by a diffusion model, often wrong", "Computed and typeset by code"],
  ["Maps", "Approximate coastlines, invented borders", "Natural Earth data, exact borders"],
  ["Math and graphs", "Pretty squiggles", "Real Manim animation of the actual function"],
  ["Changing one moment", "Re-roll the whole clip", "Edit or regenerate a single scene"],
  ["Length", "Seconds per clip", "Full narrated explainers, 1 to 6 minutes"],
  ["Languages", "Re-prompt and hope", "Same visuals, re-voiced in each language"],
  ["Narrator", "A stock voice", "Your own voice, cloned from 15 seconds"],
];

const FAQ = [
  ["Is this just a video generator?", "No. AI video is one of eleven kinds of visual and is used sparingly. Most of an explainer is built from data and code that cannot get facts wrong: real math, real map data and typeset text."],
  ["Who is it for?", "Teachers turning a lesson into a video, creators running explainer channels, NGOs and newsrooms explaining a story in several languages, and anyone who learns better by watching."],
  ["Can I control what it makes?", "Every scene is editable: the line, the kind of visual, what the viewer sees and the raw parameters. You can give the director instructions for the whole video, or ask it to rework one scene in plain words."],
  ["Which Google technology does it use?", "Gemini for directing, code, quality review and fact checks grounded in Google Search; Nano Banana for images and characters; Veo for video; Gemini TTS for narration; Lyria for music. It runs on Cloud Run with Firestore, Cloud Tasks and Cloud Storage, and voice cloning runs on a Cloud Run GPU."],
];

export default function Landing() {
  return (
    <SiteShell>
      {/* hero */}
      <section className="mx-auto max-w-[1240px] px-5 pb-14 pt-14 sm:px-8 sm:pt-20">
        <div className="grid items-end gap-10 lg:grid-cols-[1.15fr_1fr]">
          <h1 className="text-[44px] font-medium leading-[1.02] tracking-[-0.035em] text-ink sm:text-[64px] lg:text-[76px] animate-rise">
            Ask a question.<br />Get a narrated<br />explainer video.
          </h1>
          <div className="animate-rise [animation-delay:120ms]">
            <p className="max-w-[460px] text-[17px] leading-relaxed text-body">
              An AI director writes the script and picks the right visual for every scene: real math, real maps and
              charts where accuracy matters, Veo and Nano Banana where mood does. Narrated in your own cloned voice, with one-click versions in other languages.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/new" className="inline-flex h-12 items-center gap-2 rounded-full bg-ink px-6 text-[15px] font-medium text-white hover:bg-ink-soft">
                Create video <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/#watch" className="inline-flex h-12 items-center rounded-full border border-line-strong bg-white/60 px-6 text-[15px] font-medium text-ink hover:border-ink/40">
                Watch an example
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
            Eleven kinds of visual, one director.<br /><span className="text-[#9b988f]">Real data where it matters.</span>
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
                    <img src={`/showcase/${k}.jpg`} alt={s.short} className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]" />
                    {s.kind === "generated" && (
                      <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-white/90 px-2.5 py-0.5 text-[11px] font-semibold text-[#6b4f8a] backdrop-blur-md">
                        <Sparkles className="h-3 w-3" />AI-generated
                      </span>
                    )}
                  </div>
                  <div className="p-5">
                    <div className="flex items-center gap-2.5">
                      <span className={`flex h-8 w-8 items-center justify-center rounded-xl text-white ${s.art}`}><s.icon className="h-4 w-4" /></span>
                      <h3 className="text-[16px] font-semibold tracking-tight">{s.short}</h3>
                    </div>
                    <p className="mt-3 text-[13px] font-medium text-ink">{c.for}</p>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-body">{c.how}</p>
                  </div>
                </article>
              </Reveal>
            );
          })}
        </div>
      </section>

      {/* voice cloning */}
      <section id="voice" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-16 sm:px-8">
        <Reveal>
          <div className="relative overflow-hidden rounded-[28px] p-6 text-white grain art-dusk sm:p-10">
            <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
              <div>
                <p className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-[12px] font-semibold"><Mic className="h-3.5 w-3.5" />Voice cloning</p>
                <h2 className="mt-4 text-[34px] font-medium leading-[1.05] tracking-[-0.03em] sm:text-[48px]">Narrated in your own voice.</h2>
                <p className="mt-4 max-w-md text-[15px] leading-relaxed text-white/75">
                  Record about 15 seconds of speech. Your voice is cloned once and narrates every video you make, including the
                  versions in other languages. A voice is only cloned after you confirm it is yours or you have permission.
                </p>
                <ol className="mt-6 space-y-2.5 text-[14px]">
                  {["Record or upload 15 seconds", "Confirm it is your voice", "Pick it as the narrator"].map((x, i) => (
                    <li key={x} className="flex items-center gap-3"><span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-[12px] font-semibold text-ink">{i + 1}</span>{x}</li>
                  ))}
                </ol>
                <Link href="/voices" className="mt-7 inline-flex h-12 items-center gap-2 rounded-full bg-white px-6 text-[15px] font-medium text-ink hover:bg-cream">
                  Clone your voice <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
              <div>
                <p className="mb-3 text-[13px] text-white/70">One cloned voice, two languages. Press play.</p>
                <VoiceSamples dark />
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* looks */}
      <section className="mx-auto max-w-[1240px] px-5 py-16 sm:px-8">
        <Reveal>
          <h2 className="text-[36px] font-medium leading-[1.05] tracking-[-0.03em] sm:text-[52px]">
            One story, ten looks.<br /><span className="text-[#9b988f]">Professional in every one.</span>
          </h2>
          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-body">
            Pick an art direction per project. Characters stay adult and on-model, nothing looks like cheap AI art,
            and every number and map stays correct whatever the look.
          </p>
        </Reveal>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {LOOKS.map(([id, label, blurb], i) => (
            <Reveal key={id} delay={i * 60}>
              <figure className="overflow-hidden rounded-3xl border border-line bg-white">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/looks/${id}.jpg`} alt={label} className="aspect-video w-full object-cover" />
                <figcaption className="px-5 py-4">
                  <p className="text-[15px] font-semibold tracking-tight">{label}</p>
                  <p className="mt-0.5 text-[13px] text-body">{blurb}</p>
                </figcaption>
              </figure>
            </Reveal>
          ))}
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

      {/* trust */}
      <section id="trust" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-16 sm:px-8">
        <Reveal>
          <h2 className="text-[36px] font-medium leading-[1.05] tracking-[-0.03em] sm:text-[52px]">
            Checked before you see it.<br /><span className="text-[#9b988f]">Provable after you share it.</span>
          </h2>
        </Reveal>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {([
            [SearchCheck, "Fact check", "Every number and claim is checked against your sources and Google Search, with the evidence linked. Wrong claims are flagged scene by scene."],
            [ShieldCheck, "Quality check", "Gemini watches every finished scene for overlapping text, wrong pictures and broken frames, and the sound and picture are measured."],
            [Stamp, "Invisible watermark", "Every export carries a mark you cannot see. Anyone can upload a copy on the Verify page to check it came from mitrafield."],
          ] as const).map(([Icon, t, d], i) => (
            <Reveal key={t} delay={i * 80}>
              <article className="h-full rounded-3xl border border-line bg-white p-6">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-good-bg text-good"><Icon className="h-5 w-5" /></span>
                <h3 className="mt-4 text-[17px] font-semibold tracking-tight">{t}</h3>
                <p className="mt-2 text-[14px] leading-relaxed text-body">{d}</p>
                {t === "Invisible watermark" && <Link href="/verify" className="mt-3 inline-flex items-center gap-1 text-[13px] font-semibold text-ink underline underline-offset-2">Verify a video <ArrowRight className="h-3.5 w-3.5" /></Link>}
              </article>
            </Reveal>
          ))}
        </div>
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
                  Nine scenes and seven kinds of visual: a globe that knows where Hormuz is, a bar chart computed by code, a whiteboard sketch,
                  a recurring presenter and two Veo hero shots, narrated by a cloned voice. Rendered unattended.
                </p>
                <ul className="mt-5 space-y-1.5 text-[13px] text-ink/80">
                  {["Narration and visuals cut to the same moment", "Music bed ducked under the voice", "Subtitles exported alongside"].map((x) => (
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
              Create video <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </SiteShell>
  );
}
