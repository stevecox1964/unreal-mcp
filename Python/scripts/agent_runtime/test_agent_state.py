"""Offline tests for the state.json config/runtime split (autonomous queue #2).

Runtime fields (last_tick_time, current_goal, bindings, ...) churn every run and
were dirtying the tracked state.json. They now persist to a separate git-ignored
runtime.json; state.json stays config-only and stable. self.state remains the
merged in-memory dict so all callers/properties are unchanged. No Unreal, no
network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_agent_state.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent import Agent   # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _scaffold(agents_dir: Path, agent_id: str, state: dict) -> None:
    d = agents_dir / agent_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (d / "character.md").write_text("c", encoding="utf-8")
    (d / "goals.md").write_text("g", encoding="utf-8")
    (d / "rules.md").write_text("r", encoding="utf-8")
    (d / "tools.json").write_text(json.dumps({"allowed_actions": ["walk_to"]}), encoding="utf-8")


CONFIG = {"tier": 2, "role": "npc", "blueprint_class": "BP_X", "tick_interval_seconds": 0,
          "start_location": [1, 2, 3]}


def test_save_splits_config_from_runtime():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        (agents_dir / "dufus").mkdir()
        merged = {**CONFIG, "last_tick_time": "T1", "current_goal": "explore",
                  "is_busy": True, "bound_unreal_actor_name": "BP_X_C_1"}
        agent = Agent("dufus", dict(merged), "c", "g", "r", ["walk_to"])
        agent._save_state(agents_dir)

        state = json.loads((agents_dir / "dufus" / "state.json").read_text())
        runtime = json.loads((agents_dir / "dufus" / "runtime.json").read_text())
        check("state.json keeps config", state["tier"] == 2 and state["blueprint_class"] == "BP_X")
        check("state.json drops runtime churn", "last_tick_time" not in state and "current_goal" not in state)
        check("state.json drops binding", "bound_unreal_actor_name" not in state)
        check("runtime.json holds the churn", runtime["last_tick_time"] == "T1"
              and runtime["current_goal"] == "explore" and runtime["is_busy"] is True)
        check("runtime.json holds the binding", runtime["bound_unreal_actor_name"] == "BP_X_C_1")


def test_state_json_is_stable_across_a_tick():
    """A tick (mark_ticked) must not change state.json's bytes — that was the churn."""
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", CONFIG)
        agent = Agent.load(agents_dir, "dufus")
        agent._save_state(agents_dir)                 # establishes config-only state.json
        before = (agents_dir / "dufus" / "state.json").read_text()
        agent.mark_ticked(agents_dir)                 # writes a runtime field
        agent.set_goal("new goal", agents_dir)
        after = (agents_dir / "dufus" / "state.json").read_text()
        check("state.json unchanged after a tick", before == after)
        check("the goal landed in runtime.json",
              json.loads((agents_dir / "dufus" / "runtime.json").read_text())["current_goal"] == "new goal")


def test_load_merges_runtime_over_config():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", {**CONFIG, "current_goal": "seed goal"})
        (agents_dir / "dufus" / "runtime.json").write_text(
            json.dumps({"current_goal": "live goal", "last_tick_time": "T9"}), encoding="utf-8")
        agent = Agent.load(agents_dir, "dufus")
        check("config loaded", agent.tier == 2 and agent.role == "npc")
        check("runtime overrides the seed", agent.current_goal == "live goal")
        check("runtime-only field present", agent.state.get("last_tick_time") == "T9")


def test_load_without_runtime_is_backward_compatible():
    """A legacy agent dir (state.json only, no runtime.json) still loads."""
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", {**CONFIG, "current_goal": "legacy", "last_tick_time": "T0"})
        agent = Agent.load(agents_dir, "dufus")
        check("legacy fields still read", agent.current_goal == "legacy")
        check("no runtime.json required", not (agents_dir / "dufus" / "runtime.json").exists())


def test_reset_runtime_clears_runtime_file():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", CONFIG)
        agent = Agent.load(agents_dir, "dufus")
        agent.mark_ticked(agents_dir)
        agent.set_goal("temp", agents_dir)
        check("runtime.json exists after activity", (agents_dir / "dufus" / "runtime.json").exists())
        agent.reset_runtime_state(agents_dir)
        rt_path = agents_dir / "dufus" / "runtime.json"
        runtime = json.loads(rt_path.read_text()) if rt_path.exists() else {}
        check("runtime timers cleared on reset", "last_tick_time" not in runtime and "current_goal" not in runtime)


def main():
    test_save_splits_config_from_runtime()
    test_state_json_is_stable_across_a_tick()
    test_load_merges_runtime_over_config()
    test_load_without_runtime_is_backward_compatible()
    test_reset_runtime_clears_runtime_file()
    print("\nAll agent-state checks passed.")


if __name__ == "__main__":
    main()
