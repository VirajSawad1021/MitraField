"""Provenance: an invisible watermark in every exported video, and the check that reads it back.

Each export gets a random 32-bit mark id. The id (plus a CRC) is spread over the picture as a faint,
keyed noise pattern: for every frame, `strength * m[k] * sum_i(bit_i * P_i)`, where P_i are smooth keyed
patterns, m[k] is a keyed +-1 sequence over time and bit_i is +-1. A reader that knows the key correlates
each frame with the patterns and the sequence; the picture's own content averages out over time while the
mark adds up, so it survives re-encoding and rescaling. The strength follows the picture (weaker on dark,
flat areas where grain shows, stronger on busy ones).

This is classical spread-spectrum watermarking, not a trained one like SynthID, and it has limits: heavy
crops or a changed aspect ratio defeat it, and so can a determined person who denoises. `verify` therefore
reports what it found and never claims a video is NOT ours.

The registry (a `provenance` document per mark id, and one per file hash) says which export a mark
belongs to. The key lives in Secret Manager and is only ever given to the worker.
"""
import binascii
import functools
import hashlib
import os
import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from . import config, log, store

logger = log.get("provenance")

NB = 48                       # 32-bit mark id + 16-bit CRC
ID_BITS = 32
CANON = {"L": (320, 180), "P": (180, 320)}   # the size patterns live at and the reader looks at
SEQ_LEN = 1 << 17             # frames of the keyed temporal sequence (over an hour at 30 fps)
MAX_OFFSET = 20000            # how far into the sequence a trimmed copy may start
DETECT_SECONDS = 80           # the reader looks at this much of an upload

# Embedding strength in luma levels (0-255). Tuned by eye and by the robustness tests (tests/test_provenance.py).
PARAMS = {"hi": 2.0, "lo": 0.5, "tex_ref": 10.0, "lum_ref": 60.0, "lum_min": 0.8, "scale": float(os.environ.get("STUDIO_WM_SCALE", "1"))}


class WatermarkError(RuntimeError):
    pass


# ------------------------------------------------------------------ key and patterns

@functools.lru_cache(maxsize=1)
def _key() -> bytes:
    k = config.WATERMARK_KEY
    if not k:
        if config.STORE == "firestore":   # many instances share the data volume: never invent a key there
            raise WatermarkError("STUDIO_WATERMARK_KEY is not set")
        f = config.DATA / ".watermark_key"   # local development: a stable key beside the data
        if not f.exists():
            f.write_text(secrets.token_hex(32))
        k = f.read_text().strip()
    return hashlib.sha256(k.encode()).digest()


def _rng(label: str) -> np.random.Generator:
    return np.random.default_rng(int.from_bytes(hashlib.sha256(_key() + label.encode()).digest()[:8], "big"))


@functools.lru_cache(maxsize=2)
def patterns(orient: str) -> np.ndarray:
    cw, ch = CANON[orient]
    r = _rng("patterns-" + orient)
    P = np.stack([cv2.GaussianBlur(r.standard_normal((ch, cw)).astype(np.float32), (0, 0), 1.5) for _ in range(NB)])
    P -= P.mean(axis=(1, 2), keepdims=True)
    P /= P.std(axis=(1, 2), keepdims=True)
    return P


@functools.lru_cache(maxsize=1)
def sequence() -> np.ndarray:
    return np.where(_rng("sequence").random(SEQ_LEN) < 0.5, -1.0, 1.0).astype(np.float32)


# ------------------------------------------------------------------ payload

def new_mark_id() -> int:
    return secrets.randbits(ID_BITS)


def _bits(mark_id: int) -> np.ndarray:
    raw = mark_id.to_bytes(4, "big")
    word = int.from_bytes(raw, "big") << 16 | binascii.crc_hqx(raw, 0)
    return np.array([(word >> (NB - 1 - i)) & 1 for i in range(NB)])


