"""Offline coverage for #36 authored agendas and deterministic execution.

No Unreal, provider, network, or paid model call is used.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime import agenda, interruptions, planner  # noqa: E402
from agent_runtime.agent import Agent  # noqa: E402
from agent_runtime.agent_manager import AgentManager  # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def raises_validation(raw):
    try:
        agenda.validate_document(raw)
    except agenda.AgendaValidationError:
        return True
    return False


def task(task_id, start, end, policy="time_block_ends", place="square",
         objective=None):
    return {
        "id": task_id,
        "start": start,
        "end": end,
        "place": place,
        "objective": objective or task_id.replace("_", " "),
        "completion": {"type": policy},
    }


def document(*tasks):
    return agenda.validate_document({"schema_version": 1, "tasks": list(tasks)})


def advance(doc, runtime=None, *, hhmm="08:00", day="Day 1", **facts):
    return agenda.advance(
        doc, runtime,
        day=day,
        source="authored",
        minute=planner.to_minutes(hhmm),
        world_time=f"{day}, {hhmm}",
        **facts,
    )


def state(result, task_id):
    return next(item for item in result["execution"]["tasks"]
                if item["task_id"] == task_id)


def test_schema_validation_and_normalization():
    doc = document(
        task("later", "09:00", "10:00"),
        task("first", "08:00", "09:00", "arrive_at_place", "home"),
    )
    check("schema version retained", doc["schema_version"] == 1)
    check("tasks sort deterministically", [t["id"] for t in doc["tasks"]] == ["first", "later"])
    check("unknown root shape rejected", raises_validation([]))
    check("missing tasks rejected", raises_validation({"schema_version": 1}))
    check("unknown schema version rejected",
          raises_validation({"schema_version": 2, "tasks": []}))
    check("duplicate ids rejected", raises_validation({"tasks": [
        task("same", "08:00", "09:00"), task("same", "09:00", "10:00")]}))
    check("bad times rejected", raises_validation({"tasks": [
        task("bad", "25:00", "09:00")]}))
    check("reversed window rejected", raises_validation({"tasks": [
        task("bad", "10:00", "09:00")]}))
    check("overlap rejected", raises_validation({"tasks": [
        task("one", "08:00", "10:00"), task("two", "09:00", "11:00")]}))
    check("unknown completion policy rejected", raises_validation({"tasks": [
        task("bad", "08:00", "09:00", "guess")]}))
    check("arrival requires a place", raises_validation({"tasks": [
        task("bad", "08:00", "09:00", "arrive_at_place", "")]}))


def test_atomic_write_and_legacy_conversion():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "agenda.json"
        good = document(task("work", "08:00", "09:00"))
        written = agenda.write_document(path, good)
        before = path.read_bytes()
        check("atomic writer returns normalized document", written == good)
        check("atomic writer creates valid JSON", json.loads(path.read_text()) == good)
        try:
            agenda.write_document(path, {"tasks": [task("bad", "08:00", "09:00", "unknown")]})
        except agenda.AgendaValidationError:
            pass
        check("invalid replacement leaves prior file byte-identical", path.read_bytes() == before)
        check("failed write leaves no temporary files", list(path.parent.glob(".agenda.json.*.tmp")) == [])

    legacy = agenda.from_schedule([
        {"start": "08:00", "end": "10:00", "activity": "A", "place": "square"},
        {"start": "09:00", "end": "09:30", "activity": "overlap", "place": "square"},
        {"start": "10:00", "end": "11:00", "activity": "B", "place": "market"},
    ])
    check("legacy conversion drops overlapping later block",
          [t["objective"] for t in legacy["tasks"]] == ["A", "B"])
    check("legacy conversion uses time completion",
          all(t["completion"]["type"] == "time_block_ends" for t in legacy["tasks"]))


def test_arrival_progression_waiting_and_time_completion():
    doc = document(
        task("travel", "08:00", "08:30", "arrive_at_place", "village square"),
        task("work", "08:30", "09:00", "time_block_ends", "village square"),
    )
    active = advance(doc, hhmm="08:05")
    check("first eligible task activates", state(active, "travel")["status"] == "active")
    arrived = advance(doc, active["execution"], hhmm="08:10",
                      at_place_task_id="travel", at_place=True)
    check("grounded arrival completes exact task", state(arrived, "travel")["status"] == "completed")
    check("arrival evidence retained", state(arrived, "travel")["evidence"]["place"] == "village square")
    check("future successor stays pending", state(arrived, "work")["status"] == "pending")
    check("context says wait between tasks", arrived["context"]["right_now"]["status"] == "waiting")
    started = advance(doc, arrived["execution"], hhmm="08:30")
    check("successor activates at its start", state(started, "work")["status"] == "active")
    ended = advance(doc, started["execution"], hhmm="09:00")
    check("active time block completes at end", state(ended, "work")["status"] == "completed")
    check("all terminal means free agenda idle", ended["context"]["right_now"]["status"] == "idle")


def test_missed_windows_block_and_day_revision_reset():
    doc = document(task("early", "06:00", "07:00"), task("now", "08:00", "09:00"))
    result = advance(doc, hhmm="08:00")
    check("never-activated elapsed task blocks", state(result, "early")["status"] == "blocked")
    check("missed-window evidence is explicit",
          state(result, "early")["evidence"]["type"] == "time_window_missed")
    check("current task still activates", state(result, "now")["status"] == "active")

    day2 = advance(doc, result["execution"], hhmm="08:00", day="Day 2")
    check("new day creates a fresh execution ledger",
          day2["execution"]["day"] == "Day 2" and len(day2["execution"]["ledger"]) == 2)
    changed = document(task("replacement", "08:00", "09:00"))
    revised = advance(changed, day2["execution"], hhmm="08:00", day="Day 2")
    check("agenda revision resets stale task ids",
          [s["task_id"] for s in revised["execution"]["tasks"]] == ["replacement"])


def test_model_confirmation_is_exact_and_evidenced():
    doc = document(task("breakfast", "08:00", "09:00",
                        "time_or_llm_confirmed", "home"))
    active = advance(doc, hhmm="08:05")
    wrong = advance(doc, active["execution"], hhmm="08:10",
                    llm_confirmed_task_id="other",
                    llm_confirmation_evidence={"statement": "wrong"})
    check("wrong task id cannot complete", state(wrong, "breakfast")["status"] == "active")
    done = advance(doc, wrong["execution"], hhmm="08:11",
                   llm_confirmed_task_id="breakfast",
                   llm_confirmation_evidence={"statement": "Ate breakfast", "action_type": "idle"})
    check("matching model confirmation completes opt-in task",
          state(done, "breakfast")["status"] == "completed")
    check("bounded model statement retained",
          state(done, "breakfast")["evidence"]["statement"] == "Ate breakfast")


def interrupt(status="active"):
    record = interruptions.make_record(
        interrupt_id="survey:1,2", kind="survey", source="world",
        reason="survey cell", requested_at="Day 1, 08:10", payload={},
        resume_context={"agenda": {"task_id": "travel"}}, preemptible=True,
    )
    record["status"] = status
    if status == "active":
        record["activated_at"] = "Day 1, 08:10"
    else:
        record["resolved_at"] = "Day 1, 08:50"
        record["outcome"] = "survey completed"
    return record


def test_interrupt_resume_and_terminal_ledger_dedup():
    doc = document(task("travel", "08:00", "08:30", "arrive_at_place", "square"))
    active = advance(doc, hhmm="08:05")
    paused = advance(doc, active["execution"], hhmm="08:10", active_interrupt=interrupt())
    check("interrupt suspends exact active task", state(paused, "travel")["status"] == "interrupted")
    still_paused = advance(doc, paused["execution"], hhmm="08:45", active_interrupt=interrupt())
    check("interrupted arrival does not expire", state(still_paused, "travel")["status"] == "interrupted")
    resumed = advance(doc, still_paused["execution"], hhmm="08:50",
                      last_interrupt=interrupt("resolved"))
    check("resolved interrupt resumes same overdue arrival task",
          state(resumed, "travel")["status"] == "active")
    check("terminal interrupt recorded once", len(resumed["execution"]["recorded_interrupts"]) == 1)
    again = advance(doc, resumed["execution"], hhmm="08:51",
                    last_interrupt=interrupt("resolved"))
    terminal_events = [e for e in again["execution"]["ledger"]
                       if e["event"] == "interruption_resolved"]
    check("terminal interrupt ledger deduplicates", len(terminal_events) == 1)
    arrived = advance(doc, again["execution"], hhmm="08:52",
                      at_place_task_id="travel", at_place=True)
    check("resumed overdue arrival can still complete", state(arrived, "travel")["status"] == "completed")


def test_context_and_prompt_are_authoritative_and_bounded():
    doc = document(task("work", "08:00", "09:00"), task("next", "09:00", "10:00"))
    result = advance(doc, hhmm="08:00")
    result["context"]["right_now"].update({
        "arrival_verdict": "at_place",
        "route": {"leg": 1, "total": 2, "to_cell": [4, 5]},
    })
    text = agenda.prompt_text(result["context"])
    check("prompt renders all authoritative headings",
          all(h in text for h in ("## Today so far", "## Right now", "## Next")))
    check("right now includes exact task id/policy", "Task work" in text and "time_block_ends" in text)
    check("route facts appear", "Route leg 1 of 2" in text and "[4, 5]" in text)
    check("next activation condition appears", "all earlier tasks are terminal" in text)


def scaffold_agent(agents_dir, agent_id="dufus"):
    d = agents_dir / agent_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text("{}", encoding="utf-8")
    for name in ("character.md", "goals.md", "rules.md"):
        (d / name).write_text(name, encoding="utf-8")
    (d / "tools.json").write_text(json.dumps({"allowed_actions": ["idle"]}), encoding="utf-8")
    return d


class Clock:
    def now_text(self):
        return "Day 1, 08:10"


def manager_for(agents_dir):
    manager = AgentManager.__new__(AgentManager)
    manager._agents_dir = agents_dir
    manager.world_clock = Clock()
    manager.llm = None
    manager.place_db = None
    return manager


def confirmation_fixture(agents_dir):
    doc = document(task("breakfast", "08:00", "09:00",
                        "time_or_llm_confirmed", "home"))
    execution = advance(doc, hhmm="08:00")["execution"]
    agent = Agent("dufus", {"agenda_execution": execution}, "c", "g", "r", ["idle"], doc, [])
    observation = {
        "world_time": "Day 1, 08:10",
        "agenda": agenda.context(doc, execution),
        "schedule": {},
    }
    observation["agenda"]["right_now"]["arrival_verdict"] = "at_place"
    return doc, agent, observation


def test_manager_bounded_confirmation_boundary():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        scaffold_agent(agents_dir)
        manager = manager_for(agents_dir)
        _doc, agent, observation = confirmation_fixture(agents_dir)
        claim = {"task_completion": {
            "task_id": "breakfast", "confirmed": True, "evidence": "Breakfast eaten"}}
        accepted = manager._apply_task_completion_confirmation(
            agent, claim, {"type": "idle"}, {"status": "success"}, observation)
        check("manager accepts exact grounded successful claim", accepted)
        check("manager persists completed execution",
              agent.agenda_execution["tasks"][0]["status"] == "completed")

        _doc, agent, observation = confirmation_fixture(agents_dir)
        observation["agenda"]["right_now"]["arrival_verdict"] = "not_at_place"
        check("manager rejects claim away from required place", not manager._apply_task_completion_confirmation(
            agent, claim, {"type": "idle"}, {"status": "success"}, observation))
        _doc, agent, observation = confirmation_fixture(agents_dir)
        check("manager rejects claim after failed action", not manager._apply_task_completion_confirmation(
            agent, claim, {"type": "idle"}, {"status": "error", "error": "failed"}, observation))
        _doc, agent, observation = confirmation_fixture(agents_dir)
        agent.state["active_interrupt"] = interrupt()
        check("manager rejects claim during interruption", not manager._apply_task_completion_confirmation(
            agent, claim, {"type": "idle"}, {"status": "success"}, observation))


def test_manager_syncs_display_goal_and_holds_between_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp)
        scaffold_agent(agents_dir)
        manager = manager_for(agents_dir)
        doc = document(
            task("travel", "08:00", "08:30", "arrive_at_place", "square"),
            task("work", "08:30", "09:00", "time_block_ends", "square"),
        )
        agent = Agent("dufus", {}, "c", "g", "r", ["idle"], doc, [])
        directive = manager._advance_agenda(
            agent, {"world_time": "Day 1, 08:05", "place": []},
            doc, "authored", seed_if_unknown=False)
        check("active task synchronizes legacy displayed current_goal",
              agent.current_goal == "travel" and directive["task_id"] == "travel")

        arrived = advance(doc, agent.agenda_execution, hhmm="08:10",
                          at_place_task_id="travel", at_place=True)
        agent.set_agenda_execution(arrived["execution"], agents_dir)
        waiting = manager._advance_agenda(
            agent, {"world_time": "Day 1, 08:10", "place": ["square"]},
            doc, "authored", seed_if_unknown=False)
        check("between-task directive holds instead of enabling free goals",
              waiting["agenda_status"] == "waiting" and waiting["status"] == "act")
        check("waiting state synchronizes displayed current_goal",
              agent.current_goal.startswith("wait for work at 08:30"))


def test_repository_authored_agendas_validate():
    world_agents = ROOT / "worlds" / "MCP_World" / "agents"
    for agent_id in ("dufus", "maren"):
        raw = json.loads((world_agents / agent_id / "agenda.json").read_text(encoding="utf-8"))
        doc = agenda.validate_document(raw)
        check(f"{agent_id} authored agenda validates", doc["tasks"] and doc["schema_version"] == 1)


def main():
    test_schema_validation_and_normalization()
    test_atomic_write_and_legacy_conversion()
    test_arrival_progression_waiting_and_time_completion()
    test_missed_windows_block_and_day_revision_reset()
    test_model_confirmation_is_exact_and_evidenced()
    test_interrupt_resume_and_terminal_ledger_dedup()
    test_context_and_prompt_are_authoritative_and_bounded()
    test_manager_bounded_confirmation_boundary()
    test_manager_syncs_display_goal_and_holds_between_tasks()
    test_repository_authored_agendas_validate()
    print("\nAll agenda checks passed.")


if __name__ == "__main__":
    main()
