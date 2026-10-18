"""HTTP API for the workspace UI.

STUDIO_ROLE decides what this process serves: `api` (public routes, never renders), `worker`
(private /internal/tasks only, renders) or `all` (local development, both).
"""
import hmac
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import cast, config, costs, engines, jobs, log, pipeline, store, tasks, tts, voices  # noqa: F401  (tasks registers the handlers)
from .models import CastItem, Project, Scene, Source

log.setup()
logger = log.get("api")

@asynccontextmanager
async def lifespan(_app):
    recover_after_restart()
    yield


app = FastAPI(title="MitraField", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o for o in os.environ.get("STUDIO_CORS", "*").split(",") if o],
                   allow_methods=["*"], allow_headers=["*"])

PASSCODE = os.environ.get("STUDIO_PASSCODE", "")
PID = re.compile(r"^[0-9a-f]{10}$")


@app.middleware("http")
async def guard_writes(request: Request, call_next):
    """On a public deployment, anyone can browse; generating or editing needs the passcode
    (every write can spend money)."""
    if PASSCODE and request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
        if not hmac.compare_digest(request.headers.get("x-studio-pass", "").encode(), PASSCODE.encode()):
            return JSONResponse({"detail": "passcode required"}, status_code=401)
    return await call_next(request)


def valid_pid(request: Request):
    """Every route that names a project: ids are 10 hex chars, so a path can never escape the data dir."""
    pid = request.path_params.get("pid")
    if pid is not None and not PID.match(pid):
        raise HTTPException(404, "project not found")


api = APIRouter(dependencies=[Depends(valid_pid)])


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True, "role": config.ROLE}


@app.get("/readyz", include_in_schema=False)
def readyz():
    """Ready only when the project store answers. Cloud Run's startup probe and the deploy smoke test use this."""
    try:
        store.list_all()
    except Exception as e:
        logger.exception("not ready")
        return JSONResponse({"ok": False, "error": repr(e)[:200]}, status_code=503)
    return {"ok": True, "store": config.STORE, "queue": config.QUEUE, "vertex": config.VERTEX}


def get(pid):
    try:
        p = store.load(pid)
    except FileNotFoundError:
        raise HTTPException(404, "project not found")
    return p


def check_budget(pid):
    """Refuse up front (HTTP 429) instead of queueing work that would only fail."""
    with costs.track(pid):
        try:
            costs.guard()
        except costs.BudgetExceeded as e:
            raise HTTPException(429, str(e))


def media_url(p: Project):
    d = p.model_dump()
    root = str(config.DATA)
    def u(x):
        return f"/files/{Path(x).relative_to(root)}" if x and str(x).startswith(root) else None
    for s in d["scenes"]:
        s["clip_url"], s["thumb_url"], s["audio_url"] = u(s["clip"]), u(s["thumb"]), u(s["audio"])
    d["render_url"] = u(d["render_path"])
    d["cost"] = costs.summary(p.id)
    for c in d["cast"]:
        c["image_url"] = u(c["image"])
    d["character_url"] = u(str(config.DATA / p.id / "character.png")) if (config.DATA / p.id / "character.png").exists() else None
    return d


@api.get("/api/meta")
def meta():
    from .look import LOOKS
    return {"locked": bool(PASSCODE), "looks": [{"id": k, "label": v["label"], "blurb": v["blurb"]} for k, v in LOOKS.items()], "engines": [e.info() for e in engines.REGISTRY.values()], "voices": tts.GEMINI_VOICES, "voice_profiles": tts.catalogue()[0], "cloning": voices.available(), "default_voice": tts.default_voice(),
            "models": {"director": config.MODEL_DIRECTOR, "code": config.MODEL_CODE, "image": config.MODEL_IMAGE,
                       "video": config.MODEL_VEO, "voice": f"OmniVoice clones + {config.MODEL_TTS}" if voices.available() else config.MODEL_TTS, "music": config.MODEL_MUSIC}}


def _cover(p):
    """Prefer a picture beat (Veo, illustration, character, globe) over a title card."""
    root = str(config.DATA)
    thumbs = [s for s in p.get("scenes", []) if s.get("thumb") and str(s["thumb"]).startswith(root)]
    rank = {"veo": 0, "image": 1, "character": 2, "globe": 3}
    if not thumbs:
        return None
    best = min(thumbs, key=lambda s: rank.get(s["engine"], 9))
    return f"/files/{Path(best['thumb']).relative_to(root)}"


@api.get("/api/projects")
def projects():
    return [{k: p.get(k) for k in ("id", "title", "topic", "aspect", "language", "updated", "render_status")}
            | {"scenes": len(p.get("scenes", [])), "cover": _cover(p),
               "duration": round(sum(s.get("duration") or 0 for s in p.get("scenes", [])), 1),
               "engines": sorted({s["engine"] for s in p.get("scenes", [])})}
            for p in store.list_all()]


