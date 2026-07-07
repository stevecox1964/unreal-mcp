"""Grid-first routing (#17/WP8) — multi-leg travel between grid cells.

A destination several districts away becomes a plan: a straight line of
grid-cell legs, each leg a short navmesh walk the engine can actually do,
ending with a fine-approach that stops at the owned box's edge (B7b-style).
This is the mid-scale between name→position resolution and the engine's local
navmesh walking; without it agents travel greedily by vision and orbit when
the destination isn't in frame (Maren, SR2).

Pure module: no bridge, no LLM, no I/O. The AgentManager caches one route per
agent and calls ``next_waypoint`` on every routed walk; v1 paths are straight
lines by design — obstacle/no-go weighting from sweep data plugs into
``line_cells`` later (#19c).
"""
from __future__ import annotations

import math


def line_cells(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    """Grid cells from ``a`` to ``b`` inclusive — classic integer Bresenham.

    Deterministic; diagonal steps are allowed (cells are 30 m districts, the
    navmesh handles the local walk between neighboring centers).
    Examples: ``(0,0)→(3,0)`` = 4 cells along the row; ``(0,0)→(3,3)`` = the
    4-cell diagonal; ``a == b`` = ``[a]``.
    """
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    cells = [(x0, y0)]
    while (x0, y0) != (x1, y1):
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
        cells.append((x0, y0))
    return cells


def make_route(from_cell: tuple[int, int], to_cell: tuple[int, int],
               target_xy: tuple[float, float], extent_cm: float,
               destination_name: str) -> dict:
    """Build the cached route state for one destination.

    ``target_xy`` is the final anchor (owned place) or cell center
    (community); ``extent_cm`` 0.0 means a community destination — no box, so
    being in the cell is arrival. ``leg`` indexes the CURRENT waypoint in
    ``path`` (path[0] is where the agent stood; a same-cell route is
    immediately final).
    """
    return {
        "destination": destination_name,
        "target_xy": (float(target_xy[0]), float(target_xy[1])),
        "extent_cm": float(extent_cm),
        "path": line_cells(from_cell, to_cell),
        "leg": 1,
    }


def next_waypoint(route: dict, current_cell: tuple[int, int],
                  current_xy: tuple[float, float], grid) -> dict | None:
    """Advance the leg state machine and return where to walk this tick.

    Skip-ahead: entering any path cell at/after the current leg consumes the
    legs behind it (the engine may cross several cells between ticks). An
    agent off the path keeps its leg — the waypoint pulls it back; the stuck
    detector is the escape hatch (the manager replans on stuck).

    Returns ``{"x", "y", "final", "leg", "total", "cell"}`` or **None**,
    which always means "stop walking — you are there": in the destination
    cell of a community place, or inside an owned destination's extent box.
    The final owned-box approach stops at the box edge (B7b standoff), never
    at the anchor itself.
    """
    path = route["path"]
    for i in range(len(path) - 1, route["leg"] - 2, -1):
        if path[i] == tuple(current_cell):
            route["leg"] = i + 1
            break
    total = max(len(path) - 1, 1)

    if route["leg"] < len(path):
        cell = path[route["leg"]]
        center = grid.cell_center(*cell)
        if center is None:
            return None
        return {"x": center[0], "y": center[1], "final": False,
                "leg": route["leg"], "total": total, "cell": cell}

    # Standing in the destination cell.
    half = route["extent_cm"] / 2.0
    if half <= 0:
        return None   # community destination: being in the cell IS arrival
    tx, ty = route["target_xy"]
    d = math.hypot(tx - current_xy[0], ty - current_xy[1])
    if d <= half:
        return None   # inside the box — arrived
    f = (d - half) / d
    return {"x": current_xy[0] + (tx - current_xy[0]) * f,
            "y": current_xy[1] + (ty - current_xy[1]) * f,
            "final": True, "leg": total, "total": total, "cell": path[-1]}
