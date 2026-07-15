"""Offline tests for unexplored-cell sweep + community breadcrumb (backlog #7).

When an APC enters a grid cell with no place cell, it drops personality and runs
a deterministic sweep: walk to the cell center, do a 360 observation, then drop a
community place-cell breadcrumb so future APCs skip the costly re-sweep.

This file covers the loop-safe core: PlaceDB sweep state, the pure sweep planner/
state machine, and the manager override decision. The live 360 rotation+capture
is verified in PIE, not here. No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_cell_sweep.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent import Agent                  # noqa: E402
from agent_runtime.agent_manager import AgentManager   # noqa: E402
from agent_runtime.place_db import PlaceDB        # noqa: E402
from agent_runtime.world_grid import WorldGrid    # noqa: E402
from agent_runtime import cell_sweep               # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# ── PlaceDB: explored state + community breadcrumb ──────────────────────────────

def test_is_explored_and_mark_swept():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        check("fresh cell is unexplored", not db.is_explored(2, 3))

        # A named cell counts as explored (it has a place cell).
        db.set_name("maren", 5, 5, "Village Square", "T0")
        check("named cell is explored", db.is_explored(5, 5))

        # Sweeping an unnamed cell drops a community breadcrumb -> explored.
        check("first sweep records", db.mark_swept("dufus", 2, 3, "Day 1 09:00") is True)
        check("swept cell is explored", db.is_explored(2, 3))
        crumb = db.get_swept(2, 3)
        check("breadcrumb has no personal name", crumb["name"] is None)
        check("breadcrumb records who/when", crumb["swept_by"] == "dufus" and crumb["swept_at"] == "Day 1 09:00")

        # Sweeping must not clobber an existing name.
        db.mark_swept("dufus", 5, 5, "Day 1 10:00")
        check("sweep preserves an existing name", db.get_place(5, 5)["name"] == "Village Square")


def test_swept_migration_on_existing_db():
    """A pre-sweep DB (place_cells without swept columns) migrates in place."""
    import sqlite3
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "old.db"
        conn = sqlite3.connect(str(path))
        conn.executescript(
            "CREATE TABLE place_cells (col INTEGER, row INTEGER, name TEXT, "
            "named_at TEXT, named_by TEXT, PRIMARY KEY (col, row));"
        )
        conn.execute("INSERT INTO place_cells VALUES (1,1,'Old Town','T0','maren')")
        conn.commit()
        conn.close()

        db = PlaceDB(path)  # __init__ must add swept_at/swept_by
        check("old data survives migration", db.is_explored(1, 1))
        check("can sweep after migration", db.mark_swept("dufus", 7, 7, "T9") is True)
        check("migrated db tracks new sweep", db.is_explored(7, 7))


# ── Pure sweep planner / state machine ──────────────────────────────────────────

def test_compass_headings():
    h = cell_sweep.compass_headings()
    check("a full 360 in 4 steps", len(h) == 4)
    check("cardinal headings are 90deg apart", h == [0.0, 90.0, 180.0, 270.0])


def test_default_sweep_needs_bounds():
    bounded = WorldGrid(cell_size=400.0, bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})
    sweep = cell_sweep.default_sweep(bounded, 5, 5, z=90.0)
    check("bounded grid yields a sweep", sweep is not None)
    check("targets the cell center", sweep.center == (200.0, 200.0))
    check("unbounded grid yields no sweep", cell_sweep.default_sweep(WorldGrid(), 5, 5, z=90.0) is None)


def test_sweep_sequence():
    sweep = cell_sweep.CellSweep(center=(200.0, 200.0), z=90.0,
                                 headings=[0.0, 90.0, 180.0, 270.0], arrive_tolerance=50.0)
    # Far from center: keep walking to the center, not yet sweeping.
    a = sweep.next_action((1000.0, 200.0))
    check("far -> walk to center", a["type"] == "walk_to" and a["location"] == [200.0, 200.0, 90.0])
    check("not done while travelling", not sweep.is_done)

    # Arrived: emit one observation per heading, in order.
    seen = [sweep.next_action((210.0, 205.0))["yaw"] for _ in range(4)]
    check("observes every heading in order", seen == [0.0, 90.0, 180.0, 270.0])

    # Headings exhausted: done.
    done = sweep.next_action((210.0, 205.0))
    check("sweep reports done", done["type"] == "sweep_done")
    check("is_done set", sweep.is_done)


def test_arrival_is_sticky():
    sweep = cell_sweep.CellSweep(center=(0.0, 0.0), z=0.0, headings=[0.0], arrive_tolerance=50.0)
    sweep.next_action((10.0, 0.0))                 # arrive
    a = sweep.next_action((9999.0, 0.0))           # drift far after arriving
    check("does not restart travel after arriving", a["type"] != "walk_to")


# ── Sweep capability (#11.1 — any APC, no dedicated role) ──────────────────────

def test_agent_role_collapsed():
    def mk(state):
        return Agent("a", state, "", "", "", [])
    check("default role is npc", mk({}).role == "npc")
    check("is_maintenance property is gone", not hasattr(mk({}), "is_maintenance"))


class _StubMemory:
    def record(self, **kwargs):
        pass


def _manager(tmp):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=None, memory_store=_StubMemory())
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.world_grid = WorldGrid(cell_size=400.0,
                               bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    return mgr


def _obs(x, y, col=5, row=5, schedule=None):
    return {"grid": {"key": f"{col},{row}", "col": col, "row": row},
            "location": {"x": x, "y": y, "z": 90.0}, "world_time": "Day 1 09:00",
            "schedule": schedule}


def test_sweep_step_requires_place_visual_even_when_named():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        mgr.place_db.set_name("maren", 5, 5, "Village Square", "T0")
        check("named cell without a place image still needs a survey",
              mgr._sweep_step("sweeper", _obs(0.0, 0.0)) is not None)


def test_sweep_step_start_false_never_starts():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)   # cell (5,5) unexplored
        check("continuation-only call starts nothing",
              mgr._sweep_step("sweeper", _obs(0.0, 0.0), start=False) is None)
        check("no sweep went active", "sweeper" not in mgr._cell_sweeps)


def test_sweep_step_runs_then_drops_breadcrumb():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        # Cell (5,5) is unexplored; its center is (200,200) for this grid.
        first = mgr._sweep_step("sweeper", _obs(1500.0, 1500.0))
        check("unexplored cell -> walk to center", first["type"] == "walk_to")
        check("action is tagged as a sweep interrupt", first.get("_sweep_interrupt") is True)
        check("targets the cell center", first["location"] == [200.0, 200.0, 90.0])

        # Arrive at center; the sweep emits observations, then finishes.
        actions = []
        for _ in range(10):
            a = mgr._sweep_step("sweeper", _obs(200.0, 200.0))
            if a is None:
                break
            actions.append(a)
        observes = [a for a in actions if a["type"] == "observe_heading"]
        check("ran a full 4-heading survey", len(observes) == 4)
        check("no breadcrumb without four successful image captures",
              not mgr.place_db.is_explored(5, 5))
        check("sweep cleared when done", "sweeper" not in mgr._cell_sweeps)


def test_should_sweep_here_gate():
    # This low-level gate answers only whether the cell needs a survey. Schedule
    # priority is applied by _act_agent (#34), so these raw results intentionally
    # do not vary with schedule status.
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)   # cell (5,5) unexplored
        check("raw gate ignores schedule status (act)",
              mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "act"})))
        check("idle in an unexplored cell -> sweep",
              mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "idle"})))
        check("raw gate ignores schedule status (travel)",
              mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "travel"})))
        check("missing schedule -> still sweep an unexplored cell",
              mgr._should_sweep_here(_obs(200.0, 200.0, schedule=None)))

        mgr.place_db.mark_swept("someone", 5, 5, "T0")
        check("breadcrumb without visual -> survey still required",
              mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "travel"})))

        mgr.place_db = None
        check("no PlaceDB -> no sweep",
              not mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "act"})))


def test_explored_cells_set():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 1, 1, "Square", "T0")
        db.mark_swept("sweeper", 2, 3, "T0")
        db.touch("dufus", 8, 8)  # a bare visit is NOT explored
        check("explored set has named + swept only", db.explored_cells() == {(1, 1), (2, 3)})


# ── Sweep interrupt wiring: act phase start + LLM-free continuation ────────────

class _StubBridge:
    def __init__(self, loc, fail_turn=False):
        self._loc = loc
        self.actions = []
        self.turns = []
        self.fail_turn = fail_turn

    def get_observation(self, actor_name, agent_id, agents_dir):
        return {"actor_name": actor_name, "image_path": None, "location": dict(self._loc),
                "current_action": "idle", "ai_state": None}

    def execute_action(self, actor_name, action):
        self.actions.append(action)
        return {"status": "accepted", "action": action.get("type")}

    def set_facing(self, actor_name, location, yaw):
        if self.fail_turn:
            return {"error": "no actor"}
        self.turns.append(yaw)
        return {"status": "success"}

    def capture_view(self, actor_name, agent_id, agents_dir, tag):
        from PIL import Image
        path = Path(agents_dir) / agent_id / "observations" / f"{tag}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (80, 45), "navy").save(path)
        return str(path)

    def set_ai_state(self, actor_name, state):
        pass

    def print_to_screen(self, message, key=None, duration=None):
        pass


class _StubPerceiver:
    """One landmark per view — enough to prove ingest wiring."""
    def perceive(self, image_path, known_characters):
        return {"landmarks": [{"label": "fountain", "confidence": 0.9}],
                "characters": [], "caption": "a fountain"}


class _StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.state = {}
        self.bound_unreal_actor_name = f"BP_{agent_id}"
        self.bound_unreal_actor_label = agent_id
        self.unreal_actor_name = agent_id
        self.has_unreal_binding = True
        self.is_active = True
        self.is_busy = False
        self.allowed_actions = ["idle", "walk_to", "observe_heading"]
        self.ticked = 0
        self.last_activity = None

    def cooldown_expired(self):
        return True

    def mark_ticked(self, agents_dir):
        self.ticked += 1

    def set_last_activity(self, activity, agents_dir=None):
        self.last_activity = activity


def _idle_decision(agent_id):
    return {"agent_id": agent_id, "thought_summary": "t",
            "action": {"type": "idle"}, "importance": 0.5}


def _named_walk_decision(agent_id, place):
    return {"agent_id": agent_id, "thought_summary": "keep traveling",
            "action": {"type": "walk_to", "target_location": place},
            "importance": 0.5}


def test_act_agent_starts_sweep_interrupt():
    """An APC idling in an unexplored cell has its LLM action replaced by
    the sweep's first step; the sweep goes active for the next ticks."""
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 1500.0, "y": 1500.0, "z": 90.0})
        mgr = _manager(tmp)
        mgr.bridge = bridge
        agent = _StubAgent("dufus")
        mgr.agents = {"dufus": agent}

        obs = _obs(1500.0, 1500.0, schedule={"status": "idle"})
        result = mgr._act_agent(agent, _idle_decision("dufus"), obs)
        check("LLM action was replaced by the sweep step",
              bridge.actions and bridge.actions[-1]["type"] == "walk_to")
        check("executed action is tagged as a sweep interrupt",
              bridge.actions[-1].get("_sweep_interrupt") is True)
        check("sweep is now active", "dufus" in mgr._cell_sweeps)
        check("tick was recorded", agent.ticked == 1)
        check("result reports the sweep action", result["action"].get("_sweep_interrupt") is True)


