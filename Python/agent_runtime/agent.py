from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("AgentRuntime")


class Agent:
    # Fields that change every run — persisted to a git-ignored runtime.json so
    # state.json (config) stays stable and out of git's churn. self.state keeps
    # the merged view in memory, so every property/caller is unchanged.
    _RUNTIME_KEYS = frozenset({
        "last_tick_time", "last_spoke_time", "current_goal", "is_busy", "last_bound_time",
        "bound_unreal_actor_name", "bound_unreal_actor_label", "bound_unreal_actor_class",
        "daily_schedule", "last_activity",
    })

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
        # Merge in runtime fields (git-ignored), overriding any stale seed values
        # left in state.json. Legacy dirs with no runtime.json load unchanged.
        runtime_path = path / "runtime.json"
        if runtime_path.exists():
            try:
                state.update(json.loads(runtime_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                logger.warning(f"[{agent_id}] bad runtime.json — ignoring")
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
    def display_name(self) -> str:
        """The name other agents call this one — a clean semantic label, never the
        engine actor label/name. Decoupled so a placed actor can be tagged with
        engine plumbing (e.g. "APC_Maren_BP") while she stays "Maren" in the sim.
        Falls back to the actor-name hint for legacy agents that predate the field.
        """
        return self.state.get("display_name") or self.unreal_actor_name

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
    def role(self) -> str:
        """Agent role from state.json, default "npc". No role changes behavior
        today — the old dedicated-maintenance role was retired (#11.1): the
        cell sweep is a capability any APC invokes when it needs one.
        """
        return self.state.get("role", "npc")

    @property
    def survey_priority(self) -> bool:
        """Whether unexplored-cell surveys outrank this APC's schedule.

        The flag is explicit configuration rather than inferred from prose, so
        the deterministic movement controller and the LLM cannot disagree
        about whether a travel/act tick should stop at the cell center first.
        """
        return bool(self.state.get("survey_priority", False))

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
    def daily_schedule(self) -> dict:
        """Today's plan scratch: ``{"day": "Day 1", "blocks": [<schedule block>, ...]}``.

        The sequencer spine (``planner.py``); empty until a plan is generated for
        the current sim-day. Runtime scratch — regenerated each day / on reset.
        """
        return self.state.get("daily_schedule") or {}

    @property
    def daily_schedule_blocks(self) -> list:
        return self.daily_schedule.get("blocks", [])

    @property
    def daily_schedule_day(self) -> str:
        return self.daily_schedule.get("day", "")

    @property
    def last_activity(self) -> str:
        """The scheduled activity from the previous tick, for block-transition
        detection in ``planner.step`` (empty on a fresh run)."""
        return self.state.get("last_activity", "")

    @property
    def tick_interval(self) -> int:
        # 0 = no per-agent throttle; pacing comes from the adaptive sim loop.
        return int(self.state.get("tick_interval_seconds", 0))

    @property
    def speech_cooldown(self) -> int:
        return int(self.state.get("speech_cooldown_seconds", 30))

    @property
    def start_location(self):
        return self.state.get("start_location")

    @property
    def start_rotation(self):
        return self.state.get("start_rotation")

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

    def set_daily_schedule(self, blocks: list, day: str, agents_dir: Path) -> None:
        """Persist today's generated schedule to scratch (runtime.json)."""
        self.state["daily_schedule"] = {"day": day, "blocks": blocks}
        self._save_state(agents_dir)

    def set_last_activity(self, activity: str, agents_dir: Path) -> None:
        """Record the activity acted on this tick (for next tick's transition check)."""
        self.state["last_activity"] = activity
        self._save_state(agents_dir)

    def set_active(self, active: bool, agents_dir: Path) -> None:
        self.state["is_active"] = active
        self._save_state(agents_dir)

    def record_start_transform(self, location, rotation, agents_dir: Path) -> bool:
        """Capture the run-start transform once; reset_agents teleports back to it.

        Returns True if recorded, False if a start transform already exists
        (delete the keys from state.json to re-capture from a new placement).
        """
        if self.state.get("start_location"):
            return False
        self.state["start_location"] = location
        self.state["start_rotation"] = rotation
        self._save_state(agents_dir)
        return True

    def update_start_transform(self, location, rotation, agents_dir: Path) -> None:
        """Explicitly replace the reset/start point from a deliberate UI action."""
        self.state["start_location"] = location
        self.state["start_rotation"] = rotation
        self._save_state(agents_dir)

    def reset_runtime_state(self, agents_dir: Path) -> None:
        """Clear per-run timers, goal, and the day's plan so a fresh run behaves
        like the first one (the schedule regenerates for the new run/day)."""
        for key in ("last_tick_time", "last_spoke_time", "current_goal",
                    "daily_schedule", "last_activity"):
            self.state.pop(key, None)
        self.state["is_busy"] = False
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
        """Persist config to state.json (stable, tracked) and runtime fields to
        runtime.json (churning, git-ignored), split by ``_RUNTIME_KEYS``."""
        d = agents_dir / self.agent_id
        d.mkdir(parents=True, exist_ok=True)
        config = {k: v for k, v in self.state.items() if k not in self._RUNTIME_KEYS}
        runtime = {k: v for k, v in self.state.items() if k in self._RUNTIME_KEYS}
        (d / "state.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        (d / "runtime.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
