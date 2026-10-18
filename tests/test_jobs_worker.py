import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import config, jobs, worker


def test_local_queue_runs_the_handler():
    import threading
    done = threading.Event()
    jobs.HANDLERS["_probe"] = lambda pid: done.set()
    jobs.enqueue("_probe", pid="x")
    assert done.wait(5)
    del jobs.HANDLERS["_probe"]


def test_unknown_kind_is_rejected():
    with pytest.raises(KeyError):
        jobs.enqueue("nope")


def test_cloud_enqueue_builds_an_authenticated_task_with_a_long_deadline(monkeypatch):
    created = []

    class Fake:
        def queue_path(self, *a):
            return "/".join(a)

        def create_task(self, request):
            created.append(request)

            class T:
                name = "projects/p/locations/l/queues/q/tasks/123"
            return T()
    monkeypatch.setattr(jobs, "_tasks_client", lambda: Fake())
    for k, v in dict(QUEUE="cloudtasks", GCP_PROJECT="proj", GCP_REGION="asia-southeast1", TASKS_QUEUE="q",
                     WORKER_URL="https://worker.example", TASKS_SA="sa@proj.iam.gserviceaccount.com").items():
        monkeypatch.setattr(config, k, v)
    jobs.enqueue("render_scene", pid="abcdef0123", sid="s0")
    (req,) = created
    t = req["task"]
    assert req["parent"] == "proj/asia-southeast1/q"
    assert t.http_request.url == "https://worker.example/internal/tasks/render_scene"
    assert json.loads(t.http_request.body) == {"pid": "abcdef0123", "sid": "s0"}
    assert t.http_request.oidc_token.service_account_email == "sa@proj.iam.gserviceaccount.com"
    assert t.http_request.oidc_token.audience == "https://worker.example"
    assert t.dispatch_deadline.seconds == 1800


def test_cloud_enqueue_fails_loudly_when_misconfigured(monkeypatch):
    monkeypatch.setattr(config, "QUEUE", "cloudtasks")
    monkeypatch.setattr(config, "GCP_PROJECT", "proj")
    monkeypatch.setattr(config, "WORKER_URL", "")
    with pytest.raises(RuntimeError, match="WORKER_URL"):
        jobs.enqueue("assemble", pid="abcdef0123")


@pytest.fixture
def wapp():
    a = FastAPI()
    a.include_router(worker.router)
    return TestClient(a)


def test_worker_runs_the_task_and_swallows_deterministic_failures(wapp, monkeypatch):
    calls = []
    monkeypatch.setitem(jobs.HANDLERS, "ok", lambda pid: calls.append(pid))
    monkeypatch.setitem(jobs.HANDLERS, "bad", lambda pid: 1 / 0)
    assert wapp.post("/internal/tasks/ok", json={"pid": "a"}).json() == {"ok": True} and calls == ["a"]
    r = wapp.post("/internal/tasks/bad", json={"pid": "a"})
    assert r.status_code == 200 and r.json()["ok"] is False   # 200: Cloud Tasks must not retry (and re-bill) it
    assert wapp.post("/internal/tasks/unknown", json={}).status_code == 404


def test_worker_role_requires_a_valid_token_from_the_tasks_service_account(wapp, monkeypatch):
    monkeypatch.setattr(config, "ROLE", "worker")
    monkeypatch.setattr(config, "WORKER_URL", "https://worker.example")
    monkeypatch.setattr(config, "TASKS_SA", "sa@proj.iam.gserviceaccount.com")
    monkeypatch.setitem(jobs.HANDLERS, "ok", lambda **k: None)
    assert wapp.post("/internal/tasks/ok", json={}).status_code == 401
    from google.oauth2 import id_token

    def verify(token, req, audience=None):
        assert audience == "https://worker.example"
        if token == "good":
            return {"email": "sa@proj.iam.gserviceaccount.com"}
        if token == "other":
            return {"email": "evil@x.iam.gserviceaccount.com"}
        raise ValueError("bad")
    monkeypatch.setattr(id_token, "verify_oauth2_token", verify)
    h = lambda t: {"authorization": f"Bearer {t}"}  # noqa: E731
    assert wapp.post("/internal/tasks/ok", json={}, headers=h("good")).status_code == 200
    assert wapp.post("/internal/tasks/ok", json={}, headers=h("other")).status_code == 403
    assert wapp.post("/internal/tasks/ok", json={}, headers=h("forged")).status_code == 401
