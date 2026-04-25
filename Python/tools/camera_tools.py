"""
Camera Capture Tools for Unreal MCP.

Provides tools for triggering scene captures via ACameraCaptureActor.
The actor must be placed in the level and the map must be running (PIE).
"""

import logging
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_camera_tools(mcp: FastMCP):
    """Register camera capture tools with the MCP server."""

    @mcp.tool()
    def capture_camera_image(
        ctx: Context,
        actor_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger a CameraCaptureActor to take a screenshot and save it to disk.

        The map must be running in PIE (Play In Editor) for the scene capture to work.
        Images are saved as <ActorName>_<YYYYMMDD>_<HHMMSS>.png in the project folder,
        so each capture gets a unique timestamped file.

        Args:
            actor_name: Exact name of the CameraCaptureActor in the level.
                        If omitted, the first CameraCaptureActor found is used.

        Returns:
            success, actor_name, file_path of the saved image.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Failed to connect to Unreal Engine"}
            params: Dict[str, Any] = {}
            if actor_name is not None:
                params["actor_name"] = actor_name
            response = unreal.send_command("capture_camera_image", params)
            return response or {}
        except Exception as e:
            logger.error(f"capture_camera_image error: {e}")
            return {"success": False, "message": str(e)}

    logger.info("Camera tools registered successfully")
