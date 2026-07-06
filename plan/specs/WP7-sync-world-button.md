# WP7 — "I moved things — sync the world" button, v1 (#21)

**Item:** backlog #21 · **Source:** user, 2026-07-06 ("we also need a 'I moved
things, sync the world' button somewhere") · **Depends on:** WP6 (the `source`
column is the authored/wake-seed/runtime distinction this needs) · **Gate:**
none — build after WP6.

Loop-safe: web_ui route + PlaceDB ops, TestClient-tested.

## What it is

When the user rearranges actors in the editor, wake-seeded owned places go
stale and send agents hunting old spots (Maren, 2026-07-06 — fixed that day by
Claude deleting rows by hand). v1 makes that one button: **purge wake-seed
debris and report exactly what was deleted**; the next run re-seeds at the new
day-start spots. Deliberately NOT touched: authored rows (the manifest is
ground truth — re-anchoring from `actor` transforms is #21 v2) and runtime
LLM-discovered places (they are the agents' memories, not seeds).

## Design (decided)

### D1 — `PlaceDB.purge_wake_seeds() -> list[dict]`

Deletes `owned_place_cells WHERE source='wake-seed'`; returns the deleted rows
(`{col,row,owner,name,dx,dy}`) so callers can report. Empty list when nothing
matched. (Legacy rows with `source='runtime'` that were *actually* wake seeds
predate WP6 — do NOT try to guess them; the 2026-07-06 manual cleanup already
removed the known ones.)

### D2 — Route: `POST /api/world/sync` (web_ui/main.py)

Form/query param `level` (resolve via `_resolve_level` like `/api/map`).
Opens the world's `world_places.db` **only if it exists** (same guard as
`build_map` — a sync must not create a DB). Response JSON:

```json
{"level": "MCP_World", "deleted": [{"owner": "maren", "name": "the vegetable truck",
  "col": 6, "row": 6}], "count": 1}
```

`count` 0 is a fine, honest answer ("nothing to sync"). No confirmation step —
the operation is small, self-reporting, and self-healing (seeds regrow at next
wake).

### D3 — Button on `/map`

A `Sync world` button next to the level selector on `map.html` (the page the
user is on when they notice stale boxes). On click: `POST /api/world/sync`,
then render the report into the existing `#tip` line — e.g.
`synced: deleted 2 wake seeds (maren: the vegetable truck; dufus: home)` or
`synced: nothing to purge` — and force a map `refresh()`. Purple boxes for
purged seeds disappear on that refresh.

### D4 — Not in v1 (explicitly)

- No manifest re-anchoring from live actor transforms (#21 v2 — needs WP6's
  `actor` field + a bridge read; live-gated).
- No community-cell staleness marking.
- No "re-shoot map" (that's #18's button; they'll sit together later).

## Tests — extend `Python/scripts/agent_runtime/test_map_view.py` or new `test_world_sync.py` (prefer new)

1. `purge_wake_seeds` deletes only `source='wake-seed'` rows — authored and
   runtime rows survive; returns the deleted rows; second call returns [].
2. `POST /api/world/sync` (TestClient + temp world à la `_world()`): seeds a
   wake-seed row + a runtime row → response lists exactly the wake-seed row,
   count 1; DB reflects it.
3. Missing DB → `{"count": 0, "deleted": []}` and **no DB file created**.
4. `/map` page HTML contains the Sync world button + its fetch call.

## Acceptance

- [ ] `python scripts/run_tests.py` green.
- [ ] Changes confined to: `place_db.py`, `web_ui/main.py`,
      `web_ui/templates/map.html`, tests, `plan/backlog.md` #21 status.

## Executor notes

_(empty)_
