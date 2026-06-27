from __future__ import annotations

import logging

from fastapi import FastAPI, Request

logger = logging.getLogger("AgentRuntime")


def build_control_app(manager) -> FastAPI:
    """Build the runner's localhost HTTP control surface over an AgentManager.

    Routes (all JSON):
      - ``GET  /health``        → ``{"ok": true}`` (liveness; no manager call)
      - ``GET  /status``        → ``manager.get_status()``
      - ``GET  /events?limit=N`` → ``{"events": manager.recent_events(N)}`` (decision log)
      - ``POST /start``         → ``manager.start_simulation(**body)``
        (body: ``{tick_seconds?, active_agents?, mode?}``)
      - ``POST /stop``          → ``manager.stop_simulation()``
      - ``POST /tick``          → ``manager.tick()`` (run one tick now — single-step debugging)

    This is transport only — all behavior lives in the manager, so the same app
    serves the standalone ``sim_runner`` and is exercised offline with a stub
    manager via ``TestClient``. The manager owns the single Unreal socket, so the
    runner is the exclusive host of the sim loop.
    """
    app = FastAPI(title="Unreal World Sim Runner", docs_url=None, redoc_url=None)

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/status")
    def status() -> dict:
        return manager.get_status()

    @app.get("/events")
    def events(limit: int = 20) -> dict:
        return {"events": manager.recent_events(limit)}

    @app.post("/start")
    async def start(request: Request) -> dict:
        body = await _json_body(request)
        return await manager.start_simulation(
            tick_seconds=int(body.get("tick_seconds", 1)),
            active_agents=body.get("active_agents"),
            mode=body.get("mode", "live"),
        )

    @app.post("/stop")
    async def stop() -> dict:
        return await manager.stop_simulation()

    @app.post("/tick")
    async def tick() -> dict:
        return await manager.tick()

    return app


async def _json_body(request: Request) -> dict:
    """Parse a JSON request body, tolerating an empty body as ``{}``."""
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}
