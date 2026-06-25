"""
Simulation control MCP tools.

Exposes start/stop/pause/resume/status/list/inspect/set_goal/force_tick
so the Claude/OpenAI CLI can act as the simulation director.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("AgentRuntime")


def register_simulation_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def reload_llm_environment() -> Dict[str, str]:
        """Reload Python/.env and report LLM settings with secrets masked.

        Example valid input:
            {}
        """
        env_path = Path(__file__).resolve().parents[1] / ".env"
        loaded = load_dotenv(env_path, override=True)
        keys = [
            "LLM_PROVIDER",
            "LLM_MODEL",
            "OPENAI_MODEL",
            "ANTHROPIC_MODEL",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
        ]
        result: Dict[str, str] = {"loaded": str(loaded), "env_path": str(env_path)}
        for key in keys:
            value = os.environ.get(key, "")
            if key.endswith("_API_KEY") and value:
                result[key] = f"<set length {len(value)}>"
            else:
                result[key] = value
        return result

    @mcp.tool()
    async def start_simulation(
        tick_seconds: int = 1,
        active_agents: List[str] = None,
        mode: str = "live",
    ) -> Dict[str, Any]:
        """Start the NPC agent simulation loop.

        The loop is self-pacing: tick_seconds is the BASE interval, and the sleep
        starts only after a tick's processing (Gemini observation + LLM thinking
        for all agents) completes. E.g. a 2 s observation with base 1 means ~3 s
        between ticks â€” ticks never pile up and over-drive the avatars.

        Args:
            tick_seconds: Base seconds added after each tick's processing. Default 1.
            active_agents: List of agent_ids to activate. Omit to load all agents.
            mode: "live" (default) = LLM-driven decisions; "explore" = deterministic
                frontier exploration that builds each agent's spatial_map.json from
                vision (Gemini) â€” no decision LLM, the avatar maps the world by walking it.

        Example valid input:
            {"tick_seconds": 1, "active_agents": ["dufus"], "mode": "explore"}
        """
        from unreal_sim_server import get_agent_manager
        mgr = get_agent_manager()
        return await mgr.start_simulation(
            tick_seconds=tick_seconds, active_agents=active_agents, mode=mode
        )

    @mcp.tool()
    async def stop_simulation() -> Dict[str, Any]:
        """Stop the running simulation loop.

        Example valid input:
            {}
        """
        from unreal_sim_server import get_agent_manager
        return await get_agent_manager().stop_simulation()

    @mcp.tool()
    async def pause_simulation() -> Dict[str, Any]:
        """Pause the simulation loop without stopping it.

        Example valid input:
            {}
        """
        from unreal_sim_server import get_agent_manager
        return await get_agent_manager().pause_simulation()

    @mcp.tool()
    async def resume_simulation() -> Dict[str, Any]:
        """Resume a paused simulation.

        Example valid input:
            {}
        """
        from unreal_sim_server import get_agent_manager
        return await get_agent_manager().resume_simulation()

    @mcp.tool()
    def get_simulation_status() -> Dict[str, Any]:
        """Get the current simulation state, tick rate, and all agent summaries.

        Example valid input:
            {}
        """
        from unreal_sim_server import get_agent_manager
        return get_agent_manager().get_status()

    @mcp.tool()
    def list_agents() -> Dict[str, Any]:
        """List all loaded agents with their Unreal binding, tier, goal, and active state.

        Example valid input:
            {}
        """
        from unreal_sim_server import get_agent_manager
        return {"agents": get_agent_manager().list_agents()}

    @mcp.tool()
    def inspect_agent(agent_id: str) -> Dict[str, Any]:
        """Get the full configuration and state for a specific agent.

        Args:
            agent_id: The agent identifier (matches folder name in Python/worlds/<level>/agents/)

        Example valid input:
            {"agent_id": "dufus"}
        """
        from unreal_sim_server import get_agent_manager
        return get_agent_manager().inspect_agent(agent_id)

    @mcp.tool()
    def set_agent_goal(agent_id: str, goal: str) -> Dict[str, Any]:
        """Override the current goal of a running agent.

        Args:
            agent_id: The agent to update
            goal: New goal string (e.g. 'follow_player', 'patrol_ruins')

        Example valid input:
            {"agent_id": "dufus", "goal": "greet the player"}
        """
        from unreal_sim_server import get_agent_manager
        return get_agent_manager().set_agent_goal(agent_id, goal)

    @mcp.tool()
    async def force_agent_tick(agent_id: str) -> Dict[str, Any]:
        """Immediately pulse one agent regardless of its cooldown timer.

        Args:
            agent_id: The agent to tick now

        Example valid input:
            {"agent_id": "dufus"}
        """
        from unreal_sim_server import get_agent_manager
        return await get_agent_manager().pulse_agent(agent_id)

    @mcp.tool()
    def get_recent_events(limit: int = 20) -> Dict[str, Any]:
        """Return the most recent agent decision log entries.

        Args:
            limit: Maximum number of entries to return (default 20)

        Example valid input:
            {"limit": 10}
        """
        from unreal_sim_server import get_agent_manager
        mgr = get_agent_manager()
        return {"events": mgr.memory.get_recent_events(limit)}

    @mcp.tool()
    async def reset_agents() -> Dict[str, Any]:
        """Reset agents to their run-start state so sim re-runs are reproducible.

        Stops the simulation if running, then for every agent: teleports it back
        to the start transform recorded at the first start_simulation, clears
        tick/speech timers, restores memory.json from memory.seed.json (or empties
        it), and deletes spatial_map.json. Run while PIE is active so the teleport
        hits the live game world. To re-capture a new start position, delete
        start_location/start_rotation from the agent's state.json first.

        Example valid input:
            {}
        """
        from unreal_sim_server import get_agent_manager
        return await get_agent_manager().reset_agents()

    @mcp.tool()
    async def reset_world_places() -> Dict[str, Any]:
        """Wipe the shared place-cell DB so the world map starts from scratch.

        Stops the simulation if running, then clears every row from the shared
        world_places.db: place_cells (named grid cells), place_observations
        (compass landmarks), and agent_visits (per-agent visit history). The
        tables and schema are kept; only the data is deleted. This is the
        geographic counterpart to reset_agents, which preserves the map for
        reproducible re-runs — use this when you want a truly blank world.
        Agent JSON state (memories, spatial maps) is left untouched.

        Example valid input:
            {}
        """
        from unreal_sim_server import get_agent_manager
        return await get_agent_manager().reset_world_places()

    @mcp.tool()
    def generate_world_grid(cell_size: float = 400.0, padding: float = 800.0) -> Dict[str, Any]:
        """Compute the fixed world grid from the current level's actor positions.

        Scans every actor in the level, takes the min/max x/y plus padding as the
        world bounds, and writes worlds/<level>/world_grid.json. All agents then
        report their position as a stable (col, row) cell of this grid every tick.
        Run with the editor open and PIE stopped (uses an editor-world scan).
        Re-run after the level layout changes; edit the JSON to trim outliers
        (e.g. a distant skybox actor inflating the bounds).

        Args:
            cell_size: Grid cell edge length in centimeters. Default 400.
            padding: Extra margin added around the actor bounds, in cm. Default 800.

        Example valid input:
            {"cell_size": 400.0, "padding": 800.0}
        """
        from unreal_sim_server import get_agent_manager
        from agent_runtime.world_grid import WorldGrid

        mgr = get_agent_manager()
        level = mgr.bridge.get_current_level()
        if not level:
            return {"status": "error", "error": "Could not determine current level â€” is Unreal running?"}

        actors = mgr.bridge.get_level_actors()
        points = [a["location"][:2] for a in actors
                  if isinstance(a.get("location"), list) and len(a["location"]) >= 2]
        if not points:
            return {"status": "error", "error": "No actor positions returned â€” is the editor open (and PIE stopped)?"}

        xs, ys = [p[0] for p in points], [p[1] for p in points]
        bounds = {
            "min_x": min(xs) - padding, "min_y": min(ys) - padding,
            "max_x": max(xs) + padding, "max_y": max(ys) + padding,
        }
        path = Path(__file__).resolve().parents[1] / "worlds" / level / "world_grid.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"cell_size": cell_size, "bounds": bounds}, indent=2),
            encoding="utf-8",
        )
        mgr.world_grid = WorldGrid(cell_size=cell_size, bounds=bounds)
        return {
            "status": "generated",
            "level": level,
            "path": str(path),
            "actors_scanned": len(points),
            "bounds": bounds,
            "grid": mgr.world_grid.describe(),
        }

    @mcp.tool()
    def resync_simulation() -> Dict[str, Any]:
        """Re-query the current level and rebind agents without stopping the simulation.

        Use this after: loading a new map, relabeling an actor in the Outliner,
        editing an agent file on disk, or removing/adding an NPC body.

        Example valid input:
            {}
        """
        from unreal_sim_server import get_agent_manager
        return get_agent_manager().resync()

    logger.info("Simulation tools registered")
