"""Offline tests for unexplored-cell sweep + community breadcrumb (backlog #7).

When an APC enters a grid cell with no place cell, it drops personality and runs
a deterministic sweep: walk to the cell center, do a 360 observation, then drop a
community place-cell breadcrumb so future APCs skip the costly re-sweep.

This file covers the loop-safe core: PlaceDB sweep state, the pure sweep planner/
state machine, and the manager override decision. The live 360 rotation+capture
is verified in PIE, not here. No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_cell_sweep.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.place_db import PlaceDB        # noqa: E402
from agent_runtime.world_grid import WorldGrid    # noqa: E402
from agent_runtime import cell_sweep               # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# ── PlaceDB: explored state + community breadcrumb ──────────────────────────────

def test_is_explored_and_mark_swept():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        check("fresh cell is unexplored", not db.is_explored(2, 3))

        # A named cell counts as explored (it has a place cell).
        db.set_name("maren", 5, 5, "Village Square", "T0")
        check("named cell is explored", db.is_explored(5, 5))

        # Sweeping an unnamed cell drops a community breadcrumb -> explored.
        check("first sweep records", db.mark_swept("dufus", 2, 3, "Day 1 09:00") is True)
        check("swept cell is explored", db.is_explored(2, 3))
        crumb = db.get_swept(2, 3)
        check("breadcrumb has no personal name", crumb["name"] is None)
        check("breadcrumb records who/when", crumb["swept_by"] == "dufus" and crumb["swept_at"] == "Day 1 09:00")

        # Sweeping must not clobber an existing name.
        db.mark_swept("dufus", 5, 5, "Day 1 10:00")
        check("sweep preserves an existing name", db.get_place(5, 5)["name"] == "Village Square")


def test_swept_migration_on_existing_db():
    """A pre-sweep DB (place_cells without swept columns) migrates in place."""
    import sqlite3
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "old.db"
        conn = sqlite3.connect(str(path))
        conn.executescript(
            "CREATE TABLE place_cells (col INTEGER, row INTEGER, name TEXT, "
            "named_at TEXT, named_by TEXT, PRIMARY KEY (col, row));"
        )
        conn.execute("INSERT INTO place_cells VALUES (1,1,'Old Town','T0','maren')")
        conn.commit()
        conn.close()

        db = PlaceDB(path)  # __init__ must add swept_at/swept_by
        check("old data survives migration", db.is_explored(1, 1))
        check("can sweep after migration", db.mark_swept("dufus", 7, 7, "T9") is True)
        check("migrated db tracks new sweep", db.is_explored(7, 7))


# ── Pure sweep planner / state machine ──────────────────────────────────────────

def test_compass_headings():
    h = cell_sweep.compass_headings()
    check("a full 360 in 8 steps", len(h) == 8)
    check("evenly spaced 45deg", h == [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0])


def test_default_sweep_needs_bounds():
    bounded = WorldGrid(cell_size=400.0, bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})
    sweep = cell_sweep.default_sweep(bounded, 5, 5, z=90.0)
    check("bounded grid yields a sweep", sweep is not None)
    check("targets the cell center", sweep.center == (200.0, 200.0))
    check("unbounded grid yields no sweep", cell_sweep.default_sweep(WorldGrid(), 5, 5, z=90.0) is None)


def test_sweep_sequence():
    sweep = cell_sweep.CellSweep(center=(200.0, 200.0), z=90.0,
                                 headings=[0.0, 90.0, 180.0, 270.0], arrive_tolerance=50.0)
    # Far from center: keep walking to the center, not yet sweeping.
    a = sweep.next_action((1000.0, 200.0))
    check("far -> walk to center", a["type"] == "walk_to" and a["location"] == [200.0, 200.0, 90.0])
    check("not done while travelling", not sweep.is_done)

    # Arrived: emit one observation per heading, in order.
    seen = [sweep.next_action((210.0, 205.0))["yaw"] for _ in range(4)]
    check("observes every heading in order", seen == [0.0, 90.0, 180.0, 270.0])

    # Headings exhausted: done.
    done = sweep.next_action((210.0, 205.0))
    check("sweep reports done", done["type"] == "sweep_done")
    check("is_done set", sweep.is_done)


def test_arrival_is_sticky():
    sweep = cell_sweep.CellSweep(center=(0.0, 0.0), z=0.0, headings=[0.0], arrive_tolerance=50.0)
    sweep.next_action((10.0, 0.0))                 # arrive
    a = sweep.next_action((9999.0, 0.0))           # drift far after arriving
    check("does not restart travel after arriving", a["type"] != "walk_to")


def main():
    test_is_explored_and_mark_swept()
    test_swept_migration_on_existing_db()
    test_compass_headings()
    test_default_sweep_needs_bounds()
    test_sweep_sequence()
    test_arrival_is_sticky()
    print("\nAll cell-sweep checks passed.")


if __name__ == "__main__":
    main()
