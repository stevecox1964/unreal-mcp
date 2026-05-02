---
name: create-npc
description: Scaffold a new NPC agent under Python/agents/<id>/ and bind it to an Unreal actor. Replaces the npc_builder web UI. Use when the user says "create an NPC", "add an agent", "make a new character", or invokes /create-npc.
---

# Create NPC

Scaffolds the 6 agent files under `Python/agents/<agent_id>/` and binds the new NPC to an Unreal actor (find existing or spawn from a blueprint).

## Inputs

Gather these from the user. If they invoked the skill with a name (e.g. `/create-npc bartleby`), use it as `agent_id` and ask for the rest. Use AskUserQuestion for any missing required field.

| Field | Required | Default | Notes |
|---|---|---|---|
| `agent_id` | yes | — | lowercase, `[a-z0-9_]+`, must match directory name. Reject if `Python/agents/<id>/` already exists. |
| `unreal_actor_name` | yes | TitleCase of `agent_id` | Outliner label in Unreal. |
| `blueprint_class` | no | `/Game/Blueprints/BP_PlayerCharacter.BP_PlayerCharacter_C` | Used as spawn fallback if no actor with `unreal_actor_name` is found. Set explicitly if a custom blueprint exists. |
| `tier` | no | `2` | 1=Sonnet 4.6 (lead NPCs), 2=Haiku 4.5 (default), 3=no LLM (background extras). |
| `role` | yes | — | Short one-liner — feeds `character.md`. |
| `personality` | yes | — | Speaking style and disposition. |
| `backstory` | no | empty | Optional prose. |
| `long_term_goals` | yes | — | Bulleted list. |
| `current_goal` | yes | — | What the NPC is doing right now (also goes into `state.json`). |
| `extra_rules` | no | empty | Bulleted list appended after the standard rules. |

## Files to create

All under `Python/agents/<agent_id>/`. Create directory first.

### `state.json`
```json
{
  "agent_id": "<agent_id>",
  "unreal_actor_name": "<unreal_actor_name>",
  "blueprint_class": "<blueprint_class>",
  "tier": <tier>,
  "is_active": true,
  "is_busy": false,
  "current_goal": "<current_goal>",
  "tick_interval_seconds": 10,
  "speech_cooldown_seconds": 30,
  "last_tick_time": null,
  "last_spoke_time": null
}
```

### `tools.json`
```json
{
  "allowed_actions": [
    "idle",
    "walk_to",
    "speak_to",
    "inspect_object",
    "follow_character",
    "attack",
    "flee",
    "ask_for_screenshot",
    "remember"
  ]
}
```

### `memory.json`
```json
{ "agent_id": "<agent_id>", "memories": [] }
```

### `character.md`
```
# Agent: <unreal_actor_name>

## Role

<role>

## Personality

<personality>

## Speaking Style

<speaking style — derive from personality if user didn't separate them>

## Backstory

<backstory>
```

### `goals.md`
```
# Goals

## Long-Term Goals

<long_term_goals as bullet list>

## Current Goal

<current_goal>
```

### `rules.md`
```
# Rules

- Do not invent tools or actions.
- Return structured JSON decisions only.
<extra_rules>
```

## Bind to Unreal (after files are written)

1. Probe MCP socket: call `mcp__unrealMCP__find_actors_by_name` with `unreal_actor_name`. If the call errors with a connection refused / timeout, Unreal isn't in PIE — tell the user to press Play and stop. Do not retry.
2. If the actor exists → done. The agent will bind on `start_simulation`.
3. If not, the spawn fallback in `agent_manager._bind_agents` will use `blueprint_class` automatically when the simulation starts. Tell the user this will happen — no action needed unless they want to pre-place the body manually.

## Output to user

After files are written, print a summary:
- Path created: `Python/agents/<agent_id>/`
- Tier and resolved model
- Bind status: "found existing actor `<name>`" OR "will spawn from `<blueprint_class>` on simulation start" OR "Unreal offline — open PIE before starting"
- Next command they can run:
  ```
  start_simulation(tick_seconds=10, active_agents=["<agent_id>"])
  ```

## Validation rules

- Reject if directory exists. Tell user to delete it first or pick a different `agent_id`.
- Reject `agent_id` containing uppercase, spaces, or characters outside `[a-z0-9_]`.
- Reject `tier` not in {1,2,3}.
- Do not modify any files outside `Python/agents/<agent_id>/` and don't touch any existing agent's files.

## Don't

- Don't spin up the npc_builder web app (`npc_builder/` is deprecated for this workflow — file edits via this skill are the canonical path).
- Don't start the simulation automatically. Creating the NPC and starting the sim are separate user decisions.
- Don't add the NPC to any "active list" — `start_simulation`'s `active_agents` argument is how the user opts in per-run.
