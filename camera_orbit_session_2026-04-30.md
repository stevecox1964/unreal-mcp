# Camera Orbit Session — 2026-04-30

Quick reference for orbiting the `CameraCaptureActor` around a target actor in the running PIE level and reading captures back.

## Scene state at session start

- **CameraCaptureActor** (`CameraCaptureActor_UAID_00155D038691F4D402_1371610311`) at `[-560, -50, 110]`, yaw `~140°` — already pointed roughly at the cube.
- **Rainbow cube** (`StaticMeshActor_UAID_00155D03869155D402_1794492329`) at `[-1260, 720, 50]` — vertical-stripe rainbow material on a unit cube.
- **Floor** (`StaticMeshActor_UAID_A4AE111137DC54FB00_1240666663`) at origin, scale `[400, 400, 400]` — brown tiled plane.
- **Player character** (`BP_PlayerCharacter_C_...`) at `[50, -210, 50]` — visible as a small white shape from the west view.
- Map is **landscape-based** (LandscapeStreamingProxy tiles), with SkyAtmosphere + VolumetricCloud + DirectionalLight.

## Tools used

| Tool | Purpose |
|------|---------|
| `mcp__unrealMCP__get_actors_in_level` | Enumerate actors to find the cube |
| `mcp__unrealMCP__get_actor_properties` | Read camera location/rotation |
| `mcp__unrealMCP__set_actor_transform` | Move + rotate camera |
| `mcp__unrealMCP__capture_camera_image` | Trigger capture (PIE must be running) |
| `Read` (on saved PNG) | View the resulting image |

`find_actors_by_name` returned no output for `*Cube*` / `*ainbow*` — actor name is just `StaticMeshActor_UAID_...`, so glob on the *display* name doesn't help. Fall back to `get_actors_in_level` and pick by location/scale.

## Coordinate conventions confirmed

- Unreal axes: **+X = North, +Y = East, +Z = Up**.
- Yaw 0° looks toward +X. Yaw 90° looks toward +Y. Yaw 180° toward -X. Yaw -90° (or 270°) toward -Y.
- "Move 200 units north" = add 200 to X.
- To aim camera at target `(tx, ty)` from `(cx, cy)`: `yaw = atan2(ty-cy, tx-cx)` in degrees.

## The orbit pattern

Cube center `(-1260, 720)`. Radius 900u, camera Z = 110, pitch/roll = 0.

| # | Position | Camera location | Yaw | What was distinctive |
|---|----------|-----------------|-----|----------------------|
| 1 | East  | `[-360, 720, 110]`   | `180°` | Sun visible top-right, shadow left |
| 2 | North | `[-1260, 1620, 110]` | `-90°` | Shadow forward-left |
| 3 | West  | `[-2160, 720, 110]`  | `0°`   | Player character visible mid-distance left |
| 4 | South | `[-1260, -180, 110]` | `90°`  | Shadow left, mountains wrap horizon |

At every stop the cube stays centered because the yaw is computed to point at it. The shadow direction rotates predictably as you orbit, confirming the directional light is fixed.

## Recipe to replicate

```
1. Find target actor location via get_actors_in_level.
2. Pick radius R and camera height Z.
3. For each angle θ (0°, 90°, 180°, 270° for cardinal orbit):
     cam_x  = target_x + R * cos(θ)
     cam_y  = target_y + R * sin(θ)
     cam_yaw = θ + 180°   (yaw to look back at target)
4. set_actor_transform(camera, location=[cam_x, cam_y, Z], rotation=[0, cam_yaw, 0])
5. capture_camera_image()
6. Read the returned file_path to inspect.
```

## Gotchas

- **PIE must be running** for `capture_camera_image` to produce a real frame — without PIE the scene capture pipeline doesn't tick.
- Captures are saved as `<ActorName>_<YYYYMMDD>_<HHMMSS>.png` in the project folder (`MCPGameProject/`), so each shot gets a unique timestamped file — no overwrites.
- `find_actors_by_name` matches the internal actor name (`StaticMeshActor_UAID_...`), not the editor display label. For "find the cube" type tasks, list everything and filter by location/class/scale instead.
- Yaw values can come back with floating-point fuzz (e.g. `89.99999...`). Treat as the rounded value.

## Final camera state

`location=[-1260, -180, 110]`, `rotation=[0, 90, 0]` — south of cube, looking north.
