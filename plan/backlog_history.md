# Backlog history

Moved out of `plan/backlog.md` on 2026-08-19 to cut per-session read cost.
Dated status banners and the completed 2026-07 queues live here, as
evidence only — `plan/backlog.md`'s active view is authoritative.

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

