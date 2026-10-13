"""ffmpeg helpers shared by engines and the assembler."""
import json
import subprocess
from pathlib import Path

from . import config


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-1500:]}")
    return r.stdout


def duration(path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path])
    return float(json.loads(out)["format"]["duration"])


def fit(src, out, dur, size, stretch_max=1.0):
    """Normalise any clip to size@FPS, h264, no audio, exactly `dur` seconds.

    Short clips are slowed down up to `stretch_max`x, then hold the last frame.
    """
    W, H = size
    have = duration(src)
    k = min(stretch_max, max(1.0, dur / max(have, 0.1)))
    vf = (f"setpts={k:.4f}*PTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"fps={config.FPS},tpad=stop_mode=clone:stop_duration={max(0, dur - have * k) + 1:.3f},format=yuv420p")
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, "-t", f"{dur:.3f}", "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out])
    return Path(out)


def thumb(clip, out, at=None):
    d = duration(clip)
    t = d * 0.6 if at is None else min(at, d - 0.05)
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", clip, "-frames:v", "1",
         "-vf", "scale=480:-2", out])
    return Path(out)


class FrameWriter:
    """Pipe raw frames into an h264 mp4. pix_fmt 'bgra' matches cairo, 'rgb24' matches numpy/PIL."""

    def __init__(self, out, size, pix_fmt="bgra"):
        W, H = size
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", pix_fmt, "-s", f"{W}x{H}",
             "-r", str(config.FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)

    def write(self, data):
        self.p.stdin.write(data)

    def close(self):
        self.p.stdin.close()
        if self.p.wait():
            raise RuntimeError("ffmpeg frame writer failed")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
