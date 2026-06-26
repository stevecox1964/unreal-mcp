# Backlog

Rolling list of outstanding work — add items as they come up, check off or
delete them as they land. Not session-scoped; this is the durable home for
"things I want done but didn't have tokens for this session." Newest
grooming: 2026-06-25.

> **★ MVP slice** (dreams iter 5, `plan/dreams/dreams_2026-06-25_1156.md`):
> *"Runs overnight, navigates to a named place, remembers who it met"* = **#3** (runner /
> independent lifetime) + **#1** (place-name resolver) + **#5** (social store + consolidation).
> **#1 is the keystone** (no deps, offline, unblocks #4's first target and #5's social-goal hooks);
> **#3 is the long pole** (nothing built yet) — start it in parallel. #2 settings, #4 loop, and
> Child BPs are *off* the MVP critical path. Recommended order: #1 → #5 → (#3 in parallel) → web
> controller → #2/#4. Design observation→cell storage **once** in #1 for #5 to reuse.

## Recently landed

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
- [ ] Finalize grid cells and place cells.
- [ ] Design how observations attach to / save against grid/place cells.
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
- [ ] **2.2** New `agent_runtime/config_store.py` — `read_config()` (secrets as set/unset, never values)
      + `write_config()` that rewrites `.env` preserving comments and triggers the existing reload.
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
- [ ] **2.1** Factor `AgentManager` construction into `agent_runtime/factory.py` (shared by MCP + runner).
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
- [ ] **4.1** Write `plan/autonomous_loop.md` — the run-contract the loop reads each start (allowed
      surface, hard NOs, stop conditions, per-item cycle). Link from #4 + `handoffs/LATEST.md`.
- [ ] **4.2** `Python/scripts/loop/preflight.py` — refuse to start unless tree clean, on a dedicated
      loop branch (not `main`), and baseline tests green.
- [ ] **4.3** `Python/scripts/run_tests.py` — discover + run every `scripts/**/test_*.py` offline,
      one PASS/FAIL signal; `--only <glob>` for the in-progress test. (The loop has no aggregate signal today.)
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

- [ ] **Episodic observation record** — persist structured per-tick events
      `{agent, t, grid_cell, place, saw[], action, outcome}` attached to place cells (extends
      #1's "how observations save" subtask).
- [ ] **Social/acquaintance store** (per agent) — `{character: {first_met, last_seen(cell,t),
      meet_count, sentiment}}`, fed from perceived characters + say/message events; wire into
      recall and `known_characters`.
- [ ] **Social goal hooks** — let the decision layer propose "greet <person not seen today>" /
      "go where people are" (needs #1 to resolve person/place → location to navigate).
- [ ] **Memory retrieval + consolidation** — relevance = recency ⊕ spatial ⊕ social; periodic
      consolidation to beat the 30-item amnesia (critical for overnight runs).

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
- [ ] **Map query** — expose the named places to an agent: "what places do I know?" returns the
      named cells (name + direction/distance from here). Decide: a tool the LLM calls vs. injected
      into tick context.
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

## Later / ideas

- **Hybrid provider config (cloud + local mix).** Run some roles on cloud and
  others local — e.g. cloud Haiku for decisions, local qwen for vision, or vice
  versa. Already partly possible: `LLM_PROVIDER` and `VISION_PROVIDER` are
  independent in `.env`. The feature is making the mix easy to manage (per-role,
  maybe per-agent) and surfacing it in the settings page (#2). Cloud is clearly
  faster today (~9s/tick vs ~215s cold local first tick); full-local stays the
  long-term goal once the other pieces are in. **Local/hybrid is the cost enabler
  for the autonomous loop (#4)** — unattended cloud runs burn credits. Not a
  priority now, but it's the unlock for overnight autonomy.

## Notes

- **#2 and #3 are coupled** — the standalone launcher probably belongs in the
  same web app that's getting the settings page and rename.
- **#1 is independent** and the most self-contained — good candidate to tackle
  first.
- **Child BPs (Next up) are self-contained** and the chosen next task.
- **#4 (autonomous loop) is gated by local models + #3** — its first safe target
  is #1; don't point a loop at the whole backlog (half needs the editor or you).
