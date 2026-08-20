"""The prompt payload contract — what an APC's mind is allowed to receive (#84).

Before this module there was no interface. The vision path formatted 23 separate
keyword arguments through 18 private renderers; the no-vision fallback ignored all
of that and dumped the raw observation dict as JSON minus exactly one key. Same
runtime state, two different prompts, and a **deny-list of one** — so every engine
field the runtime had ever attached went to the model verbatim, and every new key
leaked by default.

Two rules, and they are the whole module:

1. **Allow-list by construction.** A field reaches the model only if it is named
   in ``ALLOWED_FIELDS``. A new runtime key is invisible until someone adds it
   here on purpose. The default is now "not sent"; it used to be "sent".
2. **No engine identity crosses the boundary.** Actor labels, blueprint class
   names and the engine's own name are lizard-brain vocabulary
   ([[architecture_lizard_brain_sensing]] puts the abstraction boundary at
   *output*). ``check_clean`` is the alarm: it does not rewrite the prompt, it
   reports loudly that one leaked, because silently mangling a prompt is worse
   than a logged defect (rule 12).

Characters are referred to by display name throughout; ``known_characters``
already exposes only display names, and ``_resolve_action_actor_refs`` maps a
name the model emits back to a bound actor. Nothing needs an actor label to work.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("AgentRuntime")

# The declared payload. Grouped by what the section is FOR, because a payload
# nobody can explain is a payload nobody can prune — and every field here costs
# tokens on every tick, forever.
ALLOWED_FIELDS: dict[str, tuple[str, ...]] = {
    # Where the body is and what it is doing.
    "self": ("location", "rotation", "current_action", "ai_state", "footing",
             "world_time", "moved_cm", "last_move"),
    # Where that is in the world's own terms.
    "place": ("grid", "place_context", "directions", "frontier", "breadcrumbs",
              "travel", "route"),
    # What the body senses right now.
    "senses": ("seen", "blocker", "stuck", "wedge", "here_no_go", "bounce"),
    # Who else is here.
    "people": ("known_characters", "nearby_characters", "acquaintances",
               "heard_speech"),
    # What it is supposed to be doing.
    "task": ("schedule", "agenda", "active_interrupt", "cell_survey",
             "known_places", "recent_episodes"),
}

# Fields that are engine plumbing and must never be projected, listed explicitly
# so the reason is recorded rather than rediscovered.
NEVER_SEND: dict[str, str] = {
    "image_path": "a local file path — the image itself is attached separately",
    "place_image_id": "a database row id, meaningless to the model",
    "bound_unreal_actor_name": "an engine actor label (#82)",
    "bound_unreal_actor_label": "an engine actor label (#82)",
    "bound_unreal_actor_class": "an engine class name (#82)",
}

# Sub-keys stripped from otherwise-allowed nested facts. `blocker.actor_name` is
# carried through the runtime on purpose (it is what makes a bad classification
# diagnosable in the log) and must stop at this boundary.
NESTED_STRIPS: dict[str, tuple[str, ...]] = {
    "blocker": ("actor_name", "actor_class", "signals"),
}

# Engine vocabulary that must not appear in a rendered prompt. Deliberately
# narrow: these match engine identity, not ordinary English.
_ENGINE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bBP_\w+", "blueprint actor label"),
    (r"\b\w+_BP_C_\d+", "blueprint class instance"),
    (r"\b(?:Static|Skeletal)MeshActor\b", "engine actor class"),
    (r"\bUnreal\s*Engine\b", "the engine's name"),
    (r"\bECC_\w+", "engine collision channel"),
)


def project(observation: dict) -> dict:
    """Return only the declared fields, grouped by section.

    Absent fields are omitted rather than sent as null — an empty section is
    honest, a null field is noise the model still pays for.
    """
    payload: dict[str, dict] = {}
    for section, fields in ALLOWED_FIELDS.items():
        block = {}
        for field in fields:
            if field not in observation:
                continue
            value = observation[field]
            if value is None:
                continue
            strips = NESTED_STRIPS.get(field)
            if strips and isinstance(value, dict):
                value = {k: v for k, v in value.items() if k not in strips}
            block[field] = value
        if block:
            payload[section] = block
    return payload


def dropped_fields(observation: dict) -> list[str]:
    """Keys present in the observation that the contract does not send.

    Not an error — most are engine plumbing — but it is the list that answers
    "what does the model NOT know?", which nobody could answer before.
    """
    allowed = {f for fields in ALLOWED_FIELDS.values() for f in fields}
    return sorted(k for k in observation if k not in allowed)


def check_clean(text: str, agent_id: str, where: str) -> list[str]:
    """Report engine identity that reached a rendered prompt.

    Reports; never rewrites. A prompt quietly altered on its way out is harder to
    debug than one that is wrong and says so (rule 12). Returns the offending
    snippets so a test can assert on them.
    """
    found: list[str] = []
    for pattern, what in _ENGINE_PATTERNS:
        for match in re.findall(pattern, text):
            found.append(match)
            logger.warning(
                f"[{agent_id}] prompt leak ({where}): {what} '{match}' reached the "
                f"model. Engine identity must stop at the payload boundary (#84)."
            )
    return found
