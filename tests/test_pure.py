import pytest

from backend import gemini, pipeline, tts
from backend.models import Project, Scene


def test_content_hash_is_stable_and_sensitive():
    assert pipeline.h("a", {"x": 1, "y": [1, 2]}) == pipeline.h("a", {"y": [1, 2], "x": 1})
    assert pipeline.h("a", {"x": 1}) != pipeline.h("a", {"x": 2})


def test_srt_times_and_sentence_split():
    assert pipeline.srt_time(3661.5) == "01:01:01,500"
    p = Project(topic="t", scenes=[Scene(narration="First one. Second one here!", duration=4.45, engine="title")])
    import tempfile
    from pathlib import Path
    f = Path(tempfile.mkdtemp()) / "a.srt"
    pipeline.write_srt(p, f)
    text = f.read_text()
    assert "First one." in text and "Second one here!" in text and text.count("-->") == 2


@pytest.mark.parametrize("script,heard,ok", [
    ("The cat sat on the mat.", "the cat sat on the mat", True),
    ("There are 3 reasons.", "there are three reasons", True),
    ("The cat sat on the mat.", "completely different words said here", False),
    ("Short line.", "short line and then a lot of extra rambling words appended", False),
])
def test_transcript_check(script, heard, ok):
    assert tts._matches(script, heard) is ok


def test_vertex_client_uses_service_identity_and_per_model_location(monkeypatch):
    from backend import config
    made = []
    monkeypatch.setattr(gemini.genai, "Client", lambda **kw: made.append(kw) or object())
    monkeypatch.setattr(gemini, "_clients", {})
    monkeypatch.setattr(config, "VERTEX", True)
    monkeypatch.setattr(config, "GCP_PROJECT", "proj")
    monkeypatch.setattr(config, "VERTEX_LOCATION", "global")
    monkeypatch.setattr(config, "VERTEX_LOCATION_OVERRIDES", {"veo": "us-central1"})
    a, b, c = gemini.client("gem"), gemini.client("veo"), gemini.client("gem")
    assert a is c and a is not b
    assert made == [{"vertexai": True, "project": "proj", "location": "global"},
                    {"vertexai": True, "project": "proj", "location": "us-central1"}]
    assert all("api_key" not in m for m in made)
