"""Scene rendering and final assembly. Everything is cached by content hash, so editing one
scene only re-does that scene."""
import hashlib
import json
import re
import shutil
from pathlib import Path

from . import config, costs, engines, gemini, jobs, log, media, store, tts
from .errors import friendly_error

logger = log.get("pipeline")


def h(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:10]


def sdir(pid, sid):
    d = store.pdir(pid) / "scenes" / sid
    d.mkdir(parents=True, exist_ok=True)
    return d


def set_scene(pid, sid, **kw):
    def f(p):
        s = store.scene(p, sid)
        for k, v in kw.items():
            setattr(s, k, v)
    store.mutate(pid, f)


def ensure_audio(pid, sid):
    p = store.load(pid)
    s = store.scene(p, sid)
    nh = h(s.narration, p.voice, p.pace, "v2")
    if s.audio and s.narration_hash == nh and Path(s.audio).exists():
        return s.duration
    wav, dur = tts.synth(s.narration, sdir(pid, sid) / f"voice_{nh}.wav", voice=p.voice, pace=p.pace, language=p.language)
    set_scene(pid, sid, audio=str(wav), duration=round(dur, 3), narration_hash=nh)
    return dur


def ensure_plan(pid, sid):
    p = store.load(pid)
    s = store.scene(p, sid)
    if s.params:
        return s.params
    params = engines.get(s.engine).plan(s, p)
    set_scene(pid, sid, params=params)
    return params


@costs.tracked
def render_scene(pid, sid, force=False):
    try:
        set_scene(pid, sid, status="rendering", error=None)
        from . import cast
        cast.ensure(pid, retry_errors=False)   # no-op once every reference image exists
        dur = ensure_audio(pid, sid)
        ensure_plan(pid, sid)
        p = store.load(pid)
        s = store.scene(p, sid)
        eng = engines.get(s.engine)
        from . import cast
        refsig = cast.signature(p, s) if s.engine in ("image", "character", "veo") else []
        if s.engine == "veo" and p.quality == "draft":
            refsig = refsig + [["draft"]]   # draft and final Veo clips are cached separately
        look_key = [p.look] if p.look != "cinematic" else []   # cinematic keeps the original cache keys
        rh = h(s.engine, s.params, round(dur, 2), p.aspect, s.brief, *([refsig] if refsig else []), *look_key)
        final = sdir(pid, sid) / f"clip_{rh}.mp4"
        if final.exists() and not force:
            set_scene(pid, sid, status="ready", clip=str(final), render_hash=rh)
            return
        work = sdir(pid, sid) / f"r_{h(s.engine, s.params, p.aspect, s.brief, refsig, *look_key) if (refsig or look_key) else h(s.engine, s.params, p.aspect, s.brief)}"
        if force and work.exists():
            shutil.rmtree(work)
        work.mkdir(exist_ok=True)
        err = None
        reuse = s.params.get("_reuse_clip")
        if reuse and Path(reuse).exists():   # e.g. a translation: same picture, new narration length
            media.fit(reuse, final, dur, config.SIZES[p.aspect], stretch_max=1.25)
            th = media.thumb(final, sdir(pid, sid) / f"thumb_{rh}.jpg")
            set_scene(pid, sid, status="ready", clip=str(final), thumb=str(th), render_hash=rh, error=None)
            return
        from .engines.kit import use_palette
        try:
            with use_palette(p.look):   # code-drawn engines take the look's colours
                if getattr(eng, "heavy", True):
                    with jobs.RENDER_LOCK:
                        raw = eng.render(s, p, dur, work)
                else:
                    raw = eng.render(s, p, dur, work)
        except costs.BudgetExceeded:
            raise   # not an engine fault: stop, do not paper over it with a title card
        except Exception as e:
            logger.exception("engine failed, using title card", extra={"pid": pid, "sid": sid, "engine": s.engine})
            err = f"{s.engine} failed ({str(e)[:300]}); showing a title card instead"
            fb = engines.get("title")
            s2 = s.model_copy(update={"params": fb.plan(s, p)})
            with jobs.RENDER_LOCK, use_palette(p.look):
                raw = fb.render(s2, p, dur, work)
        media.fit(raw, final, dur, config.SIZES[p.aspect], stretch_max=getattr(eng, "stretch_max", 1.0))
        th = media.thumb(final, sdir(pid, sid) / f"thumb_{rh}.jpg")
        set_scene(pid, sid, status="ready", clip=str(final), thumb=str(th), render_hash=rh, error=err)
    except Exception as e:
        logger.exception("scene failed", extra={"pid": pid, "sid": sid})
        set_scene(pid, sid, status="error", error=friendly_error(e))


@costs.tracked
def render_all(pid):
    """Orchestrator: make sure the cast exists, then fan out one job per beat. The last beat to
    finish claims the assemble step (see maybe_assemble), so no job ever waits on another."""
    p = store.load(pid)

    def mark(pp):
        for s in pp.scenes:
            s.status = "queued"
        pp.render_status = "rendering scenes"
        pp.render_error = None
    store.mutate(pid, mark)
    from . import cast
    cast.ensure(pid)
    for s in p.scenes:
        jobs.enqueue("render_scene", pid=pid, sid=s.id, then_assemble=True)


