"""Paths, model ids, runtime topology and render settings. Everything tunable lives here.

Runtime topology (see docs/ARCHITECTURE.md):
  STUDIO_ROLE   all (local dev) | api (public, stateless) | worker (private, renders)
  STUDIO_STORE  file (local dev) | firestore (project state, shared by every instance)
  STUDIO_QUEUE  local (in-process threads) | cloudtasks (durable, retried, rate limited)
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def env(name, default=""):
    return os.environ.get(name, default)


def env_float(name, default):
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


DATA = Path(env("STUDIO_DATA", str(ROOT / "data" / "projects")))   # a Cloud Storage mount on Cloud Run
ASSETS = ROOT / "assets"
DATA.mkdir(parents=True, exist_ok=True)

ROLE = env("STUDIO_ROLE", "all")
STORE = env("STUDIO_STORE", "file")
QUEUE = env("STUDIO_QUEUE", "local")

# Google Cloud
GCP_PROJECT = env("GOOGLE_CLOUD_PROJECT")
GCP_REGION = env("STUDIO_REGION", "asia-southeast1")
VERTEX = env("STUDIO_VERTEX") == "1"
VERTEX_LOCATION = env("GOOGLE_CLOUD_LOCATION", "global")
VERTEX_LOCATION_OVERRIDES = {   # models that are not served from the default location
    k: v for k, v in (kv.split("=", 1) for kv in env("STUDIO_VERTEX_LOCATIONS").split(";") if "=" in kv)}
TASKS_QUEUE = env("STUDIO_TASKS_QUEUE", "mitrafield-render")
TASKS_SA = env("STUDIO_TASKS_SA")            # service account whose OIDC token Cloud Tasks sends to the worker
WORKER_URL = env("STUDIO_WORKER_URL")        # https URL of the private worker service
CALLERS = [c for c in env("STUDIO_CALLERS").split(",") if c]   # extra service accounts allowed to call the worker (the deploy smoke test)

# Spend guards (USD). A request that would start a billable call past either cap is refused.
CAP_DAY_USD = env_float("STUDIO_CAP_DAY_USD", 25.0)
CAP_PROJECT_USD = env_float("STUDIO_CAP_PROJECT_USD", 5.0)

MODEL_DIRECTOR = env("STUDIO_MODEL_DIRECTOR", "gemini-3.1-pro-preview")
MODEL_FAST = env("STUDIO_MODEL_FAST", "gemini-3.5-flash")
MODEL_CODE = env("STUDIO_MODEL_CODE", "gemini-3.5-flash")
MODEL_IMAGE = env("STUDIO_MODEL_IMAGE", "gemini-3.1-flash-image")
MODEL_TTS = env("STUDIO_MODEL_TTS", "gemini-3.8-flash-tts")
MODEL_VEO = env("STUDIO_MODEL_VEO", "veo-3.1-fast-generate-preview")
MODEL_VEO_DRAFT = env("STUDIO_MODEL_VEO_DRAFT", "veo-3.1-lite-generate-preview")
MODEL_MUSIC = env("STUDIO_MODEL_MUSIC", "lyria-3-clip-preview")

# Manim runs as a subprocess of the interpreter that has it installed (this one, unless overridden).
MANIM_PY = env("STUDIO_MANIM_PY", sys.executable)
OMNI_URL = env("STUDIO_OMNI_URL", "http://localhost:8002")   # OmniVoice TTS server; empty = not available

FPS = 30
SIZES = {"16:9": (1920, 1080), "9:16": (1080, 1920)}

# Look: flat near-black, warm ink, one accent. Shared by every engine.
BG = "#0A0A0B"
INK = "#F4F1EA"
MUTED = "#8C8A85"
ACCENT = "#FF5A36"
ACCENT2 = "#4FB3FF"
