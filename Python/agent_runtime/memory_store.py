"""Decision/memory persistence for the sim's agents.

TEST-FLAG (#42): ``classify_action_error`` must return None for successful and
accepted results, map each known failure shape to its category (not_connected,
timeout, target_unresolved, transport, runtime), bound the message length, and
redact key-like substrings; ``MemoryStore.record`` must attach ``error`` with
the elapsed act phase only for failed actions and leave successful entries
compact. Edge cases: a result carrying both ``success: False`` and no message,
a non-string error value, and a missing ``timing`` dict. Suggested level:
offline unit coverage in ``scripts/agent_runtime``; a real bridge failure still
needs live/PIE verification.

TEST-FLAG (#55): ``movement_trace`` must report where the APC stood, the cell
and footing it stood on, and — for a move — the target, its compass heading and
the intent that produced it; ``MemoryStore.record`` must add ``moved_cm`` from
the previous entry's position for the same agent and omit movement fields for
non-movement actions. Edge cases: a missing/zero-displacement location, an
observation with no grid or vision, and the first entry of a run (no previous
position). Offline unit coverage in ``scripts/agent_runtime``.
"""
from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("AgentRuntime")

# One decision event must stay small enough to scroll in the cockpit feed, and
# provider/bridge text is untrusted length — hence a hard cap, not a hint.
_MAX_ERROR_CHARS = 240

# Anything key-shaped never reaches the log; the feed is copied into issues.
_SECRET_PATTERNS = [
    re.compile(r"\b(sk-|xoxb-|ghp_)[A-Za-z0-9_\-]{8,}", re.IGNORECASE),
    re.compile(r"\b([A-Za-z0-9_]*(?:api[_-]?key|token|secret|password)[A-Za-z0-9_]*)"
               r"\s*[=:]\s*\S+", re.IGNORECASE),
]

# Ordered because a message may match several; the first is the most actionable.
_ERROR_CATEGORIES = [
    ("not_connected", re.compile(r"not connected|no connection|connection refused"
                                 r"|unreal (is )?offline", re.IGNORECASE)),
    ("timeout", re.compile(r"timed? ?out|timeout|deadline exceeded", re.IGNORECASE)),
    ("target_unresolved", re.compile(r"not found|no such actor|unknown actor|could not"
                                     r" resolve|unresolved|does not exist", re.IGNORECASE)),
    ("transport", re.compile(r"socket|broken pipe|reset by peer|eof|disconnect"
                             r"|decode|json", re.IGNORECASE)),
]


def _redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) if m.re.groups and m.lastindex else "")
                           + "[redacted]", text)
    return text


def classify_action_error(result: dict, elapsed_ms: float = None) -> dict | None:
    """Summarise a failed world action as a bounded, safe diagnostic (#42).

    SR28 lost the cause of a 15-second ``speak_to`` failure because only the
    status survived. Returns None when the action did not fail, else
    ``{"code": <category>, "message": <redacted, truncated>, "elapsed_ms": ...}``.

    Example::

        classify_action_error({"success": False, "error": "Unreal not connected"}, 15000)
        # -> {"code": "not_connected", "message": "Unreal not connected",
        #     "elapsed_ms": 15000}
    """
    if not isinstance(result, dict):
        return None
    failed = (result.get("status") == "error"
              or result.get("success") is False
              or bool(result.get("error")))
    if not failed:
        return None

    raw = result.get("error") or result.get("message") or result.get("note") or ""
    message = _redact(" ".join(str(raw).split()))[:_MAX_ERROR_CHARS]

    code = "runtime"
    for name, pattern in _ERROR_CATEGORIES:
        if pattern.search(message):
            code = name
            break

    diagnostic = {"code": code, "message": message or "(no detail reported)"}
    if elapsed_ms is not None:
        diagnostic["elapsed_ms"] = round(float(elapsed_ms), 3)
    return diagnostic


# Compass sectors for a world-space vector. UE yaw: E=0, S=90, W=180, N=270,
# so +x is east and +y is south — the same convention the survey headings use.
_COMPASS = ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]

# Below this the avatar has not meaningfully moved; a heading would be noise.
_MIN_HEADING_CM = 1.0

# Action types whose whole point is displacement — only these log a target.
_MOVEMENT_ACTIONS = {"walk_to", "wander", "follow_character"}


