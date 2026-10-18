"""OmniVoice as a private GPU service. Stateless: no database, no storage, no per-user data on the instance.

    POST /voices/build       multipart: audio (wav), ref_text   ->  the voice-clone prompt (bytes)
    POST /tts/synthesize     multipart: text, prompt (the bytes from /voices/build)  ->  audio/wav
    GET  /health

The caller (the studio worker) keeps the prompts and sends one with every synthesis request, so any instance can
serve any voice and a new one starts with nothing to restore. The model weights are baked into the image, so a
cold start is a GPU attach plus a model load, with no download.
"""
import io
import logging
import os
import tempfile
import threading
from contextlib import asynccontextmanager

import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

MODEL = os.environ.get("MODEL_NAME", "k2-fsa/OmniVoice")
STEPS = int(os.environ.get("NUM_STEP", "16"))
SAMPLE_RATE = 24000
MAX_CHARS = 1500
MAX_AUDIO = 5 * 1024 * 1024
MAX_PROMPT = 1024 * 1024

log = logging.getLogger("voice")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
state: dict = {}
gpu = threading.Lock()   # one generation at a time per instance; extra requests queue here


@asynccontextmanager
async def lifespan(_):
    from omnivoice import OmniVoice
    cuda = torch.cuda.is_available()
    log.info("loading %s (cuda=%s)", MODEL, cuda)
    state["model"] = OmniVoice.from_pretrained(MODEL, device_map="cuda" if cuda else "cpu",
                                               dtype=torch.float16 if cuda else torch.float32, load_asr=False)
    log.info("ready")
    yield
    state.clear()


app = FastAPI(title="mitrafield-voice", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
def health():
    return {"ok": "model" in state, "cuda": torch.cuda.is_available()}


def _with_tempfile(data: bytes, suffix: str, fn):
    with tempfile.NamedTemporaryFile(suffix=suffix) as f:
        f.write(data)
        f.flush()
        return fn(f.name)


@app.post("/voices/build")
def build(audio: UploadFile = File(...), ref_text: str = Form(...)):
    data = audio.file.read(MAX_AUDIO + 1)
    if not data or len(data) > MAX_AUDIO or not ref_text.strip():
        raise HTTPException(422, "need a short audio sample and its transcript")

    def make(path):
        with gpu:
            prompt = state["model"].create_voice_clone_prompt(ref_audio=path, ref_text=ref_text.strip()[:600])
        with tempfile.NamedTemporaryFile(suffix=".pt") as out:
            prompt.save(out.name)
            out.seek(0)
            return out.read()
    return Response(_with_tempfile(data, ".wav", make), media_type="application/octet-stream")


@app.post("/tts/synthesize")
def synthesize(text: str = Form(...), prompt: UploadFile = File(...)):
    from omnivoice import VoiceClonePrompt
    text = text.strip()
    blob = prompt.file.read(MAX_PROMPT + 1)
    if not text or len(text) > MAX_CHARS or not blob or len(blob) > MAX_PROMPT:
        raise HTTPException(422, f"text must be 1..{MAX_CHARS} characters and a voice prompt is required")
    vp = _with_tempfile(blob, ".pt", VoiceClonePrompt.load)
    with gpu:
        audio = state["model"].generate(text=text, voice_clone_prompt=vp, num_step=STEPS)
    buf = io.BytesIO()
    sf.write(buf, audio[0], SAMPLE_RATE, format="WAV")
    return Response(buf.getvalue(), media_type="audio/wav")
