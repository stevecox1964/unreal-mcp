"""Offline tests for the MAP_Camera world-map capture (#18 capture half).

No Unreal, no network — the unreal_client calls are stubbed. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_map_capture.py

The engine capture is fixed (1920x1080, 90-degree horizontal FOV), so a
straight-down camera at height h frames exactly (2h x 2h*9/16) cm of ground —
the pose math IS the registration (#18: no hand calibration). Covers
``camera_pose_for_bounds`` and ``POST /api/map/capture`` (aim + shoot + write
image_bounds), including the fail-loud paths.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient          # noqa: E402
import web_ui.main as wm                            # noqa: E402
from web_ui import unreal_client                    # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


BOUNDS = {"min_x": -2000.0, "min_y": -2000.0, "max_x": 1999.0, "max_y": 1999.0}


def test_camera_pose_math():
    pose = wm.camera_pose_for_bounds(BOUNDS)
    cx, cy, h = pose["location"]
    check("camera centers over the bounds", (cx, cy) == (-0.5, -0.5))
    # Square bounds: the short (16:9 vertical) axis dictates the height.
    need = (BOUNDS["max_y"] - BOUNDS["min_y"]) / 2.0 / wm.MAP_CAPTURE_ASPECT
    check("height covers the binding axis + margin",
          abs(h - need * wm.MAP_CAPTURE_MARGIN) < 1e-6)
    check("camera looks straight down, north up",
          pose["rotation"] == [-90.0, -90.0, 0.0])
    ib = pose["image_bounds"]
    check("image_bounds is the exact footprint",
          ib["min_x"] == cx - h and ib["max_x"] == cx + h
          and abs((ib["max_y"] - ib["min_y"]) - 2 * h * wm.MAP_CAPTURE_ASPECT) < 1e-6)
    check("footprint contains the world bounds",
          ib["min_x"] <= BOUNDS["min_x"] and ib["max_x"] >= BOUNDS["max_x"]
          and ib["min_y"] <= BOUNDS["min_y"] and ib["max_y"] >= BOUNDS["max_y"])

    wide = wm.camera_pose_for_bounds({"min_x": 0, "max_x": 10000, "min_y": 0, "max_y": 100})
    check("wide world: the horizontal axis dictates the height",
          abs(wide["location"][2] - 5000 * wm.MAP_CAPTURE_MARGIN) < 1e-6)


class StubUnreal:
    """Records the aim + shoot calls; scriptable responses."""
    def __init__(self, move_resp=None, shot_resp=None):
        self.moves, self.shots = [], []
        self.move_resp = move_resp if move_resp is not None else {"status": "success"}
        self.shot_resp = shot_resp if shot_resp is not None else {
            "status": "success", "result": {"success": True, "actor_name": "MAP_Camera_C_1"}}

    def set_actor_transform(self, name, location=None, rotation=None):
        self.moves.append((name, location, rotation))
        return self.move_resp

    def capture_camera_image(self, actor_name, file_path):
        self.shots.append((actor_name, file_path))
        return self.shot_resp


def _world(tmp: str, level: str = "TestWorld", bounds: dict = None) -> Path:
    world = Path(tmp) / level
    (world / "agents").mkdir(parents=True)
    grid = {"cell_size": 400.0}
    if bounds is not False:
        grid["bounds"] = bounds or BOUNDS
    (world / "world_grid.json").write_text(json.dumps(grid), encoding="utf-8")
    return world


def _with_stub(tmp, stub, fn):
    old_worlds, old_client = wm.WORLDS_DIR, wm.unreal_client
    wm.WORLDS_DIR, wm.unreal_client = Path(tmp), stub
    try:
        fn(TestClient(wm.app))
    finally:
        wm.WORLDS_DIR, wm.unreal_client = old_worlds, old_client


def test_capture_route_aims_shoots_and_calibrates():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp)
        stub = StubUnreal()

        def body(client):
            data = client.post("/api/map/capture?level=TestWorld").json()
            check("route reports ok", data["ok"] is True)
            check("camera was aimed once at the pose",
                  len(stub.moves) == 1 and stub.moves[0][0] == "MAP_Camera"
                  and stub.moves[0][2] == [-90.0, -90.0, 0.0])
            check("capture targeted images/<level>.png",
                  len(stub.shots) == 1 and stub.shots[0][0] == "MAP_Camera"
                  and stub.shots[0][1].endswith("TestWorld.png"))
            check("route reports the engine's resolved actor",
                  data["actor"] == "MAP_Camera_C_1")
            check("route reports the image url", data["image_url"] == "/images/TestWorld.png")

            grid = json.loads((world / "world_grid.json").read_text(encoding="utf-8"))
            check("image_bounds calibration persisted",
                  grid["image_bounds"] == data["image_bounds"])
            check("world bounds untouched", grid["bounds"]["min_x"] == BOUNDS["min_x"])
            pose = wm.camera_pose_for_bounds(BOUNDS)
            check("persisted calibration is the camera footprint",
                  grid["image_bounds"] == pose["image_bounds"])
        _with_stub(tmp, stub, body)


def test_capture_route_fail_loud():
    with tempfile.TemporaryDirectory() as tmp:
        # No bounds -> 400, nothing aimed.
        world = Path(tmp) / "Unbounded"
        (world / "agents").mkdir(parents=True)
        (world / "world_grid.json").write_text(json.dumps({"cell_size": 400.0}),
                                               encoding="utf-8")
        stub = StubUnreal()

        def body(client):
            resp = client.post("/api/map/capture?level=Unbounded")
            check("unbounded world -> 400 with the reason",
                  resp.status_code == 400 and "bounds" in resp.json()["error"])
            check("nothing aimed without bounds", stub.moves == [])
        _with_stub(tmp, stub, body)

    with tempfile.TemporaryDirectory() as tmp:
        # Unreal unreachable on the aim -> 502, no calibration written.
        world = _world(tmp)
        stub = StubUnreal(move_resp=None)
        stub.move_resp = None

        def body(client):
            resp = client.post("/api/map/capture?level=TestWorld")
            check("unreachable Unreal -> 502",
                  resp.status_code == 502 and "MAP_Camera" in resp.json()["error"])
            grid = json.loads((world / "world_grid.json").read_text(encoding="utf-8"))
            check("no calibration written on failure", "image_bounds" not in grid)
        _with_stub(tmp, stub, body)

    with tempfile.TemporaryDirectory() as tmp:
        # Actor missing -> the engine error surfaces, no calibration written.
        world = _world(tmp)
        stub = StubUnreal(shot_resp={"status": "error",
                                     "error": "Actor not found: MAP_Camera"})

        def body(client):
            resp = client.post("/api/map/capture?level=TestWorld")
            check("engine error surfaces verbatim",
                  resp.status_code == 502 and "Actor not found" in resp.json()["error"])
            grid = json.loads((world / "world_grid.json").read_text(encoding="utf-8"))
            check("no calibration written on capture failure", "image_bounds" not in grid)
        _with_stub(tmp, stub, body)


def test_map_page_has_reshoot_button():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)
        stub = StubUnreal()

        def body(client):
            text = client.get("/map?level=TestWorld").text
            check("map page has the Re-shoot button",
                  'id="shoot-btn"' in text and "Re-shoot map" in text)
            check("button posts to /api/map/capture", "/api/map/capture" in text)
        _with_stub(tmp, stub, body)


def main():
    test_camera_pose_math()
    test_capture_route_aims_shoots_and_calibrates()
    test_capture_route_fail_loud()
    test_map_page_has_reshoot_button()
    print("\nAll map-capture checks passed.")


if __name__ == "__main__":
    main()
