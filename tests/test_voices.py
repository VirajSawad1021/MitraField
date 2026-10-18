import subprocess

import pytest
from fastapi.testclient import TestClient

from backend import app as appmod
from backend import config, jobs, store, tts, voices
from backend.models import VoiceProfile

client = TestClient(appmod.app)


def tone(path, seconds):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}", str(path)], check=True)
    return path.read_bytes()


@pytest.fixture(autouse=True)
def voice_service(monkeypatch):
    monkeypatch.setattr(config, "OMNI_URL", "http://voice.test")


@pytest.fixture
def queued(monkeypatch):
    got = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: got.append((kind, p)))
    return got


def post(wav, **kw):
    form = {"name": "Asha", "consent": "true", **kw}
    return client.post("/api/voices", data=form, files={"file": ("me.wav", wav, "audio/wav")})


def test_create_stores_the_sample_and_queues_a_build(tmp_path, queued):
    r = post(tone(tmp_path / "a.wav", 5))
    assert r.status_code == 200
    v = r.json()
    assert v["status"] == "pending" and v["name"] == "Asha" and v["id"].startswith("v_")
    assert (config.DATA / "voices" / v["id"] / "ref.wav").exists()
    assert queued == [("voice_build", {"vid": v["id"]})]


def test_consent_is_required(tmp_path, queued):
    r = post(tone(tmp_path / "a.wav", 5), consent="false")
    assert r.status_code == 400 and "permission" in r.json()["detail"]
    assert not queued and store.voice_list() == []


def test_rejects_short_and_non_audio_samples(tmp_path, queued):
    assert post(tone(tmp_path / "a.wav", 1)).status_code == 400
    assert post(b"MZ\x90 not audio at all").status_code == 400
    assert store.voice_list() == [] and not list((config.DATA / "voices").glob("*"))


def test_profile_count_is_capped(tmp_path, queued, monkeypatch):
    monkeypatch.setattr(config, "MAX_VOICES", 1)
    wav = tone(tmp_path / "a.wav", 5)
    assert post(wav).status_code == 200
    assert post(wav).status_code == 400


def test_cloning_off_without_a_voice_service(tmp_path, queued, monkeypatch):
    monkeypatch.setattr(config, "OMNI_URL", "")
    assert post(tone(tmp_path / "a.wav", 5)).status_code == 400


def test_build_transcribes_and_marks_ready(tmp_path, monkeypatch):
    v = VoiceProfile(name="Asha")
    (store.vdir(v.id) / "ref.wav").write_bytes(tone(tmp_path / "a.wav", 4))
    store.voice_save(v)
    monkeypatch.setattr(voices.gemini, "text", lambda *a, **k: "  hello there  ")
    seen = {}
    monkeypatch.setattr(voices, "_post", lambda path, timeout, **kw: seen.update(path=path, text=kw["data"]["ref_text"]) or b"PROMPT")
    voices.build(v.id)
    got = store.voice_get(v.id)
    assert got.status == "ready" and got.reference_text == "hello there"
    assert seen == {"path": "/voices/build", "text": "hello there"}
    assert (config.DATA / "voices" / v.id / "prompt.pt").read_bytes() == b"PROMPT"
    assert voices.ready(v.id).id == v.id


def test_build_failure_is_recorded_on_the_profile(tmp_path, monkeypatch):
    v = VoiceProfile(name="Asha", reference_text="hi")
    (store.vdir(v.id) / "ref.wav").write_bytes(b"x")
    store.voice_save(v)

    def boom(*a, **k):
        raise RuntimeError("voice service 503")
    monkeypatch.setattr(voices, "_post", boom)
    with pytest.raises(RuntimeError):
        voices.build(v.id)
    assert store.voice_get(v.id).status == "error"
    assert voices.ready(v.id) is None


def test_channel_voices_cannot_be_deleted_but_others_can(tmp_path, queued):
    store.voice_save(VoiceProfile(id="Johnny", name="Johnny", builtin=True, status="ready"))
    assert client.delete("/api/voices/Johnny").status_code == 403
    v = post(tone(tmp_path / "a.wav", 5)).json()
    assert client.delete(f"/api/voices/{v['id']}").status_code == 200
    assert client.delete(f"/api/voices/{v['id']}").status_code == 404
    assert not (config.DATA / "voices" / v["id"]).exists()
    assert client.delete("/api/voices/..%2Fx").status_code in (404, 405)


def test_voice_media_is_never_served():
    store.vdir("v_x")
    (config.DATA / "voices" / "v_x" / "ref.wav").write_bytes(b"RIFF")
    (config.DATA / "voices" / "v_x" / "prompt.pt").write_bytes(b"x")
    assert client.get("/files/voices/v_x/ref.wav").status_code == 404
    assert client.get("/files/voices/v_x/prompt.pt").status_code == 404


def test_meta_lists_profiles(queued):
    store.voice_save(VoiceProfile(id="Johnny", name="Johnny", builtin=True, status="ready"))
    m = client.get("/api/meta").json()
    assert m["cloning"] is True and [v["id"] for v in m["voice_profiles"]] == ["Johnny"]
    assert "Charon" in m["voices"]


def _ready_profile(tmp_path):
    v = VoiceProfile(name="Asha", status="ready")
    (store.vdir(v.id) / "prompt.pt").write_bytes(b"P")
    store.voice_save(v)
    return v


def test_narration_falls_back_to_a_gemini_voice_when_the_gpu_service_is_down(tmp_path, monkeypatch):
    v = _ready_profile(tmp_path)

    def down(*a, **k):
        raise RuntimeError("voice service 503")
    monkeypatch.setattr(voices, "_post", down)
    used = []
    monkeypatch.setattr(tts.gemini, "tts", lambda text, out, voice: used.append(voice) or tone(out, 2))
    wav, secs = tts.synth("Hello there.", tmp_path / "o.wav", voice=v.id, check=False)
    assert used == [tts.FALLBACK_VOICE] and secs > 1


def test_narration_uses_the_cloned_voice_when_ready(tmp_path, monkeypatch):
    v = _ready_profile(tmp_path)
    sent = {}
    monkeypatch.setattr(voices, "_post", lambda path, timeout, **kw: sent.update(path=path, prompt=kw["files"]["prompt"][1]) or tone(tmp_path / "r.wav", 2))
    wav, secs = tts.synth("Hello there.", tmp_path / "o.wav", voice=v.id, check=False)
    assert sent == {"path": "/tts/synthesize", "prompt": b"P"} and secs > 1


def test_unknown_or_unfinished_voice_uses_a_gemini_voice(tmp_path, monkeypatch):
    used = []
    monkeypatch.setattr(tts.gemini, "tts", lambda text, out, voice: used.append(voice) or tone(out, 2))
    tts.synth("Hi there.", tmp_path / "a.wav", voice="../../etc/passwd", check=False)
    tts.synth("Hi there.", tmp_path / "b.wav", voice="v_nope", check=False)
    assert used == [tts.FALLBACK_VOICE, tts.FALLBACK_VOICE]
