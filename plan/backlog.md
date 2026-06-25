# Backlog

Rolling list of outstanding work — add items as they come up, check off or
delete them as they land. Not session-scoped; this is the durable home for
"things I want done but didn't have tokens for this session." Newest
grooming: 2026-06-24.

## Recently landed

- **Place-cell DB reset** (2026-06-24) — `reset_world_places()` MCP tool wipes
  the shared `world_places.db` (place_cells, place_observations, agent_visits)
  for a true blank world; complements `reset_agents` which preserves the map.
  `PlaceDB.reset()` in `Python/agent_runtime/place_db.py`. *(Part of #1.)*

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

## Notes

- **#2 and #3 are coupled** — the standalone launcher probably belongs in the
  same web app that's getting the settings page and rename.
- **#1 is independent** and the most self-contained — good candidate to tackle
  first.
