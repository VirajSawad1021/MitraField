"""Veo 3.1 hero shots. Expensive: the director uses it for at most 2 moments per video.
Falls back to the image engine if generation fails or is filtered."""
from .. import config, gemini
from .base import Engine


class VeoEngine(Engine):
    name = "veo"
    heavy = False
    stretch_max = 1.35
    label = "Video shot (Veo)"
    blurb = ("Generated cinematic live-action video, 8 s. Real motion: crowds, nature, machines working, historical "
             "re-creations, dramatic establishing shots. Expensive: max 2 per video, only for hero moments.")
    params_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "shot description: subject, action, setting, lighting, lens, camera movement. No text on screen, no dialogue."},
        },
        "required": ["prompt"],
    }

    def render(self, scene, project, duration, out_dir):
        out = out_dir / "veo.mp4"
        if out.exists():
            return out
        prompt = (scene.params.get("prompt") or scene.brief) + " Cinematic, natural motion, no on-screen text, no subtitles, no logos."
        try:
            return gemini.video(prompt, out, aspect=project.aspect, seconds=8)
        except Exception as e:
            print(f"[veo] failed, falling back to image: {e}", flush=True)
            from . import REGISTRY
            img = REGISTRY["image"]
            s2 = scene.model_copy(update={"params": {"style": "photo", "shots": [
                {"prompt": scene.params.get("prompt") or scene.brief, "move": "push_in"}]}})
            return img.render(s2, project, duration, out_dir)


ENGINE = VeoEngine()
