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
    "wander":           '{"type": "wander"}  -- move through the world; seeks out known characters if any are known',
    "walk_to":          '{"type": "walk_to", "target_actor": "<actor_label>"}  -- walk directly to a known character',
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

# Dynamic portion — vision path (image attached separately by the provider call).
_USER_TEMPLATE_VISION = """\
## Your Memories
{memories}

## Characters You May Encounter
{known_characters}

## Your Location
x={x:.0f}, y={y:.0f}, z={z:.0f}

## Your Current State
{current_action}

## Current Goal
{current_goal}

The image above shows exactly what you can see right now.

IMPORTANT: Scan the ENTIRE image carefully — edges, background, sidewalks. Any human figure, person-shaped model, or character standing anywhere in the scene is almost certainly one of the known characters listed above. Game character models may look blocky or stylized but are still people. If you see ANY human figure at all, assume it is a known character and greet or approach them immediately. Do not say you see nobody if there is a person-shaped figure anywhere in the frame.

Based on what you observe, choose exactly ONE next action. Return ONLY valid JSON: no prose, no markdown fences.

{{
  "agent_id": "{agent_id}",
  "thought_summary": "one sentence describing what you see and why",
  "action": {{
    "type": "..."
  }},
  "speech": null,
  "memory_update": null,
  "importance": 0.5
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

    def decide(self, agent: "Agent", observation: dict, memories: list[dict]) -> Optional[dict]:
        provider = self._resolve_provider(agent)
        model = self._resolve_model(agent, provider)
        if not model:
            return _idle_decision(agent.agent_id, "Tier 3 - no LLM assigned")

        api_key = self._resolve_api_key(provider)
        if not api_key:
            logger.error("%s API key not set - returning idle", provider)
            return _idle_decision(agent.agent_id, f"No {provider} API key configured")

        mem_lines = "\n".join(
            f"- [{m.get('importance', 0):.1f}] {m.get('text', '')}"
            for m in memories
        ) or "No memories yet."

        action_lines = "\n".join(
            f"  {_ACTION_SCHEMAS.get(a, '{\"type\": \"' + a + '\"}')}"
            for a in agent.allowed_actions
        )
        system_text = _SYSTEM_TEMPLATE.format(
            character=agent.character_text.strip(),
            goals=agent.goals_text.strip(),
            rules=agent.rules_text.strip(),
            actions=action_lines,
        )

        image_path = observation.get("image_path")
        if image_path:
            from pathlib import Path as _Path
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
                x=loc.get("x", 0),
                y=loc.get("y", 0),
                z=loc.get("z", 0),
                current_action=action_state,
                current_goal=agent.current_goal,
            )
            if not _Path(image_path).exists():
                image_path = None  # capture wrote path but file missing — fall through
        if not image_path:
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
                raw = self._decide_anthropic(model, system_text, user_text, image_path)
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
        import base64
        client = self._anthropic_client()

        if image_path:
            image_data = base64.standard_b64encode(
                open(image_path, "rb").read()
            ).decode()
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
                {"type": "text", "text": user_text},
            ]
        else:
            content = user_text

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
