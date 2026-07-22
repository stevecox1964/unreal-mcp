"""Offline contracts for direct APC chat and temporary operator guidance (#37)."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime.agent import Agent  # noqa: E402
from agent_runtime.agent_manager import AgentManager  # noqa: E402
from agent_runtime.llm_router import _active_interrupt_note  # noqa: E402
from agent_runtime.memory_store import MemoryStore  # noqa: E402


def check(label, condition):
    if not condition:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


class ChatLLM:
    def __init__(self):
        self.calls = []

    def chat(self, agent, transcript, context, memories):
        self.calls.append((agent.agent_id, transcript, context, memories))
        return "I am wedged by the wagon. I can try the left side."


class Bridge:
    def __init__(self):
        self.actions = []
        self.states = []

    def execute_action(self, actor_name, action):
        self.actions.append((actor_name, action))
        return {"status": "accepted"}

    def set_ai_state(self, actor_name, state):
        self.states.append((actor_name, state))
        return {"status": "accepted"}

    def print_to_screen(self, message, key=None, duration=None):
        pass


def _manager(tmp):
    agents_dir = Path(tmp) / "agents"
    (agents_dir / "dufus").mkdir(parents=True)
    memory = MemoryStore(Path(tmp))
    memory.update_agents_dir(agents_dir)
    llm = ChatLLM()
    bridge = Bridge()
    manager = AgentManager(Path(tmp), llm_router=llm, unreal_bridge=bridge,
                           memory_store=memory)
    manager._agents_dir = agents_dir
    agent = Agent("dufus", {
        "unreal_actor_name": "Dufus",
        "bound_unreal_actor_name": "BP_Dufus_1",
        "current_goal": "survey unknown cells",
    }, "A stubborn but practical surveyor.", "Map the world.", "Stay truthful.",
        ["idle", "walk_to"])
    manager.agents = {"dufus": agent}
    manager._routes["dufus"] = {"destination": "north field"}
    return manager, agent, llm, bridge


async def _exercise_chat(tmp):
    manager, agent, llm, bridge = _manager(tmp)
    opened = await manager.start_chat("dufus", "Avery")
    check("chat opens as the active generic interruption", opened["status"] == "open"
          and agent.active_interrupt["kind"] == "operator_chat")
    check("opening chat stops movement immediately",
          bridge.actions[-1] == ("BP_Dufus_1", {"type": "stop"}))
    check("prior goal and route are captured for resume",
          agent.active_interrupt["resume_context"]["current_goal"] == "survey unknown cells"
          and agent.active_interrupt["resume_context"]["route_destination"] == "north field")

    tick = await manager.tick()
    check("automatic ticks do not move or decide for an open chat",
          tick["ticked"] == 0 and len(llm.calls) == 0)

    reply = await manager.send_chat_message("dufus", "Are you stuck by the wagon?")
    messages = agent.active_interrupt["payload"]["chat"]["messages"]
    check("chat returns the APC's in-character reply", reply["status"] == "replied"
          and "wagon" in reply["reply"])
    check("both turns persist in the active interruption",
          [m["role"] for m in messages] == ["operator", "agent"])
    check("chat receives the saved resume context",
          llm.calls[-1][2]["route_destination"] == "north field")

    guided = await manager.guide_from_chat("dufus", "Back up, then go around the wagon on your left.")
    active = agent.active_interrupt
    check("guide converts chat into a temporary actionable interruption",
          guided["status"] == "guiding" and active["kind"] == "operator_direction"
          and active["payload"]["chat"]["state"] == "guiding")
    check("direction is grounded in the normal decision prompt",
          "Back up, then go around" in _active_interrupt_note(active))
    check("guidance does not overwrite the prior goal", agent.current_goal == "survey unknown cells")
    manager._execute_world_action(agent, {"type": "walk_to", "direction": "left"}, {
        "location": {"x": 100.0, "y": 200.0, "z": 90.0},
        "rotation": {"y": 0.0},
        "schedule": {"status": "travel", "place": "north field"},
    })
    guided_location = bridge.actions[-1][1].get("location") or []
    check("temporary guidance is not overwritten by scheduled route execution",
          len(guided_location) == 3 and abs(guided_location[0] - 100.0) < 0.01
          and abs(guided_location[1] + 1300.0) < 0.01
          and abs(guided_location[2] - 90.0) < 0.01)

    ended = await manager.end_chat("dufus")
    check("release resolves guidance and resumes prior work",
          ended["status"] == "resumed" and agent.active_interrupt is None
          and agent.last_interrupt["kind"] == "operator_direction")
    check("release leaves the prior goal unchanged", agent.current_goal == "survey unknown cells")


def test_direct_chat_lifecycle():
    with tempfile.TemporaryDirectory() as tmp:
        asyncio.run(_exercise_chat(tmp))


def main():
    test_direct_chat_lifecycle()
    print("\nAll direct-chat checks passed.")


if __name__ == "__main__":
    main()
