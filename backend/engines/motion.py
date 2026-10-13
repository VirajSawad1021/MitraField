"""Smooth sub-pixel camera moves over a still (cv2 affine per frame, no zoompan jitter)."""
import cv2
import numpy as np

from .. import config
from ..media import FrameWriter
from .kit import ease

MOVES = ["push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down"]


def camera(img_path, out, duration, size, move="push_in", strength=1.0):
    W, H = size
    img = cv2.imread(str(img_path))[:, :, ::-1]
    ih, iw = img.shape[:2]
    cover = max(W / iw, H / ih)
    z = 0.12 * strength
    pan = 0.08 * strength
    n = max(1, int(round(duration * config.FPS)))
    with FrameWriter(out, size, "rgb24") as fw:
        for f in range(n):
            t = ease(f / max(1, n - 1)) if move in ("push_in", "pull_out") else f / max(1, n - 1)
            s, ox, oy = 1 + z / 2, 0.0, 0.0
            if move == "push_in":
                s = 1 + z * t
            elif move == "pull_out":
                s = 1 + z * (1 - t)
            elif move == "pan_left":
                ox = pan * (0.5 - t)
            elif move == "pan_right":
                ox = pan * (t - 0.5)
            elif move == "tilt_up":
                oy = pan * (0.5 - t)
            elif move == "tilt_down":
                oy = pan * (t - 0.5)
            k = cover * s
            # image centre (+offset) maps to frame centre
            cx = iw / 2 + ox * iw
            cy = ih / 2 + oy * ih
            M = np.float32([[k, 0, W / 2 - k * cx], [0, k, H / 2 - k * cy]])
            frame = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            fw.write(np.ascontiguousarray(frame).tobytes())
    return out
