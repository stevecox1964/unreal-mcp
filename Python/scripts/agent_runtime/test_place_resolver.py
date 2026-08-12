"""Offline tests for place-name navigation: name -> grid cell -> world center.

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_place_resolver.py

Covers:
  - WorldGrid.cell_center: inverse of locate(), returns the world (x, y) center.
  - PlaceDB.find_named_cell: case/whitespace-normalized exact + substring lookup.
  - AgentManager._execute_world_action: a walk_to with a string target_location
    resolves to a numeric bridge move instead of short-circuiting to idle.
  - AgentManager.preflight_places (#63): every authored agenda destination that
    resolves to nothing is reported *before* the run, with no LLM call.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager   # noqa: E402
from agent_runtime.place_db import PlaceDB              # noqa: E402
from agent_runtime.world_grid import WorldGrid          # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_cell_center_inverse_of_locate():
    g = WorldGrid(cell_size=400.0, bounds={"min_x": -2000, "min_y": -800, "max_x": 1999, "max_y": 799})
    # min corner cell (0,0): grid index (-5,-2) -> center ((-5+.5)*400, (-2+.5)*400)
    cx, cy = g.cell_center(0, 0)
    check("cell (0,0) center x", cx == -1800.0)
    check("cell (0,0) center y", cy == -600.0)
    # A center must locate back to the same cell it came from.
    loc = g.locate(cx, cy)
    check("center round-trips to its own cell", (loc["col"], loc["row"]) == (0, 0))
    loc = g.locate(*g.cell_center(9, 3))
    check("last cell center round-trips", (loc["col"], loc["row"]) == (9, 3))

    ub = WorldGrid()  # unbounded — col/row undefined, so no center
    check("unbounded grid has no cell center", ub.cell_center(0, 0) is None)


def test_find_named_cell():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        db.set_name("maren", 3, 4, "Village Square", "T0")
        db.set_name("dufus", 7, 2, "Don's Donuts", "T0")

        check("exact name (normalized case)", db.find_named_cell("village square") == (3, 4))
        check("exact name with whitespace", db.find_named_cell("  Village Square  ") == (3, 4))
        check("substring fallback", db.find_named_cell("donut") == (7, 2))
        check("unknown name -> None", db.find_named_cell("the moon") is None)
        check("empty name -> None", db.find_named_cell("   ") is None)


class StubBridge:
    """Records the action it was asked to execute; reports success."""
    def __init__(self):
        self.last = None

    def execute_action(self, actor_name, action):
        self.last = (actor_name, action)
        return {"status": "accepted", "action": action.get("type")}


class StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.bound_unreal_actor_name = f"BP_{agent_id}"
        self.bound_unreal_actor_label = agent_id
        self.unreal_actor_name = agent_id
        self.has_unreal_binding = True


def _manager_with_place(tmp, bridge):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=bridge, memory_store=None)
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.world_grid = WorldGrid(cell_size=400.0,
                               bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})
    mgr.place_db = PlaceDB(Path(tmp) / "world_places.db")
    mgr.agents = {}
    return mgr


def test_walk_to_named_place_resolves_to_location():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = StubBridge()
        mgr = _manager_with_place(tmp, bridge)
        agent = StubAgent("dufus")
        mgr.agents = {"dufus": agent}
        # cell (5,5) is grid index (0,0) -> center (200, 200) for this bounds set.
        mgr.place_db.set_name("dufus", 5, 5, "village square", "T0")

        observation = {"location": {"x": 1000.0, "y": -500.0, "z": 90.0}}
        result = mgr._execute_world_action(
            agent, {"type": "walk_to", "target_location": "village square"}, observation
        )

        check("named walk_to was sent to the bridge (not idled)",
              bridge.last is not None and bridge.last[1].get("type") == "walk_to")
        loc = bridge.last[1].get("location")
        check("resolved to the cell center x", loc is not None and loc[0] == 200.0)
        check("resolved to the cell center y", loc[1] == 200.0)
        check("z carried from the agent's current location", loc[2] == 90.0)
        check("result is not an idle", result.get("action") != "idle")


def test_unknown_named_place_falls_back_to_idle():
    with tempfile.TemporaryDirectory() as tmp:
        bridge = StubBridge()
        mgr = _manager_with_place(tmp, bridge)
        agent = StubAgent("dufus")
        mgr.agents = {"dufus": agent}

        observation = {"location": {"x": 1000.0, "y": -500.0, "z": 90.0}}
        result = mgr._execute_world_action(
            agent, {"type": "walk_to", "target_location": "atlantis"}, observation
        )
        # Falls through to the bridge, whose string short-circuit idles gracefully.
        sent = bridge.last[1] if bridge.last else {}
        check("unknown place did not invent a numeric location", "location" not in sent)
        check("unknown place idles", result.get("action") == "idle"
              or result.get("note", "").find("not resolved") >= 0
              or sent.get("target_location") == "atlantis")


class StubScheduledAgent(StubAgent):
    """An agent carrying an authored agenda, as ``preflight_places`` reads it."""
    def __init__(self, agent_id, tasks, is_active=True):
        super().__init__(agent_id)
        self.is_active = is_active
        self.authored_agenda = {"schema_version": 1, "tasks": tasks}


def _task(task_id, place, start="08:00", end="09:00"):
    return {"id": task_id, "start": start, "end": end, "place": place,
            "objective": f"do {task_id}", "completion": {"type": "time_block_ends"}}


class ExplodingLLM:
    """Any call means the preflight tried to generate a plan — that must not happen."""
    def ask(self, *args, **kwargs):
        raise AssertionError("preflight_places must not call the LLM")


def test_preflight_reports_unresolvable_agenda_places():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager_with_place(tmp, StubBridge())
        mgr.llm = ExplodingLLM()
        mgr.place_db.set_name("dufus", 5, 5, "sheriff station square", "T0")

        # The live SR miss: "Sheriff's office" is neither an exact nor a substring
        # match for "sheriff station square", so the task has no destination.
        agent = StubScheduledAgent("maren", [
            _task("news", "Sheriff's office", "18:00", "19:00"),
            _task("square", "sheriff station square", "06:00", "07:00"),
            _task("anywhere", ""),
        ])
        mgr.agents = {"maren": agent}

        rows = mgr.preflight_places()
        check("exactly one unresolved place reported", len(rows) == 1)
        row = rows[0]
        check("the unresolved place is the sheriff's office", row["place"] == "Sheriff's office")
        check("row names the agent", row["agent_id"] == "maren")
        check("row names the task", row["task_id"] == "news")
        check("row carries the time window", (row["start"], row["end"]) == ("18:00", "19:00"))

        # The regression this guards: renaming the task's place to the surveyed
        # name must clear it. A preflight that always fires is as useless as one
        # that never does.
        agent.authored_agenda["tasks"][0]["place"] = "sheriff station square"
        check("resolvable agenda reports nothing", mgr.preflight_places() == [])


def test_preflight_skips_inactive_agents_and_survives_no_agenda():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager_with_place(tmp, StubBridge())
        mgr.llm = ExplodingLLM()
        parked = StubScheduledAgent("maren", [_task("news", "Atlantis")], is_active=False)
        mgr.agents = {"maren": parked}
        check("a parked agent is not preflighted", mgr.preflight_places() == [])

        parked.is_active = True
        check("an active agent with a bad place is reported",
              len(mgr.preflight_places()) == 1)

        # An agent with no authored agenda must not trigger plan generation.
        bare = StubAgent("dufus")
        bare.is_active = True
        bare.daily_schedule_day = ""
        bare.daily_schedule_blocks = []
        mgr.agents = {"dufus": bare}
        check("no authored agenda reports nothing (and asks no model)",
              mgr.preflight_places() == [])


def test_preflight_accepts_owned_places():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = _manager_with_place(tmp, StubBridge())
        mgr.llm = ExplodingLLM()
        # An APC-owned place resolves just as a community name does — the
        # preflight must walk the same chain the navigator will.
        mgr.place_db.add_owned_place("maren", 5, 5, "the vegetable truck",
                                     dx=0.0, dy=0.0, source="authored")
        mgr.agents = {"maren": StubScheduledAgent("maren", [_task("sales", "the vegetable truck")])}
        check("an owned place counts as resolved", mgr.preflight_places() == [])


def main():
    test_cell_center_inverse_of_locate()
    test_find_named_cell()
    test_walk_to_named_place_resolves_to_location()
    test_unknown_named_place_falls_back_to_idle()
    test_preflight_reports_unresolvable_agenda_places()
    test_preflight_skips_inactive_agents_and_survives_no_agenda()
    test_preflight_accepts_owned_places()
    print("\nAll place-resolver checks passed.")


if __name__ == "__main__":
    main()
