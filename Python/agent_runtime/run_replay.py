"""Run replay index (#14): step through a sim run's observation frames.

Pure, read-only indexing over a world's on-disk artifacts (the #9 ``SR<n>``
tags). Groups observation screenshots by run + agent and joins each frame to its
decision-log entry, so a review UI can scrub a run tick by tick. No Unreal, no
network, no DB — just the observations dirs and ``logs/agent_decisions.log``.

Layout consumed (per world ``worlds/<level>/``)::

    agents/<agent>/observations/SR<n>_observation_<YYYYMMDD_HHMMSS>[_<tag>].png
    logs/agent_decisions.log   # one JSON object per line, carrying "sim_run"
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

# SR<n>_observation_<YYYYMMDD_HHMMSS>[_<tag>].png  (tag = wake_/sweep views etc.)
_FRAME_RE = re.compile(r"^(SR\d+)_observation_(\d{8}_\d{6})(?:_(.+))?\.png$")


def is_frame_name(name: str) -> bool:
    """True if ``name`` is a well-formed SR observation filename (path-safety)."""
    return bool(_FRAME_RE.match(name))


def _run_num(run: str) -> int:
    try:
        return int(run[2:])
    except (ValueError, IndexError):
        return 0


def list_agents(world_dir: Path) -> list[str]:
    adir = Path(world_dir) / "agents"
    if not adir.exists():
        return []
    return sorted(p.name for p in adir.iterdir() if p.is_dir())


def list_runs(world_dir: Path) -> list[str]:
    """Run tags (``SR<n>``) that have at least one observation frame, newest first."""
    world_dir = Path(world_dir)
    runs: set[str] = set()
    for agent in list_agents(world_dir):
        obs = world_dir / "agents" / agent / "observations"
        if not obs.exists():
            continue
        for f in obs.iterdir():
            m = _FRAME_RE.match(f.name)
            if m:
                runs.add(m.group(1))
    return sorted(runs, key=_run_num, reverse=True)


def _frame_time(stamp: str) -> datetime | None:
    try:
        return datetime.strptime(stamp, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_iso(s) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _load_decisions(world_dir: Path, run: str, agent: str) -> list[tuple]:
    """(time, entry) decision-log rows for one run+agent, tolerant of bad lines."""
    log = Path(world_dir) / "logs" / "agent_decisions.log"
    rows: list[tuple] = []
    if not log.exists():
        return rows
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("sim_run") == run and e.get("agent_id") == agent:
            rows.append((_parse_iso(e.get("timestamp")), e))
    return rows


def _nearest_decision(ftime, decisions, window: float):
    """The decision row closest in time to a frame, within ``window`` seconds."""
    if ftime is None:
        return None
    best, best_delta = None, None
    for dtime, entry in decisions:
        if dtime is None:
            continue
        delta = abs((dtime - ftime).total_seconds())
        if delta <= window and (best_delta is None or delta < best_delta):
            best, best_delta = entry, delta
    if best is None:
        return None
    return {"action_type": best.get("action_type"), "thought": best.get("thought"),
            "result_status": best.get("result_status"), "timestamp": best.get("timestamp"),
            "timing": best.get("timing")}


def list_frames(world_dir: Path, run: str, agent: str,
                max_join_seconds: float = 120.0) -> list[dict]:
    """Ordered observation frames for one run+agent, each joined to its nearest
    decision (same run+agent, closest timestamp within the window).

    Each frame: ``{filename, timestamp, tag, decision}`` where ``decision`` is
    the joined ``{action_type, thought, result_status, timestamp}`` or ``None``
    (a scene-unchanged tick captures a frame but records no decision).
    """
    world_dir = Path(world_dir)
    obs = world_dir / "agents" / agent / "observations"
    if not obs.exists():
        return []
    decisions = _load_decisions(world_dir, run, agent)
    frames: list[dict] = []
    for f in obs.iterdir():
        m = _FRAME_RE.match(f.name)
        if not m or m.group(1) != run:
            continue
        frames.append({"filename": f.name, "timestamp": m.group(2),
                       "tag": m.group(3), "_ft": _frame_time(m.group(2))})
    frames.sort(key=lambda fr: fr["timestamp"])
    for fr in frames:
        fr["decision"] = _nearest_decision(fr.pop("_ft"), decisions, max_join_seconds)
    return frames
