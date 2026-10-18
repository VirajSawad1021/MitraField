"""Project state.

Two interchangeable backends behind one small API (`load`, `save`, `mutate`, `list_all`, `delete`):

* file       data/projects/<id>/project.json. Zero setup, used for local development and tests.
* firestore  one document per project, shared by every API and worker instance. `mutate` is a
             transaction, so concurrent workers (one per beat) never overwrite each other.

Media (clips, audio, stills) always lives on the filesystem under `pdir(pid)`, which is a Cloud
Storage volume mounted at the same path in every service. Absolute paths inside a project are
stored relative to config.DATA so a project moves between machines unchanged.

The per-project cost ledger and the global spend counters live here too: they are written by many
workers at once and are read by the spend guard (see costs.py).
"""
import json
import threading
import time
from datetime import datetime, UTC
from pathlib import Path

from . import config
from .models import Project

_TOKEN = "${DATA}"


# ------------------------------------------------------------------ path portability

def _walk(x, fn):
    if isinstance(x, str):
        return fn(x)
    if isinstance(x, list):
        return [_walk(i, fn) for i in x]
    if isinstance(x, dict):
        return {k: _walk(v, fn) for k, v in x.items()}
    return x


def encode(doc):
    root = str(config.DATA)
    return _walk(doc, lambda s: _TOKEN + s[len(root):] if s.startswith(root + "/") else s)


def decode(doc):
    root = str(config.DATA)
    return _walk(doc, lambda s: root + s[len(_TOKEN):] if s.startswith(_TOKEN + "/") else s)


def _today():
    return datetime.now(UTC).strftime("%Y%m%d")


# ------------------------------------------------------------------ file backend

class FileBackend:
    def __init__(self):
        self._lock = threading.RLock()

    def _f(self, pid):
        return config.DATA / pid / "project.json"

    def get(self, pid):
        with self._lock:
            return json.loads(self._f(pid).read_text())

    def put(self, pid, doc):
        with self._lock:
            f = self._f(pid)
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(doc, indent=2))
            tmp.replace(f)

    def txn(self, pid, fn):
        with self._lock:
            doc = fn(self.get(pid))
            self.put(pid, doc)
            return doc

    def delete(self, pid):
        import shutil
        shutil.rmtree(config.DATA / pid, ignore_errors=True)

    def list(self):
        out = []
        for f in sorted(config.DATA.glob("*/project.json"), key=lambda f: -f.stat().st_mtime):
            try:
                out.append(json.loads(f.read_text()))
            except ValueError:
                pass
        return out

    # cost ledger and spend counters
    def add_cost(self, pid, row):
        with self._lock:
            spend = self._spend()   # before the ledger line is written: a first-time rebuild reads the ledgers
            d = config.DATA / pid
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "costs.jsonl", "a") as f:
                f.write(json.dumps(row) + "\n")
            for key in (f"p:{pid}", f"d:{_today()}"):
                s = spend.setdefault(key, {"total": 0.0, "calls": 0, "by_kind": {}})
                s["total"] += row["usd"]
                s["calls"] += 1
                s["by_kind"][row["kind"]] = s["by_kind"].get(row["kind"], 0) + row["usd"]
            (config.DATA / ".spend.json").write_text(json.dumps(spend))

    def _spend(self):
        f = config.DATA / ".spend.json"
        return json.loads(f.read_text()) if f.exists() else self._rebuild_spend()

    def _rebuild_spend(self):
        """First use on an existing data dir: derive per-project totals from the ledgers on disk."""
        spend = {}
        for led in config.DATA.glob("*/costs.jsonl"):
            s = spend.setdefault(f"p:{led.parent.name}", {"total": 0.0, "calls": 0, "by_kind": {}})
            for line in led.read_text().splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                s["total"] += r["usd"]
                s["calls"] += 1
                s["by_kind"][r["kind"]] = s["by_kind"].get(r["kind"], 0) + r["usd"]
        return spend

    def spend(self, key):
        with self._lock:
            return self._spend().get(key) or {"total": 0.0, "calls": 0, "by_kind": {}}


# ------------------------------------------------------------------ firestore backend

