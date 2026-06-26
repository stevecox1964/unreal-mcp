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

    # Relevance weights — recency is the base signal; being in the same place or
    # having a known face present each lift an older memory above newer noise.
    _W_RECENCY = 1.0
    _W_SAME_CELL = 2.0
    _W_SAME_PLACE = 1.0
    _W_KNOWN_PERSON = 2.0

    def relevant(self, n: int = 5, current_cell: str = None, current_place: str = None,
                 known_names: list[str] = None) -> list[dict]:
        """Return the ``n`` most relevant past events, most relevant first.

        Relevance blends recency (newer scores higher), spatial proximity (same
        grid cell, then same place), and social ties (a known person appears in
        the event). With no spatial/social context it degrades to "most recent
        first". Beats the flat recency window for overnight recall.
        """
        events = self._all()
        if not events:
            return []
        known = {str(name).strip().lower() for name in (known_names or [])}
        total = len(events)
        scored = []
        for i, e in enumerate(events):
            recency = (i + 1) / total  # 0..1, newest highest
            score = self._W_RECENCY * recency
            if current_cell is not None and e.get("grid_cell") == current_cell:
                score += self._W_SAME_CELL
            if current_place is not None and e.get("place") == current_place:
                score += self._W_SAME_PLACE
            if known and any(str(s).strip().lower() in known for s in (e.get("saw") or [])):
                score += self._W_KNOWN_PERSON
            # Stable tie-break: more recent (higher i) first.
            scored.append((score, i, e))
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [e for _, _, e in scored[:n]]

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
