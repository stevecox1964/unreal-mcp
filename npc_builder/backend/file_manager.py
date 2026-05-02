from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import List

# npc_builder/backend/ -> npc_builder/ -> project root -> Python/agents/
AGENTS_DIR = Path(__file__).parent.parent.parent / "Python" / "agents"

DEFAULT_TOOLS = {
    "allowed_actions": [
        "idle",
        "walk_to",
        "speak_to",
        "inspect_object",
        "follow_character",
        "attack",
        "flee",
        "ask_for_screenshot",
        "remember",
    ]
}


def _agent_path(agent_id: str) -> Path:
    return AGENTS_DIR / agent_id


def list_agents() -> List[str]:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(d.name for d in AGENTS_DIR.iterdir() if d.is_dir())


def create_agent(agent_id: str) -> None:
    path = _agent_path(agent_id)
    path.mkdir(parents=True, exist_ok=True)

    (path / "character.md").write_text(
        f"# Agent: {agent_id}\n\n## Role\n\n## Personality\n\n## Speaking Style\n\n## Backstory\n",
        encoding="utf-8",
    )
    (path / "goals.md").write_text(
        "# Goals\n\n## Long-Term Goals\n\n## Current Goal\n\n",
        encoding="utf-8",
    )
    (path / "rules.md").write_text(
        "# Rules\n\n- Do not invent tools or actions.\n- Return structured JSON decisions only.\n",
        encoding="utf-8",
    )

    tools = dict(DEFAULT_TOOLS)
    (path / "tools.json").write_text(json.dumps(tools, indent=2), encoding="utf-8")

    state = {
        "agent_id": agent_id,
        "is_active": True,
        "is_busy": False,
        "current_goal": "",
        "tick_interval_seconds": 10,
        "speech_cooldown_seconds": 30,
        "last_tick_time": None,
        "last_spoke_time": None,
    }
    (path / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    memory = {"agent_id": agent_id, "memories": []}
    (path / "memory.json").write_text(json.dumps(memory, indent=2), encoding="utf-8")


def delete_agent(agent_id: str) -> None:
    path = _agent_path(agent_id)
    if path.exists():
        shutil.rmtree(path)


def read_text(agent_id: str, filename: str) -> str:
    p = _agent_path(agent_id) / filename
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_text(agent_id: str, filename: str, content: str) -> None:
    _agent_path(agent_id).mkdir(parents=True, exist_ok=True)
    (_agent_path(agent_id) / filename).write_text(content, encoding="utf-8")


def read_json(agent_id: str, filename: str) -> dict:
    p = _agent_path(agent_id) / filename
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def write_json(agent_id: str, filename: str, data: dict) -> None:
    _agent_path(agent_id).mkdir(parents=True, exist_ok=True)
    (_agent_path(agent_id) / filename).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
