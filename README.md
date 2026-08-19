<div align="center">

# AI Agent Simulation
<span style="color: #555555">unreal-sim</span>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-5.5%2B-orange)](https://www.unrealengine.com)
[![Python](https://img.shields.io/badge/Python-3.12%2B-yellow)](https://www.python.org)
[![Status](https://img.shields.io/badge/Status-Experimental-red)](https://github.com/chongdashu/unreal-mcp)

**Fork of [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)**

</div>

> This is a fork of [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp). Original work by [@chongdashu](https://www.x.com/chongdashu). This fork extends the base project with additional features â€” see [Changes from Upstream](#changes-from-upstream) below.

This project is an **AI agent simulation** built in Unreal Engine: LLM-driven NPCs that perceive the world through their in-game cameras (a vision model), decide what to do (a decision LLM), remember what they have seen and who they have met, and navigate to named places — running live in PIE or as a standalone process. It began as a fork of an Unreal *MCP* (editor-authoring) project; that history still shows in parts of this README, but the focus is now the sim, not editor authoring (see the note under Overview).

## âš ï¸ Experimental Status

This project is currently in an **EXPERIMENTAL** state. The API, functionality, and implementation details are subject to significant changes. While we encourage testing and feedback, please be aware that:

- Breaking changes may occur without notice
- Features may be incomplete or unstable
- Documentation may be outdated or missing
- Production use is not recommended at this time

## ðŸŒŸ Overview

What the sim does each tick, per agent:

| Stage | What happens |
|-------|--------------|
| **Perceive** | Capture the agent's in-game camera frame; a vision model turns it into landmarks + characters + footing (what the agent is standing on) + a caption. |
| **Remember** | Sightings, places, and interactions are written to per-agent episodic + social memory and a shared spatial map. |
| **Decide** | A decision LLM picks the next action from the agent's allowed action set, grounded in what it sees and remembers, its authored agenda (`agenda.json`), and deterministic facts like footing and route progress. |
| **Act** | The action is schema-validated, then executed in Unreal (walk to a named place, speak to someone, observe, idle, ...). |

Decisions stream to `worlds/<level>/logs/agent_decisions.log` (completed decisions only) and
`worlds/<level>/logs/sim_runner.log` (every tick's outcome for every agent, including skips and
exclusions — truncated per run), plus the web cockpit's live feed.

> **Note (2026-06-28):** the **Python MCP editor-authoring tools were retired** (Actor Management,
> Blueprint Development, Blueprint Node Graph, Editor Control, Camera, Project). Epic now ships an
> official Unreal MCP for editor authoring, so maintaining ours wasn't worth it. The sim is driven by
> a **standalone runner + web cockpit** (no Claude/MCP required). The underlying C++ commands still
> exist in the plugin (reachable over the raw socket on `:55557`).
> The bridge currently lives in an editor-only module, so **Unreal must be running in PIE** to host
> the socket (making it a runtime module — for a packaged, editor-free build — is on the backlog).
>
> **Update (2026-07-08):** the Python MCP layer is now **fully retired** (backlog #22) — no MCP
> server, no `mcp.json`, no `mcp`/`fastmcp` dependency. The sim talks to Unreal over raw TCP via
> `agent_runtime/unreal_connection.py`, and anything driving the sim (web cockpit, Claude in dev
> mode, curl) uses the runner's localhost HTTP API.

## ðŸ§© Components

### Sample Project (MCPGameProject) `MCPGameProject`
- Based off the Blank Project, but with the unrealSIM plugin added.

### Plugin (UnrealMCP) `MCPGameProject/Plugins/UnrealMCP`
- Native TCP server for MCP communication
- Integrates with Unreal Editor subsystems
- Implements actor manipulation tools
- Handles command execution and response handling

### Python Runtime `Python/`
- Standalone — no Claude/MCP required to run the sim: `Python/start_sim.bat` or `python Python/sim_runner.py`
- `agent_runtime/unreal_connection.py` owns the raw TCP socket to the Unreal bridge plugin (port 55557)
- Handles command serialization, response parsing, and reconnection (Unreal closes the socket after each command)
- Loads `Python/.env` for LLM-backed NPC simulation settings

## ðŸ“‚ Directory Structure

- **MCPGameProject/** â€” Example Unreal project
  - **Plugins/UnrealMCP/** — C++ plugin source

- **Python/** â€” the standalone agent runtime (no MCP — retired 2026-07-08)
  - **agent_runtime/** â€” the cognitive loop: `agent_manager` (tick orchestration), `factory`
    (shared AgentManager construction), `llm_router`, `perception` (VLM), `memory_store`,
    `social_memory` + `episodic_memory` (per-agent memory), `place_db` + `world_grid` (shared
    spatial map), `cell_sweep` (maintenance-APC sweep), `config_store`, `unreal_bridge`
  - **scripts/** â€” offline test suite (`run_tests.py`) + the loop harness (`loop/preflight.py`)
  - **worlds/** â€” Level-scoped NPC data (one folder per Unreal level)
    - **`<LevelName>`/agents/`<agent_id>`/** â€” per-NPC config files
      - `state.json` â€” identity, binding, tier, `role` (`npc` | `maintenance`), goal, tick settings
      - `character.md` â€” role, personality, backstory
      - `goals.md` â€” long-term and current goals
      - `rules.md` â€” decision constraints
      - `tools.json` â€” allowed action list
      - `memory.json` / `social.json` / `episodes.jsonl` â€” accumulated runtime memory (git-ignored)
    - **`<LevelName>`/`world_places.db`** â€” shared spatial map (place cells + landmarks; git-ignored)
    - **`<LevelName>`/logs/** â€” per-world decision logs (runtime, git-ignored)
  - **web_ui/** â€” the web cockpit (FastAPI + Jinja2): the `/sim` controller (start/stop/step + live
    decision feed), the `/providers` page (provider-profile CRUD), and the `/settings` page
  - `sim_runner.py` â€” standalone sim engine (control API on `:8777`)
  - `start_sim.bat` â€” launches the sim engine + web cockpit (NPC scaffolding now lives in the `/create-npc` skill, not a web builder)

- **Docs/** â€” Comprehensive documentation
  - See [Docs/README.md](Docs/README.md) for documentation index

## ðŸš€ Quick Start Guide

### Running the sim (standalone — no Claude/MCP)

This is the primary path. Start things in this order:

1. **Run the Unreal project in PIE** — open the project and press **Play**. This starts the C++ TCP server (`:55557`) the sim talks to. **Run exactly one editor instance**: only one process can own `:55557`, so a second editor leaves the sim driving a window you aren't watching.
2. **Start the sim engine + web cockpit** — run `Python/start_sim.bat` (the repo's one batch file). It launches:
   - the **sim engine** (`sim_runner.py`) on `http://127.0.0.1:8777` — owns the agent loop and the single Unreal socket, exposing a localhost JSON control API (`/status`, `/start`, `/stop`, `/tick`, `/events`).
   - the **web cockpit** on `http://127.0.0.1:8765/sim` — start/stop/step the sim and watch the live decision feed. **The cockpit page opens itself in your browser** once the server is listening.

### Authoring places — Landmarks (setup phase, in the editor)

Ground-truth places are authored by dropping a marker actor in the level and setting its **actor
label** to `Landmark_<owner>_<place name with underscores>`:

```
Landmark_maren_vegetable_truck   -> maren's "vegetable truck"
Landmark_dufus_home              -> dufus's "home"
Landmark_community_town_square   -> shared "town square"
```

Any actor class works (a dedicated `Landmark_BP` marker, or rename a real prop to pin the place to
it). Owner is case-insensitive; the sim scans landmarks at start, and `/map` → **Sync world**
rescans after you move things — the tip line lists exactly which landmarks applied and flags
near-miss labels (`Landmarlk_...`) as spelling suspects. Landmarks win over `places.json` on
collision; moving the actor moves the place.

Because the engine is a plain JSON HTTP API, you can also drive it directly with curl:

```bash
curl http://127.0.0.1:8777/status
curl -X POST http://127.0.0.1:8777/start -d '{"tick_seconds":2}'
curl http://127.0.0.1:8777/events?limit=20
curl -X POST http://127.0.0.1:8777/stop
```

### Dev mode (Claude Code operating the sim)

When Claude Code is running it can start/stop the sim and help read logs + debug — it drives the
same runner HTTP API as the cockpit (`http://127.0.0.1:8777`). The MCP path was retired 2026-07-08
(#22). Always start Unreal in PIE first — without it the bridge socket isn't hosted.

For LLM key/model changes, a process restart is not needed: the simulation layer reloads
`Python/.env` before LLM decisions.

### Prerequisites
- Unreal Engine 5.5+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (used by `start_sim.bat` to run the Python side)

> **Python setup:** Uninstall any existing Python versions before proceeding. Then install Python 3.12+ fresh from [python.org](https://www.python.org/downloads/). Multiple Python versions can cause environment conflicts.

### Sample project

For getting started quickly, feel free to use the starter project in `MCPGameProject`. This is a UE 5.5 Blank Starter Project with the `UnrealMCP.uplugin` already configured. 

1. **Prepare the project**
   - Right-click your .uproject file
   - Generate Visual Studio project files
2. **Build the project (including the plugin)**
   - Open solution (`.sln`)
   - Choose `Development Editor` as your target.
   - Build

### Plugin
Otherwise, if you want to use the plugin in your existing project:

1. **Copy the plugin to your project**
   - Copy `MCPGameProject/Plugins/UnrealMCP` to your project's Plugins folder

2. **Enable the plugin**
   - Edit > Plugins
   - Find "UnrealMCP" in Editor category
   - Enable the plugin
   - Restart editor when prompted

3. **Build the plugin**
   - Right-click your .uproject file
   - Generate Visual Studio project files
   - Open solution (`.sln)
   - Build with your target platform and output settings

### Python Setup

See [Python/README.md](Python/README.md) for detailed Python setup instructions.

### LLM configuration for NPC simulation

The agent runtime uses two models, configured independently in `Python/.env`
(git-ignored): a **decision LLM** (chooses what each NPC does) and a **vision
model** (turns each screenshot into landmarks/characters). Each can be a cloud
provider **or** a local [Ollama](https://ollama.com) model.

#### Cloud (Haiku for both decisions and vision)

Haiku 4.5 is multimodal, so one provider and one key cover **both** roles — this is the simplest
cloud setup and the current default:

```dotenv
LLM_PROVIDER=anthropic            # decisions: anthropic | openai | ollama
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

VISION_PROVIDER=anthropic         # observations: anthropic | gemini | ollama
ANTHROPIC_VISION_MODEL=claude-haiku-4-5-20251001
```

Gemini stays selectable for vision (`VISION_PROVIDER=gemini`, `GEMINI_API_KEY`,
`GEMINI_MODEL=gemini-2.5-flash-lite`) if you prefer it. For OpenAI decisions instead, set
`LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL`.
The OpenAI path uses the Responses HTTP API directly through `requests` instead
of the OpenAI Python SDK, avoiding a Python 3.14 compatibility issue in the
SDK/Pydantic stack while keeping runtime behavior the same.

#### Fully local (Ollama)

Run both the decision LLM and vision on a local Ollama model — no API keys, no
cloud calls. A single **multimodal** model (e.g. `qwen3.5:4b`, which is both
vision- and tool-capable) can serve both roles:

```dotenv
LLM_PROVIDER=ollama
VISION_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b           # decision LLM
VISION_MODEL=qwen3.5:4b           # observations — must be a vision-capable model
```

Prerequisites: Ollama running locally with the model pulled
(`ollama pull qwen3.5:4b`). The adapter (`Python/agent_runtime/ollama_adapter.py`)
talks to Ollama's native `/api/chat`, disables "thinking", and forces JSON
output. The first call is slow while the model loads into VRAM — a
`qwen3.5:4b: model LOADED in Xs` line appears on the PIE overlay — and warm calls
are much faster. Switch back to cloud at any time by setting
`LLM_PROVIDER` / `VISION_PROVIDER` to their cloud values.

Settings are re-read from `.env` before each batch of LLM calls.

The sim runs standalone — no MCP client configuration needed. Start it with
`Python/start_sim.bat` or `python Python/sim_runner.py`; it talks to Unreal over
raw TCP on port 55557 via `agent_runtime/unreal_connection.py`.


## Changes from Upstream

This fork adds the following on top of [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp):

### Character Interaction System
A full NPC character command system built on a new `UAPCCharacterComponent`:
- **Messaging** â€” send messages to characters and read their replies
- **Memory** â€” per-character key-value fact store
- **Status queries** â€” health, inventory, location, AI state, current action, nearby actors
- **Action commands** â€” move to location/actor, follow, stop, look at, pickup, drop, say, play animation, set AI state
- **Blueprint events** â€” `OnMessageReceived`, `OnSayRequested`, `OnAIStateChanged`, `OnInteractRequested`

See [Docs/character_system.md](Docs/character_system.md) for full details.

### Camera Capture System
A `CameraCaptureActor` and MCP tool that lets AI assistants take and analyze in-game screenshots during PIE:
- **Scene snapshots** â€” triggers a `SceneCaptureComponent2D` render and saves a PNG to the project folder
- **Timestamped filenames** â€” each capture is saved as `<ActorName>_<YYYYMMDD>_<HHMMSS>.png`, so no captures are overwritten
- **Auto-discovery** â€” if no actor name is passed, the first `CameraCaptureActor` in the level is used
- **Image analysis** â€” AI clients can read the saved image and describe or reason about the scene

### AI RPG Agent Simulation
A first-pass agentic NPC simulation layer driven by an LLM-controlled Agent Manager running inside the Python MCP server. See [`MASTER_PLAN.md`](MASTER_PLAN.md) for the complete design.
- **Agent Manager** â€” start/stop/pause an autonomous simulation loop from the CLI
- **Live agent binding** â€” active agents bind to named Unreal actors or spawn from configured Blueprint classes
- **Multi-tier agents** â€” Hero (full LLM), Simulated (event-driven LLM), and Lightweight (no LLM unless explicitly configured)
- **World-state driven** â€” agents observe Unreal structured data; screenshots used selectively
- **Validated action pipeline** â€” LLM decisions are schema-validated before any Unreal command executes
- **Level-aware loading** â€” agents live under `Python/worlds/<LevelName>/agents/` and are loaded automatically based on the currently open Unreal level; no config field needed
- **Web cockpit** â€” local FastAPI app (`Python/web_ui/`): drive the sim (`/sim` — start/stop/step + live decision feed), manage provider profiles (`/providers`), and edit config (`/settings`). Launch with `start_sim.bat` (alongside the sim engine). NPC scaffolding moved to the `/create-npc` skill; the legacy `npc_builder` app was removed 2026-06-28.
- **Explore mode** â€” a second simulation mode (`start_simulation(mode="explore")`) where the avatar autonomously maps an unknown world by walking it: a VLM (Gemini or a local Ollama model) turns each camera frame into semantic landmarks, a deterministic frontier explorer chooses where to walk next, and a per-agent engine-agnostic grid/place map is written to `spatial_map.json`. No LLM in the movement loop. See [Explore Mode](#-explore-mode-vlm-spatial-mapping) below.
- **Local model support (Ollama)** â€” run both the decision LLM and vision perception fully locally on an Ollama model (e.g. the multimodal `qwen3.5:4b`) with no cloud API keys. Decision and vision providers are selected independently in `Python/.env`. See [LLM configuration for NPC simulation](#llm-configuration-for-npc-simulation).

### Spatial knowledge, memory & navigation

A cognitive layer the agents build and share as they run (verified live in PIE, 2026-06-26):

- **Landmarks (authored ground truth, 2026-07-08)** â€” drop a `Landmark_<owner>_<name>`-labeled
  actor in the level and the sim treats it as an authored place: scanned at sim start and by the
  `/map` **Sync world** button (which reports exactly what applied and flags near-miss labels).
  The level is the single source of truth — moving the actor moves the place.
- **Named-place navigation** â€” `walk_to "<place name>"` resolves a place name â†’ grid cell â†’ world location (`PlaceDB.find_named_cell` + `WorldGrid.cell_center`), so an agent navigates to a stated destination instead of idling. Unknown names fall back gracefully.
- **Shared world map (place cells)** â€” a SQLite `world_places.db` of named grid cells + compass-indexed landmark observations, **shared across all agents** (one agent's discoveries steer the others). `known_places` surfaces the named-place map (bearing + distance, nearest first) to each agent so it can pick a destination by name.
- **Episodic + social memory (per agent)** â€” `episodes.jsonl` records structured per-tick events `{world_time, grid_cell, place, saw[], action, outcome}`; `social.json` tracks acquaintances `{first_met, last_seen, meet_count, sentiment}` from perceived characters and speech. Recall blends recency + spatial proximity + social ties â€” beating the flat 30-item `memory.json` window for long/overnight runs.
- **Deterministic identity recognition (#44)** â€” the vision model labels every figure "unknown person"; `agent_runtime/recognition.py` reconciles that against engine-known positions (geometry, not a model guess) so an APC recognizes another APC it has already met instead of every encounter reading as a first meeting.
- **Authored agendas + daily ledger (#36)** â€” `agenda.json` per agent is stable, user-authored schedule input (tasks, places, completion policy); `agent_runtime/agenda.py` derives runtime task state and a chronological ledger from it deterministically each tick, separate from the authored file.
- **Behavioral guardrail facts, not code-side blocking** â€” when an agent does something a simple rule should have prevented (wandering off-path, drifting farther from a destination), the fix is a louder deterministic fact in the decision prompt (`FOOTING: <surface>`, `PROGRESS WARNING`) plus an explicit line in `rules.md`, not a validator that blocks the action. Judgment stays with the LLM; code's job is making the relevant fact impossible to miss.
- **Maintenance/monitor APC** â€” an optional system-worker role (`"role": "maintenance"` in `state.json`) with **no personality or LLM** that sweeps unexplored grid cells (walk to cell center â†’ 360 observe â†’ drop a *community breadcrumb*) so the personality NPCs skip the costly re-sweep. *Decision + navigation logic is complete and tested; the live 360 rotation+capture in Unreal is pending.*
- **Perception-guided exploration (#77/#78/#26, verified live SR43-SR45 2026-08-19)** — the APC's own eyes
  outrank the navmesh. Perception reports `ground_ahead` (footing the APC would stand on a few steps out)
  and `path_ahead` (`open|dead_end|blocked`); an eyes cache files those per compass word while the APC
  stays on the spot, so a direction line reads "your own eyes saw: grass ahead, the way ahead DEAD-ENDS".
  Refusal is two-scale: `refuse_cell` blocks a whole 30 m cell (corn field, water), `scope: "spot"` writes a
  9 m **no-go patch** (`no_go_patches`) that poisons one bad yard while the cell stays a survey target.
  Two consecutive opposite-heading legs count a **bounce**, stated as a fact once it repeats. All facts,
  no blockers — nothing in code stops a step onto refused ground; the prompt and the map state the record.
  A cell, once surveyed, is never re-offered (`SURVEY_STALE_REFRESH = False`).
- **Perception dataset recorder (#79)** — every perceived frame is written as a training pair the moment it
  is perceived: one JSON line per image to `agents/<id>/observations/perception_log.jsonl` (caption,
  landmarks, footing, `ground_ahead`, `path_ahead`, heading, cell, model, `sim_run`, and `error` when
  perception fails — recorded, not hidden). Wired into all four perceive sites (tick, wake sweep, survey
  sweep, legacy explore). Before this only the ~21 survey composites kept their text while the per-tick
  stream threw its labels away. Dataset packaging/dedup/splits are a build-time job over the JSONL.
- **Refused ground on `/map` (#80)** — refused cells paint a red diagonal hatch over whatever survey state
  they also carry, no-go patches draw as dashed red circles at their true radius, and both tooltips lead
  with `REFUSED by <who>: <reason> (<world time>)`. Read-only: withdrawing a refusal stays the APC's own
  `allow_cell` act, never a map click.
- **`.env` config store** â€” `agent_runtime/config_store.py` reads/writes provider/model settings with secrets shown set/unset only (backs a future settings UI; no hand-editing `.env`).

### Standalone runner & web cockpit

- **Standalone sim runner** (`Python/sim_runner.py`) â€” runs the simulation in its **own process,
  independent of Claude/MCP** (the "runs overnight without Claude open" host). It owns the
  AgentManager and the single Unreal socket, and exposes a localhost HTTP control surface
  (`/status`, `/start`, `/stop`, `/tick`); MCP tools and the web UI can *attach* via
  `agent_runtime.runner_client.RunnerClient` instead of hosting the manager themselves. Run it with
  `python sim_runner.py --port 8777` (Unreal in PIE). The control API + client are offline-tested.
- **Sim cockpit** (`/sim` in the web app) â€” drive the running sim from the browser: status panel,
  Start/Stop, single-tick **Step** (debugging), and a live decision-log feed (poll-based, with a
  **Clear feed** button + per-event local timestamps). Proxies to the sim engine via `RunnerClient`.
- **Provider profiles** (`/providers` in the web app) â€” create/edit/delete named `{provider, model}`
  profiles and assign them to the **decision** and **vision** roles. Profiles live in a `config.json`
  and are **compiled down to the plain `.env` keys** the runtime already reads (`agent_runtime/provider_profiles.py`),
  so `llm_router`/`perception` are untouched and the sim picks up changes without a restart. No secrets
  in profiles â€” keys stay in `.env`.
- **Web settings page** (`/settings` in the web app) â€” manage provider/model config (the Ollama vs
  cloud switch, models) through the UI instead of hand-editing `.env`. Secret keys show only
  whether they are *set*; a blank secret field is left untouched. Backed by `agent_runtime/config_store.py`.

### Offline test suite

The agent-runtime logic is covered by offline tests that stub Unreal entirely (no editor, no network, no LLM call) â€” the loop-safe surface for automated/unattended development:

```bash
cd Python
.venv/Scripts/python.exe scripts/run_tests.py            # one PASS/FAIL across the suite
.venv/Scripts/python.exe scripts/run_tests.py --only test_place_resolver   # a single test
```

The socket-based `scripts/{actors,node,blueprints}` scripts are integration demos that need a live editor and are excluded from this suite.

---

## ðŸŽ­ Character Interaction System

The plugin includes a full NPC character command system. The C++ side — the `UAPCCharacterComponent`,
its Blueprint events, and the `command_character_*` / `get_character_*` commands — is live and is how
the sim drives NPCs (the runtime reaches it over the raw socket via `UnrealBridge`).

> **Note (2026-06-28):** the Python examples below were the **retired** MCP wrapper tools
> (`character_tools.py`, removed with the other editor-authoring tools — see the Overview note). They
> are kept here to show the **command shapes**; the commands themselves still exist in C++ over the
> socket on `:55557`, but they are no longer exposed as Python MCP tools.

### Quick setup per NPC
1. Add `UAPCCharacterComponent` to your NPC Blueprint
2. Assign an AI Controller (required for move/follow/stop)
3. Implement the Blueprint events you want: `OnMessageReceived`, `OnSayRequested`, `OnAIStateChanged`, `OnInteractRequested`

### Example
```python
# Send a message to an NPC
send_character_message("GuardNPC", "The player was spotted near the north gate")

# Command the NPC to walk somewhere
command_character_move_to("GuardNPC", location=[1000, 500, 0])

# Make the NPC pick up a weapon
command_character_pickup("GuardNPC", "Sword_01")

# Make the NPC say something (fires OnSayRequested in Blueprint)
command_character_say("GuardNPC", "Halt! Who goes there?")

# Read replies the NPC has queued in their outbox
get_character_messages("GuardNPC", source="outbox", clear=True)
```

See [Docs/character_system.md](Docs/character_system.md) for the full command reference, component property list, and setup checklist.

---

## ðŸ¤– AI RPG Agent Simulation

> **Status: Prototype** â€” See [`MASTER_PLAN.md`](MASTER_PLAN.md) for the full design. The live task list is [`plan/backlog.md`](plan/backlog.md).

The simulation layer lets an LLM (Claude, OpenAI, or a local model) autonomously drive NPCs inside a live Unreal session.

### Architecture

```
Web cockpit / curl / Claude (dev mode)
        â”‚  localhost HTTP (:8777)
        â–¼
sim_runner.py  â”€â”€â”€ Agent Manager + Simulation Harness
        â”‚              â”œâ”€ AgentRegistry / MemoryStore
        â”‚              â”œâ”€ LLMRouter (per-agent model selection)
        â”‚              â””â”€ ActionValidator (schema + allowlist)
        â”‚  Unreal commands (raw TCP :55557)
        â–¼
Unreal C++ plugin (UnrealMCP) â†’ Unreal Editor / PIE
```

### Sim control surface (runner HTTP API on `:8777`)

| Endpoint | Description |
|------|-------------|
| `POST /start` | Start the autonomous agent loop (`tick_seconds`, `active_agents`, `mode`) |
| `POST /stop` | Stop the loop |
| `POST /pause` / `POST /resume` | Pause or resume without losing state |
| `GET /status` | Live status of the running sim |
| `GET /agents` | Browse active agents |
| `POST /tick` | Manually pulse the loop (single step) |
| `GET /events` | Tail the world event log |
| `POST /reset_day` | Restart the sim day from morning (memories kept) |

### Smoke test

With Unreal running in PIE and the runner up (`start_sim.bat`):

```bash
curl -X POST http://127.0.0.1:8777/start -d '{"tick_seconds":10,"active_agents":["dufus"]}'
curl http://127.0.0.1:8777/events?limit=10
curl -X POST http://127.0.0.1:8777/stop
```

Expected: Dufus binds to his actor in MCP_World; each tick the agent captures a camera PNG internally (via `UnrealBridge`), and the LLM decision loop returns a validated action visible in `/events` and the cockpit feed. Generated captures and decision logs are ignored by git.

### Agent tiers

| Tier | Examples | LLM usage |
|------|----------|-----------|
| 1 â€” Hero | Main villain, quest giver, lead NPC | Full memory + goal reasoning every tick |
| 2 â€” Simulated | Dufus, innkeeper, guard captain | LLM on every tick at normal cadence |
| 3 â€” Lightweight | Villagers, animals, basic guards | Behavior Tree; LLM only on promotion |

---

## ðŸ§­ Explore Mode (VLM spatial mapping)

> **Status: Working in PIE** â€” verified end-to-end 2026-06-07 (an avatar walked the town's west edge and built a labeled map).

A second simulation mode where the avatar **discovers a world by looking at it and walking it**, rather than acting on pre-authored knowledge. The thesis: distil Unreal's thousands of engine actors into an *engine-agnostic* representation â€” metric coordinates + vision-derived semantic labels + a nav graph â€” so the same pipeline would drive a real robot with a camera.

### The tick (deterministic routing; the model only perceives)

```
observe (own pose + camera frame)
  â†’ perceptual-hash diff-gate (skip re-labelling an unchanged view)
  â†’ VLM.perceive()              # frame â†’ {landmarks, characters, caption}  (Gemini or local Ollama)
  â†’ SpatialMap.ingest()          # write labels into the current grid cell
  â†’ explorer.next_target()       # pick nearest unexplored frontier  (CODE, not LLM)
  â†’ command_character_move_to()  # walk there
```

The VLM is used **only** for perception (turning pixels into labels). Movement is a deterministic frontier sweep â€” cheap, predictable coverage, no LLM in the control loop.

### The map (`worlds/<level>/agents/<id>/spatial_map.json`)

Per-agent (egocentric). Grid cells keyed `"gx,gy"` (`floor(x / cell_size)`, default 400 cm), each holding the landmark tags seen from that cell (with confidence/distance/bearing) and the `edges` traversed to neighbors. Place coordinates are derived on demand from the labels â€” nothing Unreal-specific is stored.

### Requirements (learned the hard way)

- **PIE must be running** â€” the AIController only possesses the avatar in Play.
- **Walkable NavMesh under the avatar** â€” a `NavMeshBoundsVolume` that is *tall enough* (its Z extent must clear the floor by more than the agent height; a too-thin volume builds no navmesh and the avatar silently won't move). The avatar must be **standing on green** (on the mesh), not on grass/dirt or floating.
- **A vision model** in `Python/.env` â€” either Gemini (`VISION_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash-lite`) or a local Ollama vision model (`VISION_PROVIDER=ollama`, `OLLAMA_HOST`, `VISION_MODEL=qwen3.5:4b`). See [LLM configuration](#llm-configuration-for-npc-simulation).
- **Pillow** installed (enables the diff-gate; without it every frame is re-perceived).

### Smoke test

```bash
curl -X POST http://127.0.0.1:8777/start -d '{"tick_seconds":10,"active_agents":["maren"],"mode":"explore"}'
curl -X POST http://127.0.0.1:8777/tick      # observe -> perceive -> map -> pick frontier -> walk
curl -X POST http://127.0.0.1:8777/stop
```

Expected: each tick the agent's `cells_visited` climbs, `spatial_map.json` fills with landmark-tagged cells linked by nav edges, and the avatar walks frontier-to-frontier. Delete `spatial_map.json` to start a fresh map.

---

## License
MIT

## Questions

For questions, you can reach me on X/Twitter: [@TheDrizzelz2024](https://x.com/TheDrizzelz2024)
