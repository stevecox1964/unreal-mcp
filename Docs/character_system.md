# Character Interaction System

Added 2026-04-22.

Extends the MCP plugin with a full NPC character command system — messaging, memory, status queries, and action commands (move, pickup, follow, say, etc.).

---

## Architecture

```
MCP Tool Call (Python)
  → character_tools.py  →  send_command("command_name", {params})
  → unreal_mcp_server.py  →  TCP socket to 127.0.0.1:55557
  → UnrealMCPBridge::ExecuteCommand()  →  routes to CharacterCommands
  → FUnrealMCPCharacterCommands::HandleCommand()
  → reads/writes UMCPCharacterComponent on the target Actor
```

---

## Files Added / Modified

| File | Type | Purpose |
|------|------|---------|
| `Public/MCPCharacterComponent.h` | New | `UActorComponent` — attach to any NPC Blueprint |
| `Private/MCPCharacterComponent.cpp` | New | Component constructor, default values |
| `Public/Commands/UnrealMCPCharacterCommands.h` | New | Handler class declaration |
| `Private/Commands/UnrealMCPCharacterCommands.cpp` | New | All 20 command implementations |
| `Python/tools/character_tools.py` | New | All 20 MCP Python tools |
| `UnrealMCP.Build.cs` | Modified | Added `AIModule`, `NavigationSystem` |
| `Public/UnrealMCPBridge.h` | Modified | Added include + `CharacterCommands` member |
| `Private/UnrealMCPBridge.cpp` | Modified | Constructor init, destructor reset, dispatch block |
| `Python/unreal_mcp_server.py` | Modified | Import + `register_character_tools(mcp)` |

---

## UMCPCharacterComponent

Add this component to any NPC Blueprint to enable all character commands.

### Properties (all `BlueprintReadWrite`)

| Property | Type | Description |
|----------|------|-------------|
| `Inbox` | `TArray<FString>` | Messages sent TO the character via `send_character_message` |
| `Outbox` | `TArray<FString>` | Messages FROM the character — read via `get_character_messages`, written by `command_character_say` |
| `Memory` | `TMap<FString,FString>` | Key-value fact store — read/write via `set/get_character_memory` |
| `AIState` | `FString` | Current AI state label: `idle`, `moving`, `in_combat`, `interacting`, `following`, `fleeing` |
| `CurrentAction` | `FString` | Human-readable description of what the character is doing |
| `Health` | `float` | Health value — set this from your damage system |
| `Inventory` | `TArray<FString>` | Names of actors currently attached to (carried by) this character |
| `CurrentDialogue` | `FString` | Last line set by `command_character_say` |

### Blueprint Implementable Events

Implement these in your NPC Blueprint to hook into MCP-driven behaviour:

| Event | Fired When |
|-------|-----------|
| `OnMessageReceived(Message)` | `send_character_message` is called |
| `OnAIStateChanged(NewState)` | `command_character_set_ai_state` is called |
| `OnInteractRequested(TargetActorName)` | `command_character_interact` is called |
| `OnSayRequested(Text)` | `command_character_say` is called — use this to drive your dialogue UI |

---

## Command Reference

All commands take `character_name` as the first parameter — the exact actor name in the level.

### Info / Query

| Python Tool | C++ Command | Returns |
|-------------|-------------|---------|
| `get_character_status(character_name)` | `get_character_status` | Location, ai_state, health, current_action, queue sizes |
| `get_character_location(character_name)` | `get_character_location` | World location + rotation |
| `get_character_health(character_name)` | `get_character_health` | health float, is_alive bool |
| `get_character_inventory(character_name)` | `get_character_inventory` | Array of item names |
| `get_character_current_action(character_name)` | `get_character_current_action` | current_action, ai_state |
| `get_character_view(character_name)` | `get_character_view` | **STUB** — returns `not_implemented` |
| `get_nearby_actors(character_name, radius=500)` | `get_nearby_actors` | Actors within radius with distance |
| `get_heard_sounds(character_name)` | `get_heard_sounds` | **STUB** — returns `not_implemented` |

### Messaging / Memory

