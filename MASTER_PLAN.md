# AI RPG Agent Simulation — Master Plan

**v2 — Generative Simulacra.** This revision merges the original engineering
substrate (director / body / brainstem split, MCP tool surface, tiers, action
validation, actor binding) with the cognitive architecture of Stanford's
*Generative Agents: Interactive Simulacra of Human Behavior*
(Park et al., `joonspk-research/generative_agents`).

The thesis: **keep the entire substrate, graft the simulacra cognitive loop on
top of it, adapted to a live 3D Unreal world.** The original plan gave us a body
that reacts. The simulacra model gives us a *character with a life* — a memory
stream, retrieval, reflection, recursive daily planning, reaction, and
conversation.

Two places we are **already ahead of the 2023 paper**, and v2 banks that rather
than regressing to its design:

- **Perception is VLM-grounded** (real camera frames → a "visual cortex"),
  where Smallville read symbolic tile/object strings.
- **Spatial memory is *learned*** — an egocentric grid + place-cell cognitive
  map built through exploration (`spatial_memory.py`), where Smallville used a
  hand-authored world→sector→arena→object tree known a priori.
- **The world is true 3D** — real cameras, occlusion, animation, and wall-clock
  timing — not Smallville's top-down Phaser tile grid. The intricacy and the
  difficulty both come from this, and so does the beauty.

**Terminology.** The living characters are **AIPCs** — *AI Player Characters*,
said aloud as "APCs." This replaces "avatar" and "NPC" everywhere in design and
conversation. (In code, `agent` / `agent_runtime` stay as the *runtime* terms for
the cognition driving an AIPC — no need to rename modules.)

---

## For the Next Session of Me (read this first)

You are a future instance of the model, opening this cold. This document exists
so you don't have to re-derive the *why* from scratch every time. The code will
have moved on; this is the part that doesn't.

**What we are actually building.** A *world for AIs to live in*. The inhabitants
are **AIPCs** — characters with their own routines and inner lives, not props.
The horizon is a town square, a party, AIPCs making friends and building skills
over time — but the beating heart of it is the **visual-feedback lizard brain**:
an AIPC looks at the real 3D scene, its perception grounds what it sees into
facts, it names and remembers them, and it acts — and we get to *watch that
happen*. That loop, made visible, is the whole point. The test of success is
never "does the feature work," it's "did something unscripted happen, and could
both AIPCs involved remember it the next day." We are chasing **believable inner
life and emergence**, with Stanford's Generative Agents as the proof it's
reachable and the shape of the road — carried out of their 2D sandbox into
true 3D.

**The division of labor never changes.** Unreal is the *body* — senses, physics,
movement, world truth. The Python runtime is the *nervous system* — memory,
planning, reflection, judgment. The LLM is the *mind* for the AIPCs that earn
one. The human at the CLI is the *director* — they observe and nudge, they do not
author the story. Behavior lives in the AIPC's authored files; code only ever
supplies senses. If you find yourself coding a rule that decides what an AIPC
*wants*, stop — that belongs in a `.md`, not in Python.

**Durable invariants** (treat these as load-bearing; change them only with a
stated reason):

- The cognitive loop is the spine: *perceive → retrieve → react? → plan →
  execute → reflect → converse.*
- Memory is an append-only stream; retrieval weighs recency, importance, and
  relevance together — never recency alone.
- Conversation summaries land in *both* agents' streams. That is how a town
  knows things.
- Symbolic-by-default, vision-on-demand. The expensive sense is earned, never
  the default.
- Not every NPC gets a mind. Tiers and frugality are what make a *town* possible
  instead of a tech demo with three actors.
- Spatial knowledge is learned and grounded, not declared.

