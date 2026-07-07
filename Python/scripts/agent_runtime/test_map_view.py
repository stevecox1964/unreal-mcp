"""Offline tests for the web map view (staged plan A1).

Watch the grid + place cells get built out from the web app. Covers
``PlaceDB.map_cells()`` (the data layer — every named/swept cell + landmark
count) and the ``/map`` page + ``/api/map`` JSON route rendered against a temp
world (no Unreal, no network). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_map_view.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
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


# ── data layer: PlaceDB.map_cells ──────────────────────────────────────────────

def test_map_cells_reports_named_swept_and_landmarks():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 3, 4, "Village Square", "T0")
        db.ingest_compass("maren", 3, 4, "N", [{"label": "fountain", "confidence": 0.9},
                                               {"label": "clock tower", "confidence": 0.9}])
        db.mark_swept("dufus", 7, 2, "T1")           # swept-only, no name
        db.touch("dufus", 9, 9)                       # bare visit — not a place cell

        cells = db.map_cells()
        by = {(c["col"], c["row"]): c for c in cells}
        check("bare-visit cell is not on the map", (9, 9) not in by)
        check("named + swept cells are both on the map", set(by) == {(3, 4), (7, 2)})
        check("named cell reports state=named", by[(3, 4)]["state"] == "named")
        check("named cell carries its name", by[(3, 4)]["name"] == "Village Square")
        check("landmark count counts distinct observations", by[(3, 4)]["landmarks"] == 2)
        check("swept-only cell reports state=swept", by[(7, 2)]["state"] == "swept")
        check("swept-only cell has no landmarks", by[(7, 2)]["landmarks"] == 0)
        check("swept-only cell records who swept it", by[(7, 2)]["swept_by"] == "dufus")
        check("empty world -> empty map", PlaceDB(Path(tmp) / "empty.db").map_cells() == [])


# ── staleness (A2 / #11.3): real wall-clock basis ──────────────────────────────

def test_is_stale_by_wall_clock():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 1, 1, "Old Well", "T0")     # updated_at stamped now (real time)

        now = datetime.now(timezone.utc)
        day_later = now + timedelta(hours=25)
        check("fresh cell is not stale within max_age", db.is_stale(1, 1, 24 * 3600, now=now) is False)
        check("cell older than max_age is stale", db.is_stale(1, 1, 24 * 3600, now=day_later) is True)
        check("never-initialized cell is stale", db.is_stale(5, 5, 24 * 3600, now=now) is True)


def test_map_cells_surfaces_stale_flag_when_asked():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 1, 1, "Old Well", "T0")
        future = datetime.now(timezone.utc) + timedelta(hours=25)

        # No max_age -> no staleness computed (back-compat with A1).
        plain = db.map_cells()[0]
        check("map_cells omits stale by default", "stale" not in plain)
        check("map_cells always carries updated_at", plain["updated_at"] is not None)

        flagged = db.map_cells(max_age_seconds=24 * 3600, now=future)[0]
        check("map_cells marks the cell stale when asked", flagged["stale"] is True)


# ── web layer: build_map + routes ──────────────────────────────────────────────

def _world(tmp: str, level: str = "TestWorld") -> Path:
    """Create a bounded world dir with a small grid + a PlaceDB with two cells."""
    world = Path(tmp) / level
    (world / "agents").mkdir(parents=True)
    (world / "world_grid.json").write_text(json.dumps({
        "cell_size": 400.0,
        "bounds": {"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999},
    }), encoding="utf-8")
    db = PlaceDB(world / "world_places.db")
    db.set_name("maren", 3, 4, "Village Square", "T0")
    db.mark_swept("dufus", 7, 2, "T1")
    db.add_owned_place("maren", 3, 4, "My Home", dx=120.0, dy=-80.0)
    return world


def _with_worlds(tmp, fn):
    old = wm.WORLDS_DIR
    wm.WORLDS_DIR = Path(tmp)
    try:
        fn(TestClient(wm.app))
    finally:
        wm.WORLDS_DIR = old


def test_api_map_returns_grid_and_cells():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            data = client.get("/api/map?level=TestWorld").json()
            check("api reports the level", data["level"] == "TestWorld")
            check("api reports grid dims (10x10)", (data["cols"], data["rows"]) == (10, 10))
            check("api reports cell_size", data["cell_size"] == 400.0)
            check("api returns both place cells", len(data["cells"]) == 2)
            check("api counts named + swept", data["counts"]["named"] == 1 and data["counts"]["swept"] == 1)
            check("api carries owned places with geometry (#11.2/#6c)",
                  data["owned"] == [{"col": 3, "row": 4, "owner": "maren", "name": "My Home",
                                     "dx": 120.0, "dy": -80.0, "extent_cm": 900.0}])
            check("api counts owned places", data["counts"]["owned"] == 1)
            # #6c overlay geometry: bounds + the grid's origin-anchored (0,0) corner.
            check("api carries world bounds", data["bounds"]["min_x"] == -2000)
            check("api carries the grid origin",
                  (data["origin_x"], data["origin_y"]) == (-2000.0, -2000.0))
            check("api falls back to the shared world capture (mtime-versioned)",
                  data["image_url"].startswith("/images/world_map_view.png?v="))
            check("no calibration -> image_bounds is null", data["image_bounds"] is None)
        _with_worlds(tmp, body)


def test_api_map_carries_image_bounds_calibration():
    # #6c registration fix: a capture that doesn't frame the world bounds
    # exactly gets an image_bounds calibration in world_grid.json; the overlay
    # maps world->pixel through it instead of assuming bounds.
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp, level="Calib")
        grid = json.loads((world / "world_grid.json").read_text(encoding="utf-8"))
        grid["image_bounds"] = {"min_x": -1500, "min_y": -1800, "max_x": 2500, "max_y": 2200}
        (world / "world_grid.json").write_text(json.dumps(grid), encoding="utf-8")

        def body(client):
            data = client.get("/api/map?level=Calib").json()
            check("api passes the image_bounds calibration through",
                  data["image_bounds"] == {"min_x": -1500, "min_y": -1800,
                                           "max_x": 2500, "max_y": 2200})
            check("world bounds are untouched by calibration",
                  data["bounds"]["min_x"] == -2000)
        _with_worlds(tmp, body)


def test_api_map_missing_db_is_empty_not_error():
    with tempfile.TemporaryDirectory() as tmp:
        level = "Barren"
        (Path(tmp) / level / "agents").mkdir(parents=True)
        (Path(tmp) / level / "world_grid.json").write_text(json.dumps({
            "cell_size": 400.0,
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 799, "max_y": 799},
        }), encoding="utf-8")

        def body(client):
            data = client.get("/api/map?level=Barren").json()
            check("missing DB -> empty cells, no error", data["cells"] == [])
            check("no DB file was created by a GET", not (Path(tmp) / level / "world_places.db").exists())
        _with_worlds(tmp, body)


def test_map_page_renders_with_legend_and_polls_api():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            text = client.get("/map?level=TestWorld").text
            check("map page names the world", "TestWorld" in text)
            check("map page has a legend for named/swept/unexplored",
                  "named" in text.lower() and "swept" in text.lower() and "unexplored" in text.lower())
            check("map page has an owned-place legend + marker style",
                  "owned place" in text and "owned-mark" in text)
            check("grid lines are visible (not the near-invisible pale gap)",
                  "#8b95a1" in text and "background:#ddd" not in text)
            check("map page fetches /api/map to build out live", "/api/map" in text)
            # #6c: the real capture is the map background; the grid overlays it.
            check("map page embeds the world capture",
                  '<img id="bg" src="/images/world_map_view.png' in text)
            check("map page draws cells from world coords (origin-anchored)",
                  "origin_x" in text and "placeRect" in text)
            check("map page maps through the calibrated frame + shows a coord readout",
                  "image_bounds" in text and 'id="coords"' in text)
        _with_worlds(tmp, body)


def test_map_image_is_served():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            resp = client.get("/images/world_map_view.png")
            check("shared world capture is served", resp.status_code == 200)
            check("capture is a PNG", resp.content[:4] == b"\x89PNG")
        _with_worlds(tmp, body)


def main():
    test_map_cells_reports_named_swept_and_landmarks()
    test_is_stale_by_wall_clock()
    test_map_cells_surfaces_stale_flag_when_asked()
    test_api_map_returns_grid_and_cells()
    test_api_map_carries_image_bounds_calibration()
    test_api_map_missing_db_is_empty_not_error()
    test_map_page_renders_with_legend_and_polls_api()
    test_map_image_is_served()
    print("\nAll map-view checks passed.")


if __name__ == "__main__":
    main()
