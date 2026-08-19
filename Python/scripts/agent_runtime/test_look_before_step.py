"""Offline tests for look-before-step (#77), sub-cell no-go patches (#78) and
the bounce fact (#26 slice).

SR42's north trap: every path north from the (5,5)/(6,5) road led into a
pergola yard, a trash alley, or a mobile-home bedroom. Dufus stepped in and
retreated five times, because bad ground could only be discovered by standing
on it, and because refusing ground meant refusing a whole 30 m cell that still
needed surveying. These tests pin the three fixes: the eyes' verdict per
direction, the 9 m patch refusal, and the stated bounce count.

Fully offline (no LLM, no Unreal, temp DB). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_look_before_step.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager  # noqa: E402
from agent_runtime.place_db import PLACE_EXTENT_CM, PlaceDB  # noqa: E402
from agent_runtime.world_grid import WorldGrid  # noqa: E402
from agent_runtime.llm_router import (  # noqa: E402
    _direction_lines, _seen_text, _sense_note,
)


class _Stub:
    """Stands in for any collaborator these paths never really call."""
    def __getattr__(self, _):
        return lambda *a, **k: None


class _AgentStub:
    def __init__(self, agent_id="dufus"):
        self.agent_id = agent_id


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def make_manager(tmp, name):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=_Stub(),
                       unreal_bridge=_Stub(), memory_store=_Stub())
    mgr.place_db = PlaceDB(Path(tmp) / f"{name}.db")
    mgr.world_grid = WorldGrid(
        cell_size=3000.0,
        bounds={"min_x": 0.0, "min_y": 0.0,
                "max_x": 16 * 3000.0, "max_y": 11 * 3000.0},
    )
    return mgr


def obs_at(mgr, x, y):
    return {"location": {"x": x, "y": y, "z": 100.0},
            "grid": mgr.world_grid.locate(x, y),
            "world_time": "Day 1, 09:00"}


# ── #78: the patch store ─────────────────────────────────────────────────────

def test_patch_store():
    tmp = tempfile.mkdtemp()
    db = PlaceDB(Path(tmp) / "patches.db")
    check("empty reason is rejected",
          db.refuse_patch("dufus", 0.0, 0.0, "  ", "Day 1") is False)
    check("a stated patch is stored",
          db.refuse_patch("dufus", 1000.0, 2000.0, "private backyard", "Day 1"))
    hit = db.patches_at(1000.0 + PLACE_EXTENT_CM / 2 - 1, 2000.0)
    check("a point inside the radius hits", len(hit) == 1)
    check("the reason travels with the hit", hit[0]["reason"] == "private backyard")
    check("a point outside the radius misses",
          db.patches_at(1000.0 + PLACE_EXTENT_CM, 2000.0) == [])

    # Re-refusing inside an own patch updates it instead of stacking.
    db.refuse_patch("dufus", 1100.0, 2000.0, "pergola yard", "Day 1")
    check("own overlapping refusal updates, not stacks", len(db.all_patches()) == 1)
    check("the later look wins",
          db.patches_at(1000.0, 2000.0)[0]["reason"] == "pergola yard")

    # Another APC's patch on the same ground is its own row.
    db.refuse_patch("maren", 1000.0, 2000.0, "not my ground", "Day 1")
    check("two APCs may refuse the same ground", len(db.all_patches()) == 2)

    check("withdrawing clears only your own",
          db.clear_patches_at("dufus", 1000.0, 2000.0) == 1)
    remaining = db.all_patches()
    check("the other APC's patch survives",
          len(remaining) == 1 and remaining[0]["refused_by"] == "maren")

    counts = db.reset()
    check("reset clears patches too", counts.get("no_go_patches") == 1
          and db.all_patches() == [])


# ── #78: the verdict path (scope "spot") ─────────────────────────────────────

def test_spot_verdict_writes_a_patch_one_step_away():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "verdict")
    agent = _AgentStub()
    obs = obs_at(mgr, 16500.0, 16500.0)   # center of cell (5,5)

    action = {"type": "refuse_cell", "direction": "north",
              "scope": "spot", "reason": "someone's backyard"}
    result = mgr._apply_cell_verdict(agent, action, obs)
    check("a spot verdict resolves to idle", result["type"] == "idle")
    # North is -y in UE; one step is ~15 m.
    check("the patch sits one step north",
          len(mgr.place_db.patches_at(16500.0, 16500.0 - 1500.0)) == 1)
    check("the cell itself is NOT refused",
          mgr.place_db.get_refusals(5, 5) == [])
    grid_north = mgr.world_grid.locate(16500.0, 16500.0 - 1500.0)
    check("the stepped-into cell is NOT refused either",
          mgr.place_db.get_refusals(grid_north["col"], grid_north["row"]) == [])

    # The direction sense now carries the patch, on north only.
    directions = mgr._direction_places("dufus", obs["location"])
    check("north carries the no-go patch", len(directions["north"]["no_go"]) == 1)
    check("east stays clear", directions["east"]["no_go"] == [])

    # allow_cell with scope spot withdraws it.
    mgr._apply_cell_verdict(agent, {"type": "allow_cell", "direction": "north",
                                    "scope": "spot"}, obs)
    check("allow scope spot withdraws the patch",
          mgr.place_db.patches_at(16500.0, 16500.0 - 1500.0) == [])


def test_whole_cell_refusal_unchanged():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "wholecell")
    obs = obs_at(mgr, 16500.0, 16500.0)
    mgr._apply_cell_verdict(_AgentStub(), {"type": "refuse_cell",
                                           "reason": "standing corn"}, obs)
    check("no scope still refuses the whole cell",
          mgr.place_db.get_refusals(5, 5) != [])
    check("no patch was written", mgr.place_db.all_patches() == [])


# ── #77: the eyes cache ──────────────────────────────────────────────────────

def test_eyes_reach_the_direction_lines():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "eyes")
    loc = {"x": 16500.0, "y": 16500.0, "z": 100.0}

    # A north-facing look (UE yaw 270) that saw grass and a dead end.
    mgr._note_eyes("dufus", loc, 270.0,
                   {"ground_ahead": "grass", "path_ahead": "dead_end"})
    directions = mgr._direction_places("dufus", loc)
    seen = directions["north"].get("seen_ahead")
    check("the north look is filed under north",
          seen == {"ground_ahead": "grass", "path_ahead": "dead_end"})
    check("unlooked directions carry no eyes",
          "seen_ahead" not in directions["east"])

    # An errored perception and an empty one file nothing.
    mgr._note_eyes("dufus", loc, 0.0, {"error": "boom", "ground_ahead": "road"})
    mgr._note_eyes("dufus", loc, 0.0, {"caption": "nice view"})
    check("errors and empty reports are not eyes",
          "seen_ahead" not in mgr._direction_places("dufus", loc)["east"])

    # Looks are about one spot: 15 m away they say nothing.
    moved = {"x": 16500.0, "y": 15000.0, "z": 100.0}
    check("eyes go stale on displacement",
          "seen_ahead" not in mgr._direction_places("dufus", moved)["north"])

    lines = _direction_lines(directions)
    check("the prompt line carries the eyes' verdict",
          "your own eyes saw: grass ahead, the way ahead DEAD-ENDS" in lines)
    check("the prompt line carries no-go only when present", "NO-GO" not in lines)


def test_no_go_renders_on_the_direction_line():
    lines = _direction_lines({
        "north": {"cell": "5,4", "place": None, "ground": [], "refusals": [],
                  "no_go": [{"refused_by": "dufus", "reason": "trash alley"}]},
    })
    check("the patch is stated with its reason",
          "NO-GO ground one step that way (refused by dufus: trash alley)" in lines)


def test_seen_text_states_the_ground_ahead():
    text = _seen_text({"caption": "A yard.", "footing": "pavement",
                       "ground_ahead": "grass", "path_ahead": "dead_end"})
    check("ground ahead is stated",
          "GROUND AHEAD (where a step this way lands): grass" in text)
    check("a closed path is stated", "PATH AHEAD: dead end" in text)
    open_text = _seen_text({"caption": "Road.", "footing": "road",
                            "ground_ahead": "road", "path_ahead": "open"})
    check("an open path needs no warning line", "PATH AHEAD" not in open_text)


# ── #26 slice: the bounce fact ───────────────────────────────────────────────

def test_bounce_is_counted_and_stated():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, "bounce")
    road = mgr.world_grid.locate(16500.0, 16500.0)     # (5,5)
    yard = mgr.world_grid.locate(16500.0, 13500.0)     # (5,4), one cell north

    # In (N, ends in the yard) then straight back out (S) — twice. The strict
    # alternation also credits the via cell once (the S->N re-entry pair);
    # the >=2 threshold keeps the stated fact on the real trap.
    for _ in range(2):
        mgr._drop_crumb("dufus", yard, "N", 1500.0)
        mgr._drop_crumb("dufus", road, "S", 1500.0)
    check("the entered-and-abandoned cell counts per in-and-out",
          mgr._bounces["dufus"]["5,4"] == 2)
    check("the via cell stays under the stating threshold",
          mgr._bounces["dufus"].get("5,5", 0) < 2)

    # A normal onward leg is not a bounce.
    mgr._drop_crumb("dufus", mgr.world_grid.locate(19500.0, 16500.0), "E", 1500.0)
    check("walking on does not count", mgr._bounces["dufus"]["5,4"] == 2)

    note = _sense_note({"bounce": [{"cell": "5,4", "count": 2}]})
    check("the bounce is stated to the model",
          "walked into cell 5,4 and straight back out 2 times" in note)
    check("the stated escape is the spot refusal", "scope" in note)


if __name__ == "__main__":
    test_patch_store()
    test_spot_verdict_writes_a_patch_one_step_away()
    test_whole_cell_refusal_unchanged()
    test_eyes_reach_the_direction_lines()
    test_no_go_renders_on_the_direction_line()
    test_seen_text_states_the_ground_ahead()
    test_bounce_is_counted_and_stated()
    print("All look-before-step tests passed.")
