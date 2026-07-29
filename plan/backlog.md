# Backlog

Rolling list of outstanding work — add items as they come up, check off or
delete them as they land. Not session-scoped; this is the durable home for
approved scope and priority. Handoffs are chronological session state.
Newest grooming: **2026-07-17**.

## Active view — groomed 2026-07-17

### Now

- **Live/PIE verification bundle:** #39 stale refresh and #41 truthful counts passed in SR28; finish
  #40 visible-yaw/narration grounding and verify #37 chat on its dedicated page with Dufus and Maren.

### Next

1. **#36 JSON agenda + daily ledger:** implementation and offline coverage are complete at 51/51;
   user-run live verification still needs interruption/resume plus the post-arrival `current_goal` sync fix.
2. **#37 direct APC chat live verification:** verify the moved UI still stops Dufus, supports multiple
   turns and temporary guidance, resumes prior work, and leaves Maren unaffected.
3. **#35 survey expeditions:** choose the expedition cadence, target-selection surface, chaining/return
   policy, and retry bounds before extending the now-durable survey interruption.

**Offline work built + tested 2026-07-24:** **#43** drill-down + agenda editor, **#40** survey narration
grounding, **#42** bounded action-error diagnostics. Three new test files landed at the user's explicit
request (`test_apc_agenda_ui.py`, `test_survey_grounding.py`, `test_action_errors.py`); the full offline
suite passes at **54/54**, with no regression in the previously green 51. All three still await their live
verification, which folds into the #36/#37 live session.

### Cleanup advisories (observed, not scheduled)

Raised while working, parked here on purpose — none is urgent, none should be done as a drive-by.
Add to this list rather than refactoring adjacent code mid-task.

- **`test_apc_agenda_ui.py` is not hermetic.** Its last two checks assert that
  `/api/sim/agents/<id>` returns 503 "no sim runner running". They hit the real runner URL, so the
  test **fails whenever the sim is actually running** (observed 2026-07-24 with `sim_runner` live on
  8777). The offline suite is meant to need no Unreal and no keys; it should not care whether a
  local port is bound. Fix by pointing the runner URL at a definitely-dead port for that assertion.

- **`plan/backlog.md` is ~2,800 lines and expensive to read.** A full read blows past a 25k-token cap,
  so every session pays to find the active view at the top. Suggest moving everything below the
  "Historical status log" banner into `plan/backlog_history.md` and leaving a pointer. *(Raised
  2026-07-24; directly affects per-session token cost.)*
- **`agent_runtime/agent_manager.py` is ~3,800 lines.** Tick phases, survey/interruption mechanics,
  agenda wiring, place resolution, and bridge execution all live in one class. A split along those
  seams would make each testable alone; the survey helpers are the most self-contained starting point.
- **`web_ui/main.py` is ~1,100 lines** covering world/agent CRUD, map, replay, sim proxying, settings,
  providers, and logs. FastAPI routers per concern would match how the pages already divide.
- **`templates/agent.html` nests a `<form>` inside a `<form>`** (Delete NPC inside the main edit form).
  Invalid HTML that browsers resolve inconsistently; predates this work and was left alone deliberately.
