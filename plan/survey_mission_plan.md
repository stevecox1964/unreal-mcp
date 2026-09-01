# PLAN: Survey Mission Mode — making coverage a code job, not an LLM judgment job

**Written:** 2026-08-29 (analysis of SR1–SR54 + code + `world_places.db`)
**Status:** Approved direction — not yet built.
**For the implementing LLM.** Read this first, then `MASTER_PLAN.md` §"For the Next
Session of Me", then `plan/backlog.md` "THE EXIT CONDITION". The code is ground
truth; this is the heading. Evidence for every claim is in the SR logs and the
sources cited.

---

## Why this plan exists (the diagnosis, compressed)

After ~54 runs (SR1–SR54, 2026-06 → 2026-08-29), survey coverage is **20 of 150
cells (13.3%)** (`world_places.db`: 20 rows with `swept_at`, grid 15×10).
The machinery works — SR54 (2026-08-29) ran zero errors, hop plans executed
end-to-end (`walk plan: east 87 m in 6 hops` → `all hops walked`), and Dufus made
a pre-emptive reasoned detour around a dumpster. The **throughput ceiling is
structural**, not a bug list:

1. **The survey is LLM-governed, not LLM-advised.** Every hop, sweep decision,
   and retry runs through the decision LLM. Nothing in that loop guarantees
   convergence; the backlog SR32→SR47 is a record of reactive fixes to wedges,
   bounces, re-refusals, and stalls. Explore mode (README "Explore Mode") already
   proved deterministic frontier-walking + VLM labeling works — verified live
   2026-06-07 — but live mode re-imported per-tick LLM judgment into what is a
   control problem, and the project has paid for that ever since.
2. **Resolution mismatch.** The VLM returns quantized prose
   (`bearing: left|center|right`, `distance: near|mid|far` —
   `perception.py` `_PROMPT`), while locomotion needs metric truth: SR46 found
   "a patch is 9 m across; a step is ~15 m — he cannot aim finer than the trap is
   wide." Items #81/#86/#90 built a locomotion controller out of prompt-facts.
   **The VLM must own semantics ("that is a corn field, name it"), never
   geometry ("the gap is on my left").**
3. **Perception is thrown away.** Probe results (blocker/radar/open_columns) are
   re-derived every run. `cell_ground` (48 rows) and `no_go_patches` (14 rows)
   are the first durable geometry tables — right idea, arrived months late.
4. **Cost structure.** One surveyed cell costs ≥5 ticks, 4 VLM calls, 2+
   decision calls, 7–16 s effective tick, with a 17-section decision prompt per
   hop. Judgment adds the least value exactly where the surveyor pays the most.

### The re-division of authority (the thesis, one paragraph)

> **Code decides** coverage (which cell, which hop, which heading —
> deterministic). **The LLM decides** meaning (one strategic checkpoint per
> cell: name places, refuse ground, adjust priorities). **The VLM labels**
> every frame, and the recorder keeps every label — the survey is a
> *data-collection job for the future VLM*, which is exactly what
> THE EXIT CONDITION says the survey is for.

This honors the existing doctrine: **"facts, not blockers" still governs
personality APCs**; mission mode is a **role**, like today's `maintenance` role —
not a new global controller. Dufus-the-surveyor becomes a mission executor;
Maren never changes.

## Durable invariants (unchanged — do not "fix" these)

- Personality APCs keep the full cognitive loop. Nothing here touches their tick.
- Facts-not-blockers governs LLM-governed agents. Mission mode is a **different
  authority regime**: code drives, LLM advises at checkpoints. State this in the
  code and docs so nobody "restores balance" later.
- Fail loud: skipped ground, failed headings, unmatched actors — recorded,
  never hidden.
- Offline tests first (suite is 65/65 — keep it green), live verification per SR.
- Behavior lives in authored files; code supplies senses. Mission mode is a
  *scheduling regime*, not a personality.

## Non-goals (do not do these)

- **#87** (lizard-brain-as-LLM) stays parked — it doubles per-tick cost to close
  gaps this plan closes for free.
