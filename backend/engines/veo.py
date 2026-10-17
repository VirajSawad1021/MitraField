"""Veo 3.1 hero shots. Expensive: the director uses it for at most 2 moments per video.
Falls back to the image engine if generation fails or is filtered."""
from .. import cast, config, gemini
from ..look import finish
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
            "prompt": {"type": "string", "description": "shot description like a cinematographer's: subject, action, setting, lighting, lens, one camera move. Match the project's look. No text on screen, no dialogue."},
        },
        "required": ["prompt"],
    }

    def render(self, scene, project, duration, out_dir):
        out = out_dir / "veo.mp4"
        if out.exists():
            return out
        from ..look import get as get_look
        prompt = ((scene.params.get("prompt") or scene.brief) + f" Visual style: {get_look(project.look)['image']} "
                  "Natural motion, no on-screen text, no subtitles, no logos.")
        refs = cast.refs_for(project, scene)
        try:
            first = None
            if refs:   # draw an on-model first frame with the cast references, then animate it
                first = out_dir / "first_frame.png"
                if not first.exists():
                    st = cast.style_item(project)
                    gemini.image(finish(f"Opening frame of this shot: {scene.params.get('prompt') or scene.brief}. "
                                        f"{cast.describe(project, scene)}", st.description if st else None, project.look),
                                 first, aspect=project.aspect, refs=refs)
            # pay only for what the beat needs: the shortest Veo length that covers it (with slow-motion headroom)
            seconds = next((n for n in (4, 6, 8) if n * self.stretch_max >= duration), 8)
            model = config.MODEL_VEO_DRAFT if project.quality == "draft" else config.MODEL_VEO
            return gemini.video(prompt, out, aspect=project.aspect, seconds=seconds, image_path=first, model=model)
        except Exception as e:
            print(f"[veo] failed, falling back to image: {e}", flush=True)
            from . import REGISTRY
            img = REGISTRY["image"]
            s2 = scene.model_copy(update={"params": {"style": "photo", "shots": [
                {"prompt": scene.params.get("prompt") or scene.brief, "move": "push_in"}]}})
            return img.render(s2, project, duration, out_dir)


ENGINE = VeoEngine()
