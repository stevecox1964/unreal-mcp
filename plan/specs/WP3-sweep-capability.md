# WP3 — Sweep as a capability any APC invokes (A4 / #11.1)

**Item:** backlog A4 + #11.1 · **Decision locked (user, 2026-07-01):** the
dedicated maintenance role is **retired**. Any APC that enters a grid cell with
no central place cell **it needs now** detours to the cell center, runs the 360
sweep, drops the community breadcrumb, then **resumes its scheduled task**.
The `cell_sweep.py` state machine and `PlaceDB.mark_swept` mechanics are reused
as-is.
**Gate:** the refactor + offline tests are hands-off. Live verify (a personality
APC actually detours and sweeps in PIE) stays **B-side** — not this WP.
**Depends on:** nothing (WP1/WP2 touch a different file). **Blocks:** nothing.

## Architecture decisions (made — do not re-decide)

**D1 — What "needs now" means.** An APC needs its current cell when it is going
to *stay and use it* — i.e. its sequencer directive for this tick is `"act"`
(it's at its scheduled place) or `"idle"` (free time). An APC merely **passing
through** unexplored cells while `status == "travel"` must NOT sweep — a sweep is
8 observe-headings, and sweeping every transit cell would turn the first morning
commute into an all-day survey. (The world still fills in: destinations, homes,
and free-roam cells get swept; `mark_swept` is shared/first-wins so each cell
costs the world at most one sweep ever.)

**D2 — Where the interrupt lives.** Two hooks in `AgentManager`:

- **Start** in the act phase (`_act_agent`), because that's where
  `observation["schedule"]` is available (attached during `_perceive_and_decide`)
  and where bridge calls are legal (sequential phase). If the gate fires, the
  sweep's first sub-action **replaces the LLM's chosen action for this tick**.
  (Yes, the LLM decision for that one tick is discarded — acceptable: the gate
  fires at most once per sweep, and correctness beats the one wasted call.)
- **Continue** at the top of `tick()` / `pulse_agent`: an agent with an active
  sweep in `self._cell_sweeps` skips observe/perceive/decide entirely and runs
  one sweep step in the sequential phase — deterministic, zero LLM cost,
  exactly how the maintenance path already peeled sweeps out of the LLM phases.

**D3 — Resume is free.** No resume state is stored. When the sweep finishes
(`mark_swept`, entry removed from `_cell_sweeps`), the next tick takes the
normal path and the #10 sequencer directive re-issues travel/act — combined with
WP2's gate, the agent goes back to its routine on its own.

**D4 — What gets deleted.** The role plumbing: the maintenance split in `tick()`,
the branch in `pulse_agent`, `_pulse_maintenance`, `_maintenance_tick_action`,
and `_nearest_unexplored_target` (proactive hunting for unexplored cells was the
retired role's job — nobody hunts anymore). `Agent.is_maintenance`
(`Python/agent_runtime/agent.py` ~line 102) is deleted; `Agent.role` (~line 99)
**stays** (harmless state.json field, other roles may exist someday).

**D5 — `observe_heading` still isn't implemented in the bridge** (that's B5).
Same as today for the maintenance path: the sweep issues it, the bridge errors
gracefully, the state machine still advances and the breadcrumb still drops —
the cell is marked explored without landmarks until B5 lands. No new handling.

## Current code (verified 2026-07-01, commit `6a75e20`)

`Python/agent_runtime/agent_manager.py`:
- `tick()` ~690–698: splits `maintenance = [a for a in ready if a.is_maintenance]`,
  runs `_pulse_maintenance` for them.
- `pulse_agent()` ~735–736: `if agent.is_maintenance: return self._pulse_maintenance(agent)`.
- `_maintenance_sweep(agent_id, observation)` ~1131–1170: the reusable core —
  starts a sweep if current cell unexplored, steps it, `mark_swept` + cleanup on
  `sweep_done`. Uses `self._cell_sweeps[agent_id] = {"sweep", "col", "row"}`.
- `_nearest_unexplored_target` ~1172, `_maintenance_tick_action` ~1203,
  `_pulse_maintenance` ~1354.
- `_act_agent` ~948: validate → `_execute_world_action` → memory/episode records.

## Change

All in `agent_manager.py` (+ `agent.py` property removal, + tests).

### 1. Rename the core: `_maintenance_sweep` → `_sweep_step`

Same signature and logic, two edits:
- add a keyword `start: bool = True` — when `False`, never *start* a new sweep
  (skip the "unexplored → create" branch), only continue an active one.
- change the marker it sets from `action["_maintenance"] = "sweep"` to
  `action["_sweep_interrupt"] = True`.
- update the docstring: this is now the shared sweep capability, not a role.

### 2. New continuation pulse: `_pulse_sweep(agent)`

A trimmed copy of today's `_pulse_maintenance`: build the minimal observation
(bridge `get_observation` + grid/place + world_time — no vision, no LLM), call
`self._sweep_step(agent_id, observation, start=False)`; if it returns an action,
`_execute_world_action` it and return
`{"agent_id", "action", "result", "grid", "sweep": True}`; if it returns None
(the sweep just finished → breadcrumb dropped) return
`{"agent_id", "action": "sweep_done", "grid", "sweep": True}` and let the next
tick resume normally. `mark_ticked` in both paths.

### 3. New gate: `_should_sweep_here(observation) -> bool`

Pure, module-testable predicate on the manager:

```python
def _should_sweep_here(self, observation: dict) -> bool:
    """True when this agent needs its current cell mapped right now (D1):
    it is staying here (schedule status act/idle — not passing through),
    the cell is unexplored, and the world has a PlaceDB + bounded grid."""
```
Implementation: `sched = observation.get("schedule")`; status =
`(sched or {}).get("status")` — require `status in ("act", "idle")` **or**
`sched is None` is NOT sufficient — treat missing schedule as *no sweep* (a
degraded tick shouldn't trigger detours). Then `col,row = self._cell_col_row(observation.get("grid"))`,
require `col is not None`, `self.place_db is not None`, and
`not self.place_db.is_explored(col, row)`.

### 4. Hook the start into `_act_agent`

After `action = validate(...)` succeeds and **before** `_execute_world_action`:

```python
if self._should_sweep_here(observation):
    sweep_action = self._sweep_step(agent_id, observation, start=True)
    if sweep_action is not None:
        action = sweep_action          # this tick belongs to the sweep
```
Everything downstream (execute, memory record, episode record, mark_ticked)
stays identical — the sweep action flows through the same bookkeeping, so the
interrupt is visible in the decision log and episodes.

### 5. Hook the continuation into `tick()` and `pulse_agent()`

Replace the maintenance split in `tick()` (~690–698) with:

```python
sweeping = [a for a in ready if a.agent_id in self._cell_sweeps]
ready = [a for a in ready if a.agent_id not in self._cell_sweeps]
results = []
for agent in sweeping:
    self._set_activity(agent, "sweeping")
    results.append(self._pulse_sweep(agent))
```

Replace the branch in `pulse_agent()` (~735–736) with:

```python
if agent.agent_id in self._cell_sweeps:
    return self._pulse_sweep(agent)
```

### 6. Delete the role plumbing

- `_pulse_maintenance`, `_maintenance_tick_action`, `_nearest_unexplored_target`
  — delete.
- `Agent.is_maintenance` in `agent.py` — delete (keep `role`).
- Grep check: `grep -rn "maintenance" Python/agent_runtime/` should afterwards
  only hit comments/docstrings you intentionally left (prefer zero hits;
  reword docstrings that describe the old role, e.g. `cell_sweep.py`'s module
  docstring mention if there is one).

## Tests

Update `Python/scripts/agent_runtime/test_cell_sweep.py` (it already stubs the
manager/bridge for the maintenance path — reuse its fixtures/style; remove tests
that only exercised deleted functions) and add coverage:

1. **Gate:** `_should_sweep_here` true for `{"schedule": {"status": "act"}, ...}`
   on an unexplored cell; false when status is `"travel"`; false when schedule is
   `None`/missing; false when the cell is already explored (named OR swept);
   false with no PlaceDB.
2. **Start replaces the action:** with a stubbed bridge, an agent whose directive
   is `act` in an unexplored cell has its LLM action replaced by a
   `walk_to`-to-center (or `observe_heading` if already at center) carrying
   `_sweep_interrupt`; `self._cell_sweeps` now holds the agent.
3. **Continuation skips the LLM:** with an active sweep, `pulse_agent` returns a
   sweep step and the perceive/decide stub was **not** called.
4. **Finish:** driving steps to completion calls `PlaceDB.mark_swept` once for
   the right `(col,row)`, clears `_cell_sweeps`, and the next pulse takes the
   normal path again.
5. **Travel does not sweep:** directive `travel` through an unexplored cell —
   the LLM's action executes unchanged and `_cell_sweeps` stays empty.
6. Existing suite: `python scripts/run_tests.py` fully green; fix any test that
   referenced `is_maintenance`/`_pulse_maintenance` by updating it to the new
   model (do not weaken assertions to pass).

## Acceptance

- [x] `python scripts/run_tests.py` green. (28/28.)
- [x] `grep -rn "is_maintenance\|_pulse_maintenance\|_maintenance_tick_action\|_nearest_unexplored_target" Python/`
      → only the negative test assertion (`test_cell_sweep.py` checks the property is gone).
- [x] `plan/backlog.md`: check A4 + #11.1's offline half; note live verify stays
      B-side.
- [x] Changes confined to `agent_manager.py`, `agent.py`, tests, backlog.

## Deliberately out of scope

- Stale-cell **re**-sweeping (#11.3 — shelved by the user; the gate checks
  `is_explored`, not `is_stale`).
- `observe_heading` bridge implementation (B5, C++/editor).
- Any proactive "go find unexplored cells" behavior (retired with the role).

## Executor notes

- **Built 2026-07-01 by the architect session.** As specced (D1–D5), one addition beyond the letter of
  the spec: stub agents in `test_pacing_and_reset.py`/`test_world_grid.py` carried a dead
  `is_maintenance = False` attribute — removed. `test_cell_sweep.py`'s role/dispatch sections rewritten
  to the capability model (gate, act-phase start, LLM-free continuation, travel-does-not-sweep,
  tick routing).
