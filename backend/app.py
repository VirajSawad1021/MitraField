"""HTTP API for the workspace UI."""
import shutil
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import cast, config, director, engines, jobs, pipeline, store, tts
from .models import CastItem, Project, Scene, Source

app = FastAPI(title="MitraField")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def get(pid):
    try:
        return store.load(pid)
    except FileNotFoundError:
        raise HTTPException(404, "project not found")


def media_url(p: Project):
    d = p.model_dump()
    root = str(config.DATA)
    def u(x):
        return f"/files/{Path(x).relative_to(root)}" if x and str(x).startswith(root) else None
    for s in d["scenes"]:
        s["clip_url"], s["thumb_url"], s["audio_url"] = u(s["clip"]), u(s["thumb"]), u(s["audio"])
    d["render_url"] = u(d["render_path"])
    for c in d["cast"]:
        c["image_url"] = u(c["image"])
    d["character_url"] = u(str(config.DATA / p.id / "character.png")) if (config.DATA / p.id / "character.png").exists() else None
    return d


@app.get("/api/meta")
def meta():
    return {"engines": [e.info() for e in engines.REGISTRY.values()], "voices": tts.VOICES, "channel_voices": list(tts.OMNI_VOICES), "default_voice": tts.DEFAULT_VOICE,
            "models": {"director": config.MODEL_DIRECTOR, "code": config.MODEL_CODE, "image": config.MODEL_IMAGE,
                       "video": config.MODEL_VEO, "voice": f"OmniVoice clones + {config.MODEL_TTS}", "music": config.MODEL_MUSIC}}


def _cover(p):
    """Prefer a picture beat (Veo, illustration, character, globe) over a title card."""
    root = str(config.DATA)
    thumbs = [s for s in p.get("scenes", []) if s.get("thumb") and str(s["thumb"]).startswith(root)]
    rank = {"veo": 0, "image": 1, "character": 2, "globe": 3}
    if not thumbs:
        return None
    best = min(thumbs, key=lambda s: rank.get(s["engine"], 9))
    return f"/files/{Path(best['thumb']).relative_to(root)}"


@app.get("/api/projects")
def projects():
    return [{k: p.get(k) for k in ("id", "title", "topic", "aspect", "language", "updated", "render_status")}
            | {"scenes": len(p.get("scenes", [])), "cover": _cover(p),
               "duration": round(sum(s.get("duration") or 0 for s in p.get("scenes", [])), 1),
               "engines": sorted({s["engine"] for s in p.get("scenes", [])})}
            for p in store.list_all()]


class NewProject(BaseModel):
    topic: str
    audience: str = "curious general audience"
    language: str = "English"
    aspect: str = "16:9"
    length: str = "medium"
    voice: str = tts.DEFAULT_VOICE
    notes: str = ""


@app.post("/api/projects")
def create(body: NewProject):
    p = Project(title=body.topic[:60] or "Untitled", topic=body.topic, audience=body.audience, language=body.language,
                aspect=body.aspect, length=body.length, voice=body.voice)
    if body.notes.strip():
        p.sources.append(Source(kind="note", name="Notes", text=body.notes))
    store.save(p)
    return media_url(p)


@app.get("/api/projects/{pid}")
def read(pid: str):
    return media_url(get(pid))


@app.patch("/api/projects/{pid}")
def update(pid: str, body: dict):
    allowed = {"title", "topic", "audience", "language", "aspect", "length", "voice", "music", "pace"}
    get(pid)
    return media_url(store.mutate(pid, lambda p: [setattr(p, k, v) for k, v in body.items() if k in allowed]))


@app.delete("/api/projects/{pid}")
def delete(pid: str):
    get(pid)
    shutil.rmtree(config.DATA / pid)
    return {"ok": True}


