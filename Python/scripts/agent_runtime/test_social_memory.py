"""Offline tests for the per-agent social/acquaintance memory (backlog #5).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_social_memory.py

Covers the SocialMemory store (sightings, interactions, sentiment, persistence,
ranking) and AgentManager._record_sightings wiring perceived characters in.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager      # noqa: E402
from agent_runtime.social_memory import SocialMemory      # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_sightings_and_identity():
    s = SocialMemory()
    check("new sighting recorded", s.record_sighting("Maren", "3,4", "Day 1 08:00") is True)
    check("anonymous label rejected", s.record_sighting("unknown person", "3,4", "Day 1 08:00") is False)
    check("blank label rejected", s.record_sighting("   ", "3,4", "Day 1 08:00") is False)
    check("knows the named person", s.knows("maren"))
    check("does not know a stranger", not s.knows("nobody"))

    rec = s.get("MAREN")  # lookup is case-insensitive
    check("first_met set once", rec["first_met"] == "Day 1 08:00")
    check("meet_count starts at 1", rec["meet_count"] == 1)
    check("display name preserved", rec["name"] == "Maren")

    s.record_sighting("Maren", "5,5", "Day 1 09:00")
    rec = s.get("maren")
    check("meet_count increments", rec["meet_count"] == 2)
    check("first_met unchanged on re-sight", rec["first_met"] == "Day 1 08:00")
    check("last_seen advances", rec["last_seen"] == "Day 1 09:00")
    check("last_cell tracks latest", rec["last_cell"] == "5,5")


def test_interactions_and_sentiment():
    s = SocialMemory()
    # An interaction with an unseen person implies a meeting.
    check("interaction creates acquaintance", s.record_interaction("Dufus", "Day 1 10:00", 0.3) is True)
    rec = s.get("dufus")
    check("interaction_count bumped", rec["interaction_count"] == 1)
    check("sentiment moved", abs(rec["sentiment"] - 0.3) < 1e-9)

    for _ in range(10):
        s.record_interaction("Dufus", "Day 1 10:05", 0.5)
    check("sentiment clamps at +1", s.get("dufus")["sentiment"] == 1.0)
    for _ in range(10):
        s.record_interaction("Dufus", "Day 1 10:10", -0.5)
    check("sentiment clamps at -1", s.get("dufus")["sentiment"] == -1.0)
    check("anonymous interaction rejected", s.record_interaction("someone", "Day 1 10:00", 0.5) is False)


def test_ranking_and_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "social.json"
        s = SocialMemory()
        s.record_sighting("Maren", "1,1", "T0")
        s.record_sighting("Maren", "1,1", "T1")
        s.record_sighting("Maren", "1,1", "T2")   # meet_count 3
        s.record_sighting("Bob", "2,2", "T0")     # meet_count 1
        check("ranked by meet_count desc", s.known_names() == ["Maren", "Bob"])

        s.save(path)
        reloaded = SocialMemory.load(path)
        check("survives a save/load round-trip", reloaded.get("maren")["meet_count"] == 3)
        check("reload preserves ranking", reloaded.known_names() == ["Maren", "Bob"])

    check("loading a missing file is empty, not an error",
          SocialMemory.load(Path(tmp) / "gone.json").known_names() == [])


def test_manager_records_perceived_characters():
    """AgentManager._record_sightings pulls characters out of a perception result
    and writes them to the agent's social memory, keyed to the current cell."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                           unreal_bridge=None, memory_store=None)
        mgr._agents_dir = Path(tmp) / "agents"

        observation = {
            "grid": {"key": "12,7"},
            "world_time": "Day 1 08:30",
            "seen": {"characters": [
                {"label": "Maren", "confidence": 0.9},
                {"label": "unknown person", "confidence": 0.4},
            ]},
        }
        mgr._record_sightings("dufus", observation)

        social = mgr._social("dufus")
        check("named character remembered", social.knows("maren"))
        check("anonymous character not remembered", not social.knows("unknown person"))
        check("sighting cell recorded from grid", social.get("maren")["last_cell"] == "12,7")
        check("sighting time from world_time", social.get("maren")["first_met"] == "Day 1 08:30")

        # Persisted to disk so a later tick / restart sees it.
        reloaded = SocialMemory.load(mgr._agents_dir / "dufus" / "social.json")
        check("sighting persisted to social.json", reloaded.knows("maren"))


