# MitraField: AI explainer-video workspace (AI Builder Cup 2026)

Product name: **MitraField**.
Prototype deadline: **2026-10-18**. Runs on the local server first, migrate to Google Cloud after.

## Pitch

Flow and Higgsfield make beautiful clips but cannot explain anything correctly.
MitraField is a **director agent that routes every beat of a story to the right engine**:
precise engines (Manim math, real-geography globe, whiteboard line art) where accuracy
matters, generative engines (Veo, Nano Banana) where mood matters. One workspace to go
from notes to a finished, narrated, multilingual explainer, long-form or 9:16 Short.

## Google stack (all via one Gemini API key now, Vertex AI later)

| Job | Model |
|---|---|
| Director / storyboard / engine planning / Manim code | Gemini 3.x Pro/Flash |
| Images, characters, whiteboard line art | Nano Banana (gemini-3.1-flash-image / gemini-3-pro-image) |
| Video shots | Veo 3.1 (fast) |
| Narration | Gemini TTS (gemini-3.8-flash-tts), optional local Johnny voice |
| Music bed | Lyria |
| Translation | Gemini (Cloud Translation after migration) |
| Later | Cloud Run (API + render jobs), Cloud Storage (assets), Firestore (projects), BigQuery (learn-mode analytics) |

The client lives in `backend/gemini.py`; flipping to Vertex is one flag (`STUDIO_VERTEX=1`).

## Data model

```
Project: id, title, topic, notes, audience, language, aspect (16:9 | 9:16),
         voice, look (preset), scenes[], render {status, path}
Scene:   id, narration, engine, brief (what the viewer sees), params (engine-specific),
         status (draft|queued|rendering|ready|error), duration, audio, clip, thumb, error
```

Stored as `data/projects/<id>/project.json` with assets beside it.

## Engine (style pack) interface

```python
class Engine:
    name, label, blurb          # blurb is what the director reads when routing
    def plan(scene, project) -> dict       # Gemini fills engine params from the brief
    def render(scene, project, duration, out_dir) -> Path   # mp4 of exactly `duration` s
```

Engines: `manim`, `globe`, `whiteboard`, `veo`, `image` (still + camera move), `character`,
`title` (always-safe fallback). Adding a style = dropping a file in `backend/engines/`.

## Pipeline

1. **Director**: topic + notes + uploads -> storyboard (scenes with narration, engine, brief).
2. Per scene: **TTS** (gives the real duration) -> **plan** -> **render** fitted to duration.
   Scenes render independently, so one can be edited and regenerated alone.
3. **Assemble**: concat clips + narration + Lyria bed (ducked low) + .srt subtitles.
4. **Translate**: re-voice the same storyboard in another language.

## Constraints

- Server has ~7.9 GB RAM shared with Docker services: render worker concurrency = 1.
- No em dashes in on-screen text. No text boxes/cards on screen. Flat dark background.
- Veo is expensive: director uses it for at most 2-3 hero shots per video.

## Day plan

- **Oct 13**: backend core: store, jobs, Gemini client, director, TTS, title + image + globe engines, assembler. CLI end-to-end.
- **Oct 14**: manim (Gemini code + retry + fallback), veo, whiteboard, character engines.
- **Oct 15**: workspace UI: sources canvas, storyboard cards, scene inspector, preview player, render queue.
- **Oct 16**: translate, Shorts aspect, music bed, learn mode / quiz, polish.
- **Oct 17**: demo projects, demo video, submission write-up, (Cloud Run deploy if time).
- **Oct 18**: buffer + submit.
