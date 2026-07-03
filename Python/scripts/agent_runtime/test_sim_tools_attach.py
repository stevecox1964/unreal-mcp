"""Offline tests for the MCP simulation tools as runner attachers (#3 / 2.4).

The director tools no longer host an AgentManager in the MCP process — they
attach to the standalone sim_runner over its control API via RunnerClient
(the runner owns the sim's lifetime and the single Unreal socket). Here the
whole chain runs in-process: MCP tool → RunnerClient → runner app (TestClient)
→ stub manager. No Unreal, no network, no LLM. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_sim_tools_attach.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient                 # noqa: E402
from agent_runtime.runner_app import build_control_app    # noqa: E402
from agent_runtime.runner_client import RunnerClient       # noqa: E402
from tools.simulation_tools import register_simulation_tools   # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


class StubMCP:
    """Captures @mcp.tool() registrations so each tool is directly callable."""
    def __init__(self):
        self.tools = {}

    def tool(self):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn
        return deco


class StubManager:
    """The runner-side manager the tools ultimately drive (call-recording)."""
    def __init__(self):
        self.calls = []

    def get_status(self):
        return {"running": True, "tick_count": 7}

    def recent_events(self, limit=20):
        return [{"agent_id": "dufus", "action_type": "walk_to"}][:limit]

    def clear_events(self):
        return 0

    async def start_simulation(self, tick_seconds=1, active_agents=None, mode="live"):
        self.calls.append(("start", tick_seconds, tuple(active_agents or []), mode))
        return {"status": "started", "mode": mode}

    async def stop_simulation(self):
        self.calls.append(("stop",))
        return {"status": "stopped"}

    async def pause_simulation(self):
        self.calls.append(("pause",))
        return {"status": "paused"}

    async def resume_simulation(self):
        self.calls.append(("resume",))
        return {"status": "resumed"}

    def list_agents(self):
        return [{"agent_id": "dufus"}]

    def inspect_agent(self, agent_id):
        return {"agent_id": agent_id, "tier": 2}

    def set_agent_goal(self, agent_id, goal):
        self.calls.append(("set_goal", agent_id, goal))
        return {"status": "updated", "goal": goal}

    async def pulse_agent(self, agent_id):
        self.calls.append(("pulse", agent_id))
        return {"agent_id": agent_id, "action": "idle"}

    async def reset_agents(self):
        return {"status": "reset"}

    async def reset_world_places(self):
        return {"status": "reset", "tables": ["place_cells"]}

    def resync(self):
        return {"status": "resynced", "level": "TestWorld"}

    def generate_world_grid(self, cell_size=400.0, padding=800.0):
        self.calls.append(("world_grid", cell_size, padding))
        return {"status": "generated", "level": "TestWorld"}


EXPECTED_TOOLS = {
    "reload_llm_environment", "start_simulation", "stop_simulation",
    "pause_simulation", "resume_simulation", "get_simulation_status",
    "list_agents", "inspect_agent", "set_agent_goal", "force_agent_tick",
    "get_recent_events", "reset_agents", "reset_world_places",
    "generate_world_grid", "resync_simulation",
}


def test_tools_drive_the_runner_end_to_end():
    mcp = StubMCP()
    mgr = StubManager()
    rc = RunnerClient(client=TestClient(build_control_app(mgr)))
    register_simulation_tools(mcp, runner=rc)

    check("full director surface registered", set(mcp.tools) == EXPECTED_TOOLS)
    t = mcp.tools

    r = t["start_simulation"](tick_seconds=2, active_agents=["dufus"], mode="explore")
    check("start reaches the manager through the runner",
          r["status"] == "started" and mgr.calls[-1] == ("start", 2, ("dufus",), "explore"))
    check("status round-trips", t["get_simulation_status"]()["tick_count"] == 7)
    check("pause round-trips", t["pause_simulation"]()["status"] == "paused")
    check("resume round-trips", t["resume_simulation"]()["status"] == "resumed")
    check("list_agents keeps its MCP shape",
          t["list_agents"]() == {"agents": [{"agent_id": "dufus"}]})
    check("inspect round-trips", t["inspect_agent"]("maren")["agent_id"] == "maren")
    check("set_goal forwards both args",
          t["set_agent_goal"]("dufus", "patrol") and mgr.calls[-1] == ("set_goal", "dufus", "patrol"))
    check("force tick pulses through",
          t["force_agent_tick"]("dufus")["action"] == "idle" and mgr.calls[-1] == ("pulse", "dufus"))
    check("events keep their MCP shape",
          t["get_recent_events"](5)["events"][0]["action_type"] == "walk_to")
    check("reset_agents round-trips", t["reset_agents"]()["status"] == "reset")
    check("reset_world_places round-trips",
          t["reset_world_places"]()["tables"] == ["place_cells"])
    check("generate_world_grid forwards args",
          t["generate_world_grid"](cell_size=500.0)["status"] == "generated"
          and mgr.calls[-1] == ("world_grid", 500.0, 800.0))
    check("resync round-trips", t["resync_simulation"]()["level"] == "TestWorld")
    check("stop round-trips", t["stop_simulation"]()["status"] == "stopped")


class DownClient:
    """Transport that always fails — a runner that isn't running."""
    def get(self, *a, **k):
        raise ConnectionError("connection refused")

    def post(self, *a, **k):
        raise ConnectionError("connection refused")


