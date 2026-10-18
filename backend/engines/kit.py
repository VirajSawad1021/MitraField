"""Shared pycairo drawing kit: easing, text layout, frame loop."""

import cairo

from .. import config
from ..media import FrameWriter, hex_rgb

import contextvars
from contextlib import contextmanager

from ..look import palette as look_palette

_palette = contextvars.ContextVar("palette", default=None)


class _Colour:
    """A palette colour resolved at draw time, so code engines follow the project's look.
    Behaves like an (r, g, b) tuple wherever colours are used."""

    def __init__(self, key):
        self.key = key

    def rgb(self):
        return hex_rgb((_palette.get() or look_palette(None))[self.key])

    def __getitem__(self, i):
        return self.rgb()[i]

    def __iter__(self):
        return iter(self.rgb())

    def __len__(self):
        return 3

    def __eq__(self, other):
        return isinstance(other, _Colour) and other.key == self.key

    def __hash__(self):
        return hash(self.key)


BG, INK, MUTED, ACCENT, ACCENT2 = (_Colour(k) for k in ("bg", "ink", "muted", "accent", "accent2"))


@contextmanager
def use_palette(look):
    tok = _palette.set(look_palette(look))
    try:
        yield
    finally:
        _palette.reset(tok)


def is_paper():
    return bool((_palette.get() or look_palette(None))["paper"])


def neutral():
    """A quiet secondary fill (e.g. non-highlighted bars) that works on dark and paper grounds."""
    if is_paper():
        return (0.70, 0.67, 0.62)
    m, b = MUTED.rgb(), BG.rgb()
    return tuple(0.55 * x + 0.45 * y for x, y in zip(m, b))


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def ramp(t, a, b):
    return ease((t - a) / max(1e-6, b - a))


def rgba(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], a)


def font(ctx, size, family="Inter", bold=True):
    ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


# ---- non-Latin scripts: cairo's toy text API has no font fallback or shaping, so text in
# Devanagari, Tamil, Bengali, Thai or CJK is laid out with HarfBuzz (PIL + raqm) using Noto fonts.
from functools import lru_cache
from pathlib import Path

_NOTO_DIRS = [Path.home() / ".local/share/fonts/noto", Path("/usr/share/fonts/truetype/noto-mitrafield")]
_SCRIPTS = [((0x0900, 0x097F), "NotoSansDevanagari"), ((0x0980, 0x09FF), "NotoSansBengali"),
            ((0x0B80, 0x0BFF), "NotoSansTamil"), ((0x0E00, 0x0E7F), "NotoSansThai"),
            ((0x3040, 0x30FF), "NotoSansJP"), ((0xAC00, 0xD7AF), "NotoSansKR"), ((0x4E00, 0x9FFF), "NotoSansSC")]


def needs_shaping(s):
    return any(ord(ch) > 0x024F and not ch.isspace() for ch in s or "")


def _noto_for(s):
    codes = [ord(c) for c in s]
    if any(0x3040 <= c <= 0x30FF for c in codes):
        name = "NotoSansJP"
    else:
        name = next((n for (lo, hi), n in _SCRIPTS if any(lo <= c <= hi for c in codes)), "NotoSansSC")
    for d in _NOTO_DIRS:
        if (d / f"{name}.ttf").exists():
            return str(d / f"{name}.ttf")
    return None


@lru_cache(maxsize=64)
def _pil_font(path, size, bold):
    from PIL import ImageFont
    f = ImageFont.truetype(path, max(8, int(size)), layout_engine=ImageFont.Layout.RAQM)
    try:
        axes = f.get_variation_axes()
        f.set_variation_by_axes([700 if bold and a.get("name", b"") in (b"Weight", "Weight") else a["default"] for a in axes])
    except Exception:
        pass
    return f


def measure(ctx, s, size, family="Inter", bold=True):
    """Advance width of s in px, for any script."""
    if needs_shaping(s):
        path = _noto_for(s)
        if path:
            return _pil_font(path, size, bold).getlength(s)
    font(ctx, size, family, bold)
    return ctx.text_extents(s).x_advance


