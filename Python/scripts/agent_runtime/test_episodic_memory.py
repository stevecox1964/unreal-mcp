"""Offline tests for the per-agent episodic record (backlog #5).

Structured "what happened" log: one event per acted tick, so long/overnight
runs keep a queryable history instead of only the 30-item memory.json window.
No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_episodic_memory.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager        # noqa: E402
from agent_runtime.episodic_memory import EpisodicLog       # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_append_and_recent():
    with tempfile.TemporaryDirectory() as tmp:
        log = EpisodicLog(Path(tmp) / "episodes.jsonl")
        log.record({"world_time": "T0", "grid_cell": "1,1", "place": "square",
                    "saw": ["Maren"], "action": "walk_to", "outcome": "accepted"})
        log.record({"world_time": "T1", "grid_cell": "1,2", "place": None,
                    "saw": [], "action": "observe", "outcome": "success"})

        recent = log.recent(5)
        check("both events stored", len(recent) == 2)
        check("recency order (newest last)", recent[-1]["world_time"] == "T1")
        check("event fields preserved", recent[0]["saw"] == ["Maren"])
        check("recent(1) returns only the latest", log.recent(1)[0]["world_time"] == "T1")


def test_query_filters():
    with tempfile.TemporaryDirectory() as tmp:
        log = EpisodicLog(Path(tmp) / "episodes.jsonl")
        log.record({"world_time": "T0", "grid_cell": "1,1", "place": "square", "saw": ["Maren"], "action": "a"})
        log.record({"world_time": "T1", "grid_cell": "2,2", "place": "market", "saw": [], "action": "b"})
        log.record({"world_time": "T2", "grid_cell": "1,1", "place": "square", "saw": ["Bob"], "action": "c"})

        check("filter by place", [e["world_time"] for e in log.query(place="square")] == ["T0", "T2"])
        check("filter by character seen", [e["world_time"] for e in log.query(character="Maren")] == ["T0"])
        check("character match is case-insensitive", len(log.query(character="bob")) == 1)
        check("no filter returns all", len(log.query()) == 3)


def test_persistence_is_append_only():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "episodes.jsonl"
        EpisodicLog(path).record({"world_time": "T0", "action": "a"})
        # A fresh handle (simulating a restart) appends without losing history.
        EpisodicLog(path).record({"world_time": "T1", "action": "b"})
        check("history survives across handles", len(EpisodicLog(path).recent(10)) == 2)
        check("missing file reads empty", EpisodicLog(Path(tmp) / "none.jsonl").recent(5) == [])


def test_manager_records_episode():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                           unreal_bridge=None, memory_store=None)
        mgr._agents_dir = Path(tmp) / "agents"
        observation = {
            "grid": {"key": "12,7"}, "place": ["village square"], "world_time": "Day 1 08:30",
            "seen": {"characters": [{"label": "Maren"}, {"label": "unknown person"}]},
        }
        mgr._record_episode("dufus", observation,
                            action={"type": "walk_to"}, result={"status": "accepted"})

        events = mgr._episodic("dufus").recent(5)
        check("one episode recorded", len(events) == 1)
        e = events[0]
        check("grid cell captured", e["grid_cell"] == "12,7")
        check("place captured", e["place"] == "village square")
        check("named characters captured, anon dropped", e["saw"] == ["Maren"])
        check("action + outcome captured", (e["action"], e["outcome"]) == ("walk_to", "accepted"))
        check("persisted to episodes.jsonl",
              (mgr._agents_dir / "dufus" / "episodes.jsonl").exists())


def main():
    test_append_and_recent()
    test_query_filters()
    test_persistence_is_append_only()
    test_manager_records_episode()
    print("\nAll episodic-memory checks passed.")


if __name__ == "__main__":
    main()
