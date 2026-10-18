"""Background work, behind one call: `enqueue(kind, **payload)`.

* local       in-process threads. Local development and tests; jobs die with the process.
* cloudtasks  Google Cloud Tasks delivers each job as an authenticated HTTP request to the private
              worker service, which runs it. Jobs survive restarts and deploys, are retried with
              backoff, and are rate limited by the queue, so a burst of renders cannot exhaust the
              Gemini quota or the budget.

Handlers are registered with @task in tasks.py. Every handler is idempotent (results are cached by
content hash), so at-least-once delivery is safe.
"""
import json
import queue
import threading
import time

from . import config, log

logger = log.get("jobs")

RENDER_LOCK = threading.Semaphore(1)   # one CPU-heavy render per process; the worker runs one request per instance

HANDLERS = {}
_q: "queue.Queue" = queue.Queue()
_log: list[dict] = []


def task(kind):
    def reg(fn):
        HANDLERS[kind] = fn
        return fn
    return reg


def run(kind, payload):
    """Execute one job now. Used by the local queue and by the worker's HTTP endpoint."""
    if kind not in HANDLERS:
        raise KeyError(f"unknown task {kind!r}")
    t0 = time.time()
    logger.info("task start", extra={"task": kind, **{k: v for k, v in payload.items() if k in ("pid", "sid", "cid")}})
    try:
        HANDLERS[kind](**payload)
    except Exception:
        logger.exception("task failed", extra={"task": kind, "pid": payload.get("pid")})
        raise
    logger.info("task done", extra={"task": kind, "seconds": round(time.time() - t0, 1), "pid": payload.get("pid")})


def enqueue(kind, **payload):
    if kind not in HANDLERS:
        raise KeyError(f"unknown task {kind!r}")
    if config.QUEUE == "cloudtasks":
        return _cloud(kind, payload)
    return _local(kind, payload)


def recent():
    return list(reversed(_log[-50:]))


# ------------------------------------------------------------------ local

def _local(kind, payload):
    job = {"name": f"{kind} {payload.get('pid', '')}".strip(), "status": "queued", "t": time.time(), "error": None}
    _log.append(job)
    del _log[:-200]
    _q.put((job, kind, payload))
    return job


def _worker():
    while True:
        job, kind, payload = _q.get()
        job["status"] = "running"
        try:
            run(kind, payload)
            job["status"] = "done"
        except Exception as e:
            job["status"] = "error"
            job["error"] = repr(e)[:500]


for _ in range(2):   # two runners; heavy renders still serialise on RENDER_LOCK
    threading.Thread(target=_worker, daemon=True).start()


# ------------------------------------------------------------------ cloud tasks

_ct = None
_ct_lock = threading.Lock()


def _tasks_client():
    global _ct
    with _ct_lock:
        if _ct is None:
            from google.cloud import tasks_v2
            _ct = tasks_v2.CloudTasksClient()
        return _ct


DISPATCH_DEADLINE_S = 1800   # Cloud Tasks' maximum for HTTP targets; also the age after which a job is presumed dead


def _cloud(kind, payload):
    from google.cloud import tasks_v2
    from google.protobuf import duration_pb2
    for name in ("GCP_PROJECT", "WORKER_URL", "TASKS_SA"):
        if not getattr(config, name):
            raise RuntimeError(f"cloudtasks queue needs {name} (STUDIO_*/GOOGLE_CLOUD_PROJECT) to be set")
    c = _tasks_client()
    parent = c.queue_path(config.GCP_PROJECT, config.GCP_REGION, config.TASKS_QUEUE)
    t = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=f"{config.WORKER_URL}/internal/tasks/{kind}",
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode(),
            oidc_token=tasks_v2.OidcToken(service_account_email=config.TASKS_SA, audience=config.WORKER_URL)),
        dispatch_deadline=duration_pb2.Duration(seconds=DISPATCH_DEADLINE_S))
    made = c.create_task(request={"parent": parent, "task": t})
    logger.info("task enqueued", extra={"task": kind, "pid": payload.get("pid"), "task_name": made.name.rsplit("/", 1)[-1]})
    return {"name": made.name, "status": "queued", "t": time.time(), "error": None}
