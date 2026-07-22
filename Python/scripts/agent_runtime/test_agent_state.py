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
from agent_runtime import agenda, interruptions  # noqa: E402


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


def test_daily_schedule_persists_to_runtime():
    """The planner's day plan + last_activity are scratch: they belong in
    runtime.json, must not churn state.json, round-trip on reload, and clear on reset."""
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", CONFIG)
        agent = Agent.load(agents_dir, "dufus")
        agent._save_state(agents_dir)                       # config-only state.json baseline
        before = (agents_dir / "dufus" / "state.json").read_text()

        blocks = [{"start": "08:00", "end": "12:00", "activity": "work", "place": "stall"}]
        agent.set_daily_schedule(blocks, "Day 1", agents_dir)
        agent.set_last_activity("work", agents_dir)

        after = (agents_dir / "dufus" / "state.json").read_text()
        runtime = json.loads((agents_dir / "dufus" / "runtime.json").read_text())
        check("schedule does not churn state.json", before == after)
        check("schedule lands in runtime.json", runtime["daily_schedule"]["day"] == "Day 1")
        check("last_activity lands in runtime.json", runtime["last_activity"] == "work")

        reloaded = Agent.load(agents_dir, "dufus")
        check("blocks round-trip on reload", reloaded.daily_schedule_blocks[0]["activity"] == "work")
        check("day round-trips on reload", reloaded.daily_schedule_day == "Day 1")
        check("last_activity round-trips on reload", reloaded.last_activity == "work")

        reloaded.reset_runtime_state(agents_dir)
        check("reset clears the day's plan", reloaded.daily_schedule_day == "")
        check("reset clears last_activity", reloaded.last_activity == "")


def test_interruptions_persist_in_runtime_and_reset():
    """Interruption state is runtime-only, reloadable, and reset with the day."""
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", CONFIG)
        agent = Agent.load(agents_dir, "dufus")
        agent._save_state(agents_dir)
        before = (agents_dir / "dufus" / "state.json").read_text()
        survey = interruptions.make_record(
            interrupt_id="survey-1", kind="survey", source="world",
            reason="unknown cell", priority=100, requested_at="Day 1 09:00",
            payload={"col": 2, "row": 3}, resume_context={"current_goal": "work"},
            preemptible=True,
        )
        agent.offer_interrupt(survey, agents_dir, activated_at="Day 1 09:01")
        agent.offer_interrupt(interruptions.make_record(
            interrupt_id="operator-1", kind="operator_chat", source="Avery",
            reason="wants to talk", priority=50, requested_at="Day 1 09:02",
            payload={}, resume_context={}, preemptible=True,
        ), agents_dir)
        agent.offer_interrupt(interruptions.make_record(
            interrupt_id="later", kind="survey", source="world",
            reason="another cell", priority=25, requested_at="Day 1 09:03",
            payload={}, resume_context={}, preemptible=True,
        ), agents_dir)
        agent.terminate_interrupt("resolved", "survey complete", agents_dir, "Day 1 09:04")
        agent.offer_interrupt(interruptions.make_record(
            interrupt_id="after-terminal", kind="survey", source="world",
            reason="later cell", priority=10, requested_at="Day 1 09:05",
            payload={}, resume_context={}, preemptible=True,
        ), agents_dir)

        runtime = json.loads((agents_dir / "dufus" / "runtime.json").read_text())
        check("active interruption lands in runtime", runtime["active_interrupt"]["interrupt_id"] == "operator-1")
        check("interruption queue lands in runtime", runtime["interrupt_queue"][0]["interrupt_id"] == "later")
        check("terminal interruption lands in runtime", runtime["last_interrupt"]["interrupt_id"] == "survey-1")
        check("state config stays unchanged", before == (agents_dir / "dufus" / "state.json").read_text())

        reloaded = Agent.load(agents_dir, "dufus")
        check("active interruption round-trips", reloaded.active_interrupt["kind"] == "operator_chat")
        check("queue round-trips", reloaded.interrupt_queue[0]["interrupt_id"] == "later")
        check("last terminal interruption round-trips", reloaded.last_interrupt["status"] == "resolved")
        reloaded.reset_runtime_state(agents_dir)
        check("reset clears active interruption", reloaded.active_interrupt is None)
        check("reset clears interruption queue", reloaded.interrupt_queue == [])
        check("reset clears terminal interruption", reloaded.last_interrupt is None)


