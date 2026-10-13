"""Real-geography globe: orthographic camera flights, country highlights, pins, routes.

Data is Natural Earth 50m (TopoJSON). Everything on screen is geographically exact.
"""
import json
import math
from functools import lru_cache

import numpy as np

from .. import config
from .base import Engine
from .kit import ACCENT, ACCENT2, INK, MUTED, clean, ease, ramp, render_frames, rgba, text

COLORS = {"accent": ACCENT, "blue": ACCENT2, "ink": INK}


@lru_cache(maxsize=1)
def topo():
    d = json.loads((config.ASSETS / "mapdata/countries-50m.json").read_text())
    sx, sy = d["transform"]["scale"]
    tx, ty = d["transform"]["translate"]
    arcs = []
    for a in d["arcs"]:
        q = np.cumsum(np.array(a, dtype=float), axis=0)
        arcs.append(np.column_stack([q[:, 0] * sx + tx, q[:, 1] * sy + ty]))

    def ring(idx):
        pts = [arcs[i] if i >= 0 else arcs[~i][::-1] for i in idx]
        return np.vstack(pts)

    countries = {}
    for g in d["objects"]["countries"]["geometries"]:
        name = g.get("properties", {}).get("name", "")
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        countries[name] = [[ring(r) for r in poly] for poly in polys]
    return arcs, countries


def find_country(name):
    _, cs = topo()
    n = name.lower().strip()
    alias = {"usa": "united states of america", "united states": "united states of america", "us": "united states of america",
             "uk": "united kingdom", "britain": "united kingdom", "russia": "russia", "drc": "dem. rep. congo",
             "czech republic": "czechia", "south korea": "south korea", "north korea": "north korea"}
    n = alias.get(n, n)
    for k in cs:
        if k.lower() == n:
            return k
    for k in cs:
        if n in k.lower() or k.lower() in n:
            return k
    return None


def centroid(name):
    _, cs = topo()
    polys = cs.get(name) or []
    if not polys:
        return None
    big = max(polys, key=lambda p: len(p[0]))[0]
    return float(big[:, 0].mean()), float(big[:, 1].mean())


class Cam:
    def __init__(self, lon, lat, R, cx, cy):
        self.l0, self.p0, self.R, self.cx, self.cy = math.radians(lon), math.radians(lat), R, cx, cy
        self.sp0, self.cp0 = math.sin(self.p0), math.cos(self.p0)

    def proj(self, ll, clamp=False):
        lam = np.radians(ll[:, 0]) - self.l0
        phi = np.radians(ll[:, 1])
        cphi = np.cos(phi)
        cosc = self.sp0 * np.sin(phi) + self.cp0 * cphi * np.cos(lam)
        x = cphi * np.sin(lam)
        y = -(self.cp0 * np.sin(phi) - self.sp0 * cphi * np.cos(lam))
        vis = cosc >= 0
        if clamp:   # push hidden points to the rim so fills stay closed
            r = np.hypot(x, y) + 1e-9
            x = np.where(vis, x, x / r)
            y = np.where(vis, y, y / r)
        return self.cx + self.R * x, self.cy + self.R * y, vis

    def pt(self, lon, lat):
        x, y, v = self.proj(np.array([[lon, lat]], float))
        return float(x[0]), float(y[0]), bool(v[0])


def stroke_lines(ctx, cam, arr):
    x, y, v = cam.proj(arr)
    pen = False
    for i in range(len(x)):
        if not v[i]:
            pen = False
            continue
        (ctx.line_to if pen else ctx.move_to)(x[i], y[i])
        pen = True


def fill_rings(ctx, cam, rings):
    for r in rings:
        x, y, v = cam.proj(r, clamp=True)
        if not v.any():
            continue
        ctx.move_to(x[0], y[0])
        for i in range(1, len(x)):
            ctx.line_to(x[i], y[i])
        ctx.close_path()


