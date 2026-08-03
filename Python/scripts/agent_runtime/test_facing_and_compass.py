"""Offline tests for the direction bug SR34 exposed (backlog #56).

SR34, cell (6,6): Dufus walked south into a corn field, the survey turned him
through E/S/W/N and left him facing north, and the LLM then said "turn back the
way I came". ``back`` is 180 degrees from the *current facing*, which the survey
had just reset — so it resolved to south and walked him deeper into the corn.
The engine's own rotation log proves it: yaw -114.6 on arrival, 0/90/180/-90
through the survey, and -90 still on the deciding tick.

Three things are pinned here: the survey restores the facing it arrived with,
compass directions resolve to fixed world headings regardless of facing, and
the inbound heading is stated as a fact so retreat is expressible at all.

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_facing_and_compass.py
"""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import llm_router                    # noqa: E402
from agent_runtime.agent_manager import AgentManager    # noqa: E402
from agent_runtime.place_db import PlaceDB              # noqa: E402
from agent_runtime.world_grid import WorldGrid          # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


class _StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.survey_priority = True
        self.has_unreal_binding = True
        self.bound_unreal_actor_name = f"APC_{agent_id}_BP_C_1"


class _StubBridge:
    """Records set_facing calls; everything else is a benign success."""

    def __init__(self):
        self.facings: list[float] = []

    def set_facing(self, actor, location, yaw):
        self.facings.append(float(yaw))
        return {"status": "success"}


class _StubMemory:
    def record(self, **kwargs):
        pass

    def record_survey_event(self, agent_id, progress):
        pass


def _manager(tmp, bridge=None):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=bridge, memory_store=_StubMemory())
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.world_grid = WorldGrid(cell_size=400.0,
                               bounds={"min_x": -2000, "min_y": -2000,
                                       "max_x": 1999, "max_y": 1999})
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    return mgr


def _obs(x, y, yaw, col=5, row=5):
    return {"grid": {"key": f"{col},{row}", "col": col, "row": row},
            "location": {"x": x, "y": y, "z": 90.0},
            "rotation": {"x": 0.0, "y": yaw, "z": 0.0},
            "world_time": "Day 1 09:00"}


# ── Fix 1: the survey puts the avatar back the way it was ─────────────────────

def test_survey_restores_the_facing_it_arrived_with():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge()
        mgr = _manager(tmp, bridge)
        mgr.agents = {"dufus": _StubAgent("dufus")}

        # Arrive facing SW (yaw 135) — the direction of travel into the cell.
        arriving = _obs(200.0, 200.0, 135.0)
        mgr._sweep_step("dufus", arriving)
        check("the arrival facing is remembered at sweep start",
              mgr._cell_sweeps["dufus"]["entry_yaw"] == 135.0)

        # Run the survey out. The four cardinals are turned to by the observe
        # step, which the real bridge performs; here we only need it to finish.
        for _ in range(10):
            if mgr._sweep_step("dufus", _obs(200.0, 200.0, 270.0)) is None:
                break
        check("the survey ended", "dufus" not in mgr._cell_sweeps)
        check("facing was restored exactly once", bridge.facings == [135.0])
        check("and to the arrival heading, not the survey's last cardinal (N)",
              bridge.facings[-1] == 135.0 and bridge.facings[-1] != 270.0)


def test_restore_survives_a_bridge_that_refuses_the_turn():
    class _Refusing(_StubBridge):
        def set_facing(self, actor, location, yaw):
            return {"error": "actor not found"}

    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp, _Refusing())
        mgr.agents = {"dufus": _StubAgent("dufus")}
        mgr._sweep_step("dufus", _obs(200.0, 200.0, 135.0))
        for _ in range(10):
            if mgr._sweep_step("dufus", _obs(200.0, 200.0, 270.0)) is None:
                break
        check("a failed restore never breaks the completed survey",
              "dufus" not in mgr._cell_sweeps)


# ── Fix 3: compass directions do not depend on which way the body points ──────

def test_compass_directions_are_absolute():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        # UE yaw: E=0, S=90, W=180, N=270. Same request, four different facings.
        targets = [mgr._direction_target(_obs(0.0, 0.0, yaw), "north")
                   for yaw in (0.0, 90.0, 180.0, -90.0)]
        check("north means north no matter which way the avatar faces",
              all(t is not None and round(t[1]) == round(targets[0][1])
                  for t in targets))
        check("and north is -y in UE", targets[0][1] < -1000.0)

        north = mgr._direction_target(_obs(0.0, 0.0, 33.0), "north")
        south = mgr._direction_target(_obs(0.0, 0.0, 33.0), "south")
        east = mgr._direction_target(_obs(0.0, 0.0, 33.0), "east")
        west = mgr._direction_target(_obs(0.0, 0.0, 33.0), "west")
        check("south is the exact reverse of north", round(south[1]) == -round(north[1]))
        check("east is +x", east[0] > 1000.0 and abs(east[1]) < 1.0)
        check("west is the exact reverse of east", round(west[0]) == -round(east[0]))
        check("diagonals resolve too",
              mgr._direction_target(_obs(0.0, 0.0, 33.0), "southwest") is not None)


