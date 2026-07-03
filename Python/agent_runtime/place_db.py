from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Compass directions in clockwise order starting from North.
# UE convention: yaw 0 = +X (East), 90 = +Y (South), -90/270 = -Y (North).
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

_SCHEMA = """
PRAGMA journal_mode=WAL;

-- World geography — shared across all agents.
-- One row per grid cell; name is permanent once set (first agent wins).
CREATE TABLE IF NOT EXISTS place_cells (
    col      INTEGER NOT NULL,
    row      INTEGER NOT NULL,
    name     TEXT,
    named_at TEXT,
    named_by TEXT,          -- agent_id that first named this cell
    swept_at TEXT,          -- when this cell was 360-swept (community breadcrumb)
    swept_by TEXT,          -- agent_id that first swept this cell
    updated_at TEXT,        -- real UTC of last name/sweep/refresh (staleness basis)
    PRIMARY KEY (col, row)
);

-- Compass-indexed landmark observations — world facts, shared across agents.
-- Landmarks accumulate with per-observation counts; confidence is the max seen.
CREATE TABLE IF NOT EXISTS place_observations (
    col               INTEGER NOT NULL,
    row               INTEGER NOT NULL,
    direction         TEXT    NOT NULL,
    landmark          TEXT    NOT NULL,
    confidence        REAL    NOT NULL DEFAULT 0.8,
    observation_count INTEGER NOT NULL DEFAULT 1,
    last_seen_by      TEXT,          -- agent_id that last observed this
    last_seen         TEXT    NOT NULL,
    PRIMARY KEY (col, row, direction, landmark)
);

-- Per-agent visit history — private to each agent.
-- Useful for the web UI ("who has been where") and the wake-skip check.
CREATE TABLE IF NOT EXISTS agent_visits (
    agent_id    TEXT    NOT NULL,
    col         INTEGER NOT NULL,
    row         INTEGER NOT NULL,
    visit_count INTEGER NOT NULL DEFAULT 0,
    first_seen  TEXT,
    last_seen   TEXT,
    PRIMARY KEY (agent_id, col, row)
);

-- APC-owned place cells: a named ~3m box inside a grid cell, positioned as an
-- XY offset (cm) from the cell's community anchor (the cell center). Owned by
-- one APC but readable/reusable by all (#11.2).
CREATE TABLE IF NOT EXISTS owned_place_cells (
    col        INTEGER NOT NULL,
    row        INTEGER NOT NULL,
    owner      TEXT    NOT NULL,   -- agent_id
    name       TEXT    NOT NULL,
    dx         REAL    NOT NULL DEFAULT 0,   -- cm east of the community anchor
    dy         REAL    NOT NULL DEFAULT 0,   -- cm south of the community anchor
    extent_cm  REAL    NOT NULL DEFAULT 300,
    created_at TEXT,
    updated_at TEXT,
    PRIMARY KEY (col, row, owner, name)
);
"""

_MAX_LABELS_PER_DIRECTION = 5
_CONFIDENCE_FLOOR = 0.8


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def yaw_to_compass(yaw: float) -> str:
    """Convert an absolute UE yaw to a compass direction string.

    UE: yaw 0 = +X (East), 90 = +Y (South), 270/-90 = -Y (North).
    Returns one of: N, NE, E, SE, S, SW, W, NW.

    Examples: 0→E, 45→SE, 90→S, 135→SW, 180→W, 225→NW, 270→N, 315→NE
    """
    idx = round(yaw % 360 / 45) % 8  # 0=E at yaw 0
    return COMPASS[(idx + 2) % 8]    # rotate so index 0 = N