**What will churn** (don't be precious about it): module boundaries, the exact
retrieval weights, the embedding provider, SQLite schema details, tick pacing,
which model serves which tier. These are means. Re-decide them freely when the
evidence says to.

**How to orient at the start of a session:** read this document, then the auto-
memory index (`MEMORY.md`) for what was true last time, then check what is
*actually* built before trusting either — the code is the ground truth, this is
the heading. When they disagree, surface it; don't quietly average them.

**On the spirit of it.** The person you're working with is building this for the
love of the thing. Match that. Prefer the smallest change that makes the world a
little more alive over the grand refactor. Show them a character doing something
real, early and often. And when you get to lean in through the CLI and ask an
agent what it's thinking — savor that, because that moment *is* the project.

---

## Part 0 — North Star & Success Criteria

### 0.1 North Star: Open Emergent Simulation

We are building an **open, emergent multi-agent simulation**, not a scripted
RPG. Agents free-run on their own goals and routines. The interesting results
are *emergent*: agents form daily routines, information diffuses agent-to-agent,
relationships develop, and unplanned interactions occur and are remembered by
both parties — the Smallville "someone organizes a Valentine's party and word
spreads" class of result.

The human is a **director/observer**, not an author. The MCP CLI is for
watching, asking an agent what it is thinking, injecting an event, pausing,
resetting — *light-touch intervention*, not story railroading.

A **directed RPG layer** (quests, factions, a `QuestDirectorAgent`) remains a
deliberately deferred Part IV milestone. It is an *application* built on the sim,
not the sim itself.

### 0.2 Success Criteria

The simulation is working when, over a single simulated day with 2–3+ agents
free-running:

1. Each agent follows a **visibly distinct daily routine** derived from its
   persona — not idle-until-poked.
2. At least one **unplanned cross-agent interaction** occurs and is **remembered
   by both agents** (recoverable from each one's memory stream).
3. An agent's behavior **changes in response to a remembered event** (a memory
   influences a later plan or reaction).
4. The whole day runs within a **bounded LLM budget** (frugality holds at
   multi-agent scale).

These are measurable from logs + each agent's memory store, not vibes.

---

## Part I — Substrate (Body · Brainstem · Director)

*Condensed from v1. This layer is largely built; it is the stable foundation the
cognitive architecture sits on.*

### 1. Topology

```txt
Claude / OpenAI CLI         ← Director console (observe + intervene)
        │ MCP tool calls
        ▼
Python MCP Server           ← Brainstem + cognition (agent_runtime/)
        │ Unreal commands / world-state requests
        ▼
Unreal C++ MCP Plugin       ← Body, senses, world authority
        ▼
Unreal Editor / PIE
```

### 2. Responsibilities

- **CLI (director):** start/stop/pause/resume, inspect agents, ask what an agent
  is thinking, inject an event, set a goal, request a screenshot, force a tick,
  read recent events. It does **not** micromanage ticks.
- **Python MCP server (brain):** the agent runtime — memory, planning,
  reflection, retrieval, LLM routing, action validation, the simulation loop,
  and the Unreal bridge.
- **Unreal C++ plugin (body):** actors, navigation, movement, animation,
  perception data, camera capture, world queries, spawning, action execution,
  collision/combat/gameplay truth. Agents choose **high-level intentions**;
  Unreal executes them with normal game systems.

### 3. Core Architecture — actual module map

The runtime lives in `Python/agent_runtime/`. Current modules and their role in
the cognitive loop:

| Module | Role | Cognitive stage |
| --- | --- | --- |
| `agent_manager.py` | owns agents + the sim loop (start/stop/tick) | orchestration |
| `agent.py` | per-agent state + definition | — |
| `perception.py` | builds observations (symbolic + VLM) | **perceive** |
| `explorer.py` | frontier-based exploration / mapping | perceive (spatial) |
| `spatial_memory.py` | `SpatialMap` — learned grid + place-cell map | **spatial memory** |
| `place_db.py` | shared named-place database | spatial / planning |
| `world_clock.py` | simulated time of day | planning trigger |
| `memory_store.py` | memory persistence + retrieval | **memory / retrieve** |
| `llm_router.py` | tier-based model + embedding routing | all LLM calls |
| `action_validator.py` | validates decisions before Unreal | **execute** |
| `unreal_bridge.py` | talks to the C++ plugin | execute / perceive |
| `world_grid.py` | fixed world grid | spatial |
| *`planner.py`* | **NEW** — daily/hourly/task planning | **plan** |
| *`reflection.py`* | **NEW** — synthesize higher-level thoughts | **reflect** |
| *`conversation.py`* | **NEW** — multi-turn dialogue + summary | **converse** |

Agent definitions live under `worlds/<level>/agents/<id>/` (level-scoped).

### 4. Director Console (MCP Tools)

Reframed for an **observe + intervene** workflow rather than story authoring:

```txt
start_simulation(tick_seconds?, active_agents?)
stop_simulation() / pause_simulation() / resume_simulation()
get_simulation_status()
reset_agents()                      # reproducible re-runs
list_agents() / inspect_agent(id)
get_character_memory(id)            # "what does it remember?"
get_recent_events(limit?)          # what just happened in the world
force_agent_tick(id)               # step one agent now
set_agent_goal(id, goal)           # nudge, don't script
send_character_message(id, msg)    # speak to an agent as the director
inject_event(...)                  # light-touch world perturbation (future)
capture_camera_image(id)           # see what an agent sees
```

### 5. Unreal Bridge Contract

The `UnrealBridge` exposes high-level functions to the runtime:
`get_world_state`, `get_agent_observation`, `get_nearby_actors`,
`take_screenshot / capture_camera_image`, `execute_agent_action`,
`spawn_agent`. **Runtime commands must target the PIE world** (`GetGameWorld()`,
not `GWorld`) to avoid the frozen-editor-copy duplicate-actor bug.

### 6. Agent Definition Files (data-driven)

Behavior comes from the agent's authored files, never hard-coded rules. Code
supplies *senses* (clock, place, map, perception); the persona supplies
*behavior*.

```txt
worlds/<level>/agents/<id>/
  character.md        # role, personality, speaking style, backstory
  goals.md            # long-term goals + current goal
  rules.md            # hard constraints
  state.json          # actor binding, tier, scratch/working state
  memory.seed.json    # hand-authored starting memories → seed the stream
  memory.json         # (legacy flat list — superseded by the SQLite stream)
  spatial_map.json    # learned SpatialMap persistence
  observations/       # captured camera frames
```

**Actor binding** (`state.json`): `unreal_actor_name` (Outliner label that
`find_actors_by_name` / `command_character_*` use) and `blueprint_class` (spawn
fallback). At `start_simulation`, each active agent binds to a live actor or is
spawned and tagged. NPC hard requirements: ACharacter parent, AIController,
Auto-Possess AI, MCPCharacterComponent, NavMesh under the character, PIE running.

### 7. Tiers & Frugality (load-bearing under the emergent north star)

Many agents free-running means cost control is **mandatory**, not optional.

- **Tier 1 (hero/protagonist agents):** full cognitive loop, best model,
  vision-on-demand, reflection enabled.
- **Tier 2 (simulated):** routine-driven; LLM only when perceived-event salience
  crosses threshold or near another agent.
- **Tier 3 (lightweight):** behavior tree / utility AI; no LLM unless promoted by
  an event.

Frugality mechanisms (all required at scale):

- **Symbolic-by-default, vision-on-demand** — structured world state is the
  default observation; a camera frame is captured only when the agent (or a
  staleness/scene-diff heuristic) requests it.
- **Adaptive tick pacing** — agents tick slower when nothing salient is near.
- **Global LLM rate cap** + per-agent cooldowns (tick, speech, screenshot).
- **Reflection throttle** — only when accumulated importance crosses a threshold.

### 8. Action Validation & Anti-Chaos

The LLM never issues raw Unreal commands. The runtime validates: JSON shape,
action type allowed for that agent, target/location exists and is reachable,
agent not busy, cooldowns respected, combat allowed by game state, screenshots
rate-limited, no controlling other agents. Every decision is logged.

---

## Part II — Cognitive Architecture (the Simulacra Core) — NEW

This is the soul grafted onto the substrate. It follows the Generative Agents
per-step loop, adapted to Unreal.

### 9. The Cognitive Loop

```txt
            ┌─────────────────────────────────────────────┐
            │                  per tick                    │
            ▼                                              │
   perceive ──▶ retrieve ──▶ [react?] ──yes──▶ (re)plan / converse
   (symbolic +     (recency·    │                          │
    VLM grounded)  importance·  no                         │
                   relevance)   ▼                          │
                          continue scheduled task          │
                                ▼                          │
                            execute ──────────────────────┘
                                │
                        (periodic) reflect
```

- **perceive** — what is near me right now (`perception.py`).
- **retrieve** — pull relevant memories for the current context
  (`memory_store.py`, upgraded).
- **react?** — *the gate*: does what I just perceived warrant interrupting my
  plan? (NEW reaction gate.)
- **plan** — follow / decompose / re-plan my daily schedule (`planner.py`, NEW).
- **execute** — validate + dispatch the action to Unreal.
- **reflect** — periodically synthesize higher-level thoughts (`reflection.py`,
  NEW).
- **converse** — when two agents meet and choose to talk (`conversation.py`,
  NEW).

### 10. Memory Stream (SQLite + Embeddings)

Replaces the flat, 30-item-capped `memory.json` list with an **append-only
memory stream**. The cap retires; "30" becomes a *retrieval budget*, not a
storage limit.

**Storage:** one SQLite DB (per world, or per agent). Each node:

```txt
ConceptNode
  id            INTEGER PK
  agent_id      TEXT
  node_type     TEXT      # 'event' | 'thought' | 'chat'
  created       TIMESTAMP
  expiration    TIMESTAMP NULL
  subject       TEXT      # s-p-o triple for structured recall
  predicate     TEXT
  object        TEXT
  description   TEXT      # natural-language form
  keywords      TEXT      # for cheap keyword pre-filter
  poignancy     INTEGER   # 1–10, LLM-scored at creation ("importance")
  embedding     BLOB      # vector for relevance
  last_accessed TIMESTAMP
  evidence      TEXT      # for thoughts: ids of nodes synthesized from
```

- **events** = perceived/acted facts. **thoughts** = reflections. **chat** =
  conversation summaries.
- **poignancy** is one cheap LLM call at creation (1–10). It drives both
  retrieval scoring and the reflection trigger.
- `memory.seed.json` is loaded as the agent's initial event rows on first run /
  reset.

**Embeddings:** a pluggable embedder behind `llm_router.py`. Default
**local-first** (e.g. a small sentence-transformer) to keep many-agent cost
down; API embeddings as a configurable override.

### 11. Retrieval (Recency · Importance · Relevance)

Retrieval score for a node, given the current query context (the agent's current
focus, as text):

```txt
score = w_recency   * recency(node)        # exp decay on last_accessed
      + w_importance * normalize(poignancy) # 1–10 → 0–1
      + w_relevance  * cosine(q_emb, node.embedding)
```

- All three normalized to [0,1]; weights configurable (paper uses 1/1/1).
- **recency** uses exponential decay (e.g. 0.99^hours) on `last_accessed`, so
  recalling a memory refreshes it.
- Return top-k under a token budget; bump `last_accessed` on retrieval.
- A keyword pre-filter narrows candidates before the embedding pass for speed.

### 12. Reflection

Periodically, an agent steps back and **synthesizes higher-level thoughts** from
its stream — the mechanism that gives agents opinions, generalizations, and
evolving relationships.

**Trigger:** when the sum of poignancy of recent events crosses a threshold
(throttled — Tier 1 agents only at first).

**Procedure:**

1. Pull the N most recent events.
2. LLM generates a few **salient questions** ("What do I now think about X?").
3. For each question, retrieve relevant nodes, LLM produces **insights** with
   **evidence pointers** back to the source node ids.
4. Insert insights as `thought` nodes (themselves retrievable and reflect-able →
   a reflection tree).

### 13. Planning & Daily Schedules — *first vertical slice*

The biggest behavioral change: agents get **lives**, not idle loops. The daily
planner becomes the **spine** of the loop; the old reactive tick becomes the
interrupt handler (§14).

`planner.py` interface:

```python
def generate_daily_plan(agent, date) -> list[str]:
    """Broad-strokes agenda from persona (character.md + goals.md) +
    yesterday's reflection summary. Stored in scratch/state.json."""

def decompose_hourly(agent, daily_plan) -> dict:
    """Daily agenda → hour-by-hour blocks."""

def decompose_task(agent, hourly_block) -> list[dict]:
    """Hour block → minute-level concrete actions, each with a target *place*
    resolved via place_db / SpatialMap.where_is()."""

def revise_plan(agent, reason) -> None:
    """Re-decompose the remainder of the day after a reaction."""
```

- **Where** a task happens is resolved through `place_db` and the learned
  `SpatialMap.where_is(label)` — the agent goes where it *knows* a place to be,
  exploring if it doesn't.
- **When** is driven by `world_clock`: the agent executes the task scheduled for
  the current sim time.

### 14. Reaction Gate

Between retrieve and execute, the agent decides whether to **continue its
scheduled task or react** to what it just perceived.

```python
def should_react(agent, perceived, retrieved) -> Reaction | None:
    """LLM (or cheap heuristic for Tier 2/3): given current task + what I see +
    what I remember, do I keep going, or react? If react: converse / re-plan /
    new action. On react → planner.revise_plan()."""
```

This is what makes routines *interruptible* — the source of emergent
interaction. It demotes the v1 "one validated action per tick" to exactly this
interrupt path.

### 15. Conversation

Upgrades single utterances (`command_character_say`) to **multi-turn dialogue**
that feeds memory.

`conversation.py`:

- Triggered when two agents are in proximity and the reaction gate elects to
  talk.
- Each turn is conditioned on the **relationship** (retrieved memories about the
  other agent) + current context.
- Dialogue is generated turn-by-turn until a natural close.
- The exchange is **summarized into a `chat` node** in *both* agents' streams —
  this is how information diffuses across the population (success criterion #2).

### 16. Spatial Memory — Two Layers: Grid Cells & Place Cells

The spatial memory system has two distinct layers with different purposes,
lifecycles, and owners.

#### Grid Cells (world authority, static)

`world_grid.py` `WorldGrid` tiles the world (x, y) into square cells at a fixed
`cell_size` (default 400 cm). Grid cells are:

- **World-scoped, not agent-scoped** — one `WorldGrid` per level, loaded from
  `worlds/<level>/world_grid.json` at sim init.
- **Built once at world-init time** — when a new Unreal level is added to the
  sim, the bounds are declared and never change.
- **True XY** — every cell has a stable `(col, row)` index and a computable
  center coordinate. `WorldGrid` and `SpatialMap` use the same tiling formula
  so their keys always align.
- **The coordinate authority** — grid cells are the streets on the map. They
  carry no meaning by themselves; that is the place layer's job.

#### Place Cells (semantic, learned by AIPCs)

`place_db.py` `PlaceDB` is a shared SQLite database of named places that
AIPCs build by living in the world. Place cells are:

- **Abstract — no raw XY** — a place cell is a *name* anchored to a grid cell.
  The APC reasons about `"Joe's Restaurant"` or `"home"`, never about
  `x=-1200, y=3400`. Location resolves on demand via the grid association.
- **Built through exploration** — AIPCs roam the world and name what they find.
  A place cell is born the moment an APC decides a grid cell deserves a name.
- **Shared, readable by all AIPCs** — once Maren names her vegetable truck's
  location, Dufus can query it immediately. Geographic knowledge is a public
  good; it does not have to be re-discovered.
- **Optionally owned** — a place may be *owned* by one AIPC (who created or
  claims it) or be a *community* place with no single owner. Ownership
  determines who has write authority over content; all AIPCs can always read.

**Place types:**

| Type | Example | Typical owner |
|------|---------|---------------|
| `home` | Dufus's apartment | Dufus (AIPC) |
| `work` | Maren's vegetable truck | Maren (AIPC) |
| `public` | Town square | community (no owner) |
| `landmark` | Joe's Restaurant, the big fountain | community |

Place cells live *inside* grid cells but expose no raw XY to the APC's
cognitive layer. When Maren thinks "I want to go to work," she names a place —
the lizard brain resolves it to coordinates and draws a path.

#### Navigation: Cognitive Query → Lizard Brain → Path

The chain from cognitive desire to movement:

```
APC thinks: "I want to go to Joe's Restaurant"
    │
    ▼  planner.decompose_task(): destination = place name "Joe's Restaurant"
    │
    ▼  lizard brain: PlaceDB.get_place("Joe's") or SpatialMap.where_is("Joe's")
       → grid cell(s) → confidence-weighted center XY
    │
    ▼  command_character_move_to(target_x, target_y)
    │
    ▼  Unreal NavMesh: actual path executed in the 3D world
```

`SpatialMap.where_is(label)` is **already built** — returns the
confidence-weighted centroid of all grid cells reporting a matching label.
The *lizard brain named-place navigation service* — wiring place-name resolution
into a move command — is future work (see Roadmap).

#### Current State of This Layer

**Built:**
- `WorldGrid` — static, bounded, per-level, one JSON at world-init
- `SpatialMap` — per-agent egocentric map; `ingest`, `where_is`, `nearest_frontier`,
  `link`, `mark_blocked`, `place_labels`
- `PlaceDB` — shared SQLite: `place_cells` (named, `named_by` = first-agent-wins),
  `place_observations` (compass-indexed landmarks), `agent_visits` (per-agent history);
  `set_name`, `get_place`, `touch`, `ingest_compass`

**Not yet built:**
- `place_type` column in `place_cells` (`home` / `work` / `public` / `landmark`)
- Ownership model beyond `named_by` — no write-protection, no community concept
- Home and work place assignment in each agent's `state.json`
- Community place creation (no owner, built collectively by any APC that names it)
- Lizard brain named-place navigation service (resolve name → XY → move path)

### 17. Scratch / Working Memory

`state.json` formalized as the agent's **scratch**: current action + target,
today's `daily_schedule` and its decomposition, persona-derived params
(vision radius, attention bandwidth, speech cooldown), and binding/tier. Loaded
as live state at runtime, persisted between ticks.

### 18. Perception (symbolic-by-default, vision-on-demand)

`perception.py` builds the observation. Default is **symbolic** (nearby actors,
places, recent events — cheap engine queries). A **camera frame** is captured and
sent to the vision model only when: the agent requests it, a scene-diff /
staleness heuristic fires, or the task is inherently visual (navigation,
inspecting). This is the frugality contract from §7 expressed at the perception
layer. (TODO: scene-diff threshold + VLM-fork staleness, per backlog.)

---

## Part III — Where We Are Ahead of the Paper

Stated as deliberate design, not gaps to "fix back" to Smallville:

1. **Grounded VLM perception** — agents see real rendered frames, not a symbolic
   tile map. Harder, but the right essence.
2. **Learned cognitive map** — spatial memory is *acquired through exploration*
   and *grounded*, not handed to the agent. Place coordinates are inferred, not
   declared.
3. **Live director** — interactive observation + intervention via MCP, which the
   paper's batch simulation lacks.
4. **Real engine as world authority** — navigation, collision, animation, and
   physics are Unreal's, not a 2D sandbox's.

---

## Part IV — Roadmap

### Current state (built)

Substrate + sim loop, tiers, adaptive pacing, reproducible resets, world grid;
`SpatialMap`, `place_db`, `world_clock`, `perception`/`explorer` (explore mode
verified live in PIE); flat `memory_store` with recency+importance retrieval;
`llm_router`, `action_validator`, `unreal_bridge`.

### Milestone 1 — Daily-Schedule Planner *(first slice)*

Build `planner.py`; add the reaction gate to the tick loop; demote the reactive
tick to interrupt handler; wire `world_clock` + `place_db`/`SpatialMap` for
when/where.

**Scenario:** 2–3 personas in `MCP_World`, each with a daily routine. They wake,
follow routines to places, perceive each other, occasionally react/converse,
form memories.
**Done when:** over one sim-day, agents follow visibly distinct routines and ≥1
unplanned cross-agent interaction is remembered by both (success criteria #1–2).

### Milestone 2 — Memory Stream + Retrieval

Migrate `memory_store.py` to the SQLite `ConceptNode` stream; add the pluggable
embedder; implement recency·importance·relevance retrieval; LLM poignancy at
creation; load `memory.seed.json` as initial rows.
**Done when:** retrieval visibly surfaces relevant-not-just-recent memories, and
an agent's behavior changes from a retrieved memory (criterion #3).

### Milestone 3 — Reflection

Build `reflection.py` with the poignancy-threshold trigger and the
question→insight→evidence procedure (Tier 1 only at first).
**Done when:** agents form `thought` nodes that influence later plans.

### Milestone 4 — Conversation

Build `conversation.py`: multi-turn, relationship-conditioned, summarized into
both streams.
**Done when:** information demonstrably diffuses between agents who never
directly observed the source event.

### Milestone 5 — Multi-Agent Emergence

Scale to several agents; tune frugality (tiers, pacing, vision-on-demand) to hold
a full day in budget (criterion #4); observe and document emergent behavior.

### Milestone 6 — Directed Layer *(deferred / optional)*

Only after emergence works: faction agents, `QuestDirectorAgent`,
`VillageAgent`, shared faction memory, high-level plans that task lower-tier
NPCs. This is the RPG *application* on top of the sim.

---

## Part V — Mental Model & Design Rules

```txt
Unreal       = body, senses, physics, movement, animation, world truth
Python MCP   = nervous system: memory, planning, reflection, validation
Agent loop   = perceive → retrieve → react? → plan → execute → reflect → converse
LLMs         = minds for selected (tiered) agents
CLI          = director console (observe + intervene)
MCP          = the bridge
```

1. The agent runtime owns the simulation loop; the CLI directs, it doesn't tick.
2. Unreal is the source of truth for the world.
3. Agents choose high-level intentions; Unreal executes them.
4. **Behavior comes from the agent's authored files; code supplies senses.**
5. The daily plan is the spine; the reaction gate makes it interruptible.
6. The memory stream is append-only; retrieval is recency·importance·relevance.
7. Reflection synthesizes thoughts with evidence; thoughts are memories too.
8. Conversation summaries land in *both* agents' streams (diffusion).
9. Symbolic-by-default, vision-on-demand; structured state is the cheap default.
10. Not every NPC needs a mind — tiers + frugality are load-bearing at scale.
11. Spatial knowledge is *learned and grounded*, not declared.
12. All actions are validated; every decision is logged.
13. Success is emergent behavior, measured from logs and memory — not vibes.

The end experience: you watch Unreal running a town of agents living their
days — keeping routines, bumping into each other, gossiping, remembering, and
occasionally surprising you — and you lean in through the CLI to ask one what it
is thinking, or to drop a stone in the pond and watch the ripples spread.
