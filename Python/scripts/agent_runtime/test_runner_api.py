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
        self.tick_busy = False
        self.pulse_busy = False

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
        if self.tick_busy:
            return {"status": "busy", "active_entry": "automatic_tick"}
        return {"ticked": 2}

    async def restart_day(self) -> dict:
        self.calls.append(("restart_day",))
        self.running = False
        return {"status": "day_reset", "world_time": "Day 1, 08:00", "stopped_simulation": True}

    # ── Director surface (#3/2.4 — the MCP tools attach through these) ──────────

    async def pause_simulation(self) -> dict:
        self.calls.append(("pause",))
        return {"status": "paused"}

    async def resume_simulation(self) -> dict:
        self.calls.append(("resume",))
        return {"status": "resumed"}

    def list_agents(self) -> list:
        return [{"agent_id": "dufus"}, {"agent_id": "maren"}]

    def inspect_agent(self, agent_id: str) -> dict:
        return {"agent_id": agent_id, "tier": 2}

    def set_agent_goal(self, agent_id: str, goal: str) -> dict:
        self.calls.append(("set_goal", agent_id, goal))
        return {"status": "updated", "agent_id": agent_id, "goal": goal}

    def request_interrupt(self, agent_id: str, **request) -> dict:
        self.calls.append(("request_interrupt", agent_id, request))
        return {"status": "requested", "agent_id": agent_id,
                "active_interrupt": {"kind": request["kind"], "source": request["source"]}}

    def resolve_interrupt(self, agent_id: str, status: str, outcome: str) -> dict:
        self.calls.append(("resolve_interrupt", agent_id, status, outcome))
        return {"status": status, "agent_id": agent_id,
                "last_interrupt": {"status": status, "outcome": outcome}}

    async def start_chat(self, agent_id: str, source: str) -> dict:
        self.calls.append(("chat_start", agent_id, source))
        return {"status": "open", "agent_id": agent_id}

    async def send_chat_message(self, agent_id: str, message: str) -> dict:
        self.calls.append(("chat_message", agent_id, message))
        return {"status": "replied", "agent_id": agent_id, "reply": "I hear you."}

    async def guide_from_chat(self, agent_id: str, direction: str) -> dict:
        self.calls.append(("chat_guide", agent_id, direction))
        return {"status": "guiding", "agent_id": agent_id}

    async def end_chat(self, agent_id: str) -> dict:
        self.calls.append(("chat_end", agent_id))
        return {"status": "resumed", "agent_id": agent_id}

    async def pulse_agent(self, agent_id: str) -> dict:
        self.calls.append(("pulse", agent_id))
        if self.pulse_busy:
            return {"status": "busy", "active_entry": "automatic_tick"}
        return {"agent_id": agent_id, "action": "idle"}

    async def reset_agents(self) -> dict:
        self.calls.append(("reset_agents",))
        return {"status": "reset"}

    async def reset_world_places(self) -> dict:
        self.calls.append(("reset_places",))
        return {"status": "reset", "tables": ["place_cells"]}

    def resync(self) -> dict:
        self.calls.append(("resync",))
        return {"status": "resynced", "level": "TestWorld"}

    def capture_start_transforms(self) -> dict:
        self.calls.append(("capture_starts",))
        return {"status": "captured", "captured": ["dufus", "maren"]}

    def generate_world_grid(self, cell_size: float = 400.0, padding: float = 800.0) -> dict:
        self.calls.append(("world_grid", cell_size, padding))
        return {"status": "generated", "level": "TestWorld"}

    async def regrid_world(self, level: str, origin_x: float, origin_y: float) -> dict:
        self.calls.append(("regrid", level, origin_x, origin_y))
        return {"status": "regridded", "level": level,
                "origin_x": origin_x, "origin_y": origin_y}


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


