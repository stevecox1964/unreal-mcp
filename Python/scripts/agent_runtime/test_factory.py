"""Offline test for the shared AgentManager factory (backlog #3 / 2.1).

The MCP server and the future standalone sim_runner must wire the manager
identically — so construction lives in one place. No Unreal, no network (the
bridge connects lazily, LLM clients are built on first use). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_factory.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.factory import build_agent_manager   # noqa: E402
from agent_runtime.agent_manager import AgentManager     # noqa: E402
from agent_runtime.unreal_bridge import UnrealBridge      # noqa: E402
from agent_runtime.llm_router import LLMRouter            # noqa: E402
from agent_runtime.memory_store import MemoryStore        # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_factory_wires_real_deps():
    with tempfile.TemporaryDirectory() as tmp:
        worlds = Path(tmp) / "worlds"
        mgr = build_agent_manager(worlds_dir=worlds)
        check("returns an AgentManager", isinstance(mgr, AgentManager))
        check("uses the given worlds dir", mgr.worlds_dir == worlds)
        check("wires a real UnrealBridge", isinstance(mgr.bridge, UnrealBridge))
        check("wires a real LLMRouter", isinstance(mgr.llm, LLMRouter))
        check("wires a real MemoryStore", isinstance(mgr.memory, MemoryStore))


def test_factory_defaults_worlds_dir():
    mgr = build_agent_manager()
    check("defaults to Python/worlds", mgr.worlds_dir.name == "worlds")


def main():
    test_factory_wires_real_deps()
    test_factory_defaults_worlds_dir()
    print("\nAll factory checks passed.")


if __name__ == "__main__":
    main()
