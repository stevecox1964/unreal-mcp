"""Offline regressions for #31 settled-agent event-driven cognition.

No Unreal, network, vision model, or decision model is used. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_event_driven_cognition.py

A stationary APC at the known place named by its already-persisted schedule is
settled. Unchanged ticks must keep sampling deterministic world state without
the old every-fourth-tick vision + decision heartbeat. Cognition resumes for
events that invalidate that settled state, while ungrounded agents retain the
anti-freeze heartbeat.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import (  # noqa: E402
    AgentManager, _STATIONARY_REDECIDE_TICKS,
)
from agent_runtime import planner  # noqa: E402
from agent_runtime.place_db import PlaceDB  # noqa: E402
from agent_runtime.world_grid import WorldGrid  # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


SCHEDULE = [{"start": "08:00", "end": "12:00",
             "activity": "sell vegetables", "place": "vegetable truck"}]


class FixedClock:
    def __init__(self, text="Day 1, 09:00"):
        self.text = text

    def now_text(self):
        return self.text


class StubBridge:
    def __init__(self, *, x=320.0, y=120.0, current_action="idle", changed=False):
        self.x = x
        self.y = y
        self.current_action = current_action
        self.changed = changed
        self.ai_states = []
        self.capture_calls = 0

    def get_character_state(self, name):
        return {"actor_name": name, "image_path": None,
                "location": {"x": self.x, "y": self.y, "z": 90.0},
                "rotation": {"y": 0.0}, "current_action": self.current_action,
                "ai_state": None}

    def capture_routine_observation(self, name, agent_id, agents_dir, state=None):
        self.capture_calls += 1
        observation = dict(state or self.get_character_state(name))
        observation["image_path"] = f"observation-{self.capture_calls}.png"
        return observation

    def get_observation(self, name, agent_id, agents_dir):
        return self.capture_routine_observation(name, agent_id, agents_dir)

    def is_scene_changed(self, agent_id, image_path):
        return self.changed

    def line_trace_forward(self, actor_name, distance_cm=300.0):
        return {"hit": False}

    def print_to_screen(self, message, key=-1, duration=30.0):
        pass

    def set_ai_state(self, actor_name, state):
        self.ai_states.append(state)
        return {"status": "accepted"}


class StubAgent:
    def __init__(self, blocks=None, last_activity="sell vegetables"):
        self.agent_id = "maren"
        self.bound_unreal_actor_name = "APC_Maren_BP_C_1"
        self.bound_unreal_actor_label = "Maren"
        self.unreal_actor_name = "Maren"
        self.display_name = "Maren"
        self.has_unreal_binding = True
        self.is_active = True
        self.is_busy = False
        self.daily_schedule_day = "Day 1"
        self.daily_schedule_blocks = list(SCHEDULE if blocks is None else blocks)
        self.last_activity = last_activity
        self.marked = 0

    def cooldown_expired(self):
        return True

    def mark_ticked(self, agents_dir):
        self.marked += 1


def _manager(tmp, bridge=None, blocks=None, last_activity="sell vegetables"):
    bridge = bridge or StubBridge()
    mgr = AgentManager(Path(tmp), llm_router=None, unreal_bridge=bridge, memory_store=None)
    mgr._agents_dir = Path(tmp) / "agents"
    (mgr._agents_dir / "maren").mkdir(parents=True)
    mgr.world_clock = FixedClock()
    mgr.world_grid = WorldGrid(
        cell_size=400.0,
        bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999},
    )
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    mgr.place_db.add_owned_place(
        "maren", 5, 5, "vegetable truck", dx=120.0, dy=-80.0, source="authored"
    )
    agent = StubAgent(blocks=blocks, last_activity=last_activity)
    mgr.agents = {"maren": agent}
    return mgr, agent, bridge


def test_settled_agent_has_no_fourth_tick_model_heartbeat():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, _ = _manager(tmp)
        original = planner.ensure_daily_plan
        planner.ensure_daily_plan = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("cheap gate must not generate a plan")
        )
        try:
            observations = [mgr._observe_agent(agent)
                            for _ in range(_STATIONARY_REDECIDE_TICKS * 2)]
        finally:
            planner.ensure_daily_plan = original
        check("settled unchanged agent never enters cognition", all(o is None for o in observations))
        check("cheap sampling still marks every tick", agent.marked == len(observations))


def test_ungrounded_agent_keeps_anti_freeze_heartbeat():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, _ = _manager(tmp, blocks=[])
        observations = [mgr._observe_agent(agent)
                        for _ in range(_STATIONARY_REDECIDE_TICKS)]
        check("ungrounded stationary agent re-decides on heartbeat",
              observations[:-1] == [None] * (_STATIONARY_REDECIDE_TICKS - 1)
              and observations[-1] is not None)


def test_schedule_transition_and_displacement_resume_cognition():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, bridge = _manager(tmp, last_activity="breakfast")
        check("schedule transition bypasses unchanged-scene suppression",
              mgr._observe_agent(agent) is not None)

        agent.last_activity = "sell vegetables"
        bridge.x, bridge.y = 1500.0, 1500.0
        check("place mismatch bypasses unchanged-scene suppression",
              mgr._observe_agent(agent) is not None)


def test_movement_and_nearby_arrival_resume_cognition():
    with tempfile.TemporaryDirectory() as tmp:
        changed = StubBridge(changed=True)
        mgr, agent, _ = _manager(tmp, bridge=changed)
        check("meaningful scene change resumes cognition", mgr._observe_agent(agent) is not None)

    with tempfile.TemporaryDirectory() as tmp:
        moving = StubBridge(current_action="moving")
        mgr, agent, _ = _manager(tmp, bridge=moving)
        check("unexpected movement while settled resumes cognition",
              mgr._observe_agent(agent) is not None)

    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, _ = _manager(tmp)
        check("settled baseline is suppressed", mgr._observe_agent(agent) is None)
        mgr._live_pos["dufus"] = {"x": 400.0, "y": 120.0, "yaw": 0.0}
        check("nearby APC arrival bypasses suppression", mgr._observe_agent(agent) is not None)


def test_mapped_place_suppresses_routine_pixel_change():
    with tempfile.TemporaryDirectory() as tmp:
        changed = StubBridge(changed=True)
        mgr, agent, _ = _manager(tmp, bridge=changed)
        mgr.place_db.record_place_image(
            "maren", 5, 5, "places/images/truck.png",
            {"N": "n.png", "S": "s.png", "E": "e.png", "W": "w.png"},
            description="Maren's vegetable truck", place_name="vegetable truck",
        )
        check("saved place visual replaces routine changed-scene VLM calls",
              mgr._observe_agent(agent) is None)
        check("settled mapped place creates no routine observation image",
              changed.capture_calls == 0)

        mgr._live_pos["dufus"] = {"x": 400.0, "y": 120.0, "yaw": 0.0}
        check("nearby event remains a separate cognition path",
              mgr._observe_agent(agent) is not None)
        check("nearby event captures exactly one observation image",
              changed.capture_calls == 1)
        check("cognition sleeps again after the one event tick",
              mgr._observe_agent(agent) is None and changed.capture_calls == 1)


async def test_manual_pulse_bypasses_settled_suppression():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, agent, _ = _manager(tmp)
        calls = []
        mgr._perceive_and_decide = lambda a, o: calls.append(o) or {"type": "idle"}
        mgr._act_agent = lambda a, d, o: {"agent_id": a.agent_id, "action": d["type"]}
        result = await mgr._pulse_agent_impl("maren")
        check("manual pulse enters cognition", len(calls) == 1)
        check("manual pulse returns the cognitive action", result["action"] == "idle")


async def test_activity_label_says_sampling_for_cheap_tick():
    with tempfile.TemporaryDirectory() as tmp:
        mgr, _, bridge = _manager(tmp)
        await mgr._tick_impl()
        check("cheap bridge phase is labelled sampling", bridge.ai_states == ["sampling"])


def main():
    test_settled_agent_has_no_fourth_tick_model_heartbeat()
    test_ungrounded_agent_keeps_anti_freeze_heartbeat()
    test_schedule_transition_and_displacement_resume_cognition()
    test_movement_and_nearby_arrival_resume_cognition()
    test_mapped_place_suppresses_routine_pixel_change()
    asyncio.run(test_manual_pulse_bypasses_settled_suppression())
    asyncio.run(test_activity_label_says_sampling_for_cheap_tick())
    print("\nAll event-driven cognition checks passed.")


if __name__ == "__main__":
    main()