def test_director_routes():
    """The #3/2.4 surface: everything the MCP simulation tools need over HTTP."""
    mgr = StubManager()
    client = TestClient(build_control_app(mgr))

    check("pause proxies the manager", client.post("/pause").json()["status"] == "paused")
    check("resume proxies the manager", client.post("/resume").json()["status"] == "resumed")
    check("agents lists loaded agents",
          [a["agent_id"] for a in client.get("/agents").json()["agents"]] == ["dufus", "maren"])
    check("agent detail proxies inspect", client.get("/agents/dufus").json()["tier"] == 2)

    r = client.post("/agents/dufus/goal", json={"goal": "greet the player"})
    check("goal route forwards agent + goal", mgr.calls[-1] == ("set_goal", "dufus", "greet the player"))
    check("goal route returns the update", r.json()["goal"] == "greet the player")

    request = client.post("/agents/dufus/interruptions", json={
        "kind": "operator_chat", "source": "Avery", "reason": "talk at gate",
        "priority": 200, "payload": {"topic": "gate"},
    })
    check("interrupt request route forwards explicit requester",
          request.json()["active_interrupt"]["source"] == "Avery"
          and mgr.calls[-1][0:2] == ("request_interrupt", "dufus"))
    resolved = client.post("/agents/dufus/interruptions/resolve", json={
        "status": "resolved", "outcome": "met at gate",
    })
    check("interrupt resolve route forwards terminal outcome",
          resolved.json()["last_interrupt"]["outcome"] == "met at gate"
          and mgr.calls[-1] == ("resolve_interrupt", "dufus", "resolved", "met at gate"))

    check("chat start route", client.post("/agents/dufus/chat/start", json={
        "source": "Avery"}).json()["status"] == "open"
        and mgr.calls[-1] == ("chat_start", "dufus", "Avery"))
    check("chat message route", client.post("/agents/dufus/chat/message", json={
        "message": "Are you stuck?"}).json()["reply"] == "I hear you."
        and mgr.calls[-1] == ("chat_message", "dufus", "Are you stuck?"))
    check("chat guide route", client.post("/agents/dufus/chat/guide", json={
        "direction": "Go around the wagon."}).json()["status"] == "guiding"
        and mgr.calls[-1] == ("chat_guide", "dufus", "Go around the wagon."))
    check("chat end route", client.post("/agents/dufus/chat/end").json()["status"] == "resumed"
        and mgr.calls[-1] == ("chat_end", "dufus"))

    check("per-agent tick pulses now", client.post("/agents/maren/tick").json()["agent_id"] == "maren")
    check("pulse recorded", mgr.calls[-1] == ("pulse", "maren"))

    check("reset_agents proxies", client.post("/reset_agents").json()["status"] == "reset")
    check("reset_places proxies", client.post("/reset_places").json()["tables"] == ["place_cells"])
    check("resync proxies", client.post("/resync").json()["status"] == "resynced")
    check("capture starts proxies", client.post("/capture_starts").json()["status"] == "captured")

    r = client.post("/world_grid", json={"cell_size": 500.0, "padding": 100.0})
    check("world_grid forwards args", mgr.calls[-1] == ("world_grid", 500.0, 100.0))
    check("world_grid defaults on empty body (30 m district cells)",
          client.post("/world_grid").status_code == 200
          and mgr.calls[-1] == ("world_grid", 3000.0, 800.0))
    check("regrid forwards level and logical origin",
          client.post("/regrid", json={"level": "TestWorld", "origin_x": -1000,
                                       "origin_y": 500}).json()["status"] == "regridded"
          and mgr.calls[-1] == ("regrid", "TestWorld", -1000.0, 500.0))


