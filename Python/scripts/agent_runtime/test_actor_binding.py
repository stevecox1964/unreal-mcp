"""Offline tests for display-name / actor-name decoupling (child-BP rework).

An agent's placed Unreal actor may be labeled with engine plumbing
(e.g. "APC_Maren_BP"), but other agents must still know her as "Maren" — the LLM
never sees engine names ([[architecture_lizard_brain_sensing]]). So:

  - outbound: known_characters is built from Agent.display_name ("Maren").
  - inbound: a targeted action ("walk_to Maren") resolves back to the bound
    actor name the bridge needs, matching display name / actor label / agent id.

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_actor_binding.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent import Agent                   # noqa: E402
from agent_runtime.agent_manager import AgentManager    # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _agent(agent_id, state):
    return Agent(agent_id, state, "", "", "", [])


# A bound Maren whose placed actor carries the engine label, plus the clean name.
_MAREN_STATE = {
    "unreal_actor_name": "APC_Maren_BP",
    "display_name": "Maren",
    "bound_unreal_actor_name": "APC_Maren_BP_C_0",
    "bound_unreal_actor_label": "APC_Maren_BP",
}


def _manager(agents):
    mgr = AgentManager(worlds_dir=Path(tempfile.mkdtemp()), llm_router=None,
                       unreal_bridge=None, memory_store=None)
    mgr.agents = {a.agent_id: a for a in agents}
    return mgr


def test_display_name_precedence():
    check("explicit display_name wins", _agent("maren", _MAREN_STATE).display_name == "Maren")
    check("falls back to the actor-name hint when unset",
          _agent("dufus", {"unreal_actor_name": "Dufus"}).display_name == "Dufus")
    check("falls back to agent id when nothing is set",
          _agent("gus", {}).display_name == "gus")
    check("display name is decoupled from the engine actor label",
          _agent("maren", _MAREN_STATE).display_name != _agent("maren", _MAREN_STATE).bound_unreal_actor_label)


def test_known_characters_uses_display_name_not_engine_label():
    # The exact comprehension both observe paths use, for a peer of Dufus.
    mgr = _manager([_agent("dufus", {"unreal_actor_name": "Dufus",
                                     "bound_unreal_actor_name": "BP_CameraNPC_C_1",
                                     "bound_unreal_actor_label": "Dufus"}),
                    _agent("maren", _MAREN_STATE)])
    known = [a.display_name for a in mgr.agents.values()
             if a.agent_id != "dufus" and a.has_unreal_binding]
    check("peer is exposed by clean name", known == ["Maren"])
    check("engine label never leaks into known_characters", "APC_Maren_BP" not in known)


def test_target_resolves_back_to_the_bound_actor():
    mgr = _manager([_agent("maren", _MAREN_STATE)])
    check("display name resolves to the bound actor",
          mgr._actor_name_for("Maren") == "APC_Maren_BP_C_0")
    check("agent id also resolves", mgr._actor_name_for("maren") == "APC_Maren_BP_C_0")
    check("engine actor label also resolves",
          mgr._actor_name_for("APC_Maren_BP") == "APC_Maren_BP_C_0")
    check("resolution is case-insensitive", mgr._actor_name_for("MAREN") == "APC_Maren_BP_C_0")
    check("an unknown reference (e.g. the human player) does not resolve",
          mgr._actor_name_for("Sheriff Dan") is None)


def test_resolve_action_actor_refs_rewrites_targets():
    mgr = _manager([_agent("maren", _MAREN_STATE)])
    walk = mgr._resolve_action_actor_refs({"type": "walk_to", "target_actor": "Maren"})
    check("walk_to target_actor rewritten to the actor",
          walk["target_actor"] == "APC_Maren_BP_C_0")
    follow = mgr._resolve_action_actor_refs({"type": "follow_character", "target": "Maren"})
    check("follow_character target rewritten to the actor",
          follow["target"] == "APC_Maren_BP_C_0")
    passthru = mgr._resolve_action_actor_refs({"type": "walk_to", "target_actor": "some stranger"})
    check("an unknown target passes through untouched",
          passthru["target_actor"] == "some stranger")
    unbound = _manager([_agent("maren", {"unreal_actor_name": "APC_Maren_BP",
                                         "display_name": "Maren"})])  # no binding
    check("an unbound agent never resolves", unbound._actor_name_for("Maren") is None)


def main():
    test_display_name_precedence()
    test_known_characters_uses_display_name_not_engine_label()
    test_target_resolves_back_to_the_bound_actor()
    test_resolve_action_actor_refs_rewrites_targets()
    print("\nAll actor-binding checks passed.")


if __name__ == "__main__":
    main()
