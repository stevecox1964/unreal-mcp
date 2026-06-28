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
| **Perceive** | Capture the agent's in-game camera frame; a vision model turns it into landmarks + characters + a caption. |
| **Remember** | Sightings, places, and interactions are written to per-agent episodic + social memory and a shared spatial map. |
| **Decide** | A decision LLM picks the next action from the agent's allowed action set, grounded in what it sees and remembers. |
| **Act** | The action is schema-validated, then executed in Unreal (walk to a named place, speak to someone, observe, idle, ...). |

Decisions stream to `worlds/<level>/logs/agent_decisions.log` and to the web cockpit's live feed.

> **Note (2026-06-28):** the **Python MCP editor-authoring tools were retired** (Actor Management,
> Blueprint Development, Blueprint Node Graph, Editor Control, Camera, Project). Epic now ships an
> official Unreal MCP for editor authoring, so maintaining ours wasn't worth it. The sim is driven by
> a **standalone runner + web cockpit** (no Claude/MCP required). The underlying C++ commands still
> exist in the plugin (reachable over the raw socket on `:55557`), but the Python MCP server now
> exposes only the **simulation control surface** (`simulation_tools.py` — start/stop/inspect the loop).
> The bridge currently lives in an editor-only module, so **Unreal must be running in PIE** to host
> the socket (making it a runtime module — for a packaged, editor-free build — is on the backlog).

## ðŸ§© Components

### Sample Project (MCPGameProject) `MCPGameProject`
- Based off the Blank Project, but with the unrealSIM plugin added.

### Plugin (UnrealMCP) `MCPGameProject/Plugins/UnrealMCP`
- Native TCP server for MCP communication
- Integrates with Unreal Editor subsystems
- Implements actor manipulation tools
- Handles command execution and response handling

### Python MCP Server `Python/unreal_sim_server.py`
- Implemented in `unreal_sim_server.py`
- Manages TCP socket connections to the C++ plugin (port 55557)
- Handles command serialization and response parsing
- Provides error handling and connection management
- Loads and registers tool modules from the `tools` directory
- Uses the FastMCP library to implement the Model Context Protocol
- Loads `Python/.env` for LLM-backed NPC simulation settings

## ðŸ“‚ Directory Structure

