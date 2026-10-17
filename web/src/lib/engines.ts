import { BarChart3, CalendarRange, Clapperboard, GitFork, Globe2, Image as ImageIcon, PenLine, Sigma, Smile, Type, type LucideIcon } from "lucide-react";

export type EngineStyle = { color: string; art: string; icon: LucideIcon; kind: "exact" | "generated"; short: string };

export const ENGINES: Record<string, EngineStyle> = {
  title: { color: "#2a2a28", art: "art-charcoal", icon: Type, kind: "exact", short: "Kinetic type" },
  globe: { color: "#4f7f7a", art: "art-sea", icon: Globe2, kind: "exact", short: "Globe & maps" },
  manim: { color: "#33518a", art: "art-dusk", icon: Sigma, kind: "exact", short: "Math animation" },
  chart: { color: "#2f6b5e", art: "art-sea", icon: BarChart3, kind: "exact", short: "Data chart" },
  timeline: { color: "#855b2e", art: "art-bronze", icon: CalendarRange, kind: "exact", short: "Timeline" },
  flow: { color: "#5a4f8a", art: "art-dusk", icon: GitFork, kind: "exact", short: "Flow diagram" },
  whiteboard: { color: "#4a5a3f", art: "art-olive", icon: PenLine, kind: "exact", short: "Whiteboard" },
  image: { color: "#d08a4f", art: "art-bronze", icon: ImageIcon, kind: "generated", short: "Illustrated" },
  character: { color: "#8f7aa3", art: "art-dusk", icon: Smile, kind: "generated", short: "Guide character" },
  veo: { color: "#b4643c", art: "art-clay", icon: Clapperboard, kind: "generated", short: "Veo shot" },
};

export const engineStyle = (name: string): EngineStyle => ENGINES[name] ?? ENGINES.title;
