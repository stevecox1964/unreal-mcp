<div align="center">

# Model Context Protocol for Unreal Engine
<span style="color: #555555">unreal-mcp</span>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-5.5%2B-orange)](https://www.unrealengine.com)
[![Python](https://img.shields.io/badge/Python-3.12%2B-yellow)](https://www.python.org)
[![Status](https://img.shields.io/badge/Status-Experimental-red)](https://github.com/chongdashu/unreal-mcp)

**Fork of [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)**

</div>

> This is a fork of [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp). Original work by [@chongdashu](https://www.x.com/chongdashu). This fork extends the base project with additional features — see [Changes from Upstream](#changes-from-upstream) below.

This project enables AI assistant clients like Cursor, Windsurf and Claude Desktop to control Unreal Engine through natural language using the Model Context Protocol (MCP).

## ⚠️ Experimental Status

This project is currently in an **EXPERIMENTAL** state. The API, functionality, and implementation details are subject to significant changes. While we encourage testing and feedback, please be aware that:

- Breaking changes may occur without notice
- Features may be incomplete or unstable
- Documentation may be outdated or missing
- Production use is not recommended at this time

## 🌟 Overview

The Unreal MCP integration provides comprehensive tools for controlling Unreal Engine through natural language:

| Category | Capabilities |
|----------|-------------|
| **Actor Management** | • Create and delete actors (cubes, spheres, lights, cameras, etc.)<br>• Set actor transforms (position, rotation, scale)<br>• Query actor properties and find actors by name<br>• List all actors in the current level |
| **Blueprint Development** | • Create new Blueprint classes with custom components<br>• Add and configure components (mesh, camera, light, etc.)<br>• Set component properties and physics settings<br>• Compile Blueprints and spawn Blueprint actors<br>• Create input mappings for player controls |
| **Blueprint Node Graph** | • Add event nodes (BeginPlay, Tick, etc.)<br>• Create function call nodes and connect them<br>• Add variables with custom types and default values<br>• Create component and self references<br>• Find and manage nodes in the graph |
| **Editor Control** | • Focus viewport on specific actors or locations<br>• Control viewport camera orientation and distance |
| **Character Interaction** | • Send and receive messages to/from NPC characters<br>• Query character status, health, inventory, location, and current action<br>• Command characters to move, follow, stop, look at targets<br>• Pick up and drop items (socket attachment)<br>• Set AI state, play animations, trigger dialogue<br>• Per-character key-value memory store<br>• Scan for nearby actors within a radius |
| **Camera Capture** | • Trigger a `CameraCaptureActor` to take a scene snapshot during PIE<br>• Images saved as `<ActorName>_<YYYYMMDD>_<HHMMSS>.png` in the project folder<br>• Auto-discovers the first camera in the level if no name is specified<br>• AI assistants can read the image and analyze the scene |

All these capabilities are accessible through natural language commands via AI assistants, making it easy to automate and control Unreal Engine workflows.

## 🧩 Components

### Sample Project (MCPGameProject) `MCPGameProject`
- Based off the Blank Project, but with the UnrealMCP plugin added.

### Plugin (UnrealMCP) `MCPGameProject/Plugins/UnrealMCP`
- Native TCP server for MCP communication
- Integrates with Unreal Editor subsystems
- Implements actor manipulation tools
- Handles command execution and response handling

### Python MCP Server `Python/unreal_mcp_server.py`
- Implemented in `unreal_mcp_server.py`
- Manages TCP socket connections to the C++ plugin (port 55557)
- Handles command serialization and response parsing
- Provides error handling and connection management
- Loads and registers tool modules from the `tools` directory
- Uses the FastMCP library to implement the Model Context Protocol

## 📂 Directory Structure

- **MCPGameProject/** - Example Unreal project
  - **Plugins/UnrealMCP/** - C++ plugin source
    - **Source/UnrealMCP/** - Plugin source code
    - **UnrealMCP.uplugin** - Plugin definition

- **Python/** - Python server and tools
  - **tools/** - Tool modules for actor, editor, and blueprint operations
  - **scripts/** - Example scripts and demos

- **Docs/** - Comprehensive documentation
  - See [Docs/README.md](Docs/README.md) for documentation index

## 🚀 Quick Start Guide

### Startup Sequence

Every session, start things in this order:

1. **Run the Unreal project** — open and play the project in the editor. This starts the C++ TCP server (port 55557) that the Python server connects to.
2. **Run Claude Code** — launching Claude Code starts the Python MCP server (`unreal_mcp_server.py`) via the `.mcp.json` config, which then connects to Unreal.

> If Claude Code is started before Unreal, the Python server will fail to connect. Always start Unreal first.

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

### Configuring your MCP Client

Use the following JSON for your mcp configuration based on your MCP client.

```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "uv",
      "args": [
        "--directory",
        "<path/to/the/folder/PYTHON>",
        "run",
        "unreal_mcp_server.py"
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
A full NPC character command system built on a new `UMCPCharacterComponent`:
- **Messaging** — send messages to characters and read their replies
- **Memory** — per-character key-value fact store
- **Status queries** — health, inventory, location, AI state, current action, nearby actors
- **Action commands** — move to location/actor, follow, stop, look at, pickup, drop, say, play animation, set AI state
- **Blueprint events** — `OnMessageReceived`, `OnSayRequested`, `OnAIStateChanged`, `OnInteractRequested`

See [Docs/character_system.md](Docs/character_system.md) for full details.

### Camera Capture System
A `CameraCaptureActor` and MCP tool that lets AI assistants take and analyze in-game screenshots during PIE:
- **Scene snapshots** — triggers a `SceneCaptureComponent2D` render and saves a PNG to the project folder
- **Timestamped filenames** — each capture is saved as `<ActorName>_<YYYYMMDD>_<HHMMSS>.png`, so no captures are overwritten
- **Auto-discovery** — if no actor name is passed, the first `CameraCaptureActor` in the level is used
- **Image analysis** — AI clients can read the saved image and describe or reason about the scene

### AI RPG Agent Simulation (planned)
A full agentic NPC simulation layer driven by an LLM-controlled Agent Manager running inside the Python MCP server. See [`AI_RPG_Agent_Simulation_MASTER_PLAN.md`](AI_RPG_Agent_Simulation_MASTER_PLAN.md) for the complete design.
- **Agent Manager** — start/stop/pause an autonomous simulation loop from the CLI
- **Multi-tier agents** — Hero (full LLM), Simulated (event-driven LLM), and Lightweight (Behavior Tree) NPCs
- **World-state driven** — agents observe Unreal structured data; screenshots used selectively
- **Faction & director agents** — high-level agents that coordinate groups of NPCs
- **Validated action pipeline** — LLM decisions are schema-validated before any Unreal command executes

---

## 🎭 Character Interaction System

The plugin includes a full NPC character command system added on top of the base MCP tools.

### Quick setup per NPC
1. Add `UMCPCharacterComponent` to your NPC Blueprint
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

## 🤖 AI RPG Agent Simulation

> **Status: Planned** — See [`AI_RPG_Agent_Simulation_MASTER_PLAN.md`](AI_RPG_Agent_Simulation_MASTER_PLAN.md) for the full design document.

The next major feature is an agentic NPC simulation layer that lets an LLM (Claude, OpenAI, or a local model) autonomously drive NPCs inside a live Unreal session via the MCP server.

### Architecture

```
Claude / OpenAI CLI
        │  MCP tool calls
        ▼
Python MCP Server  ─── Agent Manager + Simulation Harness
        │              ├─ AgentRegistry / MemoryStore
        │              ├─ LLMRouter (per-agent model selection)
        │              └─ ActionValidator (schema + allowlist)
        │  Unreal commands
        ▼
Unreal C++ MCP Plugin → Unreal Editor / PIE
```

### Key MCP tools (planned)

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

### Agent tiers

| Tier | Examples | LLM usage |
|------|----------|-----------|
| 1 — Hero | Gondolf, main villain, quest giver | Full memory + goal reasoning every tick |
| 2 — Simulated | Innkeeper, blacksmith, guard captain | LLM only when near player or interrupted |
| 3 — Lightweight | Villagers, animals, basic guards | Behavior Tree; LLM only on promotion |

---

## License
MIT

## Questions

For questions, you can reach me on X/Twitter: [@chongdashu](https://www.x.com/chongdashu)