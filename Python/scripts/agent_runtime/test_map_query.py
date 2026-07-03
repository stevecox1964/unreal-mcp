"""Offline tests for the map query surface (backlog #6).

"What places do I know?" — the named-place map an agent can consult before
asking for a route. No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_map_query.py

Covers PlaceDB.all_named_places and AgentManager.known_places (name + bearing +
distance from the agent's current location).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager   # noqa: E402
from agent_runtime.place_db import PlaceDB              # noqa: E402
from agent_runtime.world_grid import WorldGrid          # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_all_named_places():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 3, 4, "Village Square", "T0")
        db.set_name("dufus", 7, 2, "Don's Donuts", "T0")
        # An unnamed cell that only has visits must not appear on the map.
        db.touch("dufus", 9, 9)

        places = db.all_named_places()
        names = sorted(p["name"] for p in places)
        check("only named cells are on the map", names == ["Don's Donuts", "Village Square"])
        sq = next(p for p in places if p["name"] == "Village Square")
        check("place carries its cell", (sq["col"], sq["row"]) == (3, 4))
        check("empty world -> empty map", PlaceDB(Path(tmp) / "empty.db").all_named_places() == [])


def _manager(tmp):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=None, memory_store=None)
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.world_grid = WorldGrid(cell_size=400.0,
                               bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    return mgr


def test_known_places_bearing_and_distance():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        # cell (5,5) center is (200,200); cell (10,5) center is (2200,200) — due East (+X).
        mgr.place_db.set_name("dufus", 10, 5, "east market", "T0")
        # cell (5,10) center is (200,2200) — due South (+Y in UE).
        mgr.place_db.set_name("dufus", 5, 10, "south gate", "T0")

        # Agent standing at cell (5,5) center.
        places = mgr.known_places({"x": 200.0, "y": 200.0, "z": 90.0})
        by_name = {p["name"]: p for p in places}
        check("both named places returned", set(by_name) == {"east market", "south gate"})
        check("due +X reads as East", by_name["east market"]["bearing"] == "E")
        check("due +Y reads as South", by_name["south gate"]["bearing"] == "S")
        check("distance in meters (2000cm -> 20m)", round(by_name["east market"]["distance_m"]) == 20)
        check("places sorted nearest first", places[0]["distance_m"] <= places[-1]["distance_m"])

        check("no location -> empty map", mgr.known_places(None) == [])


def test_known_places_includes_owned_places():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        mgr.place_db.set_name("dufus", 10, 5, "east market", "T0")
        # Owned place in cell (10,5): anchor (2200,200) + offset (-200,0) = (2000,200)
        # — 1800 cm due East of the agent at (200,200).
        mgr.place_db.add_owned_place("maren", 10, 5, "My Stall", dx=-200.0, dy=0.0)

        places = mgr.known_places({"x": 200.0, "y": 200.0, "z": 90.0})
        by_name = {p["name"]: p for p in places}
        check("owned place appears on the map", "My Stall" in by_name)
        stall = by_name["My Stall"]
        check("owned place carries its owner", stall["owner"] == "maren")
        check("owned distance uses anchor + offset (1800cm -> 18m)",
              round(stall["distance_m"]) == 18)
        check("owned bearing from the offset position", stall["bearing"] == "E")
        check("community entries carry no owner", "owner" not in by_name["east market"])
        check("merged list still sorted nearest first",
              [p["distance_m"] for p in places] == sorted(p["distance_m"] for p in places))


def main():
    test_all_named_places()
    test_known_places_bearing_and_distance()
    test_known_places_includes_owned_places()
    print("\nAll map-query checks passed.")


if __name__ == "__main__":
    main()
