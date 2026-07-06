# WP6 — Authored places manifest (#15): the world's root configuration

**Item:** backlog #15 · **Source:** user, 2026-07-05 ("the APCs don't have a root
configuration — my house is over here, my vegetable truck is over here") ·
**Urgency raised 2026-07-06:** the user moved Maren/truck/Dufus in the editor and
every wake-seeded place went stale — Maren hunted a truck 9 m from where the DB
said. Authored ground truth is the durable fix. · **Gate:** none — build it.

Loop-safe: pure Python + SQLite + JSON, offline-testable throughout.

## What it is

A per-world manifest `worlds/<level>/places.json` of canonical places, loaded
into PlaceDB at sim start, before any tick. Priority becomes
**authored > discovered > wake-seeded**. Also adds a `source` column that tags
every place row as `authored` / `runtime` / `wake-seed` — WP7's sync button and
future cleanups depend on that distinction.

## Design (decided)

### D1 — Manifest schema: `worlds/<level>/places.json`

```json
{
  "places": [
    {"name": "the vegetable truck", "x": -8950.0, "y": 160.0, "owner": "maren"},
    {"name": "dufus's home", "x": -10460.0, "y": -800.0, "owner": "dufus",
     "extent_cm": 900.0},
    {"name": "village square", "x": -7500.0, "y": 1500.0, "community": true}
  ]
}
```

Per entry:
- `name` (required, non-blank after strip — reject "null"/"unknown" like
  `set_name` does),
- `x`/`y` (required, world cm — the anchor point),
- `owner` (optional agent_id → writes an **owned place cell** for that agent),
- `community` (optional bool → community-names the containing grid cell).
  **Default: `community = (owner is absent)`** — a place with no owner is a
  community place; an owned place may *also* set `"community": true` to name
  its cell.
- `extent_cm` (optional, default `PLACE_EXTENT_CM` = 900),
- `actor` (optional Unreal actor name — **parsed and preserved, otherwise
  ignored in this WP**; #21 v2 will re-anchor x/y from that actor's live
  transform).

Grid `(col,row)` and `dx/dy` are **derived** from x/y via `WorldGrid`
(`locate`, `cell_center`) — never hand-authored, exactly like the wake seed
does today (`_at_scheduled_place`, the `add_owned_place(dx=xyz[0]-center[0],…)`
branch).

### D2 — `source` column (PlaceDB migration)

- `owned_place_cells` gains `source TEXT NOT NULL DEFAULT 'runtime'`;
  `place_cells` gains `source TEXT` (NULL = legacy/runtime). Both via
  `_migrate()` — extend the existing "add columns introduced later" loop to
  cover `owned_place_cells` too (same `PRAGMA table_info` + `ALTER TABLE ADD
  COLUMN` pattern).
