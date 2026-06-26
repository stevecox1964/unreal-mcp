from __future__ import annotations

import json
import logging
import math
from pathlib import Path

logger = logging.getLogger("AgentRuntime")


class WorldGrid:
    """Fixed world-space grid shared by every agent in a level.

    Tiles world (x, y) into square cells exactly like SpatialMap — origin-anchored
    ``floor(coord / cell_size)`` — so world-grid keys and per-agent spatial-map
    cells always line up. A per-world ``worlds/<level>/world_grid.json`` may pin
    the world bounds, which gives every cell a stable (col, row) index out of a
    fixed (cols x rows) total:

        {
          "cell_size": 400.0,
          "bounds": {"min_x": -12000, "min_y": -8000, "max_x": 4000, "max_y": 8000}
        }

    Without the file (or bounds) the grid is unbounded: cell keys are still
    deterministic and reported, col/row indices are omitted.
    """

    def __init__(self, cell_size: float = 400.0, bounds: dict | None = None):
        self.cell_size = float(cell_size)
        self.bounds = bounds or None

    @classmethod
    def load(cls, path: Path) -> "WorldGrid":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(cell_size=data.get("cell_size", 400.0), bounds=data.get("bounds"))
        except Exception as e:
            logger.error(f"Bad world grid file {path}: {e} — using unbounded default")
            return cls()

    @property
    def has_bounds(self) -> bool:
        return bool(self.bounds)

    def _index(self, coord: float) -> int:
        return math.floor(coord / self.cell_size)

    def locate(self, x: float, y: float) -> dict:
        """Return the fixed grid cell containing world (x, y).

        Always includes ``key`` (matches SpatialMap cell keys) and ``cell_size``.
        With bounds also includes ``col``/``row`` (0-based from the min corner),
        the grid dimensions ``cols``/``rows``, and ``in_bounds``.
        """
        gx, gy = self._index(x), self._index(y)
        out: dict = {"key": f"{gx},{gy}", "cell_size": self.cell_size}
        if not self.bounds:
            return out

        min_gx = self._index(self.bounds["min_x"])
        min_gy = self._index(self.bounds["min_y"])
        max_gx = self._index(self.bounds["max_x"])
        max_gy = self._index(self.bounds["max_y"])
        out["col"] = gx - min_gx
        out["row"] = gy - min_gy
        out["cols"] = max_gx - min_gx + 1
        out["rows"] = max_gy - min_gy + 1
        out["in_bounds"] = min_gx <= gx <= max_gx and min_gy <= gy <= max_gy
        return out

    def cell_center(self, col: int, row: int) -> tuple[float, float] | None:
        """Return the world (x, y) center of the cell at (col, row).

        The inverse of :meth:`locate`: ``locate(*cell_center(c, r))`` round-trips
        back to ``(c, r)``. Requires bounds — without them col/row are undefined,
        so this returns ``None``.
        """
        if not self.bounds:
            return None
        min_gx = self._index(self.bounds["min_x"])
        min_gy = self._index(self.bounds["min_y"])
        cx = (min_gx + col + 0.5) * self.cell_size
        cy = (min_gy + row + 0.5) * self.cell_size
        return cx, cy

    def describe(self) -> str:
        if self.bounds:
            probe = self.locate(self.bounds["min_x"], self.bounds["min_y"])
            return f"cell_size={self.cell_size:.0f}cm, {probe['cols']}x{probe['rows']} cells (bounded)"
        return f"cell_size={self.cell_size:.0f}cm, unbounded (no world_grid.json)"
