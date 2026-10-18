import pytest
from fastapi.testclient import TestClient

from backend import app as appmod
from backend import config, costs, jobs, store

client = TestClient(appmod.app)


@pytest.fixture
def queued(monkeypatch):
    """Capture enqueued jobs instead of running them."""
    got = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: got.append((kind, p)) or {"status": "queued"})
    return got


def test_health_and_ready():
    assert client.get("/healthz").json()["ok"]
    r = client.get("/readyz")
    assert r.status_code == 200 and r.json()["store"] == "file"


def test_readyz_is_503_when_store_is_down(monkeypatch):
    def boom():
        raise RuntimeError("firestore unreachable")
    monkeypatch.setattr(store, "list_all", boom)
    assert client.get("/readyz").status_code == 503


def test_passcode_guards_writes_but_not_reads(monkeypatch):
    monkeypatch.setattr(appmod, "PASSCODE", "s3cret")
    assert client.get("/api/projects").status_code == 200
    assert client.post("/api/projects", json={"topic": "x"}).status_code == 401
    assert client.post("/api/projects", json={"topic": "x"}, headers={"x-studio-pass": "wrong"}).status_code == 401
    assert client.post("/api/projects", json={"topic": "x"}, headers={"x-studio-pass": "s3cret"}).status_code == 200


def test_passcode_compare_handles_non_ascii_header(monkeypatch):
    monkeypatch.setattr(appmod, "PASSCODE", "s3cret")
    r = client.post("/api/projects", json={"topic": "x"}, headers={"x-studio-pass": "pässword".encode("latin-1")})
    assert r.status_code == 401


@pytest.mark.parametrize("pid", ["%2e%2e", "ABCDEF0123", "abc", "abcdef01234", "abcdef012g"])
def test_malformed_project_ids_are_404(pid):
    assert client.get(f"/api/projects/{pid}").status_code == 404
    assert client.delete(f"/api/projects/{pid}").status_code == 404


def test_create_read_delete(queued):
    p = client.post("/api/projects", json={"topic": "How do tides work?"}).json()
    assert client.get(f"/api/projects/{p['id']}").json()["topic"] == "How do tides work?"
    assert any(x["id"] == p["id"] for x in client.get("/api/projects").json())
    assert client.delete(f"/api/projects/{p['id']}").status_code == 200
    assert client.get(f"/api/projects/{p['id']}").status_code == 404


def test_storyboard_and_render_enqueue_named_jobs(project, queued):
    assert client.post(f"/api/projects/{project.id}/storyboard").status_code == 200
    assert client.post(f"/api/projects/{project.id}/render").status_code == 200
    assert client.post(f"/api/projects/{project.id}/scenes/s0/render", json={"force": True}).status_code == 200
    assert [k for k, _ in queued] == ["storyboard", "render_all", "render_scene"]
    assert queued[2][1] == {"pid": project.id, "sid": "s0", "force": True}
    assert store.load(project.id).render_status == "rendering scenes"


def test_spend_cap_refuses_with_429_and_enqueues_nothing(project, queued, monkeypatch):
    monkeypatch.setattr(config, "CAP_PROJECT_USD", 0.1)
    with costs.track(project.id):
        costs.add("video", 0.5)
    r = client.post(f"/api/projects/{project.id}/render")
    assert r.status_code == 429 and "spend cap" in r.json()["detail"]
    assert queued == []


def test_unknown_project_actions_404_not_500(queued):
    assert client.post("/api/projects/abcdef0123/render").status_code == 404
    assert client.post("/api/projects/abcdef0123/cast", json={"name": "x"}).status_code == 404


def test_files_never_serve_sources_or_state(project):
    d = config.DATA / project.id
    (d / "sources").mkdir(exist_ok=True)
    (d / "sources" / "private.pdf").write_bytes(b"secret")
    (d / "out").mkdir(exist_ok=True)
    (d / "out" / "video.mp4").write_bytes(b"video")
    assert client.get(f"/files/{project.id}/out/video.mp4").content == b"video"
    assert client.get(f"/files/{project.id}/sources/private.pdf").status_code == 404
    assert client.get(f"/files/{project.id}/project.json").status_code == 404


def test_cors_is_configurable():
    assert appmod.app.user_middleware  # CORS middleware present


def test_reading_a_stale_busy_project_fails_it_with_a_message(project):
    import time
    store.mutate(project.id, lambda p: setattr(p, "render_status", "rendering scenes"))
    doc = store.backend().get(project.id)
    doc["updated"] = time.time() - 4000
    store.backend().put(project.id, doc)
    body = client.get(f"/api/projects/{project.id}").json()
    assert body["render_status"] == "error" and "Render video" in body["render_error"]
