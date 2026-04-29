# AI RPG Agent Simulation — Master Plan

## 1. Purpose

This project adds an agentic NPC simulation layer to an Unreal Engine RPG project using MCP.

The goal is to allow Claude, OpenAI, or another LLM client to control and inspect a live Unreal simulation through a Python MCP server. The Python MCP server already communicates with an Unreal C++ plugin. The new work adds an **Agent Manager / Agent Controller** inside the Python MCP server so multiple LLM-driven agents can observe the world, reason, make decisions, and send validated actions back into Unreal.

The key idea:

```txt
Claude / OpenAI CLI
        |
        | MCP tool calls
        v
Python MCP Server
        |
        | Agent Manager + Simulation Harness
        |
        | Unreal commands / world-state requests
        v
Unreal C++ MCP Plugin
        |
        v
Unreal Editor / Play Mode
```

The user should be able to say something like:

```txt
Begin simulation.
```

The LLM CLI calls an MCP tool such as:

```txt
start_simulation()
```

The Python MCP server starts a background simulation loop. The user can watch Unreal Editor / Play Mode running the simulation live.

At any time, the user should be able to say:

```txt
Stop simulation.
```

The LLM CLI calls:

```txt
stop_simulation()
```

The Agent Manager stops pulsing agents.

---

## 2. High-Level Design

### 2.1 Responsibilities

#### Claude / OpenAI CLI

The LLM CLI is the **director interface**.

It should be able to:

- Start the simulation.
- Stop the simulation.
- Pause or resume the simulation.
- Inspect agents.
- Give agents new goals.
- Ask for recent events.
- Ask for screenshots.
- Manually trigger a single agent tick.
- Override or redirect a running simulation.

The CLI should **not** micromanage every simulation tick.

#### Python MCP Server

The Python MCP server is the **brainstem and orchestration layer**.

It should own:

- Agent Manager.
- Simulation loop / pulse harness.
- Agent registry.
- Agent definitions.
- Agent memory.
- World-state cache.
- Event queue.
- LLM routing.
- Action validation.
- Logs.
- MCP tools exposed to Claude/OpenAI.
- Communication with the Unreal C++ plugin.

#### Unreal C++ MCP Plugin

The Unreal plugin is the **body / senses / world authority**.

It should own:

- Actual actors.
- Navigation.
- Movement.
- Animation.
- Perception data.
- Screenshots.
- World queries.
- Actor spawning.
- Action execution.
- Collision / combat / gameplay truth.

The LLM should not perform low-level movement or raw Unreal commands directly. It should choose high-level intentions/actions. Unreal should execute those actions using normal game systems.

---

## 3. Core Architecture

```txt
Claude/OpenAI CLI
  |
  | MCP tools
  v
Python MCP Server
  |
  | contains:
  | - AgentManager
  | - SimulationRuntime
  | - AgentRegistry
  | - MemoryStore
  | - WorldStateCache
  | - EventQueue
  | - LLMRouter
  | - ActionValidator
  |
  v
UnrealBridge
  |
  | talks to
  v
Unreal C++ MCP Plugin
  |
  v
Unreal Editor / PIE
```

For the first prototype, it is acceptable for `AgentManager` to contain the simulation harness directly.

Later, if the code grows, split it into:

```txt
AgentManager       = owns agents and agent state
SimulationRuntime  = owns start/stop/tick loop
UnrealBridge       = talks to Unreal
LLMRouter          = talks to Claude/OpenAI/local models
ActionValidator    = validates decisions before Unreal receives them
MemoryStore        = persists memories and event history
```

---

## 4. Recommended Folder Structure

Inside the Python MCP server project:

```txt
unreal_mcp_server/
  main.py

  agent_runtime/
    __init__.py
    agent_manager.py
    agent.py
    simulation_runtime.py
    unreal_bridge.py
    llm_router.py
    action_validator.py
    memory_store.py
    world_state_cache.py
    event_queue.py
    schemas.py

  agents/
    gondolf/
      character.md
      goals.md
      rules.md
      tools.json
      memory.json
      state.json

    innkeeper/
      character.md
      goals.md
      rules.md
      tools.json
      memory.json
      state.json

    bandit_01/
      character.md
      goals.md
      rules.md
      tools.json
      memory.json
      state.json

  factions/
    village/
      faction.md
      goals.md
      memory.json

    bandits/
      faction.md
      goals.md
      memory.json

  prompts/
    agent_decision_prompt.md
    dialogue_prompt.md
    memory_update_prompt.md
    visual_inspection_prompt.md
    director_command_prompt.md

  schemas/
    agent_decision.schema.json
    unreal_action.schema.json
    world_observation.schema.json
    memory_event.schema.json
    simulation_status.schema.json

  logs/
    agent_decisions.log
    world_events.log
    simulation.log
```

