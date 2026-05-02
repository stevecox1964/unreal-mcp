# Still TODO — Session 2026-05-01 (synced with code)

Snapshot of where we left off. Re-synced 2026-05-01 against current source tree.

## Current state (verified against code/logs)

- ✅ MCP server reconnected: `Python/unreal_mcp.log` shows `Connected to Unreal Engine` at 17:09:37 today — port 55557 is open, dotenv + `_resolve_model` are live.
- ✅ `Python/unreal_mcp_server.py:15-16` loads `.env` from `Python/.env`.
- ✅ `Python/agent_runtime/llm_router.py:69-93` implements 3-layer `_resolve_model`.
- ✅ `Content/Blueprints/BP_CameraNPC.uasset` exists and is the Bartleby NPC body. `BP_PlayerCharacter.uasset` and `BP_GameMode.uasset` also present.
- ✅ `Python/agents/bartleby/state.json` is wired to `/Game/Blueprints/BP_CameraNPC.BP_CameraNPC_C` and is `is_active: true`.
- ℹ️ Bartleby is the only NPC in the current acceptance path.
- ✅ User confirmed `BP_CameraNPC.CameraMount` has its **Child Actor Class** set to `CameraCaptureActor`.

## Pickup points for next session

1. Run E2E:
   - `start_simulation(tick_seconds=10, active_agents=["bartleby"])`
   - `force_agent_tick("bartleby")`
   - `capture_camera_image()` — should grab from Bartleby's CameraMount once spawned
   - `get_recent_events()`

## What was added this session (2026-05-01)

- `.claude/skills/create-npc/SKILL.md` — slash-command skill replacing the npc_builder web UI. Available after CLI restart.
- `Content/Blueprints/BP_CameraNPC.uasset` — created via MCP and currently used as Bartleby's NPC body. Parent `Actor`, has `Body` cylinder mesh + `CameraMount` ChildActorComponent slot at `[0,0,100]`. Compiled. User confirmed `CameraMount` ChildActorClass is set.
- `Python/agents/bartleby/` — current NPC acceptance target, traveling merchant, tier 2 (Haiku). Wired to `BP_CameraNPC` via `state.json.blueprint_class`.
- Memory: `plugin_gaps.md` documents the two C++ MCP plugin limitations encountered.



---

## Implementation status vs `AI_RPG_Agent_Simulation_MASTER_PLAN.md`

| § | Section | Status |
|---|---|---|
| 4 | Folder structure | ⚠️ Missing `prompts/`, `schemas/`, `factions/`, `world_state_cache.py`, `event_queue.py`, `schemas.py` |
| 5 | Agent definition files | ✅ Done for current Bartleby acceptance target |
| 6 | Agent Manager | ✅ Done (load/bind/start/stop/pause/resume/tick/pulse) |
| 7 | Simulation MCP tools | ⚠️ Missing `send_agent_message`, `take_agent_screenshot` |
| 8 | Unreal Bridge contract | ⚠️ Missing `take_screenshot`, `query_objects_near_agent` wrappers |
| 9 | Agent Decision Schema | ✅ Embedded in prompt; no separate JSON Schema file |
| 10 | Prompt Design | ⚠️ Inlined in `llm_router.py` — no `prompts/` files |
| 11 | Agent Tiers | ✅ Done (1=Sonnet 4.6, 2=Haiku 4.5, 3=none) |
| 12 | Faction/Location agents | ❌ Not implemented |
| 13 | Event Queue | ❌ Polling only — no event-driven wakeups |
| 14 | Screenshots / Vision | ❌ Action stub only; no real screenshot pipeline back to LLM |
| 15 | Action Validation | ✅ Done |
| 16 | Cooldowns & anti-chaos | ⚠️ Tick + speech cooldowns only; no global LLM rate-limit, busy-lock during long actions, priority, event dedup, memory pruning |
| 17 | Memory System | ⚠️ Simple JSON; no SQLite, embeddings, or summarization |
| 18 | LLM Routing | ✅ Done with prompt caching + 3-layer model resolution |
| 19 | Manual Override | ⚠️ Have `set_agent_goal`, `force_agent_tick`; missing `send_agent_message` |
| 20 | First-prototype live test | ❌ **Blocked — Unreal Editor not running** |
| 26 | Actor Binding Contract | ✅ Done |
| 27 | NPC Builder Web App | ⚠️ Scaffolded, not E2E verified |

