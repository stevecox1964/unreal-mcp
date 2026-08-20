from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from dotenv import load_dotenv

from . import agenda
from . import prompt_payload
from .place_db import yaw_to_compass

if TYPE_CHECKING:
    from .agent import Agent

logger = logging.getLogger("AgentRuntime")
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

# Compass abbreviation → the word the walk_to direction field accepts.
_COMPASS_WORD = {
    "N": "north", "NE": "northeast", "E": "east", "SE": "southeast",
    "S": "south", "SW": "southwest", "W": "west", "NW": "northwest",
}

# Field specs for actions that take parameters beyond "type".
_ACTION_SCHEMAS: dict[str, str] = {
    "idle":             '{"type": "idle"}',
    "wander":           '{"type": "wander"}  -- keep moving: take one step in the direction you are facing (about 15m, longer over ground already walked, shorter when something is close). Add "distance": "close|normal|far" to ask for a shorter or longer one',
    "walk_to":          '{"type": "walk_to", "target_location": "<place name>"} to travel to a named place you know (e.g. "village square", "home"), OR {"type": "walk_to", "target_actor": "<character name>"} to walk to a known character, OR {"type": "walk_to", "direction": "north|south|east|west|northeast|northwest|southeast|southwest"} to walk ~15m along that compass heading, OR {"type": "walk_to", "direction": "forward|forward-left|forward-right|left|right|back"} to walk relative to the way your body is currently facing. Any walk with a "direction" may add "distance": "close" (a few metres, for something you can see and want to stop at), "normal" (the default, about 15m) or "far" (tens of metres, for crossing ground you are only passing through). How far you actually travel is worked out from the ground ahead: it is cut short of anything refused or in the way, and it stretches across ground APCs have already walked. You will be told the length you got',
    "survey_here":      '{"type": "survey_here"} to survey the cell you are standing in — captures all four compass headings over the next few ticks and adds the cell to the shared map. Only works on a cell that has no current survey, and only for the cell underfoot',
    "refuse_cell":      '{"type": "refuse_cell", "direction": "north|south|east|west|northeast|northwest|southeast|southwest", "reason": "<what you can see that makes it not worth walking into>"} to record that the cell one step that way is not ground you will walk into. It stops being offered as somewhere to survey, for you and for every other APC, until someone withdraws it. Use it when you can SEE the reason — standing crops, water, a fence, someone\'s private yard. Omit "direction" to refuse the cell you are standing in. Add "scope": "spot" to refuse only the ~9m patch of ground one step that way instead of the whole 30m cell — use the patch for one bad yard, alley or doorway inside a cell that is otherwise worth surveying; use the whole cell for corn fields, water, and ground that is bad wall to wall',
    "allow_cell":       '{"type": "allow_cell", "direction": "<compass word, or omit for here>"} to withdraw a refusal you made earlier — the cell goes back to being ordinary ground. Add "scope": "spot" to withdraw a patch refusal instead',
    "speak_to":         '{"type": "speak_to", "target": "<character name>", "message": "<text>"} -- say something out loud to someone. This is the ONLY action that produces speech: greeting, answering, asking, thanking, saying goodbye. If you intend to say anything at all this tick, the action is speak_to. "idle" and "observe" are silent',
    "inspect_object":   '{"type": "inspect_object", "target": "<character name>"}',
    "follow_character": '{"type": "follow_character", "target": "<character name>"}',
    "attack":           '{"type": "attack", "target": "<character name>"}',
    "flee":             '{"type": "flee"}',
    "observe":            '{"type": "observe"}',
    "remember":         '{"type": "remember", "text": "<what to remember>"}',
}

# Static portion of the prompt; eligible for Anthropic prompt caching.
_SYSTEM_TEMPLATE = """\
You are controlling one character in a living world.

## Character
{character}

## Goals
{goals}

## Rules
{rules}

## Allowed Actions
Each entry shows the exact JSON shape to use in the "action" field:
{actions}
"""

# Dynamic portion — perception path: Gemini has already turned the screenshot
# into structured sightings; the decision LLM reads facts, never pixels.
_USER_TEMPLATE_VISION = """\
## Your Memories
{memories}

## People You Know (met before)
{acquaintance_lines}

## Places You Know (your map, nearest first)
{known_place_lines}

## Relevant Past Moments
{episode_lines}

## Characters You May Encounter
{known_characters}

## Nearby APCs (a position fact; not proof of line of sight)
{nearby_character_lines}

## Your Location
x={x:.0f}, y={y:.0f}, z={z:.0f}
Facing: {facing}
Travel: {travel_note}
Grid cell: {grid_cell}
Place: {place}
Time: {world_time}

## Where You Can Go Next — neighboring grid cells (one step ~15m away)
{direction_lines}

## The Wider Map — how much of the world is mapped, and where its edge is
{frontier_note}

## You See (your forward view, perceived just now)
{seen}

## Your Current State
{current_action}

## Current Goal
{current_goal}

## What You Just Heard
{heard_note}

## Active Interruption
{active_interrupt_note}

## Survey State Of The Cell You Are Standing In
{cell_survey_note}

{agenda_context}

## Your Routine Right Now
{schedule_note}
{route_map_note}
Anything listed under "You See" is really there. A CHARACTER sighting matching
a name under "People You Know" is someone you have met before; one matching
"Characters You May Encounter" is that person.
Nearby APC positions are reliable proximity facts, although they do not prove
line of sight. If your scheduled activity calls for greeting passersby, you may
turn toward or approach a nearby APC instead of wandering away to search blindly.

## What Wins Right Now
If there is an active interruption, it outranks your routine. Address the
grounded requester/reason under "Active Interruption" until it is resolved.
Your routine (see "Your Routine Right Now") is your default. When it says to
head somewhere, your action this tick should move you there, and after any pause
your next action goes back to that destination.
Whether something you see is worth pausing your routine for — a person you know,
someone speaking to you, ground worth recording — is a judgement your Rules
govern. Read them; they are written for you specifically.
Staying in character is good, but character quirks (curiosity, distraction)
color HOW you travel — they do not cancel WHERE you are going.

There are two kinds of direction, and the difference matters.

COMPASS directions — north, south, east, west and the diagonals — always mean
the same thing. Your position, the grid, the places you know and the four views
of every surveyed cell are all recorded in compass terms. Use these whenever you
are deciding WHERE TO GO: leaving somewhere, retracing your steps, heading for
unexplored ground.

BODY-RELATIVE directions — forward, forward-left, forward-right, left, right,
back — are measured from the way your body happens to be pointing right now,
which is on the "Facing" line above and changes every time you walk or turn
around. "forward" is the view described above. Use these only for reacting to
what is in the picture this instant ("step forward-left around that car").
Never use "back" to mean "the way I came" — say the compass heading instead;
the "Travel" line above tells you exactly which one that is.

Prefer a specific direction over wandering.

You navigate by what you SEE, not by what the ground will physically let you
cross. If the way toward your destination is a field of crops, tall grass, mud,
water, or other rough ground that is not a path or open passage, do not walk
into it — choose a route along roads, paths, and open ground instead, even if
you could push straight through. Go the way a person actually would.

Never walk through a person, animal, or vehicle. If a sense reports one
directly ahead while you travel, step around it: walk_to forward-left or
forward-right past it, then continue to your destination.
If your walk was halted with someone close ahead, you are already at a
comfortable distance — talk to them or act from right here; do not walk
closer. If you were only passing by, step around them instead.

If a sense says you have NOT advanced (you are stuck) or reports a structure,
foliage, or obstacle directly ahead, the straight path to your destination is
blocked by scenery — a wall, a fence, a field. Do NOT re-issue the same walk_to;
it will only wedge you against the same thing again. Turn aside: walk_to the
compass heading you came from, or one at right angles to it, to get clear of the
obstacle, then head for your destination again from the new angle. Getting
around it is your priority this tick.

If nothing is scheduled right now and nothing in view needs your attention, what
you do with the free time is up to your Character, Goals and Rules — some people
go looking, some stay at their post.

The "Place" line above is what you have previously called the spot you are standing on (empty means you have never named it). If you can tell what this place is — from the image, your goals, or your memories — name it in the "place" field; it is saved to your map so next time you will know you have been here before.
{sense_note}
Based on what you observe, choose exactly ONE next action. Return ONLY valid JSON: no prose, no markdown fences.

If and only if the active task under "Right now" uses completion
`time_or_llm_confirmed`, and this action will finish that entire objective, set
`task_completion` to {{"task_id":"<exact active id>","confirmed":true,
"evidence":"<one grounded sentence>"}}. Otherwise set it to null. Never confirm
an interrupted task.

{{
  "agent_id": "{agent_id}",
  "thought_summary": "one sentence describing what you see and why",
  "action": {{
    "type": "..."
  }},
  "place": "short name for the spot you are standing on (e.g. 'vegetable truck', 'village square'), or null if unsure",
  "speech": null,
  "task_completion": null,
  "memory_update": null,
  "importance": 0.5
}}
"""

