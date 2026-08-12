"""Offline tests for live-path stuck detection (AgentManager._detect_stuck).

A world may have imperfect navmesh, so an avatar can wedge against an obstacle
(a parked van) yet still report ai_state="moving". The lizard brain watches real
position deltas: after a few "moving but didn't advance" ticks it flags the agent
stuck so it re-decides instead of grinding into the obstacle forever. The flag is
a *sense* — the prompt only reports the fact; the LLM decides what to do. Fully
offline (no LLM, no Unreal). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_stuck_detection.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import (  # noqa: E402
    AgentManager, _STUCK_TICKS, _STUCK_PROGRESS_CM, _WEDGE_BUDGET_TICKS,
)
from agent_runtime.llm_router import _wedge_text  # noqa: E402


class _Stub:
    """Stands in for any collaborator the detector never calls."""
    def __getattr__(self, _):
        return lambda *a, **k: None


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def make_manager(tmp):
    return AgentManager(worlds_dir=Path(tmp), llm_router=_Stub(),
                        unreal_bridge=_Stub(), memory_store=_Stub())


def main():
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp)
    aid = "dufus"

    # ── A genuinely advancing avatar is never flagged ──────────────────────────
    step = _STUCK_PROGRESS_CM + 50.0
    flagged = False
    x = 0.0
    mgr._detect_stuck(aid, (x, 0.0), moving=True)         # seed position
    for _ in range(_STUCK_TICKS + 3):
        x += step
        flagged = flagged or mgr._detect_stuck(aid, (x, 0.0), moving=True)
    check("an avatar that keeps advancing is never flagged stuck", not flagged)

    # ── A pinned-but-"moving" avatar is flagged after _STUCK_TICKS ─────────────
    mgr = make_manager(tmp)
    mgr._detect_stuck(aid, (10.0, 10.0), moving=True)     # seed position
    results = [mgr._detect_stuck(aid, (10.0, 10.0), moving=True)
               for _ in range(_STUCK_TICKS)]
    check("pinned avatar is NOT flagged before the threshold",
          not any(results[:-1]))
    check("pinned avatar IS flagged once the no-progress threshold is reached",
          results[-1] is True)

    # ── After flagging, a grace window resets so we don't flag every tick ──────
    next_tick = mgr._detect_stuck(aid, (10.0, 10.0), moving=True)
    check("stuck flag resets after firing (no per-tick LLM hammering)",
          next_tick is False)

    # ── A sub-threshold drift still counts as stuck (wedged, barely sliding) ───
    mgr = make_manager(tmp)
    drift = _STUCK_PROGRESS_CM - 10.0
    mgr._detect_stuck(aid, (0.0, 0.0), moving=True)
    creeping = [mgr._detect_stuck(aid, (i * drift, 0.0), moving=True)
                for i in range(1, _STUCK_TICKS + 1)]
    check("an avatar drifting less than the progress threshold is flagged stuck",
          creeping[-1] is True)

    # ── An idle (not moving) avatar is never 'stuck' — that's the other path ───
    mgr = make_manager(tmp)
    mgr._detect_stuck(aid, (5.0, 5.0), moving=False)
    idle = [mgr._detect_stuck(aid, (5.0, 5.0), moving=False)
            for _ in range(_STUCK_TICKS + 2)]
    check("a stationary idle avatar is never flagged stuck (not the same case)",
          not any(idle))

    # ── Recovery: a stuck avatar that breaks free is no longer stuck ───────────
    mgr = make_manager(tmp)
    mgr._detect_stuck(aid, (0.0, 0.0), moving=True)
    for _ in range(_STUCK_TICKS):
        mgr._detect_stuck(aid, (0.0, 0.0), moving=True)   # get it stuck
    freed = mgr._detect_stuck(aid, (step * 5, 0.0), moving=True)
    check("an avatar that breaks free and advances is no longer stuck", not freed)

    test_wedge_budget()
    test_wedge_text()
    print("All stuck-detection checks passed.")


def _stalled(intent="east", tried=None):
    return {"intent": intent, "moved_cm": 0.0, "stalled": True,
            "tried_here": tried if tried is not None else {intent: 0.0}}


def _directions(**cells):
    """``north=("road", 4)`` -> the shape ``_direction_places`` returns."""
    out = {}
    for direction, spec in cells.items():
        footing, samples = (spec if spec else (None, 0))
        out[direction] = {
            "cell": f"{direction[0]}c",
            "place": None,
            "ground": ([{"footing": footing, "sample_count": samples}] if footing else []),
            "refusals": [],
        }
    return out


def test_wedge_budget():
    """#65: the *run* of stalls is the fact, and the escapes are measured."""
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp)
    aid = "dufus"
    dirs = _directions(north=("road", 4), east=("cultivated_field", 9),
                       south=("pavement", 1), west=None)

    # Below the budget the run is counted but no speech is made — one stall is
    # ordinary and does not need an escape list.
    first = mgr._wedge_fact(aid, _stalled(), dirs)
    check("a single stall reports a run of 1", first["run"] == 1)
    check("below budget there are no escapes yet", "escapes" not in first)

    mgr._wedge_fact(aid, _stalled(), dirs)
    third = mgr._wedge_fact(aid, _stalled(), dirs)
    check("the run reaches the budget", third["run"] == _WEDGE_BUDGET_TICKS)
    ways = {e["direction"] for e in third["escapes"]}
    check("good ground is offered as an escape", "north" in ways and "south" in ways)
    check("the heading already tried from here is excluded", "east" not in ways)
    check("a cell nobody has walked is not offered", "west" not in ways)
    check("most-walked ground is offered first", third["escapes"][0]["direction"] == "north")

    # Refusals are the APC's own ruling and must not be recycled as an escape.
    refused = _directions(north=("road", 4))
    refused["north"]["refusals"] = [{"reason": "fenced"}]
    mgr._stall_run[aid] = _WEDGE_BUDGET_TICKS - 1
    check("a refused cell is never offered as a way out",
          mgr._wedge_fact(aid, _stalled(), refused)["escapes"] == [])

    # Real movement clears the run: these are facts about one spot.
    moved = {"intent": "north", "moved_cm": 900.0, "stalled": False}
    check("a move that lands clears the wedge", mgr._wedge_fact(aid, moved, dirs) is None)
    check("the counter really reset", mgr._wedge_fact(aid, _stalled(), dirs)["run"] == 1)
    check("no movement order at all is not a wedge",
          mgr._wedge_fact(aid, None, dirs) is None)


def test_wedge_text():
    check("below budget renders nothing", _wedge_text({"run": 1, "budget": 3}) == "")
    check("a non-wedge renders nothing", _wedge_text(None) == "")

    loud = _wedge_text({"run": 3, "budget": 3, "escapes": [
        {"direction": "north", "footing": "road", "samples": 4, "cell": "6,5"}]})
    check("the run length is stated", "3 orders in a row" in loud)
    check("the escape names cell, footing and how often it was walked",
          "north" in loud and "6,5" in loud and "road" in loud and "4x" in loud)

    empty = _wedge_text({"run": 3, "budget": 3, "escapes": []})
    check("having nothing proven is stated, not hidden", "No neighbouring cell" in empty)


if __name__ == "__main__":
    main()
