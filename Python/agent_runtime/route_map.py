"""APC top-down route map (#6b / WP5) — "chart me a course" via lizard brain.

On a travel tick the APC gets a map of the corridor between where it is and
where its schedule says to be: the facts (what is known about each cell) plus
a rendered top-down image attached to its multimodal decision call. Facts,
never advice — the LLM charts the course; lizard brain describes the terrain.

Sign-off (user, 2026-07-01): rendered IMAGE (not the spec's ASCII rec);
corridor = bounding rect of (here, destination) padded 1, capped 15x15;
separate renderer over the shared PlaceDB (the web /map is untouched);
injected on travel ticks only.

Pure module: reads PlaceDB + WorldGrid, no bridge, no LLM, offline-testable.
"""
from __future__ import annotations

import logging
import math
from pathlib import Path

from .place_db import yaw_to_compass

logger = logging.getLogger("AgentRuntime")

PAD = 1            # corridor padding, cells per side (sign-off Q2)
MAX_SPAN = 15      # corridor cap per axis, cells (sign-off Q2)

# Render constants. Colors are the map's whole vocabulary — keep them in sync
# with the legend drawn on the image and the prompt note in llm_router.
_CELL_PX = 48
_LEGEND_H = 20
_MARGIN_L = 20     # left gutter: absolute row numbers (grid cell layout)
_MARGIN_T = 14     # top gutter: absolute column numbers
_COLORS = {
    "unexplored": (212, 212, 212),   # gray
    "swept":      (232, 216, 168),   # tan
    "named":      (168, 216, 168),   # green
    "grid":       (136, 136, 136),
    "from":       (32, 96, 208),     # A = you (blue)
    "to":         (208, 48, 48),     # B = destination (red)
    "text":       (0, 0, 0),
    "marker_text": (255, 255, 255),
    "legend_bg":  (255, 255, 255),
}


def _axis_window(f: int, t: int, size: int, pad: int, max_span: int) -> tuple[range, bool]:
    """Padded [min,max] window on one axis, clamped to [0, size), capped at
    ``max_span`` cells. When capped, the window anchors at the *from* end and
    extends toward the destination — the agent needs the terrain ahead of it,
    not the far end it cannot see yet."""
    lo = max(0, min(f, t) - pad)
    hi = min(size - 1, max(f, t) + pad)
    truncated = False
    if hi - lo + 1 > max_span:
        truncated = True
        if f <= t:
            lo = max(0, f - pad)
            hi = min(size - 1, lo + max_span - 1)
        else:
            hi = min(size - 1, f + pad)
            lo = max(0, hi - max_span + 1)
    return range(lo, hi + 1), truncated


def corridor(from_cell: tuple[int, int], to_cell: tuple[int, int],
             cols: int, rows: int, pad: int = PAD,
             max_span: int = MAX_SPAN) -> tuple[range, range, bool]:
    """The padded bounding (col_range, row_range) between the two cells,
    clamped to the grid, plus a ``truncated`` flag when the cap bit."""
    col_range, trunc_c = _axis_window(from_cell[0], to_cell[0], cols, pad, max_span)
    row_range, trunc_r = _axis_window(from_cell[1], to_cell[1], rows, pad, max_span)
    return col_range, row_range, trunc_c or trunc_r


def build_route_map(place_db, world_grid,
                    from_cell: tuple[int, int], to_cell: tuple[int, int],
                    destination_name: str = None,
                    path: list[tuple[int, int]] = None) -> dict | None:
    """Facts an APC can chart a course from — or None on an unbounded grid.

    ::

        {"from": {"cell": [c,r], "name": <community name|None>},
         "to":   {"cell": [c,r], "name": ..., "bearing": "NE", "distance_m": 34},
         "cells": [ {"cell": [c,r], "state": "named|swept|unexplored",
                     "name": ..., "landmarks": <count>}, ... ],   # corridor only
         "cols": [lo, hi], "rows": [lo, hi],
         "truncated": False}

    ``path`` (#17/WP8): the planned leg cells when a grid-first route exists —
    carried as ``"path": [[c, r], ...]`` and drawn as dots on the image.
    """
    if not world_grid.has_bounds:
        return None
    probe = world_grid.locate(world_grid.bounds["min_x"], world_grid.bounds["min_y"])
    cols, rows = probe["cols"], probe["rows"]

    col_range, row_range, truncated = corridor(from_cell, to_cell, cols, rows)

    known = {(c["col"], c["row"]): c for c in place_db.map_cells()}
    cells = []
    for row in row_range:
        for col in col_range:
            k = known.get((col, row))
            cells.append({
                "cell": [col, row],
                "state": k["state"] if k else "unexplored",
                "name": k["name"] if k else None,
                "landmarks": k["landmarks"] if k else 0,
            })

    from_center = world_grid.cell_center(*from_cell)
    to_center = world_grid.cell_center(*to_cell)
    if from_cell == to_cell or from_center is None or to_center is None:
        bearing, distance_m = None, 0.0
    else:
        dx, dy = to_center[0] - from_center[0], to_center[1] - from_center[1]
        bearing = yaw_to_compass(math.degrees(math.atan2(dy, dx)))
        distance_m = round(math.hypot(dx, dy) / 100.0)

    def _name_of(cell):
        k = known.get(cell)
        return k["name"] if k else None

    out = {
        "from": {"cell": list(from_cell), "name": _name_of(from_cell)},
        "to": {"cell": list(to_cell),
               "name": _name_of(to_cell) or destination_name,
               "bearing": bearing, "distance_m": distance_m},
        "cells": cells,
        "cols": [col_range.start, col_range[-1]],
        "rows": [row_range.start, row_range[-1]],
        "truncated": truncated,
    }
    if path:
        out["path"] = [list(c) for c in path]
    return out


