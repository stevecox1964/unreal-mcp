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
      - ``POST /events/clear``  → ``{"cleared": N}`` (empty the decision feed)
      - ``POST /start``         → ``manager.start_simulation(**body)``
        (body: ``{tick_seconds?, active_agents?, mode?}``)
      - ``POST /stop``          → ``manager.stop_simulation()``
      - ``POST /tick``          → ``manager.tick()`` (run one tick now — single-step debugging)
      - ``POST /pause`` / ``POST /resume`` → pause/resume the loop without stopping
      - ``GET  /agents``        → ``{"agents": manager.list_agents()}``
      - ``GET  /agents/{id}``   → ``manager.inspect_agent(id)``
      - ``POST /agents/{id}/goal`` (body ``{goal}``) → ``manager.set_agent_goal``
      - ``POST /agents/{id}/tick`` → ``manager.pulse_agent(id)`` (ignore cooldown)
      - ``POST /reset_agents``  → ``manager.reset_agents()``
      - ``POST /reset_places``  → ``manager.reset_world_places()``
      - ``POST /resync``        → ``manager.resync()``
      - ``POST /world_grid`` (body ``{cell_size?, padding?}``) → ``manager.generate_world_grid``

    This is transport only — all behavior lives in the manager, so the same app
    serves the standalone ``sim_runner`` and is exercised offline with a stub
    manager via ``TestClient``. The manager owns the single Unreal socket, so the
    runner is the exclusive host of the sim loop; the MCP simulation tools attach
    here as thin clients (#3/2.4) instead of hosting a second manager.
    """
    app = FastAPI(title="Unreal World Sim Runner", docs_url=None, redoc_url=None)

    @app.get("/")
    def root() -> dict:
        """Friendly landing for someone who opens the engine URL in a browser —
        the runner is a JSON control API; the human-facing cockpit is the web UI."""
        return {
            "service": "Unreal World Sim runner",
            "ok": True,
            "hint": "This is the JSON control API. Open the web cockpit to drive it: "
                    "http://127.0.0.1:8765/sim",
            "endpoints": ["/health", "/status", "/events", "/start", "/stop", "/tick",
                          "/pause", "/resume", "/agents", "/positions", "/reset_day",
                          "/reset_agents", "/reset_places", "/resync", "/world_grid"],
        }

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/status")
    def status() -> dict:
        return manager.get_status()

    @app.get("/events")
    def events(limit: int = 20) -> dict:
        return {"events": manager.recent_events(limit)}

    @app.post("/events/clear")
    def events_clear() -> dict:
        return {"cleared": manager.clear_events()}

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

    @app.post("/reset_day")
    async def reset_day() -> dict:
        """Restart the sim from morning (fresh day; memories + place cells kept)."""
        return await manager.restart_day()

    @app.post("/pause")
    async def pause() -> dict:
        return await manager.pause_simulation()

    @app.post("/resume")
    async def resume() -> dict:
        return await manager.resume_simulation()

    @app.get("/agents")
    def agents() -> dict:
        return {"agents": manager.list_agents()}

    @app.get("/positions")
    def positions() -> dict:
        """Last observed position/facing per active agent — the live /map dots (#18)."""
        return {"agents": manager.agent_positions()}

    @app.get("/agents/{agent_id}")
    def agent_detail(agent_id: str) -> dict:
        return manager.inspect_agent(agent_id)

    @app.post("/agents/{agent_id}/goal")
    async def agent_goal(agent_id: str, request: Request) -> dict:
        body = await _json_body(request)
        return manager.set_agent_goal(agent_id, str(body.get("goal", "")))

    @app.post("/agents/{agent_id}/tick")
    async def agent_tick(agent_id: str) -> dict:
        return await manager.pulse_agent(agent_id)

    @app.post("/reset_agents")
    async def reset_agents() -> dict:
        return await manager.reset_agents()

    @app.post("/reset_places")
    async def reset_places() -> dict:
        return await manager.reset_world_places()

    @app.post("/resync")
    def resync() -> dict:
        return manager.resync()

    @app.post("/world_grid")
    async def world_grid(request: Request) -> dict:
        body = await _json_body(request)
        return manager.generate_world_grid(
            cell_size=float(body.get("cell_size", 3000.0)),
            padding=float(body.get("padding", 800.0)),
        )

    return app


async def _json_body(request: Request) -> dict:
    """Parse a JSON request body, tolerating an empty body as ``{}``."""
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}
