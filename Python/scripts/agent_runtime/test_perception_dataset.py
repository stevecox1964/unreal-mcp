"""Offline tests for the perception dataset recorder (#79).

Dufus's captures are the VLM training corpus, but only survey composites kept
their text: the per-tick stream computed a full label every frame (caption,
landmarks, footing, ground_ahead, path_ahead) and overwrote it in
last_perception.json. The recorder appends one JSON line per perceived image
to observations/perception_log.jsonl, so every frame becomes a training pair
at the moment it is perceived.

Fully offline (no LLM, no Unreal). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_perception_dataset.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import AgentManager  # noqa: E402
from agent_runtime.world_grid import WorldGrid  # noqa: E402


class _Stub:
    def __getattr__(self, _):
        return lambda *a, **k: None


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


SEEN = {
    "caption": "A paved street with mobile homes.",
    "footing": "road",
    "ground_ahead": "grass",
    "path_ahead": "dead_end",
    "landmarks": [{"label": "green donation bin", "bearing": "right",
                   "distance": "near", "confidence": 0.9}],
    "characters": [],
    "model": "test-vlm",
}


def make_manager(tmp):
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=_Stub(),
                       unreal_bridge=_Stub(), memory_store=_Stub())
    mgr._agents_dir = Path(tmp) / "agents"
    mgr.sim_run_id = "SR99"
    mgr.world_grid = WorldGrid(
        cell_size=3000.0,
        bounds={"min_x": 0.0, "min_y": 0.0,
                "max_x": 16 * 3000.0, "max_y": 11 * 3000.0},
    )
    return mgr


def log_lines(mgr, agent_id="dufus"):
    path = mgr._agents_dir / agent_id / "observations" / "perception_log.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]


def test_a_pair_is_recorded_with_its_facts():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp)
    grid = mgr.world_grid.locate(16500.0, 16500.0)
    mgr._record_perception_pair(
        "dufus", r"C:\anywhere\SR99_observation_x.png", SEEN,
        location={"x": 16500.0, "y": 16500.0, "z": 100.0}, yaw=270.0,
        grid=grid, world_time="Day 1, 09:00", context="tick")

    lines = log_lines(mgr)
    check("one perceived image is one line", len(lines) == 1)
    line = lines[0]
    check("the image is stored by basename",
          line["image"] == "SR99_observation_x.png")
    check("the caption travels with the image",
          line["caption"] == SEEN["caption"])
    check("the new #77 labels are kept",
          (line["ground_ahead"], line["path_ahead"]) == ("grass", "dead_end"))
    check("footing is kept", line["footing"] == "road")
    check("landmarks are kept", line["landmarks"] == SEEN["landmarks"])
    check("position is kept", line["at"] == [16500.0, 16500.0])
    check("the heading is compass, not raw yaw", line["heading"] == "N")
    check("the cell is kept", line["cell"] == "5,5")
    check("the run is attributed", line["sim_run"] == "SR99")
    check("the context tags the capture kind", line["context"] == "tick")
    check("world time is kept", line["world_time"] == "Day 1, 09:00")
    check("a clean perception carries no error key", "error" not in line)


def test_the_log_appends_and_survives_misses():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp)
    mgr._record_perception_pair("dufus", "a.png", SEEN, context="wake", yaw=0.0)
    mgr._record_perception_pair("dufus", "b.png",
                                {"error": "GEMINI 500", "caption": ""},
                                context="survey_sweep")
    lines = log_lines(mgr)
    check("lines append, never overwrite", len(lines) == 2)
    check("a failed perception is recorded, not hidden",
          lines[1]["error"] == "GEMINI 500")
    check("a missing facing stays None rather than guessed",
          lines[1]["heading"] is None)


def test_nothing_to_record_writes_nothing():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp)
    mgr._record_perception_pair("dufus", None, SEEN)         # no image
    mgr._record_perception_pair("dufus", "a.png", None)      # no perception
    check("no image or no perception writes no line", log_lines(mgr) == [])

    mgr._agents_dir = None                                    # before a run
    mgr._record_perception_pair("dufus", "a.png", SEEN)       # must not raise
    check("no agents dir degrades silently", True)


if __name__ == "__main__":
    test_a_pair_is_recorded_with_its_facts()
    test_the_log_appends_and_survives_misses()
    test_nothing_to_record_writes_nothing()
    print("All perception-dataset tests passed.")
