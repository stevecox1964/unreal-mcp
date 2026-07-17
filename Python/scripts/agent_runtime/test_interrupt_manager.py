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
    (agents_dir / "dufus").mkdir(parents=True)
    memory = MemoryStore(Path(tmp))
    memory.update_agents_dir(agents_dir)
    memory.sim_run_id = "SR42"
    mgr = AgentManager(Path(tmp), llm_router=None, unreal_bridge=None, memory_store=memory)
    mgr._agents_dir = agents_dir
    mgr.agents = {"dufus": Agent("dufus", {"unreal_actor_name": "dufus"}, "", "", "",
                                  ["idle", "walk_to", "observe_heading"])}
    return mgr, mgr.agents["dufus"], memory


class _SweepBridge:
    def __init__(self, location):
        self.location = location
        self.actions = []

    def get_observation(self, actor_name, agent_id, agents_dir):
        return {"location": dict(self.location), "image_path": None,
                "current_action": "idle", "ai_state": None}

    def execute_action(self, actor_name, action):
        self.actions.append(action)
        return {"status": "accepted", "action": action.get("type")}

    def set_ai_state(self, actor_name, state):
        return {"status": "accepted"}

    def print_to_screen(self, message, key=None, duration=None):
        pass


def _survey_manager(tmp):
    mgr, agent, memory = _manager(tmp)
    mgr.world_grid = WorldGrid(
        cell_size=400.0,
        bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999},
    )
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    mgr.bridge = _SweepBridge({"x": 1500.0, "y": 1500.0, "z": 90.0})
    return mgr, agent, memory


def _idle_decision():
    return {"agent_id": "dufus", "thought_summary": "wait",
            "action": {"type": "idle"}, "importance": 0.5}


def _survey_observation():
    return {"grid": {"key": "5,5", "col": 5, "row": 5},
            "location": {"x": 1500.0, "y": 1500.0, "z": 90.0},
            "world_time": "Day 1, 09:00", "schedule": {"status": "idle"}}


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
        check("survey offer persists a pre-dispatch handoff", action and action["_survey_pending"] is True)
        mgr._terminate_active_interrupt(agent, "failed", "capture incomplete", "Day 1 09:01")
        check("survey offer and terminal outcome are audited",
              [e["event"] for e in memory.get_recent_events(10)]
              == ["interrupt_offered", "interrupt_activated", "interrupt_failed"])


def test_survey_offer_can_be_preempted_before_dispatch_then_locks():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, _ = _survey_manager(tmp)
        offer = mgr._act_agent(agent, _idle_decision(), _survey_observation())
        check("survey offer returns a durable no-op before deterministic work",
              offer["action"] == "survey_pending" and mgr.bridge.actions == [])
        check("offered survey is active and preemptible",
              agent.active_interrupt["kind"] == "survey"
              and agent.active_interrupt["preemptible"] is True)

        operator = mgr.request_interrupt(
            "dufus", kind="operator_chat", source="Avery", reason="Talk now.", priority=200,
        )
        check("higher-priority operator request preempts undispatched survey",
              operator["transition"] == "preempted"
              and agent.active_interrupt["kind"] == "operator_chat"
              and agent.interrupt_queue[0]["kind"] == "survey")

        mgr.resolve_interrupt("dufus", "resolved", "finished talking")
        step = mgr._pulse_sweep(agent)
        check("promoted survey dispatches deterministically without an LLM",
              step["sweep"] is True and mgr.bridge.actions[-1]["type"] == "walk_to")
        check("first survey action locks preemption",
              agent.active_interrupt["kind"] == "survey"
              and agent.active_interrupt["preemptible"] is False)

        queued = mgr.request_interrupt(
            "dufus", kind="operator_chat", source="Avery", reason="Wait for the sweep.", priority=200,
        )
        check("operator request queues after the first survey action locks it",
              queued["transition"] == "queued"
              and agent.active_interrupt["kind"] == "survey"
              and agent.interrupt_queue[0]["kind"] == "operator_chat")


def test_preemption_audit_names_the_displaced_interruption():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, _, memory = _manager(tmp)
        survey = mgr.request_interrupt(
            "dufus", kind="survey", source="world", reason="Map this cell.", priority=100,
        )
        operator = mgr.request_interrupt(
            "dufus", kind="operator_chat", source="Avery", reason="Talk now.", priority=200,
        )
        events = memory.get_recent_events(10, sim_run_id="SR42")
        check("preemption emits an event for the interruption displaced from attention",
              [event["event"] for event in events]
              == ["interrupt_offered", "interrupt_activated", "interrupt_offered",
                  "interrupt_preempted", "interrupt_activated"])
        check("preempted audit snapshot is the displaced survey, not the incoming operator",
              events[3]["interrupt"]["interrupt_id"]
              == survey["active_interrupt"]["interrupt_id"]
              and events[3]["interrupt"]["kind"] == "survey")
        check("following activation identifies the incoming operator",
              events[4]["interrupt"]["interrupt_id"]
              == operator["active_interrupt"]["interrupt_id"])


def test_generic_interrupt_captures_the_current_schedule_directive():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, _ = _survey_manager(tmp)
        agent.state["daily_schedule"] = {"day": "Day 1", "blocks": [
            {"start": "08:00", "end": "12:00", "activity": "sell vegetables",
             "place": "vegetable truck"},
        ]}
        agent.state["last_activity"] = "sell vegetables"
        mgr.place_db.add_owned_place(
            "dufus", 5, 5, "vegetable truck", dx=0.0, dy=0.0, source="authored",
        )
        mgr._live_pos["dufus"] = {"x": 200.0, "y": 200.0, "yaw": 0.0}
        mgr._last_grid_place["dufus"] = (
            {"key": "5,5", "col": 5, "row": 5}, ["vegetable truck"],
        )
        mgr.world_clock = type("Clock", (), {"now_text": lambda self: "Day 1, 09:00"})()

        requested = mgr.request_interrupt(
            "dufus", kind="operator_chat", source="Avery", reason="Talk at the stall.",
        )
        schedule = requested["active_interrupt"]["resume_context"]["schedule"]
        check("generic interruption captures the resolved schedule directive",
              schedule["status"] == "act" and schedule["activity"] == "sell vegetables")


def main():
    test_request_resolve_visibility_and_audit()
    test_survey_lifecycle_uses_the_same_audit_feed()
    test_survey_offer_can_be_preempted_before_dispatch_then_locks()
    test_preemption_audit_names_the_displaced_interruption()
    test_generic_interrupt_captures_the_current_schedule_directive()
    print("\nAll interrupt-manager checks passed.")


if __name__ == "__main__":
    main()
