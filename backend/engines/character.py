"""A consistent guide character across the whole video (Nano Banana with a reference sheet)."""
import threading
from concurrent.futures import ThreadPoolExecutor

from .. import cast, gemini, store
from .base import Engine
from .image import XF, chain
from .motion import MOVES, camera

CHAR_STYLE = ("cute chibi 2D cartoon character, clean bold outlines, flat cel shading, big expressive eyes, "
              "friendly, storybook quality")


_lock = threading.Lock()


def reference(project):
    f = store.pdir(project.id) / "character.png"
    with _lock:
        if not f.exists():
            gemini.image(f"Character reference sheet: one {CHAR_STYLE} guide character who would present a video about "
                         f"'{project.topic}'. Full body, front view, neutral happy pose, plain light grey background, no text.",
                         f, aspect="1:1")
    return f


class CharacterEngine(Engine):
    name = "character"
    heavy = False
    label = "Guide character"
    blurb = ("The video's recurring chibi guide character (same look every time) reacting, pointing, or acting out "
             "the idea inside a simple illustrated scene. Use for emotional beats, analogies, 'imagine you...' moments, "
             "and to give the video a friendly face. Good every 4-6 scenes.")
    params_schema = {
        "type": "object",
        "properties": {
            "shots": {"type": "array", "description": "1-2 shots", "items": {"type": "object", "properties": {
                "action": {"type": "string", "description": "what the character does + expression, e.g. 'peers through a telescope, amazed'"},
                "setting": {"type": "string", "description": "simple illustrated background that matches the beat"},
                "move": {"type": "string", "enum": MOVES}}, "required": ["action", "setting", "move"]}},
        },
        "required": ["shots"],
    }

    def refs(self, scene, project):
        """Cast references when the project has a cast; the legacy single reference sheet otherwise."""
        refs = cast.refs_for(project, scene)
        if not any("(character)" in label for label, _ in refs):
            main = cast.main_character(project)
            if main and main.image:
                refs.insert(0, (f"{main.name} (character). Keep its exact design", main.image))
        if not any("(character)" in label for label, _ in refs):
            refs.insert(0, ("the guide character. Keep its exact design", str(reference(project))))
        return refs

    def render(self, scene, project, duration, out_dir):
        refs = self.refs(scene, project)
        style = (f"Art style: {cast.style_item(project).description}" if cast.style_item(project)
                 else f"Style: {CHAR_STYLE}")
        who = cast.describe(project, scene)
        shots = (scene.params.get("shots") or [{"action": scene.brief, "setting": "", "move": "push_in"}])[:2]
        n = max(1, min(len(shots), int(duration // 5) or 1))
        shots = shots[:n]

        def still(i):
            f = out_dir / f"char_{i}.png"
            if not f.exists():
                sh = shots[i]
                gemini.image(f"The exact same character as in the reference image (same design, colors, proportions), "
                             f"{sh['action']}. Setting: {sh['setting']}. {who}{style}. Full illustrated scene, "
                             f"character clearly visible, no text, no speech bubbles.", f, aspect=project.aspect, refs=refs)
            return f

        with ThreadPoolExecutor(2) as ex:
            stills = list(ex.map(still, range(n)))
        each = (duration + XF * (n - 1)) / n
        clips = [camera(stills[i], out_dir / f"shot_{i}.mp4", each, self.size(project), shots[i].get("move", "push_in"), 0.8)
                 for i in range(n)]
        return chain(clips, out_dir / "clip.mp4", [each] * n)


ENGINE = CharacterEngine()
