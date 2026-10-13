"""Manim: Gemini writes the animation code, we render it, and errors or visual problems
are fed back for repair. Exact math, graphs, geometry, algorithms."""
import re
import subprocess

from .. import config, gemini, media
from .base import Engine

PREAMBLE = '''from manim import *
import numpy as np
config.background_color = "{bg}"
INK, MUTED, ACCENT, ACCENT2 = "{ink}", "{muted}", "{accent}", "{accent2}"
FONT = "Inter"
'''

RULES = """Write a Manim Community v0.21 scene.

Hard rules:
- Exactly one class named Beat(Scene) (or Beat(MovingCameraScene)). The preamble below is already imported; do not redefine it.
- Total animation time (sum of run_time values and self.wait calls) must be {dur:.1f} seconds. Pace the visuals to the narration:
  the first visual appears within 0.5 s, then build in step with what is being said. Never leave the screen static for more than 3 s; keep something gently moving.
- Frame is {fw:.1f} x {fh:.1f} units ({aspect}). Keep every object inside x in [-{hx:.1f}, {hx:.1f}], y in [-{hy:.1f}, {hy:.1f}].
- Background is near-black. Colors: INK (main), MUTED (secondary), ACCENT (orange highlight), ACCENT2 (blue). Use color with meaning.
- Text: Text(..., font=FONT). Math: MathTex. Max ~8 words per text line; on-screen text supports, never duplicates, the narration.
- NO boxes, cards, rectangles or frames around text. NO em dashes. No titles at the top saying the topic.
- Make it a real explanation: build the actual diagram, graph, equation, or geometry being described, with exact values.
- No external files, images, sounds, or network. No random without a fixed seed.
- Avoid overlapping objects: position with next_to / arrange / to_edge and leave space.
- Use the frame: the main diagram should be LARGE (spanning roughly 60-80% of the frame height), centered. Text font_size 34-48, at most one line at a time near the top or bottom.
- To change a caption, FadeOut the old Text and FadeIn the new one. Never Transform/ReplacementTransform one Text into a different Text (it garbles).
- Use stroke_width 3-5 for important lines so they read on a phone.
Return only the Python code for the class (no markdown fences, no preamble)."""


def strip_code(s):
    s = s.strip()
    m = re.search(r"```(?:python)?\n(.*?)```", s, re.S)
    return (m.group(1) if m else s).strip()


class ManimEngine(Engine):
    name = "manim"
    label = "Math animation"
    precise = True
    stretch_max = 1.0
    blurb = ("Code-driven animation (Manim): exact equations, graphs and plots, geometry, vectors, number lines, "
             "probability, physics diagrams, algorithms step by step. Use for anything quantitative or structural.")

    def frame(self, project):
        fh = 8.0 if project.aspect == "16:9" else 14.222
        fw = 14.222 if project.aspect == "16:9" else 8.0
        return fw, fh

    def plan(self, scene, project):
        return {"approach": scene.brief}   # code is written at render time, when the exact duration is known

    def _ask(self, scene, project, dur, extra=""):
        fw, fh = self.frame(project)
        prompt = (RULES.format(dur=dur, fw=fw, fh=fh, hx=fw / 2 - 0.4, hy=fh / 2 - 0.4, aspect=project.aspect)
                  + f"\n\nVideo topic: {project.topic}\nAudience: {project.audience}\n"
                  f"Narration for this scene ({dur:.1f} s):\n\"{scene.narration}\"\n"
                  f"What the viewer should see: {scene.params.get('approach') or scene.brief}\n"
                  f"On-screen text language: {project.language}\n{extra}")
        return strip_code(gemini.text(prompt, model=config.MODEL_CODE))

    def _render(self, code, project, out_dir):
        fw, fh = self.frame(project)
        W, H = self.size(project)
        pre = PREAMBLE.format(bg=config.BG, ink=config.INK, muted=config.MUTED, accent=config.ACCENT, accent2=config.ACCENT2)
        if project.aspect == "9:16":
            pre += "config.frame_width, config.frame_height = 8.0, 14.222\n"
        out_dir = out_dir.resolve()
        src = out_dir / "beat.py"
        src.write_text(pre + "\n" + code + "\n")
        media_dir = out_dir / "media"
        try:
            r = subprocess.run([config.MANIM_PY, "-m", "manim", "render", "-q", "l", "-r", f"{W},{H}", "--fps", str(config.FPS),
                                "--disable_caching", "--media_dir", str(media_dir), "-o", "beat.mp4", str(src), "Beat"],
                               capture_output=True, text=True, timeout=420, cwd=out_dir)
        except subprocess.TimeoutExpired:
            return None, "render timed out after 420 s; simplify the animation (fewer objects, no per-frame updaters on many objects)"
        vids = list(media_dir.rglob("beat.mp4"))
        if r.returncode or not vids:
            tail = (r.stderr or r.stdout)[-2500:]
            return None, tail
        return vids[0], None

    def _critique(self, clip, scene, dur):
        """Gemini looks at 3 frames and flags overlaps / cut-off text / empty screens."""
        from google.genai import types
        frames = []
        for k, t in enumerate((dur * 0.3, dur * 0.65, max(0, dur - 0.3))):
            f = clip.parent / f"qa_{k}.jpg"
            media.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", clip, "-frames:v", "1", "-vf", "scale=960:-2", f])
            frames.append(types.Part.from_bytes(data=f.read_bytes(), mime_type="image/jpeg"))
        verdict = gemini.json_call(
            "These are 3 frames from an explainer animation. Check for real defects only: text overlapping other text or "
            "shapes, text or objects cut off at the frame edge, unreadably small text, or a mostly empty frame. "
            f"Narration: \"{scene.narration}\"",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}, "problems": {"type": "string"}},
                    "required": ["ok", "problems"]},
            parts=frames, model=config.MODEL_FAST)
        return verdict.get("ok", True), verdict.get("problems", "")

    def render(self, scene, project, duration, out_dir):
        code_f = out_dir / "code.py"
        code = code_f.read_text() if code_f.exists() else self._ask(scene, project, duration)
        critiqued = False
        import time
        for attempt in range(4):
            t0 = time.time()
            clip, err = self._render(code, project, out_dir)
            print(f"[manim] attempt {attempt + 1}: {'ok' if clip else 'error'} in {time.time() - t0:.0f}s", flush=True)
            if clip and not critiqued:
                critiqued = True
                try:
                    ok, problems = self._critique(clip, scene, duration)
                    print(f"[manim] critique ok={ok} {problems[:120]}", flush=True)
                except Exception:
                    ok, problems = True, ""
                if not ok and problems:
                    fixed = self._ask(scene, project, duration,
                                      f"\nA previous version had these visual problems, fix them:\n{problems}\n\nPrevious code:\n{code}")
                    clip2, err2 = self._render(fixed, project, out_dir)
                    if clip2:
                        code, clip = fixed, clip2
                    else:
                        clip, err = self._render(code, project, out_dir)
            if clip:
                code_f.write_text(code)
                return clip
            code = self._ask(scene, project, duration,
                             f"\nThe previous code failed. Fix it.\nError:\n{err}\n\nPrevious code:\n{code}")
        raise RuntimeError(f"manim failed after retries: {err[-300:] if err else ''}")


ENGINE = ManimEngine()
