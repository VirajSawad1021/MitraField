import threading
import time

import pytest

from backend import config, store
from backend.models import Project


def test_paths_are_stored_relative_to_data_and_restored():
    p = Project(id="0123456789", topic="x")
    clip = str(config.DATA / "0123456789" / "a.mp4")
    doc = {"clip": clip, "params": {"nested": [clip, 1, None]}, "other": "/etc/hosts"}
    enc = store.encode(doc)
    assert enc["clip"] == "${DATA}/0123456789/a.mp4"
    assert enc["params"]["nested"][0] == "${DATA}/0123456789/a.mp4"
    assert enc["other"] == "/etc/hosts"
    assert store.decode(enc) == doc
    assert p.id


def test_saved_project_is_portable_between_data_dirs(project, tmp_path, monkeypatch):
    def put(p):
        p.scenes[0].clip = str(config.DATA / project.id / "scenes" / "c.mp4")
    project = store.mutate(project.id, put)
    raw = (config.DATA / project.id / "project.json").read_text()
    assert str(config.DATA) not in raw
    monkeypatch.setattr(config, "DATA", tmp_path / "elsewhere")
    (config.DATA / project.id).mkdir(parents=True)
    (config.DATA / project.id / "project.json").write_text(raw)
    assert store.load(project.id).scenes[0].clip == str(tmp_path / "elsewhere" / project.id / "scenes" / "c.mp4")


def test_load_missing_raises():
    with pytest.raises(FileNotFoundError):
        store.load("ffffffffff")
    assert not store.exists("ffffffffff")


def test_mutate_is_atomic_under_contention(project):
    def bump(p):
        p.pace = round(p.pace + 0.001, 6)
    ts = [threading.Thread(target=lambda: [store.mutate(project.id, bump) for _ in range(20)]) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert store.load(project.id).pace == pytest.approx(1.0 + 160 * 0.001)


def test_list_all_newest_first_and_delete(project):
    time.sleep(0.01)
    other = store.save(Project(id="1111111111", topic="newer"))
    assert [d["id"] for d in store.list_all()][:2] == [other.id, project.id]
    store.delete(other.id)
    assert [d["id"] for d in store.list_all()] == [project.id]


def test_spend_counters_accumulate_per_project_and_day(project):
    store.add_cost(project.id, {"t": 1, "kind": "voice", "model": "m", "usd": 0.25, "note": ""})
    store.add_cost(project.id, {"t": 2, "kind": "image", "model": "m", "usd": 0.75, "note": ""})
    s = store.spend(f"p:{project.id}")
    assert s["total"] == pytest.approx(1.0) and s["calls"] == 2 and s["by_kind"]["image"] == pytest.approx(0.75)
    assert store.spend(f"d:{store._today()}")["total"] == pytest.approx(1.0)


def test_spend_rebuilds_from_existing_ledgers(project):
    (config.DATA / project.id / "costs.jsonl").write_text('{"kind":"text","usd":0.5}\nnot json\n{"kind":"voice","usd":0.5}\n')
    assert store.spend(f"p:{project.id}")["total"] == pytest.approx(1.0)
