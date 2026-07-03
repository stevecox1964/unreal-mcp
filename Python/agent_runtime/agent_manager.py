from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .agent import Agent
from .action_validator import validate
from . import explorer
from .perception import VisionPerceiver
from . import cell_sweep
from . import planner
from . import route_map
from . import sim_run
from .episodic_memory import EpisodicLog
from .place_db import PlaceDB, yaw_to_compass
from .social_memory import SocialMemory, is_anonymous
from .spatial_memory import SpatialMap
from .world_clock import WorldClock
from .world_grid import WorldGrid

logger = logging.getLogger("AgentRuntime")

# A frontier cell is only blocked after this many consecutive failed walk
# attempts — unless the avatar is already adjacent, which is proof enough.
_MAX_FRONTIER_FAILURES = 3

# Wake-up look-around: yaw offsets (degrees, relative to the facing the avatar
# woke with) for the 180-degree sweep, left to right. Direction names are the
# same vocabulary walk_to's "direction" field uses.
_SWEEP_VIEWS = [
    ("left", -90.0),
    ("forward-left", -45.0),
    ("forward", 0.0),
    ("forward-right", 45.0),
    ("right", 90.0),
]

# walk_to direction → yaw offset from current facing.
_DIRECTION_YAW_OFFSET = {
    "forward": 0.0,
    "forward-left": -45.0,
    "forward-right": 45.0,
    "left": -90.0,
    "right": 90.0,
    "back": 180.0,
}

# One movement "step" for direction-relative walks (cm).
_STEP_DISTANCE = 1500.0

# When the camera view is unchanged AND the avatar is standing still, re-decide
# every Nth tick anyway so a stopped agent is always re-prompted to move to the
# next grid/place — without freezing (view never changes) or spamming the LLM
# (an intentionally-idle agent still only decides once every N stationary ticks).
_STATIONARY_REDECIDE_TICKS = 4

# Stuck detection (live path): the engine can report ai_state="moving" while the
# avatar is wedged against an un-navmeshed obstacle (a parked van) and making no
# real progress. After this many consecutive "moving but didn't advance" ticks we
# flag it stuck — force a fresh decision and tell the LLM to pick another direction.
_STUCK_PROGRESS_CM = 100.0   # min cm advanced per tick to count as real progress
_STUCK_TICKS = 3             # consecutive no-progress moving ticks → stuck
_STUCK_TRACE_CM = 300.0      # forward raycast distance when stuck (cm)

# Path sense (B7): while traveling, watch what is directly ahead so the agent
# can step around people/vehicles instead of walking through them — pawn-vs-pawn
# collision is invisible to the navmesh, so this is the cognitive loop's problem,
# not an engine steering feature. Only *mobile* categories interrupt travel;
# structures ahead are ordinary navmesh business (corners, walls) and would spam.
_AHEAD_TRACE_CM = 500.0      # forward raycast distance while traveling (cm)
_MOBILE_BLOCKERS = {"person", "animal", "vehicle"}

# Personal space (B7b): the decision cadence (~9 s/tick) is far too slow to stop
# a walk once someone is close — by the next tick the agent is in their face. So
# inside this standoff the lizard brain halts the walk itself (a motor reflex,
# like flinching — not a decision) and reports the halt as a fact; the forced
# re-decide then lets the LLM choose: talk, step around, continue. 300 cm is
# roughly where a whole person fills the first-person camera frame.
_STANDOFF_CM = 300.0

# Semantic classifier for forward-trace hits.
# Maps engine actor names/classes → generic categories the LLM can reason about.
# The lizard brain translates engine noise; it does NOT infer meaning or advise action.
_BLOCKER_KEYWORDS: list[tuple[set[str], str]] = [
    ({"van", "car", "truck", "vehicle", "bus", "taxi", "auto"}, "vehicle"),
    ({"npc", "apc", "character", "person", "human", "pedestrian", "civilian", "thirdperson"}, "person"),
    ({"dog", "cat", "animal", "bird", "creature", "pet"}, "animal"),
    ({"wall", "building", "fence", "barrier", "door", "gate", "pillar", "column"}, "structure"),
    ({"corn", "cornfield", "crop", "wheat", "foliage", "bush", "hedge", "shrub", "vegetation"}, "foliage"),
]

def _classify_blocker(actor_name: str, actor_class: str) -> str:
    text = (actor_name + " " + actor_class).lower()
    for keywords, category in _BLOCKER_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category
    return "obstacle"


def _loc_xyz(loc) -> tuple[float, float, float] | None:
    """Coerce a location payload ({x,y,z} dict or [x,y,z] list) to a float triple."""
    if isinstance(loc, dict):
        return float(loc.get("x", 0)), float(loc.get("y", 0)), float(loc.get("z", 0))
    if isinstance(loc, (list, tuple)) and len(loc) >= 3:
        return float(loc[0]), float(loc[1]), float(loc[2])
    return None


def _yaw_of(rotation) -> float | None:
    """Extract yaw (degrees) from a rotation payload ({x:pitch, y:yaw, z:roll} or [pitch, yaw, roll])."""
    if isinstance(rotation, dict) and rotation.get("y") is not None:
        return float(rotation["y"])
    if isinstance(rotation, (list, tuple)) and len(rotation) >= 2:
        return float(rotation[1])
    return None


