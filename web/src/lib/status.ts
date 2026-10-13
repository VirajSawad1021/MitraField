import type { Tone } from "@/components/ui";

export const statusTone = (s: string): [Tone, string] =>
  s === "done" ? ["good", "Ready"]
    : s === "error" ? ["bad", "Needs attention"]
    : s === "storyboard" || s === "idle" ? ["neutral", "Storyboard"]
    : s === "directing" ? ["info", "Directing"]
    : s === "assembling" ? ["warn", "Assembling"]
    : ["warn", "Rendering"];

export const PROJECT_BUSY = ["directing", "rendering scenes", "assembling"];
export const SCENE_BUSY = ["queued", "rendering"];