# Wake-up orientation at simulation start: where am I, what time is it, where
# should I be. Sent with the 180-degree sweep views when available — the answer
# comes from the agent's authored markdown plus what it can see.
_USER_TEMPLATE_WAKE = """\
## Your Memories
{memories}

## Waking Up
It is {world_time}. You are just waking up and getting your bearings.
{views_text}

## Your Location
x={x:.0f}, y={y:.0f}, z={z:.0f}
Grid cell: {grid_cell}
Place: {place}
{known_line}

## Your Schedule Right Now
{schedule_line}

{agenda_context}

## Where You Can Go Next — neighboring grid cells (one step ~15m away)
{next_cells_text}

Get your bearings by asking yourself, in character:
1. Where am I? Use the place label, your memories, and what you can see.
   If you have NOT been here before, name the place — it gets saved to the shared map.
2. The schedule verdict above already says whether you are where you should be —
   trust it over what you think you remember about the town.
   - Already there: stay here and do the scheduled task (idle, observe, speak to
     someone nearby). Do NOT walk anywhere.
   - Not there yet: your first action should start getting you there.

Return ONLY valid JSON: no prose, no markdown fences.

{{
  "agent_id": "{agent_id}",
  "thought_summary": "one sentence: where you are, what time it is, where you should be",
  "current_goal": "what you intend to do right now, in first person",
  "action": {{"type": "..."}},
  "place": "short name for the spot you woke up at, or null if unsure",
  "memory_update": "one short line worth remembering about waking up here, or null",
  "importance": 0.7
}}
"""

# Fallback for when no screenshot is available (Unreal offline, capture failed).
_USER_TEMPLATE = """\
## Your Memories
{memories}

## Current World Observation
```json
{observation}
```

## Current Goal
{current_goal}

## What You Just Heard
{heard_note}

## Active Interruption
{active_interrupt_note}

## Survey State Of The Cell You Are Standing In
{cell_survey_note}

{agenda_context}

Choose exactly ONE next action. Return ONLY valid JSON: no prose, no markdown fences.

If and only if the active task under "Right now" uses completion
`time_or_llm_confirmed`, and this action will finish that entire objective, set
`task_completion` to {{"task_id":"<exact active id>","confirmed":true,
"evidence":"<one grounded sentence>"}}. Otherwise set it to null.

{{
  "agent_id": "{agent_id}",
  "thought_summary": "one sentence",
  "action": {{
    "type": "..."
  }},
  "speech": null,
  "task_completion": null,
  "memory_update": null,
  "importance": 0.5
}}
"""


