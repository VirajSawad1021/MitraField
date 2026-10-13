"""Projects on disk: data/projects/<id>/project.json + assets beside it."""
import json
import threading
import time
from pathlib import Path

from . import config
from .models import Project

_lock = threading.RLock()


def pdir(pid) -> Path:
    d = config.DATA / pid
    d.mkdir(parents=True, exist_ok=True)
    return d


def load(pid) -> Project:
    with _lock:
        return Project.model_validate_json((config.DATA / pid / "project.json").read_text())


def save(p: Project) -> Project:
    with _lock:
        p.updated = time.time()
        p.created = p.created or p.updated
        f = pdir(p.id) / "project.json"
        tmp = f.with_suffix(".tmp")
        tmp.write_text(p.model_dump_json(indent=2))
        tmp.replace(f)
        return p


def mutate(pid, fn):
    """Load, apply fn(project), save; atomic w.r.t. other mutators."""
    with _lock:
        p = load(pid)
        fn(p)
        return save(p)


def list_all():
    out = []
    for f in sorted(config.DATA.glob("*/project.json"), key=lambda f: -f.stat().st_mtime):
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            pass
    return out


def scene(p: Project, sid):
    for s in p.scenes:
        if s.id == sid:
            return s
    raise KeyError(sid)
