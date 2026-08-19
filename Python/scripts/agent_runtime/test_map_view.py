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

def test_map_cells_reports_named_swept_and_visual_metrics():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 3, 4, "Village Square", "T0")
        db.ingest_compass("maren", 3, 4, "N", [{"label": "fountain", "confidence": 0.9},
                                               {"label": "clock tower", "confidence": 0.9}])
        db.ingest_compass("dufus", 3, 4, "S", [{"label": "Fountain", "confidence": 0.95}])
        db.ingest_compass("dufus", 3, 4, "N", [{"label": "fountain", "confidence": 0.95}])
        db.mark_swept("dufus", 7, 2, "T1")           # swept-only, no name
        db.touch("dufus", 9, 9)                       # bare visit — not a place cell

        cells = db.map_cells()
        by = {(c["col"], c["row"]): c for c in cells}
        check("bare-visit cell is not on the map", (9, 9) not in by)
        check("named + swept cells are both on the map", set(by) == {(3, 4), (7, 2)})
        check("named cell reports state=named", by[(3, 4)]["state"] == "named")
        check("named is an independent map fact",
              by[(3, 4)]["named"] is True and by[(7, 2)]["named"] is False)
        check("breadcrumb alone is not a completed visual survey",
              by[(7, 2)]["swept"] is True and by[(7, 2)]["surveyed"] is False)
        check("named cell carries its name", by[(3, 4)]["name"] == "Village Square")
        check("visual metric counts direction/label rows",
              by[(3, 4)]["visual_observations"] == 3)
        check("visual metric counts normalized textual labels",
              by[(3, 4)]["distinct_visual_labels"] == 2)
        check("visual metric sums repeated sightings",
              by[(3, 4)]["visual_sightings"] == 4)
        check("swept-only cell reports state=swept", by[(7, 2)]["state"] == "swept")
        check("swept-only cell has no visual observations",
              by[(7, 2)]["visual_observations"] == 0)
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
    image = world / "places" / "images" / "community.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    db.record_place_image(
        "maren", 3, 4, "places/images/community.png",
        {"N": "n.png", "S": "s.png", "E": "e.png", "W": "w.png"},
        description="Four views of the square",
    )
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
            mapped = next(c for c in data["cells"] if (c["col"], c["row"]) == (3, 4))
            check("api exposes surveyed-cell image metadata",
                  mapped["place_image_id"] and mapped["place_image_revision"] == 1
                  and mapped["place_image_captured_by"] == "maren")
            check("named surveyed cell exposes both non-exclusive facts",
                  mapped["named"] is True and mapped["surveyed"] is True)
            check("api exposes a browser-safe composite URL",
                  mapped["place_image_url"].startswith(
                      "/api/map/place-image?level=TestWorld&place_image_id="))
            check("api independently counts named and surveyed cells",
                  data["counts"]["named"] == 1
                  and data["counts"]["surveyed"] == 1
                  and data["counts"]["mapped"] == 2)
            check("api carries owned places with geometry (#11.2/#6c)",
                  data["owned"] == [{"col": 3, "row": 4, "owner": "maren", "name": "My Home",
                                     "dx": 120.0, "dy": -80.0, "extent_cm": 900.0}])
            check("api counts owned places", data["counts"]["owned"] == 1)
            # #6c overlay geometry: bounds + the grid's origin-anchored (0,0) corner.
            check("api carries world bounds", data["bounds"]["min_x"] == -2000)
            check("api carries the grid origin",
                  (data["origin_x"], data["origin_y"]) == (-2000.0, -2000.0))
            check("api carries configurable logical origin",
                  (data["logical_origin_x"], data["logical_origin_y"]) == (0.0, 0.0))
            check("api falls back to the shared world capture (mtime-versioned)",
                  data["image_url"].startswith("/images/world_map_view.png?v="))
            check("no calibration -> image_bounds is null", data["image_bounds"] is None)
        _with_worlds(tmp, body)


