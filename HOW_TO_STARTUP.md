# How to start and reset the Unreal simulation

Use this checklist for the next clean visual-memory run. Unreal Engine must be **5.5.4**, exactly one
Unreal Editor process may be open, and PIE must host the TCP bridge before the cockpit can control the
simulation.

## 1. Recover from “Cannot connect to Unreal”

The cockpit and Python runner can be online while Unreal's bridge is offline. A cockpit message such as
“Unreal not running” means the runner could not connect to `127.0.0.1:55557`; it does not necessarily
mean the Unreal Editor process is absent.

If the Unreal log contains:

```text
UnrealMCPBridge: Failed to bind listener socket to 127.0.0.1:55557
```

restarting PIE is not enough. The bridge starts when the editor subsystem initializes and does not retry
the failed bind.

1. Stop PIE.
2. Close Unreal Editor completely.
3. Run `Python\stop_sim.bat`.
4. Open Task Manager and confirm that no `UnrealEditor.exe` process remains.
5. Reopen `MCPGameProject\MCPGameProject.uproject`.
6. Press **Play** to start PIE.
7. Run `Python\start_sim.bat`.
8. Wait for the cockpit to open and report that the runner is online.

The successful Unreal log line is:

```text
UnrealMCPBridge: Server started on 127.0.0.1:55557
```

Do not open a second Unreal Editor instance. Only one process can own port `55557`.

## 2. Decide whether this is a clean run or a continuation

For a **clean acceptance run**, follow all cleanup steps below. This deletes learned agent state and all
durable place visual memories so the four-view capture behavior can be tested from the beginning.

For a **continuation**, press **Restart day** only. Do not press **Reset places** if the existing place
images and visual history should survive.

## 3. Confirm or capture APC starting positions

If the APCs were moved in the editor:

1. Make sure PIE is active and the simulation status in the cockpit is **idle**.
2. Put each APC at its intended wake position.
3. Press **Capture starts**.
4. Confirm that the expected APC names were captured.

Do this before **Reset agents**. Otherwise the APCs can teleport to their older stored start positions.

## 4. Clean-run cockpit button order

First press **Stop** and confirm the cockpit status is **idle**. Then press:

1. **Reset places**
   - Deletes shared PlaceDB geography, descriptions, visits, place-image IDs, shared composite files,
     and per-APC `observations/place_history` links.
   - Does not delete Unreal `Landmark_*` actors or `places.json`; authored places reapply on the next
     simulation start.
2. **Reset agents**
   - Teleports APCs to their captured start positions.
   - Clears learned memories, episodes, daily schedules, runtime state, and spatial maps.
   - Does not delete captured start positions.
3. **Clear feed**
   - Clears the decision log only.

### Optional legacy-image cleanup

No cockpit button currently removes old ordinary SR-tagged observation screenshots. For a completely
uncluttered inspection run, keep the simulation stopped and delete the contents—not the APC definitions—
of:

```text
Python\worlds\MCP_World\agents\dufus\observations
Python\worlds\MCP_World\agents\maren\observations
```

The runtime recreates these directories. Each APC's stale `last_perception.json` may also be deleted; it
will be replaced after the next perception. Do not delete the APC directory, `state.json`, character
profile, goals, or `memory.seed.json`.

## 5. Start the clean visual-memory run

1. In the cockpit, set **Mode** to `live`.
2. Set **Tick seconds** to `10` for an easy-to-observe acceptance run.
3. Press **Start** once.
4. Do not press **Step** while the simulation is running.

Expected behavior at a place with no saved visual memory:

1. The APC turns through four absolute views: north, south, east, and west.
2. The VLM produces the scene text during that survey.
3. A single 2×2 composite is created with large white N/S/E/W headings on black. Its logical
   `GRID X: <col>  Y: <row>` label appears between N and S so VLM descriptions can state which grid
   the place history came from; precise world coordinates are not drawn over the scene.
4. The APC's inspectable copy/link appears at:

```text
Python\worlds\MCP_World\agents\<apc>\observations\place_history\<place_image_id>.png
```

5. The shared original appears under:

```text
Python\worlds\MCP_World\places\images
```

After the survey, a settled APC should reuse the saved textual description and stop routine place VLM
observation. Manual pulses, schedule or movement changes, blockers, stuck state, and nearby-APC events
remain valid separate cognition triggers.

## 6. What each reset control preserves

| Control | Preserves | Deletes or resets |
| --- | --- | --- |
| **Restart day** | Memories, PlaceDB, place images, visual history | Clock/day schedule runtime |
| **Reset agents** | PlaceDB, place images, visual-history DB links, captured starts | Learned memories, episodes, spatial maps, schedules; teleports APCs |
| **Reset places** | Authored landmarks and `places.json`, APC files | PlaceDB geography, visits, image records, shared composites, APC `place_history` links |
| **Clear feed** | All simulation state | Decision-feed log only |
| **Capture starts** | All state | Replaces stored APC reset/start transforms |

## 7. Stop after verification

Press **Stop** after the place-history composites and settled-agent behavior have been inspected. Use
`Python\stop_sim.bat` when the runner and cockpit processes should also be closed; it intentionally does
not stop Unreal PIE.

## 8. Align the logical grid when setting up a world

Grid alignment is a one-time world-authoring decision, not a normal run/reset step. Do it after the
world bounds and registered top-down map image are correct, but before investing in learned place cells
or place-history images.

1. Start Unreal PIE, the runner, and the cockpit, then open **Map** for the intended world.
2. Confirm the top-down image is registered to world coordinates. Hover known landmarks and compare the
   cursor's world-coordinate readout with their Unreal transforms. Grid alignment cannot repair a
   misregistered background image.
3. Stop the simulation. Open **Align grid**, enter candidate X/Y logical origins, and press **Preview**.
   Preview is non-destructive: it hides old place overlays and moves only the empty lattice.
4. Adjust by less than one cell size (3000 cm by default). Only the offset modulo the cell size matters.
   Use roads and meaningful clusters as the guide: keep a road corridor near a useful cell center and
   avoid splitting one authored place, its extent, or a group that should share a district across an
   edge. For MCP_World the accepted alignment is X `0`, Y `650` cm.
5. Press **Apply regrid** only after inspecting the whole map and accepting the confirmation. Apply
   stops the simulation and permanently clears grid-keyed derived data: PlaceDB cells and observations,
   place-image records/files and visual-history links, agent spatial maps, route-map images, cached
   routes, and in-progress sweeps. It preserves world/image bounds, map calibration, authored world
   positions, APC captured starts, schedules, and ordinary memories.
6. Press **Sync world** after the regrid to rescan `Landmark_*` actors and reapply `places.json` using the
   new grid keys. Verify authored place markers and extents now fall in their intended cells.
7. If APC actors were moved independently, stop the sim and use **Capture starts** afterward. Capture
   starts records current APC transforms; it does not align the grid. Make sure every bound APC is at
   its intended wake position because the button captures all of them.
8. Start a fresh run and let APCs rebuild community surveys and place images under the new alignment.

Do not repeatedly reapply the same alignment between runs. Once accepted, `origin_x` and `origin_y` are
persisted in `Python/worlds/<world>/world_grid.json` and normal **Restart day** runs reuse them.
