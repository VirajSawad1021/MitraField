"""Narration.

Default narrators are the channel's own OmniVoice clones (Johnny, Viraj v8) on the local
TTS server. Gemini TTS voices remain available. Every line is transcribed after synthesis
and retaken if the voice added, dropped or garbled words.
"""
import difflib
import re
import subprocess
import threading
from pathlib import Path

import requests

from . import config, gemini
from .media import duration

# name -> (OmniVoice voice id, post filter). Johnny's filter is the approved "Lively" pass.
LIVELY = ("acompressor=threshold=-19dB:ratio=3:attack=5:release=130,"
          "equalizer=f=3300:t=q:w=1.1:g=3.3,highshelf=f=8000:g=2,atempo=1.08")
OMNI_VOICES = {
    "Johnny": ("c319e078-00eb-4b99-8e3f-6352933204d0", LIVELY),
    "Viraj_v8": ("f08990de-b71b-48fb-8da4-466ff71a93de", None),
}
GEMINI_VOICES = ["Charon", "Kore", "Puck", "Fenrir", "Aoede", "Orus", "Leda", "Zephyr"]
GEMINI_TEMPO = 1.1   # Gemini voices read slowly for explainers
VOICES = list(OMNI_VOICES) + GEMINI_VOICES
DEFAULT_VOICE = "Johnny"

_omni_lock = threading.Lock()   # one request at a time: the GPU box is shared


def _omni(text, voice, raw: Path):
    vid, _ = OMNI_VOICES[voice]
    with _omni_lock:
        r = requests.post(f"{config.OMNI_URL}/tts/generate-from-voice/{vid}", data={"text": text}, timeout=300)
    if r.status_code != 200:
        raise RuntimeError(f"OmniVoice {r.status_code}: {r.text[:200]}")
    raw.write_bytes(r.content)


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
    omni = voice in OMNI_VOICES
    post = OMNI_VOICES[voice][1] if omni else None
    tempo = pace * (1.0 if omni else GEMINI_TEMPO)
    tries = 3 if check else 1
    for attempt in range(tries):
        if omni:
            _omni(text, voice, raw)
        else:
            gemini.tts(text, raw, voice=voice)   # plain text only: style prompts get read aloud
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
            print(f"[tts] check skipped: {e}", flush=True)
            break
        if _matches(text, heard):
            break
        print(f"[tts] retake {attempt + 1}: heard {heard[:120]!r}", flush=True)
    return out_wav, duration(out_wav)
