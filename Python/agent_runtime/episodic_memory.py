from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("AgentRuntime")


class EpisodicLog:
    """Per-agent append-only record of what happened, one event per acted tick.

    Stored as JSON Lines (``<agent_dir>/episodes.jsonl``) — append-only so an
    overnight run never pays a rewrite cost and history is never trimmed (unlike
    the 30-item ``memory.json`` window). Each event is a free-form dict; the
    manager writes ``{world_time, grid_cell, place, saw[], action, outcome}``.

    Reads are best-effort: a malformed line is skipped, never fatal, so a
    partially-written tail can't crash recall.
    """

    def __init__(self, path: Path):
        self._path = path

    # ── Write ───────────────────────────────────────────────────────────────────

    def record(self, event: dict) -> None:
        """Append one event as a JSON line."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    # ── Read ────────────────────────────────────────────────────────────────────

    def _all(self) -> list[dict]:
        if not self._path.exists():
            return []
        out: list[dict] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip a torn tail line rather than fail recall
        return out

    def recent(self, n: int = 20) -> list[dict]:
        """Return the last ``n`` events, oldest first."""
        return self._all()[-n:]

    def query(self, place: str = None, character: str = None) -> list[dict]:
        """Return events matching all given filters, oldest first.

        ``place`` matches the event's ``place`` field; ``character`` matches any
        name in its ``saw`` list (case-insensitive). With no filter, returns all
        events. Example: ``query(place="square")`` or ``query(character="Maren")``.
        """
        events = self._all()
        if place is not None:
            events = [e for e in events if e.get("place") == place]
        if character is not None:
            needle = character.strip().lower()
            events = [
                e for e in events
                if any(needle == str(s).strip().lower() for s in (e.get("saw") or []))
            ]
        return events
