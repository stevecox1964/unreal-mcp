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
    check("a full 360 in 8 steps", len(h) == 8)
    check("evenly spaced 45deg", h == [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0])


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


def test_sweep_step_skips_explored_cell():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)
        mgr.place_db.set_name("maren", 5, 5, "Village Square", "T0")
        check("explored cell -> nothing to sweep", mgr._sweep_step("sweeper", _obs(0.0, 0.0)) is None)


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
        check("ran a full 8-heading sweep", len(observes) == 8)
        check("breadcrumb dropped at the swept cell", mgr.place_db.is_explored(5, 5))
        check("breadcrumb is a community marker (unnamed)", mgr.place_db.get_swept(5, 5)["name"] is None)
        check("sweep cleared when done", "sweeper" not in mgr._cell_sweeps)


def test_should_sweep_here_gate():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager(tmp)   # cell (5,5) unexplored
        check("act in an unexplored cell -> sweep",
              mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "act"})))
        check("idle in an unexplored cell -> sweep",
              mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "idle"})))
        check("travel (passing through) -> no sweep",
              not mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "travel"})))
        check("missing schedule -> no detour",
              not mgr._should_sweep_here(_obs(200.0, 200.0, schedule=None)))

        mgr.place_db.mark_swept("someone", 5, 5, "T0")
        check("explored cell -> no sweep",
              not mgr._should_sweep_here(_obs(200.0, 200.0, schedule={"status": "act"})))

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
    def __init__(self, loc):
        self._loc = loc
        self.actions = []

    def get_observation(self, actor_name, agent_id, agents_dir):
        return {"actor_name": actor_name, "image_path": None, "location": dict(self._loc),
                "current_action": "idle", "ai_state": None}

    def execute_action(self, actor_name, action):
        self.actions.append(action)
        return {"status": "accepted", "action": action.get("type")}

    def set_ai_state(self, actor_name, state):
        pass

    def print_to_screen(self, message, key=None, duration=None):
        pass


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


def test_act_agent_starts_sweep_interrupt():
    """An APC staying (act) in an unexplored cell has its LLM action replaced by
    the sweep's first step; the sweep goes active for the next ticks."""
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 1500.0, "y": 1500.0, "z": 90.0})
        mgr = _manager(tmp)
        mgr.bridge = bridge
        agent = _StubAgent("dufus")
        mgr.agents = {"dufus": agent}

        obs = _obs(1500.0, 1500.0, schedule={"status": "act", "activity": "hang out"})
        result = mgr._act_agent(agent, _idle_decision("dufus"), obs)
        check("LLM action was replaced by the sweep step",
              bridge.actions and bridge.actions[-1]["type"] == "walk_to")
        check("executed action is tagged as a sweep interrupt",
              bridge.actions[-1].get("_sweep_interrupt") is True)
        check("sweep is now active", "dufus" in mgr._cell_sweeps)
        check("tick was recorded", agent.ticked == 1)
        check("result reports the sweep action", result["action"].get("_sweep_interrupt") is True)


def test_act_agent_travel_does_not_sweep():
    """Passing through an unexplored cell mid-travel must not detour (D1)."""
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 1500.0, "y": 1500.0, "z": 90.0})
        mgr = _manager(tmp)
        mgr.bridge = bridge
        agent = _StubAgent("dufus")
        mgr.agents = {"dufus": agent}

        obs = _obs(1500.0, 1500.0, schedule={"status": "travel", "place": "village square"})
        mgr._act_agent(agent, _idle_decision("dufus"), obs)
        check("LLM action executed unchanged", bridge.actions[-1]["type"] == "idle")
        check("no sweep went active", "dufus" not in mgr._cell_sweeps)


def test_pulse_routes_active_sweep_without_llm():
    """Once a sweep is active, pulse_agent continues it LLM-free until the
    breadcrumb drops, then the normal path resumes."""
    import asyncio
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _StubBridge({"x": 200.0, "y": 200.0, "z": 90.0})   # at cell center
        mgr = _manager(tmp)
        mgr.bridge = bridge
        mgr.llm = None   # would explode if a sweeping agent hit the LLM path
        agent = _StubAgent("dufus")
        mgr.agents = {"dufus": agent}

        # Start the sweep (already at center -> first step is an observe).
        first = mgr._sweep_step("dufus", _obs(200.0, 200.0))
        check("sweep starts observing at center", first["type"] == "observe_heading")

        results = []
        for _ in range(12):
            results.append(asyncio.run(mgr.pulse_agent("dufus")))
            if "dufus" not in mgr._cell_sweeps:
                break
        check("sweep finished LLM-free", "dufus" not in mgr._cell_sweeps)
        check("continuation steps were observes",
              any(a.get("type") == "observe_heading" for a in bridge.actions))
        check("last pulse reports sweep_done", results[-1].get("action") == "sweep_done")
        check("breadcrumb dropped", mgr.place_db.is_explored(5, 5))


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
    test_sweep_step_skips_explored_cell()
    test_sweep_step_start_false_never_starts()
    test_sweep_step_runs_then_drops_breadcrumb()
    test_should_sweep_here_gate()
    test_explored_cells_set()
    test_act_agent_starts_sweep_interrupt()
    test_act_agent_travel_does_not_sweep()
    test_pulse_routes_active_sweep_without_llm()
    test_tick_routes_sweeping_agent()
    print("\nAll cell-sweep checks passed.")


if __name__ == "__main__":
    main()
