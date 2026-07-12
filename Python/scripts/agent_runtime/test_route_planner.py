"""Offline tests for grid-first routing (#17 / WP8).

No Unreal, no network, no LLM. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_route_planner.py

A far destination becomes a plan: straight-line grid-cell legs, each a short
navmesh walk, ending with a fine-approach that stops at the owned box's edge
(B7b-style). The LLM contract (walk_to target_location "<place>") is
unchanged; the manager executes it leg by leg. Covers:
  - route_planner.line_cells: pinned Bresenham outputs.
  - next_waypoint: leg advance with skip-ahead, off-path keeps the leg,
    community arrival = in the cell, owned arrival = box-edge standoff.
  - Executor: the bridge receives leg waypoints (not the final anchor),
    stuck/destination-change replans, arrival idles + pops the route,
    unknown/unbounded fallbacks.
  - Prompt/map: schedule["route"] narration + the route-map path overlay.
"""
from __future__ import annotations

import sys
import tempfile
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import llm_router, route_map, route_planner  # noqa: E402
from agent_runtime.agent_manager import AgentManager            # noqa: E402
from agent_runtime.place_db import PlaceDB                      # noqa: E402
from agent_runtime.world_grid import WorldGrid                  # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# 10x10 cells; cell (5,5) covers x,y in [0,400): center (200,200).
GRID = WorldGrid(cell_size=400.0,
                 bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})


# ── line_cells ────────────────────────────────────────────────────────────────

def test_line_cells():
    check("horizontal line",
          route_planner.line_cells((0, 0), (3, 0)) == [(0, 0), (1, 0), (2, 0), (3, 0)])
    check("vertical line",
          route_planner.line_cells((0, 0), (0, 3)) == [(0, 0), (0, 1), (0, 2), (0, 3)])
    check("perfect diagonal steps diagonally",
          route_planner.line_cells((0, 0), (3, 3)) == [(0, 0), (1, 1), (2, 2), (3, 3)])
    check("2:1 slope (pinned Bresenham)",
          route_planner.line_cells((0, 0), (4, 2))
          == [(0, 0), (1, 1), (2, 1), (3, 2), (4, 2)])
    check("same cell -> single-cell path", route_planner.line_cells((5, 5), (5, 5)) == [(5, 5)])
    check("reversed horizontal is the reverse",
          route_planner.line_cells((3, 0), (0, 0))
          == list(reversed(route_planner.line_cells((0, 0), (3, 0)))))
    check("reversed diagonal is the reverse",
          route_planner.line_cells((3, 3), (0, 0))
          == list(reversed(route_planner.line_cells((0, 0), (3, 3)))))


# ── next_waypoint ─────────────────────────────────────────────────────────────

def test_next_waypoint_legs():
    dest_center = GRID.cell_center(8, 5)   # (1400, 200)
    route = route_planner.make_route((5, 5), (8, 5), dest_center, 0.0, "village square")
    check("path is the cell line",
          route["path"] == [(5, 5), (6, 5), (7, 5), (8, 5)] and route["leg"] == 1)

    wp = route_planner.next_waypoint(route, (5, 5), (200.0, 200.0), GRID)
    check("leg 1 walks the next cell's center",
          wp == {"x": 600.0, "y": 200.0, "final": False, "leg": 1, "total": 3,
                 "cell": (6, 5)})

    # The engine crossed two cells between ticks: entering (7,5) skips leg 2.
    wp = route_planner.next_waypoint(route, (7, 5), (1000.0, 200.0), GRID)
    check("skip-ahead consumes passed legs",
          wp["leg"] == 3 and wp["cell"] == (8, 5) and route["leg"] == 3)

    # Off the path (avoidance detour): the leg holds, the waypoint pulls back.
    wp = route_planner.next_waypoint(route, (7, 6), (1000.0, 600.0), GRID)
    check("off-path keeps the current leg", wp["leg"] == 3 and wp["cell"] == (8, 5))

    # Community destination: standing in the cell IS arrival.
    check("community arrival -> None",
          route_planner.next_waypoint(route, (8, 5), (1400.0, 200.0), GRID) is None)


def test_next_waypoint_owned_standoff():
    # Owned box: anchor (320, 120) in cell (5,5), 9x9 m -> half = 450 cm.
    route = route_planner.make_route((5, 5), (5, 5), (320.0, 120.0), 900.0, "truck")
    check("same-cell route is immediately final", len(route["path"]) == 1)

    wp = route_planner.next_waypoint(route, (5, 5), (1000.0, 120.0), GRID)
    check("fine-approach stops at the box edge (not the anchor)",
          wp is not None and wp["final"] is True
          and wp["x"] == 770.0 and wp["y"] == 120.0)
    check("stop point is exactly extent/2 from the anchor",
          abs(abs(wp["x"] - 320.0) - 450.0) < 1e-9)
    check("inside the box -> None (arrived)",
          route_planner.next_waypoint(route, (5, 5), (600.0, 120.0), GRID) is None)


# ── executor ──────────────────────────────────────────────────────────────────

