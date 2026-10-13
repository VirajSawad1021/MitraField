"""Scene rendering and final assembly. Everything is cached by content hash, so editing one
scene only re-does that scene."""
import hashlib
import json
import re
import shutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config, director, engines, gemini, jobs, media, store, tts


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


def render_scene(pid, sid, force=False):
    try:
        set_scene(pid, sid, status="rendering", error=None)
        dur = ensure_audio(pid, sid)
        ensure_plan(pid, sid)
        p = store.load(pid)
        s = store.scene(p, sid)
        eng = engines.get(s.engine)
        rh = h(s.engine, s.params, round(dur, 2), p.aspect, s.brief)
        final = sdir(pid, sid) / f"clip_{rh}.mp4"
        if final.exists() and not force:
            set_scene(pid, sid, status="ready", clip=str(final), render_hash=rh)
            return
        work = sdir(pid, sid) / f"r_{h(s.engine, s.params, p.aspect, s.brief)}"
        if force and work.exists():
            shutil.rmtree(work)
        work.mkdir(exist_ok=True)
        err = None
        try:
            if getattr(eng, "heavy", True):
                with jobs.RENDER_LOCK:
                    raw = eng.render(s, p, dur, work)
            else:
                raw = eng.render(s, p, dur, work)
        except Exception as e:
            traceback.print_exc()
            err = f"{s.engine} failed ({str(e)[:300]}); showing a title card instead"
            fb = engines.get("title")
            s2 = s.model_copy(update={"params": fb.plan(s, p)})
            with jobs.RENDER_LOCK:
                raw = fb.render(s2, p, dur, work)
        media.fit(raw, final, dur, config.SIZES[p.aspect], stretch_max=getattr(eng, "stretch_max", 1.0))
        th = media.thumb(final, sdir(pid, sid) / f"thumb_{rh}.jpg")
        set_scene(pid, sid, status="ready", clip=str(final), thumb=str(th), render_hash=rh, error=err)
    except Exception as e:
        traceback.print_exc()
        set_scene(pid, sid, status="error", error=str(e)[:500])


def render_all(pid, assemble_after=True):
    p = store.load(pid)
    todo = [s.id for s in p.scenes]

    def mark(pp):
        for s in pp.scenes:
            s.status = "queued"
        pp.render_status = "rendering scenes"
    store.mutate(pid, mark)
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(lambda sid: render_scene(pid, sid), todo))
    if assemble_after:
        assemble(pid)


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
                print("music skipped:", e)
                mix = None
        if not p.music or mix is None or not Path(mix).exists():
            mix = d / "mix.wav"
            media.run(["ffmpeg", "-y", "-v", "error", "-i", d / "voice.wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                       "-ar", "48000", mix])
        srt = write_srt(p, d / "subtitles.srt")
        slug = re.sub(r"[^a-z0-9]+", "_", p.title.lower()).strip("_")[:50] or "video"
        final = d / f"{slug}.mp4"
        media.run(["ffmpeg", "-y", "-v", "error", "-i", d / "video.mp4", "-i", mix, "-map", "0:v", "-map", "1:a",
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final])

        def done(pp):
            pp.render_status, pp.render_path, pp.render_error = "done", str(final), None
        store.mutate(pid, done)
        return final
    except Exception as e:
        traceback.print_exc()

        def fail(pp):
            pp.render_status, pp.render_error = "error", str(e)[:500]
        store.mutate(pid, fail)
