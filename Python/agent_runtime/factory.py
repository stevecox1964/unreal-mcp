from __future__ import annotations

import logging
from pathlib import Path

from .agent_manager import AgentManager
from .llm_router import LLMRouter
from .memory_store import MemoryStore
from .unreal_bridge import UnrealBridge

logger = logging.getLogger("AgentRuntime")

# Python/worlds — the default world root when no override is given.
_DEFAULT_WORLDS_DIR = Path(__file__).resolve().parents[1] / "worlds"


def build_agent_manager(worlds_dir: Path = None) -> AgentManager:
    """Construct a fully-wired AgentManager with the real runtime dependencies.

    The single construction point for the standalone ``sim_runner`` (and tests),
    so every entry point wires the manager identically.

    No I/O happens here: ``UnrealBridge`` connects lazily per command and
    ``LLMRouter`` builds its API clients on first use, so this is safe to call
    offline (e.g. in tests).

    Example: ``build_agent_manager()`` or ``build_agent_manager(Path("/worlds"))``.
    """
    worlds_dir = worlds_dir or _DEFAULT_WORLDS_DIR
    mgr = AgentManager(
        worlds_dir=worlds_dir,
        llm_router=LLMRouter(),
        unreal_bridge=UnrealBridge(),
        memory_store=MemoryStore(worlds_dir),
    )
    logger.info(f"AgentManager built (worlds_dir={worlds_dir})")
    return mgr