---

## 5. Agent Definition Files

Each agent should be mostly data-driven.

Example:

```txt
agents/gondolf/
  character.md
  goals.md
  rules.md
  tools.json
  memory.json
  state.json
```

### 5.1 `character.md`

```md
# Agent: Gondolf

## Role

Old wizard NPC who protects the village.

## Personality

Wise, suspicious, slow to trust strangers, but helpful to those who prove honorable.

## Speaking Style

Speaks in short, cryptic warnings. Avoids modern slang.

## Backstory

Gondolf once guarded the Chalice of Dawn. He believes dark forces are returning to the nearby ruins.
```

### 5.2 `goals.md`

```md
# Goals

## Long-Term Goals

- Protect the village.
- Protect the Chalice of Dawn.
- Watch for suspicious strangers near the ruins.
- Help the player only after trust is established.

## Current Goal

Patrol the village square and observe newcomers.
```

### 5.3 `rules.md`

```md
# Rules

- Do not attack unless threatened.
- Do not reveal the Chalice location immediately.
- If the player asks about the Chalice, become cautious.
- If bandits are nearby, warn the village guard.
- Do not invent tools or actions.
- Return structured JSON decisions only.
```

### 5.4 `tools.json`

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

### 5.5 `memory.json`

```json
{
  "agent_id": "gondolf",
  "memories": [
    {
      "timestamp": "2026-04-29T12:00:00Z",
      "importance": 0.8,
      "text": "The player asked about the Chalice."
    }
  ]
}
```

### 5.6 `state.json`

```json
{
  "agent_id": "gondolf",
  "is_active": true,
  "is_busy": false,
  "current_goal": "patrol_village",
  "current_location": "Village Square",
  "tick_interval_seconds": 10,
  "last_tick_time": null,
  "speech_cooldown_seconds": 30,
  "last_spoke_time": null
}
```

---

## 6. Agent Manager

The Agent Manager is the central controller.

It should:

- Load all agent definitions.
- Track active/inactive agents.
- Start and stop the simulation loop.
- Pulse agents on a schedule.
- Pull world state from Unreal.
- Determine which agents are ready to think.
- Build compact observations for each agent.
- Route agent decision requests to the right LLM.
- Validate returned actions.
- Send approved actions to Unreal.
- Store memory and logs.
- Support manual overrides from the CLI.

### 6.1 Minimal Class Shape

```python
import asyncio
from typing import Dict, Optional

class AgentManager:
    def __init__(self, unreal_client, llm_router, memory_store):
        self.unreal = unreal_client
        self.llm_router = llm_router
        self.memory = memory_store
        self.agents: Dict[str, Agent] = {}

        self.running = False
        self.paused = False
        self.tick_seconds = 5
        self.sim_task: Optional[asyncio.Task] = None

    async def start_simulation(self, tick_seconds: int = 5):
        if self.running:
            return {"status": "already_running"}

        self.running = True
        self.paused = False
        self.tick_seconds = tick_seconds
        self.sim_task = asyncio.create_task(self._simulation_loop())

        return {
            "status": "started",
            "tick_seconds": self.tick_seconds
        }

    async def stop_simulation(self):
        self.running = False
        self.paused = False

        if self.sim_task:
            self.sim_task.cancel()
            self.sim_task = None

        return {"status": "stopped"}

    async def pause_simulation(self):
        self.paused = True
        return {"status": "paused"}

    async def resume_simulation(self):
        if not self.running:
            return {"status": "not_running"}

        self.paused = False
        return {"status": "resumed"}

    async def _simulation_loop(self):
        while self.running:
            if not self.paused:
                await self.tick()

            await asyncio.sleep(self.tick_seconds)

    async def tick(self):
        world_state = await self.unreal.get_world_state()

        ready_agents = self.get_ready_agents(world_state)

        for agent in ready_agents:
            await self.pulse_agent(agent, world_state)

    async def pulse_agent(self, agent, world_state):
        observation = await self.build_observation(agent, world_state)
        decision = await self.llm_router.decide(agent, observation)
        action = self.validate_action(agent, decision)

        if action:
            result = await self.unreal.execute_agent_action(agent.agent_id, action)
            await self.memory.record(agent.agent_id, observation, action, result)

    def get_ready_agents(self, world_state):
        ready = []

        for agent in self.agents.values():
            if not agent.is_active:
                continue

            if agent.is_busy:
                continue

            if not agent.cooldown_expired():
                continue

            if not self.agent_is_relevant(agent, world_state):
                continue

            ready.append(agent)

        return ready

    def agent_is_relevant(self, agent, world_state):
        # First prototype can return True for all active agents.
        # Later: only pulse agents near player or near important events.
        return True

    def validate_action(self, agent, decision):
        # Validate JSON schema.
        # Check action type is allowed.
        # Check target exists if required.
        # Check cooldowns.
        # Prevent arbitrary Unreal commands.
        return decision.get("action")
```

