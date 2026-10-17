"""Cast & Sets: recurring characters, locations, objects and one art style per project.

Each item gets a reference image once; generative engines receive the references for the
items in a beat (plus the style), so the same presenter, place or object looks the same
in every shot and Veo can animate from an on-model first frame.
"""
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import costs, gemini, store
from .models import CastItem, Project, Scene

_lock = threading.Lock()
_ensure_lock = threading.Lock()   # concurrent beats must not generate the same reference twice

PROMPTS = {
    "style": ("Style frame that defines the art direction for an explainer video about \"{t}\": {d}. "
              "Show a representative moment from that topic in this exact style. No text, no logos."),
    "character": ("Character reference sheet for '{n}': {d}. Full body, front view, neutral friendly pose, "
                  "plain light grey background, no text."),
    "location": "Establishing shot of '{n}': {d}. No people in focus, no text.",
    "object": "Reference image of '{n}': {d}. Centered on a plain light background, no text.",
}


def style_item(p: Project):
    return next((c for c in p.cast if c.kind == "style"), None)


@costs.tracked
def generate(pid, cid):
    """(Re)generate one item's reference image. Non-style items use the style as a reference."""
    with _lock:
        p = store.load(pid)
        item = next(c for c in p.cast if c.id == cid)
        store.mutate(pid, lambda pp: _set(pp, cid, status="generating", error=None))
    try:
        refs = []
        st = style_item(p)
        if item.kind != "style" and st and st.image and Path(st.image).exists():
            refs.append(("the art style to match", st.image))
        out = store.pdir(pid) / "cast" / f"{cid}_{hashlib.sha1(item.description.encode()).hexdigest()[:6]}.png"
        aspect = "1:1" if item.kind in ("character", "object") else ("9:16" if p.aspect == "9:16" else "16:9")
        gemini.image(PROMPTS[item.kind].format(n=item.name, d=item.description, t=p.topic), out, aspect=aspect, refs=refs)
        store.mutate(pid, lambda pp: _set(pp, cid, image=str(out), status="ready"))
    except Exception as e:
        store.mutate(pid, lambda pp: _set(pp, cid, status="error", error=str(e)[:300]))
        raise


def _set(p, cid, **kw):
    for c in p.cast:
        if c.id == cid:
            for k, v in kw.items():
                setattr(c, k, v)


@costs.tracked
def ensure(pid, retry_errors=True):
    """Generate every missing reference: style first (others are drawn in its style)."""
    with _ensure_lock:
        _ensure(pid, retry_errors)


def _ensure(pid, retry_errors):
    p = store.load(pid)
    skip = {"generating"} | (set() if retry_errors else {"error"})
    todo = [c for c in p.cast if not (c.image and Path(c.image).exists()) and c.status not in skip]
    styles = [c for c in todo if c.kind == "style"]
    for c in styles:
        try:
            generate(pid, c.id)
        except Exception:
            pass
    rest = [c.id for c in todo if c.kind != "style"]
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(costs.bind(lambda cid: _safe(pid, cid)), rest))


def _safe(pid, cid):
    try:
        generate(pid, cid)
    except Exception as e:
        print(f"[cast] {cid} failed: {e}", flush=True)


def refs_for(p: Project, scene: Scene, include_style=True):
    """(label, path) pairs for this beat: its cast items, then the style."""
    out = []
    by_id = {c.id: c for c in p.cast}
    for cid in scene.cast:
        c = by_id.get(cid)
        if c and c.kind != "style" and c.image and Path(c.image).exists():
            out.append((f"{c.name} ({c.kind}). Keep its exact design", c.image))
    st = style_item(p)
    if include_style and st and st.image and Path(st.image).exists():
        out.append(("the art style to match", st.image))
    return out


def describe(p: Project, scene: Scene):
    """Text that tells the image model who/what is in the shot."""
    by_id = {c.id: c for c in p.cast}
    items = [by_id[c] for c in scene.cast if c in by_id and by_id[c].kind != "style"]
    st = style_item(p)
    bits = [f"{c.name} ({c.kind}): {c.description}" for c in items]
    text = ("Featuring, exactly as in the reference images: " + "; ".join(bits) + ". ") if bits else ""
    if st:
        text += f"Art style: {st.description}. "
    return text


def signature(p: Project, scene: Scene):
    """Changes when any reference this beat depends on changes (for render caching)."""
    return [(c[0], c[1]) for c in refs_for(p, scene)]


def main_character(p: Project):
    return next((c for c in p.cast if c.kind == "character"), None)


def merge(p: Project, proposed: list[dict]):
    """Adopt the director's cast, keeping existing items (and their images) with the same name."""
    old = {c.name.lower(): c for c in p.cast}
    cast = []
    for it in proposed:
        prev = old.get(it["name"].lower())
        if prev and prev.description == it.get("description", prev.description):
            cast.append(prev)
        else:
            cast.append(CastItem(kind=it["kind"], name=it["name"], description=it.get("description", "")))
    p.cast = cast
    return {c.name.lower(): c.id for c in cast}