class VoiceOut(BaseModel):
    id: str
    name: str
    language: str
    status: str
    error: str | None
    builtin: bool


def voice_out(v):
    return VoiceOut(**v.model_dump(include=set(VoiceOut.model_fields)))


@api.get("/api/voices")
def list_voices():
    return [voice_out(v) for v in store.voice_list()]


@api.post("/api/voices")
async def create_voice(name: str = Form(...), file: UploadFile = File(...), reference_text: str = Form(""),
                       language: str = Form("English"), consent: bool = Form(False)):
    """Clone a narrator from a short sample. Needs the passcode like every write, and an explicit statement
    that the voice is the speaker's own or used with permission."""
    audio = await file.read(voices.MAX_UPLOAD + 1)
    try:
        return voice_out(voices.create(name, audio, reference_text, language, consent))
    except voices.VoiceError as e:
        raise HTTPException(400, str(e))


@api.delete("/api/voices/{vid}")
def delete_voice(vid: str):
    if not voices.ID.match(vid):
        raise HTTPException(404, "voice not found")
    try:
        v = store.voice_get(vid)
    except FileNotFoundError:
        raise HTTPException(404, "voice not found")
    if v.builtin:
        raise HTTPException(403, "The channel voices cannot be deleted.")
    store.voice_delete(vid)
    return {"ok": True}


class NewProject(BaseModel):
    topic: str
    audience: str = "curious general audience"
    language: str = "English"
    aspect: str = "16:9"
    length: str = "medium"
    voice: str = ""   # empty = the deployment's default voice
    look: str = "cinematic"
    notes: str = ""


@api.post("/api/projects")
def create(body: NewProject):
    p = Project(title=body.topic[:60] or "Untitled", topic=body.topic, audience=body.audience, language=body.language,
                aspect=body.aspect, length=body.length, voice=body.voice or tts.default_voice(), look=body.look)
    if body.notes.strip():
        p.sources.append(Source(kind="note", name="Notes", text=body.notes))
    store.save(p)
    return media_url(p)


@api.get("/api/projects/{pid}")
def read(pid: str):
    p = get(pid)
    if pipeline.reap_stale(pid):   # a job that died leaves its beat spinning: fail it when someone looks
        p = get(pid)
    return media_url(p)


@api.patch("/api/projects/{pid}")
def update(pid: str, body: dict):
    allowed = {"title", "topic", "audience", "language", "aspect", "length", "voice", "music", "pace", "quality", "look"}
    old = get(pid)
    p = store.mutate(pid, lambda p: [setattr(p, k, v) for k, v in body.items() if k in allowed])
    if "look" in body and body["look"] != old.look and p.cast:
        # a new look: restyle the cast so every reference (and the beats using it) is redrawn in it
        from .look import get as get_look
        lk = get_look(p.look)

        def restyle(pp):
            for c in pp.cast:
                if c.kind == "style":
                    c.description = f"{lk['label']}: {lk['image']}"
                c.image, c.status = None, "pending"
        store.mutate(pid, restyle)
        jobs.enqueue("cast_ensure", pid=pid)
    return media_url(get(pid))


@api.delete("/api/projects/{pid}")
def delete(pid: str):
    get(pid)
    store.delete(pid)
    return {"ok": True}


@api.post("/api/projects/{pid}/sources")
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


@api.delete("/api/projects/{pid}/sources/{sid}")
def del_source(pid: str, sid: str):
    return media_url(store.mutate(pid, lambda p: setattr(p, "sources", [s for s in p.sources if s.id != sid])))


@api.post("/api/projects/{pid}/storyboard")
def storyboard(pid: str):
    get(pid)
    check_budget(pid)
    jobs.enqueue("storyboard", pid=pid)
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


@api.post("/api/projects/{pid}/cast")
def add_cast(pid: str, body: CastEdit):
    item = CastItem(kind=body.kind or "character", name=body.name or "New", description=body.description or "")
    check_budget(pid)
    store.mutate(pid, lambda p: p.cast.append(item))
    jobs.enqueue("cast_generate", pid=pid, cid=item.id)
    return media_url(store.mutate(pid, lambda p: cast._set(p, item.id, status="generating")))


@api.patch("/api/projects/{pid}/cast/{cid}")
def edit_cast(pid: str, cid: str, body: CastEdit):
    changes = body.model_dump(exclude_none=True)
    p = get(pid)
    old = next((c for c in p.cast if c.id == cid), None)
    if not old:
        raise HTTPException(404, "cast item not found")
    redraw = "description" in changes and changes["description"] != old.description
    store.mutate(pid, lambda pp: cast._set(pp, cid, **changes))
    if redraw:
        check_budget(pid)
        jobs.enqueue("cast_generate", pid=pid, cid=cid)
    return media_url(get(pid))


@api.post("/api/projects/{pid}/cast/{cid}/generate")
def regen_cast(pid: str, cid: str):
    check_budget(pid)
    jobs.enqueue("cast_generate", pid=pid, cid=cid)
    return media_url(store.mutate(pid, lambda p: cast._set(p, cid, status="generating")))


