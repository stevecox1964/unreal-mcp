from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("AgentRuntime")

# Labels that carry no identity — a sighting of one of these is not an
# acquaintance (you can't "know" an unknown person), so they're dropped.
_ANONYMOUS = {"", "unknown", "unknown person", "person", "someone", "a person"}

_SENTIMENT_MIN, _SENTIMENT_MAX = -1.0, 1.0


def _norm(name: str) -> str:
    """Collapse whitespace and lowercase for stable identity keys."""
    return " ".join(str(name).split()).lower()


def is_anonymous(name: str) -> bool:
    """True if ``name`` carries no identity (empty or 'unknown person', etc.).

    Such a sighting can't become an acquaintance or a named ``saw`` entry.
    """
    return _norm(name) in _ANONYMOUS


class SocialMemory:
    """Per-agent acquaintance store — who this agent has met, when, and where.

    Persisted as ``<agent_dir>/social.json``. Mirrors :class:`SpatialMap`'s
    load/save shape: a plain JSON document, one per agent, so it survives long
    or overnight runs that the 30-item ``memory.json`` window forgets.

    Each acquaintance keys on a normalized name and tracks::

        {"name": "Maren",          # display name as first seen
         "first_met": "<world_time>",
         "last_seen": "<world_time>",
         "last_cell": "12,7",      # grid cell key where last seen
         "meet_count": 3,          # ticks this agent perceived them
         "interaction_count": 1,   # say/message exchanges
         "sentiment": 0.2}         # running affinity, clamped [-1, 1]

    Anonymous sightings ("unknown person") are ignored — you can only become
    acquainted with someone who has an identity.
    """

    def __init__(self, acquaintances: dict | None = None):
        # keyed by normalized name
        self._people: dict[str, dict] = acquaintances or {}

    # ── Persistence ─────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: Path) -> "SocialMemory":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(acquaintances=data.get("acquaintances", {}))
        except Exception as e:
            logger.error(f"Bad social memory {path}: {e} — starting empty")
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"acquaintances": self._people}, indent=2),
            encoding="utf-8",
        )

    # ── Write ───────────────────────────────────────────────────────────────────

    def record_sighting(self, name: str, cell_key: str | None, world_time: str) -> bool:
        """Record that this agent saw ``name`` at ``cell_key`` at ``world_time``.

        First sighting creates the acquaintance (sets ``first_met``); later ones
        bump ``meet_count`` and refresh ``last_seen``/``last_cell``. Returns False
        for anonymous/empty labels (no identity to remember).

        Example: ``record_sighting("Maren", "12,7", "Day 1 08:30")``.
        """
        key = _norm(name)
        if key in _ANONYMOUS:
            return False
        person = self._people.get(key)
        if person is None:
            self._people[key] = {
                "name": " ".join(str(name).split()),
                "first_met": world_time,
                "last_seen": world_time,
                "last_cell": cell_key,
                "meet_count": 1,
                "interaction_count": 0,
                "sentiment": 0.0,
            }
        else:
            person["last_seen"] = world_time
            person["last_cell"] = cell_key
            person["meet_count"] = person.get("meet_count", 0) + 1
        return True

    def record_interaction(self, name: str, world_time: str, sentiment_delta: float = 0.0) -> bool:
        """Record a say/message exchange with ``name``, nudging sentiment.

        Creates the acquaintance if unseen (an interaction implies a meeting).
        ``sentiment`` accumulates and is clamped to [-1, 1]. Returns False for
        anonymous labels.
        """
        key = _norm(name)
        if key in _ANONYMOUS:
            return False
        if key not in self._people:
            self.record_sighting(name, None, world_time)
        person = self._people[key]
        person["interaction_count"] = person.get("interaction_count", 0) + 1
        person["last_seen"] = world_time
        person["sentiment"] = max(
            _SENTIMENT_MIN, min(_SENTIMENT_MAX, person.get("sentiment", 0.0) + sentiment_delta)
        )
        return True

    # ── Read ────────────────────────────────────────────────────────────────────

    def get(self, name: str) -> dict | None:
        """Return the acquaintance record for ``name``, or None if unknown."""
        return self._people.get(_norm(name))

    def knows(self, name: str) -> bool:
        return _norm(name) in self._people

    def known_names(self) -> list[str]:
        """Display names of everyone this agent has met, most-met first."""
        return [p["name"] for p in self.acquaintances()]

    def acquaintances(self) -> list[dict]:
        """All acquaintances, ranked by meet_count then interaction_count desc.

        Deterministic ordering (ties break by name) so recall and prompts are
        stable across runs.
        """
        return sorted(
            self._people.values(),
            key=lambda p: (-p.get("meet_count", 0), -p.get("interaction_count", 0), p.get("name", "")),
        )
