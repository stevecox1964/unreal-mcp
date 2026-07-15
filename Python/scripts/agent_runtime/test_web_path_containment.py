"""Offline regression checks for cockpit filesystem path containment (#29).

Every world/agent identifier accepted by the web UI is untrusted.  These
checks drive representative read, write, replay, and recursive-delete routes
through FastAPI's TestClient and require traversal, absolute paths, reserved
segments, separators, and symlink escapes to fail closed without changing an
outside sentinel.  No Unreal process or network is used.

Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_web_path_containment.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
import web_ui.main as wm  # noqa: E402


FAILURES: list[str] = []
REJECTED = {400, 404}
FRAME = "SR1_observation_20260715_090000.png"
BOUNDS = {"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999}


def check(label: str, condition: bool) -> None:
    if condition:
        print(f"ok: {label}")
    else:
        print(f"FAIL: {label}")
        FAILURES.append(label)


def _agent(path: Path, agent_id: str, marker: str) -> None:
    path.mkdir(parents=True)
    (path / "state.json").write_text(json.dumps({
        "agent_id": agent_id,
        "unreal_actor_name": agent_id.title(),
        "tier": 2,
        "is_active": True,
        "current_goal": "idle",
    }), encoding="utf-8")
    (path / "character.md").write_text(marker, encoding="utf-8")
    (path / "goals.md").write_text("stay contained", encoding="utf-8")
    (path / "rules.md").write_text("do no harm", encoding="utf-8")
    (path / "tools.json").write_text(
        json.dumps({"allowed_actions": ["idle"]}), encoding="utf-8")
    (path / "memory.json").write_text(
        json.dumps({"agent_id": agent_id, "memories": []}), encoding="utf-8")


def _world(path: Path, agent_id: str = "alice", marker: str = "inside") -> Path:
    path.mkdir(parents=True)
    (path / "world_grid.json").write_text(json.dumps({
        "cell_size": 400.0,
        "bounds": BOUNDS,
    }), encoding="utf-8")
    (path / "places.json").write_text(json.dumps({
        "places": [{"name": marker, "x": 0.0, "y": 0.0}],
    }), encoding="utf-8")
    agent = path / "agents" / agent_id
    _agent(agent, agent_id, marker)
    observations = agent / "observations"
    observations.mkdir()
    (observations / FRAME).write_bytes(b"\x89PNG\r\n contained-test")
    return path


def _link(link: Path, target: Path) -> None:
    """Create a directory symlink or fail explicitly instead of skipping coverage."""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        print(f"FAIL: test host could not create required directory symlink: {exc}")
        sys.exit(1)


def _rejected(label: str, response) -> None:
    check(f"{label} is rejected with 400/404", response.status_code in REJECTED)


def test_valid_routes(client: TestClient) -> None:
    listed = client.get("/api/places", params={"level": "GoodWorld"})
    check("valid world read remains available",
          listed.status_code == 200 and listed.json()["places"][0]["name"] == "inside")
    image = client.get("/api/replay/image", params={
        "level": "GoodWorld", "agent": "alice", "file": FRAME,
    })
    check("valid contained replay image remains available", image.status_code == 200)


def test_world_identifiers(client: TestClient, root: Path, outside_world: Path) -> None:
    traversal = client.get("/api/places", params={"level": "../OutsideWorld"})
    _rejected("world traversal read", traversal)

    separated = client.get(
        "/api/replay/runs", params={"level": "GoodWorld/../../OutsideWorld"})
    _rejected("world identifier containing separators", separated)

    backslash = client.get("/api/places?level=GoodWorld%5C..%5COutsideWorld")
    _rejected("encoded backslash world traversal", backslash)

    absolute = client.get("/api/places", params={"level": str(outside_world.resolve())})
    _rejected("absolute world path", absolute)

    reserved = client.get("/api/places", params={"level": "."})
    _rejected("reserved dot world segment", reserved)

    linked = client.get("/api/places", params={"level": "LinkedWorld"})
    _rejected("world-directory symlink escape", linked)

    before = (outside_world / "places.json").read_bytes()
    write = client.post("/api/places", json={
        "level": "../OutsideWorld", "name": "escaped write", "x": 100.0, "y": 100.0,
    })
    _rejected("world traversal write", write)
    check("world traversal write leaves outside manifest byte-for-byte unchanged",
          (outside_world / "places.json").read_bytes() == before)
    check("world traversal write does not create an outside database",
          not (outside_world / "world_places.db").exists())


def test_agent_read_write_and_replay(
        client: TestClient, outside_agent: Path, outside_sentinel: Path) -> None:
    read = client.get("/worlds/GoodWorld/agents/escape")
    _rejected("agent-directory symlink read", read)

    before_character = (outside_agent / "character.md").read_bytes()
    write = client.post("/worlds/GoodWorld/agents/escape", data={
        "unreal_actor_name": "Escaped",
        "tier": "2",
        "is_active": "on",
        "current_goal": "overwrite outside",
        "tick_interval_seconds": "10",
        "speech_cooldown_seconds": "30",
        "character": "MUTATED",
        "goals": "MUTATED",
        "rules": "MUTATED",
        "allowed_actions": "idle",
    }, follow_redirects=False)
    _rejected("agent-directory symlink write", write)
    check("agent symlink write leaves outside agent content unchanged",
          (outside_agent / "character.md").read_bytes() == before_character)

    replay = client.get("/api/replay/frames", params={
        "level": "GoodWorld", "run": "SR1", "agent": "escape",
    })
    _rejected("replay index agent symlink escape", replay)

    image = client.get("/api/replay/image", params={
        "level": "GoodWorld", "agent": "escape", "file": FRAME,
    })
    _rejected("replay image agent symlink escape", image)
    check("agent read/write/replay probes preserve the outside sentinel",
          outside_sentinel.read_text(encoding="utf-8") == "DO NOT TOUCH")


def test_recursive_delete(
        client: TestClient, root: Path, outside_agent: Path, outside_sentinel: Path) -> None:
    delete_link = client.post(
        "/worlds/GoodWorld/agents/escape/delete", follow_redirects=False)
    _rejected("recursive delete through an agent symlink", delete_link)
    check("symlink-delete target still exists", outside_agent.is_dir())
    check("symlink delete preserves the outside sentinel",
          outside_sentinel.read_text(encoding="utf-8") == "DO NOT TOUCH")

    # Encoded traversal is kept encoded in the request URL and must not be
    # normalized into a different, valid target by application code.
    victim = root / "agents" / "victim"
    victim.mkdir(parents=True)
    victim_sentinel = victim / "outside-delete-sentinel.txt"
    victim_sentinel.write_text("KEEP ME", encoding="utf-8")
    traversal = client.post(
        "/worlds/%2E%2E/agents/victim/delete", follow_redirects=False)
    _rejected("encoded world traversal recursive delete", traversal)
    check("encoded traversal delete preserves its outside sentinel",
          victim_sentinel.is_file()
          and victim_sentinel.read_text(encoding="utf-8") == "KEEP ME")


def main() -> None:
    FAILURES.clear()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        worlds = root / "worlds"
        good_world = _world(worlds / "GoodWorld")
        outside_world = _world(root / "OutsideWorld", "outsider", "outside secret")
        outside_agent = root / "OutsideAgent"
        _agent(outside_agent, "escape", "outside character")
        observations = outside_agent / "observations"
        observations.mkdir()
        (observations / FRAME).write_bytes(b"\x89PNG\r\n outside-test")
        outside_sentinel = outside_agent / "outside-sentinel.txt"
        outside_sentinel.write_text("DO NOT TOUCH", encoding="utf-8")
        _link(worlds / "LinkedWorld", outside_world)
        _link(good_world / "agents" / "escape", outside_agent)

        old_worlds = wm.WORLDS_DIR
        wm.WORLDS_DIR = worlds
        try:
            client = TestClient(wm.app, raise_server_exceptions=False)
            test_valid_routes(client)
            test_world_identifiers(client, root, outside_world)
            test_agent_read_write_and_replay(client, outside_agent, outside_sentinel)
            test_recursive_delete(client, root, outside_agent, outside_sentinel)
        finally:
            wm.WORLDS_DIR = old_worlds

    if FAILURES:
        print(f"\n{len(FAILURES)} containment check(s) failed.")
        sys.exit(1)
    print("\nAll web path-containment checks passed.")


if __name__ == "__main__":
    main()
