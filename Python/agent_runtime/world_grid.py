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

    An optional ``image_bounds`` key (same shape as ``bounds``) calibrates the
    web /map overlay: the world rect the top-down capture *actually* frames,
    for captures that don't frame ``bounds`` exactly (#6c). Pure passthrough —
    navigation never reads it.
    """

    def __init__(self, cell_size: float = 400.0, bounds: dict | None = None,
                 image_bounds: dict | None = None,
                 origin_x: float = 0.0, origin_y: float = 0.0):
        self.cell_size = float(cell_size)
        self.bounds = bounds or None
        self.image_bounds = image_bounds or None
        self.origin_x = float(origin_x)
        self.origin_y = float(origin_y)

    @classmethod
    def load(cls, path: Path) -> "WorldGrid":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(cell_size=data.get("cell_size", 400.0), bounds=data.get("bounds"),
                       image_bounds=data.get("image_bounds"),
                       origin_x=data.get("origin_x", 0.0),
                       origin_y=data.get("origin_y", 0.0))
        except Exception as e:
            logger.error(f"Bad world grid file {path}: {e} — using unbounded default")
            return cls()

    @property
    def has_bounds(self) -> bool:
        return bool(self.bounds)

    def _index(self, coord: float, origin: float = 0.0) -> int:
        return math.floor((coord - origin) / self.cell_size)

    def locate(self, x: float, y: float) -> dict:
        """Return the fixed grid cell containing world (x, y).

        Always includes ``key`` (matches SpatialMap cell keys) and ``cell_size``.
        With bounds also includes ``col``/``row`` (0-based from the min corner),
        the grid dimensions ``cols``/``rows``, and ``in_bounds``.
        """
        gx = self._index(x, self.origin_x)
        gy = self._index(y, self.origin_y)
        out: dict = {"key": f"{gx},{gy}", "cell_size": self.cell_size}
        if not self.bounds:
            return out

        min_gx = self._index(self.bounds["min_x"], self.origin_x)
        min_gy = self._index(self.bounds["min_y"], self.origin_y)
        max_gx = self._index(self.bounds["max_x"], self.origin_x)
        max_gy = self._index(self.bounds["max_y"], self.origin_y)
        out["col"] = gx - min_gx
        out["row"] = gy - min_gy
        out["cols"] = max_gx - min_gx + 1
        out["rows"] = max_gy - min_gy + 1
        out["in_bounds"] = min_gx <= gx <= max_gx and min_gy <= gy <= max_gy
        return out

    def origin(self) -> tuple[float, float] | None:
        """World (x, y) of cell (0, 0)'s min corner — the grid's NW anchor.

        Cells are origin-anchored (``floor(coord / cell_size)``), so the first
        cell generally starts *outside* ``bounds`` (e.g. min_x=-24600 with
        3000 cm cells → origin x=-27000). Overlays that draw the grid over a
        world image need this to place cell edges in world space. ``None``
        without bounds.
        """
        if not self.bounds:
            return None
        return (self.origin_x
                + self._index(self.bounds["min_x"], self.origin_x) * self.cell_size,
                self.origin_y
                + self._index(self.bounds["min_y"], self.origin_y) * self.cell_size)

    def cell_center(self, col: int, row: int) -> tuple[float, float] | None:
        """Return the world (x, y) center of the cell at (col, row).

        The inverse of :meth:`locate`: ``locate(*cell_center(c, r))`` round-trips
        back to ``(c, r)``. Requires bounds — without them col/row are undefined,
        so this returns ``None``.
        """
        if not self.bounds:
            return None
        min_gx = self._index(self.bounds["min_x"], self.origin_x)
        min_gy = self._index(self.bounds["min_y"], self.origin_y)
        cx = self.origin_x + (min_gx + col + 0.5) * self.cell_size
        cy = self.origin_y + (min_gy + row + 0.5) * self.cell_size
        return cx, cy

    def describe(self) -> str:
        if self.bounds:
            probe = self.locate(self.bounds["min_x"], self.bounds["min_y"])
            return (f"cell_size={self.cell_size:.0f}cm, {probe['cols']}x{probe['rows']} cells "
                    f"(bounded, logical_origin=({self.origin_x:.0f},{self.origin_y:.0f}))")
        return f"cell_size={self.cell_size:.0f}cm, unbounded (no world_grid.json)"
