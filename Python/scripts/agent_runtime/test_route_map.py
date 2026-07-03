"""Offline tests for the APC top-down route map (#6b / WP5).

No Unreal, no network, no LLM. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_route_map.py

Sign-off (user, 2026-07-01): rendered IMAGE map; corridor +1 pad capped 15x15;
separate renderer over the shared PlaceDB; injected on travel ticks only.

Covers:
  - corridor(): pad, world-bounds clamp, from-anchored truncation, both orders.
  - build_route_map(): cell states from a temp PlaceDB, bearing/distance in
    known_places' conventions (UE: -Y is north), unbounded grid -> None.
  - render_map_image(): PNG written, geometry right, marker + state colors land
    on the expected pixels, same-cell A/B doesn't crash.
  - AgentManager.route_map_for(): destination via community name then owned
    place; unknown destination -> None; image written to observations/.
  - Travel-tick injection: _perceive_and_decide attaches route_map only when the
    schedule directive is travel; the prompt note renders facts + legend.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import llm_router, route_map          # noqa: E402
from agent_runtime.agent_manager import AgentManager     # noqa: E402
from agent_runtime.place_db import PlaceDB               # noqa: E402
from agent_runtime.world_grid import WorldGrid           # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


BOUNDS = {"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999}  # 10x10 cells


def _grid():
    return WorldGrid(cell_size=400.0, bounds=BOUNDS)


# ── corridor math ─────────────────────────────────────────────────────────────

def test_corridor():
    cols_r, rows_r, trunc = route_map.corridor((2, 5), (8, 5), 10, 10)
    check("corridor pads one cell each side", list(cols_r) == list(range(1, 10)))
    check("row corridor pads around the shared row", list(rows_r) == [4, 5, 6])
    check("small corridor is not truncated", trunc is False)

    cols_r, _, _ = route_map.corridor((0, 0), (3, 0), 10, 10)
    check("pad clamps at the world's edge", cols_r.start == 0)

    cols_r, _, trunc = route_map.corridor((0, 5), (30, 5), 40, 10)
    check("long corridor truncated", trunc is True)
    check("truncation caps the span", len(cols_r) == route_map.MAX_SPAN)
    check("truncated window anchors at the from end", 0 in cols_r)

    cols_r, _, trunc = route_map.corridor((30, 5), (0, 5), 40, 10)
    check("reverse truncation still contains the from cell", 30 in cols_r and trunc)
    check("reverse truncation caps the span", len(cols_r) == route_map.MAX_SPAN)


# ── facts ─────────────────────────────────────────────────────────────────────

def test_build_route_map_facts():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 8, 5, "village square", "T0")
        db.set_name("maren", 4, 5, "market", "T0")
        db.mark_swept("dufus", 6, 5, "T0")

        route = route_map.build_route_map(db, _grid(), (2, 5), (8, 5))
        check("route built on a bounded grid", route is not None)
        states = {tuple(c["cell"]): c["state"] for c in route["cells"]}
        check("destination cell is named", states[(8, 5)] == "named")
        check("swept cell reported", states[(6, 5)] == "swept")
        check("unknown cell is unexplored", states[(2, 5)] == "unexplored")
        check("from cell has no name", route["from"]["name"] is None)
        check("to carries the community name", route["to"]["name"] == "village square")
        check("due-east destination bears E", route["to"]["bearing"] == "E")
        check("distance is cell centers apart in m", route["to"]["distance_m"] == 24)
        check("corridor bounds reported", route["cols"] == [1, 9] and route["rows"] == [4, 6])
        check("not truncated", route["truncated"] is False)

        north = route_map.build_route_map(db, _grid(), (5, 5), (5, 2),
                                          destination_name="my home")
        check("-Y destination bears N (UE north)", north["to"]["bearing"] == "N")
        check("unnamed destination falls back to the requested name",
              north["to"]["name"] == "my home")

        same = route_map.build_route_map(db, _grid(), (8, 5), (8, 5))
        check("same-cell route has no bearing", same["to"]["bearing"] is None)
        check("same-cell route distance 0", same["to"]["distance_m"] == 0.0)

        check("unbounded grid -> None",
              route_map.build_route_map(db, WorldGrid(), (2, 5), (8, 5)) is None)


# ── image render ──────────────────────────────────────────────────────────────

def test_render_map_image():
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 8, 5, "village square", "T0")
        db.set_name("maren", 4, 5, "market", "T0")
        db.mark_swept("dufus", 6, 5, "T0")
        route = route_map.build_route_map(db, _grid(), (2, 5), (8, 5))

        out = route_map.render_map_image(route, Path(tmp) / "maps" / "route.png")
        check("image written (parent dir created)", out is not None and out.exists())

        img = Image.open(out)
        # corridor is 9x3 cells at 48px + col/row label gutters + a 20px legend strip
        ML, MT = route_map._MARGIN_L, route_map._MARGIN_T
        check("image geometry matches the corridor + gutters",
              img.size == (ML + 9 * 48, MT + 3 * 48 + 20))
        px = img.load()
        # Sample inside the marker disc but left of its white letter glyph.
        check("A marker (you) is blue at the from cell", px[ML + 64, MT + 72] == (32, 96, 208))
        check("B marker (destination) is red at the to cell", px[ML + 352, MT + 72] == (208, 48, 48))
        check("named cell filled green", px[ML + 168, MT + 72] == (168, 216, 168))
        check("swept cell filled tan", px[ML + 264, MT + 72] == (232, 216, 168))
        check("unexplored cell filled gray", px[ML + 24, MT + 24] == (212, 212, 212))
        # Grid cell layout labels: dark text pixels in the top and left gutters
        # (the font may anti-alias, so "dark", not exactly black).
        w, hh = img.size
        def _has_text(xs, ys):
            return any(sum(px[x, y][:3]) < 384 for y in ys for x in xs)
        check("column numbers drawn in the top gutter", _has_text(range(ML, w), range(MT)))
        check("row numbers drawn in the left gutter", _has_text(range(ML), range(MT, hh - 20)))

        same = route_map.build_route_map(db, _grid(), (8, 5), (8, 5))
        out2 = route_map.render_map_image(same, Path(tmp) / "maps" / "same.png")
        check("same-cell A/B renders without crashing", out2 is not None and out2.exists())


# ── manager wiring ────────────────────────────────────────────────────────────

class StubBridge:
    def print_to_screen(self, message, key=-1, duration=30.0):
        pass

    def set_ai_state(self, actor_name, state):
        return {"status": "accepted"}


class StubMemory:
    def get_relevant_memories(self, agent_id):
        return []


class StubLLM:
    """Captures what decide() was handed; returns no decision."""
    def __init__(self):
        self.observation = None

    def decide(self, agent, observation, memories):
        self.observation = observation
        return None


class StubAgent:
    def __init__(self, agent_id, blocks=None):
        self.agent_id = agent_id
        self.bound_unreal_actor_name = f"BP_{agent_id}"
        self.bound_unreal_actor_label = agent_id
        self.unreal_actor_name = agent_id
        self.has_unreal_binding = True
        self.is_active = True
        self.current_goal = "test goal"
        self.last_activity = None
        self.daily_schedule_day = "Day 1" if blocks is not None else None
        self.daily_schedule_blocks = blocks or []
        self.character_text = "A test character."
        self.goals_text = "Test goals."

    def set_daily_schedule(self, day, blocks, agents_dir=None):
        self.daily_schedule_day, self.daily_schedule_blocks = day, blocks

    def set_last_activity(self, activity, agents_dir=None):
        self.last_activity = activity

    def mark_ticked(self, agents_dir):
        pass


def _manager(tmp, llm=None):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=llm,
                       unreal_bridge=StubBridge(), memory_store=StubMemory())
    mgr._agents_dir = Path(tmp) / "agents"
    mgr._agents_dir.mkdir(parents=True, exist_ok=True)
    mgr.world_grid = _grid()
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    if llm is not None:
        mgr.llm = llm
    if mgr.memory is None:
        mgr.memory = StubMemory()
    return mgr


def _obs_at(mgr, x, y):
    return {"location": {"x": x, "y": y, "z": 90.0},
            "grid": mgr.world_grid.locate(x, y),
            "image_path": None, "place": [],
            "world_time": "Day 1, 09:00", "current_action": "idle"}


def test_route_map_for():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        agent_id = "dufus"
        mgr.agents = {agent_id: StubAgent(agent_id)}
        mgr.place_db.set_name("maren", 8, 5, "village square", "T0")
        mgr.place_db.add_owned_place("dufus", 3, 3, "My Home", dx=120.0, dy=-80.0)
        obs = _obs_at(mgr, 200.0, 200.0)   # cell (5,5)

        route = mgr.route_map_for(agent_id, "village square", obs)
        check("community destination resolves", route is not None)
        check("route from the agent's cell", route["from"]["cell"] == [5, 5])
        check("route to the named cell", route["to"]["cell"] == [8, 5])
        img = route.get("image_path")
        check("image written under the agent's observations",
              img is not None and Path(img).exists()
              and Path(img).parent.name == "observations")

        route = mgr.route_map_for(agent_id, "my home", obs)
        check("owned place resolves as destination",
              route is not None and route["to"]["cell"] == [3, 3])

        check("unknown destination -> None",
              mgr.route_map_for(agent_id, "atlantis", obs) is None)
        mgr.world_grid = WorldGrid()   # unbounded
        check("unbounded grid -> None",
              mgr.route_map_for(agent_id, "village square", obs) is None)


def test_travel_tick_injection():
    blocks = [{"start": "08:00", "end": "12:00",
               "activity": "tend the stall", "place": "village square"}]
    with tempfile.TemporaryDirectory() as tmp:
        llm = StubLLM()
        mgr = _manager(tmp, llm=llm)
        agent = StubAgent("dufus", blocks=blocks)
        mgr.agents = {"dufus": agent}
        mgr.place_db.set_name("maren", 8, 5, "village square", "T0")

        obs = _obs_at(mgr, 200.0, 200.0)   # cell (5,5), not at the square
        mgr._perceive_and_decide(agent, obs)
        seen = llm.observation
        check("decide() ran with the observation", seen is not None)
        check("directive is travel", (seen.get("schedule") or {}).get("status") == "travel")
        check("travel tick carries the route map", "route_map" in seen)
        check("route map image attached for the multimodal call",
              Path(seen["route_map"]["image_path"]).exists())

        # At the destination the directive is act — no map is built.
        llm2 = StubLLM()
        mgr2 = _manager(tmp, llm=llm2)
        agent2 = StubAgent("maren", blocks=blocks)
        mgr2.agents = {"maren": agent2}
        mgr2.place_db.set_name("maren", 8, 5, "village square", "T0")
        obs2 = _obs_at(mgr2, *mgr2.world_grid.cell_center(8, 5))
        obs2["place"] = ["village square"]
        mgr2._perceive_and_decide(agent2, obs2)
        seen2 = llm2.observation
        check("at-destination directive is act",
              (seen2.get("schedule") or {}).get("status") == "act")
        check("non-travel tick carries no map", "route_map" not in seen2)


def test_prompt_note():
    check("no route map -> empty note", llm_router._route_map_note({}) == "")
    route = {"to": {"name": "village square", "bearing": "E", "distance_m": 24},
             "cells": [{"cell": [8, 5], "state": "named", "name": "village square",
                        "landmarks": 3}],
             "image_path": "x/route_map.png", "truncated": False}
    note = llm_router._route_map_note({"route_map": route})
    check("note names the destination", '"village square"' in note)
    check("note carries bearing + distance", "E of you" in note and "24 m" in note)
    check("note explains the attached image legend",
          "A (blue) = you" in note and "B (red)" in note)
    check("note reports facts, not a route to follow", "you should" not in note.lower())

    del route["image_path"]
    note = llm_router._route_map_note({"route_map": route})
    check("no image -> no legend", "attached" not in note)

    check("template has the map slot", "{route_map_note}" in llm_router._USER_TEMPLATE_VISION)


def main():
    test_corridor()
    test_build_route_map_facts()
    test_render_map_image()
    test_route_map_for()
    test_travel_tick_injection()
    test_prompt_note()
    print("\nAll route-map checks passed.")


if __name__ == "__main__":
    main()
