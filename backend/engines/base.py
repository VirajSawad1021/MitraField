"""Style-pack contract. Each engine turns a scene brief into a clip of an exact duration."""
from pathlib import Path

from .. import config, gemini


class Engine:
    name = "base"
    label = "Base"
    blurb = ""                 # what the director reads when deciding where to route a beat
    precise = False            # true = facts/geometry are exact (not generated pixels)
    params_schema: dict = {}   # JSON schema for plan() output
    plan_guide = ""            # extra instructions for the planner

    def size(self, project):
        return config.SIZES[project.aspect]

    def plan(self, scene, project) -> dict:
        if not self.params_schema:
            return {}
        prompt = (f"You are planning one scene of an explainer video using the '{self.label}' visual engine.\n"
                  f"Engine: {self.blurb}\n{self.plan_guide}\n\n"
                  f"Video topic: {project.topic}\nAudience: {project.audience}\nAspect: {project.aspect}\n"
                  f"Narration for this scene (on-screen language: {project.language}):\n\"{scene.narration}\"\n"
                  f"Visual brief: {scene.brief}\n\nReturn the engine parameters as JSON.")
        return gemini.json_call(prompt, schema=self.params_schema, model=config.MODEL_FAST)

    def render(self, scene, project, duration: float, out_dir: Path) -> Path:
        raise NotImplementedError

    def info(self):
        return {"name": self.name, "label": self.label, "blurb": self.blurb, "precise": self.precise}
