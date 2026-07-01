# WP5 — APC top-down map via lizard brain (#6b) — DESIGN, do not build

**Item:** backlog #6b · **Scenario (user, 2026-07-01):** *"I woke up, I'm at my
house, but my schedule says I need to be at my vegetable truck. Build a top-down
map of where I am and where I need to be, so I can chart a course."*

> **GATE — design sign-off only.** The user said "do not implement yet". This
> document answers the parked design questions with recommendations so the next
> joint session is a 5-minute yes/no per question, and so an executor can build
> it the day it's approved. **No code until the backlog marks #6b approved.**

## The three parked questions, answered (recommendations)

### Q1 — Is the "map" a semantic structure the LLM reads, or a rendered image?

**Semantic structure, rendered as text (JSON + an ASCII grid), not an image.**

- The lizard-brain contract ([[feedback_lizard_brain_contract]],
  [[architecture_lizard_brain_sensing]]) says the LLM gets generic semantic
  labels — a data structure of known facts fits; a rendered image would then
  need vision to read back what we already have as data (a round-trip through
  pixels for nothing).
- Everything needed is already queryable: `PlaceDB.map_cells()` (named/swept
  state per cell), `place_observations` (landmarks per compass direction),
  `WorldGrid` (geometry), `find_named_cell`/`find_owned_place` (destination).
- ASCII grids are cheap to log, diff, and show in the web cockpit for debugging.

### Q2 — How far does it extend: corridor between here↔there, or a radius?

**Corridor: the bounding rectangle of (current cell, destination cell) padded
by 1 cell on every side, clamped to world bounds.** Rationale: the scenario is
always "here → there"; a radius wastes tokens on cells behind the agent; the
+1 pad keeps detour options (one row/col around the straight line) visible.
Worst case on the current world (~40×40 m town, 400 cm cells) this stays small;
if a future world makes corridors huge, cap at ~15×15 cells and say so in the
output ("map truncated").

### Q3 — Shared with the web A1 `/map` view, or separate?

**Same data source (PlaceDB), separate renderer.** A1's `map_cells()` +
`map.html` serve the *human* observability view (whole world, colors, polling).
The APC map is per-query, corridor-scoped, and text — a different projection of
the same tables. No coupling: the new module reads PlaceDB; it does not touch
`web_ui`. (B-side nice-to-have later: a cockpit debug page that shows the last
map an APC requested.)

## Contract compliance (the design tension, resolved)

Per #6's resolution notes: the output is **facts, not advice**.

- Cells are labeled by *known state* (`name`, `swept`, `unexplored`) and
  landmarks — never engine names, never actor refs.
- The "course" is reported as facts: *"cells between you and the destination,
  and what is known about each"* plus a straight-line bearing/distance — not
  "you should go via X". The LLM charts the course; lizard brain describes the
  terrain. If a later slice adds a navmesh path query (#6 routing), it comes
  back the same way: "a walkable route exists: NE 12 m, then E 20 m" — a fact
  about the world.

## Build spec (for the day it's approved)

New module `Python/agent_runtime/route_map.py` — pure, dependency-injected,
offline-testable (no bridge, no LLM):

```python
def corridor(from_cell: tuple[int,int], to_cell: tuple[int,int],
             cols: int, rows: int, pad: int = 1,
             max_span: int = 15) -> tuple[range, range]
    """The padded bounding col/row ranges (Q2), clamped to the grid."""

def build_route_map(place_db, world_grid,
                    from_cell: tuple[int,int], to_cell: tuple[int,int]) -> dict
    """Facts an APC can chart a course from:
    {
      "from": {"cell": [c,r], "name": <community name|None>},
      "to":   {"cell": [c,r], "name": ..., "bearing": "NE", "distance_m": 34},
      "cells": [ {"cell": [c,r], "state": "named|swept|unexplored",
                  "name": ..., "landmarks": <count>}, ... ],   # corridor only
      "ascii": "<grid drawing>",
      "truncated": False,
    }"""

def render_ascii(cells, from_cell, to_cell) -> str
```

ASCII legend (fixed): `A` = you, `B` = destination, `#` = named cell,
`+` = swept, `.` = unexplored, one row per grid row (north at top — note the UE
mapping already used by `yaw_to_compass`: -Y is north). Landmark names are
listed *below* the grid, keyed by cell, not crammed into it.

Wiring (one seam): `AgentManager` gets
`route_map_for(agent_id, destination_name) -> dict | None` — resolve the
destination via the existing resolver chain (community name, then WP4 owned
places if landed), locate the agent's current cell, delegate to
`build_route_map`. Exposure to the LLM (a tool? injected on travel ticks under a
`## Your Map` section?) is a **separate decision** — recommend: inject only on
`schedule.status == "travel"` ticks to bound token cost. Confirm at sign-off.

Tests (`test_route_map.py`): corridor math (pad, clamp, max_span truncation);
cell states pulled from a temp PlaceDB; bearing/distance against
`known_places`' conventions; ASCII renders A/B/#/+/. in the right positions on
a small synthetic world; unbounded grid → None/empty (no crash).

## Dependencies / sequencing

- Works **without** WP4 (destination = community-named cell); WP4 adds owned
  destinations ("my vegetable truck") — build after WP4 if both are approved.
- Feeds #6 "lizard-brain routing" (the navmesh path-as-facts call slots into
  `build_route_map` output later as `"route": [...]`).
- Ties into A3/#10: on wake with a travel directive, this is the map the APC
  reads.

## Decision checklist for the sign-off session

- [ ] Q1 semantic-text map (rec: yes)
- [ ] Q2 corridor+1, cap 15 (rec: yes)
- [ ] Q3 separate renderer over shared PlaceDB (rec: yes)
- [ ] Exposure: inject on travel ticks only (rec) vs. an explicit LLM tool
- [ ] Build now vs. after WP4 (rec: after, if WP4 approved)

## Executor notes

*(append findings/deviations here)*
