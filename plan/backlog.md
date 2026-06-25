# Backlog

Rolling list of outstanding work — add items as they come up, check off or
delete them as they land. Not session-scoped; this is the durable home for
"things I want done but didn't have tokens for this session." Newest
grooming: 2026-06-25.

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

- [ ] Build a place-name → PlaceDB cell-center (or scene actor) resolver so
      `walk_to <place>` navigates instead of idling.
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

---

## 3. Independent sim lifetime

**Status:** Not started · **Size:** Potentially large · **Independence:** Coupled with #2

Today **Claude Code owns the lifetime** of the MCP server + simulator — when
Claude isn't running, the sim isn't running. The user wants the world sim to run
**independently of Claude Code** so it can run overnight or for long stretches
without Claude Code open.

- [ ] Decouple the agent runtime / Unreal bridge so the sim loop runs as a
      standalone process (launched from the web app or a CLI/service) with its
      own lifetime.
- [ ] Claude Code (and the MCP tools) should be able to **attach to and inspect**
      a running sim, not be the thing that keeps it alive.

The sim is the product; Claude is a tool for building it, not a required host
process. The standalone launcher likely belongs in the same web app as #2.

---

## 4. Autonomous building loop (run unattended until limits, resume next session)

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
