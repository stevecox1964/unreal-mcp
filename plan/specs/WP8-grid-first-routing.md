# WP8 — Grid-first routing (#17): multi-leg travel between grid cells

**Item:** backlog #17 · **Source:** user, 2026-07-05 ("we don't really have a
navigation system"); direction locked 2026-07-01 ("navigation is grid-first —
route grid→grid, then fine-approach the place cell") · **Depends on:** #15
(built 2026-07-07 — trustworthy endpoints) · **Gate:** none — loop-safe
throughout. Queue note: #18 (live camera) ranks above this but its capture
half needs the user's editor; this one an executor can build hands-off.

## What it is

Today a travel tick resolves the scheduled place to its **final** world
position and walks straight at it; when the destination is districts away and
not in frame, the agent travels greedily by vision and orbits (Maren, SR2).
This WP inserts the missing mid-scale: a destination several cells away
becomes a **plan** — a sequence of grid-cell legs, each leg a short navmesh
walk the engine can actually do, ending with a fine-approach that stops at
the owned box's edge (B7b-style). The LLM's contract is unchanged (it still
says `walk_to` with `target_location "<place>"`); the manager executes that
intent leg by leg and the prompt/log narrate the leg for legibility.

## Design (decided)

### D1 — Route module: `agent_runtime/route_planner.py` (new, pure)

No bridge, no LLM, no I/O — same purity contract as `route_map.py`. Named
`route_planner` (not `router`/`nav`) to sit beside `route_map` and `planner`.

```python
def line_cells(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]
```
Classic integer Bresenham from cell ``a`` to cell ``b`` inclusive, exactly
this algorithm (so every implementation produces identical paths — the tests
pin outputs):

```python
(x0, y0), (x1, y1) = a, b
dx, dy = abs(x1 - x0), -abs(y1 - y0)
sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
err = dx + dy
cells = [(x0, y0)]
while (x0, y0) != (x1, y1):
    e2 = 2 * err
    if e2 >= dy: err += dy; x0 += sx
    if e2 <= dx: err += dx; y0 += sy
    cells.append((x0, y0))
return cells
```

Diagonal steps are allowed (cells are 30 m districts; the navmesh handles the
local walk). v1 is a straight-line cell walk by design — obstacle/no-go cell
weighting from sweep data is the future slice (#19 option c hooks in here;
NOT in this WP).

```python
def make_route(from_cell, to_cell, target_xy: tuple[float, float],
               extent_cm: float, destination_name: str) -> dict
```
Returns the route state (a plain dict — it is cached per agent):

```python
{"destination": destination_name,       # verbatim, for cache-hit comparison
 "target_xy": (x, y),                   # final anchor (owned) or cell center (community)
 "extent_cm": extent_cm,                # 0.0 = community destination (no box)
 "path": line_cells(from_cell, to_cell),
 "leg": 1}                              # index into path of the CURRENT waypoint
```

``leg`` starts at 1 (path[0] is where the agent stood). A same-cell route has
``path == [cell]`` and ``leg == 1 == len(path)`` — immediately final.

```python
def next_waypoint(route: dict, current_cell: tuple[int, int],
                  current_xy: tuple[float, float], grid: WorldGrid) -> dict | None
```
The leg state machine, called every routed walk:

1. **Skip-ahead advance:** if ``current_cell`` appears in ``path`` at any
   index ``i >= route["leg"] - 1``, set ``route["leg"] = i + 1`` (largest such
   ``i``). The engine may cross several cells between ticks; entering any
   later path cell consumes the legs behind it. An agent *off* the path
   (avoidance detour) keeps its current leg — the waypoint pulls it back;
   the stuck detector is the escape hatch (D2).
2. **En-route:** if ``route["leg"] < len(path)``, return
   ``{"x", "y", "final": False, "leg": route["leg"], "total": len(path) - 1,
   "cell": path[route["leg"]]}`` where (x, y) = ``grid.cell_center`` of that
   cell.
