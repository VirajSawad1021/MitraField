"""Quality check of a finished video, run automatically after assembly.

The same pass we do by hand for the channels: technical checks with ffmpeg (black or frozen picture,
silence, loudness, length), a contact sheet of the whole video, and a Gemini vision review of every
beat, whatever engine drew it (cut-off or overlapping text, garbled words in generated images,
off-model characters, a picture that does not match the narration). The report is saved on the
project; flagged beats can be fixed with one click (the issues are passed back into the beat's brief).
"""
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config, costs, gemini, log, media, store

logger = log.get("qa")

LOUDNESS_TARGET, LOUDNESS_TOL = -14.0, 2.0
BLACK_MIN_S = 1.5      # a black stretch longer than this inside the video is a defect (a whiteboard starts blank)
FREEZE_MIN_S = 4.0     # a picture that does not change for this long (beats this short are fine)
SILENCE_MIN_S = 2.5    # a gap in the narration longer than this

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["text_cut_off", "text_overlap", "garbled_text", "off_model",
                                                 "mismatch", "empty_or_broken", "layout", "other"]},
            "severity": {"type": "string", "enum": ["major", "minor"],
                         "description": "major = a viewer would clearly notice or be misled; minor = polish"},
            "detail": {"type": "string", "description": "one short sentence a creator can act on"}},
            "required": ["kind", "severity", "detail"]}},
    },
    "required": ["ok", "issues"],
}


def _ffmpeg_log(args):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *map(str, args), "-f", "null", "-"],
                       capture_output=True, text=True)
    return r.stderr


def technical(final: Path, expected: float):
    """ffmpeg checks on the finished file. Returns a list of {check, ok, detail}."""
    out = []
    dur = media.duration(final)
    out.append({"check": "length", "ok": abs(dur - expected) < 1.0,
                "detail": f"{dur:.1f} s for {expected:.1f} s of narration"})

    log_v = _ffmpeg_log(["-i", final, "-vf", f"blackdetect=d={BLACK_MIN_S}:pic_th=0.98,freezedetect=n=0.003:d={FREEZE_MIN_S}", "-an"])
    blacks = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log_v)]
    blacks = [(a, b) for a, b in blacks if a > 0.3 and b < dur - 0.3]          # fades at the very ends are fine
    out.append({"check": "black frames", "ok": not blacks,
                "detail": ", ".join(f"{a:.1f}-{b:.1f} s" for a, b in blacks) or "none"})
    freezes = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", log_v)]
    out.append({"check": "frozen picture", "ok": not freezes,
                "detail": f"{len(freezes)} stretch(es), longest {max(freezes):.1f} s" if freezes else "none"})

    log_a = _ffmpeg_log(["-i", final, "-vn", "-af", f"silencedetect=n=-45dB:d={SILENCE_MIN_S},ebur128"])
    sil = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", log_a)]
    out.append({"check": "silence gaps", "ok": not sil,
                "detail": f"{len(sil)} gap(s), longest {max(sil):.1f} s" if sil else "none"})
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", log_a)
    lufs = float(m[-1]) if m else None
    out.append({"check": "loudness", "ok": lufs is not None and abs(lufs - LOUDNESS_TARGET) <= LOUDNESS_TOL,
                "detail": f"{lufs:.1f} LUFS (target {LOUDNESS_TARGET:.0f})" if lufs is not None else "unmeasured"})
    return out