class LLMRouter:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._clients = {}

    def _anthropic_client(self):
        if "anthropic" not in self._clients:
            import anthropic
            self._clients["anthropic"] = anthropic.Anthropic(
                api_key=self._resolve_api_key("anthropic")
            )
        return self._clients["anthropic"]

    def _openai_client(self):
        if "openai" not in self._clients:
            from openai import OpenAI
            self._clients["openai"] = OpenAI(api_key=self._resolve_api_key("openai"))
        return self._clients["openai"]

    def _resolve_provider(self, agent: "Agent") -> str:
        _reload_env()
        per_agent = agent.state.get("llm_provider") or agent.state.get("provider")
        provider = per_agent or os.environ.get("LLM_PROVIDER") or "anthropic"
        return str(provider).strip().lower()

    def _resolve_api_key(self, provider: str) -> str:
        _reload_env()
        if provider == "ollama":
            return "local"  # Ollama runs without auth; sentinel satisfies the key guard
        if self.api_key:
            return self.api_key
        if provider == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        return os.environ.get("ANTHROPIC_API_KEY", "")

    def _resolve_model(self, agent: "Agent", provider: str) -> Optional[str]:
        _reload_env()
        """Resolve which model to use for this agent.

        Priority:
          1. agent.state["model"]      - per-agent override (also the only way
                                         to enable an LLM for a Tier 3 agent)
          2. Tier 3 short-circuit      - Tier 3 = no LLM by design
          3. LLM_MODEL env var         - provider-agnostic global default
          4. provider model env var    - OPENAI_MODEL or ANTHROPIC_MODEL
          5. provider tier mapping     - built-in fallback
        """
        per_agent = agent.state.get("model")
        if per_agent:
            return per_agent

        if agent.tier == 3:
            return None

        env_default = os.environ.get("LLM_MODEL")
        if env_default:
            return env_default

        provider_env = {
            "openai": "OPENAI_MODEL",
            "anthropic": "ANTHROPIC_MODEL",
            "ollama": "OLLAMA_MODEL",
        }.get(provider)
        if provider_env and os.environ.get(provider_env):
            return os.environ[provider_env]

        if provider == "ollama":
            return "qwen3.5:4b"

        if provider == "openai":
            return {
                1: "gpt-5.4",
                2: "gpt-5.4-mini",
            }.get(agent.tier, "gpt-5.4-mini")

        # Decision role only — vision resolves separately (perception.py), so the
        # VLM stays on Haiku 4.5 regardless of what an APC decides with.
        return {
            1: "claude-sonnet-5",
            2: "claude-sonnet-5",
        }.get(agent.tier, "claude-sonnet-5")

    def _system_text(self, agent: "Agent") -> str:
        action_lines = "\n".join(
            f"  {_ACTION_SCHEMAS.get(a, '{\"type\": \"' + a + '\"}')}"
            for a in agent.allowed_actions
        )
        return _SYSTEM_TEMPLATE.format(
            character=agent.character_text.strip(),
            goals=agent.goals_text.strip(),
            rules=agent.rules_text.strip(),
            actions=action_lines,
        )

    def orient(self, agent: "Agent", context: dict, memories: list[dict]) -> Optional[dict]:
        """Wake-up orientation at simulation start (the spool-up).

        One text-only call: given the agent's own character/goals/rules, the
        world time, where it is standing, and its perceived 180-degree
        look-around (``context["views"]`` — captions/landmarks/characters from
        the vision perceiver), the agent states where it should be, what it
        intends, and its first action — returned as ``{"thought_summary",
        "current_goal", "action", "place", "memory_update", "importance"}``,
        or None on failure.
        """
        provider = self._resolve_provider(agent)
        model = self._resolve_model(agent, provider)
        if not model:
            return None
        if not self._resolve_api_key(provider):
            logger.error("%s API key not set - skipping wake-up", provider)
            return None

        views = context.get("views") or []
        if views:
            lines = []
            for v in views:
                bits = []
                if v.get("caption"):
                    bits.append(v["caption"])
                names = [lm["label"] for lm in v.get("landmarks") or []]
                if names:
                    bits.append("you see: " + ", ".join(names))
                chars = [c["label"] for c in v.get("characters") or []]
                if chars:
                    bits.append("characters: " + ", ".join(chars))
                if v.get("places"):
                    bits.append("your map calls this way: " + ", ".join(v["places"]))
                lines.append(f"- {v['direction']}: " + ("; ".join(bits) if bits else "(nothing notable)"))
            views_text = (
                "You turn through the four absolute cardinal views of this place:\n"
                + "\n".join(lines)
            )
        else:
            description = str(context.get("place_description") or "").strip()
            views_text = (
                "Your saved place visual memory describes it as:\n" + description
                if description else
                "You cannot see anything yet — rely on your memories and the place label."
            )

        loc = context.get("location") or {}
        place = context.get("place") or []
        known = context.get("known_place")
        fam = context.get("familiarity") or {}
        visit_count = fam.get("visit_count", 0)
        named_by_me = fam.get("named_by_me", False)

        if named_by_me and visit_count > 0:
            known_line = (
                f"**You named this place yourself** ('{known}'). You have been here "
                f"{visit_count} time(s). This is YOUR place — you know exactly where you are. "
                f"If your goals say to be here, you are already there. Act accordingly."
            )
        elif visit_count > 0 and known:
            known_line = (
                f"You know this place — you have been here {visit_count} time(s). "
                f"The shared map calls it '{known}'."
            )
        elif known:
            known_line = (
                f"This place ('{known}') is on the shared map. You have not been here before."
            )
        else:
            known_line = "You have not been here before — if you can tell what it is, name it."
        # When a confirmed place name exists it takes over the Place: line entirely.
        # Raw compass observations may include stale or misleading labels (e.g. a
        # landmark named "motel area" observed from this cell that contradicts the
        # formal place name), so we suppress them when the identity is certain.
        if known:
            place_str = known
        else:
            place_str = ", ".join(place) if place else "unknown"

        user_text = _USER_TEMPLATE_WAKE.format(
            agent_id=agent.agent_id,
            memories=_memory_lines(memories),
            world_time=context.get("world_time", "unknown"),
            views_text=views_text,
            grid_cell=_grid_text(context.get("grid")),
            place=place_str,
            known_line=known_line,
            schedule_line=_wake_schedule_line(context.get("schedule")),
            agenda_context=agenda.prompt_text(
                context.get("agenda") or (context.get("schedule") or {}).get("agenda")),
            next_cells_text=_direction_lines(context.get("directions")),
            x=loc.get("x", 0),
            y=loc.get("y", 0),
            z=loc.get("z", 0),
        )

        # #84: the wake prompt is a separate path — it builds its own text and
        # dispatches directly, so decide()'s boundary check never sees it. Every
        # path that reaches a model gets the alarm, or the alarm means nothing.
        prompt_payload.check_clean(user_text, agent.agent_id, "wake prompt")

        try:
            if provider == "ollama":
                raw = self._decide_ollama(model, self._system_text(agent), user_text)
            elif provider == "openai":
                raw = self._decide_openai(model, self._system_text(agent), user_text)
            else:
                raw = self._decide_anthropic(model, self._system_text(agent), user_text)
            orientation = _load_decision_json(raw)
            logger.info(
                "[%s] %s/%s woke up: %s",
                agent.agent_id, provider, model,
                orientation.get("thought_summary", "")[:120],
            )
            return orientation
        except json.JSONDecodeError as e:
            logger.warning(f"[{agent.agent_id}] Wake-up returned invalid JSON: {e}\nRaw: {raw!r}")
            return None
        except Exception as e:
            logger.error(f"[{agent.agent_id}] Wake-up LLM call failed: {e}")
            return None

    def decide(self, agent: "Agent", observation: dict, memories: list[dict]) -> Optional[dict]:
        provider = self._resolve_provider(agent)
        model = self._resolve_model(agent, provider)
        if not model:
            return _idle_decision(agent.agent_id, "Tier 3 - no LLM assigned")

        api_key = self._resolve_api_key(provider)
        if not api_key:
            logger.error("%s API key not set - returning idle", provider)
            return _idle_decision(agent.agent_id, f"No {provider} API key configured")

        mem_lines = _memory_lines(memories)
        system_text = self._system_text(agent)

        if observation.get("seen") is not None or observation.get("image_path"):
            loc = observation.get("location") or {}
            action_state = observation.get("current_action") or "idle"
            if observation.get("ai_state"):
                action_state += f" ({observation['ai_state']})"
            known = observation.get("known_characters") or []
            known_text = ", ".join(known) if known else "none known yet"
            user_text = _USER_TEMPLATE_VISION.format(
                agent_id=agent.agent_id,
                memories=mem_lines,
                known_characters=known_text,
                nearby_character_lines=_nearby_character_lines(observation.get("nearby_characters")),
                grid_cell=_grid_text(observation.get("grid")),
                place=_place_text(observation),
                x=loc.get("x", 0),
                y=loc.get("y", 0),
                z=loc.get("z", 0),
                facing=_facing_text(observation.get("rotation")),
                travel_note=_travel_note(observation.get("travel")),
                direction_lines=_direction_lines(
                    observation.get("directions"),
                    (observation.get("seen") or {}).get("landmarks"),
                    _yaw_of_rotation(observation.get("rotation"))),
                frontier_note=_frontier_note(observation.get("frontier")),
                seen=_seen_text(observation.get("seen"), observation.get("breadcrumbs")),
                world_time=observation.get("world_time", "unknown"),
                current_action=action_state,
                current_goal=agent.current_goal,
                active_interrupt_note=_active_interrupt_note(observation.get("active_interrupt")),
                cell_survey_note=_cell_survey_note(observation),
                heard_note=_heard_note(observation),
                agenda_context=agenda.prompt_text(observation.get("agenda")),
                sense_note=_sense_note(observation),
                schedule_note=_schedule_note(observation.get("schedule")),
                route_map_note=_route_map_note(observation),
                acquaintance_lines=_acquaintance_lines(observation.get("acquaintances")),
                known_place_lines=_known_place_lines(observation.get("known_places")),
                episode_lines=_episode_lines(observation.get("recent_episodes")),
            )
        else:
            # #84: the declared payload, not the raw dict. This line used to be
            # a deny-list of exactly one key, so every engine field the runtime
            # had ever attached went to the model and every NEW key leaked by
            # default. Now a field is sent only if the contract names it.
            obs_for_text = prompt_payload.project(observation)
            user_text = _USER_TEMPLATE.format(
                agent_id=agent.agent_id,
                memories=mem_lines,
                observation=json.dumps(obs_for_text, indent=2),
                current_goal=agent.current_goal,
                active_interrupt_note=_active_interrupt_note(observation.get("active_interrupt")),
                cell_survey_note=_cell_survey_note(observation),
                heard_note=_heard_note(observation),
                agenda_context=agenda.prompt_text(observation.get("agenda")),
            )

        # #84: the boundary alarm. The allow-list above is what PREVENTS a leak;
        # this is what makes one visible if a renderer reintroduces it. It reports
        # and never rewrites — a prompt quietly altered on its way out is harder
        # to debug than one that is wrong and says so (rule 12).
        prompt_payload.check_clean(user_text, agent.agent_id, "decision prompt")
        prompt_payload.check_clean(system_text, agent.agent_id, "system prompt")

        # Travel ticks may carry a rendered route map (#6b/WP5) — attach it so
        # the multimodal decision call literally sees the terrain between here
        # and the destination. OpenAI's path here is text-only; it still gets
        # the map's facts through the "Your Map" prompt section.
        map_image = (observation.get("route_map") or {}).get("image_path")
        try:
            if provider == "ollama":
                raw = self._decide_ollama(model, system_text, user_text, image_path=map_image)
            elif provider == "openai":
                raw = self._decide_openai(model, system_text, user_text)
            elif provider == "anthropic":
                raw = self._decide_anthropic(model, system_text, user_text, image_path=map_image)
            else:
                logger.error("[%s] Unknown LLM provider: %s", agent.agent_id, provider)
                return _idle_decision(agent.agent_id, f"Unknown LLM provider: {provider}")

            logger.debug(f"[{agent.agent_id}] Raw LLM response: {raw}")
            decision = _load_decision_json(raw)
            logger.info(
                "[%s] %s/%s decided: %s - %s",
                agent.agent_id,
                provider,
                model,
                decision.get("action", {}).get("type"),
                decision.get("thought_summary", "")[:80],
            )
            return decision

        except json.JSONDecodeError as e:
            logger.warning(f"[{agent.agent_id}] LLM returned invalid JSON: {e}\nRaw: {raw!r}")
            return None
        except Exception as e:
            logger.error(f"[{agent.agent_id}] LLM call failed: {e}")
            return None

    def ask(self, agent: "Agent", prompt: str) -> Optional[str]:
        """Generic text completion through the agent's resolved provider/model.

        Used by the planner to generate a daily schedule (the prompt is
        self-contained, so the system message is minimal). Returns the raw text,
        or None if there is no model/key or the call fails — callers degrade
        gracefully (the planner falls back to a default schedule).
        """
        provider = self._resolve_provider(agent)
        model = self._resolve_model(agent, provider)
        if not model:
            return None
        if not self._resolve_api_key(provider):
            logger.error("%s API key not set - cannot ask()", provider)
            return None
        system = "You are a careful planning assistant. Follow the instructions exactly and return only what is requested."
        # The planner builds this prompt itself (#84). Guarded like every other
        # path that reaches a model — a schedule prompt naming an actor label
        # would teach the model engine vocabulary just as surely as a tick does.
        prompt_payload.check_clean(prompt, agent.agent_id, "ask prompt")
        try:
            if provider == "ollama":
                return self._decide_ollama(model, system, prompt)
            if provider == "openai":
                return self._decide_openai(model, system, prompt)
            return self._decide_anthropic(model, system, prompt)
        except Exception as e:
            logger.error("[%s] ask() failed: %s", agent.agent_id, e)
            return None

    def chat(self, agent: "Agent", transcript: list[dict], context: dict,
             memories: list[dict]) -> Optional[str]:
        """Return one in-character direct-chat reply as plain text.

        This is deliberately separate from ``decide``: an open conversation
        freezes physical action, so the model must answer the operator without
        emitting action JSON or claiming that an action already happened.
        """
        provider = self._resolve_provider(agent)
        model = self._resolve_model(agent, provider)
        if not model:
            return None
        if not self._resolve_api_key(provider):
            logger.error("%s API key not set - cannot chat()", provider)
            return None

        system = f"""You are {agent.display_name}, a character in a living world.

Character:
{agent.character_text.strip()}

Goals:
{agent.goals_text.strip()}

Rules:
{agent.rules_text.strip()}

Reply directly to the operator in character. Be concise and concrete. You may
accept, question, or decline guidance according to your character and grounded
facts. The conversation has paused your movement: do not claim you have already
performed an action. Do not output JSON or markdown."""
        lines = [
            f"Current goal: {context.get('current_goal') or agent.current_goal}",
            f"Paused route destination: {context.get('route_destination') or 'none'}",
            "Relevant memories:",
            _memory_lines(memories),
            "Conversation:",
        ]
        for message in transcript[-20:]:
            role = "Operator" if message.get("role") == "operator" else agent.display_name
            lines.append(f"{role}: {str(message.get('text') or '').strip()}")
        lines.append(f"Reply as {agent.display_name}:")
        prompt = "\n".join(lines)
        # The operator-chat path builds its own prompt too (#84).
        prompt_payload.check_clean(prompt, agent.agent_id, "chat prompt")
        prompt_payload.check_clean(system, agent.agent_id, "chat system prompt")
        try:
            if provider == "ollama":
                return self._decide_ollama(model, system, prompt)
            if provider == "openai":
                return self._openai_text(model, system, prompt)
            return self._decide_anthropic(model, system, prompt)
        except Exception as e:
            logger.error("[%s] chat() failed: %s", agent.agent_id, e)
            return None

    def _decide_ollama(
        self, model: str, system_text: str, user_text: str, image_path: str | None = None
    ) -> str:
        from .ollama_adapter import chat
        return _strip_markdown_fences(chat(model, system_text, user_text, image_path=image_path))

    def _decide_anthropic(
        self, model: str, system_text: str, user_text: str, image_path: str | None = None
    ) -> str:
        if image_path:
            content = [
                _image_block(image_path),
                {"type": "text", "text": user_text},
            ]
        else:
            content = user_text
        return self._anthropic_call(model, system_text, content)

    def _anthropic_call(self, model: str, system_text: str, content) -> str:
        client = self._anthropic_client()
        response = client.messages.create(
            model=model,
            # max_tokens caps thinking AND response text together, and Sonnet 5
            # thinks by default. At 1024 a tick could spend the whole budget
            # reasoning and return a thinking block with no decision at all
            # (SR35, 19:53:07) — the model wasn't broken, it ran out of room
            # mid-thought. Sonnet 5 also tokenizes ~30% heavier than Haiku 4.5.
            max_tokens=4096,
            # Declared rather than defaulted: the sim's whole premise is that the
            # LLM reasons about where to go, so thinking stays on. `medium` keeps
            # that reasoning bounded — a tick is one short JSON decision, not an
            # essay, and every tick pays for the thinking it does.
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            system=[{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": content}],
        )
        # Models with thinking enabled (e.g. Sonnet 5) put a ThinkingBlock before
        # the TextBlock, so content[0] is not guaranteed to have .text.
        text = "".join(b.text for b in response.content if b.type == "text")
        if not text:
            blocks = [b.type for b in response.content]
            if response.stop_reason == "max_tokens":
                raise ValueError(
                    f"ran out of tokens before deciding — spent all {response.usage.output_tokens} "
                    f"output tokens on {blocks} and never wrote a decision; raise max_tokens "
                    f"or lower effort"
                )
            raise ValueError(f"No text block in response (blocks: {blocks}, "
                             f"stop_reason: {response.stop_reason})")
        return _strip_markdown_fences(text.strip())

    def _decide_openai(self, model: str, system_text: str, user_text: str) -> str:
        import requests

        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self._resolve_api_key('openai')}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "instructions": system_text,
                "input": user_text,
                "max_output_tokens": 512,
                "text": {"format": {"type": "json_object"}},
            },
            timeout=60,
        )
        if response.status_code >= 400:
            logger.error("OpenAI API error %s: %s", response.status_code, response.text[:500])
            response.raise_for_status()

        payload = response.json()
        output_text = payload.get("output_text")
        if output_text:
            return _strip_markdown_fences(output_text.strip())

        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return _strip_markdown_fences(text.strip())

        raise ValueError("OpenAI response did not include output_text")

    def _openai_text(self, model: str, system_text: str, user_text: str) -> str:
        """OpenAI Responses call for plain conversational text, not action JSON."""
        import requests

        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self._resolve_api_key('openai')}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "instructions": system_text,
                "input": user_text,
                "max_output_tokens": 512,
            },
            timeout=60,
        )
        if response.status_code >= 400:
            logger.error("OpenAI API error %s: %s", response.status_code, response.text[:500])
            response.raise_for_status()
        payload = response.json()
        output_text = payload.get("output_text")
        if output_text:
            return _strip_markdown_fences(output_text.strip())
        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return _strip_markdown_fences(text.strip())
        raise ValueError("OpenAI response did not include output_text")