3. **Final approach** (``leg >= len(path)``, i.e. standing in the destination
   cell):
   - Community destination (``extent_cm == 0``): return **None** — being in
     the cell IS arrival (`_at_scheduled_place` flips the directive to "act");
     there is nothing left to walk.
   - Owned destination: stop at the box edge, B7b-standoff style. With
     ``d = hypot(target_xy - current_xy)`` and ``half = extent_cm / 2``:
     if ``d <= half`` return **None** (inside the box — arrived); else return
     the point ``current_xy + (target_xy - current_xy) * (d - half) / d`` with
     ``final: True, leg == total``.

Returning **None** always means "stop walking — you are there".

### D2 — Leg executor: AgentManager integration

- **Endpoint resolution refactor (no behavior change):** extract the shared
  resolution chain into
  ``_resolve_place_endpoint(agent_id, name) -> dict | None`` returning
  ``{"cell": (c, r), "xy": (x, y), "extent_cm": float}`` — community match:
  cell + its center + ``extent_cm = 0.0``; else owned match (preferred_owner
  = agent_id): cell + anchor (center + dx/dy) + its extent. Rewrite
  ``_resolve_place_target`` and the destination lookup in ``route_map_for``
  on top of it (both currently duplicate the find_named_cell →
  find_owned_place chain).
- **Route cache:** ``self._routes: dict[str, dict]`` (agent_id → route) in
  ``__init__``, cleared in ``start_simulation`` next to the other per-run
  caches (``self._spatial.clear()`` block) **and** in the level-reload paths
  that clear those caches.
- **Hook** — in ``_execute_world_action``'s walk_to-by-name branch (the
  ``isinstance(action.get("target_location"), str)`` block), replace the
  direct ``_resolve_place_target`` call with:
  1. ``end = self._resolve_place_endpoint(agent_id, name)``; if None, leave
     the action unchanged (bridge's graceful idle — today's behavior).
  2. If the grid is unbounded or the agent's current cell is unknown
     (``_cell_col_row`` → None): walk directly to
     ``_resolve_place_target``'s answer — today's behavior, no routing.
  3. **Stuck replan:** if ``observation.get("stuck")``, ``self._routes.pop
     (agent_id, None)`` first — the next step re-plans a fresh line from
     where the agent actually is. (v1 replan = new straight line; smarter
     lines come with sweep-data costs, later.)
  4. Cache check: reuse ``self._routes[agent_id]`` only if its
     ``destination`` equals the requested name (verbatim) **and** its
     ``path[-1]`` equals ``end["cell"]`` (the DB may have re-resolved, e.g.
     manifest re-applied mid-run). Else
     ``make_route(current_cell, end["cell"], end["xy"], end["extent_cm"], name)``.
  5. ``wp = next_waypoint(route, current_cell, current_xy, self.world_grid)``.
     - ``None`` → pop the route and return
       ``{"status": "accepted", "action": "idle",
       "note": f"arrived at {name}"}`` (do NOT reissue a walk; the directive
       flips to "act" on the next decide).
     - else → ``action = {**action, "location": [wp["x"], wp["y"], z]}`` (z =
       current z, like ``_resolve_place_target``) and annotate the executed
       result's ``note`` with ``f"leg {wp['leg']}/{wp['total']} -> cell
       {wp['cell']}"`` (community final approach has ``cell`` = destination
       cell) so the decision feed shows the plan unfolding.
- Direction walks, wander, and target_actor walks are untouched.

### D3 — Prompt surface (legibility, not a contract change)

- ``_attach_schedule``: when the directive's status is ``travel`` and
  ``self._routes.get(agent_id)`` has ``destination == directive place``
  (verbatim), attach
  ``observation["schedule"]["route"] = {"leg": route["leg"],
  "total": max(len(route["path"]) - 1, 1), "to_cell": list(path[min(leg, len-1)]),
  "heading": <compass>}`` — heading via ``yaw_to_compass(degrees(atan2(dy, dx)))``
  from the agent toward that cell's center (the same math ``known_places``
  uses). The route dict is the *previous* tick's plan — that is fine, it is
  a narration, not a command.
- ``llm_router._schedule_note`` travel branch: when ``directive["route"]``
  exists, prepend one line to the existing text:
  ``f"You are en route: leg {r['leg']} of {r['total']}, heading {r['heading']}
  toward cell ({c}, {r2})."`` — everything else (walk_to target_location
  contract, do-not-start-activity warning) stays word-for-word.