---

## 7. Simulation Control MCP Tools

The Python MCP server should expose simulation-control tools to Claude/OpenAI.

### 7.1 Required Tools

```txt
start_simulation(tick_seconds?: int, active_agents?: list[str])
stop_simulation()
pause_simulation()
resume_simulation()
get_simulation_status()
list_agents()
inspect_agent(agent_id: str)
set_agent_goal(agent_id: str, goal: str)
send_agent_message(agent_id: str, message: str)
force_agent_tick(agent_id: str)
get_recent_events(limit?: int)
take_agent_screenshot(agent_id: str)
```

### 7.2 Example Tool: `start_simulation`

Input:

```json
{
  "tick_seconds": 5,
  "active_agents": ["gondolf", "innkeeper"]
}
```

Output:

```json
{
  "status": "started",
  "tick_seconds": 5,
  "active_agents": ["gondolf", "innkeeper"]
}
```

### 7.3 Example Tool: `stop_simulation`

Input:

```json
{}
```

Output:

```json
{
  "status": "stopped"
}
```

### 7.4 Example Tool: `get_simulation_status`

Output:

```json
{
  "status": "running",
  "paused": false,
  "tick_seconds": 5,
  "active_agents": 2,
  "last_tick_time": "2026-04-29T16:30:00Z",
  "unreal_connected": true,
  "llm_router_connected": true
}
```

---

## 8. Unreal Bridge / C++ Plugin Contract

The Python MCP server should communicate with the Unreal C++ plugin through an `UnrealBridge`.

The bridge should expose high-level functions to the Agent Manager.

### 8.1 UnrealBridge Methods

```python
class UnrealBridge:
    async def get_world_state(self) -> dict:
        pass

    async def get_agent_observation(self, agent_id: str) -> dict:
        pass

    async def take_screenshot(self, camera_or_agent_id: str) -> dict:
        pass

    async def execute_agent_action(self, agent_id: str, action: dict) -> dict:
        pass

    async def query_objects_near_agent(self, agent_id: str, radius: float) -> dict:
        pass

    async def spawn_agent(self, agent_definition: dict) -> dict:
        pass
```

### 8.2 World State Example

```json
{
  "world_id": "demo_village",
  "time_of_day": "evening",
  "player": {
    "id": "player",
    "location": "Village Tavern",
    "position": [125.0, 300.0, 0.0]
  },
  "agents": [
    {
      "id": "gondolf",
      "location": "Village Square",
      "position": [400.0, 250.0, 0.0],
      "state": "idle",
      "is_visible_to_player": false
    },
    {
      "id": "innkeeper",
      "location": "Village Tavern",
      "position": [150.0, 320.0, 0.0],
      "state": "working",
      "is_visible_to_player": true
    }
  ],
  "events": [
    {
      "type": "player_entered_area",
      "area": "Village Tavern",
      "nearby_agents": ["innkeeper"],
      "importance": 0.7
    }
  ]
}
```

### 8.3 Agent Observation Example

