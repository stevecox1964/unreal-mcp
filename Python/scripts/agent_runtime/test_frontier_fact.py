"""Offline tests for the wider-map sense (AgentManager._frontier_fact, #73).

SR41 surveyed 15 cells of a 17x12 grid and laid them out 7 wide and 2 tall. No
component was broken: every navigation fact an APC had was one cell wide, so
"where should the survey go next" was answered by whichever way the body already
pointed, and a random walk with no sense of extent draws a line.

These tests pin the three things the fact must state — how big the grid is, what
shape the mapped block has, and where its nearest edges are — and the two ways
the shape can be lost: refused cells re-offered as frontier, and a truncated list
that all points one way. Fully offline (no LLM, no Unreal, temp DB). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_frontier_fact.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.agent_manager import (  # noqa: E402
    AgentManager, _FRONTIER_LIMIT, _compass_word,
)
from agent_runtime.place_db import PlaceDB  # noqa: E402
from agent_runtime.world_grid import WorldGrid  # noqa: E402
from agent_runtime.llm_router import _frontier_note  # noqa: E402


class _Stub:
    """Stands in for any collaborator the fact never calls."""
    def __getattr__(self, _):
        return lambda *a, **k: None


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def make_manager(tmp, cells, bounds=True):
    """A manager whose PlaceDB holds exactly ``cells`` as swept ground."""
    mgr = AgentManager(worlds_dir=Path(tmp), llm_router=_Stub(),
                       unreal_bridge=_Stub(), memory_store=_Stub())
    db_path = Path(tmp) / f"frontier_{abs(hash(tuple(sorted(cells))))}.db"
    mgr.place_db = PlaceDB(db_path)
    for col, row in cells:
        mgr.place_db.mark_swept("dufus", col, row, "Day 1, 08:00")
    # 17x12 to match MCP_World, so the numbers in these tests are the numbers
    # the live run will produce.
    mgr.world_grid = WorldGrid(
        cell_size=3000.0,
        bounds={"min_x": 0.0, "min_y": 0.0, "max_x": 16 * 3000.0, "max_y": 11 * 3000.0},
    ) if bounds else WorldGrid(cell_size=3000.0)
    return mgr


def grid_at(mgr, col, row):
    """The locate() dict for a cell, the way an observation carries it."""
    center = mgr.world_grid.cell_center(col, row)
    if center is None:                     # unbounded grid — no col/row at all
        return mgr.world_grid.locate(0.0, 0.0)
    return mgr.world_grid.locate(*center)


def test_compass_word():
    check("+row is south", _compass_word(0, 1) == "south")
    check("-row is north", _compass_word(0, -1) == "north")
    check("+col is east", _compass_word(1, 0) == "east")
    check("-col is west", _compass_word(-1, 0) == "west")
    check("diagonals read vertical-first", _compass_word(1, -1) == "northeast")
    check("the cell underfoot has no bearing", _compass_word(0, 0) == "here")


def test_grid_extent_is_stated():
    """The fact SR41 was missing: the world has twelve rows in it."""
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, [(5, 5), (6, 5)])
    fact = mgr._frontier_fact(grid_at(mgr, 5, 5))
    check("the grid's width is stated", fact["cols"] == 17)
    check("the grid's depth is stated", fact["rows"] == 12)
    check("the total is stated", fact["total"] == 204)
    check("how much is mapped is stated", fact["mapped"] == 2)


def test_shape_of_the_mapped_block():
    """A strip must report as a strip — this is the sentence that was absent."""
    tmp = tempfile.mkdtemp()
    ribbon = [(c, r) for c in range(3, 10) for r in (5, 6)]   # SR41's shape
    mgr = make_manager(tmp, ribbon)
    extent = mgr._frontier_fact(grid_at(mgr, 6, 5))["extent"]
    check("the mapped block's width is measured", extent["width"] == 7)
    check("the mapped block's height is measured", extent["height"] == 2)
    check("the block's column span is stated",
          (extent["min_col"], extent["max_col"]) == (3, 9))
    check("the block's row span is stated",
          (extent["min_row"], extent["max_row"]) == (5, 6))

    note = _frontier_note(mgr._frontier_fact(grid_at(mgr, 6, 5)))
    check("the rendered note says the block is 7 wide and 2 tall",
          "7 cells wide and 2 tall" in note)


def test_frontier_touches_mapped_ground():
    """Frontier means the edge of the blob, not every unmapped cell in the grid."""
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, [(5, 5)])
    fact = mgr._frontier_fact(grid_at(mgr, 5, 5))
    # The eight neighbours of a single mapped cell, and nothing further out.
    check("only cells adjacent to mapped ground are frontier",
          fact["frontier_total"] == 8)
    check("the far corner of the grid is not offered",
          all(f["cell"] != "16,11" for f in fact["cells"]))


def test_refused_cells_are_not_frontier():
    """A cell somebody ruled out must not come back as unexplored ground (#59)."""
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, [(5, 5)])
    before = mgr._frontier_fact(grid_at(mgr, 5, 5))["frontier_total"]
    mgr.place_db.refuse_cell("dufus", 5, 4, "standing corn", "Day 1, 08:00")
    after = mgr._frontier_fact(grid_at(mgr, 5, 5))
    check("refusing a cell removes it from the frontier",
          after["frontier_total"] == before - 1)
    check("the refused cell is never named as somewhere to go",
          all(f["cell"] != "5,4" for f in after["cells"]))


