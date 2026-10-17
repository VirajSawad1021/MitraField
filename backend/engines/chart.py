"""Data charts drawn by code: bars that grow and count up, or a line that draws itself.
Every number comes from the plan (taken from the narration or sources), never from pixels."""
import math

from .base import Engine
from .kit import ACCENT, ACCENT2, INK, MUTED, clean, ease, ease_out, ramp, render_frames, rgba, text


def fmt(v, unit=""):
    a = abs(v)
    s = f"{v / 1e9:.1f}B" if a >= 1e9 else f"{v / 1e6:.1f}M" if a >= 1e6 else f"{v / 1e3:.1f}K" if a >= 1e4 else (
        f"{v:,.0f}" if a >= 100 or float(v).is_integer() else f"{v:.1f}")
    s = s.replace(".0B", "B").replace(".0M", "M").replace(".0K", "K")
    return f"{unit}{s}" if unit in ("$", "€", "£", "₹") else f"{s}{unit}"


class ChartEngine(Engine):
    name = "chart"
    label = "Data chart"
    precise = True
    blurb = ("Animated data chart from real numbers: bars that grow and count up to compare quantities, or a line "
             "that draws a trend over time. Use whenever the narration compares amounts, shares, rankings or a change "
             "over years. Numbers must come from the narration or sources.")
    params_schema = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["bar", "line"]},
            "title": {"type": "string", "description": "short chart title, max 6 words"},
            "unit": {"type": "string", "description": "e.g. '%', '$', ' km', ' million barrels'"},
            "bars": {"type": "array", "description": "for bar charts, 2-7 items", "items": {"type": "object", "properties": {
                "label": {"type": "string"}, "value": {"type": "number"}, "highlight": {"type": "boolean"}},
                "required": ["label", "value"]}},
            "x_labels": {"type": "array", "items": {"type": "string"}, "description": "for line charts, e.g. years"},
            "values": {"type": "array", "items": {"type": "number"}, "description": "for line charts, one per x label"},
            "source": {"type": "string", "description": "where the numbers come from, short, may be empty"},
        },
        "required": ["kind", "title"],
    }
    plan_guide = ("Use only numbers stated in the narration, brief or the user's sources. Do not invent data. "
                  "Highlight the one bar the narration is about. Never use em dashes.")

    def render(self, scene, project, duration, out_dir):
        p = scene.params
        W, H = self.size(project)
        u = min(W, H) / 1080
        title, unit, source = clean(p.get("title", "")), p.get("unit", "") or "", clean(p.get("source", ""))
        tall = H > W
        if p.get("kind") == "line" and p.get("values"):
            draw = self._line(p, W, H, u, unit, duration, tall)
        else:
            draw = self._bars(p, W, H, u, unit, duration, tall)

        def frame(ctx, t, W, H):
            text(ctx, title, W / 2, (190 if tall else 130) * u, 52 * u, INK, ramp(t, 0, 0.4))
            draw(ctx, t)
            if source:
                text(ctx, f"Source: {source}", W / 2, H - 60 * u, 24 * u, MUTED, ramp(t, 0.6, 1.0), bold=False)

        return render_frames(frame, duration, (W, H), out_dir / "clip.mp4")

    def _bars(self, p, W, H, u, unit, duration, tall):
        bars = (p.get("bars") or [{"label": "?", "value": 1}])[:7]
        vmax = max(b["value"] for b in bars) or 1
        n = len(bars)
        grow = min(2.2, duration * 0.5)
        stagger = min(0.25, grow / max(1, n) * 0.6)
        x0, x1 = W * (0.10 if tall else 0.26), W * (0.70 if tall else 0.82)   # room for the value label
        top, bottom = H * (0.24 if tall else 0.26), H * (0.82 if tall else 0.84)
        row = (bottom - top) / n
        bh = min(row * 0.62, 90 * u)

        def draw(ctx, t):
            for i, b in enumerate(bars):
                k = ease_out((t - 0.3 - i * stagger) / grow)
                if k <= 0:
                    continue
                y = top + row * i + (row - bh) / 2
                col = ACCENT if b.get("highlight") else (0.42, 0.42, 0.41)
                w = (x1 - x0) * (b["value"] / vmax) * k
                ctx.rectangle(x0, y, max(2 * u, w), bh)
                rgba(ctx, col, 1)
                ctx.fill()
                lab = clean(b["label"])
                if tall:
                    text(ctx, lab, x0, y - 12 * u, 30 * u, INK, min(1, k * 2), anchor="l")
                else:
                    text(ctx, lab, x0 - 24 * u, y + bh / 2 + 12 * u, 32 * u, INK, min(1, k * 2), anchor="r")
                text(ctx, fmt(b["value"] * k, unit) if k < 1 else fmt(b["value"], unit), x0 + w + 18 * u, y + bh / 2 + 12 * u,
                     34 * u, ACCENT if b.get("highlight") else INK, min(1, k * 2), anchor="l")
        return draw

    def _line(self, p, W, H, u, unit, duration, tall):
        vals = [float(v) for v in p["values"]]
        labels = [str(x) for x in (p.get("x_labels") or [])][:len(vals)]
        lo, hi = min(0.0, min(vals)), max(vals) or 1
        x0, x1 = W * 0.12, W * 0.88
        y0, y1 = H * (0.78 if tall else 0.80), H * (0.30 if tall else 0.26)
        draw_t = min(duration * 0.7, 3.5)
        pts = [(x0 + (x1 - x0) * i / max(1, len(vals) - 1), y0 + (y1 - y0) * (v - lo) / (hi - lo)) for i, v in enumerate(vals)]

        def draw(ctx, t):
            a = ramp(t, 0.1, 0.5)
            rgba(ctx, MUTED, 0.6 * a)
            ctx.set_line_width(2 * u)
            ctx.move_to(x0, y0)
            ctx.line_to(x1, y0)
            ctx.stroke()
            step = max(1, len(labels) // (5 if tall else 8))
            for i, lab in enumerate(labels):
                if i % step == 0 or i == len(labels) - 1:
                    text(ctx, lab, pts[i][0], y0 + 44 * u, 26 * u, MUTED, a, bold=False)
            k = ease((t - 0.4) / draw_t)
            if k <= 0:
                return
            seg = k * (len(pts) - 1)
            ctx.move_to(*pts[0])
            last = pts[0]
            for i in range(1, len(pts)):
                if i <= seg:
                    ctx.line_to(*pts[i])
                    last = pts[i]
                else:
                    f = seg - (i - 1)
                    if f > 0:
                        last = (pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f)
                        ctx.line_to(*last)
                    break
            rgba(ctx, ACCENT2, 1)
            ctx.set_line_width(5 * u)
            ctx.stroke()
            ctx.arc(last[0], last[1], 10 * u, 0, 2 * math.pi)
            rgba(ctx, ACCENT, 1)
            ctx.fill()
            v = lo + (y0 - last[1]) / (y0 - y1) * (hi - lo)
            text(ctx, fmt(v, unit), last[0], last[1] - 30 * u, 40 * u, INK, 1)
        return draw


ENGINE = ChartEngine()
