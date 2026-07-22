from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from dotenv import load_dotenv

if TYPE_CHECKING:
    from .agent import Agent

logger = logging.getLogger("AgentRuntime")
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

# Field specs for actions that take parameters beyond "type".
_ACTION_SCHEMAS: dict[str, str] = {
    "idle":             '{"type": "idle"}',
    "wander":           '{"type": "wander"}  -- keep moving: take one step (~15m) in the direction you are facing',
    "walk_to":          '{"type": "walk_to", "target_location": "<place name>"} to travel to a named place you know (e.g. "village square", "home"), OR {"type": "walk_to", "target_actor": "<actor_label>"} to walk to a known character, OR {"type": "walk_to", "direction": "forward|forward-left|forward-right|left|right|back"} to walk ~15m toward what you see in that direction',
    "speak_to":         '{"type": "speak_to", "target": "<actor_label>", "message": "<text>"}',
    "inspect_object":   '{"type": "inspect_object", "target": "<actor_name>"}',
    "follow_character": '{"type": "follow_character", "target": "<actor_name>"}',
    "attack":           '{"type": "attack", "target": "<actor_name>"}',
    "flee":             '{"type": "flee"}',
    "observe":            '{"type": "observe"}',
    "remember":         '{"type": "remember", "text": "<what to remember>"}',
}