def _xy(loc) -> tuple[float, float] | None:
    """Coerce a location payload ({x,y,...} dict or [x,y,...] list) to (x, y)."""
    if isinstance(loc, dict) and loc.get("x") is not None:
        return float(loc["x"]), float(loc["y"])
    if isinstance(loc, (list, tuple)) and len(loc) >= 2:
        return float(loc[0]), float(loc[1])
    return None


def _compass_of(dx: float, dy: float) -> str | None:
    """Compass label of a world-space vector; None when there is no vector."""
    if math.hypot(dx, dy) < _MIN_HEADING_CM:
        return None
    sector = int(((math.degrees(math.atan2(dy, dx)) % 360.0) + 22.5) // 45) % 8
    return _COMPASS[sector]


def _move_intent(action: dict) -> str | None:
    """Name the form of the movement request the LLM (or a routine) produced.

    The forms are not interchangeable: a ``direction`` is relative to the
    avatar's current facing, while a place/actor/cell/location is absolute.
    SR33's log could not tell them apart, which is why a walk deeper into a
    corn field and a walk back out both read as ``walk_to success``.
    """
    if action.get("direction"):
        return f"direction:{action['direction']}"
    target = action.get("target_location")
    if isinstance(target, str) and target.strip():
        return f"place:{target.strip()}"
    if action.get("target_actor"):
        return f"actor:{action['target_actor']}"
    if action.get("target_cell") is not None:
        return f"cell:{action['target_cell']}"
    if action.get("_sweep"):
        return f"survey:{action['_sweep']}"
    if _xy(action.get("location")) is not None or _xy(target) is not None:
        return "location"
    return None


def movement_trace(observation: dict, action: dict,
                   previous_xy: tuple[float, float] | None = None) -> dict:
    """Describe where an action happened and where it aimed (#55).

    SR33 logged "turning back the way I came" twice with no position, target or
    heading, so a 15 m walk *into* a corn field and the walk back out were
    indistinguishable — both read ``walk_to success``. Returns the fields that
    make a movement auditable::

        {"at": [x, y], "cell": "5,6", "footing": "cultivated_field",
         "facing_yaw": 180.0, "moved_cm": 1465.8,
         "move": {"intent": "direction:back", "target": [x, y], "heading": "N"}}

    Every field is omitted when the underlying fact is absent — an observation
    with no vision has no ``footing``, an idle action has no ``move``.
    """
    trace: dict = {}
    here = _xy(observation.get("location"))
    if here is not None:
        trace["at"] = [round(here[0], 1), round(here[1], 1)]
    if previous_xy is not None and here is not None:
        trace["moved_cm"] = round(math.hypot(here[0] - previous_xy[0],
                                             here[1] - previous_xy[1]), 1)

    grid = observation.get("grid") or {}
    if grid.get("col") is not None and grid.get("row") is not None:
        trace["cell"] = f"{grid['col']},{grid['row']}"
    footing = (observation.get("seen") or {}).get("footing")
    if footing:
        trace["footing"] = str(footing)
    rotation = observation.get("rotation")
    if isinstance(rotation, dict) and rotation.get("y") is not None:
        trace["facing_yaw"] = round(float(rotation["y"]), 1)
    elif isinstance(rotation, (list, tuple)) and len(rotation) >= 2:
        trace["facing_yaw"] = round(float(rotation[1]), 1)

    if action.get("type") not in _MOVEMENT_ACTIONS and not action.get("_sweep"):
        return trace

    move: dict = {}
    intent = _move_intent(action)
    if intent:
        move["intent"] = intent
    # A direction walk carries no coordinates until execution resolves it, so
    # the executor stashes what it actually aimed at — without it the heading a
    # direction word produced is exactly the thing the log cannot show. The
    # executor works on a COPY of the action, so the stash rides on the
    # observation; the action is still checked first for callers that pass a
    # fully resolved action straight in.
    target = (_xy(action.get("_resolved_target"))
              or _xy(observation.get("_resolved_target"))
              or _xy(action.get("location"))
              or _xy(action.get("target_location")))
    if target is not None:
        move["target"] = [round(target[0], 1), round(target[1], 1)]
        if here is not None:
            heading = _compass_of(target[0] - here[0], target[1] - here[1])
            if heading:
                move["heading"] = heading
            move["distance_cm"] = round(math.hypot(target[0] - here[0],
                                                   target[1] - here[1]), 1)
    if move:
        trace["move"] = move
    return trace


def movement_summary(trace: dict, action_type: str, status: str = "") -> str:
    """One line of movement for a human watching it happen — the PIE overlay.

    The decision log records where the APC stood, what it aimed at and what it
    was standing on, but none of that reached the viewport, so watching a run
    still meant reading the log afterwards. ASCII only: this is drawn by the
    engine's debug text, not a browser. Example::

        walk_to north 15m ->N [success] | cell 4,6 | cultivated_field
    """
    move = trace.get("move") or {}
    parts = [str(action_type or "?")]
    intent = str(move.get("intent") or "")
    if intent:
        # "direction:north" reads as "north"; "place:village square" keeps its
        # kind, because "walk_to village square" and "walk_to north" are
        # different sorts of request and the difference is the point.
        parts.append(intent.split(":", 1)[1] if intent.startswith("direction:") else intent)
    if move.get("distance_cm") is not None:
        parts.append(f"{round(move['distance_cm'] / 100)}m")
    if move.get("heading"):
        parts.append(f"->{move['heading']}")
    if status:
        parts.append(f"[{status}]")

    tail = []
    if trace.get("cell"):
        tail.append(f"cell {trace['cell']}")
    if trace.get("footing"):
        tail.append(str(trace["footing"]))
    if trace.get("moved_cm") is not None:
        tail.append(f"moved {round(trace['moved_cm'] / 100)}m")
    return " ".join(parts) + (" | " + " | ".join(tail) if tail else "")


class MemoryStore:
    def __init__(self, worlds_dir: Path):
        self.worlds_dir = worlds_dir
        self.agents_dir: Path | None = None
        self.decisions_log: Path | None = None
        self.events_log: Path | None = None
        # Current sim run tag (SR<n>), set by AgentManager at run start so each
        # decision-log entry is attributable to a single run.
        self.sim_run_id: str = "SR0"
        # Last logged position per agent — the only way a decision row can say
        # how far the *previous* decision actually moved the avatar (#55).
        self._last_xy: dict[str, tuple[float, float]] = {}

    def update_agents_dir(self, agents_dir: Path) -> None:
        self.agents_dir = agents_dir
        log_dir = agents_dir.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_log = log_dir / "agent_decisions.log"
        self.events_log = log_dir / "world_events.log"

    # ── Read ──────────────────────────────────────────────────────────────────

    def load_memories(self, agent_id: str) -> list[dict]:
        if not self.agents_dir:
            return []
        p = self.agents_dir / agent_id / "memory.json"
        if not p.exists():
            return []
        raw = json.loads(p.read_text(encoding="utf-8")).get("memories", [])
        # Normalise string seeds → dict so callers can always call .get()
        return [
            m if isinstance(m, dict) else {"timestamp": "1970-01-01T00:00:00+00:00", "importance": 0.5, "text": str(m)}
            for m in raw
        ]

    def get_relevant_memories(self, agent_id: str) -> list[dict]:
        memories = self.load_memories(agent_id)
        high_importance = [m for m in memories if m.get("importance", 0) >= 0.7]
        recent = memories[-5:]
        # Merge, deduplicate by timestamp, sort
        combined = {m["timestamp"]: m for m in high_importance + recent}
        return sorted(combined.values(), key=lambda m: m["timestamp"])

    def get_recent_events(self, limit: int = 20, sim_run_id: str = None) -> list[dict]:
        """Return recent decisions, optionally restricted to one simulation run."""
        if limit <= 0:
            return []
        if not self.decisions_log or not self.decisions_log.exists():
            return []
        lines = self.decisions_log.read_text(encoding="utf-8").strip().splitlines()
        entries = []
        for line in lines:
            try:
                entry = json.loads(line)
                if sim_run_id is None or entry.get("sim_run") == sim_run_id:
                    entries.append(entry)
            except json.JSONDecodeError:
                pass
        return entries[-limit:]

    def clear_recent_events(self) -> int:
        """Empty the decision log (the Sim-page "feed"). Returns lines cleared.

        Truncates ``agent_decisions.log`` rather than deleting it so the path
        stays valid for the next tick. Agent memories (memory.json) are untouched
        — this only clears the debug decision feed.
        """
        if not self.decisions_log or not self.decisions_log.exists():
            return 0
        cleared = len(self.decisions_log.read_text(encoding="utf-8").strip().splitlines())
        self.decisions_log.write_text("", encoding="utf-8")
        return cleared

    # ── Write ─────────────────────────────────────────────────────────────────

    _MAX_MEMORIES = 30

    def reset_memories(self, agent_id: str) -> str:
        """Restore memory.json from memory.seed.json if present, else clear it.

        memory.seed.json holds an agent's hand-authored starting memories so a
        reset doesn't wipe them along with the run-accumulated ones.
        Returns "seeded" or "cleared".
        """
        p = self.agents_dir / agent_id / "memory.json"
        seed = self.agents_dir / agent_id / "memory.seed.json"
        if seed.exists():
            p.write_text(seed.read_text(encoding="utf-8"), encoding="utf-8")
            return "seeded"
        p.write_text(
            json.dumps({"agent_id": agent_id, "memories": []}, indent=2),
            encoding="utf-8",
        )
        return "cleared"

    def record(
        self,
        agent_id: str,
        observation: dict,
        action: dict,
        result: dict,
        memory_update: str | None = None,
        importance: float = 0.5,
        timing: dict | None = None,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = {
            "timestamp": timestamp,
            "sim_run": self.sim_run_id,
            "agent_id": agent_id,
            "action_type": action.get("type"),
            "thought": observation.get("_thought"),
            "result_status": result.get("status") or result.get("success"),
        }
        entry.update(movement_trace(observation, action, self._last_xy.get(agent_id)))
        # "accepted" is the bridge taking the command, not the body moving. A
        # stalled order kept reading as `success` with `moved_cm: 0.0` beside it
        # and nothing tying the two together (#59) — so the verdict is stated.
        last_move = observation.get("last_move")
        if isinstance(last_move, dict) and last_move.get("stalled"):
            entry["stalled_order"] = {"intent": last_move.get("intent"),
                                      "moved_cm": last_move.get("moved_cm")}
        here = _xy(observation.get("location"))
        if here is not None:
            self._last_xy[agent_id] = here

        if timing:
            entry["timing"] = timing
        # A failed action keeps enough detail to tell timeout from transport from
        # target resolution (#42); successful entries stay exactly as compact.
        diagnostic = classify_action_error(result, (timing or {}).get("act_ms"))
        if diagnostic:
            entry["error"] = diagnostic
        with open(self.decisions_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Don't persist memories for idle actions — they're never meaningful.
        # Also skip low-importance updates to avoid log spam.
        action_type = action.get("type", "idle")
        if memory_update and action_type != "idle":
            # Normalize: LLM sometimes returns {"text": "..."} instead of a plain string.
            if isinstance(memory_update, dict):
                memory_update = memory_update.get("text", str(memory_update))

            p = self.agents_dir / agent_id / "memory.json"
            data = (
                json.loads(p.read_text(encoding="utf-8"))
                if p.exists()
                else {"agent_id": agent_id, "memories": []}
            )
            data["memories"].append(
                {"timestamp": timestamp, "importance": importance, "text": memory_update}
            )
            # Trim to keep the most recent N entries.
            if len(data["memories"]) > self._MAX_MEMORIES:
                data["memories"] = data["memories"][-self._MAX_MEMORIES:]
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")

        logger.info(
            f"[{agent_id}] action={action.get('type')} "
            f"result={result.get('status', result.get('success', '?'))}"
            + (f" error={diagnostic['code']}: {diagnostic['message']}" if diagnostic else "")
        )

    def record_interrupt_event(self, agent_id: str, event: str, interrupt: dict) -> None:
        """Append one attributed interruption lifecycle event to the decision feed."""
        if not self.decisions_log:
            return
        snapshot = {
            key: interrupt.get(key)
            for key in ("interrupt_id", "kind", "source", "reason", "priority", "status",
                        "preemptible", "requested_at", "outcome")
            if key in interrupt
        }
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sim_run": self.sim_run_id,
            "agent_id": agent_id,
            "event": f"interrupt_{event}",
            "interrupt": snapshot,
        }
        with open(self.decisions_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def record_survey_event(self, agent_id: str, progress: dict) -> None:
        """Append one deterministic survey-heading result to the decision feed."""
        if not self.decisions_log:
            return
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sim_run": self.sim_run_id,
            "agent_id": agent_id,
            "event": "survey_heading",
            "survey_progress": dict(progress),
        }
        with open(self.decisions_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