class StubBridge:
    def __init__(self):
        self.calls = []

    def execute_action(self, actor_name, action):
        self.calls.append((actor_name, action))
        return {"status": "accepted", "action": action.get("type")}


class StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.display_name = agent_id.title()
        self.bound_unreal_actor_name = f"BP_{agent_id}"


def _manager(tmp):
    bridge = StubBridge()
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=bridge, memory_store=None)
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.world_grid = GRID
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    mgr.agents = {}
    return mgr, bridge


def _obs(x, y, stuck=False):
    return {"location": {"x": x, "y": y, "z": 90.0},
            "grid": GRID.locate(x, y), "stuck": stuck}


WALK = {"type": "walk_to", "target_location": "the vegetable truck"}


def test_executor_walks_legs():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, bridge = _manager(tmp)
        maren = StubAgent("maren")
        # Anchor (1520, 120) in cell (8,5) — three cells east of the agent.
        # extent 200 (not the 900 default): this test grid's 4 m cells are
        # smaller than the 9 m box, which would make the whole destination
        # cell "inside the box" and skip the fine-approach branch.
        mgr.place_db.add_owned_place("maren", 8, 5, "the vegetable truck",
                                     dx=120.0, dy=-80.0, extent_cm=200.0)

        result = mgr._execute_world_action(maren, dict(WALK), _obs(200.0, 200.0))
        sent = bridge.calls[-1][1]
        check("bridge got the LEG waypoint, not the final anchor",
              sent["location"] == [600.0, 200.0, 90.0])
        check("result note narrates the leg", result.get("note") == "leg 1/3 -> cell (6, 5)")
        check("route cached for the agent", "maren" in mgr._routes)

        # Two cells later (skip-ahead), the walk targets the destination cell.
        mgr._execute_world_action(maren, dict(WALK), _obs(1000.0, 200.0))
        sent = bridge.calls[-1][1]
        check("mid-path tick walks the following leg",
              sent["location"] == [1400.0, 200.0, 90.0])

        # In the destination cell but outside the box: box-edge fine-approach.
        mgr._execute_world_action(maren, dict(WALK), _obs(1200.0, 120.0))
        sent = bridge.calls[-1][1]
        check("final approach stops at the box edge",
              sent["location"] == [1520.0 - 100.0, 120.0, 90.0])

        # Inside the box: no walk issued, route popped, honest arrival note.
        n_calls = len(bridge.calls)
        result = mgr._execute_world_action(maren, dict(WALK), _obs(1470.0, 120.0))
        check("arrival idles instead of re-walking",
              result["action"] == "idle" and "arrived" in result["note"])
        check("no bridge walk on arrival", len(bridge.calls) == n_calls)
        check("route popped on arrival", "maren" not in mgr._routes)


def test_executor_replans():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, bridge = _manager(tmp)
        maren = StubAgent("maren")
        mgr.place_db.add_owned_place("maren", 8, 5, "the vegetable truck",
                                     dx=120.0, dy=-80.0)
        mgr.place_db.set_name("dufus", 5, 8, "village square", "T0")

        mgr._execute_world_action(maren, dict(WALK), _obs(200.0, 200.0))
        first = mgr._routes["maren"]

        # Stuck drops the plan; a fresh line is planned from the current cell.
        mgr._execute_world_action(maren, dict(WALK), _obs(600.0, 200.0, stuck=True))
        second = mgr._routes["maren"]
        check("stuck replans from where the agent really is",
              second is not first and second["path"][0] == (6, 5))

        # A different destination re-plans too.
        mgr._execute_world_action(
            maren, {"type": "walk_to", "target_location": "village square"},
            _obs(600.0, 200.0))
        check("destination change re-plans",
              mgr._routes["maren"]["destination"] == "village square"
              and mgr._routes["maren"]["path"][-1] == (5, 8))


def test_executor_fallbacks():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, bridge = _manager(tmp)
        maren = StubAgent("maren")
        mgr.place_db.add_owned_place("maren", 8, 5, "the vegetable truck",
                                     dx=120.0, dy=-80.0)

        # Unknown name: action passes through unchanged (bridge's graceful idle).
        mgr._execute_world_action(
            maren, {"type": "walk_to", "target_location": "atlantis"}, _obs(200.0, 200.0))
        sent = bridge.calls[-1][1]
        check("unknown place passes through unchanged",
              "location" not in sent and sent["target_location"] == "atlantis")
        check("no route cached for an unknown place", "maren" not in mgr._routes)

        # Unbounded grid: no cell centers exist, so the endpoint itself is
        # unresolvable — the action passes through (today's behavior) and no
        # route is cached.
        mgr.world_grid = WorldGrid(cell_size=400.0)
        mgr._execute_world_action(maren, dict(WALK), _obs(200.0, 200.0))
        sent = bridge.calls[-1][1]
        check("unbounded grid passes through, nothing routed",
              "location" not in sent and "maren" not in mgr._routes)


