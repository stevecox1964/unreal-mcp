# Backlog

Rolling list of outstanding work — add items as they come up, check off or
delete them as they land. Not session-scoped; this is the durable home for
"things I want done but didn't have tokens for this session." Newest
grooming: 2026-06-26.

> **▶ Resume the autonomous loop:** next credit window, say **"run the autonomous loop."**
> It reads the **"## Autonomous queue"** below, takes the next unchecked item, and grinds
> loop-safe (offline-testable) work on an `auto-loop/*` branch per `plan/autonomous_loop.md`:
> failing test → implement → `python scripts/run_tests.py` green → commit → check off.
> **Never pushes** — work piles up for human review + merge. (Handoffs are retired; this
> backlog is the single source of truth — see memory `feedback-no-handoffs`.)

> **★ MVP slice** *"Runs overnight, navigates to a named place, remembers who it met"* —
> mostly **landed**: **#1** place-name nav ✓, **#5** social + episodic + relevance recall ✓,
> **#3** factory ✓. The remaining MVP gap is **#3's standalone runner** (the "runs overnight
> independent of Claude" long pole — nothing built but the factory).

> **⚑ Status (2026-07-01 — grooming + direction reset, Claude-driven):** Two director calls locked:
> **(1) #10.5 = BALANCED reaction gate** (routine destination wins; only a known friend / being-spoken-to
> interrupts, then resume — persona distractibility is a low-weight nudge, never an override). **(2) The
> "maintenance APC" concept is RETIRED** — there is no dedicated no-personality worker; **any APC builds a
> community place cell when it needs one** (folded into **#11**; #7's sweep *mechanics* survive as the
> engine, the *dedicated role* does not). New direction from the user: **start winding down the
> grid/place-cell design** — get it debugged and finished — then move to the **next set**: **Child BPs**,
> **restart the sim from morning**, and **web-app observability** — *view sim progress* and *watch the
> grid + place cells get built out* live from the web app. **Staging below** splits work into a **loop-safe
> autonomous queue** (I grind these hands-off, commit-per-green, no push) and a **"work together" queue**
> (blocked on you — editor/PIE/design), ordered so we can knock them out together when you're back.
> Baseline restored to **24/24** (fixed a Starlette-1.0 `TemplateResponse` breakage from the Python-3.14
> env upgrade).
>
> **⚑ Status (2026-06-28, late — Claude-driven, PUSHED):** built **MASTER_PLAN Milestone 1 — the
> daily-schedule planner + sequencer** (`planner.py`, #10.1–10.4) and **wired it into the live tick**,
> verified live in PIE: agents now generate an in-character daily schedule (persisted to `runtime.json`),
> and `walk_to "<place>"` resolves + routes — Dufus headed to the **village square** from his schedule on
> wake, the first **goal-directed navigation** the sim has done (previously the LLM was never told it
> could navigate to a place by name — only "forward"). Also: a **vision bug fix** (Gemini branch media-type
> sniff), a big **README/docs accuracy pass** (sim-first reframe, dead-link fixes, retired-tool notes),
> and `still_todo.md` marked superseded. **Diagnosis confirmed live:** grid/place-cell reuse + the
> communal-sweep design (#7) are real and working (Dufus woke at a place he'd named over 9 prior runs);
> the old "lock-up" was aimless reactivity, now addressed. `scripts/run_tests.py` = **24/24**, **8 commits
> pushed to `origin/auto-loop/backlog`** (this session pushes directly per `feedback-push-no-prs`).
> **Next:** #10.5 reaction-gate weighting (routine vs. distractibility — a director's call) + the navmesh
> `stuck` wedge robustness item. Both need PIE.

> **⚑ Status (2026-06-28):** session added **Haiku-for-vision** (#7.0 — vision now runs on Haiku 4.5,
> Gemini optional), **provider-profiles CRUD** in the web UI (#7.1/7.2 done, #7.3 UI pending live
> verify), and **retired the stale MCP→Unreal editor-authoring tools** (#8 — 8 modules removed, docs
> fixed). Also introduced the **dev-mode vs sim-mode** framing (#9, memory `feedback-dev-sim-modes`).
> `python scripts/run_tests.py` = **22/22 green**, 6 new commits on `auto-loop/backlog`, never pushed.
> **Loop-safe backlog is now essentially exhausted** — remaining work is live/editor/design (browser
> verify of `/providers`, the #8/#9 design calls, merge to main). *(The legacy `npc_builder/` app —
> frontend+backend, superseded by `web_ui/` + the `/create-npc` skill — was **deleted 2026-06-28** at
> the user's request; nothing active imported it.)*

> **⚑ Status (2026-06-26, eve):** the autonomous loop ran again and **cleared the entire
> "Autonomous queue" (5/5 items)** on branch `auto-loop/backlog` — episodic consolidation,
> state.json config/runtime split, the standalone-runner control surface, the web settings backend,
> and the NPC-Builder→Unreal-World-Sim rename. `python scripts/run_tests.py` = **18/18 green**,
> never pushed. First action for a new session: review + merge `auto-loop/backlog`. After that the
> remaining work is live/editor (see "Outstanding").

> **✅ Validated live (PIE sim run, 2026-06-26 — 23 ticks, cloud, zero errors):** the new
> agent_manager path runs clean end-to-end. **Confirmed working:** episodic memory (`episodes.jsonl`
> written + growing), grid/place pipeline incl. the scene-unchanged regression fix, `walk_to`
> execution, and the social store correctly staying empty for anonymous-only sightings (no false
> acquaintances). **Built + offline-tested but not yet hit by this run's scenario:** the #1 *named-place
> resolver* (no cell was named "village square" in PlaceDB, so agents walked by frontier), social
> recording *by name* (the two NPCs never came within range), and the #7 maintenance APC (no
> `role:"maintenance"` agent configured). System is healthy for multi-day running.

## ▶▶ Staged plan (2026-07-01) — direction reset: wind down grid/place, then observability

Two ordered queues. **A** is what I grind hands-off while you're gone (loop-safe, commit-per-green, no
push). **B** is blocked on you (editor / PIE / live / a design call) — ordered so we can knock it out
together when you're back. Detail for each lives in the thematic sections below (`## N`).

### A — Loop-safe autonomous queue (grind now)

- [x] **A1 · Web map view — watch the grid + place cells build out.** ✓ 2026-07-01 — `PlaceDB.map_cells()`
      (named/swept cells + landmark counts) + `web_ui` `GET /map` page and `GET /api/map` JSON; `map.html`
      renders the bounded grid as a CSS grid colored **named / swept / unexplored**, polls `/api/map` every
      3s so you watch cells fill in live, with a built-out % + per-cell hover (name / who / landmarks).
      Missing DB → empty map (a GET never spawns a blank world). Map nav link added. Offline test:
      `test_map_view.py` (temp world via `TestClient`). Suite 25/25. *(Live verify = B2.)*
- [ ] **A2 · Grid/place staleness (#11.3).** `PlaceDB.is_stale(col,row,max_age)` + freshness query + a
      `stale` flag surfaced to A1's map. Winds down the grid/place design. Loop-safe + tested.
- [ ] **A3 · Restart the sim from morning.** A reset that clears runtime state (`daily_schedule`,
      `last_activity` via the existing `reset_runtime_state`) **and** resets `WorldClock` to morning,
      exposed on the runner control API (`POST /reset_day`) + a web-cockpit button. Offline-testable via
      `TestClient`/stub runner. → serves #3/#9 + #10 (fresh day regenerates the plan).
- [ ] **A4 · Collapse the maintenance-role gating (#11.1 logic).** Refactor so the sweep is a capability
      any APC invokes; remove the `role:"maintenance"` branch/`_pulse_maintenance`. Offline-test the
      enter-cell → central-missing → sweep decision as a pure step. (Live verify is B-side.)
- [ ] **A5 · APC-owned place cells schema (#11.2).** PlaceDB schema/ownership change for multiple
      APC-owned cells per grid cell + tests. Larger; after A1–A4.

### B — Work together (blocked on you: editor / PIE / live / design)

Ordered for a joint session:

1. **B1 · Child Blueprints** `BP_Dufus` / `BP_Maren` (child of `BP_CameraNPC`, mesh override + rebind).
   *Editor + mesh choice.* — you named this as a next thing; detail in **"▶ Next up"** below.
2. **B2 · Live grid/place debug in PIE** — run the sim and watch cells build out on the **A1 map view**;
   confirm reuse + A2 staleness behave. Pairs with A1/A2 to *finish* the grid/place design.
3. **B3 · #10.5 balanced-gate live tune** — the PIE prompt-weighting change + verify Dufus reaches the
   village square instead of diverting to every passer-by.
4. **B4 · Restart-from-morning live verify** — drive the A3 reset button against PIE.
5. **B5 · `observe_heading` bridge handler** (#7 live half) — rotate-to-yaw + capture + `ingest_compass`
   so sweeps produce real landmarks. *C++/editor rebuild.*
6. **B6 · Merge `auto-loop/backlog` → `main`** + push decision.
7. **Carryover:** settings-page UX polish, providers end-to-end spot check, navmesh `stuck` robustness.

---

## Autonomous queue — loop-safe (offline-testable), grind hands-off

Build these in order on an `auto-loop/*` branch; each is Python whose **logic** is offline-testable
even though final live execution may need PIE. Commit each green step, never push.

> **Active queue is the "▶▶ Staged plan → A" above** (2026-07-01). The numbered 1–10 below are the
> *prior* loop cycle (all landed except #9 parked / #10.5 which is now a B-side live tune) — kept for
> history.

1. ~~**Episodic consolidation**~~ ✓ 2026-06-26 — `EpisodicLog.consolidate()` rolls events older than
   `keep_recent` into compact per-place summary rows `{kind:"summary", place, count, first/last_time,
   actions, saw, grid_cells}`; auto-runs from `record()` every `_consolidate_every` appends once over
   `_max_events` (1000/200/200 defaults), atomic tmp-rewrite. `query`/`relevant`/`recent` tolerate
   summary rows. Test: `test_episodic_memory.py`.
2. ~~**`state.json` config/runtime split**~~ ✓ 2026-06-26 — runtime fields (`_RUNTIME_KEYS`:
   last_tick_time/last_spoke_time/current_goal/is_busy/last_bound_time/bound_*) now persist to a
   git-ignored `runtime.json`; `state.json` is config-only and stays byte-stable across ticks (no more
   churn). `self.state` is still the merged in-memory view, so all callers/properties are unchanged;
   `load()` merges runtime over config; legacy dirs (no runtime.json) load fine. Test: `test_agent_state.py`.
   *(One-time: the committed `dufus`/`maren` state.json shed their stale runtime keys on the next live
   save — expected, then stable.)*
3. ~~**#3 standalone runner (control surface)**~~ ✓ 2026-06-26 — `runner_app.build_control_app`
   (FastAPI: `/health`, `/status`, `/start`, `/stop`, `/tick` over the manager), `runner_client.RunnerClient`
   (injectable HTTP client + `is_running`/`reachable`), and `sim_runner.py` entry point (`create_app`
   via `factory` + `uvicorn.run`). Routes + client + wiring offline-tested via `TestClient`/ASGI
   (`test_runner_api.py`). **Remaining (live, deferred):** run `sim_runner.py` against Unreal in PIE;
   wire `simulation_tools.py` + `web_ui` as thin `RunnerClient` attachers (#3 actions 2.4/2.5) — both
   need a live runner to verify.
4. ~~**#2 web settings backend**~~ ✓ 2026-06-26 — `web_ui`: `GET /settings` (page), `GET /api/settings`
   (JSON, secrets masked), `POST /settings` (form → `config_store.write_config`; a blank secret field
   is left as-is so it can't be wiped). `settings.html` template + `ENV_PATH`. Offline-tested via
   `TestClient` over a temp .env (`test_settings_page.py`). *Remaining (live): a nav link + visual
   polish, and surfacing the Ollama⇄cloud toggle nicely — verify in a browser.*
5. ~~**"NPC Builder" → "Unreal World Sim" rename**~~ ✓ 2026-06-26 — display strings in `web_ui`
   templates (`base.html`, `index.html`, `settings.html`), `main.py` title/docstring, and
   `start_npc_builder.bat`; added a Settings nav link. `npc_builder` *code identifiers* and the .bat
   *filename* left for a later pass. Branding/nav asserted in `test_settings_page.py`.

**Direction (user, 2026-06-26):** the **web UI is the cockpit** — drive/step/log the sim for
debugging and CRUD the providers — and the **sim engine runs standalone** (`sim_runner`), so it can
run slow **local/offline models** with no Claude attached. Claude shifts to **plain API calls** for
coding, and the bespoke MCP is eventually retired (Epic ships an official Unreal MCP now). New items:

6. ~~**Web sim controller (drive + step + log)**~~ ✓ 2026-06-26 — `web_ui` `/sim` cockpit:
   status panel (running/tick/agents), **Start/Stop**, single-tick **Step** (debugging), and a live
   decision-log panel — JS polls `/api/sim/status` + `/api/sim/events` every 2s. Routes proxy to
   `sim_runner` via `RunnerClient`; "no sim runner running" handled. Runner gained `GET /events` +
   `recent_events` (and a `get_status` bugfix the stub had masked). `start_sim.bat` boots engine +
   cockpit with no Claude. Nav link added. Offline-tested with a stub runner (`test_sim_controller.py`).
   *Live verify: run `start_sim.bat` with Unreal in PIE and drive it in a browser.*
7. **Provider config — Haiku-for-vision, then profiles CRUD (web UI).** *(user, 2026-06-28: Haiku
   4.5 is multimodal — it does decisions AND vision, so Gemini comes out of the active path. This is
   the on-ramp to making providers fully configurable from the web UI. Direction: **option B —
   named provider *profiles*** with create/edit/delete, assigned to roles.)*
   - [x] **7.0 Haiku vision (loop-safe).** ✓ 2026-06-28 — `VisionPerceiver` (`perception.py`) gained an
         `anthropic` branch: `VISION_PROVIDER=anthropic` perceives screenshots via Haiku 4.5
         (`claude-haiku-4-5-20251001`, override `ANTHROPIC_VISION_MODEL`), returning the same
         `{landmarks, characters, caption}` shape and degrading to an empty result on a missing key.
         `.env` flipped to `VISION_PROVIDER=anthropic` (gitignored); the **Gemini + ollama branches stay
         selectable** (user choice 2026-06-28). Offline test: `test_vision_perceiver.py` (stubbed
         Anthropic client). Suite 20/20.
   - [x] **7.1 Provider profiles model** ✓ 2026-06-28 — `agent_runtime/provider_profiles.py`:
         `config.json` of named `{provider, model}` profiles + `roles{decision,vision}`. CRUD
         (`upsert_profile`/`delete_profile`/`assign_role`, missing-file seeds defaults) and
         `apply_to_env` which **compiles** the active roles to the plain `.env` keys the runtime
         already reads (`LLM_PROVIDER`/`LLM_MODEL`, `VISION_PROVIDER` + the provider's model var) — so
         resolution logic in `llm_router`/`perception` is untouched. No secrets in profiles (keys stay
         in `.env`). Offline test: `test_provider_profiles.py`.
   - [x] **7.2 CRUD routes** ✓ 2026-06-28 — `web_ui`: `GET /api/providers`, `GET /providers`,
         `POST /providers/{save,delete,assign}`. Every mutation re-applies to `.env` (sim reloads each
         tick → no restart). Ollama⇄cloud is just another profile. Offline test: `test_providers_page.py`
         (`TestClient`). `config.json` gitignored (seeded on first read).
   - [x] **7.3 UI** — `providers.html` (role selectors + profile table + add/edit form) and a
         Providers nav link landed; user ran the web server and confirmed it "looks good enough"
         (2026-06-28). *(Deeper end-to-end "assign in UI → sim uses it" still worth a spot-check.)*

8. ~~**Strip stale MCP→Unreal *non-sim* (editor authoring) tools.**~~ ✓ 2026-06-28 — removed the 8
   authoring tool modules (`editor_tools`, `blueprint_tools`, `node_tools`, `umg_tools`,
   `character_tools`, `camera_tools`, `attachment_tools`, `project_tools`, ~2300 lines) + their
   `register_*` imports/calls in `unreal_sim_server.py`; rewrote the stale `info()` prompt to describe
   the remaining sim tools. **Kept** `simulation_tools.py`. Verified safe first: only `unreal_sim_server`
   imported them, nothing under `agent_runtime/`/`sim_runner`/`runner_app`/`web_ui` did; the standalone
   sim reaches Unreal via `UnrealBridge` raw socket commands (e.g. `capture_camera_image` as a C++
   command, not the `camera_tools` wrapper). `import unreal_sim_server` still OK (bridge's
   `get_unreal_connection` intact); suite 22/22; no stale refs anywhere. First phase of the
   "deprecate the custom MCP" idea below; C++/Blueprints untouched.

9. **Sim Run ID (`SR<n>`) — tag observations + logs per run.** *(user, 2026-06-28 — loop-safe.
   **Parked:** user said "no rename for now" — keep backlogged, don't implement/schedule yet.)* Give
   every sim run a monotonic number so artifacts and logs are attributable to a single run for
   debugging. Pieces:
   - **Allocator** — a small `agent_runtime/sim_run.py`: read+increment a persisted counter at sim
     start (first run = `SR1`), expose the **current run id**. Persist in a git-ignored file (e.g.
     `Python/worlds/<level>/sim_run.json` or alongside `runtime.json`). *Decision: global vs per-world
     counter (rec: per-world).*
   - **Observation files** — prefix `SR<n>_`: `SR42_observation_<ts>.png` at the three capture sites
     in `unreal_bridge.py` (`capture`/`capture_view`/`capture_observation`, lines ~141/172/297). The
     run id has to reach the bridge (set on the manager at run start → passed to capture calls).
   - **Decision log** — add a `sim_run` field to each entry in `memory_store.record()`
     (`agent_decisions.log`), and/or prefix — so you can filter the JSONL by run.
   - **General logs** — a `logging.Filter` that injects `SR<n>` into `AgentRuntime` log lines, wired
     into `sim_runner.py`'s format (`%(sim_run)s …`), so console/file lines carry the run.
   - **Offline-testable:** counter increment/persistence, filename prefixing, the log-record field, the
     filter injection — all without Unreal. Live verify: filenames + log prefixes appear in a real run.

10. **Daily-schedule planner + sequencer — MASTER_PLAN Milestone 1 (the cognitive-loop spine).**
    *(Claude-driven, 2026-06-28. The biggest behavioral gap: agents decide tick-by-tick with no
    routine. The plan makes the daily schedule the **spine** and the reactive tick the interrupt
    handler.)* User framing: not just a planner but a **sequencer** — "I wake, what time is it, I
    should be at the stall, oh I'm already there, what next, 12:00 → go to lunch."
    - [x] **10.1 Planner module (loop-safe)** ✓ 2026-06-28 — `agent_runtime/planner.py`, a dependency-free,
          offline-testable module. Deterministic core: `to_minutes`/`minute_of_day` (parses
          `WorldClock.now_text()`), `normalize_schedule` (drops malformed blocks, sorts), and the spine
          `current_block(schedule, minute)` ("what should I be doing now?", start-inclusive/end-exclusive).
          LLM **injected** as a `prompt->text` callable so it's provider-free: `generate_daily_plan(...,
          ask=None)` returns a deterministic all-day fallback; with `ask` it parses a JSON block list and
          degrades to fallback on any failure. Blocks carry place **names** (resolution stays the existing
          `walk_to` named-place job, not declared here). Test: `test_planner.py`.
    - [x] **10.2 Sequencer step (loop-safe)** ✓ 2026-06-28 — `planner.step(schedule, minute, current_place,
          prev_activity)` returns a directive `{block, activity, place, status, transition, intent}`:
          **travel** (go to the place), **act** (already there → LLM picks the sub-action), or **idle**;
          `transition=True` when a block boundary flips (noon → lunch). `_same_place` does loose
          containment matching ("vegetable truck" ⊆ a richer perceived label). Pure/testable; the LLM
          owns only the sub-action, grounded by `intent`. Tests in `test_planner.py` walk the wake →
          travel → arrived → noon-transition narrative.
    - [x] **10.3 Persist the day's schedule in scratch (loop-safe)** ✓ 2026-06-28 — `Agent` gained
          `daily_schedule` (`{day, blocks}`) + `last_activity` runtime keys (in `_RUNTIME_KEYS` → land in
          git-ignored `runtime.json`, never churn `state.json`), with `set_daily_schedule`/`set_last_activity`
          and `reset_runtime_state` clearing both so a fresh run regenerates. `planner.ensure_daily_plan(agent,
          day, ask=, agents_dir=)` generates+persists once per sim-day (idempotent within the day — only the
          first tick asks the LLM) and `planner.day_of("Day 1, 08:23")="Day 1"`. Tests: `test_planner.py`
          (idempotency/regeneration via a duck-typed agent) + `test_agent_state.py` (runtime round-trip,
          no state.json churn, reset clears).
    - [x] **10.4 Wire the sequencer into the live tick** ✓ 2026-06-28 (verified live, Dufus/MCP_World) —
          `llm_router.ask()` (generic completion the planner uses to generate the day's schedule via the
          agent's model); **added `walk_to {target_location:"<place>"}` to the action schema** so the LLM
          can navigate to a named place (the resolver existed in `_execute_world_action` but the model was
          never told it could — this was why agents could only step "forward"); `{schedule_note}` in the
          decision prompt fed by the sequencer directive. `agent_manager._attach_schedule` runs
          `ensure_daily_plan` (idempotent/day) + `planner.step` in the decide phase, injects the directive,
          and persists `last_activity`. **Live result:** full in-character daily schedule generated +
          persisted to `runtime.json`; wake resolved `'village square' -> cell center` and issued a real
          `move_to` (goal-directed navigation, previously impossible). Suite 24/24.
    - [ ] **10.5 Reaction-gate weighting (tuning)** — decide-phase reactivity still tends to override the
          scheduled destination (agent greets every passer-by instead of pressing on). Bias the prompt so
          the routine destination wins unless a genuinely salient event interrupts (Master Plan §14 reaction
          gate). **Decision (user, 2026-07-01): BALANCED GATE** — the routine destination wins by default;
          only a genuinely salient event (a *known friend*, or *being spoken to*) may interrupt, and after
          the interrupt the agent **resumes** the scheduled destination. Persona distractibility (Dufus's
          "chase something shiny") stays in-character but must **not** win over the routine on its own — it's
          a low-weight nudge, not an override. Implementation (live/PIE): in `llm_router._USER_TEMPLATE_VISION`
          + `_schedule_note`, raise the scheduled destination's weight above the "greet whoever you see"
          reaction, then verify Dufus reaches the village square instead of diverting to every passer-by.
          Also: navmesh wedging (`stuck on an obstacle`) persists as a separate live robustness issue —
          agent recovers but it stalls progress.

11. **Grid-cell place-cell model — central community cell + APC-owned cells + staleness.**
    *(user, 2026-07-01 — a design-reconciliation pass. "I think we have all of this in the design but make
    a backlog item to make sure.")* User's intended model of how the world gets built out:
    - Each **grid cell** houses **one central place cell** at the cell **center** with a **360° observation
      scan** — the *community* record for all APCs.
    - When an APC **navigates into a new grid cell**, it **checks for an initialized central place cell**; if
      none exists, it **moves to the cell center, runs the 360 scan to initialize it, then resumes its
      task**.
    - An APC may own **several place cells within one grid cell** — **owned by that APC but reusable by
      others** — so knowledge accumulates and the world fills in.
    - If a grid cell's place cell is **out of date / stale** (enough sim-time has passed since its last
      initialization), an **update observation** must re-run.

    **Reconciliation against what's built (verify, then fill the gaps — don't rebuild the done parts):**
    - [x] *Central cell + 360 scan exist.* `place_cells` is keyed `(col,row)` = one cell per grid cell;
          `cell_sweep.py` does GOTO_CENTER → observe 8 compass headings → `PlaceDB.mark_swept` (the
          `swept_at` community breadcrumb); landmarks land in `place_observations`. Reuse via
          `is_explored`/`get_swept`/`explored_cells` (#1, #7). **This is the central-cell design already.**
    - [ ] **11.1 Any-APC self-initialization (behavior gap + role retirement).** **Decided (2026-07-01):
          no dedicated maintenance role** — collapse the `role:"maintenance"` gating (`_pulse_maintenance`
          + the role branches in `pulse_agent`/`tick`) so the sweep is a **capability any APC invokes**, not
          a role. Behavior: an APC that enters a grid cell with no central place cell **it needs now**
          detours to center, runs the 360, `mark_swept`, then resumes its scheduled task (a #10 sequencer
          interrupt — reuses the balanced reaction gate from #10.5: initialize-if-needed wins, then resume).
          The `cell_sweep.py` state machine + `mark_swept` mechanics are reused as-is. *Live/PIE verify: a
          personality APC actually detours + sweeps a fresh cell it wants to use.*
    - [ ] **11.2 Multiple APC-owned place cells per grid cell (schema gap).** The schema allows only **one**
          place cell per `(col,row)` (it's the PK). The model wants a **central community cell** *plus*
          several **APC-owned** sub-cells in the same grid cell (owned by an APC, readable/reusable by
          others). Needs a data-model change: either a separate `owned_place_cells` table keyed
          `(col,row,owner,slot)` with an `owner`/reusable flag, or promote place cells to their own id.
          Keep the central cell distinct from owned cells. *Decision: what distinguishes a "place cell"
          within a grid cell — a sub-position, a landmark cluster, a named spot? (rec: a named spot with a
          world position inside the cell; central cell = the unnamed 360 breadcrumb at center.)*
    - [ ] **11.3 Staleness / TTL re-observation (missing).** No expiry today — `is_explored` is True
          forever once swept. Add a freshness check: given `swept_at` (and a configurable max-age in
          sim-time), `is_stale(col,row)` and a re-observation path that re-runs the 360 and refreshes the
          landmarks/timestamp. *Decision: TTL in sim-days? re-observe on entry when stale, or lazily when an
          APC needs current info? (rec: lazy — re-observe on entry only if stale AND the APC is about to
          rely on it.)*
    - **Loop-safe (offline-testable):** the PlaceDB schema/ownership change (11.2), `is_stale` + the
      freshness query (11.3), and the decision logic for "enter cell → central missing/stale → sweep" as a
      pure planner step (11.1's logic). Live verify (PIE): a personality APC actually detours to center and
      sweeps a fresh cell, and re-sweeps a stale one.

    Relates to: #1 (grid/place cells — "Finalize grid cells and place cells" + "how observations attach"),
    #7 (maintenance APC sweep), #6 (map/known_places), engine-agnostic navigation.

(Items 1–6 landed 2026-06-26, 19/19 green; #7.0–7.2 + #8 landed 2026-06-28, 22/22; #10.1–10.2 + vision
Gemini-media-type fix landed 2026-06-28, 24/24.)

---

## Outstanding — human / editor / live (not loop-safe)

- **Merge** `auto-loop/backlog` → `main` (21 commits) and decide on `git push`.
- **#7 maintenance APC — live half:** implement `observe_heading` in the Unreal bridge/C++
  (rotate to yaw + capture + `ingest_compass`); spawn a `role:"maintenance"` actor. *Editor/PIE.*
- **#3 standalone runner:** `sim_runner.py` + localhost control API + thin MCP clients (factory done). *Live Unreal.*
- **#2 settings page + rename:** UI (`config_store` backend done); "NPC Builder" → "Unreal World Sim". *Live app to verify.*
- **#6 map:** manual-capture mode (user snapshots) + lizard-brain routing (path-as-facts). *Editor/design.*
- **#5 consolidation** + a **sentiment policy:** need an LLM summariser/signal.
- **Child Blueprints** `BP_Dufus`/`BP_Maren` (mesh override) + rebind. *Editor + mesh choice.*

## Recently landed

- **Autonomous loop — 21 commits on `auto-loop/backlog`** (2026-06-26, offline-tested, unpushed):
  **#1** place-name nav (`walk_to "village square"` resolves to a location); the **loop harness**
  (`scripts/run_tests.py`, `plan/autonomous_loop.md`, `scripts/loop/preflight.py` — #4.1–4.3);
  green baseline (fixed a scene-unchanged grid/place regression + stale stubs); **#5** memory layer
  (`SocialMemory`, `EpisodicLog`, speech→interaction, relevance recall); **#6** map query
  (`known_places`); **#2.2** `config_store.py`; **#3/2.1** `factory.build_agent_manager`; and **#7**
  the **maintenance/monitor APC** (PlaceDB sweep state + community breadcrumbs, `cell_sweep` planner,
  `Agent.role`, `_maintenance_sweep`/`_nearest_unexplored_target`/`_pulse_maintenance`, tick routing).
  See `plan/handoffs/LATEST.md` for detail.
- **Agent activity display** (2026-06-25) — `observing`/`thinking` now push to
  each NPC's `AIState` from the sequential tick phases (`_set_activity` in
  `agent_manager.py`, `bridge.set_ai_state`). A Text Render component on
  `BP_CameraNPC` (bound to `AIState`, added in-editor) shows the word above each
  head. Verified live on cloud. *(Display lives on the shared base BP → child
  BPs in "Next up" inherit it for free.)*
- **Rename MCPCharacterComponent → APCCharacterComponent** (2026-06-25) — moving
  off MCP branding for the in-world component; `[CoreRedirects]` keeps existing
  Blueprints intact. Module/plugin stay `UnrealMCP` for now (larger separate job).
- **Place-cell DB reset** (2026-06-24) — `reset_world_places()` MCP tool wipes
  the shared `world_places.db` (place_cells, place_observations, agent_visits)
  for a true blank world; complements `reset_agents` which preserves the map.
  `PlaceDB.reset()` in `Python/agent_runtime/place_db.py`. *(Part of #1.)*

---

## ▶ Next up: Child Blueprints for per-agent meshes

**Status:** Next · **Independence:** Self-contained

Dufus and Maren currently share one Blueprint (`BP_CameraNPC`) and look
identical. Give each its own mesh without duplicating logic.

- [ ] Create `BP_Dufus` and `BP_Maren` as **child Blueprints of `BP_CameraNPC`**,
      overriding **only** the skeletal mesh (keep all shared logic — the
      `APCCharacterComponent`, the AIState Text Render display, AI controller —
      on the base so both inherit it).
- [ ] Rebind the agents to the new child BPs: today `dufus` → `BP_CameraNPC_C_1`,
      `maren` → `BP_CameraNPC_C_0` (placed actors). Either replace the placed
      actors with the child BPs or update each agent's `unreal_actor_name` /
      `blueprint_class` binding so the sim spawns/binds the right one.
- [ ] Pick the two meshes (project has `SkeletonCharacter` + AssetsvilleTown
      character skeletal meshes available).

Why child BPs not full copies: fix shared bugs once; the status-bubble display
and component come along automatically.

---

## 1. Named-place navigation + grid/place cells

**Status:** Not started · **Independence:** Self-contained (no dependency on #2/#3)

The real remaining navigation gap. A `walk_to` with a string place-name
("village square", "Don's Donuts", "Sheriff's office") currently short-circuits
to **idle** in `execute_action` (`Python/agent_runtime/unreal_bridge.py`) — there
is no resolver mapping a place name to a world location or scene actor. Agents
wander by direction/frontier but never navigate *to* a stated goal. (Dufus's
memory is a long loop of "still searching for village square.")

- [x] Build a place-name → PlaceDB cell-center resolver so `walk_to <place>`
      navigates instead of idling. ✓ 2026-06-26 — `PlaceDB.find_named_cell` +
      `WorldGrid.cell_center` + `AgentManager._resolve_place_target`, wired into
      `_execute_world_action`. Offline test: `scripts/agent_runtime/test_place_resolver.py`.
- [ ] Finalize grid cells and place cells. *(Design reconciled in **#11** — central community cell +
      APC-owned cells + staleness.)*
- [ ] Design how observations attach to / save against grid/place cells. *(See **#11**.)*
- [x] Reset the place-cell DB to start from scratch (`reset_world_places()`). ✓ 2026-06-24

> Note: the walk_to *error* is already dead (no failures since 2026-05-14). This
> item is the genuine outstanding work — goal-directed navigation, not the error.

Relates to: engine-agnostic navigation, lizard-brain sensing.

---

## 2. World Sim web-app settings page + rename

**Status:** Not started · **Independence:** Coupled with #3 (shared web app)

The app's scope has grown past building individual NPCs — it's becoming the
control surface for the whole simulation.

- [ ] Add a **settings/configuration page** to the web app — manage config
      (model/provider selection, sim parameters) through the UI instead of
      hand-editing `.env`.
  - [ ] First control to surface: the Ollama vs cloud provider switch
        (currently `.env`-only: `LLM_PROVIDER` / `VISION_PROVIDER`).
- [ ] Rename **"NPC Builder" → "Unreal World Sim"** throughout:
  - [ ] UI titles
  - [ ] `start_npc_builder.bat`
  - [ ] the `web_ui` app
  - [ ] `npc_builder` references
  - [ ] `/create-npc` skill text that mentions "the npc_builder web UI"

Config complexity is ours to solve in the UI, not the user's.

Action breakdown (from dreams iter 3, `plan/dreams/dreams_2026-06-25_1131.md` — subagent-ready):
- [ ] **2.1** Rename surface strings only (`web_ui` templates, `main.py` title/docstring,
      `start_npc_builder.bat`, `/create-npc` skill prose); leave `npc_builder` *code identifiers* for a
      separate pass.
- [x] **2.2** New `agent_runtime/config_store.py` — `read_config()` (secrets as set/unset, never values)
      + `write_config()` that rewrites `.env` preserving comments/order, leaving omitted secrets intact.
      ✓ 2026-06-26. Offline test: `test_config_store.py`. *(Reload: callers invoke the existing
      `load_dotenv(override=True)` path — `reload_llm_environment`; not bundled into write_config.)*
- [ ] **2.3** Settings page: `GET/POST /settings` in `web_ui/main.py` + `settings.html` + nav link.
- [ ] **2.4** First control — Ollama⇄cloud provider toggle (decision + vision roles, hybrid-selectable),
      writes both keys and reloads with no restart.

Decisions (human): persistence target `.env` vs new `config.json` (rec: `.env`)? secrets editable in the
form or set/unset display only (rec: display only)? rename scope surface-only now vs code identifiers too
(rec: surface-only)?

---

## 3. Independent sim lifetime

**Status:** Not started · **Size:** Potentially large · **Independence:** Coupled with #2

Today **Claude Code owns the lifetime** of the MCP server + simulator — when
Claude isn't running, the sim isn't running. The user wants the world sim to run
**independently of Claude Code** so it can run overnight or for long stretches
without Claude Code open.

The coupling is one line: `unreal_sim_server.py:417` `mcp.run(transport='stdio')` — the MCP
server is a stdio subprocess of Claude Code, and the `AgentManager` (async sim loop) lives inside
it. `UnrealBridge` (TCP 55557) + the web UI's direct socket are already Claude-independent.

Action breakdown (from dreams iter 2, `plan/dreams/dreams_2026-06-24_2327.md` — subagent-ready):
- [x] **2.1** Factor `AgentManager` construction into `agent_runtime/factory.py` (shared by MCP + runner).
      ✓ 2026-06-26 — `build_agent_manager(worlds_dir=None)`; `get_agent_manager` now delegates to it.
      No I/O at construction, so offline-testable: `test_factory.py`.
- [ ] **2.2** New `Python/sim_runner.py` — standalone process that runs the loop with no MCP/Claude.
- [ ] **2.3** Control surface on the runner (localhost HTTP: start/stop/status/tick).
- [ ] **2.4** Make `simulation_tools.py` thin clients of the runner (attach, don't host).
- [ ] **2.5** Point web_ui at the runner control API (→ theme #2/③ controller). Fleshed out in dreams
      iter 3 (`plan/dreams/dreams_2026-06-25_1131.md` Action 3.5): `sim_runner_client` in
      `web_ui/unreal_client.py` + a dashboard status panel and start/stop buttons; no auto-spawn (keep
      lifetime decoupled); if no runner is reachable, render "no sim runner running". **Blocked on 2.2–2.3
      (the runner + its control API)** — until then, build the UI against a documented mock contract.

Decisions (human): IPC = HTTP (rec)? auto-spawn runner from MCP (rec: no)? Unreal socket owned by
runner exclusively (rec: yes — bridge isn't concurrency-safe)? one runner/machine vs per-world?

The sim is the product; Claude is a tool for building it, not a required host
process. The standalone launcher likely belongs in the same web app as #2.

---

## 4. Autonomous building loop (run unattended until limits, resume next session)

> **Split (dreams iter 5):** **#4a — the harness** (4.1 contract, 4.2 preflight, 4.3 aggregator) is pure
> Python/offline and can be built **now**, even exercised on #1 before #3 exists — it makes **no LLM calls**,
> so it's cheap on cloud. **#4b — running the *live* sim unattended** is what's gated by #3 + local models
> (per-tick inference cost). Don't let #4b's blockers stall #4a.

**Status:** Not started · **Size:** Process/setup, not a code feature · **Depends on:** local models (cost) + #3 (engine autonomy)

Goal: put Claude into a **self-paced `/loop`** that works this backlog
unattended — building, testing, committing — until the daily credit/usage limit
cuts it off, then **resumes the next session** from the handoff. The idea is to
use up daily credits productively instead of leaving them unspent.

**How it would run:**
- [ ] `/loop` with no interval (self-paced): work backlog items, each as
      branch → failing test → implement → run tests → commit on green → update
      this backlog. Cross-session continuity comes from `plan/handoffs/LATEST.md`
      + this file (the loop reads them on each start). Optionally a daily
      `/schedule` routine kicks it off after credits refresh.
- [ ] There is **no "credits draining" signal** to detect — the session just
      stops when limits hit. The handoff is what makes it recoverable, so the
      loop must keep the handoff/backlog current as it goes.

**Guardrails (must have — unattended = errors compound):**
- [ ] Dedicated branch; commit every green step; **never push** unattended.
- [ ] **Never** touch C++, Blueprints/UMG, or `.env`; never start the sim / need
      PIE. (These need an editor rebuild + MCP restart Claude *cannot* do itself —
      see #3 — or a human decision.)
- [ ] Skip + log (don't guess) anything needing the editor, a rebuild, a design
      choice (e.g. meshes), or that's ambiguous. Stop if tests fail and can't be
      fixed in ~2 tries.

**What's actually loop-safe here:** Python-only, test-verifiable work. Best first
target is **#1 named-place navigation** (self-contained, testable). Blocked from
autonomy: Child-BP/meshes (editor + design), settings page UX, anything C++.

Action breakdown (from dreams iter 4, `plan/dreams/dreams_2026-06-25_1149.md` — subagent-ready).
Key grounding: tests here are **standalone offline scripts** under `Python/scripts/**/test_*.py` (14
today) that stub Unreal entirely — that offline-stub surface *is* the loop-safe zone (no pytest, no PIE).
- [x] **4.1** Write `plan/autonomous_loop.md` — the run-contract the loop reads each start (allowed
      surface, hard NOs, stop conditions, per-item cycle). ✓ 2026-06-26.
- [x] **4.2** `Python/scripts/loop/preflight.py` — refuse to start unless tree clean, on a dedicated
      loop branch (not `main`), and baseline tests green. ✓ 2026-06-26 — pure guards
      (`is_loop_branch`/`tree_is_clean`/`evaluate`) + live git/test gathering. Test: `test_preflight.py`.
- [x] **4.3** `Python/scripts/run_tests.py` — discover + run every offline `scripts/agent_runtime/test_*.py`,
      one PASS/FAIL signal; `--only <glob>` for the in-progress test. ✓ 2026-06-26. (Socket-based
      actors/node/blueprints tests need live Unreal — excluded.)
- [ ] **4.4** First target failing-test-first: `test_place_resolver.py` + a PlaceDB place-name→cell-center
      resolver, wiring `walk_to` to navigate instead of idle (drives backlog #1).
- [ ] **4.5** Recoverability: update `handoffs/LATEST.md` + check off backlog on every green commit
      (the `/handoff` skill already does most of this) — this is what makes the loop resumable.

Decisions (human): run on cloud now since the *build/test* loop makes no LLM calls (rec: yes; keep live-sim
for local models)? kickoff via `/schedule` vs manual `/loop` (rec: manual first)? branch-per-item (rec:
yes)? human reviews each loop branch before `main` (rec: yes — "never push" implies never auto-merge)?

**Why local models matter for this (the link):** an unattended loop on cloud
(Haiku + Gemini) burns paid credits fast and exactly defeats the "use unspent
credits" aim — the cost lands on API spend instead. **Full-local (or hybrid)
inference is what makes long autonomous/overnight running viable without blowing
up credits.** So local models (below) and #3 are the real enablers of this goal.

---

## 5. Episodic observation + social memory layer

**Status:** Not started · **Independence:** Extends #1 · **Source:** dreams iteration 1
(`plan/dreams/dreams_2026-06-24_2308.md`)

Today observation is split: spatial facts → `world_places.db` (good); everything episodic →
free-text `memory.json`, capped at 30 and trimmed. No structured record of *what happened* or
*who an agent met*, and recall is just importance+recency. Long/overnight runs forget.

- [x] **Episodic observation record** — persist structured per-tick events
      `{world_time, grid_cell, place, saw[], action, outcome}`. ✓ 2026-06-26 — `EpisodicLog`
      (`episodic_memory.py`, append-only per-agent `episodes.jsonl`); `AgentManager._record_episode`
      records each acted tick in the live path; `query(place=/character=)` for recall. Offline test:
      `test_episodic_memory.py`. *(Wired in the live decision path; explore-mode ticks not yet logged.)*
- [x] **Social/acquaintance store** (per agent) — `{character: {first_met, last_seen, last_cell,
      meet_count, interaction_count, sentiment}}`. ✓ 2026-06-26 — `SocialMemory`
      (`social_memory.py`, per-agent `social.json`); fed from perceived characters via
      `AgentManager._record_sightings` in the perceive phase; acquaintances surfaced on the
      observation for recall. Offline test: `test_social_memory.py`.
      `speak_to` now logs an interaction with each perceived named person
      (`AgentManager._record_interactions`, neutral sentiment — affinity isn't inferred without a
      real signal). *Still open:* a sentiment policy (would need an LLM/heuristic signal).
- [ ] **Social goal hooks** — let the decision layer propose "greet <person not seen today>" /
      "go where people are" (needs #1 to resolve person/place → location to navigate).
- [x] **Memory retrieval** — relevance = recency ⊕ spatial (same cell/place) ⊕ social (known face
      present). ✓ 2026-06-26 — `EpisodicLog.relevant()`; surfaced as `observation["recent_episodes"]`
      (top 5) in recall. Tested by ordering properties, not magic constants (`test_episodic_memory.py`).
      *Still open:* periodic **consolidation** (summarising old episodes) — needs an LLM summariser,
      so deferred out of the loop.

Open Qs (for human): episodic obs shared vs private per agent? scripted vs LLM-chosen sociality?
rolling window + consolidation vs full episodic history?

---

## 6. Map feature — named-place query + manual capture + lizard-brain routing

**Status:** Not started · **Independence:** Builds on #1 (place resolver) · **Source:** user, 2026-06-26

A first-class **"map"**: a queryable set of **named places**. An agent asks the map *what
places exist* (and roughly where), picks a destination, then asks **lizard brain** *how to get
there* — lizard brain returns a **path / road-map** (a route to follow). #1 already built the
*lookup half* (name → cell → world location, `find_named_cell` + `cell_center`); this item adds
the **map query surface**, a **manual authoring mode**, and the **routing call**.

**Two SIM modes for building the map:**
- [ ] **Explore mode** (exists today) — agents build the map out themselves via the
      frontier/explorer policy, naming cells as they go (`PlaceDB.set_name`).
- [ ] **Manual / authoring mode** (new) — the **end user** moves around the world and takes
      **"snapshots"** at a spot, creating a named place from that location (screenshot + name +
      world position → `PlaceDB.set_name`). Lets a human author the map without running agents.
      *(Per [[feedback_drag_and_drop]]: the user must not need Unreal knowledge — capture is a
      button + a name, the world position is ours to read.)*

**The agent → map → lizard-brain flow:**
- [x] **Map query** — expose the named places to an agent: "what places do I know?" returns the
      named cells. ✓ 2026-06-26 — `PlaceDB.all_named_places` + `AgentManager.known_places(location)`
      (name + compass bearing + distance_m, nearest first); surfaced as `observation["known_places"]`
      (nearest 8) for recall, so the agent can pick a destination by name and `walk_to` resolves it
      (#1). Offline test: `test_map_query.py`. *(Chose context-injection over an LLM tool for now —
      revisit if the place list grows large.)*
- [ ] **Lizard-brain routing** — agent asks "route me to <named place>"; lizard brain uses a nav
      primitive (navmesh **path query**) and returns a **path** — a sequence of waypoints/headings
      to the place. The LLM still *decides whether to follow it*; lizard brain only reports the route.

**Design tension to resolve (human):** returning a *path* brushes against the **lizard-brain
contract** ([[feedback_lizard_brain_contract]], [[architecture_lizard_brain_sensing]]): lizard
brain reports **facts**, never advises. Keep it on-contract by treating a path as **facts**
("waypoints: NE 40m → E past the fountain → N 15m"), **semantic** (per [[architecture_lizard_brain_sensing]]
the output is generic labels/headings, never raw engine waypoints or actor names), and
**non-prescriptive** (the LLM chooses to follow, deviate, or ignore it — consistent with
[[architecture_engine_agnostic_navigation]]: the cognitive loop owns navigation decisions, the
engine just answers "is there a path and what is it").

Decisions (human): map query as an LLM tool vs. context injection? manual-mode capture UI — where
(settings page #2 / a new authoring view) and what's in a "snapshot" (screenshot + name + pos)?
path granularity — coarse semantic directions vs. a waypoint list? does lizard brain *walk* the
path (follow waypoints) or just *hand it back* for the LLM to drive step by step?

Relates to: #1 (resolver — lookup half done), #5 (social/episodic — "places where people are"),
[[architecture_engine_agnostic_navigation]], [[architecture_lizard_brain_sensing]],
[[feedback_lizard_brain_contract]], [[feedback_drag_and_drop]].

---

## 7. Community place-cell sweep — unexplored-cell 360 + breadcrumbs  *(mechanics; role RETIRED)*

**Status:** Mechanics built; **dedicated-role concept retired 2026-07-01** — behavior folded into **#11**
· **Independence:** Builds on #1/#6 + PlaceDB · **Source:** user, 2026-06-26

The **sweep mechanic**: in a grid cell that has **no place cell**, an APC walks to the cell **center**,
does a **360 observation**, then drops a **community place-cell breadcrumb** there. The breadcrumb marks
the cell explored so other APCs reuse it and **skip the costly 360** (vision calls) — shared knowledge,
paid once. This engine is built and offline-tested (below) and stays.

> **DIRECTION CHANGE (user, 2026-07-01):** the earlier "**dedicated maintenance/monitor APC** — a
> personality-free, LLM-free system worker" concept is **RETIRED**. There is **no** special maintenance
> role. **Any APC builds a community place cell when it needs one** (it enters an uninitialized cell it
> wants to use → detours to center → 360 → breadcrumb → resumes its task). The `role:"maintenance"`
> gating (`_pulse_maintenance` and the role branch in `pulse_agent`/`tick`) should be **collapsed** so the
> sweep is a capability any APC invokes, not a role. Tracked as **#11.1**. *(Superseded design note, kept
> for history: this was previously framed as a dedicated worker "not a personality NPC" — that framing is
> now dropped entirely.)*

- [x] **PlaceDB sweep state** ✓ 2026-06-26 — `is_explored(col,row)` (named OR swept),
      `mark_swept(agent,col,row,t)` drops an unnamed community breadcrumb (first sweep wins,
      never clobbers a name), `get_swept`. Schema migrates existing DBs (adds `swept_at`/`swept_by`).
      Test: `test_cell_sweep.py`.
- [x] **Pure sweep planner / state machine** (`cell_sweep.py`) ✓ 2026-06-26 — `CellSweep` sequences
      GOTO_CENTER → observe each of 8 compass headings → DONE (sticky arrival); `default_sweep`
      builds one from the world grid (None if unbounded). Test: `test_cell_sweep.py`.
- [x] **Maintenance role + sweep behavior** ✓ 2026-06-26 — `Agent.role`/`is_maintenance` (from
      `state.json`, default `npc`); `AgentManager._maintenance_sweep` runs the sweep on an unexplored
      current cell and drops the breadcrumb on finish. All offline-tested.
- [x] **Maintenance tick action (compose sweep + travel)** ✓ 2026-06-26 —
      `AgentManager._maintenance_tick_action`: sweep the current cell, else walk to the nearest
      unexplored cell (`_nearest_unexplored_target` + `PlaceDB.explored_cells`); None when the whole
      map is mapped. Offline-tested.
- [x] **Wire the tick by role** ✓ 2026-06-26 — `_pulse_maintenance` runs a maintenance agent's
      deterministic, no-LLM tick (build obs → `_maintenance_tick_action` → bridge); routed in both
      `pulse_agent` and the multi-agent `tick()` (peeled out of the perceive/decide phases, run in
      the sequential bridge phase). Offline-tested. Safe: only `role:"maintenance"` agents take this
      path, and none exist yet.
- [ ] **Live 360 rotation+capture in Unreal** — execute `observe_heading` (rotate to yaw + capture +
      `ingest_compass`) so the sweep's landmarks become the breadcrumb's content. *Needs PIE.*
- [ ] **Spawn/config a maintenance APC** — a `role: "maintenance"` agent (likely a simple/no-mesh
      actor). Editor/config + `/create-npc`-style scaffolding. *Needs you.*

Relates to: #1 (cell_center resolve), #6 (map/known_places), #5 (episodic), engine-agnostic nav.

---

## 8. Talk to Unreal without MCP (Claude-driven + standalone)

**Status:** Not started · **Source:** user, 2026-06-28 · **Independence:** relates to #3 + the
MCP-deprecation idea

Two ways to drive Unreal, and the user wants **both** to work without the custom MCP:
- **Standalone (no Claude):** already largely solved — `UnrealBridge` talks to the engine over a
  **raw TCP socket (:55557)** that is independent of MCP/Claude, and `sim_runner` + the web cockpit
  drive the loop through it (#3/#6). This path doesn't touch MCP at all.
- **Claude-driving (when Claude is running):** today Claude reaches Unreal *through* the `unrealSIM`
  MCP tools. The question the user raised — *"how can you talk to Unreal but not use MCP?"* — is how
  Claude keeps a hands-on path once MCP is retired. Candidate: Claude calls the **runner's HTTP
  control API** (`sim_runner` on :8777) and/or a thin **bridge HTTP shim** over the existing TCP
  socket, instead of MCP tools. The web UI already proves the runner API is enough to drive the sim.

- [ ] Decide the Claude→Unreal path post-MCP: runner HTTP API (rec) vs a small bridge HTTP shim vs
      Epic's official Unreal MCP. (User likes Claude driving when it's running, but not via *our* MCP.)
- [ ] Document/expose whatever Claude needs on the runner's HTTP surface so a session with no
      `unrealSIM` tools can still inspect + nudge the sim.

Relates to: #3 (standalone runner), the MCP-deprecation idea below.

---

## 9. Dev mode vs sim mode — Claude as operator

**Status:** Not started · **Source:** user, 2026-06-28 · **Independence:** uses computer/browser use,
needs supervision first · See memory [[feedback-dev-sim-modes]].

Two operating modes the user wants framed explicitly:
- **Sim mode** — the sim runs **standalone**, web-driven, no Claude/MCP (the #3/#6 work).
- **Dev mode** — Claude Code is running and acts as the **operator**: start/stop the sim on request,
  and **help read logs + debug when things break** (a core dev-mode job).

The goal is to grow Claude into a hands-on operator of the dev loop:
- [ ] **Start/stop the World Builder web UI** (and the sim) from Claude — today `start_sim.bat` /
      `start_npc_builder.bat` boot them; wire Claude to launch/kill them (background process control).
- [ ] **Iterate on code changes via the web UI** — make a change, (re)start the UI, drive it with
      **browser use**, observe, fix. Claude has **computer + browser use**.
- [ ] **Log triage** — fluent at pulling the sim/runner logs and pinpointing failures (dev-mode's
      bread and butter).
- [ ] **Autonomy progression** — *supervised first*; once it runs smoothly, Claude does the
      start/stop/test/iterate loop **itself until credits run out** (ties into #4 / [[project_autonomous_loop]]).

Decisions (human): which logs are canonical for triage? how does Claude detect "UI is up / healthy"
before driving it (health endpoint vs port check)? guardrails for unsupervised UI-driving runs?

---

## Later / ideas

- **Bridge as a Runtime module → run the sim from a *packaged* build (no editor)** (user, 2026-06-28).
  Today the sim **hard-requires the editor in PIE**: the `:55557` bridge lives in the
  `UnrealMCP.uplugin` module declared `"Type": "Editor"` (`UnrealMCPBridge.cpp`, `MCP_SERVER_PORT 55557`)
  and depends on **EditorScriptingUtilities**, so it is **not cooked into a packaged `.exe`** — a
  standalone build would never open the socket and every tick would fail. To take the editor "out of
  the equation" the bridge must be ported **`Editor` → `Runtime`**: flip the module type/loading phase,
  drop the EditorScriptingUtilities dependency, and replace every editor-only call (editor-world actor
  lookups via `GEditor`/editor subsystems, `EditorScriptingUtilities`, etc.) with runtime equivalents
  that work in a cooked game world. Deliberate C++ work, **needs an editor rebuild** (not loop-safe).
  Big payoff: one game window, no PIE-vs-editor-world ambiguity, no multi-instance confusion (see memory
  `feedback-single-unreal-instance`), and it's the natural host for the "runs overnight" standalone sim
  (#3) — Claude could launch/kill the packaged build directly (dev mode, #9). *Until this lands, the
  editor in PIE is required and there must be exactly one instance — the user's.*

- **Deprecate the custom MCP server** (user direction, 2026-06-26). Move Claude to plain **API calls**
  for coding help and back away from the bespoke `UnrealMCP` Python MCP server entirely — **Epic now
  ships an official Unreal MCP server**, so maintaining ours isn't worth it. Phased, and done *last*
  (once the web UI fully drives the sim): (a) sim fully drivable with **no MCP** (web UI → `sim_runner`);
  (b) anything Claude needs goes through API calls / the runner's HTTP API; (c) retire
  `unreal_sim_server.py` + the `tools/*` MCP registration. The standalone-sim + web-cockpit work
  (queue #6/#7) is the on-ramp to this.

- **Hybrid provider config (cloud + local mix).** Run some roles on cloud and
  others local — e.g. cloud Haiku for decisions, local qwen for vision, or vice
  versa. Already partly possible: `LLM_PROVIDER` and `VISION_PROVIDER` are
  independent in `.env`. The feature is making the mix easy to manage (per-role,
  maybe per-agent) and surfacing it in the settings page (#2/#7). **Note (2026-06-28):** Haiku 4.5
  is multimodal, so the simplest cloud setup is now **Haiku for *both* decisions and vision** (one
  provider, one key) — Gemini is no longer required for vision (#7.0). Cloud is clearly
  faster today (~9s/tick vs ~215s cold local first tick); full-local stays the
  long-term goal once the other pieces are in. **Local/hybrid is the cost enabler
  for the autonomous loop (#4)** — unattended cloud runs burn credits. Not a
  priority now, but it's the unlock for overnight autonomy.

- **Build-documentary for YouTube (LOW PRIORITY).** *(user, 2026-06-28)* Turn the project's progress into
  a documentary series — **one video per stage/milestone** — that Claude can largely assemble. The raw
  material is already accreting: **git history** (commits = stages), **`plan/handoffs/*`** (session diary),
  the dated **backlog status banners**, the **`MASTER_PLAN` milestones** (natural episode boundaries), and
  the sim's own visuals — **PIE screen-recordings**, per-agent **`observations/*.png`**, and the web
  cockpit feed. The "money shots" are live moments (e.g. *Dufus routing to the village square* on the day
  named-place nav first worked). Plan: (a) a per-stage **narration/script** generated from the milestone +
  its commits/handoff; (b) **capture** the matching live demo (screen-record a PIE run); (c) **assemble**
  via the existing **`fal-video-pipeline`** skill. Each episode = *what we set out to do → the problem →
  the fix → the live demo*. Decisions for later: capture tooling (OBS vs. in-engine), how much is
  AI-narrated vs. the user's voice, episode cadence (per milestone vs. per session). Not loop-safe (needs
  capture + the user's channel/voice) — park until the sim is more visually compelling.

## Notes

- **The offline-testable Python core is done.** What remains is the editor/live
  half: each open item below needs Unreal/PIE, the web app running, an LLM signal,
  or a human decision. The next loop session has no loop-safe work until one of
  those unblocks (e.g. the `observe_heading` bridge handler lands).
- **#2 and #3 are coupled** — the standalone launcher probably belongs in the
  same web app that's getting the settings page and rename.
- **#4 (autonomous loop) harness is built** (`run_tests.py`, `preflight.py`,
  `autonomous_loop.md`); running it *live* is still gated by local models + #3.
- **The autonomous loop verifies via `python scripts/run_tests.py` (15/15)** — keep
  it green; preflight refuses to start on a dirty tree or `main`.