def test_act_agent_act_tick_is_sweep_exempt():
    """A scheduled "act" tick never starts a sweep (user, 2026-07-05): the agent
    is AT its place doing its job — Maren waking at her stall must not walk off
    to the cell center to survey the district. The cell gets swept on a later
    travel/idle tick instead."""
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 1500.0, "y": 1500.0, "z": 90.0})
        mgr = _manager(tmp)
        mgr.bridge = bridge
        agent = _StubAgent("dufus")
        mgr.agents = {"dufus": agent}

        obs = _obs(1500.0, 1500.0, schedule={"status": "act", "activity": "tend the stall"})
        mgr._act_agent(agent, _idle_decision("dufus"), obs)
        check("act tick kept the LLM action (no sweep interrupt)",
              bridge.actions and bridge.actions[-1]["type"] == "idle")
        check("no sweep went active on an act tick", "dufus" not in mgr._cell_sweeps)


def test_act_agent_travel_defers_sweep_on_entry():
    """SR18/#34: a transient unexplored-cell entry must not replace scheduled
    travel with a walk back to that cell's center.  The route keeps priority and
    the unexplored cell remains available for a later non-travel survey."""
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 1500.0, "y": 1500.0, "z": 90.0})
        mgr = _manager(tmp)
        mgr.bridge = bridge
        agent = _StubAgent("dufus")
        mgr.agents = {"dufus": agent}
        mgr.place_db.set_name("dufus", 8, 5, "village square", "T0")

        obs = _obs(1500.0, 1500.0, schedule={"status": "travel", "place": "village square"})
        mgr._act_agent(agent, _named_walk_decision("dufus", "village square"), obs)
        check("travel tick kept the routed walk (no sweep interrupt)",
              bridge.actions[-1]["type"] == "walk_to"
              and bridge.actions[-1].get("location") is not None
              and bridge.actions[-1].get("_sweep_interrupt") is not True)
        check("no sweep went active on incidental entry", "dufus" not in mgr._cell_sweeps)


