from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("AgentRuntime")


class UnrealBridge:
    """
    Thin wrapper around UnrealConnection.send_command that exposes
    high-level methods the AgentManager and ActionValidator can call.

    Deliberately synchronous — matches the existing send_command API.
    All socket calls reconnect per-command (Unreal closes after each).
    """

    def _send(self, command: str, params: dict) -> dict:
        from unreal_mcp_server import get_unreal_connection
        conn = get_unreal_connection()
        if not conn:
            return {"success": False, "error": "Unreal not connected"}
        try:
            result = conn.send_command(command, params)
            if not result:
                return {}
            if result.get("status") == "success" and isinstance(result.get("result"), dict):
                return {"status": "success", **result["result"]}
            return result
        except Exception as e:
            logger.error(f"send_command {command} error: {e}")
            return {"success": False, "error": str(e)}

    # ── Level info ────────────────────────────────────────────────────────────

    def get_current_level(self) -> str:
        """Return the short name of the currently loaded level, or '' on failure."""
        result = self._send("get_current_level_name", {})
        return result.get("name", "")

    # ── Actor binding ─────────────────────────────────────────────────────────

    def find_actor(self, actor_name: str) -> Optional[dict]:
        """Resolve an actor by internal name or editor label, preferring exact matches."""
        result = self._send("find_actors_by_name", {"pattern": actor_name})
        actors = result.get("actors", [])
        if not actors:
            return None

        wanted = actor_name.casefold()
        for actor in actors:
            if str(actor.get("name", "")).casefold() == wanted:
                return actor
        for actor in actors:
            if str(actor.get("label", "")).casefold() == wanted:
                return actor
        return actors[0]

    def spawn_actor(
        self,
        blueprint_class: str,
        actor_name: str,
        location: list[float] | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "blueprint_name": self._blueprint_asset_name(blueprint_class),
            "actor_name": actor_name,
            "location": location or [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
        }
        return self._send("spawn_blueprint_actor", params)

    def _blueprint_asset_name(self, blueprint_class: str) -> str:
        """Convert /Game/Blueprints/BP_Name.BP_Name_C to BP_Name for this plugin."""
        name = blueprint_class.rsplit("/", 1)[-1]
        name = name.split(".", 1)[0]
        if name.endswith("_C"):
            name = name[:-2]
        return name

    # ── Observation ───────────────────────────────────────────────────────────

    def get_observation(self, actor_name: str) -> dict:
        """Gather structured world state for one agent."""
        location = self._send("get_character_location",    {"character_name": actor_name})
        nearby   = self._send("get_nearby_actors",         {"character_name": actor_name, "radius": 500.0})
        action   = self._send("get_character_current_action", {"character_name": actor_name})
        return {
            "actor_name":     actor_name,
            "location":       location.get("location"),
            "nearby_actors":  nearby.get("actors", []),
            "current_action": action.get("current_action"),
            "ai_state":       action.get("ai_state"),
        }

    # ── Action execution ──────────────────────────────────────────────────────

    def execute_action(self, actor_name: str, action: dict) -> dict:
        t = action.get("type", "idle")

        if t == "idle":
            return {"status": "accepted", "action": "idle"}

        if t == "walk_to":
            params: dict[str, Any] = {"character_name": actor_name}
            if action.get("target_actor"):
                params["target_actor"] = action["target_actor"]
            elif action.get("location"):
                params["location"] = action["location"]
            elif action.get("target_location"):
                # LLM sometimes uses target_location as a string label
                # Best effort: log and idle — real location resolution needs world-state lookup
                logger.warning(f"walk_to with string target_location '{action['target_location']}' — idling")
                return {"status": "accepted", "action": "idle", "note": "string location not resolved"}
            return self._send("command_character_move_to", params)

        if t == "speak_to":
            return self._send("command_character_say", {
                "character_name": actor_name,
                "text": action.get("message", ""),
            })

        if t == "follow_character":
            return self._send("command_character_follow", {
                "character_name": actor_name,
                "target_actor":   action.get("target", ""),
            })

        if t == "stop":
            return self._send("command_character_stop", {"character_name": actor_name})

        if t == "inspect_object":
            return self._send("command_character_look_at", {
                "character_name": actor_name,
                "target_actor":   action.get("target", ""),
            })

        if t == "attack":
            self._send("command_character_set_ai_state", {"character_name": actor_name, "state": "in_combat"})
            return {"status": "accepted", "action": "attack"}

        if t == "flee":
            self._send("command_character_set_ai_state", {"character_name": actor_name, "state": "fleeing"})
            return {"status": "accepted", "action": "flee"}

        if t == "remember":
            return {"status": "accepted", "action": "remember"}

        logger.warning(f"Unknown action type: {t}")
        return {"status": "error", "error": f"Unknown action: {t}"}

    def capture_observation(self, agent_id: str, actor_name: str, agents_dir: Path) -> dict:
        """Capture a camera image into <agents_dir>/<agent_id>/observations/."""
        obs_dir = agents_dir / agent_id / "observations"
        obs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_path = obs_dir / f"observation_{timestamp}.png"
        return self._send("capture_camera_image", {
            "actor_name": actor_name,
            "file_path":  str(file_path),
        })
