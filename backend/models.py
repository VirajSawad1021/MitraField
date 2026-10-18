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
    created: float = 0
    updated: float = 0
