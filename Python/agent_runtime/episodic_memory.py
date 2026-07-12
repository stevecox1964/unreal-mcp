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

    # Auto-consolidation defaults: once the log passes ``_max_events``, roll up
    # everything older than the most recent ``_keep_recent`` into per-place
    # summaries. Checked only every ``_consolidate_every`` appends so the rewrite
    # cost is amortised (a no-op below the threshold).
    _max_events = 1000
    _keep_recent = 200
    _consolidate_every = 200

    def __init__(self, path: Path):
        self._path = path
        self._since_consolidate = 0

    # ── Write ───────────────────────────────────────────────────────────────────

    def record(self, event: dict) -> None:
        """Append one event as a JSON line; consolidate periodically when large."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        self._since_consolidate += 1
        if self._since_consolidate >= self._consolidate_every:
            self._since_consolidate = 0
            self.consolidate()

    def reset(self) -> int:
        """Clear learned episodes and return the number of events removed."""
        removed = len(self._all())
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text("", encoding="utf-8")
        self._since_consolidate = 0
        return removed

    def consolidate(self, max_events: int = None, keep_recent: int = None) -> dict:
        """Roll up old events into compact per-place summaries to cap file growth.

        A no-op while the log has ``<= max_events`` rows. Otherwise everything
        older than the most recent ``keep_recent`` events is grouped by ``place``
        into one summary row each — ``{kind:"summary", place, count, first_time,
        last_time, actions:{...}, saw:[unique], grid_cells:[unique]}`` — and the
        recent tail is kept verbatim. Summary rows carry ``place``/``saw`` so
        ``query``/``relevant`` keep working across them. Returns a small report.
        """
        max_events = self._max_events if max_events is None else max_events
        keep_recent = self._keep_recent if keep_recent is None else keep_recent
        events = self._all()
        if len(events) <= max_events:
            return {"consolidated": 0, "summaries": 0, "kept": len(events)}

        old, recent = events[:-keep_recent], events[-keep_recent:]
        # Don't re-summarise existing summary rows away — carry them through.
        passthrough = [e for e in old if e.get("kind") == "summary"]
        to_roll = [e for e in old if e.get("kind") != "summary"]

        groups: dict[str, list[dict]] = {}
        for e in to_roll:
            groups.setdefault(e.get("place") or "", []).append(e)

        summaries: list[dict] = list(passthrough)
        for place, evs in groups.items():
            times = [e.get("world_time", "") for e in evs]
            actions: dict[str, int] = {}
            saw: set[str] = set()
            cells: set[str] = set()
            for e in evs:
                actions[e.get("action")] = actions.get(e.get("action"), 0) + 1
                saw.update(s for s in (e.get("saw") or []) if s)
                if e.get("grid_cell"):
                    cells.add(e["grid_cell"])
            summaries.append({
                "kind": "summary",
                "place": place or None,
                "count": len(evs),
                "first_time": min(times) if times else None,
                "last_time": max(times) if times else None,
                "actions": actions,
                "saw": sorted(saw),
                "grid_cells": sorted(cells),
            })
        # Oldest-first overall: summaries (by their last_time) then recent verbatim.
        summaries.sort(key=lambda s: (s.get("last_time") or ""))
        rows = summaries + recent

        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        tmp.replace(self._path)
        return {"consolidated": len(to_roll), "summaries": len(summaries), "kept": len(recent)}

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
