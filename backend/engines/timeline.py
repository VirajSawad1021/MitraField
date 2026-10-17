"""Timelines drawn by code: a time axis that draws in, events landing at their exact dates."""
import math

from .base import Engine
from .kit import ACCENT, INK, MUTED, clean, ease_out, fit_size, ramp, render_frames, rgba, text, wrap


class TimelineEngine(Engine):
    name = "timeline"
    label = "Timeline"
    precise = True
    blurb = ("Exact timeline: a time axis draws in and events land at their real dates, one by one. Use for history, "
             "'how we got here', sequences of discoveries or a countdown of years. 2-6 events.")
    params_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "max 6 words, may be empty"},
            "events": {"type": "array", "description": "2-6 events in time order", "items": {"type": "object", "properties": {
                "year": {"type": "number", "description": "year (negative for BC); decimals allowed for months"},
                "date_label": {"type": "string", "description": "how the date is shown, e.g. '1912', 'April 1912', '300 BC'"},
                "label": {"type": "string", "description": "what happened, max 7 words"},
                "highlight": {"type": "boolean"}}, "required": ["year", "date_label", "label"]}},
        },
        "required": ["events"],
    }
    plan_guide = "Dates must be historically accurate and come from the narration or sources. Never use em dashes."

    def render(self, scene, project, duration, out_dir):
        p = scene.params
        W, H = self.size(project)
        u = min(W, H) / 1080
        tall = H > W
        ev = sorted(p.get("events") or [], key=lambda e: e["year"])[:6]
        if not ev:
            ev = [{"year": 0, "date_label": "", "label": clean(scene.narration)[:40]}]
        y_lo, y_hi = ev[0]["year"], ev[-1]["year"]
        span = (y_hi - y_lo) or 1
        title = clean(p.get("title", ""))
        axis_t = min(1.0, duration * 0.15)
        per = (duration * 0.75 - axis_t) / len(ev)

        if tall:   # vertical axis down the left third
            ax, a0, a1 = W * 0.26, H * 0.20, H * 0.86
        else:
            ay, a0, a1 = H * 0.56, W * 0.13, W * 0.87   # room for the end labels
        frac = [(e["year"] - y_lo) / span for e in ev]
        if len(ev) > 1 and min(b - a for a, b in zip(frac, frac[1:])) < 0.12:
            frac = [i / (len(ev) - 1) for i in range(len(ev))]   # crowded dates: even spacing, labels stay readable
        where = {id(e): a0 + (a1 - a0) * f for e, f in zip(ev, frac)}
        pos = lambda e: where[id(e)]

        def draw(ctx, t, W, H):
            if title:
                text(ctx, title, W / 2, (120 if tall else 120) * u, 50 * u, INK, ramp(t, 0, 0.4))
            k = ease_out(t / axis_t)
            rgba(ctx, MUTED, 0.7)
            ctx.set_line_width(3 * u)
            if tall:
                ctx.move_to(ax, a0)
                ctx.line_to(ax, a0 + (a1 - a0) * k)
            else:
                ctx.move_to(a0, ay)
                ctx.line_to(a0 + (a1 - a0) * k, ay)
            ctx.stroke()
            for i, e in enumerate(ev):
                s = axis_t + i * per
                a = ramp(t, s, s + 0.35)
                if a <= 0:
                    continue
                col = ACCENT if e.get("highlight") or i == len(ev) - 1 and not any(x.get("highlight") for x in ev) else INK
                pop = 1 + 0.5 * (1 - ease_out((t - s) / 0.4))
                lab = clean(e["label"])
                if tall:
                    y = pos(e)
                    ctx.arc(ax, y, 11 * u * pop, 0, 2 * math.pi)
                    rgba(ctx, col, a)
                    ctx.fill()
                    text(ctx, clean(e["date_label"]), ax - 30 * u, y + 13 * u, 36 * u, col, a, anchor="r")
                    import cairo
                    probe = cairo.Context(cairo.ImageSurface(cairo.FORMAT_RGB24, 8, 8))
                    for j, line in enumerate(wrap(probe, lab, 34 * u, W * 0.62, bold=False)[:2]):
                        text(ctx, line, ax + 34 * u, y + 13 * u + j * 42 * u, 34 * u, INK, a, bold=False, anchor="l")
                else:
                    x = pos(e)
                    up = i % 2 == 0
                    ctx.move_to(x, ay)
                    ctx.line_to(x, ay + (-1 if up else 1) * 60 * u * a)
                    rgba(ctx, col, 0.6 * a)
                    ctx.set_line_width(2 * u)
                    ctx.stroke()
                    ctx.arc(x, ay, 11 * u * pop, 0, 2 * math.pi)
                    rgba(ctx, col, a)
                    ctx.fill()
                    import cairo
                    probe = cairo.Context(cairo.ImageSurface(cairo.FORMAT_RGB24, 8, 8))
                    lines = wrap(probe, lab, 30 * u, W * 0.20, bold=False)[:3]
                    base = ay - 90 * u - (len(lines) - 1) * 38 * u if up else ay + 110 * u
                    text(ctx, clean(e["date_label"]), x, base - 46 * u if up else base, 40 * u, col, a)
                    for j, line in enumerate(lines):
                        yy = base + j * 38 * u if up else base + 46 * u + j * 38 * u
                        text(ctx, line, x, yy, 30 * u, INK, a, bold=False)

        return render_frames(draw, duration, (W, H), out_dir / "clip.mp4")


ENGINE = TimelineEngine()
