"""Offline tests for WorldClock — the in-world time-of-day sense (A3 support).

Covers the morning-start reading and reset() (used by 'restart the sim from
morning'). No Unreal, no sleeping on real time. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_world_clock.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.world_clock import WorldClock   # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_morning_start_and_reset():
    clock = WorldClock(start="08:00", minutes_per_real_minute=10.0)
    check("before start, reads the configured morning", clock.now_text() == "Day 1, 08:00")

    clock.start()
    # Anchored 'now' is still essentially the start minute (no real time elapsed).
    check("just-started clock still reads morning", clock.now_text() == "Day 1, 08:00")

    clock.reset()
    check("after reset, un-anchored back to morning", clock.now_text() == "Day 1, 08:00")


def test_custom_start_time():
    check("a 06:30 world starts at 06:30", WorldClock(start="06:30").now_text() == "Day 1, 06:30")


def main():
    test_morning_start_and_reset()
    test_custom_start_time()
    print("\nAll world-clock checks passed.")


if __name__ == "__main__":
    main()
