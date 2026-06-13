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
    AgentManager, _STUCK_TICKS, _STUCK_PROGRESS_CM,
)


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

    print("All stuck-detection checks passed.")


if __name__ == "__main__":
    main()
