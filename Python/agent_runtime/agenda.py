"""Authored APC agendas and deterministic daily execution state (#36).

``agenda.json`` is stable, user-authored input.  Runtime task states and the
chronological ledger live separately in ``runtime.json``.  This module is pure:
callers provide time, arrival, and interruption facts, then persist the returned
JSON-safe execution document.

TEST-FLAG (#36): validate schema failures, duplicate ids, policy rejection,
atomic no-partial-write behavior, authored loading, day/revision rollover,
arrival/time/bounded-model completion, failed-action confirmation rejection,
missed-arrival blocking, interrupt/resume identity, terminal-interrupt
deduplication, and prompt context. Suggested level: offline unit coverage in
``scripts/agent_runtime``; no Unreal or model call should be required.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path

from . import planner


SCHEMA_VERSION = 1
COMPLETION_POLICIES = frozenset({
    "arrive_at_place",
    "time_block_ends",
    "time_or_llm_confirmed",
})
TASK_STATUSES = frozenset({"pending", "active", "interrupted", "completed", "blocked"})


class AgendaValidationError(ValueError):
    """Raised when an authored agenda cannot be accepted as a whole."""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def validate_document(raw: dict) -> dict:
    """Return a detached normalized v1 agenda or raise ``AgendaValidationError``.

    Validation is all-or-nothing so an editor can reject bad JSON without a
    partial write. Unknown completion policies are deliberately fatal.
    """
    errors: list[str] = []
    if not isinstance(raw, dict):
        raise AgendaValidationError(["agenda must be a JSON object"])
    version = raw.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    tasks = raw.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks must be an array")
        tasks = []

    clean: list[dict] = []
    seen: set[str] = set()
    for index, task in enumerate(tasks):
        prefix = f"tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{prefix} must be an object")
            continue
        values = {}
        for field in ("id", "start", "end", "place", "objective"):
            value = task.get(field)
            if not isinstance(value, str) or (field != "place" and not value.strip()):
                errors.append(f"{prefix}.{field} must be a non-empty string"
                              if field != "place" else f"{prefix}.place must be a string")
                values[field] = ""
            else:
                values[field] = value.strip()
        task_id = values.get("id", "")
        if task_id in seen:
            errors.append(f"{prefix}.id duplicates {task_id!r}")
        elif task_id:
            seen.add(task_id)

        try:
            start = planner.to_minutes(values.get("start", ""))
            end = planner.to_minutes(values.get("end", ""))
            if start >= end:
                errors.append(f"{prefix} start must be before end")
        except (TypeError, ValueError):
            errors.append(f"{prefix} start/end must be valid HH:MM times")

        completion = task.get("completion")
        policy = completion.get("type") if isinstance(completion, dict) else None
        if policy not in COMPLETION_POLICIES:
            errors.append(
                f"{prefix}.completion.type must be one of "
                + ", ".join(sorted(COMPLETION_POLICIES))
            )
            policy = "time_block_ends"
        if policy == "arrive_at_place" and not values.get("place"):
            errors.append(f"{prefix}.place is required for arrive_at_place")
        clean.append({
            "id": task_id,
            "start": values.get("start", ""),
            "end": values.get("end", ""),
            "place": values.get("place", ""),
            "objective": values.get("objective", ""),
            "completion": {"type": policy},
        })

    if not errors:
        clean.sort(key=lambda item: (planner.to_minutes(item["start"]),
                                     planner.to_minutes(item["end"]), item["id"]))
        for prior, current in zip(clean, clean[1:]):
            if planner.to_minutes(current["start"]) < planner.to_minutes(prior["end"]):
                errors.append(
                    f"tasks {prior['id']!r} and {current['id']!r} overlap")
    if errors:
        raise AgendaValidationError(errors)
    return {"schema_version": SCHEMA_VERSION, "tasks": clean}


def write_document(path: Path, raw: dict) -> dict:
    """Validate and atomically replace one authored agenda file.

    The destination is untouched if validation or serialization fails.
    """
    document = validate_document(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp",
                                         dir=str(path.parent), text=True)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return document


def from_schedule(blocks: list[dict]) -> dict:
    """Convert legacy generated schedule blocks into the v1 runtime contract."""
    tasks = []
    last_end = -1
    for index, block in enumerate(planner.normalize_schedule(blocks)):
        start = planner.to_minutes(block["start"])
        end = planner.to_minutes(block["end"])
        if start < last_end:
            continue
        last_end = end
        compact_start = block["start"].replace(":", "")
        tasks.append({
            "id": f"generated_{index + 1}_{compact_start}",
            "start": block["start"],
            "end": block["end"],
            "place": block.get("place", ""),
            "objective": block.get("activity", planner.FALLBACK_ACTIVITY),
            "completion": {"type": "time_block_ends"},
        })
    return validate_document({"schema_version": SCHEMA_VERSION, "tasks": tasks})


def to_schedule(document: dict) -> list[dict]:
    """Expose agenda tasks through the legacy schedule-shaped routing seam."""
    return [{
        "id": task["id"],
        "start": task["start"],
        "end": task["end"],
        "activity": task["objective"],
        "objective": task["objective"],
        "place": task["place"],
        "completion": copy.deepcopy(task["completion"]),
    } for task in document.get("tasks", [])]


def revision(document: dict) -> str:
    """Stable content identity used to reset stale runtime execution safely."""
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def prepare_execution(document: dict, runtime: dict | None, *, day: str,
                      source: str) -> dict:
    """Reconcile runtime state with the authored day and agenda revision."""
    expected_ids = [task["id"] for task in document.get("tasks", [])]
    if not _execution_matches(runtime, day, source, revision(document), expected_ids):
        return {
            "schema_version": SCHEMA_VERSION,
            "day": day,
            "source": source,
            "agenda_revision": revision(document),
            "tasks": [{"task_id": task_id, "status": "pending"}
                      for task_id in expected_ids],
            "ledger": [],
            "recorded_interrupts": [],
        }
    return copy.deepcopy(runtime)


def advance(document: dict, runtime: dict | None, *, day: str, source: str,
            minute: int, world_time: str, active_interrupt: dict | None = None,
            last_interrupt: dict | None = None, at_place_task_id: str = "",
            at_place: bool | None = None, llm_confirmed_task_id: str = "",
            llm_confirmation_evidence: dict | None = None) -> dict:
    """Advance one agenda from grounded facts and return execution + active task.

    ``at_place`` applies only when ``at_place_task_id`` still owns attention,
    preventing an arrival fact for one task from completing a successor task.
    """
    execution = prepare_execution(document, runtime, day=day, source=source)
    task_by_id = {task["id"]: task for task in document.get("tasks", [])}
    state_by_id = {state["task_id"]: state for state in execution["tasks"]}
    _record_terminal_interrupt(execution, last_interrupt, world_time)

    # Time is authoritative even if the process was asleep across a boundary.
    for task in document.get("tasks", []):
        state = state_by_id[task["id"]]
        if state["status"] in {"completed", "blocked", "interrupted"}:
            continue
        policy = task["completion"]["type"]
        if (state["status"] == "active" and policy == "arrive_at_place"
                and state.get("interrupted_at")):
            # Arrival work resumes exactly after an interruption even when its
            # original window elapsed; only an explicit reprioritization may
            # abandon that suspended destination.
            continue
        if planner.to_minutes(task["end"]) <= minute:
            if state["status"] == "pending":
                _transition(execution, state, task, "blocked", world_time,
                            {"type": "time_window_missed", "ended_at": task["end"]})
            elif policy in {"time_block_ends", "time_or_llm_confirmed"}:
                _transition(execution, state, task, "completed", world_time,
                            {"type": "time_block_ended", "at": task["end"]})
            else:
                _transition(execution, state, task, "blocked", world_time,
                            {"type": "arrival_window_missed", "place": task["place"]})

    active_state = next((state for state in execution["tasks"]
                         if state["status"] in {"active", "interrupted"}), None)
    if active_state is None:
        active_state = next((state for state in execution["tasks"]
                             if state["status"] == "pending"
                             and planner.to_minutes(task_by_id[state["task_id"]]["start"]) <= minute
                             < planner.to_minutes(task_by_id[state["task_id"]]["end"])), None)
        if active_state is not None:
            _transition(execution, active_state, task_by_id[active_state["task_id"]],
                        "active", world_time, {"type": "start_time_reached"})

    if active_state is not None:
        task = task_by_id[active_state["task_id"]]
        if isinstance(active_interrupt, dict):
            if active_state["status"] != "interrupted":
                _transition(execution, active_state, task, "interrupted", world_time, {
                    "type": "interruption",
                    "interrupt_id": active_interrupt.get("interrupt_id"),
                    "kind": active_interrupt.get("kind"),
                })
        elif active_state["status"] == "interrupted":
            _transition(execution, active_state, task, "active", world_time,
                        {"type": "interruption_resolved"})

        if active_state["status"] == "active":
            policy = task["completion"]["type"]
            if (policy == "arrive_at_place" and task["id"] == at_place_task_id
                    and at_place is True):
                _transition(execution, active_state, task, "completed", world_time, {
                    "type": "arrived_at_place", "place": task["place"],
                })
            elif (policy == "time_or_llm_confirmed"
                  and task["id"] == llm_confirmed_task_id):
                _transition(execution, active_state, task, "completed", world_time, {
                    "type": "llm_confirmed", "task_id": task["id"],
                    **(copy.deepcopy(llm_confirmation_evidence)
                       if isinstance(llm_confirmation_evidence, dict) else {}),
                })

    active_state = next((state for state in execution["tasks"]
                         if state["status"] in {"active", "interrupted"}), None)
    if active_state is None:
        # An early completion may expose another already-eligible task.
        active_state = next((state for state in execution["tasks"]
                             if state["status"] == "pending"
                             and planner.to_minutes(task_by_id[state["task_id"]]["start"]) <= minute
                             < planner.to_minutes(task_by_id[state["task_id"]]["end"])), None)
        if active_state is not None:
            _transition(execution, active_state, task_by_id[active_state["task_id"]],
                        "active", world_time, {"type": "prior_task_completed"})

    active_task = (copy.deepcopy(task_by_id[active_state["task_id"]])
                   if active_state is not None else None)
    return {"execution": execution, "active_task": active_task,
            "context": context(document, execution, active_interrupt=active_interrupt)}


def context(document: dict, execution: dict, *, active_interrupt: dict | None = None) -> dict:
    """Build authoritative Today-so-far / Right-now / Next structured facts."""
    task_by_id = {task["id"]: task for task in document.get("tasks", [])}
    state_by_id = {state["task_id"]: state for state in execution.get("tasks", [])}
    active_state = next((state for state in execution.get("tasks", [])
                         if state.get("status") in {"active", "interrupted"}), None)
    active_task = task_by_id.get(active_state["task_id"]) if active_state else None
    next_task = next((task for task in document.get("tasks", [])
                      if state_by_id.get(task["id"], {}).get("status") == "pending"), None)
    waiting = active_task is None and next_task is not None
    return {
        "today_so_far": copy.deepcopy(execution.get("ledger", [])),
        "right_now": ({
            "task_id": active_task["id"],
            "status": active_state["status"],
            "objective": active_task["objective"],
            "place": active_task["place"],
            "completion": copy.deepcopy(active_task["completion"]),
            "active_interrupt": (copy.deepcopy(active_interrupt)
                                 if isinstance(active_interrupt, dict) else None),
        } if active_task else {
            "task_id": None, "status": "waiting" if waiting else "idle",
            "objective": "", "place": "",
            "active_interrupt": (copy.deepcopy(active_interrupt)
                                 if isinstance(active_interrupt, dict) else None),
        }),
        "next": ({
            "task_id": next_task["id"], "objective": next_task["objective"],
            "place": next_task["place"], "activates_at": next_task["start"],
            "activation_condition": "start time reached and all earlier tasks are terminal",
        } if next_task else None),
    }


def prompt_text(facts: dict | None) -> str:
    """Render the three compact authoritative prompt sections."""
    facts = facts or {}
    ledger = facts.get("today_so_far") or []
    terminal = [entry for entry in ledger
                if entry.get("event") in {"completed", "blocked", "interruption_resolved"}]
    today_lines = []
    for entry in terminal[-8:]:
        label = entry.get("objective") or entry.get("kind") or entry.get("task_id") or "work"
        today_lines.append(f"- {entry.get('world_time', '?')}: {entry['event']} — {label}")
    right = facts.get("right_now") or {}
    if right.get("task_id"):
        right_line = (f"Task {right.get('task_id')} — {right.get('status')}: "
                      f"{right.get('objective')}"
                      + (f" at {right.get('place')}" if right.get("place") else "")
                      + f". Arrival: {right.get('arrival_verdict', 'unknown')}."
                      + f" Completion: {(right.get('completion') or {}).get('type', 'unknown')}.")
        route = right.get("route")
        if isinstance(route, dict):
            right_line += (f" Route leg {route.get('leg', '?')} of {route.get('total', '?')}"
                           f" toward cell {route.get('to_cell', '?')}.")
    else:
        right_line = ("Waiting for the next agenda task; stay here and do not begin free-goal work."
                      if right.get("status") == "waiting"
                      else "No agenda task is active; all eligible agenda work is terminal.")
    nxt = facts.get("next")
    next_line = (f"{nxt['objective']}"
                 + (f" at {nxt['place']}" if nxt.get("place") else "")
                 + f"; activates when {nxt['activation_condition']} "
                   f"(not before {nxt['activates_at']})."
                 if nxt else "No unfinished agenda task remains.")
    return ("## Today so far\n" + ("\n".join(today_lines) if today_lines else "Nothing completed or blocked yet.")
            + "\n\n## Right now\n" + right_line
            + "\n\n## Next\n" + next_line)


def _transition(execution: dict, state: dict, task: dict, status: str,
                world_time: str, evidence: dict) -> None:
    if status not in TASK_STATUSES or state.get("status") == status:
        return
    state["status"] = status
    timestamp_field = {
        "active": "activated_at", "interrupted": "interrupted_at",
        "completed": "completed_at", "blocked": "blocked_at",
    }.get(status)
    if timestamp_field:
        state[timestamp_field] = world_time
    if status in {"completed", "blocked"}:
        state["evidence"] = copy.deepcopy(evidence)
    event = "resumed" if status == "active" and state.get("interrupted_at") else status
    execution["ledger"].append({
        "world_time": world_time,
        "event": event,
        "task_id": task["id"],
        "objective": task["objective"],
        "evidence": copy.deepcopy(evidence),
    })


def _record_terminal_interrupt(execution: dict, record: dict | None, world_time: str) -> None:
    if not isinstance(record, dict) or record.get("status") not in {
        "resolved", "declined", "cancelled", "failed",
    }:
        return
    interrupt_id = str(record.get("interrupt_id") or "").strip()
    if not interrupt_id or interrupt_id in execution["recorded_interrupts"]:
        return
    execution["recorded_interrupts"].append(interrupt_id)
    execution["ledger"].append({
        "world_time": record.get("resolved_at") or world_time,
        "event": "interruption_resolved",
        "interrupt_id": interrupt_id,
        "kind": record.get("kind"),
        "status": record.get("status"),
        "outcome": record.get("outcome", ""),
    })


def _execution_matches(runtime: dict | None, day: str, source: str,
                       expected_revision: str, expected_ids: list[str]) -> bool:
    if not isinstance(runtime, dict):
        return False
    if (runtime.get("schema_version") != SCHEMA_VERSION or runtime.get("day") != day
            or runtime.get("source") != source
            or runtime.get("agenda_revision") != expected_revision):
        return False
    states = runtime.get("tasks")
    if (not isinstance(states, list) or any(not isinstance(state, dict) for state in states)
            or [state.get("task_id") for state in states] != expected_ids):
        return False
    if any(state.get("status") not in TASK_STATUSES for state in states):
        return False
    return isinstance(runtime.get("ledger"), list) and isinstance(
        runtime.get("recorded_interrupts"), list)
