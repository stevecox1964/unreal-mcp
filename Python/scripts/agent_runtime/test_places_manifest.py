"""Offline tests for the authored places manifest (WP6 / #15).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_places_manifest.py

places.json is the world's root configuration: canonical places loaded into
PlaceDB at sim start, before any tick. Priority: authored > discovered >
wake-seeded. Covers:
  - load_manifest: missing/bad file tolerance, per-entry fail-loud skips,
    D1 defaulting (community iff no owner; extent 900; actor preserved).
  - apply_manifest: derived (col,row)+dx/dy, declarative convergence on
    re-apply (moves + deletes), runtime rows untouched, unbounded grid no-op.
  - Authored-wins community naming (runtime name overwritten, sweep survives).
  - Resolution: an authored place satisfies _at_scheduled_place and the wake
    seed never fires.
  - _validate_schedule: unauthored places warned + returned, once per day.
  - source tagging: wake-seed / runtime / authored + column migration.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import places_manifest                # noqa: E402
from agent_runtime.agent_manager import AgentManager     # noqa: E402
from agent_runtime.place_db import PLACE_EXTENT_CM, PlaceDB  # noqa: E402
from agent_runtime.world_grid import WorldGrid           # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# cell (5,5) covers x,y in [0,400): center (200,200) — same grid as test_wake_place.
GRID = WorldGrid(cell_size=400.0,
                 bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})


def _write(tmp, payload) -> Path:
    p = Path(tmp) / "places.json"
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload),
                 encoding="utf-8")
    return p


def _sources(db_path, table="owned_place_cells"):
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(f"SELECT name, source FROM {table} WHERE name IS NOT NULL").fetchall()
    finally:
        conn.close()


# ── load_manifest ──────────────────────────────────────────────────────────────

def test_load_manifest():
    with tempfile.TemporaryDirectory() as tmp:
        check("missing file -> []",
              places_manifest.load_manifest(Path(tmp) / "places.json") == [])
        check("bad JSON -> [] (no raise)",
              places_manifest.load_manifest(_write(tmp, "{nope")) == [])
        check("non-list places -> []",
              places_manifest.load_manifest(_write(tmp, {"places": "x"})) == [])

        entries = places_manifest.load_manifest(_write(tmp, {"places": [
            {"name": "the vegetable truck", "x": 320.0, "y": 120.0, "owner": "maren"},
            {"name": "  ", "x": 0, "y": 0},                       # blank name — skipped
            {"name": "bad coords", "x": "east", "y": 0},          # non-numeric — skipped
            {"name": "village square", "x": -800.0, "y": 900.0},
            {"name": "dufus's home", "x": 100.0, "y": 100.0, "owner": "dufus",
             "community": True, "extent_cm": 1200.0, "actor": "BP_House_3"},
        ]}))
        check("bad entries skipped, good survive", len(entries) == 3)
        truck, square, home = entries
        check("owned entry defaults community=False",
              truck["owner"] == "maren" and truck["community"] is False)
        check("ownerless entry defaults community=True",
              square["owner"] is None and square["community"] is True)
        check("extent defaults to 900", truck["extent_cm"] == PLACE_EXTENT_CM == 900.0)
        check("explicit extent + community + actor preserved",
              home["extent_cm"] == 1200.0 and home["community"] is True
              and home["actor"] == "BP_House_3")


# ── apply_manifest ─────────────────────────────────────────────────────────────

def test_apply_owned_and_community():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        summary = places_manifest.apply_manifest(db, GRID, [
            {"name": "the vegetable truck", "x": 320.0, "y": 120.0, "owner": "maren",
             "community": False, "extent_cm": 900.0, "actor": None},
            {"name": "village square", "x": -800.0, "y": 900.0, "owner": None,
             "community": True, "extent_cm": 900.0, "actor": None},
        ])
        check("summary counts", summary == {"applied": 2, "owned": 1,
                                            "community": 1, "skipped": 0})

        owned = db.find_owned_place("the vegetable truck")
        check("owned row at derived cell", owned["col"] == 5 and owned["row"] == 5)
        center = GRID.cell_center(5, 5)
        check("cell_center + (dx,dy) == authored (x,y)",
              (center[0] + owned["dx"], center[1] + owned["dy"]) == (320.0, 120.0))

        check("community entry names its cell",
              db.find_named_cell("village square") == (3, 7))
        rows = _sources(Path(tmp) / "world_places.db", "place_cells")
        check("community name tagged authored", rows == [("village square", "authored")])
        rows = _sources(Path(tmp) / "world_places.db")
        check("owned row tagged authored", rows == [("the vegetable truck", "authored")])


def test_reapply_converges():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        # A runtime discovery that must survive every re-apply.
        db.add_owned_place("maren", 1, 1, "favorite bench", dx=10.0, dy=10.0)
        truck = {"name": "the vegetable truck", "x": 320.0, "y": 120.0, "owner": "maren",
                 "community": False, "extent_cm": 900.0, "actor": None}
        home = {"name": "dufus's home", "x": -1500.0, "y": -1500.0, "owner": "dufus",
                "community": False, "extent_cm": 900.0, "actor": None}
        places_manifest.apply_manifest(db, GRID, [truck, home])

        # The user moves the truck (edit x/y) and deletes dufus's home.
        moved = dict(truck, x=-800.0, y=900.0)
        places_manifest.apply_manifest(db, GRID, [moved])

        owned = db.all_owned_places()
        authored = [o for o in owned if o["name"] == "the vegetable truck"]
        check("moved entry re-anchors, no duplicate rows",
              len(authored) == 1 and (authored[0]["col"], authored[0]["row"]) == (3, 7))
        check("removed entry's row is gone after re-apply",
              db.find_owned_place("dufus's home") is None)
        check("runtime row untouched by the authored clear",
              db.find_owned_place("favorite bench") is not None)


def test_apply_guards():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        entry = {"name": "x", "x": 0.0, "y": 0.0, "owner": "maren",
                 "community": False, "extent_cm": 900.0, "actor": None}
        summary = places_manifest.apply_manifest(db, WorldGrid(cell_size=400.0), [entry])
        check("unbounded grid -> applied 0, nothing written",
              summary["applied"] == 0 and db.all_owned_places() == [])

        far = dict(entry, name="off the map", x=99999.0)
        summary = places_manifest.apply_manifest(db, GRID, [far])
        check("out-of-bounds entry skipped",
              summary == {"applied": 0, "owned": 0, "community": 0, "skipped": 1})

        # Two authored entries claiming the same cell: first in file wins.
        a = {"name": "market square", "x": 100.0, "y": 100.0, "owner": None,
             "community": True, "extent_cm": 900.0, "actor": None}
        b = dict(a, name="fish market", x=150.0)
        places_manifest.apply_manifest(db, GRID, [a, b])
        check("same-cell authored conflict: first in file wins",
              db.find_named_cell("market square") == (5, 5)
              and db.find_named_cell("fish market") is None)


def test_authored_wins_over_runtime_name():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.mark_swept("dufus", 5, 5, "T0")                    # sweep data on the row
        db.set_name("dufus", 5, 5, "motel", "T1")             # runtime name
        places_manifest.apply_manifest(db, GRID, [
            {"name": "market square", "x": 100.0, "y": 100.0, "owner": None,
             "community": True, "extent_cm": 900.0, "actor": None},
        ])
        check("authored community name overwrites the runtime name",
              db.find_named_cell("market square") == (5, 5)
              and db.find_named_cell("motel") is None)
        swept = db.get_swept(5, 5)
        check("runtime sweep data survives the overwrite",
              swept is not None and swept["swept_by"] == "dufus")


# ── resolution: authored place satisfies the schedule, wake seed stays quiet ──

class StubBridge:
    def execute_action(self, actor_name, action):
        return {"status": "accepted", "action": action.get("type")}


def _manager(tmp):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=StubBridge(), memory_store=None)
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.world_grid = GRID
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    mgr.agents = {}
    return mgr


BLOCK = {"start": "08:00", "end": "12:00",
         "activity": "tend the stall", "place": "the vegetable truck"}


def test_authored_place_resolves_no_wake_seed():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        places_manifest.apply_manifest(mgr.place_db, mgr.world_grid, [
            {"name": "the vegetable truck", "x": 320.0, "y": 120.0, "owner": "maren",
             "community": False, "extent_cm": 900.0, "actor": None},
        ])
        obs = {"location": {"x": 320.0, "y": 120.0, "z": 90.0},
               "grid": mgr.world_grid.locate(320.0, 120.0)}
        at = mgr._at_scheduled_place("maren", BLOCK, obs, seed_if_unknown=True)
        check("standing in the authored truck box -> True", at is True)
        rows = _sources(Path(tmp) / "world_places.db")
        check("no wake seed fired (authored row is the only one)",
              rows == [("the vegetable truck", "authored")])


# ── _validate_schedule (D5) ────────────────────────────────────────────────────

class StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id


def test_validate_schedule():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        mgr.place_db.add_owned_place("maren", 5, 5, "the vegetable truck",
                                     dx=120.0, dy=-80.0, source="authored")
        schedule = [dict(BLOCK),
                    {"start": "12:00", "end": "13:00",
                     "activity": "eat lunch", "place": "Don's Donuts"},
                    {"start": "13:00", "end": "14:00", "activity": "rest"}]
        bad = mgr._validate_schedule(StubAgent("maren"), schedule, "Day 1")
        check("unresolvable place is returned as a bad block",
              len(bad) == 1 and bad[0]["place"] == "Don's Donuts")
        check("second call same day is cached -> []",
              mgr._validate_schedule(StubAgent("maren"), schedule, "Day 1") == [])
        check("a new day re-validates",
              len(mgr._validate_schedule(StubAgent("maren"), schedule, "Day 2")) == 1)
        check("run reset re-arms validation",
              (mgr._validated_plans.clear(),
               mgr._validate_schedule(StubAgent("maren"), schedule, "Day 1"))[1] != [])


# ── source tagging + migration (D2) ────────────────────────────────────────────

def test_source_tagging():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        obs = {"location": {"x": 320.0, "y": 120.0, "z": 90.0},
               "grid": mgr.world_grid.locate(320.0, 120.0)}
        mgr._at_scheduled_place("maren", BLOCK, obs, seed_if_unknown=True)
        mgr.place_db.add_owned_place("maren", 5, 5, "discovered corner", dx=0.0, dy=0.0)
        rows = dict(_sources(Path(tmp) / "world_places.db"))
        check("wake seed writes source='wake-seed'",
              rows["the vegetable truck"] == "wake-seed")
        check("add_owned_place defaults to source='runtime'",
              rows["discovered corner"] == "runtime")


def test_migration_adds_source_column():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "world_places.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE place_cells (
                col INTEGER NOT NULL, row INTEGER NOT NULL, name TEXT,
                named_at TEXT, named_by TEXT, swept_at TEXT, swept_by TEXT,
                updated_at TEXT, PRIMARY KEY (col, row));
            CREATE TABLE owned_place_cells (
                col INTEGER NOT NULL, row INTEGER NOT NULL,
                owner TEXT NOT NULL, name TEXT NOT NULL,
                dx REAL NOT NULL DEFAULT 0, dy REAL NOT NULL DEFAULT 0,
                extent_cm REAL NOT NULL DEFAULT 900,
                created_at TEXT, updated_at TEXT,
                PRIMARY KEY (col, row, owner, name));
            INSERT INTO owned_place_cells (col, row, owner, name) VALUES (1, 1, 'maren', 'old row');
        """)
        conn.commit()
        conn.close()

        db = PlaceDB(db_path)   # reopening migrates
        conn = sqlite3.connect(str(db_path))
        try:
            place_cols = {r[1] for r in conn.execute("PRAGMA table_info(place_cells)")}
            owned_cols = {r[1] for r in conn.execute("PRAGMA table_info(owned_place_cells)")}
            legacy = conn.execute(
                "SELECT source FROM owned_place_cells WHERE name='old row'").fetchone()[0]
        finally:
            conn.close()
        check("migration adds source to place_cells", "source" in place_cols)
        check("migration adds source to owned_place_cells", "source" in owned_cols)
        check("legacy owned rows default to 'runtime'", legacy == "runtime")
        check("migrated DB still answers queries",
              db.find_owned_place("old row") is not None)


def main():
    test_load_manifest()
    test_apply_owned_and_community()
    test_reapply_converges()
    test_apply_guards()
    test_authored_wins_over_runtime_name()
    test_authored_place_resolves_no_wake_seed()
    test_validate_schedule()
    test_source_tagging()
    test_migration_adds_source_column()
    print("\nAll places-manifest checks passed.")


if __name__ == "__main__":
    main()
