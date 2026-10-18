"""One Gemini client for the whole app. STUDIO_VERTEX=1 switches to Vertex AI."""
import json
import os
import threading
import time
import wave
from pathlib import Path

from google import genai
from google.genai import types

from . import config, costs, log

logger = log.get("gemini")

_clients = {}
_client_lock = threading.Lock()


def client(model=None):
    """One shared client per Vertex location (or the single API-key client). Created under a lock:
    a second client built by a racing thread would be garbage-collected (and closed) mid-request.

    On Cloud Run, Vertex AI authenticates as the service account, so no API key exists in the
    container. Some preview models are served from a different location than the default
    (STUDIO_VERTEX_LOCATIONS="veo-3.1-fast-generate-preview=us-central1;lyria-3-clip-preview=us-central1")."""
    loc = config.VERTEX_LOCATION_OVERRIDES.get(model, config.VERTEX_LOCATION) if config.VERTEX else None
    with _client_lock:
        if loc not in _clients:
            if config.VERTEX:
                _clients[loc] = genai.Client(vertexai=True, project=config.GCP_PROJECT, location=loc)
            else:
                _clients[loc] = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        return _clients[loc]


def _is_rate_limit(e):
    return "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)


def _retry(fn, tries=3, rate_tries=6):
    """Retry transient 5xx quickly, and rate limits (per-minute quotas) patiently: 10, 20, 40, 60, 60 s.
    A refused spend cap is never retried."""
    costs.guard()
    i = 0
    while True:
        try:
            return fn()
        except costs.BudgetExceeded:
            raise
        except Exception as e:
            i += 1
            limit = rate_tries if _is_rate_limit(e) else tries
            if i >= limit:
                raise
            wait = min(60, 10 * 2 ** (i - 1)) if _is_rate_limit(e) else 4 * i
            logger.warning("retry %d/%d in %ds: %s", i, limit - 1, wait, str(e)[:160], extra={"attempt": i})
            time.sleep(wait)


def text(prompt, model=None, system=None, parts=None, temperature=None):
    contents = [prompt] + list(parts or [])
    cfg = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
    m = model or config.MODEL_FAST
    r = _retry(lambda: client(m).models.generate_content(model=m, contents=contents, config=cfg))
    costs.tokens(m, r.usage_metadata)
    return r.text or ""


def json_call(prompt, schema=None, model=None, system=None, parts=None, temperature=None):
    """Structured output. `schema` is a pydantic model or JSON schema dict."""
    contents = [prompt] + list(parts or [])
    cfg = types.GenerateContentConfig(system_instruction=system, temperature=temperature,
                                      response_mime_type="application/json", response_schema=schema)
    m = model or config.MODEL_FAST
    r = _retry(lambda: client(m).models.generate_content(model=m, contents=contents, config=cfg))
    costs.tokens(m, r.usage_metadata)
    return json.loads(r.text)


def image(prompt, out, aspect="16:9", refs=(), model=None):
    """Nano Banana. `refs` are image paths, or (label, path) pairs, used for consistency."""
    parts = []
    for r in refs:
        label, path = r if isinstance(r, tuple) else (None, r)
        if label:
            parts.append(f"Reference image: {label}")
        parts.append(types.Part.from_bytes(data=Path(path).read_bytes(), mime_type="image/png"))
    cfg = types.GenerateContentConfig(response_modalities=["IMAGE"],
                                      image_config=types.ImageConfig(aspect_ratio=aspect))

    def go():
        r = client(model or config.MODEL_IMAGE).models.generate_content(model=model or config.MODEL_IMAGE, contents=parts + [prompt], config=cfg)
        for p in r.candidates[0].content.parts:
            if p.inline_data and p.inline_data.data:
                return p.inline_data.data
        raise RuntimeError("no image returned")

    data = _retry(go)
    m = model or config.MODEL_IMAGE
    costs.add("image", costs.IMAGE.get(m, 0.067), m, Path(out).name)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    raw = Path(out).with_suffix(".raw")
    raw.write_bytes(data)
    # normalise whatever came back (png/jpeg/webp) to png
    from PIL import Image
    Image.open(raw).convert("RGB").save(out)
    raw.unlink()
    return Path(out)


def tts(text_in, out_wav, voice="Charon", model=None):
    """Gemini TTS -> 24 kHz mono 16-bit wav. Send only the words to speak: any
    instruction in the prompt can end up read aloud."""
    prompt = text_in
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))))

    def go():
        r = client(model or config.MODEL_TTS).models.generate_content(model=model or config.MODEL_TTS, contents=prompt, config=cfg)
        return r.candidates[0].content.parts[0].inline_data.data

    pcm = _retry(go)
    costs.add("voice", len(pcm) / 48000 * costs.TTS_PER_SECOND, model or config.MODEL_TTS)
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
    op = _retry(lambda: client(model or config.MODEL_VEO).models.generate_videos(
        model=model or config.MODEL_VEO, prompt=prompt,
        config=types.GenerateVideosConfig(aspect_ratio=aspect, duration_seconds=seconds, number_of_videos=1), **kw))
    while not op.done:
        time.sleep(8)
        op = client(model or config.MODEL_VEO).operations.get(op)
    m = model or config.MODEL_VEO
    costs.add("video", seconds * costs.VEO_PER_SECOND.get(m, 0.10), m, f"{seconds}s clip")   # billed even if filtered
    if op.error:
        raise RuntimeError(f"veo: {op.error}")
    vids = op.response.generated_videos if op.response else None
    if not vids:
        raise RuntimeError("veo returned no video (likely filtered)")
    v = vids[0].video
    if not getattr(v, "video_bytes", None):   # Vertex returns the bytes inline; the Gemini API returns a file to fetch
        client(m).files.download(file=v)
    v.save(str(out))
    return Path(out)


def music(prompt, out):
    """Lyria clip -> audio file. Falls back to a plain prompt if the first is refused."""
    cfg = types.GenerateContentConfig(response_modalities=["AUDIO"])
    for pr in (prompt, "Calm minimal ambient instrumental, soft piano and warm pads, slow, no drums, no vocals."):
        r = _retry(lambda: client(config.MODEL_MUSIC).models.generate_content(model=config.MODEL_MUSIC, contents=pr, config=cfg))
        cand = (r.candidates or [None])[0]
        for p in (cand.content.parts if cand and cand.content and cand.content.parts else []):
            if p.inline_data and p.inline_data.data:
                Path(out).write_bytes(p.inline_data.data)
                costs.add("music", costs.MUSIC_PER_CLIP, config.MODEL_MUSIC)
                return Path(out), p.inline_data.mime_type
    raise RuntimeError("no music returned")