class FirestoreBackend:
    """projects/{pid}      {data: <project json>, updated, render_status}
       projects/{pid}/costs/{auto}   one row per billable call (audit trail, write-only)
       spend/{p:<pid> | d:<yyyymmdd>} running totals the spend guard reads in one get()

    The project is one JSON string, not a map: engine params contain nested arrays (coordinates,
    chart series) which Firestore does not allow, and a project never approaches the 1 MiB limit."""

    def __init__(self):
        from google.cloud import firestore
        self.fs = firestore
        self.db = firestore.Client(project=config.GCP_PROJECT or None)
        self.col = self.db.collection("projects")

    @staticmethod
    def _pack(doc):
        return {"data": json.dumps(doc), "updated": doc.get("updated", 0), "render_status": doc.get("render_status", "")}

    def get(self, pid):
        snap = self.col.document(pid).get()
        if not snap.exists:
            raise FileNotFoundError(pid)
        return json.loads(snap.get("data"))

    def put(self, pid, doc):
        self.col.document(pid).set(self._pack(doc))

    def txn(self, pid, fn):
        """Read-modify-write in a transaction. Many workers (one per beat) update the same project at
        once, so a transaction can be aborted by contention: retry with jittered exponential backoff
        on top of the client's own few attempts. Callers should not hold work that is not idempotent in fn."""
        import random

        from google.api_core import exceptions as gex
        ref = self.col.document(pid)

        @self.fs.transactional
        def run(t):
            snap = ref.get(transaction=t)
            if not snap.exists:
                raise FileNotFoundError(pid)
            doc = fn(json.loads(snap.get("data")))
            t.set(ref, self._pack(doc))
            return doc

        for attempt in range(12):
            try:
                return run(self.db.transaction())
            except (gex.Aborted, gex.Conflict, gex.DeadlineExceeded, ValueError) as e:
                # the client gives up with ValueError("Failed to commit transaction in N attempts") on contention
                if isinstance(e, ValueError) and not isinstance(e.__cause__, (gex.Aborted, gex.Conflict, gex.DeadlineExceeded)):
                    raise
                if attempt == 11:
                    raise
                time.sleep(random.uniform(0.05, 0.25) * min(2 ** attempt, 16))

    def delete(self, pid):
        import shutil
        for c in self.col.document(pid).collection("costs").stream():
            c.reference.delete()
        self.col.document(pid).delete()
        shutil.rmtree(config.DATA / pid, ignore_errors=True)

    def list(self):
        q = self.col.order_by("updated", direction=self.fs.Query.DESCENDING).limit(200)
        return [json.loads(s.get("data")) for s in q.stream()]

    def add_cost(self, pid, row):
        self.col.document(pid).collection("costs").add(row)
        inc = self.fs.Increment
        for key in (f"p:{pid}", f"d:{_today()}"):
            self.db.collection("spend").document(key).set(
                {"total": inc(row["usd"]), "calls": inc(1), "by_kind": {row["kind"]: inc(row["usd"])}}, merge=True)

    def spend(self, key):
        snap = self.db.collection("spend").document(key).get()
        return snap.to_dict() if snap.exists else {"total": 0.0, "calls": 0, "by_kind": {}}


_backend = None
_backend_lock = threading.Lock()


def backend():
    global _backend
    with _backend_lock:
        if _backend is None:
            _backend = FirestoreBackend() if config.STORE == "firestore" else FileBackend()
        return _backend


def use(b):
    """Swap the backend (tests)."""
    global _backend
    _backend = b


# ------------------------------------------------------------------ public API

def pdir(pid) -> Path:
    d = config.DATA / pid
    d.mkdir(parents=True, exist_ok=True)
    return d


def exists(pid) -> bool:
    try:
        backend().get(pid)
        return True
    except FileNotFoundError:
        return False


def load(pid) -> Project:
    return Project.model_validate(decode(backend().get(pid)))


def save(p: Project) -> Project:
    p.updated = time.time()
    p.created = p.created or p.updated
    backend().put(p.id, encode(p.model_dump(mode="json")))
    return p


def mutate(pid, fn):
    """Load, apply fn(project), save, as one atomic step. fn may run more than once (a transaction
    retries on contention), so it must only change the project it is given."""
    def apply(doc):
        p = Project.model_validate(decode(doc))
        fn(p)
        p.updated = time.time()
        p.created = p.created or p.updated
        return encode(p.model_dump(mode="json"))
    return Project.model_validate(decode(backend().txn(pid, apply)))


def delete(pid):
    backend().delete(pid)


def list_all():
    return [decode(d) for d in backend().list()]


def scene(p: Project, sid):
    for s in p.scenes:
        if s.id == sid:
            return s
    raise KeyError(sid)


# cost ledger / spend counters (used by costs.py)
def add_cost(pid, row):
    backend().add_cost(pid, row)


def spend(key):
    return backend().spend(key)
