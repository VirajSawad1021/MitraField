"""Narration. Gemini TTS by default; 'johnny:*' voices use the local OmniVoice clone."""
import subprocess
from pathlib import Path

import requests

from . import config, gemini
from .media import duration

GEMINI_VOICES = ["Charon", "Kore", "Puck", "Fenrir", "Aoede", "Orus", "Leda", "Zephyr", "Iapetus", "Algenib", "Sulafat", "Gacrux"]


def synth(text, out_wav, voice="Charon", style=None, pace=1.12):
    out_wav = Path(out_wav)
    raw = out_wav.with_name(out_wav.stem + "_raw.wav")
    if voice.startswith("johnny"):
        r = requests.post(f"{config.JOHNNY_URL}/tts", json={"text": text}, timeout=600)
        r.raise_for_status()
        raw.write_bytes(r.content)
    else:
        gemini.tts(text, raw, voice=voice, style=style)
    # trim edge silence, 48 kHz mono, small tail so scenes breathe
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af",
                    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                    f"silenceremove=start_periods=1:start_threshold=-50dB,areverse,atempo={pace:.3f},apad=pad_dur=0.45",
                    "-ar", "48000", "-ac", "1", str(out_wav)], check=True)
    raw.unlink(missing_ok=True)
    return out_wav, duration(out_wav)