def test_at_place_wander_stays_inside_place():
    """SR11 regression: Dufus may roam the square, but not leave its cell."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr, _ = _manager(tmp)
        dufus = StubAgent("dufus")
        mgr.place_db.set_name("dufus", 5, 5, "village square", "T0")
        obs = _obs(390.0, 200.0)
        obs["rotation"] = {"x": 0.0, "y": 0.0, "z": 0.0}
        obs["schedule"] = {"status": "act", "place": "village square"}

        bounded = mgr._bound_at_place_movement(dufus, {"type": "wander"}, obs)
        target = bounded.get("location")
        target_cell = GRID.locate(target[0], target[1])
        check("wander becomes a deterministic bounded walk", bounded["type"] == "walk_to")
        check("bounded wander remains in scheduled cell",
              (target_cell["col"], target_cell["row"]) == (5, 5))
        check("boundary wander turns back into the place", target[0] < 390.0)


def test_nearby_apcs_and_perception_evidence():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, _ = _manager(tmp)
        mgr.agents = {"dufus": StubAgent("dufus"), "maren": StubAgent("maren")}
        mgr._live_pos = {
            "dufus": {"x": 0.0, "y": 0.0, "yaw": 0.0},
            "maren": {"x": 1500.0, "y": 0.0, "yaw": 0.0},
        }
        observations = {
            "dufus": {"location": {"x": 0.0, "y": 0.0, "z": 90.0}},
            "maren": {"location": {"x": 1500.0, "y": 0.0, "z": 90.0}},
        }
        mgr._attach_nearby_characters(observations)
        check("nearby APC survives a vision miss",
              observations["maren"]["nearby_characters"]
              == [{"name": "Dufus", "distance_cm": 1500.0}])

        agent_dir = Path(tmp) / "agents" / "maren"
        agent_dir.mkdir(parents=True)
        mgr._save_perception_evidence("maren", {"world_time": "Day 1, 08:15",
                                                "image_path": "frame.png"},
                                      {"model": "haiku", "caption": "street",
                                       "landmarks": [], "characters": []})
        saved = json.loads((agent_dir / "last_perception.json").read_text(encoding="utf-8"))
        check("latest structured vision result is inspectable",
              saved["world_time"] == "Day 1, 08:15" and saved["characters"] == [])


# ── prompt + map surface ──────────────────────────────────────────────────────

def test_schedule_route_narration():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, _ = _manager(tmp)
        mgr.place_db.add_owned_place("maren", 8, 5, "the vegetable truck",
                                     dx=120.0, dy=-80.0)
        maren = StubAgent("maren")
        mgr._execute_world_action(maren, dict(WALK), _obs(200.0, 200.0))

        obs = _obs(200.0, 200.0)
        obs["schedule"] = {"status": "travel", "place": "the vegetable truck"}
        mgr._attach_route_progress("maren", obs)
        r = obs["schedule"].get("route")
        check("travel directive carries the route narration",
              r == {"leg": 1, "total": 3, "to_cell": [6, 5], "heading": "E"})

        note = llm_router._schedule_note(obs["schedule"])
        check("prompt narrates the leg",
              "en route: leg 1 of 3" in note and "heading E" in note
              and "cell (6, 5)" in note)
        check("walk_to contract unchanged",
              'target_location "the vegetable truck"' in note)

        # A route for a different place attaches nothing.
        obs2 = _obs(200.0, 200.0)
        obs2["schedule"] = {"status": "travel", "place": "village square"}
        mgr._attach_route_progress("maren", obs2)
        check("mismatched destination attaches nothing",
              "route" not in obs2["schedule"])
        check("note renders without a route",
              "en route" not in llm_router._schedule_note(obs2["schedule"]))


def test_route_map_path_overlay():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 8, 5, "village square", "T0")
        path = route_planner.line_cells((5, 5), (8, 5))

        route = route_map.build_route_map(db, GRID, (5, 5), (8, 5), path=path)
        check("facts carry the planned path",
              route["path"] == [[5, 5], [6, 5], [7, 5], [8, 5]])
        out = route_map.render_map_image(route, Path(tmp) / "route.png")
        check("path overlay renders", out is not None and out.exists())

        from PIL import Image
        img = Image.open(out)
        # Intermediate path cell (6,5): corridor cols [4,9], rows [4,6] ->
        # local (2,1); dot center at margins + 2.5/1.5 cells.
        x = route_map._MARGIN_L + 2 * 48 + 24
        y = route_map._MARGIN_T + 1 * 48 + 24
        check("route dot drawn on an intermediate path cell",
              img.load()[x, y] == (32, 96, 208))

        no_path = route_map.build_route_map(db, GRID, (5, 5), (8, 5))
        check("no path -> no path key", "path" not in no_path)


def main():
    test_line_cells()
    test_next_waypoint_legs()
    test_next_waypoint_owned_standoff()
    test_executor_walks_legs()
    test_executor_replans()
    test_executor_fallbacks()
    test_at_place_wander_stays_inside_place()
    test_nearby_apcs_and_perception_evidence()
    test_schedule_route_narration()
    test_route_map_path_overlay()
    print("\nAll route-planner checks passed.")


if __name__ == "__main__":
    main()