def _memory_lines(memories: list[dict]) -> str:
    return "\n".join(
        f"- [{m.get('importance', 0):.1f}] {m.get('text', '')}"
        for m in memories
    ) or "No memories yet."


def _image_block(image_path: str) -> dict:
    import base64
    image_data = base64.standard_b64encode(open(image_path, "rb").read()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}}


def _sense_note(observation: dict) -> str:
    """Raw movement senses — facts only, no inference, no advice.

    ``stuck`` (not advancing while moving) and ``blocker`` (something directly
    ahead on the travel path, B7) are independent: a person can be ahead before
    the agent is wedged on them. The LLM reasons; the lizard brain senses.
    """
    lines = []
    # Whether the last order actually moved the body. The engine reports a walk
    # as "accepted" the moment it takes the command, so an order that achieved
    # nothing looked identical to one that crossed a field (#59).
    last_move = observation.get("last_move")
    if isinstance(last_move, dict) and last_move.get("intent"):
        if last_move.get("stalled"):
            lines.append(
                f"Sense: you ordered \"{last_move['intent']}\" last tick and have "
                f"not moved since — you are against something that stopped you.")
        elif last_move.get("moved_cm") is not None:
            lines.append(
                f"Sense: your last order (\"{last_move['intent']}\") moved you "
                f"{round(last_move['moved_cm'] / 100, 1)} m.")
        went = last_move.get("went")
        if isinstance(went, dict) and went.get("heading"):
            lines.append(
                f"Sense: you ordered \"{last_move['intent']}\" and ended up "
                f"{went['heading']} of where you started. The ground you were "
                f"walked over is not the straight line you asked for — something "
                f"between you and that point sent you round.")
        plan = last_move.get("plan")
        if isinstance(plan, dict) and plan.get("why"):
            lines.append(f"Sense: {plan['why']}.")
    tried = _tried_here_text(last_move)
    if tried:
        lines.append(tried)
    wedge = _wedge_text(observation.get("wedge"))
    if wedge:
        lines.append(wedge)
    here_no_go = observation.get("here_no_go")
    if isinstance(here_no_go, dict):
        # SR44: the patch only rendered on step targets, so the APC stood in
        # the yard it had just refused and refused it again, eight ticks
        # running. Underfoot is a fact too.
        lines.append(
            f"Sense: you are STANDING in ground already refused "
            f"(by {here_no_go.get('refused_by', 'someone')}: "
            f"{here_no_go.get('reason', '?')}). It is already recorded — do NOT "
            f"refuse it again. Leave it: walk a proven direction or RETRACE.")
    for bounce in observation.get("bounce") or []:
        # Walked in and straight back out, repeatedly — the pocket will not
        # change on the next try (#26). Stated with the way out of the loop.
        lines.append(
            f"Sense: you have walked into cell {bounce.get('cell')} and straight "
            f"back out {bounce.get('count')} times this run. That ground is a "
            f"pocket that leads nowhere. Do not try it head-on again — refuse "
            f"the bad ground (refuse_cell with \"scope\": \"spot\") or approach "
            f"that cell from a different side.")
    if observation.get("stuck"):
        lines.append("Sense: you have not advanced for several ticks while moving.")
    blocker = observation.get("blocker")
    if blocker:
        # #61: the navmesh is baked once and knows nothing about a truck parked on
        # it, so "navmesh clear" and "path physically blocked" disagree exactly
        # here. Metres, not centimetres, and the distance is stated plainly — the
        # standoff is named as a fact so the model can judge it, never as an order.
        metres = blocker['distance_cm'] / 100.0
        lines.append(
            f"Sense: your forward probe struck a {blocker['category']} "
            f"{metres:.1f} m directly ahead of you. The navmesh does not know it "
            f"is there. Walking straight ahead runs into it."
        )
        # #81: the body-box facts. A thin ray could say "something ahead" but
        # never "the gap is on your left" — and in SR46 Dufus refused three
        # patches accurately and still kept landing in them, because a 15 m step
        # cannot aim finer than a 9 m trap. Stated as measurement, never advice.
        if blocker.get("fits") is False:
            openings = [str(c).replace("_", " ") for c in (blocker.get("open_columns") or [])]
            if blocker.get("raster_silent"):
                lines.append(
                    f"Sense: your body DOES NOT FIT straight ahead — measured "
                    f"clearance {blocker.get('clearance_cm', 0.0) / 100.0:.1f} m — "
                    f"and the scan could NOT tell which side the gap is on. "
                    f"Whatever stopped you passed between the scan lines.")
            elif blocker.get("fully_blocked") or not openings:
                lines.append(
                    "Sense: your body DOES NOT FIT ahead and NO side is open — "
                    "you are completely blocked in this direction. This was "
                    "measured, not guessed.")
            else:
                lines.append(
                    f"Sense: your body DOES NOT FIT straight ahead. Measured "
                    f"clearance {blocker.get('clearance_cm', 0.0) / 100.0:.1f} m. "
                    f"The gap is on your: {', '.join(openings)}.")
        elif blocker.get("fits") is True:
            lines.append(
                "Sense: your body DOES fit past it — the way ahead is passable, "
                "though something is beside your path.")
        if blocker.get("halted"):
            lines.append("Sense: your walk has been halted.")
    return ("\n" + "\n".join(lines) + "\n") if lines else ""


