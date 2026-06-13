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
    "walk_to":          '{"type": "walk_to", "target_actor": "<actor_label>"} to walk to a known character, OR {"type": "walk_to", "direction": "forward|forward-left|forward-right|left|right|back"} to walk ~15m toward what you see in that direction',
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

## Characters You May Encounter
{known_characters}

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

Anything listed under "You See" is really there. A CHARACTER sighting matching
one of the known characters above is that person — consider greeting or
approaching them.

To move toward anything you see, use walk_to with a direction relative to your
facing — "forward" is the view described above. Prefer a specific direction
over wandering.

If nothing in view needs your attention, keep exploring: pick a direction whose
neighboring cell is still "unexplored" and walk_to it so the shared world map
keeps growing. A cell that already has a name has been mapped — you do not need
to go re-record it. Do not stand still with nowhere to be.

The "Place" line above is what you have previously called the spot you are standing on (empty means you have never named it). If you can tell what this place is — from the image, your goals, or your memories — name it in the "place" field; it is saved to your map so next time you will know you have been here before.
{stuck_note}
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

## Where You Can Go Next — neighboring grid cells (one step ~15m away)
{next_cells_text}

Get your bearings by asking yourself, in character:
1. Where am I? Use what you can see, the place label, and your memories. If you
   have NOT been here before, name the place you are standing in — it is saved
   to the shared map so next time you (or anyone) will know it.
2. What time is it, and what does that time of day mean for my routine?
3. Where should I be right now — and am I already there? If not, your first
   action should start getting you there.

Then choose the FIRST action that starts your day. If where you should be is
visible in one of the views, use {{"type": "walk_to", "direction": "<that
view's direction>"}} — directions are relative to the way you are facing
("forward"). If you have nowhere specific to be, do not stand still: walk_to a
neighboring cell that is still "unexplored" to help map the world.

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
        }.get(provider)
        if provider_env and os.environ.get(provider_env):
            return os.environ[provider_env]

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
                "You slowly turn your head and look around, sweeping 180 degrees "
                "from your left to your right:\n" + "\n".join(lines)
            )
        else:
            views_text = "You cannot see anything yet — rely on your memories and the place label."

        loc = context.get("location") or {}
        place = context.get("place") or []
        known = context.get("known_place")
        known_line = (
            f"You have been here before — this place ('{known}') is already on the "
            f"shared map, so there is nothing new to record. Decide where to go next."
            if known else
            "You have not named this spot yet — if you can tell what it is, name it."
        )
        user_text = _USER_TEMPLATE_WAKE.format(
            agent_id=agent.agent_id,
            memories=_memory_lines(memories),
            world_time=context.get("world_time", "unknown"),
            views_text=views_text,
            grid_cell=_grid_text(context.get("grid")),
            place=", ".join(place) if place else "unknown",
            known_line=known_line,
            next_cells_text=_direction_lines(context.get("directions")),
            x=loc.get("x", 0),
            y=loc.get("y", 0),
            z=loc.get("z", 0),
        )

        try:
            if provider == "openai":
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
            # Report the fact only — the agent should notice it isn't progressing
            # and reason out what to do. The lizard brain senses; it does not advise.
            stuck_note = (
                "\nNote: your last move command did not change your position — you "
                "issued a move but you are not actually getting anywhere.\n"
                if observation.get("stuck") else ""
            )
            user_text = _USER_TEMPLATE_VISION.format(
                agent_id=agent.agent_id,
                memories=mem_lines,
                known_characters=known_text,
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
                stuck_note=stuck_note,
            )
        else:
            obs_for_text = {k: v for k, v in observation.items() if k != "image_path"}
            user_text = _USER_TEMPLATE.format(
                agent_id=agent.agent_id,
                memories=mem_lines,
                observation=json.dumps(obs_for_text, indent=2),
                current_goal=agent.current_goal,
            )

        try:
            if provider == "openai":
                raw = self._decide_openai(model, system_text, user_text)
            elif provider == "anthropic":
                raw = self._decide_anthropic(model, system_text, user_text)
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


def _memory_lines(memories: list[dict]) -> str:
    return "\n".join(
        f"- [{m.get('importance', 0):.1f}] {m.get('text', '')}"
        for m in memories
    ) or "No memories yet."


def _image_block(image_path: str) -> dict:
    import base64
    image_data = base64.standard_b64encode(open(image_path, "rb").read()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}}


def _facing_text(rotation) -> str:
    if isinstance(rotation, dict) and rotation.get("y") is not None:
        return f"yaw {float(rotation['y']):.0f} degrees"
    if isinstance(rotation, (list, tuple)) and len(rotation) >= 2:
        return f"yaw {float(rotation[1]):.0f} degrees"
    return "unknown"


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


def _place_text(observation: dict) -> str:
    """Render place context for the prompt.

    If the agent has a named place in PlaceDB, show it with compass landmarks.
    Otherwise fall back to the flat legacy place label list.
    """
    ctx = observation.get("place_context")
    if ctx and ctx.get("name"):
        compass = ctx.get("compass") or {}
        lines = [f"{ctx['name']} (known)"]
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
