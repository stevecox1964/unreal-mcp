# Still TODO — updated 2026-05-01

Snapshot of verified state and open work. Regenerated after the Dufus session.

---

## Verified working (as of 2026-05-01)

- ✅ End-to-end pipeline: Claude CLI → Python MCP server (port 55557) → C++ plugin → Unreal PIE
- ✅ `start_simulation` / `pause_simulation` / `resume_simulation` / `stop_simulation` / `force_agent_tick`
- ✅ `capture_camera_image` — saves timestamped PNG from `CameraCaptureActor_1`
- ✅ Bartleby — tier 2 agent, `BP_CameraNPC`, ticking with `idle` / `ask_for_screenshot` actions accepted
- ✅ Dufus — agent files under `Python/agents/dufus/`, binds to `BP_CameraNPC_C_1` (label `Dufus`)
- ✅ `MCPCharacterComponent` added to `BP_CameraNPC` — `get_character_current_action`, `get_character_messages`, `send_character_message`, `get_character_health`, `get_character_memory`, `command_character_say`, `command_character_set_ai_state` all work for both Bartleby and Dufus
- ✅ `/create-npc` Claude Code skill available for scaffolding new agents

---

## Active agents

| Agent | Status |
|-------|--------|
| Bartleby | Bound to `BP_CameraNPC_C` (label `Bartleby`). Ticking, decisions logged in `get_recent_events`. |
| Dufus | Bound to `BP_CameraNPC_C_1` (label `Dufus`). `force_agent_tick` returned `validation_failed` — see item 2 below. |
| Gondolf | Binding mismatch — see item 3. Excluded from active sims. |

---

## Open tasks (priority order)

### 1. Level-awareness (next major workstream)

AgentManager loads all agents on disk regardless of active level — causes wrong-actor binds and ghost-spawns when an NPC body isn't in the current map.

**Phase 1 — C++ plugin:** Add `get_current_level_name` command to `UnrealMCPEditorCommands.cpp`. Return `World->GetMapName()` + package path. Recompile plugin.

**Phase 2 — Python tool:** Wrap in `Python/tools/editor_tools.py` as `get_current_level_name()`.

**Phase 3 — Agent schema:** Add `levels: list[str]` to `state.json` (default `["*"]` = any level). Update `agent_runtime/agent.py` to read it. Migrate: Bartleby → current level, Dufus → current level, Gondolf → `[]`.

**Phase 4 — AgentManager filtering:** Skip agents whose `levels` doesn't include current level. No spawn-fallback for skipped agents. Clear `bound_unreal_actor_*` at bind time (don't persist across restarts).

**Phase 4.5 — `resync_simulation` tool:** Re-bind without stop/start cycle. Add to `Python/tools/simulation_tools.py`.

**Phase 5 — `/create-npc` skill:** Inject `"levels": ["<current_level>"]` into state template. Probe `get_current_level_name` at creation time.

**Phase 6 — Cleanup:** Delete phantom `BP_CameraNPC` at origin (ghost-spawn from earlier session). Smoke-test level filtering with just Dufus.

Full step-by-step checklist: `memory/todo_level_awareness.md`.

---

### 2. Debug Dufus `validation_failed` tick

`force_agent_tick("dufus")` → `{"action": "idle", "reason": "validation_failed"}`. LLM response didn't pass schema validation; nothing written to `get_recent_events`.

- Add verbose logging in `agent_runtime/action_validator.py` to print raw LLM output before validation.
- Compare raw output against expected JSON schema.
- Check `Python/agents/dufus/tools.json` — ensure `allowed_actions` match validator's known action names exactly.
- Re-run `force_agent_tick("dufus")` and inspect.

---

### 3. Fix Gondolf binding mismatch

`state.json:unreal_actor_name = "Gondolf"` but level actor Outliner label is `BP_PlayerCharacter`. AgentManager matches by label so it misses and falls to spawn.

Options: (A) Rename actor label to `Gondolf` in editor, (B) update `state.json` to `"BP_PlayerCharacter"`, (C) place a dedicated `Gondolf`-labeled actor.

---

### 4. Per-NPC camera routing

`capture_camera_image` uses the first `CameraCaptureActor` found — can't distinguish Dufus's camera from Bartleby's. Fix: accept a character/NPC name and resolve the `CameraCaptureActor` via that character's owning `BP_CameraNPC` (walk ChildActorComponent tree or use actor tags set at spawn).

Related: `get_character_view` in `character_tools.py` is a stub returning `not_implemented`. Once per-NPC routing works, this can wrap it.

---

### 5. Remaining master-plan gaps

| § | Section | Status |
|---|---|---|
| 4 | Folder structure | ⚠️ Missing `prompts/`, `schemas/`, `factions/`, `world_state_cache.py`, `event_queue.py` |
| 7 | Simulation MCP tools | ⚠️ Missing `send_agent_message`, `take_agent_screenshot` |
| 8 | Unreal Bridge | ⚠️ Missing `query_objects_near_agent` wrapper |
| 13 | Event Queue | ❌ Polling only — no event-driven wakeups |
| 14 | Screenshots / Vision | ⚠️ Camera capture works; LLM vision loop for agents needs wiring |
| 16 | Cooldowns / anti-chaos | ⚠️ Tick + speech cooldowns only; no global LLM rate-limit, busy-lock, priority, memory pruning |
| 17 | Memory System | ⚠️ Simple JSON; no SQLite, embeddings, or summarization |
| 19 | Manual Override | ⚠️ `set_agent_goal` + `force_agent_tick` done; missing `send_agent_message` |
| 27 | NPC Builder Web App | ⚠️ Scaffolded, superseded by `/create-npc` skill |

---

## Quick-start for new session

```
# Unreal must be running in PIE first
reload_llm_environment()
start_simulation(tick_seconds=10, active_agents=["bartleby", "dufus"])
force_agent_tick("bartleby")
force_agent_tick("dufus")
capture_camera_image()
get_recent_events(limit=10)
stop_simulation()
```