def _tried_here_text(last_move: dict | None) -> str:
    """Every heading already attempted from this exact spot, and what's left (#60).

    SR40 alternated east and southeast for eight ticks against the same
    obstacle, because each tick only knew the previous order had failed and the
    other direction therefore looked untried. Both halves are stated: what has
    failed here, and what has not been attempted from here — the second is what
    ends the loop, and it is a fact, not a suggestion. Which one to take, or
    whether to speak to whoever is in the way instead, stays the model's call.
    """
    tried = (last_move or {}).get("tried_here")
    if not isinstance(tried, dict) or not tried:
        return ""
    failed = ", ".join(f"{d} ({round(cm / 100, 1)} m)" for d, cm in tried.items())
    untried = [w for w in _COMPASS_WORD.values() if w not in tried]
    line = f"Sense: from this exact spot you have already tried: {failed}."
    if untried:
        line += f" Not yet tried from here: {', '.join(untried)}."
    return line


def _wedge_text(wedge: dict | None) -> str:
    """How long the stall has been going on, and the ways out somebody has walked (#65).

    ``tried_here`` says which headings failed *here*; this says *this has been
    going on for N ticks* and names the neighbouring cells with proven footing
    that have not been tried yet. SR39 and SR40 both burned their endgame on one
    spot while every individual line in the prompt was true — the missing fact
    was the run, and the missing answer was the one the shared map already had.

    Silent below the budget: a single stall is ordinary and does not need a
    speech. "NONE KNOWN" is stated rather than hidden — an APC with no recorded
    good ground nearby is in a different situation from one ignoring an open road.
    """
    if not isinstance(wedge, dict) or wedge.get("escapes") is None:
        return ""
    escapes = wedge["escapes"]
    line = (f"Sense: you have now been stopped on this exact spot for "
            f"{wedge.get('run')} orders in a row.")
    if escapes:
        ways = ", ".join(
            f"{e['direction']} (cell {e['cell']} — {e['footing']}, walked "
            f"{e['samples']}x)" for e in escapes[:4])
        line += (f" Ground somebody has actually walked, that you have NOT tried "
                 f"from here: {ways}.")
    else:
        line += (" No neighbouring cell has recorded footing anybody has walked —"
                 " nothing proven is available; you are choosing from the view alone.")
    return line


def _active_interrupt_note(record: dict | None) -> str:
    """Render one grounded active interruption without inventing a speaker."""
    if not isinstance(record, dict):
        return ("No active interruption.\nNo deterministic survey is active. "
                "Do not claim any compass view was captured or saved.")
    source = str(record.get("source") or "unknown requester").strip()
    reason = str(record.get("reason") or "no reason supplied").strip()
    kind = str(record.get("kind") or "interruption").strip()
    priority = record.get("priority", "?")
    direction = ""
    payload = record.get("payload")
    chat = payload.get("chat") if isinstance(payload, dict) else None
    if isinstance(chat, dict) and chat.get("state") == "guiding":
        direction = str(chat.get("direction") or "").strip()
    direction_line = f"\nOperator direction to follow now: {direction}" if direction else ""
    survey_line = ""
    if kind == "survey":
        progress = payload.get("survey_progress") if isinstance(payload, dict) else None
        if isinstance(progress, dict):
            completed = [str(x) for x in progress.get("completed_headings") or []]
            failed = [str(x) for x in progress.get("failed_headings") or []]
            saved = ", ".join(completed) if completed else "none"
            current = progress.get("current_heading") or "none"
            survey_line = (
                f"\nAuthoritative deterministic survey progress: "
                f"{len(completed)}/4 saved ({saved}); current heading {current}; "
                f"failed {', '.join(failed) if failed else 'none'}. "
                "Do not claim an uncaptured heading was saved."
            )
    return (f"Priority {priority} {kind} from {source}: {reason}{direction_line}{survey_line}\n"
            "This active interruption outranks your routine until it is resolved.")


def _heard_note(observation: dict) -> str:
    """Render speech this agent actually received this tick (#45).

    The reaction gate lets "someone is speaking to you" interrupt the routine;
    this is the only place that clause can get a grounded speaker from, so an
    empty result must say plainly that nobody spoke — otherwise the model is
    free to imagine a conversation.
    """
    heard = observation.get("heard")
    if not heard:
        return "Nobody has spoken to you. Do not answer or refer to anything unsaid."
    lines = [f'- {item.get("speaker", "someone")} said: "{item.get("text", "")}"'
             + (f' ({item["distance_cm"]:.0f} cm away)'
                if item.get("distance_cm") is not None else "")
             for item in heard[:5]]
    speakers = ", ".join(dict.fromkeys(str(item.get("speaker", "someone"))
                                       for item in heard[:5]))
    return ("These people spoke within earshot just now. Being spoken to is one of the "
            "two things that may interrupt your routine — you may answer this tick.\n"
            + "\n".join(lines)
            + f"\nIf you decide to answer {speakers}, the action is speak_to with your "
              "words in \"message\". Deciding to answer and then choosing idle or "
              "observe leaves them standing in silence — nothing you did not put in a "
              "speak_to message was ever said out loud.")


