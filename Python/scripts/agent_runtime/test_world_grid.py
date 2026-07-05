"""Offline tests for the fixed world grid and per-tick grid/place reporting.

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_world_grid.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager   # noqa: E402
from agent_runtime.spatial_memory import SpatialMap    # noqa: E402
from agent_runtime.world_grid import WorldGrid         # noqa: E402


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


async def test_grid_reported_without_perception():
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

        r1 = mgr.pulse_agent("testy")
        r1 = await r1
        check("skipped LLM (scene unchanged)", r1["reason"] == "scene_unchanged")
        check("grid reported anyway", r1["grid"]["key"] == "0,0")
        check("grid has fixed col/row", (r1["grid"]["col"], r1["grid"]["row"]) == (5, 5))
        check("place reported anyway", r1["place"] == ["pawn shop"])

        # Avatar moves a cell over — grid follows position, place is unknown there.
        bridge.loc = {"x": 500.0, "y": 200.0, "z": 90.0}
        r2 = await mgr.pulse_agent("testy")
        check("grid tracks movement without new sights", r2["grid"]["key"] == "1,0")
        check("unmapped cell has unknown place", r2["place"] == [])


def main():
    import asyncio
    test_grid_math()
    test_place_labels()
    asyncio.run(test_grid_reported_without_perception())
    print("\nAll world-grid checks passed.")


if __name__ == "__main__":
    main()
