# Simulation Runbook

How to run the NPC agent simulation. The sim is driven through MCP (this repo's
`unrealSIM` server) â€” from the Claude Code CLI, just ask in plain language
("start the sim", "reset the agents"). Web UI sim control is deferred.

## Architecture (who thinks what)

| Role | Model | Where |
| --- | --- | --- |
| NPC thoughts (wake orientation, per-tick decisions) | Anthropic Haiku | `Python/agent_runtime/llm_router.py` |
| NPC eyes (screenshot â†’ named sightings) | Gemini flash-lite | `Python/agent_runtime/perception.py` |
| Builder/director (writes code, drives sim via MCP) | Claude Code CLI | not part of the sim loop |

The decision LLM never sees pixels: Gemini turns every capture into structured
sightings (landmarks/characters with bearing + distance), Python accumulates
them into each agent's spatial map, and the decision LLM reads facts as text.
Division of labor: **the LLM judges, Unreal senses, Python accumulates.**

## Prerequisites (each session)

1. **Unreal editor open** with the MCP_World level and **PIE running** (Play).
   Agents bind to live PIE actors â€” nothing works outside PIE.
2. **MCP server connected.** After ANY Python change: reconnect via `/mcp`.
   C++ plugin changes need an Unreal recompile instead.
3. **Keys/models in `Python/.env`** â€” `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL`
   (thoughts), `GEMINI_API_KEY` + `GEMINI_MODEL` (eyes), `LLM_PROVIDER`.
   The `.env` is re-read on every LLM call, so edits apply immediately â€”
   no restart needed.

## Controls (MCP tools)

| What | Tool |
| --- | --- |
| Start simulation | `start_simulation` â€” `tick_seconds` (base pacing, default 1), `active_agents` (e.g. `["maren"]`, omit for all), `mode` (`"live"` = LLM-driven, `"explore"` = deterministic frontier mapping) |
| Stop | `stop_simulation` |
| Pause / resume | `pause_simulation` / `resume_simulation` |
| Status | `get_simulation_status` |
| Agents | `list_agents`, `inspect_agent` |
| Reset to run-start | `reset_agents` â€” teleports each agent back to its recorded start transform, reseeds memories, wipes spatial maps. **PIE must be running.** |
| Change a goal mid-run | `set_agent_goal` |
| Rebind after level/actor changes | `resync_simulation` |

Never parallelize Unreal MCP calls â€” the bridge is a single socket; concurrent
calls time out.

## What happens on `start_simulation` (live mode)

1. Agents load from `Python/worlds/<level>/agents/<id>/` (character.md,
   goals.md, rules.md, tools.json, state.json) and bind to PIE actors.
2. Each agent's run-start transform is recorded once (used by `reset_agents`).
3. The log file is truncated â€” every run starts a clean log.
4. **Wake sequence** per agent (the spool-up):
   - 180Â° look-around: turn in place through 5 headings (left â†’ right),
     capture a view at each, restore original facing
   - Gemini perceives each view (landmarks, characters, caption)
   - One Haiku call answers, in character: *Where am I? What time is it?
     Where should I be?* â€” and returns a goal, a name for the current place,
     and the first action of the day
   - The place name and all sweep sightings are written into the agent's
     spatial map; the first action executes immediately
5. **Tick loop**: capture â†’ visual-diff gate (skip if scene unchanged) â†’
   Gemini perceives â†’ Haiku decides one action â†’ action executes â†’ memory +
   spatial map updated. Base tick sleep starts only after processing, so ticks
   never pile up.

## Movement vocabulary

- `walk_to target_actor=<label>` â€” walk to a known character
- `walk_to direction=forward|forward-left|forward-right|left|right|back` â€”
  one ~15 m step relative to current facing ("forward" = the perceived view)
- `wander` â€” one step forward (purposeful continue, not random)

## Where to watch

- **Log**: `Python/unreal_mcp.log` (cleared each run) â€” or the log panel in
  the web UI at `http://localhost:8765`
- **What they saw**: `Python/worlds/<level>/agents/<id>/observations/*.png`
  (`*_wake_<direction>.png` = the 5 sweep views)
- **Mental map**: `Python/worlds/<level>/agents/<id>/spatial_map.json` â€”
  grid cells visited + accumulated place labels
- **Memories / goals / binding**: `memory.json`, `state.json` in the same dir
- **World clock config**: `Python/worlds/<level>/world.json`;
  grid bounds: `world_grid.json`