def _decode(bits: np.ndarray):
    word = 0
    for b in bits:
        word = word << 1 | int(b)
    mark_id, crc = word >> 16, word & 0xFFFF
    return mark_id, binascii.crc_hqx(mark_id.to_bytes(4, "big"), 0) == crc


def mark_hex(mark_id: int) -> str:
    return f"{mark_id:08x}"


# ------------------------------------------------------------------ embedding

def strength_map(y: np.ndarray) -> np.ndarray:
    """Per-pixel embedding strength for one luma frame: low on dark flat areas, high on busy bright ones."""
    h, w = y.shape
    s = cv2.resize(y, (max(w // 4, 1), max(h // 4, 1)), interpolation=cv2.INTER_AREA)
    mu = cv2.blur(s, (5, 5))
    tex = np.sqrt(np.maximum(cv2.blur(s * s, (5, 5)) - mu * mu, 0))
    f_tex = np.clip(tex / PARAMS["tex_ref"], 0, 1)
    f_lum = np.clip(mu / PARAMS["lum_ref"], PARAMS["lum_min"], 1)
    m = (PARAMS["lo"] + (PARAMS["hi"] - PARAMS["lo"]) * f_tex) * f_lum * PARAMS["scale"]
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)


def _probe(path) -> tuple[int, int]:
    o = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                 "-of", "csv=p=0", str(path)], timeout=60).decode().strip().split(",")
    return int(o[0]), int(o[1])


def _orient(w, h):
    return "P" if h > w else "L"


def embed(video, audio, dst, mark_id: int):
    """Write `dst` = `video` with the mark in its picture, muxed with `audio` (AAC). One re-encode."""
    w, h = _probe(video)
    orient = _orient(w, h)
    s = np.where(_bits(mark_id) == 1, 1.0, -1.0).astype(np.float32)
    S = (s[:, None, None] * patterns(orient)).sum(0) / np.sqrt(NB)
    S = cv2.resize(S, (w, h), interpolation=cv2.INTER_LINEAR)
    m = sequence()
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-an", "-pix_fmt", "yuv420p", "-f", "rawvideo", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{w}x{h}",
                            "-r", str(config.FPS), "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(dst)],
                           stdin=subprocess.PIPE)
    size, k = w * h * 3 // 2, 0
    try:
        while True:
            raw = dec.stdout.read(size)
            if len(raw) < size:
                break
            if k >= SEQ_LEN:
                enc.stdin.write(raw)   # past the sequence (over an hour): left unmarked
            else:
                fr = np.frombuffer(raw, np.uint8).copy()
                y = fr[:w * h].reshape(h, w).astype(np.float32)
                y += (m[k] * S) * strength_map(y)
                fr[:w * h] = np.clip(np.rint(y), 0, 255).astype(np.uint8).ravel()
                enc.stdin.write(fr.tobytes())
            k += 1
        enc.stdin.close()
        if enc.wait() != 0 or dec.wait() != 0 or k == 0:
            raise WatermarkError("ffmpeg failed while embedding the mark")
    finally:
        for p in (dec, enc):
            if p.poll() is None:
                p.kill()


# ------------------------------------------------------------------ detection

@dataclass
class Detection:
    found: bool = False          # a mark with a valid checksum was read
    mark_id: int | None = None
    snr: float = 0.0             # how far the mark stands above the noise floor (higher is surer)
    frames: int = 0              # how many frames were read
    offset: int = 0              # where in the original the upload starts (frames); non-zero means it was trimmed


def _luma_frames(path, orient, seconds):
    cw, ch = CANON[orient]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-t", str(seconds), "-i", str(path), "-an", "-vf",
                          f"fps={config.FPS},scale={cw}:{ch}:flags=area", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE)
    n = cw * ch
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            yield np.frombuffer(b, np.uint8).reshape(ch, cw).astype(np.float32)
    finally:
        p.kill()


