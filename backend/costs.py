"""Per-project cost ledger.

Every billable call is priced from Google's published paid-tier rates and appended to
the store (see store.py). The project in scope is carried in a context variable;
`bind` carries it into worker threads.
"""
import contextvars
import time
from contextlib import contextmanager

from . import config, store

# USD, Gemini API paid tier (ai.google.dev/gemini-api/docs/pricing, checked 2026-10-17).
TOKENS = {   # per 1M tokens: (input, output incl. thinking)
    "pro": (2.00, 12.00),
    "flash": (0.75, 3.75),   # 3.5 Flash is not listed; priced at the listed 3.8 Flash rate (an upper bound)
}
IMAGE = {"gemini-3.1-flash-image": 0.067, "gemini-3-pro-image": 0.134}   # per 1K image
VEO_PER_SECOND = {"veo-3.1-generate-preview": 0.40, "veo-3.1-fast-generate-preview": 0.10,
                  "veo-3.1-lite-generate-preview": 0.05,
                  "veo-3.1-generate-001": 0.40, "veo-3.1-fast-generate-001": 0.10, "veo-3.1-lite-generate-001": 0.05}   # Vertex ids                    # 720p
TTS_PER_SECOND = 0.000225          # gemini-3.8-flash-tts audio output
MUSIC_PER_CLIP = 0.04              # Lyria 3 clip

_project = contextvars.ContextVar("cost_project", default=None)


@contextmanager
def track(pid):
    tok = _project.set(pid)
    try:
        yield
    finally:
        _project.reset(tok)


def tracked(fn):
    """Decorator for job entry points whose first argument is the project id."""
    import functools

    @functools.wraps(fn)
    def run(pid, *a, **kw):
        with track(pid):
            return fn(pid, *a, **kw)
    return run


def bind(fn):
    """Wrap fn so it runs with the caller's cost context, from any thread."""
    parent = contextvars.copy_context()
    return lambda *a, **kw: parent.copy().run(fn, *a, **kw)


class BudgetExceeded(RuntimeError):
    """A billable call was refused because a spend cap has been reached."""


_cache = {}


def _spend(key, ttl=5.0):
    """Running total for a project or a day. Cached for a few seconds: the guard runs before every
    billable call and must not turn each one into extra database reads."""
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    v = store.spend(key)
    _cache[key] = (time.time(), v)
    return v


def guard():
    """Raise BudgetExceeded when today's total, or the current project's total, is over its cap."""
    day = _spend(f"d:{store._today()}")["total"]
    if day >= config.CAP_DAY_USD:
        raise BudgetExceeded(f"The daily spend cap (${config.CAP_DAY_USD:.2f}) has been reached. Try again tomorrow.")
    pid = _project.get()
    if pid and _spend(f"p:{pid}")["total"] >= config.CAP_PROJECT_USD:
        raise BudgetExceeded(f"This project has reached its spend cap (${config.CAP_PROJECT_USD:.2f}).")


def add(kind, usd, model="", note=""):
    pid = _project.get()
    if not pid:
        return
    row = {"t": round(time.time(), 1), "kind": kind, "model": model, "usd": round(usd, 5), "note": note}
    store.add_cost(pid, row)
    for key in (f"p:{pid}", f"d:{store._today()}"):
        _cache.pop(key, None)


def tokens(model, usage, note=""):
    if usage is None:
        return
    tin = usage.prompt_token_count or 0
    tout = (usage.candidates_token_count or 0) + (getattr(usage, "thoughts_token_count", 0) or 0)
    pin, pout = TOKENS["pro" if "pro" in model else "flash"]
    add("text", tin / 1e6 * pin + tout / 1e6 * pout, model, note or f"{tin} in / {tout} out tokens")


def summary(pid):
    r = store.spend(f"p:{pid}")
    by = r.get("by_kind") or {}
    return {"total": round(r.get("total", 0.0), 4), "by_kind": {k: round(v, 4) for k, v in sorted(by.items(), key=lambda x: -x[1])},
            "calls": int(r.get("calls", 0))}
