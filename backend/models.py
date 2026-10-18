"""Project / scene data model (stored as JSON on disk)."""
from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


def new_id():
    return uuid.uuid4().hex[:10]


SceneStatus = Literal["draft", "queued", "rendering", "ready", "error"]


CastKind = Literal["character", "location", "object", "style"]


class CastItem(BaseModel):
    """A Flow-style ingredient: defined once, referenced by every beat it appears in."""
    id: str = Field(default_factory=new_id)
    kind: CastKind = "character"
    name: str
    description: str = ""
    image: str | None = None
    status: Literal["pending", "generating", "ready", "error"] = "pending"
    error: str | None = None


class VoiceProfile(BaseModel):
    """A narrator a person cloned from a short sample of their own voice. `id` is what Project.voice stores.
    The sample and the model's voice-clone prompt live in the media volume under voices/<id>/."""
    id: str = Field(default_factory=lambda: "v_" + new_id())
    name: str
    language: str = "English"
    reference_text: str = ""
    status: Literal["pending", "ready", "error"] = "pending"
    error: str | None = None
    builtin: bool = False                 # the channel's own voices, seeded rather than created in the app
    post_filter: str | None = None        # optional ffmpeg audio filter applied after synthesis
    created: float = 0.0


class Scene(BaseModel):
    id: str = Field(default_factory=new_id)
    narration: str
    engine: str = "title"
    brief: str = ""
    params: dict[str, Any] = {}
    cast: list[str] = []                   # CastItem ids that appear in this beat
    status: SceneStatus = "draft"
    duration: float | None = None
    audio: str | None = None
    clip: str | None = None
    thumb: str | None = None
    error: str | None = None
    narration_hash: str | None = None   # audio is reused while narration+voice are unchanged
    render_hash: str | None = None      # clip is reused while engine+params+duration are unchanged


class Source(BaseModel):
    id: str = Field(default_factory=new_id)
    kind: Literal["note", "file", "link"] = "note"
    name: str = ""
    text: str = ""
    path: str | None = None


class Project(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str = "Untitled"
    topic: str = ""
    audience: str = "curious general audience"
    instructions: str = ""   # optional free-text direction for the director ("only manim", "no AI video"...)
    language: str = "English"
    aspect: Literal["16:9", "9:16"] = "16:9"
    length: Literal["short", "medium", "long"] = "medium"
    voice: str = "Johnny"   # falls back to the deployment default when unavailable
    music: bool = True
    look: str = "cinematic"   # art direction preset, see backend/look.py
    quality: Literal["draft", "final"] = "final"   # draft = cheaper Veo model for iterating
    pace: float = 1.0   # extra tempo on top of each voice's own pacing
    sources: list[Source] = []
    cast: list[CastItem] = []
    scenes: list[Scene] = []
    render_status: str = "idle"
    render_path: str | None = None
    render_error: str | None = None
    qa: dict | None = None   # quality report of the last render, see backend/qa.py
    factcheck: dict | None = None   # claims checked against sources and Google Search, see backend/factcheck.py
    render_sig: str | None = None   # which clips and narration the current export was made from (pipeline.render_sig)
    mark_id: str | None = None   # provenance mark of the current export (see provenance.py); None when it is unmarked
    created: float = 0
    updated: float = 0
