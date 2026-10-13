"""Hand-drawn explainer: Nano Banana draws clean line art, then we draw it on stroke by stroke
(chalk on the dark board by default, or marker on a whiteboard)."""
import cv2
import numpy as np

from .. import config, gemini
from ..media import FrameWriter, hex_rgb
from .base import Engine
from .kit import ease

CELL = 14


def stroke_order(ink, cell=CELL):
    """Ink cells ordered like a person drawing: component by component, left to right,
    nearest-neighbour walk inside each component."""
    H, W = ink.shape
    gh, gw = H // cell, W // cell
    g = ink[:gh * cell, :gw * cell].reshape(gh, cell, gw, cell).max(axis=(1, 3)) > 0
    n, lab = cv2.connectedComponents(g.astype(np.uint8), connectivity=8)
    comps = []
    for k in range(1, n):
        ys, xs = np.nonzero(lab == k)
        comps.append((xs.min() + 0.25 * ys.min(), ys, xs))
    comps.sort(key=lambda c: c[0])
    order = []
    for _, ys, xs in comps:
        pts = np.column_stack([ys, xs]).astype(float)
        left = np.ones(len(pts), bool)
        i = int(np.argmin(pts[:, 1] + pts[:, 0] * 0.3))
        while True:
            left[i] = False
            order.append((int(pts[i, 0]), int(pts[i, 1])))
            if not left.any():
                break
            cand = np.nonzero(left)[0]
            d = np.abs(pts[cand] - pts[i]).sum(axis=1)
            i = int(cand[np.argmin(d)])
    return order


class WhiteboardEngine(Engine):
    name = "whiteboard"
    label = "Whiteboard sketch"
    blurb = ("A hand-drawn sketch is drawn on stroke by stroke, like a teacher at a board: simple diagrams of "
             "processes, cause and effect, comparisons, everyday objects, flows with arrows. Friendly and clear. "
             "No exact numbers or maps.")
    params_schema = {
        "type": "object",
        "properties": {
            "drawing": {"type": "string", "description": "what is drawn: simple objects, arrows, layout left to right. Max 3-4 elements. No words."},
            "board": {"type": "string", "enum": ["chalk", "whiteboard"]},
        },
        "required": ["drawing", "board"],
    }
    plan_guide = "Think like a teacher sketching quickly: a few iconic objects connected by arrows, left to right. No written words."

    def render(self, scene, project, duration, out_dir):
        W, H = self.size(project)
        art = out_dir / "lineart.png"
        if not art.exists():
            gemini.image(f"Simple black marker line drawing on a pure white background, filling the whole frame edge to edge, "
                         f"no paper, no border, no shading, no text or letters, clean single-weight strokes, "
                         f"whiteboard explainer style: {scene.params.get('drawing') or scene.brief}",
                         art, aspect=project.aspect)
        img = cv2.imread(str(art), cv2.IMREAD_GRAYSCALE)
        ys, xs = np.nonzero(img < 170)
        if len(xs):   # crop to the drawing so it fills the frame
            m = 20
            img = img[max(0, ys.min() - m):ys.max() + m, max(0, xs.min() - m):xs.max() + m]
        ih, iw = img.shape
        k = min(W * 0.86 / iw, H * 0.82 / ih)
        img = cv2.resize(img, (int(iw * k), int(ih * k)), interpolation=cv2.INTER_AREA)
        canvas_g = np.full((H, W), 255, np.uint8)
        y0, x0 = (H - img.shape[0]) // 2, (W - img.shape[1]) // 2
        canvas_g[y0:y0 + img.shape[0], x0:x0 + img.shape[1]] = img
        alpha = np.clip((200 - canvas_g.astype(float)) / 150, 0, 1)   # ink strength 0..1
        board = scene.params.get("board", "chalk")
        if board == "chalk":
            bg = np.array([int(c * 255) for c in hex_rgb(config.BG)], float)
            ink = np.array([int(c * 255) for c in hex_rgb(config.INK)], float)
        else:
            bg, ink = np.array([250, 250, 247], float), np.array([25, 25, 30], float)
        order = stroke_order((alpha > 0.15).astype(np.uint8))
        draw_t = min(duration * 0.75, max(2.5, len(order) / 120))
        n = max(1, int(round(duration * config.FPS)))
        reveal = np.zeros((H, W), float)
        done = 0
        tip_c = np.array([int(c * 255) for c in hex_rgb(config.ACCENT)], float)
        with FrameWriter(out_dir / "clip.mp4", (W, H), "rgb24") as fw:
            for f in range(n):
                t = f / config.FPS
                target = int(len(order) * ease(min(1, t / draw_t)) ** 0.85) if draw_t > 0 else len(order)
                tip = None
                while done < target:
                    cy, cx = order[done]
                    reveal[cy * CELL:(cy + 1) * CELL, cx * CELL:(cx + 1) * CELL] = 1
                    tip = (cx * CELL + CELL // 2, cy * CELL + CELL // 2)
                    done += 1
                a = (alpha * reveal)[..., None]
                frame = bg * (1 - a) + ink * a
                if tip is not None and done < len(order):
                    cv2.circle(frame, tip, 9, tip_c.tolist(), -1, lineType=cv2.LINE_AA)
                fw.write(frame.astype(np.uint8).tobytes())
        return out_dir / "clip.mp4"


ENGINE = WhiteboardEngine()
