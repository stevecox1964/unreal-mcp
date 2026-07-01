"""Offline tests for the standalone sim runner's control API + client (queue #3).

The runner lets the simulation run independent of Claude/MCP, driven over a
localhost HTTP control surface (status/start/stop/tick). Here we test the route
handlers and the client end-to-end against an in-process ASGI app — no real
socket, no Unreal, no LLM. The live run (uvicorn + a real AgentManager bound to
Unreal) is exercised in PIE, not here. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_runner_api.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient                # noqa: E402
from agent_runtime.runner_app import build_control_app   # noqa: E402
from agent_runtime.runner_client import RunnerClient      # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


class StubManager:
    """Stand-in for AgentManager — mirrors its REAL control method names
    (get_status/recent_events/start_simulation/stop_simulation/tick), records
    calls, no Unreal."""
    def __init__(self):
        self.running = False
        self.calls = []

    def get_status(self) -> dict:
        return {"running": self.running, "tick_count": 3, "agent_count": 2}

    def recent_events(self, limit: int = 20) -> list:
        return [{"agent_id": "dufus", "action_type": "walk_to"}][:limit]

    def clear_events(self) -> int:
        self.calls.append(("clear_events",))
        return 4

    async def start_simulation(self, tick_seconds=1, active_agents=None, mode="live") -> dict:
        self.calls.append(("start", tick_seconds, tuple(active_agents or []), mode))
        self.running = True
        return {"status": "started", "mode": mode, "tick_seconds": tick_seconds,
                "active_agents": active_agents or []}

    async def stop_simulation(self) -> dict:
        self.calls.append(("stop",))
        self.running = False
        return {"status": "stopped", "ticks": 5}

    async def tick(self) -> dict:
        self.calls.append(("tick",))
        return {"ticked": 2}

    async def restart_day(self) -> dict:
        self.calls.append(("restart_day",))
        self.running = False
        return {"status": "day_reset", "world_time": "Day 1, 08:00", "stopped_simulation": True}


def test_control_app_routes():
    mgr = StubManager()
    client = TestClient(build_control_app(mgr))

    check("root gives a friendly pointer (no bare 404)", client.get("/").status_code == 200)
    check("root names the service", client.get("/").json()["service"] == "Unreal World Sim runner")
    check("health endpoint", client.get("/health").json()["ok"] is True)
    check("status proxies the manager", client.get("/status").json()["tick_count"] == 3)

    r = client.post("/start", json={"tick_seconds": 2, "mode": "explore", "active_agents": ["dufus"]})
    check("start returns 200", r.status_code == 200)
    check("start forwarded args to the manager",
          mgr.calls[-1] == ("start", 2, ("dufus",), "explore"))
    check("status reflects running after start", client.get("/status").json()["running"] is True)

    check("tick proxies the manager", client.post("/tick").json()["ticked"] == 2)
    check("events endpoint returns the decision log",
          client.get("/events").json()["events"][0]["action_type"] == "walk_to")
    check("events respects the limit", client.get("/events?limit=0").json()["events"] == [])
    check("events/clear proxies the manager", client.post("/events/clear").json()["cleared"] == 4)
    check("clear recorded as a manager call", mgr.calls[-1] == ("clear_events",))

    r = client.post("/reset_day")
    check("reset_day proxies the manager", r.json()["status"] == "day_reset")
    check("reset_day reports the morning time", r.json()["world_time"] == "Day 1, 08:00")
    check("reset_day recorded as a manager call", mgr.calls[-1] == ("restart_day",))

    check("stop returns the manager result", client.post("/stop").json()["ticks"] == 5)
    check("status reflects stopped", client.get("/status").json()["running"] is False)


def test_start_defaults():
    mgr = StubManager()
    client = TestClient(build_control_app(mgr))
    client.post("/start", json={})  # empty body -> manager defaults
    check("empty start uses manager defaults", mgr.calls[-1] == ("start", 1, (), "live"))


def test_runner_client_round_trip():
    """RunnerClient drives the same app in-process (TestClient as its transport)."""
    mgr = StubManager()
    rc = RunnerClient(client=TestClient(build_control_app(mgr)))

    check("client.health", rc.health()["ok"] is True)
    check("client.status", rc.status()["agent_count"] == 2)

    started = rc.start(tick_seconds=3, mode="live", active_agents=["maren"])
    check("client.start returns started", started["status"] == "started")
    check("client.start forwarded args", mgr.calls[-1] == ("start", 3, ("maren",), "live"))

    check("client.tick", rc.tick()["ticked"] == 2)
    check("client.events returns the log list", rc.events()[0]["action_type"] == "walk_to")
    check("client.reset_day restarts from morning", rc.reset_day()["status"] == "day_reset")
    check("client.reset_day forwarded", mgr.calls[-1] == ("restart_day",))
    check("client.stop", rc.stop()["status"] == "stopped")


def test_runner_client_is_running_helper():
    mgr = StubManager()
    rc = RunnerClient(client=TestClient(build_control_app(mgr)))
    check("not running initially", rc.is_running() is False)
    rc.start()
    check("running after start", rc.is_running() is True)


def test_sim_runner_create_app_wires_offline():
    """sim_runner.create_app() builds the control app over a real (factory-wired)
    manager with no I/O — /health responds without ever touching Unreal."""
    import sim_runner
    app = sim_runner.create_app()
    client = TestClient(app)
    check("create_app serves /health", client.get("/health").json()["ok"] is True)
    check("create_app exposes /status route",
          any(getattr(r, "path", None) == "/status" for r in app.routes))


def main():
    test_control_app_routes()
    test_start_defaults()
    test_runner_client_round_trip()
    test_runner_client_is_running_helper()
    test_sim_runner_create_app_wires_offline()
    print("\nAll runner-api checks passed.")


if __name__ == "__main__":
    main()