```json
{
  "agent_id": "innkeeper",
  "location": "Village Tavern",
  "nearby_characters": [
    {
      "id": "player",
      "name": "Player",
      "distance": 300,
      "faction": "unknown"
    }
  ],
  "nearby_objects": [
    {
      "id": "bar_counter",
      "name": "Bar Counter",
      "distance": 80
    }
  ],
  "visible_threats": [],
  "current_task": "serve_customers",
  "recent_events": [
    {
      "type": "player_entered_area",
      "area": "Village Tavern",
      "importance": 0.7
    }
  ]
}
```

### 8.4 Execute Action Example

Input:

```json
{
  "agent_id": "innkeeper",
  "action": {
    "type": "speak_to",
    "target": "player",
    "message": "Welcome, traveler. Looking for a room or a rumor?"
  }
}
```

Output:

```json
{
  "status": "accepted",
  "agent_id": "innkeeper",
  "action_id": "act_123",
  "estimated_duration_seconds": 4
}
```

---

## 9. Agent Decision Schema

The LLM should return structured JSON only.

### 9.1 Agent Decision

```json
{
  "agent_id": "gondolf",
  "thought_summary": "The player is near the tavern, but I have no reason to intervene yet.",
  "action": {
    "type": "idle",
    "duration_seconds": 5
  },
  "speech": null,
  "memory_update": null,
  "importance": 0.2
}
```

### 9.2 Speak Action

```json
{
  "agent_id": "innkeeper",
  "thought_summary": "The player entered my tavern, so I should greet them.",
  "action": {
    "type": "speak_to",
    "target": "player",
    "message": "Welcome to the Hearth & Hammer. Need a room, a drink, or information?"
  },
  "speech": {
    "target": "player",
    "message": "Welcome to the Hearth & Hammer. Need a room, a drink, or information?"
  },
  "memory_update": "The player entered the tavern for the first time.",
  "importance": 0.5
}
```

### 9.3 Walk Action

```json
{
  "agent_id": "gondolf",
  "thought_summary": "I heard of movement near the east gate and should investigate.",
  "action": {
    "type": "walk_to",
    "target_location": "East Gate"
  },
  "speech": null,
  "memory_update": "Suspicious movement was reported near the east gate.",
  "importance": 0.6
}
```

### 9.4 Ask For Screenshot Action

```json
{
  "agent_id": "gondolf",
  "thought_summary": "The structured data is unclear. I need a visual check of the ruins entrance.",
  "action": {
    "type": "ask_for_screenshot",
    "camera": "agent_view"
  },
  "speech": null,
  "memory_update": null,
  "importance": 0.4
}
```

---

## 10. Prompt Design

The decision prompt should be strict and boring.

### 10.1 `prompts/agent_decision_prompt.md`

```md
You are controlling one NPC in an Unreal Engine RPG world.

You must choose exactly one next action from the allowed actions.

Do not invent tools.
Do not invent locations, characters, or objects.
Do not control other characters.
Do not output prose outside JSON.
Do not issue raw Unreal commands.
Do not choose actions that are not in the allowed action list.

Consider:
- Your personality
- Your goals
- Your memories
- The current world observation
- Nearby characters and objects
- Current threats
- Current task
- Cooldowns
- Whether speaking is appropriate

Return JSON only using this shape:

{
  "agent_id": "...",
  "thought_summary": "...",
  "action": {
    "type": "..."
  },
  "speech": null,
  "memory_update": null,
  "importance": 0.0
}
```

### 10.2 Prompt Inputs

The Agent Manager should build a prompt from:

```txt
- Agent character.md
- Agent goals.md
- Agent rules.md
- Allowed tools/actions
- Relevant memory
- Current observation
- Recent world events
- Current cooldowns/state
```

---

## 11. Agent Tiers

Not every NPC should use a full LLM every few seconds.

### 11.1 Tier 1: Hero Agents

Major story NPCs.

Examples:

```txt
Gondolf
Main villain
Player companion
Quest giver
Faction leader
```

Features:

- Full memory.
- Goal reasoning.
- Dialogue.
- Screenshots when useful.
- More expensive LLM allowed.

### 11.2 Tier 2: Simulated Agents

Important background NPCs.

Examples:

```txt
Innkeeper
Blacksmith
Guard captain
Merchant
```

Features:

- Mostly schedule/routine driven.
- LLM only when interrupted or near player.
- Less frequent ticks.

### 11.3 Tier 3: Lightweight NPCs

Generic background actors.

Examples:

```txt
Villagers
Animals
Basic guards
Random bandits
```

Features:

