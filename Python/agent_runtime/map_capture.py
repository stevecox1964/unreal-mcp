"""World-map capture from the MAP_Camera pawn (#18) — pose math + bridge flow.

The engine capture is fixed by CameraCaptureActor::CaptureCameraViewToFile:
1920x1080 render target and the fresh SceneCaptureComponent2D's default
90-degree *horizontal* FOV. A straight-down camera at height h therefore
frames exactly (2h x 2h*ASPECT) cm of ground centered under it — the pose IS
the registration; ``image_bounds`` is computed, never hand-measured.

``camera_pose_for_bounds`` is the single source of that math (the web UI's
/api/map/capture imports it); ``capture_world_map`` is the bridge-side flow
used at grid registration time (AgentManager.generate_world_grid).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("AgentRuntime")

MAP_CAPTURE_ASPECT = 1080.0 / 1920.0
MAP_CAPTURE_MARGIN = 1.02          # slack so the world edge isn't at pixel 0
MAP_CAMERA_ACTOR = "MAP_Camera"    # the user-placed camera pawn (by label)
# [pitch, yaw, roll]: straight down, yawed so image up = -Y = north and
# image right = +X = east — the /map overlay's fixed convention (#6c).
MAP_CAMERA_ROTATION = [-90.0, -90.0, 0.0]


def camera_pose_for_bounds(bounds: dict) -> dict:
    """Top-down camera pose framing ``bounds``, and the world rect it sees.

    Pure math (offline-testable): center the camera over the bounds rect at
    the height whose 90-degree-FOV footprint covers both axes, then report
    that footprint as ``image_bounds`` — the exact rect the capture frames.
    """
    cx = (bounds["min_x"] + bounds["max_x"]) / 2.0
    cy = (bounds["min_y"] + bounds["max_y"]) / 2.0
    half_w = (bounds["max_x"] - bounds["min_x"]) / 2.0
    half_h = (bounds["max_y"] - bounds["min_y"]) / 2.0
    h = max(half_w, half_h / MAP_CAPTURE_ASPECT) * MAP_CAPTURE_MARGIN
    return {
        "location": [cx, cy, h],
        "rotation": list(MAP_CAMERA_ROTATION),
        "image_bounds": {
            "min_x": cx - h, "max_x": cx + h,
            "min_y": cy - h * MAP_CAPTURE_ASPECT, "max_y": cy + h * MAP_CAPTURE_ASPECT,
        },
    }


def capture_world_map(bridge, level: str, bounds: dict, grid_path: Path,
                      images_dir: Path, actor: str = MAP_CAMERA_ACTOR) -> dict:
    """Aim MAP_Camera over ``bounds``, capture ``images_dir/<level>.png``, and
    persist the footprint as ``image_bounds`` in ``grid_path``.

    Best-effort but honest: every failure is reported in the returned dict
    (``{"ok": False, "error": ...}``) and logged — never a silent skip. On
    success returns ``{"ok": True, "image": ..., "image_bounds": ...}``.
    """
    pose = camera_pose_for_bounds(bounds)
    moved = bridge.set_actor_transform(actor, pose["location"], pose["rotation"])
    if moved.get("status") != "success":
        err = f"could not position '{actor}': {moved.get('error', 'unknown')}"
        logger.warning(f"world-map capture skipped — {err}")
        return {"ok": False, "error": err}

    image_file = images_dir / f"{level}.png"
    shot = bridge.capture_camera_image(actor, str(image_file))
    if shot.get("status") != "success" or not shot.get("success"):
        err = f"capture failed on '{actor}': {shot.get('error', 'unknown')}"
        logger.warning(f"world-map capture skipped — {err}")
        return {"ok": False, "error": err}

    raw = json.loads(grid_path.read_text(encoding="utf-8"))
    raw["image_bounds"] = pose["image_bounds"]
    grid_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    logger.info(f"world map captured: {image_file} (registered to bounds)")
    return {"ok": True, "image": str(image_file), "image_bounds": pose["image_bounds"]}
