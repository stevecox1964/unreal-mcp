from __future__ import annotations

import asyncio
import json
import logging
import math
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .agent import Agent
from .action_validator import validate
from . import explorer
from .perception import VisionPerceiver
from . import cell_sweep
from .landmarks import merge_entries, scan_landmarks
from . import map_capture
from . import places_manifest
from . import planner
from . import place_visuals
from . import route_map
from . import route_planner
from . import sim_run
from .episodic_memory import EpisodicLog
from .place_db import PLACE_EXTENT_CM, PlaceDB, yaw_to_compass
from .social_memory import SocialMemory, is_anonymous
from .spatial_memory import SpatialMap
from .world_clock import WorldClock
from .world_grid import WorldGrid

logger = logging.getLogger("AgentRuntime")

# A frontier cell is only blocked after this many consecutive failed walk
# attempts — unless the avatar is already adjacent, which is proof enough.
_MAX_FRONTIER_FAILURES = 3

# Wake/new-place survey: absolute UE yaws for the four cardinal views. These
# labels and yaws are geographic, not relative to the avatar's initial facing.
_SWEEP_VIEWS = [
    ("N", 270.0),
    ("S", 90.0),
    ("E", 0.0),
    ("W", 180.0),
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

# Don't re-greet (#12.1): once an agent has spoken with someone, suppress the
# "you may greet a known person" interrupt for this many sim-minutes so they
# don't say hi every tick the person stays in view. A fresh encounter after the
# cooldown (or a new sim-day) greets again.
_GREET_COOLDOWN_MINUTES = 60
_NEARBY_CHARACTER_CM = 2500.0
_PLACE_ROAM_MARGIN_CM = 100.0

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
        # Every path that can observe/decide/act shares this gate: the automatic
        # loop, POST /tick, and POST /agents/{id}/tick. The active label is set
        # synchronously before acquiring the lock so competing requests return
        # busy immediately instead of queueing behind a long LLM call.
        self._tick_lock = asyncio.Lock()
        self._active_tick_entry: str | None = None

        # Explore-mode state (per agent).
        self.perceiver = VisionPerceiver()
        self._spatial: dict[str, SpatialMap] = {}   # agent_id -> loaded map (cache)
        self._social_mem: dict[str, SocialMemory] = {}  # agent_id -> acquaintance store (cache)
        self._episodic_log: dict[str, EpisodicLog] = {}  # agent_id -> episodic event log (cache)
        self._cell_sweeps: dict[str, dict] = {}      # agent_id -> in-progress unexplored-cell sweep
        self._last_cell: dict[str, str] = {}        # agent_id -> previous cell key, for nav edges
        self._frontier_failures: dict[str, dict[str, int]] = {}  # agent_id -> cell key -> consecutive failed walks
        self._scene_skips: dict[str, int] = {}      # agent_id -> consecutive scene-unchanged skips (gate liveness)
        self._nearby_ids: dict[str, frozenset[str]] = {}  # agent_id -> nearby APC ids on prior cheap sample
        self._last_pos: dict[str, tuple] = {}       # agent_id -> last (x, y), for stuck detection
        self._no_progress: dict[str, int] = {}      # agent_id -> consecutive "moving but didn't advance" ticks
        self._last_grid_place: dict[str, tuple] = {}  # agent_id -> (grid, place), reported even when LLM skipped
        self._routes: dict[str, dict] = {}          # agent_id -> cached grid-first route (#17/WP8)
        self._live_pos: dict[str, dict] = {}        # agent_id -> {x,y,yaw} last observed (#18 live map)

        # Fixed per-level grid; reloaded with the level in _load_agents.
        self.world_grid = WorldGrid()

        # In-world clock; reloaded with the level, anchored at start_simulation.
        self.world_clock = WorldClock()

        # SQLite place cell store — initialised in start_simulation once world dir is known.
        self.place_db: PlaceDB | None = None

        # Sim run tag (SR<n>) — allocated per-world in start_simulation, pushed to
        # the bridge (observation filenames) + memory (decision log) for attribution.
        self.sim_run_id: str = "SR0"

        # Agents whose first schedule step of this run has passed. Only that
        # first step may seed a missing scheduled place as the agent's own
        # place cell (wake-time initialization) — cleared per run.
        self._wake_stepped: set[str] = set()

        # True when this world has a places.json (WP6): the wake seed then
        # warns — an unresolvable scheduled place likely means the user forgot
        # to author it.
        self._manifest_present = False

        # (agent_id, day) pairs whose daily plan was already validated against
        # PlaceDB (WP6 D5) — once per agent per day; cleared per run.
        self._validated_plans: set[tuple[str, str]] = set()

    # Lifecycle

    async def start_simulation(
        self,
        tick_seconds: int = 1,
        active_agents: list[str] | None = None,
        mode: str = "live",
    ) -> dict:
        if (isinstance(tick_seconds, bool)
                or not isinstance(tick_seconds, (int, float))
                or tick_seconds <= 0):
            return {"status": "error", "error": "tick_seconds must be positive"}
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
        self._nearby_ids.clear()
        self._last_pos.clear()
        self._no_progress.clear()
        self._routes.clear()
        self._live_pos.clear()

        self._load_agents(active_agents)
        if active_agents:
            for agent in self.agents.values():
                agent.set_active(True, self._agents_dir)
        bound_count = self._bind_agents()

        # Open (or create) the SQLite place cell store for this world.
        if self._agents_dir is not None:
            db_path = self._agents_dir.parent / "world_places.db"
            self.place_db = PlaceDB(db_path)

            # Authored ground truth, loaded before any tick so scheduled places
            # resolve without wake-seeding. Two sources feed the same manifest
            # pipeline (#23): Landmark_* actors in the level (ground truth,
            # wins on collision) and places.json (fallback / no-Unreal path).
            self._manifest_present = False
            try:
                level_actors = self.bridge.get_level_actors()
            except Exception as e:
                logger.warning(f"get_level_actors() failed ({e}) — landmarks skipped, "
                               f"places.json only")
                level_actors = []
            scanned = scan_landmarks(level_actors)
            landmarks = scanned["entries"]
            if scanned["suspects"]:
                logger.error(f"landmark suspects ignored: {scanned['suspects']}")
            manifest = places_manifest.load_manifest(self._agents_dir.parent / "places.json")
            if not landmarks:
                logger.info(f"landmarks: 0 (level) — no Landmark_* actors found, "
                           f"places.json: {len(manifest)}")
            merged = merge_entries(landmarks, manifest)
            if merged:
                summary = places_manifest.apply_manifest(self.place_db, self.world_grid, merged)
                logger.info(f"landmarks: {len(landmarks)} (level), places.json: {len(manifest)}, "
                           f"applied: {summary}")
                self._manifest_present = True

            # Allocate this run's SR<n> tag (per-world) and push it everywhere the
            # run needs stamping: observation filenames + the decision log.
            self.sim_run_id = sim_run.allocate_run(self._agents_dir.parent)
            sim_run.set_active_run(self.sim_run_id)
            self.bridge.sim_run_id = self.sim_run_id
            self.memory.sim_run_id = self.sim_run_id
            logger.info(f"Sim run {self.sim_run_id} — observations + decision log tagged")

        # New run = a fresh wake for every agent (wake-time place seeding rearms).
        self._wake_stepped.clear()
        self._validated_plans.clear()

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
            "tick_in_progress": self._active_tick_entry is not None,
            "active_tick_entry": self._active_tick_entry,
            "agent_count": len(self.agents),
            "agents": [self._agent_summary(a) for a in self.agents.values()],
        }

    def recent_events(self, limit: int = 20) -> list[dict]:
        """Decision-feed entries from only the active simulation run."""
        return self.memory.get_recent_events(limit, sim_run_id=self.sim_run_id) if self.memory else []

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
                    result = await self.tick(entry="automatic_tick")
                except Exception as e:
                    logger.error(f"Tick error: {e}")
                duration = time.monotonic() - started
                self._last_tick_duration = duration
                if not result or result.get("status") != "busy":
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

                # Sequencer directive at the TRUE spawn position, before any
                # first action can move the agent: seeds a first-time scheduled
                # place right here and tells the orient prompt, with ground
                # truth, whether the agent is already where it should be —
                # instead of letting the LLM guess and walk off (Maren, SR2).
                directive = self._wake_directive(agent, loc, grid, world_time)
                visual_place_name = (
                    (directive or {}).get("place")
                    if (directive or {}).get("status") == "act" else None
                )
                place_image = None
                if self.place_db and col is not None:
                    place_image = self.place_db.current_place_image(
                        agent.agent_id, col, row, visual_place_name
                    )

                if place_image:
                    # A complete shared visual memory is the survey gate. A
                    # name/sweep breadcrumb alone is not enough.
                    self._link_place_visual_history(agent.agent_id, place_image)
                    # Pass personal familiarity so the orient prompt can tell the
                    # agent whether this is THEIR place or just a place they've
                    # visited, giving them the signal to stay vs. move on.
                    logger.info(
                        f"[{agent.agent_id}] WAKE {world_time} at mapped place "
                        f"'{place_image.get('name') or (known_place or {}).get('name') or visual_place_name or grid.get('key')}' "
                        f"(visits={familiarity.get('visit_count',0)}, "
                        f"named_by_me={familiarity.get('named_by_me',False)}) — skipping sweep"
                    )
                    memories = self.memory.get_relevant_memories(agent.agent_id)
                    context = {
                        "world_time": world_time, "location": loc, "rotation": rot,
                        "grid": grid, "place": place, "views": [],
                        "directions": self._direction_places(agent.agent_id, loc, rot),
                        "known_place": (place_image.get("name")
                                        or (known_place or {}).get("name")
                                        or visual_place_name),
                        "place_image_id": place_image["place_image_id"],
                        "place_description": place_image.get("description", ""),
                        "familiarity": familiarity,
                        "schedule": directive,
                    }
                    needs_orient.append((agent, context, memories))
                    continue

                known_chars = [
                    a.display_name
                    for a in self.agents.values()
                    if a.agent_id != agent.agent_id and a.has_unreal_binding
                ]
                views = self._wake_sweep(agent, loc, rot, known_chars)
                place_image = self._ingest_wake_views(
                    agent.agent_id, col, row, views, world_time, visual_place_name
                )

                memories = self.memory.get_relevant_memories(agent.agent_id)
                context = {
                    "world_time": world_time, "location": loc, "rotation": rot,
                    "grid": grid, "place": place, "views": views,
                    "directions": self._direction_places(agent.agent_id, loc, rot),
                    "known_place": None,
                    "place_image_id": (place_image or {}).get("place_image_id"),
                    "place_description": (place_image or {}).get("description", ""),
                    "familiarity": familiarity,
                    "schedule": directive,
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
                    forward = next((v for v in views if v["direction"] == "E"), None)
                    wake_obs = {
                        "location": loc, "rotation": rot,
                        "image_path": forward["image_path"] if forward else None,
                        # Named-place travel must route from the true wake cell;
                        # omitting this made _execute_routed_walk fall back to a
                        # brief direct beeline at the final place anchor.
                        "grid": grid, "place": place,
                        "world_time": context.get("world_time"),
                        "schedule": context.get("schedule"),
                    }
                    first_result = self._execute_world_action(agent, first_action, wake_obs)

                self.memory.record(
                    agent_id=agent.agent_id,
                    observation={
                        "wake": True, "world_time": context["world_time"], "location": loc,
                        "grid": grid, "place": place,
                        "place_image_id": context.get("place_image_id"),
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

    def _ingest_wake_views(self, agent_id: str, col, row,
                           views: list[dict], world_time: str,
                           place_name: str = None) -> dict | None:
        """Record a wake sweep's views in the shared PlaceDB.

        Each view's landmarks feed the cell's compass-observation table, and a
        non-empty sweep drops the community breadcrumb (``mark_swept``): the
        wake look-around observed five headings from inside the cell, which
        counts as the district's community sweep (user, 2026-07-06). Scheduled
        "act" ticks are sweep-exempt, so without this an agent working its own
        cell (Dufus at home) would leave its district unexplored on the map
        forever. No-op without a PlaceDB or grid indices; an empty sweep
        (no transform / every heading failed) records nothing.
        """
        if not self.place_db or col is None:
            return None
        for v in views:
            if v.get("landmarks"):
                self.place_db.ingest_compass(
                    agent_id, col, row, yaw_to_compass(v["yaw"]), v["landmarks"]
                )
        image = self._save_place_visual(agent_id, col, row, views, place_name)
        if views and self.place_db.mark_swept(agent_id, col, row, world_time):
            logger.info(
                f"[{agent_id}] wake: community place cell swept at ({col},{row}) "
                f"— breadcrumb dropped"
            )
        return image

    def _wake_sweep(self, agent: Agent, loc, rot, known_characters: list[str]) -> list[dict]:
        """Capture the four absolute cardinal views of a new place.

        Turn in 90-degree steps, capture a view at each, perceive it (VLM turns
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
        for direction, yaw in _SWEEP_VIEWS:
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

    def _world_relative_path(self, path: str | Path) -> str:
        """Return a world-relative generated-artifact path when possible."""
        candidate = Path(path).resolve()
        world_root = self._agents_dir.parent.resolve()
        try:
            return str(candidate.relative_to(world_root))
        except ValueError:
            return str(candidate)

    def _save_place_visual(self, agent_id: str, col: int, row: int,
                           views: list[dict], place_name: str = None) -> dict | None:
        """Compose and register a complete four-view visual memory."""
        if self.place_db is None or col is None:
            return None
        by_direction = {
            str(view.get("direction", "")).upper(): view
            for view in views if view.get("image_path")
        }
        if any(direction not in by_direction for direction in place_visuals.CARDINAL_DIRECTIONS):
            logger.warning(
                f"[{agent_id}] place visual ({col},{row}) incomplete — "
                f"have {sorted(by_direction)}; needs N/S/E/W"
            )
            return None

        shared_dir = self._agents_dir.parent / "places" / "images"
        composite_path = shared_dir / f"{uuid.uuid4().hex}.png"
        sources = {d: by_direction[d]["image_path"] for d in place_visuals.CARDINAL_DIRECTIONS}
        try:
            place_visuals.build_place_composite(sources, composite_path)
            description = "\n".join(
                f"{d}: {str(by_direction[d].get('caption') or '').strip()}"
                for d in place_visuals.CARDINAL_DIRECTIONS
                if str(by_direction[d].get("caption") or "").strip()
            )
            image = self.place_db.record_place_image(
                agent_id, col, row,
                self._world_relative_path(composite_path),
                {d: self._world_relative_path(sources[d])
                 for d in place_visuals.CARDINAL_DIRECTIONS},
                description=description,
                place_name=place_name,
            )
            self._expose_place_visual_history(agent_id, image)
            logger.info(
                f"[{agent_id}] place visual saved: {image['place_image_id']} "
                f"({image['place_kind']} {col},{row} revision {image['revision']})"
            )
            return image
        except Exception as e:
            if composite_path.exists():
                composite_path.unlink()
            logger.error(f"[{agent_id}] place visual save failed: {e}")
            return None

    def _link_place_visual_history(self, agent_id: str, image: dict) -> None:
        """Link one shared place image into the APC's inspectable history."""
        linked = self.place_db.link_agent_to_place_image(agent_id, image["place_image_id"])
        if not linked:
            return
        self._expose_place_visual_history(agent_id, linked)

    def _expose_place_visual_history(self, agent_id: str, image: dict) -> None:
        """Expose an already-recorded visual-history link as an image file."""
        place_visuals.expose_in_agent_history(
            self.place_db.absolute_image_path(image),
            self._agents_dir / agent_id / "observations",
            image["place_image_id"],
        )

    async def _run_tick_entry(self, entry: str, operation) -> dict:
        """Run one tick-like operation, or reject it without waiting.

        The event loop cannot switch tasks between the active-entry check and
        assignment, which makes the busy decision atomic for this manager.
        ``asyncio.Lock`` remains the actual critical-section guard.
        """
        if self._active_tick_entry is not None:
            return {
                "status": "busy",
                "error": "A simulation tick is already in progress",
                "requested_entry": entry,
                "active_entry": self._active_tick_entry,
            }

        self._active_tick_entry = entry
        await self._tick_lock.acquire()
        try:
            return await operation()
        finally:
            self._tick_lock.release()
            self._active_tick_entry = None

    async def tick(self, entry: str = "tick") -> dict:
        """Run a whole-simulation tick unless another tick entry is active."""
        return await self._run_tick_entry(entry, self._tick_impl)

    async def _tick_impl(self) -> dict:
        """Run one simulation tick across all ready agents.

        Three phases keep Unreal bridge calls sequential while LLM calls
        run in parallel across agents:
          1. Observe (sequential, bridge): cheap state gate, then screenshot only
             for agents whose cognition was rearmed
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
            self._set_activity(agent, "sampling")
            observations[agent.agent_id] = self._observe_agent(agent)
        self._attach_nearby_characters(observations)

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
        """Run one agent immediately unless another tick entry is active."""
        return await self._run_tick_entry(
            f"agent_tick:{agent_id}", lambda: self._pulse_agent_impl(agent_id)
        )

    async def _pulse_agent_impl(self, agent_id: str) -> dict:
        """Single-agent tick implementation; caller owns the shared tick lock."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": f"Agent '{agent_id}' not loaded"}
        if agent.agent_id in self._cell_sweeps:
            return self._pulse_sweep(agent)
        if self.mode == "explore":
            return self._pulse_explore(agent)
        self._set_activity(agent, "sampling")
        # This endpoint is an explicit operator pulse. It intentionally bypasses
        # settled-agent suppression so "pulse" still means "think now".
        obs = self._observe_agent(agent, force_cognition=True)
        if obs is None:
            grid, place = self._last_grid_place.get(agent_id, (None, []))
            return {"agent_id": agent_id, "action": "idle", "reason": "scene_unchanged",
                    "grid": grid, "place": place}
        self._attach_nearby_characters({agent_id: obs})
        self._set_activity(agent, "thinking")
        decision = await asyncio.to_thread(self._perceive_and_decide, agent, obs)
        return self._act_agent(agent, decision, obs)

    # ── Tick phases ──────────────────────────────────────────────────────────

    def _observe_agent(self, agent: Agent, force_cognition: bool = False) -> dict | None:
        """Phase 1: gather world state via bridge.

        Returns an observation dict, or None if the scene is unchanged
        (scene_unchanged agents are skipped by phases 2 and 3).
        """
        agent_id = agent.agent_id
        # The lizard-brain gate must run before camera capture. In particular,
        # a stationary APC at its scheduled mapped place should not create a
        # duplicate PNG merely to discover that cognition is asleep.
        state_reader = getattr(self.bridge, "get_character_state", None)
        if callable(state_reader):
            observation = state_reader(agent.bound_unreal_actor_name)
        else:
            # Compatibility for engine-neutral adapters that have not yet split
            # cheap state sampling from their observation implementation.
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
                if observation["place_context"]:
                    observation["place_image_id"] = observation["place_context"].get(
                        "place_image_id"
                    )

        # Live map telemetry (#18): remember where this agent was last observed.
        self._record_live_pos(agent_id, observation)

        # Proximity is a cheap deterministic event source. It must run before
        # the visual-diff gate because _attach_nearby_characters normally runs
        # after this method, when a suppressed observation is already gone.
        nearby_now = self._nearby_agent_ids(agent_id, _loc_xyz(observation.get("location")))
        nearby_before = self._nearby_ids.get(agent_id)
        nearby_changed = nearby_before is not None and nearby_now != nearby_before
        self._nearby_ids[agent_id] = nearby_now

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

        # A completed place survey is durable visual context. While the APC is
        # intentionally settled there, routine pixel changes do not trigger
        # another paid VLM observation. Explicit/manual, schedule, proximity,
        # blocker, and stuck events remain separate transient cognition paths.
        try:
            mapped_schedule = self._existing_schedule_directive(agent, observation)
        except Exception as e:
            logger.warning(f"[{agent_id}] mapped-place cognition gate failed: {e}")
            mapped_schedule = None
        mapped_block = (mapped_schedule or {}).get("block") or {}
        mapped_settled = bool(
            mapped_schedule
            and mapped_schedule.get("status") == "act"
            and mapped_block.get("place")
            and not mapped_schedule.get("transition")
            and not moving
        )
        mapped_schedule_event = bool(
            mapped_schedule
            and (mapped_schedule.get("transition")
                 or mapped_schedule.get("status") == "travel"
                 or (mapped_schedule.get("status") == "act" and moving))
        )
        mapped_visual = None
        col, row = self._cell_col_row(grid)
        if self.place_db and col is not None and mapped_block.get("place"):
            mapped_visual = self.place_db.current_place_image(
                agent_id, col, row, mapped_block["place"]
            )
            if mapped_visual:
                observation["place_image_id"] = mapped_visual["place_image_id"]
        mapped_event = force_cognition or nearby_changed or mapped_schedule_event
        if (mapped_visual and mapped_settled and not stuck
                and "blocker" not in observation and not mapped_event):
            agent.mark_ticked(self._agents_dir)
            logger.info(
                f"[{agent_id}] place visual {mapped_visual['place_image_id']} supplies context — "
                "settled routine sampled; VLM sleeping"
            )
            self._pie_activity(agent_id, "state sampled (mapped place)")
            return None

        # An event opened cognition (or the place is not yet durably mapped).
        # Render exactly one routine frame now; no image file exists on the
        # settled mapped-place return path above.
        capture_observation = getattr(self.bridge, "capture_routine_observation", None)
        if callable(capture_observation):
            observation = capture_observation(
                agent.bound_unreal_actor_name, agent_id, self._agents_dir, observation
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
            try:
                schedule = self._existing_schedule_directive(agent, observation)
            except Exception as e:
                logger.warning(f"[{agent_id}] cheap schedule gate failed: {e}")
                schedule = None
            block = (schedule or {}).get("block") or {}
            settled = bool(
                schedule
                and schedule.get("status") == "act"
                and block.get("place")
                and not schedule.get("transition")
                and not moving
            )
            schedule_event = bool(
                schedule
                and (schedule.get("transition")
                     or schedule.get("status") == "travel"
                     or (schedule.get("status") == "act" and moving))
            )
            event = force_cognition or nearby_changed or schedule_event
            if (settled and not stuck and not blocked and not event):
                agent.mark_ticked(self._agents_dir)
                logger.info(
                    f"[{agent_id}] grid={grid.get('key') if grid else '?'} "
                    f"place={observation.get('place_context', {}) or place or 'unknown'} "
                    "— settled at scheduled place, state sampled; cognition sleeping"
                )
                self._pie_activity(agent_id, "state sampled (settled)")
                return None
            if (not stuck and not blocked and not event
                    and (moving or skips % _STATIONARY_REDECIDE_TICKS != 0)):
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
            elif force_cognition:
                why = "manual pulse"
            elif nearby_changed:
                why = "nearby characters changed"
            elif schedule_event:
                why = "schedule or place state changed"
            else:
                why = f"stationary {skips} ticks"
            logger.info(
                f"[{agent_id}] {why} — re-deciding to pick a new direction"
            )

        self._scene_skips[agent_id] = 0
        return observation

    def _nearby_agent_ids(self, agent_id: str, xyz) -> frozenset[str]:
        """Nearby APC ids from cached transforms; no bridge or model work."""
        if xyz is None:
            return frozenset()
        return frozenset(
            other_id for other_id, pos in self._live_pos.items()
            if other_id != agent_id
            and math.hypot(pos["x"] - xyz[0], pos["y"] - xyz[1]) <= _NEARBY_CHARACTER_CM
        )

    def _existing_schedule_directive(self, agent: Agent,
                                     observation: dict) -> dict | None:
        """Resolve the persisted schedule against current geometry, model-free.

        This is only a cognition gate. It never calls ``ensure_daily_plan`` and
        never wake-seeds a missing place. The full schedule attachment remains
        in the cognition phase, where a missing/new-day plan may be generated.
        """
        world_time = observation.get("world_time", "")
        day = planner.day_of(world_time)
        schedule = getattr(agent, "daily_schedule_blocks", None)
        if not schedule or getattr(agent, "daily_schedule_day", "") != day:
            return None
        minute = planner.minute_of_day(world_time)
        block = planner.current_block(schedule, minute)
        if block is None:
            return planner.step(
                schedule, minute, current_place=None,
                prev_activity=getattr(agent, "last_activity", None), at_place=None,
            )
        if not block.get("place"):
            return None
        at_place = self._at_scheduled_place(
            agent.agent_id, block, observation, seed_if_unknown=False,
        )
        if at_place is None:
            return None
        place_context = observation.get("place_context") or {}
        place_names = observation.get("place") or []
        current_place = place_context.get("name") or (place_names[0] if place_names else None)
        return planner.step(
            schedule, minute, current_place=current_place,
            prev_activity=getattr(agent, "last_activity", None), at_place=at_place,
        )

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
            self._save_perception_evidence(agent_id, observation, seen)

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
        # who this agent has met (e.g. greet someone, seek out a friend). Tag each
        # with recently_greeted (#12.1) so the reaction gate won't re-greet someone
        # just spoken with.
        acquaintances = self._social(agent_id).acquaintances()
        observation["acquaintances"] = self._mark_recent_greetings(
            acquaintances, observation.get("world_time"))
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
            self._validate_schedule(agent, schedule, planner.day_of(world_time))
            pc = observation.get("place_context") or {}
            place_list = observation.get("place") or []
            current_place = pc.get("name") or (place_list[0] if place_list else None)
            minute = planner.minute_of_day(world_time)
            # Geometric "am I already there?" beats name matching: on a fresh
            # world nothing is named yet, and the old name-only check sent an
            # agent hunting for the place it was standing at (Maren's wake bug).
            # (Normally the spool-up already consumed the wake seed at the true
            # spawn — this is the no-spool-up fallback.) Only a step that had
            # real position data consumes the once-per-run seed chance.
            wake = agent.agent_id not in self._wake_stepped
            if (_loc_xyz(observation.get("location")) is not None
                    and self._cell_col_row(observation.get("grid"))[0] is not None):
                self._wake_stepped.add(agent.agent_id)
            at_place = self._at_scheduled_place(
                agent.agent_id, planner.current_block(schedule, minute),
                observation, seed_if_unknown=wake,
            )
            observation["schedule"] = planner.step(
                schedule, minute,
                current_place=current_place, prev_activity=agent.last_activity,
                at_place=at_place,
            )
            self._attach_route_progress(agent.agent_id, observation)
        except Exception as e:
            logger.warning(f"[{agent.agent_id}] schedule step failed: {e}")
            observation["schedule"] = None

    def _attach_route_progress(self, agent_id: str, observation: dict) -> None:
        """Narrate the cached grid-first route on a travel tick (#17/WP8).

        Attaches ``schedule["route"] = {leg, total, to_cell, heading}`` when
        the previous tick's cached route is for this directive's place — pure
        legibility for the prompt and the decision log; the LLM contract
        (walk_to target_location) is unchanged.
        """
        directive = observation.get("schedule") or {}
        route = self._routes.get(agent_id)
        if (directive.get("status") != "travel" or not route
                or route["destination"] != directive.get("place")):
            return
        path, leg = route["path"], route["leg"]
        cell = path[min(leg, len(path) - 1)]
        center = self.world_grid.cell_center(*cell)
        xyz = _loc_xyz(observation.get("location"))
        heading = None
        if center is not None and xyz is not None:
            dx, dy = center[0] - xyz[0], center[1] - xyz[1]
            if dx or dy:
                heading = yaw_to_compass(math.degrees(math.atan2(dy, dx)))
        directive["route"] = {"leg": min(leg, max(len(path) - 1, 1)),
                              "total": max(len(path) - 1, 1),
                              "to_cell": list(cell), "heading": heading}

    def _validate_schedule(self, agent: Agent, schedule: list | None, day: str) -> list:
        """Fail loud at plan time: warn for schedule blocks whose place resolves
        to nothing in PlaceDB (WP6 D5) — the agent will hunt for it; the fix is
        authoring it in places.json. Resolves through the same chain as
        ``_at_scheduled_place`` (community name, else owned place). Runs at
        most once per (agent_id, day); returns the bad blocks (for tests),
        ``[]`` when cached or nothing to check.
        """
        key = (agent.agent_id, day)
        if key in self._validated_plans or self.place_db is None:
            return []
        self._validated_plans.add(key)
        bad = []
        for block in schedule or []:
            name = str(block.get("place") or "").strip()
            if not name:
                continue
            if self.place_db.find_named_cell(name) is not None:
                continue
            if self.place_db.find_owned_place(name, preferred_owner=agent.agent_id) is not None:
                continue
            bad.append(block)
            logger.warning(
                f"[{agent.agent_id}] schedule {block.get('start')}-{block.get('end')} "
                f"'{block.get('activity')}' place '{name}' resolves to NOTHING — "
                f"agent will hunt; author it in places.json")
        return bad

    def _wake_directive(self, agent: Agent, loc, grid: dict | None,
                        world_time: str) -> dict | None:
        """Sequencer directive for the spool-up wake, at the true spawn spot.

        Runs BEFORE the orient LLM call can move the agent: generates the
        day's schedule, seeds a first-time scheduled place at the spawn
        position (the once-per-run ``seed_if_unknown``), and returns
        ``planner.step``'s directive so the wake prompt can state with ground
        truth whether the agent is already where it should be. Without this,
        the orient prompt asked the LLM to guess — Maren guessed "walk to the
        truck" while standing next to it, and the late per-tick seed then
        stamped her place mid-walk (SR2). Returns None on any failure (the
        wake prompt falls back to its generic guidance).
        """
        try:
            ask = getattr(self.llm, "ask", None)
            schedule = planner.ensure_daily_plan(
                agent, planner.day_of(world_time),
                ask=(lambda p: ask(agent, p)) if ask else None,
                agents_dir=self._agents_dir,
            )
            self._validate_schedule(agent, schedule, planner.day_of(world_time))
            minute = planner.minute_of_day(world_time)
            obs = {"location": loc, "grid": grid}
            seed = agent.agent_id not in self._wake_stepped
            if (_loc_xyz(loc) is not None
                    and self._cell_col_row(grid)[0] is not None):
                self._wake_stepped.add(agent.agent_id)
            at_place = self._at_scheduled_place(
                agent.agent_id, planner.current_block(schedule, minute),
                obs, seed_if_unknown=seed,
            )
            return planner.step(schedule, minute, current_place=None,
                                prev_activity=None, at_place=at_place)
        except Exception as e:
            logger.warning(f"[{agent.agent_id}] wake directive failed: {e}")
            return None

    def _at_scheduled_place(self, agent_id: str, block: dict | None,
                            observation: dict, seed_if_unknown: bool = False) -> bool | None:
        """Is the agent physically at the active block's place? (None = unknown.)

        Resolves the place through the same chain as walk_to: a community-named
        cell means "there" = standing in that grid cell (a 30 m district); an
        owned place cell means "there" = inside its extent box (9x9 m around
        the anchor+offset point, #11.2).

        ``seed_if_unknown`` (the agent's first schedule step of a run — wake):
        if the place resolves to nothing at all, it is created as the agent's
        own place cell centered where the agent stands. The editor placement
        is the agent's day-start spot by convention, so "wake at your stall"
        works on a fresh world instead of sending the agent off hunting for a
        name no one has recorded yet (first-time place-cell initialization).
        """
        name = str((block or {}).get("place") or "").strip()
        if not name or self.place_db is None:
            return None
        xyz = _loc_xyz(observation.get("location"))
        col, row = self._cell_col_row(observation.get("grid"))
        if xyz is None or col is None:
            return None

        end = self._resolve_place_endpoint(agent_id, name)
        if end is None:
            if not seed_if_unknown:
                return None
            center = self.world_grid.cell_center(col, row)
            if center is None:
                return None
            if self.place_db.add_owned_place(agent_id, col, row, name,
                                             dx=xyz[0] - center[0],
                                             dy=xyz[1] - center[1],
                                             source="wake-seed"):
                # With a places.json the seed is a fallback that shouldn't fire:
                # an unresolvable scheduled place likely means it wasn't authored.
                log = logger.warning if self._manifest_present else logger.info
                log(f"[{agent_id}] wake: seeded own place cell '{name}' "
                    f"({PLACE_EXTENT_CM / 100:.0f} m box) at current spot "
                    f"({col},{row})"
                    + (" — despite places.json; place not authored?"
                       if self._manifest_present else ""))
                return True
            return None
        if float(end.get("extent_cm") or 0.0) <= 0:
            return (col, row) == tuple(end["cell"])
        half = float(end["extent_cm"]) / 2.0
        return (abs(xyz[0] - end["xy"][0]) <= half
                and abs(xyz[1] - end["xy"][1]) <= half)

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

        action = self._bound_at_place_movement(agent, action, observation)

        # Sweep interrupt (#11.1/#34): an APC staying in an unexplored cell maps it
        # before acting — the sweep's first step replaces this tick's LLM action;
        # the following steps run LLM-free via _pulse_sweep until the breadcrumb
        # drops, then the sequencer resumes the routine. Scheduled "act" and
        # "travel" ticks are normally exempt. Acting APCs must not abandon their
        # post, and ordinary travelers must not treat transient cell crossings
        # as detours. An APC configured with survey_priority deliberately flips
        # that policy: it owns the current unexplored cell first, walks to its
        # exact center, completes N/S/E/W, and then resumes its unchanged schedule.
        sched_status = (observation.get("schedule") or {}).get("status")
        survey_priority = bool(getattr(agent, "survey_priority", False))
        if ((survey_priority or sched_status not in {"act", "travel"})
                and self._should_sweep_here(observation, agent_id)):
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

    def _bound_at_place_movement(self, agent: Agent, action: dict,
                                 observation: dict) -> dict:
        """Keep freeform roaming inside the place where the schedule says to act.

        The LLM may choose ``wander`` to perform an activity such as "wander the
        village square". A raw wander is a 15 m forward step and can leave the
        place immediately (SR11). Convert it to a concrete target clamped inside
        the community cell or owned-place box. Named travel and actor approaches
        remain unchanged.
        """
        sched = observation.get("schedule") or {}
        if sched.get("status") != "act" or not sched.get("place"):
            return action
        if not (action.get("type") == "wander"
                or (action.get("type") == "walk_to" and action.get("direction"))):
            return action

        xyz = _loc_xyz(observation.get("location"))
        desired = self._direction_target(observation, action.get("direction") or "forward")
        end = self._resolve_place_endpoint(agent.agent_id, sched["place"])
        if xyz is None or desired is None or end is None:
            return {"type": "idle"}

        cx, cy = end["xy"]
        extent = float(end.get("extent_cm") or 0.0)
        half = (extent / 2.0 if extent > 0 else self.world_grid.cell_size / 2.0)
        safe_half = max(half - _PLACE_ROAM_MARGIN_CM, 0.0)
        tx = min(max(desired[0], cx - safe_half), cx + safe_half)
        ty = min(max(desired[1], cy - safe_half), cy + safe_half)

        # At an edge, clamping can produce the current point. Turn back toward
        # the anchor so repeated wander decisions cannot wedge on the boundary.
        if math.hypot(tx - xyz[0], ty - xyz[1]) < 100.0:
            tx, ty = cx, cy
        return {"type": "walk_to", "location": [tx, ty, xyz[2]]}

    def _attach_nearby_characters(self, observations: dict[str, dict | None]) -> None:
        """Attach deterministic APC proximity facts before parallel LLM work.

        Vision remains the authority for line of sight. This engine-neutral
        position fact prevents a small/far character missed by the VLM from
        becoming completely nonexistent to the decision layer.
        """
        for agent_id, observation in observations.items():
            if observation is None:
                continue
            here = _loc_xyz(observation.get("location"))
            if here is None:
                continue
            nearby = []
            for other_id, pos in self._live_pos.items():
                if other_id == agent_id:
                    continue
                distance = math.hypot(pos["x"] - here[0], pos["y"] - here[1])
                if distance <= _NEARBY_CHARACTER_CM:
                    other = self.agents.get(other_id)
                    nearby.append({"name": getattr(other, "display_name", other_id),
                                   "distance_cm": round(distance, 1)})
            observation["nearby_characters"] = sorted(nearby, key=lambda x: x["distance_cm"])

    def _resolve_place_endpoint(self, agent_id: str, name: str) -> dict | None:
        """Resolve a place name to a travel endpoint, or None if unknown.

        The shared resolution chain (#11.2, grid-first): a community-named
        cell wins — endpoint is the cell itself (``extent_cm`` 0.0: being in
        the cell is arrival); otherwise an APC-owned place cell (this agent's
        own entries preferred) — endpoint is its anchor + extent box. Returns
        ``{"cell": (c, r), "xy": (x, y), "extent_cm": float}``.
        """
        if self.place_db is None:
            return None

        owned = self.place_db.find_owned_place(name, preferred_owner=agent_id)

        # Authored markers are world ground truth. They beat runtime community
        # labels and wake seeds even when the authored name is a safe fuzzy
        # match (SR11: "vegitable truck" vs "the vegetable truck").
        if owned is not None and owned.get("source") == "authored":
            endpoint = self._owned_place_endpoint(owned)
            if endpoint is not None:
                return endpoint

        cell = self.place_db.find_named_cell(name)
        if cell is not None:
            center = self.world_grid.cell_center(*cell)
            if center is not None:
                logger.info(f"Resolved place '{name}' -> cell {cell} center {center}")
                return {"cell": cell, "xy": center, "extent_cm": 0.0}

        if owned is not None:
            return self._owned_place_endpoint(owned)
        return None

    def _owned_place_endpoint(self, owned: dict) -> dict | None:
        center = self.world_grid.cell_center(owned["col"], owned["row"])
        if center is None:
            return None
        logger.info(
            f"Resolved owned place '{owned['name']}' ({owned['owner']}, "
            f"{owned.get('source') or 'runtime'}) -> cell "
            f"({owned['col']},{owned['row']}) offset ({owned['dx']:.0f},{owned['dy']:.0f})"
        )
        return {"cell": (owned["col"], owned["row"]),
                "xy": (center[0] + owned["dx"], center[1] + owned["dy"]),
                "extent_cm": float(owned.get("extent_cm") or PLACE_EXTENT_CM)}

    def _resolve_place_target(self, agent_id: str, name: str, observation: dict) -> list[float] | None:
        """Resolve a place name to a walk target ``[x, y, z]``, or None.

        The endpoint's world position with the agent's current z kept, so it
        stays on the ground plane. Returns None when the name is unknown —
        callers fall back to the bridge's graceful idle.
        """
        end = self._resolve_place_endpoint(agent_id, name)
        if end is None:
            return None
        xyz = _loc_xyz(observation.get("location"))
        z = xyz[2] if xyz else 0.0
        return [end["xy"][0], end["xy"][1], z]

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
        end = self._resolve_place_endpoint(agent_id, destination_name)
        if end is None:
            return None
        # Draw the planned legs (#17/WP8) when the cached route is for this
        # same destination — the corridor image shows the plan, not just A/B.
        cached = self._routes.get(agent_id)
        path = (cached["path"] if cached and cached["destination"] == destination_name
                and cached["path"][-1] == end["cell"] else None)
        route = route_map.build_route_map(
            self.place_db, self.world_grid, (col, row), end["cell"],
            destination_name=destination_name, path=path,
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
            smap = SpatialMap.load(
                path, cell_size=self.world_grid.cell_size,
                origin_x=self.world_grid.origin_x, origin_y=self.world_grid.origin_y,
            )
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

    def _mark_recent_greetings(self, acquaintances: list, world_time) -> list:
        """Copy each acquaintance with a ``recently_greeted`` flag (#12.1): True
        when this agent spoke with them within ``_GREET_COOLDOWN_MINUTES`` of now
        (sim-time). Copies rather than mutates so the derived flag never leaks
        into the persisted social store. A backwards clock (day restart) reads as
        not-recent, so greetings resume after a fresh day.
        """
        out = []
        for a in acquaintances:
            li = a.get("last_interacted")
            recent = False
            if li and world_time:
                elapsed = planner.minutes_between(li, world_time)
                recent = 0 <= elapsed < _GREET_COOLDOWN_MINUTES
            out.append({**a, "recently_greeted": recent})
        return out

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
            # A name/breadcrumb is not visual memory; only a complete place
            # image makes this community cell survey-ready.
            if (self.place_db is None
                    or self.place_db.current_place_image(agent_id, col, row) is not None):
                return None
            sweep = cell_sweep.default_sweep(self.world_grid, col, row, z=xyz[2])
            if sweep is None:
                return None
            active = {"sweep": sweep, "col": col, "row": row, "views": []}
            self._cell_sweeps[agent_id] = active
            logger.info(f"[{agent_id}] sweep: unexplored cell ({col},{row}) — sweeping")

        action = active["sweep"].next_action((xyz[0], xyz[1]))
        if action.get("type") == "sweep_done":
            image = self._save_place_visual(
                agent_id, active["col"], active["row"], active.get("views", [])
            )
            if image:
                self.place_db.mark_swept(
                    agent_id, active["col"], active["row"],
                    observation.get("world_time", self.world_clock.now_text())
                )
            self._cell_sweeps.pop(agent_id, None)
            logger.info(
                f"[{agent_id}] sweep: ({active['col']},{active['row']}) "
                + ("visual saved; breadcrumb dropped" if image
                   else "visual incomplete; cell remains due for survey")
            )
            return None
        action["_sweep_interrupt"] = True
        return action

    def _should_sweep_here(self, observation: dict, agent_id: str = "") -> bool:
        """True when the current grid cell still needs a community place image.

        This is the schedule-agnostic spatial/storage gate. The act-phase caller
        applies #34's routine policy plus the per-APC survey-priority override.
        Needs a bounded grid (a cell center to walk to) and a PlaceDB (somewhere
        to drop the breadcrumb).
        """
        col, row = self._cell_col_row(observation.get("grid"))
        if col is None or self.place_db is None:
            return False
        return self.place_db.current_place_image(agent_id, col, row) is None

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
            "place_image_id": observation.get("place_image_id"),
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
                    # name becomes an APC-owned place cell — a named 9x9 m box at an
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

    def _execute_routed_walk(self, agent: Agent, action: dict, observation: dict) -> dict:
        """Execute a walk_to-by-name as the current leg of a grid-first route
        (#17/WP8).

        Plans a straight cell line to the destination once, caches it per
        agent, and walks the current leg's cell center each tick — the leg
        state machine (``route_planner.next_waypoint``) advances on cell
        entry with skip-ahead. Stuck drops the route (replan from where the
        agent really is). ``None`` from the state machine means arrived: the
        route is dropped and no walk is issued (the directive flips to "act"
        on the next decide). Unknown names pass through unchanged (bridge's
        graceful idle); no position/cell/bounds falls back to today's direct
        walk to the endpoint.
        """
        agent_id = agent.agent_id
        name = action["target_location"]
        end = self._resolve_place_endpoint(agent_id, name)
        if end is None:
            return self.bridge.execute_action(agent.bound_unreal_actor_name, action)

        xyz = _loc_xyz(observation.get("location"))
        col, row = self._cell_col_row(observation.get("grid"))
        z = xyz[2] if xyz else 0.0
        if xyz is None or col is None or not self.world_grid.has_bounds:
            return self.bridge.execute_action(
                agent.bound_unreal_actor_name,
                {**action, "location": [end["xy"][0], end["xy"][1], z]})

        if observation.get("stuck"):
            # Wedged mid-route: drop the plan, re-line from where we really are.
            self._routes.pop(agent_id, None)

        route = self._routes.get(agent_id)
        if (route is None or route["destination"] != name
                or route["path"][-1] != end["cell"]):
            route = route_planner.make_route((col, row), end["cell"], end["xy"],
                                             end["extent_cm"], name)
            self._routes[agent_id] = route
            logger.info(f"[{agent_id}] route planned: {len(route['path']) - 1} leg(s) "
                        f"from ({col},{row}) to {end['cell']} for '{name}'")

        wp = route_planner.next_waypoint(route, (col, row), (xyz[0], xyz[1]),
                                         self.world_grid)
        if wp is None:
            self._routes.pop(agent_id, None)
            return {"status": "accepted", "action": "idle",
                    "note": f"arrived at {name}"}

        result = self.bridge.execute_action(
            agent.bound_unreal_actor_name,
            {**action, "location": [wp["x"], wp["y"], z]})
        if isinstance(result, dict) and not result.get("error"):
            result["note"] = f"leg {wp['leg']}/{wp['total']} -> cell {wp['cell']}"
        return result

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

        # walk_to a named place ("village square") — grid-first routing
        # (#17/WP8): resolve the name to an endpoint, then walk the current
        # LEG of a cell-by-cell plan instead of beelining the final position
        # (greedy-by-vision travel orbits when the destination isn't in
        # frame). The LLM contract is unchanged; only execution is legged.
        if (t == "walk_to" and isinstance(action.get("target_location"), str)
                and not action.get("location") and not action.get("target_actor")):
            return self._execute_routed_walk(agent, action, observation)

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
        active = self._cell_sweeps.get(agent_id)
        if active is not None:
            active.setdefault("views", []).append({
                "direction": direction,
                "yaw": yaw,
                "image_path": image_path,
                "caption": seen.get("caption", ""),
                "landmarks": landmarks,
                "characters": seen.get("characters", []),
            })
        return {"status": "success", "action": "observe_heading", "direction": direction,
                "yaw": yaw, "landmarks": len(landmarks), "image_path": image_path,
                "caption": seen.get("caption", "")}

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
        start transform, clears per-run timers and episodic recall, restores
        memories from memory.seed.json (or empties them), and deletes spatial maps.
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
            entry["episodes"] = self._episodic(agent.agent_id).reset()

            map_path = self._agents_dir / agent.agent_id / "spatial_map.json"
            if map_path.exists():
                map_path.unlink()
                entry["spatial_map"] = "deleted"

            results.append(entry)

        self._spatial.clear()
        self._last_cell.clear()
        self._frontier_failures.clear()
        self._scene_skips.clear()
        self._nearby_ids.clear()
        self._last_pos.clear()
        self._no_progress.clear()
        self._routes.clear()
        self._live_pos.clear()
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

    async def regrid_world(self, level: str, origin_x: float, origin_y: float) -> dict:
        """Apply a logical lattice origin and invalidate all grid-keyed state.

        Regridding is deliberately destructive to derived geography: PlaceDB
        rows/images, per-agent spatial maps, rendered route maps, and in-memory
        routes/sweeps all refer to the old cell keys. Authored world positions,
        agent starts, schedules, and ordinary memories are preserved.
        """
        if not (math.isfinite(origin_x) and math.isfinite(origin_y)):
            return {"status": "error", "error": "origin_x/origin_y must be finite numbers"}

        worlds_root = self.worlds_dir.resolve()
        world_dir = (worlds_root / str(level)).resolve()
        if (world_dir == worlds_root or worlds_root not in world_dir.parents
                or not world_dir.is_dir()):
            return {"status": "error", "error": f"Unknown or unsafe world '{level}'"}
        grid_path = world_dir / "world_grid.json"
        if not grid_path.is_file():
            return {"status": "error", "error": f"{level} has no world_grid.json"}
        try:
            raw = json.loads(grid_path.read_text(encoding="utf-8"))
        except Exception as e:
            return {"status": "error", "error": f"Could not read world_grid.json: {e}"}
        if not raw.get("bounds"):
            return {"status": "error", "error": f"{level} has no bounded grid"}

        was_running = self.running
        if was_running:
            await self.stop_simulation()

        db_path = world_dir / "world_places.db"
        removed = {}
        if db_path.exists():
            target_db = (self.place_db if self.place_db is not None
                         and self.place_db._path.resolve() == db_path.resolve()
                         else PlaceDB(db_path))
            removed = target_db.reset()

        deleted_spatial_maps = 0
        deleted_route_maps = 0
        agents_dir = world_dir / "agents"
        if agents_dir.is_dir():
            for path in agents_dir.glob("*/spatial_map.json"):
                path.unlink()
                deleted_spatial_maps += 1
            for path in agents_dir.glob("*/observations/route_map.png"):
                path.unlink()
                deleted_route_maps += 1

        raw["origin_x"] = float(origin_x)
        raw["origin_y"] = float(origin_y)
        temp_path = grid_path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        temp_path.replace(grid_path)
        updated_grid = WorldGrid.load(grid_path)

        if self._agents_dir is not None and self._agents_dir.parent.resolve() == world_dir:
            self.world_grid = updated_grid
        self._spatial.clear()
        self._last_cell.clear()
        self._last_grid_place.clear()
        self._frontier_failures.clear()
        self._routes.clear()
        self._cell_sweeps.clear()
        self._live_pos.clear()

        logger.info(
            f"=== WORLD REGRID === level={level} logical_origin=({origin_x:.0f},{origin_y:.0f}) "
            f"places={removed} spatial_maps={deleted_spatial_maps}"
            f"{', sim stopped first' if was_running else ''}"
        )
        return {
            "status": "regridded", "level": level,
            "origin_x": updated_grid.origin_x, "origin_y": updated_grid.origin_y,
            "effective_origin": list(updated_grid.origin() or ()),
            "stopped_simulation": was_running, "removed": removed,
            "deleted_spatial_maps": deleted_spatial_maps,
            "deleted_route_maps": deleted_route_maps,
        }

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

    def capture_start_transforms(self) -> dict:
        """Adopt current bound APC transforms as explicit reset/start points.

        This is intentionally operator-triggered: silently refreshing on every
        start would capture a wandered runtime position during a same-PIE rerun.
        Use after placing APCs in the editor (and while the sim is stopped).
        """
        if self.running:
            return {"status": "error", "error": "Stop the simulation before capturing starts"}
        if not self.agents:
            self._load_agents(None)
            self._bind_agents()
        if not self._agents_dir:
            return {"status": "error", "error": "No agents loaded — is Unreal connected?"}

        captured, skipped = [], []
        for agent in self.agents.values():
            if not agent.has_unreal_binding:
                skipped.append({"agent_id": agent.agent_id, "reason": "no Unreal binding"})
                continue
            transform = self.bridge.get_character_transform(agent.bound_unreal_actor_name) or {}
            if not transform.get("location"):
                skipped.append({"agent_id": agent.agent_id, "reason": "no transform"})
                continue
            agent.update_start_transform(transform["location"], transform.get("rotation"),
                                         self._agents_dir)
            captured.append(agent.agent_id)
        logger.info(f"Captured APC start transforms: {captured}; skipped={skipped}")
        return {"status": "captured", "captured": captured, "skipped": skipped}

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
        that holds several ~9 m place cells, not a place-sized tile (the 4 m
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
        # A regrid invalidates any previous image_bounds calibration — write
        # only the new grid; the capture below re-derives the calibration.
        path.write_text(
            json.dumps({"cell_size": cell_size, "bounds": bounds,
                        "origin_x": 0.0, "origin_y": 0.0}, indent=2),
            encoding="utf-8",
        )
        self.world_grid = WorldGrid(cell_size=cell_size, bounds=bounds)

        # Registration shot (#18): shoot the world map from the MAP_Camera pawn
        # framed to the fresh bounds. Best-effort — a world without the pawn
        # still gets its grid; the failure is reported, never swallowed.
        shot = map_capture.capture_world_map(
            self.bridge, level, bounds, path,
            images_dir=self.worlds_dir.parent / "web_ui" / "images",
        )
        return {
            "status": "generated",
            "level": level,
            "path": str(path),
            "actors_scanned": len(points),
            "bounds": bounds,
            "grid": self.world_grid.describe(),
            "map_capture": shot,
        }

    # Helpers

    def _save_perception_evidence(self, agent_id: str, observation: dict, seen: dict) -> None:
        """Persist the latest structured VLM output so live misses are inspectable."""
        if not self._agents_dir:
            return
        path = self._agents_dir / agent_id / "last_perception.json"
        payload = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "world_time": observation.get("world_time"),
            "image_path": observation.get("image_path"),
            "model": seen.get("model"),
            "caption": seen.get("caption", ""),
            "landmarks": seen.get("landmarks") or [],
            "characters": seen.get("characters") or [],
            "error": seen.get("error"),
        }
        try:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception as e:
            logger.warning(f"[{agent_id}] could not save perception evidence: {e}")

    def _record_live_pos(self, agent_id: str, observation: dict) -> None:
        """Remember the agent's last observed position + facing (#18 live map).

        Written on every observe tick from data already in hand — no extra
        engine traffic. A positionless tick (no transform yet) records
        nothing; the previous fix stays until fresher data arrives.
        """
        xyz = _loc_xyz(observation.get("location"))
        if xyz is None:
            return
        self._live_pos[agent_id] = {
            "x": xyz[0], "y": xyz[1],
            "yaw": _yaw_of(observation.get("rotation")),
        }

    def agent_positions(self) -> list[dict]:
        """Last observed position per active agent — the live /map dots (#18).

        Returns ``[{agent_id, x, y, yaw, col, row}, ...]`` (col/row None on an
        unbounded grid). Agents never observed this run are absent — the map
        only shows what the sim has actually seen, never a guess.
        """
        out = []
        for a in self.agents.values():
            p = self._live_pos.get(a.agent_id)
            if p is None or not a.is_active:
                continue
            col, row = self._cell_col_row(self.world_grid.locate(p["x"], p["y"]))
            out.append({"agent_id": a.agent_id, "x": p["x"], "y": p["y"],
                        "yaw": p["yaw"], "col": col, "row": row})
        return out

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
