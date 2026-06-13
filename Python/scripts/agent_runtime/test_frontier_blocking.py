"""Offline test for hardened frontier blocking in explore mode.

A failed walk_to must NOT permanently block a frontier cell unless there is
evidence the cell is genuinely unreachable: the avatar is adjacent to it, or
the same cell failed _MAX_FRONTIER_FAILURES consecutive attempts. Fully
offline (no Unreal, no Gemini — observations carry no image). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_frontier_blocking.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager, _MAX_FRONTIER_FAILURES  # noqa: E402


class StubBridge:
    """Fake Unreal: position is scripted, walk_to outcome is scripted per call."""
    def __init__(self):
        self.loc = {"x": 50.0, "y": 50.0, "z": 91.0}
        self.walk_results: list[dict] = []   # popped front on each walk_to
        self.moves: list[dict] = []

    def get_observation(self, name, agent_id, agents_dir):
        return {"actor_name": name, "image_path": None,
                "location": dict(self.loc), "current_action": "idle", "ai_state": None}

    def is_scene_changed(self, agent_id, image_path):
        return False

    def execute_action(self, name, action):
        self.moves.append(action)
        if self.walk_results:
            return self.walk_results.pop(0)
        return {"status": "accepted"}


class StubAgent:
    def __init__(self, agent_id, actor):
        self.agent_id = agent_id
        self.bound_unreal_actor_name = actor
        self.bound_unreal_actor_label = actor
        self.unreal_actor_name = actor
        self.has_unreal_binding = True

    def mark_ticked(self, agents_dir):
        pass


class StubMemory:
    def record(self, **kwargs):
        pass


def is_blocked(smap, key):
    cell = smap.describe(key)
    return bool(cell and cell["blocked"])   # no entry at all = never blocked


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def make_manager(tmp, bridge):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=None,
                       unreal_bridge=bridge, memory_store=StubMemory())
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.mode = "explore"
    agent = StubAgent("maren", "BP_Maren")
    mgr.agents = {agent.agent_id: agent}
    return mgr, agent


def push_frontier_out(mgr, agent_id):
    """Visit the avatar's 8 neighbour cells so the nearest frontier is ~2 cells
    away (farther than the adjacency threshold of 1.5 x cell_size)."""
    smap = mgr._spatial_map(agent_id)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx, cy = (dx + 0.5) * smap.cell_size, (dy + 0.5) * smap.cell_size
            smap.ingest(cx, cy)
    return smap


def main():
    # ── Adjacent frontier + walk error → blocked immediately ──────────────────
    with tempfile.TemporaryDirectory() as d:
        bridge = StubBridge()
        mgr, agent = make_manager(d, bridge)
        bridge.walk_results = [{"error": "no path"}]
        r = mgr._pulse_explore(agent)
        smap = mgr._spatial_map(agent.agent_id)
        cell = smap.describe(r["target_cell"])
        check("adjacent frontier with walk error is blocked on first attempt",
              cell is not None and cell["blocked"])

    # ── Far frontier + transient errors → retried, blocked only after N ──────
    with tempfile.TemporaryDirectory() as d:
        bridge = StubBridge()
        mgr, agent = make_manager(d, bridge)
        smap = push_frontier_out(mgr, agent.agent_id)
        bridge.walk_results = [{"error": "no path"}] * _MAX_FRONTIER_FAILURES

        targets = []
        for i in range(_MAX_FRONTIER_FAILURES):
            r = mgr._pulse_explore(agent)
            targets.append(r["target_cell"])
            blocked = is_blocked(smap, r["target_cell"])
            if i < _MAX_FRONTIER_FAILURES - 1:
                check(f"far frontier not blocked after failure {i + 1}", not blocked)
            else:
                check(f"far frontier blocked after {_MAX_FRONTIER_FAILURES} consecutive failures", blocked)
        check("same cell was retried each tick", len(set(targets)) == 1)
        tx, ty = smap.cell_center(targets[0])
        check("test targeted a non-adjacent cell",
              ((tx - 50.0) ** 2 + (ty - 50.0) ** 2) ** 0.5 > smap.cell_size * 1.5)

    # ── A successful walk clears the failure counter ──────────────────────────
    with tempfile.TemporaryDirectory() as d:
        bridge = StubBridge()
        mgr, agent = make_manager(d, bridge)
        smap = push_frontier_out(mgr, agent.agent_id)
        bridge.walk_results = [
            {"error": "no path"}, {"error": "no path"},   # 2 failures (1 below threshold)
            {"status": "accepted"},                        # success — counter resets
            {"error": "no path"}, {"error": "no path"},   # 2 more failures
        ]
        target = None
        for _ in range(5):
            r = mgr._pulse_explore(agent)
            target = r["target_cell"]
        check("cell not blocked after success reset the counter",
              not is_blocked(smap, target))
        check("failure counter restarted after success",
              mgr._frontier_failures["maren"].get(target) == 2)

    print("All frontier-blocking checks passed.")


if __name__ == "__main__":
    main()