## Offline tests (no Unreal, no API keys)

```
cd Python
.venv\Scripts\python.exe scripts\agent_runtime\test_spool_up.py
.venv\Scripts\python.exe scripts\agent_runtime\test_frontier_blocking.py
.venv\Scripts\python.exe scripts\agent_runtime\test_stuck_detection.py
```

## Level fixes (Unreal editor)

### Vehicles don't block the navmesh â†’ NPCs wedge against them

World vehicles are loose **`SkeletalMeshActor`** instances named `veh_*`
(`veh_Van_*`, `veh_VegetableTruck*`). Skeletal meshes do **not** carve the Recast
navmesh (their collision is a PhysicsAsset, which the nav build ignores), so NPCs
path straight into them and get stuck. Editing the collision preset on the actors
does nothing for navigation â€” you must add an explicit nav modifier.

The software net for this already exists (stuck detection re-decides a wedged
agent â€” see below), but the proper fix is to carve the navmesh. Run this in
Unreal: **Tools â†’ Execute Python Script** (or Output Log `Cmd: â–¾ Python`):

```python
import unreal

# Half-extents of the carve box (cm). Vehicles ~5 m long â†’ ~260 x 120 x 120.
EXTENT = unreal.Vector(260.0, 120.0, 120.0)
PREFIX = "veh_"          # narrow to one actor (e.g. "veh_van_2") to test first

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
vehicles = [a for a in eas.get_all_level_actors()
            if a.get_actor_label().lower().startswith(PREFIX.lower())
            and isinstance(a, unreal.SkeletalMeshActor)]

done = 0
for a in vehicles:
    skm = a.skeletal_mesh_component          # strip nav relevance so the
    if skm:                                  # modifier uses FailsafeExtent (a
        try:                                 # clean box), not skeletal geo
            skm.set_editor_property("can_ever_affect_navigation", False)
        except Exception as e:
            unreal.log_warning(f"nav-relevance not disabled on {a.get_actor_label()}: {e}")
    comp = a.add_component_by_class(unreal.NavModifierComponent, False,
                                    unreal.Transform(), False)
    if not comp:
        unreal.log_warning(f"skip {a.get_actor_label()} (no component)")
        continue
    comp.set_editor_property("area_class", unreal.NavArea_Null)   # remove cells
    comp.set_editor_property("failsafe_extent", EXTENT)
    done += 1

unreal.log(f"NavModifier(Null) added to {done} / {len(vehicles)} vehicles")
```

Steps:
1. **Test on one** â€” set `PREFIX = "veh_van_2"`, run, press **`P`** to view the
   navmesh, confirm a hole under that van. Tune `EXTENT` if needed.
2. Run on all `veh_`, then **save the level** (instanced components persist on save).
3. **Navigation Mesh â†’ Runtime Generation = `Dynamic Modifiers Only`**,
   **Build â†’ Build Paths**, verify holes with **`P`**.

`NavArea_Null` (not `NavArea_Obstacle`) is deliberate â€” Null removes the cells so
AI routes around; Obstacle only raises cost. The MCP bridge can't run editor
Python, so this is a manual step.

## Troubleshooting

- **"No agents could be bound"** â€” PIE not running, or actor names/labels in
  `state.json` don't match the level. Run `resync_simulation` or check labels.
- **Wake-up LLM call failed: `'typing.Union' object has no attribute
  '__module__'`** â€” outdated `anthropic`/`httpcore` for Python 3.14. Fixed
  2026-06-11 (`anthropic>=0.109`, lock updated). If it recurs:
  `uv pip install --python .venv\Scripts\python.exe -U httpcore httpx anthropic`
- **Agents keep authored goals after wake** â€” the wake failed soft; check the
  log for `Wake-up failed` / `Wake-up produced no orientation`.
- **"your vision failed this tick" in prompts / perception errors in log** â€”
  Gemini key/quota problem; sim keeps running blind on memories + map.
- **Sweep views all look identical** â€” actor rotation isn't reaching the
  capture camera; check that `command_character_teleport` rotation works for
  the character blueprint.
- **NPC wedged against a vehicle / not moving despite walking** â€” the vehicle
  isn't carved out of the navmesh. The live path now detects this (logs
  `[id] stuck on an obstacle â€” re-deciding`) and re-prompts the agent to find
  another way; the permanent fix is the navmesh carveout above (Level fixes).
- **Python edits not taking effect** â€” you forgot `/mcp` reconnect.
