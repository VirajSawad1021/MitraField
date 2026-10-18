from backend import director, engines, gemini
from backend.models import Project, Scene


def _capture(monkeypatch, reply):
    seen = {}

    def fake(prompt, **kw):
        seen.update(prompt=prompt, **kw)
        return reply
    monkeypatch.setattr(gemini, "json_call", fake)
    return seen


def test_storyboard_passes_the_users_direction_to_the_director(monkeypatch):
    seen = _capture(monkeypatch, {"title": "T", "cast": [], "scenes": [
        {"narration": "One.", "engine": next(iter(engines.REGISTRY)), "brief": "b"}]})
    p = Project(topic="vectors", instructions="Use only manim. No generated images or video.")
    director.storyboard(p)
    assert "Direction from the user (binding):\nUse only manim. No generated images or video." in seen["prompt"]
    assert "binding and overrides" in seen["system"]


def test_no_direction_leaves_the_prompt_unchanged(monkeypatch):
    seen = _capture(monkeypatch, {"title": "T", "cast": [], "scenes": []})
    director.storyboard(Project(topic="vectors", instructions="   "))
    assert "Direction from the user" not in seen["prompt"]


def test_rewrite_scene_keeps_the_direction(monkeypatch):
    eng = next(iter(engines.REGISTRY))
    seen = _capture(monkeypatch, {"narration": "n", "engine": eng, "brief": "b"})
    p = Project(topic="x", instructions="text only", scenes=[Scene(narration="a", engine=eng)])
    director.rewrite_scene(p, p.scenes[0], "make it shorter")
    assert "text only" in seen["prompt"]
