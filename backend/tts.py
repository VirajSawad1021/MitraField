"""Narration.

Narrators are cloned voices (voices.py: the channel's own, plus any profile a person creates) rendered by the
OmniVoice GPU service, and Gemini TTS voices. A cloned voice that cannot be rendered falls back to a Gemini
voice rather than failing the beat. Every line is transcribed after synthesis and retaken if the voice added,
dropped or garbled words.
"""
import difflib
import re
import subprocess
import threading
from pathlib import Path

from . import config, gemini, log, store, voices
from .media import duration

GEMINI_VOICES = ["Charon", "Kore", "Puck", "Fenrir", "Aoede", "Orus", "Leda", "Zephyr"]
GEMINI_TEMPO = 1.1   # Gemini voices read slowly for explainers
FALLBACK_VOICE = "Charon"
DEFAULT_VOICE = "Johnny" if config.OMNI_URL else FALLBACK_VOICE


def catalogue():
    """(ready cloned voices, Gemini voices) for the UI: [{id, name, builtin}], [id]."""
    mine = []
    if voices.available():
        mine = [{"id": v.id, "name": v.name, "builtin": v.builtin, "status": v.status}
                for v in store.voice_list() if v.status != "error"]
    return mine, GEMINI_VOICES


logger = log.get("tts")
_omni_lock = threading.Lock()   # one request at a time per process; the GPU service queues the rest


def _words(s):
    return re.findall(r"[a-z0-9']+", s.lower())


def _matches(script, heard):
    """True when what was spoken is the script (numbers may be read as digits or words)."""
    a, b = _words(script), _words(heard)
    if not a:
        return True
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ratio >= 0.75 and len(b) <= len(a) * 1.3 + 3


def _heard(wav: Path):
    from google.genai import types
    part = types.Part.from_bytes(data=wav.read_bytes(), mime_type="audio/wav")
    return gemini.text("Transcribe this narration verbatim. Output only the spoken words.", parts=[part])


def synth(text, out_wav, voice=DEFAULT_VOICE, pace=1.0, check=True, language="English"):
    """Synthesize one line to a trimmed 48 kHz mono wav. Returns (path, seconds)."""
    out_wav = Path(out_wav)
    raw = out_wav.with_name(out_wav.stem + "_raw.wav")
    profile = voices.ready(voice)
    if profile is None and voice not in GEMINI_VOICES:
        voice = FALLBACK_VOICE   # a deleted or unfinished profile, or a deployment without the voice service
    tries = 3 if check else 1
    for attempt in range(tries):
        omni = profile is not None
        if omni:
            try:
                with _omni_lock:
                    voices.synth(text, profile, raw)
            except Exception as e:   # cold GPU, quota, outage: keep the video going in a Gemini voice
                logger.warning("voice %s unavailable, using %s: %s", profile.id, FALLBACK_VOICE, e)
                profile, voice, omni = None, FALLBACK_VOICE, False
        if not omni:
            gemini.tts(text, raw, voice=voice)   # plain text only: style prompts get read aloud
        post = profile.post_filter if omni else None
        tempo = pace * (1.0 if omni else GEMINI_TEMPO)
        chain = [post] if post else []
        chain += ["silenceremove=start_periods=1:start_threshold=-50dB", "areverse",
                  "silenceremove=start_periods=1:start_threshold=-50dB", "areverse"]
        if abs(tempo - 1.0) > 0.005:
            chain.append(f"atempo={tempo:.3f}")
        chain.append("apad=pad_dur=0.45")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", ",".join(chain),
                        "-ar", "48000", "-ac", "1", str(out_wav)], check=True)
        raw.unlink(missing_ok=True)
        if not check or language.lower() != "english":
            break
        try:
            heard = _heard(out_wav)
        except Exception as e:   # the check is a safety net, never a blocker
            logger.warning("transcript check skipped: %s", e)
            break
        if _matches(text, heard):
            break
        logger.info("retake %d: heard %r", attempt + 1, heard[:120])
    return out_wav, duration(out_wav)