def _offset_location(x: float, y: float, z: float, yaw_deg: float, distance: float) -> list[float]:
    """World location `distance` cm from (x, y) along world yaw (UE: X forward, yaw toward +Y)."""
    rad = math.radians(yaw_deg)
    return [x + math.cos(rad) * distance, y + math.sin(rad) * distance, z]


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
        self._social_mem: dict[str, SocialMemory] = {}  # agent_id -> acquaintance store (cache)
        self._episodic_log: dict[str, EpisodicLog] = {}  # agent_id -> episodic event log (cache)
        self._cell_sweeps: dict[str, dict] = {}      # agent_id -> in-progress unexplored-cell sweep
        self._last_cell: dict[str, str] = {}        # agent_id -> previous cell key, for nav edges
        self._frontier_failures: dict[str, dict[str, int]] = {}  # agent_id -> cell key -> consecutive failed walks
        self._scene_skips: dict[str, int] = {}      # agent_id -> consecutive scene-unchanged skips (gate liveness)
        self._last_pos: dict[str, tuple] = {}       # agent_id -> last (x, y), for stuck detection
        self._no_progress: dict[str, int] = {}      # agent_id -> consecutive "moving but didn't advance" ticks
        self._last_grid_place: dict[str, tuple] = {}  # agent_id -> (grid, place), reported even when LLM skipped

        # Fixed per-level grid; reloaded with the level in _load_agents.
        self.world_grid = WorldGrid()

        # In-world clock; reloaded with the level, anchored at start_simulation.
        self.world_clock = WorldClock()

        # SQLite place cell store — initialised in start_simulation once world dir is known.
        self.place_db: PlaceDB | None = None

        # Sim run tag (SR<n>) — allocated per-world in start_simulation, pushed to
        # the bridge (observation filenames) + memory (decision log) for attribution.
        self.sim_run_id: str = "SR0"

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

        # Truncate the log file so each run starts with a clean slate.
        for _h in logging.root.handlers:
            if isinstance(_h, logging.FileHandler):
                _h.stream.seek(0)
                _h.stream.truncate(0)
                break

        # Drop cached maps so each run reloads from disk (and picks up the right level).
        self._spatial.clear()
        self._last_cell.clear()
        self._frontier_failures.clear()
        self._scene_skips.clear()
        self._last_pos.clear()
        self._no_progress.clear()

        self._load_agents(active_agents)
        if active_agents:
            for agent in self.agents.values():
                agent.set_active(True, self._agents_dir)
        bound_count = self._bind_agents()

        # Open (or create) the SQLite place cell store for this world.
        if self._agents_dir is not None:
            db_path = self._agents_dir.parent / "world_places.db"
            self.place_db = PlaceDB(db_path)

            # Allocate this run's SR<n> tag (per-world) and push it everywhere the
            # run needs stamping: observation filenames + the decision log.
            self.sim_run_id = sim_run.allocate_run(self._agents_dir.parent)
            self.bridge.sim_run_id = self.sim_run_id
            self.memory.sim_run_id = self.sim_run_id
            logger.info(f"Sim run {self.sim_run_id} — observations + decision log tagged")

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

        # Clear stale per-run state (goal, timers) so every run wakes clean.
        for agent in active:
            agent.reset_runtime_state(self._agents_dir)
            logger.info(f"[{agent.agent_id}] Runtime state reset for new run")

        # Teleport every agent back to their recorded start position.
        # Memories and place cells are intentionally preserved across runs.
        for agent in active:
            if agent.start_location and agent.has_unreal_binding:
                result = self.bridge.teleport(
                    agent.bound_unreal_actor_name, agent.start_location, agent.start_rotation
                )
                ok = result.get("success") is True or result.get("status") == "success"
                if ok:
                    logger.info(f"[{agent.agent_id}] Repositioned to start transform {agent.start_location}")
                else:
                    logger.warning(f"[{agent.agent_id}] Reposition failed: {result.get('error', 'unknown')}")
            else:
                logger.warning(f"[{agent.agent_id}] No start transform recorded — skipping reposition")

        self.bridge.clear_scene_cache()

        self.running = True
        self.paused = False
        self.tick_seconds = tick_seconds
        self._tick_count = 0
        self._started_at = time.monotonic()
        self.world_clock.start()
        self._sim_task = asyncio.create_task(self._loop())

        logger.info(
            f"=== SIMULATION START === mode={self.mode} base_tick={tick_seconds}s "
            f"time={self.world_clock.now_text()} agents={[a.agent_id for a in active]}"
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

    def recent_events(self, limit: int = 20) -> list[dict]:
        """Recent agent decision-log entries (for the web cockpit's live log)."""
        return self.memory.get_recent_events(limit) if self.memory else []

    def clear_events(self) -> int:
        """Clear the decision feed (the cockpit's live log). Returns lines cleared."""
        return self.memory.clear_recent_events() if self.memory else 0

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

        self.world_clock = WorldClock.load(self.worlds_dir / current_level / "world.json")
        logger.info(f"World clock for '{current_level}': {self.world_clock.describe()}")
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
        if self.mode == "live":
            # Spool-up: each agent wakes and orients itself before the first tick.
            await self._wake_agents()
            self._print_sim_status()
            self._flush_model_pie()
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
                self._print_sim_status()
                self._flush_model_pie()
            # Base pacing sleeps AFTER the tick completes: with N avatars the gap
            # between ticks is their full observation + thinking time plus the base,
            # so ticks can never pile up and over-drive the avatars.
            await asyncio.sleep(self.tick_seconds)
        logger.info("Simulation loop exited")

    def _print_sim_status(self) -> None:
        """Push agent names and current goals to the PIE viewport as on-screen debug messages."""
        active = sorted(
            (a for a in self.agents.values() if a.is_active and a.has_unreal_binding),
            key=lambda a: a.agent_id,
        )
        elapsed = int(time.monotonic() - self._started_at) if self._started_at else 0
        header = f"[SIM] tick={self._tick_count}  elapsed={elapsed}s  mode={self.mode}"
        self.bridge.print_to_screen(header, key=99, duration=30.0)
        for i, agent in enumerate(active):
            goal = agent.current_goal
            if len(goal) > 45:
                goal = goal[:42] + "..."
            self.bridge.print_to_screen(f"  {agent.agent_id}: {goal}", key=100 + i, duration=30.0)

    def _agent_slot(self, agent_id: str) -> int:
        """Stable PIE-line index for an agent (matches _print_sim_status ordering)."""
        ids = sorted(
            a.agent_id for a in self.agents.values()
            if a.is_active and a.has_unreal_binding
        )
        try:
            return ids.index(agent_id)
        except ValueError:
            return 0

    def _pie_activity(self, agent_id: str, message: str) -> None:
        """Update this agent's PIE activity line (key 130+slot), in place each tick.

        Bridge is single-socket, so call only from the sequential tick phases
        (observe / act) — never from the parallel perceive+decide phase.
        """
        self.bridge.print_to_screen(
            f"  {agent_id}: {message}",
            key=130 + self._agent_slot(agent_id),
            duration=30.0,
        )

    def _set_activity(self, agent: Agent, state: str) -> None:
        """Push a cognitive/physical activity label to the agent's actor.

        Sets AIState (fires OnAIStateChanged) so the above-head status bubble can
        show what the agent is doing — e.g. "observing", "thinking". Single-socket
        bridge, so call only from the sequential tick phases (observe / act),
        never from the parallel perceive+decide phase.
        """
        if agent.has_unreal_binding:
            self.bridge.set_ai_state(agent.bound_unreal_actor_name, state)

    def _flush_model_pie(self) -> None:
        """Drain queued Ollama model-load lines to PIE (sequential phase only)."""
        from .ollama_adapter import take_pending_pie
        for msg in take_pending_pie():
            self.bridge.print_to_screen(msg, key=200, duration=20.0)

    async def _wake_agents(self) -> None:
        """Spool-up: each agent wakes and orients itself before the first tick.

        Phase 1 (sequential, bridge): for each agent, check PlaceDB for a
          known place.  If known → skip sweep; if unknown → run 180° sweep,
          ingest compass observations into PlaceDB.
        Phase 2 (parallel, thread pool): fire orient LLM calls simultaneously.
        Phase 3 (sequential, bridge): apply goals + execute each first action.
        """
        if not self.llm:
            logger.info("Wake-up skipped — no LLM router")
            return
        world_time = self.world_clock.now_text()
        active = [a for a in self.agents.values() if a.is_active and a.has_unreal_binding]

        # Phase 1: bridge (sequential) — sweep unknown places, skip known ones.
        needs_orient: list[tuple] = []   # (agent, context, memories)
        for agent in active:
            try:
                tf = self.bridge.get_character_transform(agent.bound_unreal_actor_name)
                loc = tf.get("location")
                rot = tf.get("rotation")
                grid, place = self._grid_and_place(agent.agent_id, loc)
                col, row = self._cell_col_row(grid)

                known_place = None
                familiarity: dict = {}
                if self.place_db and col is not None:
                    known_place = self.place_db.get_place(col, row)
                    familiarity = self.place_db.agent_familiarity(agent.agent_id, col, row)

                if known_place:
                    # Place is on the shared map — skip the expensive 180° sweep.
                    # Pass personal familiarity so the orient prompt can tell the
                    # agent whether this is THEIR place or just a place they've
                    # visited, giving them the signal to stay vs. move on.
                    logger.info(
                        f"[{agent.agent_id}] WAKE {world_time} at known place "
                        f"'{known_place['name']}' (visits={familiarity.get('visit_count',0)}, "
                        f"named_by_me={familiarity.get('named_by_me',False)}) — skipping sweep"
                    )
                    memories = self.memory.get_relevant_memories(agent.agent_id)
                    context = {
                        "world_time": world_time, "location": loc, "rotation": rot,
                        "grid": grid, "place": place, "views": [],
                        "directions": self._direction_places(agent.agent_id, loc, rot),
                        "known_place": known_place["name"],
                        "familiarity": familiarity,
                    }
                    needs_orient.append((agent, context, memories))
                    continue

                known_chars = [
                    a.display_name
                    for a in self.agents.values()
                    if a.agent_id != agent.agent_id and a.has_unreal_binding
                ]
                views = self._wake_sweep(agent, loc, rot, known_chars)

                # Ingest each sweep view into PlaceDB with its compass direction.
                if self.place_db and col is not None:
                    for v in views:
                        if v.get("landmarks"):
                            self.place_db.ingest_compass(
                                agent.agent_id, col, row,
                                yaw_to_compass(v["yaw"]),
                                v["landmarks"],
                            )

                memories = self.memory.get_relevant_memories(agent.agent_id)
                context = {
                    "world_time": world_time, "location": loc, "rotation": rot,
                    "grid": grid, "place": place, "views": views,
                    "directions": self._direction_places(agent.agent_id, loc, rot),
                    "known_place": None,
                    "familiarity": familiarity,
                }
                needs_orient.append((agent, context, memories))
            except Exception as e:
                logger.error(f"[{agent.agent_id}] Wake sweep failed: {e} — keeping authored goal")

        if not needs_orient:
            return

        # Phase 2: orient LLM calls (parallel via thread pool).
        orient_tasks = [
            asyncio.to_thread(self.llm.orient, agent, ctx, mems)
            for agent, ctx, mems in needs_orient
        ]
        orientations = await asyncio.gather(*orient_tasks, return_exceptions=True)

        # Phase 3: apply orientations + first actions (sequential, bridge).
        for (agent, context, memories), orientation in zip(needs_orient, orientations):
            try:
                loc = context["location"]
                rot = context["rotation"]
                grid = context["grid"]
                place = context["place"]
                views = context.get("views", [])

                if isinstance(orientation, Exception):
                    logger.error(f"[{agent.agent_id}] Orient call failed: {orientation}")
                    orientation = None
                if not orientation:
                    logger.warning(
                        f"[{agent.agent_id}] Wake-up produced no orientation — "
                        f"keeping authored goal: {agent.current_goal!r}"
                    )
                    continue

                goal = str(orientation.get("current_goal") or "").strip()
                if goal:
                    agent.set_goal(goal, self._agents_dir)

                self._record_place(agent.agent_id, loc, orientation.get("place"))

                first_action = validate(agent, orientation, {})
                first_result = None
                if first_action:
                    forward = next((v for v in views if v["direction"] == "forward"), None)
                    wake_obs = {
                        "location": loc, "rotation": rot,
                        "image_path": forward["image_path"] if forward else None,
                    }
                    first_result = self._execute_world_action(agent, first_action, wake_obs)

                self.memory.record(
                    agent_id=agent.agent_id,
                    observation={
                        "wake": True, "world_time": context["world_time"], "location": loc,
                        "grid": grid, "place": place,
                        "views": [v["direction"] for v in views],
                        "_thought": orientation.get("thought_summary"),
                    },
                    action={"type": "wake", "first_action": first_action},
                    result=first_result or {"status": "ok"},
                    memory_update=orientation.get("memory_update"),
                    importance=float(orientation.get("importance", 0.7)),
                )
                logger.info(
                    f"[{agent.agent_id}] WAKE {context['world_time']} place={place or 'unknown'} "
                    f"views={len(views)} goal={goal or agent.current_goal!r} "
                    f"first_action={first_action.get('type') if first_action else None}"
                )
            except Exception as e:
                logger.error(f"[{agent.agent_id}] Wake orientation failed: {e} — keeping authored goal")

    def _wake_sweep(self, agent: Agent, loc, rot, known_characters: list[str]) -> list[dict]:
        """The 180-degree look-around: turn in place through five headings
        (left to right), capture a view at each, perceive it (Gemini turns
        pixels into named sightings), then restore the original facing so
        movement directions stay relative to it.

        Each view carries what was seen plus what the agent's own map already
        knows about the cell one step away in that direction. All sightings
        are accumulated into the agent's spatial map. A failed turn, capture,
        or perception just degrades that view — never aborts the wake. Calls
        are strictly sequential (single-socket bridge).
        """
        base_yaw = _yaw_of(rot)
        xyz = _loc_xyz(loc)
        if xyz is None or base_yaw is None:
            logger.warning(f"[{agent.agent_id}] No transform — waking without a look-around")
            return []
        views: list[dict] = []
        sightings: list[dict] = []
        smap = self._spatial_map(agent.agent_id)
        for direction, offset in _SWEEP_VIEWS:
            yaw = base_yaw + offset
            turn = self.bridge.set_facing(agent.bound_unreal_actor_name, loc, yaw)
            if turn.get("error"):
                logger.warning(f"[{agent.agent_id}] sweep turn '{direction}' failed: {turn['error']}")
                continue
            time.sleep(0.25)  # let the rotated frame render before capturing
            image_path = self.bridge.capture_view(
                agent.bound_unreal_actor_name, agent.agent_id, self._agents_dir, f"wake_{direction}"
            )
            if not image_path:
                logger.warning(f"[{agent.agent_id}] sweep capture '{direction}' failed")
                continue
            seen = self.perceiver.perceive(image_path, known_characters)
            if seen.get("error"):
                logger.warning(f"[{agent.agent_id}] sweep perception '{direction}' failed: {seen['error']}")
            sightings.extend(seen.get("landmarks") or [])
            tx, ty, _ = _offset_location(*xyz, yaw, _STEP_DISTANCE)
            views.append({
                "direction": direction, "yaw": yaw, "image_path": image_path,
                "caption": seen.get("caption", ""),
                "landmarks": seen.get("landmarks", []),
                "characters": seen.get("characters", []),
                "places": smap.place_labels(self.world_grid.locate(tx, ty)["key"]),
            })
        # Face back the way the avatar woke up.
        self.bridge.teleport(agent.bound_unreal_actor_name, loc, rot)
        # Everything seen during the sweep goes into the mental map.
        if sightings:
            smap.ingest(xyz[0], xyz[1], sightings)
            smap.save(self._agents_dir / agent.agent_id / "spatial_map.json")
        return views

    async def tick(self) -> dict:
        """Run one simulation tick across all ready agents.

        Three phases keep Unreal bridge calls sequential while LLM calls
        run in parallel across agents:
          1. Observe (sequential, bridge): screenshot + world state queries
          2. Perceive + decide (parallel, thread pool): Gemini → Haiku
          3. Act (sequential, bridge): execute action + persist memory
        """
        ready = [
            a for a in self.agents.values()
            if a.is_active and not a.is_busy and a.cooldown_expired()
        ]
        # Agents mid-sweep (#11.1) run a deterministic, bridge-only, no-LLM step —
        # keep them out of the perceive/decide phases until the sweep finishes.
        sweeping = [a for a in ready if a.agent_id in self._cell_sweeps]
        ready = [a for a in ready if a.agent_id not in self._cell_sweeps]

        results = []
        # Sweep phase (sequential — single bridge socket, like the others).
        for agent in sweeping:
            self._set_activity(agent, "sweeping")
            results.append(self._pulse_sweep(agent))

        # Phase 1: observe (sequential, bridge)
        observations: dict[str, dict | None] = {}
        for agent in ready:
            self._set_activity(agent, "observing")
            observations[agent.agent_id] = self._observe_agent(agent)

        # Phase 2: perceive + decide (parallel, thread pool)
        llm_needed = [a for a in ready if observations.get(a.agent_id) is not None]
        # Flag "thinking" sequentially before launching the parallel decide batch —
        # the LLM call blocks for the bulk of the tick, so this is what's on screen.
        for agent in llm_needed:
            self._set_activity(agent, "thinking")
        decisions: dict[str, dict | None] = {}
        if llm_needed:
            tasks = [
                asyncio.to_thread(self._perceive_and_decide, agent, observations[agent.agent_id])
                for agent in llm_needed
            ]
            results_raw = await asyncio.gather(*tasks, return_exceptions=True)
            for agent, result in zip(llm_needed, results_raw):
                decisions[agent.agent_id] = result

        # Phase 3: act (sequential, bridge) — appends to the sweep results.
        for agent in ready:
            obs = observations.get(agent.agent_id)
            decision = decisions.get(agent.agent_id)
            results.append(self._act_agent(agent, decision, obs))

        return {"ticked": len(results), "agent_results": results}

    async def pulse_agent(self, agent_id: str) -> dict:
        """Single-agent tick used by force_agent_tick MCP tool and tests."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": f"Agent '{agent_id}' not loaded"}
        if agent.agent_id in self._cell_sweeps:
            return self._pulse_sweep(agent)
        if self.mode == "explore":
            return self._pulse_explore(agent)
        obs = self._observe_agent(agent)
        if obs is None:
            grid, place = self._last_grid_place.get(agent_id, (None, []))
            return {"agent_id": agent_id, "action": "idle", "reason": "scene_unchanged",
                    "grid": grid, "place": place}
        decision = await asyncio.to_thread(self._perceive_and_decide, agent, obs)
        return self._act_agent(agent, decision, obs)

    # ── Tick phases ──────────────────────────────────────────────────────────

    def _observe_agent(self, agent: Agent) -> dict | None:
        """Phase 1: gather world state via bridge.

        Returns an observation dict, or None if the scene is unchanged
        (scene_unchanged agents are skipped by phases 2 and 3).
        """
        agent_id = agent.agent_id
        observation = self.bridge.get_observation(
            agent.bound_unreal_actor_name, agent_id, self._agents_dir
        )
        observation["known_characters"] = [
            a.display_name
            for a in self.agents.values()
            if a.agent_id != agent_id and a.has_unreal_binding
        ]
        grid, place = self._grid_and_place(agent_id, observation.get("location"))
        observation["grid"] = grid
        observation["place"] = place
        # Stash so a scene-unchanged skip can still report position (pure lookups,
        # no engine/LLM) — explore mode reports grid+place every tick and the
        # standard path must too, even when the diff gate skips perception.
        self._last_grid_place[agent_id] = (grid, place)
        observation["world_time"] = self.world_clock.now_text()
        observation["directions"] = self._direction_places(
            agent_id, observation.get("location"), observation.get("rotation")
        )

        # Structured place context from SQLite (None if not yet named).
        if self.place_db and grid:
            col, row = self._cell_col_row(grid)
            if col is not None:
                self.place_db.touch(agent_id, col, row)
                observation["place_context"] = self.place_db.get_place(col, row)

        # Stuck detection: "moving" but not actually advancing (wedged on an
        # obstacle the navmesh doesn't route around). Attach to the observation so
        # the decision prompt can tell the agent to pick another direction.
        moving = "moving" in str(observation.get("current_action") or "").lower()
        stuck = self._detect_stuck(agent_id, _loc_xyz(observation.get("location")), moving)
        observation["stuck"] = stuck
        # Forward path sense (B7): trace ahead on every moving tick, not just when
        # already wedged. A mobile blocker (someone crossing the path) becomes a
        # fact the LLM can sidestep *before* the collision; when stuck, whatever
        # is ahead is reported. Facts only — the decision stays with the LLM.
        if moving or stuck:
            trace = self.bridge.line_trace_forward(
                agent.bound_unreal_actor_name,
                _STUCK_TRACE_CM if stuck else _AHEAD_TRACE_CM,
            )
            if trace.get("hit"):
                category = _classify_blocker(
                    trace.get("actor_name", ""), trace.get("actor_class", "")
                )
                if stuck or category in _MOBILE_BLOCKERS:
                    observation["blocker"] = {
                        "category": category,
                        "distance_cm": trace.get("distance_cm", 0.0),
                    }
                    # Personal space (B7b): inside the standoff, halt the walk
                    # NOW — waiting for the LLM means walking into their face.
                    if (moving and category in _MOBILE_BLOCKERS
                            and observation["blocker"]["distance_cm"] <= _STANDOFF_CM):
                        self.bridge.execute_action(
                            agent.bound_unreal_actor_name, {"type": "stop"}
                        )
                        observation["blocker"]["halted"] = True
                        logger.info(
                            f"[{agent_id}] reflex stop: {category} "
                            f"{observation['blocker']['distance_cm']:.0f} cm ahead "
                            f"(standoff {_STANDOFF_CM:.0f} cm)"
                        )

        if not self.bridge.is_scene_changed(agent_id, observation.get("image_path")):
            # The view is unchanged. Skip the LLM if the avatar is still travelling
            # (its own motion will change the view) or to rate-limit an idle agent —
            # but force a fresh decision every Nth stationary tick so a stopped
            # avatar is always re-prompted to move to the next grid/place. Without
            # this a stationary agent freezes: no motion → identical view → LLM
            # skipped → no new move → identical view, forever. A *stuck* agent
            # reports "moving" but isn't progressing, so never skip it — it must
            # re-decide to escape the obstacle. Same for a mobile blocker directly
            # ahead (B7): the agent must re-decide *now* to step around, not after
            # it has already walked through them.
            skips = self._scene_skips.get(agent_id, 0) + 1
            self._scene_skips[agent_id] = skips
            blocked = "blocker" in observation
            if not stuck and not blocked and (moving or skips % _STATIONARY_REDECIDE_TICKS != 0):
                agent.mark_ticked(self._agents_dir)
                reason = "moving" if moving else f"idle {skips}/{_STATIONARY_REDECIDE_TICKS}"
                logger.info(
                    f"[{agent_id}] grid={grid.get('key') if grid else '?'} "
                    f"place={observation.get('place_context', {}) or place or 'unknown'} "
                    f"— scene unchanged ({reason}), skipping LLM"
                )
                self._pie_activity(agent_id, f"OBS skip ({reason})")
                return None
            if stuck:
                why = "stuck on an obstacle"
            elif blocked:
                why = f"{observation['blocker']['category']} directly ahead"
            else:
                why = f"stationary {skips} ticks"
            logger.info(
                f"[{agent_id}] {why} — re-deciding to pick a new direction"
            )

        self._scene_skips[agent_id] = 0
        return observation

    def _detect_stuck(self, agent_id: str, xyz, moving: bool) -> bool:
        """True when the avatar reports moving but isn't actually advancing.

        Lizard-brain "device driver" robustness: worlds may have imperfect navmesh,
        so an avatar can wedge against an obstacle (a parked van) yet still report
        ai_state="moving". We watch real position delta across ticks; after
        ``_STUCK_TICKS`` no-progress moving ticks the agent is stuck and must
        re-decide. Mirrors explore mode's frontier-failure blocking for the live
        LLM path. Returns False whenever the agent isn't moving or is advancing.
        """
        last = self._last_pos.get(agent_id)
        if xyz is not None:
            self._last_pos[agent_id] = (xyz[0], xyz[1])
        if xyz is None or not moving or last is None:
            self._no_progress[agent_id] = 0
            return False
        moved = math.hypot(xyz[0] - last[0], xyz[1] - last[1])
        if moved >= _STUCK_PROGRESS_CM:
            self._no_progress[agent_id] = 0
            return False
        n = self._no_progress.get(agent_id, 0) + 1
        if n >= _STUCK_TICKS:
            # Flag stuck and reset, so the redirect gets a fresh grace window to
            # take effect before we'd flag again — no per-tick LLM hammering.
            self._no_progress[agent_id] = 0
            return True
        self._no_progress[agent_id] = n
        return False

    def _perceive_and_decide(self, agent: Agent, observation: dict) -> dict | None:
        """Phase 2: Gemini perception → LLM decision.

        Runs in a thread pool so multiple agents can execute this
        concurrently. No bridge calls here — bridge is single-socket.
        """
        agent_id = agent.agent_id

        if observation.get("image_path"):
            seen = self.perceiver.perceive(
                observation["image_path"], observation["known_characters"]
            )
            if seen.get("error"):
                logger.warning(f"[{agent_id}] perception failed: {seen['error']}")
            observation["seen"] = seen

            xyz = _loc_xyz(observation.get("location"))
            if xyz and seen.get("landmarks"):
                # Raw sightings → spatial map (for direction-preview in prompts)
                smap = self._spatial_map(agent_id)
                smap.ingest(xyz[0], xyz[1], seen["landmarks"])
                smap.save(self._agents_dir / agent_id / "spatial_map.json")

                # Compass-oriented sightings → PlaceDB
                if self.place_db:
                    grid = observation.get("grid")
                    col, row = self._cell_col_row(grid)
                    yaw = _yaw_of(observation.get("rotation"))
                    if col is not None and yaw is not None:
                        self.place_db.ingest_compass(
                            agent_id, col, row,
                            yaw_to_compass(yaw),
                            seen["landmarks"],
                        )

            # Remember who was seen this tick (named characters → social memory).
            self._record_sightings(agent_id, observation)

        # Surface known people for recall so the decision layer can reason about
        # who this agent has met (e.g. greet someone, seek out a friend).
        acquaintances = self._social(agent_id).acquaintances()
        observation["acquaintances"] = acquaintances
        # Surface the named-place map (nearest first) so the agent can pick a
        # destination by name — walk_to then resolves it to a location (#1).
        observation["known_places"] = self.known_places(observation.get("location"))[:8]
        # Surface the most relevant past episodes (recency ⊕ same place ⊕ known
        # faces) so overnight runs recall more than the flat 30-item window.
        place_list = observation.get("place") or []
        observation["recent_episodes"] = self._episodic(agent_id).relevant(
            n=5,
            current_cell=(observation.get("grid") or {}).get("key"),
            current_place=place_list[0] if place_list else None,
            known_names=[a["name"] for a in acquaintances],
        )

        # Sequencer: give the agent a routine to follow instead of pure reaction.
        # ensure_daily_plan generates the day's schedule once (idempotent within a
        # sim-day), then step() answers "what should I be doing now?" — travel to
        # the scheduled place, act here, or idle. The directive grounds the
        # decision prompt; the LLM still chooses the action.
        self._attach_schedule(agent, observation)

        # Travel ticks get a top-down route map (#6b/WP5): the corridor between
        # here and the scheduled destination, as facts + a rendered image the
        # multimodal decision call reads. Travel-only bounds the token cost.
        sched = observation.get("schedule") or {}
        if sched.get("status") == "travel" and sched.get("place"):
            try:
                route = self.route_map_for(agent_id, sched["place"], observation)
                if route:
                    observation["route_map"] = route
            except Exception as e:
                logger.warning(f"[{agent_id}] route map failed: {e}")

        memories = self.memory.get_relevant_memories(agent_id)
        return self.llm.decide(agent, observation, memories)

    def _attach_schedule(self, agent: Agent, observation: dict) -> None:
        """Compute the sequencer directive for this tick and attach it to the
        observation as ``observation["schedule"]`` (consumed by the decision
        prompt). Pure per-agent file writes (the day's plan), safe in the
        parallel decide phase. Degrades silently — a planning hiccup must never
        break a tick."""
        try:
            world_time = observation.get("world_time", "")
            ask = getattr(self.llm, "ask", None)
            schedule = planner.ensure_daily_plan(
                agent, planner.day_of(world_time),
                ask=(lambda p: ask(agent, p)) if ask else None,
                agents_dir=self._agents_dir,
            )
            pc = observation.get("place_context") or {}
            place_list = observation.get("place") or []
            current_place = pc.get("name") or (place_list[0] if place_list else None)
            observation["schedule"] = planner.step(
                schedule, planner.minute_of_day(world_time),
                current_place=current_place, prev_activity=agent.last_activity,
            )
        except Exception as e:
            logger.warning(f"[{agent.agent_id}] schedule step failed: {e}")
            observation["schedule"] = None

    def _act_agent(self, agent: Agent, decision, observation: dict | None) -> dict:
        """Phase 3: validate decision, execute in Unreal, persist memory."""
        agent_id = agent.agent_id

        if observation is None:
            return {"agent_id": agent_id, "action": "idle", "reason": "scene_unchanged"}

        if isinstance(decision, Exception):
            logger.error(f"[{agent_id}] LLM phase exception: {decision}")
            decision = None

        if not decision:
            logger.warning(f"[{agent_id}] No decision - idling")
            agent.mark_ticked(self._agents_dir)
            self._pie_activity(agent_id, "OBS fire -> no decision (idle)")
            return {"agent_id": agent_id, "action": "idle", "reason": "no_decision"}

        action = validate(agent, decision, observation)
        if not action:
            agent.mark_ticked(self._agents_dir)
            self._pie_activity(agent_id, "OBS fire -> invalid decision (idle)")
            return {"agent_id": agent_id, "action": "idle", "reason": "validation_failed"}

        # Sweep interrupt (#11.1): an APC staying in an unexplored cell maps it
        # before acting — the sweep's first step replaces this tick's LLM action;
        # the following steps run LLM-free via _pulse_sweep until the breadcrumb
        # drops, then the sequencer resumes the routine.
        if self._should_sweep_here(observation):
            sweep_action = self._sweep_step(agent_id, observation, start=True)
            if sweep_action is not None:
                action = sweep_action

        result = self._execute_world_action(agent, action, observation)
        status = result.get("status") or result.get("success")
        self._pie_activity(agent_id, f"OBS fire -> {action.get('type')} [{status}]")

        # Name the place if the LLM provided one.
        self._record_place(agent_id, observation.get("location"), decision.get("place"))

        if action.get("type") == "speak_to":
            agent.mark_spoke(self._agents_dir)
            self._record_interactions(agent_id, observation)

        observation["_thought"] = decision.get("thought_summary")
        self.memory.record(
            agent_id=agent_id,
            observation=observation,
            action=action,
            result=result,
            memory_update=decision.get("memory_update"),
            importance=float(decision.get("importance", 0.5)),
        )
        self._record_episode(agent_id, observation, action, result)
        # Remember the scheduled activity this tick so next tick's sequencer can
        # detect a block boundary (e.g. noon: "sell veg" -> "have lunch").
        sched = observation.get("schedule")
        if sched is not None:
            agent.set_last_activity(sched.get("activity", ""), self._agents_dir)
        agent.mark_ticked(self._agents_dir)

        return {
            "agent_id": agent_id,
            "thought":  decision.get("thought_summary"),
            "action":   action,
            "result":   result,
            "grid":     observation.get("grid"),
            "place":    observation.get("place"),
        }

    def _resolve_place_target(self, agent_id: str, name: str, observation: dict) -> list[float] | None:
        """Resolve a place name to a walk target ``[x, y, z]``, or None.

        Resolution order (#11.2, grid-first): a community-named cell wins and
        resolves to its cell center; otherwise an APC-owned place cell (the
        resolving agent's own entries preferred) resolves to the community
        anchor plus its stored XY offset. Keeps the agent's current z so it
        stays on the ground plane. Returns None when there is no PlaceDB, the
        grid is unbounded, or the name is unknown — callers fall back to the
        bridge's graceful idle.
        """
        if self.place_db is None:
            return None
        xyz = _loc_xyz(observation.get("location"))
        z = xyz[2] if xyz else 0.0

        cell = self.place_db.find_named_cell(name)
        if cell is not None:
            center = self.world_grid.cell_center(*cell)
            if center is not None:
                logger.info(f"Resolved place '{name}' -> cell {cell} center {center}")
                return [center[0], center[1], z]

        owned = self.place_db.find_owned_place(name, preferred_owner=agent_id)
        if owned is not None:
            center = self.world_grid.cell_center(owned["col"], owned["row"])
            if center is not None:
                logger.info(
                    f"Resolved owned place '{name}' ({owned['owner']}) -> cell "
                    f"({owned['col']},{owned['row']}) offset ({owned['dx']:.0f},{owned['dy']:.0f})"
                )
                return [center[0] + owned["dx"], center[1] + owned["dy"], z]
        return None

    def known_places(self, location) -> list[dict]:
        """The named-place map relative to ``location`` — nearest first.

        Each entry: ``{"name", "bearing", "distance_m", "col", "row"}`` where
        bearing is a compass label (N..NW) from the agent toward the place and
        distance is in meters. APC-owned place cells (#11.2) are included too,
        positioned at their community anchor + XY offset and carrying an extra
        ``"owner"`` key. This is the "map" an agent consults — it answers
        *what places exist and roughly which way* before any routing. Returns []
        with no PlaceDB, an unbounded grid, or no location.
        """
        if self.place_db is None:
            return []
        xyz = _loc_xyz(location)
        if xyz is None:
            return []
        x, y = xyz[0], xyz[1]
        out: list[dict] = []

        def _entry(place, px, py, **extra):
            dx, dy = px - x, py - y
            return {
                "name": place["name"],
                "bearing": yaw_to_compass(math.degrees(math.atan2(dy, dx))),
                "distance_m": math.hypot(dx, dy) / 100.0,
                "col": place["col"],
                "row": place["row"],
                **extra,
            }

        for place in self.place_db.all_named_places():
            center = self.world_grid.cell_center(place["col"], place["row"])
            if center is None:
                continue
            out.append(_entry(place, center[0], center[1]))
        for place in self.place_db.all_owned_places():
            center = self.world_grid.cell_center(place["col"], place["row"])
            if center is None:
                continue
            out.append(_entry(place, center[0] + place["dx"], center[1] + place["dy"],
                              owner=place["owner"]))
        out.sort(key=lambda p: p["distance_m"])
        return out

    def route_map_for(self, agent_id: str, destination_name: str, observation: dict) -> dict | None:
        """Top-down route map facts + rendered image for a travel tick (#6b/WP5).

        Resolves the destination through the same chain as walk_to (community
        name first, then this agent's owned places), locates the agent's current
        cell, and delegates to route_map.build_route_map. The image lands in the
        agent's observations dir (overwritten per tick — it is ephemeral sense
        data, though the cockpit can peek at the latest one). Returns None when
        anything is missing (no PlaceDB, unbounded grid, unknown destination,
        no current cell) — the tick proceeds without a map.
        """
        if self.place_db is None or not self.world_grid.has_bounds:
            return None
        col, row = self._cell_col_row(observation.get("grid"))
        if col is None:
            return None
        dest = self.place_db.find_named_cell(destination_name)
        if dest is None:
            owned = self.place_db.find_owned_place(destination_name, preferred_owner=agent_id)
            if owned is not None:
                dest = (owned["col"], owned["row"])
        if dest is None:
            return None
        route = route_map.build_route_map(
            self.place_db, self.world_grid, (col, row), dest,
            destination_name=destination_name,
        )
        if route is None:
            return None
        image = route_map.render_map_image(
            route, self._agents_dir / agent_id / "observations" / "route_map.png"
        )
        if image is not None:
            route["image_path"] = str(image)
        return route

    def _cell_col_row(self, grid: dict | None) -> tuple[int, int] | tuple[None, None]:
        """Extract (col, row) integers from a world_grid.locate() result dict."""
        if not grid:
            return None, None
        try:
            return int(grid["col"]), int(grid["row"])
        except (KeyError, TypeError, ValueError):
            return None, None

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

    def _social(self, agent_id: str) -> SocialMemory:
        """Load (and cache) this agent's acquaintance store."""
        s = self._social_mem.get(agent_id)
        if s is None:
            s = SocialMemory.load(self._agents_dir / agent_id / "social.json")
            self._social_mem[agent_id] = s
        return s

    def _record_sightings(self, agent_id: str, observation: dict) -> None:
        """Persist perceived named characters into this agent's social memory.

        Pulls characters out of ``observation["seen"]``, keys each sighting to
        the current grid cell + world time, and saves. Anonymous figures
        ("unknown person") are dropped by SocialMemory — only identities are
        remembered. Pure (no engine/LLM/socket), so it runs in the parallel
        perceive phase: each agent only writes its own social.json.
        """
        characters = (observation.get("seen") or {}).get("characters") or []
        if not characters:
            return
        grid = observation.get("grid") or {}
        cell_key = grid.get("key")
        world_time = observation.get("world_time", "")
        social = self._social(agent_id)
        changed = False
        for c in characters:
            if social.record_sighting(c.get("label", ""), cell_key, world_time):
                changed = True
        if changed:
            social.save(self._agents_dir / agent_id / "social.json")

    def _record_interactions(self, agent_id: str, observation: dict, sentiment_delta: float = 0.0) -> None:
        """Log a social interaction with each named person currently perceived.

        Called when the agent speaks: speech has no explicit target, so the
        interaction is attributed to whoever it can see. Sentiment defaults to
        neutral — we don't infer affinity from a message without a real signal
        (that would need an LLM call the loop avoids). Pure, per-agent file.
        """
        characters = (observation.get("seen") or {}).get("characters") or []
        world_time = observation.get("world_time", "")
        social = self._social(agent_id)
        changed = False
        for c in characters:
            if social.record_interaction(c.get("label", ""), world_time, sentiment_delta):
                changed = True
        if changed:
            social.save(self._agents_dir / agent_id / "social.json")

    def _sweep_step(self, agent_id: str, observation: dict, start: bool = True) -> dict | None:
        """One step of the shared sweep capability (#11.1).

        Any APC that needs an unexplored cell walks to the cell center, observes
        each compass heading, then drops the community breadcrumb
        (``PlaceDB.mark_swept``) so every other APC skips the costly 360.

        With ``start=True`` a new sweep may begin when the current cell is
        genuinely unexplored; with ``start=False`` only an already-active sweep
        continues. Returns the next sweep sub-action, or None when there is
        nothing to do (nothing active/startable, missing PlaceDB / bounds /
        grid, or the sweep just finished). The returned action carries
        ``_sweep_interrupt`` so callers can see the tick was spent sweeping.
        """
        col, row = self._cell_col_row(observation.get("grid"))
        if col is None:
            return None
        xyz = _loc_xyz(observation.get("location"))
        if xyz is None:
            return None

        active = self._cell_sweeps.get(agent_id)
        if active is None:
            if not start:
                return None
            # Only start a sweep on a genuinely unexplored cell.
            if self.place_db is None or self.place_db.is_explored(col, row):
                return None
            sweep = cell_sweep.default_sweep(self.world_grid, col, row, z=xyz[2])
            if sweep is None:
                return None
            active = {"sweep": sweep, "col": col, "row": row}
            self._cell_sweeps[agent_id] = active
            logger.info(f"[{agent_id}] sweep: unexplored cell ({col},{row}) — sweeping")

        action = active["sweep"].next_action((xyz[0], xyz[1]))
        if action.get("type") == "sweep_done":
            self.place_db.mark_swept(agent_id, active["col"], active["row"],
                                     observation.get("world_time", self.world_clock.now_text()))
            self._cell_sweeps.pop(agent_id, None)
            logger.info(f"[{agent_id}] sweep: swept ({active['col']},{active['row']}) — breadcrumb dropped")
            return None
        action["_sweep_interrupt"] = True
        return action

    def _should_sweep_here(self, observation: dict) -> bool:
        """True when the agent's current grid cell has no community place cell yet
        (#11.1). The sweep fires on **entry to any un-swept cell** — whether the
        agent is traveling through or stopped — so the world's grid districts get
        mapped as APCs roam (user, 2026-07-03: "sweep on entry to any new cell,"
        even mid-travel). The first APC into a cell pays the ~9-tick 360; every
        APC after reuses the community breadcrumb (``is_explored``), so detours
        fall off as the map fills in. Needs a bounded grid (a cell center to walk
        to) + a PlaceDB (somewhere to drop the breadcrumb).
        """
        col, row = self._cell_col_row(observation.get("grid"))
        if col is None or self.place_db is None:
            return False
        return not self.place_db.is_explored(col, row)

    def _episodic(self, agent_id: str) -> EpisodicLog:
        """Load (and cache) this agent's append-only episodic event log."""
        log = self._episodic_log.get(agent_id)
        if log is None:
            log = EpisodicLog(self._agents_dir / agent_id / "episodes.jsonl")
            self._episodic_log[agent_id] = log
        return log

    def _record_episode(self, agent_id: str, observation: dict, action: dict, result: dict) -> None:
        """Append a structured "what happened" event for this acted tick.

        Captures where (grid cell + place), who was seen (named only), what the
        agent did, and the outcome — so overnight runs keep a queryable history
        beyond the 30-item memory.json window.
        """
        grid = observation.get("grid") or {}
        place_list = observation.get("place") or []
        characters = (observation.get("seen") or {}).get("characters") or []
        saw = [c.get("label") for c in characters
               if c.get("label") and not is_anonymous(c.get("label", ""))]
        self._episodic(agent_id).record({
            "world_time": observation.get("world_time", ""),
            "grid_cell": grid.get("key"),
            "place": place_list[0] if place_list else None,
            "saw": saw,
            "action": action.get("type"),
            "outcome": result.get("status") or result.get("success"),
        })

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

    def _direction_places(self, agent_id: str, location, rotation) -> dict[str, dict]:
        """Lizard-brain navigation sense: the grid cell one step (~15m) ahead in
        each walkable direction, plus what the SHARED world map knows about it.

        Reads PlaceDB (shared by every avatar), so one agent's discoveries steer
        another's — Maren's named cells show up in Dufus's options. Each value is
        ``{"cell": "col,row", "place": <name or None>}``; ``place is None`` means
        the cell is still unexplored, a good place to go map next.
        """
        xyz = _loc_xyz(location)
        yaw = _yaw_of(rotation)
        if xyz is None or yaw is None:
            return {}
        out: dict[str, dict] = {}
        for direction, offset in _DIRECTION_YAW_OFFSET.items():
            tx, ty, _ = _offset_location(*xyz, yaw + offset, _STEP_DISTANCE)
            grid = self.world_grid.locate(tx, ty)
            col, row = self._cell_col_row(grid)
            name = None
            if self.place_db and col is not None:
                known = self.place_db.get_place(col, row)
                name = known.get("name") if known else None
            out[direction] = {"cell": grid.get("key", "?"), "place": name}
        return out

    def _record_place(self, agent_id: str, location, place_name) -> None:
        """Persist an LLM-named place into PlaceDB and the legacy spatial map."""
        name = str(place_name or "").strip()
        xyz = _loc_xyz(location)
        if not name or name.lower() in ("null", "none", "unknown") or xyz is None:
            return
        # Write to PlaceDB (primary store — permanent, compass-structured).
        if self.place_db:
            grid = self.world_grid.locate(xyz[0], xyz[1])
            col, row = self._cell_col_row(grid)
            if col is not None:
                stored = self.place_db.set_name(agent_id, col, row, name, self.world_clock.now_text())
                if stored:
                    logger.info(f"[{agent_id}] place named: '{name}' at {grid.get('key')}")
                else:
                    # Cell already community-named (first name wins). A *different*
                    # name becomes an APC-owned place cell — a named ~3m box at an
                    # XY offset from the community anchor (#11.2) — instead of
                    # being silently dropped ("My Home" inside "village square").
                    existing = self.place_db.get_place(col, row)
                    existing_name = ((existing or {}).get("name") or "").strip().lower()
                    if existing_name and existing_name != name.lower():
                        center = self.world_grid.cell_center(col, row)
                        if center is not None and self.place_db.add_owned_place(
                                agent_id, col, row, name,
                                dx=xyz[0] - center[0], dy=xyz[1] - center[1]):
                            logger.info(f"[{agent_id}] owned place: '{name}' at {grid.get('key')}")
        # Also write to the legacy spatial map (keeps direction previews working).
        smap = self._spatial_map(agent_id)
        smap.ingest(xyz[0], xyz[1], [{"label": name, "confidence": 0.8, "distance": "near"}])
        smap.save(self._agents_dir / agent_id / "spatial_map.json")

    def _direction_target(self, observation: dict, direction: str) -> list[float] | None:
        """Resolve a facing-relative direction to a world location one step away."""
        xyz = _loc_xyz(observation.get("location"))
        yaw = _yaw_of(observation.get("rotation"))
        offset = _DIRECTION_YAW_OFFSET.get(str(direction or "").strip().lower())
        if xyz is None or yaw is None or offset is None:
            return None
        return _offset_location(*xyz, yaw + offset, _STEP_DISTANCE)

    def _execute_world_action(self, agent: Agent, action: dict, observation: dict) -> dict:
        """Execute a validated action in Unreal, resolving direction-relative movement.

        ``wander`` is a forward step; ``walk_to`` with a ``direction`` becomes a
        walk to a world location computed from the agent's current facing.
        """
        action = self._resolve_action_actor_refs(action)
        t = action.get("type")

        if t == "observe":
            return {"status": "success", "image_path": observation.get("image_path"), "action": "observe"}

        # Sweep observation (#7/#11.1 live half): no bridge-side handler needed —
        # composed from existing primitives (set_facing + capture + perceive +
        # ingest_compass), the same path the wake look-around uses.
        if t == "observe_heading":
            return self._execute_sweep_observe(agent, action, observation)

        if t == "wander" or (t == "walk_to" and action.get("direction")):
            direction = action.get("direction") or "forward"
            target = self._direction_target(observation, direction)
            if target is None and t == "wander":
                # No yaw available — legacy random step so wander never dead-ends.
                import random
                xyz = _loc_xyz(observation.get("location"))
                if xyz:
                    target = [xyz[0] + random.uniform(-2500, 2500), xyz[1] + random.uniform(-2500, 2500), xyz[2]]
            if target is None:
                return {"status": "accepted", "action": "idle",
                        "note": f"cannot resolve direction '{direction}' — no location/facing"}
            result = self.bridge.execute_action(
                agent.bound_unreal_actor_name, {"type": "walk_to", "location": target}
            )
            if result.get("error"):
                return {"status": "accepted", "action": "idle",
                        "note": f"walk {direction} blocked: {result.get('error')}"}
            return result

        # walk_to a named place ("village square") — resolve the name to a world
        # location via PlaceDB + the world grid, instead of letting the bridge
        # short-circuit string targets to idle.
        if (t == "walk_to" and isinstance(action.get("target_location"), str)
                and not action.get("location") and not action.get("target_actor")):
            target = self._resolve_place_target(agent.agent_id, action["target_location"], observation)
            if target is not None:
                action = {**action, "location": target}

        # walk_to a known character: stop a personal-space standoff short of them
        # (B7b) instead of walking into their face. The bridge's move-to-actor
        # drives the whole gap closed, and the ~9 s decision cadence means the
        # reflex stop in _observe_agent can't catch an approach that closes it
        # within a single tick — so terminate the approach short at the command
        # level. Engine-agnostic: compute a stop point and reuse walk_to location.
        # Falls through unchanged if either position is unknown (e.g. the player).
        if (t == "walk_to" and action.get("target_actor")
                and not action.get("location") and not action.get("direction")):
            me = _loc_xyz(observation.get("location"))
            tgt = None
            if me is not None:
                tf = self.bridge.get_character_transform(action["target_actor"])
                tgt = _loc_xyz((tf or {}).get("location"))
            if me is not None and tgt is not None:
                dist = math.hypot(tgt[0] - me[0], tgt[1] - me[1])
                if dist <= _STANDOFF_CM:
                    return {"status": "accepted", "action": "idle",
                            "note": "already at greeting distance — did not close in"}
                f = (dist - _STANDOFF_CM) / dist
                action = {k: v for k, v in action.items() if k != "target_actor"}
                action["location"] = [me[0] + (tgt[0] - me[0]) * f,
                                      me[1] + (tgt[1] - me[1]) * f, tgt[2]]

        return self.bridge.execute_action(agent.bound_unreal_actor_name, action)

    def _execute_sweep_observe(self, agent: Agent, action: dict, observation: dict) -> dict:
        """Execute one sweep observation: turn in place to the absolute yaw,
        capture, perceive, and ingest the landmarks into the shared PlaceDB
        under that compass direction.

        Reuses the wake look-around's primitives (``set_facing`` +
        ``capture_view`` + the vision perceiver) — no engine-side handler
        exists or is needed. Degrades per-heading: a failed turn/capture/
        perception returns an error result and records nothing, but the sweep
        state machine has already advanced, so one bad heading never wedges
        the sweep. Runs only in the sequential phases (single-socket bridge;
        one heading = one tick).
        """
        agent_id = agent.agent_id
        yaw = float(action.get("yaw", 0.0))
        direction = yaw_to_compass(yaw)
        turn = self.bridge.set_facing(agent.bound_unreal_actor_name,
                                      observation.get("location"), yaw)
        if turn.get("error"):
            return {"status": "error", "action": "observe_heading", "direction": direction,
                    "error": f"turn failed: {turn['error']}"}
        time.sleep(0.25)  # let the rotated frame render before capturing
        image_path = self.bridge.capture_view(
            agent.bound_unreal_actor_name, agent_id, self._agents_dir, f"sweep_{direction}"
        )
        if not image_path:
            return {"status": "error", "action": "observe_heading", "direction": direction,
                    "error": "capture failed"}
        seen = self.perceiver.perceive(image_path, observation.get("known_characters") or [])
        if seen.get("error"):
            return {"status": "error", "action": "observe_heading", "direction": direction,
                    "error": f"perception failed: {seen['error']}"}
        landmarks = seen.get("landmarks") or []
        col, row = self._cell_col_row(observation.get("grid"))
        if self.place_db and col is not None and landmarks:
            self.place_db.ingest_compass(agent_id, col, row, direction, landmarks)
        return {"status": "success", "action": "observe_heading", "direction": direction,
                "yaw": yaw, "landmarks": len(landmarks), "image_path": image_path}

    def _pulse_sweep(self, agent: Agent) -> dict:
        """One tick for an agent mid-sweep — deterministic, no perception LLM.

        Builds a minimal observation (position + grid; no vision diff gate,
        which a deterministic step doesn't need), then continues the active
        sweep. When the sweep just finished (breadcrumb dropped), reports it
        and lets the next tick resume the normal perceive/decide path — the
        #10 sequencer directive re-issues the routine on its own.
        """
        agent_id = agent.agent_id
        observation = self.bridge.get_observation(
            agent.bound_unreal_actor_name, agent_id, self._agents_dir
        )
        grid, place = self._grid_and_place(agent_id, observation.get("location"))
        observation["grid"] = grid
        observation["place"] = place
        observation["world_time"] = self.world_clock.now_text()

        action = self._sweep_step(agent_id, observation, start=False)
        if action is None:
            agent.mark_ticked(self._agents_dir)
            return {"agent_id": agent_id, "action": "sweep_done", "grid": grid, "sweep": True}

        result = self._execute_world_action(agent, action, observation)
        agent.mark_ticked(self._agents_dir)
        return {"agent_id": agent_id, "action": action, "result": result,
                "grid": grid, "sweep": True}

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
            failures = self._frontier_failures.setdefault(agent_id, {})
            if result.get("error") or result.get("success") is False:
                # Block only with evidence the cell itself is unreachable: the
                # avatar is standing next to it and still can't enter, or the
                # same cell keeps failing. A transient no-path / never-started
                # error must not permanently poison the frontier.
                tx, ty = smap.cell_center(target["cell"])
                adjacent = math.hypot(tx - x, ty - y) <= smap.cell_size * 1.5
                attempts = failures.get(target["cell"], 0) + 1
                if adjacent or attempts >= _MAX_FRONTIER_FAILURES:
                    smap.mark_blocked(target["cell"])
                    failures.pop(target["cell"], None)
                    why = "adjacent and obstructed" if adjacent else f"{attempts} failed attempts"
                    logger.info(
                        f"[{agent_id}] frontier {target['cell']} blocked ({why}): {result.get('error')}"
                    )
                else:
                    failures[target["cell"]] = attempts
                    logger.info(
                        f"[{agent_id}] frontier {target['cell']} walk failed "
                        f"(attempt {attempts}/{_MAX_FRONTIER_FAILURES}, not blocking): {result.get('error')}"
                    )
            else:
                failures.pop(target["cell"], None)
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
        observation["world_time"] = self.world_clock.now_text()
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

    async def restart_day(self) -> dict:
        """Restart the sim from morning — a fresh day that keeps the world.

        Stops the sim if running, re-anchors the world clock to its configured
        morning start, and clears each agent's per-run runtime state (daily
        schedule, last activity, timers) so a new morning plan regenerates on the
        next start. Memories and place cells are intentionally **preserved** — the
        world keeps everything it has learned; only the day resets. (Contrast
        reset_agents, which also wipes memories + spatial maps.)
        """
        was_running = self.running
        if was_running:
            await self.stop_simulation()

        if not self.agents:
            self._load_agents(None)
            self._bind_agents()

        self.world_clock.reset()   # now_text() -> configured morning start

        agent_ids = []
        for agent in self.agents.values():
            agent.reset_runtime_state(self._agents_dir)
            agent_ids.append(agent.agent_id)

        logger.info(
            f"=== DAY RESTART === {len(agent_ids)} agent(s) reset to morning "
            f"({self.world_clock.now_text()}); memories + place cells preserved"
            f"{', sim stopped first' if was_running else ''}"
        )
        return {
            "status": "day_reset",
            "world_time": self.world_clock.now_text(),
            "stopped_simulation": was_running,
            "agents": agent_ids,
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
        self._frontier_failures.clear()
        self._scene_skips.clear()
        self._last_pos.clear()
        self._no_progress.clear()
        self.bridge.clear_scene_cache()

        failures = [r["agent_id"] for r in results if not r["teleported"]]
        logger.info(
            f"=== AGENTS RESET === {len(results)} agent(s)"
            f"{', sim stopped first' if was_running else ''}"
            f"{', teleport FAILED for: ' + ', '.join(failures) if failures else ''}"
        )
        return {"status": "reset", "stopped_simulation": was_running, "agents": results}

    async def reset_world_places(self) -> dict:
        """Wipe the shared place-cell DB so the world map starts from scratch.

        Unlike reset_agents (which preserves geography for reproducible re-runs),
        this clears place_cells, place_observations, and agent_visits entirely.
        Stops the sim first if running so no tick is mid-write. Agent JSON state
        (memories, spatial maps) is left untouched — run reset_agents for that.
        """
        was_running = self.running
        if was_running:
            await self.stop_simulation()

        # Resolve the DB even when the sim has never started this session.
        if self.place_db is None:
            if not self.agents:
                self._load_agents(None)
            if not self._agents_dir:
                return {"status": "error", "error": "No agents loaded — cannot locate world_places.db"}
            self.place_db = PlaceDB(self._agents_dir.parent / "world_places.db")

        removed = self.place_db.reset()
        logger.info(
            f"=== WORLD PLACES WIPED === place_cells={removed['place_cells']}, "
            f"place_observations={removed['place_observations']}, agent_visits={removed['agent_visits']}"
            f"{', sim stopped first' if was_running else ''}"
        )
        return {"status": "reset", "stopped_simulation": was_running, "removed": removed}

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

    def generate_world_grid(self, cell_size: float = 3000.0, padding: float = 800.0) -> dict:
        """Compute the fixed world grid from the current level's actor positions.

        Scans every actor, takes the min/max x/y plus padding as the world
        bounds, writes ``worlds/<level>/world_grid.json``, and swaps the live
        grid in place. Needs the editor open with PIE stopped (editor-world
        scan). Lived in the MCP tool until #3/2.4 moved it here so the runner
        (the bridge's sole owner) can serve it over HTTP.

        ``cell_size`` default is 3000 cm (30 m) — a grid cell is a *district*
        that holds several ~3 m place cells, not a place-sized tile (the 4 m
        default made grid cells ≈ place cells, collapsing the hierarchy).
        """
        level = self.bridge.get_current_level()
        if not level:
            return {"status": "error",
                    "error": "Could not determine current level — is Unreal running?"}

        actors = self.bridge.get_level_actors()
        points = [a["location"][:2] for a in actors
                  if isinstance(a.get("location"), list) and len(a["location"]) >= 2]
        if not points:
            return {"status": "error",
                    "error": "No actor positions returned — is the editor open (and PIE stopped)?"}

        xs, ys = [p[0] for p in points], [p[1] for p in points]
        bounds = {
            "min_x": min(xs) - padding, "min_y": min(ys) - padding,
            "max_x": max(xs) + padding, "max_y": max(ys) + padding,
        }
        path = self.worlds_dir / level / "world_grid.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"cell_size": cell_size, "bounds": bounds}, indent=2),
            encoding="utf-8",
        )
        self.world_grid = WorldGrid(cell_size=cell_size, bounds=bounds)
        return {
            "status": "generated",
            "level": level,
            "path": str(path),
            "actors_scanned": len(points),
            "bounds": bounds,
            "grid": self.world_grid.describe(),
        }

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
        """Translate a character reference in an action target into the bound
        Unreal actor name the bridge needs.

        The LLM only ever knows agents by their **display name** (that is all
        known_characters exposes), so a targeted action arrives as
        ``target_actor="Maren"`` — not the actor "APC_Maren_BP" the engine wants.
        This is the reverse of known_characters: match the reference against each
        agent's display name, actor label, or id (case-insensitively) and swap in
        the bound actor name. Non-matches (e.g. the human player) pass through.
        """
        resolved = dict(action)
        for key in ("target", "target_actor"):
            value = resolved.get(key)
            if isinstance(value, str):
                actor = self._actor_name_for(value)
                if actor:
                    resolved[key] = actor
        return resolved

    def _actor_name_for(self, ref: str) -> str | None:
        """Resolve a character reference (display name / actor label / agent id)
        to its bound Unreal actor name, case-insensitively; None if no match."""
        key = ref.strip().lower()
        if not key:
            return None
        for a in self.agents.values():
            if not a.has_unreal_binding:
                continue
            if key in {a.agent_id.lower(), a.display_name.lower(),
                       (a.bound_unreal_actor_label or "").lower()}:
                return a.bound_unreal_actor_name
        return None
