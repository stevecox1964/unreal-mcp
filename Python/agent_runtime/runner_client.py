from __future__ import annotations

import logging

logger = logging.getLogger("AgentRuntime")

DEFAULT_BASE_URL = "http://127.0.0.1:8777"


class RunnerClient:
    """Thin HTTP client for the standalone sim runner's control API.

    Lets the MCP tools and the web UI *attach* to a running ``sim_runner`` instead
    of hosting the AgentManager themselves — keeping the sim's lifetime decoupled
    from Claude. All methods return the runner's JSON dict.

    The HTTP client is injectable so it can be driven in-process against a
    ``TestClient`` in tests (no real socket); in production it defaults to an
    ``httpx`` client at ``base_url``.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL, client=None, timeout: float = 5.0):
        if client is not None:
            self._client = client
        else:
            import httpx
            self._client = httpx.Client(base_url=base_url, timeout=timeout)

    # ── Control ─────────────────────────────────────────────────────────────────

    def health(self) -> dict:
        return self._client.get("/health").json()

    def status(self) -> dict:
        return self._client.get("/status").json()

    def start(self, tick_seconds: int = 1, active_agents: list[str] = None,
              mode: str = "live") -> dict:
        return self._client.post("/start", json={
            "tick_seconds": tick_seconds, "active_agents": active_agents, "mode": mode,
        }).json()

    def stop(self) -> dict:
        return self._client.post("/stop").json()

    def tick(self) -> dict:
        return self._client.post("/tick").json()

    # ── Convenience ─────────────────────────────────────────────────────────────

    def is_running(self) -> bool:
        """True if the runner reports a running sim. False if unreachable."""
        try:
            return bool(self.status().get("running"))
        except Exception as e:
            logger.debug(f"runner unreachable: {e}")
            return False

    def reachable(self) -> bool:
        """True if a runner answers /health at all."""
        try:
            return bool(self.health().get("ok"))
        except Exception:
            return False
