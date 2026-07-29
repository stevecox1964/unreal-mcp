# Simulation Runbook

How to run the NPC agent simulation. There are two ways to drive it:

- **Standalone** (normal use) — `Python/start_sim.bat` runs the sim engine and a
  web cockpit. No Claude, no MCP. This is the path documented step-by-step below.
- **From Claude Code** — the `unrealSIM` MCP server; just ask in plain language
  ("start the sim", "reset the agents"). See *MCP controls* near the end.

## Architecture (who thinks what)

| Role | Model | Where |
| --- | --- | --- |
| NPC thoughts (wake orientation, per-tick decisions) | Anthropic **Sonnet 5** | `Python/agent_runtime/llm_router.py` |
| NPC eyes (screenshot -> named sightings) | Anthropic **Haiku 4.5** | `Python/agent_runtime/perception.py` |
| Builder/director (writes code, drives sim via MCP) | Claude Code CLI | not part of the sim loop |

The two roles resolve **independently**: decisions read `ANTHROPIC_MODEL`, vision
reads `ANTHROPIC_VISION_MODEL`. Changing one never moves the other. Gemini
(`VISION_PROVIDER=gemini` + `GEMINI_MODEL`) and local Ollama are alternative
vision providers; both are configured in `.env` but inactive.

The decision LLM never sees pixels: the vision model turns every capture into
structured sightings (landmarks/characters with bearing + distance), Python
accumulates them into each agent's spatial map, and the decision LLM reads facts
as text. Division of labor: **the LLM judges, Unreal senses, Python accumulates.**

---

## Startup sequence (every session)

### 1. Unreal — get into PIE

Open the Unreal editor on the **MCP_World** level and press **Play** (PIE).

**Agents bind to live PIE actors — nothing works outside PIE.** If the sim is
started while PIE is stopped, every agent fails to bind and the run is dead on
arrival.

### 2. Start the sim app

Double-click **`Python/start_sim.bat`**. It:

1. Kills anything already listening on **8777** (sim engine) and **8765** (cockpit).
2. Opens a **"Sim Engine (sim_runner)"** console window — this is the engine.
3. Starts the web cockpit in the window you launched from.
4. Opens `http://127.0.0.1:8765/sim` in your browser once port 8765 answers.

Leave **both** windows open. Closing the Sim Engine window kills the run; the
cockpit is only a remote control for it.

> After editing any Python file, restart via `start_sim.bat` — it relaunches both
> processes. Editing `.env` does **not** need a restart (it is re-read on every
> LLM call), but editing code does.

### 3. Cockpit — the clicks

At `http://127.0.0.1:8765/sim`:

1. Check the **Status** line at the top. It should show the runner and your
   agents. If it says it can't reach the runner, the Sim Engine window isn't up.
2. Set **Tick seconds** (default 2) and **Mode**:
   - `live` — LLM-driven. This is the normal mode.
   - `explore` — deterministic frontier mapping, no LLM.
3. Click **▶ Start**.

**That is the only required click.** Everything else on the page is situational.

### 4. Watch it

- **Live, everything** — the **Sim Engine console window**. Scroll back here
  first when something goes wrong mid-run.
- **After the fact, everything** — `Python/worlds/<level>/logs/sim_runner.log`
  mirrors that console stream to disk, so closing the window no longer destroys
  the record. **Truncated at the start of every run**, so copy it elsewhere
  before starting the next one if a run is worth keeping.
- **Feed** — the event panel on `/sim`, tailing `agent_decisions.log`
  (**Clear feed** truncates that file). Note it records **completed decisions
  only**: a tick where an APC never decided appears nowhere in it. That is what
  `sim_runner.log` is for.
- **An individual APC** — `/worlds/MCP_World/agents/<id>` for the cockpit
  drill-down: right now, next, agenda tasks, today so far, survey state.
- **Talk to one** — `/chat`. **Replay a run frame-by-frame** — `/replay`.
- **Map viewer** — `/map`. **Keys/models** — `/settings`.

---

## Cockpit buttons — what each one actually does

Only **Start** is part of a normal run. The rest are tools you reach for
deliberately.

