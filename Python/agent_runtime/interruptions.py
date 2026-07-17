"""Pure, JSON-safe lifecycle operations for APC interruptions (WP9/#38).

The module deliberately has no agent, manager, clock, Unreal, or web dependency.
Its callers own timestamp selection and persist the returned JSON dictionaries.
"""
from __future__ import annotations

import copy
import json


DEFAULT_PRIORITIES = {
    "safety": 300,
    "system": 300,
    "operator_chat": 200,
    "operator": 200,
    "user": 200,
    "survey": 100,
}
QUEUED = "queued"
ACTIVE = "active"
TERMINAL = frozenset({"resolved", "declined", "cancelled", "failed"})
_STATUSES = TERMINAL | {QUEUED, ACTIVE}
_REQUIRED_TEXT = ("interrupt_id", "kind", "source", "reason", "requested_at")


def default_priority(kind: str) -> int:
    """Return the locked v1 priority for a semantic interruption kind."""
    return DEFAULT_PRIORITIES.get(str(kind or "").strip().lower(), 100)


def make_record(*, interrupt_id: str, kind: str, source: str, reason: str,
                requested_at: str, payload: dict, resume_context: dict,
                preemptible: bool, priority: int = None) -> dict:
    """Build one validated queued interruption record from JSON-safe fields."""
    resolved_priority = default_priority(kind) if priority is None else priority
    record = {
        "interrupt_id": interrupt_id,
        "kind": kind,
        "source": source,
        "reason": reason,
        "priority": resolved_priority,
        "status": QUEUED,
        "requested_at": requested_at,
        "payload": payload,
        "resume_context": resume_context,
        "preemptible": preemptible,
    }
    validated = validate_record(record)
    if validated is None:
        raise ValueError("Invalid interruption record")
    return validated


def validate_record(raw: dict) -> dict | None:
    """Return a detached valid record, or ``None`` for malformed external state.

    Unknown keys deliberately survive validation so producers can own their small
    payloads without a central schema migration.
    """
    if not isinstance(raw, dict):
        return None
    for key in _REQUIRED_TEXT:
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            return None
    priority = raw.get("priority")
    if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 1000:
        return None
    if raw.get("status") not in _STATUSES:
        return None
    if not isinstance(raw.get("payload"), dict) or not isinstance(raw.get("resume_context"), dict):
        return None
    if not isinstance(raw.get("preemptible"), bool):
        return None
    for key in ("activated_at", "resolved_at", "outcome"):
        if key in raw and not isinstance(raw[key], str):
            return None
    try:
        json.dumps(raw)
    except (TypeError, ValueError):
        return None
    return copy.deepcopy(raw)


def sanitize_state(active: dict | None, queue: list | None,
                   last_interrupt: dict | None) -> dict:
    """Fail closed on malformed persisted state and restore queue ordering."""
    clean_active = validate_record(active) if isinstance(active, dict) else None
    if clean_active is not None and clean_active["status"] != ACTIVE:
        clean_active = None

    clean_queue = []
    seen = {clean_active["interrupt_id"]} if clean_active else set()
    if isinstance(queue, list):
        for raw in queue:
            record = validate_record(raw) if isinstance(raw, dict) else None
            if (record is None or record["status"] != QUEUED
                    or record["interrupt_id"] in seen):
                continue
            seen.add(record["interrupt_id"])
            clean_queue.append(record)
    clean_queue = _ordered(clean_queue)

    clean_last = validate_record(last_interrupt) if isinstance(last_interrupt, dict) else None
    if clean_last is not None and clean_last["status"] not in TERMINAL:
        clean_last = None
    return {"active": clean_active, "queue": clean_queue, "last_interrupt": clean_last}


def offer(active: dict | None, queue: list | None, record: dict,
          activated_at: str = "", last_interrupt: dict | None = None) -> dict:
    """Offer a record: activate, queue, or safely preempt the active record."""
    state = sanitize_state(active, queue, last_interrupt)
    incoming = validate_record(record)
    if incoming is None or incoming["status"] != QUEUED:
        raise ValueError("Only a valid queued interruption may be offered")
    if incoming["interrupt_id"] in _ids(state):
        raise ValueError("Interrupt id is already active or queued")

    if state["active"] is None:
        state["active"] = _activate(incoming, activated_at)
        state["transition"] = "activated"
        return state

    current = state["active"]
    if incoming["priority"] > current["priority"] and current["preemptible"]:
        state["active"] = _activate(incoming, activated_at)
        state["queue"] = _enqueue(_queue_record(current), state["queue"])
        state["transition"] = "preempted"
        state["displaced"] = current
        return state

    state["queue"] = _enqueue(incoming, state["queue"])
    state["transition"] = "queued"
    return state