- ``route_map.build_route_map`` gains ``path: list[tuple[int, int]] = None``;
  when given, the returned dict carries ``"path": [[c, r], ...]`` and
  ``render_map_image`` draws a small filled circle (radius ``cell_px // 8``,
  color ``(32, 96, 208)`` — the existing "from" blue) at the center of every
  path cell between A and B (exclusive). ``route_map_for`` passes the cached
  route's path when one matches the destination. Legend gains ``dots=route``.

### D4 — Not in this slice (explicitly)

- No obstacle-aware pathing (no-go cells / navmesh-cost weighting from sweep
  data) — the ``line_cells`` seam is where #19(c) plugs in later.
- No change to ``_at_scheduled_place`` / arrival semantics — geometric arrival
  already works; routing only changes *how the walk is executed*.
- No engine-side anything.

## Tests — new `Python/scripts/agent_runtime/test_route_planner.py`

check() style, temp dirs, no pytest; stub bridge that *records*
``execute_action`` calls (copy `test_wake_place.py`'s `_manager` +
`StubBridge`, add a `calls` list). Cover:

1. **line_cells:** pinned outputs for horizontal ((0,0)→(3,0)), vertical,
   perfect diagonal ((0,0)→(3,3) = 4 cells), a 2:1 slope, same-cell, and a
   reversed pair (b→a is a→b reversed for these cases).
2. **next_waypoint:** leg 1 waypoint is path[1]'s center; entering path[2]
   directly skips leg 2 (skip-ahead); off-path cell keeps the leg; community
   final → None in the destination cell; owned final → stop point exactly
   ``extent/2`` short of the anchor (assert the standoff distance), None once
   inside the box.
3. **Executor:** owned place 3+ cells away → the bridge receives the *leg-1
   cell center*, not the final anchor; after teleporting the stub observation
   into a mid-path cell, the next walk targets the following leg; the result
   note carries ``leg k/n``.
4. **Replan:** ``observation["stuck"] = True`` drops the cached route (a new
   route is planned from the current cell); changing the destination name
   re-plans; ``start_simulation``-style ``_routes.clear()`` re-arms.
5. **Arrival:** walk executed inside the owned box returns the idle
   "arrived" result and pops the route; community destination in-cell does
   the same via next_waypoint None.
6. **Fallbacks:** unknown name → action passes through unchanged; unbounded
   grid → direct walk to the resolved target (no route cached).
7. **Prompt/map:** ``_attach_schedule`` attaches ``schedule["route"]`` when
   the cached route matches the travel place; ``_schedule_note`` renders the
   "en route: leg …" line; ``build_route_map(path=...)`` carries the path and
   ``render_map_image`` still writes a PNG.

Existing suite must stay green — `test_owned_places.py` and
`test_route_map.py` exercise the old direct-walk behavior; where they assert
the bridge target is the final anchor for a *multi-cell* trip, update them to
the leg waypoint (that behavior change is the point of this WP); same-cell
trips keep their fine-approach semantics.

## Acceptance

- [x] `python scripts/run_tests.py` green (38/38 files, 2026-07-07).
- [x] Changes confined to: `route_planner.py` (new), `agent_manager.py`,
      `route_map.py`, `llm_router.py` (_schedule_note only), tests,
      `plan/backlog.md` #17 status.
- [x] The LLM action contract is unchanged (no new action types, no prompt
      contract change beyond the added en-route narration line).

## Executor notes

Built 2026-07-07 in-session, same day as the spec. Notes:
- No existing tests needed the predicted update — `test_owned_places` /
  `test_route_map` exercise `_resolve_place_target` / `route_map_for`
  directly, not the executor's walk target, and both are behavior-compatible.
- The walk_to-by-name branch became `_execute_routed_walk` (early return) —
  it can never fall through to the target_actor block, which its guard
  already excluded.
- Test grid caveat baked into `test_route_planner.py`: the 4 m test cells are
  smaller than the 9 m default box (real districts are 30 m), so the
  fine-approach case uses `extent_cm=200` to be geometrically reachable.