| Python Tool | C++ Command | Notes |
|-------------|-------------|-------|
| `send_character_message(character_name, message)` | `send_character_message` | Pushes to Inbox, fires `OnMessageReceived` |
| `get_character_messages(character_name, source="outbox", clear=False)` | `get_character_messages` | Reads Outbox or Inbox; optionally clears |
| `set_character_memory(character_name, key, value)` | `set_character_memory` | Writes to Memory map |
| `get_character_memory(character_name, key=None)` | `get_character_memory` | Single key lookup or full map |

### Action Commands

| Python Tool | C++ Command | Notes |
|-------------|-------------|-------|
| `command_character_move_to(character_name, location=None, target_actor=None)` | `command_character_move_to` | Requires AIController on the character |
| `command_character_follow(character_name, target_actor)` | `command_character_follow` | Requires AIController |
| `command_character_stop(character_name)` | `command_character_stop` | Calls `AAIController::StopMovement()` |
| `command_character_look_at(character_name, location=None, target_actor=None)` | `command_character_look_at` | Rotates character to face target (yaw only) |
| `command_character_pickup(character_name, item_name, socket="hand_r")` | `command_character_pickup` | Attaches item to skeletal mesh socket |
| `command_character_drop(character_name, item_name=None)` | `command_character_drop` | Drops specific item or all attached actors |
| `command_character_interact(character_name, target_actor="")` | `command_character_interact` | **STUB** — fires `OnInteractRequested` in Blueprint |
| `command_character_play_animation(character_name, montage_path, play_rate=1.0)` | `command_character_play_animation` | Full asset path required, e.g. `/Game/Animations/AM_Wave` |
| `command_character_say(character_name, text)` | `command_character_say` | Sets CurrentDialogue, adds to Outbox, fires `OnSayRequested` |
| `command_character_set_ai_state(character_name, state)` | `command_character_set_ai_state` | Fires `OnAIStateChanged` in Blueprint |

---

## Setup Checklist (per NPC)

1. Add `UMCPCharacterComponent` to the NPC Blueprint
2. Assign an **AI Controller** class in the NPC Blueprint defaults (required for move/follow/stop)
3. Ensure the Skeletal Mesh has a `hand_r` socket (required for pickup with default socket name)
4. Implement the Blueprint events you need (`OnMessageReceived`, `OnSayRequested`, etc.)
5. Rebuild the plugin after adding the new C++ files

---

## Stubs — Future Work

### `get_character_view`
Will be wired to the user's existing **camera screenshot component** when ready.
Currently returns:
```json
{ "success": true, "status": "not_implemented", "visible_actors": [] }
```

### `get_heard_sounds`
Requires `UAIPerceptionComponent` with hearing configured on the NPC.
Currently returns:
```json
{ "success": true, "status": "not_implemented", "sounds": [] }
```

### `command_character_interact`
Currently fires `OnInteractRequested(target_actor)` on the component — implement the actual interaction logic in the NPC Blueprint.

---

## Example Usage

```python
# Send a message to an NPC
send_character_message("GuardNPC", "The player was last seen near the north gate")

# Ask the NPC where they are
loc = get_character_location("GuardNPC")
# → { "location": {"x": 100, "y": 200, "z": 0}, "rotation": {...} }

# Command the NPC to walk to a location
command_character_move_to("GuardNPC", location=[1000, 500, 0])

# Command the NPC to pick up an item
command_character_pickup("GuardNPC", "Sword_01")

# Make the NPC say something (drives OnSayRequested in Blueprint)
command_character_say("GuardNPC", "Halt! Who goes there?")

# Check what the NPC is carrying
get_character_inventory("GuardNPC")
# → { "inventory": ["Sword_01"], "count": 1 }

# Store a memory fact
set_character_memory("GuardNPC", "last_seen_player", "north_gate")

# Read it back
get_character_memory("GuardNPC", key="last_seen_player")
# → { "key": "last_seen_player", "value": "north_gate" }

# Read NPC replies from their outbox
get_character_messages("GuardNPC", source="outbox", clear=True)
```
