from __future__ import annotations

import math

from .world_grid import WorldGrid

# A place survey samples the four absolute cardinal headings. In UE yaw,
# East=0, South=90, West=180, North=270.
_CARDINAL_HEADINGS = [0.0, 90.0, 180.0, 270.0]


def compass_headings() -> list[float]:
    """The absolute yaws for a full 360 place survey — four 90-degree turns.

    Example: ``[0, 90, 180, 270]`` (E, S, W, N in UE coordinates).
    """
    return list(_CARDINAL_HEADINGS)


class CellSweep:
    """Deterministic state machine for sweeping one grid cell.

    Sequences a single, personality-free routine: **walk to the cell center**,
    then **observe each compass heading** in turn, then **done**. Pure — it emits
    the next sub-action given the agent's current position; the live layer
    executes movement/rotation/capture and, on completion, drops the community
    breadcrumb (``PlaceDB.mark_swept``).

    Arrival is sticky: once within ``arrive_tolerance`` of the center, the sweep
    proceeds to observing and never reverts to travelling even if the avatar
    drifts (it's spinning in place, so position may jitter).
    """

    def __init__(self, center: tuple[float, float], z: float,
                 headings: list[float] = None, arrive_tolerance: float = 100.0):
        self.center = center
        self.z = z
        self._headings = list(headings if headings is not None else compass_headings())
        self._tolerance = arrive_tolerance
        self._arrived = False
        self._done = False

    @property
    def is_done(self) -> bool:
        return self._done

    def next_action(self, agent_xy: tuple[float, float]) -> dict:
        """Return the next sub-action: walk-to-center, observe-heading, or done."""
        if self._done:
            return {"type": "sweep_done"}

        if not self._arrived:
            dist = math.hypot(agent_xy[0] - self.center[0], agent_xy[1] - self.center[1])
            if dist > self._tolerance:
                return {"type": "walk_to",
                        "location": [self.center[0], self.center[1], self.z],
                        "_sweep": "goto_center"}
            self._arrived = True  # sticky

        if self._headings:
            yaw = self._headings.pop(0)
            return {"type": "observe_heading", "yaw": yaw, "_sweep": "observe"}

        self._done = True
        return {"type": "sweep_done"}


def default_sweep(world_grid: WorldGrid, col: int, row: int, z: float,
                  arrive_tolerance: float = None) -> CellSweep | None:
    """Build a :class:`CellSweep` targeting the center of cell ``(col, row)``.

    Returns None when the grid is unbounded (no cell center exists). The default
    arrival tolerance is a quarter of a cell, so "at the center" is forgiving.
    """
    center = world_grid.cell_center(col, row)
    if center is None:
        return None
    tol = arrive_tolerance if arrive_tolerance is not None else world_grid.cell_size / 4.0
    return CellSweep(center=center, z=z, arrive_tolerance=tol)
