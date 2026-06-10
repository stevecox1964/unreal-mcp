from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("AgentRuntime")

# Relative-distance buckets reported by the vision model, as a closeness weight.
# Nearer sightings localise a landmark better, so they dominate the centroid.
_DISTANCE_WEIGHT = {"near": 1.0, "mid": 0.6, "far": 0.3}

# 8-connected grid neighbourhood (Moore), used for frontier expansion.
_NEIGHBOR_OFFSETS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),          (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


class SpatialMap:
    """Per-agent egocentric cognitive map ("grid + place cells").

    Grid layer: a deterministic tiling of world (x, y) into square cells of
    ``cell_size`` cm. The cell an agent occupies is derived purely from its own
    position (path integration) — never from an omniscient engine world scan.

    Place layer: each visited cell accumulates landmark tags extracted from
    vision. Named-place coordinates are derived on demand (see ``where_is``) by
    averaging the centres of the cells that reported a label — there is no
    separately stored, drift-prone place table to keep in sync.

    The map is 2-D: z is intentionally not tracked. Movement re-uses the agent's
    current z, since these worlds are effectively single-storey at street level.
    """

    def __init__(self, cell_size: float = 400.0, cells: dict | None = None):
        self.cell_size = cell_size
        self.cells: dict[str, dict] = cells or {}

    # ── Persistence ───────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: Path, cell_size: float = 400.0) -> "SpatialMap":
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(cell_size=data.get("cell_size", cell_size), cells=data.get("cells", {}))
        return cls(cell_size=cell_size)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"cell_size": self.cell_size, "cells": self.cells}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ── Grid math ─────────────────────────────────────────────────────────────

    def cell_key(self, x: float, y: float) -> str:
        return f"{math.floor(x / self.cell_size)},{math.floor(y / self.cell_size)}"

    def cell_center(self, key: str) -> tuple[float, float]:
        gx, gy = self._parse(key)
        return ((gx + 0.5) * self.cell_size, (gy + 0.5) * self.cell_size)

    @staticmethod
    def _parse(key: str) -> tuple[int, int]:
        gx, gy = key.split(",")
        return int(gx), int(gy)

    def neighbors(self, key: str) -> list[str]:
        gx, gy = self._parse(key)
        return [f"{gx + dx},{gy + dy}" for dx, dy in _NEIGHBOR_OFFSETS]

    # ── Ingest ────────────────────────────────────────────────────────────────

    def _ensure_cell(self, key: str, ts: str) -> dict:
        cell = self.cells.get(key)
        if cell is None:
            cell = {
                "visit_count": 0,
                "first_seen": ts,
                "last_seen": ts,
                "landmarks": {},
                "edges": [],
                "blocked": False,
            }
            self.cells[key] = cell
        return cell

    def ingest(self, x: float, y: float, landmarks: list[dict] | None = None,
               timestamp: str | None = None) -> str:
        """Record that the agent stood at (x, y) and saw ``landmarks`` there.

        ``landmarks`` items look like Gemini's perception output:
        ``{"label": "Don's Donuts", "bearing": "right", "distance": "mid",
        "confidence": 0.85}``. Returns the key of the occupied cell.
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        key = self.cell_key(x, y)
        cell = self._ensure_cell(key, ts)
        cell["visit_count"] += 1
        cell["last_seen"] = ts

        for lm in landmarks or []:
            label = str(lm.get("label", "")).strip()
            if not label:
                continue
            conf = float(lm.get("confidence", 0.5))
            dist = str(lm.get("distance", "mid"))
            tag = cell["landmarks"].get(label)
            if tag is None:
                cell["landmarks"][label] = {
                    "count": 1, "confidence": conf,
                    "distance": dist, "bearing": lm.get("bearing"),
                }
            else:
                tag["count"] += 1
                tag["confidence"] = max(tag["confidence"], conf)
                # Keep the closest sighting — it localises the landmark best.
                if _DISTANCE_WEIGHT.get(dist, 0) > _DISTANCE_WEIGHT.get(tag["distance"], 0):
                    tag["distance"] = dist
                    tag["bearing"] = lm.get("bearing")
        return key

    def link(self, from_key: str, to_key: str) -> None:
        """Record a traversed path between two cells (undirected nav edge)."""
        if from_key == to_key:
            return
        for a, b in ((from_key, to_key), (to_key, from_key)):
            cell = self.cells.get(a)
            if cell is not None and b not in cell["edges"]:
                cell["edges"].append(b)

    def mark_blocked(self, key: str) -> None:
        """Flag a cell as unreachable (e.g. walk_to failed — off NavMesh).

        Blocked cells are skipped by frontier selection so the explorer doesn't
        repeatedly try to enter the same dead end.
        """
        ts = datetime.now(timezone.utc).isoformat()
        self._ensure_cell(key, ts)["blocked"] = True

    # ── Queries ───────────────────────────────────────────────────────────────

    def _visited_keys(self) -> list[str]:
        return [k for k, c in self.cells.items() if c["visit_count"] > 0 and not c["blocked"]]

    def where_is(self, label: str) -> dict | None:
        """Estimate world coordinates of a named place from observations.

        Returns ``{"x", "y", "support", "confidence"}`` — the confidence-and-
        closeness-weighted centroid of every cell that reported a matching
        label — or ``None`` if the label has never been seen. Matching is
        case-insensitive and substring-tolerant ("donut" matches "Don's Donuts").
        """
        q = label.strip().casefold()
        wsum = wx = wy = 0.0
        support = 0
        best_conf = 0.0
        for key, cell in self.cells.items():
            for tag_label, tag in cell["landmarks"].items():
                cl = tag_label.casefold()
                if q not in cl and cl not in q:
                    continue
                weight = tag["count"] * tag["confidence"] * _DISTANCE_WEIGHT.get(tag["distance"], 0.3)
                if weight <= 0:
                    continue
                cx, cy = self.cell_center(key)
                wx += cx * weight
                wy += cy * weight
                wsum += weight
                support += 1
                best_conf = max(best_conf, tag["confidence"])
        if wsum <= 0:
            return None
        return {"x": wx / wsum, "y": wy / wsum, "support": support, "confidence": best_conf}

    def nearest_frontier(self, from_key: str) -> str | None:
        """Return the closest unexplored cell adjacent to explored space.

        A frontier cell is a grid neighbour of a visited cell that is itself
        neither visited nor blocked. The nearest one to ``from_key`` (Euclidean
        on grid indices) is chosen; deterministic tie-break by grid coords.
        Returns ``None`` when no frontier exists (nothing visited yet, or all
        reachable cells are explored or blocked).
        """
        candidates: set[str] = set()
        for vkey in self._visited_keys():
            for nkey in self.neighbors(vkey):
                ncell = self.cells.get(nkey)
                if ncell is not None and (ncell["visit_count"] > 0 or ncell["blocked"]):
                    continue
                candidates.add(nkey)
        if not candidates:
            return None

        fx, fy = self._parse(from_key)

        def rank(key: str) -> tuple[float, int, int]:
            gx, gy = self._parse(key)
            return (math.hypot(gx - fx, gy - fy), gx, gy)

        return min(candidates, key=rank)

    def describe(self, key: str) -> dict | None:
        """Return what is known about a cell, or None if never recorded."""
        return self.cells.get(key)

    def place_labels(self, key: str, top_n: int = 3) -> list[str]:
        """Best-known landmark labels for a cell — the 'place' the agent is in.

        Ranked by sighting count x confidence; empty if the cell is unknown or
        has no landmarks yet.
        """
        cell = self.cells.get(key)
        if not cell:
            return []
        ranked = sorted(
            cell["landmarks"].items(),
            key=lambda kv: kv[1]["count"] * kv[1]["confidence"],
            reverse=True,
        )
        return [label for label, _ in ranked[:top_n]]

    def stats(self) -> dict:
        visited = self._visited_keys()
        labels = {
            lbl for c in self.cells.values() for lbl in c["landmarks"]
        }
        return {
            "cell_size": self.cell_size,
            "cells_recorded": len(self.cells),
            "cells_visited": len(visited),
            "distinct_labels": len(labels),
            "labels": sorted(labels),
        }