@api.post("/api/projects/{pid}/cast/generate")
def gen_all_cast(pid: str):
    check_budget(pid)
    jobs.enqueue("cast_ensure", pid=pid)
    return media_url(get(pid))


@api.delete("/api/projects/{pid}/cast/{cid}")
def del_cast(pid: str, cid: str):
    def f(p):
        p.cast = [c for c in p.cast if c.id != cid]
        for s in p.scenes:
            s.cast = [x for x in s.cast if x != cid]
    return media_url(store.mutate(pid, f))


@api.patch("/api/projects/{pid}/scenes/{sid}")
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


@api.post("/api/projects/{pid}/scenes")
def add_scene(pid: str, body: dict):
    after = body.get("after")
    sc = Scene(narration=body.get("narration", "New scene."), engine=body.get("engine", "title"), brief=body.get("brief", ""))

    def f(p):
        idx = next((i + 1 for i, s in enumerate(p.scenes) if s.id == after), len(p.scenes))
        p.scenes.insert(idx, sc)
    return media_url(store.mutate(pid, f))


@api.delete("/api/projects/{pid}/scenes/{sid}")
def del_scene(pid: str, sid: str):
    return media_url(store.mutate(pid, lambda p: setattr(p, "scenes", [s for s in p.scenes if s.id != sid])))


@api.post("/api/projects/{pid}/order")
def reorder(pid: str, body: dict):
    ids = body["ids"]

    def f(p):
        by = {s.id: s for s in p.scenes}
        p.scenes = [by[i] for i in ids if i in by] + [s for s in p.scenes if s.id not in ids]
    return media_url(store.mutate(pid, f))


@api.post("/api/projects/{pid}/scenes/{sid}/rewrite")
def rewrite(pid: str, sid: str, body: dict):
    get(pid)
    check_budget(pid)
    pipeline.set_scene(pid, sid, status="queued")
    jobs.enqueue("rewrite", pid=pid, sid=sid, instruction=body.get("instruction", ""))
    return media_url(get(pid))


@api.post("/api/projects/{pid}/scenes/{sid}/render")
def render_one(pid: str, sid: str, body: dict | None = None):
    force = bool((body or {}).get("force"))
    get(pid)
    check_budget(pid)
    if (body or {}).get("replan"):
        pipeline.set_scene(pid, sid, params={})
    pipeline.set_scene(pid, sid, status="queued")
    jobs.enqueue("render_scene", pid=pid, sid=sid, force=force)
    return media_url(get(pid))


@api.post("/api/projects/{pid}/render")
def render(pid: str):
    if not get(pid).scenes:
        raise HTTPException(400, "There is no storyboard to render yet.")
    check_budget(pid)
    store.mutate(pid, lambda p: setattr(p, "render_status", "rendering scenes"))
    jobs.enqueue("render_all", pid=pid)
    return media_url(get(pid))


@api.post("/api/projects/{pid}/assemble")
def assemble(pid: str):
    get(pid)
    check_budget(pid)
    store.mutate(pid, lambda p: setattr(p, "render_status", "assembling"))
    jobs.enqueue("assemble", pid=pid)
    return media_url(get(pid))


@api.post("/api/projects/{pid}/translate")
def translate(pid: str, body: dict):
    get(pid)
    check_budget(pid)
    jobs.enqueue("translate", pid=pid, language=body["language"])
    return {"ok": True}


@api.get("/api/jobs")
def job_list():
    return jobs.recent()


class PublicFiles(StaticFiles):
    """Rendered media is public (the demo is browsable). Uploaded sources and voice samples are not."""

    async def get_response(self, path, scope):
        if "sources/" in path or path.startswith("voices/") or path.endswith((".json", ".jsonl")):
            raise HTTPException(404)
        return await super().get_response(path, scope)


@app.exception_handler(FileNotFoundError)
async def _missing(request, exc):
    return JSONResponse({"detail": "not found"}, status_code=404)


if config.ROLE in ("all", "api"):
    app.include_router(api)
    app.mount("/files", PublicFiles(directory=str(config.DATA)), name="files")
if config.ROLE == "worker" or (config.ROLE == "all" and config.QUEUE == "cloudtasks"):
    from .worker import router as worker_router
    app.include_router(worker_router)
dist = config.ROOT / "web" / "out"
if dist.exists() and config.ROLE in ("all", "api"):
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")


def recover_after_restart():
    """With the local queue, jobs die with the process, so anything left busy is failed at once. With
    Cloud Tasks nothing is lost on restart (the queue redelivers), so this only fails jobs older than
    a job can run, and only when a person opens the project (see read)."""
    if config.QUEUE != "local":
        return
    for row in store.list_all():
        if row.get("id") and pipeline.reap_stale(row["id"], min_age=0):
            logger.info("reset interrupted project", extra={"pid": row["id"]})
