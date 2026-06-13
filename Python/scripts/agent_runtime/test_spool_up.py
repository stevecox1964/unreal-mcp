"""Offline tests for the world clock and the wake-up spool-up.

The spool-up gives each agent one orientation moment at simulation start:
"it is {time}, you are at {place} — where should you be?" The answer (and all
behavior) comes from the agent's authored markdown; code only supplies the
senses. Fully offline — LLM and Unreal are stubbed. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_spool_up.py
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager  # noqa: E402
from agent_runtime.world_clock import WorldClock      # noqa: E402


class StubBridge:
    def __init__(self):
        self.facings = []        # yaws the sweep turned to
        self.teleports = []      # restore-facing calls
        self.executed = []       # actions executed in Unreal

    def get_character_transform(self, name):
        return {"location": {"x": 50.0, "y": 50.0, "z": 91.0},
                "rotation": {"x": 0, "y": 0, "z": 0}}

    def set_facing(self, name, location, yaw):
        self.facings.append(yaw)
        return {"status": "success"}

    def capture_view(self, name, agent_id, agents_dir, tag):
        return f"stub_{tag}.png"

    def teleport(self, name, location, rotation=None):
        self.teleports.append((location, rotation))
        return {"status": "success"}

    def execute_action(self, name, action):
        self.executed.append(action)
        return {"status": "success"}


class StubRouter:
    def __init__(self, orientation):
        self.orientation = orientation
        self.calls = []

    def orient(self, agent, context, memories):
        self.calls.append(context)
        return self.orientation


class StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.bound_unreal_actor_name = "BP_Stub"
        self.has_unreal_binding = True
        self.is_active = True
        self.goal = "authored goal"
        self.current_goal = "authored goal"
        self.allowed_actions = ["idle", "walk_to", "wander", "observe"]

    def set_goal(self, goal, agents_dir):
        self.goal = goal
        self.current_goal = goal


class StubPerceiver:
    def perceive(self, image_path, known_characters=None):
        return {
            "landmarks": [{"label": "Vegetable Truck", "bearing": "center",
                           "distance": "near", "confidence": 0.9}],
            "characters": [],
            "caption": "A truck parked by the roadside.",
        }


class StubMemory:
    def __init__(self):
        self.records = []

    def get_relevant_memories(self, agent_id):
        return []

    def record(self, **kwargs):
        self.records.append(kwargs)


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def make_manager(tmp, router):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=router,
                       unreal_bridge=StubBridge(), memory_store=StubMemory())
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.mode = "live"
    mgr.perceiver = StubPerceiver()
    agent = StubAgent("maren")
    mgr.agents = {agent.agent_id: agent}
    return mgr, agent


def main():
    # ── WorldClock math ────────────────────────────────────────────────────────
    clock = WorldClock()
    check("clock before start shows the configured start time",
          clock.now_text() == "Day 1, 08:00")

    clock = WorldClock(start="08:00", minutes_per_real_minute=60.0)
    clock._anchor = time.monotonic() - 90          # 1.5 real min x60 = 90 world min
    check("scaled clock advances world time", clock.now_text() == "Day 1, 09:30")

    clock = WorldClock(start="23:00", minutes_per_real_minute=60.0)
    clock._anchor = time.monotonic() - 120         # 2 real min x60 = 2 world hours
    check("clock rolls into the next day", clock.now_text() == "Day 2, 01:00")

    check("missing world.json gives the default clock",
          WorldClock.load(Path("does/not/exist.json")).now_text() == "Day 1, 08:00")

    # ── Wake-up: 180° sweep, orientation, place naming, first action ──────────
    with tempfile.TemporaryDirectory() as d:
        router = StubRouter({
            "agent_id": "maren",
            "thought_summary": "It is morning; I should be at my stall.",
            "current_goal": "Open the stall and arrange the wares",
            "action": {"type": "walk_to", "direction": "right"},
            "place": "vegetable stall",
            "memory_update": "Woke at the square at 08:00",
            "importance": 0.7,
        })
        mgr, agent = make_manager(d, router)
        bridge = mgr.bridge
        mgr.world_clock.start()
        asyncio.run(mgr._wake_agents())

        check("orient was called once per active agent", len(router.calls) == 1)
        ctx = router.calls[0]
        check("wake context carries world time", str(ctx.get("world_time", "")).startswith("Day 1, "))
        check("wake context carries a grid cell", (ctx.get("grid") or {}).get("key") is not None)
        check("sweep captured five views", len(ctx.get("views") or []) == 5)
        check("sweep spans 180 degrees left to right",
              bridge.facings == [-90.0, -45.0, 0.0, 45.0, 90.0])
        check("sweep views are named with movement directions",
              [v["direction"] for v in ctx["views"]]
              == ["left", "forward-left", "forward", "forward-right", "right"])
        check("sweep views carry perceived captions",
              all(v["caption"] == "A truck parked by the roadside." for v in ctx["views"]))
        check("sweep views carry perceived landmarks",
              ctx["views"][0]["landmarks"][0]["label"] == "Vegetable Truck")
        check("facing restored after the sweep", len(bridge.teleports) == 1)
        check("agent adopted its own intention as the goal",
              agent.current_goal == "Open the stall and arrange the wares")

        # First action: walk_to direction "right" from yaw 0 → toward +Y.
        check("first action executed in Unreal", len(bridge.executed) == 1)
        walked = bridge.executed[0]
        check("first action is a resolved walk_to", walked["type"] == "walk_to")
        tx, ty, _ = walked["location"]
        check("direction 'right' resolved toward +Y (~1500cm)",
              abs(tx - 50.0) < 1.0 and abs(ty - 1550.0) < 1.0)

        # Mental map: both the LLM-named place and the sweep's perceived
        # landmarks are written into the spatial map at the wake cell.
        smap = mgr._spatial_map("maren")
        labels = smap.place_labels(smap.cell_key(50.0, 50.0))
        check("named place saved to the spatial map ('been here before')",
              "vegetable stall" in labels)
        check("sweep sightings saved to the spatial map",
              "Vegetable Truck" in labels)

        records = mgr.memory.records
        check("wake moment recorded as a memory", len(records) == 1)
        check("wake memory keeps the orientation note",
              records[0]["memory_update"] == "Woke at the square at 08:00")
        check("wake observation is marked as a wake", records[0]["observation"]["wake"] is True)
        check("wake memory records the first action",
              records[0]["action"]["first_action"]["type"] == "walk_to")

    # ── Wake-up failure keeps the authored goal ───────────────────────────────
    with tempfile.TemporaryDirectory() as d:
        mgr, agent = make_manager(d, StubRouter(None))
        asyncio.run(mgr._wake_agents())
        check("failed wake-up keeps the authored goal", agent.current_goal == "authored goal")
        check("failed wake-up records nothing", len(mgr.memory.records) == 0)

    print("All spool-up checks passed.")


if __name__ == "__main__":
    main()
