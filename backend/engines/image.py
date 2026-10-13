"""Nano Banana stills + smooth camera moves. Long beats get 2-3 shots with crossfades,
so a still never sits on screen for more than ~6 s."""
from concurrent.futures import ThreadPoolExecutor

from .. import gemini, media
from .base import Engine
from .motion import MOVES, camera

STYLES = {
    "editorial": "cinematic editorial illustration, muted natural palette, soft directional light, painterly detail, no text",
    "photo": "photorealistic documentary photograph, natural light, 35mm, shallow depth of field, no text, no watermark",
    "atlas": "vintage atlas engraving, aged parchment, fine hatching, hand-tinted watercolor, no modern text",
    "diagram": "clean scientific illustration on a near-black background, thin precise lines, no text or labels",
    "3d": "clean stylised 3D render, soft studio lighting, dark seamless background, no text",
}
XF = 0.5   # crossfade seconds


def chain(clips, out, durs):
    """Crossfade-concatenate clips (each durs[i] long) into one."""
    if len(clips) == 1:
        return clips[0]
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for c in clips:
        cmd += ["-i", c]
    fc, prev, off = [], "[0:v]", 0.0
    for i in range(1, len(clips)):
        off += durs[i - 1] - XF
        lab = f"[x{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}{lab}")
        prev = lab
    cmd += ["-filter_complex", ";".join(fc), "-map", prev, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", out]
    media.run(cmd)
    return out


class ImageEngine(Engine):
    name = "image"
    heavy = False
    label = "Illustrated shots"
    blurb = ("Generated stills (photo, editorial illustration, vintage atlas, 3D) with slow camera moves, 1-3 shots "
             "per scene. Use to SHOW a place, object, kind of person, historical setting or metaphor. "
             "Not for exact numbers, diagrams with labels, or maps.")
    params_schema = {
        "type": "object",
        "properties": {
            "style": {"type": "string", "enum": list(STYLES)},
            "shots": {"type": "array", "description": "1 shot per ~5 seconds of narration, max 3", "items": {
                "type": "object", "properties": {
                    "prompt": {"type": "string", "description": "concrete composition: subject, setting, framing, mood. No text."},
                    "move": {"type": "string", "enum": MOVES}},
                "required": ["prompt", "move"]}},
        },
        "required": ["style", "shots"],
    }
    plan_guide = ("Shots should progress with the narration (e.g. wide establishing, then detail). "
                  "Keep the same style and visual world across shots. Never ask for written words or logos.")

    def render(self, scene, project, duration, out_dir):
        p = scene.params
        shots = (p.get("shots") or [{"prompt": p.get("prompt", scene.brief), "move": p.get("move", "push_in")}])[:3]
        n = max(1, min(len(shots), int(duration // 4.5) or 1))
        shots = shots[:n]
        style = STYLES.get(p.get("style"), STYLES["editorial"])

        def still(i):
            f = out_dir / f"still_{i}.png"
            if not f.exists():
                gemini.image(f"{shots[i]['prompt']}. Style: {style}.", f, aspect=project.aspect)
            return f

        with ThreadPoolExecutor(3) as ex:
            stills = list(ex.map(still, range(n)))
        each = (duration + XF * (n - 1)) / n
        durs = [each] * n
        clips = [camera(stills[i], out_dir / f"shot_{i}.mp4", durs[i], self.size(project), shots[i].get("move", "push_in"))
                 for i in range(n)]
        return chain(clips, out_dir / "clip.mp4", durs)


ENGINE = ImageEngine()
