"""Offline tests for the decision feed: record -> read -> clear (Clear-feed btn).

The Sim page's live feed tails agent_decisions.log via MemoryStore. The Clear
feed button truncates that file (without touching agent memories). Pure file I/O
in a temp dir — no Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_decision_feed.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.memory_store import MemoryStore  # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _store(tmp: Path) -> MemoryStore:
    agents = tmp / "agents"
    (agents / "dufus").mkdir(parents=True)
    ms = MemoryStore(tmp)
    ms.update_agents_dir(agents)
    return ms


def test_record_then_read_with_timestamp():
    with tempfile.TemporaryDirectory() as t:
        ms = _store(Path(t))
        ms.record("dufus", {"_thought": "to the square"}, {"type": "walk_to"}, {"status": "success"})
        ms.record("maren", {"_thought": "tend stand"}, {"type": "idle"}, {"status": "accepted"})
        events = ms.get_recent_events(10)
        check("both decisions read back", len(events) == 2)
        check("entry carries the agent + action", events[0]["agent_id"] == "dufus"
              and events[0]["action_type"] == "walk_to")
        check("entry carries a timestamp for the feed", bool(events[0].get("timestamp")))


def test_clear_empties_feed_but_keeps_path():
    with tempfile.TemporaryDirectory() as t:
        ms = _store(Path(t))
        ms.record("dufus", {"_thought": "x"}, {"type": "walk_to"}, {"status": "success"})
        ms.record("dufus", {"_thought": "y"}, {"type": "idle"}, {"status": "accepted"})
        cleared = ms.clear_recent_events()
        check("clear reports the number of lines removed", cleared == 2)
        check("feed is empty after clear", ms.get_recent_events(10) == [])
        check("log file still exists (path stays valid)", ms.decisions_log.exists())

        # New decisions still append cleanly after a clear.
        ms.record("maren", {"_thought": "z"}, {"type": "observe"}, {"status": "success"})
        check("recording works after clear", len(ms.get_recent_events(10)) == 1)


def test_feed_can_show_only_the_active_run():
    with tempfile.TemporaryDirectory() as t:
        ms = _store(Path(t))
        ms.sim_run_id = "SR12"
        ms.record("dufus", {"_thought": "old"}, {"type": "walk_to"}, {"status": "success"})
        ms.sim_run_id = "SR13"
        ms.record("maren", {"_thought": "new"}, {"type": "idle"}, {"status": "accepted"})

        current = ms.get_recent_events(20, sim_run_id="SR13")
        check("active-run feed excludes previous decisions",
              len(current) == 1 and current[0]["sim_run"] == "SR13")
        check("durable decision log keeps both runs", len(ms.get_recent_events(20)) == 2)
        check("zero limit returns an empty feed", ms.get_recent_events(0) == [])


def test_clear_on_empty_is_safe():
    with tempfile.TemporaryDirectory() as t:
        ms = _store(Path(t))
        check("clearing a never-written feed returns 0", ms.clear_recent_events() == 0)


def main():
    test_record_then_read_with_timestamp()
    test_clear_empties_feed_but_keeps_path()
    test_feed_can_show_only_the_active_run()
    test_clear_on_empty_is_safe()
    print("\nAll decision-feed checks passed.")


if __name__ == "__main__":
    main()