def test_pulse_routes_active_sweep_without_llm():
    """Once a sweep is active, pulse_agent continues it LLM-free until the
    breadcrumb drops — and each observe turns, captures, perceives, and ingests
    its landmarks into the shared map (the #7 live half, no engine handler)."""
    import asyncio
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 200.0, "y": 200.0, "z": 90.0})   # at cell center
        mgr = _manager(tmp)
        mgr.bridge = bridge
        mgr.perceiver = _StubPerceiver()
        mgr.llm = None   # would explode if a sweeping agent hit the LLM path
        agent = _StubAgent("dufus")
        mgr.agents = {"dufus": agent}

        # Start the sweep (already at center -> first step is an observe).
        first = mgr._sweep_step("dufus", _obs(200.0, 200.0))
        check("sweep starts observing at center", first["type"] == "observe_heading")
        mgr._execute_world_action(agent, first, _obs(200.0, 200.0))

        results = []
        for _ in range(12):
            results.append(asyncio.run(mgr.pulse_agent("dufus")))
            if "dufus" not in mgr._cell_sweeps:
                break
        check("sweep finished LLM-free", "dufus" not in mgr._cell_sweeps)
        check("last pulse reports sweep_done", results[-1].get("action") == "sweep_done")
        check("breadcrumb dropped", mgr.place_db.is_explored(5, 5))
        check("turned through all 4 cardinal headings", len(bridge.turns) == 4)
        cells = mgr.place_db.map_cells()
        check("every heading ingested its landmark", cells and cells[0]["landmarks"] == 4)
        visual = mgr.place_db.current_place_image("dufus", 5, 5)
        check("four views produced a durable place image", visual is not None)
        check("place image appears in APC visual history",
              (Path(tmp) / "agents/dufus/observations/place_history"
               / f"{visual['place_image_id']}.png").is_file())


