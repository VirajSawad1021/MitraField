# MitraField

Explainer-video workspace: a Gemini director agent writes the story and routes every beat to the
engine that can show it best. See `docs/SPEC.md` for the pitch, architecture and day plan.

## Run

```bash
cd ~/lab/AI_Content/aibuildercup
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8020     # API + built UI at http://<server>:8020
cd web && npm run dev                                             # UI hot-reload at :3000 (proxies /api to 8020)
cd web && NODE_ENV=production npx next build                      # rebuild the static UI served by 8020
.venv/bin/python cli.py "topic" short 16:9                        # headless end-to-end
```

Secrets: `.env` holds `GEMINI_API_KEY` (never commit). Narration uses the OmniVoice server at `STUDIO_OMNI_URL` (default `http://localhost:8002`) for the Johnny and Viraj v8 voices. `STUDIO_VERTEX=1` + `GOOGLE_CLOUD_PROJECT` switches to Vertex AI.

## Layout

```
backend/
  app.py          FastAPI: projects, sources, scenes, render, translate
  director.py     storyboard / rewrite-one-scene / translate (Gemini)
  pipeline.py     per-scene TTS -> plan -> render -> fit, assembly (music, loudnorm, .srt); hash-cached
  gemini.py       one client for text, JSON, Nano Banana, TTS, Veo, Lyria
  engines/        style packs, auto-registered (ENGINE = ...):
                  title, globe, manim, whiteboard, image, character, veo
web/              Next.js app: landing, new video, projects, studio workspace
data/projects/    project.json + all generated media per project
```

## Adding an engine

New file in `backend/engines/` with a class that sets `name/label/blurb/params_schema` and implements
`render(scene, project, duration, out_dir) -> mp4`. The director sees it automatically via `blurb`.
Set `heavy = False` for API-bound engines (they skip the single CPU render slot).
