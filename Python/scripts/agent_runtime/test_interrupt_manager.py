"""Offline manager contracts for generic APC interruption control (WP9/#38)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime.agent import Agent  # noqa: E402
from agent_runtime.agent_manager import AgentManager  # noqa: E402
from agent_runtime.memory_store import MemoryStore  # noqa: E402
from agent_runtime.place_db import PlaceDB  # noqa: E402
from agent_runtime.world_grid import WorldGrid  # noqa: E402


def check(label, condition):
    if not condition:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _manager(tmp):
    agents_dir = Path(tmp) / "agents"
    memory = MemoryStore(Path(tmp))
    memory.update_agents_dir(agents_dir)
    memory.sim_run_id = "SR42"
    mgr = AgentManager(Path(tmp), llm_router=None, unreal_bridge=None, memory_store=memory)
    mgr._agents_dir = agents_dir
    mgr.agents = {"dufus": Agent("dufus", {}, "", "", "", [])}
    return mgr, mgr.agents["dufus"], memory


def test_request_resolve_visibility_and_audit():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, memory = _manager(tmp)
        invalid = mgr.request_interrupt("dufus", kind="operator_chat", source="", reason="talk")
        check("invalid request is explicit", invalid["status"] == "error" and "source" in invalid["error"])
        check("invalid request does not mutate APC", agent.active_interrupt is None)

        requested = mgr.request_interrupt(
            "dufus", kind="operator_chat", source="Avery", reason="Please meet me at the gate.",
            priority=200, payload={"topic": "gate"}, preemptible=True,
        )
        check("valid request activates", requested["status"] == "requested"
              and requested["active_interrupt"]["source"] == "Avery")
        check("list shows compact active work", mgr.list_agents()[0]["interrupt_queue_count"] == 0
              and mgr.list_agents()[0]["active_interrupt"]["kind"] == "operator_chat")
        detail = mgr.inspect_agent("dufus")
        check("inspect shows active + full queue + last", detail["active_interrupt"]["reason"].startswith("Please")
              and detail["interrupt_queue"] == [] and detail["last_interrupt"] is None)

        resolved = mgr.resolve_interrupt("dufus", status="resolved", outcome="met at gate")
        check("resolve returns terminal state", resolved["status"] == "resolved"
              and resolved["last_interrupt"]["outcome"] == "met at gate")
        events = memory.get_recent_events(10, sim_run_id="SR42")
        check("lifecycle events carry run attribution", [e["event"] for e in events]
              == ["interrupt_offered", "interrupt_activated", "interrupt_resolved"])
        check("audit event has compact snapshot", events[-1]["interrupt"]["kind"] == "operator_chat")


def test_survey_lifecycle_uses_the_same_audit_feed():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, memory = _manager(tmp)
        mgr.world_grid = WorldGrid(
            cell_size=400.0,
            bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999},
        )
        mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
        action = mgr._offer_survey_interrupt(agent, {
            "grid": {"key": "5,5", "col": 5, "row": 5},
            "location": {"x": 200.0, "y": 200.0, "z": 90.0},
            "world_time": "Day 1 09:00", "schedule": {},
        })
        check("survey offer activates deterministic work", action and action["type"] == "observe_heading")
        mgr._terminate_active_interrupt(agent, "failed", "capture incomplete", "Day 1 09:01")
        check("survey offer and terminal outcome are audited",
              [e["event"] for e in memory.get_recent_events(10)]
              == ["interrupt_offered", "interrupt_activated", "interrupt_failed"])


def main():
    test_request_resolve_visibility_and_audit()
    test_survey_lifecycle_uses_the_same_audit_feed()
    print("\nAll interrupt-manager checks passed.")


if __name__ == "__main__":
    main()
