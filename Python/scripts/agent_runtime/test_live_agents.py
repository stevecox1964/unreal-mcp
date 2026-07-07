"""Offline tests for the live agent dots on /map (#18 live half).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_live_agents.py

The observe phase records each agent's last seen position + facing (data it
already has — no extra engine traffic); the runner serves it at /positions;
the web UI proxies it at /api/map/agents; map.html draws dots. No runner (or
nothing observed yet) = no dots — the map never shows a stale guess.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient                # noqa: E402
from agent_runtime.agent_manager import AgentManager      # noqa: E402
from agent_runtime.runner_app import build_control_app    # noqa: E402
import web_ui.main as wm                                   # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# ── manager: record + report ──────────────────────────────────────────────────

class StubBridge:
    def execute_action(self, actor_name, action):
        return {"status": "accepted"}


class StubAgent:
    def __init__(self, agent_id, is_active=True):
        self.agent_id = agent_id
        self.is_active = is_active


def _manager(tmp):
    from agent_runtime.world_grid import WorldGrid
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=StubBridge(), memory_store=None)
    mgr.world_grid = WorldGrid(cell_size=400.0,
                               bounds={"min_x": -2000, "min_y": -2000,
                                       "max_x": 1999, "max_y": 1999})
    mgr.agents = {}
    return mgr


def test_record_and_report_positions():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        mgr.agents = {"maren": StubAgent("maren"),
                      "dufus": StubAgent("dufus"),
                      "ghost": StubAgent("ghost", is_active=False)}

        mgr._record_live_pos("maren", {"location": {"x": 320.0, "y": 120.0, "z": 90.0},
                                       "rotation": {"x": 0.0, "y": 45.0, "z": 0.0}})
        mgr._record_live_pos("ghost", {"location": {"x": 0.0, "y": 0.0, "z": 90.0}})
        mgr._record_live_pos("dufus", {"place": []})   # positionless tick

        out = mgr.agent_positions()
        check("only observed + active agents are reported",
              [a["agent_id"] for a in out] == ["maren"])
        a = out[0]
        check("position + facing carried", (a["x"], a["y"], a["yaw"]) == (320.0, 120.0, 45.0))
        check("grid cell derived", (a["col"], a["row"]) == (5, 5))

        # A fresher observation replaces the fix; a positionless one doesn't wipe it.
        mgr._record_live_pos("maren", {"location": {"x": 1500.0, "y": 1500.0, "z": 90.0}})
        mgr._record_live_pos("maren", {"place": []})
        a = mgr.agent_positions()[0]
        check("fresher fix replaces, positionless tick keeps the last",
              (a["x"], a["y"]) == (1500.0, 1500.0))
        check("no rotation -> yaw None", a["yaw"] is None)

        mgr._live_pos.clear()   # what start_simulation / reset_agents do per run
        check("cleared run starts with no dots", mgr.agent_positions() == [])


# ── runner: /positions ────────────────────────────────────────────────────────

class StubRunnerManager:
    def agent_positions(self):
        return [{"agent_id": "maren", "x": 1.0, "y": 2.0, "yaw": 90.0, "col": 5, "row": 5}]


def test_runner_positions_route():
    client = TestClient(build_control_app(StubRunnerManager()))
    data = client.get("/positions").json()
    check("runner serves /positions", data["agents"][0]["agent_id"] == "maren")
    check("root lists the endpoint", "/positions" in client.get("/").json()["endpoints"])


# ── web ui: /api/map/agents proxy + the map page markup ──────────────────────

class StubRunner:
    def __init__(self, agents=None, broken=False):
        self._agents, self._broken = agents or [], broken

    def positions(self):
        if self._broken:
            raise ConnectionError("no runner")
        return self._agents


def _with_runner(stub, fn):
    old = wm.get_runner
    wm.get_runner = lambda: stub
    try:
        fn(TestClient(wm.app))
    finally:
        wm.get_runner = old


def test_api_map_agents_proxy():
    agents = [{"agent_id": "maren", "x": 1.0, "y": 2.0, "yaw": None, "col": 5, "row": 5}]

    def online(client):
        data = client.get("/api/map/agents").json()
        check("proxy reports online + agents",
              data["online"] is True and data["agents"] == agents)
    _with_runner(StubRunner(agents), online)

    def offline(client):
        data = client.get("/api/map/agents").json()
        check("no runner -> honest offline, no stale dots",
              data == {"online": False, "agents": []})
    _with_runner(StubRunner(broken=True), offline)


def test_map_page_has_agents_layer():
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "TestWorld"
        (world / "agents").mkdir(parents=True)
        (world / "world_grid.json").write_text(json.dumps({
            "cell_size": 400.0,
            "bounds": {"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999},
        }), encoding="utf-8")
        old = wm.WORLDS_DIR
        wm.WORLDS_DIR = Path(tmp)
        try:
            text = TestClient(wm.app).get("/map?level=TestWorld").text
        finally:
            wm.WORLDS_DIR = old
        check("map page has the agents layer", 'id="agents"' in text)
        check("map page polls the live positions", "/api/map/agents" in text)
        check("map page styles the dots + facing tick",
              "agent-dot" in text and "agent-tick" in text)
        check("legend names the live agents", "agent (live)" in text)


def main():
    test_record_and_report_positions()
    test_runner_positions_route()
    test_api_map_agents_proxy()
    test_map_page_has_agents_layer()
    print("\nAll live-agent checks passed.")


if __name__ == "__main__":
    main()
