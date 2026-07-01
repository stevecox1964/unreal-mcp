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
        check("stop proxied", client.post("/api/sim/stop").json()["status"] == "stopped")
        check("calls recorded in order", [c[0] for c in stub.calls] == ["start", "tick", "reset_day", "stop"])
    _with_runner(stub, body)


def main():
    test_sim_page_renders_with_controls()
    test_api_status_online_and_offline()
    test_api_events_proxied()
    test_clear_feed_proxied()
    test_control_actions_proxy_to_runner()
    print("\nAll sim-controller checks passed.")


if __name__ == "__main__":
    main()
