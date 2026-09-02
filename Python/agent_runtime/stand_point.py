"""Pure scorer for the survey stand point (#103) — no engine, no LLM.

``_sweep_step`` used to walk every survey to the literal center of the grid
cell and shoot its four compass frames from wherever that landed — inside a
wall, hard against the back of a house, wherever the geometric center
happened to fall. This module answers a narrower, engine-free question given
facts already measured by the body: of a handful of candidate spots inside
the cell, which one gives the survey the most breathing room, and is
"staying put" (the body's current position) good enough to skip the walk.

Every function here is pure data-in/data-out — the caller (``agent_manager``)
is the one that calls ``unreal_bridge.radar(location=...)`` for each
candidate and hands the resulting probe dict to :func:`score`.
"""
from __future__ import annotations

import math

# A spot 10 m clear on a heading is "open" — the count of open headings is a
# tie-breaker behind minimum clearance, so this only matters when two
# candidates have the same tightest squeeze.
_OPEN_HEADING_CM = 1000.0

# A partial path that still lands within 1.5 m of the candidate is close
# enough to call "got there"; the survey does not need the literal point,
# it needs to stand roughly there and shoot four frames.
_PARTIAL_GAP_VETO_CM = 150.0

# The stay rule (#103): an explorer standing in an already-acceptable spot
# does not double back for a marginal gain. 0.8 is a judgment call — no
# number was specified beyond "a marginal gain" — chosen so "here" only loses
# to a candidate that is meaningfully more open, not fractionally so.
_STAY_RATIO = 0.8

# Sentinel: the probe came from a plugin build that never measured walkable
# ground at all (rule 12 — "not measured" must never read as "not walkable").
UNMEASURED = "unmeasured"


def candidates(center_xy: tuple[float, float], cell_size: float,
               here_xy: tuple[float, float] | None = None
               ) -> list[tuple[float, float, str]]:
    """Candidate stand points inside one grid cell: the centre, then two rings.

    Ring 1 sits at ``cell_size/6`` (about a third of the half-width, ~10 m for
    a 30 m cell); ring 2 at ``cell_size/3`` (about two thirds). Both rings
    have 8 points, 45 degrees apart, so every candidate — including the
    diagonals — stays inside the cell (the largest ring radius is still less
    than the half-width). Labels: ``"center"``, ``"ring1_<deg>"``,
    ``"ring2_<deg>"`` where ``<deg>`` is 0/45/.../315 in the same yaw
    convention as the rest of the sim (0=East, 90=South, ...).

    ``here_xy`` — the body's current position, when it is already standing
    inside the target cell — is prepended with label ``"here"`` so the
    caller can apply the stay rule. Total candidates: 17 (centre + 8 + 8),
    plus 1 more when ``here_xy`` is given.
    """
    cx, cy = center_xy
    out: list[tuple[float, float, str]] = []
    if here_xy is not None:
        out.append((here_xy[0], here_xy[1], "here"))
    out.append((cx, cy, "center"))
    for radius, ring_name in ((cell_size / 6.0, "ring1"), (cell_size / 3.0, "ring2")):
        for deg in range(0, 360, 45):
            rad = math.radians(deg)
            out.append((cx + radius * math.cos(rad), cy + radius * math.sin(rad),
                       f"{ring_name}_{deg}"))
    return out


def score(probe: dict) -> tuple | str | None:
    """Score one candidate's ``radar(location=...)`` result, or veto it.

    Vetoes (returns ``None``, a hard "cannot stand here"):
      - ``ground_under_feet`` is false (no walkable ground under the point).
      - ``path`` is ``"none"`` (nothing can walk there).
      - ``path`` is ``"partial"`` with ``path_end_gap_cm`` over 150 cm (the
        reachable point lands too far short to call this "getting there").

    Otherwise returns ``(min_clearance_cm, open_headings, -dist_to_center_cm)``
    — a tuple that sorts largest-is-best: the tightest squeeze on the ring
    (bigger is more open), then how many headings clear 10 m, then closeness
    to the true cell centre (ties favour the tidier survey point). The caller
    must have already added ``dist_to_center_cm`` to ``probe`` — this module
    never sees the cell centre, only what the body measured from the point.

    A probe with no ``ground_under_feet`` key at all — an old plugin build
    that never measured walkable ground — returns the sentinel
    :data:`UNMEASURED` instead of scoring anything (rule 12: "not measured"
    is never "not walkable").
    """
    if "ground_under_feet" not in probe:
        return UNMEASURED
    if not probe["ground_under_feet"]:
        return None
    # A missing 'path' alongside a present 'ground_under_feet' should not
    # happen (the engine sets both together for a location probe) — treated
    # as "none" defensively rather than silently scoring an unmeasured path.
    path = probe.get("path", "none")
    if path == "none":
        return None
    if path == "partial" and float(probe.get("path_end_gap_cm", 0.0)) > _PARTIAL_GAP_VETO_CM:
        return None
    ring = probe.get("ring") or []
    if not ring:
        return None
    clearances = [float(sector.get("clearance_cm", 0.0)) for sector in ring]
    min_clearance_cm = min(clearances)
    open_headings = sum(1 for c in clearances if c >= _OPEN_HEADING_CM)
    dist_to_center_cm = float(probe.get("dist_to_center_cm", 0.0))
    return (min_clearance_cm, open_headings, -dist_to_center_cm)


def choose(scored: list[tuple[str, tuple[float, float], tuple | None]]
           ) -> tuple[str, tuple[float, float], tuple] | None:
    """Pick the best-scoring candidate, applying the stay rule for ``"here"``.

    ``scored`` is ``[(label, xy, score), ...]`` as produced by :func:`score`
    for each candidate (entries scored :data:`UNMEASURED` are the caller's
    concern — stop probing and fall back before this is ever called). Vetoed
    entries (score ``None``) are ignored here. Returns ``None`` when nothing
    passed.

    **Stay rule:** if a ``"here"`` candidate passed and its minimum clearance
    is at least 0.8x the best candidate's, ``"here"`` wins even when another
    spot scores higher — an explorer standing in an acceptable spot does not
    double back for a marginal gain.
    """
    passing = [t for t in scored if t[2] is not None]
    if not passing:
        return None
    best = max(passing, key=lambda t: t[2])
    here = next((t for t in passing if t[0] == "here"), None)
    if here is not None and here[2][0] >= _STAY_RATIO * best[2][0]:
        return here
    return best
