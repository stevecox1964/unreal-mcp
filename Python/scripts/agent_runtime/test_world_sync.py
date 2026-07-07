"""Offline tests for the "I moved things — sync the world" button (WP7 / #21 v1).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_world_sync.py

When the user rearranges actors in the editor, wake-seeded owned places go
stale and send agents hunting old spots. The sync purges exactly the
``source='wake-seed'`` rows (authored rows are ground truth, runtime rows are
agent memories — both survive) and reports what was deleted; the next run
re-seeds at the new day-start positions. Covers ``PlaceDB.purge_wake_seeds``,
``POST /api/world/sync``, and the /map button.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient          # noqa: E402
from agent_runtime.place_db import PlaceDB          # noqa: E402
import web_ui.main as wm                            # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _seed(db: PlaceDB) -> None:
    db.add_owned_place("maren", 6, 6, "the vegetable truck", dx=50.0, dy=10.0,
                       source="wake-seed")
    db.add_owned_place("dufus", 5, 5, "home", dx=0.0, dy=0.0, source="authored")
    db.add_owned_place("maren", 1, 1, "favorite bench", dx=10.0, dy=10.0)  # runtime


# ── data layer: PlaceDB.purge_wake_seeds ───────────────────────────────────────

def test_purge_deletes_only_wake_seeds():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        _seed(db)

        deleted = db.purge_wake_seeds()
        check("purge returns the deleted rows",
              deleted == [{"col": 6, "row": 6, "owner": "maren",
                           "name": "the vegetable truck", "dx": 50.0, "dy": 10.0}])
        survivors = {(o["name"], ) for o in db.all_owned_places()}
        check("authored + runtime rows survive",
              survivors == {("home",), ("favorite bench",)})
        check("second purge returns []", db.purge_wake_seeds() == [])


# ── web layer: POST /api/world/sync + the /map button ──────────────────────────

def _world(tmp: str, level: str = "TestWorld", with_db: bool = True) -> Path:
    world = Path(tmp) / level
    (world / "agents").mkdir(parents=True)
    (world / "world_grid.json").write_text(json.dumps({
        "cell_size": 400.0,
        "bounds": {"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999},
    }), encoding="utf-8")
    if with_db:
        _seed(PlaceDB(world / "world_places.db"))
    return world


def _with_worlds(tmp, fn):
    old = wm.WORLDS_DIR
    wm.WORLDS_DIR = Path(tmp)
    try:
        fn(TestClient(wm.app))
    finally:
        wm.WORLDS_DIR = old


def test_sync_route_purges_and_reports():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp)

        def body(client):
            data = client.post("/api/world/sync?level=TestWorld").json()
            check("sync reports the level", data["level"] == "TestWorld")
            check("sync lists exactly the wake-seed row",
                  data["deleted"] == [{"owner": "maren", "name": "the vegetable truck",
                                       "col": 6, "row": 6}])
            check("sync counts it", data["count"] == 1)
            db = PlaceDB(world / "world_places.db")
            check("DB reflects the purge (authored + runtime survive)",
                  {o["name"] for o in db.all_owned_places()} == {"home", "favorite bench"})
            again = client.post("/api/world/sync?level=TestWorld").json()
            check("nothing to sync is an honest count 0",
                  again["count"] == 0 and again["deleted"] == [])
        _with_worlds(tmp, body)


def test_sync_missing_db_creates_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp, level="Barren", with_db=False)

        def body(client):
            data = client.post("/api/world/sync?level=Barren").json()
            check("missing DB -> count 0, deleted []",
                  data == {"level": "Barren", "deleted": [], "count": 0})
            check("no DB file was created by a sync",
                  not (world / "world_places.db").exists())
        _with_worlds(tmp, body)


def test_map_page_has_sync_button():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            text = client.get("/map?level=TestWorld").text
            check("map page has the Sync world button",
                  'id="sync-btn"' in text and "Sync world" in text)
            check("button posts to /api/world/sync", "/api/world/sync" in text)
        _with_worlds(tmp, body)


def main():
    test_purge_deletes_only_wake_seeds()
    test_sync_route_purges_and_reports()
    test_sync_missing_db_creates_nothing()
    test_map_page_has_sync_button()
    print("\nAll world-sync checks passed.")


if __name__ == "__main__":
    main()