- **MCPGameProject/** â€” Example Unreal project
  - **Plugins/UnrealMCP/** — C++ plugin source

- **Python/** â€” Python MCP server and agent runtime
  - **tools/** â€” MCP tool modules (`simulation_tools` — the sim control surface; editor-authoring
    tools retired 2026-06-28, see the Overview note)
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
2. **Start the sim engine + web cockpit** — run `Python/start_sim.bat`. It launches:
   - the **sim engine** (`sim_runner.py`) on `http://127.0.0.1:8777` — owns the agent loop and the single Unreal socket, exposing a localhost JSON control API (`/status`, `/start`, `/stop`, `/tick`, `/events`).
   - the **web cockpit** on `http://127.0.0.1:8765/sim` — start/stop/step the sim and watch the live decision feed (with a Clear-feed button + per-event timestamps).

Because the engine is a plain JSON HTTP API, you can also drive it directly with curl:

```bash
curl http://127.0.0.1:8777/status
curl -X POST http://127.0.0.1:8777/start -d '{"tick_seconds":2}'
curl http://127.0.0.1:8777/events?limit=20
curl -X POST http://127.0.0.1:8777/stop
```

### Dev mode (Claude Code operating the sim)

When Claude Code is running it can start/stop the sim and help read logs + debug. Historically Claude
reached Unreal through the Python MCP server (`unreal_sim_server.py`, launched via `.mcp.json`); that
path still works for the **simulation control surface**, but the standalone runner above is the
direction of travel. Always start Unreal in PIE first — without it the bridge socket isn't hosted.

### Restarting the MCP server without rebooting

The MCP server runs over stdio, so the MCP client owns the live child process. If the transport gets stale, use the repo-root helper:

```powershell
.\restart_unreal_sim_server.bat
```

Then reload or reconnect the `unrealSIM` server in your MCP client. This stops only this repo's `unreal_sim_server.py` processes; it does not restart Unreal or Windows.

For LLM key/model changes, a process restart should not be needed after the latest changes. The simulation layer reloads `Python/.env` before LLM decisions, and the MCP tool `reload_llm_environment()` can be used to reload and inspect masked LLM settings.

### Prerequisites
- Unreal Engine 5.5+
- Python 3.12+
- MCP Client (e.g., Claude Desktop, Cursor, Windsurf)

> **Python setup:** Uninstall any existing Python versions before proceeding. Then install Python 3.12+ fresh from [python.org](https://www.python.org/downloads/). Having multiple Python versions can cause conflicts with the MCP server.

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

### Python Server Setup

See [Python/README.md](Python/README.md) for detailed Python setup instructions, including:
- Setting up your Python environment
- Running the MCP server
- Using direct or server-based connections

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

Settings are re-read from `.env` before each batch of LLM calls; the
`reload_llm_environment()` MCP tool reloads and reports them with secrets masked.

### Configuring your MCP Client

Use the following JSON for your mcp configuration based on your MCP client.

```json
{
  "mcpServers": {
    "unrealSIM": {
      "command": "uv",
      "args": [
        "--directory",
        "<path/to/the/folder/PYTHON>",
        "run",
        "unreal_sim_server.py"
      ]
    }
  }
}
```

An example is found in `mcp.json`

### MCP Configuration Locations

Depending on which MCP client you're using, the configuration file location will differ:

| MCP Client | Configuration File Location | Notes |
|------------|------------------------------|-------|
| Claude Desktop | `~/.config/claude-desktop/mcp.json` | On Windows: `%USERPROFILE%\.config\claude-desktop\mcp.json` |
| Cursor | `.cursor/mcp.json` | Located in your project root directory |
| Windsurf | `~/.config/windsurf/mcp.json` | On Windows: `%USERPROFILE%\.config\windsurf\mcp.json` |

Each client uses the same JSON format as shown in the example above. 
Simply place the configuration in the appropriate location for your MCP client.


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
A first-pass agentic NPC simulation layer driven by an LLM-controlled Agent Manager running inside the Python MCP server. See [`AI_RPG_Agent_Simulation_MASTER_PLAN.md`](AI_RPG_Agent_Simulation_MASTER_PLAN.md) for the complete design.
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

- **Named-place navigation** â€” `walk_to "<place name>"` resolves a place name â†’ grid cell â†’ world location (`PlaceDB.find_named_cell` + `WorldGrid.cell_center`), so an agent navigates to a stated destination instead of idling. Unknown names fall back gracefully.
- **Shared world map (place cells)** â€” a SQLite `world_places.db` of named grid cells + compass-indexed landmark observations, **shared across all agents** (one agent's discoveries steer the others). `known_places` surfaces the named-place map (bearing + distance, nearest first) to each agent so it can pick a destination by name.
- **Episodic + social memory (per agent)** â€” `episodes.jsonl` records structured per-tick events `{world_time, grid_cell, place, saw[], action, outcome}`; `social.json` tracks acquaintances `{first_met, last_seen, meet_count, sentiment}` from perceived characters and speech. Recall blends recency + spatial proximity + social ties â€” beating the flat 30-item `memory.json` window for long/overnight runs.
- **Maintenance/monitor APC** â€” an optional system-worker role (`"role": "maintenance"` in `state.json`) with **no personality or LLM** that sweeps unexplored grid cells (walk to cell center â†’ 360 observe â†’ drop a *community breadcrumb*) so the personality NPCs skip the costly re-sweep. *Decision + navigation logic is complete and tested; the live 360 rotation+capture in Unreal is pending.*
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

The plugin includes a full NPC character command system added on top of the base MCP tools.

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

> **Status: Prototype** â€” See [`AI_RPG_Agent_Simulation_MASTER_PLAN.md`](AI_RPG_Agent_Simulation_MASTER_PLAN.md) and [`still_todo.md`](still_todo.md) for the full design and current task list.

The simulation layer lets an LLM (Claude, OpenAI, or a local model) autonomously drive NPCs inside a live Unreal session via the MCP server.

### Architecture

```
Claude / OpenAI CLI
        â”‚  MCP tool calls
        â–¼
Python MCP Server  â”€â”€â”€ Agent Manager + Simulation Harness
        â”‚              â”œâ”€ AgentRegistry / MemoryStore
        â”‚              â”œâ”€ LLMRouter (per-agent model selection)
        â”‚              â””â”€ ActionValidator (schema + allowlist)
        â”‚  Unreal commands
        â–¼
Unreal C++ MCP Plugin â†’ Unreal Editor / PIE
```

### Key MCP tools

| Tool | Description |
|------|-------------|
| `start_simulation` | Start the autonomous agent loop |
| `stop_simulation` | Stop the loop |
| `pause_simulation` / `resume_simulation` | Pause or resume without losing state |
| `get_simulation_status` | Live status of the running sim |
| `list_agents` / `inspect_agent` | Browse active agents |
| `set_agent_goal` | Override an agent's current goal |
| `force_agent_tick` | Manually pulse a single agent |
| `get_recent_events` | Tail the world event log |
| `reload_llm_environment` | Reload `Python/.env` and report masked LLM settings |

### Smoke test

With Unreal running in PIE and `unrealSIM` connected:

```txt
reload_llm_environment()
start_simulation(tick_seconds=10, active_agents=["dufus"])
force_agent_tick("dufus")
get_recent_events(limit=10)
stop_simulation()
```

Expected: Dufus binds to the `BP_CameraNPC_C_1` actor in MCP_World; each tick the agent captures a camera PNG internally (via `UnrealBridge`, not a separate MCP tool), and the LLM decision loop returns a validated action logged in `get_recent_events`. Generated captures and decision logs are ignored by git.

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

```txt
start_simulation(tick_seconds=10, active_agents=["maren"], mode="explore")
force_agent_tick("maren")     # observe â†’ perceive â†’ map â†’ pick frontier â†’ walk
get_character_location("Maren")   # x/y should track toward the frontier cell centre
stop_simulation()
```

Expected: each tick the agent's `cells_visited` climbs, `spatial_map.json` fills with landmark-tagged cells linked by nav edges, and the avatar walks frontier-to-frontier. Delete `spatial_map.json` to start a fresh map.

---

## License
MIT

## Questions

For questions, you can reach me on X/Twitter: [@chongdashu](https://www.x.com/chongdashu)
