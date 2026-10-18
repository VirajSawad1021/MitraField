/* Demo content for /demo. Every number here comes from a real run on the prototype server. */

export type Demo = {
  id: string; tab: string; prompt: string; aspect: "16:9" | "9:16"; video: string; poster: string;
  beats: number; exact: number; length: string; route: string[]; voice: string; renderTime: string; note: string;
};

export const DEMOS: Demo[] = [
  {
    id: "0846ab6934", tab: "Geography · Hormuz", aspect: "16:9",
    prompt: "Why does a tiny strip of water called the Strait of Hormuz matter to the whole world?",
    video: "/demo/hormuz.mp4", poster: "/demo/hormuz.jpg",
    beats: 9, exact: 5, length: "0:49", voice: "Johnny", renderTime: "about 8 minutes",
    route: ["title", "globe", "veo", "whiteboard", "manim", "character", "globe", "veo", "image"],
    note: "A geography story, so the director leaned on the real-data globe: Iran, Oman and the bypass pipelines are drawn from Natural Earth, and the 21 million barrels a day is a bar chart computed by code.",
  },
  {
    id: "a834483018", tab: "Math · Fourier", aspect: "16:9",
    prompt: "What is a Fourier transform, really?",
    video: "/demo/fourier.mp4", poster: "/demo/fourier.jpg",
    beats: 8, exact: 4, length: "0:43", voice: "Johnny", renderTime: "about 4 minutes",
    route: ["whiteboard", "title", "image", "manim", "manim", "character", "veo", "image"],
    note: "A math idea, so the core is Manim: a real tangled wave pulled apart into its sine components, then turned side-on into frequency spikes. The cake-unbaking analogy is a whiteboard sketch, and Veo carries the MRI payoff.",
  },
  {
    id: "ade6d28b73", tab: "Biology · Short", aspect: "9:16",
    prompt: "How does a vaccine teach your body to fight a virus?",
    video: "/demo/vaccine.mp4", poster: "/demo/vaccine.jpg",
    beats: 9, exact: 5, length: "0:54", voice: "Johnny", renderTime: "about 9 minutes",
    route: ["image", "scene", "character", "manim", "whiteboard", "image", "veo", "manim", "character"],
    note: "A vertical Short in the Editorial flat look. An immunologist presenter, Dr. Lena Park, is defined once in the cast and appears consistently; a code-drawn motion scene shows the immune system starting from scratch, and Manim plots the antibody surge. Charts, sketches and Manim all switch to the look's paper palette.",
  },
  {
    id: "23aebfb0d5", tab: "History · Cast & Sets", aspect: "16:9",
    prompt: "Why did the Titanic sink?",
    video: "/demo/titanic.mp4", poster: "/demo/titanic.jpg",
    beats: 8, exact: 4, length: "0:48", voice: "Johnny", renderTime: "about 9 minutes including drawing the cast",
    route: ["image", "manim", "veo", "whiteboard", "character", "manim", "veo", "title"],
    note: "The director defined a cast with the storyboard: the RMS Titanic, a 1912 shipbuilder called Thomas who presents, and one moody historical style. Every still and both Veo shots were drawn from those references, so the same ship appears throughout. The compartments are Manim, the flooding chain a whiteboard sketch.",
  },
  {
    id: "790e11f67a", tab: "Woodblock look", aspect: "16:9",
    prompt: "How does a tsunami form, and why is it so different from a normal wave?",
    video: "/demo/tsunami.mp4", poster: "/demo/tsunami.jpg",
    beats: 7, exact: 5, length: "0:46", voice: "Johnny", renderTime: "about 7 minutes",
    route: ["title", "scene", "manim", "globe", "image", "manim", "veo"],
    note: "The Woodblock look carries through every engine: kinetic type, a code-drawn motion scene, Manim and the globe all render on paper in the print palette, and the still and the Veo wave are drawn in the same style. Draft mode, about one dollar.",
  },
  {
    id: "d78bf2a264", tab: "Hindi translation", aspect: "16:9",
    prompt: "Translate: The Bottleneck of the World",
    video: "/demo/hormuz_hi.mp4", poster: "/demo/hormuz_hi.jpg",
    beats: 9, exact: 5, length: "1:03", voice: "Johnny", renderTime: "a few minutes",
    route: ["title", "globe", "veo", "whiteboard", "manim", "character", "globe", "veo", "image"],
    note: "One click from the English Hormuz video. The director rewrote the narration for natural spoken Hindi, the same cloned narrator read it, and every on-screen label (animated text, map pins, the Manim chart) was re-rendered in Devanagari. Picture beats reused their finished shots, so nothing was regenerated.",
  },
];

export type Step = { title: string; who: string; body: string; points: string[]; shot: string; path: string };

export const STEPS: Step[] = [
  {
    title: "Ask a question", who: "You", path: "/new", shot: "/demo/steps/01_new.webp",
    body: "Type what you want explained and pick the format, length, language, narrator and audience. Notes, PDFs and images are optional sources the director treats as the truth.",
    points: ["Landscape video or vertical Short", "Your own cloned voice or a Gemini voice", "Nothing renders until you have seen the storyboard"],
  },
  {
    title: "The director writes and routes", who: "Director agent", path: "/studio", shot: "/demo/steps/03_storyboard.webp",
    body: "Gemini writes the narration scene by scene, hook first and one idea per scene, then picks the visual that can show each one truthfully.",
    points: ["Facts, numbers and maps are drawn from data and code", "Mood and metaphor go to Nano Banana and Veo, labelled AI-generated", "Veo is capped at two hero shots per video"],
  },
  {
    title: "Change any scene", who: "You", path: "/studio", shot: "/demo/steps/04_inspector.webp",
    body: "Click a scene to edit its line, switch the visual or describe what the viewer should see. Or just tell the director what you want, like 'simpler' or 'show it on a map', and it rewrites that scene in context.",
    points: ["Only the scenes you change are re-rendered", "Raw parameters for full control", "Drag scenes to reorder the story"],
  },
  {
    title: "Render, with a self-check", who: "Engines", path: "/studio", shot: "/demo/steps/05_rendering.webp",
    body: "Each scene is narrated first, so its visual is rendered to the exact length of the sentence. Scenes render in parallel; Gemini looks at the frames and repairs anything that overlaps.",
    points: ["Every narration line is transcribed and retaken if it drifts", "A failed scene falls back to a safe visual instead of breaking the video", "Generated stills and Veo shots are cached between renders"],
  },
  {
    title: "Watch and export", who: "Assembler", path: "/studio", shot: "/demo/steps/06_final.webp",
    body: "The scenes are joined with a Lyria music bed kept low under the voice, mastered to streaming loudness, and exported with subtitles and an invisible watermark.",
    points: ["MP4 plus an .srt subtitle file", "Music generated for the topic, ducked under narration", "-14 LUFS, ready for YouTube"],
  },
  {
    title: "Keep going", who: "Director agent", path: "/projects", shot: "/demo/steps/07_projects.webp",
    body: "Every video stays editable in Projects. Turn a topic into a vertical Short, or translate a finished video: the director rewrites the narration for natural speech and the visuals are reused.",
    points: ["One-click language versions", "Shorts and long-form from the same workspace", "Projects keep their sources, scenes and renders"],
  },
];
