"""Private HTTP entry point for background jobs. Only mounted on the worker service.

Cloud Run IAM already limits who can call this service (only the Cloud Tasks service account holds
roles/run.invoker). The OIDC token is verified again here so the endpoint stays safe if the service
is ever made public by mistake.
"""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import config, jobs, log, tasks  # noqa: F401  (tasks registers the handlers)

logger = log.get("worker")
router = APIRouter()


def _verify(request: Request):
    if config.ROLE != "worker":
        return
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "missing token")
    from google.auth.transport import requests as greq
    from google.oauth2 import id_token
    try:
        claims = id_token.verify_oauth2_token(auth[7:], greq.Request(), audience=config.WORKER_URL)
    except Exception:
        raise HTTPException(401, "bad token")
    allowed = {c for c in [config.TASKS_SA, *config.CALLERS] if c}
    if allowed and claims.get("email") not in allowed:
        raise HTTPException(403, "wrong caller")


@router.get("/internal/selftest")
def selftest(request: Request):
    """What the deploy gate calls before a new revision gets traffic: a real Firestore round trip and a
    real (one-word) model call as the worker's own identity, so a broken IAM binding, region or model id
    fails the deploy instead of the first user."""
    _verify(request)
    from . import gemini, sandbox, store
    out = {"store": config.STORE, "queue": config.QUEUE, "vertex": config.VERTEX, "net_isolated": sandbox.NET_ISOLATED}
    store.list_all()
    out["firestore"] = "ok"
    out["model"] = gemini.text("Reply with the single word: ok", model=config.MODEL_FAST).strip()[:20]
    from . import voices
    if voices.available():
        out["voice"] = "ok" if voices.health().get("ok") else "down"
    return out


@router.post("/internal/tasks/{kind}")
async def run_task(kind: str, request: Request):
    _verify(request)
    if kind not in jobs.HANDLERS:
        raise HTTPException(404, "unknown task")
    payload = json.loads((await request.body()) or b"{}")
    from starlette.concurrency import run_in_threadpool
    try:
        await run_in_threadpool(jobs.run, kind, payload)
    except Exception as e:
        # The handler has already recorded the failure on the project. Returning 200 stops Cloud Tasks from
        # re-running a job that fails deterministically (and spending again); infrastructure failures
        # (instance killed, deadline) never reach this line and are retried by the queue.
        return JSONResponse({"ok": False, "error": repr(e)[:300]})
    return {"ok": True}
