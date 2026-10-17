"""Flow diagrams drawn by code: steps appear one at a time and arrows draw between them.
Nodes are marked with dots and labels (no boxes), laid out as a row, a cycle or a tree."""
import math

import cairo

from .base import Engine
from .kit import ACCENT, ACCENT2, INK, MUTED, clean, ease, ease_out, ramp, render_frames, rgba, text, wrap

_probe = cairo.Context(cairo.ImageSurface(cairo.FORMAT_RGB24, 8, 8))


class FlowEngine(Engine):
    name = "flow"
    label = "Flow diagram"
    precise = True
    blurb = ("Exact step-by-step diagram: labelled steps appear one at a time and arrows draw between them, as a "
             "sequence, a cycle (loops like the water cycle) or a branching tree. Use for processes, pipelines, cause "
             "and effect chains and systems. 3-6 steps.")
    params_schema = {
        "type": "object",
        "properties": {
            "layout": {"type": "string", "enum": ["row", "cycle", "tree"]},
            "nodes": {"type": "array", "description": "3-6 steps in reveal order", "items": {"type": "object", "properties": {
                "id": {"type": "string"}, "label": {"type": "string", "description": "max 4 words"},
                "highlight": {"type": "boolean"}}, "required": ["id", "label"]}},
            "edges": {"type": "array", "items": {"type": "object", "properties": {
                "from": {"type": "string"}, "to": {"type": "string"}, "label": {"type": "string", "description": "optional, max 3 words"}},
                "required": ["from", "to"]}},
            "caption": {"type": "string", "description": "optional bottom line, max 8 words"},
        },
        "required": ["layout", "nodes", "edges"],
    }
    plan_guide = "Labels are short noun phrases. Edges follow the real process. Never use em dashes."

    def layout(self, p, W, H, tall):
        nodes = (p.get("nodes") or [])[:6]
        ids = [n["id"] for n in nodes]
        kind = p.get("layout", "row")
        pos = {}
        cx, cy = W / 2, H * (0.46 if p.get("caption") else 0.50)
        self.cy = cy
        if kind == "cycle":
            r = min(W, H) * (0.22 if tall else 0.27)
            for i, nid in enumerate(ids):
                a = -math.pi / 2 + 2 * math.pi * i / len(ids)
                pos[nid] = (cx + r * math.cos(a), cy + r * math.sin(a))
        elif kind == "tree":
            parents = {e["to"]: e["from"] for e in p.get("edges", []) if e["from"] in ids and e["to"] in ids}
            depth = {}
            for nid in ids:
                d, cur, seen = 0, nid, set()
                while cur in parents and cur not in seen:
                    seen.add(cur)
                    cur = parents[cur]
                    d += 1
                depth[nid] = d
            levels = {}
            for nid in ids:
                levels.setdefault(depth[nid], []).append(nid)
            L = max(levels) + 1
            for d, row in levels.items():
                for j, nid in enumerate(row):
                    if tall:
                        pos[nid] = (W * (j + 1) / (len(row) + 1), H * (0.22 + 0.62 * d / max(1, L - 1)))
                    else:
                        pos[nid] = (W * (0.14 + 0.72 * d / max(1, L - 1)), H * (j + 1) / (len(row) + 1))
        else:
            for i, nid in enumerate(ids):
                f = i / max(1, len(ids) - 1)
                pos[nid] = (cx, H * (0.18 + 0.66 * f)) if tall else (W * (0.10 + 0.80 * f), cy)
        return nodes, pos

    def render(self, scene, project, duration, out_dir):
        p = scene.params
        W, H = self.size(project)
        u = min(W, H) / 1080
        tall = H > W
        nodes, pos = self.layout(p, W, H, tall)
        if not nodes:
            raise ValueError("flow diagram needs nodes")
        edges = [e for e in p.get("edges", []) if e["from"] in pos and e["to"] in pos]
        order = {n["id"]: i for i, n in enumerate(nodes)}
        per = (duration * 0.8) / (len(nodes) + 0.5)
        caption = clean(p.get("caption", ""))
        R = 16 * u

        def appear(nid):
            return 0.3 + order[nid] * per

        def draw(ctx, t, W, H):
            # arrows first, drawn once both ends exist
            for e in edges:
                s = max(appear(e["from"]), appear(e["to"])) - per * 0.35
                k = ease((t - s) / (per * 0.5))
                if k <= 0:
                    continue
                (x0, y0), (x1, y1) = pos[e["from"]], pos[e["to"]]
                dx, dy = x1 - x0, y1 - y0
                d = math.hypot(dx, dy) or 1
                ux, uy = dx / d, dy / d
                gap = 70 * u
                sx, sy = x0 + ux * gap, y0 + uy * gap
                ex, ey = x1 - ux * gap, y1 - uy * gap
                mx, my = sx + (ex - sx) * k, sy + (ey - sy) * k
                bend = 0.18 * d if p.get("layout") == "cycle" else 0
                nx, ny = -uy * bend, ux * bend
                ctx.move_to(sx, sy)
                ctx.curve_to(sx + (mx - sx) / 3 + nx * k, sy + (my - sy) / 3 + ny * k,
                             sx + 2 * (mx - sx) / 3 + nx * k, sy + 2 * (my - sy) / 3 + ny * k, mx, my)
                rgba(ctx, ACCENT2, 0.95)
                ctx.set_line_width(4 * u)
                ctx.stroke()
                if k > 0.98:
                    ang = math.atan2(ey - (sy + 2 * (ey - sy) / 3 + ny), ex - (sx + 2 * (ex - sx) / 3 + nx))
                    for side in (-1, 1):
                        ctx.move_to(ex, ey)
                        ctx.line_to(ex - 22 * u * math.cos(ang + side * 0.45), ey - 22 * u * math.sin(ang + side * 0.45))
                    ctx.stroke()
                    if e.get("label"):
                        text(ctx, clean(e["label"]), (sx + ex) / 2 + nx * 0.8, (sy + ey) / 2 + ny * 0.8 - 14 * u, 26 * u, MUTED, 1, bold=False)
            for n in nodes:
                a = ramp(t, appear(n["id"]), appear(n["id"]) + 0.3)
                if a <= 0:
                    continue
                x, y = pos[n["id"]]
                col = ACCENT if n.get("highlight") else INK
                pop = 1 + 0.6 * (1 - ease_out((t - appear(n["id"])) / 0.45))
                ctx.arc(x, y, R * pop, 0, 2 * math.pi)
                rgba(ctx, col, a)
                ctx.fill()
                ctx.arc(x, y, R * 2.1 * pop, 0, 2 * math.pi)
                rgba(ctx, col, 0.35 * a)
                ctx.set_line_width(2.5 * u)
                ctx.stroke()
                lines = wrap(_probe, clean(n["label"]), 36 * u, (W * 0.22) if not tall else W * 0.6)[:2]
                if p.get("layout") == "cycle":   # labels sit outside the ring, away from the arrows
                    ox, oy = x - W / 2, y - self.cy
                    d = math.hypot(ox, oy) or 1
                    lx, ly = x + ox / d * 70 * u, y + oy / d * 70 * u
                    anchor = "c" if abs(ox / d) < 0.4 else ("l" if ox > 0 else "r")
                    if tall and anchor != "c":   # narrow frame: side labels go under their dot
                        lx, ly, anchor = x, y + 64 * u, "c"
                    base = ly + 13 * u - (len(lines) - 1) * 22 * u + (24 * u if oy / d > 0.4 else -10 * u if oy / d < -0.4 else 0)
                    for j, line in enumerate(lines):
                        text(ctx, line, lx, base + j * 44 * u, 36 * u, col, a, anchor=anchor)
                elif tall and p.get("layout") == "row":
                    for j, line in enumerate(lines):
                        text(ctx, line, x + 60 * u, y + 13 * u + j * 44 * u, 36 * u, col, a, anchor="l")
                else:
                    for j, line in enumerate(lines):
                        text(ctx, line, x, y + 78 * u + j * 44 * u, 36 * u, col, a)
            if caption:
                text(ctx, caption, W / 2, H - 80 * u, 40 * u, INK, ramp(t, duration * 0.6, duration * 0.6 + 0.4))

        return render_frames(draw, duration, (W, H), out_dir / "clip.mp4")


ENGINE = FlowEngine()
