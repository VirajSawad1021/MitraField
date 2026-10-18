"""Motion scenes: Gemini writes an animated HTML/SVG scene for the beat's exact duration, and we
render it frame-exact in headless Chromium by seeking every animation to each frame's time.
Layered illustration, icons, parallax, cards and kinetic type, all drawn by code in the project's look."""
import re
import subprocess

from .. import config, gemini, log, media
from ..look import get as get_look, palette
from .base import Engine

RULES = """Write ONE self-contained HTML document that is a single animated motion-graphics shot for an explainer video.

Hard rules:
- Canvas: exactly {w}x{h} px. Put everything inside <div id="stage"> sized {w}x{h}, overflow hidden. No scrollbars.
- Total length {dur:.1f} s. Animate ONLY with CSS @keyframes (animation-delay / animation-duration / fill-mode both)
  or the Web Animations API. NO setTimeout, setInterval, requestAnimationFrame or random numbers: the renderer pauses
  every animation and seeks it to exact times, so anything else will not move.
- Pace the visuals to the narration: something appears within 0.4 s, then build step by step as the words say it.
  Keep gentle continuous motion (slow camera drift, parallax layers, floating elements) so it is never static.
- Draw with inline SVG and CSS shapes only. No external images, fonts, scripts or network requests.
- Fonts: font-family "Inter" for text, "Fraunces" for big headlines (both installed). Max ~8 words per text element,
  font-size >= {minfont}px. On-screen text supports the narration, it does not repeat it.
- Art direction ({look}): {image}
- Palette (use these, plus tints of them): background {bg}, main ink {ink}, muted {muted}, accent {accent}, second accent {accent2}.
  {paper}
- Make it a real, specific explanation of the beat (the actual objects, process, comparison or numbers), composed
  like a premium motion-design studio would: layered depth, clear focal point, eased motion (cubic-bezier), no clutter.
- Scale: the main subject is LARGE, filling roughly 60-80% of the frame, centred on the focal point. No tiny
  diagrams floating in empty space.
- Text sits directly on the scene: NO boxes, cards, pills, panels or borders around text.
- No em dashes. No logos. No borders around the whole frame.
Return only the HTML document, starting with <!doctype html>."""


def strip_html(s):
    m = re.search(r"```(?:html)?\n(.*?)```", s, re.S)
    s = (m.group(1) if m else s).strip()
    i = s.lower().find("<!doctype")
    return s[i:] if i >= 0 else s


logger = log.get("scene")