---

## Task list (in priority order)

1. **[in_progress] First live end-to-end test (Phase 1 acceptance)** — see "Blockers" section below
2. [pending] Add `send_agent_message` MCP tool
3. [pending] Add `take_agent_screenshot` MCP tool + screenshot pipeline (§14)
4. [pending] Implement event queue (§13)
5. [pending] Tighten cooldown / anti-chaos controls (§16) — global LLM rate-limit, busy-lock release, priority queue, memory pruning, error fallback
6. [pending] Move prompts into `prompts/` directory (§4, §10)
7. [pending] Add JSON schemas (§4)
8. [pending] Resolve string `target_location` for `walk_to` (§8 / known limitation) — needs world-state name→position lookup
9. [pending] Faction / Director agents (Phase 8, §12)
10. [pending] Memory system upgrade (§17) — SQLite → embeddings → semantic retrieval → summarization
11. [pending] E2E test NPC Builder web app (§27)
12. [pending] Add second NPC and multi-agent test (§20 second wave)

---

## Code changes made this session

### `Python/pyproject.toml`
- Added `python-dotenv>=1.0.0`

### `Python/unreal_mcp_server.py`
- Added at top:
  ```python
  from pathlib import Path
  from dotenv import load_dotenv
  load_dotenv(Path(__file__).parent / ".env")
  ```
  Loads `.env` regardless of cwd.

### `Python/agent_runtime/llm_router.py`
- Replaced `_model_for_tier(tier)` with `_resolve_model(agent)` — 3-layer resolution:
  1. `agent.state["model"]` (per-agent override; only way to give a Tier 3 agent an LLM)
  2. Tier 3 short-circuit → `None` (no LLM, no cost)
  3. `os.environ["ANTHROPIC_MODEL"]` (loaded from `.env`)
  4. Tier 1 → `claude-sonnet-4-6`, Tier 2 → `claude-haiku-4-5-20251001`

### `.env` location
- User created `Python/.env` containing `ANTHROPIC_API_KEY=...` and `ANTHROPIC_MODEL=...`
- Already covered by root `.gitignore` (line 104)

### Files deleted
- `SESSION_HANDOFF.md` (per user request, fresh start)

---

## Blockers found while attempting task #1 (live E2E test)

**Hard block (RESOLVED 2026-05-01 17:09; user reconfirmed PIE running):** MCP server connected to Unreal at startup — port 55557 is open.

**Soft block (RESOLVED):** The active BP NPC is Bartleby via `BP_CameraNPC`.

**Stale code (RESOLVED):** Server is running on the post-edit code as of 17:09:37 today.

### What `find_actor` and `start_simulation` returned during this session
- Old non-Bartleby actor probes are no longer relevant to task #1; the active BP NPC is Bartleby.
- `start_simulation` → `{"status": "error", "error": "No agents could be bound to Unreal actors"}` (also because Unreal offline)
- `get_simulation_status` → returned valid empty status (this only touches Python side, no socket call needed)

Next probe should target Bartleby only.

---

## To unblock task #1 — user-action checklist

1. Then say "Continue task #1" — Claude will run `find_actor` for Bartleby, `start_simulation(..., active_agents=["bartleby"])`, `force_agent_tick("bartleby")`, `capture_camera_image()`, `get_recent_events()`.

---

## Memory snapshots (already saved)

- `~/.claude/projects/.../memory/project_overview.md` — what exists, current status
- `~/.claude/projects/.../memory/architecture_decisions.md` — key design choices

These persist across sessions — Claude will load them automatically next time.