- Behavior Tree / Utility AI / State Machine.
- No LLM unless promoted by an event.
- Can be controlled indirectly by faction agents.

---

## 12. Faction and Location Agents

In addition to character agents, support higher-level agents later.

Examples:

```txt
VillageAgent
BanditFactionAgent
DungeonDirectorAgent
QuestDirectorAgent
WeatherMoodAgent
```

Faction agents can make broad decisions without giving every NPC a full LLM brain.

Example:

```txt
BanditFactionAgent:
- Goal: steal supplies from village.
- Knows: player killed two scouts.
- Decision: send two bandits to watch the east road.
```

Individual bandits can then follow simple commands using normal Unreal behavior systems.

---

## 13. Event Queue

The Agent Manager should support both polling and events.

### 13.1 Polling

Every N seconds:

```txt
AgentManager.tick()
  -> get_world_state()
  -> choose ready agents
  -> pulse each ready agent
```

### 13.2 Events

Unreal can report important events:

```json
{
  "type": "world_event",
  "event": "player_entered_area",
  "area": "Village_Tavern",
  "nearby_agents": ["innkeeper", "gondolf"],
  "importance": 0.75,
  "timestamp": "2026-04-29T16:05:00Z"
}
```

The Agent Manager decides whether to wake agents.

It should not blindly call an LLM for every event.

### 13.3 Suggested Event Types

```txt
player_entered_area
player_left_area
agent_saw_player
agent_heard_noise
agent_attacked
agent_spoke
item_discovered
quest_state_changed
combat_started
combat_ended
important_object_moved
```

---

## 14. Screenshots and Vision

Screenshots are powerful but should be used selectively.

Structured Unreal data should be the default.

Use screenshots when:

- The agent is confused.
- Visual confirmation is needed.
- The player is nearby and expression/pose/location matters.
- A new object appeared.
- The agent is inspecting something.
- The LLM specifically asks for `ask_for_screenshot`.

Do not send screenshots every tick for every agent.

Recommended flow:

```txt
1. Agent receives structured observation.
2. Agent decides it needs visual context.
3. Agent returns ask_for_screenshot.
4. Agent Manager asks Unreal for screenshot.
5. Agent Manager sends visual observation to the LLM.
6. Agent returns final action.
```

---

## 15. Action Validation

Never let the LLM directly execute arbitrary Unreal commands.

The Agent Manager must validate:

- JSON is valid.
- Action type is allowed for that agent.
- Target exists.
- Target is reachable if applicable.
- Agent is not busy.
- Cooldowns are respected.
- Speech cooldown is respected.
- Combat actions are allowed by current game state.
- Screenshot requests are rate-limited.
- The action does not control other agents improperly.

Example:

```python
def validate_action(agent, decision, world_state):
    action = decision.get("action")

    if not action:
        return None

    action_type = action.get("type")

    if action_type not in agent.allowed_actions:
        return None

    if action_type == "speak_to":
        if not agent.can_speak():
            return None
        if not target_exists(action.get("target"), world_state):
            return None

    if action_type == "walk_to":
        if not location_exists(action.get("target_location"), world_state):
            return None

    return action
```

---

## 16. Cooldowns and Anti-Chaos Controls

Without controls, agentic NPCs will become noisy and expensive.

Add:

```txt
- Tick interval per agent
- Global max LLM calls per minute
- Speech cooldown
- Screenshot cooldown
- Busy/locked state while actions execute
- Priority system
- Event deduplication
- Memory pruning
- Error fallback behavior
```

Example state:

```json
{
  "agent_id": "gondolf",
  "last_llm_tick": "2026-04-29T16:05:00Z",
  "min_tick_interval_seconds": 10,
  "can_speak": true,
  "speech_cooldown_seconds": 30,
  "current_goal": "patrol_village",
  "locked_until_action_complete": true
}
```

---

## 17. Memory System

Start simple.

Use local JSON files first.

Later, use SQLite.

### 17.1 Memory Record

```json
{
  "timestamp": "2026-04-29T16:10:00Z",
  "agent_id": "gondolf",
  "type": "observation_action_result",
  "observation": {
    "location": "Village Square",
    "nearby_characters": ["player"]
  },
  "action": {
    "type": "speak_to",
    "target": "player",
    "message": "You tread near dangerous ground."
  },
  "result": {
    "status": "accepted"
  },
  "importance": 0.7,
  "summary": "Gondolf warned the player near the village square."
}
```