def maybe_assemble(pid):
    """Called after every beat of a full render. Exactly one caller wins the claim: the status flip is
    a transaction, so concurrent workers cannot both assemble, and a retried job cannot assemble twice."""
    won = []

    def claim(p):
        won.clear()
        if p.render_status == "rendering scenes" and all(s.status in ("ready", "error") for s in p.scenes):
            p.render_status = "assembling"
            won.append(True)
    store.mutate(pid, claim)
    if won:
        jobs.enqueue("assemble", pid=pid)


STALE_AFTER_S = jobs.DISPATCH_DEADLINE_S + 300


def reap_stale(pid, min_age=STALE_AFTER_S):
    """A job that died mid-flight (instance killed, deadline passed) leaves its beat 'rendering' forever.
    Anything busy and untouched for longer than a job can possibly run is failed with a clear message."""
    import time
    busy_scene, busy_project = {"queued", "rendering"}, {"directing", "rendering scenes", "assembling"}
    p = store.load(pid)
    if time.time() - p.updated < min_age:
        return False
    if not (p.render_status in busy_project or any(s.status in busy_scene for s in p.scenes)
            or any(c.status == "generating" for c in p.cast)):
        return False

    def reset(pp):
        for s in pp.scenes:
            if s.status in busy_scene:
                s.status = "ready" if s.clip and Path(s.clip).exists() and s.render_hash else "draft"
        for c in pp.cast:
            if c.status == "generating":
                c.status = "pending"
        if pp.render_status in busy_project:
            was = pp.render_status
            pp.render_status = "error"
            pp.render_error = ("This took too long and was stopped while "
                               f"{'being directed' if was == 'directing' else 'rendering'}. Press "
                               f"{'Re-direct' if was == 'directing' else 'Render video'} to continue; finished beats are kept.")
    store.mutate(pid, reset)
    logger.warning("reaped stale project", extra={"pid": pid})
    return True


# ------------------------------------------------------------------ assembly

def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(p, out):
    t, i, rows = 0.0, 1, []
    for s in p.scenes:
        sents = [x for x in re.split(r"(?<=[.!?。।])\s+", s.narration.strip()) if x]
        speak = max(0.1, (s.duration or 0) - 0.45)
        total = sum(len(x) for x in sents) or 1
        st = t
        for x in sents:
            d = speak * len(x) / total
            rows.append(f"{i}\n{srt_time(st)} --> {srt_time(st + d)}\n{x}\n")
            i += 1
            st += d
        t += s.duration or 0
    Path(out).write_text("\n".join(rows), encoding="utf-8")
    return out


def ensure_music(p):
    f = store.pdir(p.id) / "music.mp3"
    if not f.exists():
        mood = gemini.text(f"In one line, describe calm instrumental background music for a documentary about: {p.topic}. "
                           "Minimal, no drums, no vocals, slow. Just the description.")
        gemini.music(f"{mood.strip()} Instrumental only, no vocals, soft and steady, suitable under narration.", f)
    return f


@costs.tracked
def assemble(pid):
    store.mutate(pid, lambda p: setattr(p, "render_status", "assembling"))
    try:
        p = store.load(pid)
        bad = [i + 1 for i, s in enumerate(p.scenes) if not (s.clip and Path(s.clip).exists() and s.audio)]
        if bad:
            raise RuntimeError(f"scenes not ready: {bad}")
        d = store.pdir(pid) / "out"
        d.mkdir(exist_ok=True)
        lst = d / "clips.txt"
        lst.write_text("".join(f"file '{s.clip}'\n" for s in p.scenes))
        alst = d / "voice.txt"
        alst.write_text("".join(f"file '{s.audio}'\n" for s in p.scenes))
        media.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", d / "video.mp4"])
        media.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", alst, "-c:a", "pcm_s16le", d / "voice.wav"])
        total = media.duration(d / "voice.wav")
        mix = d / "mix.wav"
        if p.music:
            try:
                m = ensure_music(p)
                media.run(["ffmpeg", "-y", "-v", "error", "-i", d / "voice.wav", "-stream_loop", "-1", "-i", m,
                           "-filter_complex",
                           f"[1:a]aresample=48000,volume=-24dB,afade=t=in:d=2,afade=t=out:st={max(0, total - 3):.2f}:d=3[m];"
                           f"[0:a]aresample=48000[v];[v][m]amix=inputs=2:duration=first:normalize=0,"
                           f"loudnorm=I=-14:TP=-1.5:LRA=11",
                           "-t", f"{total:.3f}", "-ar", "48000", mix])
            except Exception as e:
                logger.warning("music skipped: %s", e, extra={"pid": p.id})
                mix = None
        if not p.music or mix is None or not Path(mix).exists():
            mix = d / "mix.wav"
            media.run(["ffmpeg", "-y", "-v", "error", "-i", d / "voice.wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                       "-ar", "48000", mix])
        write_srt(p, d / "subtitles.srt")   # shipped beside the video as a sidecar file
        slug = re.sub(r"[^a-z0-9]+", "_", p.title.lower()).strip("_")[:50] or "video"
        final = d / f"{slug}.mp4"
        media.run(["ffmpeg", "-y", "-v", "error", "-i", d / "video.mp4", "-i", mix, "-map", "0:v", "-map", "1:a",
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final])

        def done(pp):
            pp.render_status, pp.render_path, pp.render_error = "done", str(final), None
        store.mutate(pid, done)
        return final
    except Exception as e:
        logger.exception("assemble failed", extra={"pid": pid})
        msg = friendly_error(e)

        def fail(pp):
            pp.render_status, pp.render_error = "error", msg
        store.mutate(pid, fail)
