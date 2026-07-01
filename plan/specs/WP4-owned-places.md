# WP4 — APC-owned place cells + grid-first resolve (A5 / #11.2)

**Item:** backlog A5 + #11.2 · **Definition locked (user, 2026-07-01):** an
APC-owned place cell is a **named ~3 m bounding box** (Maren's "The vegetable
truck", "My Home"), positioned by **XY offset from the grid cell's community
place cell**; **navigation is grid-first** (coarse grid routing, place cells
only for the last leg).

> **GATE — do not build without user approval.** The user flagged this "maybe
> too complicated" and soft-deferred it behind #6b. This spec exists so the
> yes/no is cheap: everything below is decided; the user only approves or
> rejects the *minimal slice*. Executor sessions: skip this WP unless the
> backlog marks it approved.

## What the architect recommends the user approve (the minimal slice)

Grid-first navigation **already exists** in skeleton form: `walk_to "<name>"` →
`PlaceDB.find_named_cell` → `WorldGrid.cell_center` → one navmesh walk. The
genuinely missing pieces are only:

1. a place inside a cell can't be finer than the cell center (400 cm cell — a
   3 m box *is* most of a cell, so the offset mostly matters for **identity**,
   not geometry);
2. one name per grid cell (PK is `(col,row)`) — Maren cannot have "My Home" in
   the same cell as the community name "village outskirts"; today her name is
   silently **dropped** (`set_name` is first-wins, `_record_place` discards the
   False return).

So the minimal slice = an **owned-places store + resolver fallback + organic
write path**. The two-leg "route grid→grid then fine-approach" choreography is
**not** built here — a single `walk_to` to `cell_center + offset` gives the same
arrival point, and multi-cell coarse routing is #6b's course-charting job.
If the user rejects even this: the fallback status quo is "owned names in an
already-named cell keep being dropped", which quietly loses "My Home".

## Design (decided)

### D1 — Schema: new table in `place_db.py`'s `_SCHEMA`

```sql
-- APC-owned place cells: a named ~3m box inside a grid cell, positioned as an
-- XY offset (cm) from the cell's community anchor (the cell center). Owned by
-- one APC but readable/reusable by all (#11.2).
CREATE TABLE IF NOT EXISTS owned_place_cells (
    col        INTEGER NOT NULL,
    row        INTEGER NOT NULL,
    owner      TEXT    NOT NULL,   -- agent_id
    name       TEXT    NOT NULL,
    dx         REAL    NOT NULL DEFAULT 0,  -- cm east of the community anchor
    dy         REAL    NOT NULL DEFAULT 0,  -- cm south of the community anchor
    extent_cm  REAL    NOT NULL DEFAULT 300,
    created_at TEXT,
    updated_at TEXT,
    PRIMARY KEY (col, row, owner, name)
);
```
`CREATE TABLE IF NOT EXISTS` self-migrates existing DBs (same pattern as the
rest of `_SCHEMA`); no `_migrate` change needed. The **community anchor** is the
grid cell center (`WorldGrid.cell_center(col,row)`) — the sweep's GOTO_CENTER
point — so world position = `cell_center + (dx, dy)` and stays derivable if the
grid file ever moves.

### D2 — PlaceDB API (mirror the style of `set_name`/`find_named_cell`)

```python
def add_owned_place(self, agent_id, col, row, name, dx, dy, extent_cm=300.0) -> bool
```
Upsert: an owner may re-place/refresh **their own** entry (`updated_at` bumps);
different owners never collide (owner is in the PK). Reject blank/"null" names
like `set_name` does. Returns True when written.

```python
def find_owned_place(self, name, preferred_owner=None) -> dict | None
```
Same normalization + matching rules as `find_named_cell` (exact beats
substring, deterministic tie-break by `(col,row,owner,name)`), with one extra
rule: among equal-quality matches, `preferred_owner`'s entry wins (my "My Home"
before someone else's). Returns
`{"col","row","owner","name","dx","dy","extent_cm"}`.

