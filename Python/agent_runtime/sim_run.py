"""Per-world sim run counter (``SR<n>``).

Every simulation run gets a monotonic id (first run = ``SR1``) so that
observation screenshots, the decision log, and general logs are all attributable
to a single run when debugging. The counter is **per-world** — each level counts
independently — and persists in a git-ignored ``sim_run.json`` next to the
world's other runtime state (``Python/worlds/<level>/sim_run.json``).

No Unreal, no network: pure counter I/O, fully offline-testable.
"""
from __future__ import annotations

import json
from pathlib import Path

_FILE = "sim_run.json"


def _path(world_dir: Path) -> Path:
    return Path(world_dir) / _FILE


def format_run(n: int) -> str:
    """Format a run number as its SR tag, e.g. ``42`` -> ``'SR42'``."""
    return f"SR{n}"


def current_number(world_dir: Path) -> int:
    """The last allocated run number for this world (``0`` if none/corrupt).

    Example: ``current_number(Path('Python/worlds/MCP_World'))`` -> ``7``.
    """
    p = _path(world_dir)
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("run", 0))
    except (ValueError, TypeError, OSError, json.JSONDecodeError):
        return 0


def current_run(world_dir: Path) -> str:
    """The current SR tag for this world (``'SR0'`` when nothing allocated yet)."""
    return format_run(current_number(world_dir))


def allocate_run(world_dir: Path) -> str:
    """Increment and persist the per-world run counter; return the new SR tag.

    The first ever run for a world returns ``'SR1'``; a missing or corrupt
    counter file restarts from ``1``. Example:
    ``allocate_run(Path('Python/worlds/MCP_World'))`` -> ``'SR1'``.
    """
    world_dir = Path(world_dir)
    world_dir.mkdir(parents=True, exist_ok=True)
    n = current_number(world_dir) + 1
    _path(world_dir).write_text(json.dumps({"run": n}), encoding="utf-8")
    return format_run(n)
