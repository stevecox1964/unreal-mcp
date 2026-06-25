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
            conn.commit()
        finally:
            conn.close()

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

        Clears place_cells (names), place_observations (landmarks), and
        agent_visits (per-agent history). The schema is preserved; only rows
        are deleted. Returns the row count removed from each table.
        """
        with self._lock, self._connect() as conn:
            counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("place_cells", "place_observations", "agent_visits")
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
                "INSERT INTO place_cells (col, row, name, named_at, named_by) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(col, row) DO UPDATE SET "
                "  name = excluded.name, named_at = excluded.named_at, named_by = excluded.named_by",
                (col, row, name, world_time, agent_id),
            )
        return True

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