- `add_owned_place(...)` gains `source: str = "runtime"` (plain default —
  MCP-tool typing rules don't apply here, but keep the simple form). The upsert
  also updates `source` on conflict.
- `set_name(...)` gains `source: str = None` handled in the body (store NULL
  when absent) — only the manifest loader passes it.
- Call-site tagging: the wake seed in `_at_scheduled_place` passes
  `source="wake-seed"`; the organic naming path in `_execute_world_action`
  (~line 1592, the different-name-in-named-cell branch) keeps the default
  `"runtime"`.

### D3 — Loader module: `agent_runtime/places_manifest.py` (new)

Two pure functions (mirror `WorldGrid.load`'s tolerance style, but **fail
loud per entry** — never silently drop):

```python
def load_manifest(path: Path) -> list[dict]
```
Missing file → `[]` (a world without a manifest is legal). Unparseable JSON or
a non-list `places` → `logger.error`, return `[]`. Per entry: missing/blank
`name`, non-numeric `x`/`y` → `logger.error` naming the entry, skip it, keep
the rest. Returns normalized dicts
`{name, x, y, owner|None, community: bool, extent_cm: float, actor|None}`
with the D1 defaulting applied.

```python
def apply_manifest(place_db: PlaceDB, grid: WorldGrid, entries: list[dict]) -> dict
```
Requires a **bounded** grid: if `grid.has_bounds` is false, `logger.error`
("manifest needs world_grid.json bounds") and return `{"applied": 0, ...}`
without writing. Then, in one pass:

1. **Clear previous authored state** (this is what makes moves/deletes work —
   the manifest is declarative, re-applying converges):
   - `DELETE FROM owned_place_cells WHERE source='authored'`
   - `UPDATE place_cells SET name=NULL, named_by=NULL, named_at=NULL,
     source=NULL WHERE source='authored'` (never DELETE the row — it may carry
     sweep data).
   Add a `PlaceDB.clear_authored()` method for this; the loader must not run
   raw SQL.
2. **Write each entry:** derive `col,row = locate(x,y)`, `center =
   cell_center(col,row)`, `dx,dy = x-center[0], y-center[1]`.
   - `owner` set → `add_owned_place(owner, col, row, name, dx, dy, extent_cm,
     source="authored")`.
   - `community` true → community-name the cell **authored-wins**: if the cell
     already has a *different* runtime name, `logger.warning` ("authored
     '<new>' overwrites runtime '<old>' at (col,row)") and overwrite (name,
     named_by="authored", source='authored'). `set_name` is first-wins, so add
     `PlaceDB.set_name_authored(col, row, name, world_time)` doing the
     overwriting upsert. Two authored entries claiming the same cell: first in
     file wins, `logger.error` for the second (a manifest bug the user must
     see).
   - Entry `in_bounds` false from `locate` → `logger.error`, skip.
3. Return `{"applied": N, "owned": n1, "community": n2, "skipped": n3}`.

### D4 — Call site: `AgentManager.start_simulation`

Right after `self.place_db = PlaceDB(db_path)` (~line 228):

```python
manifest = places_manifest.load_manifest(self._agents_dir.parent / "places.json")
if manifest:
    summary = places_manifest.apply_manifest(self.place_db, self.world_grid, manifest)
    logger.info(f"places.json: {summary}")
    self._manifest_present = True
```

`self._manifest_present` (init False in `__init__`) — used by D6's log-level
choice. Note `_load_agents` (line 219) has already run, so `self.world_grid`
is the level's bounded grid.

### D5 — Schedule validation (fail loud at plan time)

New `AgentManager._validate_schedule(agent, schedule)`: for each block, resolve
`block["place"]` through the same chain as `_at_scheduled_place`
(`find_named_cell`, else `find_owned_place(name, preferred_owner=agent_id)`);
collect blocks that resolve to nothing. `logger.warning` one line per bad
block: `[<agent>] schedule 08:00-12:00 'tend the stall' place 'the vegetable
truck' resolves to NOTHING — agent will hunt; author it in places.json`.
Returns the bad-block list (for tests).

Called after `planner.ensure_daily_plan(...)` in **both** `_attach_schedule`
and `_wake_directive`, at most once per `(agent_id, day)` — cache
`self._validated_plans: set[tuple[str, str]]`, cleared in `start_simulation`
next to `_wake_stepped.clear()`.

### D6 — Wake-seed demoted to fallback (log-only change)

No behavior change: the seed already fires only when the place resolves to
nothing, and authored entries make scheduled places resolvable. Change: when
the seed fires and `self._manifest_present`, log at **WARNING** ("seeding
'<name>' despite places.json — place not authored?") instead of INFO. The
seed keeps `source="wake-seed"` (D2).

### D7 — Not in this slice (explicitly)

- No `places.json` for MCP_World is authored here — the *user* places things;
  Claude/the executor must not invent world coordinates. (The 2026-07-06 facts
  can seed it in a dev session: truck at (-8950, 160) owner maren; dufus home
  at (-10460, -800) owner dufus.)
- No web UI (that's #16 / WP7's report surface).
- No re-anchoring from `actor` transforms (#21 v2).
- `all_owned_places()` / map payloads don't expose `source` yet — WP7 adds
  what it needs.

## Tests — new `Python/scripts/agent_runtime/test_places_manifest.py`

check() style, temp dirs, no pytest. Cover:

1. **load_manifest:** missing file → []; bad JSON → [] (and no raise); bad
   entries (blank name, string x) skipped while good ones survive; defaulting
   (`community` true iff no owner; extent default 900; actor preserved).
2. **apply_manifest:** owned entry → owned row at derived (col,row) with
   dx/dy such that `cell_center + (dx,dy) == (x,y)` (assert floats);
   community entry → named cell with `source='authored'`; re-apply after
   editing x/y (simulate the user moving the truck) → row re-anchors, **no
   duplicate rows**; entry removed from manifest → authored row gone after
   re-apply; runtime rows untouched by clear; unbounded grid → applied 0,
   nothing written.
3. **Authored wins:** cell runtime-named "motel" + authored community "market
   square" in the same cell → name becomes "market square"; the runtime
   sweep data on that row survives.
4. **Resolution:** after apply, `_at_scheduled_place` (reuse the `_manager`
   stub from `test_wake_place.py`) returns True standing inside the authored
   truck box and **no wake seed fires** (no `wake-seed` row appears).
5. **Validation:** a schedule block naming an unauthored place returns it
   from `_validate_schedule` (and an authored one doesn't); once-per-day cache
   works.
6. **Source tagging:** wake seed writes `source='wake-seed'`;
   `add_owned_place` default is `'runtime'`; migration adds the column to a
   pre-existing DB file (create with old schema minus the column, reopen,
   assert PRAGMA shows it).

Existing suite must stay green; `test_wake_place.py` and `test_owned_places.py`
call sites are signature-compatible (new params have defaults).

## Acceptance

- [ ] `python scripts/run_tests.py` green (36+ files).
- [ ] Changes confined to: `places_manifest.py` (new), `place_db.py`,
      `agent_manager.py`, tests, `plan/backlog.md` #15 status.
- [ ] No `places.json` committed for MCP_World (user authors it).

## Executor notes

_(empty)_
