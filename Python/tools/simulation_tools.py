"""
Simulation control MCP tools — thin clients of the standalone sim runner.

Exposes start/stop/pause/resume/status/list/inspect/set_goal/force_tick
so the Claude/OpenAI CLI can act as the simulation director. Since #3/2.4
these tools ATTACH to a running ``sim_runner`` over its localhost control
API (RunnerClient) instead of hosting an AgentManager in the MCP process —
the runner owns the sim's lifetime and the single Unreal socket. If no
runner is reachable, every tool fails loud with how to start one; nothing
falls back to in-process hosting.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from agent_runtime.runner_client import RunnerClient, DEFAULT_BASE_URL

logger = logging.getLogger("AgentRuntime")

_NO_RUNNER_HINT = (
    f"No sim runner reachable at {DEFAULT_BASE_URL} — start it first "
    "(start_sim.bat, or `python Python/sim_runner.py`), then retry."
)


def register_simulation_tools(mcp: FastMCP, runner: RunnerClient = None) -> None:
    """Register the director tools. ``runner`` is injectable for tests; by
    default a client for the local sim runner is created on first use."""
    state = {"runner": runner}

    def _runner() -> RunnerClient:
        if state["runner"] is None:
            state["runner"] = RunnerClient()
        return state["runner"]

    def _attached(call):
        """Run one RunnerClient call; a transport failure means no runner."""
        try:
            return call(_runner())
        except Exception as e:
            logger.warning(f"sim runner call failed: {e}")
            return {"status": "error", "error": f"{_NO_RUNNER_HINT} ({e})"}

    @mcp.tool()
    def reload_llm_environment() -> Dict[str, str]:
        """Reload Python/.env and report LLM settings with secrets masked.

        Note: the sim itself runs in the standalone runner and re-reads .env
        as it goes — this reports what is configured, for this MCP process.

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
    def start_simulation(
        tick_seconds: int = 1,
        active_agents: List[str] = None,
        mode: str = "live",
    ) -> Dict[str, Any]:
        """Start the NPC agent simulation loop (in the attached sim runner).

        The loop is self-pacing: tick_seconds is the BASE interval, and the sleep
        starts only after a tick's processing (vision + LLM thinking for all
        agents) completes. E.g. a 2 s observation with base 1 means ~3 s between
        ticks — ticks never pile up and over-drive the avatars.

        Args:
            tick_seconds: Base seconds added after each tick's processing. Default 1.
            active_agents: List of agent_ids to activate. Omit to load all agents.
            mode: "live" (default) = LLM-driven decisions; "explore" = deterministic
                frontier exploration that builds each agent's spatial_map.json from
                vision — no decision LLM, the avatar maps the world by walking it.

        Example valid input:
            {"tick_seconds": 1, "active_agents": ["dufus"], "mode": "explore"}
        """
        return _attached(lambda r: r.start(
            tick_seconds=tick_seconds, active_agents=active_agents, mode=mode
        ))

    @mcp.tool()
    def stop_simulation() -> Dict[str, Any]:
        """Stop the running simulation loop.

        Example valid input:
            {}
        """
        return _attached(lambda r: r.stop())

    @mcp.tool()
    def pause_simulation() -> Dict[str, Any]:
        """Pause the simulation loop without stopping it.

        Example valid input:
            {}
        """
        return _attached(lambda r: r.pause())

    @mcp.tool()
    def resume_simulation() -> Dict[str, Any]:
        """Resume a paused simulation.

        Example valid input:
            {}
        """
        return _attached(lambda r: r.resume())

    @mcp.tool()
    def get_simulation_status() -> Dict[str, Any]:
        """Get the current simulation state, tick rate, and all agent summaries.

        Example valid input:
            {}
        """
        return _attached(lambda r: r.status())

    @mcp.tool()
    def list_agents() -> Dict[str, Any]:
        """List all loaded agents with their Unreal binding, tier, goal, and active state.

        Example valid input:
            {}
        """
        return _attached(lambda r: {"agents": r.agents()})

    @mcp.tool()
    def inspect_agent(agent_id: str) -> Dict[str, Any]:
        """Get the full configuration and state for a specific agent.

        Args:
            agent_id: The agent identifier (matches folder name in Python/worlds/<level>/agents/)

        Example valid input:
            {"agent_id": "dufus"}
        """
        return _attached(lambda r: r.inspect_agent(agent_id))

    @mcp.tool()
    def set_agent_goal(agent_id: str, goal: str) -> Dict[str, Any]:
        """Override the current goal of a running agent.

        Args:
            agent_id: The agent to update
            goal: New goal string (e.g. 'follow_player', 'patrol_ruins')

        Example valid input:
            {"agent_id": "dufus", "goal": "greet the player"}
        """
        return _attached(lambda r: r.set_agent_goal(agent_id, goal))

    @mcp.tool()
    def force_agent_tick(agent_id: str) -> Dict[str, Any]:
        """Immediately pulse one agent regardless of its cooldown timer.

        Args:
            agent_id: The agent to tick now

        Example valid input:
            {"agent_id": "dufus"}
        """
        return _attached(lambda r: r.pulse_agent(agent_id))

    @mcp.tool()
    def get_recent_events(limit: int = 20) -> Dict[str, Any]:
        """Return the most recent agent decision log entries.

        Args:
            limit: Maximum number of entries to return (default 20)

        Example valid input:
            {"limit": 10}
        """
        return _attached(lambda r: {"events": r.events(limit)})

    @mcp.tool()
    def reset_agents() -> Dict[str, Any]:
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
        return _attached(lambda r: r.reset_agents())

    @mcp.tool()
    def reset_world_places() -> Dict[str, Any]:
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
        return _attached(lambda r: r.reset_places())

    @mcp.tool()
    def generate_world_grid(cell_size: float = 3000.0, padding: float = 800.0) -> Dict[str, Any]:
        """Compute the fixed world grid from the current level's actor positions.

        Scans every actor in the level, takes the min/max x/y plus padding as the
        world bounds, and writes worlds/<level>/world_grid.json. All agents then
        report their position as a stable (col, row) cell of this grid every tick.
        Run with the editor open and PIE stopped (uses an editor-world scan).
        Re-run after the level layout changes; edit the JSON to trim outliers
        (e.g. a distant skybox actor inflating the bounds).

        A grid cell is a navigation *district* that holds several ~9 m place
        cells, so the default is 3000 cm (30 m) — not a place-sized tile.

        Args:
            cell_size: Grid cell edge length in centimeters. Default 3000 (30 m).
            padding: Extra margin added around the actor bounds, in cm. Default 800.

        Example valid input:
            {"cell_size": 3000.0, "padding": 800.0}
        """
        return _attached(lambda r: r.generate_world_grid(cell_size=cell_size, padding=padding))

    @mcp.tool()
    def resync_simulation() -> Dict[str, Any]:
        """Re-query the current level and rebind agents without stopping the simulation.

        Use this after: loading a new map, relabeling an actor in the Outliner,
        editing an agent file on disk, or removing/adding an NPC body.

        Example valid input:
            {}
        """
        return _attached(lambda r: r.resync())

    logger.info("Simulation tools registered (attach to sim runner)")