def test_malformed_interruptions_are_ignored_on_load():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", CONFIG)
        (agents_dir / "dufus" / "runtime.json").write_text(json.dumps({
            "active_interrupt": {"interrupt_id": "bad", "priority": True},
            "interrupt_queue": [{"interrupt_id": "also-bad"}],
            "last_interrupt": "not a record",
        }), encoding="utf-8")
        agent = Agent.load(agents_dir, "dufus")
        check("malformed active interruption cannot block agent", agent.active_interrupt is None)
        check("malformed queue records are ignored", agent.interrupt_queue == [])
        check("malformed terminal record is ignored", agent.last_interrupt is None)


def _agenda_doc(objective="work"):
    return {"schema_version": 1, "tasks": [{
        "id": "work", "start": "08:00", "end": "09:00", "place": "stall",
        "objective": objective, "completion": {"type": "time_block_ends"},
    }]}


def test_authored_agenda_load_replace_runtime_and_reset():
    """Authored agenda stays tracked; execution is runtime-only and resettable."""
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", CONFIG)
        agent_dir = agents_dir / "dufus"
        (agent_dir / "agenda.json").write_text(json.dumps(_agenda_doc()), encoding="utf-8")
        agent = Agent.load(agents_dir, "dufus")
        check("valid agenda loads", agent.authored_agenda["tasks"][0]["objective"] == "work")
        check("valid agenda has no errors", agent.agenda_errors == [])

        execution = agenda.prepare_execution(
            agent.authored_agenda, None, day="Day 1", source="authored")
        agent.set_agenda_execution(execution, agents_dir)
        config = json.loads((agent_dir / "state.json").read_text())
        runtime = json.loads((agent_dir / "runtime.json").read_text())
        check("execution is excluded from state config", "agenda_execution" not in config)
        check("execution persists in runtime", runtime["agenda_execution"]["day"] == "Day 1")

        replacement = agent.replace_authored_agenda(_agenda_doc("new work"), agents_dir)
        check("validated replacement updates tracked agenda",
              json.loads((agent_dir / "agenda.json").read_text()) == replacement)
        check("replacement invalidates old execution", agent.agenda_execution == {})
        reloaded = Agent.load(agents_dir, "dufus")
        check("replacement round-trips", reloaded.authored_agenda["tasks"][0]["objective"] == "new work")

        reloaded.set_agenda_execution(
            agenda.prepare_execution(reloaded.authored_agenda, None,
                                     day="Day 1", source="authored"), agents_dir)
        reloaded.reset_runtime_state(agents_dir)
        check("day reset clears execution", reloaded.agenda_execution == {})
        check("day reset preserves authored agenda file", (agent_dir / "agenda.json").exists())


def test_bad_authored_agenda_fails_closed_with_actionable_errors():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        _scaffold(agents_dir, "dufus", CONFIG)
        agent_dir = agents_dir / "dufus"
        (agent_dir / "agenda.json").write_text('{"tasks":[{"id":"bad"}]}', encoding="utf-8")
        agent = Agent.load(agents_dir, "dufus")
        check("invalid agenda is not activated", agent.authored_agenda is None)
        check("schema errors identify task fields",
              agent.agenda_errors and any("tasks[0]" in error for error in agent.agenda_errors))

        (agent_dir / "agenda.json").write_text('{bad json', encoding="utf-8")
        malformed = Agent.load(agents_dir, "dufus")
        check("malformed JSON is not activated", malformed.authored_agenda is None)
        check("JSON error includes location", "line" in malformed.agenda_errors[0]
              and "column" in malformed.agenda_errors[0])


def main():
    test_save_splits_config_from_runtime()
    test_daily_schedule_persists_to_runtime()
    test_state_json_is_stable_across_a_tick()
    test_load_merges_runtime_over_config()
    test_load_without_runtime_is_backward_compatible()
    test_reset_runtime_clears_runtime_file()
    test_interruptions_persist_in_runtime_and_reset()
    test_malformed_interruptions_are_ignored_on_load()
    test_authored_agenda_load_replace_runtime_and_reset()
    test_bad_authored_agenda_fails_closed_with_actionable_errors()
    print("\nAll agent-state checks passed.")


if __name__ == "__main__":
    main()
