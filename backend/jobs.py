"""Single background worker (the box has little RAM; one render at a time).

API-bound steps (TTS, images, Veo) run in a small thread pool; CPU-heavy renders
(manim, cairo, ffmpeg) go through the one-slot render lock.
"""
import queue
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

RENDER_LOCK = threading.Semaphore(1)
API_POOL = ThreadPoolExecutor(max_workers=3)

_q: "queue.Queue" = queue.Queue()
_log: list[dict] = []


def submit(name, fn, *a, **kw):
    job = {"name": name, "status": "queued", "t": time.time(), "error": None}
    _log.append(job)
    del _log[:-200]
    _q.put((job, fn, a, kw))
    return job


def recent():
    return list(reversed(_log[-50:]))


def _worker():
    while True:
        job, fn, a, kw = _q.get()
        job["status"] = "running"
        try:
            fn(*a, **kw)
            job["status"] = "done"
        except Exception as e:
            job["status"] = "error"
            job["error"] = repr(e)[:500]
            traceback.print_exc()


for _ in range(2):   # two job runners; heavy renders still serialise on RENDER_LOCK
    threading.Thread(target=_worker, daemon=True).start()
