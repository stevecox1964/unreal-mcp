# WP9 — Generic APC interruption lifecycle (#38)

**Gate:** DONE 2026-07-17. The user asked to start #38 and run it to completion after accepting
the recommended v1: one active interruption, a visible priority queue, direct-user requests above
optional surveys, and explicit resume-or-convert resolution.

**Classification:** Loop-safe Python/domain/runner work. No Unreal, PIE, paid model, C++, Blueprint,
UMG, secret, or live-world work is part of this package.

## Outcome

Every APC owns one durable, engine-neutral interruption lifecycle. Survey opportunities and future
operator chat requests enter the same priority queue instead of bypassing the scheduler through
feature-specific control flow. The active goal, schedule, and cached route remain unchanged and
inspectable while an interruption runs; resolving it returns control to normal scheduling.

This package integrates the already-built survey behavior as the first real interrupt producer and
adds a generic localhost runner API that #37 can use later. It does **not** build the chat UI, transcript
memory, ordered goals, or survey-expedition target selection (#37, #12.2, #36, and #35 respectively).

## Locked v1 decisions

1. **One active record plus a priority queue.** No nested stack. Equal priorities are FIFO.
2. **Default priorities:** safety/system `300`, operator/user `200`, survey/world opportunity `100`.
   A caller may supply a non-boolean integer override from `0..1000`; otherwise kind defaults apply.
3. **Safe preemption:** a higher-priority record may displace an active record only while the active
   record is marked `preemptible`. The displaced record returns to the queue. A survey becomes
   non-preemptible when its first deterministic movement/capture step is dispatched; later operator
   requests wait until the four-view survey reaches a terminal outcome.
4. **Agency boundary:** queueing/presenting is generic. Safety events may be mandatory; survey-priority
   policy auto-accepts survey work exactly as today. A future operator conversation auto-claims
   attention, but accepting or rejecting behavioral direction belongs to #37/#36.
5. **Resume without opaque snapshots:** `current_goal`, the daily schedule, `last_activity`, and cached
   route are not mutated. Each record stores a small JSON `resume_context` for inspection (current goal,
   schedule directive, and route destination when available). Resolution returns to the normal
   sequencer; v1 does not serialize arbitrary LLM intent.
6. **Persistence:** `active_interrupt`, ordered `interrupt_queue`, and `last_interrupt` are runtime
   fields in each APC's `runtime.json`. A normal process restart preserves them. Malformed loaded
   records are ignored by accessors and cannot block the APC.
7. **Survey recovery:** survey payload includes target `col,row`. If the process restarts after an
   active survey record was saved but before its manager-local `CellSweep` survives, the next survey
   pulse reconstructs the deterministic sweep from that target. A completed target resolves as
   already complete; an incomplete capture resolves failed and can be offered again on a later tick.
8. **Reset policy:** Restart day and Reset agents clear all interruption runtime. Regrid cancels survey
   interruptions and clears manager-local sweep state because their grid targets are invalid; unrelated
   future interrupt kinds need not be discarded by regrid.
9. **Visibility:** list/inspect surfaces expose the active record and queue count/full queue. Lifecycle
   transitions append attributed entries to the existing decision feed/log with `sim_run`, agent,
   event, and a compact interrupt snapshot.
10. **Prompt/event behavior:** an active non-survey interruption wakes a settled APC and appears as a
    grounded prompt fact that outranks the routine until resolved. Survey remains deterministic and
    LLM-free once active.
11. **Operator identity:** the generic API accepts an explicit `source`/requester string. Nothing in
    #38 hardcodes `Root`; #37 will populate it from the configured in-world identity.

## Record contract

Records are JSON dictionaries with these persisted fields:

- `interrupt_id`: non-empty stable string;
- `kind`: non-empty semantic kind (`survey`, `operator_chat`, `safety`, or future value);
- `source`: non-empty producer/requester identity;
- `reason`: non-empty grounded explanation;
- `priority`: integer `0..1000` (booleans rejected);
- `status`: `queued`, `active`, `resolved`, `declined`, `cancelled`, or `failed`;
- `requested_at`: sim/world time or UTC string supplied by the producer;
- `payload`: small JSON dictionary owned by the producer;
- `resume_context`: small JSON dictionary for inspection only;
- `preemptible`: boolean;
- optional lifecycle timestamps/outcome: `activated_at`, `resolved_at`, `outcome`.

Only `queued` records appear in `interrupt_queue`; only an `active` record appears in
`active_interrupt`; `last_interrupt` holds the latest terminal record. Unknown extra payload keys are
preserved. Invalid top-level records fail closed.

## Test-first implementation

### 1. Pure lifecycle and Agent persistence

Add `agent_runtime/interruptions.py` for record construction, validation, ordering, activation,
preemption, defer/decline/cancel, and terminal resolution using plain JSON dictionaries. `Agent` wraps
those operations and writes through to `runtime.json`.

Failing tests first must prove:

- first offer activates; lower priority queues; higher priority preempts only when allowed;
- FIFO tie ordering and exactly one active record;
- resolving promotes the highest queued record;
- deferring/declining/cancelling have explicit terminal/queued states;
- active/queue/last round-trip in `runtime.json` without changing `state.json`;
- malformed persisted records are ignored; restart/day-agent reset behavior is explicit.

### 2. Manager arbitration and survey migration

Add manager helpers to offer, inspect, dispatch, resolve, and cancel interruptions. Replace the two
`agent_id in _cell_sweeps` fast paths with “active interrupt kind is survey.” Survey start in
`_act_agent` offers a `survey` record with target cell and resume context, then dispatches the existing
`CellSweep`. `_pulse_sweep` resolves the record at completion and reconstructs missing manager-local
survey state from the persisted target after a process restart.

Tests must retain all existing #34 behavior and additionally prove:

- survey start creates an active persisted record and leaves schedule/current goal unchanged;
- deterministic continuation still performs no decision-LLM call;
- completion/failed capture resolves and normal cognition resumes next tick;
- persisted active survey reconstructs after manager-local state loss;
- Reset day/agents clear interrupts and `_cell_sweeps`; regrid cancels survey interrupts.

### 3. Cognition, inspection, runner API, and audit log

- Attach active interrupt facts to observations and render a compact `Active Interruption` prompt note.
- Active non-survey interruption counts as an event in the settled-agent cognition gate.
- `list_agents` exposes compact active/queue information; `inspect_agent` exposes active, full queue,
  and last terminal record.
- Add manager `request_interrupt` and `resolve_interrupt` methods plus runner routes/client methods.
  Request validation errors are explicit and never mutate state.
- Add `MemoryStore.record_interrupt_event` so offered, activated/preempted, deferred, resolved,
  declined, cancelled, and failed transitions are visible in the existing feed with run attribution.

Offline tests cover runner/client transport, prompt wording/priority, settled-agent wake, inspector
payloads, validation failure, and lifecycle log attribution.

## Acceptance

- One APC cannot have two active interruptions.
- Dufus's existing unknown-cell survey uses the generic persisted lifecycle, completes N/S/E/W without
  an LLM call during continuation, and returns to his unchanged schedule/goal.
- A priority-200 operator request can preempt a still-preemptible priority-100 survey offer; after the
  first survey step it queues safely until survey completion.
- A simulated process restart reconstructs an active survey from `payload.col,row`.
- A settled APC with an active generic operator request wakes cognition and sees the requester/reason
  as higher priority than its routine.
- Inspector and decision feed explain active, queued, and terminal outcomes.
- Focused tests and the full offline suite pass. Live role-play remains #37/PIE verification and must
  not be claimed by this package.

## Executor stop conditions

Stop and report rather than guessing if implementation would require changing the user's schedule or
goal semantics, serializing route internals, adding the chat UI/transcript model, running Unreal/PIE,
or broadening reset behavior beyond the decisions above.

## Completion evidence

- Pure lifecycle/persistence: `52cee1b` (`feat: persist APC interruption lifecycle`).
- Survey migration/recovery: `f77616f` (`feat: route surveys through interruption lifecycle`).
- Generic controls, cognition, visibility, and audit feed: `18056e0`
  (`feat: expose APC interruption controls`).
- Durable API-reachable survey preemption window, corrected audit attribution, and current schedule
  resume context: `485a00c` (`fix: make survey interruption preemption durable`).
- Terra's delegated final offline suite passed **49/49** in 30.6 seconds.
- No Unreal/PIE, live role-play, paid-model, C++, Blueprint, or UMG work was performed. Chat remains
  #37 and ordered/reprioritized goals remain #36.
