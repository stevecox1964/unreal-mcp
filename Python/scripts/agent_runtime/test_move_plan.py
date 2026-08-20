"""Offline tests for the move plan — #86, #88, #89, #90.

Before these, every direction-relative move was exactly 15 m, forever, whatever
was in front of the body and however close the goal. SR46 landed in three 9 m
patches it had accurately refused (a 15 m step cannot aim finer than the trap is
wide); SR47 asked for 45 m north twice and arrived 52 m east then 48 m west,
because a far target lets the navmesh route around something; SR49 bounced 30 m
back and forth for fourteen ticks because the body-box raster is exactly as wide
as the body and could only ever say `open=none`.

What is pinned here:

* **#90** the step IS the engine's answer — `plan_step` derives the distance from
  the measured reach, and the fixed step survives only as a labelled fallback.
* **#86** a refusal shortens the step, an unmeasured input is never read as
  clear, and a grown step is cut into hops so the engine never gets a far target.
* **#88** a column with anything in it is not a gap, and a heading list names
  compass words — with "none of them fit" distinguishable from "never asked".
* **#89** `_look_along` returns *not measured* rather than *clear* on a miss.
* The five things that end a walk plan, each of which buys a cognition tick.

Fully offline (no LLM, no Unreal, temp DB). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_move_plan.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import move_plan  # noqa: E402
from agent_runtime.agent_manager import (  # noqa: E402
    _STEP_DISTANCE, AgentManager, _open_columns,
)
from agent_runtime.llm_router import _sense_note  # noqa: E402
from agent_runtime.place_db import PlaceDB  # noqa: E402
from agent_runtime.world_grid import WorldGrid  # noqa: E402


class _Stub:
    """Stands in for any collaborator these paths never really call."""
    def __getattr__(self, _):
        return lambda *a, **k: None


class _AgentStub:
    agent_id = "dufus"
    bound_unreal_actor_name = "APC_Dufus"

    def mark_ticked(self, _agents_dir):
        pass


class _VolumeBridge(_Stub):
    """A bridge whose forward volume answers per heading offset.

    ``blocked`` maps a yaw offset (degrees, 0 = straight ahead) to the distance
    at which the body stops. An offset absent from the map is clear.
    """

    def __init__(self, blocked=None):
        self.blocked = blocked or {}
        self.calls = []
        self.orders = []

    def forward_volume(self, actor, distance_cm=500.0, yaw_offset_deg=0.0):
        self.calls.append((distance_cm, yaw_offset_deg))
        hit = self.blocked.get(yaw_offset_deg)
        if hit is None:
            return {"success": True, "fits": True, "hit": False,
                    "clearance_cm": distance_cm, "nearest_cm": distance_cm,
                    "cells": [], "open_columns": []}
        return {"success": True, "fits": False, "hit": True,
                "clearance_cm": float(hit), "nearest_cm": float(hit),
                "cells": [{"column": c, "blocked": True}
                          for c in ("far_left", "left", "centre",
                                    "right", "far_right")],
                "open_columns": [],
                "contact": {"actor_name": "veh_Sedan_6",
                            "actor_class": "SkeletalMeshActor",
                            "distance_cm": float(hit)}}

    def execute_action(self, actor, action):
        self.orders.append(action.get("location"))
        return {"status": "success"}


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def make_manager(tmp, name, bridge=None):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=_Stub(),
                       unreal_bridge=bridge or _Stub(), memory_store=_Stub())
    mgr.place_db = PlaceDB(Path(tmp) / f"{name}.db")
    mgr.world_grid = WorldGrid(
        cell_size=3000.0,
        bounds={"min_x": 0.0, "min_y": 0.0,
                "max_x": 16 * 3000.0, "max_y": 11 * 3000.0},
    )
    return mgr


def obs_at(x, y, yaw=0.0):
    """Facing east by default: UE yaw 0 is +x, which _ABSOLUTE_DIRECTION_YAW calls east."""
    return {"location": {"x": x, "y": y, "z": 100.0},
            "rotation": {"x": 0.0, "y": yaw, "z": 0.0}}


# ── #90: the engine's answer IS the step ─────────────────────────────────────

def test_the_step_is_what_the_engine_measured():
    wide = move_plan.plan_step(reach_cm=9000.0, standoff_cm=300.0)
    check("clear ground gives the measured reach less the standoff",
          wide["distance_cm"] == 8700.0)
    check("a measured step says so", wide["measured"] is True)

    near = move_plan.plan_step(reach_cm=1200.0, standoff_cm=300.0)
    check("a wall at 12 m gives a 9 m step", near["distance_cm"] == 900.0)
    check("the step is not the old constant", near["distance_cm"] != _STEP_DISTANCE)

    # The whole point: two different grounds must not produce the same step.
    check("different ground, different step",
          wide["distance_cm"] != near["distance_cm"])


def test_an_unmeasured_step_is_labelled_a_guess():
    blind = move_plan.plan_step(reach_cm=None)
    check("no measurement falls back to the fixed step",
          blind["distance_cm"] == _STEP_DISTANCE)
    check("and does not claim to be measured", blind["measured"] is False)
    check("and says out loud that it is a guess", "guess" in blind["why"])
    # Rule 12: silence must never be dressed up as evidence.
    check("a measured step never calls itself a guess",
          "guess" not in move_plan.plan_step(reach_cm=9000.0)["why"])


def test_the_model_may_only_ask_for_less():
    clear = move_plan.plan_step(reach_cm=9000.0, prefer="close")
    check("'close' overrides open ground", clear["distance_cm"] == 400.0)
    check("and the reason names the asking, not the ground",
          "you asked to stop close" in clear["why"])
    far = move_plan.plan_step(reach_cm=1200.0, prefer="far", standoff_cm=300.0)
    check("'far' cannot exceed what the ground allows",
          far["distance_cm"] == 900.0)


def test_the_step_never_outruns_the_ground_it_described():
    plan = move_plan.plan_step(reach_cm=1200.0, open_run_cm=9000.0,
                               standoff_cm=300.0)
    check("a 9 m step does not report 90 m of known ground",
          "90.0 m" not in plan["why"])
    check("it describes the ground being crossed",
          "All of it is ground APCs have walked before" in plan["why"])
    fresh = move_plan.plan_step(reach_cm=9000.0, open_run_cm=0.0)
    check("new ground is stated as new",
          "None of it has been walked before" in fresh["why"])


# ── #86: refusals, floors, hops ──────────────────────────────────────────────

def test_a_refusal_shortens_the_step_but_never_cancels_it():
    plan = move_plan.plan_step(reach_cm=9000.0, stop_short_cm=2000.0)
    check("the step stops short of refused ground",
          plan["distance_cm"] == 2000.0 - move_plan.STOP_SHORT_MARGIN_CM)
    check("the refusal is named", plan["capped_by"] == "refused ground")
    check("the move still happens", plan["distance_cm"] > 0)


def test_no_room_is_a_refusal_to_shuffle():
    plan = move_plan.plan_step(reach_cm=340.0, standoff_cm=300.0)
    check("a wall inside the standoff yields no step at all",
          plan["distance_cm"] == 0.0)
    check("and says why", "no room to step" in plan["why"])


def test_hops_never_hand_the_engine_a_far_target():
    legs = move_plan.leg_distances(9000.0, _STEP_DISTANCE)
    check("a 90 m step becomes six hops", legs == [1500.0, 3000.0, 4500.0,
                                                   6000.0, 7500.0, 9000.0])
    check("no hop is longer than the fixed step — the distance SR47 proved safe",
          max(b - a for a, b in zip([0.0] + legs, legs)) <= _STEP_DISTANCE)
    check("the hops end exactly on the step", legs[-1] == 9000.0)
    check("a short step is one hop", move_plan.leg_distances(1500.0) == [1500.0])
    tail = move_plan.leg_distances(1600.0, _STEP_DISTANCE)
    check("a remainder too small to be its own hop is absorbed", tail == [1600.0])


# ── #88: a gap you cannot fit through is not a gap ───────────────────────────

def test_a_column_with_anything_in_it_is_not_a_gap():
    # SR49's sedan: 17 cm into far_right at body height, clear above it.
    sedan = {"fits": False,
             "open_columns": ["left", "centre", "right", "far_right"],
             "cells": [{"column": "far_left", "blocked": True},
                       {"column": "left", "blocked": False},
                       {"column": "centre", "blocked": False},
                       {"column": "right", "blocked": False},
                       {"column": "far_right", "blocked": True},
                       {"column": "far_right", "blocked": False}]}
    openings, silent = _open_columns(sedan)
    check("a column blocked at body height is not offered as a gap",
          "far_right" not in openings)
    check("the clear columns survive", openings == ["left", "centre", "right"])
    check("this is not the 'saw nothing' case", silent is False)


def test_a_sweep_that_hits_what_no_ray_hit_names_no_side():
    paint = {"fits": False,
             "open_columns": ["far_left", "left", "centre", "right", "far_right"],
             "cells": [{"column": c, "blocked": False}
                       for c in ("far_left", "left", "centre", "right", "far_right")]}
    openings, silent = _open_columns(paint)
    check("five invented gaps become none", openings == [])
    check("and the scan admits it saw nothing", silent is True)


def test_open_headings_are_compass_words_nearest_turn_first():
    tmp = tempfile.mkdtemp()
    bridge = _VolumeBridge(blocked={0.0: 30.0, 45.0: 30.0, 90.0: 30.0})
    mgr = make_manager(tmp, "headings", bridge)
    # Facing east: -45 is northeast, -90 is north.
    found = mgr._open_headings(_AgentStub(), obs_at(0.0, 0.0, yaw=0.0), 500.0)
    check("only the headings the body fits down are returned",
          [h["heading"] for h in found] == ["northeast", "north"])
    check("compass words, never body-relative ones (#59)",
          all(h["heading"] not in ("left", "forward-left") for h in found))
    check("the smallest turn comes first", found[0]["turn_deg"] < found[1]["turn_deg"])


def test_boxed_in_is_not_the_same_as_never_asked():
    never = _sense_note({"blocker": {"category": "prop", "distance_cm": 352.0,
                                     "fits": False, "clearance_cm": 352.0,
                                     "open_columns": []}})
    boxed = _sense_note({"blocker": {"category": "prop", "distance_cm": 352.0,
                                     "fits": False, "clearance_cm": 352.0,
                                     "open_columns": [], "open_headings": []}})
    check("never probed says nothing about the sides",
          "fits down none of them" not in never)
    check("boxed in says every heading was measured",
          "fits down none of them" in boxed)
    check("the two are different facts", never != boxed)

    found = _sense_note({"blocker": {"category": "prop", "distance_cm": 352.0,
                                     "fits": False, "clearance_cm": 352.0,
                                     "open_columns": [],
                                     "open_headings": [{"heading": "north",
                                                        "clearance_cm": 500.0,
                                                        "turn_deg": 90}]}})
    check("a way out is stated", "DOES fit these ways: north" in found)
    check("clearance is stated as a floor, not a measurement",
          "at least" in found)


# ── #89: not measured is never 'clear' ───────────────────────────────────────

def test_a_probe_that_could_not_answer_returns_none():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "silence", _Stub())          # no forward_volume
    check("no probe means not measured",
          mgr._look_along(_AgentStub(), obs_at(0.0, 0.0), 0.0, 9000.0) is None)

    mgr2 = make_manager(tmp, "silence2", _VolumeBridge())
    check("no facing means not measured",
          mgr2._look_along(_AgentStub(), {"location": {"x": 0, "y": 0, "z": 0}},
                           0.0, 9000.0) is None)
    check("a clear sweep returns the full distance asked",
          mgr2._look_along(_AgentStub(), obs_at(0.0, 0.0), 0.0, 9000.0) == 9000.0)


def test_the_plan_probes_as_far_as_it_means_to_walk():
    tmp = tempfile.mkdtemp()
    bridge = _VolumeBridge()
    mgr = make_manager(tmp, "reach", bridge)
    mgr._plan_move(_AgentStub(), obs_at(16500.0, 16500.0), "east", {})
    asked = bridge.calls[-1][0]
    check("the plan asks the engine for the whole step, not a fixed 5 m",
          asked == move_plan.MAX_STEP_CM)
    check("which is far more than the travel probe", asked > 500.0)


# ── #86: _scan_ahead, end to end from the shared map ─────────────────────────

def test_the_scan_finds_a_refused_patch_and_stops_short_of_it():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "scan")
    x, y = 16500.0, 16500.0
    # Somebody refused a 9 m patch 10 m due east of where we stand.
    mgr.place_db.refuse_patch("maren", x + 1000.0, y, "private yard", "Day 1, 09:00")

    scan = mgr._scan_ahead((x, y, 100.0), 0.0, move_plan.MAX_STEP_CM)   # east
    check("the scan finds the refusal", scan["stop_short_cm"] is not None)
    check("and names it", "private yard" in scan["stop_reason"])
    check("it stops short of the patch, not inside it",
          0 < scan["stop_short_cm"] < 1000.0)

    clear = mgr._scan_ahead((x, y, 100.0), 180.0, move_plan.MAX_STEP_CM)  # west
    check("a heading with nothing on it reports nothing",
          clear["stop_short_cm"] is None)


def test_the_scan_finds_a_refused_cell():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "scancell")
    x, y = 16500.0, 16500.0
    east = mgr.world_grid.locate(x + 3000.0, y)
    mgr.place_db.refuse_cell("dufus", east["col"], east["row"],
                             "standing corn wall to wall", "Day 1, 09:00")

    scan = mgr._scan_ahead((x, y, 100.0), 0.0, move_plan.MAX_STEP_CM)
    check("a refused cell stops the scan", scan["stop_short_cm"] is not None)
    check("and is named as a cell, not a patch",
          scan["stop_reason"] == "refused cell")


def test_only_ground_that_was_STOOD_on_counts_as_proven():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "proven")
    x, y = 16500.0, 16500.0
    bare = mgr._scan_ahead((x, y, 100.0), 0.0, 6000.0)
    check("ground nobody has walked is not proven", bare["open_run_cm"] == 0.0)

    for step in (1500.0, 4500.0):
        cell = mgr.world_grid.locate(x + step, y)
        mgr.place_db.record_ground("dufus", cell["col"], cell["row"], "pavement")
    here = mgr.world_grid.locate(x, y)
    mgr.place_db.record_ground("dufus", here["col"], here["row"], "pavement")
    walked = mgr._scan_ahead((x, y, 100.0), 0.0, 6000.0)
    check("ground somebody stood on is proven", walked["open_run_cm"] > 0.0)
    check("the run never exceeds the ground it scanned",
          walked["open_run_cm"] <= 6000.0)


# ── #55: the heading a direction word produced reaches the log ───────────────

def test_the_resolved_target_survives_the_action_copy():
    from agent_runtime.memory_store import movement_trace
    observation = {"location": {"x": 0.0, "y": 0.0, "z": 100.0},
                   "_resolved_target": [1500.0, 0.0, 100.0]}
    trace = movement_trace(observation, {"type": "walk_to", "direction": "east"})
    check("a direction walk logs what it actually aimed at",
          trace["move"]["target"] == [1500.0, 0.0])
    check("and the heading it produced", trace["move"]["heading"] == "E")


# ── #86: the walk plan's five exits ──────────────────────────────────────────

def _walking(tmp, name, blocked=None):
    bridge = _VolumeBridge(blocked)
    mgr = make_manager(tmp, name, bridge)
    mgr.bridge.get_character_state = lambda actor: {
        "location": {"x": mgr._test_xy[0], "y": mgr._test_xy[1], "z": 100.0}}
    mgr._test_xy = (0.0, 0.0)
    mgr._nearby_agent_ids = lambda agent_id, xyz: frozenset()
    mgr._open_walk_plan("dufus", obs_at(0.0, 0.0), "east",
                        move_plan.leg_distances(9000.0, _STEP_DISTANCE),
                        {"distance_cm": 9000.0})
    return mgr, _AgentStub()


def test_a_clean_plan_walks_every_hop_without_a_decision():
    tmp = tempfile.mkdtemp()
    mgr, agent = _walking(tmp, "clean")
    for hop in range(1, 7):
        mgr._test_xy = (1500.0 * hop, 0.0)
        mgr._pulse_walk(agent)
    check("the plan retires when the hops run out",
          "dufus" not in mgr._walk_plans)
    # The first hop is ordered by the normal action path; _pulse_walk owns the
    # rest, so the walked sequence starts at that first hop.
    hops = [_STEP_DISTANCE] + [o[0] for o in mgr.bridge.orders]
    check("the engine was never given a target beyond one hop",
          max(b - a for a, b in zip(hops, hops[1:])) <= _STEP_DISTANCE)
    check("five hops were ordered without a decision", len(mgr.bridge.orders) == 5)


def test_drifting_off_the_line_ends_the_plan():
    tmp = tempfile.mkdtemp()
    mgr, agent = _walking(tmp, "drift")
    mgr._test_xy = (1500.0, 900.0)                     # 9 m sideways
    mgr._pulse_walk(agent)
    check("the SR47 detour is caught after one hop",
          "dufus" not in mgr._walk_plans)
    check("and buys a cognition tick", "dufus" in mgr._force_next_decide)


def test_something_ahead_ends_the_plan():
    tmp = tempfile.mkdtemp()
    mgr, agent = _walking(tmp, "ahead", blocked={0.0: 100.0})
    mgr._test_xy = (1500.0, 0.0)
    mgr._pulse_walk(agent)
    check("a body that does not fit hands the tick back",
          "dufus" not in mgr._walk_plans)


def test_no_ground_made_ends_the_plan():
    tmp = tempfile.mkdtemp()
    mgr, agent = _walking(tmp, "wedge")
    for _ in range(4):
        mgr._test_xy = (200.0, 0.0)                    # never advances
        mgr._pulse_walk(agent)
    check("a wedge cannot hide inside the tick budget",
          "dufus" not in mgr._walk_plans)


def test_someone_arriving_ends_the_plan():
    tmp = tempfile.mkdtemp()
    mgr, agent = _walking(tmp, "company")
    mgr._walk_plans["dufus"]["nearby"] = frozenset()
    mgr._nearby_agent_ids = lambda agent_id, xyz: frozenset(["maren"])
    mgr._test_xy = (1500.0, 0.0)
    mgr._pulse_walk(agent)
    check("a plan never walks an APC past someone it should have noticed",
          "dufus" not in mgr._walk_plans)


def test_the_plan_has_a_ceiling():
    tmp = tempfile.mkdtemp()
    mgr, agent = _walking(tmp, "ceiling")
    mgr._walk_plans["dufus"]["ticks"] = 999
    mgr._pulse_walk(agent)
    check("no plan outlives its tick budget", "dufus" not in mgr._walk_plans)


# ── #86: the drift fact ──────────────────────────────────────────────────────

def test_a_walk_that_went_elsewhere_says_so():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "went")
    # Ordered north (yaw 270 => -y); the body ended up 48 m east. SR47's tick 2.
    mgr._last_order["dufus"] = {"intent": "north", "from": (0.0, 0.0),
                                "heading_yaw": 270.0, "plan": None}
    fact = mgr._last_move_fact("dufus", {"x": 4800.0, "y": 0.0, "z": 100.0})
    check("the achieved heading is stated", fact["went"]["heading"] == "east")
    check("and the size of the mistake is measured",
          fact["went"]["drift_deg"] > 45)

    note = _sense_note({"last_move": fact})
    check("the model is told it did not go where it was sent",
          "ended up east of where you started" in note)

    mgr._last_order["dufus"] = {"intent": "north", "from": (0.0, 0.0),
                                "heading_yaw": 270.0, "plan": None}
    straight = mgr._last_move_fact("dufus", {"x": 0.0, "y": -4800.0, "z": 100.0})
    check("a walk that went where it was sent says nothing",
          "went" not in straight)


if __name__ == "__main__":
    test_the_step_is_what_the_engine_measured()
    test_an_unmeasured_step_is_labelled_a_guess()
    test_the_model_may_only_ask_for_less()
    test_the_step_never_outruns_the_ground_it_described()
    test_a_refusal_shortens_the_step_but_never_cancels_it()
    test_no_room_is_a_refusal_to_shuffle()
    test_hops_never_hand_the_engine_a_far_target()
    test_a_column_with_anything_in_it_is_not_a_gap()
    test_a_sweep_that_hits_what_no_ray_hit_names_no_side()
    test_open_headings_are_compass_words_nearest_turn_first()
    test_boxed_in_is_not_the_same_as_never_asked()
    test_a_probe_that_could_not_answer_returns_none()
    test_the_plan_probes_as_far_as_it_means_to_walk()
    test_the_scan_finds_a_refused_patch_and_stops_short_of_it()
    test_the_scan_finds_a_refused_cell()
    test_only_ground_that_was_STOOD_on_counts_as_proven()
    test_the_resolved_target_survives_the_action_copy()
    test_a_clean_plan_walks_every_hop_without_a_decision()
    test_drifting_off_the_line_ends_the_plan()
    test_something_ahead_ends_the_plan()
    test_no_ground_made_ends_the_plan()
    test_someone_arriving_ends_the_plan()
    test_the_plan_has_a_ceiling()
    test_a_walk_that_went_elsewhere_says_so()
    print("All move plan tests passed.")