@app.post("/api/projects/{pid}/sources")
async def add_source(pid: str, file: UploadFile | None = File(None), text: str = "", name: str = ""):
    get(pid)
    if file:
        d = store.pdir(pid) / "sources"
        d.mkdir(exist_ok=True)
        dest = d / f"{int(time.time())}_{Path(file.filename).name}"
        dest.write_bytes(await file.read())
        src = Source(kind="file", name=file.filename, path=str(dest))
    else:
        src = Source(kind="note", name=name or "Note", text=text)
    return media_url(store.mutate(pid, lambda p: p.sources.append(src)))


@app.delete("/api/projects/{pid}/sources/{sid}")
def del_source(pid: str, sid: str):
    return media_url(store.mutate(pid, lambda p: setattr(p, "sources", [s for s in p.sources if s.id != sid])))


def _storyboard(pid):
    store.mutate(pid, lambda p: setattr(p, "render_status", "directing"))
    try:
        p = director.storyboard(store.load(pid))
        p.render_status = "storyboard"
        store.save(p)
        jobs.submit(f"cast {pid}", cast.ensure, pid)   # reference images are ready before the first render
    except Exception as e:
        store.mutate(pid, lambda p: (setattr(p, "render_status", "error"), setattr(p, "render_error", str(e)[:400])))
        raise


@app.post("/api/projects/{pid}/storyboard")
def storyboard(pid: str):
    get(pid)
    jobs.submit(f"storyboard {pid}", _storyboard, pid)
    return media_url(store.mutate(pid, lambda p: setattr(p, "render_status", "directing")))


class SceneEdit(BaseModel):
    narration: str | None = None
    engine: str | None = None
    brief: str | None = None
    params: dict | None = None
    cast: list[str] | None = None


# ------------------------------------------------------------------ cast & sets

class CastEdit(BaseModel):
    kind: str | None = None
    name: str | None = None
    description: str | None = None


@app.post("/api/projects/{pid}/cast")
def add_cast(pid: str, body: CastEdit):
    item = CastItem(kind=body.kind or "character", name=body.name or "New", description=body.description or "")
    store.mutate(pid, lambda p: p.cast.append(item))
    jobs.submit(f"cast {item.id}", cast.generate, pid, item.id)
    return media_url(store.mutate(pid, lambda p: cast._set(p, item.id, status="generating")))


@app.patch("/api/projects/{pid}/cast/{cid}")
def edit_cast(pid: str, cid: str, body: CastEdit):
    changes = body.model_dump(exclude_none=True)
    p = get(pid)
    old = next((c for c in p.cast if c.id == cid), None)
    if not old:
        raise HTTPException(404, "cast item not found")
    redraw = "description" in changes and changes["description"] != old.description
    store.mutate(pid, lambda pp: cast._set(pp, cid, **changes))
    if redraw:
        jobs.submit(f"cast {cid}", cast.generate, pid, cid)
    return media_url(get(pid))


@app.post("/api/projects/{pid}/cast/{cid}/generate")
def regen_cast(pid: str, cid: str):
    jobs.submit(f"cast {cid}", cast.generate, pid, cid)
    return media_url(store.mutate(pid, lambda p: cast._set(p, cid, status="generating")))


@app.post("/api/projects/{pid}/cast/generate")
def gen_all_cast(pid: str):
    jobs.submit(f"cast all {pid}", cast.ensure, pid)
    return media_url(get(pid))


@app.delete("/api/projects/{pid}/cast/{cid}")
def del_cast(pid: str, cid: str):
    def f(p):
        p.cast = [c for c in p.cast if c.id != cid]
        for s in p.scenes:
            s.cast = [x for x in s.cast if x != cid]
    return media_url(store.mutate(pid, f))


@app.patch("/api/projects/{pid}/scenes/{sid}")
def edit_scene(pid: str, sid: str, body: SceneEdit):
    def f(p):
        s = store.scene(p, sid)
        for k, v in body.model_dump(exclude_none=True).items():
            setattr(s, k, v)
        if body.engine is not None or body.brief is not None:
            if body.params is None:
                s.params = {}
        s.status = "draft"
    return media_url(store.mutate(pid, f))


