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


def main():
    test_is_explored_and_mark_swept()
    test_swept_migration_on_existing_db()
    print("\nAll cell-sweep (PlaceDB) checks passed.")


if __name__ == "__main__":
    main()
