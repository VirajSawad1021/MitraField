"""Runs only against the Firestore emulator (CI starts one; locally: firebase emulators:exec --only firestore ...)."""
import os
import threading

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="no Firestore emulator")

from backend import store  # noqa: E402
from backend.models import Project, Scene  # noqa: E402


@pytest.fixture
def fs(monkeypatch):
    from backend import config
    monkeypatch.setattr(config, "GCP_PROJECT", "demo-mitrafield")
    b = store.FirestoreBackend()
    for d in b.col.stream():
        b.delete(d.id)
    store.use(b)
    return b


def test_roundtrip_with_nested_arrays(fs):
    p = Project(id="aaaaaaaaaa", topic="t", scenes=[Scene(id="s1", narration="n", params={"route": [[1.0, 2.0], [3.0, 4.0]]})])
    store.save(p)
    assert store.load("aaaaaaaaaa").scenes[0].params["route"] == [[1.0, 2.0], [3.0, 4.0]]


def test_transactions_do_not_lose_updates_across_threads(fs):
    store.save(Project(id="bbbbbbbbbb", topic="t"))
    ts = [threading.Thread(target=lambda: [store.mutate("bbbbbbbbbb", lambda p: setattr(p, "pace", p.pace + 1)) for _ in range(5)])
          for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert store.load("bbbbbbbbbb").pace == 31


def test_missing_and_list_order(fs):
    with pytest.raises(FileNotFoundError):
        store.load("cccccccccc")
    a = store.save(Project(id="dddddddddd", topic="a"))
    b = store.save(Project(id="eeeeeeeeee", topic="b"))
    assert [d["id"] for d in store.list_all()] == [b.id, a.id]


def test_spend_counters(fs):
    store.save(Project(id="ffffffffff", topic="t"))
    store.add_cost("ffffffffff", {"t": 1, "kind": "video", "model": "veo", "usd": 0.4, "note": ""})
    store.add_cost("ffffffffff", {"t": 2, "kind": "video", "model": "veo", "usd": 0.4, "note": ""})
    s = store.spend("p:ffffffffff")
    assert s["total"] == pytest.approx(0.8) and s["calls"] == 2 and s["by_kind"]["video"] == pytest.approx(0.8)
    store.delete("ffffffffff")
    with pytest.raises(FileNotFoundError):
        store.load("ffffffffff")
