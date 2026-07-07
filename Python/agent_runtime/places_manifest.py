"""Authored places manifest (#15/WP6) — the world's root configuration.

A per-world ``worlds/<level>/places.json`` declares canonical places (the
user's ground truth: "my house is over here, my vegetable truck is over
here"). ``load_manifest`` parses + validates it; ``apply_manifest`` writes it
into PlaceDB at sim start, before any tick, so scheduled places resolve
without the wake seed guessing. Priority: authored > discovered > wake-seeded.

The manifest is declarative: apply clears previous authored state first, so
re-applying after the user moves or removes an entry converges. Grid
(col, row) and dx/dy are always derived from world x/y via WorldGrid — never
hand-authored.

Entry schema (see plan/specs/WP6-authored-places-manifest.md D1)::

    {"places": [
        {"name": "the vegetable truck", "x": -8950.0, "y": 160.0, "owner": "maren"},
        {"name": "village square", "x": -7500.0, "y": 1500.0, "community": true}
    ]}
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .place_db import PLACE_EXTENT_CM, PlaceDB
from .world_grid import WorldGrid

logger = logging.getLogger("AgentRuntime")


def load_manifest(path: Path) -> list[dict]:
    """Parse ``places.json`` into normalized entry dicts, failing loud per entry.

    A missing file is legal (a world without a manifest) → ``[]``. Unparseable
    JSON or a non-list ``places`` → ``logger.error``, ``[]``. A bad entry
    (missing/blank/placeholder name, non-numeric x/y) is logged by name and
    skipped; the rest survive — never silently drop.

    Returns dicts ``{name, x, y, owner, community, extent_cm, actor}`` with
    defaulting applied: ``community`` defaults to True iff ``owner`` is absent
    (a place nobody owns is a community place); ``extent_cm`` defaults to
    PLACE_EXTENT_CM; ``owner``/``actor`` are None when absent.
    """
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"places manifest {path}: unparseable JSON ({e}) — ignoring manifest")
        return []
    places = data.get("places") if isinstance(data, dict) else None
    if not isinstance(places, list):
        logger.error(f"places manifest {path}: 'places' must be a list — ignoring manifest")
        return []

    entries: list[dict] = []
    for i, raw in enumerate(places):
        label = f"entry {i} ({raw.get('name')!r})" if isinstance(raw, dict) else f"entry {i}"
        if not isinstance(raw, dict):
            logger.error(f"places manifest {path}: {label} is not an object — skipped")
            continue
        name = str(raw.get("name") or "").strip()
        if not name or name.lower() in ("null", "none", "unknown"):
            logger.error(f"places manifest {path}: {label} has no usable name — skipped")
            continue
        try:
            x, y = float(raw["x"]), float(raw["y"])
        except (KeyError, TypeError, ValueError):
            logger.error(f"places manifest {path}: {label} needs numeric x and y — skipped")
            continue
        owner = str(raw["owner"]).strip() if raw.get("owner") else None
        try:
            extent = float(raw.get("extent_cm", PLACE_EXTENT_CM))
        except (TypeError, ValueError):
            logger.error(f"places manifest {path}: {label} has non-numeric extent_cm — skipped")
            continue
        entries.append({
            "name": name,
            "x": x,
            "y": y,
            "owner": owner,
            "community": bool(raw.get("community", owner is None)),
            "extent_cm": extent,
            # Reserved for #21 v2 (re-anchor x/y from the live actor transform);
            # parsed and preserved, otherwise ignored in this WP.
            "actor": str(raw["actor"]).strip() if raw.get("actor") else None,
        })
    return entries


def apply_manifest(place_db: PlaceDB, grid: WorldGrid, entries: list[dict]) -> dict:
    """Write authored entries into PlaceDB, converging on the manifest.

    Clears previous authored state first (moves/deletes converge), then per
    entry derives (col, row) + dx/dy from x/y and writes: an ``owner`` entry
    becomes an owned place cell (source='authored'); a ``community`` entry
    community-names its grid cell, authored-wins over any runtime name (with a
    warning). Two authored entries claiming the same cell: first in file wins,
    the second is a logged manifest bug. Requires a bounded grid.

    Returns ``{"applied": N, "owned": n1, "community": n2, "skipped": n3}``
    where applied/skipped count entries and owned/community count writes.
    """
    summary = {"applied": 0, "owned": 0, "community": 0, "skipped": 0}
    if not grid.has_bounds:
        logger.error("places manifest needs world_grid.json bounds — nothing applied")
        return summary

    place_db.clear_authored()
    authored_cells: dict[tuple[int, int], str] = {}   # cell -> name written this pass
    for entry in entries:
        loc = grid.locate(entry["x"], entry["y"])
        if not loc.get("in_bounds"):
            logger.error(f"places manifest: '{entry['name']}' at "
                         f"({entry['x']}, {entry['y']}) is outside world bounds — skipped")
            summary["skipped"] += 1
            continue
        col, row = loc["col"], loc["row"]
        center = grid.cell_center(col, row)
        wrote = False

        if entry["owner"]:
            if place_db.add_owned_place(entry["owner"], col, row, entry["name"],
                                        dx=entry["x"] - center[0],
                                        dy=entry["y"] - center[1],
                                        extent_cm=entry["extent_cm"],
                                        source="authored"):
                summary["owned"] += 1
                wrote = True

        if entry["community"]:
            if (col, row) in authored_cells:
                logger.error(f"places manifest: authored '{entry['name']}' claims cell "
                             f"({col},{row}) already authored as "
                             f"'{authored_cells[(col, row)]}' — first in file wins")
            else:
                existing = place_db.get_place(col, row)
                old = (existing or {}).get("name")
                if old and old.strip().lower() != entry["name"].lower():
                    logger.warning(f"places manifest: authored '{entry['name']}' overwrites "
                                   f"runtime '{old}' at ({col},{row})")
                if place_db.set_name_authored(col, row, entry["name"],
                                              world_time="authored"):
                    authored_cells[(col, row)] = entry["name"]
                    summary["community"] += 1
                    wrote = True

        summary["applied" if wrote else "skipped"] += 1
    return summary
