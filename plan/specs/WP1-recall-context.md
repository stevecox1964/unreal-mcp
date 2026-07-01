# WP1 — Render the built recall context into the decision prompt

**Item:** closes a gap found in the 2026-07-01 architect pass (feeds #5, #6, #10.5)
**Gate:** none — build hands-off.
**Depends on:** nothing. **Blocks:** WP2.

## Problem (verified in code, 2026-07-01)

`AgentManager._perceive_and_decide` (`Python/agent_runtime/agent_manager.py`
~lines 896–911) attaches three recall structures to the observation every tick:

- `observation["acquaintances"]` — `SocialMemory.acquaintances()`, ranked list of
  `{name, meet_count, interaction_count, first_met, last_seen, last_cell, sentiment}`
- `observation["known_places"]` — `AgentManager.known_places(location)[:8]`,
  nearest-first `{name, bearing, distance_m, col, row}`
- `observation["recent_episodes"]` — `EpisodicLog.relevant(n=5, ...)`

**None of them are rendered into `_USER_TEMPLATE_VISION`** (`Python/agent_runtime/llm_router.py`,
template at ~line 51, formatted in `decide()` at ~line 413). The format call passes
`memories, known_characters, grid_cell, place, x, y, z, facing, direction_lines,
seen, world_time, current_action, current_goal, stuck_note, schedule_note` — and
nothing else. So the social store (#5), the named-place map (#6 "map query"), and
episodic relevance recall are **invisible to the LLM** in the normal vision path.
(Only the no-image fallback `_USER_TEMPLATE` sees them, via the raw observation
JSON dump.)

`known_characters` is a different thing — it's the list of *other sim agents*
(who could in principle be met), not who this agent has actually met.

## Change

All in `Python/agent_runtime/llm_router.py`. No behavior change outside prompt
construction.

### 1. Three new pure renderers (place near `_seen_text` / `_direction_lines`)

```python
def _acquaintance_lines(acquaintances: list | None) -> str:
    """People this agent has actually met, most familiar first.

    Input items come from SocialMemory.acquaintances():
    {name, meet_count, interaction_count, last_seen, ...}. Cap at 8.
    """
```
Output, one line per person (skip items with no `name`):
`- Maren — met 4 times, spoken with 2 times, last seen Day 1, 09:12`
(use `meet_count`, `interaction_count`, `last_seen`; omit a clause whose value is
falsy). Empty/None input → `"Nobody yet — you have not met anyone."`

```python
def _known_place_lines(places: list | None) -> str:
    """The agent's named-place map, nearest first (from AgentManager.known_places)."""
```
Output per item: `- village square — SE, 34 m` (fields `name`, `bearing`,
`distance_m`; round distance to whole meters). Empty/None →
`"No named places yet — name places as you discover them."`

```python
def _episode_lines(episodes: list | None) -> str:
    """Relevant past episodes (from EpisodicLog.relevant): what happened where."""
```
Each episode is `{world_time, grid_cell, place, saw, action, outcome}` (summary
rows may instead have `kind:"summary"`, `place`, `count`, `first_time`,
`last_time`, `actions`, `saw`). Render event rows as
`- [Day 1, 09:12] at vegetable truck: speak_to, saw Maren` (omit empty parts);
summary rows as `- [Day 1, 08:00–11:40] around vegetable truck: 14 events`.
Empty/None → `"Nothing memorable yet."`

### 2. Template sections

In `_USER_TEMPLATE_VISION`, directly after the `## Your Memories` block, add:

```
## People You Know (met before)
{acquaintance_lines}

## Places You Know (your map, nearest first)
{known_place_lines}

## Relevant Past Moments
{episode_lines}
```

And change the existing sentence
`A CHARACTER sighting matching one of the known characters above is that person`
to reference both lists:
`A CHARACTER sighting matching a name under "People You Know" is someone you have
met before. One matching "Characters You May Encounter" is that person.`
(Leave the "consider greeting" clause alone — WP2 rewrites it.)

### 3. Wire into `decide()`

In the `_USER_TEMPLATE_VISION.format(...)` call add:

```python
acquaintance_lines=_acquaintance_lines(observation.get("acquaintances")),
known_place_lines=_known_place_lines(observation.get("known_places")),
episode_lines=_episode_lines(observation.get("recent_episodes")),
```

Do **not** add these to `_USER_TEMPLATE` (fallback already carries the raw
observation) or `_USER_TEMPLATE_WAKE` (wake has its own orientation flow — out of
scope).

## Tests

New `Python/scripts/agent_runtime/test_prompt_context.py`, copying the
`check()` style of `test_map_query.py`. Import the renderers from
`agent_runtime.llm_router` directly (pure functions, no LLM/provider needed):

1. `_acquaintance_lines`: one full item renders name + counts + last_seen; empty
   list and `None` give the "Nobody yet" line; a 10-item list renders 8 lines.
2. `_known_place_lines`: renders `name — bearing, Nm` and rounds `distance_m`;
   empty → placeholder.
3. `_episode_lines`: event row renders time/place/action/saw; summary row
   (`kind:"summary"`) renders the count form without raising; empty → placeholder.
4. Template contract: `_USER_TEMPLATE_VISION` contains the three new
   placeholders (`{acquaintance_lines}` etc.) and the headings
   `## People You Know` / `## Places You Know` — so a template edit can't silently
   drop the sections.

## Acceptance

- [ ] `python scripts/run_tests.py` green (existing suite + the new file).
- [ ] `grep -rn "acquaintance_lines" Python/agent_runtime/llm_router.py` shows the
      renderer, the template placeholder, and the format kwarg (same for the
      other two).
- [ ] No changes outside `llm_router.py` + the new test file.

## Executor notes

*(append findings/deviations here)*
