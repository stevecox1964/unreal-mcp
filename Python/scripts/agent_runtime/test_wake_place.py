"""Offline tests for the wake/already-there place fix (user, 2026-07-05).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_wake_place.py

The bug: the sequencer's "am I already there?" was a name-only match against
the community cell name, so on a fresh world (nothing named yet) an agent
standing at its scheduled place was told to travel — Maren woke at her stall
and wandered off hunting for "the vegetable truck".

Covers:
  - planner.step(at_place=...): geometric ground truth overrides the name
    match in both directions; None falls back to the legacy name match.
  - AgentManager._at_scheduled_place: community cell = same grid cell;
    owned place = inside its extent box (9x9 m); unresolvable = None.
  - Wake seeding: the agent's FIRST schedule step of a run seeds an unknown
    scheduled place as the agent's own place cell centered where it stands
    (first-time place-cell initialization); later steps never seed.
  - End-to-end _attach_schedule: Maren wakes at her (unnamed) stall ->
    status "act", owned place created; a later unknown place -> "travel".
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import planner                        # noqa: E402
from agent_runtime.agent_manager import AgentManager     # noqa: E402
from agent_runtime.place_db import PLACE_EXTENT_CM, PlaceDB  # noqa: E402
from agent_runtime.world_grid import WorldGrid           # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


SCHED = [{"start": "08:00", "end": "12:00",
          "activity": "tend the stall", "place": "the vegetable truck"}]


def test_planner_at_place_override():
    nine = 9 * 60
    d = planner.step(SCHED, nine, current_place=None, at_place=True)
    check("at_place=True -> act (position beats missing name)", d["status"] == "act")
    d = planner.step(SCHED, nine, current_place="the vegetable truck", at_place=False)
    check("at_place=False -> travel (position beats matching name)", d["status"] == "travel")
    d = planner.step(SCHED, nine, current_place="the vegetable truck", at_place=None)
    check("at_place=None -> legacy name match still acts", d["status"] == "act")
    d = planner.step(SCHED, nine, current_place=None, at_place=None)
    check("at_place=None + unknown place -> legacy travel", d["status"] == "travel")


class StubBridge:
    def execute_action(self, actor_name, action):
        return {"status": "accepted", "action": action.get("type")}


def _manager(tmp):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=StubBridge(), memory_store=None)
    mgr._agents_dir = Path(tmp) / "agents"
    # cell (5,5) covers x,y in [0,400): grid index (0,0), center (200,200).
    mgr.world_grid = WorldGrid(cell_size=400.0,
                               bounds={"min_x": -2000, "min_y": -2000,
                                       "max_x": 1999, "max_y": 1999})
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    mgr.agents = {}
    return mgr


def _obs(mgr, x, y, world_time="Day 1, 09:00"):
    return {"location": {"x": x, "y": y, "z": 90.0},
            "grid": mgr.world_grid.locate(x, y),
            "place": [], "place_context": {}, "world_time": world_time}


BLOCK = SCHED[0]


def test_at_scheduled_place_geometry():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)

        # Unresolvable, no seeding allowed -> unknown.
        check("unknown place -> None",
              mgr._at_scheduled_place("maren", BLOCK, _obs(mgr, 320.0, 120.0)) is None)
        check("no block -> None", mgr._at_scheduled_place("maren", None, _obs(mgr, 0, 0)) is None)
        check("nothing was seeded", mgr.place_db.all_owned_places() == [])

        # Community-named cell: "there" = standing in that grid cell.
        mgr.place_db.set_name("dufus", 5, 5, "the vegetable truck", "T0")
        check("in the community cell -> True",
              mgr._at_scheduled_place("maren", BLOCK, _obs(mgr, 320.0, 120.0)) is True)
        check("outside the community cell -> False",
              mgr._at_scheduled_place("maren", BLOCK, _obs(mgr, 1500.0, 1500.0)) is False)


def test_at_scheduled_place_owned_box():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        # Owned place anchored at cell (5,5) center (200,200) + (120,-80) = (320,120).
        mgr.place_db.add_owned_place("maren", 5, 5, "the vegetable truck",
                                     dx=120.0, dy=-80.0)
        half = PLACE_EXTENT_CM / 2.0
        check("at the anchor point -> True",
              mgr._at_scheduled_place("maren", BLOCK, _obs(mgr, 320.0, 120.0)) is True)
        check("just inside the 9m box -> True",
              mgr._at_scheduled_place("maren", BLOCK,
                                      _obs(mgr, 320.0 + half - 1, 120.0)) is True)
        check("just outside the 9m box -> False",
              mgr._at_scheduled_place("maren", BLOCK,
                                      _obs(mgr, 320.0 + half + 1, 120.0)) is False)


def test_wake_seeds_unknown_place():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        at = mgr._at_scheduled_place("maren", BLOCK, _obs(mgr, 320.0, 120.0),
                                     seed_if_unknown=True)
        check("wake seed -> already there", at is True)
        owned = mgr.place_db.owned_places_in_cell(5, 5)
        check("owned place created", len(owned) == 1
              and owned[0]["name"] == "the vegetable truck"
              and owned[0]["owner"] == "maren")
        check("centered where the agent stands",
              owned[0]["dx"] == 120.0 and owned[0]["dy"] == -80.0)
        check("9x9 m box", owned[0]["extent_cm"] == PLACE_EXTENT_CM == 900.0)


class StubAgent:
    """Duck-typed Agent: just what ensure_daily_plan + step consume."""
    def __init__(self, agent_id, blocks):
        self.agent_id = agent_id
        self.last_activity = None
        self.character_text = "stub"
        self.goals_text = "stub"
        self.daily_schedule_day = "Day 1"
        self.daily_schedule_blocks = blocks

    def set_daily_schedule(self, blocks, day, agents_dir=None):
        self.daily_schedule_blocks, self.daily_schedule_day = blocks, day


def test_attach_schedule_wake_flow():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        maren = StubAgent("maren", [dict(b) for b in SCHED])

        # Wake: standing at the (unrecorded) stall -> act, and the stall is
        # seeded as her own 9x9 m place cell (first-time initialization).
        obs = _obs(mgr, 320.0, 120.0)
        mgr._attach_schedule(maren, obs)
        check("wake at the stall -> act (not travel)",
              obs["schedule"]["status"] == "act")
        check("stall seeded on wake",
              mgr.place_db.find_owned_place("the vegetable truck") is not None)

        # Later step, different unknown place -> travel, and NO seeding.
        maren.daily_schedule_blocks[0]["place"] = "Don's Donuts"
        obs2 = _obs(mgr, 320.0, 120.0)
        mgr._attach_schedule(maren, obs2)
        check("later unknown place -> travel", obs2["schedule"]["status"] == "travel")
        check("later steps never seed",
              mgr.place_db.find_owned_place("Don's Donuts") is None)

        # A new run rearms the wake seed (start_simulation clears the marker).
        mgr._wake_stepped.clear()
        obs3 = _obs(mgr, 320.0, 120.0)
        mgr._attach_schedule(maren, obs3)
        check("next run's first step may seed again",
              mgr.place_db.find_owned_place("Don's Donuts") is not None)
        check("re-armed wake -> act at the new spot", obs3["schedule"]["status"] == "act")


def main():
    test_planner_at_place_override()
    test_at_scheduled_place_geometry()
    test_at_scheduled_place_owned_box()
    test_wake_seeds_unknown_place()
    test_attach_schedule_wake_flow()
    print("\nAll wake-place checks passed.")


if __name__ == "__main__":
    main()
