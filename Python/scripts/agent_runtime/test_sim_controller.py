"""Offline tests for the web sim controller (autonomous queue #6).

The web UI cockpit drives the standalone sim_runner over HTTP: status, start/stop,
single-tick step (debugging), and a live decision-log panel. Here the web routes
are exercised against a stub runner (no real runner, no Unreal, no network). The
real wiring to a live runner is verified in a browser. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_sim_controller.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient   # noqa: E402
import web_ui.main as wm                     # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


class StubRunner:
    def __init__(self, online=True):
        self.online = online
        self.running = False
        self.calls = []

    def status(self):
        if not self.online:
            raise RuntimeError("offline")
        return {"running": self.running, "tick_count": 7, "agent_count": 2}

    def events(self, limit=20):
        if not self.online:
            raise RuntimeError("offline")
        return [{"timestamp": "2026-06-28T18:51:43+00:00", "agent_id": "dufus",
                 "action_type": "walk_to", "thought": "to the square"}]

    def clear_events(self):
        if not self.online:
            raise RuntimeError("offline")
        self.calls.append(("clear_events",)); return {"cleared": 5}

    def start(self, tick_seconds=1, active_agents=None, mode="live"):
        self.calls.append(("start", tick_seconds, mode)); self.running = True
        return {"status": "started"}

    def stop(self):
        self.calls.append(("stop",)); self.running = False
        return {"status": "stopped"}

    def tick(self):
        self.calls.append(("tick",)); return {"ticked": 2}

    def reset_day(self):
        self.calls.append(("reset_day",)); self.running = False
        return {"status": "day_reset", "world_time": "Day 1, 08:00"}

    def reset_agents(self):
        self.calls.append(("reset_agents",))
        return {"status": "agents_reset", "agent_count": 2}

    def reset_places(self):
        self.calls.append(("reset_places",))
        return {"status": "places_reset"}

    def capture_starts(self):
        self.calls.append(("capture_starts",))
        return {"status": "captured", "captured": ["dufus", "maren"]}

    def inspect_agent(self, agent_id):
        self.calls.append(("inspect_agent", agent_id))
        return {"agent_id": agent_id, "active_interrupt": None}

    def start_chat(self, agent_id, source):
        self.calls.append(("chat_start", agent_id, source))
        return {"status": "open", "agent_id": agent_id}

    def send_chat_message(self, agent_id, message):
        self.calls.append(("chat_message", agent_id, message))
        return {"status": "replied", "reply": "I can try that."}

    def guide_from_chat(self, agent_id, direction):
        self.calls.append(("chat_guide", agent_id, direction))
        return {"status": "guiding"}

    def end_chat(self, agent_id):
        self.calls.append(("chat_end", agent_id))
        return {"status": "resumed"}

    def generate_world_grid(self, cell_size=3000.0, padding=800.0):
        if not self.online:
            raise RuntimeError("offline")
        self.calls.append(("generate_world_grid", cell_size, padding))
        return {"status": "generated", "level": "TestWorld", "actors_scanned": 3,
                "bounds": {"min_x": -1000, "min_y": -1000, "max_x": 1000, "max_y": 1000}}


def _with_runner(stub, fn):
    old = wm.get_runner
    wm.get_runner = lambda: stub
    try:
        fn(TestClient(wm.app))
    finally:
        wm.get_runner = old


def test_sim_page_renders_with_controls():
    def body(client):
        text = client.get("/sim").text
        check("sim page returns the cockpit", "Start" in text and "Stop" in text and "Step" in text)
        check("sim page has a Clear feed button", "Clear feed" in text)
        check("sim page has a Restart day button", "Restart day" in text)
        check("sim page has a Reset agents button", "Reset agents" in text)
        check("sim page has a Reset places button", "Reset places" in text)
        check("sim page has a Capture starts button", "Capture starts" in text)
        check("sim page has direct APC chat controls",
              "Direct APC chat" in text and "Guide with this" in text
              and "Resume prior work" in text)
        check("sim page renders a timestamp per event", "fmtTime(e.timestamp)" in text)
    _with_runner(StubRunner(), body)


def test_api_status_online_and_offline():
    def online(client):
        s = client.get("/api/sim/status").json()
        check("online flagged true", s["online"] is True)
        check("status proxied from runner", s["tick_count"] == 7)
    _with_runner(StubRunner(online=True), online)

    def offline(client):
        s = client.get("/api/sim/status").json()
        check("offline flagged when runner unreachable", s["online"] is False)
    _with_runner(StubRunner(online=False), offline)


def test_api_events_proxied():
    def body(client):
        evs = client.get("/api/sim/events").json()["events"]
        check("events proxied from runner", evs[0]["action_type"] == "walk_to")
        check("event carries a timestamp for the feed", evs[0]["timestamp"].startswith("2026-06-28"))
    _with_runner(StubRunner(), body)

    def offline(client):
        check("events empty when runner offline", client.get("/api/sim/events").json()["events"] == [])
    _with_runner(StubRunner(online=False), offline)


def test_clear_feed_proxied():
    stub = StubRunner()

    def body(client):
        r = client.post("/api/sim/events/clear").json()
        check("clear proxied to runner", r["cleared"] == 5)
        check("clear recorded as a call", stub.calls[-1] == ("clear_events",))
    _with_runner(stub, body)

    def offline(client):
        check("clear degrades to 0 when runner offline",
              client.post("/api/sim/events/clear").json()["cleared"] == 0)
    _with_runner(StubRunner(online=False), offline)


def test_control_actions_proxy_to_runner():
    stub = StubRunner()

    def body(client):
        check("start proxied", client.post("/api/sim/start", json={"tick_seconds": 2, "mode": "explore"}).json()["status"] == "started")
        check("start forwarded args", stub.calls[-1] == ("start", 2, "explore"))
        check("step (single tick) proxied", client.post("/api/sim/tick").json()["ticked"] == 2)
        check("restart-day proxied", client.post("/api/sim/reset_day").json()["status"] == "day_reset")
        check("reset-agents proxied", client.post("/api/sim/reset_agents").json()["status"] == "agents_reset")
        check("reset-places proxied", client.post("/api/sim/reset_places").json()["status"] == "places_reset")
        check("capture-starts proxied", client.post("/api/sim/capture_starts").json()["status"] == "captured")
        check("stop proxied", client.post("/api/sim/stop").json()["status"] == "stopped")
        check("calls recorded in order", [c[0] for c in stub.calls] ==
              ["start", "tick", "reset_day", "reset_agents", "reset_places",
               "capture_starts", "stop"])
    _with_runner(stub, body)


def test_chat_actions_proxy_to_runner():
    stub = StubRunner()

    def body(client):
        check("chat inspect proxied",
              client.get("/api/sim/agents/dufus").json()["agent_id"] == "dufus")
        check("chat start proxied",
              client.post("/api/sim/agents/dufus/chat/start",
                          json={"source": "Avery"}).json()["status"] == "open")
        check("chat message proxied",
              client.post("/api/sim/agents/dufus/chat/message",
                          json={"message": "Are you stuck?"}).json()["reply"] == "I can try that.")
        check("chat guidance proxied",
              client.post("/api/sim/agents/dufus/chat/guide",
                          json={"direction": "Go left."}).json()["status"] == "guiding")
        check("chat release proxied",
              client.post("/api/sim/agents/dufus/chat/end").json()["status"] == "resumed")
        check("chat calls preserve explicit operator content", stub.calls[-5:] == [
            ("inspect_agent", "dufus"), ("chat_start", "dufus", "Avery"),
            ("chat_message", "dufus", "Are you stuck?"),
            ("chat_guide", "dufus", "Go left."), ("chat_end", "dufus"),
        ])
    _with_runner(stub, body)


def test_world_grid_proxied():
    """#13.2: POST /api/world/grid proxies to the runner's generate_world_grid."""
    stub = StubRunner()

    def body(client):
        r = client.post("/api/world/grid").json()
        check("grid generation proxied (ok)", r["ok"] is True)
        check("grid payload passed through", r["actors_scanned"] == 3)
        check("defaults used when body omitted", stub.calls[-1] == ("generate_world_grid", 3000.0, 800.0))
    _with_runner(stub, body)

    def custom(client):
        r = client.post("/api/world/grid", json={"cell_size": 500, "padding": 100}).json()
        check("custom cell_size/padding forwarded", stub.calls[-1] == ("generate_world_grid", 500.0, 100.0))
        check("still ok", r["ok"] is True)
    _with_runner(stub, custom)

    def offline(client):
        r = client.post("/api/world/grid")
        check("unreachable runner -> 503", r.status_code == 503)
        data = r.json()
        check("unreachable runner -> ok false", data["ok"] is False)
        check("unreachable runner -> 'no sim runner running' envelope",
              data["error"] == "no sim runner running")
    _with_runner(StubRunner(online=False), offline)

    class ErrRunner(StubRunner):
        def generate_world_grid(self, cell_size=3000.0, padding=800.0):
            return {"status": "error", "error": "No actor positions returned"}

    def manager_error(client):
        r = client.post("/api/world/grid")
        check("manager-side error surfaced as ok:false", r.status_code == 400)
        check("manager-side error text passed through",
              r.json()["error"] == "No actor positions returned")
    _with_runner(ErrRunner(), manager_error)


def main():
    test_sim_page_renders_with_controls()
    test_api_status_online_and_offline()
    test_api_events_proxied()
    test_clear_feed_proxied()
    test_control_actions_proxy_to_runner()
    test_chat_actions_proxy_to_runner()
    test_world_grid_proxied()
    print("\nAll sim-controller checks passed.")


if __name__ == "__main__":
    main()
