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

    logger.debug(f"[{agent.agent_id}] Validating decision: {decision}")

    action = decision.get("action")
    if not action or not isinstance(action, dict):
        logger.warning(
            f"[{agent.agent_id}] Decision has no valid action field "
            f"(got {type(action).__name__}: {action!r}) | full decision: {decision}"
        )
        return None

    action_type = action.get("type")
    if not action_type:
        logger.warning(
            f"[{agent.agent_id}] Action missing 'type' field | action: {action}"
        )
        return None

    if action_type not in agent.allowed_actions:
        logger.warning(
            f"[{agent.agent_id}] Action '{action_type}' not in allowed_actions "
            f"{agent.allowed_actions} — full action: {action}"
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
        if (
            not action.get("target_actor")
            and not action.get("location")
            and not action.get("target_location")
            and not action.get("direction")
        ):
            logger.warning(f"[{agent.agent_id}] walk_to missing target/direction - dropping")
            return None

    if action_type == "follow_character":
        if not action.get("target"):
            logger.warning(f"[{agent.agent_id}] follow_character missing target - dropping")
            return None

    if action_type == "refuse_cell":
        # A refusal without a stated reason is exactly the opaque "impassable"
        # flag we did not want: it removes ground from the survey queue and
        # leaves nothing to review or train on (#59).
        if not str(action.get("reason") or "").strip():
            logger.warning(f"[{agent.agent_id}] refuse_cell missing reason - dropping")
            return None

    return action
