"""One Gemini client for the whole app. STUDIO_VERTEX=1 switches to Vertex AI."""
import json
import os
import threading
import time
import wave
from pathlib import Path

from google import genai
from google.genai import types

from . import config


_client = None
_client_lock = threading.Lock()


def client():
    """One shared client. Created under a lock: a second client built by a racing thread
    would be garbage-collected (and closed) mid-request."""
    global _client
    with _client_lock:
        if _client is None:
            if config.VERTEX:
                _client = genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"],
                                       location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
            else:
                _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        return _client


def _retry(fn, tries=3):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # rate limits / transient 5xx
            if i == tries - 1:
                raise
            print(f"[gemini] retry {i + 1}: {e}", flush=True)
            time.sleep(4 * (i + 1))


def text(prompt, model=None, system=None, parts=None, temperature=None):
    contents = [prompt] + list(parts or [])
    cfg = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
    r = _retry(lambda: client().models.generate_content(model=model or config.MODEL_FAST, contents=contents, config=cfg))
    return r.text or ""


def json_call(prompt, schema=None, model=None, system=None, parts=None, temperature=None):
    """Structured output. `schema` is a pydantic model or JSON schema dict."""
    contents = [prompt] + list(parts or [])
    cfg = types.GenerateContentConfig(system_instruction=system, temperature=temperature,
                                      response_mime_type="application/json", response_schema=schema)
    r = _retry(lambda: client().models.generate_content(model=model or config.MODEL_FAST, contents=contents, config=cfg))
    return json.loads(r.text)


def image(prompt, out, aspect="16:9", refs=(), model=None):
    """Nano Banana. `refs` are image paths used for character/style consistency."""
    parts = [types.Part.from_bytes(data=Path(p).read_bytes(), mime_type="image/png") for p in refs]
    cfg = types.GenerateContentConfig(response_modalities=["IMAGE"],
                                      image_config=types.ImageConfig(aspect_ratio=aspect))

    def go():
        r = client().models.generate_content(model=model or config.MODEL_IMAGE, contents=parts + [prompt], config=cfg)
        for p in r.candidates[0].content.parts:
            if p.inline_data and p.inline_data.data:
                return p.inline_data.data
        raise RuntimeError("no image returned")

    data = _retry(go)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    raw = Path(out).with_suffix(".raw")
    raw.write_bytes(data)
    # normalise whatever came back (png/jpeg/webp) to png
    from PIL import Image
    Image.open(raw).convert("RGB").save(out)
    raw.unlink()
    return Path(out)


def tts(text_in, out_wav, voice="Charon", style=None, model=None):
    """Gemini TTS -> 24 kHz mono 16-bit wav."""
    prompt = f"{style}: {text_in}" if style else text_in
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))))

    def go():
        r = client().models.generate_content(model=model or config.MODEL_TTS, contents=prompt, config=cfg)
        return r.candidates[0].content.parts[0].inline_data.data

    pcm = _retry(go)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    return Path(out_wav)


def video(prompt, out, aspect="16:9", seconds=8, image_path=None, model=None):
    """Veo. Blocks until the clip is ready (usually 1-3 min)."""
    kw = {}
    if image_path:
        kw["image"] = types.Image(image_bytes=Path(image_path).read_bytes(), mime_type="image/png")
    op = _retry(lambda: client().models.generate_videos(
        model=model or config.MODEL_VEO, prompt=prompt,
        config=types.GenerateVideosConfig(aspect_ratio=aspect, duration_seconds=seconds, number_of_videos=1), **kw))
    while not op.done:
        time.sleep(8)
        op = client().operations.get(op)
    if op.error:
        raise RuntimeError(f"veo: {op.error}")
    vids = op.response.generated_videos if op.response else None
    if not vids:
        raise RuntimeError("veo returned no video (likely filtered)")
    v = vids[0].video
    client().files.download(file=v)
    v.save(str(out))
    return Path(out)


def music(prompt, out):
    """Lyria clip -> audio file. Falls back to a plain prompt if the first is refused."""
    cfg = types.GenerateContentConfig(response_modalities=["AUDIO"])
    for pr in (prompt, "Calm minimal ambient instrumental, soft piano and warm pads, slow, no drums, no vocals."):
        r = _retry(lambda: client().models.generate_content(model=config.MODEL_MUSIC, contents=pr, config=cfg))
        cand = (r.candidates or [None])[0]
        for p in (cand.content.parts if cand and cand.content and cand.content.parts else []):
            if p.inline_data and p.inline_data.data:
                Path(out).write_bytes(p.inline_data.data)
                return Path(out), p.inline_data.mime_type
    raise RuntimeError("no music returned")
