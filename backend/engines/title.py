"""Kinetic typography: one strong line, words land on the beat. Always-safe fallback engine."""
from .base import Engine
from .kit import ACCENT, INK, MUTED, clean, ease_out, fit_size, ramp, render_frames, text


class TitleEngine(Engine):
    name = "title"
    label = "Kinetic type"
    precise = True
    blurb = ("Big bold statement or number on a dark background, words animate in one by one. "
             "Use for the hook, a striking number, a definition, or a chapter turn. Text only, no imagery.")
    params_schema = {
        "type": "object",
        "properties": {
            "kicker": {"type": "string", "description": "tiny label above, 1-3 words, may be empty"},
            "headline": {"type": "string", "description": "max 9 words, the line that should stick"},
            "accent_words": {"type": "array", "items": {"type": "string"}, "description": "1-2 words from headline to color"},
            "sub": {"type": "string", "description": "optional supporting line, max 12 words"},
        },
        "required": ["headline"],
    }
    plan_guide = "Sentence case (only the first word and names capitalised). Never use em dashes. Keep it punchy; the narration carries the detail."

    def render(self, scene, project, duration, out_dir):
        p = scene.params or {}
        head = clean(p.get("headline") or scene.narration.split(".")[0])
        kicker, sub = clean(p.get("kicker", "")).upper(), clean(p.get("sub", ""))
        accents = {a.lower().strip(".,!?") for a in p.get("accent_words", [])}
        W, H = self.size(project)
        u = min(W, H) / 1080

        import cairo
        probe = cairo.Context(cairo.ImageSurface(cairo.FORMAT_RGB24, 8, 8))
        size, lines = fit_size(probe, head, 118 * u, W * 0.80, 3 if W > H else 5, "Fraunces")
        words = [(li, w) for li, line in enumerate(lines) for w in line.split()]
        lead = min(1.4, duration * 0.35)
        per = lead / max(1, len(words))
        lh = size * 1.18
        y0 = H / 2 - (len(lines) - 1) * lh / 2 + size * 0.35

        def draw(ctx, t, W, H):
            if kicker:
                text(ctx, kicker, W / 2, y0 - size * 1.25, 30 * u, ACCENT, ramp(t, 0, 0.4))
            from .kit import font
            font(ctx, size, "Fraunces")
            widths = {}
            for li, line in enumerate(lines):
                widths[li] = ctx.text_extents(line).x_advance
            space = ctx.text_extents("a a").x_advance - ctx.text_extents("aa").x_advance
            xs = {li: W / 2 - widths[li] / 2 for li in widths}
            for i, (li, w) in enumerate(words):
                k = ease_out((t - 0.15 - i * per) / 0.45)
                font(ctx, size, "Fraunces")
                adv = ctx.text_extents(w).x_advance
                col = ACCENT if w.lower().strip(".,!?") in accents else INK
                text(ctx, w, xs[li], y0 + li * lh + (1 - k) * 24 * u, size, col, k, "Fraunces", anchor="l")
                xs[li] += adv + space
            if sub:
                text(ctx, sub, W / 2, y0 + (len(lines) - 1) * lh + size * 1.1, 40 * u, MUTED,
                     ramp(t, lead + 0.2, lead + 0.8), bold=False)

        return render_frames(draw, duration, (W, H), out_dir / "clip.mp4")


ENGINE = TitleEngine()
