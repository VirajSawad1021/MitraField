"""The director agent: sources -> storyboard, routing each beat to the right engine."""
import mimetypes
from pathlib import Path

from google.genai import types

from . import config, engines, gemini
from .models import Project, Scene

LENGTHS = {"short": "45-60 seconds TOTAL (about 130 spoken words), 7-9 scenes of 1-2 short sentences, hook in the first 2 seconds",
           "medium": "2-3 minutes (about 380 spoken words), 14-18 scenes",
           "long": "5-6 minutes (about 800 spoken words), 30-36 scenes"}

SYSTEM = """You are the director of an explainer-video studio. You write narration that sounds like a great
documentary narrator talking to one curious person, and you decide how every beat is SHOWN.

Story craft:
- Scene 1 is the hook: a surprising fact, question or image that creates a curiosity gap. No greetings, no "in this video".
- Build understanding step by step: concrete example before abstraction, one idea per scene.
- Every scene's narration is 1-3 spoken sentences (about 6-14 seconds). Write for the ear: short sentences, no lists, no parentheses.
- End with the payoff that closes the opening question, then one line that leaves the viewer thinking.
- Be factually careful. If the sources contain facts, prefer them over your memory.
- Never use em dashes.

Routing (the core of the product): pick the engine whose strengths match the beat.
- Precise engines (exact, never hallucinated): use them whenever correctness matters (numbers, math, geography, processes).
- Generative engines (images, video): use them for mood, setting, people, history, metaphor.
- Vary the look: avoid the same engine more than twice in a row.
- Text-only engines (title) are for short punchy beats only: one sentence, max 6 seconds.
- Math, physics, geometry, graphs, equations, algorithms, data: always a precise engine, never a generated image.
- Compared amounts or a trend over time go to chart; dated events go to timeline; processes, cycles and
  cause-and-effect chains go to flow (or whiteboard when a friendly sketch suits better).
- Video generation (veo) is expensive: use it for at most 2 hero moments, and NOT for scene 1 by default.
- The opening should fit the topic: a real place opens on the globe, a math idea on a striking manim visual,
  a human story on the character or an image. Do not follow a fixed template (e.g. hook shot then title card).

The brief for each scene describes concretely what the viewer SEES, in enough detail for a visual artist.

Cast & sets (visual consistency across the whole video):
- Define the recurring visual ingredients once: exactly 1 "style" (the art direction every generated shot
  shares, e.g. "warm painterly editorial illustration, soft natural light, muted earthy palette"), 0-2
  "character" (a recurring guide or the person the story follows), 0-3 "location", 0-2 "object".
- The main recurring subject (a ship, a building, a machine, a person the story follows) MUST be a cast item,
  as do places that are shown more than once. Define things that appear in 2+ generated beats, and the
  character used by the character engine.
- Names are short and human-readable, e.g. "RMS Titanic", "Captain Smith", "Engine room", "Painterly night".
- Descriptions are visual and specific (age, clothing, colours, materials, era), never abstract.
- Each scene lists the names of the cast items visible in it (generative engines only; empty for exact engines).

Engines:
{engines}
"""


BOARD_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "cast": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["style", "character", "location", "object"]},
            "name": {"type": "string"},
            "description": {"type": "string"}}, "required": ["kind", "name", "description"]}},
        "scenes": {"type": "array", "items": {"type": "object", "properties": {
            "narration": {"type": "string"},
            "engine": {"type": "string", "enum": None},
            "brief": {"type": "string"},
            "cast": {"type": "array", "items": {"type": "string"}}}, "required": ["narration", "engine", "brief"]}},
    },
    "required": ["title", "cast", "scenes"],
}


def engine_menu():
    return "\n".join(f"- {e.name}: {e.blurb}" for e in engines.REGISTRY.values())


def source_parts(p: Project):
    parts, notes = [], []
    for s in p.sources:
        if s.kind == "file" and s.path and Path(s.path).exists():
            mime = mimetypes.guess_type(s.path)[0] or "application/octet-stream"
            if mime.startswith(("image/", "application/pdf", "text/", "audio/", "video/")):
                parts.append(types.Part.from_bytes(data=Path(s.path).read_bytes(), mime_type=mime))
        if s.text:
            notes.append(f"[{s.name or s.kind}]\n{s.text}")
    return parts, "\n\n".join(notes)


def storyboard(p: Project) -> Project:
    schema = {**BOARD_SCHEMA}
    schema["properties"]["scenes"]["items"]["properties"]["engine"]["enum"] = list(engines.REGISTRY)
    parts, notes = source_parts(p)
    prompt = (f"Topic: {p.topic}\nAudience: {p.audience}\nNarration language: {p.language}\n"
              f"Format: {p.aspect} ({'vertical Short' if p.aspect == '9:16' else 'landscape video'}), length {LENGTHS[p.length]}.\n"
              + (f"\nSource notes from the user:\n{notes}\n" if notes else "")
              + ("\nAttached files are sources too.\n" if parts else "")
              + "\nWrite the storyboard.")
    sysmsg = SYSTEM.format(engines=engine_menu())
    board = gemini.json_call(prompt, schema=schema, model=config.MODEL_DIRECTOR, system=sysmsg, parts=parts)
    from . import cast as castmod
    p.title = board.get("title") or p.title
    ids = castmod.merge(p, board.get("cast") or [])
    p.scenes = [Scene(narration=s["narration"].replace("—", ", "), engine=s["engine"], brief=s["brief"],
                      cast=[ids[n.lower()] for n in s.get("cast", []) if n.lower() in ids])
                for s in board["scenes"]]
    return p


def rewrite_scene(p: Project, scene: Scene, instruction: str) -> Scene:
    """Edit one beat in context (e.g. 'make it simpler', 'show this on a map instead')."""
    ctx = "\n".join(f"{i + 1}. [{s.engine}] {s.narration}" for i, s in enumerate(p.scenes))
    schema = {"type": "object", "properties": {"narration": {"type": "string"},
                                               "engine": {"type": "string", "enum": list(engines.REGISTRY)},
                                               "brief": {"type": "string"}},
              "required": ["narration", "engine", "brief"]}
    prompt = (f"Storyboard so far:\n{ctx}\n\nRewrite this scene:\n[{scene.engine}] {scene.narration}\nBrief: {scene.brief}\n\n"
              f"Instruction from the user: {instruction}\nKeep it consistent with the scenes around it.")
    r = gemini.json_call(prompt, schema=schema, model=config.MODEL_DIRECTOR, system=SYSTEM.format(engines=engine_menu()))
    scene.narration, scene.engine, scene.brief = r["narration"].replace("—", ", "), r["engine"], r["brief"]
    scene.params = {}
    return scene


def translate(p: Project, language: str) -> list[str]:
    lines = [s.narration for s in p.scenes]
    schema = {"type": "object", "properties": {"lines": {"type": "array", "items": {"type": "string"}}}, "required": ["lines"]}
    r = gemini.json_call(
        f"Translate each narration line into natural spoken {language} for a documentary voice-over. "
        f"Keep numbers and names accurate. Return exactly {len(lines)} lines in order.\n\n"
        + "\n".join(f"{i + 1}. {l}" for i, l in enumerate(lines)),
        schema=schema, model=config.MODEL_DIRECTOR)
    out = r["lines"]
    if len(out) != len(lines):
        raise RuntimeError("translation line count mismatch")
    return out
