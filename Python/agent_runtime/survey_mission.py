"""Survey Mission Mode (#96) — which cell to survey next is a code job.

After 54 runs the survey covered 20 of 150 cells, and the backlog from SR32 to
SR54 is a record of what per-tick LLM judgment costs on what is really a
control problem: wedges, bounces, re-refusals, two-node loops. Explore mode
proved the other shape years-of-runs ago — deterministic frontier walking with
the model doing labeling only — and this module brings that shape to the live
survey, per ``plan/survey_mission_plan.md``.

The re-division of authority: **code decides coverage** (this module — which
cell, in what order), **the LLM decides meaning** (one checkpoint decision per
finished cell: name the place, refuse bad ground), **the VLM labels frames**.
Personality APCs are untouched; the facts-not-blockers doctrine still governs
them. A mission is a different authority regime, and only an APC whose
``state.json`` opts in with ``"mission": "survey"`` lives under it.

Pure functions, like ``cell_sweep`` and ``route_planner``: no bridge, no LLM,
no I/O. The caller (AgentManager) supplies what is done and what is
unreachable; this module answers only "where next?".

Ring order is the whole policy: cells are visited center-out (Chebyshev rings
around an origin cell — the town), each ring swept in bearing order clockwise
from north. Skipping swept/refused/unreachable cells makes the ring order
automatically *look past* covered ground: as the survey fills in, the first
un-done cell in ring order IS the frontier, however far from the body it lies.
Getting there is the existing locomotion stack's job, not this module's.
"""
from __future__ import annotations

import math


def ring_cells(cols: int, rows: int,
               origin: tuple[int, int]) -> list[tuple[int, int]]:
    """Every in-grid cell, ordered center-out from ``origin``.

    Ring = Chebyshev distance (rings are squares, matching the square grid);
    within a ring, bearing clockwise from grid north (north = decreasing row),
    ties broken by (col, row) so the order is total and deterministic — the
    same world always surveys in the same order, which is what makes a run's
    coverage comparable to the last run's.
    """
    ox, oy = origin

    def key(cell: tuple[int, int]):
        c, r = cell
        ring = max(abs(c - ox), abs(r - oy))
        bearing = math.atan2(c - ox, -(r - oy))  # 0 = north, clockwise +
        if bearing < 0:
            bearing += 2 * math.pi
        return (ring, bearing, c, r)

    return sorted(((c, r) for c in range(cols) for r in range(rows)), key=key)


def next_target(cols: int, rows: int, origin: tuple[int, int],
                done: set[tuple[int, int]],
                unreachable=None) -> tuple[int, int] | None:
    """The first cell in ring order still worth surveying, or None = complete.

    ``done`` is membership (swept or refused — both are answered ground);
    ``unreachable`` is a predicate, because "can the body get in" lives in the
    caller's spatial map and may be expensive — it is only asked about cells
    that survived the cheap set check. None means every cell is answered:
    the mission is complete, and the caller says so loudly (rule 12), never
    by going quiet.
    """
    for cell in ring_cells(cols, rows, origin):
        if cell in done:
            continue
        if unreachable is not None and unreachable(cell):
            continue
        return cell
    return None
