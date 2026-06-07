from __future__ import annotations

import logging

from .spatial_memory import SpatialMap

logger = logging.getLogger("AgentRuntime")


def next_target(spatial_map: SpatialMap, x: float, y: float, z: float) -> dict | None:
    """Choose where an exploring agent should walk next — pure, deterministic.

    Frontier-based coverage: head for the nearest cell that borders explored
    space but is itself unexplored. No LLM is involved in this routing decision
    (the VLM only perceives); ``nearest_frontier`` breaks ties by grid
    coordinates, so the choice is stable and the agent doesn't oscillate.

    The caller is expected to ``ingest`` the agent's current position *before*
    calling this, so the occupied cell counts as explored. Returns::

        {"cell": "3,-2", "location": {"x": ..., "y": ..., "z": ...}}

    reusing the agent's current ``z`` (the map is 2-D). Returns ``None`` only
    when no frontier exists — i.e. nothing has been ingested yet, which the
    caller should treat as "seed the map first".
    """
    current = spatial_map.cell_key(x, y)
    frontier = spatial_map.nearest_frontier(current)
    if frontier is None:
        logger.debug("explorer: no frontier from %s (map empty?)", current)
        return None
    tx, ty = spatial_map.cell_center(frontier)
    return {"cell": frontier, "location": {"x": tx, "y": ty, "z": z}}
