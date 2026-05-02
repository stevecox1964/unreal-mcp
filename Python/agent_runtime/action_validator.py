from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import Agent

logger = logging.getLogger("AgentRuntime")


def validate(agent: "Agent", decision: dict, observation: dict) -> dict | None:
    """
    Returns the validated action dict, or None if the decision should be dropped.
    May substitute a safe fallback (idle) instead of returning None.
    """
    if not decision:
        return None

    action = decision.get("action")
    if not action or not isinstance(action, dict):
        logger.warning(f"[{agent.agent_id}] Decision has no valid action field")
        return None

    action_type = action.get("type")
    if not action_type:
        logger.warning(f"[{agent.agent_id}] Action missing 'type' field")
        return None

    if action_type not in agent.allowed_actions:
        logger.warning(
            f"[{agent.agent_id}] Action '{action_type}' not in allowed_actions "
            f"{agent.allowed_actions} - dropping"
        )
        return None

    if action_type == "speak_to":
        if not agent.can_speak():
            logger.info(f"[{agent.agent_id}] Speech on cooldown - substituting idle")
            return {"type": "idle"}
        if not action.get("message"):
            logger.warning(f"[{agent.agent_id}] speak_to missing message - dropping")
            return None

    if action_type == "walk_to":
        if not action.get("target_actor") and not action.get("location") and not action.get("target_location"):
            logger.warning(f"[{agent.agent_id}] walk_to missing target - dropping")
            return None

    if action_type == "follow_character":
        if not action.get("target"):
            logger.warning(f"[{agent.agent_id}] follow_character missing target - dropping")
            return None

    return action
