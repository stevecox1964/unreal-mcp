"""Landmarks (#23) — BP-authored ground truth places, read straight from the level.

The author drops a cheap marker actor (``Landmark_BP``) in the editor and sets
its **actor label** to ``Landmark_<owner>_<place name with underscores>``:

    Landmark_maren_vegetable_truck   -> owner "maren", name "vegetable truck"
    Landmark_dufus_home              -> owner "dufus", name "home"
    Landmark_community_town_square   -> owner None, community=True, name "town square"

Detection is by label prefix, class-agnostic — renaming a real prop's label
also works and pins the place to the prop itself. This module turns the raw
actor list (``get_actors_in_level`` / ``get_actors``: ``{name, label, class,
location, ...}``) into the same normalized entry shape ``places_manifest.
load_manifest`` produces, so both feed the same ``apply_manifest``.
"""
from __future__ import annotations

import logging

from .place_db import PLACE_EXTENT_CM

logger = logging.getLogger("AgentRuntime")

LANDMARK_PREFIX = "Landmark_"


def landmark_from_actor(actor: dict) -> dict | None:
    """Parse one level actor into a manifest-shaped entry, or ``None``.

    Non-``Landmark_`` labels return ``None`` silently (not every actor in the
    level is a landmark). The prefix match is **case-insensitive** — authors
    typo the case constantly (``landmark_maren_home`` works just like
    ``Landmark_maren_home``). A label that starts with the prefix but is
    malformed — no owner token, no name, or a blank name — is
    ``logger.error``-ed and skipped (fail loud, not silent).

    Returns ``{name, x, y, owner, community, extent_cm, actor}`` — same shape
    as ``places_manifest.load_manifest`` entries. The owner token is
    **casefolded** before use (agent ids are lowercase; ``Community`` maps
    the same as ``community``): casefolded token ``"community"`` maps to
    ``owner=None, community=True``; any other token maps to
    ``owner=<casefolded token>, community=False``. Display ``name`` stays as
    authored (only underscores -> spaces + strip).
    """
    label = str(actor.get("label") or "")
    prefix_len = len(LANDMARK_PREFIX)
    if label[:prefix_len].casefold() != LANDMARK_PREFIX.casefold():
        return None

    rest = label[prefix_len:]
    parts = rest.split("_", 1)
    owner_token = parts[0].casefold()
    name_raw = parts[1] if len(parts) > 1 else ""

    if not owner_token or not name_raw.strip():
        logger.error(f"landmark actor '{actor.get('name')}': malformed label "
                     f"'{label}' (need Landmark_<owner>_<name>) — skipped")
        return None

    name = name_raw.replace("_", " ").strip()
    if not name:
        logger.error(f"landmark actor '{actor.get('name')}': malformed label "
                     f"'{label}' (need Landmark_<owner>_<name>) — skipped")
        return None

    if owner_token == "community":
        owner, community = None, True
    else:
        owner, community = owner_token, False

    return {
        "name": name,
        "x": float(actor["location"][0]),
        "y": float(actor["location"][1]),
        "owner": owner,
        "community": community,
        "extent_cm": PLACE_EXTENT_CM,
        "actor": actor.get("name"),
    }


def _levenshtein(a: str, b: str) -> int:
    """Classic edit distance (insert/delete/substitute), two-row DP, no imports."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


def scan_landmarks(actors: list) -> dict:
    """Parse a level's actor list into landmark entries, plus near-miss suspects.

    Returns ``{"entries": [...], "suspects": [...]}``. ``entries`` is the
    same as ``landmarks_from_actors`` used to return. A **suspect** is a
    non-landmark actor whose label's first underscore-token (the text before
    the first ``_``, or the whole label if there is none) casefolds to
    Levenshtein distance 1 or 2 from ``"landmark"`` — a typo'd prefix like
    ``Landmarlk_Dufus_Home``. Suspects are ``logger.error``-ed and returned,
    never guessed into a place. Malformed true-prefix labels (e.g.
    ``Landmark_maren_``) are handled by ``landmark_from_actor`` (error +
    skip) and are never suspects.
    """
    entries = []
    suspects = []
    for actor in actors:
        entry = landmark_from_actor(actor)
        if entry is not None:
            entries.append(entry)
            continue
        label = str(actor.get("label") or "")
        token = label.split("_", 1)[0].casefold()
        if token == "landmark":
            continue
        if 1 <= _levenshtein(token, "landmark") <= 2:
            logger.error(f"label '{label}' looks like a landmark but isn't — "
                         f"did you mean Landmark_<owner>_<name>? — ignored")
            suspects.append(label)
    return {"entries": entries, "suspects": suspects}


def landmarks_from_actors(actors: list) -> list[dict]:
    """Parse a level's actor list into landmark entries, skipping non-landmarks.

    Thin wrapper over ``scan_landmarks`` (API compat) — drops the suspects.
    """
    return scan_landmarks(actors)["entries"]


def merge_entries(landmarks: list[dict], manifest_entries: list[dict]) -> list[dict]:
    """Merge landmark entries (level, ground truth) with places.json entries.

    Dedupe key is ``(owner or "", name.casefold())``: a landmark always wins
    over a places.json entry claiming the same place — the shadowed
    places.json entry is ``logger.warning``-ed. Landmarks are returned first
    so ``apply_manifest``'s first-wins cell rule favors them.
    """
    landmark_keys = {(e["owner"] or "", e["name"].casefold()) for e in landmarks}
    merged = list(landmarks)
    for entry in manifest_entries:
        key = (entry["owner"] or "", entry["name"].casefold())
        if key in landmark_keys:
            logger.warning(f"places manifest: '{entry['name']}' (owner={entry['owner']}) "
                           f"shadowed by a landmark actor — landmark wins")
            continue
        merged.append(entry)
    return merged