def _cell_survey_note(observation: dict) -> str:
    """The authoritative survey verdict for the cell underfoot (#40).

    SR28 showed that "no survey is active" was not enough grounding: with no
    statement about *this cell*, cognition kept narrating that headings here
    still needed surveying after the survey had already resolved. This states
    the deterministic verdict and forbids both inventions explicitly.
    """
    facts = observation.get("cell_survey")
    if not isinstance(facts, dict):
        return ("Survey state for this cell is unavailable. Do not claim this cell "
                "needs surveying and do not claim any view here was captured or saved.")

    cell = facts.get("cell", "?")
    total = facts.get("total_headings") or 4
    if facts.get("active_here"):
        completed = [str(x) for x in facts.get("completed_headings") or []]
        failed = [str(x) for x in facts.get("failed_headings") or []]
        return (
            f"Cell ({cell}) is being surveyed right now: {len(completed)}/{total} headings "
            f"saved ({', '.join(completed) if completed else 'none'}); "
            f"failed {', '.join(failed) if failed else 'none'}. "
            "Only the deterministic survey saves headings. Do not claim you saved a "
            "heading that is not listed above."
        )
    if facts.get("fresh"):
        return (
            f"Cell ({cell}) has a complete, current community survey. It does NOT need "
            "surveying and no heading here is missing. Do not say you need to survey, "
            "observe, or capture headings here, and do not claim you saved a view — "
            "no capture is happening this tick."
        )
    return (
        f"Cell ({cell}) has no current community survey. You are standing in it, so "
        f"you can survey it now with {{\"type\": \"survey_here\"}} — that captures all "
        f"{total} headings over the next few ticks and adds this cell to the shared map. "
        "Nothing surveys it unless you choose to. You are not surveying it right now, "
        "so do not claim any view here has been captured or saved."
    )


def _route_map_note(observation: dict) -> str:
    """The "Your Map" section for a travel tick (#6b/WP5) — facts + the image
    legend. Empty when no route map was built this tick. The map describes the
    terrain; charting the course stays with the LLM."""
    route = observation.get("route_map")
    if not route:
        return ""
    to = route.get("to") or {}
    dest = to.get("name") or "your destination"
    lines = [f'\n## Your Map — the area between you and "{dest}"']
    if to.get("bearing"):
        lines.append(f"The destination is {to['bearing']} of you, about {to['distance_m']} m away.")
    else:
        lines.append("You are already in the destination's grid cell.")
    named = [c for c in route.get("cells") or [] if c.get("name")]
    if named:
        lines.append("Known places on this map: "
                     + "; ".join(f'"{c["name"]}" at cell ({c["cell"][0]},{c["cell"][1]})'
                                 for c in named[:8]) + ".")
    if route.get("image_path"):
        lines.append("A top-down map image is attached: north is up; A (blue) = you, "
                     "B (red) = the destination; green cells are named places, tan cells "
                     "have been observed, gray cells are unknown. The numbers along the "
                     "edges are grid cell columns (top) and rows (left).")
    if route.get("truncated"):
        lines.append("The map is truncated — the destination area may extend past its edge.")
    lines.append("The map only shows what is known — chart your own course with walk_to.")
    return "\n".join(lines) + "\n"


def _facing_text(rotation) -> str:
    """Which way the body is pointing, in compass terms (#56).

    A raw yaw is not something the model can reason with, and body-relative
    words ("forward", "back") are measured from exactly this value — so it has
    to be legible, or those words are a guess.
    """
    yaw = None
    if isinstance(rotation, dict) and rotation.get("y") is not None:
        yaw = float(rotation["y"])
    elif isinstance(rotation, (list, tuple)) and len(rotation) >= 2:
        yaw = float(rotation[1])
    if yaw is None:
        return "unknown"
    return f"{yaw_to_compass(yaw)} (yaw {yaw:.0f} degrees)"


def _travel_note(travel: dict | None) -> str:
    """State the heading the APC actually arrived on, so retreat is expressible.

    SR34's model kept deciding "turn back the way I came" with nothing in the
    prompt saying which way that was.
    """
    if not travel or not travel.get("heading"):
        return "You have not travelled yet this run."
    return (f"You arrived here heading {travel['heading']} "
            f"({round(travel.get('distance_cm', 0) / 100)} m). "
            f"The way you came is {travel['came_from']} — "
            f"walk_to {_COMPASS_WORD[travel['came_from']]} to retrace it.")


def _acquaintance_lines(acquaintances: list | None) -> str:
    """People this agent has actually met, most familiar first (cap 8).

    Items come from SocialMemory.acquaintances():
    {name, meet_count, interaction_count, last_seen, ...}.
    """
    lines = []
    for a in (acquaintances or [])[:8]:
        name = str(a.get("name") or "").strip()
        if not name:
            continue
        parts = []
        if a.get("meet_count"):
            parts.append(f"met {a['meet_count']} times")
        if a.get("interaction_count"):
            parts.append(f"spoken with {a['interaction_count']} times")
        if a.get("last_seen"):
            parts.append(f"last seen {a['last_seen']}")
        if a.get("recently_greeted"):
            parts.append("already greeted recently — no need to say hi again")
        lines.append(f"- {name} — {', '.join(parts)}" if parts else f"- {name}")
    return "\n".join(lines) or "Nobody yet — you have not met anyone."


def _known_place_lines(places: list | None) -> str:
    """The agent's named-place map, nearest first (from AgentManager.known_places).

    Community places render bare; APC-owned places (#11.2) carry their owner —
    "My Home — N, 12 m (maren's place)" — so an agent can tell its own spots
    from someone else's.
    """
    lines = []
    for p in places or []:
        name = str(p.get("name") or "").strip()
        if not name:
            continue
        owner = str(p.get("owner") or "").strip()
        suffix = f" ({owner}'s place)" if owner else ""
        lines.append(f"- {name} — {p.get('bearing', '?')}, {round(p.get('distance_m') or 0)} m{suffix}")
    return "\n".join(lines) or "No named places yet — name places as you discover them."


def _episode_lines(episodes: list | None) -> str:
    """Relevant past episodes (from EpisodicLog.relevant): what happened where."""
    lines = []
    for e in episodes or []:
        if e.get("kind") == "summary":
            span = f"{e.get('first_time', '?')}–{e.get('last_time', '?')}"
            place = e.get("place") or "somewhere"
            lines.append(f"- [{span}] around {place}: {e.get('count', 0)} events")
            continue
        bits = []
        if e.get("action"):
            bits.append(str(e["action"]))
        saw = [s for s in (e.get("saw") or []) if s]
        if saw:
            bits.append("saw " + ", ".join(saw))
        where = e.get("place") or e.get("grid_cell") or "somewhere"
        lines.append(f"- [{e.get('world_time', '?')}] at {where}: {', '.join(bits) or 'nothing notable'}")
    return "\n".join(lines) or "Nothing memorable yet."


def _nearby_character_lines(characters: list | None) -> str:
    """Deterministic proximity facts from the current APC position snapshot."""
    lines = []
    for character in characters or []:
        name = str(character.get("name") or "").strip()
        if name:
            lines.append(f"- {name} — about {round((character.get('distance_cm') or 0) / 100)} m away")
    return "\n".join(lines) or "No other APC is nearby."


def _seen_text(seen: dict | None, breadcrumbs: list | None = None) -> str:
    """Render a perception result ({landmarks, characters, caption}) as prompt lines."""
    if not seen:
        return "(no view this tick)"
    if seen.get("error"):
        return f"(your vision failed this tick: {seen['error']})"
    lines = []
    if seen.get("caption"):
        lines.append(seen["caption"])
    if seen.get("footing"):
        lines.append(f"FOOTING: {seen['footing']}")
    if seen.get("ground_ahead"):
        lines.append(f"GROUND AHEAD (where a step this way lands): {seen['ground_ahead']}")
    path_ahead = str(seen.get("path_ahead") or "").strip()
    if path_ahead and path_ahead != "open":
        lines.append(f"PATH AHEAD: {path_ahead.replace('_', ' ')}")
    trail = _breadcrumb_text(breadcrumbs)
    if trail:
        lines.append(trail)
    for lm in seen.get("landmarks") or []:
        lines.append(f"- {lm['label']} ({lm.get('bearing', '?')}, {lm.get('distance', '?')})")
    for ch in seen.get("characters") or []:
        lines.append(f"- CHARACTER: {ch['label']} ({ch.get('bearing', '?')}, {ch.get('distance', '?')})")
    return "\n".join(lines) or "(nothing notable)"


