"""Offline tests for the click-to-author places editor (#16).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_places_editor.py

The no-Unreal answer to "Maren's truck is here": author mode on /map turns a
click into a places.json entry (WP6's manifest — the user's ground truth) and
re-applies the manifest to PlaceDB immediately, so moves and deletes converge
without a sim restart. Covers GET/POST/DELETE /api/places, validation
(fail-loud, never heal a corrupt file), and the author-mode page markup.
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


BOUNDS = {"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999}  # 10x10 cells


def _world(tmp: str, level: str = "TestWorld", bounded: bool = True) -> Path:
    world = Path(tmp) / level
    (world / "agents" / "maren").mkdir(parents=True)
    grid = {"cell_size": 400.0}
    if bounded:
        grid["bounds"] = BOUNDS
    (world / "world_grid.json").write_text(json.dumps(grid), encoding="utf-8")
    return world


def _with_worlds(tmp, fn):
    old = wm.WORLDS_DIR
    wm.WORLDS_DIR = Path(tmp)
    try:
        fn(TestClient(wm.app))
    finally:
        wm.WORLDS_DIR = old


def _post(client, **body):
    body.setdefault("level", "TestWorld")
    return client.post("/api/places", json=body)


def test_author_move_delete_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp)
        # A runtime discovery that must survive every authored edit.
        PlaceDB(world / "world_places.db").add_owned_place(
            "maren", 1, 1, "favorite bench", dx=10.0, dy=10.0)

        def body(client):
            r = _post(client, name="the vegetable truck", x=320.0, y=120.0, owner="maren")
            check("author POST ok", r.status_code == 200 and r.json()["ok"] is True)
            check("first write is a create", r.json()["replaced"] is False)
            check("apply ran with it", r.json()["applied"]["owned"] == 1)

            manifest = json.loads((world / "places.json").read_text(encoding="utf-8"))
            check("places.json holds the entry",
                  manifest["places"] == [{"name": "the vegetable truck",
                                          "x": 320.0, "y": 120.0, "owner": "maren"}])
            db = PlaceDB(world / "world_places.db")
            owned = db.find_owned_place("the vegetable truck")
            check("PlaceDB converged immediately (cell derived)",
                  owned is not None and (owned["col"], owned["row"]) == (5, 5))

            # Same name, new click = move (no duplicate anywhere).
            r = _post(client, name="The Vegetable Truck", x=-800.0, y=900.0, owner="maren")
            check("same name is a move", r.json()["replaced"] is True)
            manifest = json.loads((world / "places.json").read_text(encoding="utf-8"))
            check("no duplicate entry after the move", len(manifest["places"]) == 1)
            owned = PlaceDB(world / "world_places.db").find_owned_place("the vegetable truck")
            check("DB re-anchored to the new click",
                  (owned["col"], owned["row"]) == (3, 7))

            # Community place: no owner -> names the cell.
            _post(client, name="village square", x=100.0, y=100.0)
            check("community entry names its cell",
                  PlaceDB(world / "world_places.db").find_named_cell("village square") == (5, 5))

            # GET lists the raw manifest.
            listed = client.get("/api/places?level=TestWorld").json()
            check("GET lists the authored entries",
                  [p["name"] for p in listed["places"]]
                  == ["The Vegetable Truck", "village square"])

            # DELETE removes entry + its rows; runtime rows always survive.
            r = client.delete("/api/places?level=TestWorld&name=the%20vegetable%20truck")
            check("DELETE ok", r.json()["ok"] is True and r.json()["removed"] == 1)
            db = PlaceDB(world / "world_places.db")
            check("authored row gone after delete",
                  db.find_owned_place("the vegetable truck") is None)
            check("runtime discovery survived it all",
                  db.find_owned_place("favorite bench") is not None)
            check("unknown delete -> 404",
                  client.delete("/api/places?level=TestWorld&name=atlantis").status_code == 404)
        _with_worlds(tmp, body)


def test_validation_fails_loud():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp)

        def body(client):
            check("blank name -> 400", _post(client, name="  ", x=0, y=0).status_code == 400)
            check("placeholder name -> 400",
                  _post(client, name="unknown", x=0, y=0).status_code == 400)
            check("missing coords -> 400", _post(client, name="x").status_code == 400)
            check("out of bounds -> 400",
                  _post(client, name="x", x=99999.0, y=0).status_code == 400)
            check("nothing written by rejected posts", not (world / "places.json").exists())

            # A corrupt manifest is surfaced, never silently rewritten.
            (world / "places.json").write_text("{nope", encoding="utf-8")
            r = _post(client, name="x", x=0.0, y=0.0)
            check("corrupt places.json -> 500 naming the fix",
                  r.status_code == 500 and "unparseable" in r.json()["error"])
            check("corrupt file left untouched",
                  (world / "places.json").read_text(encoding="utf-8") == "{nope")
        _with_worlds(tmp, body)

    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp, bounded=False)

        def body(client):
            r = _post(client, name="x", x=0.0, y=0.0)
            check("unbounded grid -> 400 naming the fix",
                  r.status_code == 400 and "bounds" in r.json()["error"])
        _with_worlds(tmp, body)


def test_map_page_has_author_mode():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            text = client.get("/map?level=TestWorld").text
            check("map page has the Author places toggle",
                  'id="author-btn"' in text and "Author places" in text)
            check("author panel with name/owner/extent inputs",
                  'id="place-name"' in text and 'id="place-owner"' in text
                  and 'id="place-extent"' in text)
            check("owner dropdown lists the world's agents + community",
                  ">community<" in text and ">maren<" in text)
            check("panel drives /api/places", "/api/places" in text)
        _with_worlds(tmp, body)


def main():
    test_author_move_delete_roundtrip()
    test_validation_fails_loud()
    test_map_page_has_author_mode()
    print("\nAll places-editor checks passed.")


if __name__ == "__main__":
    main()
