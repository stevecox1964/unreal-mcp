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


def test_relevance_ranking():
    """relevant() blends recency, spatial proximity, and social ties. Asserted by
    ordering properties, not magic constants."""
    with tempfile.TemporaryDirectory() as tmp:
        log = EpisodicLog(Path(tmp) / "episodes.jsonl")
        # Oldest -> newest. e0 here-and-now-ish, e1 elsewhere, e2 with a friend.
        log.record({"world_time": "T0", "grid_cell": "1,1", "place": "square", "saw": []})
        log.record({"world_time": "T1", "grid_cell": "9,9", "place": "far field", "saw": []})
        log.record({"world_time": "T2", "grid_cell": "9,9", "place": "far field", "saw": ["Maren"]})

        # Spatial: at cell 1,1 with no social context, the same-cell event wins
        # over more-recent elsewhere events.
        top = log.relevant(n=1, current_cell="1,1", current_place="square", known_names=[])
        check("same-cell event ranks top", top[0]["world_time"] == "T0")

        # Social: knowing Maren lifts the event she appears in.
        ranked = log.relevant(n=3, current_cell="9,9", current_place="far field", known_names=["Maren"])
        check("event with a known person outranks its peer",
              ranked.index(next(e for e in ranked if e["world_time"] == "T2"))
              < ranked.index(next(e for e in ranked if e["world_time"] == "T1")))

        # Recency: with no spatial/social signal at all, newest comes first.
        plain = log.relevant(n=3, current_cell=None, current_place=None, known_names=[])
        check("newest first when nothing else distinguishes", plain[0]["world_time"] == "T2")
        check("relevant caps at n", len(log.relevant(n=2)) == 2)


def test_consolidate_rolls_up_old_keeps_recent():
    with tempfile.TemporaryDirectory() as tmp:
        log = EpisodicLog(Path(tmp) / "episodes.jsonl")
        # 30 events at "square", 10 at "market"; oldest first.
        for i in range(30):
            log.record({"world_time": f"T{i:03d}", "grid_cell": "1,1", "place": "square",
                        "saw": (["Maren"] if i % 2 == 0 else []), "action": "walk_to", "outcome": "ok"})
        for i in range(30, 40):
            log.record({"world_time": f"T{i:03d}", "grid_cell": "2,2", "place": "market",
                        "saw": [], "action": "idle", "outcome": "ok"})

        # Below threshold: no-op.
        res = log.consolidate(max_events=100, keep_recent=10)
        check("no-op below threshold", res["consolidated"] == 0)
        check("nothing changed below threshold", len(log.recent(999)) == 40)

        # Above threshold: summarise all but the most recent 10.
        res = log.consolidate(max_events=20, keep_recent=10)
        check("rolled up the old events", res["consolidated"] == 30)
        rows = log.recent(999)
        summaries = [r for r in rows if r.get("kind") == "summary"]
        verbatim = [r for r in rows if r.get("kind") != "summary"]
        check("recent 10 kept verbatim", len(verbatim) == 10)
        check("the kept events are the newest", verbatim[-1]["world_time"] == "T039")
        check("old events summarised by place", {s["place"] for s in summaries} == {"square"})
        sq = next(s for s in summaries if s["place"] == "square")
        check("summary counts the rolled-up events", sq["count"] == 30)
        check("summary preserves unique faces seen", sq["saw"] == ["Maren"])
        check("summary records its time span", (sq["first_time"], sq["last_time"]) == ("T000", "T029"))


def test_reads_tolerate_summaries():
    with tempfile.TemporaryDirectory() as tmp:
        log = EpisodicLog(Path(tmp) / "episodes.jsonl")
        for i in range(40):
            log.record({"world_time": f"T{i:03d}", "grid_cell": "1,1", "place": "square",
                        "saw": ["Maren"], "action": "a", "outcome": "ok"})
        log.consolidate(max_events=20, keep_recent=10)
        # query/relevant must still work across summary + verbatim rows.
        check("query by place spans summaries", len(log.query(place="square")) >= 1)
        check("query by character spans summaries", len(log.query(character="maren")) >= 1)
        check("relevant() does not crash on summaries",
              isinstance(log.relevant(n=5, current_place="square", known_names=["Maren"]), list))


def test_record_auto_consolidates_when_large():
    with tempfile.TemporaryDirectory() as tmp:
        log = EpisodicLog(Path(tmp) / "episodes.jsonl")
        # Tight thresholds so the auto-trigger fires within the test.
        log._max_events, log._keep_recent, log._consolidate_every = 50, 20, 25
        for i in range(120):
            log.record({"world_time": f"T{i:03d}", "grid_cell": "1,1", "place": "square",
                        "saw": [], "action": "a", "outcome": "ok"})
        rows = log.recent(999)
        check("auto-consolidation kept the file bounded", len(rows) < 120)
        check("a summary row is present", any(r.get("kind") == "summary" for r in rows))
        check("newest event still present verbatim", rows[-1]["world_time"] == "T119")


def main():
    test_append_and_recent()
    test_query_filters()
    test_persistence_is_append_only()
    test_manager_records_episode()
    test_relevance_ranking()
    test_consolidate_rolls_up_old_keeps_recent()
    test_reads_tolerate_summaries()
    test_record_auto_consolidates_when_large()
    print("\nAll episodic-memory checks passed.")


if __name__ == "__main__":
    main()
