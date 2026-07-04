"""Offline tests for run replay (#14) — step through a run's observation frames.

Covers the pure index/join layer (``agent_runtime.run_replay``) and the web
routes (``/api/replay/*`` + the image serve, path-traversal-guarded) against a
temp world of fake observation PNGs + a decision log. No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_run_replay.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient          # noqa: E402
from agent_runtime import run_replay               # noqa: E402
import web_ui.main as wm                            # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _world(tmp: str, level: str = "TestWorld") -> Path:
    """A world with SR1/SR2 observation frames for dufus + a decision log."""
    world = Path(tmp) / level
    obs = world / "agents" / "dufus" / "observations"
    obs.mkdir(parents=True)
    (world / "agents" / "maren" / "observations").mkdir(parents=True)
    # Two SR1 frames (one with a decision, one without) + one SR2 frame.
    for name in ["SR1_observation_20260703_090000.png",
                 "SR1_observation_20260703_091000.png",
                 "SR1_observation_20260703_090010_wake_forward.png",
                 "SR2_observation_20260704_080000.png"]:
        (obs / name).write_bytes(b"\x89PNG\r\n fake")
    logs = world / "logs"
    logs.mkdir()
    lines = [
        {"timestamp": "2026-07-03T09:00:03+00:00", "sim_run": "SR1", "agent_id": "dufus",
         "action_type": "walk_to", "thought": "heading to the square", "result_status": "success"},
        {"timestamp": "2026-07-04T08:00:01+00:00", "sim_run": "SR2", "agent_id": "dufus",
         "action_type": "speak_to", "thought": "greet Maren", "result_status": "success"},
        # A different run/agent that must never bleed into dufus's SR1 frames.
        {"timestamp": "2026-07-03T09:00:05+00:00", "sim_run": "SR1", "agent_id": "maren",
         "action_type": "idle", "thought": "at my truck", "result_status": "success"},
    ]
    (logs / "agent_decisions.log").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    return world


# ── pure index + join ───────────────────────────────────────────────────────────

def test_list_runs_and_agents():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp)
        check("runs listed newest-first", run_replay.list_runs(world) == ["SR2", "SR1"])
        check("agents discovered from dirs", run_replay.list_agents(world) == ["dufus", "maren"])
        check("empty world -> no runs", run_replay.list_runs(Path(tmp) / "nope") == [])


def test_frames_ordered_and_run_scoped():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp)
        frames = run_replay.list_frames(world, "SR1", "dufus")
        check("only this run's frames (3 SR1, not the SR2 one)", len(frames) == 3)
        stamps = [f["timestamp"] for f in frames]
        check("frames sorted by timestamp", stamps == sorted(stamps))
        check("tagged frame keeps its tag", frames[1]["tag"] == "wake_forward")
        check("untagged frame has no tag", frames[0]["tag"] is None)


def test_decision_join_by_nearest_time():
    with tempfile.TemporaryDirectory() as tmp:
        world = _world(tmp)
        frames = run_replay.list_frames(world, "SR1", "dufus")
        first = frames[0]                                     # 09:00:00
        check("nearby decision joins to the frame (3s later)",
              first["decision"] and first["decision"]["action_type"] == "walk_to")
        check("join never crosses agents (maren's idle not used)",
              first["decision"]["thought"] == "heading to the square")
        last = frames[-1]                                     # 09:10:00, no decision within window
        check("a frame with no nearby decision joins to None", last["decision"] is None)


def test_frame_name_guard():
    check("valid frame name accepted", run_replay.is_frame_name("SR3_observation_20260704_101112.png"))
    check("valid tagged frame accepted",
          run_replay.is_frame_name("SR3_observation_20260704_101112_wake_left.png"))
    check("traversal / junk rejected", not run_replay.is_frame_name("../../secret.png"))
    check("non-SR png rejected", not run_replay.is_frame_name("observation_20260704_101112.png"))


# ── web routes ──────────────────────────────────────────────────────────────────

def _with_worlds(tmp, fn):
    old = wm.WORLDS_DIR
    wm.WORLDS_DIR = Path(tmp)
    try:
        fn(TestClient(wm.app))
    finally:
        wm.WORLDS_DIR = old


def test_api_runs_and_frames():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            runs = client.get("/api/replay/runs?level=TestWorld").json()
            check("api lists runs", runs["runs"] == ["SR2", "SR1"])
            check("api lists agents", "dufus" in runs["agents"])

            data = client.get("/api/replay/frames?level=TestWorld&run=SR1&agent=dufus").json()
            check("api returns the 3 SR1 frames", len(data["frames"]) == 3)
            fr = data["frames"][0]
            check("frame carries an image url with the right params",
                  "/api/replay/image?level=TestWorld&agent=dufus&file=" in fr["image_url"])
            check("frame carries its joined decision", fr["decision"]["action_type"] == "walk_to")
        _with_worlds(tmp, body)


def test_api_image_serves_and_guards_traversal():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            ok = client.get("/api/replay/image?level=TestWorld&agent=dufus"
                            "&file=SR1_observation_20260703_090000.png")
            check("valid frame image is served", ok.status_code == 200)
            check("served as png", ok.headers["content-type"].startswith("image/png"))

            bad = client.get("/api/replay/image?level=TestWorld&agent=dufus"
                             "&file=../../../../logs/agent_decisions.log")
            check("path traversal is refused (404)", bad.status_code == 404)

            missing = client.get("/api/replay/image?level=TestWorld&agent=dufus"
                                 "&file=SR9_observation_20990101_000000.png")
            check("a non-existent frame is 404", missing.status_code == 404)
        _with_worlds(tmp, body)


def test_replay_page_renders():
    with tempfile.TemporaryDirectory() as tmp:
        _world(tmp)

        def body(client):
            html = client.get("/replay?level=TestWorld").text
            check("page renders the replay heading", "Run Replay" in html)
            check("page wires the frames api", "/api/replay/frames" in html)
        _with_worlds(tmp, body)


def main():
    test_list_runs_and_agents()
    test_frames_ordered_and_run_scoped()
    test_decision_join_by_nearest_time()
    test_frame_name_guard()
    test_api_runs_and_frames()
    test_api_image_serves_and_guards_traversal()
    test_replay_page_renders()
    print("\nAll run-replay checks passed.")


if __name__ == "__main__":
    main()
