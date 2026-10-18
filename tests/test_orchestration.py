"""The fan-out / fan-in that replaced the in-process thread pool."""
import threading

from backend import cast, jobs, pipeline, store, tasks


def _ready(pid, sid):
    store.mutate(pid, lambda p: setattr(store.scene(p, sid), "status", "ready"))


def test_render_all_fans_out_one_job_per_beat(project, monkeypatch):
    sent = []
    monkeypatch.setattr(cast, "ensure", lambda pid, **k: None)
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: sent.append((kind, p)))
    pipeline.render_all(project.id)
    assert [k for k, _ in sent] == ["render_scene"] * 3
    assert all(p["then_assemble"] for _, p in sent)
    p = store.load(project.id)
    assert p.render_status == "rendering scenes" and {s.status for s in p.scenes} == {"queued"}


def test_only_the_last_beat_triggers_assembly(project, monkeypatch):
    sent = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: sent.append(kind))
    store.mutate(project.id, lambda p: (setattr(p, "render_status", "rendering scenes"), [setattr(s, "status", "queued") for s in p.scenes]))
    for sid in ("s0", "s1"):
        _ready(project.id, sid)
        pipeline.maybe_assemble(project.id)
    assert sent == []
    _ready(project.id, "s2")
    pipeline.maybe_assemble(project.id)
    assert sent == ["assemble"] and store.load(project.id).render_status == "assembling"


def test_concurrent_finishers_claim_assembly_exactly_once(project, monkeypatch):
    sent = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: sent.append(kind))
    store.mutate(project.id, lambda p: (setattr(p, "render_status", "rendering scenes"), [setattr(s, "status", "ready") for s in p.scenes]))
    ts = [threading.Thread(target=pipeline.maybe_assemble, args=(project.id,)) for _ in range(12)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sent == ["assemble"]


def test_a_redelivered_beat_job_does_not_assemble_twice(project, monkeypatch):
    sent = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: sent.append(kind))
    monkeypatch.setattr(pipeline, "render_scene", lambda pid, sid, force=False: _ready(pid, sid))
    store.mutate(project.id, lambda p: (setattr(p, "render_status", "rendering scenes"), [setattr(s, "status", "queued") for s in p.scenes]))
    for sid in ("s0", "s1", "s2", "s2", "s2"):   # Cloud Tasks is at-least-once
        tasks.render_scene(project.id, sid, then_assemble=True)
    assert sent == ["assemble"]


def test_failed_beats_still_let_the_project_finish(project, monkeypatch):
    sent = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: sent.append(kind))
    store.mutate(project.id, lambda p: (setattr(p, "render_status", "rendering scenes"),
                                        [setattr(s, "status", "error" if s.id == "s1" else "ready") for s in p.scenes]))
    pipeline.maybe_assemble(project.id)
    assert sent == ["assemble"]


def test_single_beat_render_never_assembles(project, monkeypatch):
    sent = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: sent.append(kind))
    monkeypatch.setattr(pipeline, "render_scene", lambda pid, sid, force=False: _ready(pid, sid))
    tasks.render_scene(project.id, "s0")
    assert sent == []


def test_every_enqueued_kind_has_a_handler():
    import re
    from pathlib import Path
    src = (Path(__file__).parent.parent / "backend").glob("*.py")
    kinds = {m for f in src for m in re.findall(r'enqueue\("([a-z_]+)"', f.read_text())}
    assert kinds and kinds <= set(jobs.HANDLERS), kinds - set(jobs.HANDLERS)