def _breadcrumb_text(trail: list | None) -> str:
    """The legs the APC actually walked, oldest first, plus the way back (#58).

    One tick only ever shows the ground you are on now, so a two-cell ping-pong
    between rough patches is invisible from inside it — SR37 spent its last five
    decisions alternating between a cornfield and a lawn, each retreat correct on
    its own. Bare surfaces were not enough to escape it either: "field -> grass ->
    field" names the trap without naming a single place, so there was nothing to
    walk back to.

    RETRACE is the recorded headings reversed, in order. That is arithmetic on
    facts already stated, not counsel — the same derivation as ``came_from`` —
    and the model remains free to ignore it and strike out somewhere new.
    """
    if not trail:
        return ""
    lines = ["BREADCRUMBS (oldest first — ground you have actually stood on):"]
    for i, crumb in enumerate(trail):
        if not isinstance(crumb, dict):
            continue
        leg = f"  {i + 1}. cell {crumb.get('cell', '?')}"
        if crumb.get("heading"):
            leg += f" (walked {crumb['heading']}"
            if crumb.get("distance_cm"):
                leg += f" {round(crumb['distance_cm'] / 100)}m"
            leg += ")"
        leg += f" — {crumb.get('footing') or 'ground not reported'}"
        if i == len(trail) - 1:
            leg += "   <- you are here"
        lines.append(leg)
    back = [_OPPOSITE[c["heading"]] for c in reversed(trail)
            if isinstance(c, dict) and c.get("heading") in _OPPOSITE]
    if back:
        lines.append("RETRACE (undoes the trail above, in order): "
                     + " then ".join(back))
    return "\n".join(lines)


# Reversing a compass heading — the same pairing agent_manager uses for
# ``came_from``, kept here so the prompt text can state a retrace without
# importing the manager.
_OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E",
             "NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}


def _load_decision_json(raw: str) -> dict:
    """Parse a decision, tolerating a trailing sign-off after the JSON (#59).

    SR39 lost a whole decision to ``Extra data: line 1 column 207`` — the object
    was complete and well-formed, with prose after it. Throwing away a good
    decision because the model kept talking is our bug, not its. Anything that
    is not a complete leading JSON object still raises.
    """
    decoded, end = json.JSONDecoder().raw_decode(raw.strip())
    if not isinstance(decoded, dict):
        raise json.JSONDecodeError("decision must be a JSON object", raw, 0)
    trailing = raw.strip()[end:].strip()
    if trailing:
        logger.info("dropped %d chars of prose after the decision JSON", len(trailing))
    return decoded


def _yaw_of_rotation(rotation) -> float | None:
    """UE yaw from either rotation shape, or None when there isn't one."""
    if isinstance(rotation, dict) and rotation.get("y") is not None:
        return float(rotation["y"])
    if isinstance(rotation, (list, tuple)) and len(rotation) >= 2:
        return float(rotation[1])
    return None


def _direction_lines(directions: dict | None, landmarks: list | None = None,
                     facing_yaw: float | None = None) -> str:
    """Render the per-direction next-cell sense from agent_manager._direction_places.

    Each value is ``{"cell": "col,row", "place": <name|None>, "ground": [...],
    "refusals": [...]}`` — a named place means that cell is already mapped; None
    means it's unexplored (go map it). ``ground`` is what APCs have actually
    stood on there, commonest first; empty means nobody has ever stood in that
    cell, and that gap is stated rather than left to look like a clean bill of
    health (#58).

    ``landmarks`` are this tick's sightings, which carry a bearing. They are
    folded onto the matching compass line rather than listed separately (#59):
    the reason not to walk somewhere was in the picture, the invitation to walk
    there was in this list, and joining them was left to the model to do in its
    head every tick — under a goal that pays it for unexplored ground. SR39 has
    Dufus naming the corn and stepping into it in the same sentence.
    """
    if not directions:
        return "Nothing mapped yet — navigate by what you see in the image."
    lines = []
    for d, info in directions.items():
        if isinstance(info, dict):
            place = info.get("place")
            refusal = _refusal_text(info.get("refusals"))
            # A refused cell is not "unexplored ground waiting to be surveyed",
            # and must never read like it — that description is what kept
            # pulling Dufus back into the same field run after run (#59).
            status = refusal or (f'"{place}"' if place else "unexplored")
            lines.append(f"- {d}: cell {info.get('cell', '?')} — {status}"
                         f", {_ground_text(info.get('ground'))}")
            no_go = _no_go_text(info.get("no_go"))
            if no_go:
                lines[-1] += f"; {no_go}"
            eyes = _eyes_text(info.get("seen_ahead"))
            if eyes:
                lines[-1] += f"; {eyes}"
            seen_that_way = _visible_that_way(d, landmarks, facing_yaw)
            if seen_that_way:
                lines[-1] += f"; you can see {seen_that_way}"
        else:  # legacy list-of-labels form
            lines.append(f"- {d}: {', '.join(info) if info else 'unmapped'}")
    return "\n".join(lines)


def _frontier_note(frontier: dict | None) -> str:
    """How big the world is, what shape the map is, and where its edge lies (#73).

    The eight-neighbour list above answers "where can I put my foot". It cannot
    answer "where should the survey go next", because it is one cell wide in
    every direction and every unmapped neighbour looks equally worth having. Ask
    that question 48 times with no wider fact and you get SR41: 15 cells of a
    17x12 grid, laid out 7 wide and 2 tall, because whichever way the body was
    already pointing won every tie.

    The map's own shape is stated because that is the fact that was missing —
    "2 rows tall" is the sentence that makes going north thinkable. Nothing here
    picks a cell. Per [[feedback_facts_not_blocking]] the frontier is measured
    and shown; which edge to grow, and whether to grow one at all rather than
    keep an appointment, stays the model's call and its Rules'.
    """
    if not isinstance(frontier, dict):
        return ("The extent of the world is not known here — no wider map fact is "
                "available. Navigate by the neighbouring cells above.")

    extent = frontier.get("extent") or {}
    lines = [
        f"The world grid is {frontier.get('cols')} cells across (west-east) and "
        f"{frontier.get('rows')} deep (north-south) — {frontier.get('total')} cells in all.",
        f"{frontier.get('mapped')} of them are mapped. Mapped ground currently spans "
        f"columns {extent.get('min_col')}-{extent.get('max_col')} and rows "
        f"{extent.get('min_row')}-{extent.get('max_row')}: a block "
        f"{extent.get('width')} cells wide and {extent.get('height')} tall.",
    ]
    cells = frontier.get("cells") or []
    if cells:
        ways = "; ".join(
            f"cell {f['cell']} — {f['direction']}, {f['steps']} "
            f"cell{'s' if f['steps'] != 1 else ''} away" for f in cells)
        more = frontier.get("frontier_total", len(cells)) - len(cells)
        lines.append(
            f"Nearest unmapped ground touching the mapped block, one per direction: "
            f"{ways}" + (f" ({frontier.get('frontier_total')} such cells in all)"
                         if more > 0 else "") + ".")
    else:
        lines.append("No unmapped cell touches the mapped block — every edge of it "
                     "is either mapped or refused.")
    return "\n".join(lines)


def _no_go_text(patches: list | None) -> str:
    """State that the ground one step that way was refused as a patch (#78).

    A patch is smaller than a cell on purpose: the cell may still be worth
    surveying while this particular approach — a yard, an alley mouth, a
    doorway — is not ground to step onto. Like a cell refusal it is a stated
    fact, not a wall.
    """
    stated = [p for p in (patches or []) if isinstance(p, dict) and p.get("reason")]
    if not stated:
        return ""
    first = stated[0]
    return (f"NO-GO ground one step that way (refused by "
            f"{first.get('refused_by', 'someone')}: {first['reason']})")