class SceneEngine(Engine):
    name = "scene"
    label = "Motion scene"
    precise = True
    heavy = True
    blurb = ("Code-drawn motion graphics: an animated layered illustration built from SVG shapes, icons, cards and "
             "kinetic type in the project's look, with parallax and smooth camera drift. Use for concepts, systems, "
             "comparisons, step-by-step mechanisms and stylish chapter moments. Exact text and numbers.")

    def plan(self, scene, project):
        return {"approach": scene.brief}

    def _ask(self, scene, project, dur, extra=""):
        W, H = self.size(project)
        lk, pal = get_look(project.look), palette(project.look)
        paper = ("Give the background a subtle paper texture (an SVG feTurbulence noise filter at low opacity)."
                 if pal["paper"] else "Keep the background flat.")
        prompt = (RULES.format(w=W, h=H, dur=dur, minfont=34 if W > H else 40, look=lk["label"], image=lk["image"],
                               paper=paper, **{k: pal[k] for k in ("bg", "ink", "muted", "accent", "accent2")})
                  + f"\n\nVideo topic: {project.topic}\nNarration for this shot ({dur:.1f} s):\n\"{scene.narration}\"\n"
                  f"What the viewer should see: {scene.params.get('approach') or scene.brief}\n"
                  f"On-screen text language: {project.language}\n{extra}")
        return strip_html(gemini.text(prompt, model=config.MODEL_CODE))

    def _render(self, html, project, duration, out_dir):
        """Seek-render every frame with Playwright; returns (mp4, problems)."""
        from playwright.sync_api import sync_playwright
        W, H = self.size(project)
        page_file = out_dir / "scene.html"
        page_file.write_text(html)
        n = max(1, int(round(duration * config.FPS)))
        out = out_dir / "clip.mp4"
        errors = []
        for crash_try in range(2):   # a browser crash is not the model's fault: retry the same page once
            ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(config.FPS), "-c:v", "mjpeg",
                                   "-i", "-", "-vf", f"scale={W}:{H},format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
                                   "-crf", "18", str(out)], stdin=subprocess.PIPE)
            try:
                with sync_playwright() as p:
                    # /dev/shm is tiny in containers (Cloud Run too); without this Chromium crashes mid-render
                    b = p.chromium.launch(args=["--disable-dev-shm-usage", "--disable-gpu"])
                    try:
                        pg = b.new_page(viewport={"width": W, "height": H})
                        pg.on("pageerror", lambda e: errors.append(str(e)))
                        pg.route("http*://**", lambda r: r.abort())   # self-contained only
                        pg.goto(page_file.resolve().as_uri())
                        pg.wait_for_timeout(300)
                        count = pg.evaluate("document.getAnimations().length")
                        for f in range(n):
                            t = f / config.FPS * 1000
                            pg.evaluate("t => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = t; } "
                                        "if (window.seek) window.seek(t / 1000); }", t)
                            ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
                    finally:
                        b.close()
                ff.stdin.close()
                ff.wait()
                break
            except Exception as e:
                ff.kill()
                ff.wait()
                logger.warning("browser pass %d failed: %s", crash_try + 1, str(e)[:200])
                if crash_try == 1:
                    raise
                errors.clear()
        problems = list(errors)
        if count == 0 and "window.seek" not in html:
            problems.append("The page has no CSS or Web Animations, so nothing moves. Animate with @keyframes.")
        return out, problems

    def _critique(self, clip, scene, duration):
        from google.genai import types
        frames = []
        for k, t in enumerate((duration * 0.2, duration * 0.55, max(0, duration - 0.3))):
            f = clip.parent / f"qa_{k}.jpg"
            media.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", clip, "-frames:v", "1", "-vf", "scale=960:-2", f])
            frames.append(types.Part.from_bytes(data=f.read_bytes(), mime_type="image/jpeg"))
        v = gemini.json_call(
            "Three frames from a motion-graphics shot. Flag only real defects: overlapping or cut-off text, unreadably "
            "small text, empty or broken frames, elements off-canvas, or nothing changing between frames. "
            f"Narration: \"{scene.narration}\"",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}, "problems": {"type": "string"}},
                    "required": ["ok", "problems"]}, parts=frames, model=config.MODEL_FAST)
        return v.get("ok", True), v.get("problems", "")

    def render(self, scene, project, duration, out_dir):
        code_f = out_dir / "scene_final.html"
        html = code_f.read_text() if code_f.exists() else self._ask(scene, project, duration)
        for attempt in range(3):
            clip, problems = self._render(html, project, duration, out_dir)
            logger.info("attempt %d: %s", attempt + 1, "ok" if not problems else problems[0][:120])
            if not problems and attempt == 0:
                try:
                    ok, issue = self._critique(clip, scene, duration)
                except Exception:
                    ok, issue = True, ""
                logger.info("critique ok=%s %s", ok, issue[:120])
                if not ok and issue:
                    problems = [issue]
            if not problems:
                code_f.write_text(html)
                return clip
            html = self._ask(scene, project, duration,
                             f"\nA previous version had these problems, fix them:\n{chr(10).join(problems)[:1500]}\n\nPrevious HTML:\n{html[:12000]}")
        code_f.write_text(html)
        return clip   # best effort: the last render


ENGINE = SceneEngine()
