"""Shared pycairo drawing kit: easing, text layout, frame loop."""
import math

import cairo

from .. import config
from ..media import FrameWriter, hex_rgb

BG, INK, MUTED, ACCENT, ACCENT2 = (hex_rgb(c) for c in (config.BG, config.INK, config.MUTED, config.ACCENT, config.ACCENT2))


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


def text(ctx, s, x, y, size, color, alpha=1.0, family="Inter", bold=True, anchor="c"):
    if alpha <= 0 or not s:
        return 0
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
        if cur and ctx.text_extents(t).x_advance > max_w:
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


def render_frames(draw, duration, size, out):
    """draw(ctx, t, W, H) per frame; background is cleared for you."""
    W, H = size
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
            draw(ctx, f / config.FPS, W, H)
            ctx.restore()
            surf.flush()
            fw.write(bytes(surf.get_data()))
    return out