def _eyes_text(seen_ahead: dict | None) -> str:
    """What the APC's own eyes saw down this heading, from this spot (#77).

    The engine will happily walk a body into a backyard or a bedroom; the
    pixels that said not to were on screen one look earlier. This is that look,
    carried to the step decision. Facts only — the rules say what outranks what.
    """
    if not isinstance(seen_ahead, dict):
        return ""
    bits = []
    ground = str(seen_ahead.get("ground_ahead") or "").strip()
    if ground:
        bits.append(f"{ground} ahead")
    path = str(seen_ahead.get("path_ahead") or "").strip()
    if path == "dead_end":
        bits.append("the way ahead DEAD-ENDS")
    elif path == "blocked":
        bits.append("something solid immediately ahead")
    return f"your own eyes saw: {', '.join(bits)}" if bits else ""


def _refusal_text(refusals: list | None) -> str:
    """State that a cell was ruled out, by whom, and why (#59).

    Named or unexplored were the only two things a cell could be, so a cell an
    APC deliberately rejected went back to reading "unexplored" — an open
    invitation, re-issued every run. The reason is carried because it is the
    whole point: "standing corn" and "a fence" are different facts about the
    world, and this pairing (walkable by the engine, refused by an APC) is the
    training signal the corpus is being built to hold.
    """
    stated = [r for r in (refusals or []) if isinstance(r, dict) and r.get("reason")]
    if not stated:
        return ""
    first = stated[0]
    more = f" (+{len(stated) - 1} more)" if len(stated) > 1 else ""
    return (f"REFUSED by {first.get('refused_by', 'someone')}: "
            f"{first['reason']}{more} — not somewhere to survey")


# A sighting's bearing is where it sits in the frame, not a compass heading.
_VIEW_BEARING_OFFSET = {"left": -45.0, "center": 0.0, "right": 45.0}


def _visible_that_way(direction: str, landmarks: list | None,
                      facing_yaw: float | None = None) -> str:
    """What this tick's view shows toward one compass direction (#59).

    Perception reports a landmark as left/center/right of the frame, which only
    means a compass heading once you know which way the body points — so this
    needs the facing yaw and returns nothing without it rather than guessing.
    """
    if facing_yaw is None or not landmarks:
        return ""
    want = str(direction or "").strip().lower()
    hits = []
    for lm in landmarks:
        if not isinstance(lm, dict) or not lm.get("label"):
            continue
        offset = _VIEW_BEARING_OFFSET.get(str(lm.get("bearing", "center")).lower())
        if offset is None:
            continue
        heading = yaw_to_compass(facing_yaw + offset)
        if _COMPASS_WORD.get(heading, "").lower() == want:
            distance = str(lm.get("distance") or "").strip()
            hits.append(f"{lm['label']}{f' ({distance})' if distance else ''}")
    return ", ".join(hits[:3])


def _ground_text(ground: list | None) -> str:
    """What has been felt underfoot in a cell, commonest first (#58).

    Two footings for one cell is not a contradiction — a 30 m cell can be half
    road and half field — so both are named with their sample counts instead of
    picking a winner. Capped at two: the top pair is what a decision turns on.
    """
    surfaces = [g for g in (ground or []) if isinstance(g, dict) and g.get("footing")]
    if not surfaces:
        return "ground never walked"
    parts = [f"{g['footing']} x{g.get('sample_count', 1)}" for g in surfaces[:2]]
    return "ground walked: " + ", ".join(parts)


def _wake_schedule_line(directive: dict | None) -> str:
    """Render the spool-up sequencer verdict for the wake prompt.

    The manager computed this at the agent's true spawn position (geometric,
    with a first-time place seeded right there), so the prompt can STATE
    whether the agent is already where the schedule wants it — the LLM must
    not guess this from memory ("my truck is on main street somewhere...").
    """
    if not directive:
        return ("(No schedule verdict available — use your goals and what "
                "you can see.)")
    status = directive.get("status")
    place = directive.get("place") or ""
    activity = directive.get("activity") or ""
    if status == "act" and place:
        return (f"Scheduled now: {activity} at {place}. Your position CONFIRMS "
                f"you are already at {place} — this exact spot is it, even if "
                f"you cannot see it in frame. Do NOT walk toward it; stay here "
                f"and begin: {activity}.")
    if status == "travel" and place:
        return (f"Scheduled now: {activity} at {place}. You are NOT there yet — "
                f"your first action should start you toward {place} "
                f"(walk_to with target_location \"{place}\").")
    if status == "act":
        return f"Scheduled now: {activity} — it has no fixed place, do it here."
    return "Nothing is scheduled right now — follow your goals."


def _schedule_note(directive: dict | None) -> str:
    """Render the sequencer directive (planner.step) for the decision prompt.

    Turns "what your routine says right now" into a line the LLM can act on:
    travel to the scheduled place, do the activity here, or (idle) explore.
    """
    if not directive or directive.get("status") == "idle":
        # What free time is *for* is the persona's business, not the sequencer's
        # (#64) — a shopkeeper minding her post and a surveyor pushing outward are
        # both correct answers, and only their Rules know which is which.
        return ("Your schedule has nothing fixed right now — follow your goals and "
                "your rules.")
    intent = directive.get("intent", "")
    if directive.get("status") == "travel" and directive.get("place"):
        # Grid-first route narration (#17/WP8): legibility only — the walk_to
        # contract below is unchanged; the manager executes it leg by leg.
        r = directive.get("route")
        en_route = ""
        if r:
            heading = f", heading {r['heading']}" if r.get("heading") else ""
            en_route = (f"You are en route: leg {r['leg']} of {r['total']}{heading} "
                        f"toward cell ({r['to_cell'][0]}, {r['to_cell'][1]}).\n")
            delta_cm = r.get("delta_cm")
            if delta_cm is not None and delta_cm > 0:
                en_route += (
                    f"PROGRESS WARNING: your last move took you {round(delta_cm / 100)}m "
                    f"FARTHER from your destination, not closer. Correct course toward it "
                    f"now — this overrides any other movement urge.\n")
        return (f"{en_route}{intent}\nThis is your priority right now: use walk_to with "
                f"target_location \"{directive['place']}\" and keep going until you "
                f"arrive. Do NOT start the scheduled activity on the way — even if "
                f"it involves people, it happens at the destination. What is worth "
                f"a brief pause on the way is set by your rules.")
    if directive.get("place"):
        return (f"{intent}\nYour position confirms you are already at "
                f"{directive['place']} — even if you cannot see it in frame. Do "
                f"NOT walk_to it or go looking for it; stay here and do the "
                f"activity (idle, observe, speak to someone nearby).")
    return f"{intent}\nYou are where you should be — do this where you are."


def _place_text(observation: dict) -> str:
    """Render place context for the prompt.

    If the agent has a named place in PlaceDB, show it with compass landmarks.
    Otherwise fall back to the flat legacy place label list.
    """
    ctx = observation.get("place_context")
    if ctx and ctx.get("name"):
        compass = ctx.get("compass") or {}
        lines = [f"{ctx['name']} (known)"]
        if ctx.get("description"):
            lines.append("  saved visual memory: " + str(ctx["description"]).replace("\n", "; "))
        if ctx.get("place_image_id"):
            lines.append(f"  place image id: {ctx['place_image_id']}")
        for d in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]:
            labels = compass.get(d) or []
            if labels:
                lines.append(f"  {d}: {', '.join(labels)}")
        return "\n".join(lines)
    place = observation.get("place") or []
    return ", ".join(place) if place else "unknown"


def _grid_text(grid: dict | None) -> str:
    """Name this cell exactly once (#59).

    This used to print the raw signed grid key *and* the col/row pair — "-3,0
    (col 6, row 6 of 12x9)" — two names for one cell in a single line. SR39 has
    Dufus reasoning about "cell -3,0" all run while everything we stored called
    it "6,6". Only col/row is spoken now; it is what PlaceDB, the decision log
    and the survey messages already key on.
    """
    grid = grid or {}
    if grid.get("col") is None:
        return str(grid.get("key", "unknown"))
    return f"{grid['col']},{grid['row']} (of {grid.get('cols', '?')}x{grid.get('rows', '?')})"


def _idle_decision(agent_id: str, reason: str) -> dict:
    return {
        "agent_id": agent_id,
        "thought_summary": reason,
        "action": {"type": "idle"},
        "speech": None,
        "memory_update": None,
        "importance": 0.0,
    }


def _reload_env() -> None:
    load_dotenv(_ENV_PATH, override=True)


def _strip_markdown_fences(raw: str) -> str:
    if raw.startswith("```"):
        lines = raw.splitlines()
        return "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return raw