```python
def owned_places_in_cell(self, col, row) -> list[dict]
```
All owned entries in a cell, ordered by `(owner, name)` — for #6b and the map
view later.

### D3 — Resolver fallback (`agent_manager._resolve_place_target`, ~line 1008)

Change signature to accept the resolving agent:
`_resolve_place_target(self, agent_id: str, name: str, observation: dict)`
(one caller, in `_execute_world_action` ~1348 — pass `agent.agent_id`).
Resolution order:
1. `find_named_cell(name)` → cell center (**unchanged** — community names win);
2. else `find_owned_place(name, preferred_owner=agent_id)` →
   `cell_center(col,row) + (dx,dy)`, keep the agent's current z.
Log the resolution the same way the community hit does
(`Resolved owned place '<name>' (<owner>) -> ...`).

This IS grid-first in the degenerate single-leg case: the target is expressed
as *grid cell + local offset*, and the engine walks there. Multi-cell coarse
routing stays out (see gate note above / #6b).

### D4 — Organic write path (`agent_manager._record_place`, ~line 1283)

Today: `set_name` first-wins; a second name in the cell is dropped. New:

```python
stored = self.place_db.set_name(agent_id, col, row, name, now)
if stored:
    log "place named" (unchanged)
elif <cell already has a DIFFERENT community name>:
    center = self.world_grid.cell_center(col, row)
    if center is not None:
        self.place_db.add_owned_place(agent_id, col, row, name,
                                      dx=xyz[0]-center[0], dy=xyz[1]-center[1])
        log f"owned place: '{name}' by {agent_id} at {grid_key}"
```
"Different name" check: `get_place(col,row)["name"].strip().lower() != name.lower()`
(re-naming the same community name must not create a shadow owned entry).
The legacy spatial-map ingest at the end of `_record_place` stays as-is.

### D5 — Not in this slice (explicitly)

- Surfacing owned places in `known_places` / the decision prompt (follow-up —
  needs a cap/format decision once we see volumes).
- The web `/map` showing owned boxes (nice B-side polish).
- The 3 m extent doing anything (no geometry consumes it yet; stored so the
  fine-approach and #6b can use it later).
- Multi-leg grid→grid routing (#6b).

## Tests

New `Python/scripts/agent_runtime/test_owned_places.py` (check() style, temp
dir DB like `test_cell_sweep.py`/`test_place_resolver.py`):

1. **CRUD:** `add_owned_place` writes; same owner+name upserts (updated_at
   changes, no second row); two owners can hold the same name in the same cell;
   blank/"null" names rejected.
2. **Find:** exact beats substring; `preferred_owner` wins ties; unknown → None.
3. **Resolver order:** a name that exists as a community cell resolves to that
   cell center even when an owned place shares the name; a name that exists
   only as an owned place resolves to `center + (dx,dy)` (assert the actual
   floats); unknown name still returns None.
4. **Write path:** in a cell already community-named "village square", a
   decision naming "my home" creates an owned entry with offset =
   agent position − cell center; re-naming "village square" creates nothing;
   in an unnamed cell, behavior is unchanged (community name, no owned row).
5. Existing `test_place_resolver.py` still green (update its call sites for the
   new `_resolve_place_target` signature).

## Acceptance

- [x] User approval recorded in `plan/backlog.md` #11.2 **before any code**. (User: "WP4 approved,
      build the minimal slice", 2026-07-01.)
- [x] `python scripts/run_tests.py` green. (27/27.)
- [x] Changes confined to `place_db.py`, `agent_manager.py`, tests, backlog.

## Executor notes

- **Built 2026-07-01 by the architect session directly** (user approved and asked for it in-session,
  so no executor handout). Implemented exactly as specced (D1–D5); no deviations. New test:
  `test_owned_places.py` (28 checks). `test_place_resolver.py` needed no edits — it exercises
  `_execute_world_action`, not `_resolve_place_target` directly.