def test_last_interacted_tracks_speech_only():
    # #12.1: last_interacted marks a real conversation, distinct from a sighting.
    s = SocialMemory()
    s.record_sighting("Maren", "3,4", "Day 1, 08:00")
    check("a mere sighting sets no last_interacted", s.last_interacted("Maren") is None)
    s.record_interaction("Maren", "Day 1, 08:05")
    check("speaking sets last_interacted", s.last_interacted("maren") == "Day 1, 08:05")
    check("record carries the field", s.get("maren")["last_interacted"] == "Day 1, 08:05")
    check("unknown person has no last_interacted", s.last_interacted("nobody") is None)


def test_recently_greeted_cooldown():
    """AgentManager._mark_recent_greetings flags an acquaintance greeted within the
    cooldown so the reaction gate won't re-greet (#12.1)."""
    from agent_runtime.agent_manager import _GREET_COOLDOWN_MINUTES
    with tempfile.TemporaryDirectory() as tmp:
        mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                           unreal_bridge=None, memory_store=None)
        just = [{"name": "Maren", "last_interacted": "Day 1, 08:00"}]
        near = mgr._mark_recent_greetings(just, "Day 1, 08:10")   # 10 min later
        check("recently greeted -> flagged", near[0]["recently_greeted"] is True)

        later = mgr._mark_recent_greetings(just, f"Day 1, 09:30")  # 90 min > cooldown
        check("past the cooldown -> not flagged (greet again)",
              later[0]["recently_greeted"] is False)
        check("cooldown is a positive window", _GREET_COOLDOWN_MINUTES > 0)

        never = mgr._mark_recent_greetings([{"name": "Bob"}], "Day 1, 08:10")
        check("never interacted -> not flagged", never[0]["recently_greeted"] is False)

        # A backwards clock (day restart) must not read as "recent".
        restart = mgr._mark_recent_greetings(
            [{"name": "Maren", "last_interacted": "Day 2, 08:00"}], "Day 1, 08:10")
        check("clock went backwards -> not flagged", restart[0]["recently_greeted"] is False)

        # Enrichment is a copy — the flag never leaks into the stored record.
        check("source record left unmutated", "recently_greeted" not in just[0])


def test_manager_records_interactions_on_speech():
    """When an agent speaks, it logs an interaction with each named person it
    currently perceives (the meeting is the fact; sentiment stays neutral)."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                           unreal_bridge=None, memory_store=None)
        mgr._agents_dir = Path(tmp) / "agents"
        observation = {
            "grid": {"key": "4,4"}, "world_time": "Day 1 09:00",
            "seen": {"characters": [{"label": "Maren"}, {"label": "unknown person"}]},
        }
        mgr._record_interactions("dufus", observation)

        social = mgr._social("dufus")
        check("interaction logged for named person", social.get("maren")["interaction_count"] == 1)
        check("anonymous person not logged", not social.knows("unknown person"))
        check("sentiment stays neutral without a real signal", social.get("maren")["sentiment"] == 0.0)


def main():
    test_sightings_and_identity()
    test_interactions_and_sentiment()
    test_ranking_and_persistence()
    test_manager_records_perceived_characters()
    test_last_interacted_tracks_speech_only()
    test_recently_greeted_cooldown()
    test_manager_records_interactions_on_speech()
    print("\nAll social-memory checks passed.")


if __name__ == "__main__":
    main()