def test_observe_heading_direction_and_ingest():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 200.0, "y": 200.0, "z": 90.0})
        mgr = _manager(tmp)
        mgr.bridge = bridge
        mgr.perceiver = _StubPerceiver()
        agent = _StubAgent("dufus")

        result = mgr._execute_world_action(
            agent, {"type": "observe_heading", "yaw": 90.0}, _obs(200.0, 200.0))
        check("observe succeeded", result.get("status") == "success")
        check("yaw 90 maps to compass S (UE convention)", result.get("direction") == "S")
        check("one landmark recorded", result.get("landmarks") == 1)
        mgr.place_db.mark_swept("dufus", 5, 5, "T0")   # make the cell visible to map_cells
        check("landmark is in the shared map", mgr.place_db.map_cells()[0]["landmarks"] == 1)


def test_observe_heading_degrades_on_turn_failure():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 200.0, "y": 200.0, "z": 90.0}, fail_turn=True)
        mgr = _manager(tmp)
        mgr.bridge = bridge
        mgr.perceiver = _StubPerceiver()
        agent = _StubAgent("dufus")

        result = mgr._execute_world_action(
            agent, {"type": "observe_heading", "yaw": 0.0}, _obs(200.0, 200.0))
        check("turn failure -> error result, no crash", result.get("status") == "error")
        check("nothing ingested on failure", mgr.place_db.map_cells() == [])


def test_tick_routes_sweeping_agent():
    """In the multi-agent tick, an agent mid-sweep runs the deterministic sweep
    phase (bridge action, no LLM) rather than the perceive→decide phases."""
    import asyncio
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 1500.0, "y": 1500.0, "z": 90.0})
        mgr = _manager(tmp)
        mgr.bridge = bridge
        mgr.llm = None  # would explode if a sweeping agent were sent to the LLM path
        agent = _StubAgent("dufus")
        mgr.agents = {"dufus": agent}
        # Activate a sweep for cell (5,5), as the act-phase gate would.
        first = mgr._sweep_step("dufus", _obs(1500.0, 1500.0))
        check("sweep activated", first is not None and "dufus" in mgr._cell_sweeps)

        result = asyncio.run(mgr.tick())
        check("the sweeping agent was ticked", result["ticked"] == 1)
        check("it acted through the bridge (no LLM)",
              bridge.actions and bridge.actions[-1]["type"] == "walk_to")
        check("tick result is flagged as a sweep", result["agent_results"][0].get("sweep") is True)


def main():
    test_is_explored_and_mark_swept()
    test_swept_migration_on_existing_db()
    test_compass_headings()
    test_default_sweep_needs_bounds()
    test_sweep_sequence()
    test_arrival_is_sticky()
    test_agent_role_collapsed()
    test_sweep_step_requires_place_visual_even_when_named()
    test_sweep_step_start_false_never_starts()
    test_sweep_step_runs_then_drops_breadcrumb()
    test_should_sweep_here_gate()
    test_explored_cells_set()
    test_act_agent_starts_sweep_interrupt()
    test_act_agent_act_tick_is_sweep_exempt()
    test_act_agent_travel_defers_sweep_on_entry()
    test_pulse_routes_active_sweep_without_llm()
    test_observe_heading_direction_and_ingest()
    test_observe_heading_degrades_on_turn_failure()
    test_tick_routes_sweeping_agent()
    print("\nAll cell-sweep checks passed.")


if __name__ == "__main__":
    main()
