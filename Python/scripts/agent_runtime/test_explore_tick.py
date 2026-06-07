"""Offline integration test for AgentManager explore mode.

Stubs Unreal (bridge / memory / agent) but hits REAL Gemini on a saved
screenshot, so it exercises the whole explore tick:
    observe -> perceive (Gemini) -> ingest -> frontier -> walk -> persist.

Needs GEMINI_API_KEY in Python/.env and network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_explore_tick.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager  # noqa: E402

_FRAME = ROOT / "worlds/MCP_World/agents/maren/observations/observation_20260514_010330.png"


class StubBridge:
    """Fake Unreal: serves a saved frame, advances position to each walk target."""
    def __init__(self, frame: str):
        self.frame = frame
        self.loc = {"x": 50.0, "y": 50.0, "z": 91.0}
        self.moves: list[dict] = []

    def get_observation(self, name, agent_id, agents_dir):
        return {"actor_name": name, "image_path": self.frame,
                "location": dict(self.loc), "current_action": "idle", "ai_state": None}

    def is_scene_changed(self, agent_id, image_path):
        return True  # force perception every tick in the test

    def execute_action(self, name, action):
        self.moves.append(action)
        if action.get("location"):
            self.loc = dict(action["location"])  # avatar "arrives" at the target
        return {"status": "accepted"}


class StubAgent:
    def __init__(self, agent_id, actor):
        self.agent_id = agent_id
        self.bound_unreal_actor_name = actor
        self.bound_unreal_actor_label = actor
        self.unreal_actor_name = actor
        self.has_unreal_binding = True
        self.ticks = 0

    def mark_ticked(self, agents_dir):
        self.ticks += 1


class StubMemory:
    def record(self, **kwargs):
        pass


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def main():
    if not _FRAME.exists():
        print(f"SKIP: sample frame missing: {_FRAME}")
        return

    with tempfile.TemporaryDirectory() as d:
        agents_dir = Path(d) / "agents"
        bridge = StubBridge(str(_FRAME))
        mgr = AgentManager(worlds_dir=Path(d), llm_router=None,
                           unreal_bridge=bridge, memory_store=StubMemory())
        mgr._agents_dir = agents_dir
        mgr.mode = "explore"
        agent = StubAgent("maren", "BP_Maren")
        mgr.agents = {agent.agent_id: agent}

        r1 = mgr._pulse_explore(agent)
        print("tick1:", json.dumps({k: r1[k] for k in ("cell", "landmarks_seen", "target_cell")}))
        check("tick1 perceived landmarks from Gemini", r1["landmarks_seen"] > 0)
        check("tick1 occupied origin cell", r1["cell"] == "0,0")
        check("tick1 chose a frontier target", r1["target_cell"] is not None)
        check("tick1 issued a walk_to", len(bridge.moves) == 1 and bridge.moves[0]["type"] == "walk_to")
        check("tick1 mapped one visited cell", r1["map_stats"]["cells_visited"] == 1)
        check("tick1 named real places", r1["map_stats"]["distinct_labels"] > 0)

        r2 = mgr._pulse_explore(agent)
        print("tick2:", json.dumps({k: r2[k] for k in ("cell", "landmarks_seen", "target_cell")}))
        check("avatar moved to a new cell", r2["cell"] != r1["cell"])
        check("tick2 issued a second walk_to", len(bridge.moves) == 2)
        check("exploration expanded coverage", r2["map_stats"]["cells_visited"] == 2)

        # Persistence + nav-edge linkage
        saved = json.loads((agents_dir / "maren" / "spatial_map.json").read_text(encoding="utf-8"))
        cells = saved["cells"]
        check("map persisted to disk", len(cells) >= 2)
        check("traversed edge recorded", any(c["edges"] for c in cells.values()))
        labels = sorted({lbl for c in cells.values() for lbl in c["landmarks"]})
        check("persisted landmarks are vision labels", len(labels) > 0)
        print("\nlabels discovered:", labels)
        print("All explore-tick checks passed.")


if __name__ == "__main__":
    main()
