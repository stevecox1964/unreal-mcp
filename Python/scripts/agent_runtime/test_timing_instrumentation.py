"""Offline contracts for movement-startup and tick-phase timing (#20)."""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager  # noqa: E402
from agent_runtime.memory_store import MemoryStore  # noqa: E402
from agent_runtime import run_replay  # noqa: E402


def check(label, condition):
    if not condition:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "World"
        agents = world / "agents"
        (agents / "dufus").mkdir(parents=True)
        memory = MemoryStore(Path(tmp))
        memory.update_agents_dir(agents)
        timing = {
            "observe_ms": 12.5, "llm_ms": 84.0, "act_ms": 3.25,
            "wake_to_walk_accepted_ms": 150.0,
            "wake_to_first_displacement_ms": 425.0,
        }
        memory.record("dufus", {"_thought": "go"}, {"type": "walk_to"},
                      {"status": "accepted"}, timing=timing)
        entry = json.loads(memory.decisions_log.read_text(encoding="utf-8"))
        check("decision log preserves per-phase and movement-startup timing",
              entry["timing"] == timing)

        # Replay projection itself is pinned directly; frame parsing is covered
        # in test_run_replay and should not obscure this schema assertion.
        projected = run_replay._nearest_decision(
            time_from_iso(entry["timestamp"]),
            [(time_from_iso(entry["timestamp"]), entry)], 1.0)
        check("replay exposes timing beside the joined decision",
              projected["timing"] == timing)

        mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                           unreal_bridge=None, memory_store=memory)
        mgr._begin_movement_timing("dufus", {"x": 0.0, "y": 0.0, "z": 90.0})
        mgr._mark_first_walk_accepted(
            "dufus", {"type": "walk_to", "target_location": "square"},
            {"status": "accepted"})
        mgr._mark_first_displacement("dufus", {"x": 25.0, "y": 0.0, "z": 90.0})
        startup = mgr._movement_timing_snapshot("dufus")
        check("startup milestones are monotonic and non-negative",
              startup["wake_to_first_displacement_ms"]
              >= startup["wake_to_walk_accepted_ms"] >= 0.0)

    print("\nAll timing-instrumentation checks passed.")


def time_from_iso(value: str):
    from datetime import datetime
    return datetime.fromisoformat(value)


if __name__ == "__main__":
    main()