| Button | What it does | When |
| --- | --- | --- |
| **▶ Start** | Begins the run at the chosen tick/mode | Every run |
| **■ Stop** | Halts the loop; leaves all state alone | End of a run, or before repositioning APCs |
| **⏭ Step (1 tick)** | Advances exactly one tick | Debugging — watch one decision in isolation |
| **☀ Restart day** | Fresh morning, schedules regenerate. **Memories and place cells are kept** | Re-run a day without losing what they learned |
| **🧠 Reset agents** | Teleports APCs to start spots and **wipes learned memories** (restores `memory.seed.json` if present) | Clean-slate behaviour test |
| **🗺 Reset places** | Wipes the shared world map DB (landmarks re-apply on next start) | Map/survey work — throws away every APC's shared map |
| **📍 Capture starts** | Records each APC's **current** Unreal position as its future start/reset point | After hand-placing APCs in the editor. **Stop the sim and place them first** |

The four outlined buttons each pop a confirm dialog first — read it, they are not
all reversible. **Reset places** and **Reset agents** destroy accumulated state.

---

## What happens on Start (live mode)

1. Agents load from `Python/worlds/<level>/agents/<id>/` (character.md, goals.md,
   rules.md, agenda.json, tools.json, state.json) and bind to PIE actors.
2. Each agent's run-start transform is recorded once (used by *Reset agents*).
3. The run gets a new **`SR<n>`** id. Every decision-log line and every
   observation PNG is tagged with it — that tag is how you separate this run
   from previous ones afterwards. (Nothing is truncated in standalone mode; logs
   accumulate across runs.)
4. **Wake sequence** per agent (the spool-up):
   - 180-degree look-around: turn in place through 5 headings (left to right),
     capture a view at each, restore original facing
   - The vision model perceives each view (landmarks, characters, caption)
   - One decision call answers, in character: *Where am I? What time is it?
     Where should I be?* — returning a goal, a name for the current place, and
     the first action of the day
   - Place name and all sweep sightings are written into the spatial map; the
     first action executes immediately
5. **Tick loop**: capture -> visual-diff gate (skip if scene unchanged) -> vision
   model perceives -> decision model picks one action -> action executes ->
   memory + spatial map updated. Base tick sleep starts only after processing,
   so ticks never pile up.

---

## MCP controls (driving from Claude Code instead)

Requires `/mcp` reconnect after **any** Python change; C++ plugin changes need an
Unreal recompile instead.

| What | Tool |
| --- | --- |
| Start simulation | `start_simulation` — `tick_seconds` (default 1), `active_agents` (e.g. `["maren"]`, omit for all), `mode` (`live` / `explore`) |
| Stop | `stop_simulation` |
| Pause / resume | `pause_simulation` / `resume_simulation` |
| Status | `get_simulation_status` |
| Agents | `list_agents`, `inspect_agent` |
| Reset to run-start | `reset_agents` — teleports each agent back to its recorded start transform, reseeds memories, wipes spatial maps. **PIE must be running.** |
| Change a goal mid-run | `set_agent_goal` |
| Rebind after level/actor changes | `resync_simulation` |

Never parallelize Unreal MCP calls — the bridge is a single socket; concurrent
calls time out.

---

## Movement vocabulary

- `walk_to target_actor=<label>` — walk to a known character
- `walk_to direction=forward|forward-left|forward-right|left|right|back` —
  one ~15 m step relative to current facing ("forward" = the perceived view)
- `wander` — one step forward (purposeful continue, not random)

## After a run — what to read, in order

Everything below lives under `Python/worlds/<level>/` (`<level>` = `MCP_World`).
Runs are identified by an **`SR<n>`** tag; filter by it to isolate one run.

**Note there is no single "the log file".** `sim_runner` logs to its console
window only. `Python/unreal_mcp.log` exists but is written by the **MCP server
path**, not the standalone app — if you ran `start_sim.bat`, that file is stale
and does not describe your run. Ignore it.

### 1. `logs/agent_decisions.log` — the primary record

One JSON object per line, each carrying `sim_run`, the agent, the chosen action,
and the outcome. This is what the cockpit feed tails and what `/replay` joins
against. Start here for "what did they actually do".

```
cd Python\worlds\MCP_World\logs
findstr "SR29" agent_decisions.log          # everything from run 29
findstr /C:"\"agent_id\": \"dufus\"" agent_decisions.log
```

Survives across runs — it is only truncated by **Clear feed**.

### 2. `logs/world_events.log` — world-level events

Same directory, sibling to the decision log.

### 3. Per-agent state — `agents/<id>/`

Read these as *end-of-run state*, not history — most are overwritten each tick.