def test_no_runner_fails_loud_not_hosting():
    mcp = StubMCP()
    register_simulation_tools(mcp, runner=RunnerClient(client=DownClient()))

    for name in ("get_simulation_status", "start_simulation", "list_agents"):
        r = mcp.tools[name]()
        check(f"{name} without a runner reports error", r.get("status") == "error")
        check(f"{name} error says how to start the runner", "sim_runner" in r.get("error", ""))


def test_tools_no_longer_host_the_manager():
    """Contract pin: attach, don't host — no in-process AgentManager fallback."""
    src = (ROOT / "tools" / "simulation_tools.py").read_text(encoding="utf-8")
    check("tools never import get_agent_manager", "get_agent_manager" not in src)
    check("tools go through RunnerClient", "RunnerClient" in src)


def test_manager_generate_world_grid_offline():
    """The scan logic moved into AgentManager (#3/2.4) — verify with a stub bridge."""
    from agent_runtime.agent_manager import AgentManager

    class GridBridge:
        def get_current_level(self):
            return "TestWorld"

        def get_level_actors(self):
            return [{"location": [0.0, 0.0, 0.0]},
                    {"location": [1000.0, 2000.0, 50.0]},
                    {"name": "no_location"}]

        def print_to_screen(self, message, key=-1, duration=30.0):
            pass

    with tempfile.TemporaryDirectory() as tmp:
        mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                           unreal_bridge=GridBridge(), memory_store=None)
        out = mgr.generate_world_grid(cell_size=400.0, padding=100.0)
        check("grid generated from the actor scan", out["status"] == "generated")
        check("bounds = actor extent + padding",
              out["bounds"] == {"min_x": -100.0, "min_y": -100.0,
                                "max_x": 1100.0, "max_y": 2100.0})
        check("grid file written under worlds/<level>",
              (Path(tmp) / "TestWorld" / "world_grid.json").exists())
        check("live grid swapped in", mgr.world_grid.has_bounds)

    class NoLevelBridge(GridBridge):
        def get_current_level(self):
            return None

    with tempfile.TemporaryDirectory() as tmp:
        mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                           unreal_bridge=NoLevelBridge(), memory_store=None)
        check("no level -> loud error",
              mgr.generate_world_grid()["status"] == "error")


def main():
    test_tools_drive_the_runner_end_to_end()
    test_no_runner_fails_loud_not_hosting()
    test_tools_no_longer_host_the_manager()
    test_manager_generate_world_grid_offline()
    print("\nAll sim-tools-attach checks passed.")


if __name__ == "__main__":
    main()