# Static portion of the prompt; eligible for Anthropic prompt caching.
_SYSTEM_TEMPLATE = """\
You are controlling one NPC in an Unreal Engine RPG world.

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

## Nearby APCs (engine position fact; not proof of line of sight)
{nearby_character_lines}

## Your Location
x={x:.0f}, y={y:.0f}, z={z:.0f}
Facing: {facing}
Grid cell: {grid_cell}
Place: {place}
Time: {world_time}

## Where You Can Go Next — neighboring grid cells (one step ~15m away)
{direction_lines}

## You See (your forward view, perceived just now)
{seen}

## Your Current State
{current_action}

## Current Goal
{current_goal}

## Active Interruption
{active_interrupt_note}

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
head somewhere, your action this tick should move you there. Do NOT stop for
strangers, scenery, or cells you could explore — those can wait.
Exactly two things justify pausing your routine:
1. You see someone under "People You Know" you have NOT already greeted recently
   — you may greet them briefly. If their line says "already greeted recently",
   you have said hi this encounter; do not stop again — a nod is enough, keep going.
2. Someone is speaking to you — respond (even if you already greeted them).
After such a pause, your next action goes back to the scheduled destination.
Staying in character is good, but character quirks (curiosity, distraction)
color HOW you travel — they do not cancel WHERE you are going.

To move toward anything you see, use walk_to with a direction relative to your
facing — "forward" is the view described above. Prefer a specific direction
over wandering.

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
it will only wedge you against the same thing again. Turn aside: walk_to left,
right, or back to get clear of the obstacle, then head for your destination
again from the new angle. Getting around it is your priority this tick.

If nothing is scheduled right now and nothing in view needs your attention,
keep exploring: pick a direction whose
neighboring cell is still "unexplored" and walk_to it so the shared world map
keeps growing. A cell that already has a name has been mapped — you do not need
to go re-record it. Do not stand still with nowhere to be.

The "Place" line above is what you have previously called the spot you are standing on (empty means you have never named it). If you can tell what this place is — from the image, your goals, or your memories — name it in the "place" field; it is saved to your map so next time you will know you have been here before.
{sense_note}
Based on what you observe, choose exactly ONE next action. Return ONLY valid JSON: no prose, no markdown fences.

{{
  "agent_id": "{agent_id}",
  "thought_summary": "one sentence describing what you see and why",
  "action": {{
    "type": "..."
  }},
  "place": "short name for the spot you are standing on (e.g. 'vegetable truck', 'village square'), or null if unsure",
  "speech": null,
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

## Active Interruption
{active_interrupt_note}

Choose exactly ONE next action. Return ONLY valid JSON: no prose, no markdown fences.

{{
  "agent_id": "{agent_id}",
  "thought_summary": "one sentence",
  "action": {{
    "type": "..."
  }},
  "speech": null,
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

        return {
            1: "claude-sonnet-4-6",
            2: "claude-haiku-4-5-20251001",
        }.get(agent.tier, "claude-haiku-4-5-20251001")

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
            next_cells_text=_direction_lines(context.get("directions")),
            x=loc.get("x", 0),
            y=loc.get("y", 0),
            z=loc.get("z", 0),
        )

        try:
            if provider == "ollama":
                raw = self._decide_ollama(model, self._system_text(agent), user_text)
            elif provider == "openai":
                raw = self._decide_openai(model, self._system_text(agent), user_text)
            else:
                raw = self._decide_anthropic(model, self._system_text(agent), user_text)
            orientation = json.loads(raw)
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
                direction_lines=_direction_lines(observation.get("directions")),
                seen=_seen_text(observation.get("seen")),
                world_time=observation.get("world_time", "unknown"),
                current_action=action_state,
                current_goal=agent.current_goal,
                active_interrupt_note=_active_interrupt_note(observation.get("active_interrupt")),
                sense_note=_sense_note(observation),
                schedule_note=_schedule_note(observation.get("schedule")),
                route_map_note=_route_map_note(observation),
                acquaintance_lines=_acquaintance_lines(observation.get("acquaintances")),
                known_place_lines=_known_place_lines(observation.get("known_places")),
                episode_lines=_episode_lines(observation.get("recent_episodes")),
            )
        else:
            obs_for_text = {k: v for k, v in observation.items() if k != "image_path"}
            user_text = _USER_TEMPLATE.format(
                agent_id=agent.agent_id,
                memories=mem_lines,
                observation=json.dumps(obs_for_text, indent=2),
                current_goal=agent.current_goal,
                active_interrupt_note=_active_interrupt_note(observation.get("active_interrupt")),
            )

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
            decision = json.loads(raw)
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

        system = f"""You are {agent.display_name}, a character in an Unreal Engine world.

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
            max_tokens=512,
            system=[{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": content}],
        )
        return _strip_markdown_fences(response.content[0].text.strip())

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
    if observation.get("stuck"):
        lines.append("Sense: you have not advanced for several ticks while moving.")
    blocker = observation.get("blocker")
    if blocker:
        lines.append(
            f"Sense: there is a {blocker['category']} "
            f"{blocker['distance_cm']:.0f} cm directly ahead of you."
        )
        if blocker.get("halted"):
            lines.append("Sense: your walk has been halted.")
    return ("\n" + "\n".join(lines) + "\n") if lines else ""


def _active_interrupt_note(record: dict | None) -> str:
    """Render one grounded active interruption without inventing a speaker."""
    if not isinstance(record, dict):
        return "No active interruption."
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
    return (f"Priority {priority} {kind} from {source}: {reason}{direction_line}\n"
            "This active interruption outranks your routine until it is resolved.")


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
    if isinstance(rotation, dict) and rotation.get("y") is not None:
        return f"yaw {float(rotation['y']):.0f} degrees"
    if isinstance(rotation, (list, tuple)) and len(rotation) >= 2:
        return f"yaw {float(rotation[1]):.0f} degrees"
    return "unknown"


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


def _seen_text(seen: dict | None) -> str:
    """Render a perception result ({landmarks, characters, caption}) as prompt lines."""
    if not seen:
        return "(no view this tick)"
    if seen.get("error"):
        return f"(your vision failed this tick: {seen['error']})"
    lines = []
    if seen.get("caption"):
        lines.append(seen["caption"])
    for lm in seen.get("landmarks") or []:
        lines.append(f"- {lm['label']} ({lm.get('bearing', '?')}, {lm.get('distance', '?')})")
    for ch in seen.get("characters") or []:
        lines.append(f"- CHARACTER: {ch['label']} ({ch.get('bearing', '?')}, {ch.get('distance', '?')})")
    return "\n".join(lines) or "(nothing notable)"


def _direction_lines(directions: dict | None) -> str:
    """Render the per-direction next-cell sense from agent_manager._direction_places.

    Each value is ``{"cell": "col,row", "place": <name|None>}`` — a named place
    means that cell is already mapped; None means it's unexplored (go map it).
    """
    if not directions:
        return "Nothing mapped yet — navigate by what you see in the image."
    lines = []
    for d, info in directions.items():
        if isinstance(info, dict):
            place = info.get("place")
            status = f'"{place}"' if place else "unexplored"
            lines.append(f"- {d}: cell {info.get('cell', '?')} — {status}")
        else:  # legacy list-of-labels form
            lines.append(f"- {d}: {', '.join(info) if info else 'unmapped'}")
    return "\n".join(lines)


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
        return ("Your schedule has nothing fixed right now — follow your goals or keep "
                "exploring unmapped cells.")
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
        return (f"{en_route}{intent}\nThis is your priority right now: use walk_to with "
                f"target_location \"{directive['place']}\" and keep going until you "
                f"arrive. Do NOT start the scheduled activity on the way — even if "
                f"it involves people, it happens at the destination. Only a person "
                f"you know or someone speaking to you is worth a brief pause.")
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
    grid = grid or {}
    text = grid.get("key", "unknown")
    if grid.get("col") is not None:
        text += f" (col {grid['col']}, row {grid['row']} of {grid['cols']}x{grid['rows']})"
    return text


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
