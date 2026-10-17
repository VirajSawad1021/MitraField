"""A consistent guide character across the whole video (Nano Banana with a reference sheet)."""
import threading
from concurrent.futures import ThreadPoolExecutor

from .. import cast, costs, gemini, store
from .base import Engine
from .image import XF, chain
from .motion import MOVES, camera

from ..look import CINEMATIC, finish

CHAR_STYLE = CINEMATIC


_lock = threading.Lock()


def reference(project):
    f = store.pdir(project.id) / "character.png"
    with _lock:
        if not f.exists():
            gemini.image(finish(f"Portrait reference of one real-looking adult presenter for a documentary about "
                                f"'{project.topic}': natural face, age-appropriate wardrobe, waist-up, neutral expression, "
                                f"plain softly lit grey backdrop"), f, aspect="1:1")
    return f


class CharacterEngine(Engine):
    name = "character"
    heavy = False
    label = "Presenter"
    blurb = ("A recurring real-looking person (the same face every time), filmed like a documentary: a presenter, "
             "an expert, or the person the story follows, acting out the idea in a real setting. Use for human "
             "moments, analogies and 'imagine you...' beats. Good every 4-6 scenes.")
    params_schema = {
        "type": "object",
        "properties": {
            "shots": {"type": "array", "description": "1-2 shots", "items": {"type": "object", "properties": {
                "action": {"type": "string", "description": "what the person does, with a natural expression, e.g. 'studies a cracked rivet under a desk lamp'"},
                "setting": {"type": "string", "description": "a real, specific location and lighting that matches the beat"},
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
        style = cast.style_item(project).description if cast.style_item(project) else None
        who = cast.describe(project, scene)
        shots = (scene.params.get("shots") or [{"action": scene.brief, "setting": "", "move": "push_in"}])[:2]
        n = max(1, min(len(shots), int(duration // 5) or 1))
        shots = shots[:n]

        def still(i):
            f = out_dir / f"char_{i}.png"
            if not f.exists():
                sh = shots[i]
                gemini.image(finish(f"Film still. The exact same person as in the reference image (same face, hair, build "
                                    f"and wardrobe), {sh['action']}. Setting: {sh['setting']}. {who}Medium or medium-wide "
                                    f"shot, the person clearly visible, candid and unposed", style), f, aspect=project.aspect, refs=refs)
            return f

        with ThreadPoolExecutor(2) as ex:
            stills = list(ex.map(costs.bind(still), range(n)))
        each = (duration + XF * (n - 1)) / n
        clips = [camera(stills[i], out_dir / f"shot_{i}.mp4", each, self.size(project), shots[i].get("move", "push_in"), 0.8)
                 for i in range(n)]
        return chain(clips, out_dir / "clip.mp4", [each] * n)


ENGINE = CharacterEngine()