def _shaped_text(ctx, s, x, y, size, color, alpha, bold, anchor):
    from PIL import Image, ImageDraw
    import numpy as np
    path = _noto_for(s)
    if not path:
        return 0
    f = _pil_font(path, size, bold)
    l, t, r, b = f.getbbox(s, anchor="ls")
    pad = int(size * 0.3)
    w, h = int(r - l) + 2 * pad, int(b - t) + 2 * pad
    img = Image.new("L", (max(1, w), max(1, h)), 0)
    ImageDraw.Draw(img).text((pad - l, pad - t), s, font=f, fill=255, anchor="ls")
    a = (np.asarray(img, np.float32) / 255.0) * alpha
    rgb = [c for c in color]
    buf = np.zeros((h, w, 4), np.uint8)
    buf[..., 0] = (rgb[2] * 255 * a).astype(np.uint8)   # cairo ARGB32 is premultiplied BGRA
    buf[..., 1] = (rgb[1] * 255 * a).astype(np.uint8)
    buf[..., 2] = (rgb[0] * 255 * a).astype(np.uint8)
    buf[..., 3] = (255 * a).astype(np.uint8)
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    data = bytearray(stride * h)
    np.frombuffer(data, np.uint8).reshape(h, stride)[:, :w * 4] = buf.reshape(h, w * 4)
    surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, w, h, stride)
    adv = f.getlength(s)
    left = {"c": x - adv / 2, "l": x, "r": x - adv}[anchor]
    ctx.save()
    ctx.set_source_surface(surf, left + l - pad, y + t - pad)
    ctx.paint()
    ctx.restore()
    return adv


def text(ctx, s, x, y, size, color, alpha=1.0, family="Inter", bold=True, anchor="c"):
    if alpha <= 0 or not s:
        return 0
    if needs_shaping(s):
        return _shaped_text(ctx, s, x, y, size, color, alpha, bold, anchor)
    font(ctx, size, family, bold)
    e = ctx.text_extents(s)
    dx = {"c": -e.width / 2 - e.x_bearing, "l": -e.x_bearing, "r": -e.width - e.x_bearing}[anchor]
    ctx.move_to(x + dx, y)
    rgba(ctx, color, alpha)
    ctx.show_text(s)
    ctx.new_path()
    return e.x_advance


def wrap(ctx, s, size, max_w, family="Inter", bold=True):
    font(ctx, size, family, bold)
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if cur and measure(ctx, t, size, family, bold) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def fit_size(ctx, s, size, max_w, max_lines, family="Inter", bold=True):
    while size > 20:
        ls = wrap(ctx, s, size, max_w, family, bold)
        if len(ls) <= max_lines:
            return size, ls
        size *= 0.9
    return size, wrap(ctx, s, size, max_w, family, bold)


def clean(s):
    """House rule: no em dashes on screen."""
    return (s or "").replace("—", ", ").replace("–", "-").strip()


def _paper_texture(W, H):
    """Subtle fibre/grain overlay for paper looks, generated once per clip."""
    import numpy as np
    rng = np.random.default_rng(7)
    small = rng.normal(0, 1, (H // 4 + 1, W // 4 + 1)).astype(np.float32)
    import cv2
    n = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC) * 0.6 + rng.normal(0, 1, (H, W)).astype(np.float32) * 0.4
    a = np.clip(np.abs(n) * 10, 0, 22).astype(np.uint8)          # alpha up to ~9%
    buf = np.zeros((H, W, 4), np.uint8)
    buf[..., 3] = a
    buf[..., :3] = (np.where(n[..., None] > 0, 255, 0) * (a[..., None] / 255.0)).astype(np.uint8)   # premultiplied
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, W)
    data = bytearray(stride * H)
    arr = np.frombuffer(data, np.uint8).reshape(H, stride)[:, :W * 4].reshape(H, W, 4)
    arr[:] = buf
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, W, H, stride), data


def render_frames(draw, duration, size, out):
    """draw(ctx, t, W, H) per frame; background (and paper grain on paper looks) is drawn for you."""
    W, H = size
    paper = _paper_texture(W, H) if is_paper() else None
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    n = max(1, int(round(duration * config.FPS)))
    with FrameWriter(out, size, "bgra") as fw:
        for f in range(n):
            ctx.save()
            rgba(ctx, BG)
            ctx.paint()
            if paper:
                ctx.set_source_surface(paper[0], 0, 0)
                ctx.paint()
            draw(ctx, f / config.FPS, W, H)
            ctx.restore()
            surf.flush()
            fw.write(bytes(surf.get_data()))
    return out