### 17.2 Retrieval

For first version:

- Include last 5 memories.
- Include important memories with importance > 0.7.
- Include memories related to nearby characters.

Later:

- Store embeddings.
- Retrieve memories based on semantic similarity.
- Summarize old memories.

---

## 18. LLM Routing

The Agent Manager should not assume every agent uses the same model.

Use an `LLMRouter`.

Example routing:

```txt
Gondolf              -> Claude / GPT high-end model
Main villain         -> Claude / GPT high-end model
Innkeeper            -> cheaper model
Generic villager     -> local/small model or no LLM
Bandit grunt         -> Behavior Tree unless special event
QuestDirectorAgent   -> high-end model
```

Minimal interface:

```python
class LLMRouter:
    async def decide(self, agent, observation):
        model = self.select_model(agent)
        prompt = self.build_prompt(agent, observation)
        return await model.complete_json(prompt)

    def select_model(self, agent):
        if agent.tier == 1:
            return self.high_reasoning_model
        if agent.tier == 2:
            return self.light_model
        return self.local_or_none_model
```

---

## 19. Manual Override Commands

While the simulation is running, the user should be able to intervene through the CLI.

Examples:

```txt
Tell Gondolf to go to the bridge.
Make the bandits hostile.
Pause villager agents.
Give the player a quest clue.
Force a screenshot from Gondolf's view.
Set Innkeeper's goal to greet the player.
```

Expose MCP tools for this.

Example:

```python
async def set_agent_goal(self, agent_id: str, goal: str):
    agent = self.agents[agent_id]
    agent.current_goal = goal
    agent.force_next_tick = True

    return {
        "status": "goal_updated",
        "agent_id": agent_id,
        "goal": goal
    }
```

---

## 20. First Prototype Scope

Do not start with many agents.

Build the first prototype with:

```txt
- 1 player
- 1 intelligent NPC
- 1 simple world-state endpoint
- 1 screenshot endpoint
- 1 action endpoint
- 1 memory file
- 1 decision loop every 5–10 seconds
```

Recommended first scenario:

```txt
Gondolf stands in a village.
Player walks nearby.
Agent Manager sends Gondolf world state.
Gondolf decides whether to greet, ignore, follow, warn, or ask for screenshot.
Unreal performs the action.
Gondolf remembers the interaction.
```

Then add:

```txt
- Second NPC
- Shared memory
- Faction goal
- Quest state
- Visual inspection
- Event queue
```

---

## 21. Implementation Phases

### Phase 1 — Skeleton Agent Manager

Build:

```txt
agent_runtime/agent.py
agent_runtime/agent_manager.py
agent_runtime/memory_store.py
agent_runtime/unreal_bridge.py
```

Implement:

```txt
load_agents()
start_simulation()
stop_simulation()
pause_simulation()
resume_simulation()
get_simulation_status()
tick()
```

Use mock Unreal responses at first if needed.

### Phase 2 — MCP Tool Exposure

Expose tools from the existing Python MCP server:

```txt
start_simulation
stop_simulation
pause_simulation
resume_simulation
get_simulation_status
list_agents
inspect_agent
set_agent_goal
force_agent_tick
```

Verify Claude/OpenAI CLI can call them.

### Phase 3 — Unreal Bridge Integration

Connect Agent Manager to the existing Unreal C++ plugin.

Implement or wire:

```txt
get_world_state
get_agent_observation
execute_agent_action
take_screenshot
```

### Phase 4 — LLM Decision Loop

Implement:

```txt
LLMRouter
agent_decision_prompt
JSON-only decision parsing
schema validation
fallback behavior
```

The first LLM action set should be small:

```txt
idle
walk_to
speak_to
ask_for_screenshot
remember
```

### Phase 5 — Memory and Logs

Implement:

```txt
memory.json read/write
agent_decisions.log
world_events.log
recent events MCP tool
```

### Phase 6 — Screenshots / Vision

Add:

```txt
ask_for_screenshot action
take_agent_screenshot MCP call
vision-specific prompt
rate limiting
```

### Phase 7 — Multiple Agents

Add:

```txt
agent prioritization
tick staggering
speech cooldown
busy state
near-player filtering
event queue
```

### Phase 8 — Factions and Directors

