"""Every background job, registered by name. The API enqueues them (jobs.enqueue); the worker
runs them (jobs.run). Each is idempotent: re-running a finished job finds its result in the
content-hash cache and does nothing.
"""
import shutil
import time
from pathlib import Path

from . import cast, config, costs, director, factcheck, guards, jobs, log, pipeline, provenance, qa, store, voices
from .errors import friendly_error
from .models import new_id

logger = log.get("tasks")

# engines that put words on screen: re-planned and re-rendered in the new language
TEXT_ENGINES = {"title", "manim", "globe", "chart", "timeline", "flow", "scene"}


@jobs.task("storyboard")
@costs.tracked
def storyboard(pid):
    store.mutate(pid, lambda p: setattr(p, "render_status", "directing"))
    try:
        src = store.load(pid)
        guards.screen_request(src.topic, src.instructions)   # no fabricated words or deeds of real people
        p = director.storyboard(src)
        p.render_status = "storyboard"
        store.save(p)
    except Exception as e:
        msg = friendly_error(e)
        store.mutate(pid, lambda p: (setattr(p, "render_status", "error"), setattr(p, "render_error", msg)))
        raise
    jobs.enqueue("cast_ensure", pid=pid)   # reference images are ready before the first render
    jobs.enqueue("factcheck", pid=pid)     # claims are checked before anything is rendered


@jobs.task("cast_ensure")
def cast_ensure(pid):
    cast.ensure(pid)


@jobs.task("cast_generate")
def cast_generate(pid, cid):
    cast.generate(pid, cid)


@jobs.task("voice_build")
def voice_build(vid):
    voices.build(vid)


@jobs.task("verify")
def verify(vid, chunks, size):
    """Check an uploaded video for our watermark. The upload arrives as numbered pieces in verify/<vid>/ (the API
    cannot take one big request); it is joined, read, and deleted again whatever the outcome."""
    d = config.DATA / "verify" / vid
    try:
        doc = store.doc_get("verifications", vid)
    except FileNotFoundError:
        return
    try:
        parts = [d / f"{i:05d}.part" for i in range(chunks)]
        deadline = time.time() + 90   # the shared volume can take a moment to show files another instance wrote
        while not (all(p.exists() for p in parts) and sum(p.stat().st_size for p in parts) == size):
            if time.time() > deadline:
                raise RuntimeError("upload incomplete")
            time.sleep(2)
        whole = d / "upload.bin"
        with open(whole, "wb") as out:
            for p in parts:
                with open(p, "rb") as f:
                    shutil.copyfileobj(f, out)
        res = provenance.verify(whole)
        doc.update(status="done", **res)
    except Exception as e:
        logger.warning("verify failed: %r", e, extra={"vid": vid})
        doc.update(status="error", error="That file could not be read as a video." if "ffprobe" in repr(e) or "ffmpeg" in repr(e)
                   else "The upload did not arrive in full. Please try again.")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    doc["finished"] = time.time()
    store.doc_put("verifications", vid, doc)


@jobs.task("render_all")
def render_all(pid):
    pipeline.render_all(pid)


@jobs.task("render_scene")
def render_scene(pid, sid, force=False, then_assemble=False):
    pipeline.render_scene(pid, sid, force)
    if then_assemble:
        pipeline.maybe_assemble(pid)


@jobs.task("assemble")
def assemble(pid):
    pipeline.assemble(pid)


@jobs.task("qa")
def quality_check(pid):
    qa.run(pid)
    factcheck.run(pid)   # again with the rendered beats' on-screen numbers and labels


@jobs.task("factcheck")
def fact_check(pid):
    factcheck.run(pid)


@jobs.task("rewrite")
@costs.tracked
def rewrite(pid, sid, instruction):
    p = store.load(pid)
    try:
        guards.screen_request(p.topic, instruction)
    except guards.Refused as e:
        pipeline.set_scene(pid, sid, status="ready" if store.scene(p, sid).clip else "draft", error=str(e))
        return
    s = director.rewrite_scene(p, store.scene(p, sid), instruction)
    s.status = "draft"
    store.mutate(pid, lambda pp: pp.scenes.__setitem__([x.id for x in pp.scenes].index(sid), s))
    pipeline.render_scene(pid, sid)


@jobs.task("translate")
@costs.tracked
def translate(pid, language):
    src = store.load(pid)
    lines = director.translate(src, language)
    p = src.model_copy(deep=True)
    p.id, p.title, p.language = new_id(), f"{src.title} ({language})", language
    p.render_status, p.render_path, p.render_error = "rendering scenes", None, None
    src_clips = {x.id: x.clip for x in src.scenes}
    for s, line in zip(p.scenes, lines):
        src_clip = src_clips.get(s.id)
        old = config.DATA / src.id / "scenes" / s.id
        new = new_id()
        if old.exists() and s.engine not in TEXT_ENGINES:   # reuse generated stills / Veo shots
            shutil.copytree(old, config.DATA / p.id / "scenes" / new, ignore=shutil.ignore_patterns("clip_*", "voice_*", "thumb_*"))
        s.id, s.narration, s.audio, s.clip, s.thumb, s.status, s.narration_hash = new, line, None, None, None, "queued", None
        if s.engine in TEXT_ENGINES:   # on-screen text must be re-planned in the new language
            s.params = {}
        elif src_clip and Path(src_clip).exists():   # pictures have no words: reuse the finished shot as is
            s.params = {**s.params, "_reuse_clip": src_clip}
    store.save(p)
    jobs.enqueue("render_all", pid=p.id)