def test_the_list_keeps_its_shape_when_truncated():
    """The bug the fact exists to fix must not be reproduced by the fact itself.

    A ribbon has far more frontier cells along its long sides than off its ends.
    Sorting by distance alone fills a short list from one side, which is the same
    "everything points that way" input that drew the line in the first place.
    """
    tmp = tempfile.mkdtemp()
    ribbon = [(c, r) for c in range(3, 10) for r in (5, 6)]
    mgr = make_manager(tmp, ribbon)
    cells = mgr._frontier_fact(grid_at(mgr, 6, 5))["cells"]
    check("the list is capped", len(cells) <= _FRONTIER_LIMIT)
    check("no two entries share a bearing",
          len({f["direction"] for f in cells}) == len(cells))
    check("nearest-first ordering survives the per-bearing pick",
          [f["steps"] for f in cells] == sorted(f["steps"] for f in cells))
    check("both long sides of the ribbon are represented",
          {"north", "south"} <= {f["direction"] for f in cells})

    note = _frontier_note(mgr._frontier_fact(grid_at(mgr, 6, 5)))
    check("the note admits how many frontier cells there really are",
          "cells in all" in note)


def test_cell_underfoot_is_not_a_destination():
    """Where you already stand has its own authoritative survey verdict."""
    tmp = tempfile.mkdtemp()
    mgr = make_manager(tmp, [(5, 5)])
    fact = mgr._frontier_fact(grid_at(mgr, 6, 5))   # standing on a frontier cell
    check("the cell underfoot is not listed as somewhere to go",
          all(f["cell"] != "6,5" for f in fact["cells"]))
    check("no entry is zero steps away", all(f["steps"] > 0 for f in fact["cells"]))


def test_silent_when_there_is_nothing_to_say():
    """No blob, no bounds, no DB — three ways there is no honest fact."""
    tmp = tempfile.mkdtemp()
    empty = make_manager(tmp, [])
    check("nothing mapped yet means no frontier fact",
          empty._frontier_fact(grid_at(empty, 5, 5)) is None)

    unbounded = make_manager(tmp, [(5, 5)], bounds=False)
    check("an unbounded grid has no col/row and so no fact",
          unbounded._frontier_fact(grid_at(unbounded, 5, 5)) is None)

    no_db = make_manager(tmp, [(5, 5)])
    no_db.place_db = None
    check("no place DB means no fact", no_db._frontier_fact(grid_at(no_db, 5, 5)) is None)

    check("the note says so plainly rather than inventing a map",
          "not known" in _frontier_note(None))


def test_a_fully_mapped_block_says_so():
    """"No frontier" is a real state and must not read like "none found"."""
    tmp = tempfile.mkdtemp()
    everything = [(c, r) for c in range(17) for r in range(12)]
    mgr = make_manager(tmp, everything)
    fact = mgr._frontier_fact(grid_at(mgr, 5, 5))
    check("a fully mapped grid has no frontier", fact["cells"] == [])
    check("the note states it outright",
          "No unmapped cell touches" in _frontier_note(fact))


def main():
    test_compass_word()
    test_grid_extent_is_stated()
    test_shape_of_the_mapped_block()
    test_frontier_touches_mapped_ground()
    test_refused_cells_are_not_frontier()
    test_the_list_keeps_its_shape_when_truncated()
    test_cell_underfoot_is_not_a_destination()
    test_silent_when_there_is_nothing_to_say()
    test_a_fully_mapped_block_says_so()
    print("\nAll frontier-fact checks passed.")


if __name__ == "__main__":
    main()
