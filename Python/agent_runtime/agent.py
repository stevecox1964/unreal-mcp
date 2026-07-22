from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import agenda
from . import interruptions

logger = logging.getLogger("AgentRuntime")


class Agent:
    # Fields that change every run — persisted to a git-ignored runtime.json so
    # state.json (config) stays stable and out of git's churn. self.state keeps
    # the merged view in memory, so every property/caller is unchanged.
    _RUNTIME_KEYS = frozenset({
        "last_tick_time", "last_spoke_time", "current_goal", "is_busy", "last_bound_time",
        "bound_unreal_actor_name", "bound_unreal_actor_label", "bound_unreal_actor_class",
        "daily_schedule", "last_activity", "active_interrupt", "interrupt_queue", "last_interrupt",
        "agenda_execution",
    })

    def __init__(
        self,
        agent_id: str,
        state: dict,
        character_text: str,
        goals_text: str,
        rules_text: str,
        allowed_actions: list[str],
        authored_agenda: dict | None = None,
        agenda_errors: list[str] | None = None,
    ):
        self.agent_id = agent_id
        self.state = state
        self.character_text = character_text
        self.goals_text = goals_text
        self.rules_text = rules_text
        self.allowed_actions = allowed_actions
        self.authored_agenda = authored_agenda
        self.agenda_errors = list(agenda_errors or [])

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
        authored_agenda = None
        agenda_errors = []
        agenda_path = path / "agenda.json"
        if agenda_path.exists():
            try:
                authored_agenda = agenda.validate_document(
                    json.loads(agenda_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                agenda_errors = [f"invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"]
            except agenda.AgendaValidationError as exc:
                agenda_errors = exc.errors
            if agenda_errors:
                logger.error("[%s] agenda.json rejected: %s", agent_id, "; ".join(agenda_errors))
        return cls(
            agent_id=agent_id,
            state=state,
            character_text=character,
            goals_text=goals,
            rules_text=rules,
            allowed_actions=tools.get("allowed_actions", []),
            authored_agenda=authored_agenda,
            agenda_errors=agenda_errors,
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
    def active_interrupt(self) -> dict | None:
        """The one valid active interruption, or ``None`` for absent/bad state."""
        return interruptions.sanitize_state(
            self.state.get("active_interrupt"), self.state.get("interrupt_queue"),
            self.state.get("last_interrupt"),
        )["active"]

    @property
    def interrupt_queue(self) -> list[dict]:
        """Valid queued interruptions in priority/FIFO order."""
        return interruptions.sanitize_state(
            self.state.get("active_interrupt"), self.state.get("interrupt_queue"),
            self.state.get("last_interrupt"),
        )["queue"]

    @property
    def last_interrupt(self) -> dict | None:
        """Most recent valid terminal interruption, if one was persisted."""
        return interruptions.sanitize_state(
            self.state.get("active_interrupt"), self.state.get("interrupt_queue"),
            self.state.get("last_interrupt"),
        )["last_interrupt"]

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
    def agenda_execution(self) -> dict:
        """Deterministic per-day task state and ledger from the authored agenda."""
        value = self.state.get("agenda_execution")
        return value if isinstance(value, dict) else {}

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

    def offer_interrupt(self, record: dict, agents_dir: Path,
                        activated_at: str = "") -> dict:
        """Offer a valid queued interruption and persist its lifecycle result."""
        result = interruptions.offer(
            self.active_interrupt, self.interrupt_queue, record, activated_at,
            self.last_interrupt,
        )
        self._set_interruptions(result, agents_dir)
        return result

    def defer_interrupt(self, agents_dir: Path, deferred_at: str = "") -> dict:
        """Defer the active interruption and persist the promoted queue state."""
        result = interruptions.defer(
            self.active_interrupt, self.interrupt_queue, deferred_at, self.last_interrupt,
        )
        self._set_interruptions(result, agents_dir)
        return result

    def terminate_interrupt(self, status: str, outcome: str, agents_dir: Path,
                            resolved_at: str = "") -> dict:
        """Terminally finish the active interruption and persist queue promotion."""
        result = interruptions.terminate(
            self.active_interrupt, self.interrupt_queue, status, outcome, resolved_at,
            self.last_interrupt,
        )
        self._set_interruptions(result, agents_dir)
        return result

    def activate_next_interrupt(self, agents_dir: Path, activated_at: str = "") -> dict:
        """Promote queued work when no active interruption currently owns attention."""
        result = interruptions.activate_next(
            self.active_interrupt, self.interrupt_queue, activated_at, self.last_interrupt,
        )
        self._set_interruptions(result, agents_dir)
        return result

    def set_active_interrupt_preemptible(self, preemptible: bool, agents_dir: Path) -> bool:
        """Persist whether the active interruption can be safely displaced."""
        active = self.active_interrupt
        if active is None:
            return False
        active["preemptible"] = bool(preemptible)
        self.state["active_interrupt"] = active
        self._save_state(agents_dir)
        return True

    def replace_active_interrupt(self, record: dict, agents_dir: Path) -> bool:
        """Persist a validated update to the currently active interruption.

        Chat owns mutable transcript/mode data inside its interruption payload.
        Restrict replacement to the same active id so a stale request cannot
        overwrite a newly promoted or preempting interruption.
        """
        current = self.active_interrupt
        updated = interruptions.validate_record(record)
        if (current is None or updated is None or updated.get("status") != "active"
                or updated.get("interrupt_id") != current.get("interrupt_id")):
            return False
        self.state["active_interrupt"] = updated
        self._save_state(agents_dir)
        return True

    def cancel_interrupts(self, kind: str, outcome: str, agents_dir: Path,
                          resolved_at: str = "") -> dict:
        """Cancel persisted interruptions of one semantic kind."""
        result = interruptions.cancel_kind(
            self.active_interrupt, self.interrupt_queue, kind, outcome, resolved_at,
            self.last_interrupt,
        )
        self._set_interruptions(result, agents_dir)
        return result

    def set_daily_schedule(self, blocks: list, day: str, agents_dir: Path) -> None:
        """Persist today's generated schedule to scratch (runtime.json)."""
        self.state["daily_schedule"] = {"day": day, "blocks": blocks}
        self._save_state(agents_dir)

    def set_last_activity(self, activity: str, agents_dir: Path) -> None:
        """Record the activity acted on this tick (for next tick's transition check)."""
        self.state["last_activity"] = activity
        self._save_state(agents_dir)

    def set_agenda_execution(self, execution: dict, agents_dir: Path) -> None:
        """Persist runtime agenda state separately from authored ``agenda.json``."""
        if execution != self.state.get("agenda_execution"):
            self.state["agenda_execution"] = execution
            self._save_state(agents_dir)

    def replace_authored_agenda(self, raw: dict, agents_dir: Path) -> dict:
        """Atomically validate/save ``agenda.json`` and invalidate stale execution."""
        path = agents_dir / self.agent_id / "agenda.json"
        document = agenda.write_document(path, raw)
        self.authored_agenda = document
        self.agenda_errors = []
        self.state.pop("agenda_execution", None)
        self._save_state(agents_dir)
        return document

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
                    "daily_schedule", "last_activity", "active_interrupt",
                    "interrupt_queue", "last_interrupt", "agenda_execution"):
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

    def _set_interruptions(self, lifecycle: dict, agents_dir: Path) -> None:
        """Replace persisted interruption fields with one lifecycle transition."""
        active = lifecycle.get("active")
        queue = lifecycle.get("queue") or []
        last = lifecycle.get("last_interrupt")
        if active is None:
            self.state.pop("active_interrupt", None)
        else:
            self.state["active_interrupt"] = active
        if queue:
            self.state["interrupt_queue"] = queue
        else:
            self.state.pop("interrupt_queue", None)
        if last is None:
            self.state.pop("last_interrupt", None)
        else:
            self.state["last_interrupt"] = last
        self._save_state(agents_dir)
