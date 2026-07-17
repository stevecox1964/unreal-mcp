"""Offline tests for the fixed world grid and per-tick grid/place reporting.

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_world_grid.py
"""
from __future__ import annotations

import json
import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager   # noqa: E402
from agent_runtime.spatial_memory import SpatialMap    # noqa: E402
from agent_runtime.world_grid import WorldGrid         # noqa: E402
from agent_runtime.place_db import PlaceDB             # noqa: E402
from agent_runtime.agent import Agent                  # noqa: E402
from agent_runtime import interruptions                # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_grid_math():
    g = WorldGrid()  # unbounded default
    loc = g.locate(50, -50)
    check("unbounded grid still has a key", loc["key"] == "0,-1")
    check("unbounded grid has no col/row", "col" not in loc)

    g = WorldGrid(cell_size=400.0, bounds={"min_x": -2000, "min_y": -800, "max_x": 1999, "max_y": 799})
    loc = g.locate(-2000, -800)
    check("min corner is col 0, row 0", (loc["col"], loc["row"]) == (0, 0))
    check("grid dims fixed by world size", (loc["cols"], loc["rows"]) == (10, 4))
    loc = g.locate(1999, 799)
    check("max corner is last cell", (loc["col"], loc["row"]) == (9, 3))
    check("max corner in bounds", loc["in_bounds"])
    loc = g.locate(5000, 0)
    check("outside world flagged", not loc["in_bounds"])

    smap = SpatialMap(cell_size=400.0)
    check("grid keys align with spatial map cells",
          g.locate(-777, 123)["key"] == smap.cell_key(-777, 123))

    # origin(): cell (0,0)'s min corner, generally outside bounds (#6c overlay).
    check("unbounded grid has no origin", WorldGrid().origin() is None)
    check("aligned bounds -> origin at the min corner", g.origin() == (-2000.0, -800.0))
    mcp = WorldGrid(cell_size=3000.0, bounds={"min_x": -24600.0, "min_y": -15158.6,
                                              "max_x": 22400.0, "max_y": 15700.0})
    check("unaligned bounds -> origin floored outside them",
          mcp.origin() == (-27000.0, -18000.0))
    check("origin is cell (0,0)",
          mcp.locate(-26999.0, -17999.0)["col"] == 0 and mcp.locate(-26999.0, -17999.0)["row"] == 0)


def test_place_labels():
    smap = SpatialMap(cell_size=400.0)
    key = smap.ingest(100, 100, [
        {"label": "red barn", "confidence": 0.9, "distance": "near"},
        {"label": "water tower", "confidence": 0.4, "distance": "far"},
    ])
    smap.ingest(100, 100, [{"label": "red barn", "confidence": 0.9, "distance": "near"}])
    labels = smap.place_labels(key)
    check("place labels ranked by count x confidence", labels[0] == "red barn")
    check("unknown cell gives empty place", smap.place_labels("99,99") == [])


def test_configurable_logical_origin():
    bounds = {"min_x": -24600.0, "min_y": -15158.6,
              "max_x": 22400.0, "max_y": 15700.0}
    grid = WorldGrid(cell_size=3000.0, bounds=bounds,
                     origin_x=-1000.0, origin_y=500.0)
    check("configured origin shifts the visible lattice",
          grid.origin() == (-25000.0, -17500.0))
    samples = [(-24600.0, -15158.6), (-9445.9, -2429.3),
               (-1.0, -1.0), (22400.0, 15700.0)]
    for x, y in samples:
        located = grid.locate(x, y)
        center = grid.cell_center(located["col"], located["row"])
        round_trip = grid.locate(*center)
        check(f"offset round trip at ({x},{y})",
              (round_trip["col"], round_trip["row"])
              == (located["col"], located["row"]))

    smap = SpatialMap(cell_size=3000.0, origin_x=-1000.0, origin_y=500.0)
    check("offset grid keys still align with spatial memory",
          grid.locate(-9445.9, -2429.3)["key"] == smap.cell_key(-9445.9, -2429.3))

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "world_grid.json"
        path.write_text(json.dumps({"cell_size": 3000.0, "bounds": bounds,
                                    "origin_x": -1000.0, "origin_y": 500.0}),
                        encoding="utf-8")
        loaded = WorldGrid.load(path)
        check("logical origin loads from world_grid.json",
              (loaded.origin_x, loaded.origin_y) == (-1000.0, 500.0))


class StubBridge:
    """Live-mode stub: location moves, scene never changes (diff gate closed)."""
    def __init__(self):
        self.loc = {"x": 100.0, "y": 200.0, "z": 90.0}

    def get_observation(self, name, agent_id, agents_dir):
        return {"actor_name": name, "image_path": None, "location": dict(self.loc),
                "current_action": "idle", "ai_state": None}

    def is_scene_changed(self, agent_id, image_path):
        return False

    def print_to_screen(self, message, key=-1, duration=30.0):
        pass  # PIE overlay is a no-op under test

    def set_ai_state(self, actor_name, state):
        return {"status": "accepted"}  # activity bubble is a no-op under test


class StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.bound_unreal_actor_name = f"BP_{agent_id}"
        self.bound_unreal_actor_label = agent_id
        self.unreal_actor_name = agent_id
        self.has_unreal_binding = True
        self.is_active = True
        self.is_busy = False

    def cooldown_expired(self):
        return True

    def mark_ticked(self, agents_dir):
        pass


def test_grid_reported_without_perception():
    """Even when the diff gate skips the LLM, the tick reports grid + place."""
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp) / "agents"
        (agents_dir / "testy").mkdir(parents=True)
        bridge = StubBridge()
        mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                           unreal_bridge=bridge, memory_store=None)
        mgr._agents_dir = agents_dir
        mgr.world_grid = WorldGrid(cell_size=400.0,
                                   bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})
        agent = StubAgent("testy")
        mgr.agents = {"testy": agent}

        # Seed the agent's spatial map so the current cell has a known place.
        smap = mgr._spatial_map("testy")
        smap.ingest(100, 200, [{"label": "pawn shop", "confidence": 0.9, "distance": "near"}])

        check("skipped LLM (scene unchanged)", mgr._observe_agent(agent) is None)
        grid1, place1 = mgr._last_grid_place["testy"]
        check("grid reported anyway", grid1["key"] == "0,0")
        check("grid has fixed col/row", (grid1["col"], grid1["row"]) == (5, 5))
        check("place reported anyway", place1 == ["pawn shop"])

        # Avatar moves a cell over — grid follows position, place is unknown there.
        bridge.loc = {"x": 500.0, "y": 200.0, "z": 90.0}
        check("moved unchanged view still skips LLM", mgr._observe_agent(agent) is None)
        grid2, place2 = mgr._last_grid_place["testy"]
        check("grid tracks movement without new sights", grid2["key"] == "1,0")
        check("unmapped cell has unknown place", place2 == [])


def test_regrid_clears_grid_keyed_state():
    with tempfile.TemporaryDirectory() as tmp:
        worlds = Path(tmp)
        world = worlds / "TestWorld"
        agents = world / "agents"
        (agents / "dufus" / "observations").mkdir(parents=True)
        (agents / "dufus" / "spatial_map.json").write_text("{}", encoding="utf-8")
        (agents / "dufus" / "observations" / "route_map.png").write_bytes(b"old")
        grid_path = world / "world_grid.json"
        grid_path.write_text(json.dumps({
            "cell_size": 3000.0,
            "bounds": {"min_x": -9000, "min_y": -6000, "max_x": 3000, "max_y": 6000},
            "image_bounds": {"min_x": -9500, "min_y": -6500,
                             "max_x": 3500, "max_y": 6500},
        }), encoding="utf-8")
        db = PlaceDB(world / "world_places.db")
        db.set_name("dufus", 1, 1, "old square", "T0")
        image_path = world / "places" / "images" / "old.png"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"old image")
        db.record_place_image(
            "dufus", 1, 1, "places/images/old.png",
            {"N": "n.png", "S": "s.png", "E": "e.png", "W": "w.png"},
        )

        mgr = AgentManager(worlds_dir=worlds, llm_router=None,
                           unreal_bridge=None, memory_store=None)
        mgr._agents_dir = agents
        mgr.place_db = db
        mgr.world_grid = WorldGrid.load(grid_path)
        mgr._routes["dufus"] = {"destination": "old square"}
        agent = Agent("dufus", {}, "", "", "", [])
        agent.offer_interrupt(interruptions.make_record(
            interrupt_id="survey:1,1", kind="survey", source="world",
            reason="old grid", priority=100, requested_at="T0",
            payload={"col": 1, "row": 1}, resume_context={}, preemptible=False,
        ), agents, activated_at="T0")
        mgr.agents = {"dufus": agent}
        mgr._cell_sweeps["dufus"] = {"execution_only": True}
        result = asyncio.run(mgr.regrid_world("TestWorld", -1000.0, 500.0))

        check("regrid transaction succeeds", result["status"] == "regridded")
        check("regrid persists the configured logical origin",
              (WorldGrid.load(grid_path).origin_x, WorldGrid.load(grid_path).origin_y)
              == (-1000.0, 500.0))
        check("regrid preserves image calibration",
              WorldGrid.load(grid_path).image_bounds is not None)
        check("regrid clears PlaceDB cells and place images",
              db.map_cells() == [] and not image_path.exists())
        check("regrid deletes spatial and rendered route maps",
              not (agents / "dufus" / "spatial_map.json").exists()
              and not (agents / "dufus" / "observations" / "route_map.png").exists())
        check("regrid clears cached routes", mgr._routes == {})
        check("regrid cancels persisted survey interruption",
              agent.active_interrupt is None and agent.last_interrupt["status"] == "cancelled")
        check("regrid clears local sweep execution", mgr._cell_sweeps == {})


def main():
    test_grid_math()
    test_place_labels()
    test_configurable_logical_origin()
    test_grid_reported_without_perception()
    test_regrid_clears_grid_keyed_state()
    print("\nAll world-grid checks passed.")


if __name__ == "__main__":
    main()
