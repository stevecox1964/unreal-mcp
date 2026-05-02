from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class TextContent(BaseModel):
    content: str


class ToolsContent(BaseModel):
    allowed_actions: List[str]


class StateContent(BaseModel):
    agent_id: str
    is_active: bool = True
    is_busy: bool = False
    current_goal: str = ""
    tick_interval_seconds: int = 10
    speech_cooldown_seconds: int = 30
    last_tick_time: Optional[str] = None
    last_spoke_time: Optional[str] = None


class MemoryEntry(BaseModel):
    timestamp: str
    importance: float
    text: str


class MemoryContent(BaseModel):
    agent_id: str
    memories: List[MemoryEntry] = []
