from __future__ import annotations

import math
import sqlite3
import shutil
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Compass directions in clockwise order starting from North.
# UE convention: yaw 0 = +X (East), 90 = +Y (South), -90/270 = -Y (North).
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
COMMUNITY_SURVEY_MAX_AGE_SECONDS = 24 * 3600

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
    source   TEXT,          -- 'authored' when named by places.json; NULL = legacy/runtime
    place_image_id TEXT,    -- current durable N/S/E/W visual-memory revision
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

-- APC-owned place cells: a named 9x9 m box inside a grid cell, positioned as
-- an XY offset (cm) from the cell's community anchor (the cell center). Owned
-- by one APC but readable/reusable by all (#11.2).
CREATE TABLE IF NOT EXISTS owned_place_cells (
    col        INTEGER NOT NULL,
    row        INTEGER NOT NULL,
    owner      TEXT    NOT NULL,   -- agent_id
    name       TEXT    NOT NULL,
    dx         REAL    NOT NULL DEFAULT 0,   -- cm east of the community anchor
    dy         REAL    NOT NULL DEFAULT 0,   -- cm south of the community anchor
    extent_cm  REAL    NOT NULL DEFAULT 900,
    created_at TEXT,
    updated_at TEXT,
    source     TEXT    NOT NULL DEFAULT 'runtime',  -- authored | runtime | wake-seed
    place_image_id TEXT,    -- current durable N/S/E/W visual-memory revision
    PRIMARY KEY (col, row, owner, name)
);

-- Immutable place-image revisions. Logical grid X/Y is also rendered in the
-- composite heading for VLM grounding; precise world coordinates remain metadata.
CREATE TABLE IF NOT EXISTS place_images (
    place_image_id TEXT PRIMARY KEY,
    place_key      TEXT    NOT NULL,
    place_kind     TEXT    NOT NULL,
    col            INTEGER NOT NULL,
    row            INTEGER NOT NULL,
    owner          TEXT,
    name           TEXT,
    revision       INTEGER NOT NULL,
    image_path     TEXT    NOT NULL,
    north_path     TEXT    NOT NULL,
    south_path     TEXT    NOT NULL,
    east_path      TEXT    NOT NULL,
    west_path      TEXT    NOT NULL,
    description    TEXT    NOT NULL DEFAULT '',
    captured_by    TEXT    NOT NULL,
    captured_at    TEXT    NOT NULL,
    -- World position the four frames were taken from. Without it a composite
    -- filed under the wrong cell is undetectable (SR33 wrote (5,5) and (5,6)
    -- from one spot); with it, every revision can be checked against its cell.
    captured_x     REAL,
    captured_y     REAL,
    UNIQUE (place_key, revision)
);

-- What the ground was actually like underfoot in a cell — shared world fact,
-- accumulated from the lizard brain's footing report every tick an APC stands
-- there (#58). Keyed by footing as well as cell because a 30 m cell is often
-- part road and part field; storing only the newest reading would flip-flop and
-- report "grass" for a cell an APC has crossed twenty times on gravel. Counts
-- make the mix legible ("mostly gravel_road, some grass") instead of averaging
-- two different truths into one wrong one.
CREATE TABLE IF NOT EXISTS cell_ground (
    col          INTEGER NOT NULL,
    row          INTEGER NOT NULL,
    footing      TEXT    NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 1,
    last_seen_by TEXT,
    last_seen    TEXT    NOT NULL,
    PRIMARY KEY (col, row, footing)
);

-- Cells an APC looked at and decided not to walk into, with the reason it gave
-- (#59). The map had exactly two states — named, or unexplored — so a cell an
-- APC deliberately rejected relaxed back to "unexplored" and was re-advertised
-- as a survey target on the next run, forever. Dufus walked into the same corn
-- field across SR34, SR37, SR38 and SR39 for this reason.
--
-- Nothing in the code enforces a refusal: it is a fact the APC stated, stored
-- so it stops being forgotten, and shown back to every APC. The reason matters
-- more than the flag — "standing corn", "someone's yard" and "fence" are three
-- different refusals, and the navmesh-walkable/APC-refused pair is exactly the
-- training signal the world exists to collect.
CREATE TABLE IF NOT EXISTS cell_refusals (
    col        INTEGER NOT NULL,
    row        INTEGER NOT NULL,
    refused_by TEXT    NOT NULL,
    reason     TEXT    NOT NULL,
    refused_at TEXT    NOT NULL,   -- world time, as the APC stated it
    updated_at TEXT    NOT NULL,   -- real UTC
    PRIMARY KEY (col, row, refused_by)
);

-- Sub-cell no-go ground (#78). A cell refusal paints a whole 30 m district —
-- right for a cornfield, wrong for one bad backyard in an otherwise surveyable
-- cell: SR42's cell (6,4) had to stay a survey target while its south approach
-- (a pergola yard and a mobile-home interior) kept trapping Dufus. A patch is a
-- point plus a radius (default one place-cell extent, 9 m), refused by an APC
-- with a stated reason. Same contract as cell_refusals: a fact shown back to
-- every APC, never an enforcement — nothing stops a step onto a patch.
--
-- source (#91): 'stated' is the mind's judgement — someone's yard, standing
-- corn — and keeps forever, because an opinion does not expire. 'measured' is
-- the body's own reading: the engine swept this capsule along this heading and
-- it did not fit. A reading is true of the moment it was taken, and the parked
-- van that produced it drives away, so measured patches are believed for
-- `dead_end.MEASURED_TTL_S` and then stop steering navigation. They are never
-- deleted: `all_patches` is the reviewable record and must stay complete.
CREATE TABLE IF NOT EXISTS no_go_patches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    x          REAL NOT NULL,
    y          REAL NOT NULL,
    radius_cm  REAL NOT NULL,
    refused_by TEXT NOT NULL,
    reason     TEXT NOT NULL,
    refused_at TEXT NOT NULL,   -- world time, as the APC stated it
    updated_at TEXT NOT NULL,   -- real UTC
    source     TEXT NOT NULL DEFAULT 'stated',
    proofs     INTEGER NOT NULL DEFAULT 0
);

-- Per-APC living visual history linked to exact shared image revisions.
CREATE TABLE IF NOT EXISTS agent_visual_history (
    agent_id       TEXT NOT NULL,
    place_image_id TEXT NOT NULL,
    first_seen     TEXT NOT NULL,
    last_seen      TEXT NOT NULL,
    visit_count    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (agent_id, place_image_id)
);
"""

_MAX_LABELS_PER_DIRECTION = 5
_CONFIDENCE_FLOOR = 0.8

# Owned place cells are a square box this wide around their anchor point —
# 9x9 m around the APC (user, 2026-07-05). Grid cells (30 m districts) hold
# several of these; keep the two sizes an order of magnitude apart.
PLACE_EXTENT_CM = 900.0


def _age_seconds(stamp: str | None, now: datetime | None = None) -> float | None:
    """Seconds since an ``_iso_now()`` stamp. ``None`` when it cannot be read.

    Unreadable is not "old" (#91): a row whose timestamp we cannot parse must
    keep steering navigation rather than silently lapsing, per rule 12.
    """
    if not stamp:
        return None
    try:
        when = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return ((now or datetime.now(timezone.utc)) - when).total_seconds()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _place_key(name: str) -> str:
    """Normalize harmless wording differences without rewriting display names."""
    key = " ".join(str(name or "").casefold().split())
    return key[4:] if key.startswith("the ") else key


def _edit_distance(a: str, b: str) -> int:
    """Small two-row Levenshtein helper for typo-tolerant authored places."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            curr.append(min(curr[-1] + 1, prev[j] + 1,
                            prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


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
        for col in ("swept_at", "swept_by", "updated_at", "source", "place_image_id"):
            if col not in have:
                conn.execute(f"ALTER TABLE place_cells ADD COLUMN {col} TEXT")
        # source: authored (places.json) / runtime (LLM-discovered) / wake-seed.
        # Pre-WP6 rows default to 'runtime' — never guess which were wake seeds.
        have = {r[1] for r in conn.execute("PRAGMA table_info(owned_place_cells)")}
        if "source" not in have:
            conn.execute("ALTER TABLE owned_place_cells "
                         "ADD COLUMN source TEXT NOT NULL DEFAULT 'runtime'")
        if "place_image_id" not in have:
            conn.execute("ALTER TABLE owned_place_cells ADD COLUMN place_image_id TEXT")
        # captured_x/y: where the four frames were shot. NULL on pre-#55 rows —
        # never guess a position for a revision that did not record one.
        have = {r[1] for r in conn.execute("PRAGMA table_info(place_images)")}
        for col in ("captured_x", "captured_y"):
            if col not in have:
                conn.execute(f"ALTER TABLE place_images ADD COLUMN {col} REAL")
        # source/proofs (#91): who wrote this no-go patch, a mind or a body, and
        # on how much evidence. Pre-#91 rows were all the mind's — the body could
        # not write one — so 'stated' is the honest default, never a guess.
        have = {r[1] for r in conn.execute("PRAGMA table_info(no_go_patches)")}
        if "source" not in have:
            conn.execute("ALTER TABLE no_go_patches "
                         "ADD COLUMN source TEXT NOT NULL DEFAULT 'stated'")
        if "proofs" not in have:
            conn.execute("ALTER TABLE no_go_patches "
                         "ADD COLUMN proofs INTEGER NOT NULL DEFAULT 0")

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

        Clears geography, place-image revisions, and APC visual-history links.
        Generated shared images and per-agent ``observations/place_history``
        links are removed with the DB rows. The schema is preserved. Returns
        row counts for every cleared table.
        """
        with self._lock, self._connect() as conn:
            image_paths = [r[0] for r in conn.execute("SELECT image_path FROM place_images")]
            tables = ("agent_visual_history", "place_images", "place_cells",
                      "place_observations", "agent_visits", "owned_place_cells",
                      "cell_ground", "cell_refusals", "no_go_patches")
            counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in tables
            }
            for table in tables:
                conn.execute(f"DELETE FROM {table}")
        self._delete_visual_files(image_paths)
        return counts

    def _delete_visual_files(self, relative_paths: list[str]) -> None:
        """Delete only generated visual-memory files contained by this world."""
        world_root = self._path.parent.resolve()
        for relative in relative_paths:
            candidate = (world_root / relative).resolve()
            if candidate != world_root and world_root in candidate.parents and candidate.is_file():
                candidate.unlink()
        agents_dir = world_root / "agents"
        if agents_dir.is_dir():
            for history in agents_dir.glob("*/observations/place_history"):
                resolved = history.resolve()
                if agents_dir.resolve() in resolved.parents and resolved.is_dir():
                    shutil.rmtree(resolved)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_place(self, col: int, row: int) -> dict | None:
        """Return shared place context if the cell has a name, else None.

        Returns place name, compass facts, and current visual-memory reference.
        Only landmarks with confidence >= _CONFIDENCE_FLOOR are included,
        capped at _MAX_LABELS_PER_DIRECTION per compass direction.
        """
        with self._connect() as conn:
            cell = conn.execute(
                "SELECT name, place_image_id FROM place_cells "
                "WHERE col=? AND row=? AND name IS NOT NULL",
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
            visual = None
            if cell["place_image_id"]:
                visual = conn.execute(
                    "SELECT image_path, description, revision FROM place_images "
                    "WHERE place_image_id=?", (cell["place_image_id"],)
                ).fetchone()

        compass: dict[str, list[str]] = {d: [] for d in COMPASS}
        for o in obs:
            d = o["direction"]
            if d in compass and o["landmark"] not in compass[d]:
                compass[d].append(o["landmark"])
        compass = {d: labels[:_MAX_LABELS_PER_DIRECTION] for d, labels in compass.items()}
        return {
            "name": cell["name"],
            "compass": compass,
            "place_image_id": cell["place_image_id"],
            "place_image_path": visual["image_path"] if visual else None,
            "description": visual["description"] if visual else "",
            "place_image_revision": visual["revision"] if visual else None,
        }

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
        needle = _place_key(name)
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

            {col, row, name, named, swept, surveyed, named_by, named_at,
             swept_at, swept_by, updated_at, landmarks, state}

        ``named``, ``swept``, and ``surveyed`` are independent facts. ``state``
        remains the mutually exclusive paint class (named first, then swept)
        for backwards-compatible map styling.
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
                "SELECT c.col, c.row, c.name, c.named_by, c.named_at, c.swept_at, "
                "c.swept_by, c.updated_at, c.place_image_id, p.revision, "
                "p.description, p.captured_by, p.captured_at "
                "FROM place_cells c LEFT JOIN place_images p "
                "ON p.place_image_id=c.place_image_id "
                "WHERE c.name IS NOT NULL OR c.swept_at IS NOT NULL "
                "ORDER BY c.col, c.row"
            ).fetchall()
            counts = conn.execute(
                "SELECT col, row, COUNT(*) AS visual_observations, "
                "COUNT(DISTINCT LOWER(TRIM(landmark))) AS distinct_visual_labels, "
                "COALESCE(SUM(observation_count), 0) AS visual_sightings "
                "FROM place_observations WHERE confidence >= ? GROUP BY col, row",
                (_CONFIDENCE_FLOOR,),
            ).fetchall()
        visual_counts = {(c["col"], c["row"]): c for c in counts}
        now = now or datetime.now(timezone.utc)
        out = []
        for r in cells:
            cell = {
                "col": r["col"], "row": r["row"],
                "name": r["name"], "named_by": r["named_by"], "named_at": r["named_at"],
                "swept_at": r["swept_at"], "swept_by": r["swept_by"],
                "updated_at": r["updated_at"],
                "named": bool(r["name"]),
                "swept": bool(r["swept_at"]),
                "surveyed": bool(r["place_image_id"]),
                "visual_observations": 0,
                "distinct_visual_labels": 0,
                "visual_sightings": 0,
                # Compatibility for engine-neutral route-map facts. The web UI
                # deliberately does not present this as physical landmarks.
                "landmarks": 0,
                "state": "named" if r["name"] else "swept",
                "place_image_id": r["place_image_id"],
                "place_image_revision": r["revision"],
                "place_image_description": r["description"],
                "place_image_captured_by": r["captured_by"],
                "place_image_captured_at": r["captured_at"],
            }
            metrics = visual_counts.get((r["col"], r["row"]))
            if metrics:
                cell.update({
                    "visual_observations": metrics["visual_observations"],
                    "distinct_visual_labels": metrics["distinct_visual_labels"],
                    "visual_sightings": metrics["visual_sightings"],
                    "landmarks": metrics["visual_observations"],
                })
            if max_age_seconds is not None:
                cell["stale"] = self._age_exceeds(r["updated_at"], max_age_seconds, now)
            out.append(cell)
        return out

    def place_image(self, place_image_id: str) -> dict | None:
        """Return one immutable place-image revision by ID.

        Example valid input: ``place_image("0123456789abcdef0123456789abcdef")``.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM place_images WHERE place_image_id=?", (place_image_id,)
            ).fetchone()
        return dict(row) if row else None

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

    def record_ground(self, agent_id: str, col: int, row: int, footing: str) -> None:
        """Remember what an APC was actually standing on in this cell (#58).

        Every tick of footing is a free measurement of walkability that we were
        throwing away: SR37 crossed gravel to get into a cornfield and, once in
        it, had no record that the cell behind it was road. Shared across
        agents, like every other world fact in this DB.
        """
        surface = str(footing or "").strip()
        if not surface:
            return
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO cell_ground (col, row, footing, sample_count, last_seen_by, last_seen) "
                "VALUES (?, ?, ?, 1, ?, ?) "
                "ON CONFLICT(col, row, footing) DO UPDATE SET "
                "  sample_count = sample_count + 1, "
                "  last_seen_by = excluded.last_seen_by, "
                "  last_seen = excluded.last_seen",
                (col, row, surface, agent_id, now),
            )

    def get_ground(self, col: int, row: int) -> list[dict]:
        """Known footings for a cell, commonest first. Empty = never stood in.

        Empty is a real answer and must stay distinguishable from "we walked it
        and it was rough" — an APC choosing a way out needs to know which of the
        two it is looking at.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT footing, sample_count, last_seen_by, last_seen FROM cell_ground "
                "WHERE col=? AND row=? ORDER BY sample_count DESC, footing ASC",
                (col, row),
            ).fetchall()
        return [dict(r) for r in rows]

    def refuse_cell(self, agent_id: str, col: int, row: int, reason: str,
                    world_time: str) -> bool:
        """Record that an APC looked at a cell and chose not to walk into it.

        Re-refusing updates the reason rather than stacking duplicates — an APC
        is allowed to change its mind about why, and a later look is the better
        one. Returns False for an empty reason: a refusal without a stated
        reason is the flag we specifically did not want.
        """
        why = str(reason or "").strip()
        if not why:
            return False
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO cell_refusals (col, row, refused_by, reason, refused_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(col, row, refused_by) DO UPDATE SET "
                "  reason = excluded.reason, refused_at = excluded.refused_at, "
                "  updated_at = excluded.updated_at",
                (col, row, agent_id, why, str(world_time or ""), _iso_now()),
            )
        return True

    def clear_refusal(self, agent_id: str, col: int, row: int) -> bool:
        """Withdraw this APC's refusal of a cell — it may change its mind."""
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM cell_refusals WHERE col=? AND row=? AND refused_by=?",
                (col, row, agent_id),
            )
        return cur.rowcount > 0

    def get_refusals(self, col: int, row: int) -> list[dict]:
        """Every APC's stated refusal of this cell, newest first. Empty = none."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT refused_by, reason, refused_at FROM cell_refusals "
                "WHERE col=? AND row=? ORDER BY updated_at DESC",
                (col, row),
            ).fetchall()
        return [dict(r) for r in rows]

    def refuse_patch(self, agent_id: str, x: float, y: float, reason: str,
                     world_time: str,
                     radius_cm: float = PLACE_EXTENT_CM / 2,
                     source: str = "stated", proofs: int = 0) -> bool:
        """Record a sub-cell no-go patch: this ground, not this whole cell (#78).

        Re-refusing a spot already inside one of this APC's patches updates
        that patch's reason instead of stacking overlapping circles — a later
        look is the better one, same rule as ``refuse_cell``. Returns False for
        an empty reason.

        ``source`` says who wrote it (#91). ``'stated'`` is the mind's judgement
        and keeps forever; ``'measured'`` is the body's own engine reading and is
        believed only for a while, because the thing it read can move. They are
        different claims with different lifetimes, so a patch merges ONLY with a
        patch of its own source — SR54 showed what merging across them does: a
        1.1 m measured seal landed inside a stale 4.5 m stated circle, inherited
        its radius, and walled off three of a pocket's four exits.

        Within a source the radius only ever GROWS on update, and the update
        keeps the higher proof count — a wall that stopped the APC three times
        is not narrowed back to one body's width by a fourth reading taken from
        further away. A ``'measured'`` radius is additionally clamped to
        ``dead_end.MAX_RADIUS_CM``: the body's evidence never spans more than a
        body-scale volume, whatever the caller states.
        """
        from . import dead_end
        why = str(reason or "").strip()
        if not why:
            return False
        kind = str(source)
        radius = float(radius_cm)
        if kind == "measured":
            radius = min(radius, dead_end.MAX_RADIUS_CM)
        with self._lock, self._connect() as conn:
            own = conn.execute(
                "SELECT id, x, y, radius_cm, proofs, source FROM no_go_patches "
                "WHERE refused_by=?",
                (agent_id,),
            ).fetchall()
            for row in own:
                if str(row["source"] or "stated") != kind:
                    continue
                if math.hypot(x - row["x"], y - row["y"]) <= row["radius_cm"]:
                    # The centre moves too. A widening patch that keeps its old
                    # centre swallows the APC that widened it — the caller slid
                    # the circle clear on purpose (#91) and dropping that here
                    # puts the APC back inside its own mark.
                    merged = max(radius, float(row["radius_cm"]))
                    if kind == "measured":
                        merged = min(merged, dead_end.MAX_RADIUS_CM)
                    conn.execute(
                        "UPDATE no_go_patches SET x=?, y=?, reason=?, refused_at=?, "
                        "  updated_at=?, radius_cm=?, source=?, proofs=? WHERE id=?",
                        (float(x), float(y), why, str(world_time or ""), _iso_now(),
                         merged,
                         kind, max(int(proofs), int(row["proofs"] or 0)),
                         row["id"]),
                    )
                    return True
            conn.execute(
                "INSERT INTO no_go_patches (x, y, radius_cm, refused_by, reason, "
                "refused_at, updated_at, source, proofs) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (float(x), float(y), radius, agent_id, why,
                 str(world_time or ""), _iso_now(), kind, int(proofs)),
            )
        return True

    def patches_at(self, x: float, y: float) -> list[dict]:
        """Every LIVE no-go patch containing this point, newest first. Empty = clear.

        Live, not every: an expired body measurement is history, not navigation
        (#91). ``all_patches`` still shows it.
        """
        return [p for p in self.active_patches()
                if math.hypot(x - p["x"], y - p["y"]) <= p["radius_cm"]]

    def active_patches(self) -> list[dict]:
        """Patches that should still steer a step, newest first (#91).

        A ``'stated'`` patch is somebody's judgement about ground and never
        lapses. A ``'measured'`` one is a reading the body took at a moment, and
        an hour later the thing it read may have driven off — so it stops
        steering after ``dead_end.MEASURED_TTL_S`` rather than fencing off a
        street forever on the strength of one parked van.

        Nothing is deleted. Rule 12: the record of what got skipped stays whole
        and countable in ``all_patches``, expiry or not.
        """
        from . import dead_end
        now = datetime.now(timezone.utc)
        live = []
        for patch in self.all_patches():
            if patch.get("source") != "measured":
                live.append(patch)
                continue
            age = _age_seconds(patch.get("updated_at"), now)
            if age is None or age <= dead_end.MEASURED_TTL_S:
                live.append(patch)
        return live

    def clear_patches_at(self, agent_id: str, x: float, y: float) -> int:
        """Withdraw this APC's patches containing a point. Returns how many."""
        with self._lock, self._connect() as conn:
            own = conn.execute(
                "SELECT id, x, y, radius_cm FROM no_go_patches WHERE refused_by=?",
                (agent_id,),
            ).fetchall()
            hits = [row["id"] for row in own
                    if math.hypot(x - row["x"], y - row["y"]) <= row["radius_cm"]]
            for patch_id in hits:
                conn.execute("DELETE FROM no_go_patches WHERE id=?", (patch_id,))
        return len(hits)

    def all_patches(self) -> list[dict]:
        """Every no-go patch in the world — the reviewable record, like refusals."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, x, y, radius_cm, refused_by, reason, refused_at, "
                "updated_at, source, proofs FROM no_go_patches "
                "ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def all_refusals(self) -> list[dict]:
        """Every refusal in the world — the visible record of what got skipped.

        A gap in the corpus must stay countable. Surveyed and
        refused-with-a-reason are different states and neither may look like the
        other; this is what a reviewer reads to see what was left out and why.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT col, row, refused_by, reason, refused_at, updated_at "
                "FROM cell_refusals ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def set_name(self, agent_id: str, col: int, row: int, name: str, world_time: str,
                 source: str = None) -> bool:
        """Assign a canonical name to a shared place cell.

        Only writes if the cell has no name yet — first agent wins.
        Returns True if the name was stored, False if already named or invalid.
        ``source`` tags where the name came from (NULL = runtime/legacy); only
        the places.json loader passes it.
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
                "INSERT INTO place_cells (col, row, name, named_at, named_by, updated_at, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(col, row) DO UPDATE SET "
                "  name = excluded.name, named_at = excluded.named_at, named_by = excluded.named_by, "
                "  updated_at = excluded.updated_at, source = excluded.source",
                (col, row, name, world_time, agent_id, _iso_now(), source),
            )
        return True

    def set_name_authored(self, col: int, row: int, name: str, world_time: str) -> bool:
        """Community-name a cell from the authored manifest — authored wins.

        Unlike ``set_name`` (first agent wins), this overwrites any existing
        name: places.json is ground truth. ``named_by`` becomes ``"authored"``
        and ``source`` ``'authored'``; sweep data on the row is untouched.
        Returns False only for blank/placeholder names.
        """
        name = name.strip()
        if not name or name.lower() in ("null", "none", "unknown"):
            return False
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO place_cells (col, row, name, named_at, named_by, updated_at, source) "
                "VALUES (?, ?, ?, ?, 'authored', ?, 'authored') "
                "ON CONFLICT(col, row) DO UPDATE SET "
                "  name = excluded.name, named_at = excluded.named_at, named_by = excluded.named_by, "
                "  updated_at = excluded.updated_at, source = excluded.source",
                (col, row, name, world_time, _iso_now()),
            )
        return True

    def clear_authored(self) -> None:
        """Remove all authored state so a manifest re-apply converges.

        Authored owned rows are deleted outright; authored community names are
        blanked in place (the row may carry sweep data — never delete it).
        """
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM owned_place_cells WHERE source='authored'")
            conn.execute(
                "UPDATE place_cells SET name=NULL, named_by=NULL, named_at=NULL, source=NULL "
                "WHERE source='authored'"
            )

    def add_owned_place(self, agent_id: str, col: int, row: int, name: str,
                        dx: float, dy: float, extent_cm: float = PLACE_EXTENT_CM,
                        source: str = "runtime") -> bool:
        """Store an APC-owned place cell: a named 9x9 m box inside a grid cell.

        Position is an XY offset (cm) from the cell's community anchor (the
        cell center), so world position stays derivable. An owner may re-place
        their own entry (upsert bumps ``updated_at``); different owners never
        collide. Rejects blank/placeholder names like ``set_name``. Returns
        True when written. ``source`` tags provenance: ``'authored'``
        (places.json), ``'runtime'`` (LLM-discovered), or ``'wake-seed'``.
        Example: ``add_owned_place("maren", 5, 5, "My Home", dx=120.0,
        dy=-80.0)``.
        """
        name = name.strip()
        if not name or name.lower() in ("null", "none", "unknown"):
            return False
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO owned_place_cells "
                "  (col, row, owner, name, dx, dy, extent_cm, created_at, updated_at, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(col, row, owner, name) DO UPDATE SET "
                "  dx = excluded.dx, dy = excluded.dy, "
                "  extent_cm = excluded.extent_cm, updated_at = excluded.updated_at, "
                "  source = excluded.source",
                (col, row, agent_id, name, float(dx), float(dy), float(extent_cm), now, now,
                 source),
            )
        return True

    def purge_wake_seeds(self) -> list[dict]:
        """Delete every wake-seeded owned place cell — the "sync the world" op
        (#21 v1). When the user moves actors in the editor, wake seeds go stale
        and send agents hunting old spots; purging them is safe because the
        next run re-seeds at the new day-start positions. Authored rows
        (ground truth) and runtime rows (agent memories) are never touched —
        including pre-WP6 legacy rows tagged 'runtime' that may really have
        been seeds; never guess. Returns the deleted rows
        ``{col,row,owner,name,dx,dy}`` so callers can report, ``[]`` when
        nothing matched.
        """
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT col, row, owner, name, dx, dy FROM owned_place_cells "
                "WHERE source='wake-seed' ORDER BY col, row, owner, name"
            ).fetchall()
            conn.execute("DELETE FROM owned_place_cells WHERE source='wake-seed'")
        return [dict(r) for r in rows]

    def find_owned_place(self, name: str, preferred_owner: str = None) -> dict | None:
        """Resolve a name to an APC-owned place cell, or None if unknown.

        Same normalization + matching rules as ``find_named_cell`` (exact beats
        substring; deterministic tie-break by (col, row, owner, name)), with one
        extra rule: among equal-quality matches, ``preferred_owner``'s entry
        wins — my "My Home" resolves before someone else's. Returns
        ``{"col","row","owner","name","dx","dy","extent_cm"}``.
        """
        needle = _place_key(name)
        if not needle:
            return None
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT col, row, owner, name, dx, dy, extent_cm, source "
                "FROM owned_place_cells ORDER BY col, row, owner, name"
            ).fetchall()
        best: tuple[tuple[int, int, int], dict] | None = None
        for r in rows:
            owned_name = _place_key(r["name"])
            if owned_name == needle:
                quality = 0
            elif needle in owned_name or owned_name in needle:
                quality = 1
            elif len(needle) >= 8 and len(owned_name) >= 8 and _edit_distance(needle, owned_name) <= 1:
                quality = 2
            else:
                continue
            source_rank = {"authored": 0, "runtime": 1, "wake-seed": 2}.get(
                r["source"], 1)
            owner_rank = 0 if (preferred_owner and r["owner"] == preferred_owner) else 1
            # Ground truth outranks learned/guessed aliases. Within one source,
            # exact still beats substring/fuzzy and the preferred owner wins ties.
            key = (source_rank, quality, owner_rank)
            if best is None or key < best[0]:   # strict: first (ordered) match wins ties
                best = (key, dict(r))
                if key == (0, 0, 0):
                    break
        return best[1] if best else None

    def all_owned_places(self) -> list[dict]:
        """Every APC-owned place cell — the owned half of the world map (#11.2).

        Returns ``{"col","row","owner","name","dx","dy","extent_cm","source",
        "created_at"}`` per row, ordered by (col, row, owner, name).
        ``known_places`` and the web map read this alongside ``all_named_places``
        so owned places ("My Home") are consultable, not just resolvable.
        Provenance and age ride along because a duplicate row can only be judged
        against them — authored is ground truth, oldest keeps a name's meaning
        (#75).
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT col, row, owner, name, dx, dy, extent_cm, source, created_at "
                "FROM owned_place_cells ORDER BY col, row, owner, name"
            ).fetchall()
        return [dict(r) for r in rows]

    def remove_owned_place(self, owner: str, col: int, row: int, name: str) -> bool:
        """Delete one APC-owned place row. True if a row was actually removed.

        Used to collapse a place recorded twice under one name in two cells
        (#75). Exact match on the full key — this never removes "everything
        called X", because two places genuinely sharing a name are two places.
        """
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM owned_place_cells "
                "WHERE owner=? AND col=? AND row=? AND name=?",
                (owner, col, row, name),
            )
        return cur.rowcount > 0

    def owned_places_in_cell(self, col: int, row: int) -> list[dict]:
        """All APC-owned place cells inside one grid cell, ordered by (owner, name)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT owner, name, dx, dy, extent_cm FROM owned_place_cells "
                "WHERE col=? AND row=? ORDER BY owner, name",
                (col, row),
            ).fetchall()
        return [dict(r) for r in rows]

    def _visual_place_ref(self, agent_id: str, col: int, row: int,
                          place_name: str = None) -> dict:
        """Resolve a visual-memory owner without using image pixels for identity."""
        if place_name:
            owned = self.find_owned_place(place_name, preferred_owner=agent_id)
            if owned and (owned["col"], owned["row"]) == (col, row):
                key = f"owned:{col}:{row}:{owned['owner']}:{_place_key(owned['name'])}"
                return {"kind": "owned", "key": key, "owner": owned["owner"],
                        "name": owned["name"]}
        with self._connect() as conn:
            cell = conn.execute(
                "SELECT name FROM place_cells WHERE col=? AND row=?", (col, row)
            ).fetchone()
        return {"kind": "community", "key": f"community:{col}:{row}",
                "owner": None, "name": cell["name"] if cell else None}

    def current_place_image(self, agent_id: str, col: int, row: int,
                            place_name: str = None) -> dict | None:
        """Return the current place-image revision for a community or owned place.

        ``place_name`` selects an owned place when it resolves inside this cell;
        otherwise the community cell is selected. Example valid input:
        ``current_place_image("maren", 5, 5, "the vegetable truck")``.
        """
        ref = self._visual_place_ref(agent_id, col, row, place_name)
        with self._connect() as conn:
            if ref["kind"] == "owned":
                pointer = conn.execute(
                    "SELECT place_image_id FROM owned_place_cells "
                    "WHERE col=? AND row=? AND owner=? AND name=?",
                    (col, row, ref["owner"], ref["name"]),
                ).fetchone()
            else:
                pointer = conn.execute(
                    "SELECT place_image_id FROM place_cells WHERE col=? AND row=?",
                    (col, row),
                ).fetchone()
            if not pointer or not pointer["place_image_id"]:
                return None
            image = conn.execute(
                "SELECT * FROM place_images WHERE place_image_id=?",
                (pointer["place_image_id"],),
            ).fetchone()
        return dict(image) if image else None

    def record_place_image(self, agent_id: str, col: int, row: int,
                           image_path: str, views: dict[str, str],
                           description: str = "", place_name: str = None,
                           captured_xy: tuple[float, float] = None) -> dict:
        """Create an immutable place-image revision and make it current.

        Paths are stored relative to the world directory. ``views`` must contain
        N/S/E/W source paths. The capturing APC is linked to the exact revision.
        ``captured_xy`` is the world position the frames were shot from, so a
        revision filed under the wrong cell can be found later (#55).
        Example valid input::

            record_place_image("maren", 5, 5, "places/images/id.png",
                               {"N": "n.png", "S": "s.png", "E": "e.png", "W": "w.png"})
        """
        normalized = {str(k).upper(): str(v) for k, v in views.items()}
        missing = [d for d in ("N", "S", "E", "W") if not normalized.get(d)]
        if missing:
            raise ValueError(f"place image missing cardinal views: {missing}")
        ref = self._visual_place_ref(agent_id, col, row, place_name)
        image_id = uuid.uuid4().hex
        now = _iso_now()
        with self._lock, self._connect() as conn:
            revision = conn.execute(
                "SELECT COALESCE(MAX(revision), 0) + 1 FROM place_images WHERE place_key=?",
                (ref["key"],),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO place_images "
                "(place_image_id, place_key, place_kind, col, row, owner, name, revision, "
                " image_path, north_path, south_path, east_path, west_path, description, "
                " captured_by, captured_at, captured_x, captured_y) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (image_id, ref["key"], ref["kind"], col, row, ref["owner"], ref["name"],
                 revision, str(image_path), normalized["N"], normalized["S"],
                 normalized["E"], normalized["W"], str(description or ""), agent_id, now,
                 float(captured_xy[0]) if captured_xy else None,
                 float(captured_xy[1]) if captured_xy else None),
            )
            if ref["kind"] == "owned":
                conn.execute(
                    "UPDATE owned_place_cells SET place_image_id=? "
                    "WHERE col=? AND row=? AND owner=? AND name=?",
                    (image_id, col, row, ref["owner"], ref["name"]),
                )
            else:
                conn.execute(
                    "INSERT INTO place_cells (col, row, place_image_id, updated_at) "
                    "VALUES (?, ?, ?, ?) ON CONFLICT(col,row) DO UPDATE SET "
                    "place_image_id=excluded.place_image_id, updated_at=excluded.updated_at",
                    (col, row, image_id, now),
                )
            conn.execute(
                "INSERT INTO agent_visual_history "
                "(agent_id, place_image_id, first_seen, last_seen, visit_count) "
                "VALUES (?, ?, ?, ?, 1)", (agent_id, image_id, now, now),
            )
            image = conn.execute(
                "SELECT * FROM place_images WHERE place_image_id=?", (image_id,)
            ).fetchone()
        return dict(image)

    def link_agent_to_place_image(self, agent_id: str, place_image_id: str) -> dict | None:
        """Link an APC visit to an existing shared visual-memory revision."""
        now = _iso_now()
        with self._lock, self._connect() as conn:
            image = conn.execute(
                "SELECT * FROM place_images WHERE place_image_id=?", (place_image_id,)
            ).fetchone()
            if not image:
                return None
            conn.execute(
                "INSERT INTO agent_visual_history "
                "(agent_id, place_image_id, first_seen, last_seen, visit_count) "
                "VALUES (?, ?, ?, ?, 1) ON CONFLICT(agent_id, place_image_id) DO UPDATE SET "
                "last_seen=excluded.last_seen, visit_count=visit_count+1",
                (agent_id, place_image_id, now, now),
            )
        return dict(image)

    def agent_visual_history(self, agent_id: str) -> list[dict]:
        """Return an APC's chronological place-image history, oldest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT h.first_seen, h.last_seen, h.visit_count, p.* "
                "FROM agent_visual_history h JOIN place_images p USING(place_image_id) "
                "WHERE h.agent_id=? ORDER BY h.first_seen, p.place_image_id", (agent_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def absolute_image_path(self, image: dict) -> Path:
        """Resolve a stored generated-image path against the world directory."""
        return self._path.parent / str(image["image_path"])

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