def test_api_map_carries_refused_ground():
    """Refused cells and no-go patches reach the map, with who and why (#80)."""
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp)
        db = PlaceDB(world / "world_places.db")
        db.refuse_cell("dufus", 5, 5, "standing corn", "Day 1, 08:02")
        db.refuse_cell("maren", 5, 5, "not my ground", "Day 1, 09:00")
        db.refuse_patch("dufus", -1500.0, -1500.0, "private backyard", "Day 1, 09:15")

        def body(client):
            data = client.get("/api/map?level=TestWorld").json()
            refusals = data["refusals"]
            check("every refusal reaches the map", len(refusals) == 2)
            corn = next(r for r in refusals if r["refused_by"] == "dufus")
            check("a refusal says who, why, and when",
                  (corn["col"], corn["row"], corn["reason"], corn["refused_at"])
                  == (5, 5, "standing corn", "Day 1, 08:02"))
            check("two refusals of one cell count it once",
                  data["counts"]["refused"] == 1)
            patch = data["no_go"][0]
            check("a no-go patch carries its true geometry",
                  (patch["x"], patch["y"], patch["radius_cm"]) == (-1500.0, -1500.0, 450.0))
            check("a patch says who and why",
                  patch["refused_by"] == "dufus" and patch["reason"] == "private backyard")
            check("patches are counted", data["counts"]["no_go"] == 1)
            check("a refused-only cell is NOT a mapped place cell",
                  all((c["col"], c["row"]) != (5, 5) for c in data["cells"]))

            page = client.get("/map?level=TestWorld").text
            check("the legend names refused ground", "refused (off-limits)" in page)
            check("the legend names no-go patches", "no-go patch" in page)
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
            check("map page has independent named/surveyed/unexplored legend",
                  'id="n-named"' in text and 'id="n-surveyed"' in text
                  and "unexplored" in text.lower() and 'id="n-swept"' not in text)
            check("map page has an owned-place legend + marker style",
                  "owned place" in text and "owned-mark" in text)
            check("map page has clickable surveyed-community markers",
                  "surveyed community" in text and "survey-mark" in text
                  and 'id="survey-dialog"' in text)
            check("surveyed-community markers render as centered 3px squares",
                  'width:3px; height:3px' in text
                  and 'left:4px; top:4px' in text
                  and 'transform:translate(-50%,-50%)' in text)
            check("map page labels counts as visual observations, not physical landmarks",
                  "visual observations" in text.lower()
                  and "${cell.landmarks} landmark(s)" not in text)
            check("stale wording explains saved surveys remain refreshable",
                  "saved survey older than" in text.lower()
                  and "eligible for refresh" in text.lower())
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
            # Zoom/pan: the transform lives on #view and both coordinate
            # readers must measure #view (the transformed element), not #wrap.
            check("map page has the zoom/pan view layer",
                  'id="view"' in text and "applyView" in text and '"wheel"' in text)
            check("coordinate math reads the transformed element",
                  "view.getBoundingClientRect()" in text
                  and "wrap.getBoundingClientRect(), f = geo.frame" not in text)
            check("map page has preview-first grid alignment controls",
                  'id="align-grid-btn"' in text and 'id="grid-preview-btn"' in text
                  and '"/api/world/regrid"' in text)
        _with_worlds(tmp, body)


def test_map_page_shows_grid_gen_callout_when_ungridded():
    # #13.2: a level with no world_grid.json bounds gets the "Generate world
    # grid" callout; a bounded level renders exactly what it renders today.
    with tempfile.TemporaryDirectory() as tmp:
        level = "Ungridded"
        (Path(tmp) / level / "agents").mkdir(parents=True)

        def body(client):
            text = client.get(f"/map?level={level}").text
            check("ungridded level has no bounded grid message",
                  "has no bounded grid" in text)
            check("ungridded level shows the grid-gen callout",
                  "has no grid yet" in text and 'id="gen-grid-btn"' in text)
            check("callout button posts the new route",
                  '"/api/world/grid"' in text)
        _with_worlds(tmp, body)

    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)   # bounded world (TestWorld) — has_bounds True

        def body(client):
            text = client.get("/map?level=TestWorld").text
            check("bounded level has no grid-gen callout",
                  "has no grid yet" not in text and 'id="gen-grid-btn"' not in text)
        _with_worlds(tmp, body)


def test_map_image_is_served():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            resp = client.get("/images/world_map_view.png")
            check("shared world capture is served", resp.status_code == 200)
            check("capture is a PNG", resp.content[:4] == b"\x89PNG")
        _with_worlds(tmp, body)


def test_place_composite_is_served_from_current_map_record():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            mapped = next(c for c in client.get("/api/map?level=TestWorld").json()["cells"]
                          if (c["col"], c["row"]) == (3, 4))
            resp = client.get(mapped["place_image_url"])
            check("survey composite endpoint serves the current place image", resp.status_code == 200)
            check("survey composite endpoint returns PNG content", resp.content.startswith(b"\x89PNG"))
            missing = client.get(
                "/api/map/place-image?level=TestWorld&place_image_id=does-not-exist")
            check("unknown place image is not exposed", missing.status_code == 404)
        _with_worlds(tmp, body)


def test_regrid_proxy_requires_confirmation():
    class StubRunner:
        def __init__(self):
            self.calls = []

        def regrid(self, level, origin_x, origin_y):
            self.calls.append((level, origin_x, origin_y))
            return {"status": "regridded", "level": level,
                    "origin_x": origin_x, "origin_y": origin_y}

    stub = StubRunner()
    old = wm.get_runner
    wm.get_runner = lambda: stub
    try:
        client = TestClient(wm.app)
        denied = client.post("/api/world/regrid", json={
            "level": "TestWorld", "origin_x": -1000, "origin_y": 500,
        })
        check("regrid proxy rejects an unconfirmed destructive apply",
              denied.status_code == 400 and stub.calls == [])
        applied = client.post("/api/world/regrid", json={
            "level": "TestWorld", "origin_x": -1000, "origin_y": 500,
            "confirm": True,
        })
        check("confirmed regrid reaches the runner",
              applied.status_code == 200
              and stub.calls == [("TestWorld", -1000.0, 500.0)])
    finally:
        wm.get_runner = old


def main():
    test_map_cells_reports_named_swept_and_visual_metrics()
    test_is_stale_by_wall_clock()
    test_map_cells_surfaces_stale_flag_when_asked()
    test_api_map_returns_grid_and_cells()
    test_api_map_carries_refused_ground()
    test_api_map_carries_image_bounds_calibration()
    test_api_map_missing_db_is_empty_not_error()
    test_map_page_renders_with_legend_and_polls_api()
    test_map_page_shows_grid_gen_callout_when_ungridded()
    test_map_image_is_served()
    test_place_composite_is_served_from_current_map_record()
    test_regrid_proxy_requires_confirmation()
    print("\nAll map-view checks passed.")


if __name__ == "__main__":
    main()