class PlaceDB:
    """SQLite-backed geographic knowledge base shared across all agents.

    World geography (place_cells, place_observations) is agent-agnostic —
    once Maren names and maps a cell, Dufus can read that data immediately
    and skip re-sweeping the same location.

    Per-agent visit history (agent_visits) is private, used by the web UI
    to show who has been where, and by the wake-skip optimization.

    Thread-safe: WAL mode allows concurrent reads; a write lock serialises
    all INSERT/UPDATE operations.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.executescript(_SCHEMA)
            self._migrate(conn)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Add columns introduced after a DB was first created (idempotent)."""
        have = {r[1] for r in conn.execute("PRAGMA table_info(place_cells)")}
        # updated_at: real (wall-clock) UTC of the last name/sweep/refresh — the
        # basis for staleness. Real time, not world time: the WorldClock resets
        # every run, so sim-time can't express cross-run "how long since we last
        # looked at this cell". See is_stale.
        for col in ("swept_at", "swept_by", "updated_at"):
            if col not in have:
                conn.execute(f"ALTER TABLE place_cells ADD COLUMN {col} TEXT")

    # ── Internal ──────────────────────────────────────────────────────────────

    @contextmanager
    def _connect(self):
        """Open a connection, commit on success, rollback on error, always close."""
        conn = sqlite3.connect(str(self._path), timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset(self) -> dict:
        """Wipe all geographic knowledge — start the world map from scratch.

        Clears place_cells (names), place_observations (landmarks), agent_visits
        (per-agent history), and owned_place_cells (APC-owned ~3 m spots). The
        schema is preserved; only rows are deleted. Returns the row count removed
        from each table. All of these are keyed by grid (col, row), so a change
        in the grid's cell_size invalidates every row — reset after regridding.
        """
        with self._lock, self._connect() as conn:
            counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("place_cells", "place_observations", "agent_visits",
                              "owned_place_cells")
            }
            for table in counts:
                conn.execute(f"DELETE FROM {table}")
        return counts

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_place(self, col: int, row: int) -> dict | None:
        """Return shared place context if the cell has a name, else None.

        Returns: {"name": str, "compass": {"N": [str,...], ...}}
        Only landmarks with confidence >= _CONFIDENCE_FLOOR are included,
        capped at _MAX_LABELS_PER_DIRECTION per compass direction.
        """
        with self._connect() as conn:
            cell = conn.execute(
                "SELECT name FROM place_cells WHERE col=? AND row=? AND name IS NOT NULL",
                (col, row),
            ).fetchone()
            if not cell:
                return None
            obs = conn.execute(
                "SELECT direction, landmark FROM place_observations "
                "WHERE col=? AND row=? AND confidence >= ? "
                "ORDER BY observation_count DESC, confidence DESC",
                (col, row, _CONFIDENCE_FLOOR),
            ).fetchall()

        compass: dict[str, list[str]] = {d: [] for d in COMPASS}
        for o in obs:
            d = o["direction"]
            if d in compass and o["landmark"] not in compass[d]:
                compass[d].append(o["landmark"])
        compass = {d: labels[:_MAX_LABELS_PER_DIRECTION] for d, labels in compass.items()}
        return {"name": cell["name"], "compass": compass}

    # ── Write ─────────────────────────────────────────────────────────────────

    def find_named_cell(self, name: str) -> tuple[int, int] | None:
        """Resolve a place name to a grid cell (col, row), or None if unknown.

        Matching is case- and whitespace-insensitive. A normalized **exact**
        match wins; failing that, a **substring** match (the query inside a cell
        name, or a cell name inside the query) is accepted. Ties break
        deterministically by (col, row) so the same name always resolves the same
        way. Returns the cell of the best match.

        Examples: "village square" -> (3, 4); "  Village Square  " -> (3, 4);
        "donut" -> the "Don's Donuts" cell; "the moon" -> None.
        """
        needle = " ".join(name.split()).lower()
        if not needle:
            return None
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT col, row, name FROM place_cells "
                "WHERE name IS NOT NULL ORDER BY col, row"
            ).fetchall()
        substring: tuple[int, int] | None = None
        for r in rows:
            cell_name = " ".join(r["name"].split()).lower()
            if cell_name == needle:
                return r["col"], r["row"]
            if substring is None and (needle in cell_name or cell_name in needle):
                substring = (r["col"], r["row"])
        return substring

    def all_named_places(self) -> list[dict]:
        """Return every named cell as ``{"name", "col", "row"}`` — the world map.

        Only cells with a name appear (a bare visit doesn't make a place).
        Ordered by (col, row) for deterministic output. This is the queryable
        "map" an agent consults before asking how to get somewhere.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, col, row FROM place_cells "
                "WHERE name IS NOT NULL ORDER BY col, row"
            ).fetchall()
        return [{"name": r["name"], "col": r["col"], "row": r["row"]} for r in rows]

    def is_stale(self, col: int, row: int, max_age_seconds: float, now: datetime = None) -> bool:
        """True if a cell needs re-observing: never initialized, or last touched
        (named/swept/refreshed) more than ``max_age_seconds`` ago.

        Staleness is measured in **real** wall-clock time against ``updated_at``
        (UTC), not world time — the WorldClock resets every run, so sim-time can't
        express "how long since we last looked here" across runs. ``now`` is
        injectable (a tz-aware ``datetime``) for testing; it defaults to the
        current UTC time. A cell with no place row, or no ``updated_at``, is stale.
        """
        now = now or datetime.now(timezone.utc)
        with self._connect() as conn:
            r = conn.execute(
                "SELECT updated_at FROM place_cells WHERE col=? AND row=?",
                (col, row),
            ).fetchone()
        if not r or not r["updated_at"]:
            return True
        try:
            age = (now - datetime.fromisoformat(r["updated_at"])).total_seconds()
        except ValueError:
            return True
        return age > max_age_seconds

    def map_cells(self, max_age_seconds: float = None, now: datetime = None) -> list[dict]:
        """Every place cell (named and/or swept) with its landmark count — the map view.

        One dict per row in place_cells that has a name or a sweep::

            {col, row, name, named_by, named_at, swept_at, swept_by,
             updated_at, landmarks, state}

        ``state`` is ``"named"`` if the cell has a name, else ``"swept"``.
        ``landmarks`` counts distinct compass observations at/above the confidence
        floor. Cells with only agent visits (no name, no sweep) are excluded — a
        bare visit doesn't make a place cell. Ordered by (col, row). This is what
        the web map view renders so you can watch the world get built out.

        When ``max_age_seconds`` is given, each cell also carries ``stale`` (bool),
        computed against its ``updated_at`` at ``now`` (defaults to current UTC) —
        so the map can flag cells due for re-observation. Omitted otherwise.
        """
        with self._connect() as conn:
            cells = conn.execute(
                "SELECT col, row, name, named_by, named_at, swept_at, swept_by, updated_at "
                "FROM place_cells "
                "WHERE name IS NOT NULL OR swept_at IS NOT NULL "
                "ORDER BY col, row"
            ).fetchall()
            counts = conn.execute(
                "SELECT col, row, COUNT(*) AS n FROM place_observations "
                "WHERE confidence >= ? GROUP BY col, row",
                (_CONFIDENCE_FLOOR,),
            ).fetchall()
        landmark_count = {(c["col"], c["row"]): c["n"] for c in counts}
        now = now or datetime.now(timezone.utc)
        out = []
        for r in cells:
            cell = {
                "col": r["col"], "row": r["row"],
                "name": r["name"], "named_by": r["named_by"], "named_at": r["named_at"],
                "swept_at": r["swept_at"], "swept_by": r["swept_by"],
                "updated_at": r["updated_at"],
                "landmarks": landmark_count.get((r["col"], r["row"]), 0),
                "state": "named" if r["name"] else "swept",
            }
            if max_age_seconds is not None:
                cell["stale"] = self._age_exceeds(r["updated_at"], max_age_seconds, now)
            out.append(cell)
        return out

    @staticmethod
    def _age_exceeds(updated_at: str, max_age_seconds: float, now: datetime) -> bool:
        """True if ``updated_at`` (UTC ISO) is missing or older than the max age at ``now``."""
        if not updated_at:
            return True
        try:
            return (now - datetime.fromisoformat(updated_at)).total_seconds() > max_age_seconds
        except ValueError:
            return True

    def is_explored(self, col: int, row: int) -> bool:
        """True if this grid cell already has a place cell (named or swept).

        An unexplored cell (no row, or a row with neither a name nor a sweep)
        is what triggers an APC's deterministic sweep. Example:
        ``is_explored(2, 3)`` → False until someone names or sweeps it.
        """
        with self._connect() as conn:
            row_ = conn.execute(
                "SELECT 1 FROM place_cells WHERE col=? AND row=? "
                "AND (name IS NOT NULL OR swept_at IS NOT NULL)",
                (col, row),
            ).fetchone()
        return row_ is not None

    def explored_cells(self) -> set[tuple[int, int]]:
        """Return the set of (col, row) cells that have a place cell (named or swept).

        One query — cheaper than calling ``is_explored`` per cell when scanning the
        grid for the nearest unexplored cell.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT col, row FROM place_cells "
                "WHERE name IS NOT NULL OR swept_at IS NOT NULL"
            ).fetchall()
        return {(r["col"], r["row"]) for r in rows}

    def get_swept(self, col: int, row: int) -> dict | None:
        """Return ``{name, swept_at, swept_by}`` for a cell's breadcrumb, or None."""
        with self._connect() as conn:
            r = conn.execute(
                "SELECT name, swept_at, swept_by FROM place_cells WHERE col=? AND row=?",
                (col, row),
            ).fetchone()
        if not r or (r["swept_at"] is None and r["name"] is None):
            return None
        return {"name": r["name"], "swept_at": r["swept_at"], "swept_by": r["swept_by"]}

    def mark_swept(self, agent_id: str, col: int, row: int, world_time: str) -> bool:
        """Drop a community place-cell breadcrumb after a 360 sweep of a cell.

        Creates (or annotates) the cell's place row with ``swept_at``/``swept_by``
        without giving it a personal name — so future APCs see the cell is
        explored and skip the costly re-sweep. Never clobbers an existing name or
        an earlier sweep (first sweep wins). Returns True if the breadcrumb was
        written, False if the cell was already swept.
        """
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT swept_at FROM place_cells WHERE col=? AND row=?",
                (col, row),
            ).fetchone()
            if existing and existing["swept_at"]:
                return False
            conn.execute(
                "INSERT INTO place_cells (col, row, swept_at, swept_by, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(col, row) DO UPDATE SET "
                "  swept_at = excluded.swept_at, swept_by = excluded.swept_by, "
                "  updated_at = excluded.updated_at",
                (col, row, world_time, agent_id, _iso_now()),
            )
        return True

    def touch(self, agent_id: str, col: int, row: int) -> None:
        """Record a visit for this agent; upsert agent_visits."""
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_visits (agent_id, col, row, visit_count, first_seen, last_seen) "
                "VALUES (?, ?, ?, 1, ?, ?) "
                "ON CONFLICT(agent_id, col, row) DO UPDATE SET "
                "  visit_count = visit_count + 1, last_seen = excluded.last_seen",
                (agent_id, col, row, now, now),
            )

    def set_name(self, agent_id: str, col: int, row: int, name: str, world_time: str) -> bool:
        """Assign a canonical name to a shared place cell.

        Only writes if the cell has no name yet — first agent wins.
        Returns True if the name was stored, False if already named or invalid.
        """
        name = name.strip()
        if not name or name.lower() in ("null", "none", "unknown"):
            return False
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT name FROM place_cells WHERE col=? AND row=?",
                (col, row),
            ).fetchone()
            if existing and existing["name"]:
                return False
            conn.execute(
                "INSERT INTO place_cells (col, row, name, named_at, named_by, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(col, row) DO UPDATE SET "
                "  name = excluded.name, named_at = excluded.named_at, named_by = excluded.named_by, "
                "  updated_at = excluded.updated_at",
                (col, row, name, world_time, agent_id, _iso_now()),
            )
        return True

    def add_owned_place(self, agent_id: str, col: int, row: int, name: str,
                        dx: float, dy: float, extent_cm: float = 300.0) -> bool:
        """Store an APC-owned place cell: a named ~3m box inside a grid cell.

        Position is an XY offset (cm) from the cell's community anchor (the
        cell center), so world position stays derivable. An owner may re-place
        their own entry (upsert bumps ``updated_at``); different owners never
        collide. Rejects blank/placeholder names like ``set_name``. Returns
        True when written. Example: ``add_owned_place("maren", 5, 5, "My Home",
        dx=120.0, dy=-80.0)``.
        """
        name = name.strip()
        if not name or name.lower() in ("null", "none", "unknown"):
            return False
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO owned_place_cells "
                "  (col, row, owner, name, dx, dy, extent_cm, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(col, row, owner, name) DO UPDATE SET "
                "  dx = excluded.dx, dy = excluded.dy, "
                "  extent_cm = excluded.extent_cm, updated_at = excluded.updated_at",
                (col, row, agent_id, name, float(dx), float(dy), float(extent_cm), now, now),
            )
        return True

    def find_owned_place(self, name: str, preferred_owner: str = None) -> dict | None:
        """Resolve a name to an APC-owned place cell, or None if unknown.

        Same normalization + matching rules as ``find_named_cell`` (exact beats
        substring; deterministic tie-break by (col, row, owner, name)), with one
        extra rule: among equal-quality matches, ``preferred_owner``'s entry
        wins — my "My Home" resolves before someone else's. Returns
        ``{"col","row","owner","name","dx","dy","extent_cm"}``.
        """
        needle = " ".join(name.split()).lower()
        if not needle:
            return None
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT col, row, owner, name, dx, dy, extent_cm "
                "FROM owned_place_cells ORDER BY col, row, owner, name"
            ).fetchall()
        best: tuple[tuple[int, int], dict] | None = None
        for r in rows:
            owned_name = " ".join(r["name"].split()).lower()
            if owned_name == needle:
                quality = 0
            elif needle in owned_name or owned_name in needle:
                quality = 1
            else:
                continue
            owner_rank = 0 if (preferred_owner and r["owner"] == preferred_owner) else 1
            key = (quality, owner_rank)
            if best is None or key < best[0]:   # strict: first (ordered) match wins ties
                best = (key, dict(r))
                if key == (0, 0):
                    break
        return best[1] if best else None

    def all_owned_places(self) -> list[dict]:
        """Every APC-owned place cell — the owned half of the world map (#11.2).

        Returns ``{"col","row","owner","name","dx","dy","extent_cm"}`` per row,
        ordered by (col, row, owner, name). ``known_places`` and the web map
        read this alongside ``all_named_places`` so owned places ("My Home")
        are consultable, not just resolvable.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT col, row, owner, name, dx, dy, extent_cm "
                "FROM owned_place_cells ORDER BY col, row, owner, name"
            ).fetchall()
        return [dict(r) for r in rows]

    def owned_places_in_cell(self, col: int, row: int) -> list[dict]:
        """All APC-owned place cells inside one grid cell, ordered by (owner, name)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT owner, name, dx, dy, extent_cm FROM owned_place_cells "
                "WHERE col=? AND row=? ORDER BY owner, name",
                (col, row),
            ).fetchall()
        return [dict(r) for r in rows]

    def agent_familiarity(self, agent_id: str, col: int, row: int) -> dict:
        """Return this agent's personal relationship with a grid cell.

        Returns: {visit_count, named_by_me, first_seen, last_seen}
        visit_count 0 means the agent has never been here.
        named_by_me True means this agent was the first to name the cell.
        """
        with self._connect() as conn:
            visit = conn.execute(
                "SELECT visit_count, first_seen, last_seen FROM agent_visits "
                "WHERE agent_id=? AND col=? AND row=?",
                (agent_id, col, row),
            ).fetchone()
            cell = conn.execute(
                "SELECT named_by FROM place_cells WHERE col=? AND row=?",
                (col, row),
            ).fetchone()
        return {
            "visit_count": visit["visit_count"] if visit else 0,
            "named_by_me": bool(cell and cell["named_by"] == agent_id),
            "first_seen": visit["first_seen"] if visit else None,
            "last_seen": visit["last_seen"] if visit else None,
        }

    def ingest_compass(
        self,
        agent_id: str,
        col: int,
        row: int,
        direction: str,
        landmarks: list[dict],
    ) -> None:
        """Upsert landmark observations into the shared world map.

        Each landmark dict must have "label" (str) and "confidence" (float).
        Landmarks below _CONFIDENCE_FLOOR are ignored.
        """
        if direction not in COMPASS:
            return
        now = _iso_now()
        rows = [
            (col, row, direction, lm["label"], float(lm.get("confidence", 0.8)), agent_id, now)
            for lm in landmarks
            if lm.get("label") and float(lm.get("confidence", 0)) >= _CONFIDENCE_FLOOR
        ]
        if not rows:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT INTO place_observations "
                "  (col, row, direction, landmark, confidence, observation_count, last_seen_by, last_seen) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, ?) "
                "ON CONFLICT(col, row, direction, landmark) DO UPDATE SET "
                "  observation_count = observation_count + 1, "
                "  confidence = MAX(confidence, excluded.confidence), "
                "  last_seen_by = excluded.last_seen_by, "
                "  last_seen = excluded.last_seen",
                rows,
            )
