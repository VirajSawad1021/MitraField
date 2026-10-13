"""Paths, model ids and render settings. Everything tunable lives here."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "projects"
ASSETS = ROOT / "assets"
DATA.mkdir(parents=True, exist_ok=True)

for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

VERTEX = os.environ.get("STUDIO_VERTEX") == "1"

MODEL_DIRECTOR = os.environ.get("STUDIO_MODEL_DIRECTOR", "gemini-3.1-pro-preview")
MODEL_FAST = os.environ.get("STUDIO_MODEL_FAST", "gemini-3.5-flash")
MODEL_CODE = os.environ.get("STUDIO_MODEL_CODE", "gemini-3.5-flash")
MODEL_IMAGE = os.environ.get("STUDIO_MODEL_IMAGE", "gemini-3.1-flash-image")
MODEL_TTS = os.environ.get("STUDIO_MODEL_TTS", "gemini-3.8-flash-tts")
MODEL_VEO = os.environ.get("STUDIO_MODEL_VEO", "veo-3.1-fast-generate-preview")
MODEL_MUSIC = os.environ.get("STUDIO_MODEL_MUSIC", "lyria-3-clip-preview")

# Manim lives in the channel venv; we call it as a subprocess.
MANIM_PY = os.environ.get("STUDIO_MANIM_PY", str(ROOT.parent / "YT/ai_video_generator_gpu/venv/bin/python"))
JOHNNY_URL = os.environ.get("STUDIO_JOHNNY_URL", "http://localhost:8002")

FPS = 30
SIZES = {"16:9": (1920, 1080), "9:16": (1080, 1920)}

# Look: flat near-black, warm ink, one accent. Shared by every engine.
BG = "#0A0A0B"
INK = "#F4F1EA"
MUTED = "#8C8A85"
ACCENT = "#FF5A36"
ACCENT2 = "#4FB3FF"
