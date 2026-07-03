"""Offline tests for APC-owned place cells (#11.2 minimal slice, WP4).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_owned_places.py

Covers:
  - PlaceDB.add_owned_place / find_owned_place / owned_places_in_cell:
    upsert per (col,row,owner,name), exact-beats-substring matching,
    preferred-owner tie-break.
  - AgentManager._resolve_place_target: community name wins; owned place
    resolves to community anchor (cell center) + stored XY offset.
  - AgentManager._record_place: a different name in an already community-named
    cell becomes an owned place (offset from the anchor) instead of being
    dropped; re-naming the same community name creates nothing.
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


def test_owned_place_crud():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")

        check("add writes", db.add_owned_place("maren", 5, 5, "My Home", dx=120.0, dy=-80.0))
        check("blank name rejected", not db.add_owned_place("maren", 5, 5, "   ", 0, 0))
        check("'null' name rejected", not db.add_owned_place("maren", 5, 5, "null", 0, 0))

        # Same owner+name upserts in place (no second row, offset refreshed).
        check("same owner+name upserts", db.add_owned_place("maren", 5, 5, "My Home", dx=10.0, dy=20.0))
        in_cell = db.owned_places_in_cell(5, 5)
        check("upsert kept one row", len(in_cell) == 1)
        check("upsert refreshed offset", in_cell[0]["dx"] == 10.0 and in_cell[0]["dy"] == 20.0)
        check("default extent is 3m", in_cell[0]["extent_cm"] == 300.0)

        # Two owners can hold the same name in the same cell.
        check("second owner, same name", db.add_owned_place("dufus", 5, 5, "My Home", dx=-50.0, dy=0.0))
        in_cell = db.owned_places_in_cell(5, 5)
        check("two owners coexist", len(in_cell) == 2)
        check("ordered by owner", [p["owner"] for p in in_cell] == ["dufus", "maren"])

        # all_owned_places: the whole owned map, deterministic order (#11.2).
        db.add_owned_place("maren", 2, 9, "Herb Garden", dx=0.0, dy=0.0)
        world = db.all_owned_places()
        check("all_owned_places lists every entry", len(world) == 3)
        check("all_owned_places ordered by cell then owner",
              [(p["col"], p["row"], p["owner"]) for p in world]
              == [(2, 9, "maren"), (5, 5, "dufus"), (5, 5, "maren")])
        check("all_owned_places carries offsets",
              all("dx" in p and "dy" in p and "extent_cm" in p for p in world))
        check("empty db -> no owned places",
              PlaceDB(Path(tmp) / "empty.db").all_owned_places() == [])


def test_find_owned_place():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.add_owned_place("maren", 5, 5, "The Vegetable Truck", dx=100.0, dy=0.0)
        db.add_owned_place("dufus", 7, 2, "My Home", dx=0.0, dy=50.0)
        db.add_owned_place("maren", 6, 6, "My Home", dx=30.0, dy=40.0)

        hit = db.find_owned_place("the vegetable truck")
        check("exact (normalized case)", hit and (hit["col"], hit["row"]) == (5, 5))
        hit = db.find_owned_place("vegetable")
        check("substring fallback", hit and hit["name"] == "The Vegetable Truck")
        check("unknown -> None", db.find_owned_place("atlantis") is None)
        check("empty -> None", db.find_owned_place("   ") is None)

        # preferred_owner wins a tie between equal-quality matches.
        hit = db.find_owned_place("my home", preferred_owner="maren")
        check("preferred owner wins tie", hit and hit["owner"] == "maren" and (hit["col"], hit["row"]) == (6, 6))
        hit = db.find_owned_place("my home", preferred_owner="dufus")
        check("other preferred owner wins tie", hit and hit["owner"] == "dufus")
        hit = db.find_owned_place("my home")
        check("no preference -> deterministic (col,row) order", hit and (hit["col"], hit["row"]) == (6, 6))

        # Exact beats substring even when the substring match is the preferred owner's.
        db.add_owned_place("dufus", 8, 8, "home", dx=0.0, dy=0.0)
        hit = db.find_owned_place("home", preferred_owner="maren")
        check("exact beats preferred substring", hit and hit["owner"] == "dufus" and hit["name"] == "home")


class StubBridge:
    def __init__(self):
        self.last = None

    def execute_action(self, actor_name, action):
        self.last = (actor_name, action)
        return {"status": "accepted", "action": action.get("type")}


def _manager(tmp, bridge=None):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=bridge or StubBridge(), memory_store=None)
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.world_grid = WorldGrid(cell_size=400.0,
                               bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    mgr.agents = {}
    return mgr


def test_resolver_order():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        obs = {"location": {"x": 1000.0, "y": -500.0, "z": 90.0}}
        # cell (5,5) is grid index (0,0) -> center (200, 200) for this bounds set.
        mgr.place_db.set_name("dufus", 5, 5, "village square", "T0")
        # An owned place sharing the community name, elsewhere — must NOT win.
        mgr.place_db.add_owned_place("maren", 6, 5, "village square", dx=50.0, dy=50.0)
        # An owned-only name in the community-named cell.
        mgr.place_db.add_owned_place("maren", 5, 5, "My Home", dx=120.0, dy=-80.0)

        target = mgr._resolve_place_target("maren", "village square", obs)
        check("community name beats owned shadow", target == [200.0, 200.0, 90.0])

        target = mgr._resolve_place_target("maren", "my home", obs)
        check("owned place -> anchor + offset", target == [320.0, 120.0, 90.0])
        check("z carried from current location", target[2] == 90.0)

        check("unknown still None", mgr._resolve_place_target("maren", "atlantis", obs) is None)


def test_record_place_owned_write_path():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        (Path(tmp) / "agents" / "maren").mkdir(parents=True)
        # Community-name cell (5,5) (center 200,200) first.
        mgr.place_db.set_name("dufus", 5, 5, "village square", "T0")

        # Maren, standing at (320, 120) in the same cell, names "My Home".
        mgr._record_place("maren", {"x": 320.0, "y": 120.0, "z": 90.0}, "My Home")
        owned = mgr.place_db.owned_places_in_cell(5, 5)
        check("different name became an owned place", len(owned) == 1 and owned[0]["name"] == "My Home")
        check("offset measured from the anchor", owned[0]["dx"] == 120.0 and owned[0]["dy"] == -80.0)
        check("community name untouched",
              mgr.place_db.get_place(5, 5)["name"] == "village square")

        # Re-naming the same community name must not create a shadow entry.
        mgr._record_place("maren", {"x": 200.0, "y": 200.0, "z": 90.0}, "Village Square")
        check("same community name creates nothing",
              len(mgr.place_db.owned_places_in_cell(5, 5)) == 1)

        # In an unnamed cell, behavior is unchanged: community name, no owned row.
        # (720, 200) is cell index (1,0) -> col 6, row 5.
        mgr._record_place("maren", {"x": 720.0, "y": 200.0, "z": 90.0}, "The Vegetable Truck")
        check("unnamed cell still takes the community name",
              mgr.place_db.get_place(6, 5)["name"] == "The Vegetable Truck")
        check("no owned row in a fresh cell", mgr.place_db.owned_places_in_cell(6, 5) == [])


def test_reset_clears_owned_places():
    # Owned places are keyed by grid (col,row) too, so a world reset (e.g. after
    # regridding to a new cell_size) must wipe them along with community cells —
    # otherwise stale 3 m boxes survive at grid coordinates that no longer mean
    # the same place.
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 5, 5, "Village Square", "T0")
        db.add_owned_place("maren", 5, 5, "My Home", dx=120.0, dy=-80.0)

        removed = db.reset()
        check("reset reports owned rows removed", removed["owned_place_cells"] == 1)
        check("named cells wiped", db.all_named_places() == [])
        check("owned cells wiped", db.all_owned_places() == [])


def main():
    test_owned_place_crud()
    test_find_owned_place()
    test_resolver_order()
    test_record_place_owned_write_path()
    test_reset_clears_owned_places()
    print("\nAll owned-place checks passed.")


if __name__ == "__main__":
    main()