def great_circle(a, b, n=80):
    lo1, la1, lo2, la2 = map(math.radians, (*a, *b))
    p1 = np.array([math.cos(la1) * math.cos(lo1), math.cos(la1) * math.sin(lo1), math.sin(la1)])
    p2 = np.array([math.cos(la2) * math.cos(lo2), math.cos(la2) * math.sin(lo2), math.sin(la2)])
    w = math.acos(max(-1, min(1, float(p1 @ p2))))
    if w < 1e-6:
        return np.array([a, b], float)
    pts = []
    for t in np.linspace(0, 1, n):
        p = (math.sin((1 - t) * w) * p1 + math.sin(t * w) * p2) / math.sin(w)
        pts.append([math.degrees(math.atan2(p[1], p[0])), math.degrees(math.asin(p[2]))])
    return np.array(pts)


def lerp_lon(a, b, t):
    d = ((b - a + 180) % 360) - 180
    return a + d * t


class GlobeEngine(Engine):
    name = "globe"
    label = "Globe & maps"
    precise = True
    blurb = ("Exact real-world globe (Natural Earth data): camera flies between places, countries light up, "
             "pins with labels, great-circle routes. Use for anything WHERE: countries, cities, trade routes, "
             "migrations, empires, distances.")
    params_schema = {
        "type": "object",
        "properties": {
            "keyframes": {"type": "array", "description": "camera path, 1-3 stops", "items": {
                "type": "object", "properties": {
                    "lon": {"type": "number"}, "lat": {"type": "number"},
                    "zoom": {"type": "number", "description": "1 = whole globe, 2 = continent, 4 = country, 7 = small country/region"},
                    "at": {"type": "number", "description": "0-1 fraction of scene time when camera arrives"}},
                "required": ["lon", "lat", "zoom", "at"]}},
            "highlights": {"type": "array", "items": {"type": "object", "properties": {
                "country": {"type": "string", "description": "English country name"},
                "color": {"type": "string", "enum": ["accent", "blue", "ink"]},
                "label": {"type": "boolean"},
                "at": {"type": "number"}}, "required": ["country", "at"]}},
            "pins": {"type": "array", "items": {"type": "object", "properties": {
                "lon": {"type": "number"}, "lat": {"type": "number"}, "label": {"type": "string"},
                "at": {"type": "number"}}, "required": ["lon", "lat", "label", "at"]}},
            "routes": {"type": "array", "items": {"type": "object", "properties": {
                "from_lon": {"type": "number"}, "from_lat": {"type": "number"},
                "to_lon": {"type": "number"}, "to_lat": {"type": "number"},
                "at": {"type": "number"}}, "required": ["from_lon", "from_lat", "to_lon", "to_lat", "at"]}},
            "caption": {"type": "string", "description": "optional short line at the bottom, max 8 words"},
        },
        "required": ["keyframes"],
    }
    plan_guide = ("Use accurate coordinates. Time the 'at' values to when the narration mentions each thing "
                  "(assume narration is read at an even pace). Keep it uncluttered: at most 4 highlights, 4 pins.")

    def render(self, scene, project, duration, out_dir):
        p = scene.params
        W, H = self.size(project)
        u = min(W, H) / 1080
        arcs, countries = topo()
        allpts = np.vstack(arcs)
        splits = np.cumsum([len(a) for a in arcs])[:-1]
        kfs = sorted(p.get("keyframes") or [{"lon": 0, "lat": 20, "zoom": 1, "at": 0}], key=lambda k: k["at"])
        if kfs[0]["at"] > 0:
            kfs.insert(0, {**kfs[0], "at": 0.0, "zoom": max(1.0, kfs[0]["zoom"] * 0.6)})
        hl = []
        for h in p.get("highlights") or []:
            name = find_country(h["country"])
            if name:
                hl.append((name, COLORS.get(h.get("color", "accent"), ACCENT), h.get("label", True), h.get("at", 0)))
        pins = p.get("pins") or []
        routes = [(great_circle((r["from_lon"], r["from_lat"]), (r["to_lon"], r["to_lat"])), r["at"]) for r in p.get("routes") or []]
        caption = clean(p.get("caption", ""))
        base_R = min(W, H) * 0.40

        def cam_at(f):
            k = kfs
            if f <= k[0]["at"]:
                a = b = k[0]
                t = 0
            elif f >= k[-1]["at"]:
                a = b = k[-1]
                t = 0
            else:
                i = max(j for j in range(len(k)) if k[j]["at"] <= f)
                a, b = k[i], k[i + 1]
                t = ease((f - a["at"]) / max(1e-6, b["at"] - a["at"]))
            lon = lerp_lon(a["lon"], b["lon"], t)
            lat = a["lat"] + (b["lat"] - a["lat"]) * t
            z = math.exp(math.log(a["zoom"]) + (math.log(b["zoom"]) - math.log(a["zoom"])) * t)
            return Cam(lon, lat, base_R * z, W / 2, H / 2 - (40 * u if caption else 0))

        def draw(ctx, t, W, H):
            f = t / duration
            cam = cam_at(f)
            # ocean disc
            ctx.arc(cam.cx, cam.cy, cam.R, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, 0.025)
            ctx.fill_preserve()
            rgba(ctx, INK, 0.25)
            ctx.set_line_width(2 * u)
            ctx.stroke()
            # graticule
            for lo in range(-180, 180, 15):
                stroke_lines(ctx, cam, np.array([[lo, la] for la in range(-90, 91, 2)], float))
            for la in range(-75, 76, 15):
                stroke_lines(ctx, cam, np.array([[lo, la] for lo in range(-180, 181, 2)], float))
            rgba(ctx, INK, 0.06)
            ctx.set_line_width(1 * u)
            ctx.stroke()
            # land, filled softly so the map never reads as empty
            for polys in countries.values():
                for poly in polys:
                    fill_rings(ctx, cam, poly[:1])
            ctx.set_source_rgba(1, 1, 1, 0.045)
            ctx.fill()
            # coastlines + borders
            x, y, v = cam.proj(allpts)
            for xs, ys, vs in zip(np.split(x, splits), np.split(y, splits), np.split(v, splits)):
                pen = False
                for i in range(len(xs)):
                    if not vs[i]:
                        pen = False
                        continue
                    (ctx.line_to if pen else ctx.move_to)(xs[i], ys[i])
                    pen = True
            rgba(ctx, INK, 0.45)
            ctx.set_line_width(1.2 * u)
            ctx.stroke()
            # highlights
            for name, col, lab, at in hl:
                a = ramp(f, at, at + 0.08)
                if a <= 0:
                    continue
                for poly in countries[name]:
                    fill_rings(ctx, cam, poly)
                ctx.set_fill_rule(0)
                rgba(ctx, col, (0.28 if col == INK else 0.55) * a)
                ctx.fill_preserve()
                rgba(ctx, col, a)
                ctx.set_line_width(2 * u)
                ctx.stroke()
                c = centroid(name)
                if lab and c:
                    px, py, vis = cam.pt(*c)
                    if vis:
                        text(ctx, name.upper(), px, py + 12 * u, 26 * u, INK, a)
            # routes
            for pts, at in routes:
                k = ramp(f, at, at + 0.25)
                if k <= 0:
                    continue
                n = max(2, int(len(pts) * k))
                stroke_lines(ctx, cam, pts[:n])
                rgba(ctx, ACCENT2, 0.95)
                ctx.set_line_width(4 * u)
                ctx.stroke()
                hx, hy, hv = cam.pt(*pts[n - 1])
                if hv:
                    ctx.arc(hx, hy, 7 * u, 0, 2 * math.pi)
                    rgba(ctx, ACCENT2)
                    ctx.fill()
            # pins
            for pn in pins:
                a = ramp(f, pn["at"], pn["at"] + 0.06)
                if a <= 0:
                    continue
                px, py, vis = cam.pt(pn["lon"], pn["lat"])
                if not vis:
                    continue
                pulse = 1 + 0.6 * (1 - ramp(f, pn["at"], pn["at"] + 0.12))
                ctx.arc(px, py, 22 * u * pulse, 0, 2 * math.pi)
                rgba(ctx, ACCENT, 0.9 * a)
                ctx.set_line_width(4 * u)
                ctx.stroke()
                ctx.arc(px, py, 9 * u, 0, 2 * math.pi)
                ctx.fill()
                text(ctx, clean(pn["label"]), px + 36 * u, py + 11 * u, 32 * u, INK, a, anchor="l")
            if caption:
                text(ctx, caption, W / 2, H - 90 * u, 44 * u, INK, ramp(f, 0.05, 0.15), bold=True)

        return render_frames(draw, duration, (W, H), out_dir / "clip.mp4")


ENGINE = GlobeEngine()
