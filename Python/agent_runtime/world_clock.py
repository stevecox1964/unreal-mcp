from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("AgentRuntime")


class WorldClock:
    """In-world time of day, anchored when the simulation starts.

    Configured per level in ``worlds/<level>/world.json``::

        {"clock": {"start": "08:00", "minutes_per_real_minute": 10.0}}

    Without the file the day starts at 08:00 at real-time speed. The clock is
    a *sense*: it is reported to agents in observations and at wake-up; what an
    agent does with the time of day comes from its authored markdown, never
    from code.
    """

    def __init__(self, start: str = "08:00", minutes_per_real_minute: float = 1.0):
        h, m = str(start).split(":")
        self.start_minutes = int(h) * 60 + int(m)
        self.scale = float(minutes_per_real_minute)
        self._anchor: float | None = None

    @classmethod
    def load(cls, path: Path) -> "WorldClock":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            clock = data.get("clock") or {}
            return cls(
                start=clock.get("start", "08:00"),
                minutes_per_real_minute=clock.get("minutes_per_real_minute", 1.0),
            )
        except Exception as e:
            logger.error(f"Bad world file {path}: {e} — using default clock")
            return cls()

    def start(self) -> None:
        """Anchor the clock to now; world time advances from here."""
        self._anchor = time.monotonic()

    def reset(self) -> None:
        """Un-anchor the clock so ``now_text()`` reads the configured morning start
        again — used when restarting the sim's day without immediately running it."""
        self._anchor = None

    def now_text(self) -> str:
        """Current world time, e.g. ``"Day 1, 08:23"``.

        Before ``start()`` is called this is simply the configured start time.
        """
        elapsed_real_min = ((time.monotonic() - self._anchor) / 60.0) if self._anchor else 0.0
        total = self.start_minutes + elapsed_real_min * self.scale
        day, minutes = divmod(int(total), 24 * 60)
        return f"Day {day + 1}, {minutes // 60:02d}:{minutes % 60:02d}"

    def describe(self) -> str:
        return (
            f"start {self.start_minutes // 60:02d}:{self.start_minutes % 60:02d}, "
            f"x{self.scale:g} speed"
        )