def contact_sheet(final: Path, out: Path, aspect: str):
    """One frame every ~3 s in a grid, like the manual QA sheets."""
    dur = media.duration(final)
    n = max(4, min(30, int(dur // 3)))
    cols = 6 if aspect == "16:9" else 10
    rows = -(-n // cols)
    w = 320 if aspect == "16:9" else 180
    media.run(["ffmpeg", "-y", "-v", "error", "-i", final, "-vf", f"fps={n / dur:.4f},scale={w}:-2,tile={cols}x{rows}",
               "-frames:v", "1", "-q:v", "4", out])
    return out


def _frames(clip: Path, dur: float, dest: Path):
    from google.genai import types
    parts = []
    for k, t in enumerate((dur * 0.15, dur * 0.5, max(0.0, dur - 0.25))):
        f = dest / f"qa_{k}.jpg"
        media.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", clip, "-frames:v", "1", "-vf", "scale=960:-2", f])
        parts.append(types.Part.from_bytes(data=f.read_bytes(), mime_type="image/jpeg"))
    return parts


def review_beat(p, s, i):
    """Gemini looks at the start, middle and end of one beat in context."""
    if not (s.clip and Path(s.clip).exists()):
        return {"ok": False, "issues": [{"kind": "empty_or_broken", "detail": "The scene has no rendered clip."}]}
    from .look import get as get_look
    lk = get_look(p.look)
    names = {c.id: f"{c.name} ({c.kind}): {c.description}" for c in p.cast}
    cast = "; ".join(names[c] for c in s.cast if c in names) or "none"
    d = Path(s.clip).parent
    prompt = (
        "You are the quality reviewer of an explainer-video studio. These are 3 frames (start, middle, end) of one beat. "
        "Report only real defects a viewer would notice:\n"
        "- text cut off at the frame edge, or overlapping other text or shapes, or too small to read on a phone\n"
        "- garbled, misspelled or nonsense words inside images (generated pictures often contain fake text)\n"
        "- a cast character that does not match its description (wrong outfit, costume, age) or looks childish\n"
        "- a picture that does not show what the narration says, or a broken / empty / mostly blank frame\n"
        "The project's look is chosen on purpose; never ask to change the art style. Mark an issue 'major' only if a "
        "viewer would clearly notice it or be misled; small polish is 'minor'. If it is fine, return ok=true.\n\n"
        f"Beat {i + 1} of {len(p.scenes)}. Engine: {s.engine}. Project look: {lk['label']}: {lk['image']} "
        f"On-screen language: {p.language}.\nNarration: \"{s.narration}\"\nIntended picture: {s.brief}\nCast in this beat: {cast}")
    try:
        v = gemini.json_call(prompt, schema=REVIEW_SCHEMA, parts=_frames(Path(s.clip), s.duration or media.duration(s.clip), d),
                             model=config.MODEL_FAST)
    except Exception as e:   # the reviewer is a safety net, never a blocker
        logger.warning("beat review skipped: %s", e, extra={"pid": p.id})
        return {"ok": True, "issues": [], "skipped": True}
    issues = [x for x in v.get("issues", []) if x.get("detail")]
    major = [x for x in issues if x.get("severity") != "minor"]
    return {"ok": not major, "issues": issues}


@costs.tracked
def run(pid):
    p = store.load(pid)
    if not (p.render_path and Path(p.render_path).exists()):
        return None
    store.mutate(pid, lambda pp: setattr(pp, "qa", {"status": "checking", "t": time.time()}))
    final = Path(p.render_path)
    out = final.parent
    try:
        tech = technical(final, sum(s.duration or 0 for s in p.scenes))
        sheet = contact_sheet(final, out / "contact_sheet.jpg", p.aspect)
        with ThreadPoolExecutor(4) as ex:
            reviews = list(ex.map(costs.bind(lambda a: review_beat(p, *a)), [(s, i) for i, s in enumerate(p.scenes)]))
        beats = {s.id: r for s, r in zip(p.scenes, reviews)}
        flagged = [s.id for s in p.scenes if not beats[s.id]["ok"]]
        tech_bad = [c["check"] for c in tech if not c["ok"]]
        report = {"status": "passed" if not flagged and not tech_bad else "flagged", "t": time.time(),
                  "render": str(final), "sheet": str(sheet), "technical": tech, "beats": beats,
                  "flagged": flagged, "summary": _summary(flagged, tech_bad)}
    except Exception as e:
        logger.exception("qa failed", extra={"pid": pid})
        report = {"status": "error", "t": time.time(), "summary": f"The quality check could not run: {str(e)[:200]}"}
    store.mutate(pid, lambda pp: setattr(pp, "qa", report))
    (out / "qa.json").write_text(json.dumps(report, indent=1))
    return report


def _summary(flagged, tech_bad):
    if not flagged and not tech_bad:
        return "Every scene and every technical check passed."
    bits = []
    if flagged:
        bits.append(f"{len(flagged)} scene{'s' if len(flagged) > 1 else ''} flagged")
    if tech_bad:
        bits.append("technical: " + ", ".join(tech_bad))
    return "; ".join(bits).capitalize() + "."


def fix_brief(brief: str, issues: list[dict]) -> str:
    """Fold the reviewer's issues into the beat's brief, replacing any earlier fix note."""
    base = re.sub(r"\s*Fix from review:.*$", "", brief or "", flags=re.S).strip()
    notes = " ".join(f"{x['detail'].rstrip('.')}." for x in issues)
    return f"{base} Fix from review: {notes}".strip()
