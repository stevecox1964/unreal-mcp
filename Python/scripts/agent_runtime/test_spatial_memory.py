"""Unit tests for agent_runtime.spatial_memory.SpatialMap.

Pure logic — no Unreal, no network. Run directly:

    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_spatial_memory.py

Exits non-zero on the first failed assertion.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make the agent_runtime package importable (Python/ is parents[2] of this file).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_runtime.spatial_memory import SpatialMap  # noqa: E402

_passed = 0


def check(label: str, cond: bool) -> None:
    global _passed
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    _passed += 1
    print(f"ok: {label}")


def test_grid_math() -> None:
    m = SpatialMap(cell_size=400.0)
    # floor-based binning, including negative coordinates
    check("origin cell", m.cell_key(10, 10) == "0,0")
    check("cell boundary is exclusive at top", m.cell_key(400, 0) == "1,0")
    check("negative x floors toward -inf", m.cell_key(-10, -10) == "-1,-1")
    # center round-trips back into the same cell
    cx, cy = m.cell_center("3,-2")
    check("center inside its cell", m.cell_key(cx, cy) == "3,-2")
    check("center is mid-cell", (cx, cy) == (3.5 * 400, -1.5 * 400))


def test_ingest_merges_landmarks() -> None:
    m = SpatialMap(cell_size=400.0)
    key = m.ingest(50, 50, [{"label": "Don's Donuts", "distance": "far", "confidence": 0.6}], timestamp="t1")
    check("ingest returns occupied cell", key == "0,0")
    check("first visit counted", m.cells["0,0"]["visit_count"] == 1)

    # Re-observe the same landmark, closer and more confident.
    m.ingest(60, 60, [{"label": "Don's Donuts", "distance": "near", "confidence": 0.9}], timestamp="t2")
    tag = m.cells["0,0"]["landmarks"]["Don's Donuts"]
    check("visit_count increments", m.cells["0,0"]["visit_count"] == 2)
    check("landmark sighting count merges", tag["count"] == 2)
    check("confidence keeps the max", tag["confidence"] == 0.9)
    check("distance upgrades to nearest seen", tag["distance"] == "near")
    check("last_seen advances", m.cells["0,0"]["last_seen"] == "t2")
    check("first_seen is preserved", m.cells["0,0"]["first_seen"] == "t1")


def test_links_are_undirected_and_deduped() -> None:
    m = SpatialMap()
    m.ingest(50, 50, timestamp="t")
    m.ingest(450, 50, timestamp="t")
    m.link("0,0", "1,0")
    m.link("0,0", "1,0")           # duplicate ignored
    m.link("0,0", "0,0")           # self-link ignored
    check("edge recorded forward", m.cells["0,0"]["edges"] == ["1,0"])
    check("edge recorded backward", m.cells["1,0"]["edges"] == ["0,0"])


def test_where_is_weights_by_closeness() -> None:
    m = SpatialMap(cell_size=400.0)
    # Same label seen from two cells; the near sighting should pull the
    # estimate toward its cell, away from the far one.
    m.ingest(50, 50, [{"label": "Sheriff", "distance": "far", "confidence": 0.9}])
    m.ingest(2050, 50, [{"label": "Sheriff", "distance": "near", "confidence": 0.9}])
    est = m.where_is("sheriff")          # case-insensitive
    check("known place resolves", est is not None)
    near_center_x = m.cell_center("5,0")[0]   # 2050 -> cell 5
    far_center_x = m.cell_center("0,0")[0]
    midpoint = (near_center_x + far_center_x) / 2
    check("estimate biased toward near sighting", est["x"] > midpoint)
    check("support counts both cells", est["support"] == 2)
    check("substring match works", m.where_is("Sher") is not None)
    check("unknown place returns None", m.where_is("Library") is None)


def test_frontier_selection() -> None:
    m = SpatialMap(cell_size=400.0)
    m.ingest(50, 50, timestamp="t")              # visit cell 0,0
    f = m.nearest_frontier("0,0")
    check("frontier exists after first visit", f is not None)
    check("frontier is an unvisited neighbor", f in m.neighbors("0,0"))

    # Block every neighbor except one; that one must be chosen.
    nbrs = m.neighbors("0,0")
    survivor = nbrs[3]
    for nk in nbrs:
        if nk != survivor:
            m.mark_blocked(nk)
    check("frontier skips blocked cells", m.nearest_frontier("0,0") == survivor)

    # Visit the survivor too. Every neighbor of 0,0 is now visited or blocked,
    # so the only remaining frontier must come from the survivor's own
    # neighborhood — i.e. exploration pushes outward, not back into 0,0.
    m.ingest(*m.cell_center(survivor), timestamp="t")
    f2 = m.nearest_frontier("0,0")
    check("frontier expands outward via survivor", f2 is not None and f2 in m.neighbors(survivor))
    check("frontier f2 is genuinely unexplored", m.cells.get(f2) is None)

    empty = SpatialMap()
    check("no frontier when nothing visited", empty.nearest_frontier("0,0") is None)


def test_persistence_round_trip() -> None:
    m = SpatialMap(cell_size=250.0)
    m.ingest(100, 100, [{"label": "Motel", "distance": "mid", "confidence": 0.7}], timestamp="t")
    m.link("0,0", "1,0")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "sub" / "spatial_map.json"
        m.save(p)                                # also creates parent dir
        check("save writes file", p.exists())
        loaded = SpatialMap.load(p)
        check("cell_size persists", loaded.cell_size == 250.0)
        check("cells persist", loaded.cells["0,0"]["landmarks"]["Motel"]["confidence"] == 0.7)
        check("load of missing file is empty", SpatialMap.load(Path(d) / "nope.json").cells == {})


if __name__ == "__main__":
    test_grid_math()
    test_ingest_merges_landmarks()
    test_links_are_undirected_and_deduped()
    test_where_is_weights_by_closeness()
    test_frontier_selection()
    test_persistence_round_trip()
    print(f"\nAll {_passed} checks passed.")
