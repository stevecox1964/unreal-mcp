"""Offline tests for the B7 forward path sense (pawn avoidance, engine-agnostic).

Stubs Unreal entirely (no network, no vision). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_blocker_sense.py

The bug: agents walk *through* people during walk_to — pawn-vs-pawn collision is
invisible to the navmesh, and the old blocker sense only fired after the agent
was already wedged (stuck). The fix is cognitive, not engine steering (no RVO):

  1. While moving, the lizard brain traces ahead every tick; a *mobile* category
     (person/animal/vehicle) becomes a blocker fact on the observation.
  2. A mobile blocker forces a re-decide (the scene-unchanged gate must not skip
     the LLM) so the agent can step around before the collision.
  3. Structures ahead while traveling stay silent (ordinary navmesh business);
     when stuck, whatever is ahead is reported (unchanged behavior).
  4. The prompt renders the facts (_sense_note) and carries the mind-level
     doctrine: step around, don't walk through.

B7b (personal space): the ~9 s tick cadence is too slow to stop a walk once
someone is close, so inside _STANDOFF_CM the lizard brain halts the walk itself
(motor reflex, not a decision), attaches blocker.halted, and the forced
re-decide lets the LLM choose from a whole-person-in-frame distance.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import llm_router                                    # noqa: E402
from agent_runtime.agent_manager import (                               # noqa: E402
    AgentManager, _AHEAD_TRACE_CM, _STANDOFF_CM, _STUCK_TICKS, _STUCK_TRACE_CM,
)


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


class TraceBridge:
    """Stub bridge: fixed observation, scriptable forward trace, unchanged scene."""

    def __init__(self, current_action="moving", hit=None):
        self.current_action = current_action
        self.hit = hit                    # None = no hit, else dict returned on trace
        self.trace_calls: list[float] = []  # distances requested
        self.actions: list[dict] = []       # execute_action payloads (reflex stops)

    def get_observation(self, name, agent_id, agents_dir):
        return {"actor_name": name, "image_path": None,
                "location": {"x": 100.0, "y": 200.0, "z": 90.0},
                "current_action": self.current_action, "ai_state": None}

    def line_trace_forward(self, actor_name, distance_cm=300.0):
        self.trace_calls.append(distance_cm)
        return dict(self.hit) if self.hit else {"hit": False}

    def execute_action(self, actor_name, action):
        self.actions.append(action)
        return {"status": "accepted"}

    def is_scene_changed(self, agent_id, image_path):
        return False  # always unchanged — exercises the skip gate

    def print_to_screen(self, message, key=-1, duration=30.0):
        pass

    def set_ai_state(self, actor_name, state):
        return {"status": "accepted"}


class StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.bound_unreal_actor_name = f"BP_{agent_id}"
        self.bound_unreal_actor_label = agent_id
        self.unreal_actor_name = agent_id
        self.has_unreal_binding = True
        self.is_active = True

    def mark_ticked(self, agents_dir):
        pass


def _manager(tmp, bridge):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=bridge, memory_store=None)
    mgr._agents_dir = Path(tmp) / "agents"
    agent = StubAgent("dufus")
    mgr.agents = {"dufus": agent}
    return mgr, agent


def test_person_ahead_while_moving_is_a_fact_and_forces_redecide():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = TraceBridge(hit={"hit": True, "actor_name": "BP_Maren_2",
                                  "actor_class": "BP_CameraNPC_C", "distance_cm": 210.0})
        mgr, agent = _manager(tmp, bridge)
        obs = mgr._observe_agent(agent)
        check("moving tick traced ahead", len(bridge.trace_calls) == 1)
        check("proactive trace uses the travel distance",
              bridge.trace_calls[0] == _AHEAD_TRACE_CM)
        check("observation returned despite unchanged scene (re-decide forced)",
              obs is not None)
        check("person blocker attached", (obs.get("blocker") or {}).get("category") == "person")
        check("blocker distance carried", obs["blocker"]["distance_cm"] == 210.0)
        check("not flagged stuck (first tick just seeds position)", obs.get("stuck") is False)
        check("inside standoff -> reflex stop issued (B7b)",
              bridge.actions == [{"type": "stop"}])
        check("halt reported as a fact", obs["blocker"].get("halted") is True)


def test_person_beyond_standoff_is_a_fact_but_no_reflex_stop():
    with tempfile.TemporaryDirectory() as tmp:
        distance = _STANDOFF_CM + 100.0     # seen coming, still outside personal space
        bridge = TraceBridge(hit={"hit": True, "actor_name": "BP_Maren_2",
                                  "actor_class": "BP_CameraNPC_C", "distance_cm": distance})
        mgr, agent = _manager(tmp, bridge)
        obs = mgr._observe_agent(agent)
        check("distant person still attaches the blocker fact",
              (obs.get("blocker") or {}).get("distance_cm") == distance)
        check("re-decide still forced beyond the standoff", obs is not None)
        check("no reflex stop beyond the standoff (B7b)", bridge.actions == [])
        check("no halted fact beyond the standoff", "halted" not in obs["blocker"])


def test_structure_ahead_while_moving_stays_silent():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = TraceBridge(hit={"hit": True, "actor_name": "SM_Wall_14",
                                  "actor_class": "StaticMeshActor", "distance_cm": 300.0})
        mgr, agent = _manager(tmp, bridge)
        obs = mgr._observe_agent(agent)
        check("structure while traveling attaches no blocker", obs is None or "blocker" not in obs)
        check("moving + unchanged scene still skips the LLM", obs is None)


def test_idle_agent_never_traces():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = TraceBridge(current_action="idle",
                             hit={"hit": True, "actor_name": "BP_Maren_2",
                                  "actor_class": "BP_CameraNPC_C", "distance_cm": 100.0})
        mgr, agent = _manager(tmp, bridge)
        mgr._observe_agent(agent)
        check("no forward trace when not moving", len(bridge.trace_calls) == 0)


def test_stuck_still_reports_any_category():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = TraceBridge(hit={"hit": True, "actor_name": "SM_Fence_3",
                                  "actor_class": "StaticMeshActor", "distance_cm": 120.0})
        mgr, agent = _manager(tmp, bridge)
        obs = None
        for _ in range(_STUCK_TICKS + 1):   # same position every tick → wedged
            obs = mgr._observe_agent(agent)
        check("wedged agent flagged stuck", obs is not None and obs.get("stuck") is True)
        check("stuck reports the structure too",
              (obs.get("blocker") or {}).get("category") == "structure")
        check("stuck trace uses the stuck distance", bridge.trace_calls[-1] == _STUCK_TRACE_CM)
        check("structure inside standoff triggers no reflex stop (mobile only)",
              bridge.actions == [])


def test_apc_child_bp_classifies_as_person():
    # The user's child blueprints (APC_BP) carry no "npc"/"character" substring —
    # they must still read as a person or avoidance goes silent for them.
    from agent_runtime.agent_manager import _classify_blocker
    check("APC child BP is a person", _classify_blocker("APC_BP_2", "APC_BP_C") == "person")


def test_sense_note_renders_facts_only():
    note = llm_router._sense_note({"blocker": {"category": "person", "distance_cm": 210.0}})
    check("blocker renders without stuck", "person 210 cm directly ahead" in note)
    check("no stuck line when not stuck", "not advanced" not in note)
    check("no halt line when not halted", "halted" not in note)

    note = llm_router._sense_note(
        {"blocker": {"category": "person", "distance_cm": 210.0, "halted": True}})
    check("reflex halt renders as a fact", "your walk has been halted" in note)

    note = llm_router._sense_note({"stuck": True})
    check("stuck renders without blocker", "not advanced" in note)

    note = llm_router._sense_note(
        {"stuck": True, "blocker": {"category": "vehicle", "distance_cm": 90.0}})
    check("both senses render together",
          "not advanced" in note and "vehicle 90 cm directly ahead" in note)
    check("sense lines are facts, not advice", "should" not in note and "go around" not in note)

    check("no senses -> empty note", llm_router._sense_note({}) == "")


def test_prompt_carries_sense_slot_and_doctrine():
    tpl = llm_router._USER_TEMPLATE_VISION
    check("template has the sense slot", "{sense_note}" in tpl)
    check("doctrine: never walk through", "Never walk through a person" in tpl)
    check("doctrine: sidestep then continue",
          "step around" in tpl and "continue to your destination" in tpl)
    check("doctrine: halted means close enough (B7b)",
          "do not walk\ncloser" in tpl or "do not walk closer" in tpl.replace("\n", " "))


def main():
    test_person_ahead_while_moving_is_a_fact_and_forces_redecide()
    test_person_beyond_standoff_is_a_fact_but_no_reflex_stop()
    test_structure_ahead_while_moving_stays_silent()
    test_idle_agent_never_traces()
    test_stuck_still_reports_any_category()
    test_apc_child_bp_classifies_as_person()
    test_sense_note_renders_facts_only()
    test_prompt_carries_sense_slot_and_doctrine()
    print("\nAll blocker-sense checks passed.")


if __name__ == "__main__":
    main()