- **Phase B** (#66/#67/#68) stays blocked until THE EXIT CONDITION is met.
- **#84** (prompt payload contract) does not widen beyond the mission checkpoint
  prompt while a live-run lane is open.
- No new navigation subsystem. Reuse cell_sweep, frontier machinery, refusals,
  hop plans, body-box, reflex stops.

---

## Phase 0 — Write-down (do first, ~15 min)

1. This document lives at `plan/survey_mission_plan.md` (done — you are reading it).
2. Add one line to `plan/backlog.md` "Now" section:
   **#93 Survey Mission Mode (see plan/survey_mission_plan.md)** and cross-link
   it from "THE EXIT CONDITION" section.
3. Do not start Phase B. Do not touch Maren (parked per user, 2026-08-19).

## Phase 1 — #93 Survey Mission Mode (the core)

**Goal:** a survey run where the decision LLM is called **once per cell**, not
once per tick, and ring-growth emerges deterministically.

**Design:**

- New module `Python/agent_runtime/survey_mission.py` — a pure state machine
  (mirror `cell_sweep.py`'s style: pure, testable, no I/O):
  - `Mission(target_cell_count | tick_budget, origin=world_center)`
    → `next_action(agent_state, place_db) -> goto(cell) | sweep(cell) | checkpoint | done`.
  - Target selection = **center-out rings** over the world grid (existing
    `world_grid.json` bounds, rings from world origin), skipping
    swept/refused/unreachable cells. This **is #76**, promoted from
    prompt-facts to mission logic.
  - On arrival: run the existing 4-heading sweep automatically (reuse
    `_execute_sweep_observe` and `_sweep_step`/composite machinery in
    `agent_manager.py`). Sweep-on-arrival replaces per-tick LLM-initiated
    `survey_here`.
  - After `sweep_done`: one **checkpoint** — a single decision-LLM call with a
    trimmed prompt (below) — then next target computed. No LLM between cells
    except reflex facts.
  - Travel reuses the existing locomotion stack (#86/#90/#92): hop plans, walk
    plans, reflex stops, body-box. Mission mode changes *who chooses the target
    and when to think*, not the locomotion stack.
- **Checkpoint prompt contract (new, small):** goal confirmation, the cell's
  composite summary, new `cell_ground`/refusal facts, frontier ring progress,
  and the naming action set (`set_name`, `refuse_cell`, no-go spot, `continue`).
  Cap at ~5 sections. This is #84's "one declared payload" idea getting its
  safe proving ground — scope it to the mission prompt only.
- **Agent wiring:** `"role": "maintenance"` agents (or a new
  `"mission": "survey"` field in `state.json`) enter mission mode at run start;
  personality APCs are untouched. `tools.json` allowlist unchanged.
- **Integration:** `agent_manager._tick_impl` pre-bucketing gains a mission
  bucket alongside `_pulse_sweep`/`_pulse_walk` — bridge-only on travel/sweep
  ticks, LLM only on the checkpoint.

**Tests (offline, extend `scripts/run_tests.py` patterns):**
- Ring order from a synthetic grid (center-out, ties by bearing); skips
  swept/refused/unreachable; exhaustion → `done`.
- Checkpoint contract: exactly one LLM call per cell; zero LLM calls on
  travel/sweep ticks (assert via router stub).
- Sweep-on-arrival: arrival → 4 observe_headings → composite → checkpoint, with
  no decision ticks in between.
- Abort paths: unreachable cell after `_MAX_SURVEY_TRAVEL_TICKS` → skip + log,
  never end the mission.

**Live grading (SR55+):** cells/hour; ring-shaped growth on `/map`; decision
calls per cell ≤ 1.5; zero wedges ending the run; corpus lines per cell =
4 headings + tick stream.

## Phase 2 — #94 Persistent geometry layer

**Goal:** the world gets less confusing every run. Today probe knowledge dies
with the run.

- Extend PlaceDB: table `obstacles(cell_col, cell_row, x, y, heading_deg, kind,
  label, class_name, first_seen_run)` — ingested from **existing** signals:
  `blocker:` probe hits, radar sweeps, body-box `open_columns`, footing
  samples, and `no_go_patches` (keep that table; reference it).
- Write path: whenever the runtime classifies a blocker or records a wedge
  escape, upsert an obstacle row (dedup at ~2 m). Read path: mission goto picks
  approach headings from obstacle rows; the checkpoint prompt gets one summary
  line ("known obstructions in cell: van at E 12 m, dumpster at NE 8 m").
- The fail-loud blocker classifier stays; unmatched classes get a row with
  `class_name` and no label (feeds #83's case, loses nothing).
- **Tests:** ingest/dedup/merge, cross-run persistence, and mission planning
  respecting geometry (fixture: a cell with a recorded van → goto approaches
  from a different heading).
- **Live grading:** the second overnight run shows *fewer* wedge/bounce ticks
  than the first on the same cells — geometry doing its job.

## Phase 3 — #95 Corpus completeness (small)

- During mission sweeps, every capture lands in `perception_log.jsonl` with
  `context="survey_sweep"` (#79 covers the four live perceive sites — verify the
  mission path uses them, not a bypass).
- Add a **build-time** script `scripts/build_perception_dataset.py`: reads the
  JSONL, dedups by perceptual hash, filters `error` rows, emits train/val
  splits. Explicitly out of the sim loop (matches #79's scope note).

## Phase 4 — #96 Doctrine + path reconciliation

- **#85 fix, properly:** create `Python/worlds/<level>/doctrine/navigation.md`
  (shared), included in every APC's system prompt; `rules.md` keeps persona
  only. Move Dufus's 94 lines accordingly; Maren inherits the doctrine
  automatically.
- **Retire the fork:** legacy explore mode's `explorer.next_target` and mission
  mode become one driver — explore mode becomes a thin alias over mission mode
  or is removed (keep tests green; update README).
- **#84 note:** the mission checkpoint prompt is the first consumer of a
  declared payload contract; do **not** widen #84 to all prompts while any live
  lane is open.

## Phase 5 — #97 Overnight run harness (the exit-condition instrument)

- `Python/start_sim.bat --overnight` (or a runner flag): starts the sim, then a
  watchdog loop appends `{cells_swept, corpus_lines, wedges, stalls, errors,
  decisions}` hourly to `logs/overnight_report.jsonl`; auto-**stop** on crash of
  either process. Restarting Unreal is out of scope — PIE must stay open;
  document that.
- **Acceptance = the exit condition, measured** (per backlog "THE EXIT
  CONDITION"):
  1. Multi-hour unattended run: no wedge ends it, no repeated-ground spiral
     (bounce counter flat), no stall ending the run.
  2. `world_places.db` coverage grows run-over-run (≥1 cell/hour on the current
     150-cell map; coverage was 13.3% on 2026-08-29 — beat it visibly).
  3. `perception_log.jsonl` grows ~4 lines/cell + tick lines, clean enough for
     the dataset builder.
- Grade per the backlog's grading rule — throughput and cleanliness, not social
  events. Write the SR record per repo convention (backlog entry, SR55+).

---

## Explicit ordering & gates

```
#93 mission mode  →  live SR55 (rings + ≤1 LLM call/cell)
   → #94 geometry  →  SR56 (repeat-ground shrinks)
   → #95 corpus    →  dataset builder runs on SR55 artifacts
   → #96 doctrine  →  SR56+ (Maren refuses ground using shared doctrine)
   → #97 overnight →  EXIT CONDITION MET → Phase B unblocks
```

- Phase 1 may start immediately (offline-first). #94 can be built in parallel
  (pure DB + ingest). #96/#97 depend on mission mode existing.
- **Do not** re-argue Phase B ordering; do not add prompt facts as a substitute
  for mission logic; do **not** "simplify" by giving the mission LLM per-hop
  judgment back — that is the failure mode this plan exists to end.

## Backlog entries to add (copy into `plan/backlog.md`, "Now" section)

- **#93 Survey Mission Mode** — deterministic center-out ring driver with one
  LLM checkpoint per cell; sweep-on-arrival; personality APCs untouched.
  Spec: `plan/survey_mission_plan.md` Phase 1.
- **#94 Persistent geometry layer** — `obstacles` table in PlaceDB fed by
  blocker/radar/body-box signals; mission goto respects it.
  Spec: Phase 2.
- **#95 Perception corpus completeness** — mission path records all four
  perceive sites; build-time dataset packager.
  Spec: Phase 3.
- **#96 Shared navigation doctrine** — `doctrine/navigation.md` + rules.md
  slimming (implements #85); retire the explore-mode fork.
  Spec: Phase 4.
- **#97 Overnight run harness** — watchdog + hourly metrics; the
  exit-condition instrument.
  Spec: Phase 5.

## Open decisions (implementer: do not guess — surface to the user)

1. **Mission cadence when the frontier is unreachable** (blocked ring cell):
   skip ring-ward and continue outward, or end the mission? Default: skip,
   log, keep going.
2. **Checkpoint model tier:** Sonnet (current) at 1 call/cell, or Haiku for
   checkpoints? Cost vs naming quality. Default: keep Sonnet — it is now once
   per cell.
3. **Does Maren ever get a mission?** Default: no — mission is
   maintenance-role only until the exit condition is met.
