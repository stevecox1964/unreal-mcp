"""
Actor Attachment Tools for Unreal MCP.

Generic primitives for parenting one actor to another in the Unreal scene
graph, optionally snapping to a named socket on the parent's SkeletalMesh.
Use cases include mounting a CameraCaptureActor to a character's head,
attaching a weapon to a hand socket, parenting a prop to a vehicle, etc.
"""

import logging
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_attachment_tools(mcp: FastMCP):
    """Register actor attachment tools with the MCP server."""

    @mcp.tool()
    def attach_actor_to_actor(
        ctx: Context,
        child_actor: str,
        parent_actor: str,
        socket: Optional[str] = None,
        weld_simulated_bodies: bool = True
    ) -> Dict[str, Any]:
        """Attach one actor to another in the Unreal scene graph.

        Uses SnapToTarget rules so the child inherits the parent's location
        and rotation each frame. If `socket` is provided and the parent is a
        Character whose SkeletalMesh has a matching socket/bone, the child
        snaps to that socket; otherwise it attaches to the parent's root.

        Common usages:
          - Mount a CameraCaptureActor to an NPC's head:
              attach_actor_to_actor("CameraCaptureActor_1", "NPC_Bob", socket="head")
          - Put a weapon in a character's right hand:
              attach_actor_to_actor("Sword_1", "NPC_Bob", socket="hand_r")
          - Parent a prop to a vehicle's root:
              attach_actor_to_actor("Crate_1", "Truck_1")

        Args:
            child_actor: Exact name of the actor to attach.
            parent_actor: Exact name of the actor to attach to.
            socket: Optional socket/bone name on the parent's SkeletalMesh.
                    Falls back to root attach if missing or not found.
            weld_simulated_bodies: When the child has simulated physics, weld
                                   it to the parent's body (default true).

        Returns:
            success, child_actor, parent_actor, attached_to_socket, and
            either socket (when snapped to one) or note (when fallen back).
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            params: Dict[str, Any] = {
                "child_actor": child_actor,
                "parent_actor": parent_actor,
                "weld_simulated_bodies": weld_simulated_bodies,
            }
            if socket:
                params["socket"] = socket
            response = unreal.send_command("attach_actor_to_actor", params)
            return response or {}
        except Exception as e:
            logger.error(f"attach_actor_to_actor error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def detach_actor(
        ctx: Context,
        actor_name: str
    ) -> Dict[str, Any]:
        """Detach an actor from its current parent.

        Uses KeepWorld rules, so the actor stays at its current world
        position and rotation after detaching.

        Args:
            actor_name: Exact name of the actor to detach.

        Returns:
            success, actor_name.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            response = unreal.send_command("detach_actor", {"actor_name": actor_name})
            return response or {}
        except Exception as e:
            logger.error(f"detach_actor error: {e}")
            return {"success": False, "message": str(e)}

    logger.info("Attachment tools registered successfully")
