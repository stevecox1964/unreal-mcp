"""Offline tests for the per-world sim run id (SR<n>, backlog #9).

Every run gets a monotonic per-world tag so observation screenshots and the
decision log are attributable to one run when debugging. Covers the allocator
(increment/persist/corruption/per-world), the bridge stamping observation
filenames, and the decision-log field. No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_sim_run.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import sim_run                       # noqa: E402
from agent_runtime.memory_store import MemoryStore      # noqa: E402
from agent_runtime.unreal_bridge import UnrealBridge    # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# ── Allocator: increment, persist, corruption, per-world ────────────────────────

def test_first_run_is_sr1_and_increments():
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "MCP_World"
        check("no counter yet -> current is SR0", sim_run.current_run(world) == "SR0")
        check("first allocation is SR1", sim_run.allocate_run(world) == "SR1")
        check("second allocation is SR2", sim_run.allocate_run(world) == "SR2")
        check("current_run reflects the last allocation", sim_run.current_run(world) == "SR2")
        check("counter persisted to sim_run.json",
              json.loads((world / "sim_run.json").read_text())["run"] == 2)


def test_allocation_survives_process_restart():
    # A fresh call (no in-memory state) must continue from the persisted counter.
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "w"
        sim_run.allocate_run(world)   # SR1
        sim_run.allocate_run(world)   # SR2
        check("a later run keeps counting up from disk", sim_run.allocate_run(world) == "SR3")


def test_corrupt_counter_restarts_from_one():
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "w"
        world.mkdir(parents=True)
        (world / "sim_run.json").write_text("{ not valid json")
        check("corrupt file reads as 0", sim_run.current_number(world) == 0)
        check("corrupt file re-allocates from SR1", sim_run.allocate_run(world) == "SR1")


def test_counter_is_per_world():
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "world_a"
        b = Path(tmp) / "world_b"
        sim_run.allocate_run(a)   # a -> SR1
        sim_run.allocate_run(a)   # a -> SR2
        check("second world counts independently", sim_run.allocate_run(b) == "SR1")
        check("first world is unaffected", sim_run.current_run(a) == "SR2")


# ── Bridge stamps the SR tag onto observation filenames ─────────────────────────

class _CaptureBridge(UnrealBridge):
    """Real bridge, but _send is stubbed to record params (no Unreal socket)."""
    def __init__(self):
        super().__init__()
        self.sent: list[tuple[str, dict]] = []

    def _send(self, command, params):
        self.sent.append((command, params))
        # get_observation reads success/location/current_action off the results.
        return {"success": True, "location": {"x": 0, "y": 0, "z": 0},
                "rotation": None, "current_action": "idle", "ai_state": None}


def test_observation_filename_carries_the_run_tag():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp) / "agents"
        bridge = _CaptureBridge()
        bridge.sim_run_id = "SR7"
        bridge.get_observation("BP_dufus", "dufus", agents_dir)

        capture = next(p for c, p in bridge.sent if c == "capture_camera_image")
        name = Path(capture["file_path"]).name
        check("observation png is prefixed with the run tag", name.startswith("SR7_observation_"))

        # capture_view (tagged) and capture_observation carry it too.
        view_path = bridge.capture_view("BP_dufus", "dufus", agents_dir, tag="wake")
        check("capture_view png carries the run tag", Path(view_path).name.startswith("SR7_observation_"))
        bridge.capture_observation("dufus", "BP_dufus", agents_dir)
        last = bridge.sent[-1][1]["file_path"]
        check("capture_observation png carries the run tag", Path(last).name.startswith("SR7_observation_"))


def test_bridge_defaults_to_sr0_before_a_run_starts():
    bridge = UnrealBridge()
    check("bridge defaults to SR0 until a run allocates one", bridge.sim_run_id == "SR0")


# ── Decision log carries the run tag ────────────────────────────────────────────

def test_decision_log_entry_has_sim_run():
    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp) / "MCP_World" / "agents"
        agents_dir.mkdir(parents=True)
        mem = MemoryStore(Path(tmp))
        mem.update_agents_dir(agents_dir)
        check("memory defaults to SR0", mem.sim_run_id == "SR0")
        mem.sim_run_id = "SR3"
        mem.record(agent_id="dufus",
                   observation={"_thought": "heading out"},
                   action={"type": "walk_to"},
                   result={"status": "success"})
        line = mem.decisions_log.read_text(encoding="utf-8").strip().splitlines()[-1]
        entry = json.loads(line)
        check("decision entry is stamped with the run tag", entry["sim_run"] == "SR3")


def main():
    test_first_run_is_sr1_and_increments()
    test_allocation_survives_process_restart()
    test_corrupt_counter_restarts_from_one()
    test_counter_is_per_world()
    test_observation_filename_carries_the_run_tag()
    test_bridge_defaults_to_sr0_before_a_run_starts()
    test_decision_log_entry_has_sim_run()
    print("\nAll sim-run checks passed.")


if __name__ == "__main__":
    main()
