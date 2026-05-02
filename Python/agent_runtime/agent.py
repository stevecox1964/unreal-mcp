from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("AgentRuntime")


class Agent:
    def __init__(
        self,
        agent_id: str,
        state: dict,
        character_text: str,
        goals_text: str,
        rules_text: str,
        allowed_actions: list[str],
    ):
        self.agent_id = agent_id
        self.state = state
        self.character_text = character_text
        self.goals_text = goals_text
        self.rules_text = rules_text
        self.allowed_actions = allowed_actions

    # Factory

    @classmethod
    def load(cls, agents_dir: Path, agent_id: str) -> "Agent":
        path = agents_dir / agent_id
        state = json.loads((path / "state.json").read_text(encoding="utf-8"))
        character = (path / "character.md").read_text(encoding="utf-8")
        goals = (path / "goals.md").read_text(encoding="utf-8")
        rules = (path / "rules.md").read_text(encoding="utf-8")
        tools = json.loads((path / "tools.json").read_text(encoding="utf-8"))
        return cls(
            agent_id=agent_id,
            state=state,
            character_text=character,
            goals_text=goals,
            rules_text=rules,
            allowed_actions=tools.get("allowed_actions", []),
        )

    # Properties

    @property
    def unreal_actor_name(self) -> str:
        return self.state.get("unreal_actor_name", self.agent_id)

    @property
    def bound_unreal_actor_name(self) -> str:
        return self.state.get("bound_unreal_actor_name", self.unreal_actor_name)

    @property
    def bound_unreal_actor_label(self) -> str:
        return self.state.get("bound_unreal_actor_label", "")

    @property
    def has_unreal_binding(self) -> bool:
        return bool(self.state.get("bound_unreal_actor_name"))

    @property
    def blueprint_class(self) -> str:
        return self.state.get("blueprint_class", "")

    @property
    def tier(self) -> int:
        return int(self.state.get("tier", 1))

    @property
    def is_active(self) -> bool:
        return bool(self.state.get("is_active", True))

    @property
    def is_busy(self) -> bool:
        return bool(self.state.get("is_busy", False))

    @property
    def current_goal(self) -> str:
        return self.state.get("current_goal", "idle")

    @property
    def tick_interval(self) -> int:
        return int(self.state.get("tick_interval_seconds", 10))

    @property
    def speech_cooldown(self) -> int:
        return int(self.state.get("speech_cooldown_seconds", 30))

    # Cooldown checks

    def cooldown_expired(self) -> bool:
        last = self.state.get("last_tick_time")
        if not last:
            return True
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
        return elapsed >= self.tick_interval

    def can_speak(self) -> bool:
        last = self.state.get("last_spoke_time")
        if not last:
            return True
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
        return elapsed >= self.speech_cooldown

    # State mutations (write-through to disk)

    def mark_ticked(self, agents_dir: Path) -> None:
        self.state["last_tick_time"] = datetime.now(timezone.utc).isoformat()
        self._save_state(agents_dir)

    def mark_spoke(self, agents_dir: Path) -> None:
        self.state["last_spoke_time"] = datetime.now(timezone.utc).isoformat()
        self._save_state(agents_dir)

    def set_busy(self, busy: bool, agents_dir: Path) -> None:
        self.state["is_busy"] = busy
        self._save_state(agents_dir)

    def set_goal(self, goal: str, agents_dir: Path) -> None:
        self.state["current_goal"] = goal
        self._save_state(agents_dir)

    def set_active(self, active: bool, agents_dir: Path) -> None:
        self.state["is_active"] = active
        self._save_state(agents_dir)

    def bind_unreal_actor(self, actor: dict[str, Any], agents_dir: Path) -> None:
        """Persist the resolved Unreal actor identity for runtime commands."""
        actor_name = actor.get("name")
        if actor_name:
            self.state["bound_unreal_actor_name"] = actor_name
        if actor.get("label"):
            self.state["bound_unreal_actor_label"] = actor["label"]
        if actor.get("class"):
            self.state["bound_unreal_actor_class"] = actor["class"]
        self.state["last_bound_time"] = datetime.now(timezone.utc).isoformat()
        self._save_state(agents_dir)

    def clear_unreal_binding(self, agents_dir: Path) -> None:
        for key in (
            "bound_unreal_actor_name",
            "bound_unreal_actor_label",
            "bound_unreal_actor_class",
            "last_bound_time",
        ):
            self.state.pop(key, None)
        self._save_state(agents_dir)

    def _save_state(self, agents_dir: Path) -> None:
        p = agents_dir / self.agent_id / "state.json"
        p.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
