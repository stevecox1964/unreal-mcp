"""Offline tests for adaptive tick pacing and reset_agents.

Stubs Unreal entirely (no network, no Gemini). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_pacing_and_reset.py

Checks:
  1. The sim loop's base sleep starts AFTER tick processing, so the effective
     interval is processing time + base — slow observations stretch the
     interval instead of letting ticks pile up.
  2. reset_agents teleports back to the recorded start transform, clears
     per-run timers, restores seed memories, and deletes the spatial map.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager  # noqa: E402
from agent_runtime.memory_store import MemoryStore    # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# ── 1. Adaptive pacing ────────────────────────────────────────────────────────

class SlowBridge:
    """get_observation blocks for `delay` seconds, like a slow camera+Gemini hop."""
    def __init__(self, delay: float):
        self.delay = delay
        self.tick_starts: list[float] = []

    def get_observation(self, name, agent_id, agents_dir):
        self.tick_starts.append(time.monotonic())
        time.sleep(self.delay)
        return {"actor_name": name, "image_path": None, "location": None,
                "current_action": "idle", "ai_state": None}

    def is_scene_changed(self, agent_id, image_path):
        return False  # short-circuits pulse_agent right after the observation


class StubAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.bound_unreal_actor_name = f"BP_{agent_id}"
        self.bound_unreal_actor_label = agent_id
        self.unreal_actor_name = agent_id
        self.has_unreal_binding = True
        self.is_active = True
        self.is_busy = False

    def cooldown_expired(self):
        return True

    def mark_ticked(self, agents_dir):
        pass


async def run_pacing() -> None:
    delay, base, runtime = 0.8, 1, 4.5
    bridge = SlowBridge(delay)
    mgr = AgentManager(worlds_dir=Path("."), llm_router=None,
                       unreal_bridge=bridge, memory_store=None)
    mgr.agents = {"a": StubAgent("a")}
    mgr.tick_seconds = base
    mgr.running = True
    task = asyncio.create_task(mgr._loop())
    await asyncio.sleep(runtime)
    mgr.running = False
    task.cancel()

    starts = bridge.tick_starts
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    print(f"tick starts: {len(starts)}, gaps: {[f'{g:.2f}' for g in gaps]}")
    # Fixed 1 s pacing would fit ~5 ticks in 4.5 s; expanded (~1.8 s) fits 3.
    check("interval expanded to processing + base", all(g >= delay + base - 0.1 for g in gaps))
    check("ticks did not pile up", len(starts) <= 3)
    check("loop kept ticking", len(starts) >= 2)


# ── 2. reset_agents ───────────────────────────────────────────────────────────

class ResetBridge:
    def __init__(self):
        self.loc = {"x": 100.0, "y": 200.0, "z": 90.0}
        self.rot = {"x": 0.0, "y": 45.0, "z": 0.0}
        self.teleports: list[dict] = []

    def get_current_level(self):
        return "TestWorld"

    def find_actor(self, name):
        return {"name": f"BP_{name}", "label": name, "class": "BP_TestNPC_C"}

    def get_character_transform(self, actor_name):
        return {"location": dict(self.loc), "rotation": dict(self.rot)}

    def teleport(self, actor_name, location, rotation=None):
        self.teleports.append({"actor": actor_name, "location": location, "rotation": rotation})
        self.loc = dict(location)
        return {"success": True, "status": "success"}

    def clear_scene_cache(self):
        pass


def make_agent_files(agents_dir: Path, agent_id: str) -> Path:
    d = agents_dir / agent_id
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps({
        "agent_id": agent_id, "unreal_actor_name": agent_id, "is_active": True,
        "last_tick_time": "2026-06-01T00:00:00+00:00",
        "last_spoke_time": "2026-06-01T00:00:00+00:00",
    }), encoding="utf-8")
    for f in ("character.md", "goals.md", "rules.md"):
        (d / f).write_text("test", encoding="utf-8")
    (d / "tools.json").write_text(json.dumps({"allowed_actions": ["walk_to"]}), encoding="utf-8")
    return d


async def run_reset() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        worlds = Path(tmp)
        agents_dir = worlds / "TestWorld" / "agents"
        d = make_agent_files(agents_dir, "testy")
        (d / "memory.seed.json").write_text(
            json.dumps({"agent_id": "testy", "memories": [{"timestamp": "t0", "importance": 0.8, "text": "seed"}]}),
            encoding="utf-8")
        (d / "memory.json").write_text(
            json.dumps({"agent_id": "testy", "memories": [{"timestamp": "t1", "importance": 0.5, "text": "runtime junk"}]}),
            encoding="utf-8")
        (d / "spatial_map.json").write_text("{}", encoding="utf-8")

        bridge = ResetBridge()
        mgr = AgentManager(worlds_dir=worlds, llm_router=None,
                           unreal_bridge=bridge, memory_store=MemoryStore(worlds))
        started = await mgr.start_simulation(tick_seconds=1, active_agents=["testy"])
        check("simulation started", started["status"] == "started")

        state = json.loads((d / "state.json").read_text(encoding="utf-8"))
        check("start transform recorded at first start",
              state.get("start_location") == {"x": 100.0, "y": 200.0, "z": 90.0})

        # Avatar wanders off; then reset.
        bridge.loc = {"x": -500.0, "y": 999.0, "z": 90.0}
        result = await mgr.reset_agents()

        check("reset stopped the running sim", result["stopped_simulation"] and not mgr.running)
        entry = result["agents"][0]
        check("agent teleported", entry["teleported"])
        check("teleport went to the start location",
              bridge.teleports[-1]["location"] == {"x": 100.0, "y": 200.0, "z": 90.0})

        state = json.loads((d / "state.json").read_text(encoding="utf-8"))
        check("run timers cleared", "last_tick_time" not in state and "last_spoke_time" not in state)
        check("start transform survives reset", state.get("start_location") is not None)

        mem = json.loads((d / "memory.json").read_text(encoding="utf-8"))
        check("memories restored from seed",
              entry["memories"] == "seeded" and [m["text"] for m in mem["memories"]] == ["seed"])
        check("spatial map deleted", not (d / "spatial_map.json").exists())

        # Second run after reset records nothing new (transform already known).
        started = await mgr.start_simulation(tick_seconds=1, active_agents=["testy"])
        check("sim restarts after reset", started["status"] == "started")
        await mgr.stop_simulation()


async def main() -> None:
    await run_pacing()
    await run_reset()
    print("\nAll pacing + reset checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