def test_runner_client_director_methods():
    mgr = StubManager()
    rc = RunnerClient(client=TestClient(build_control_app(mgr)))

    check("client.pause", rc.pause()["status"] == "paused")
    check("client.resume", rc.resume()["status"] == "resumed")
    check("client.agents returns the list", rc.agents()[0]["agent_id"] == "dufus")
    check("client.inspect_agent", rc.inspect_agent("maren")["agent_id"] == "maren")
    check("client.set_agent_goal", rc.set_agent_goal("dufus", "patrol")["goal"] == "patrol")
    check("client.request_interrupt forwards requester",
          rc.request_interrupt("dufus", "operator_chat", "Avery", "talk")["status"] == "requested"
          and mgr.calls[-1][0:2] == ("request_interrupt", "dufus"))
    check("client.resolve_interrupt forwards terminal outcome",
          rc.resolve_interrupt("dufus", "resolved", "talked")["last_interrupt"]["outcome"] == "talked")
    check("client.start_chat", rc.start_chat("dufus", "Avery")["status"] == "open")
    check("client.send_chat_message",
          rc.send_chat_message("dufus", "Help?")["reply"] == "I hear you.")
    check("client.guide_from_chat",
          rc.guide_from_chat("dufus", "Step left.")["status"] == "guiding")
    check("client.end_chat", rc.end_chat("dufus")["status"] == "resumed")
    check("client.pulse_agent", rc.pulse_agent("dufus")["agent_id"] == "dufus")
    check("client.reset_agents", rc.reset_agents()["status"] == "reset")
    check("client.reset_places", rc.reset_places()["status"] == "reset")
    check("client.resync", rc.resync()["status"] == "resynced")
    check("client.capture_starts", rc.capture_starts()["captured"] == ["dufus", "maren"])
    check("client.generate_world_grid forwards args",
          rc.generate_world_grid(cell_size=250.0)["status"] == "generated"
          and mgr.calls[-1] == ("world_grid", 250.0, 800.0))
    check("client.regrid forwards the committed origin",
          rc.regrid("TestWorld", -1000.0, 500.0)["status"] == "regridded"
          and mgr.calls[-1] == ("regrid", "TestWorld", -1000.0, 500.0))


def test_start_defaults():
    mgr = StubManager()
    client = TestClient(build_control_app(mgr))
    client.post("/start", json={})  # empty body -> manager defaults
    check("empty start uses manager defaults", mgr.calls[-1] == ("start", 1, (), "live"))


def test_start_rejects_invalid_cadence():
    mgr = StubManager()
    client = TestClient(build_control_app(mgr))
    calls_before = list(mgr.calls)

    for value in (0, -1, "not-a-number"):
        response = client.post("/start", json={"tick_seconds": value})
        check(f"start rejects tick_seconds={value!r}", response.status_code == 400)
        check("invalid cadence never reaches manager", mgr.calls == calls_before)


def test_interrupt_request_rejects_invalid_body():
    mgr = StubManager()
    client = TestClient(build_control_app(mgr))
    calls_before = list(mgr.calls)
    response = client.post("/agents/dufus/interruptions", json={
        "kind": "operator_chat", "source": "", "reason": "talk",
    })
    check("request rejects missing requester", response.status_code == 400)
    check("invalid request never reaches manager", mgr.calls == calls_before)


def test_tick_conflicts_return_409():
    mgr = StubManager()
    client = TestClient(build_control_app(mgr))
    mgr.tick_busy = True
    whole = client.post("/tick")
    check("busy whole tick returns HTTP conflict", whole.status_code == 409)
    check("busy whole tick keeps manager payload", whole.json()["active_entry"] == "automatic_tick")

    mgr.pulse_busy = True
    pulse = client.post("/agents/dufus/tick")
    check("busy agent pulse returns HTTP conflict", pulse.status_code == 409)


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
    test_director_routes()
    test_runner_client_director_methods()
    test_start_defaults()
    test_start_rejects_invalid_cadence()
    test_interrupt_request_rejects_invalid_body()
    test_tick_conflicts_return_409()
    test_runner_client_round_trip()
    test_runner_client_is_running_helper()
    test_sim_runner_create_app_wires_offline()
    print("\nAll runner-api checks passed.")


if __name__ == "__main__":
    main()
