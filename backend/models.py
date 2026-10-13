"""Project / scene data model (stored as JSON on disk)."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
import uuid


def new_id():
    return uuid.uuid4().hex[:10]


SceneStatus = Literal["draft", "queued", "rendering", "ready", "error"]


class Scene(BaseModel):
    id: str = Field(default_factory=new_id)
    narration: str
    engine: str = "title"
    brief: str = ""
    params: dict[str, Any] = {}
    status: SceneStatus = "draft"
    duration: Optional[float] = None
    audio: Optional[str] = None
    clip: Optional[str] = None
    thumb: Optional[str] = None
    error: Optional[str] = None
    narration_hash: Optional[str] = None   # audio is reused while narration+voice are unchanged
    render_hash: Optional[str] = None      # clip is reused while engine+params+duration are unchanged


class Source(BaseModel):
    id: str = Field(default_factory=new_id)
    kind: Literal["note", "file", "link"] = "note"
    name: str = ""
    text: str = ""
    path: Optional[str] = None


class Project(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str = "Untitled"
    topic: str = ""
    audience: str = "curious general audience"
    language: str = "English"
    aspect: Literal["16:9", "9:16"] = "16:9"
    length: Literal["short", "medium", "long"] = "medium"
    voice: str = "Johnny"
    music: bool = True
    pace: float = 1.0   # extra tempo on top of each voice's own pacing
    sources: list[Source] = []
    scenes: list[Scene] = []
    render_status: str = "idle"
    render_path: Optional[str] = None
    render_error: Optional[str] = None
    created: float = 0
    updated: float = 0
