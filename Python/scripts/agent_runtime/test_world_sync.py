"""Offline tests for the "I moved things — sync the world" button
(WP7 / #21 v1, upgraded by #23 to also rescan landmarks).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_world_sync.py

When the user rearranges actors in the editor, wake-seeded owned places go
stale and send agents hunting old spots. The sync purges exactly the
``source='wake-seed'`` rows (authored rows are ground truth, runtime rows are
agent memories — both survive) and reports what was deleted; the next run
re-seeds at the new day-start positions. #23 folds a landmark rescan into the
same button: ``unreal_client.get_actors()`` -> ``Landmark_*`` actors -> merged
with places.json -> re-applied, so a moved/renamed landmark converges
immediately (the #21 v2 re-anchor). Covers ``PlaceDB.purge_wake_seeds``,
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

def _world(tmp: str, level: str = "TestWorld", with_db: bool = True,
          places: list = None) -> Path:
    world = Path(tmp) / level
    (world / "agents").mkdir(parents=True)
    (world / "world_grid.json").write_text(json.dumps({
        "cell_size": 400.0,
        "bounds": {"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999},
    }), encoding="utf-8")
    if places is not None:
        (world / "places.json").write_text(json.dumps({"places": places}), encoding="utf-8")
    if with_db:
        _seed(PlaceDB(world / "world_places.db"))
    return world


def _with_worlds(tmp, fn, actors=None):
    """Patch WORLDS_DIR + stub unreal_client.get_actors (default: unreachable -> [])."""
    old = wm.WORLDS_DIR
    old_get_actors = wm.unreal_client.get_actors
    wm.WORLDS_DIR = Path(tmp)
    wm.unreal_client.get_actors = lambda: (actors or [])
    try:
        fn(TestClient(wm.app))
    finally:
        wm.WORLDS_DIR = old
        wm.unreal_client.get_actors = old_get_actors


def test_sync_route_purges_and_reports():
    with tempfile.TemporaryDirectory() as tmp:
        # "home" (dufus, cell (5,5), dx=dy=0) is seeded straight into PlaceDB as
        # source='authored' by _seed(); apply_manifest is declarative (#23), so
        # it only survives a re-apply if places.json still backs it — same as
        # a landmark actor would. x=200,y=200 is cell (5,5)'s center.
        world = _world(tmp, places=[{"name": "home", "x": 200.0, "y": 200.0, "owner": "dufus"}])

        def body(client):
            data = client.post("/api/world/sync?level=TestWorld").json()
            check("sync reports the level", data["level"] == "TestWorld")
            check("sync lists exactly the wake-seed row",
                  data["deleted"] == [{"owner": "maren", "name": "the vegetable truck",
                                       "col": 6, "row": 6}])
            check("sync counts it", data["count"] == 1)
            check("no landmark actors -> landmarks 0", data["landmarks"] == 0)
            check("applied summary reports places.json's 'home' re-applied",
                  data["applied"] == {"applied": 1, "owned": 1, "community": 0, "skipped": 0})
            db = PlaceDB(world / "world_places.db")
            check("DB reflects the purge (authored + runtime survive)",
                  {o["name"] for o in db.all_owned_places()} == {"home", "favorite bench"})
            again = client.post("/api/world/sync?level=TestWorld").json()
            check("nothing to sync is an honest count 0",
                  again["count"] == 0 and again["deleted"] == [])
        _with_worlds(tmp, body)


def test_sync_missing_db_purges_nothing_but_still_rescans():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp, level="Barren", with_db=False)

        def body(client):
            data = client.post("/api/world/sync?level=Barren").json()
            check("missing DB -> nothing to purge",
                  data["deleted"] == [] and data["count"] == 0)
            check("no landmarks, no places.json -> landmarks 0", data["landmarks"] == 0)
            check("applied summary present (nothing to apply)",
                  data["applied"] == {"applied": 0, "owned": 0, "community": 0, "skipped": 0})
            check("the landmark/manifest rescan opens the world's PlaceDB",
                  (world / "world_places.db").exists())
        _with_worlds(tmp, body)


def test_sync_rescans_landmarks():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp, level="TestWorld", with_db=False)
        actor = {"name": "BP_VegTruck_C_1", "label": "Landmark_maren_vegetable_truck",
                 "class": "BP_VegTruck_C", "location": [320.0, 120.0, 90.0]}

        def body(client):
            data = client.post("/api/world/sync?level=TestWorld").json()
            check("one landmark actor -> landmarks 1", data["landmarks"] == 1)
            check("applied summary reports the owned write",
                  data["applied"] == {"applied": 1, "owned": 1, "community": 0, "skipped": 0})
            db = PlaceDB(world / "world_places.db")
            owned = db.find_owned_place("vegetable truck")
            check("landmark reached PlaceDB via the sync route",
                  owned is not None and owned["owner"] == "maren")
        _with_worlds(tmp, body, actors=[actor])


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
    test_sync_missing_db_purges_nothing_but_still_rescans()
    test_sync_rescans_landmarks()
    test_map_page_has_sync_button()
    print("\nAll world-sync checks passed.")


if __name__ == "__main__":
    main()
