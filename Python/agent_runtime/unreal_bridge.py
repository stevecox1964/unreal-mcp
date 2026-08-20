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
        # Current sim run tag (SR<n>), set by AgentManager at run start; prefixes
        # every observation screenshot so captures are attributable to one run.
        self.sim_run_id: str = "SR0"

    def _send(self, command: str, params: dict) -> dict:
        from .unreal_connection import get_unreal_connection
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

    def forward_volume(self, actor_name: str, distance_cm: float = 500.0,
                       yaw_offset_deg: float = 0.0) -> dict:
        """Sweep the character's own body forward and raster its frontal area (#81).

        Answers two questions the single ray could not: whether the BODY fits
        (capsule sweep on ECC_Pawn, the channel that actually stops movement) and
        WHERE the gap is (a 5x3 ray raster, left-to-right and bottom-to-top).
        Raw engine data only — semantic classification belongs in the caller.

        Result: {'fits', 'clearance_cm', 'open_columns', 'blocked_columns',
                 'open_rows', 'cells', 'blocked_fraction', 'nearest_cm',
                 'fully_blocked', 'hit', 'contact': {...}}
        """
        return self._send("get_character_forward_volume", {
            "character_name": actor_name,
            "distance_cm": distance_cm,
            "yaw_offset_deg": yaw_offset_deg,
        })

    def get_character_transform(self, actor_name: str) -> dict:
        """Return {'location': {x,y,z}, 'rotation': {x:pitch, y:yaw, z:roll}} or empty values."""
        result = self._send("get_character_location", {"character_name": actor_name})
        return {"location": result.get("location"), "rotation": result.get("rotation")}

    def set_actor_transform(self, actor_name: str, location=None, rotation=None) -> dict:
        """Move/rotate a level actor (editor world). ``rotation`` is [pitch, yaw, roll].

        Unlike ``teleport`` (a PIE character command) this drives any placed
        actor — used to aim the MAP_Camera pawn for world-map captures (#18).
        """
        params: dict[str, Any] = {"name": actor_name}
        if location is not None:
            params["location"] = _xyz_list(location)
        if rotation is not None:
            params["rotation"] = _xyz_list(rotation)
        return self._send("set_actor_transform", params)

    def capture_camera_image(self, actor_name: str, file_path: str) -> dict:
        """Capture a CameraCaptureActor's view to ``file_path`` (PNG, 1920x1080).

        ``actor_name`` may be the capture actor itself or an actor with one
        attached — the engine handler resolves both.
        """
        return self._send("capture_camera_image", {
            "actor_name": actor_name,
            "file_path": file_path,
        })

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

    def get_character_state(self, actor_name: str) -> dict:
        """Gather cheap deterministic state without rendering a camera image."""
        location = self._send("get_character_location", {"character_name": actor_name})
        action = self._send("get_character_current_action", {"character_name": actor_name})
        return {
            "actor_name": actor_name,
            "location": location.get("location"),
            "rotation": location.get("rotation"),
            "current_action": action.get("current_action"),
            "ai_state": action.get("ai_state"),
        }

    def capture_routine_observation(self, actor_name: str, agent_id: str,
                                    agents_dir: Path, state: dict = None) -> dict:
        """Capture one routine camera image and attach already-sampled state."""
        observation = dict(state or self.get_character_state(actor_name))

        obs_dir = agents_dir / agent_id / "observations"
        obs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        image_file = obs_dir / f"{self.sim_run_id}_observation_{timestamp}.png"
        capture = self._send("capture_camera_image", {
            "actor_name": actor_name,
            "file_path":  str(image_file),
        })
        observation["image_path"] = str(image_file) if capture.get("success") else None
        return observation

    def get_observation(self, actor_name: str, agent_id: str, agents_dir: Path) -> dict:
        """Capture a screenshot and gather minimal engine state for one agent.

        Callers that can suppress vision from deterministic state should use
        ``get_character_state`` first, then ``capture_routine_observation`` only
        when an event actually requires visual cognition.
        """
        state = self.get_character_state(actor_name)
        return self.capture_routine_observation(actor_name, agent_id, agents_dir, state)

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
        image_file = obs_dir / f"{self.sim_run_id}_observation_{timestamp}_{tag}.png"
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

    def set_ai_state(self, actor_name: str, state: str) -> dict:
        """Set the character's AIState label and fire OnAIStateChanged in Blueprint.

        Drives the above-head status bubble. Single-socket, so call only from the
        sequential tick phases — never from the parallel perceive+decide phase.
        """
        return self._send("command_character_set_ai_state", {"character_name": actor_name, "state": state})

    def capture_observation(self, agent_id: str, actor_name: str, agents_dir: Path) -> dict:
        """Capture a camera image into <agents_dir>/<agent_id>/observations/."""
        obs_dir = agents_dir / agent_id / "observations"
        obs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_path = obs_dir / f"{self.sim_run_id}_observation_{timestamp}.png"
        return self._send("capture_camera_image", {
            "actor_name": actor_name,
            "file_path":  str(file_path),
        })
