"""Every background job, registered by name. The API enqueues them (jobs.enqueue); the worker
runs them (jobs.run). Each is idempotent: re-running a finished job finds its result in the
content-hash cache and does nothing.
"""
import shutil
from pathlib import Path

from . import cast, config, costs, director, jobs, log, pipeline, store
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
        p = director.storyboard(store.load(pid))
        p.render_status = "storyboard"
        store.save(p)
    except Exception as e:
        msg = friendly_error(e)
        store.mutate(pid, lambda p: (setattr(p, "render_status", "error"), setattr(p, "render_error", msg)))
        raise
    jobs.enqueue("cast_ensure", pid=pid)   # reference images are ready before the first render


@jobs.task("cast_ensure")
def cast_ensure(pid):
    cast.ensure(pid)


@jobs.task("cast_generate")
def cast_generate(pid, cid):
    cast.generate(pid, cid)


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


@jobs.task("rewrite")
@costs.tracked
def rewrite(pid, sid, instruction):
    p = store.load(pid)
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