def activate_next(active: dict | None, queue: list | None, activated_at: str = "",
                  last_interrupt: dict | None = None) -> dict:
    """Activate the highest queued record when nothing is active.

    This public recovery operation keeps a persisted queue from becoming inert
    after a restart or a defer with no alternate record to receive attention.
    """
    state = sanitize_state(active, queue, last_interrupt)
    if state["active"] is not None:
        state["transition"] = "already_active"
        return state
    state["active"], state["queue"] = _promote(state["queue"], activated_at)
    state["transition"] = "activated_next" if state["active"] else "idle"
    return state


def defer(active: dict | None, queue: list | None, deferred_at: str = "",
          last_interrupt: dict | None = None) -> dict:
    """Yield active attention to the next queued record, retaining this work queued."""
    state = sanitize_state(active, queue, last_interrupt)
    if state["active"] is None:
        raise ValueError("No active interruption to defer")
    deferred = _queue_record(state["active"])
    next_active, remaining = _promote(state["queue"], deferred_at)
    if next_active is not None:
        state["active"] = next_active
        state["queue"] = _enqueue(deferred, remaining)
    else:
        # A defer with no other work must not strand the only record queued.
        resumed = activate_next(None, [deferred], deferred_at, state["last_interrupt"])
        state["active"], state["queue"] = resumed["active"], resumed["queue"]
    state["transition"] = "deferred"
    return state


def terminate(active: dict | None, queue: list | None, status: str, outcome: str,
              resolved_at: str = "", last_interrupt: dict | None = None) -> dict:
    """Terminally resolve, decline, cancel, or fail the active record, then promote."""
    if status not in TERMINAL:
        raise ValueError("Termination status must be resolved, declined, cancelled, or failed")
    state = sanitize_state(active, queue, last_interrupt)
    if state["active"] is None:
        raise ValueError("No active interruption to terminate")
    terminal = copy.deepcopy(state["active"])
    terminal["status"] = status
    if resolved_at:
        terminal["resolved_at"] = resolved_at
    if outcome:
        terminal["outcome"] = outcome
    state["active"], state["queue"] = _promote(state["queue"], resolved_at)
    state["last_interrupt"] = terminal
    state["transition"] = status
    return state


def cancel_kind(active: dict | None, queue: list | None, kind: str, outcome: str,
                resolved_at: str = "", last_interrupt: dict | None = None) -> dict:
    """Cancel active/queued records of one kind and promote surviving work."""
    state = sanitize_state(active, queue, last_interrupt)
    matching = []
    if state["active"] is not None and state["active"].get("kind") == kind:
        matching.append(state["active"])
        state["active"] = None
    remaining = []
    for record in state["queue"]:
        if record.get("kind") == kind:
            matching.append(record)
        else:
            remaining.append(record)
    state["queue"] = remaining
    if state["active"] is None:
        state["active"], state["queue"] = _promote(state["queue"], resolved_at)
    if matching:
        terminal = copy.deepcopy(matching[-1])
        terminal["status"] = "cancelled"
        if resolved_at:
            terminal["resolved_at"] = resolved_at
        if outcome:
            terminal["outcome"] = outcome
        state["last_interrupt"] = terminal
    state["transition"] = "cancelled" if matching else "unchanged"
    state["cancelled_count"] = len(matching)
    return state


def _ids(state: dict) -> set[str]:
    return ({state["active"]["interrupt_id"]} if state["active"] else set()) | {
        item["interrupt_id"] for item in state["queue"]
    }


def _ordered(queue: list[dict]) -> list[dict]:
    # Python sorting is stable, retaining insertion/FIFO order for equal priorities.
    return sorted(queue, key=lambda item: item["priority"], reverse=True)


def _enqueue(record: dict, queue: list[dict]) -> list[dict]:
    return _ordered([*queue, _queue_record(record)])


def _queue_record(record: dict) -> dict:
    queued = copy.deepcopy(record)
    queued["status"] = QUEUED
    queued.pop("activated_at", None)
    return queued


def _activate(record: dict, activated_at: str) -> dict:
    active = copy.deepcopy(record)
    active["status"] = ACTIVE
    if activated_at:
        active["activated_at"] = activated_at
    return active


def _promote(queue: list[dict], activated_at: str) -> tuple[dict | None, list[dict]]:
    if not queue:
        return None, []
    ordered = _ordered(queue)
    return _activate(ordered[0], activated_at), ordered[1:]
