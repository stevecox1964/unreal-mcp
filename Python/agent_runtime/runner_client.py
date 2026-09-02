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

    def events(self, limit: int = 20) -> list:
        """Recent decision-log entries for the cockpit's live log."""
        return self._client.get("/events", params={"limit": limit}).json().get("events", [])

    def clear_events(self) -> dict:
        """Empty the decision feed; returns ``{"cleared": N}``."""
        return self._client.post("/events/clear").json()

    def start(self, tick_seconds: int = 1, active_agents: list[str] = None,
              mode: str = "play") -> dict:
        return self._client.post("/start", json={
            "tick_seconds": tick_seconds, "active_agents": active_agents, "mode": mode,
        }).json()

    def stop(self) -> dict:
        return self._client.post("/stop").json()

    def tick(self) -> dict:
        return self._client.post("/tick").json()

    def reset_day(self) -> dict:
        """Restart the sim from morning — fresh day, keep memories + place cells."""
        return self._client.post("/reset_day").json()

    def pause(self) -> dict:
        return self._client.post("/pause").json()

    def resume(self) -> dict:
        return self._client.post("/resume").json()

    def agents(self) -> list:
        return self._client.get("/agents").json().get("agents", [])

    def positions(self) -> list:
        """Last observed agent positions for the live map (#18)."""
        return self._client.get("/positions").json().get("agents", [])

    def inspect_agent(self, agent_id: str) -> dict:
        return self._client.get(f"/agents/{agent_id}").json()

    def set_agent_goal(self, agent_id: str, goal: str) -> dict:
        return self._client.post(f"/agents/{agent_id}/goal", json={"goal": goal}).json()

    def request_interrupt(self, agent_id: str, kind: str, source: str, reason: str,
                          priority: int = None, payload: dict = None,
                          preemptible: bool = True) -> dict:
        """Offer an explicit-source generic interruption for one APC."""
        body = {"kind": kind, "source": source, "reason": reason,
                "preemptible": preemptible}
        if priority is not None:
            body["priority"] = priority
        if payload is not None:
            body["payload"] = payload
        return self._client.post(f"/agents/{agent_id}/interruptions", json=body).json()

    def resolve_interrupt(self, agent_id: str, status: str, outcome: str) -> dict:
        """Record a terminal result for an APC's active interruption."""
        return self._client.post(f"/agents/{agent_id}/interruptions/resolve", json={
            "status": status, "outcome": outcome,
        }).json()

    def start_chat(self, agent_id: str, source: str) -> dict:
        return self._client.post(f"/agents/{agent_id}/chat/start", json={
            "source": source,
        }).json()

    def send_chat_message(self, agent_id: str, message: str) -> dict:
        return self._client.post(f"/agents/{agent_id}/chat/message", json={
            "message": message,
        }).json()

    def guide_from_chat(self, agent_id: str, direction: str) -> dict:
        return self._client.post(f"/agents/{agent_id}/chat/guide", json={
            "direction": direction,
        }).json()

    def end_chat(self, agent_id: str) -> dict:
        return self._client.post(f"/agents/{agent_id}/chat/end").json()

    def pulse_agent(self, agent_id: str) -> dict:
        """Tick one agent now, ignoring its cooldown."""
        return self._client.post(f"/agents/{agent_id}/tick").json()

    def reset_agents(self) -> dict:
        return self._client.post("/reset_agents").json()

    def reset_places(self) -> dict:
        return self._client.post("/reset_places").json()

    def resync(self) -> dict:
        return self._client.post("/resync").json()

    def capture_starts(self) -> dict:
        """Adopt current Unreal APC transforms as reset/start points."""
        return self._client.post("/capture_starts").json()

    def generate_world_grid(self, cell_size: float = 3000.0, padding: float = 800.0) -> dict:
        return self._client.post("/world_grid", json={
            "cell_size": cell_size, "padding": padding,
        }).json()

    def regrid(self, level: str, origin_x: float, origin_y: float) -> dict:
        """Apply a logical origin and clear state keyed by the old grid."""
        return self._client.post("/regrid", json={
            "level": level, "origin_x": origin_x, "origin_y": origin_y,
        }).json()

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
