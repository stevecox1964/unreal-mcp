"""Standalone Unreal World Sim runner.

Runs the agent simulation **independent of Claude / the MCP server** — its own
process, driven over a localhost HTTP control surface (see `agent_runtime.runner_app`).
This is the "runs overnight without Claude open" host: it owns the AgentManager
(and therefore the single Unreal socket); the MCP tools and web UI *attach* to it
via `agent_runtime.runner_client.RunnerClient`.

Run (with Unreal in PIE):
    .venv/Scripts/python.exe sim_runner.py --port 8777

Then drive it:
    curl http://127.0.0.1:8777/status
    curl -X POST http://127.0.0.1:8777/start -d '{"tick_seconds":2}'

The control API + client are offline-tested (scripts/agent_runtime/test_runner_api.py);
the live loop against Unreal is verified in PIE.
"""
from __future__ import annotations

import argparse
import logging

from agent_runtime import sim_run
from agent_runtime.factory import build_agent_manager
from agent_runtime.runner_app import build_control_app

logger = logging.getLogger("AgentRuntime")


def create_app():
    """Build the control app over a fresh, factory-wired AgentManager.

    No I/O at construction (the bridge connects lazily; LLM clients build on first
    use), so this is safe to import/build offline; the manager only touches Unreal
    once a tick actually runs.
    """
    return build_control_app(build_agent_manager())


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the Unreal World Sim as a standalone process.")
    ap.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8777, help="bind port (default 8777)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(sim_run)s] %(message)s")
    run_filter = sim_run.SimRunFilter()
    for handler in logging.root.handlers:
        handler.addFilter(run_filter)
    logger.info(f"Starting sim runner on http://{args.host}:{args.port}")

    import uvicorn
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