def render_map_image(route: dict, out_path: Path, cell_px: int = _CELL_PX) -> Path | None:
    """Draw the route facts as a top-down PNG: north up (row 0 is the -Y /
    north edge, drawn at the top), east right. A = you, B = destination;
    cell fill encodes known state. Returns the written path, or None on any
    render failure — a map hiccup must never break a tick."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        col_lo, col_hi = route["cols"]
        row_lo, row_hi = route["rows"]
        ncols, nrows = col_hi - col_lo + 1, row_hi - row_lo + 1
        w = _MARGIN_L + ncols * cell_px
        h = _MARGIN_T + nrows * cell_px + _LEGEND_H
        img = Image.new("RGB", (w, h), _COLORS["legend_bg"])
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        for c in route["cells"]:
            col, row = c["cell"]
            x0 = _MARGIN_L + (col - col_lo) * cell_px
            y0 = _MARGIN_T + (row - row_lo) * cell_px
            draw.rectangle([x0, y0, x0 + cell_px, y0 + cell_px],
                           fill=_COLORS[c["state"]], outline=_COLORS["grid"])
            if c["name"]:
                # Truncate to the cell width; the prompt note carries full names.
                label = c["name"][: max(3, cell_px // 7)]
                draw.text((x0 + 3, y0 + 3), label, fill=_COLORS["text"], font=font)

        # Grid cell layout: absolute column numbers across the top gutter, row
        # numbers down the left — the same (col,row) vocabulary as the facts
        # dict and the web /map tooltips.
        for i in range(ncols):
            s = str(col_lo + i)
            draw.text((_MARGIN_L + i * cell_px + cell_px // 2 - 3 * len(s), 2),
                      s, fill=_COLORS["text"], font=font)
        for j in range(nrows):
            s = str(row_lo + j)
            draw.text((2, _MARGIN_T + j * cell_px + cell_px // 2 - 5),
                      s, fill=_COLORS["text"], font=font)

        def _marker(cell, letter, color, dx=0):
            col, row = cell
            cx = _MARGIN_L + (col - col_lo) * cell_px + cell_px // 2 + dx
            cy = _MARGIN_T + (row - row_lo) * cell_px + cell_px // 2
            r = cell_px // 4
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
            draw.text((cx - 3, cy - 6), letter, fill=_COLORS["marker_text"], font=font)

        # Planned route legs (#17/WP8): a dot per intermediate path cell —
        # the corridor shows the plan, not just the endpoints.
        endpoints = (route["from"]["cell"], route["to"]["cell"])
        for pc in route.get("path") or []:
            if list(pc) in [list(e) for e in endpoints]:
                continue
            col, row = pc
            if not (col_lo <= col <= col_hi and row_lo <= row <= row_hi):
                continue
            cx = _MARGIN_L + (col - col_lo) * cell_px + cell_px // 2
            cy = _MARGIN_T + (row - row_lo) * cell_px + cell_px // 2
            r = cell_px // 8
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_COLORS["from"])

        same_cell = route["from"]["cell"] == route["to"]["cell"]
        _marker(route["from"]["cell"], "A", _COLORS["from"], dx=-cell_px // 5 if same_cell else 0)
        _marker(route["to"]["cell"], "B", _COLORS["to"], dx=cell_px // 5 if same_cell else 0)

        legend = "A=you  B=destination  green=named  tan=observed  gray=unknown  N=up  edges=col,row"
        if route.get("path"):
            legend += "  dots=route"
        if route.get("truncated"):
            legend += "  (map truncated)"
        draw.text((4, h - _LEGEND_H + 4), legend, fill=_COLORS["text"], font=font)

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG")
        return out_path
    except Exception as e:
        logger.warning("route map render failed: %s", e)
        return None