| File | What it tells you |
| --- | --- |
| `memory.json` | The rolling ~30-item memory window — the fastest read on whether an APC is repeating itself |
| `episodes.jsonl` | Append-only event history: where, who was seen, action, outcome. The one durable per-agent record |
| `social.json` | Who they've recognized. **Absent = they never identified anyone** |
| `spatial_map.json` | Grid cells visited + accumulated place labels |
| `last_perception.json` | The most recent vision result — check here when sightings look wrong |
| `runtime.json` | Live runtime state (interrupts, survey progress, agenda) |
| `state.json` | Binding, tier, `survey_priority`, start transform |

### 4. `agents/<id>/observations/*.png` — what they saw

Named `SR<n>_observation_<YYYYMMDD_HHMMSS>[_<tag>].png`; `_wake_<direction>` are
the 5 spool-up sweep views. Filter by the `SR` prefix for one run. `/replay`
scrubs these tick-by-tick joined to the decision log — usually easier than
opening PNGs by hand.

### Config, for reference

`world.json` (world clock), `world_grid.json` (grid bounds),
`world_places.db` (shared place/landmark DB).

## Offline tests (no Unreal, no API keys)

```
cd Python
.venv\Scripts\python.exe scripts\run_tests.py          # full suite
.venv\Scripts\python.exe scripts\agent_runtime\test_spool_up.py   # one file
```

---

## Level fixes (Unreal editor)

### Vehicles don't block the navmesh, so NPCs wedge against them

World vehicles are loose **`SkeletalMeshActor`** instances named `veh_*`
(`veh_Van_*`, `veh_VegetableTruck*`). Skeletal meshes do **not** carve the Recast
navmesh (their collision is a PhysicsAsset, which the nav build ignores), so NPCs
path straight into them and get stuck. Editing the collision preset on the actors
does nothing for navigation — you must add an explicit nav modifier.

The software net for this already exists (stuck detection re-decides a wedged
agent), but the proper fix is to carve the navmesh. Run this in Unreal:
**Tools -> Execute Python Script** (or Output Log `Cmd: Python`):

```python
import unreal

# Half-extents of the carve box (cm). Vehicles ~5 m long -> ~260 x 120 x 120.
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
1. **Test on one** — set `PREFIX = "veh_van_2"`, run, press **`P`** to view the
   navmesh, confirm a hole under that van. Tune `EXTENT` if needed.
2. Run on all `veh_`, then **save the level** (instanced components persist on save).
3. **Navigation Mesh -> Runtime Generation = `Dynamic Modifiers Only`**,
   **Build -> Build Paths**, verify holes with **`P`**.

`NavArea_Null` (not `NavArea_Obstacle`) is deliberate — Null removes the cells so
AI routes around; Obstacle only raises cost. The MCP bridge can't run editor
Python, so this is a manual step.

---

## Troubleshooting

- **Cockpit says it can't reach the runner / Start does nothing** — the
  "Sim Engine (sim_runner)" console window isn't running, or something else
  grabbed port 8777. Re-run `start_sim.bat` (it clears both ports first).
- **"No agents could be bound"** — PIE not running, or actor names/labels in
  `state.json` don't match the level. Run `resync_simulation` or check labels.
- **Code changes not taking effect** — standalone: you didn't re-run
  `start_sim.bat`. Via MCP: you forgot the `/mcp` reconnect. (`.env` edits *do*
  apply immediately — it is re-read on every LLM call.)
- **Agents keep authored goals after wake** — the wake failed soft; check the
  log for `Wake-up failed` / `Wake-up produced no orientation`.
- **"your vision failed this tick" in prompts / perception errors in log** —
  vision key or quota problem; the sim keeps running blind on memories + map.
- **Sweep views all look identical** — actor rotation isn't reaching the
  capture camera; check that `command_character_teleport` rotation works for
  the character blueprint.
- **NPC wedged against a vehicle / not moving despite walking** — the vehicle
  isn't carved out of the navmesh. The live path detects this (logs
  `[id] stuck on an obstacle — re-deciding`) and re-prompts the agent to find
  another way; the permanent fix is the navmesh carveout above (Level fixes).
- **Wake-up LLM call failed: `'typing.Union' object has no attribute
  '__module__'`** — outdated `anthropic`/`httpcore` for Python 3.14. Fixed
  2026-06-11 (`anthropic>=0.109`). If it recurs:
  `uv pip install --python .venv\Scripts\python.exe -U httpcore httpx anthropic`
