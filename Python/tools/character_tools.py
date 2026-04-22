"""
Character Tools for Unreal MCP.

Provides tools for querying character state and issuing commands to NPC characters.
Requires UMCPCharacterComponent to be attached to the target actor in Unreal.
"""

import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_character_tools(mcp: FastMCP):
    """Register character tools with the MCP server."""

    # -----------------------------------------------------------------------
    # Info / Query
    # -----------------------------------------------------------------------

    @mcp.tool()
    def get_character_status(ctx: Context, character_name: str) -> Dict[str, Any]:
        """Get full status of a character: location, AI state, health, current action, message queue sizes.

        Args:
            character_name: Exact name of the actor in the level
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_character_status", {"character_name": character_name})
            return response or {}
        except Exception as e:
            logger.error(f"get_character_status error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_character_location(ctx: Context, character_name: str) -> Dict[str, Any]:
        """Get the world location and rotation of a character.

        Args:
            character_name: Exact name of the actor in the level
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_character_location", {"character_name": character_name})
            return response or {}
        except Exception as e:
            logger.error(f"get_character_location error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_character_health(ctx: Context, character_name: str) -> Dict[str, Any]:
        """Get the health value of a character (requires MCPCharacterComponent).

        Args:
            character_name: Exact name of the actor in the level
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_character_health", {"character_name": character_name})
            return response or {}
        except Exception as e:
            logger.error(f"get_character_health error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_character_inventory(ctx: Context, character_name: str) -> Dict[str, Any]:
        """Get the list of items currently carried by a character.

        Args:
            character_name: Exact name of the actor in the level
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_character_inventory", {"character_name": character_name})
            return response or {}
        except Exception as e:
            logger.error(f"get_character_inventory error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_character_current_action(ctx: Context, character_name: str) -> Dict[str, Any]:
        """Get what a character is currently doing (current_action and ai_state).

        Args:
            character_name: Exact name of the actor in the level
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_character_current_action", {"character_name": character_name})
            return response or {}
        except Exception as e:
            logger.error(f"get_character_current_action error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_character_view(ctx: Context, character_name: str) -> Dict[str, Any]:
        """[STUB] Get what the character can see. Will be wired to the camera screenshot component.

        Args:
            character_name: Exact name of the actor in the level
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_character_view", {"character_name": character_name})
            return response or {}
        except Exception as e:
            logger.error(f"get_character_view error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_nearby_actors(
        ctx: Context,
        character_name: str,
        radius: float = 500.0
    ) -> Dict[str, Any]:
        """Get all actors within a radius of the character.

        Args:
            character_name: Exact name of the actor in the level
            radius: Search radius in Unreal units (default 500)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_nearby_actors", {
                "character_name": character_name,
                "radius": radius
            })
            return response or {}
        except Exception as e:
            logger.error(f"get_nearby_actors error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_heard_sounds(ctx: Context, character_name: str) -> Dict[str, Any]:
        """[STUB] Get recent sounds perceived by the character (requires UAIPerceptionComponent).

        Args:
            character_name: Exact name of the actor in the level
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_heard_sounds", {"character_name": character_name})
            return response or {}
        except Exception as e:
            logger.error(f"get_heard_sounds error: {e}")
            return {"success": False, "message": str(e)}

    # -----------------------------------------------------------------------
    # Messaging / Memory
    # -----------------------------------------------------------------------

    @mcp.tool()
    def send_character_message(
        ctx: Context,
        character_name: str,
        message: str
    ) -> Dict[str, Any]:
        """Send a message to a character's inbox. Fires OnMessageReceived in the NPC Blueprint.

        Args:
            character_name: Exact name of the actor in the level
            message: The message string to deliver
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("send_character_message", {
                "character_name": character_name,
                "message": message
            })
            return response or {}
        except Exception as e:
            logger.error(f"send_character_message error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_character_messages(
        ctx: Context,
        character_name: str,
        source: str = "outbox",
        clear: bool = False
    ) -> Dict[str, Any]:
        """Read messages from a character's outbox (or inbox).

        Args:
            character_name: Exact name of the actor in the level
            source: "outbox" (default) or "inbox"
            clear: If True, empties the queue after reading
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("get_character_messages", {
                "character_name": character_name,
                "source": source,
                "clear": clear
            })
            return response or {}
        except Exception as e:
            logger.error(f"get_character_messages error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_character_memory(
        ctx: Context,
        character_name: str,
        key: str,
        value: str
    ) -> Dict[str, Any]:
        """Write a key-value fact into a character's memory store.

        Args:
            character_name: Exact name of the actor in the level
            key: Memory key (e.g. "last_seen_player_location")
            value: Memory value (stored as string)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("set_character_memory", {
                "character_name": character_name,
                "key": key,
                "value": value
            })
            return response or {}
        except Exception as e:
            logger.error(f"set_character_memory error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_character_memory(
        ctx: Context,
        character_name: str,
        key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Read from a character's memory store. Pass a key for a single lookup, or omit for all.

        Args:
            character_name: Exact name of the actor in the level
            key: Optional specific key to read; omit to return the full memory map
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            params: Dict[str, Any] = {"character_name": character_name}
            if key is not None:
                params["key"] = key
            response = unreal.send_command("get_character_memory", params)
            return response or {}
        except Exception as e:
            logger.error(f"get_character_memory error: {e}")
            return {"success": False, "message": str(e)}

    # -----------------------------------------------------------------------
    # Action Commands
    # -----------------------------------------------------------------------

    @mcp.tool()
    def command_character_move_to(
        ctx: Context,
        character_name: str,
        location: Optional[List[float]] = None,
        target_actor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Command a character to walk to a world location or another actor.
        Provide either location [x, y, z] or target_actor name.

        Args:
            character_name: Exact name of the character actor
            location: [x, y, z] destination in world space
            target_actor: Name of the actor to walk to
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            params: Dict[str, Any] = {"character_name": character_name}
            if location is not None:
                params["location"] = [float(v) for v in location]
            if target_actor is not None:
                params["target_actor"] = target_actor
            response = unreal.send_command("command_character_move_to", params)
            return response or {}
        except Exception as e:
            logger.error(f"command_character_move_to error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_follow(
        ctx: Context,
        character_name: str,
        target_actor: str
    ) -> Dict[str, Any]:
        """Command a character to follow another actor.

        Args:
            character_name: Exact name of the character actor
            target_actor: Name of the actor to follow
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("command_character_follow", {
                "character_name": character_name,
                "target_actor": target_actor
            })
            return response or {}
        except Exception as e:
            logger.error(f"command_character_follow error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_stop(ctx: Context, character_name: str) -> Dict[str, Any]:
        """Stop a character's current movement immediately.

        Args:
            character_name: Exact name of the character actor
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("command_character_stop", {"character_name": character_name})
            return response or {}
        except Exception as e:
            logger.error(f"command_character_stop error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_look_at(
        ctx: Context,
        character_name: str,
        location: Optional[List[float]] = None,
        target_actor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Rotate a character to face a location or actor.
        Provide either location [x, y, z] or target_actor name.

        Args:
            character_name: Exact name of the character actor
            location: [x, y, z] world position to face
            target_actor: Name of the actor to face
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            params: Dict[str, Any] = {"character_name": character_name}
            if location is not None:
                params["location"] = [float(v) for v in location]
            if target_actor is not None:
                params["target_actor"] = target_actor
            response = unreal.send_command("command_character_look_at", params)
            return response or {}
        except Exception as e:
            logger.error(f"command_character_look_at error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_pickup(
        ctx: Context,
        character_name: str,
        item_name: str,
        socket: str = "hand_r"
    ) -> Dict[str, Any]:
        """Command a character to pick up an actor, attaching it to a mesh socket.

        Args:
            character_name: Exact name of the character actor
            item_name: Exact name of the actor to pick up
            socket: Skeletal mesh socket to attach to (default "hand_r")
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("command_character_pickup", {
                "character_name": character_name,
                "item_name": item_name,
                "socket": socket
            })
            return response or {}
        except Exception as e:
            logger.error(f"command_character_pickup error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_drop(
        ctx: Context,
        character_name: str,
        item_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Command a character to drop a carried item, or all items if item_name is omitted.

        Args:
            character_name: Exact name of the character actor
            item_name: Name of specific item to drop; omit to drop everything
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            params: Dict[str, Any] = {"character_name": character_name}
            if item_name is not None:
                params["item_name"] = item_name
            response = unreal.send_command("command_character_drop", params)
            return response or {}
        except Exception as e:
            logger.error(f"command_character_drop error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_interact(
        ctx: Context,
        character_name: str,
        target_actor: str = ""
    ) -> Dict[str, Any]:
        """[STUB] Command a character to interact with a nearby object.
        Fires OnInteractRequested in the NPC Blueprint — implement the logic there.

        Args:
            character_name: Exact name of the character actor
            target_actor: Name of the actor to interact with
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("command_character_interact", {
                "character_name": character_name,
                "target_actor": target_actor
            })
            return response or {}
        except Exception as e:
            logger.error(f"command_character_interact error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_play_animation(
        ctx: Context,
        character_name: str,
        montage_path: str,
        play_rate: float = 1.0
    ) -> Dict[str, Any]:
        """Play an AnimMontage on a character by its full asset path.

        Args:
            character_name: Exact name of the character actor
            montage_path: Full Unreal asset path, e.g. "/Game/Animations/AM_Wave"
            play_rate: Playback speed multiplier (default 1.0)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("command_character_play_animation", {
                "character_name": character_name,
                "montage_path": montage_path,
                "play_rate": play_rate
            })
            return response or {}
        except Exception as e:
            logger.error(f"command_character_play_animation error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_say(
        ctx: Context,
        character_name: str,
        text: str
    ) -> Dict[str, Any]:
        """Make a character say something. Sets CurrentDialogue, adds to outbox,
        and fires OnSayRequested in the NPC Blueprint for driving your dialogue UI.

        Args:
            character_name: Exact name of the character actor
            text: The line of dialogue to speak
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("command_character_say", {
                "character_name": character_name,
                "text": text
            })
            return response or {}
        except Exception as e:
            logger.error(f"command_character_say error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def command_character_set_ai_state(
        ctx: Context,
        character_name: str,
        state: str
    ) -> Dict[str, Any]:
        """Override a character's AI state label and fire OnAIStateChanged in Blueprint.
        Valid states: idle, moving, in_combat, interacting, following, fleeing.

        Args:
            character_name: Exact name of the character actor
            state: New AI state string
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("command_character_set_ai_state", {
                "character_name": character_name,
                "state": state
            })
            return response or {}
        except Exception as e:
            logger.error(f"command_character_set_ai_state error: {e}")
            return {"success": False, "message": str(e)}

    logger.info("Character tools registered successfully")
