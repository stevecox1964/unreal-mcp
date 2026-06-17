from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("AgentRuntime")


def _xyz_list(loc) -> list[float]:
    """Coerce a location ({x,y,z} dict or [x,y,z] sequence) to an [x, y, z] list."""
    if isinstance(loc, dict):
        return [float(loc.get("x", 0)), float(loc.get("y", 0)), float(loc.get("z", 0))]
    if isinstance(loc, (list, tuple)):
        vals = [float(v) for v in loc[:3]]
        return vals + [0.0] * (3 - len(vals))
    return [0.0, 0.0, 0.0]


class UnrealBridge:
    """
    Thin wrapper around UnrealConnection.send_command that exposes
    high-level methods the AgentManager and ActionValidator can call.

    Deliberately synchronous â€” matches the existing send_command API.
    All socket calls reconnect per-command (Unreal closes after each).
    """

    def __init__(self) -> None:
        # Keyed by agent_id â€” used by is_scene_changed for the visual diff gate.
        self._last_image_hashes: dict[str, str] = {}

    def _send(self, command: str, params: dict) -> dict:
        from unreal_sim_server import get_unreal_connection
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

    # â”€â”€ Level info â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_current_level(self) -> str:
        """Return the short name of the currently loaded level, or '' on failure."""
        result = self._send("get_current_level_name", {})
        return result.get("name", "")

    def get_level_actors(self) -> list[dict]:
        """All actors in the current level (editor command â€” run outside PIE)."""
        result = self._send("get_actors_in_level", {})
        return result.get("actors") or []

    # â”€â”€ Actor binding â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    def line_trace_forward(self, actor_name: str, distance_cm: float = 300.0) -> dict:
        """Fire a forward line trace from the actor's eye position.

        Returns raw engine data only â€” semantic classification belongs in the caller.
        Result: {'hit': bool, 'actor_name': str, 'actor_class': str, 'distance_cm': float}
        or {'hit': False} when nothing is struck within distance_cm.
        """
        return self._send("get_character_forward_trace", {
            "character_name": actor_name,
            "distance_cm": distance_cm,
        })

    def get_character_transform(self, actor_name: str) -> dict:
        """Return {'location': {x,y,z}, 'rotation': {x:pitch, y:yaw, z:roll}} or empty values."""
        result = self._send("get_character_location", {"character_name": actor_name})
        return {"location": result.get("location"), "rotation": result.get("rotation")}

    def teleport(self, actor_name: str, location, rotation=None) -> dict:
        """Instantly move a character (PIE world) â€” used by reset_agents, not by NPC actions."""
        params: dict[str, Any] = {
            "character_name": actor_name,
            "location": _xyz_list(location),
        }
        if rotation is not None:
            params["rotation"] = _xyz_list(rotation)  # [pitch, yaw, roll]
        return self._send("command_character_teleport", params)

    def _blueprint_asset_name(self, blueprint_class: str) -> str:
        """Convert /Game/Blueprints/BP_Name.BP_Name_C to BP_Name for this plugin."""
        name = blueprint_class.rsplit("/", 1)[-1]
        name = name.split(".", 1)[0]
        if name.endswith("_C"):
            name = name[:-2]
        return name

    # â”€â”€ Observation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_observation(self, actor_name: str, agent_id: str, agents_dir: Path) -> dict:
        """Capture a screenshot and gather minimal engine state for one agent.

        Vision is the primary observation channel â€” the NPC sees what its
        camera sees. Engine queries are kept to the minimum needed for movement
        planning (own location) and action continuity (current_action).
        """
        obs_dir = agents_dir / agent_id / "observations"
        obs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        image_file = obs_dir / f"observation_{timestamp}.png"
        capture = self._send("capture_camera_image", {
            "actor_name": actor_name,
            "file_path":  str(image_file),
        })
        image_path = str(image_file) if capture.get("success") else None

        location = self._send("get_character_location",       {"character_name": actor_name})
        action   = self._send("get_character_current_action", {"character_name": actor_name})
        return {
            "actor_name":     actor_name,
            "image_path":     image_path,
            "location":       location.get("location"),
            "rotation":       location.get("rotation"),
            "current_action": action.get("current_action"),
            "ai_state":       action.get("ai_state"),
        }

    def set_facing(self, actor_name: str, location, yaw: float) -> dict:
        """Turn a character in place to face the given world yaw (degrees)."""
        return self._send("command_character_teleport", {
            "character_name": actor_name,
            "location": _xyz_list(location),
            "rotation": [0.0, float(yaw), 0.0],  # [pitch, yaw, roll]
        })

    def capture_view(self, actor_name: str, agent_id: str, agents_dir: Path, tag: str) -> str | None:
        """Capture one camera image tagged by purpose; returns the path or None."""
        obs_dir = agents_dir / agent_id / "observations"
        obs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        image_file = obs_dir / f"observation_{timestamp}_{tag}.png"
        capture = self._send("capture_camera_image", {
            "actor_name": actor_name,
            "file_path":  str(image_file),
        })
        return str(image_file) if capture.get("success") else None

    def clear_scene_cache(self) -> None:
        """Forget last-seen image hashes so the next tick always perceives."""
        self._last_image_hashes.clear()

    def is_scene_changed(self, agent_id: str, image_path: str) -> bool:
        """Return True if the scene has changed enough to warrant an LLM call.

        Uses a perceptual average-hash diff on the captured screenshot.
        On first tick, PIL unavailable, or capture failure â€” always returns True.
        Threshold: 8 differing bits out of 64 (~87% similarity).
        """
        if not image_path:
            return True
        new_hash = self._image_hash(image_path)
        if not new_hash:
            return True
        last_hash = self._last_image_hashes.get(agent_id)
        self._last_image_hashes[agent_id] = new_hash
        if not last_hash:
            return True
        return self._hamming(last_hash, new_hash) > 8

    def _image_hash(self, image_path: str) -> str | None:
        """8Ã—8 average-hash of an image â†’ 16-char hex string, or None on failure."""
        try:
            from PIL import Image  # optional dependency
            img = Image.open(image_path).convert("L").resize((8, 8), Image.LANCZOS)
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if p >= avg else "0" for p in pixels)
            return format(int(bits, 2), "016x")
        except ImportError:
            logger.debug("Pillow not installed â€” visual diff gate disabled")
            return None
        except Exception as e:
            logger.debug(f"Image hash failed for {image_path}: {e}")
            return None

    @staticmethod
    def _hamming(a: str, b: str) -> int:
        return bin(int(a, 16) ^ int(b, 16)).count("1")

    # â”€â”€ Action execution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def execute_action(self, actor_name: str, action: dict) -> dict:
        t = action.get("type", "idle")

        if t == "idle":
            return {"status": "accepted", "action": "idle"}

        if t == "walk_to":
            params: dict[str, Any] = {"character_name": actor_name}
            if action.get("target_actor"):
                params["target_actor"] = action["target_actor"]
            elif action.get("location"):
                # The C++ move handler expects location as an [x, y, z] array.
                # The LLM (and explorer) hand us a {"x","y","z"} dict â€” coerce it,
                # or moves silently default to world origin (0,0,0).
                params["location"] = _xyz_list(action["location"])
            elif action.get("target_location"):
                # LLM sometimes uses target_location as a string label
                # Best effort: log and idle â€” real location resolution needs world-state lookup
                logger.warning(f"walk_to with string target_location '{action['target_location']}' â€” idling")
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

    def print_to_screen(self, message: str, key: int = -1, duration: float = 30.0) -> None:
        """Display a debug message in the PIE viewport (key-based replacement)."""
        self._send("print_to_screen", {"message": message, "key": key, "duration": duration})

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
