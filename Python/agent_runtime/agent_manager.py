from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .agent import Agent
from .action_validator import validate

logger = logging.getLogger("AgentRuntime")


class AgentManager:
    def __init__(
        self,
        agents_dir: Path,
        llm_router,
        unreal_bridge,
        memory_store,
    ):
        self.agents_dir = agents_dir
        self.llm = llm_router
        self.bridge = unreal_bridge
        self.memory = memory_store

        self.agents: dict[str, Agent] = {}
        self.running = False
        self.paused = False
        self.tick_seconds = 5
        self._sim_task: Optional[asyncio.Task] = None

    # Lifecycle

    async def start_simulation(
        self,
        tick_seconds: int = 5,
        active_agents: list[str] | None = None,
    ) -> dict:
        if self.running:
            return {"status": "already_running", "tick_seconds": self.tick_seconds}

        self._load_agents(active_agents)
        if active_agents:
            for agent in self.agents.values():
                agent.set_active(True, self.agents_dir)
        bound_count = self._bind_agents()

        active = [a for a in self.agents.values() if a.is_active and a.has_unreal_binding]
        if not active:
            return {
                "status": "error",
                "error": "No agents could be bound to Unreal actors",
                "loaded_agents": list(self.agents.keys()),
                "bound_count": bound_count,
            }

        self.running = True
        self.paused = False
        self.tick_seconds = tick_seconds
        self._sim_task = asyncio.create_task(self._loop())

        logger.info(f"Simulation started - agents: {[a.agent_id for a in active]}")
        return {
            "status": "started",
            "tick_seconds": tick_seconds,
            "active_agents": [a.agent_id for a in active],
        }

    async def stop_simulation(self) -> dict:
        self.running = False
        self.paused = False
        if self._sim_task:
            self._sim_task.cancel()
            self._sim_task = None
        logger.info("Simulation stopped")
        return {"status": "stopped"}

    async def pause_simulation(self) -> dict:
        self.paused = True
        return {"status": "paused"}

    async def resume_simulation(self) -> dict:
        if not self.running:
            return {"status": "error", "error": "Simulation not running"}
        self.paused = False
        return {"status": "resumed"}

    def get_status(self) -> dict:
        return {
            "running": self.running,
            "paused": self.paused,
            "tick_seconds": self.tick_seconds,
            "agent_count": len(self.agents),
            "agents": [self._agent_summary(a) for a in self.agents.values()],
        }

    # Agent loading and binding

    def _load_agents(self, active_only: list[str] | None) -> None:
        self.agents.clear()
        if not self.agents_dir.exists():
            logger.warning(f"agents_dir does not exist: {self.agents_dir}")
            return
        for path in sorted(self.agents_dir.iterdir()):
            if not path.is_dir():
                continue
            agent_id = path.name
            if active_only and agent_id not in active_only:
                continue
            try:
                agent = Agent.load(self.agents_dir, agent_id)
                self.agents[agent_id] = agent
                logger.info(f"Loaded agent '{agent_id}' -> Unreal actor '{agent.unreal_actor_name}'")
            except Exception as e:
                logger.error(f"Failed to load agent '{agent_id}': {e}")

    def _bind_agents(self) -> int:
        """Resolve each agent to a live Unreal actor (find or spawn)."""
        bound_count = 0
        for agent in self.agents.values():
            actor = self.bridge.find_actor(agent.bound_unreal_actor_name)
            if not actor and agent.bound_unreal_actor_name != agent.unreal_actor_name:
                agent.clear_unreal_binding(self.agents_dir)
                actor = self.bridge.find_actor(agent.unreal_actor_name)

            if actor:
                agent.bind_unreal_actor(actor, self.agents_dir)
                logger.info(
                    f"[{agent.agent_id}] Bound to Unreal actor "
                    f"'{agent.bound_unreal_actor_name}' from hint '{agent.unreal_actor_name}'"
                )
                bound_count += 1
                continue

            if agent.blueprint_class:
                result = self.bridge.spawn_actor(
                    agent.blueprint_class,
                    agent.unreal_actor_name,
                )
                if result.get("success") is not False and result.get("name"):
                    agent.bind_unreal_actor(result, self.agents_dir)
                    logger.info(
                        f"[{agent.agent_id}] Spawned '{agent.blueprint_class}' as "
                        f"'{agent.bound_unreal_actor_name}'"
                    )
                    bound_count += 1
                else:
                    logger.warning(
                        f"[{agent.agent_id}] Spawn failed: {result.get('error') or result.get('message')}"
                    )
                    agent.clear_unreal_binding(self.agents_dir)
            else:
                logger.warning(
                    f"[{agent.agent_id}] Actor '{agent.unreal_actor_name}' not found "
                    f"and no blueprint_class set"
                )
                agent.clear_unreal_binding(self.agents_dir)
        return bound_count

    # Simulation loop

    async def _loop(self) -> None:
        logger.info("Simulation loop running")
        while self.running:
            if not self.paused:
                try:
                    await self.tick()
                except Exception as e:
                    logger.error(f"Tick error: {e}")
            await asyncio.sleep(self.tick_seconds)
        logger.info("Simulation loop exited")

    async def tick(self) -> dict:
        ready = [
            a for a in self.agents.values()
            if a.is_active and not a.is_busy and a.cooldown_expired()
        ]
        results = []
        for agent in ready:
            result = await self.pulse_agent(agent.agent_id)
            results.append(result)
        return {"ticked": len(results), "agent_results": results}

    async def pulse_agent(self, agent_id: str) -> dict:
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": f"Agent '{agent_id}' not loaded"}

        # Gather world state
        observation = self.bridge.get_observation(agent.bound_unreal_actor_name)

        # Retrieve relevant memories
        memories = self.memory.get_relevant_memories(agent_id)

        # LLM decision
        decision = self.llm.decide(agent, observation, memories)

        if not decision:
            logger.warning(f"[{agent_id}] No decision - idling")
            agent.mark_ticked(self.agents_dir)
            return {"agent_id": agent_id, "action": "idle", "reason": "no_decision"}

        # Validate
        action = validate(agent, decision, observation)
        if not action:
            agent.mark_ticked(self.agents_dir)
            return {"agent_id": agent_id, "action": "idle", "reason": "validation_failed"}

        # Execute in Unreal
        action = self._resolve_action_actor_refs(action)
        result = self.bridge.execute_action(agent.bound_unreal_actor_name, action)

        # Track speech cooldown
        if action.get("type") == "speak_to":
            agent.mark_spoke(self.agents_dir)

        # Persist memory + log
        observation["_thought"] = decision.get("thought_summary")
        self.memory.record(
            agent_id=agent_id,
            observation=observation,
            action=action,
            result=result,
            memory_update=decision.get("memory_update"),
            importance=float(decision.get("importance", 0.5)),
        )

        agent.mark_ticked(self.agents_dir)

        return {
            "agent_id":   agent_id,
            "thought":    decision.get("thought_summary"),
            "action":     action,
            "result":     result,
        }

    # Director commands

    def list_agents(self) -> list[dict]:
        return [self._agent_summary(a) for a in self.agents.values()]

    def inspect_agent(self, agent_id: str) -> dict:
        a = self.agents.get(agent_id)
        if not a:
            return {"error": f"Agent '{agent_id}' not loaded"}
        return {
            "agent_id":        a.agent_id,
            "unreal_actor_name": a.unreal_actor_name,
            "bound_unreal_actor_name": a.bound_unreal_actor_name,
            "bound_unreal_actor_label": a.bound_unreal_actor_label,
            "blueprint_class": a.blueprint_class,
            "tier":            a.tier,
            "is_active":       a.is_active,
            "is_busy":         a.is_busy,
            "current_goal":    a.current_goal,
            "allowed_actions": a.allowed_actions,
            "state":           a.state,
        }

    def set_agent_goal(self, agent_id: str, goal: str) -> dict:
        a = self.agents.get(agent_id)
        if not a:
            return {"error": f"Agent '{agent_id}' not loaded"}
        a.set_goal(goal, self.agents_dir)
        logger.info(f"[{agent_id}] Goal updated -> '{goal}'")
        return {"status": "updated", "agent_id": agent_id, "goal": goal}

    # Helpers

    def _agent_summary(self, a: Agent) -> dict:
        return {
            "agent_id":          a.agent_id,
            "unreal_actor_name": a.unreal_actor_name,
            "bound_unreal_actor_name": a.bound_unreal_actor_name,
            "bound_unreal_actor_label": a.bound_unreal_actor_label,
            "tier":              a.tier,
            "is_active":         a.is_active,
            "is_busy":           a.is_busy,
            "current_goal":      a.current_goal,
            "last_tick_time":    a.state.get("last_tick_time"),
        }

    def _resolve_action_actor_refs(self, action: dict) -> dict:
        """Translate agent IDs in action targets into bound Unreal actor names."""
        resolved = dict(action)
        for key in ("target", "target_actor"):
            value = resolved.get(key)
            if isinstance(value, str) and value in self.agents:
                resolved[key] = self.agents[value].bound_unreal_actor_name
        return resolved
