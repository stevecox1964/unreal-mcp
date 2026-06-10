from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .agent import Agent
from .action_validator import validate
from . import explorer
from .perception import VisionPerceiver
from .spatial_memory import SpatialMap
from .world_grid import WorldGrid

logger = logging.getLogger("AgentRuntime")


def _loc_xyz(loc) -> tuple[float, float, float] | None:
    """Coerce a location payload ({x,y,z} dict or [x,y,z] list) to a float triple."""
    if isinstance(loc, dict):
        return float(loc.get("x", 0)), float(loc.get("y", 0)), float(loc.get("z", 0))
    if isinstance(loc, (list, tuple)) and len(loc) >= 3:
        return float(loc[0]), float(loc[1]), float(loc[2])
    return None


class AgentManager:
    def __init__(
        self,
        worlds_dir: Path,
        llm_router,
        unreal_bridge,
        memory_store,
    ):
        self.worlds_dir = worlds_dir
        self._agents_dir: Path | None = None
        self.llm = llm_router
        self.bridge = unreal_bridge
        self.memory = memory_store

        self.agents: dict[str, Agent] = {}
        self.running = False
        self.paused = False
        self.tick_seconds = 1
        self.mode = "live"                       # "live" = LLM-driven; "explore" = frontier mapping
        self._sim_task: Optional[asyncio.Task] = None
        self._tick_count = 0
        self._started_at: float | None = None
        self._last_tick_duration = 0.0

        # Explore-mode state (per agent).
        self.perceiver = VisionPerceiver()
        self._spatial: dict[str, SpatialMap] = {}   # agent_id -> loaded map (cache)
        self._last_cell: dict[str, str] = {}        # agent_id -> previous cell key, for nav edges

        # Fixed per-level grid; reloaded with the level in _load_agents.
        self.world_grid = WorldGrid()

    # Lifecycle

    async def start_simulation(
        self,
        tick_seconds: int = 1,
        active_agents: list[str] | None = None,
        mode: str = "live",
    ) -> dict:
        if self.running:
            return {"status": "already_running", "tick_seconds": self.tick_seconds}

        self.mode = (mode or "live").strip().lower()
        # Drop cached maps so each run reloads from disk (and picks up the right level).
        self._spatial.clear()
        self._last_cell.clear()

        self._load_agents(active_agents)
        if active_agents:
            for agent in self.agents.values():
                agent.set_active(True, self._agents_dir)
        bound_count = self._bind_agents()

        active = [a for a in self.agents.values() if a.is_active and a.has_unreal_binding]
        if not active:
            return {
                "status": "error",
                "error": "No agents could be bound to Unreal actors",
                "loaded_agents": list(self.agents.keys()),
                "bound_count": bound_count,
            }

        # Record each agent's run-start transform (once) so reset_agents can
        # teleport it back for reproducible re-runs.
        for agent in active:
            tf = self.bridge.get_character_transform(agent.bound_unreal_actor_name)
            if tf.get("location"):
                if agent.record_start_transform(tf["location"], tf.get("rotation"), self._agents_dir):
                    logger.info(f"[{agent.agent_id}] Start transform recorded: {tf['location']}")
            else:
                logger.warning(f"[{agent.agent_id}] Could not read start transform — reset won't reposition this agent")

        self.running = True
        self.paused = False
        self.tick_seconds = tick_seconds
        self._tick_count = 0
        self._started_at = time.monotonic()
        self._sim_task = asyncio.create_task(self._loop())

        logger.info(
            f"=== SIMULATION START === mode={self.mode} base_tick={tick_seconds}s "
            f"agents={[a.agent_id for a in active]}"
        )
        return {
            "status": "started",
            "mode": self.mode,
            "tick_seconds": tick_seconds,
            "active_agents": [a.agent_id for a in active],
        }

    async def stop_simulation(self) -> dict:
        was_running = self.running
        self.running = False
        self.paused = False
        if self._sim_task:
            self._sim_task.cancel()
            self._sim_task = None
        elapsed = time.monotonic() - self._started_at if self._started_at else 0.0
        if was_running:
            logger.info(f"=== SIMULATION STOP === ticks={self._tick_count} elapsed={elapsed:.1f}s")
        else:
            logger.info("=== SIMULATION STOP === (was not running)")
        self._started_at = None
        return {"status": "stopped", "ticks": self._tick_count, "elapsed_seconds": round(elapsed, 1)}

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
            "mode": self.mode,
            "tick_seconds": self.tick_seconds,
            "tick_count": self._tick_count,
            "last_tick_duration_seconds": round(self._last_tick_duration, 2),
            "agent_count": len(self.agents),
            "agents": [self._agent_summary(a) for a in self.agents.values()],
        }

    # Agent loading and binding

    def _load_agents(self, active_only: list[str] | None) -> None:
        self.agents.clear()

        current_level = self.bridge.get_current_level()
        if not current_level:
            logger.warning("Could not determine current level — no agents loaded")
            return

        agents_dir = self.worlds_dir / current_level / "agents"
        if not agents_dir.exists():
            logger.warning(f"No agents directory for level '{current_level}': {agents_dir}")
            return

        self._agents_dir = agents_dir
        self.memory.update_agents_dir(agents_dir)

        self.world_grid = WorldGrid.load(self.worlds_dir / current_level / "world_grid.json")
        logger.info(f"World grid for '{current_level}': {self.world_grid.describe()}")
        logger.info(f"Loading agents for level '{current_level}' from {agents_dir}")

        for path in sorted(agents_dir.iterdir()):
            if not path.is_dir():
                continue
            agent_id = path.name
            if active_only and agent_id not in active_only:
                continue
            try:
                agent = Agent.load(agents_dir, agent_id)
            except Exception as e:
                logger.error(f"Failed to load agent '{agent_id}': {e}")
                continue

            self.agents[agent_id] = agent
            logger.info(f"Loaded agent '{agent_id}' -> Unreal actor '{agent.unreal_actor_name}'")

    def _bind_agents(self) -> int:
        """Resolve each agent to a live Unreal actor (find or spawn)."""
        for agent in self.agents.values():
            agent.clear_unreal_binding(self._agents_dir)

        bound_count = 0
        for agent in self.agents.values():
            actor = self.bridge.find_actor(agent.bound_unreal_actor_name)
            if not actor and agent.bound_unreal_actor_name != agent.unreal_actor_name:
                agent.clear_unreal_binding(self._agents_dir)
                actor = self.bridge.find_actor(agent.unreal_actor_name)

            if actor:
                agent.bind_unreal_actor(actor, self._agents_dir)
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
                    agent.bind_unreal_actor(result, self._agents_dir)
                    logger.info(
                        f"[{agent.agent_id}] Spawned '{agent.blueprint_class}' as "
                        f"'{agent.bound_unreal_actor_name}'"
                    )
                    bound_count += 1
                else:
                    logger.warning(
                        f"[{agent.agent_id}] Spawn failed: {result.get('error') or result.get('message')}"
                    )
                    agent.clear_unreal_binding(self._agents_dir)
            else:
                logger.warning(
                    f"[{agent.agent_id}] Actor '{agent.unreal_actor_name}' not found "
                    f"and no blueprint_class set"
                )
                agent.clear_unreal_binding(self._agents_dir)
        return bound_count

    # Simulation loop

    async def _loop(self) -> None:
        logger.info(
            f"Simulation loop running — base tick {self.tick_seconds}s; the sleep starts "
            f"only after each tick's processing, so the interval expands with observation/LLM time"
        )
        while self.running:
            if not self.paused:
                started = time.monotonic()
                result = None
                try:
                    result = await self.tick()
                except Exception as e:
                    logger.error(f"Tick error: {e}")
                duration = time.monotonic() - started
                self._last_tick_duration = duration
                self._tick_count += 1
                if result and result.get("ticked"):
                    logger.info(
                        f"Tick #{self._tick_count}: {result['ticked']} agent(s) in {duration:.2f}s "
                        f"— next in {self.tick_seconds}s (effective interval ~{duration + self.tick_seconds:.2f}s)"
                    )
            # Base pacing sleeps AFTER the tick completes: with N avatars the gap
            # between ticks is their full observation + thinking time plus the base,
            # so ticks can never pile up and over-drive the avatars.
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

        if self.mode == "explore":
            return self._pulse_explore(agent)

        # Gather world state — screenshot + minimal engine queries
        observation = self.bridge.get_observation(
            agent.bound_unreal_actor_name, agent.agent_id, self._agents_dir
        )
        # Inject known cast — other bound agents by label, no positions
        observation["known_characters"] = [
            a.bound_unreal_actor_label or a.unreal_actor_name
            for a in self.agents.values()
            if a.agent_id != agent_id and a.has_unreal_binding
        ]

        # Fixed world-grid cell + known place — reported every tick, perception or not.
        grid, place = self._grid_and_place(agent_id, observation.get("location"))
        observation["grid"] = grid
        observation["place"] = place

        # Visual diff gate: skip LLM if the scene hasn't changed since last tick
        if not self.bridge.is_scene_changed(agent.agent_id, observation.get("image_path")):
            agent.mark_ticked(self._agents_dir)
            logger.info(
                f"[{agent_id}] grid={grid.get('key') if grid else '?'} "
                f"place={place or 'unknown'} — scene unchanged, skipping LLM"
            )
            return {
                "agent_id": agent_id, "action": "idle", "reason": "scene_unchanged",
                "grid": grid, "place": place,
            }

        # Retrieve relevant memories
        memories = self.memory.get_relevant_memories(agent_id)

        # LLM decision
        decision = self.llm.decide(agent, observation, memories)

        if not decision:
            logger.warning(f"[{agent_id}] No decision - idling")
            agent.mark_ticked(self._agents_dir)
            return {"agent_id": agent_id, "action": "idle", "reason": "no_decision"}

        # Validate
        action = validate(agent, decision, observation)
        if not action:
            agent.mark_ticked(self._agents_dir)
            return {"agent_id": agent_id, "action": "idle", "reason": "validation_failed"}

        # Execute in Unreal
        action = self._resolve_action_actor_refs(action)
        if action.get("type") == "observe":
            result = {"status": "success", "image_path": observation.get("image_path"), "action": "observe"}
        elif action.get("type") == "wander":
            import random
            known = observation.get("known_characters", [])
            if known:
                target = random.choice(known)
                result = self.bridge.execute_action(
                    agent.bound_unreal_actor_name,
                    {"type": "walk_to", "target_actor": target},
                )
                # If already adjacent (pathfinding fails), just idle this tick
                if result.get("error"):
                    result = {"status": "accepted", "action": "idle", "note": "already adjacent"}
            else:
                result = {"status": "accepted", "action": "idle"}
        else:
            result = self.bridge.execute_action(agent.bound_unreal_actor_name, action)

        # Track speech cooldown
        if action.get("type") == "speak_to":
            agent.mark_spoke(self._agents_dir)

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

        agent.mark_ticked(self._agents_dir)

        return {
            "agent_id":   agent_id,
            "thought":    decision.get("thought_summary"),
            "action":     action,
            "result":     result,
            "grid":       grid,
            "place":      place,
        }

    # ── Explore mode ───────────────────────────────────────────────────────────

    def _spatial_map(self, agent_id: str) -> SpatialMap:
        """Load (and cache) this agent's per-agent egocentric map."""
        smap = self._spatial.get(agent_id)
        if smap is None:
            path = self._agents_dir / agent_id / "spatial_map.json"
            # Tile with the world grid's cell size so map cells and grid keys align.
            smap = SpatialMap.load(path, cell_size=self.world_grid.cell_size)
            self._spatial[agent_id] = smap
        return smap

    def _grid_and_place(self, agent_id: str, location) -> tuple[dict | None, list[str]]:
        """Fixed world-grid cell for a location + known place labels for it.

        Pure lookups (grid math + this agent's saved spatial map) — no engine
        or LLM calls, so it runs every tick even when perception is skipped.
        """
        xyz = _loc_xyz(location)
        if xyz is None:
            return None, []
        grid = self.world_grid.locate(xyz[0], xyz[1])
        place = self._spatial_map(agent_id).place_labels(grid["key"])
        return grid, place

    def _pulse_explore(self, agent: Agent) -> dict:
        """One exploration tick: see → perceive → map → pick frontier → walk.

        The avatar's own position (path integration) and a screenshot are the
        only engine inputs. Gemini turns the screenshot into landmark labels;
        a deterministic frontier policy — never the LLM — chooses where to walk.
        The visual-diff gate only skips re-labelling an unchanged view; the
        avatar still maps its cell and moves, so it can never get stuck idling.
        """
        agent_id = agent.agent_id
        observation = self.bridge.get_observation(
            agent.bound_unreal_actor_name, agent_id, self._agents_dir
        )
        xyz = _loc_xyz(observation.get("location"))
        if xyz is None:
            agent.mark_ticked(self._agents_dir)
            logger.warning(f"[{agent_id}] explore: no location — skipping tick")
            return {"agent_id": agent_id, "action": "idle", "reason": "no_location"}
        x, y, z = xyz

        image_path = observation.get("image_path")
        known = [
            a.bound_unreal_actor_label or a.unreal_actor_name
            for a in self.agents.values()
            if a.agent_id != agent_id and a.has_unreal_binding
        ]

        # Perceive only when the view changed — otherwise reuse "nothing new seen".
        landmarks, caption = [], ""
        if image_path and self.bridge.is_scene_changed(agent_id, image_path):
            perceived = self.perceiver.perceive(image_path, known)
            landmarks = perceived.get("landmarks", [])
            caption = perceived.get("caption", "")
            if perceived.get("error"):
                logger.warning(f"[{agent_id}] perception error: {perceived['error']}")

        # Map: record the occupied cell + what was seen, link the traversed edge.
        smap = self._spatial_map(agent_id)
        cell = smap.ingest(x, y, landmarks)
        prev = self._last_cell.get(agent_id)
        if prev and prev != cell:
            smap.link(prev, cell)
        self._last_cell[agent_id] = cell

        # Route: deterministic frontier choice → walk there.
        target = explorer.next_target(smap, x, y, z)
        if target:
            result = self.bridge.execute_action(
                agent.bound_unreal_actor_name,
                {"type": "walk_to", "location": target["location"]},
            )
            if result.get("error") or result.get("success") is False:
                # Unreachable (off NavMesh etc.) — don't keep retrying this cell.
                smap.mark_blocked(target["cell"])
                logger.info(f"[{agent_id}] frontier {target['cell']} blocked: {result.get('error')}")
        else:
            result = {"status": "accepted", "action": "idle", "note": "no frontier"}

        smap.save(self._agents_dir / agent_id / "spatial_map.json")

        # Fixed world-grid cell + known place — reported even when perception skipped.
        grid = self.world_grid.locate(x, y)
        place = smap.place_labels(cell)

        action = {"type": "walk_to", "target_cell": target["cell"]} if target else {"type": "idle"}
        observation["_thought"] = caption
        observation["grid"] = grid
        observation["place"] = place
        self.memory.record(
            agent_id=agent_id, observation=observation, action=action,
            result=result, memory_update=None, importance=0.3,
        )
        agent.mark_ticked(self._agents_dir)

        stats = smap.stats()
        logger.info(
            f"[{agent_id}] explore grid={grid['key']}"
            f"{' (col ' + str(grid['col']) + ',row ' + str(grid['row']) + ')' if 'col' in grid else ''} "
            f"place={place or 'unknown'} saw={len(landmarks)} "
            f"target={target['cell'] if target else None} "
            f"visited={stats['cells_visited']} labels={stats['distinct_labels']}"
        )
        return {
            "agent_id": agent_id,
            "cell": cell,
            "grid": grid,
            "place": place,
            "caption": caption,
            "landmarks_seen": len(landmarks),
            "target_cell": target["cell"] if target else None,
            "result": result,
            "map_stats": stats,
        }

    async def reset_agents(self) -> dict:
        """Reset agents to their run-start state for reproducible re-runs.

        Stops the sim if running, teleports each agent back to its recorded
        start transform, clears per-run timers, restores memories from
        memory.seed.json (or empties them), and deletes spatial maps.
        """
        was_running = self.running
        if was_running:
            await self.stop_simulation()

        if not self.agents:
            self._load_agents(None)
            self._bind_agents()
        if not self.agents or not self._agents_dir:
            return {"status": "error", "error": "No agents loaded — is Unreal connected?"}

        results = []
        for agent in self.agents.values():
            entry: dict = {"agent_id": agent.agent_id}

            if agent.start_location and agent.has_unreal_binding:
                result = self.bridge.teleport(
                    agent.bound_unreal_actor_name, agent.start_location, agent.start_rotation
                )
                ok = result.get("success") is True or result.get("status") == "success"
                entry["teleported"] = ok
                if not ok:
                    entry["teleport_error"] = result.get("error") or "unknown error"
            else:
                entry["teleported"] = False
                entry["teleport_error"] = (
                    "no Unreal binding" if agent.start_location else "no start transform recorded"
                )

            agent.reset_runtime_state(self._agents_dir)
            entry["memories"] = self.memory.reset_memories(agent.agent_id)

            map_path = self._agents_dir / agent.agent_id / "spatial_map.json"
            if map_path.exists():
                map_path.unlink()
                entry["spatial_map"] = "deleted"

            results.append(entry)

        self._spatial.clear()
        self._last_cell.clear()
        self.bridge.clear_scene_cache()

        failures = [r["agent_id"] for r in results if not r["teleported"]]
        logger.info(
            f"=== AGENTS RESET === {len(results)} agent(s)"
            f"{', sim stopped first' if was_running else ''}"
            f"{', teleport FAILED for: ' + ', '.join(failures) if failures else ''}"
        )
        return {"status": "reset", "stopped_simulation": was_running, "agents": results}

    def resync(self) -> dict:
        """Re-query the world and rebind agents without a full stop/restart cycle."""
        was_paused = self.paused
        self.paused = True

        pre_bindings = {
            a.agent_id: a.bound_unreal_actor_label
            for a in self.agents.values()
        }

        active_ids = list(self.agents.keys()) if self.agents else None
        self._load_agents(active_ids)
        bound_count = self._bind_agents()

        current_level = self.bridge.get_current_level()

        added, removed, rebound, skipped_levels = [], [], [], []
        all_ids = set(pre_bindings) | set(self.agents)
        for aid in all_ids:
            was_in = aid in pre_bindings
            now_in = aid in self.agents
            if not was_in and now_in:
                added.append(aid)
            elif was_in and not now_in:
                removed.append(aid)
            elif was_in and now_in:
                old_label = pre_bindings[aid]
                new_label = self.agents[aid].bound_unreal_actor_label
                if old_label != new_label:
                    rebound.append({"agent_id": aid, "old_label": old_label, "new_label": new_label})

        self.paused = was_paused
        logger.info(f"Resync complete — level='{current_level}' bound={bound_count}")
        return {
            "status": "resynced",
            "level": current_level,
            "bound_count": bound_count,
            "added": added,
            "removed": removed,
            "rebound": rebound,
            "skipped_levels": skipped_levels,
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
        a.set_goal(goal, self._agents_dir)
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