- **Template `<script>` blocks duplicate fetch/poll helpers** across `index`, `sim`, `map`, and `agent`.
  `web_ui/static/apc_drilldown.js` (#43) establishes the precedent for extracting shared JS.
- **`save_agent` silently defaults malformed form values** (`int(form.get(...) or 10)`), so a bad tier or
  interval becomes a default instead of an error — the "fail loud" rule would prefer a rejection.

### Waiting

- **#16 map authoring:** lock the required name/description fields, exact-click versus grid-center
  anchoring, default APC-place extent, and the migration/precedence rule if it replaces landmarks.
- **#35 survey expeditions + #13.4 pristine survey reset:** choose cadence/target-selection,
  chaining/return policy, and the exact purge boundary while preserving LLM agency and authored world
  configuration.
- **#32 visual cortex:** choose transient gaze retention/dedup and unique-frame retention; semantic
  place recall remains an approved implementation slice once its query surface is selected.
- **#27 later slices:** community-landmark final-approach geometry and the bounded local-recovery/
  road/dead-end policy still need their explicit design choices.
- **PIE/live verification bundle:** #23 landmarks after editor moves, #24 launcher, #14 replay,
  B7b personal space, and remaining cockpit/onboarding checks.
- **Child Blueprint meshes:** actor rebind is done; mesh selection remains an editor choice.
- **#12.2 interaction memory:** needs a compact event-schema decision before implementation.

### Loop-safe

The approved 2026-07-21 offline queue—**#39**, **#40**, **#41**, and the dedicated Chat-page slice of
**#37**—is complete at 50/50. Each item retains its listed PIE verification. #36 remains design-gated:
survey completion is now authoritative, but no structured goal-to-interruption link exists yet, so a
free-form text match must not silently clear a goal.

**Execution note 2026-07-21:** autonomous preflight was attempted after approval and correctly blocked
on the pre-existing dirty tree: the uncommitted #37 direct-chat implementation overlaps runtime, runner,
web, tests, backlog, handoff, and spec files, with `places.json` also untracked. Preserve and reconcile
that work into a reviewed clean baseline before starting #39; do not stash, discard, or absorb it into an
unrelated survey commit.

> **Historical status log below.** Dated banners and the 2026-07-01 queues are retained
> as evidence, not as current priority. The active view above is authoritative.

> **Historical — prior autonomous-loop instruction:** next credit window, say **"run the autonomous loop."**
> It reads the **"## Autonomous queue"** below, takes the next unchecked item, and grinds
> loop-safe (offline-testable) work on an `auto-loop/*` branch per `plan/autonomous_loop.md`:
> failing test → implement → `python scripts/run_tests.py` green → commit → check off.
> **Never pushes** — work piles up for human review + merge. Current policy is that the
> backlog owns scope while handoffs preserve session state; see `plan/autonomous_loop.md`.

> **Historical MVP checkpoint (2026-06-26):** *"Runs overnight, navigates to a named place,
> remembers who it met"* — at that date #1 and #5 had landed while #3 was only a factory.
> The standalone runner described as missing here was built later; see #3 and #24.

> **⚑ Status (2026-07-07, eve — camera bugs fixed + /map zoom/pan; user-verified live):** the
> "2 cameras on MAP_Camera" was the C++ capture **leaking a SceneCaptureComponent2D per shot**
> (now transient + destroyed after the file write) and the horizontal re-shoot was a **PIE/editor
> world mismatch** (set_actor_transform resolved in GWorld, capture in the PIE-preferring world —
> both now `GetGameWorld()`). `/map` gained **scroll-zoom / drag-pan / double-click reset** (author
> clicks + coord readout stay exact at any zoom). A live-verified registered top-down capture is
> installed. **User verified (plugin rebuilt, several sim runs):** zoom/pan works, **agent dots for
> Maren + Dufus show live** (#18's pending dot verify ✓), MAP_Camera BP camera rotation zeroed,
> exactly 3 CameraCaptureActors in level (Maren/Dufus/map — correct). Suite **41/41**, pushed.
> **Still to do: the user authors places.json by clicking on /map** (skipped today for speed);
> more testing tomorrow. Queue: #19 (needs a/b/c design call), #20 (instrument during runs),
> #17 routing PIE verify.
>
> **⚑ Status (2026-07-07 — WP6 + WP7 built in-session, queue items 1–2 done):** **#15 authored
> places manifest DONE** (`places_manifest.py`, `source` column authored/runtime/wake-seed,
> plan-time schedule validation, wake seed demoted to a warning fallback) and **#21 v1 sync-world
> button DONE** (`purge_wake_seeds` + `POST /api/world/sync` + /map button). Suite **37/37**,
> pushed. **For the user:** author `worlds/MCP_World/places.json` with the real spots (2026-07-06
> facts: truck (-8950, 160) owner maren; dufus home (-10460, -800) owner dufus) — nobody but you
> writes world coordinates (WP6 D7). Queue continues at **#18** (live camera — live-gated) /
> **#17** (grid-first routing).
>
> **⚑ Status (2026-07-06, later — user moved the actors; four new items #18–#21, queue re-ranked):**
> User rearranged the level in PIE: **Maren + the vegetable truck now at (-8950, 160), Dufus's home
> at (-10460, -800)** — intending all three in one district. **Facts from the grid math:** Maren is
> in cell **(6,6)** (50 cm from its west edge) and Dufus in **(5,5)** — *adjacent diagonals
> straddling the cell corner at world (-9000, 0), not the same cell.* The "(2,6)" the user read off
> the map is the ~4-cell skew — placement decisions were being made against a mis-registered map.
> **Maren wandering again = stale wake seeds**, not the wake fix regressing: her owned "the
> vegetable truck" rows still anchored at the OLD spot (~9 m east of the new one), so the geometric
> verdict was honestly "not there yet" and she traveled. **Live DB cleaned (out-of-band):** 6 stale
> owned rows deleted (maren: "the vegetable truck", "vegetable truck"; dufus: "home", "farm road",
> "village square", "main street" — all four seeded at his old day-start spot); both agents re-seed
> at their new spawns on next wake. **The manual /map png is now stale too (user: "my bad — bad
> idea")** — superseded by **#18 live registered top-down camera**. New items: **#18** (real-time
> registered map), **#19** (keep APCs on sidewalks/roads — Maren cuts through the corn field and
> back yards), **#20** (Dufus slow to start moving), **#21** ("I moved things — sync the world"
> button). **Ranked next work (before moving on):**
> **1. #15** authored places manifest — the durable fix for the whole moved-actor/stale-seed class;
> **2. #21** sync-the-world button — the recurring editor-iteration pain, v1 slice is small;
> **3. #18** live registered top-down camera — registration correct by construction + real-time view;
> **4. #17** grid-first routing — structural anti-orbit for travel;
> **5. #19** sidewalks/roads — needs #17's planner + a design call;
> **6. #16** click-to-author places — needs #18's trustworthy map;
> **7. #20** movement pacing — instrument during the next SRs.
>
> **⚑ Status (2026-07-06 — user feedback on the /map screenshot, two fixes):** **(1) Map skew
> diagnosed** — cells render 3–4 grid cells right of the world features because the capture
> (`web_ui/images/world_map_view.png`) is a hand-taken editor viewport screenshot (HUD/toolbar baked
> in), so #6c's "assume-covers-bounds" doesn't hold; the overlay math itself checks out (17×12=204,
> Maren (-8400,150)→(6,6)). **Fix:** optional `image_bounds` in `world_grid.json` = the world rect
> the capture *actually* frames; `/api/map` passes it through and `map.html` maps world→pixel
> through it. `/map` also gained a **cursor world-coord + cell readout** to measure the offset
> (hover a known landmark, e.g. Maren's spawn (-8400, 150) — the delta is the calibration).
> MCP_World numbers still to be measured, or re-shoot the capture framed exactly to bounds.
> **(2) Community place cell at wake** — user expects every explored district to get a community
> cell; Dufus never made one (wake sweep ingested observations but dropped no breadcrumb + act
> ticks are sweep-exempt, and he *acts* at home all morning). **Fix:** `_ingest_wake_views` drops
> `mark_swept` after a non-empty wake sweep — the 180° look-around counts as the district's sweep.
> Suite **35/35**. Known gap: an agent that *travels* into an unexplored cell and starts a
> scheduled act block there still won't sweep it until a travel/idle tick.
>
> **⚑ Status (2026-07-05 — user present, three items landed):** **(1) Maren wake bug FIXED** —
> the sequencer's "am I already there?" was a name-only match vs the community cell name, so on a
> fresh DB an agent standing at its scheduled place was told to travel (Maren woke at her stall and
> wandered off). Now geometric: `_at_scheduled_place` resolves the block's place (community cell =
> same grid cell; owned place = inside its extent box) and overrides the name match
> (`planner.step(at_place=...)`). **First-wake initialization:** an agent's first schedule step of a
> run seeds an unresolvable scheduled place as the agent's own place cell centered where it stands
> (editor placement = day-start spot by convention) — `test_wake_place.py`. **(2) Place cells are
> now 9×9 m around the APC** (`PLACE_EXTENT_CM` = 900, was 300); live MCP_World DB rows widened
> out-of-band. **(3) #6c BUILT** — real top-down capture under the web `/map` grid (see #6c).
> **Design call to veto:** a scheduled **"act" tick is now sweep-exempt** (partially reverses
> 2026-07-03 "sweep on entry even when acting") — Maren waking at her stall must not walk to the
> cell center to survey the district; the cell is swept on a later travel/idle tick
> (`test_cell_sweep.py` updated). Suite **35/35**. **PIE verify:** Maren wakes at the truck and
> stays (log line: `wake: seeded own place cell`); `/map` shows the grid registered over the town.
>
> **⚑ Same day, later — SR2 live run + fix:** map overlay confirmed visually (user). But Maren
> still orbited: the per-tick seed fired **too late** — the spool-up orient LLM (no schedule
> awareness) already decided "walk to the truck" and moved her, so the seed stamped the wrong spot.
> **Fix:** `_wake_directive` — at spool-up, before the orient call, seed the scheduled place at the
> **true spawn transform** and put the sequencer verdict in the wake prompt as ground truth
> ("your position CONFIRMS you are already there"); act ticks also now forbid `walk_to`-ing the
> place you're standing in (anti-orbit). Maren's SR2 mis-seed deleted from the live DB (re-seeds
> next run); bindings checked — **personalities were NOT swapped** (maren→APC_Maren_BP_C_1,
> dufus→APC_Dufus_BP_C_1). Dufus's "stuck" = directive said travel-to-'home' (his 07:00–08:30
> block) vs persona pulling to the square — the same wake fix grounds him too. Suite **35/35**.
>
> **⚑ Status (2026-07-03 — user present, two items landed):** **(1) B7b personal space BUILT** —
> lizard-brain **reflex stop**: while moving, a *mobile* blocker inside **300 cm** (`_STANDOFF_CM`
> ≈ whole person fills the camera frame, per the user's ask) triggers an immediate bridge `stop`
> (motor reflex, not a decision — the ~9 s tick cadence is too slow to react once someone is close),
> the fact renders as "your walk has been halted", and the forced re-decide (B7) lets the LLM choose:
> talk / step around / continue (doctrine: halted = close enough, do not walk closer). Facts from
> 500 cm unchanged. No C++ changes. `test_blocker_sense.py`. **Needs PIE verify.**
> **(2) Route map grid layout** — the WP5 PNG now draws the **grid cell layout**: absolute column
> numbers across the top gutter, row numbers down the left (same col,row vocabulary as `/map`
> tooltips + the facts dict); legend + prompt note updated. `test_route_map.py`. Suite **30/30**.
> Meanwhile the user is building **B1 child BPs** (APC_BP as a child of the shared base BP) in-editor
> — the blocker classifier learned `apc` so those children still read as *person* (B7/B7b keep working).
>
> **⚑ Same session, later (user: "Finish #11.2 and #3"):** **(3) #11.2 leftovers landed** — owned
> places now surface in `known_places` (anchor+offset position, `(maren's place)` owner tag in the
> prompt) and on the web `/map` (purple dot + tooltip + legend count; new `PlaceDB.all_owned_places`).
> Still open from the full #11.2 model: the 3 m extent doing geometry + multi-leg grid→grid routing.
> **(4) #3/2.4 landed — attach, don't host:** `simulation_tools.py` MCP tools are now thin
> `RunnerClient` attachers to the standalone `sim_runner` (which owns the sim lifetime + the single
> Unreal socket); no runner = loud error, no in-process fallback. Runner API grew the full director
> surface (pause/resume/agents/goal/pulse/resets/resync/world_grid); `generate_world_grid` logic moved
> into `AgentManager`. End-to-end offline test `test_sim_tools_attach.py`. Suite **31/31**.
> **Live verify (B-side):** drive the MCP tools against a real running `sim_runner` once.
>
> **⚑ Status (2026-07-01, night — user present, two items landed):** **(1) B7 offline fix built** —
> user's call: fix it **engine-agnostically** (no RVO); the lizard brain now traces ahead every moving
> tick, mobile blockers become facts that force a re-decide, the LLM sidesteps (`test_blocker_sense.py`).
> **(2) WP5/#6b signed off + built** — user answered all four gates (**Q1 = rendered IMAGE**, against
> the text rec; corridor+1 cap 15; separate renderer; travel-ticks-only): `route_map.py` + travel-tick
> injection + the PNG attached to the multimodal decision call (`test_route_map.py`). Suite **30/30**.
> **Live run same night (user):** Dufus **roams all around** (huge progress — the system is starting
> to work), the **web `/map` updates live** (B2 ✓ in essence), and B7 is **partial** — he moves around
> people but only after getting in their faces → **B7b personal-space follow-up** queued. Merged +
> pushed to `main` at the user's request.
>
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
> env upgrade). **Then ground the loop-safe queue: A1, A2, A3 all landed** (commit-per-green, unpushed) —
> **A1** web map view (`/map` + `/api/map`, watch cells build out live), **A2** staleness (`is_stale` +
> `updated_at`, real-wall-clock basis, stale cells flagged on the map), **A3** restart-from-morning
> (`restart_day()` + `☀ Restart day` cockpit button, keeps memories/places). Suite **26/26**.
> **Stopped there:** A4 (collapse the maintenance-role routing) + A5 (owned-cells schema) are live-path
> refactors held for a joint session. **Both prior decisions now answered (user, 2026-07-01):** #11.3
> staleness re-observation is **SHELVED** ("maybe we don't need this now" — signal stays, don't build the
> re-observe path); #11.2 **APC-owned place cell = a named ~3m bounding box positioned by XY offset from
> the grid's community cell**, and **navigation is grid-first** (route grid→grid, then fine-approach the
> place cell in the target grid). See #11.2 / #6b.
>
> **⚑ Autonomous-loop run (2026-07-01, later):** ran the loop against this queue — **loop-safe work is
> drained.** Only housekeeping landed: gitignored the intentional `.mcp.json.disabled` so preflight reads a
> clean tree (it was the sole thing blocking the loop). **Nothing else was loop-safe to grind:** A4
> (collapse maintenance-role routing) + #11.1 are live-path behavior changes needing PIE; A5/#11.2 is
> user-flagged uncertain ("maybe too complicated") + soft-deferred behind #6b; #11.3 shelved; #6b parked
> ("do not implement yet"); #10.5 is a live PIE tune; everything under *Outstanding/Later* is editor /
> live-sim / an LLM signal / a design call. Baseline **26/26**, preflight green. Per the loop contract
> (don't invent busywork), the loop **stops here** — remaining progress needs you (PIE / editor / a design
> decision). Best next joint move: the **B-queue** (B1 child BPs, B2 live grid/place debug on the new
> `/map`, B3 #10.5 tune, B4 restart-day verify).
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

> **⚑ Architect pass (2026-07-01, afternoon — Fable):** the stalled items are now **spec'd for executor
> sessions** (Opus/Sonnet grunt work) under **`plan/specs/`** — every design call made, exact files/
> functions/tests named, gates marked. Read `plan/specs/README.md` first (executor contract). Queue:
> **WP1** (render acquaintances/known_places/recent_episodes into the decision prompt — an architect
> *finding*: all three are computed each tick in `_perceive_and_decide` but never rendered into
> `_USER_TEMPLATE_VISION`, so #5 social recall and the #6 map query are invisible to the LLM), **WP2**
> (#10.5 balanced-gate prompt edits, offline slice), **WP3** (A4/#11.1 sweep-as-capability refactor).
> **Gated (user approval before build):** **WP4** (A5/#11.2 owned places — minimal slice defined),
> **WP5** (#6b top-down map — design answers ready for sign-off). WP1–WP3 are loop-safe and hands-off.

## Historical staged plan (2026-07-01) — completed/drained

Two ordered queues. **A** is what I grind hands-off while you're gone (loop-safe, commit-per-green, no
push). **B** is blocked on you (editor / PIE / live / a design call) — ordered so we can knock it out
together when you're back. Detail for each lives in the thematic sections below (`## N`).

### A — Completed loop-safe queue (archive)

- [x] **A1 · Web map view — watch the grid + place cells build out.** ✓ 2026-07-01 — `PlaceDB.map_cells()`
      (named/swept cells + landmark counts) + `web_ui` `GET /map` page and `GET /api/map` JSON; `map.html`
      renders the bounded grid as a CSS grid colored **named / swept / unexplored**, polls `/api/map` every
      3s so you watch cells fill in live, with a built-out % + per-cell hover (name / who / landmarks).
      Missing DB → empty map (a GET never spawns a blank world). Map nav link added. Offline test:
      `test_map_view.py` (temp world via `TestClient`). Suite 25/25. *(Live verify = B2.)*
- [x] **A2 · Grid/place staleness (#11.3).** ✓ 2026-07-01 — `PlaceDB.is_stale(col,row,max_age,now=)` +
      an `updated_at` (real UTC) column stamped on name/sweep; `map_cells(max_age_seconds=,now=)` surfaces a
      `stale` flag; the A1 map shows stale cells (red ring + count, "not re-observed in >24h"). **Basis =
      real wall-clock, not sim-time** (the `WorldClock` resets every run, so sim-time can't express cross-run
      staleness). The re-sweep that *refreshes* `updated_at` is live (#11.1/B2). Test: `test_map_view.py`.
      Suite 25/25.
- [x] **A3 · Restart the sim from morning.** ✓ 2026-07-01 — `AgentManager.restart_day()` stops if running,
      re-anchors the clock to its configured morning start (`WorldClock.reset()`), and clears each agent's
      runtime state (fresh schedules regenerate) while **preserving memories + place cells** (unlike
      `reset_agents`). Exposed end-to-end: runner `POST /reset_day` → `RunnerClient.reset_day()` →
      web `POST /api/sim/reset_day` → a **☀ Restart day** cockpit button (with a confirm). Transport tested
      offline (`test_runner_api.py`, `test_sim_controller.py`) + `WorldClock.reset()` unit test
      (`test_world_clock.py`). Suite 26/26. *(Live drive = B4.)*
- [x] **A4 · Collapse the maintenance-role gating (#11.1 logic).** ✓ 2026-07-01 (WP3 built) — sweep is
      now a capability any APC invokes: `_should_sweep_here` (schedule status act/idle in an unexplored
      cell — **never mid-travel**) starts the sweep in `_act_agent` (first step replaces that tick's LLM
      action); agents mid-sweep skip perceive/decide and continue LLM-free via `_pulse_sweep` until
      `mark_swept` drops the breadcrumb, then the sequencer resumes the routine. Deleted:
      `_pulse_maintenance`, `_maintenance_tick_action`, `_nearest_unexplored_target` (proactive hunting
      retired with the role), `Agent.is_maintenance` (+ the tick/pulse role branches). `Agent.role` field
      stays (inert). Tests: `test_cell_sweep.py` rewritten to the capability model. Suite 28/28.
      Spec: `plan/specs/WP3-sweep-capability.md`. *(Live verify = B-side: a personality APC detours +
      sweeps in PIE.)*
- [x] **A5 · APC-owned place cells schema (#11.2) — minimal slice.** ✓ 2026-07-01 (**user approved WP4**,
      built same session) — `owned_place_cells` table (named ~3m box, XY offset from the community anchor,
      PK `(col,row,owner,name)`); `PlaceDB.add_owned_place`/`find_owned_place` (exact>substring,
      preferred-owner tie-break)/`owned_places_in_cell`; `_resolve_place_target` falls back community →
      owned (anchor + offset); `_record_place` turns a *different* name in an already-named cell into an
      owned place instead of dropping it ("My Home" inside "village square" is no longer lost). Test:
      `test_owned_places.py`. Suite 27/27. Spec: `plan/specs/WP4-owned-places.md`. *Deferred per spec D5:
      prompt/known_places surfacing, /map display, extent geometry, multi-leg grid→grid routing (#6b).*
- [x] **A6 · Render recall context into the decision prompt.** ✓ 2026-07-01 (WP1 built) — new prompt
      sections **People You Know / Places You Know / Relevant Past Moments** rendered from
      `acquaintances`/`known_places`/`recent_episodes` (previously computed every tick but never shown to
      the LLM — social recall #5 and the map query #6 were invisible). Renderers are pure + tested
      (`test_prompt_context.py`). Spec: `plan/specs/WP1-recall-context.md`.
- [x] **A7 · #10.5 balanced-gate prompt edits (offline slice).** ✓ 2026-07-01 (WP2 built) — "What Wins
      Right Now" block (routine wins; only a known person / being spoken to interrupts; resume after),
      exploration gated on an empty schedule, travel directive stated as the priority. Contract-pinned by
      string tests; **live tune + verify stays B3.** Spec: `plan/specs/WP2-reaction-gate.md`.

### B — Historical joint-session queue (use the active Waiting list above)

Ordered for a joint session:

1. **B1 · Child Blueprints** `BP_Dufus` / `BP_Maren` (child of `BP_CameraNPC`, mesh override + rebind).
   *Editor + mesh choice.* — you named this as a next thing; detail in **"▶ Next up"** below.
2. **B2 · Live grid/place debug in PIE** — **mostly ✓ 2026-07-01 night (user):** Dufus roams freely and
   the **A1 `/map` page updates live** as he goes. Still worth a focused pass: cell *reuse* on a revisit,
   A2 staleness flags, a sweep populating landmarks (B5), and the WP5 route-map PNG on a travel tick.
3. ~~**B3 · #10.5 balanced-gate live tune**~~ — **VERIFIED LIVE ✓ 2026-07-01 eve** (two PIE runs).
   Run 1 exposed the failure precisely: the travel intent led with the activity ("It's time to greet
   passers-by — head to...") so Dufus greeted strangers en route and stalled at the gas station. Fixed
   destination-first (`2f2aece`); run 2: the gate held **every tick** — "I see two unknown people ahead...
   but I gotta keep heading", "my routine says to head straight". Maren stayed at her post both runs.
   *(Friend-interrupt path still untested — the two NPCs haven't met.)*
4. **B4 · Restart-from-morning live verify** — drive the A3 reset button against PIE.
5. **B5 · `observe_heading`** — **built offline 2026-07-01, NO C++/rebuild needed** (composed from
   `set_facing` + `capture_view` + perceive + `ingest_compass` — the wake look-around's own primitives).
   What's left of B5 is just the **PIE verify**: watch a sweep turn through 8 headings and landmarks
   appear on `/map` — folds into B2.
6. **B6 · Merge `auto-loop/backlog` → `main`** + push decision.
7. **B7 · Dufus crashes into people (pawn collision during walk_to).** *(user, 2026-07-01 eve — observed
   live.)* **Offline fix BUILT ✓ 2026-07-01 (option (c) cognitive — user's call: "not game engine
   specific", so RVO/(a) is ruled out).** While moving, the lizard brain now line-traces ahead **every
   tick** (500 cm; previously only after wedging): a *mobile* category (person/animal/vehicle) directly
   ahead becomes a `blocker` fact ("person 210 cm directly ahead") and **forces a re-decide** (the
   scene-unchanged gate no longer skips the LLM), so the agent sidesteps via `walk_to
   forward-left/right` before the collision. Structures ahead stay silent while traveling (navmesh
   business); the stuck path is unchanged. Prompt: `_sense_note` (facts) + step-around doctrine.
   Test: `test_blocker_sense.py`. **PIE-verified 2026-07-01 night (partial ✓):** Dufus roams and
   *does* move around people — but only **after the fact**: he still gets right in their faces before
   sidestepping (undesirable). **Follow-up B7b BUILT ✓ 2026-07-03 (reflex stop, no C++):** inside a
   **300 cm standoff** (`_STANDOFF_CM` — whole person in camera frame, the user's spec) the lizard
   brain halts the walk itself via a bridge `stop` (motor reflex — the ~9 s tick cadence can't stop
   a walk in time once someone is close), attaches `blocker.halted`, and the forced re-decide lets
   the LLM choose from talking distance (doctrine: halted = close enough; step around if passing).
   Facts still attach from 500 cm. `test_blocker_sense.py`. **Needs PIE verify:** Dufus should now
   stop ~3 m short of people instead of face-to-face.
8. **Carryover:** settings-page UX polish, providers end-to-end spot check, navmesh `stuck` robustness.

---

## Historical autonomous queue — completed prior cycle

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

9. **Sim Run ID (`SR<n>`) — tag observations + logs per run.** *(user, 2026-06-28; **un-parked +
   core landed 2026-07-03**.)* Give every sim run a monotonic number so artifacts and logs are
   attributable to a single run for debugging. Pieces:
   - [x] **Allocator** ✓ 2026-07-03 — `agent_runtime/sim_run.py`: `allocate_run(world_dir)` reads+
     increments a **per-world** counter (first run = `SR1`; corrupt/missing → restarts at 1), plus
     `current_run`/`current_number`/`format_run`. Persists to a git-ignored
     `Python/worlds/<level>/sim_run.json`. Allocated once in `AgentManager.start_simulation` (after
     `_load_agents`, world dir = `_agents_dir.parent`), then pushed to the bridge + memory.
   - [x] **Observation files** ✓ 2026-07-03 — all three capture sites in `unreal_bridge.py`
     (`get_observation`/`capture_view`/`capture_observation`) now prefix `SR<n>_observation_<ts>.png`.
     The run id reaches the bridge via `bridge.sim_run_id` (default `SR0`, set at run start).
   - [x] **Decision log** ✓ 2026-07-03 — each `memory_store.record()` entry carries a `sim_run` field
     (via `memory.sim_run_id`), so `agent_decisions.log` is filterable by run.
   - [x] **General logs** ✓ 2026-07-08 — a `logging.Filter` that injects `SR<n>` into `AgentRuntime` log lines, wired
     into `sim_runner.py`'s format (`%(sim_run)s …`), so console/file lines carry the run. *(Remaining
     sub-item; needs care so records emitted before a run allocates one still format.)*
     SimRunFilter in sim_run.py (in-process active run set at allocation); sim_runner format carries [SR<n>]; pre-allocation records read SR0.
   - **Offline test:** `test_sim_run.py` (counter increment/persist/corruption/per-world, bridge
     filename prefix, decision-log field). **Live verify:** `SR<n>_` filenames + the `sim_run` field
     appear in a real PIE run.
   - [~] **Observation/image artifact strategy review — promoted to canonical #32.**
     *(user, 2026-07-13: “rethink the whole observation and images having sim runs on them”)*
     Re-evaluate the full lifecycle before adding more replay features: which cheap samples need no
     image, which cognition events need an image for the VLM, which frames are worth retaining for
     debugging/replay, and whether `SR<n>` belongs in every filename versus run directories or indexed
     metadata. Include retention/pruning, storage growth, failed/aborted runs, wake/sweep/route-map
     images, and the ability to reconstruct “what the APC saw when it decided.” Preserve decision/log
     run attribution unless the review finds a better trace key; do not delete existing artifacts as
     part of the design pass. **Acceptance:** document one coherent capture + attribution + retention
     policy, show how #14 replay consumes it, estimate artifacts for a representative run, and identify
     a migration path for existing `SR<n>_observation_*.png` files. **Classification:** design decision;
     implementation classification depends on the chosen storage/replay policy.
     The 2026-07-13 stopping-point review supplied the durable-place-image direction and visual-cortex
     boundary; #32 now owns the remaining transient-frame retention decision and implementation plan.

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
    - [x] **10.5 Reaction-gate weighting (tuning)** — **DONE + VERIFIED LIVE ✓ 2026-07-01** (WP2 offline
          slice + destination-first travel-intent fix `2f2aece`; see B3 above for the two-run story) — decide-phase reactivity still tends to override the
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
          agent recovers but it stalls progress. **Spec for the offline slice:
          `plan/specs/WP2-reaction-gate.md`** (A7; depends on A6/WP1 — the prompt must show "People You
          Know" before "only a known friend interrupts" can bind).

11. **Grid-cell place-cell model — central community cell + APC-owned cells + staleness.**
    *(user, 2026-07-01 — a design-reconciliation pass. "I think we have all of this in the design but make
    a backlog item to make sure.")*

    > **⚑ SIZES RESOLVED (user, 2026-07-03, from a top-down world screenshot):** the old grid cell
    > (**4 m**) ≈ the place cell (**3 m**), which collapsed the hierarchy — a 4 m cell can't hold
    > "several place cells," and 119×78 = 9,282 cells was absurd to sweep. **Decision: grid cell = 30 m
    > (`cell_size` 3000 cm) — a navigation *district*; place cell = ~3 m default, buildings bigger via
    > `extent_cm`.** MCP_World regridded to **17×12 = 204 cells**; the place DB was reset (its rows were
    > keyed under the old 4 m grid). `generate_world_grid` default is now 3000 cm; `PlaceDB.reset` now
    > also clears `owned_place_cells`; the web `/map` gridlines were darkened so cells are visible.

    User's intended model of how the world gets built out:
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
    - [x] **11.1 Any-APC self-initialization (behavior gap + role retirement).** ✓ 2026-07-01 offline
          half (WP3/A4 — see A-queue above); live behavior later verified through #34/SR21 and the
          2026-07-17 user-observed run. **Decided (2026-07-01):
          no dedicated maintenance role** — collapse the `role:"maintenance"` gating (`_pulse_maintenance`
          + the role branches in `pulse_agent`/`tick`) so the sweep is a **capability any APC invokes**, not
          a role. Behavior: an APC that enters a grid cell with no central place cell **it needs now**
          detours to center, runs the 360, `mark_swept`, then resumes its scheduled task (a #10 sequencer
          interrupt — reuses the balanced reaction gate from #10.5: initialize-if-needed wins, then resume).
          The `cell_sweep.py` state machine + `mark_swept` mechanics are reused as-is. *Live/PIE verify: a
          personality APC actually detours + sweeps a fresh cell it wants to use.*
          **Spec: `plan/specs/WP3-sweep-capability.md`** (A4).
    - [ ] **11.2 Multiple APC-owned place cells per grid cell (schema gap).** The schema allows only **one**
          place cell per `(col,row)` (it's the PK). The model wants a **central community cell** *plus*
          several **APC-owned** place cells in the same grid cell (owned by an APC, readable/reusable by
          others). **Definition (user, 2026-07-01):**
          - An **APC-owned place cell** is a **named ~3-meter bounding box** — e.g. Maren's "The vegetable
            truck", and soon her "My Home".
          - Its position is stored as an **XY offset relative to the grid cell's community place cell** (not
            an absolute world coord). The community cell is the per-grid anchor; owned cells hang off it.
          - **Navigation is two-phase, grid-first:** the APC asks lizard brain **which grid cell** a named
            place ("my home") is in, then **navigates grid→grid** (coarse) until it enters the target grid;
            once inside, it asks that grid for the named place cell and does the **fine approach** to the
            3m box (its XY offset from the community cell). *"I'd rather APCs navigate by grid, then place
            cells" — coarse grid routing first, place cells only for the last leg.*
          - Schema implication: a separate owned-cells store keyed by `(col,row,owner,name)` holding the
            **XY offset + 3m extent + owner + reusable flag**, distinct from the central community cell.
          *(User flagged this may be more than we need yet — capture the model, sequence after A1–A3 /
          the #6b APC map. Grid-first nav is the load-bearing idea.)*
          **APPROVED + minimal slice LANDED ✓ 2026-07-01** (see A5 above; spec
          `plan/specs/WP4-owned-places.md`). **Surfacing landed ✓ 2026-07-03:** owned places appear in
          `known_places`/the decision prompt (anchor+offset position, owner tag) and on the web `/map`
          (dot + tooltip + count; `PlaceDB.all_owned_places`). *Still open from the full model:* the 3m
          extent doing geometry, and multi-leg grid→grid coarse routing (#6b's course-charting).
    - [~] **11.3 Staleness / TTL re-observation. — SHELVED (user, 2026-07-01: "maybe we don't need this
          now"). Keep in backlog, don't build the re-observation path yet.** *Signal already built (A2,
          2026-07-01):* `PlaceDB.is_stale` + `updated_at` (real UTC) + a `stale` flag on the map; basis =
          real wall-clock (WorldClock resets each run → sim-time can't express cross-run age). *Parked
          (revisit later):* the re-observation path — when an APC enters a stale cell it needs, re-run the
          360 and **refresh `updated_at`** (today `mark_swept` is first-wins; would need a `refresh_sweep`),
          and the eager-on-entry vs. lazy decision. Not needed for now.
    - [ ] **11.4 Durable cardinal place surveys — canonical design in #32.** A place/grid survey should
          retain four shared N/E/S/W source images + grid/place/world metadata until a complete geographic
          DB reset. This is distinct from transient APC gaze frames. Reconcile the existing 8-heading
          semantic sweep with the four-image artifact contract during #32 design; do not duplicate storage
          policy here.
    - **Loop-safe (offline-testable):** the PlaceDB schema/ownership change (11.2), `is_stale` + the
      freshness query (11.3), and the decision logic for "enter cell → central missing/stale → sweep" as a
      pure planner step (11.1's logic). Live verify (PIE): a personality APC actually detours to center and
      sweeps a fresh cell, and re-sweeps a stale one.

    Relates to: #1 (grid/place cells — "Finalize grid cells and place cells" + "how observations attach"),
    #7 (maintenance APC sweep), #6 (map/known_places), engine-agnostic navigation.

(Items 1–6 landed 2026-06-26, 19/19 green; #7.0–7.2 + #8 landed 2026-06-28, 22/22; #10.1–10.2 + vision
Gemini-media-type fix landed 2026-06-28, 24/24.)

---

## 12. Interaction memory (met-someone events + "no need to re-greet")

**Status:** 12.1 BUILT (offline) 2026-07-03; 12.2 not started · **Independence:** Self-contained (loop-safe) · *(user, 2026-07-03)*

Fallout from B7b working: now that Dufus **stops ~3 m short and faces people** instead of walking
through them, greetings become real *interactions* with state — and that adds detail/complexity we
have to remember. Two related pieces, in priority order:

- [x] **12.1 — Don't re-greet.** ✓ 2026-07-03 *(user's higher priority — "I have been here before and
  talked to these people, no need to go back and say Hi.")* `SocialMemory` now stamps a
  **`last_interacted`** world-time on every `record_interaction` (distinct from a mere sighting's
  `last_seen`) + a `last_interacted(name)` reader. New `planner.absolute_minute`/`minutes_between`
  measure sim-time across day rollover. `AgentManager._mark_recent_greetings` tags each surfaced
  acquaintance `recently_greeted` when spoken with inside **`_GREET_COOLDOWN_MINUTES` (60)** (copies,
  never mutates the store; a backwards clock / new day reads as not-recent → greet again). The reaction
  gate reads it: `_acquaintance_lines` marks "already greeted recently — no need to say hi again", and
  the #10.5 doctrine's greet rule now excludes an already-greeted person (a nod is enough; being
  *spoken to* still gets a response). Tests: `test_social_memory.py`, `test_planner.py`,
  `test_prompt_context.py`. Suite 34/34. **Live verify:** two agents meet, greet once, then pass
  without re-greeting each tick.
- **12.2 — Interaction memory proper.** A greeting is an **interaction** with content worth keeping: who,
  when, where (grid/place), what was said, sentiment. Today speech→interaction feeds `SocialMemory`
  + episodic, but there's no first-class "interaction" record an agent can recall ("last time I saw
  Maren she was heading to her truck"). Design a compact interaction event (likely a specialization of
  the episodic log) that the decision prompt can surface under "People You Know."

Relates to: #5 (social/episodic memory), #10.5 (reaction gate — the greet interrupt), B7b (the standoff
that turns a pass-by into a face-to-face interaction).

---

## 13. World initialization + "make all the things" generation

**Status:** **In progress** — 13.1–13.3 built offline 2026-07-09 (suite 42/42 at
those commits); plugin-install guidance, clean-clone QUICKSTART validation, and broader generation
remain open. · *(user, 2026-07-03; reframed 2026-07-05 as the **downloader bootstrap**;
re-reframed 2026-07-09 to the landmark era — "paramount to making this project useful to others")*

> **⚑ Re-reframed (user, 2026-07-09):** "The world grid gen and landmark items plus dropping APCs
> into the world is paramount to making this project useful to others. We are both experimenting
> but will need to harden the **git download and set things up** sequence." The 2026-07-05 flow
> below is updated to the **landmark era** (#23/#25 replaced the click-authoring path — the level
> is the source of truth, not a web UI). **New-user sequence to harden:**
> 1. **git clone → `Python/start_sim.bat`** — uv bootstraps deps, runner + cockpit come up, tab
>    opens itself (#24 ✓). Harden: a fresh clone has **no `.env`** — first run must land on the
>    settings page saying "add your API key here", never a stack trace ([[drag-and-drop]]: fail
>    loud *with instructions*).
> 2. **Plugin into *their* Unreal project** — copy/enable the bridge plugin, confirm the 55557
>    listener in the Output Log. Harden: document it; cockpit shows "Unreal not connected — did
>    the plugin load?" instead of silent 0-agent starts (the 2026-07-08 failure, now a known class).
> 3. **Author the world in the editor** (#23): drop `Landmark_<owner>_<name>` actors + drop APC
>    child BPs at their day-start posts (editor placement = wake spot — put each APC *at* its
>    first-block landmark).
> 4. **Generate `world_grid.json`** for a fresh level — `generate_world_grid` exists but needs a
>    zero-knowledge path (cockpit button / first-run prompt), not a Claude-driven call.
> 5. **Create agents** — `/create-npc` or web form → `agents/<id>/` md files + actor binding.
> 6. **`/map` → Sync world** (landmarks listed, suspects flagged, #25 ✓) → **Start**.
> Steps 1/2/4 are the hardening gaps; 3/5/6 exist. A `QUICKSTART.md` walking exactly this
> sequence, verified against a scratch clone on a clean machine, is the acceptance test.

### Executor slices (spec'd 2026-07-09, Fable — both loop-safe, both web-layer only)

- [x] **13.1 · First-run setup banner (gap 1).** ✓ 2026-07-09 (Sonnet executor `f88f8b9`,
      worktree; merged, suite 42/42). A fresh clone has no `.env`; today nothing tells
      the user. Build: **(a)** `config_store.setup_status(env_path) -> dict` —
      `{"env_exists": bool, "provider_ready": bool, "ready": bool}`; `provider_ready` = the
      configured `LLM_PROVIDER` is `ollama` (needs no key) **or** any key matching
      `is_secret`-style `*_API_KEY` is set non-empty; `ready = env_exists and provider_ready`;
      missing `.env` → all False, **never raises**. **(b)** `web_ui`: `GET /api/setup` returns it;
      the `/` (index) and `/sim` page routes pass `setup` into their template context, and the
      templates render a dismissable banner when `not ready`: "First run? Add your model provider
      key in **Settings** →" linking `/settings` (which already exists and works). No redirect, no
      gating of routes — a loud banner only. **(c)** Offline tests (`test_first_run.py`, pattern =
      `test_settings_page.py`): status dict for missing .env / ollama-no-key / anthropic+key;
      banner present when not ready, absent when ready (TestClient + tmp .env via the same
      ENV_PATH override the settings tests use). Files: `agent_runtime/config_store.py`,
      `web_ui/main.py`, `web_ui/templates/index.html` + `sim.html` (or `base.html` if both
      inherit a block), new test. **Do not** touch llm_router/perception key resolution.
- [x] **13.2 · Grid-gen from the cockpit (gap 4).** ✓ 2026-07-09 (Sonnet executor `75ae079`,
      worktree; merged, suite 42/42; live verify: press the /map button on a fresh level).
      Executor's sound extras: proper `{ok, error}` envelope (503 runner-down / 400 manager
      error) so the callout can show failures. **Fallout fix, same session:** both worktree
      venvs failed at import on Python 3.11 — `llm_router.py:308` uses PEP-701 f-string
      syntax; `requires-python` bumped `>=3.10` → `>=3.12` (+ re-lock + smoke import), so a
      fresh clone's uv provisions a parseable interpreter (an onboarding bug #13 exists to
      kill). `generate_world_grid` exists end-to-end
      (manager → runner `POST /world_grid` → `RunnerClient.generate_world_grid`) but a new user
      has no way to invoke it. Build: **(a)** `web_ui` `POST /api/world/grid` — proxy to
      `RunnerClient.generate_world_grid()` (accept optional `cell_size`/`padding` in the JSON
      body, default 3000/800), with the same "no sim runner running" error envelope the other
      `/api/sim/*` proxies use. **(b)** `/map` page: when the level has no `world_grid.json`
      (the existing no-bounds/no-grid error path in `/api/map`), render a callout — "This level
      has no grid yet — **Generate world grid**" — whose button POSTs the new route and reloads
      the map on `ok`. Keep the existing behavior when a grid exists (no new UI). **(c)** Offline
      tests (extend `test_map_view.py` / `test_sim_controller.py` patterns): route proxies to a
      stub runner + surfaces its error when unreachable; map page HTML carries the callout when
      the grid file is absent and not when present. Files: `web_ui/main.py`,
      `web_ui/templates/map.html`, tests. **Do not** change `AgentManager.generate_world_grid`
      or the runner routes.

- [x] **13.3 · Cockpit buttons for the deep resets.** ✓ 2026-07-09 (Sonnet executor `0648b10`,
      worktree; merged, suite 42/42; live verify: click both buttons in a browser). 🧠 Reset
      agents + 🗺 Reset places now sit beside ☀ Restart day with honest confirm() text.
      **Caveat surfaced during the hand-wipe that prompted this:** maren's `memory.seed.json`
      is stale (May world: "shop canopy", "pawn shop") — Reset agents re-injects it; rewrite or
      delete the seed. (Spec'd 2026-07-09, Fable.) The user asked
      "do we have a webUI button for all this?" while we hand-wiped agent brains + the place DB —
      answer was no. `reset_agents` and `reset_places` exist end-to-end (manager → runner
      `POST /reset_agents`/`/reset_places` → `RunnerClient.reset_agents()`/`.reset_places()`)
      but the `/sim` cockpit only exposes `reset_day`. Build, mirroring the existing reset_day
      pattern exactly: **(a)** `web_ui/main.py`: `POST /api/sim/reset_agents` and
      `POST /api/sim/reset_places` proxying the client methods (same error handling as
      `/api/sim/reset_day`). **(b)** `sim.html`: two buttons beside ☀ Restart day, each with a
      `confirm()` whose text says what it really does — "Reset agents: teleport agents to their
      start spots and wipe learned memories (restores memory.seed.json if present)" / "Reset
      places: wipe the shared world map DB (landmarks re-apply on next sim start)". **(c)**
      Tests: extend `test_sim_controller.py` (stub runner grows the two methods; routes proxy +
      surface stub payloads; degrade cleanly when the runner is down, same as reset_day's test).
      Files: `web_ui/main.py`, `web_ui/templates/sim.html`, `test_sim_controller.py`. **Do not**
      touch `runner_app.py`, `runner_client.py`, `agent_manager.py`, or any #13.1/#13.2 files
      beyond these three.

- [ ] **13.4 · One reviewed “pristine survey run” reset.** Requested 2026-07-15 for the future
      whole-map survey experiment: the user wants to “clean everything out / files / db / etc” and
      let Dufus start fresh. Existing **Reset agents** + **Reset places** do not clearly cover every
      generated observation, place composite/history link, replay/log artifact, runtime schedule,
      and stale seed-memory source as one auditable operation. Design the purge boundary before
      implementation: preserve authored agent identity/goals, landmarks, `places.json`, grid/map
      calibration, and provider config by default; enumerate generated knowledge/artifacts to remove;
      preview/report every target; then perform the reset only after explicit confirmation. Decide
      whether hand-authored `memory.seed.json` is retained, ignored for this run, or separately reset.
      Acceptance requires an offline temp-world fixture proving no target escapes the world root and
      a fresh start contains no prior learned place/visual/replay state while authored world truth
      still re-applies. **Classification:** design decision first; then loop-safe filesystem/reset
      transaction plus one live cockpit verification. **Supports:** #35.

The long-term goal: **initialize a world from scratch** with **generation code that builds all the
things** — spawns/wires the actors, child BPs, agents, grid, and place cells automatically, so a new
world stands itself up. This is the automated end-state of the [[drag-and-drop]] philosophy: the end
user adds content, the system makes it work; config complexity is ours, never theirs.

**Interim (now):** until that generation code exists, **Claude Code (dev mode) does the linking by
hand when the user adds things in Unreal.** Concretely, what the child-BP rework needed this session:
- A user drops a new actor / child BP in the level (e.g. `APC_Maren_BP`, `APC_Dufus_BP`).
- CC relinks the agent config: `unreal_actor_name` (find/bind hint), `blueprint_class` (spawn
  fallback), and `display_name` (the clean name others use — engine label stays out of the sim).
- CC verifies the binding round-trips (known_characters shows the clean name; targeted actions
  resolve back to the actor) and the suite stays green.

**Toward generation (future pieces to design):**
- A world-init routine that takes an inventory of placed actors + intended agents and **emits the
  agent `state.json` + bindings** (the manual step above, automated).
- Auto-discovery of placed actors from the running level (the bridge can already `find_actor`) so the
  config can be **generated from what's actually in the world**, not hand-authored.
- Bootstrapping the grid + community place cells for a fresh level (relates to #11 activation / the
  30 m district grid — see [[grid-place-cell-sizes]]).
- Scaffolding a new agent end-to-end (the `/create-npc` skill is the seed of this).

Relates to: `feedback_drag_and_drop`, `feedback_dev_sim_modes` (dev-mode CC operates), #11 (grid/place
build-out), the child-BP rework (the first hand-linked example), `/create-npc`, **#23/#25 landmarks
(the authoring path this flow now routes through — #15 `places.json` is the secondary source, #16
click-authoring is fallback only)**, #24 (`start_sim.bat`, step 1's one-click).

---

## 14. Run replay — single-step through a sim run's observations

**Status:** BUILT (offline) 2026-07-03; further replay expansion paused behind #32 image-lifecycle
design · **Depends on:** #9 attribution + #32 artifact policy · *(user, 2026-07-03)*

> **✓ Landed 2026-07-03:** `agent_runtime/run_replay.py` (pure index/join —
> `list_runs`/`list_agents`/`list_frames`, joining each observation frame to its nearest
> decision-log entry by run+agent+time) + web routes `/replay`, `/api/replay/runs|frames|image`
> (image serve is path-traversal-guarded to well-formed SR names inside the agent's obs dir) +
> `replay.html` (run/agent pickers, prev/next + scrubber + ←/→ keys, frame beside its decision) +
> a Replay nav link. Test: `test_run_replay.py` (index, join, name-guard, routes). Suite 34/34.
> **Live verify:** run the web app after a PIE run and scrub `SR2` frame by frame.

The point of the SR<n> tag (#9): **be able to single-step through the sim runs** for debugging — scrub
the captured observation frames of a run in order (and jump between runs), seeing what each agent saw
and decided tick by tick. #9 tagged the artifacts (`SR<n>_observation_<ts>.png` + a `sim_run` field on
every `agent_decisions.log` entry); this item is the **review surface** that consumes them.

Pieces to design:
- **Group by run + agent:** list runs (from `sim_run.json` / distinct `SR<n>` in the observations dir),
  and within a run, each agent's frames in timestamp order. The filename already carries `SR<n>` +
  agent (via the per-agent `observations/` dir) + timestamp, so this is a directory/filename scan.
- **Step UI (web cockpit):** prev/next through frames, showing the observation image alongside the
  matching decision (join `agent_decisions.log` rows on `sim_run` + nearest timestamp — action,
  thought, result). A scrubber + keyboard step. Lives in `web_ui` next to the `/sim` cockpit + `/map`.
- **Cross-run compare (later):** step the *same* tick/time across two runs to see how a change moved
  behavior.

Loop-safe core: the run/frame indexing + the log-join are pure and offline-testable; the page is a
`TestClient` route like the other `web_ui` pages. Live value: watch a real run back frame by frame.

Relates to: #9 (the tag it consumes), #6/#6b (map + route images), the `web_ui` cockpit (`/sim`).
The deferred #9 observation/image artifact review is the design gate for further replay expansion.

---

## 15. Authored places manifest — the world's root configuration

**Status:** ✅ **DONE 2026-07-07** (built per `plan/specs/WP6-authored-places-manifest.md`; suite
36/36). `places_manifest.py` (load + declarative converging apply), `source` column
(authored/runtime/wake-seed) with migration, loader call in `start_simulation`,
`_validate_schedule` fail-loud at plan time, wake seed demoted (WARNING when a manifest exists).
**No `places.json` authored for MCP_World — the user places things** (spec D7; 2026-07-06 facts:
truck (-8950, 160) owner maren; dufus home (-10460, -800) owner dufus). · **Source:** user,
2026-07-05 ("the APCs don't have a root configuration — my house is over here, my vegetable truck
is over here") · **Independence:** self-contained (loop-safe); #16/#17 build on it

Today places only exist if an LLM *discovers* one at runtime or the wake-seed *guesses* one
("editor placement = day-start spot" — a convention, and SR2 showed how fragile it is: the seed
stamped the truck mid-walk). The sequencer can already answer "what time is it, where should I be"
(`planner.step`) — what it can't do on a fresh world is resolve the *where* to a real position.
The fix is **authored ground truth**: a per-world manifest of canonical places loaded into PlaceDB
at world load, before any tick.

Pieces:
- **`worlds/<level>/places.json`** — the manifest. Per entry: `name`, world `x/y` (anchor),
  `extent_cm` (default 900 = the 9×9 m place cell; bigger for buildings), optional `owner`
  (agent_id → an owned place cell: "maren's vegetable truck", "dufus's home") and optional
  `community: true` (also community-name the containing grid cell, e.g. "village square").
- **Loader** — on world load (AgentManager `_load_agents` / `start_simulation`), upsert manifest
  entries into PlaceDB (idempotent; authored entries win over runtime discoveries of the same
  name — re-running never duplicates). Grid (col,row) + dx/dy are *derived* from x/y via
  `WorldGrid`, never hand-authored.
- **Schedule validation (fail loud)** — after `generate_daily_plan`, log a warning for any block
  whose `place` resolves to nothing (manifest, community, or owned): the agent will be told to
  travel somewhere unreachable. Surfaces the "hunting for a place nobody recorded" class of bug at
  plan time instead of tick 40.
- **Wake-seed demoted to fallback** — with a manifest present, `_wake_directive` resolves
  authored places and only seeds when the world is genuinely unauthored (keep the mechanism,
  document the priority: authored > discovered > wake-seeded).
- **Offline tests:** loader idempotency, owner vs community writes, derived col/row round-trip,
  schedule-validation warning.

Relates to: #11.2 (owned place cells — the storage this fills), #13 (bootstrap flow — the manifest
is its config artifact), #16 (the editor that writes this file), [[grid-place-cell-sizes]],
`feedback_drag_and_drop`.

---

## 16. Click-to-author places on the /map — the no-Unreal place editor

**Status:** **USER LIVE-VERIFIED 2026-07-21** (author-place flow “looks good”); original implementation ✅ **DONE
2026-07-07** (suite 41/41). "Author places" toggle on `/map`: fill
name/owner/extent, click the registered map → `POST /api/places` writes `places.json` (same
normalized name = move/edit, no duplicates) and **re-applies the whole manifest to PlaceDB
immediately** (WP6's declarative converge — no sim restart). Panel lists authored entries with
per-entry delete (`DELETE /api/places`); `GET /api/places` serves the raw manifest. Fail-loud
validation mirrors the loader (blank/placeholder names, non-numeric or out-of-bounds coords,
unbounded grid); a **corrupt places.json is surfaced with a 500 and never rewritten**. Runtime
LLM-discovered rows survive every authored edit. **The user now authors MCP_World's places by
clicking** — WP6 D7 satisfied without anyone typing coordinates. · **Source:** user, 2026-07-05 ·
**Depends on:** #15 ✅, #18 ✅ (the registered map)

The #6c map is registered world↔pixel in both directions, which makes it the natural authoring
surface: **click a spot on the real top-down map → name it → optionally assign an owner/extent →
saved to `places.json` + PlaceDB.** This is the [[drag-and-drop]] answer to "how does a user say
'Maren's truck is here' without opening Unreal": they don't touch the engine at all — one
screenshot, then everything is clicks in the browser.

Pieces:
- **Pixel→world inverse** on the map page (the overlay already does world→pixel; the inverse is
  the same linear map) — click yields world (x, y), display the target cell + snap preview.
- **An "author" mode toggle** on `/map`: click → small form (name, owner dropdown from the world's
  agents or "community", extent) → `POST /api/places` → validates, writes `places.json`, upserts
  PlaceDB, map refreshes (the new box appears immediately).
- **Edit/delete** for authored entries (click an existing authored box) — runtime-discovered
  places stay read-only here.
- **Offline tests:** the POST round-trip (TestClient + temp world), pixel↔world inverse math,
  authored-vs-discovered edit guard.

**Reopened authoring direction (user, 2026-07-17):** “click somewhere in a grid, and then click an
author button” to open a focused dialog. The dialog must let the author choose **community place
cell** or **APC place cell**; choosing APC reveals a selector populated from the world's APCs. It
then accepts a brief description and offers explicit **Save** and **Cancel** actions. Save creates
the place at the clicked grid/location and refreshes the map; Cancel leaves authored state untouched.
The user expects this map-first workflow will **most likely replace landmarks**, reversing #23's
earlier editor-first direction, but that replacement is not yet locked and must not silently delete
or ignore existing landmark-authored places.

Acceptance evidence for the reopened slice: the selected point/grid is visibly retained while the
dialog is open; community versus APC ownership is persisted correctly; the APC list comes from the
current world; description round-trips through the authoring store and edit UI; Save produces one
immediate map result; Cancel produces none; malformed or conflicting entries fail visibly. Open
decisions: whether a separate place name is required or derived from the description, whether a
community place anchors at the exact click or grid center, default APC-place extent, and the explicit
migration/precedence rule among map-authored entries, `places.json`, existing landmark actors, and
runtime discoveries. **Classification:** design decision for the source-of-truth migration, then
loop-safe web/API/storage work plus live map QA.

Relates to: #15 (writes its manifest), #6c (the map surface), #2 (web app), #13 (bootstrap step 3).

---

## 17. Grid-first navigation — multi-leg routing between grid cells

**Status:** ✅ **DONE 2026-07-07; LIVE VERIFIED SR15 2026-07-13** — Dufus traveled from his authored
start to the authored village-square community cell and began greeting there. (Built per
`plan/specs/WP8-grid-first-routing.md`; suite
38/38). `route_planner.py` (pinned Bresenham cell line + leg state machine w/ skip-ahead +
B7b box-edge fine-approach), `_execute_routed_walk` leg executor (stuck replans, arrival idles),
en-route prompt narration, route-map path dots. LLM contract unchanged. v1 = straight-line legs;
sweep-data/no-go weighting is the #19c seam in `line_cells`. SR15 satisfied the coarse multi-district
live verification; landmark-level final approach and recovery remain canonical in #27. ·
**Source:** user, 2026-07-05 ("we don't really have a navigation system") ·
**Depends on:** #15 (✅ done); consumed #6b's corridor work

What exists: name→position resolution, the engine navmesh for *local* walking, lizard-brain
blocker facts + the B7b standoff, and the #6b route-map PNG on travel ticks. What's missing is the
**mid-scale**: agents travel greedily by vision, so when the destination isn't in frame they orbit
(Maren, SR2). A destination several districts away should become a *plan*: a sequence of grid-cell
legs, each leg a short navmesh walk the engine can actually do.

Pieces:
- **Route planner (pure, loop-safe):** grid A → grid B as a cell path (starts as a straight-line
  cell walk; obstacles/no-go cells can come later from sweep data) → waypoint list of cell centers,
  ending with a fine-approach to the place-cell anchor (stop at the 9×9 m box edge, B7b-style).
- **Leg executor:** a travel tick walks the *current leg's* waypoint (not the final destination),
  advancing legs on arrival; a blocked leg re-plans rather than wedging (re-uses the stuck/blocker
  facts — the cognitive loop stays the obstacle-solver per
  [[architecture-engine-agnostic-navigation]]; no engine patches).
- **Prompt surface:** the travel directive names the leg ("heading N toward cell (6,4) — 2 legs to
  the vegetable truck") so decisions and the decision log stay legible; the #6b route map draws the
  planned corridor instead of just the straight line.
- **Offline tests:** path generation, leg advance/replan state machine, arrival at box edge.

Relates to: #11.2 (grid-first decision + fine-approach), #6b (route map = the visualization of this
plan), #1 (resolution), B7b (standoff at arrival), `architecture_engine_agnostic_navigation`.

---

## 18. Live registered top-down map camera — real-time /map, registration by construction

**Status:** ✅ **Capture half DONE 2026-07-07** (user placed a `MAP_Camera` pawn — a
CameraCaptureActor subclass — and it's wired end-to-end): `POST /api/map/capture` aims the pawn
top-down over the world bounds (pitch −90, yaw −90 = north up/east right), captures 1920×1080 to
`web_ui/images/<level>.png`, and writes the exact camera footprint as `image_bounds` (the engine
capture's 90° horizontal FOV makes the frame computable — registration by construction, zero hand
calibration). "Re-shoot map" button on `/map`; image URL is mtime-versioned so a re-shoot shows
immediately. **Verified live in the editor (no PIE needed):** Maren's truck at (−8950, 160) lands
within ~4 m of its predicted pixel (the old hand shot was ~120 m off). MCP_World's registered
capture + calibration committed. **Live half DONE 2026-07-07 too:** the observe phase records each
agent's last seen position/facing (no extra engine traffic), runner serves `GET /positions`, web UI
proxies `/api/map/agents`, and `/map` draws red dots + facing tick + name every 3 s poll (runner
offline = no dots, never stale ones). Suite 40/40. **Also:** `generate_world_grid` now takes the
registration shot automatically (regrid → fresh registered map + calibration in one step; missing
MAP_Camera reported honestly, grid unaffected) — pose math shared in `agent_runtime/map_capture.py`.
**Still open:** optional re-shoot-on-timer; PIE verify of the dots during a real run. ·
**Source:** user, 2026-07-06 ·
**Supersedes:** the manual screenshot and #6c's open registration question; `image_bounds` stays
as the calibration mechanism (now machine-written).

The 2026-07-06 skew hurt twice: the overlay was wrong, *and the user placed actors against the
wrong map* (read "(2,6)" for what is really (6,6)). A hand screenshot can never be trusted; the
sim should shoot its own map with a camera whose frame is *defined* to be the world bounds — then
world→pixel is exact with zero calibration.

Pieces:
- **Engine-side capture:** an orthographic top-down capture (SceneCapture2D or equivalent bridge
  command) centered on the bounds rect, ortho width = bounds width, output aspect = bounds aspect
  → written to `images/<level>.png` on demand. No HUD, no toolbar, no guessing.
- **Bridge + runner surface:** `capture_world_map` callable from the web UI (a "re-shoot map"
  button — pairs with #21's sync) and optionally on a timer while the sim runs.
- **Real-time layer (loop-safe):** `/api/map` gains live agent positions from the runner
  (`get_character_transform` already exists); `map.html` draws moving agent dots + facing + name
  labels over the registered image, polling with the existing 3 s refresh. The *terrain* image
  refreshes on capture; the *agents* move every poll — that's the "see what's going on" view.
- **Offline tests:** agent-marker payload + rendering (TestClient); the capture itself is
  live-verify.

Relates to: #6c (the overlay engine this feeds), #16 (authoring needs a trustworthy map), #21
(same "world changed" workflow), #9 (dev-mode observability), #33 (logical grid offset; distinct
from image registration).

---

## 19. Keep APCs on sidewalks and roads

**Status:** **Folded into #27** on 2026-07-11; this section preserves the original problem and
option analysis. Do not implement (a)/(b)/(c) independently. · **Source:** user, 2026-07-06
("Maren is wandering into the corn field and people's back yards") · **Depends on:** #17

Agents cut straight lines through anything walkable — corn fields, yards. Navmesh says "walkable";
nothing says "socially, stay on the pavement." Options, not mutually exclusive:

- **(a) Engine-side navmesh area costs** — nav-modifier volumes over roads/sidewalks (cheap cost)
  vs everything else (expensive). Zero runtime code, immediate effect on every navmesh walk — but
  per-level editor work, invisible to the cognitive loop, and leans against
  [[architecture-engine-agnostic-navigation]] ("obstacles are solved by the cognitive loop, not
  engine patches"). Cheap immediate win if the user wants it; needs their call.
- **(b) Lizard-brain surface fact** — a ground probe reports *facts only* per the
  [[lizard-brain-contract]]: "surface underfoot: grass/road/pavement; nearest road ~4 m north."
  The LLM (and travel directive) get a standing rule: prefer pavement when traveling. Engine
  primitive inside, generic semantic label out.
- **(c) Route-planner weighting (#17)** — the grid-first planner prefers legs through cells whose
  sweep observations look road-like (community names/landmarks: "main street", "rural town road"),
  so multi-leg routes follow the street grid structurally instead of beelining.

Likely shape: (c) for the mid-scale + (b) for the local scale; (a) only if the user wants the
instant version. Offline tests: planner weighting (c) and the fact formatting (b) are both
loop-safe.

**(b) landed 2026-07-29, VLM variant.** User's explicit call this session: enforcement stays in the
LLM (no code-side blocking of `walk_to`) — the fix is making the disagreement between "navmesh says
walkable" and "you should not be here" an unmissable fact each tick, not a rule buried in prose the
LLM has to notice on its own. Rather than an engine ground probe (which would need per-level
authoring nothing in the repo currently has — see #53), `perception.py`'s existing per-tick VLM call
now also classifies `footing` (`pavement|road|dirt_path|grass|cultivated_field|water|other`) straight
from the image; `llm_router._seen_text` renders it as an explicit `FOOTING: <value>` prompt line
(`llm_router.py`); both `rules.md` files gained a non-negotiable line telling the LLM to turn back
when footing isn't pavement/road/dirt_path. Same session also added a companion fact for the
"moved farther from goal" half of the complaint: `agent_manager._attach_route_progress` now tracks
distance-to-destination tick over tick and stamps `delta_cm` on the route fact; `llm_router._schedule_note`
renders an explicit `PROGRESS WARNING` line when it's positive (noise-floored at `_PROGRESS_NOISE_CM`
= 200 cm). Offline: `test_seen_text_footing`, `test_perceive_parses_footing`, and the extended
`test_schedule_route_narration` in `test_route_planner.py`. **Not done, and deliberately not
attempted:** no action is blocked or auto-corrected — this is facts-plus-rules only, per the user's
choice. Live-run verification still owed: does the louder fact actually change behavior, or does the
LLM still walk into the field.

---

## 20. Movement pacing — Dufus is slow to get going

**Status:** ✅ **INSTRUMENTATION DONE 2026-07-15 — 47/47 offline green; tuning remains evidence-gated** ·
**Source:** user, 2026-07-06 ("Dufus takes a long time to move, but eventually does. Goes down street.")

Might be real (tick cadence, cooldowns, walk speed, LLM latency per decision) or might be persona
+ schedule (his own plan keeps him home until 08:30 sim time — flagged 2026-07-05 as "looks
stuck"). Don't tune blind: instrument first. Add per-agent timing to the decision log / replay
(#14): wall-clock from wake → first `walk_to` accepted → first actual displacement, and per-tick
latency broken into observe/LLM/act. Then decide whether the fix is pacing config, schedule
trimming, or nothing.

**Built:** each recorded decision now carries wall-clock `observe_ms`, per-agent parallel `llm_ms`,
and `act_ms`. Per-run movement startup tracks wake → first accepted walk and wake → first observed
displacement (10 cm jitter threshold), and adds each available milestone to subsequent timing data.
Wake entries carry available startup timing; replay's joined decision exposes the same timing object.
No cadence, schedule, persona, or walk-speed tuning was guessed.

---

## 21. "I moved things — sync the world" button

**Status:** ✅ **v1 DONE 2026-07-07** (built per `plan/specs/WP7-sync-world-button.md`; suite
37/37). `PlaceDB.purge_wake_seeds()` + `POST /api/world/sync` + a "Sync world" button on `/map`
that reports exactly what was deleted into the tip line and redraws. Deletes only
`source='wake-seed'` rows — authored (ground truth) and runtime (agent memories) rows survive;
legacy pre-WP6 rows are never guessed at. **v2 (manifest re-anchor from `actor` transforms) still
open — live-gated.** · **Source:** user, 2026-07-06 ("we also need a 'I moved things, sync the
world' button somewhere") · **Depends on:** nothing for v1; #15 for v2

Today, moving an actor in the editor silently invalidates wake-seeded owned places (and the map
png): Maren hunted a truck that was 9 m from where the DB said. The 2026-07-06 fix was Claude
deleting rows out-of-band — that must become a button.

Pieces:
- **v1 (pre-#15): re-seed from reality.** A button on `/map` or `/sim`: for every bound agent,
  read the live transform via the bridge, then delete that agent's *wake-seeded* owned rows and
  let the next wake re-seed at the new day-start spot. Reports exactly what it deleted (fail loud,
  per [[global-fail-loud]] — no silent "synced ✓"). Offline-testable logic + TestClient route;
  live transform read is thin.
- **v2 (with #15): manifest re-anchor.** Manifest entries optionally bind to an Unreal actor name
  (the truck mesh, the house). Sync reads those actors' transforms, rewrites `places.json` x/y,
  re-upserts PlaceDB, and re-runs schedule validation — authored places move *with* the world.
  Community cells whose landmarks moved get flagged stale for re-observation rather than deleted.
- **Pairs with #18's "re-shoot map" button** — one "the world changed" workflow: re-shoot +
  re-sync.

Relates to: #15 (authored ground truth), #18 (same trigger), #13 (bootstrap = the first-ever sync),
`feedback_drag_and_drop` (config complexity is our problem, not the user's).

---

## 22. Retire the MCP layer — the sim is standalone; the socket class moves to agent_runtime

**Status:** ✅ DONE 2026-07-08 (Sonnet executor) — suite 40/40 with mcp/fastmcp uninstalled ·
**Source:** user, 2026-07-08 ("we don't use mcp anymore. Do we have mcp code still?") ·
**Depends on:** nothing

MCP is dead weight now: the sim runs via `sim_runner.py` + the web UI, and dev-mode driving goes
over the runner's localhost HTTP API (`RunnerClient`), not MCP tools. But the raw Unreal socket
class (`UnrealConnection`, TCP 55557) still lives *inside* `unreal_sim_server.py`, so every
process — runner, web UI, offline suite — transitively imports the `mcp` pip package just to
borrow the socket (`unreal_bridge.py:38`). That's why the suite broke when `mcp` vanished from
the venv (2026-07-07 handoff) and why "pip install mcp" logs still appear in a repo that
supposedly dropped MCP.

Plan (all offline-testable):

1. **New `Python/agent_runtime/unreal_connection.py`** — move `UNREAL_HOST`/`UNREAL_PORT`, the
   `UnrealConnection` class, the module singleton, and `get_unreal_connection()` verbatim from
   `unreal_sim_server.py` (lines 32–255). Module logger `logging.getLogger("UnrealConnection")`;
   **no `logging.basicConfig`** — each process owns its logging (side effect: the stray
   DEBUG-to-`unreal_mcp.log` config that piggybacked on this import dies; `sim_runner.py` already
   configures its own).
2. **`agent_runtime/unreal_bridge.py`** `_send()` imports
   `from .unreal_connection import get_unreal_connection` instead of `from unreal_sim_server …`.
3. **Delete:** `Python/unreal_sim_server.py`, `Python/tools/` (only `simulation_tools.py` in it),
   `Python/scripts/agent_runtime/test_sim_tools_attach.py` (suite 41 → 40 by design — the surface
   under test is gone), `mcp.json`, `restart_unreal_sim_server.bat`,
   `Python/restart_unreal_mcp_stdio.ps1`. (`RunnerClient` **stays** — web UI + sim_runner use it.)
4. **`Python/pyproject.toml`:** drop `mcp[cli]` and `fastmcp` deps; drop
   `py-modules = ["unreal_sim_server"]`; fix the project description (it still says "MCP is the
   communication layer").
5. **Docs (light touch, only where misleading):** `README.md` (MCP-server section, restart
   section, `mcp.json` snippet), `Python/README.md` (add-a-tool paragraph → point at
   `unreal_bridge` + runner API). Historical docs (`Docs/`, handoffs, this backlog's history)
   stay as written.
6. **Verify (success criteria):** `pip uninstall -y mcp fastmcp` from the venv, then
   `scripts/run_tests.py` → **40/40 green** — the suite passing *without* the package installed
   is the proof the dependency is really gone. Plus `grep`-clean: no live `from mcp`/`import mcp`
   outside `plan/`/`Docs/`.

Relates to: #3 (independent sim lifetime — this finishes the decoupling), #8 in the autonomous
queue (retired the authoring half on 2026-06-28; this retires the rest),
`project_identity` (sim, not MCP bridge).

---

## 23. Landmarks — BP-authored ground-truth places (author the world in the editor, not a UI)

**Status:** ✅ Python half DONE 2026-07-08 (Sonnet executor) — suite 41/41; further landmark rollout
is paused while reopened #16 decides whether map authoring replaces landmarks · **Source:** user,
2026-07-08 ("during a
setup phase, the world author should place BPs at certain locations before sim runs… back away
from building a full blown sim UI, and just let the APCs build things") ·
**Depends on:** #15 (reuses the manifest pipeline as-is)

**Direction reset.** Authored ground truth moves *into the level*: the author drops a marker BP
where a place is; the sim reads it. The level becomes the single source of truth, so the whole
drift class of bugs (truck 9 m from where the DB said, wake-seed guessing, stale map coords)
stops existing — move the actor, the place moved. `/map` demotes to viewer/debug; #16
click-authoring stays as a fallback but is no longer the recommended path; `places.json` stays
supported (landmarks are simply a **second entry source** feeding the same `apply_manifest`).
Full sim-authoring-UI ambitions are parked: APCs build everything else themselves — landmarks
are their starting points.

**Vocabulary (locked, user 2026-07-08):** the term is **landmark** ("anchor" rejected — means
too much). Tiers: **landmarks** (author, editor, ground truth) → **community cells** (APC-built
at runtime) → **memories** (episodic/social/spatial).

**Authoring contract (user side, editor):**
- Create `Landmark_BP`: a cheap marker actor — editor billboard/sprite, `bHiddenInGame`, no
  collision, no variables needed for v1.
- Drop an instance and set its **actor label** to `Landmark_<owner>_<place name with
  underscores>`: `Landmark_maren_vegetable_truck`, `Landmark_dufus_home`,
  `Landmark_community_town_square`. Owner token = text up to the next underscore;
  `community` = shared/unowned. Name = the remainder, underscores → spaces.
- Detection is by **label prefix, class-agnostic** — renaming a real prop's label (the actual
  truck mesh) also works and pins the place to the prop itself.
- Caveat: UE auto-suffixes duplicated labels (`…_home2`) — the wrong name shows loud on /map;
  fix the label.

**Why label, not BP variables:** `get_actors_in_level` already returns
name/label/class/location for every actor (`UnrealMCPCommonUtils::ActorToJson`) — **zero C++,
no plugin rebuild**. Reading BP variables over the socket is a v2 (new plugin command +
rebuild) if labels ever feel clunky.

**Plan (Python half, all offline-testable):**
1. New `Python/agent_runtime/landmarks.py`:
   - `landmark_from_actor(actor: dict) -> dict | None` — `None` (silently) for non-`Landmark_`
     labels; malformed landmark labels (`Landmark_`, `Landmark_maren_`, blank name) are
     `logger.error`-ed and skipped (fail loud). Valid → the same normalized entry shape
     `load_manifest` returns: `{name, x, y, owner, community, extent_cm, actor}` with x/y from
     `actor["location"][0..1]`, `owner=None` + `community=True` for the `community` token,
     `extent_cm=PLACE_EXTENT_CM`, `actor=actor["name"]` (free #21-v2 provenance).
   - `landmarks_from_actors(actors: list) -> list[dict]`.
   - `merge_entries(landmarks, manifest_entries) -> list[dict]` — dedupe key
     `(owner or "", name.casefold())`; **landmark wins**, shadowed `places.json` entry is
     `logger.warning`-ed. Landmarks first in the returned list (apply's first-wins cell rule).
2. `agent_manager.py` `start_simulation` (the `places.json` block, ~line 249): fetch
   `self.bridge.get_level_actors()`, parse landmarks, merge with `load_manifest` entries, apply
   the merged list. `_manifest_present = True` iff the merged list is non-empty. Log counts
   separately: `landmarks: N (level), places.json: M, applied: {summary}`. Unreal unreachable →
   `get_level_actors()` returns `[]` → places.json only, `logger.info` says no landmarks found.
3. `/api/world/sync` (`web_ui/main.py`, #21): after `purge_wake_seeds`, rescan —
   `unreal_client.get_actors()` → landmarks → merge with places.json → `apply_manifest`.
   Response gains `landmarks` + `applied`; the `/map` tip line reports them. (`unreal_client`
   is already stubbed by existing tests — same pattern.)
4. **No schema change:** landmark rows are written `source='authored'` (they *are* authored
   ground truth); provenance is logged, not stored. `clear_authored()` convergence covers them.
5. Tests: new `test_landmarks.py` (parser valid/malformed/non-landmark cases, community token,
   underscore names, merge precedence, stub-actors → PlaceDB end-to-end: right cell + dx/dy +
   owner) + extend the sync-route test with stubbed `unreal_client`. Suite 40 → 41.

**Live half (user, next session):** create `Landmark_BP`, drop `Landmark_maren_vegetable_truck`
at the truck and `Landmark_dufus_home` at the house, press **Sync world** (or start a run) —
then watch wake behavior: Maren stays at her truck, Dufus home until 08:30. This replaces the
"click places on /map" step from HANDOFF_2026-07-07.

Relates to: #15 (pipeline reused), #16 (demoted to fallback), #21 (v2 re-anchor subsumed —
landmark rescan *is* the re-anchor), #18 (map viewer unchanged), memory
`project_landmarks_direction`.

---

## 24. start_sim.bat opens the cockpit page itself (one batch file, one double-click)

**Status:** ✅ Built 2026-07-08 (Sonnet executor) — live double-click verify remains the user's ·
**Source:** user, 2026-07-08 ("make the start_sim bat run so the web page just opens
and we only have one batch file") · **Depends on:** nothing

Half is already true: after #22, `Python/start_sim.bat` is the repo's **only** batch file
(engine build scripts aside). Remaining: today the user must read the console and type
`http://127.0.0.1:8765/sim` — the bat should open it in the default browser once the cockpit
is actually listening.

Plan:
- Before the blocking `uvicorn` line, launch a minimized background waiter:
  `start "" /min powershell -NoProfile -Command "for($i=0;$i -lt 30;$i++){ if(Test-NetConnection
  127.0.0.1 -Port 8765 -InformationLevel Quiet -WarningAction SilentlyContinue){ Start-Process
  'http://127.0.0.1:8765/sim'; exit } Start-Sleep 1 }"` — polls up to 30 s (first run can be
  slow while `uv` resolves), opens `/sim` exactly once when the port is live, exits silently if
  the server never comes up (the console error is already loud in that case).
- Banner text gains "the cockpit page opens automatically".
- No second .bat, no .ps1 file — the waiter stays inline so the one-file rule holds.

**Verify:** executor = static + snippet check only (run the waiter loop standalone against a
closed port with a short count → exits quietly; confirm exactly one repo .bat). **Live
double-click = user** (server boots + browser tab appears).

---

## 25. Landmark hardening — the author's typos are our problem

**Status:** ✅ DONE 2026-07-08 (Sonnet executor) — suite 41/41 · **Source:** user's first live
authoring attempt, 2026-07-08 — three landmarks, three hazards (screenshot):
`Landmarlk_Dufus_Home` (prefix typo → silently invisible), `Landmark_Maren_Vegitable_truck`
(owner case + name spelling), `Landmark_Maren_home` (owner case breaks the case-sensitive
`preferred_owner` tie-break in `find_owned_place` — Dufus resolving "home" could get Maren's) ·
**Depends on:** #23

Per `feedback_drag_and_drop`: config complexity is ours. Three fixes, all in the #23 scan layer —
**`place_db.py` matching stays untouched** (normalize at the boundary, not in the store):

1. **Owner casefold + case-insensitive prefix** (`agent_runtime/landmarks.py`):
   `owner = owner_token.casefold()` (agent ids are lowercase; `Community`≡`community` too), and
   the `Landmark_` prefix match becomes case-insensitive (`landmark_maren_home` works). Display
   name stays as authored (name matching is already case-insensitive downstream).
2. **Near-miss prefix detection.** New `scan_landmarks(actors) -> {"entries": [...], "suspects":
   [...]}`: a label whose first underscore-token casefolds to within **Levenshtein distance 1–2**
   of `landmark` (but isn't it) is a *suspect* — `logger.error`-ed and returned, never guessed
   into a place. Tiny inline DP levenshtein, no new deps. `landmarks_from_actors` stays as a thin
   entries-only wrapper (API compat).
3. **Visible sync report.** `agent_manager` logs suspects at error level at sim start.
   `/api/world/sync` response gains `landmark_places` (`["maren/vegetable truck", …]`,
   `community/<name>` for community) and `suspects` (raw labels); the `/map` tip line prints
   both — applied names in one glance, and `⚠ ignored near-landmark labels: … (check spelling)`
   when a suspect exists. The un-fixable case (a *spelled-wrong name* like "Vegitable") becomes
   visible by reading the applied list.

Tests (`test_landmarks.py` + `test_world_sync.py`): case-insensitive prefix accept; owner
casefold (`Landmark_Maren_home` → owner `maren`); `Landmark_Community_town_square` → community;
suspect detection (`Landmarlk_Dufus_Home` → suspect, `PlayerStart`/`MAP_Camera` → not);
`scan_landmarks` shape; sync response carries `landmark_places` + `suspects`.

---

## 26. Dead-end recognition — navmesh-reachable ≠ worth walking

**Status:** **Folded into #27** on 2026-07-11; this section preserves the observed failure and
candidate signals. Do not build a separate memory-only patch before the movement-controller
contract is approved. · **Source:** user, 2026-07-09, watching SR9+: *"Dufus took off down the street, came back
and oscillated back and forth into/out of a yard. Just because a nav mesh says a bot can walk
there doesn't mean they should. Dead end recognition another backlog item."*

The failure: greedy-by-vision travel wanders into pockets (yards, alcoves, fenced corners) that
are navmesh-legal but lead nowhere, then oscillates in/out because each re-decide sees the same
tempting opening. Engine-agnostic per [[architecture_engine_agnostic_navigation]] — the fix is
cognitive, not a navmesh patch:

- **Recognize** ("I entered this pocket and had to come back out") — candidate signals we already
  have: `_no_progress` / same-cell stuck counts, revisit-within-N-ticks of a just-left cell,
  route-leg regression (#17's leg counter going backwards).
- **Remember** — a "dead end toward X" note (place/episodic layer) so the *next* travel decision
  is told "the yard on your right dead-ends" as a fact ([[feedback_lizard_brain_contract]]: facts,
  not advice).
- **Route around** — #17's grid-first legs shrink the problem (a routed agent has less reason to
  enter a yard at all); #19's sidewalk/road preference then biases the fine legs. Spec after #17
  lands; this item holds the user's framing so it isn't lost.

---

## 27. Navigation executive + deterministic movement controller

**Status:** **APPROVED / IN PROGRESS** — authoritative scheduled-travel slice **LIVE VERIFIED
2026-07-15**; earlier robustness slices are also built. SR14 proved correct
semantic destination choice and progress, and SR15 (2026-07-13) proved arrival at the authored village
square with no stuck event. Persistent navigation-ticket, road preference, and deliberate obstacle/
dead-end recovery remain. · **Canonical for:** #19 road/sidewalk preference and #26 dead-end recognition ·
**Builds on:** #17 routed semantic travel (live arrival verified in SR15)

The current navigation path mixes two control models. A scheduled destination creates a routed
semantic trip, but the decision prompt still encourages frame-by-frame directional `walk_to`
actions. The model can therefore bypass or destabilize the cached route while deterministic state
only reacts after the movement has already gone wrong.

Proposed responsibility boundary:

- **AI executive:** choose or change durable semantic intent — destination, activity, interaction,
  or explicit cancellation. It does not steer every movement frame.
- **Persistent navigation ticket:** destination identity, endpoint, route cells, current leg,
  progress, retries, arrival, cancellation, and terminal failure survive across decisions.
- **Deterministic movement controller (lizard brain):** advance the ticket, keep personal space,
  follow socially valid surfaces, detect no-progress/regression/dead ends, retry locally, and report
  facts/outcomes to the executive.
- **Engine-neutral embodiment port:** expose pose, movement command/status, obstacle/person/surface
  facts, and stop; keep Unreal TCP details in the first adapter.
- **Spatial roles stay distinct:** grids index exploration/routing, place cells define semantic
  arrival, and `Landmark_*` actors provide authored anchors.
- **Headless reference world:** a tiny deterministic adapter proves route progress, recovery,
  arrival, and failure without Unreal or an LLM.

Approval gate satisfied 2026-07-11 when the user asked Codex to make the APC body less brittle and
write the movement code. Continue in small acceptance-tested slices; the persistent ticket/headless
adapter comes next, with road preference and dead-end recovery behind that seam.

**First slice landed offline (2026-07-11):** scheduled `wander`/directional movement is clamped
inside the active community cell or owned-place box (fixes Dufus's square→leave→return loop);
authored owned landmarks outrank runtime community aliases and wake seeds with conservative
one-edit typo tolerance (`vegitable truck` resolves for `the vegetable truck`); every decision gets
deterministic nearby-APC distance facts in addition to VLM sightings; the latest structured vision
result persists as `last_perception.json`; and the cockpit gained **Capture starts** so deliberate
editor placement can replace stale reset coordinates without hand-editing JSON. These are seams
toward the proposed controller, not the persistent navigation ticket itself.

**SR15 arrival finding (user visual acceptance, 2026-07-13):** Dufus traveled down the street and
stopped near the lower-left corner of the destination grid cell, not near the physical
`Landmark_Community_village_square` actor. That matches current code: community landmarks name a
30 m district, `_resolve_place_endpoint` returns `extent_cm=0`, and entering anywhere in the cell is
arrival. This proves coarse routing but exposes the missing fine leg. Design decision for the next
slice: a community landmark should continue naming the broad district while also retaining its actor
XY/extent as the scheduled-trip endpoint; shifting the whole grid (#33) may improve layout but must not
stand in for landmark-level arrival semantics. Acceptance: a trip first reaches the correct district,
then approaches the landmark extent, while generic community exploration may still treat cell entry as
sufficient.

**SR19 controller finding (2026-07-14):** the corrected start and #34 travel-sweep gate both worked.
Wake issued the correct deterministic eastbound waypoint from `(-10460,-800)` to `(-7500,-850)`, but
subsequent LLM decisions repeatedly said "east" while emitting relative ~15 m movement steps. Once the
avatar had turned, relative `forward` physically sent it west and then northwest into woods. The live
`route_map.png` made the split explicit: A (actual cell `(5,3)`) was disconnected from the still-cached
row-5 route to B (village square `(8,5)`). Next slice should make a scheduled named-place ticket
authoritative, reject ordinary relative movement while it is active, allow bounded directional motion
only for confirmed blocker/stuck recovery, and reconnect/replan when actual position is genuinely off
route.

Acceptance for the eventual umbrella item: a named-place trip cannot be replaced accidentally by
directional steering; local avoidance does not discard the destination; progress/failure is
observable; and the same navigator passes in both the headless adapter and Unreal integration.

**Authoritative-travel slice built (2026-07-15):** `_execute_world_action` now rewrites ordinary
scheduled `wander` and directional `walk_to` actions to the active named schedule destination before
relative movement can execute. This seam covers normal decisions and wake first-actions; the existing
grid router emits the deterministic next cell-center waypoint and replans from the observed cell on a
stuck report. The SR19 regression pins Dufus at cell `(5,5)`, facing west, while traveling to village
square `(8,5)`: an LLM `forward` action sends `[600,200,90]` east and caches the village-square route,
not a westward relative step. Recovery exceptions remain a later explicit policy decision. Full
offline suite: **44/44 passed**.

**Live acceptance (2026-07-15, user run):** Dufus went straight to the village instead of turning
west/east and leaving the route for the weeds. This closes the SR19 authoritative-control defect.
The umbrella item remains open only for the separately waiting community-landmark fine arrival and
bounded blocker/stuck recovery, road, and dead-end policies.

---

## 28. Runner tick safety — serialize entry points and validate cadence

**Status:** ✅ **DONE 2026-07-11** — manager-owned non-waiting tick gate; runner returns HTTP 409
for conflicting whole-sim/per-agent requests; `/status` exposes the active entry for cockpit UX;
invalid cadence rejected at runner and manager boundaries; full offline suite 42/42. ·
**Source:** architecture/correctness audit

`AgentManager._loop()` awaits `tick()`, but the HTTP `POST /tick` and
`POST /agents/{id}/tick` entry points can invoke the same manager concurrently while an automatic
tick is waiting on LLM work. That can overlap bridge calls, route/sweep state, decisions, and acts.
`start_simulation()` also accepts zero or negative `tick_seconds`, so the loop can become a tight
or invalid cadence.

Required behavior:

- one manager-owned async lock covers automatic ticks, whole-sim manual ticks, and per-agent pulses;
- a concurrent manual request returns an explicit busy/conflict result rather than waiting behind a
  long LLM call or entering the bridge;
- `tick_seconds <= 0` is rejected at the runner boundary and defensively by the manager;
- offline tests force overlap with a controllable await and prove only one tick reaches observe/act;
- existing sequential bridge and parallel-per-agent LLM behavior inside one tick stays unchanged.

Implemented in `agent_manager.py` and `runner_app.py`; regression coverage lives in
`test_pacing_and_reset.py` and `test_runner_api.py`.

---

## 29. Contain cockpit world and agent filesystem paths

**Status:** ✅ **DONE 2026-07-15 — 45/45 offline green** · **Source:** architecture/correctness audit ·
**Touches:** `web_ui/main.py` and web-route tests

Several cockpit routes join untrusted `{level}` and `{agent_id}` values directly under
`WORLDS_DIR`; the delete route passes that result to `shutil.rmtree`. Creation validates a new
agent id, but edit/read/delete paths and level names do not share a containment check.

Required behavior:

- one resolver validates identifiers and proves the resolved path remains under the expected
  world/agents root before every read, write, mkdir, or delete;
- reject traversal, separators, absolute paths, empty/reserved segments, and symlink escapes with a
  400/404 response; never normalize them into a different valid target;
- recursive delete operates only on the already-contained resolved agent directory;
- route tests cover encoded traversal and verify that an outside sentinel is untouched.

**Built:** one shared identifier/containment boundary now anchors world, agent, fixed child-file,
map-image, place, and replay paths beneath their trusted resolved roots before reads, writes, mkdir,
serving, or deletion. World/agent listings skip escaping links; replay indexing also rejects frame
symlink escapes. Regression coverage includes valid routes plus traversal, encoded backslashes,
absolute/reserved segments, world/agent symlinks, writes, replay, and recursive delete with outside
files and sentinels unchanged.

---

## 30. Declare the runner client's direct HTTP dependency

**Status:** ✅ **DONE 2026-07-15 — 46/46 offline green** · **Source:** architecture/correctness audit ·
**Touches:** `Python/pyproject.toml`, lockfile, dependency/import smoke test

`RunnerClient` imports `httpx` directly, but `pyproject.toml` does not declare it. The current
environment receives it transitively, which makes clean installs dependent on another package's
implementation details.

Add a compatible direct `httpx` dependency, refresh the lockfile, and verify a clean project
environment can import and construct `RunnerClient` without relying on test-only dependencies.

**Built:** `httpx>=0.25.0,<1` is now an explicit application dependency and `uv.lock` was refreshed.
The offline packaging contract parses `pyproject.toml`, requires the direct declaration, constructs
the default `RunnerClient`, and closes its HTTP client.

---

## 31. Event-driven cognition for agents settled at a known place

**Status:** ✅ **LIVE VERIFIED SR15 2026-07-13 — 43/43 offline green** · **Source:** user after SR14:
“Maren was observing a lot… if she is at a place / landmark and she knows she should stay put” ·
**Touches:** `agent_manager.py`, activity-state wording, and offline tick/pacing tests

The scene-diff gate currently forces every fourth stationary tick through the full perception and
decision path so an aimless stopped agent cannot freeze forever. That fallback is too broad for an
agent whose deterministic schedule and landmark geometry already say it should remain where it is.
In SR14, Maren was correctly at the authored vegetable truck but still produced five repeated
`idle` decisions. With both active roles on Anthropic, those decisions imply five paid vision calls
plus five paid decision calls, in addition to wake orientation.

Desired behavior:

- keep cheap engine/state sampling (position, movement, schedule time, place containment, nearby APC
  facts), but do not invoke vision or the decision LLM merely because a stationary-tick counter elapsed;
- suppress recurring model work when the current schedule says `act`, geometric place resolution
  confirms the APC is at the scheduled authored/known place, it is intentionally stationary, the scene
  is unchanged, and no relevant event is present;
- wake cognition immediately for a schedule/block transition, displacement/place change, movement or
  stuck/blocker state, a nearby APC arriving/leaving or interaction signal, a genuinely changed scene,
  or an explicit manual pulse; no paid periodic heartbeat by default for a settled routine;
- keep the anti-freeze fallback for agents that are idle without a grounded routine or whose place is
  unknown, so cost control cannot strand an agent that still needs to choose what to do;
- make cockpit/in-world activity truthful: distinguish cheap state sampling from an actual paid
  perception/decision phase rather than showing every eligibility check as `observing`.

Acceptance evidence (offline): a test runs a settled, at-landmark `act` agent beyond the old four-tick
threshold and proves the perceiver/decision router are not called; companion tests prove a schedule
transition and a relevant nearby/scene event re-enable cognition, while an ungrounded stationary agent
still receives the anti-freeze re-decision. The full offline suite must remain green. Final PIE
acceptance: in a short run Maren stays at the truck with no repeated `idle` decision rows until an
event or schedule transition occurs.

**Built:** `_observe_agent` now uses the persisted schedule and place geometry as a model-free sleep
gate; schedule/place/movement/scene/proximity events wake cognition, and explicit operator pulses bypass
the gate. Ungrounded agents retain the four-tick anti-freeze fallback. Cheap bridge checks now display
`sampling`, with `thinking` reserved for actual cognition. Regression coverage lives in
`test_event_driven_cognition.py`; `test_world_grid.py` now exercises its no-perception report directly
because manual pulse intentionally means “think now.” Full offline suite: **43/43 passed**.

**Live acceptance (SR15):** the run stopped at tick 8. Maren woke at the authored vegetable truck and
made two early `idle` decisions while Dufus was nearby/moving through her scene, then made **zero**
additional decisions from ticks 3–8 while she remained settled. Dufus continued independently, reached
the authored village square, and began greeting there. This is the intended event-driven result: paid
cognition occurred for the nearby/changed-scene events and slept once the settled scene stabilized.

**Classification:** loop-safe implementation with a focused live/PIE cost verification.

---

## 32. Visual cortex + two-tier image lifecycle

**Status:** **IN PROGRESS — core place visual memory and map inspection are live-proven; semantic
recall and transient-frame policy remain** (2026-07-15) ·
**Source:** user stopping-point review: “rebuild this image scene capture code so that a place image is
actually 4 images with north east south west as well as grid/place xy data”; follow-up: “We are
building visual memories” and every community or individual place cell needs a corresponding place
image · **Canonical for:** the
#9 observation-artifact review, #14 replay inputs, #7/#11 place surveys, and #31 event-driven cognition

The current capture path conflates three different things in one per-agent `observations/` directory:
ordinary forward-view samples, wake/sweep views, and replay evidence. `get_observation` writes a new
`SR<n>_observation_<timestamp>.png` before the image hash decides whether the scene changed, so identical
stationary scenes accumulate even when no VLM or decision call follows. Meanwhile `place_observations`
stores compass labels but not the durable source images that describe shared geography.

### Locked direction

- Introduce an engine-neutral **visual cortex** between the Unreal adapter and cognition. The engine
  port supplies raw pose/movement/proximity/capture facts; the visual cortex owns change detection,
  cached perception, image lifecycle, and the decision to request a VLM interpretation. Lizard brain
  consumes engine-neutral facts/reflex events; the executive LLM never sees Unreal actors, sockets,
  traces, capture commands, or raw coordinate plumbing.
- Separate **APC gaze/decision frames** from **place survey images**. A frame showing what Dufus or
  Maren looked at is transient evidence tied to a cognition event; it is not shared geographic memory.
- Every durable place, whether a community cell or an individual/authored/owned place, has a stable
  place identity and a corresponding **place-image record**. The rendered place image is one composite
  backed by exactly four cardinal source views: **N, S, E, W**. Its header/label band uses a black
  background with large white direction text so a VLM can reliably distinguish the views. Per the
  user's 2026-07-17 grounding requirement, the black label band also places
  `GRID X: <col>  Y: <row>` between N and S so the VLM can explicitly identify the source grid;
  precise world-coordinate overlays remain excluded.
- Store level, grid `(col,row)`, world anchor/extent, place identity/source, capture time, content hashes,
  and image revision as database metadata rather than drawing coordinates into the pixels. The stable
  place record points to its current `place_image_id`; each place-image revision points back to exactly
  one place. Filenames and identifiers are place/revision based, never `SR<n>` based.
- Place images are shared world facts rather than copies owned by whichever APC captured them. APC
  visual history is represented by visit/observation records linking `(agent, place, visited_at)` to the
  exact `place_image_id` revision seen then. Refreshing a place creates or promotes a new revision without
  rewriting the APC's historical visit. This yields a living, chronological record of where each APC
  has been without duplicating the same composite for every visitor.
- Place-scoped episodic memories remain distinct records linked to the same stable place identity. A
  place recall query can return the PlaceDB text description, current or historically seen composite,
  APC visits, and memories formed there.
- Semantic intent and routing stay separate: the LLM may resolve “the coffee shop I visited” from known
  places, descriptions, images, visits, and memories; the deterministic lizard brain then reads the
  resolved place's stored grid key and returns the grid route array. Coordinates belong in metadata and
  route facts, not in the VLM-facing composite.
- Place-survey images survive agent resets, day restarts, and ordinary sim runs. A full PlaceDB clean-out
  deletes their DB index and files together. An explicit refresh/re-sweep may replace a direction, but
  ordinary visits must reuse the existing set.
- Cheap event sampling should precede image capture where engine-neutral facts are sufficient. When a
  pixel sample is still needed for change detection, it may use a rolling scratch frame; durable storage
  occurs only under an explicit gaze/replay or place-survey policy.

### Open decisions before implementation

- **Transient gaze retention:** (a) overwrite one latest frame per APC, (b) keep a bounded ring per APC,
  or (c) content-address/deduplicate image blobs while decision/run metadata references the hash.
  **Recommendation:** (c), with a rolling scratch capture—identical pixels are stored once, replay can
  still prove what an APC saw in multiple runs, and `SR<n>` remains metadata rather than multiplying
  filenames. The user has not locked this choice yet.
- Retention for unique transient decision frames: forever, last N runs, size/time budget, or manual
  promotion. Place surveys are already decided: retain until full geographic DB reset.
- #14 replay must be redesigned around decision→image references rather than assuming every timestamped
  file in an agent directory is a meaningful frame. Existing SR-tagged files need a non-destructive
  migration/compatibility path.

### Cleanup and build plan

1. Inventory every image producer, consumer, directory, filename rule, PlaceDB observation field, replay
   assumption, and reset/delete path; classify each artifact as scratch sample, transient gaze evidence,
   cardinal source view, rendered place image, or legacy/unknown.
2. Write the engine-neutral visual-cortex contract and place-image state model. Lock stable place IDs,
   immutable image revisions, the `place_image_id` relationship, APC visit links, memory links, refresh
   semantics, and ownership/deletion rules before moving files.
3. Add schema migrations and repositories for place images, their four source views, APC place visits,
   and place-scoped memory lookup. Preserve existing PlaceDB descriptions and legacy observation rows;
   migration must be non-destructive and restartable.
4. Build and test the N/S/E/W compositor, including deterministic panel ordering, large white headings on
   black, a centered logical grid X/Y heading, consistent dimensions, missing-view rejection, and
   content hashes, without precise world-coordinate overlays.
5. Route capture through the visual cortex: cheap facts first, rolling scratch only when pixels are
   needed, durable place-image creation/refresh only for a place lifecycle event, and transient gaze
   persistence only under the separately chosen retention policy.
6. Expose engine-neutral recall operations for known/visited places, a place's image and memories, and
   an APC's chronological visual history. Resolve semantic place intent first; pass only the resolved
   grid key to deterministic route planning.
7. Update replay, reset, PlaceDB clean-out, cockpit/map inspection, and metrics around the new IDs;
   migrate or quarantine legacy SR-tagged images only after referential-integrity checks.
8. Verify offline with a fake engine and then in PIE with one community cell and one individual place,
   two APC visitors, a refreshed place image, semantic coffee-shop recall, and deterministic grid-route
   output.

### Implementation progress — 2026-07-14

- Wake surveys and travel-cell surveys now use exactly four absolute cardinal views instead of the old
  five relative wake views / eight 45-degree cell views. A place becomes survey-complete only when all
  N/S/E/W captures succeed; a name or breadcrumb alone no longer suppresses the missing visual.
- `place_images` stores immutable revisions, four source paths, the composite path, scene description,
  capture attribution, and place identity. Community and owned-place rows carry their current
  `place_image_id`; `agent_visual_history` links each APC to the exact shared revision it encountered.
- Pillow renders a deterministic 2x2 composite with large white N/S/E/W headings on black and no
  coordinate overlay. Shared composites have no sim-run identifier and are exposed under each APC's
  `observations/place_history/` by hard link when available (copy fallback).
- Wake reuses an existing place image and its saved textual description instead of re-surveying. A
  settled APC with a mapped scheduled place suppresses routine changed-pixel VLM work; manual pulses,
  schedule/movement changes, stuck/blocker state, and APC proximity events remain separate cognition
  paths.
- PlaceDB full reset removes place-image rows, shared composites, and APC history links. Agent/day reset
  preserves them. Focused compositor/schema/history/reset/suppression tests were added; full offline
  suite: **44/44 passed**.
- Still required before completion: live PIE proof of real camera composition and wake reuse; cockpit or
  model-facing semantic recall that can fetch a selected historical composite plus place episodes;
  migration/quarantine of existing SR-tagged observations; and the transient gaze retention decision.
- **SR21 map inspection follow-up (user, 2026-07-15):** Dufus live-produced community composites for
  cells `(5,5)`, `(7,5)`, `(7,4)`, and `(8,4)`, but `/map` represented them only by cell fill while
  authored owned places retained distinct purple markers. Add a center marker for every surveyed
  community cell; clicking it must expose the current N/S/E/W composite plus capture metadata without
  confusing it with an owned-place extent. The hover's current “N landmarks” is actually a count of
  confidence-qualified `(direction, VLM label)` rows (for SR21 `(7,5)`: 47 rows, 43 lowercased labels,
  52 sightings), not unique physical landmarks. Rename it to honest visual-observation metrics now and
  report label-row, distinct-label, and total-sighting counts; semantic synonym deduplication remains a
  later visual-cortex improvement. **Classification:** loop-safe API/UI/tests plus focused live map QA.
- **Map follow-up landed 2026-07-15:** `/map` now renders a blue center marker for every community
  cell with a current place image; its dialog serves the N/S/E/W composite plus revision, capturer,
  timestamp, and description. Hover reports visual-observation rows, normalized textual labels, and
  total sightings instead of claiming unique physical landmarks. Verified against the live SR21 DB:
  five markers rendered and Dufus's `(7,5)` 1280×848 composite loaded with no browser errors. Full
  offline suite: **44/44 passed**.
- **Marker cleanup 2026-07-17:** follow-up live inspection confirmed the 10 px blue community markers
  were still oversized and appeared off-center. Their visible footprint is now a centered 3×3 px blue
  square inside a transparent centered 11×11 px click target, so dialog behavior remains usable.
  Focused map-view coverage passes (58 checks); Terra independently ran the full offline suite, 47/47.
- **Grid-heading follow-up landed 2026-07-17:** place-history composites now show
  `GRID X: <col>  Y: <row>` between the N and S labels so the VLM's text response can explicitly state
  which logical grid produced the image. This intentionally supersedes the earlier blanket ban on
  coordinate text while retaining the ban on precise world-coordinate scene overlays. The production
  survey path supplies the place cell's actual col/row, and focused pixel/layout coverage plus the full
  offline suite pass (**47/47**). **Classification:** loop-safe compositor integration + focused image
  regression.

**Acceptance:** a written capture/state model names every image class and owner; an offline fake engine
proves unchanged samples cause neither a new durable file nor a VLM call; repeated identical decision
frames deduplicate under the chosen policy; both a community cell and an individual place receive a
valid N/S/E/W composite with readable white-on-black headings and its logical grid X/Y between N and S,
with no precise world-coordinate overlay; every place
record resolves its current `place_image_id`; APC visits retain the exact historical image revision;
place recall returns description + image + visits + memories; semantic recall of a previously visited
coffee shop resolves its grid and deterministic routing returns a grid array without asking a VLM to
read coordinates from the image; PlaceDB reset removes place-image rows/files, while agent reset does
not; and the same visual-cortex contract runs against a headless adapter and Unreal. Instrument image
writes, cache hits, VLM calls, and trigger reason so #20 can measure cost. **Classification:** design
decision now; then loop-safe Python/storage tests + focused live/PIE capture verification. Existing
bridge primitives appear sufficient; no C++ is assumed.

---

## 33. Configurable logical grid origin aligned to the authored world

**Status:** ✅ **DONE 2026-07-14 — implementation, MCP_World alignment, and live reuse verified** ·
**Source:** user map review: Maren’s place cell/landmark nearly crosses two cells and the grid should
align with streets/buildings · **Depends on:** #18 registered map; invalidates grid-keyed #11/#32 data

This is not another image-registration fix. `image_bounds` correctly maps the captured world image to
world coordinates but intentionally does not affect navigation. `WorldGrid` currently computes
`floor(world_coord / 3000)`; for MCP_World that forces the logical grid origin to approximately
`(-27000,-18000)` cm. The lattice therefore follows arbitrary world-zero multiples rather than the
authored street/building layout, which can put one semantic place or 9 m owned extent across a district
edge even while the overlay is pixel-perfect.

Desired behavior:

- `world_grid.json` can pin an explicit logical `origin_x/origin_y` (or equivalent offset modulo cell
  size), independent of world/image bounds; `locate`, `origin`, `cell_center`, route planning, place
  offsets, SpatialMap keys, web overlays, cursor readout, and generation all use the same transform;
- `/map` provides a preview-first way to adjust the lattice over the registered image and inspect which
  landmarks/owned extents straddle boundaries before applying it;
- applying an offset is treated as a **regrid**, never a cosmetic CSS shift: require confirmation, clear
  all grid-keyed PlaceDB/spatial/route data and #32 place-survey images, then rescan authored landmarks;
- world/grid round trips remain stable for negative UE coordinates and edge cells; image registration
  remains unchanged when only the logical grid offset moves.

Open decision: manual numeric offset, drag-the-grid UI, landmark/street-assisted suggestion, or a blend.
**Recommendation:** direct drag/numeric controls with snap + a preview report, optionally offering a
non-authoritative heuristic; the world author—not an algorithm—chooses which streets/buildings define
good district boundaries. Acceptance: offline transform/round-trip tests, map/API parity tests, a reset
transaction test proving no old `(col,row)` data survives, and PIE visual acceptance that Maren’s chosen
place/landmark grouping lies inside the intended cell. **Classification:** design decision + loop-safe
grid/map/storage work; final alignment is live/editor acceptance.

### Implementation progress — 2026-07-14

- `world_grid.json` now accepts `origin_x`/`origin_y`; WorldGrid locate/origin/cell-center math and
  per-agent SpatialMap use the same offset-aware transform while omitted/zero values preserve the old
  world-zero behavior.
- `/map` now has an **Align grid** panel with numeric 100 cm controls and a non-destructive preview.
  Preview redraws the empty lattice over the registered image and hides old place overlays so stale
  cell keys cannot be mistaken for the proposed layout.
- Applying requires an explicit destructive confirmation and runs through the standalone runner. The
  transaction stops the sim, preserves authored positions/bounds/image calibration, writes the new
  logical origin, and clears PlaceDB cells/images/history links, agent spatial maps, rendered/cached
  routes, and in-progress sweeps tied to the old grid.
- Offset round trips, SpatialMap parity, reset integrity, runner/client transport, confirmation gating,
  and map controls are covered offline. Full suite: **44/44 passed**.
- MCP_World accepted and applied logical origin X `0`, Y `650` cm. SR18–SR21 rebuilt place images and
  exercised cell centers/routes under that lattice. Future origin changes remain deliberate regrids,
  not normal run setup.

---

## 34. Defer community-cell surveys during scheduled travel

**Status:** ✅ **DONE 2026-07-15 — ordinary and survey-priority policies live-observed** · **Source:** SR18 live
review: Dufus began
the correct village-square route, briefly entered an adjacent unsurveyed cell while navigating around
the blue house/car, then the sweep interrupt replaced his route action and sent him backward to that
cell's center · **Depends on:** #11.1 sweep capability and #17 routed travel

The sweep gate currently fires on entry to any unexplored cell even when the schedule directive is
`travel`. A transient boundary crossing can therefore replace the deterministic route action, pull the
APC to an unrelated cell center for a four-view survey, and only resume the route roughly a minute
later. This makes a correct route look like a motel/house detour and lets exploration override the
agent's scheduled destination.

Desired behavior: scheduled travel has priority for ordinary APCs. Entering or clipping an unexplored
cell while en route must not start a survey or replace the routed movement action. An APC explicitly
configured with `survey_priority`, however, deliberately reverses that order: it routes to the exact
center of each encountered unexplored cell, completes N/S/E/W, and only then resumes its unchanged
scheduled destination. Existing in-progress sweeps may finish; wake surveys and non-travel survey
behavior remain unchanged.

Acceptance: an offline regression presents an unexplored current cell with schedule status `travel`
and proves the LLM's routed `walk_to` survives unchanged and no sweep state starts; companion coverage
proves a non-travel tick still starts the survey. A fresh PIE run should show Dufus follow the
village-square route without being pulled to a newly crossed cell center. **Classification:** loop-safe
Python behavior + live/PIE verification.

### Implementation progress — 2026-07-14

- `_act_agent` now gives both scheduled `travel` and `act` directives priority over starting a new
  community-cell survey. Unscheduled/idle survey behavior is unchanged, and the separate active-sweep
  continuation path still finishes a survey already in progress.
- **Policy update 2026-07-15:** the user requested a per-APC surveyor exception. `survey_priority=true`
  now makes surveys outrank `travel`/`act`; Dufus has this setting plus matching surveyor goals. The
  deterministic sweep still owns center arrival and all four cardinal captures before schedule resume.
- Regression coverage proves a named-place routed `walk_to` survives entry into an unexplored cell,
  starts no sweep state, and retains its deterministic waypoint; companion idle and continuation tests
  remain green. Full offline suite: **44/44 passed**.
- **Live evidence:** SR19 showed the ordinary travel gate caused no survey detour; its remaining
  west/north deviation was the separate #27 mixed-control defect. SR21 then live-proved the explicit
  surveyor exception: Dufus completed durable community composites at `(5,5)`, `(7,5)`, `(7,4)`, and
  `(8,4)` before resuming schedule travel.
- **Live follow-up 2026-07-17:** another user-observed run confirmed Dufus recognizes an unsurveyed
  grid cell, interrupts his current activity, and begins its survey. This reinforces the survey-priority
  behavior; the broader village-to-frontier expedition contract remains separate in #35.

---

## 35. LLM-directed survey expeditions from the village

**Status:** **IDEA / DESIGN GATE — requested 2026-07-15** · **Source:** user: “Dufus is the surveyor
and periodically does random unknown cell explorations, then heads back to village… survey the whole
map visually” · **Builds on:** #7/#11.1 sweep capability, #17/#27 routing, #32 place visual memory,
#34 `survey_priority`, #38's generic interruption lifecycle, and #13.4 pristine-run reset

Going straight to the village was the first live step, not the final survey behavior. Dufus should
periodically leave the village on a survey expedition, choose an unknown reachable grid cell, travel
there, center in the cell, capture the complete N/S/E/W visual survey, and return to the village. Over
repeated expeditions, shared visual coverage should be able to reach every reachable grid cell and the
map should make remaining unknown coverage obvious.

The behavior must preserve LLM agency. Do **not** hardcode a global “random walk then return” state
machine or a fixed cell sequence into `AgentManager`. The deterministic layer may expose grounded
facts/capabilities—unknown frontier candidates, reachability, coverage, route progress, survey
completion, and a durable current destination—and must own safe movement execution once the LLM has
chosen an intent. Dufus’s surveyor identity, desire to explore, decision to depart/return, and choice
among reasonable candidate cells should come from his goals/planning prompt and model decision. A
bounded fallback may prevent a lost/stalled expedition, but must be reported as a fact rather than
silently replacing the model’s intent.

Desired acceptance evidence:

- on a pristine #13.4 run, Dufus reaches the village, later chooses an unknown reachable cell from
  map facts, surveys it completely, and returns to the village without a hardcoded route;
- multiple excursions select new unknown cells rather than repeatedly revisiting completed cells;
- coverage reports reachable/visually surveyed/unknown counts and can eventually reach 100% of the
  reachable bounded grid (with unreachable cells reported, not retried forever);
- decision/replay logs show what facts the LLM saw, why it chose the target, the durable intent, and
  deterministic route/survey outcomes;
- ordinary APCs remain unaffected unless given the same explicit surveyor goal/policy.

**Open decisions for next session:** what event/cadence invites an expedition; whether the model sees
all unknown cells, a small frontier shortlist, or a tool query; how “random” is expressed without
making selection deterministic infrastructure policy; expedition retry/timeout bounds; whether every
trip must return to the village or the LLM may chain nearby surveys; and the #13.4 purge/retention
boundary. **Classification:** design decision, then loop-safe planner/context tests plus live/PIE
whole-map coverage verification.

---

## 36. Ordered primary and secondary goals per APC

**Status:** **IMPLEMENTATION + OFFLINE TESTS COMPLETE 2026-07-22 — 51/51; LIVE VERIFY PARTIAL** · **Source:** user: “Dufus and other APCs
to have multiple goals, primary and secondary etc. So when a goal is met, start running the next
goal.” · **Builds on:** #10 planner/sequencer, #31 event-driven cognition, #35's durable survey
intent, and the generic interruption lifecycle in #38

Each APC should have an authored or model-visible ordered portfolio of goals rather than one effective
goal. One goal is active, lower-priority goals remain available, and satisfying the active goal advances
the APC to the next eligible goal without a manual state edit. Goal priority, active state, completion
evidence, and transition history must be inspectable; completing one action or arriving at one waypoint
must not silently count as completing a larger goal.

Desired acceptance evidence: Dufus completes a primary goal, records why it is complete, activates his
secondary goal, and begins pursuing it on the next appropriate cognition event; an interruption pauses
and later resumes the same active goal unless an explicit reprioritization occurs; each APC advances its
own list independently; blocked, abandoned, and completed goals remain distinguishable in state and
logs. Open decisions: whether ordering is strictly primary/secondary or numeric priority, who may declare
completion (LLM, deterministic facts, user, or a combination), how recurring and blocked goals behave,
and how goals interact with daily schedules and direct user directions from #37. **Classification:**
design decision, then loop-safe goal-state/sequencer tests plus live/PIE behavior verification.

**New evidence 2026-07-21:** SR27 deterministically resolved `survey:6,6` with outcome `survey completed`,
but Dufus retained “I need to survey this cell thoroughly” as his current goal and immediately resumed
narrating more survey work. When a deterministic completion corresponds to the active goal, #36 must
consume that evidence exactly once and visibly clear or advance the goal; it must not infer completion
from free-form model narration.

**Additional live evidence 2026-07-21 (SR28):** Dufus immediately pursued the authored “go home and
find my hat” goal, reached his motel-room home, returned to his starting area for a deterministic survey,
went home again, and after the interruption resolved headed back toward the village. His persisted goal,
daily schedule destination, suspended route, and survey interruption each behaved plausibly in isolation,
but their arbitration produced visible backtracking. The #36 design must define which intent wins after
arrival and interruption resolution, preserve the exact suspended intent, and prevent schedule/goal
oscillation unless a logged goal transition or new fact justifies it. Acceptance evidence must include
this home → survey → resume scenario with no unexplained return to a superseded destination.

**Design locked 2026-07-21:** use an editable JSON agenda with deterministic execution state, not a
general-purpose behavior tree. Authored tasks use this minimum schema:

```json
{
  "tasks": [
    {
      "id": "morning_square",
      "start": "08:30",
      "end": "09:00",
      "place": "village square",
      "objective": "Travel to the village square",
      "completion": {"type": "arrive_at_place"}
    }
  ]
}
```

Keep authored agenda data separate from runtime execution. Runtime tracks each task as `pending`,
`active`, `interrupted`, `completed`, or `blocked`, with timestamps and grounded completion evidence.
Supported first-slice completion policies are `arrive_at_place`, `time_block_ends`, and
`time_or_llm_confirmed`; implementation must validate unknown policy names rather than silently guessing.
Unknown/stale community-cell surveys and direct chat are interruptions: they suspend the exact active
task and resume it afterward unless an explicit, logged reprioritization changes the agenda.

Existing `episodes.jsonl` remains episodic memory, but it is not the authoritative daily ledger: prompt
retrieval is relevance-based and `last_activity` stores only one string. Build a compact chronological
daily ledger from task transitions and interruption outcomes, then provide the decision LLM these three
grounded sections on every applicable cognition event:

- **Today so far:** completed/blocked work and serviced interruptions, with time ranges and evidence;
- **Right now:** the one active task, current place/destination, arrival verdict, and grounded route;
- **Next:** the next eligible unfinished task and the deterministic condition that activates it.

The deterministic executive selects/advances/resumes the task; the LLM chooses the in-character actions
used to carry out its objective. When Dufus arrives in `village square`, `arrive_at_place` completes the
travel task and the next eligible square activity becomes active, instead of asking the model to invent
a new goal. Other than bounded unknown/stale cell interruptions, Dufus follows his agenda until all
eligible tasks are done; only then does free goal-driven behavior become the default.

Acceptance evidence: schema validation and migration/fallback tests; deterministic transitions for
arrival, time expiry, LLM-confirmed completion, blocked work, and day rollover; Today so far / Right now /
Next prompt snapshots derived from runtime facts; survey and chat interrupt/resume tests preserving the
same task; no duplicate completion; and a live run in which Dufus completes morning work, services a
survey, reaches the named village square, advances to its next activity, and does not backtrack to a
completed destination. **Classification:** loop-safe data/sequencer/prompt work plus live/PIE behavior
verification.

**Implementation and verification evidence 2026-07-22:** authored data now lives in validated, atomically written
per-APC `agenda.json` files using schema version 1; deterministic execution and the chronological ledger
remain separate in ignored `runtime.json`. Dufus and Maren have tracked authored agendas, while APCs
without one retain a generated-schedule compatibility fallback. Runtime transitions cover pending,
active, interrupted, completed, and blocked work; arrival and time policies use deterministic facts;
`time_or_llm_confirmed` accepts only the exact active task, at its required place, after a successful
world action, with a bounded explicit evidence statement. Decision prompts receive authoritative Today
so far / Right now / Next sections, route/arrival facts, and interruption state. Agent inspection exposes
authored data, validation errors, execution state, and ledger context. Sol authored schema, persistence,
transition, interruption, prompt, manager-boundary, state, navigation, and real-agenda tests; Terra ran
the complete offline suite with **51/51 passing**. In the user's live run, Dufus completed
`morning_home`, traveled to the square with grounded arrival, and activated `square_morning` without
runtime agenda errors. That run exposed stale legacy `current_goal` text after the task transition; the
executive now synchronizes it to the active agenda objective. Restarted-process live verification of
that fix and an interruption/resume cycle remain required.

---

## 37. Direct operator chat and direction for a selected APC

**Status:** **OFFLINE COMPLETE 2026-07-21 — 50/50; LIVE PIE/MODEL VERIFY NEXT** · **Source:** user: “I want to have a
feature where I can ‘chat’ with a particular APC… interrupt [its] current goal… and give direction
to the APC.” · **Builds on:** #10.5 interrupt/resume policy, #12 interaction memory, #31 event-driven
cognition, #36 multi-goal state, and the generic interruption lifecycle in #38

Provide a user-facing control that selects one APC and opens a direct conversation with it. A new
message is a deliberate cognition event: the selected APC safely pauses its current activity/goal,
receives the user's words in character and with its relevant memory/context, and can accept grounded
direction. Other APCs continue unaffected. The paused goal and movement intent must remain explicit so
chat does not accidentally erase work or leave an invisible route running underneath the conversation.

Desired acceptance evidence: the user selects Dufus, sends and receives multiple chat turns, gives a
direction, and sees whether Dufus accepted, questioned, or declined it; his prior goal is visibly paused;
ending chat either resumes it or applies the new direction according to an explicit choice; the exchange
and resulting goal transition are auditable and available to appropriate memory. Open decisions: where
chat lives (cockpit, map, or both), whether movement freezes during the session, whether a direction is
a temporary interrupt or may insert/reprioritize #36 goals, how the user ends/releases the conversation,
and which transcript details persist. **Implemented MVP:** Simulation-cockpit selector and explicit
operator identity; open chat freezes the selected APC; multiple turns persist in the interruption;
“Guide with this” converts chat into temporary prompt-grounded direction; “Resume prior work” resolves
it without changing the prior goal/schedule/route. Permanent goal promotion remains #36 and permanent
transcript memory remains #12.2. See `plan/specs/WP10-direct-apc-chat.md`. **Classification:** offline
UI/control/state complete; live/PIE conversation, physical stop/guidance, and unaffected-peer verify pending.

**Approved UI follow-up 2026-07-21:** move all direct-chat cockpit controls to their own `/chat` page.
Place **Chat** immediately next to **Sim** in the primary navigation, remove the chat panel from `/sim`
rather than duplicating it, and preserve APC selection, operator identity, transcript, send, guide, and
resume behavior. Acceptance evidence: offline route/template tests prove `/chat` contains the complete
chat surface, `/sim` no longer contains it, navigation order is Sim then Chat, and existing API/control
tests remain green. **Classification:** loop-safe web UI; live/PIE chat verification remains required.

**Implementation evidence 2026-07-21:** `/chat` now owns APC selection, operator identity, transcript,
send, guide, and resume controls; `/sim` retains simulation status, survey progress, controls, and the
decision feed without chat duplication; shared navigation is Sim → Chat → Map. Focused web tests and
the full offline suite passed (50/50). Live chat behavior still requires PIE/model verification.

---

## 38. Generic APC interruption, resolution, and resume lifecycle

**Status:** **✅ OFFLINE COMPLETE 2026-07-17 — 49/49; live role-play remains #37** · **Source:** user: “APCs need a generic
interruption ability. Dufus has a ‘I need to survey this unknown cell’; Maren may have a ‘Root user
wants to talk to me’… This way, I can role play with the APCs and fine tune their behaviors.” ·
**Unifies:** #10.5 reaction gating, #11.1/#34 survey interruption, #31 cognition wake events, #36 goal
progression, and #37 direct operator chat

Create one engine-neutral interruption lifecycle rather than adding a separate override path for every
feature. An interruption identifies its source/requester, reason, relevant grounded facts, urgency or
priority, and what work should be resumed afterward. It can be queued/presented, accepted, deferred or
declined when agency allows, activated, resolved, and then either resume the suspended activity/goal or
explicitly convert into a new/reprioritized goal. The paused movement ticket, schedule directive, and
active #36 goal must remain inspectable throughout; an interrupt may not silently discard or continue
them underneath the new activity.

The same lifecycle should express at least these first cases:

- Dufus receives an internal/world opportunity: an unknown grid cell needs a survey.
- Maren receives a social/operator request: the world user's configured persona wants to talk with her.

The operator identity must come from world/user configuration or an explicit role-play identity, not be
hardcoded as “Root.” Conversation and accepted directions should reach the APC as in-world context so
the user can role-play and refine behavior, with an explicit policy for whether those directions are
temporary, remembered, or promoted into #36 goals.

Acceptance evidence: an APC with an active goal can service a survey interruption and resume the exact
suspended work; a selected APC receives a named-user chat interruption through the same lifecycle while
other APCs continue; simultaneous interrupts are ordered visibly; deferred/declined/expired interrupts
do not vanish; resolution and resume/goal-transition outcomes appear in state and decision logs. Open
decisions: priority and preemption rules, interrupt stacking versus a single active interrupt, optional
versus mandatory events, expiry/retry behavior, persistence across restarts, the player's in-world
identity model, and how lasting behavioral directions differ from ordinary conversation. **Classification:**
design decision, then loop-safe interruption/state-machine tests plus live/PIE survey and role-play
verification.

### Implementation progress — 2026-07-17

- Locked and built one durable `active_interrupt` plus a priority/FIFO queue in APC `runtime.json`.
  Safety/system defaults to priority 300, explicit operator/user work to 200, and surveys to 100;
  higher-priority work only preempts an active record while it is marked preemptible.
- Migrated Dufus's deterministic unknown-cell survey into the generic lifecycle. Its target cell
  persists, restart recovery reconstructs manager-local sweep state, the first deterministic step
  closes the preemption window, and terminal outcomes return control to the unchanged schedule/goal.
- Added generic request/resolve manager methods and localhost runner/client routes with an explicit
  requester identity. Active operator work wakes settled cognition and appears as a grounded prompt
  fact above routine activity; no `Root` identity is hardcoded.
- List/inspect surfaces now expose active, queued, and last-terminal interruption state. Lifecycle
  transitions append compact, sim-run-attributed entries to the existing decision feed.
- Reset day/agents clears interruption runtime; regrid cancels survey interruptions without discarding
  unrelated future kinds. Malformed persisted records fail closed.
- Test-first implementation landed in `a4937ad`, `52cee1b`, `f77616f`, `18056e0`, and `485a00c`;
  the last commit makes the promised pre-dispatch survey preemption window externally reachable and
  corrects preemption audit attribution. Terra's final delegated full offline run passed **49/49**.
  No Unreal/PIE or paid-model call was made.
- #38 deliberately stops at the generic control surface. Multi-turn chat/transcripts and accepted
  direction semantics remain #37; ordered/reprioritized goals remain #36.

---

## 39. Refresh stale community-cell surveys

**Status:** **OFFLINE + LIVE VERIFIED 2026-07-21 (SR28)** · **Source:** user after SR27: “cockpit
says cells that have place cell in center but text says needs reobservation” · **Builds on:** #7 survey
mechanics, #32 place-image lifecycle, and #38 survey interruptions

A saved center composite and a stale outline describe different facts: the composite exists, while the
cell has not been updated in over 24 real hours. The cockpit currently labels that state “needs
re-observation,” but `_should_sweep_here` rejects every cell that already has a current place image, so
no automatic path can perform the advertised refresh.

Desired behavior: an otherwise eligible APC visit may offer one deterministic survey interruption for
a stale community cell even when a prior composite exists; a fresh composite still suppresses redundant
surveys; completing the refresh replaces/advances the current place image and updates the cell timestamp
so it is no longer stale. Queueing and duplicate suppression must continue to use #38.

Acceptance evidence: offline tests establish fresh-existing → no sweep, stale-existing → one survey,
active/queued duplicate → no second survey, and completed refresh → fresh cell with a current composite.
Do not call vision or PIE in the offline test. Live verification should confirm one red cell refreshes
without sending an APC on repeated surveys. **Classification:** loop-safe runtime/database behavior plus
live/PIE verification.

**Implementation evidence 2026-07-21:** survey eligibility now requires a present, non-stale community
composite. A stale existing image proceeds through #38, creates the next immutable visual revision, and
becomes fresh when the capture is recorded; a fresh image still suppresses the survey. Focused
`test_cell_sweep.py` and the full offline suite passed (50/50). Live verification should confirm one red
cell refreshes once without repeat surveying.

**Live evidence 2026-07-21 (SR28):** Dufus refreshed stale cells `(5,5)`, `(6,5)`, and `(7,5)` exactly
once, producing revision-2 place-history composites and leaving the map at zero stale cells. Mark the
stale-refresh behavior live-verified; retain broader expedition/goal behavior under #35/#36.

---

## 40. Ground and expose deterministic survey progress

**Status:** **TELEMETRY LIVE-VERIFIED 2026-07-21 (SR28); VISIBLE YAW + NARRATION FIX PENDING** · **Source:** user after SR27: “Dufus says
he needs to survey cells, but I do not see him rotating.”

SR27 did execute distinct E/S/W/N captures and resolve `survey:6,6`, but each facing change is an
instant teleport rotation, individual heading steps are absent from the decision feed/cockpit, and the
ordinary LLM loop claimed views were saved both before and after the real deterministic sweep. Operators
therefore cannot distinguish actual survey work from invented narration.

Desired behavior: publish the active survey cell, phase, current heading, completed headings, and capture
result through inspect/API state and compact sim-attributed decision events; show that progress on the
web surface; ground cognition with that authoritative state and prohibit claims that an uncaptured
heading was saved. Completion clears transient progress. This item does not require a turn animation;
PIE must still verify that the actor's yaw changes for each real heading.

Acceptance evidence: offline tests observe ordered E/S/W/N progress, one event per attempted heading,
accurate success/failure sets, prompt facts derived only from deterministic state, no stale progress after
resolution/restart, and rendering of active heading/progress. Live verification confirms visible yaw
changes and matching captures. **Classification:** loop-safe runtime/log/API/web work plus live/PIE
verification.

**Implementation evidence 2026-07-21:** the persisted survey interruption now owns phase, current
heading, successful headings, failed headings, and the last result. Agent inspection/status and the Sim
cockpit expose it; each attempt emits a sim-run-attributed `survey_heading` event; restart recovery skips
already attempted headings; and prompts explicitly distinguish deterministic saved views from model
narration. Focused sweep/feed/prompt/web tests and the full offline suite passed (50/50). PIE must still
confirm visible yaw changes align with the E/S/W/N capture files.

**Live evidence and remaining defect 2026-07-21 (SR28):** all three surveys emitted successful ordered
E/S/W/N heading events and distinct capture files with no failed headings, confirming that deterministic
survey progress is live. After `(7,5)` resolved, however, ordinary cognition again narrated that headings
still needed surveying and claimed views had been saved even though no `survey_heading` action occurred.
The data layer correctly rejected redundant work, but prompt-only grounding was insufficient. Desired
behavior now includes a compact authoritative current-cell survey fact (fresh/active/completed headings)
and deterministic validation or suppression of unsupported “saved/surveyed” claims. Acceptance evidence:
after a completed survey, subsequent ordinary decisions neither claim missing headings nor claim a saved
capture without a matching deterministic event. **Classification:** loop-safe cognition/action-policy
work plus live/PIE model verification.

**Implementation evidence 2026-07-24:** every decide tick now attaches `observation["cell_survey"]` — the
deterministic fresh/due/active verdict for the cell underfoot, read from `current_place_image` + staleness
rather than from any interruption — and both prompt templates render it as a **Survey State Of The Cell
You Are Standing In** section that forbids both inventions explicitly. Prompt grounding alone was
insufficient in SR28, so `cell_sweep.filter_survey_claims` additionally drops, in code, any narration
sentence claiming a saved capture when no `survey_heading` ran that tick or claiming the cell still needs
surveying when its survey is current; dropped claims are logged as warnings rather than silently smoothed.
Unrelated uses of "saved" pass through untouched. Offline coverage: `test_survey_grounding.py` (the exact
SR28 string, supported claims surviving, ordinary narration untouched, empty/non-string/all-dropped edge
cases, and all four prompt verdicts). Full suite **54/54**. **Still owed:** the PIE visible-yaw check, and
a live model run confirming post-survey decisions stop inventing headings.

---

## 41. Make map survey counts and stale wording truthful

**Status:** **OFFLINE + LIVE VERIFIED 2026-07-21 (SR28)** · **Source:** SR27 cockpit review

The map assigns one exclusive display state: a named cell is `named` even when it also has `swept_at`
and a saved composite. This produced `named 8, swept 0` while multiple blue center markers proved survey
history existed. The stale tooltip simultaneously promises “needs re-observation” although the current
scheduler cannot refresh such cells.

Desired behavior: expose and count independent facts—named, has completed survey/composite, stale, and
owned—rather than treating named and swept as mutually exclusive. Until #39 is active, stale copy must
describe age without promising an unavailable action; after #39 lands it may explicitly say the cell is
eligible for refresh. Preserve the existing visual distinctions and center-marker click target.

Acceptance evidence: offline map/API/template tests cover a named surveyed cell contributing to both
counts, an unnamed surveyed cell, a stale surveyed cell with its blue marker intact, and wording that
matches refresh capability. **Classification:** loop-safe database/web UI work.

**Implementation evidence 2026-07-21:** `map_cells` now exposes independent `named`, `swept`, and
`surveyed` booleans. The API counts named, surveyed, mapped, stale, and owned without overlap errors;
the legend counts blue-marker community surveys rather than unnamed-only sweep state; and stale copy
states that an older saved survey is eligible for refresh under #39. Focused map tests and the full
offline suite passed (50/50).

**Live evidence 2026-07-21 (SR28):** after the three refreshes, the database/map facts reported 8 named,
6 surveyed, and 0 stale cells. The independent survey/stale accounting is live-verified.

---

## 42. Preserve actionable bridge/action error details in the decision feed

**Status:** **INVESTIGATION / BACKLOGGED 2026-07-21** · **Source:** SR28 log review

SR28 recorded one Dufus `speak_to` action as an error after roughly 15 seconds, then recovered on the
next attempt. The decision feed retained the action and error status but not the underlying bridge/error
detail, so the cause cannot be distinguished among timeout, target resolution, transport, or another
runtime failure.

Desired behavior: failed actions retain a bounded, safe diagnostic code/message and elapsed phase in the
sim-run-attributed decision event, without exposing secrets or unbounded provider output. Acceptance
evidence: an induced bridge/action failure can be traced from the decision feed to a specific failure
category, while successful events remain compact and existing recovery behavior is unchanged.
**Classification:** loop-safe logging/tests, with live/PIE verification for a real bridge failure.

**Implementation evidence 2026-07-24:** `memory_store.classify_action_error` maps a failed result to one
of `not_connected` / `timeout` / `target_unresolved` / `transport` / `runtime`, with the message whitespace-
collapsed, key-redacted, and capped at 240 characters, plus the elapsed act phase. `MemoryStore.record`
attaches it as `error` only when the action failed — successful entries keep exactly their previous keys —
and the console log line carries the category too. The Sim feed renders `⚠ <code>: <message> after <n>ms`.
An accepted-with-note recovery is deliberately not treated as a failure, so existing recovery behavior is
unchanged. SR28's case now reads as `timeout` at ~15021 ms instead of a bare error status. Offline
coverage: `test_action_errors.py` (every category, non-failures including accepted-with-note, message cap,
key redaction, and a feed entry that stays compact on success). Full suite **54/54**. **Still owed:**
live/PIE verification against a real induced bridge failure.

---

## 43. Make APC profiles discoverable and edit the JSON agenda

**Status:** **APPROVED 2026-07-21; NAV ENTRY IMPLEMENTED 2026-07-22; DRILL-DOWN/EDITOR PENDING** · **Source:** user: “I don't see the APC
profile page anywhere, did we lose that? I thought we had a way to set goals and etc on APCs in the
webUI?” · **Depends on:** #36 authored/runtime agenda contract

The APC editor still exists at `/worlds/{level}/agents/{agent_id}` and currently edits identity,
behavior settings, `current_goal`, `character.md`, `goals.md`, `rules.md`, and allowed actions. It appears
lost because the primary navigation has no clearly labeled APC/Worlds entry; users must click the
`Unreal World Sim` brand to return to the world list and then click an agent's `Edit` button. The page
also cannot edit the generated daily schedule or show structured task completion state.

Desired behavior: add an obvious **APCs** primary-navigation destination; keep the per-world agent list
and existing editor reachable from it; add a validated editor for #36's authored JSON agenda; and add a
read-only live panel showing **Today so far**, **Right now**, and **Next**, including active task state,
completion evidence, and any suspended interruption. Preserve the existing character/goals/rules/action
editing rather than replacing it.

**Cockpit drill-down requirement added 2026-07-22:** the user found raw endpoint JSON too painful to
read and requested “a way to see these JSON files in the cockpit in a nice drill down way, not just raw
web view file dump.” The cockpit/APC profile should render authored agenda tasks, runtime task states,
ledger events, completion evidence, interruptions, and other useful per-APC JSON as labeled summaries
with expandable nested details. Users should be able to collapse noise, distinguish authored data from
runtime facts at a glance, and navigate directly from the APC list. A raw JSON view may remain for
diagnostics but must be secondary/advanced, not the primary experience.

Acceptance evidence: navigation/template tests prove APCs are reachable without knowing a URL; Dufus's
profile round-trips a valid agenda without overwriting unrelated authored files; invalid JSON/schema is
rejected with actionable inline errors and no partial write; the runtime panel distinguishes authored
agenda from execution state; and live verification shows task transitions without a page restart.
The drill-down acceptance additionally requires nested objects/arrays to expand and collapse without
losing labels, task statuses and completion evidence to be readable without inspecting JSON syntax,
and malformed or unavailable runtime data to render a bounded error state rather than a file dump.
**Classification:** loop-safe web/storage tests plus live web/PIE verification. ~~**Open implementation
choice:** structured task-row editor and dedicated state components versus a reusable recursive JSON
viewer; retain a raw/advanced view either way.~~ **Resolved 2026-07-24 (Claude's call, user delegated —
open to veto): both.** Dedicated components own the shapes we know; a generic recursive renderer handles
nested/unknown data beneath them; raw JSON is a collapsed advanced view.

**Implementation evidence 2026-07-24:** `web_ui/static/apc_drilldown.js` provides the recursive renderer
(depth- and item-capped, `textContent` only so authored files cannot inject markup) plus dedicated Right
now / Next / Agenda tasks / Today so far / Survey / Other-state components. The APC profile page gained a
**live task state** panel polling `/api/sim/agents/{id}` every 3 s — task transitions appear without a page
reload — and an **Agenda** editor posting to a new `POST /worlds/{level}/agents/{id}/agenda` route that is
deliberately separate from `update_agent`, so saving an agenda cannot rewrite character/goals/rules.
`validate_agenda_text` mirrors `Agent.load`'s wording, and rejection re-renders the submitted text with
inline errors while leaving `agenda.json` untouched (verified: malformed JSON and a bad
`completion.type` both left the file byte-identical; a valid document round-tripped). A down runner or a
malformed payload renders a bounded message, never a file dump. Offline coverage:
`test_apc_agenda_ui.py` (editor + live panel + renderer present, reachable from the index, malformed JSON
and schema violations both rejected inline with the file byte-identical, valid round-trip, other authored
files untouched, starter template valid, bounded runner-down envelope). Full suite **54/54**. **Still
owed:** live verification in a browser against a running sim.

---

## 44. Resolve APC identity from engine facts, not from vision

**Status:** **DIAGNOSED 2026-07-24, NOT STARTED** · **Source:** Claude code/data audit ·
**Blocks:** #5 social memory, #12.1 don't-re-greet, #10.5 friend-interrupt, #12.2 interaction memory

Evidence: `last_perception.json` shows every character sighting labeled `unknown person`, while the same
tick's `observation["nearby_characters"]` carries the exact engine truth (`{"name": "Maren",
"distance_cm": ...}`). `SocialMemory` deliberately drops anonymous labels, so **no `social.json` has ever
been created for any APC**, `episodes.jsonl` records `saw: []` on every event, and `memory.json` fills
with interchangeable "Met someone new" entries. The identity exists and is discarded one layer earlier.

Desired behavior: identity resolution is deterministic and belongs to the lizard brain — when another APC
is within a plausible sighting range and inside the forward view (positions + yaw are already known),
that sighting is recorded under its `display_name`. Vision keeps describing appearance; it never decides
who someone is. The LLM still receives only semantic labels, never engine actor names.

Acceptance evidence: two APCs in view of each other produce `social.json` entries naming each other;
`episodes.jsonl` records non-empty `saw`; "People You Know" is non-empty on the next encounter; an APC out
of view or out of range is not recorded. **Classification:** loop-safe geometry/memory work plus live
verification that Dufus and Maren recognize each other.

**IMPLEMENTED 2026-07-24.** New pure module `agent_runtime/recognition.py`: `visible_characters` resolves
who is inside the forward view from position + yaw (2500 cm range, 110 degree FOV, left/center/right and
near/mid/far buckets), and `merge_identities` folds them into the vision character list — an identified APC
replaces at most one anonymous blob in the same bearing bucket, so Maren is not double-counted, while
genuine non-APC bystanders survive. `AgentManager._identify_visible_apcs` runs every tick *before*
`_record_sightings`, deliberately outside the `image_path` guard: recognition is geometry and needs no
frame. Someone behind the agent is skipped — proximity is not sighting. Offline coverage in
`test_recognition.py`, including the payoff assertion that social memory now populates and `meet_count`
accumulates across sightings. Suite **55/55**. **Still owed:** live confirmation that `social.json` appears
for both APCs and that "People You Know" is non-empty on a second encounter.

---

## 45. Deliver speech to the APCs who can hear it

**Status:** **DIAGNOSED 2026-07-24, NOT STARTED** · **Source:** Claude code/data audit ·
**Blocks:** #10.5 reaction gate, #12.2 interaction memory, #46

Evidence: `speak_to` sends the line to the engine and nothing else. There is no `heard`/`spoken_to`
concept anywhere in `agent_runtime/`. The decision prompt names exactly two things that may interrupt a
routine — seeing a known person, and *being spoken to* — and **neither is reachable**: the first is
blocked by #44, the second because speech is never delivered to another agent's observation. Both social
affordances in the reaction gate are currently dead code.

Desired behavior: an utterance becomes a fact for every APC within hearing range, surfaced in the next
decision as who said what, so responding is a grounded choice rather than an invention. Bounded: recent
utterances only, capped count, no replay of an entire conversation history.

**IMPLEMENTED 2026-07-24.** `speak_to` now publishes through `_record_utterance` into a bounded 20-entry
buffer carrying speaker display name, text (capped at 400 chars), world time, and position;
`_attach_heard_speech` delivers to any APC within `_HEARING_CM` (1200 cm — wider than the 300 cm standoff
so a greeting reaches someone approaching, narrower than sighting range so nobody overhears across the
district). A monotonic id plus a per-agent consumed marker means a line is heard exactly once and never
re-surfaces a tick later from across the square; an APC never hears itself. The prompt gained a **What You
Just Heard** section in both the vision and text-only (OpenAI) templates, which states plainly that nobody
spoke when the list is empty — otherwise the model is free to imagine a conversation. Offline coverage in
`test_recognition.py`, including manager-level delivery, the heard-once guarantee, self-exclusion, and the
distance gate. Suite **55/55**. **Still owed:** live confirmation that Dufus answers something Maren
actually said.

Acceptance evidence: Maren speaking near Dufus puts an attributed utterance in Dufus's next observation
and prompt; an APC out of range hears nothing; the reaction gate's "someone is speaking to you" clause can
actually fire. **Classification:** loop-safe runtime/prompt work plus live verification.

---

## 46. Multi-turn APC-to-APC conversation with retained content

**Status:** **PROPOSED 2026-07-24** · **Depends on:** #44, #45 · **Relates to:** #12.2

Once APCs can recognize and hear each other, a greeting should be able to become an exchange: turn-taking
between two APCs over several ticks, with what was actually said retained and recallable later ("last time
I saw Maren she was heading to her truck"). Today `_record_interactions` logs that *an* interaction
happened, with neutral sentiment and no content.

Open design choices before implementation: whether a conversation is a first-class interruption (reusing
#38's machinery) or a lighter per-tick state; how many turns before it must yield to the agenda; and
whether content lands in the episodic log or the dedicated store #12.2 has been waiting on.
**Classification:** design decision, then loop-safe implementation.

---

## 47. Reflection — synthesize observations into higher-level insights

**Status:** **PROPOSED 2026-07-24** · **Source:** Claude code/data audit ·
**Relates to:** the Stanford Generative Agents north star

Evidence: `EpisodicLog.consolidate()` compacts old events into count/place *summary rows*; nothing ever
produces an insight. `memory.json` is a flat list of same-shaped observations, so an APC never concludes
anything from its own history. Reflection is the mechanism in the reference architecture that turns a
memory stream into apparent understanding, and it is the one major component this sim has no analogue for.

Desired behavior: periodically (importance-triggered, not every tick — cost matters), an APC asks what its
recent memories imply, and stores a small number of durable higher-level statements that then feed recall
alongside raw episodes. Reflections must be attributable to the observations that produced them.

Open choices: trigger (accumulated importance vs. daily), how many insights to keep, and whether they
influence the agenda or only cognition. **Classification:** design decision, then loop-safe implementation
with one model call per reflection.

---

## 48. Separate character from engine chores in authored goals

**Status:** **DONE 2026-07-24** · **Source:** Claude code/data audit

Dufus's `goals.md` opened with "Be the village surveyor. In every cell that has not been visually surveyed,
go to the exact center and complete the full north, south, east, and west survey…" — survey *mechanism*
authored into *character*. It was presumably added to force surveying before the deterministic survey
interruption existed; that machinery now exists (#38/#39/#40), so the instruction competed with it and
crowded out the personality that makes Dufus legible as a person.

**Resolved:** the mechanism clause is cut and the authored content is re-pointed at what the user actually
wants Dufus to be — a forward explorer who ranges outward, captures what he sees, and gravitates back to
the village square to report. `goals.md` is motivation-only (see somewhere new, bring it home, never walk
back over covered ground, square is home base); `agenda.json` replaces the home/square/market loop with two
long open-destination expedition blocks (`place: ""`, `time_block_ends`) bracketed by `arrive_at_place`
returns to the square; `character.md` Role gains "accidental explorer".

**Code change — capture in place, no backtracking.** The doubling-back the user objected to is the sweep's
`goto_center` leg (`cell_sweep.py:119-124`): the APC walks back to the cell center before the N/S/E/W
capture. `_sweep_step` now passes `arrive_tolerance=world_grid.cell_size` for a `survey_priority` APC, so
"arrived" is already true anywhere inside the cell (max half-diagonal ≈0.71 cells) and the walk leg never
emits. Ordinary APCs keep walk-to-center. Covered by
`test_cell_sweep.test_explorer_surveys_in_place_without_backtracking` (verified failing without the fix).

**Constraint found while doing this:** `PlaceDB.record_place_image` *requires* all four cardinal views and
raises `ValueError` otherwise (`place_db.py:784-787`), and the community place image is the only shared
visual store — so "other APCs can use his knowledge" structurally depends on the four-heading capture.
Hence the fix drops the walk, not the survey. Removing the survey entirely (e.g. `survey_priority: false`)
would make Dufus explore without contributing anything other APCs can read.

Follow-on effects: the old absolute-priority clause no longer outranks the social reactions #44/#45 just
unblocked, #40's `filter_survey_claims` is no longer fed narration it must drop as warnings, and the goal
slots carry Dufus's actual hooks again. **Live check still owed:** confirm on a real run that he ranges
outward instead of orbiting the square, and that off-center captures still yield usable composites.

---

## 49. Record capture pose on place images (VLM training metadata)

**Status:** **OPEN 2026-07-24** · **Source:** raised by #48's capture-in-place change

Context the user supplied 2026-07-24: the survey behavior exists substantially to build a **custom VLM**,
and **Dufus is the training-data source** — he is the world-scanning APC, now expressed as an ordinary APC
carrying the survey attribute rather than a dedicated role (see the #7/#11.1 retirement).

`place_images` (`place_db.py:81-96`) records `col`, `row`, the four view paths, `description`,
`captured_by`, `captured_at`. It does **not** record camera x/y/z or per-view yaw, despite the schema
comment claiming "precise world coordinates remain metadata" — there is no such column. Camera pose is
therefore only inferable as "somewhere in cell (col,row)".

That was a tight bound while every capture happened at the cell center (±100 cm tolerance). #48's
capture-in-place change loosens it to anywhere inside a 30 m cell — up to ~21 m from center — so the same
`col,row` label now covers a much wider range of true camera poses. Fine for the in-sim lookup ("what does
this cell look like"); lossy for a training corpus where pose is a natural label.

Proposed: add `capture_x`, `capture_y`, `capture_z` to `place_images` (migration in `PlaceDB.__init__`,
same pattern as the existing `swept_at`/`swept_by` migration) and persist the per-view yaw alongside each
cardinal path. `_save_place_visual` already has the observation in hand at capture time.

**Classification:** loop-safe (schema migration + offline test); needs the user's go-ahead because it is
dataset design, not a bug. Alternative if pose is not wanted in the corpus: revert #48 to center capture
and accept the backtracking — explicitly rejected by the user on 2026-07-24.

---

## 50. Experiment: APC cognition on Sonnet 5 instead of Haiku 4.5

**Status:** **RUNNING 2026-07-24** · **Source:** user call — "see if switching from Haiku to Sonnet solves a lot of the problems"

Every APC ran its decision role on Haiku 4.5 (both Dufus and Maren are `tier: 2`, and the tier-2 default was
`claude-haiku-4-5-20251001`). Hypothesis: a chunk of what reads as puppet-like behaviour is model capability,
not missing machinery.

Changed in `llm_router._resolve_model`: both tiers now return `claude-sonnet-5`. Tiers are deliberately
collapsed so the live run is a clean A/B — model is the only variable. `_anthropic_call` `max_tokens` went
512 → 1024, because Sonnet 5 tokenizes ~30% heavier than Haiku and a truncated decision JSON costs a whole
tick. **Vision is untouched** — `perception.py` resolves the VLM independently and stays on Haiku 4.5.

Cost: roughly 3× per token vs Haiku ($3/$15 per MTok, intro $2/$10 through 2026-08-31, vs $1/$5).

Not yet evaluated — needs the live run. **To revert:** restore the two-tier map in `_resolve_model`.
Opus 5 is the next rung but needs `_anthropic_call` made thinking-safe first (thinking is on by default
there; `content[0]` becomes a thinking block and `max_tokens` would cap thinking + answer together).

---

## 51. Durable runner log — stop losing the only record of what a run did

**Status:** **OPEN 2026-07-24** · **Source:** Claude, blocked while diagnosing SR30 · **Blocks:** every
live-run diagnosis, including #50's evaluation

SR30 (2026-07-24, ~4½ min) could not be diagnosed after the fact. From disk it looked as if the agents had
stopped thinking: Dufus wrote **23 observation captures but zero decisions**, Maren wrote 6 captures and a
single decision, then both went quiet. Nothing on disk said why, because:

- `agent_decisions.log` records **completed decisions only**. Every skip, exclusion, and exception is
  invisible to it by design — an agent that never decides leaves no trace at all.
- `sim_runner` logs everything else to **stdout only** (`logging.basicConfig` with the default stream
  handler, `sim_runner.py:47`). No `FileHandler` is attached anywhere in the codebase. When the console
  window closes, the entire run narrative is gone. `AgentManager.start` already contains truncate-on-start
  logic that looks for a `logging.FileHandler` (`agent_manager.py:249-253`) — that branch has never had a
  handler to find.

The irony: the reasons *are* logged. `_observe_agent` explains every cognition skip at INFO ("settled at
scheduled place, cognition sleeping", "scene unchanged (idle 3/N), skipping LLM"), and `_act_agent` logs
`LLM phase exception` / `No decision - idling`. All of it went to a window that no longer exists.

One genuine blind spot remains beyond durability: agents dropped from the `ready` filter in `_tick_impl`
(`is_busy`, cooldown, open chat, inactive) are logged **nowhere**. An APC wedged `is_busy` silently
vanishes from the sim and no log line marks its disappearance — the leading suspect for Maren going quiet
after 22:27:00.

Desired behavior:

1. The runner writes its full log to a file next to `agent_decisions.log`, truncated per run, so a closed
   console costs nothing.
2. Every tick accounts for **every** active agent — decided, skipped (with reason), or excluded (with
   reason). A silent disappearance becomes impossible.

Acceptance evidence: after a run, `logs/sim_runner.log` explains each agent's every tick without the
console; an agent stuck `is_busy` produces a visible per-tick line naming the cause.

**Classification:** loop-safe logging work. This is the "fail loud" rule applied to the sim's own loop —
"nothing in the log" must never again be the same observation as "nothing happened".

**IMPLEMENTED 2026-07-24.** Three changes, all in `agent_manager.py` plus a RUNBOOK correction:

- `_attach_run_log` adds a root `FileHandler` at `logs/sim_runner.log`, alongside `agent_decisions.log`,
  carrying the runner's own format and `SimRunFilter` so entries stay SR-tagged. Called from `start()`
  immediately after the SR tag is allocated — the log directory is only known once a level's agents load,
  which is why this lives in the manager rather than in `sim_runner.py`. Opened `mode="w"` (truncate per
  run, matching the decision log) and idempotent, so repeated runs in one process reuse one handler. It
  also raises the `AgentRuntime` logger to INFO explicitly: hosts that never call `basicConfig` (web UI,
  MCP) leave root at WARNING, which would drop every INFO record before any handler saw it. A failed open
  logs an error and leaves the console path working rather than taking the run down.
- `_tick_impl` now names every active agent excluded from the tick — `busy`, `cooling down (Ns)`,
  `chat open` — via `_not_ready_reason`, which mirrors the ready filter's own order. This was the one
  genuinely unlogged path: a wedged `is_busy` APC previously left the simulation in total silence.
- `_loop`'s existing `Tick #N` line gained a per-agent outcome roll-up from `_tick_outcomes`
  (`dufus=idle(scene_unchanged), maren=speak_to`), and a tick where **no** agent ran now logs that fact
  instead of passing unremarked — the exact shape of the SR30 blackout.

Verified by direct exercise of the three helpers (not the offline suite): the handler creates and writes
the file, a second call adds no duplicate handler, the roll-up renders reasons and returns empty for an
empty tick, and each not-ready branch returns its expected label. **Still owed:** the next live run — read
`logs/sim_runner.log` afterwards and it should explain every one of Dufus's silent ticks.

---

## 52. Simplify Dufus's goal stack — explore-and-survey only, drop the agenda juggling

**Status:** **OPEN 2026-07-29** · **Source:** user, live-run frustration: "we are asking too much of Dufus
with regards to our software technology. First he tries to go home and eat breakfast then he says go to get
his hat, then he gets interrupted."

Dufus is [[Dufus = VLM Training Corpus]]-scoped already (the world-scanning survey APC), but his
agenda/schedule still carries ordinary-life tasks (breakfast, fetch hat, etc.) that compete with survey
work for the same cognition slot and get preempted mid-chain. Each preemption is itself a source of the
"asks too much of the LLM" problem raised this session (agenda item, then override, then resume — more
state for the LLM to track correctly, more surface for it to get wrong). The user's proposed fix: strip
Dufus down to one job — wander the world and capture pictures (survey) — and remove the daily-life
schedule entirely for this character, rather than fixing the interruption/resume plumbing under it.

Needs a design pass before implementation:
- Does Dufus keep `agenda.json`/`goals.md` at all, or does his loop bypass the scheduler entirely and run
  survey/explore as the only behavior?
- Does he keep recognition/greeting/speech (social behaviors), or is he purely a silent camera?
- Does this apply only to Dufus, or does it imply a general "role" simplification for any future
  survey-only APC?

**Classification:** design-gated, not loop-safe — a character-scope decision, needs the user's call before
touching `agenda.json`/`goals.md`/`rules.md` or the scheduler's handling of him.

---

## 53. Capture navmesh-vs-semantic traversability disagreement as VLM training signal

**Status:** **OPEN 2026-07-29 — not building yet, explicit user call** · **Source:** user, this session:
"I know I can go forward (Unreal Nav Mesh), but I know I am blocked via LLM thoughts. I think this is the
big value of the system... Dufus or any 'surveyor' should be returning this information. This information
will be used to build a VLM for the particular world."

Distinct from what's already tracked:
- **#19/#27** (folded together) already identified the underlying disagreement — "navmesh says walkable;
  nothing says socially, stay off" (the corn-field/yard case, verbatim from 2026-07-06) — and proposed a
  lizard-brain surface fact (ground probe: "surface underfoot: grass/road/pavement") as one fix option. That
  is a same-tick *runtime* fact for the LLM to act on, not a stored training example.
- **#49** already establishes Dufus as the training-data source for a future custom VLM and proposes storing
  camera pose (`capture_x/y/z`, yaw) on place images — but only geometry, not any semantic/behavioral label.

What's net-new here: whenever a survey-flagged APC's navmesh reports a location as walkable **and** the
LLM's own reasoning rejects it (rules-driven refusal, "that's the corn field", "that moves away from my
goal"), that disagreement is itself a labeled example — pairs the frame Dufus already captures with a
ground-truth "physically possible, semantically rejected" tag and the LLM's stated reason. A future VLM
trained on this corpus could eventually report "cultivated field ahead, avoid" as a sensed fact the same way
the lizard brain already reports surface/obstacle facts ([[feedback_lizard_brain_contract]]), closing the
loop without ever hand-authoring zone geometry (e.g. the corn field's bounds, which nothing in the repo
currently records).

Needs before implementation (none of this is decided):
- Where the disagreement gets logged — a new capture record tied to `place_images`, or its own table —
  and whether it's Dufus-only or any APC carrying the survey attribute.
- What counts as "the LLM blocked it": a structured field the decision schema doesn't carry yet (today
  `thought_summary` is free text), vs. a rules.md-driven rejection the validator can detect deterministically.

**Classification:** design-gated, explicitly deferred — dataset design for a not-yet-started custom VLM,
not a bug fix. Relates to: #49, #19/#27, [[project_dufus_vlm_training_corpus]].

---

## Outstanding — human / editor / live (not loop-safe)

- **#35/#13.4:** design the LLM-directed expedition contract and pristine-run purge boundary before
  implementing whole-map visual surveying.
- **#32:** choose transient gaze retention/dedup policy and whether owned landmarks receive their own
  four-image survey sets in addition to community cells. Community marker/composite inspection is done.
- **#27:** choose community-landmark anchor/extent semantics, then continue persistent-ticket and
  obstacle/dead-end work; coarse routed arrival itself passed in SR15.
- **PIE verification bundle:** #17 routed travel, #23 landmarks, #24 launcher, #13.2/#13.3 cockpit
  controls, #14 replay, B7b personal space, and sweep/map behavior. Record each result against its
  canonical item; do not create another status banner.
- **Child Blueprints:** choose and apply Maren/Dufus meshes in the editor; bindings already landed.
- **#12.2:** decide whether interaction content belongs in the episodic log or a dedicated store.

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

**Status:** Rebind landed (2026-07-03); mesh choice pending · **Independence:** Self-contained

Dufus and Maren currently share one Blueprint (`BP_CameraNPC`) and look
identical. Give each its own mesh without duplicating logic.

- [x] Create child Blueprints of `BP_CameraNPC` — **user made `APC_Maren_BP` +
      `APC_Dufus_BP`** in-editor (2026-07-03), inheriting the shared
      `APCCharacterComponent` / AIState display / AI controller from the base.
- [x] **Rebind the agents (Python side) ✓ 2026-07-03.** Each `state.json` now
      binds to its child actor (`unreal_actor_name` = the placed label
      `APC_<Name>_BP`, `blueprint_class` = `/Game/Blueprints/APC_<Name>_BP.APC_<Name>_BP_C`).
      **Plus a display-name decoupling** so the engine label never leaks into the
      sim: new `Agent.display_name` ("Maren"/"Dufus") drives `known_characters`,
      and `_resolve_action_actor_refs`/`_actor_name_for` map a target back
      (display name / label / id → bound actor). Test: `test_actor_binding.py`.
- [ ] Pick the two meshes (project has `SkeletonCharacter` + AssetsvilleTown
      character skeletal meshes available). *(Editor + mesh choice — B-side.)*

*(The hand-linking done here is the first worked example of **#13** world-build
assistance — CC wires config when the user adds things, pending generation code.)*

Why child BPs not full copies: fix shared bugs once; the status-bubble display
and component come along automatically.

---

## 1. Named-place navigation + grid/place cells

**Status:** **Foundation complete** — name resolution and place/grid persistence landed; #17 added
multi-leg routing. Remaining navigation responsibility is canonical in #27. · **Independence:**
Self-contained (no dependency on #2/#3)

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
- [x] Finalize grid cells and place cells. Central community cells, APC-owned cells, extents,
      staleness, authored sources, and routed travel landed across A2/A5 and #15–#18.
- [x] Attach observations to grid/place cells through visits, compass observations, sweeps, and
      authored/runtime source tagging. Further movement policy belongs to #27.
- [x] Reset the place-cell DB to start from scratch (`reset_world_places()`). ✓ 2026-06-24

> Note: the walk_to *error* is already dead (no failures since 2026-05-14). This
> item is the genuine outstanding work — goal-directed navigation, not the error.

Relates to: engine-agnostic navigation, lizard-brain sensing.

---

## 2. World Sim web-app settings page + rename

**Status:** **Core built offline** — settings backend/page, provider profiles, navigation, and
surface rename landed; live UX spot-check/polish remains. · **Independence:** Coupled with #3
(shared web app)

The app's scope has grown past building individual NPCs — it's becoming the
control surface for the whole simulation.

- [x] Add a **settings/configuration page** to the web app — manage config
      (model/provider selection, sim parameters) through the UI instead of
      hand-editing `.env`. ✓ 2026-06-26; provider-profile CRUD followed 2026-06-28.
  - [x] Ollama/cloud selection is surfaced through named provider profiles.
- [x] Rename the active surface **"NPC Builder" → "Unreal World Sim"**. Legacy
      `npc_builder` code was later removed; #22 removed obsolete launch/MCP surfaces.

Config complexity is ours to solve in the UI, not the user's.

Action breakdown (from dreams iter 3, `plan/dreams/dreams_2026-06-25_1131.md` — subagent-ready):
- [x] **2.1** Rename surface strings only (`web_ui` templates, `main.py` title/docstring,
      `start_npc_builder.bat`, `/create-npc` skill prose); leave `npc_builder` *code identifiers* for a
      separate pass. ✓ 2026-06-26.
- [x] **2.2** New `agent_runtime/config_store.py` — `read_config()` (secrets as set/unset, never values)
      + `write_config()` that rewrites `.env` preserving comments/order, leaving omitted secrets intact.
      ✓ 2026-06-26. Offline test: `test_config_store.py`. *(Reload: callers invoke the existing
      `load_dotenv(override=True)` path — `reload_llm_environment`; not bundled into write_config.)*
- [x] **2.3** Settings page: `GET/POST /settings` in `web_ui/main.py` + `settings.html` + nav link.
- [x] **2.4** Provider selection generalized beyond the original toggle into named profiles with
      decision/vision role assignment. Live UX polish remains, not core implementation.

Decisions (human): persistence target `.env` vs new `config.json` (rec: `.env`)? secrets editable in the
form or set/unset display only (rec: display only)? rename scope surface-only now vs code identifiers too
(rec: surface-only)?

---

## 3. Independent sim lifetime

**Status:** **Built offline; live Unreal verification pending** — `sim_runner.py`, runner HTTP API,
`RunnerClient`, web cockpit, and one-click launcher exist. · **Size:** Potentially large ·
**Independence:** Coupled with #2

Originally Claude Code owned the simulator lifetime. The standalone runner now owns it and the
web cockpit controls it over localhost HTTP; remaining work is live verification and hardening.

The coupling is one line: `unreal_sim_server.py:417` `mcp.run(transport='stdio')` — the MCP
server is a stdio subprocess of Claude Code, and the `AgentManager` (async sim loop) lives inside
it. `UnrealBridge` (TCP 55557) + the web UI's direct socket are already Claude-independent.

Action breakdown (from dreams iter 2, `plan/dreams/dreams_2026-06-24_2327.md` — subagent-ready):
- [x] **2.1** Factor `AgentManager` construction into `agent_runtime/factory.py` (shared by MCP + runner).
      ✓ 2026-06-26 — `build_agent_manager(worlds_dir=None)`; `get_agent_manager` now delegates to it.
      No I/O at construction, so offline-testable: `test_factory.py`.
- [x] **2.2** New `Python/sim_runner.py` — standalone process that runs the loop with no MCP/Claude.
- [x] **2.3** Control surface on the runner (localhost HTTP: start/stop/status/tick).
- [x] **2.4** Make `simulation_tools.py` thin clients of the runner (attach, don't host).
      ✓ 2026-07-03 — every director tool goes through `RunnerClient`; no runner reachable = loud
      error with the start hint (never an in-process manager). Runner API + client grew the missing
      director surface; `generate_world_grid` moved into `AgentManager` (the runner owns the bridge).
      Offline end-to-end: `test_sim_tools_attach.py`. *Live verify: run `sim_runner` + drive one tool.*
- [x] **2.5** Point web_ui at the runner control API (→ theme #2/③ controller). Fleshed out in dreams
      iter 3 (`plan/dreams/dreams_2026-06-25_1131.md` Action 3.5): `sim_runner_client` in
      `web_ui/unreal_client.py` + a dashboard status panel and start/stop buttons; no auto-spawn (keep
      lifetime decoupled); if no runner is reachable, render "no sim runner running". ✓ 2026-06-26.

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

**Status:** **Harness built; Codex workflow refresh landed** — test runner/preflight and the five
project-local skills are committed on `main` as of `0d64b21`. Live-sim
autonomy remains gated by cost and Unreal/PIE. · **Size:** Process/setup, not a code feature ·
**Depends on:** #3 live verification for live-sim autonomy

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

**Status:** **Core memory layer built** — episodic/social stores, prompt recall, consolidation, and
recent-greeting suppression landed; #12.2 interaction schema and sentiment policy remain open. ·
**Independence:** Extends #1 · **Source:** dreams iteration 1
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

**Status:** **QUERY/ROUTE-PROMPT SLICE REOPENED 2026-07-21** — query/authoring/visualization and
coarse routing landed through #1, #16, #17, #18, #23, and #27; the navmesh path-as-facts query and
guaranteed pre-decision delivery remain outstanding. · **Independence:**
Builds on #1 (place resolver) · **Source:** user, 2026-06-26

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

**Renewed requirement and live evidence 2026-07-21 (SR28):** the world now contains a named community
cell called `village square`, yet Dufus followed competing home/survey/schedule intents and backtracked
before heading toward the village. When cognition says “I have to go to the village square,” lizard brain
must query the canonical PlaceDB name resolver for the matching grid cell, query a traversable route from
the APC's current position to that cell, and place both facts in the same decision context: resolved name,
target `(col,row)`, target world center/arrival region, reachability, and a bounded semantic waypoint or
heading sequence. Do not depend on the LLM remembering where the name is, and do not let the model invent
engine coordinates. The route is factual context; the LLM retains the choice to follow or revise it.

Acceptance evidence: with `village square` named in PlaceDB, a travel decision receives its exact resolved
cell and a valid current-position-to-target path before choosing an action; an unknown or ambiguous name
produces an explicit grounded failure/candidate list; route progress is refreshed after deviation or an
interruption; and a live run reaches the village square without returning to an obsolete starting point.
**Classification:** C++/editor nav-query integration plus loop-safe resolver/context/policy tests and
live/PIE navigation verification. **Dependency/open decision:** reuse the existing UE navigation bridge
if it can return path points; otherwise add a read-only path-query primitive. Preserve #27's movement
execution and #36's intent arbitration rather than embedding goal priority in the route provider.

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

## 6b. APC-generated top-down map — lizard-brain "chart me a course"

**Status:** **Built offline 2026-07-01; PIE attachment verify pending** · **Source:** user,
2026-07-01 · **Independence:** builds on #1/#6 + lizard brain

An APC needs to build its **own top-down map** to plan a route, generated on demand via **lizard brain**.
The scenario the user gave: *"I woke up, I'm at my house, but my schedule says I need to be at my
vegetable truck. Build a top-down map of where I am and where I need to be, so I can chart a course."*

- [x] **APC map-view component** ✓ 2026-07-01 (WP5 built — see sign-off note below) — `route_map.py`
      builds corridor facts from PlaceDB + WorldGrid and renders a top-down PNG; injected on travel
      ticks into the decision prompt + attached to the multimodal decision call.
- [x] **Charting a course** — the substrate is in the APC's hands (map facts + image on every travel
      tick; the LLM charts the course). ✓ 2026-07-01. *The navmesh path-as-facts query stays open as
      #6 "lizard-brain routing" — it would slot into `build_route_map` output as `"route": [...]`.*

Ties into: the "restart day / morning" flow (#10 + A3) — on wake with a schedule destination, the APC
builds this map to get moving; #6 (lizard-brain routing — path as facts); #1 (name→cell resolve);
[[architecture_lizard_brain_sensing]], [[feedback_lizard_brain_contract]] (map/route must stay **facts**,
never prescriptive advice).

*(Design questions for later — do not implement yet: is the "map" a semantic structure the LLM reads, or
a rendered image? how far around the APC does it extend — just the corridor between here↔there, or a
radius? shared with the web A1 view or separate?)*

**APPROVED + BUILT ✓ 2026-07-01** (user signed off the four decisions same session; see
`plan/specs/WP5-apc-topdown-map.md` executor notes). Sign-off: **Q1 = RENDERED IMAGE** (user's call,
diverging from the semantic-text rec — the facts dict is still built, the PNG is a projection of it,
attached to the multimodal decision call), Q2 corridor+1 cap 15×15, Q3 separate renderer over shared
PlaceDB, exposure = travel ticks only. Built: `route_map.py` (`corridor`/`build_route_map`/
`render_map_image`), `AgentManager.route_map_for` (community→owned resolution), travel-tick injection
in `_perceive_and_decide`, `{route_map_note}` prompt section, image passed to the anthropic/ollama
decision call (OpenAI text-only). Test: `test_route_map.py`. Suite 30/30. **Remaining: PIE verify**
(map attaches on a live travel tick; folds into B2).

---

## 6c. Real-world PNG map background — grid + place cells overlaid on the actual world

**Status:** **Superseded/completed by #18** — the registered live camera replaced manual
assume-bounds calibration and agent dots were user-verified. · **Source:** user, 2026-07-03 ·
**Independence:** extends A1 (web `/map`) + #6b

> **⚑ Built 2026-07-05:** calibration decision made by the user ("if the actual world is m×n, we
> carve that up into 30 m cells — calculate off that fact") = **assume-covers-bounds**: the capture
> frames the world bounds exactly, world→pixel is linear. Orientation follows the project compass
> convention (`place_db.py`): **+X = east = image right, +Y = south = image down, row 0 = north/top**
> (image 1023×670 aspect 1.527 ≈ bounds 47000×30859 aspect 1.523 — confirms whole-world framing).
> `WorldGrid.origin()` exposes the origin-anchored cell (0,0) corner (starts *outside* bounds —
> edge cells crop at the image edge, `overflow:hidden`). `/api/map` now carries
> `bounds/origin_x/origin_y/image_url` + owned `dx/dy/extent_cm`; `map.html` draws the capture as
> the background with translucent world-registered cell overlays + purple 9×9 m owned-place boxes
> (first consumer of `extent_cm`). Per-level `images/<level>.png` beats the shared
> `world_map_view.png`; no capture → plain background at the world's aspect (same overlay engine).
> Tests: `test_map_view.py`, `test_world_grid.py`. **Live verify:** open `/map` in a browser over
> the real capture; re-shoot the capture if the gridlines look offset from the town.
· **Asset in place:** `Python/web_ui/images/world_map_view.png` (1023×670, a top-down capture of the
whole level; the user added it "for future work").

Today both maps are **abstract**: the web `/map` (A1) is a bare CSS grid of colored cells, and the #6b
route map is a rendered top-down of cell states. The user wants the grid + place cells drawn **on top of
a real top-down image of the world**, so you see the actual town with the grid, named community cells,
and APC-owned place cells (the 3 m boxes / bigger building extents) registered over it. Applies to the
web `/map` first; could later back the #6b APC route map too.

**The crux is registration (world ↔ image-pixel mapping), not drawing.** Everything else is
straightforward overlay work; the hard part is knowing which world (X, Y) each pixel is.
- The capture already looks **whole-world framed**: image aspect 1.527 ≈ world-bounds aspect 1.523
  (`world_grid.json` bounds 47000×30859 cm). So a first cut can assume *the PNG covers exactly the grid
  bounds* and map linearly bounds→pixels. Verify before trusting it.
- **UE axis orientation must be reconciled:** X is forward/north-ish (red), Y is right/east (green),
  and our grid convention is **row 0 = north (−Y) at the top** (see A1 / `route_map.py`). The capture's
  in-editor axis gizmo (bottom-left of the screenshot) shows X/Y rotated from screen up/right, so the
  overlay needs an explicit `world→pixel` transform (which world axis → image u, which → image v, and
  the sign/flip), not an assumption.
- Make it **robust to re-capture:** store the image's world extent + orientation next to it (e.g.
  `world_map_view.json`: `{covers_bounds: {min_x,min_y,max_x,max_y}, x_axis:"right|left|up|down",
  y_axis:...}` or a 2-point calibration `pixel↔world`). Then a new screenshot at a different framing
  just updates that file, no code change. Decision below.

**Build sketch (once registration is settled):**
- `web_ui`: serve the PNG (static route/`/images/...`); add a `world→pixel` helper from the calibration.
- `map.html`: put the PNG as the `#grid` background (or an absolutely-positioned layer under it), size
  the grid to the image, and make cells a **semi-transparent overlay** with an opacity/hide toggle so
  you can see the town through them. Named/swept/owned styling unchanged.
- **Place-cell markers:** draw community names at their cell centers and owned places at
  `cell_center + (dx,dy)` (already in `all_owned_places`), sized by `extent_cm` (the 3 m box, bigger for
  buildings) — the first consumer of the extent field (#11.2 D5 left it unused).
- Keep the abstract grid as a fallback when no image/calibration exists (worlds without a capture).

**Decisions (human, later):** calibration method — assume-covers-bounds (simplest, works if every
capture is whole-world ortho) vs. a stored world-extent JSON vs. an in-UI 2-point click-calibration
(most robust to ad-hoc screenshots)? Is the capture **orthographic** (needed for a clean linear map) or
a perspective shot (parallax → non-linear, would need corner homography)? One shared background for the
web map and the #6b APC route map, or separate?

Ties into: A1 (web `/map`), #6b (APC route map), #11.2 (owned-place extents), #1 (name→cell resolve),
`generate_world_grid` (bounds source), [[architecture_lizard_brain_sensing]].

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
- [x] **Live 360 rotation+capture (`observe_heading`)** ✓ 2026-07-01 — **no C++ needed** (the assumed
      "bridge/C++ handler" was stale): composed in Python from the wake look-around's existing primitives
      — `AgentManager._execute_sweep_observe` does `set_facing` (rotate in place) → settle → `capture_view`
      → perceive → `PlaceDB.ingest_compass` under `yaw_to_compass(yaw)`; routed from
      `_execute_world_action` on `observe_heading`. Degrades per-heading (bad turn/capture/vision records
      nothing, never wedges the sweep). Offline-tested end-to-end with stubs (full 8-heading sweep
      populates 8 compass observations): `test_cell_sweep.py`. *Live PIE verify remains (B-side).*
- [~] ~~**Spawn/config a maintenance APC**~~ — **obsolete**: the dedicated role was retired (#11.1/WP3);
      any APC sweeps. Nothing to spawn.

Relates to: #1 (cell_center resolve), #6 (map/known_places), #5 (episodic), engine-agnostic nav.

---

## 8. Talk to Unreal without MCP (Claude-driven + standalone)

**Status:** **Standalone and HTTP operator paths built; custom MCP retired by #22.** Documentation
and higher-level dev-mode ergonomics remain under #9. · **Source:** user, 2026-06-28 ·
**Independence:** relates to #3

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

**Status:** **Partially realized** — standalone sim mode and HTTP controls exist; a durable supervised
operator workflow and log-triage contract remain open. · **Source:** user, 2026-06-28 ·
**Independence:** uses computer/browser use, needs supervision first.

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

- **Current priority and classification live only in the Active view at the top.** Dated
  banners and old queues are evidence, not instructions.
- **The historical #32 → #33 → #27 direction and #29 → #20 → #30 offline queue are complete or
  superseded.** #38 interruption architecture is now offline-complete. Current priority is only the
  Active view at the top: #37 chat, then #36 ordered goals; #16 authoring and #35 expeditions wait on
  their listed choices.
- **#4's harness is built** (`run_tests.py`, `preflight.py`, `autonomous_loop.md`);
  running the live sim autonomously is still gated by Unreal/PIE reliability and inference cost.
- **Verification uses `python scripts/run_tests.py`.** Never copy an old suite count forward;
  record the count produced by the commit being described.