@app.post("/api/projects/{pid}/scenes")
def add_scene(pid: str, body: dict):
    after = body.get("after")
    sc = Scene(narration=body.get("narration", "New scene."), engine=body.get("engine", "title"), brief=body.get("brief", ""))

    def f(p):
        idx = next((i + 1 for i, s in enumerate(p.scenes) if s.id == after), len(p.scenes))
        p.scenes.insert(idx, sc)
    return media_url(store.mutate(pid, f))


@app.delete("/api/projects/{pid}/scenes/{sid}")
def del_scene(pid: str, sid: str):
    return media_url(store.mutate(pid, lambda p: setattr(p, "scenes", [s for s in p.scenes if s.id != sid])))


@app.post("/api/projects/{pid}/order")
def reorder(pid: str, body: dict):
    ids = body["ids"]

    def f(p):
        by = {s.id: s for s in p.scenes}
        p.scenes = [by[i] for i in ids if i in by] + [s for s in p.scenes if s.id not in ids]
    return media_url(store.mutate(pid, f))


def _rewrite(pid, sid, instruction):
    p = store.load(pid)
    s = director.rewrite_scene(p, store.scene(p, sid), instruction)
    s.status = "draft"
    store.mutate(pid, lambda pp: pp.scenes.__setitem__([x.id for x in pp.scenes].index(sid), s))
    pipeline.render_scene(pid, sid)


@app.post("/api/projects/{pid}/scenes/{sid}/rewrite")
def rewrite(pid: str, sid: str, body: dict):
    jobs.submit(f"rewrite {sid}", _rewrite, pid, sid, body.get("instruction", ""))
    pipeline.set_scene(pid, sid, status="queued")
    return media_url(get(pid))


@app.post("/api/projects/{pid}/scenes/{sid}/render")
def render_one(pid: str, sid: str, body: dict | None = None):
    force = bool((body or {}).get("force"))
    if (body or {}).get("replan"):
        pipeline.set_scene(pid, sid, params={})
    pipeline.set_scene(pid, sid, status="queued")
    jobs.submit(f"render {sid}", pipeline.render_scene, pid, sid, force)
    return media_url(get(pid))


@app.post("/api/projects/{pid}/render")
def render(pid: str):
    get(pid)
    jobs.submit(f"render all {pid}", pipeline.render_all, pid)
    return media_url(store.mutate(pid, lambda p: setattr(p, "render_status", "rendering scenes")))


@app.post("/api/projects/{pid}/assemble")
def assemble(pid: str):
    jobs.submit(f"assemble {pid}", pipeline.assemble, pid)
    return media_url(store.mutate(pid, lambda p: setattr(p, "render_status", "assembling")))


def _translate(pid, language):
    src = store.load(pid)
    lines = director.translate(src, language)
    p = src.model_copy(deep=True)
    from .models import new_id
    p.id, p.title, p.language = new_id(), f"{src.title} ({language})", language
    p.render_status, p.render_path = "rendering scenes", None
    old_ids = [s.id for s in p.scenes]
    for s, line in zip(p.scenes, lines):
        old = config.DATA / src.id / "scenes" / s.id
        new = new_id()
        if old.exists() and s.engine not in ("title", "manim", "globe"):   # reuse generated stills / Veo shots
            shutil.copytree(old, config.DATA / p.id / "scenes" / new, ignore=shutil.ignore_patterns("clip_*", "voice_*", "thumb_*"))
        s.id, s.narration, s.audio, s.clip, s.thumb, s.status, s.narration_hash = new, line, None, None, None, "queued", None
        if s.engine in ("title", "manim", "globe"):   # on-screen text must be re-planned in the new language
            s.params = {}
    store.save(p)
    pipeline.render_all(p.id)


@app.post("/api/projects/{pid}/translate")
def translate(pid: str, body: dict):
    jobs.submit(f"translate {pid}", _translate, pid, body["language"])
    return {"ok": True}


@app.get("/api/jobs")
def job_list():
    return jobs.recent()


app.mount("/files", StaticFiles(directory=str(config.DATA)), name="files")
dist = config.ROOT / "web" / "out"
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")