def detect(path, seconds: int = DETECT_SECONDS) -> Detection:
    w, h = _probe(path)
    orient = _orient(w, h)
    cw, ch = CANON[orient]
    P = patterns(orient).reshape(NB, -1)
    rows = []
    for y in _luma_frames(path, orient, seconds):
        y = y - cv2.GaussianBlur(y, (0, 0), 6)       # the picture's own low frequencies would swamp the mark
        rows.append(P @ y.ravel() / (cw * ch))
    n = len(rows)
    if n < 20:
        return Detection(frames=n)
    C = np.stack(rows)                                # frames x bits
    size = 1 << int(np.ceil(np.log2(n + MAX_OFFSET + 1)))
    m = sequence()[:min(SEQ_LEN, MAX_OFFSET + n)]
    # acc[o, i] = sum_k m[o + k] * C[k, i]: the mark's evidence for every start offset at once
    acc = np.fft.irfft(np.fft.rfft(m, size)[:, None] * np.conj(np.fft.rfft(C, size, axis=0)), size, axis=0)[:len(m) - n + 1]
    energy = (acc ** 2).sum(1)
    best = int(energy.argmax())
    others = np.delete(acc, slice(max(best - 2, 0), best + 3), axis=0)
    noise = float(others.std()) or 1e-9
    snr = float(np.abs(acc[best]).mean() / noise)
    mark_id, ok = _decode((acc[best] > 0).astype(int))
    return Detection(found=ok and snr >= 3.0, mark_id=mark_id if ok else None, snr=round(snr, 1), frames=n, offset=best)


# ------------------------------------------------------------------ registry

def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def register(p, mark_id: int, final: Path):
    """Record an export: which project it came from, when, and the hash of the exact file."""
    digest = sha256(final)
    rec = {"mark": mark_hex(mark_id), "project": p.id, "created": time.time(), "sha256": digest,
           "bytes": final.stat().st_size, "aspect": p.aspect, "engines": sorted({s.engine for s in p.scenes}),
           "seconds": round(sum(s.duration or 0 for s in p.scenes), 1)}
    store.doc_put("provenance", rec["mark"], rec)
    store.doc_put("provenance_files", digest, {"mark": rec["mark"]})
    return rec


def lookup(mark: str):
    try:
        return store.doc_get("provenance", mark)
    except FileNotFoundError:
        return None


def verify(path) -> dict:
    """What we can say about an uploaded video: the exact file, a mark, or nothing found."""
    digest = sha256(path)
    try:
        exact = store.doc_get("provenance_files", digest)
    except FileNotFoundError:
        exact = None
    d = detect(path)
    rec = lookup(exact["mark"]) if exact else (lookup(mark_hex(d.mark_id)) if d.found else None)
    if exact and rec:
        verdict = "exact"
    elif rec:
        verdict = "mark"
    else:
        verdict = "none"
    out = {"verdict": verdict, "frames": d.frames, "snr": d.snr, "trimmed": bool(d.found and d.offset > 0)}
    if rec:
        out["origin"] = {k: rec[k] for k in ("created", "project", "engines", "seconds", "aspect")}
    if verdict == "none" and d.frames < 90:
        out["note"] = "The video is too short to check reliably."
    return out


def selftest() -> bool:
    """A real embed and read-back on a generated clip. Fails when the key is missing or ffmpeg is broken."""
    tmp = config.DATA / f".wmtest-{secrets.token_hex(4)}"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        src, aud, out = tmp / "src.mp4", tmp / "a.wav", tmp / "out.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "gradients=size=640x360:rate=30:duration=8:speed=0.02:c0=0x1d2a3a:c1=0xe8dfc8",
                        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "8", "-c:v", "libx264", "-c:a", "pcm_s16le", str(tmp / "av.mkv")],
                       check=True, timeout=120)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp / "av.mkv"), "-an", str(src)], check=True, timeout=120)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp / "av.mkv"), "-vn", str(aud)], check=True, timeout=120)
        embed(src, aud, out, 0xC0FFEE01)
        d = detect(out)
        return d.found and d.mark_id == 0xC0FFEE01
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
