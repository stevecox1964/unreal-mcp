"""Offline contracts for the generic APC interruption lifecycle (WP9/#38).

No Unreal, network, or model calls. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_interruptions.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime import interruptions  # noqa: E402


def check(label, condition):
    if not condition:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def offer(interrupt_id, priority, *, preemptible=True, kind="survey"):
    return interruptions.make_record(
        interrupt_id=interrupt_id,
        kind=kind,
        source="world",
        reason=f"reason for {interrupt_id}",
        priority=priority,
        requested_at="Day 1 09:00",
        payload={"col": 2, "row": 3},
        resume_context={"current_goal": "work"},
        preemptible=preemptible,
    )


def test_first_offer_activates_and_lower_priority_queues():
    result = interruptions.offer(None, [], offer("survey-a", 100), activated_at="T1")
    check("first offer activates", result["transition"] == "activated")
    check("active record is marked active", result["active"]["status"] == "active")
    check("activation timestamp is recorded", result["active"]["activated_at"] == "T1")

    lower = interruptions.offer(result["active"], result["queue"], offer("low", 50))
    check("lower priority stays queued", lower["transition"] == "queued")
    check("one active record remains", lower["active"]["interrupt_id"] == "survey-a")
    check("lower priority is queued", [r["interrupt_id"] for r in lower["queue"]] == ["low"])
    check("survey gets its default world-opportunity priority",
          interruptions.make_record(
              interrupt_id="default", kind="survey", source="world", reason="unknown",
              requested_at="T0", payload={}, resume_context={}, preemptible=True,
          )["priority"] == 100)


def test_preemption_and_fifo_queue_order():
    active = interruptions.offer(None, [], offer("survey-a", 100), activated_at="T1")
    preempted = interruptions.offer(active["active"], active["queue"], offer("operator", 200), activated_at="T2")
    check("higher priority preempts a preemptible record", preempted["transition"] == "preempted")
    check("preempting record is active", preempted["active"]["interrupt_id"] == "operator")
    check("displaced record returns to the queue", preempted["queue"][0]["interrupt_id"] == "survey-a")

    first = interruptions.offer(None, [], offer("a", 100), activated_at="T1")
    second = interruptions.offer(first["active"], first["queue"], offer("b", 50))
    third = interruptions.offer(second["active"], second["queue"], offer("c", 50))
    check("equal priorities keep FIFO order", [r["interrupt_id"] for r in third["queue"]] == ["b", "c"])

    locked = interruptions.offer(None, [], offer("locked", 100, preemptible=False), activated_at="T1")
    blocked = interruptions.offer(locked["active"], locked["queue"], offer("operator", 200))
    check("non-preemptible active record cannot be displaced", blocked["active"]["interrupt_id"] == "locked")
    check("blocked preemptor queues by priority", blocked["queue"][0]["interrupt_id"] == "operator")


def test_terminal_and_defer_transitions_promote_queue():
    first = interruptions.offer(None, [], offer("survey", 100), activated_at="T1")
    second = interruptions.offer(first["active"], first["queue"], offer("operator", 200))
    deferred = interruptions.defer(second["active"], second["queue"], deferred_at="T2")
    check("defer moves active record back to queued", deferred["transition"] == "deferred")
    check("defer promotes highest queued record", deferred["active"]["interrupt_id"] == "survey")
    check("deferred record stays queued", deferred["queue"][0]["interrupt_id"] == "operator")

    resolved = interruptions.terminate(deferred["active"], deferred["queue"], "resolved", "done", "T3")
    check("resolution is terminal", resolved["last_interrupt"]["status"] == "resolved")
    check("resolution records outcome", resolved["last_interrupt"]["outcome"] == "done")
    check("resolution promotes queued work", resolved["active"]["interrupt_id"] == "operator")

    retained = interruptions.offer(
        resolved["active"], resolved["queue"], offer("later", 25),
        last_interrupt=resolved["last_interrupt"],
    )
    check("later offer preserves terminal history", retained["last_interrupt"]["interrupt_id"] == "survey")
    retained_after_defer = interruptions.defer(
        retained["active"], retained["queue"], "T3.5", retained["last_interrupt"],
    )
    check("later defer preserves terminal history",
          retained_after_defer["last_interrupt"]["interrupt_id"] == "survey")

    cancelled = interruptions.terminate(resolved["active"], resolved["queue"], "cancelled", "operator left", "T4")
    check("cancellation is terminal", cancelled["last_interrupt"]["status"] == "cancelled")
    check("cancellation leaves no active work", cancelled["active"] is None)

    declined = interruptions.terminate(
        interruptions.offer(None, [], offer("decline", 100))["active"], [],
        "declined", "not now", "T5",
    )
    check("declining is terminal", declined["last_interrupt"]["status"] == "declined")


def test_activate_next_recovers_a_deferred_only_record():
    initial = interruptions.offer(None, [], offer("only", 100), activated_at="T1")
    deferred = interruptions.defer(initial["active"], initial["queue"], deferred_at="T2")
    check("defer-only record immediately returns active", deferred["active"]["interrupt_id"] == "only")
    check("defer-only record does not remain stranded queued", deferred["queue"] == [])

    recovered = interruptions.activate_next(None, [offer("queued", 100)], activated_at="T3")
    check("activate-next promotes persisted queued work", recovered["active"]["interrupt_id"] == "queued")
    check("activate-next consumes the promoted queue entry", recovered["queue"] == [])


def test_cancelling_one_kind_promotes_surviving_work():
    first = interruptions.offer(None, [], offer("survey-active", 100), activated_at="T1")
    second = interruptions.offer(first["active"], first["queue"], offer("operator", 50, kind="operator_chat"))
    third = interruptions.offer(second["active"], second["queue"], offer("survey-queued", 25))
    cancelled = interruptions.cancel_kind(
        third["active"], third["queue"], "survey", "grid changed", "T2",
    )
    check("cancelling active survey promotes surviving work",
          cancelled["active"]["interrupt_id"] == "operator")
    check("cancelling survey removes queued survey work", cancelled["queue"] == [])
    check("cancelling survey records a terminal outcome",
          cancelled["last_interrupt"]["status"] == "cancelled")


def test_invalid_records_fail_closed():
    valid = offer("ok", 100)
    malformed = {"interrupt_id": "bad", "kind": "survey", "priority": True}
    state = interruptions.sanitize_state(malformed, [valid, malformed], malformed)
    check("malformed active record is ignored", state["active"] is None)
    check("malformed queued record is ignored", [r["interrupt_id"] for r in state["queue"]] == ["ok"])
    check("malformed terminal record is ignored", state["last_interrupt"] is None)


def main():
    test_first_offer_activates_and_lower_priority_queues()
    test_preemption_and_fifo_queue_order()
    test_terminal_and_defer_transitions_promote_queue()
    test_activate_next_recovers_a_deferred_only_record()
    test_cancelling_one_kind_promotes_surviving_work()
    test_invalid_records_fail_closed()
    print("\nAll interruption lifecycle checks passed.")


if __name__ == "__main__":
    main()