Add:

```txt
Faction agents
QuestDirectorAgent
VillageAgent
shared memory
high-level plans that create tasks for lower-tier NPCs
```

---

## 22. Suggested Python Interfaces

### 22.1 Agent

```python
class Agent:
    def __init__(
        self,
        agent_id: str,
        name: str,
        tier: int,
        character_text: str,
        goals_text: str,
        rules_text: str,
        allowed_actions: list[str],
        state: dict,
    ):
        self.agent_id = agent_id
        self.name = name
        self.tier = tier
        self.character_text = character_text
        self.goals_text = goals_text
        self.rules_text = rules_text
        self.allowed_actions = allowed_actions
        self.state = state

    @property
    def is_active(self) -> bool:
        return self.state.get("is_active", True)

    @property
    def is_busy(self) -> bool:
        return self.state.get("is_busy", False)

    def cooldown_expired(self) -> bool:
        # Check last tick time versus tick interval.
        return True
```

### 22.2 AgentManager

```python
class AgentManager:
    async def start_simulation(self, tick_seconds: int = 5) -> dict:
        ...

    async def stop_simulation(self) -> dict:
        ...

    async def pause_simulation(self) -> dict:
        ...

    async def resume_simulation(self) -> dict:
        ...

    def get_status(self) -> dict:
        ...

    async def tick(self) -> dict:
        ...

    async def pulse_agent(self, agent_id: str) -> dict:
        ...

    def list_agents(self) -> list[dict]:
        ...

    def inspect_agent(self, agent_id: str) -> dict:
        ...

    def set_agent_goal(self, agent_id: str, goal: str) -> dict:
        ...
```

---

## 23. Example Runtime Flow

### 23.1 User Starts Simulation

User says in Claude/OpenAI CLI:

```txt
Begin simulation with Gondolf and the Innkeeper active.
```

LLM calls MCP:

```json
{
  "tool": "start_simulation",
  "arguments": {
    "tick_seconds": 5,
    "active_agents": ["gondolf", "innkeeper"]
  }
}
```

Agent Manager:

```txt
- sets running = true
- activates requested agents
- creates background async simulation task
- returns status
```

### 23.2 Simulation Tick

```txt
AgentManager._simulation_loop()
  -> AgentManager.tick()
    -> UnrealBridge.get_world_state()
    -> AgentManager.get_ready_agents()
    -> AgentManager.pulse_agent(gondolf)
      -> build observation
      -> call LLMRouter.decide()
      -> validate action
      -> UnrealBridge.execute_agent_action()
      -> MemoryStore.record()
    -> AgentManager.pulse_agent(innkeeper)
      -> same flow
```

### 23.3 User Stops Simulation

User says:

```txt
Stop simulation.
```

LLM calls:

```json
{
  "tool": "stop_simulation",
  "arguments": {}
}
```

Agent Manager:

```txt
- sets running = false
- cancels background task
- returns stopped status
```

---

## 24. Important Design Rules

1. The Agent Manager owns the simulation loop.
2. The LLM CLI starts/stops/inspects/directs the simulation.
3. The LLM CLI does not manually tick every agent.
4. Unreal remains the source of truth for the world.
5. The Python MCP server is the orchestration brain.
6. The Unreal C++ plugin is the body/senses/action layer.
7. Agents choose high-level actions, not low-level movement.
8. All LLM actions must be validated before hitting Unreal.
9. Structured world state should be used by default.
10. Screenshots should be used selectively.
11. Not every NPC needs an LLM brain.
12. Start with one agent before scaling.
13. Keep agent definitions human-editable.
14. Keep runtime state machine-readable.
15. Log every decision.

---

## 25. Final Mental Model

```txt
Unreal = body, senses, physics, movement, animation, combat, world truth

Python MCP Server = nervous system, scheduler, memory, validation, orchestration

Agent Manager = simulation brainstem

LLMs = minds for selected agents

Claude/OpenAI CLI = director console

MCP = communication bridge
```

The final user experience should feel like:

```txt
User watches Unreal Editor running.

User talks to Claude/OpenAI CLI as the simulation director.

The CLI calls MCP tools on the Python MCP server.

The Agent Manager starts or stops the autonomous sim loop.

Agents observe the Unreal world, reason, speak, move, remember, and pursue goals.

Unreal executes the visible results.
```
