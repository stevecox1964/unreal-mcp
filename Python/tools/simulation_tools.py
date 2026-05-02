"""
Simulation control MCP tools.

Exposes start/stop/pause/resume/status/list/inspect/set_goal/force_tick
so the Claude/OpenAI CLI can act as the simulation director.
"""

from __future__ import annotations

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
        tick_seconds: int = 5,
        active_agents: List[str] = None,
    ) -> Dict[str, Any]:
        """Start the NPC agent simulation loop.

        Args:
            tick_seconds: How often (in seconds) each agent is pulsed. Default 5.
            active_agents: List of agent_ids to activate. Omit to load all agents.

        Example valid input:
            {"tick_seconds": 10, "active_agents": ["gondolf", "bartleby"]}
        """
        from unreal_mcp_server import get_agent_manager
        mgr = get_agent_manager()
        return await mgr.start_simulation(tick_seconds=tick_seconds, active_agents=active_agents)

    @mcp.tool()
    async def stop_simulation() -> Dict[str, Any]:
        """Stop the running simulation loop.

        Example valid input:
            {}
        """
        from unreal_mcp_server import get_agent_manager
        return await get_agent_manager().stop_simulation()

    @mcp.tool()
    async def pause_simulation() -> Dict[str, Any]:
        """Pause the simulation loop without stopping it.

        Example valid input:
            {}
        """
        from unreal_mcp_server import get_agent_manager
        return await get_agent_manager().pause_simulation()

    @mcp.tool()
    async def resume_simulation() -> Dict[str, Any]:
        """Resume a paused simulation.

        Example valid input:
            {}
        """
        from unreal_mcp_server import get_agent_manager
        return await get_agent_manager().resume_simulation()

    @mcp.tool()
    def get_simulation_status() -> Dict[str, Any]:
        """Get the current simulation state, tick rate, and all agent summaries.

        Example valid input:
            {}
        """
        from unreal_mcp_server import get_agent_manager
        return get_agent_manager().get_status()

    @mcp.tool()
    def list_agents() -> Dict[str, Any]:
        """List all loaded agents with their Unreal binding, tier, goal, and active state.

        Example valid input:
            {}
        """
        from unreal_mcp_server import get_agent_manager
        return {"agents": get_agent_manager().list_agents()}

    @mcp.tool()
    def inspect_agent(agent_id: str) -> Dict[str, Any]:
        """Get the full configuration and state for a specific agent.

        Args:
            agent_id: The agent identifier (matches folder name in Python/agents/)

        Example valid input:
            {"agent_id": "bartleby"}
        """
        from unreal_mcp_server import get_agent_manager
        return get_agent_manager().inspect_agent(agent_id)

    @mcp.tool()
    def set_agent_goal(agent_id: str, goal: str) -> Dict[str, Any]:
        """Override the current goal of a running agent.

        Args:
            agent_id: The agent to update
            goal: New goal string (e.g. 'follow_player', 'patrol_ruins')

        Example valid input:
            {"agent_id": "bartleby", "goal": "greet the player"}
        """
        from unreal_mcp_server import get_agent_manager
        return get_agent_manager().set_agent_goal(agent_id, goal)

    @mcp.tool()
    async def force_agent_tick(agent_id: str) -> Dict[str, Any]:
        """Immediately pulse one agent regardless of its cooldown timer.

        Args:
            agent_id: The agent to tick now

        Example valid input:
            {"agent_id": "bartleby"}
        """
        from unreal_mcp_server import get_agent_manager
        return await get_agent_manager().pulse_agent(agent_id)

    @mcp.tool()
    def get_recent_events(limit: int = 20) -> Dict[str, Any]:
        """Return the most recent agent decision log entries.

        Args:
            limit: Maximum number of entries to return (default 20)

        Example valid input:
            {"limit": 10}
        """
        from unreal_mcp_server import get_agent_manager
        mgr = get_agent_manager()
        return {"events": mgr.memory.get_recent_events(limit)}

    logger.info("Simulation tools registered")
