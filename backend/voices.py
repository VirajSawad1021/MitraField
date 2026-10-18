"""Voice profiles: clone a narrator from a short sample of someone's own voice.

    create()  validates and normalises the sample, stores it, and queues a build
    build()   (worker job) writes the reference transcript if none was given, asks the OmniVoice GPU service for a
              voice-clone prompt, and marks the profile ready
    synth()   one line of narration in a profile's voice, through the GPU service

The GPU service is stateless: the prompt travels with every synthesis request, so it needs no database and no
storage. Profiles live in the project store; the sample and the prompt are in the media volume.
"""
import re
import subprocess
import time
from pathlib import Path

import requests

from . import config, costs, gemini, jobs, log, store
from .models import VoiceProfile

logger = log.get("voices")

MAX_UPLOAD = 10 * 1024 * 1024
MIN_SECONDS, MAX_SECONDS = 3.0, 20.0
ID = re.compile(r"^[A-Za-z0-9_]{1,40}$")
_tokens: dict = {}


class VoiceError(ValueError):
    """The sample or the request cannot be used; the message is shown to the person."""


def available() -> bool:
    return bool(config.OMNI_URL)


def _auth() -> dict:
    """An identity token for the private GPU service (Cloud Run), minted from the runtime service account.
    Not sent to a local server."""
    if not config.OMNI_URL.startswith("https://"):
        return {}
    hit = _tokens.get(config.OMNI_URL)
    if not hit or hit[0] < time.time():
        import google.auth.transport.requests
        from google.oauth2 import id_token
        tok = id_token.fetch_id_token(google.auth.transport.requests.Request(), config.OMNI_URL)
        _tokens[config.OMNI_URL] = hit = (time.time() + 45 * 60, tok)
    return {"Authorization": f"Bearer {hit[1]}"}


def _post(path, timeout, **kw):
    r = requests.post(f"{config.OMNI_URL}{path}", headers=_auth(), timeout=timeout, **kw)
    if r.status_code != 200:
        raise RuntimeError(f"voice service {r.status_code}: {r.text[:200]}")
    return r.content


def health() -> dict:
    r = requests.get(f"{config.OMNI_URL}/health", headers=_auth(), timeout=240)   # a cold GPU instance needs a while
    r.raise_for_status()
    return r.json()


def normalise(raw: bytes, dest: Path) -> float:
    """Decode whatever was uploaded (wav, mp3, m4a, ogg, a browser recording) to a mono 24 kHz wav, at most
    MAX_SECONDS long. Decoding it ourselves means the model only ever sees audio we produced."""
    if not raw or len(raw) > MAX_UPLOAD:
        raise VoiceError("The sample must be an audio file under 10 MB.")
    src = dest.with_suffix(".upload")
    src.write_bytes(raw)
    try:
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-t", str(MAX_SECONDS), "-ac", "1", "-ar", "24000",
                            "-af", "silenceremove=start_periods=1:start_threshold=-45dB", str(dest)],
                           capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise VoiceError("That audio could not be read.")
    finally:
        src.unlink(missing_ok=True)
    if r.returncode != 0 or not dest.exists():
        raise VoiceError("That does not look like an audio file.")
    from .media import duration
    secs = duration(dest)
    if secs < MIN_SECONDS:
        dest.unlink(missing_ok=True)
        raise VoiceError(f"The sample is {secs:.1f} s of speech; record at least {MIN_SECONDS:.0f} s of clear talking.")
    return secs


def create(name: str, audio: bytes, reference_text: str = "", language: str = "English", consent: bool = False) -> VoiceProfile:
    if not available():
        raise VoiceError("Voice cloning is not enabled on this deployment.")
    if not consent:
        raise VoiceError("Confirm that this is your own voice, or that you have permission to clone it.")
    name = " ".join(name.split())[:40]
    if not name:
        raise VoiceError("Give the voice a name.")
    if len(store.voice_list()) >= config.MAX_VOICES:
        raise VoiceError(f"This studio is limited to {config.MAX_VOICES} voices. Delete one first.")
    v = VoiceProfile(name=name, language=language, reference_text=" ".join(reference_text.split())[:600])
    try:
        normalise(audio, store.vdir(v.id) / "ref.wav")
    except VoiceError:
        store.voice_delete(v.id)
        raise
    store.voice_save(v)
    try:
        jobs.enqueue("voice_build", vid=v.id)
    except Exception:   # nothing will ever build it: do not leave a profile spinning
        store.voice_delete(v.id)
        raise
    return v


def build(vid):
    """Worker job. Idempotent: a ready profile is left alone."""
    v = store.voice_get(vid)
    if v.status == "ready":
        return
    try:
        ref = store.vdir(vid) / "ref.wav"
        if not v.reference_text:
            from google.genai import types
            with costs.track(f"voice-{vid}"):
                v.reference_text = gemini.text(
                    "Transcribe this recording verbatim. Output only the spoken words.",
                    parts=[types.Part.from_bytes(data=ref.read_bytes(), mime_type="audio/wav")]).strip()[:600]
        if not v.reference_text:
            raise VoiceError("No speech was found in the sample.")
        prompt = _post("/voices/build", 180, data={"ref_text": v.reference_text}, files={"audio": ("ref.wav", ref.read_bytes(), "audio/wav")})
        (store.vdir(vid) / "prompt.pt").write_bytes(prompt)
        v.status, v.error = "ready", None
    except costs.BudgetExceeded:
        raise
    except Exception as e:
        v.status, v.error = "error", str(e)[:300] if isinstance(e, VoiceError) else "The voice could not be built. Try a cleaner sample."
        logger.exception("voice build failed", extra={"vid": vid})
        store.voice_save(v)
        if not isinstance(e, VoiceError):
            raise
        return
    store.voice_save(v)


def ready(vid) -> VoiceProfile | None:
    """The profile behind a project's `voice`, when it is a usable cloned voice."""
    if not available() or not ID.match(vid or ""):
        return None
    try:
        v = store.voice_get(vid)
    except FileNotFoundError:
        return None
    return v if v.status == "ready" and (config.DATA / "voices" / vid / "prompt.pt").exists() else None


def synth(text: str, v: VoiceProfile, out: Path):
    out.write_bytes(_post("/tts/synthesize", 300, data={"text": text},
                          files={"prompt": ("prompt.pt", (config.DATA / "voices" / v.id / "prompt.pt").read_bytes(), "application/octet-stream")}))