def test_body_relative_directions_still_work_and_still_follow_facing():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        facing_south = mgr._direction_target(_obs(0.0, 0.0, 90.0), "forward")
        facing_north = mgr._direction_target(_obs(0.0, 0.0, 270.0), "forward")
        check("forward still means whichever way the body points",
              facing_south[1] > 0 and facing_north[1] < 0)
        check("unknown direction words resolve to nothing, loudly",
              mgr._direction_target(_obs(0.0, 0.0, 90.0), "widdershins") is None)


def test_the_sr34_corn_field_decision_now_leaves_the_field():
    """The exact SR34 failure, replayed against the fixed resolver.

    Dufus walked south into the corn (arriving yaw -114.6), the survey left him
    at yaw -90, and he asked to go back the way he came. Body-relative ``back``
    from yaw -90 is south — deeper in. The compass word he is now told to use
    takes him north, out.
    """
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        after_survey = _obs(-8982.7, 735.4, -90.0)
        old_way = mgr._direction_target(after_survey, "back")
        new_way = mgr._direction_target(after_survey, "north")
        check("body-relative 'back' after a survey still walks south (the bug)",
              old_way[1] > 735.4)
        check("the compass heading walks north, out of the field",
              new_way[1] < 735.4)


# ── Fix 2: the inbound heading is a stated fact ───────────────────────────────

def test_travel_fact_reports_the_heading_actually_travelled():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        check("no fact before the APC has moved",
              mgr._travel_fact("dufus", {"x": 0.0, "y": 0.0, "z": 0.0}) is None)

        # Walk south 1500cm (UE: +y is south), as SR34 did into the corn.
        fact = mgr._travel_fact("dufus", {"x": 0.0, "y": 1500.0, "z": 0.0})
        check("the heading travelled is south", fact["heading"] == "S")
        check("so the way back is north", fact["came_from"] == "N")
        check("distance is recorded", fact["distance_cm"] == 1500.0)

        # Standing still must not overwrite it with jitter.
        same = mgr._travel_fact("dufus", {"x": 0.0, "y": 1500.5, "z": 0.0})
        check("pose jitter does not invent a new heading", same["heading"] == "S")

        # A different agent keeps its own trail.
        check("the fact is per agent",
              mgr._travel_fact("maren", {"x": 9000.0, "y": 9000.0, "z": 0.0}) is None)


def test_travel_note_names_the_word_the_action_accepts():
    note = llm_router._travel_note({"heading": "S", "came_from": "N",
                                    "distance_cm": 1500.0})
    check("it states the heading travelled", "heading S" in note)
    check("it states the way back", "The way you came is N" in note)
    check("it names the exact direction word walk_to takes",
          "walk_to north" in note)
    check("it says nothing before the first move",
          "not travelled yet" in llm_router._travel_note(None))


def test_facing_is_reported_in_compass_terms():
    check("north", llm_router._facing_text({"y": -90.0}).startswith("N "))
    check("south", llm_router._facing_text({"y": 90.0}).startswith("S "))
    check("the raw yaw is still there for the log",
          "yaw 90" in llm_router._facing_text({"y": 90.0}))
    check("unknown rotation stays unknown",
          llm_router._facing_text(None) == "unknown")


def test_prompt_carries_the_travel_slot_and_compass_vocabulary():
    tpl = llm_router._USER_TEMPLATE_VISION
    check("template has the travel slot", "{travel_note}" in tpl)
    schema = llm_router._ACTION_SCHEMAS["walk_to"]
    check("walk_to advertises compass directions", "north|south|east|west" in schema)
    check("walk_to still advertises body-relative ones", "forward-left" in schema)


if __name__ == "__main__":
    test_survey_restores_the_facing_it_arrived_with()
    test_restore_survives_a_bridge_that_refuses_the_turn()
    test_compass_directions_are_absolute()
    test_body_relative_directions_still_work_and_still_follow_facing()
    test_the_sr34_corn_field_decision_now_leaves_the_field()
    test_travel_fact_reports_the_heading_actually_travelled()
    test_travel_note_names_the_word_the_action_accepts()
    test_facing_is_reported_in_compass_terms()
    test_prompt_carries_the_travel_slot_and_compass_vocabulary()
    print("\nAll facing/compass checks passed.")
