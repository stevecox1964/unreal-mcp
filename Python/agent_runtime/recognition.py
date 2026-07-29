"""Deterministic identity resolution for APCs in view (#44).

The vision model labels every figure ``unknown person``; the engine knows
exactly who is standing there. Reconciling the two is geometry, not judgement,
so it belongs to the lizard brain: given a viewer's position and yaw plus the
other APCs' positions, decide who is in the forward view and how far away.

The output stays semantic — a display name, a left/center/right bearing, and a
near/mid/far distance — so the decision layer still never sees an engine actor
name or a raw coordinate.

Pure: no engine, no model, no I/O.
"""
from __future__ import annotations

import math

# A person is recognizable well beyond conversational range, but not across the
# whole district; this matches the existing proximity-fact radius.
DEFAULT_RANGE_CM = 2500.0
# Roughly what the forward capture frames, so recognition agrees with the image
# the VLM described rather than naming someone behind the agent.
DEFAULT_FOV_DEG = 110.0

_CENTER_DEG = 20.0      # inside this, a figure reads as straight ahead
_NEAR_CM = 800.0
_MID_CM = 1600.0


def bearing_label(relative_deg: float) -> str:
    """Bucket a signed relative angle into left/center/right (UE: +Y is right)."""
    if relative_deg > _CENTER_DEG:
        return "right"
    if relative_deg < -_CENTER_DEG:
        return "left"
    return "center"


def distance_label(distance_cm: float) -> str:
    """Bucket a distance into the same near/mid/far vocabulary vision uses."""
    if distance_cm <= _NEAR_CM:
        return "near"
    if distance_cm <= _MID_CM:
        return "mid"
    return "far"


def relative_angle(yaw_deg: float, dx: float, dy: float) -> float:
    """Signed degrees from the viewer's facing to the vector (dx, dy), in [-180, 180]."""
    angle = math.degrees(math.atan2(dy, dx)) - yaw_deg
    return (angle + 180.0) % 360.0 - 180.0


def visible_characters(here: tuple[float, float], yaw_deg: float,
                       others: list[dict], *, max_cm: float = DEFAULT_RANGE_CM,
                       fov_deg: float = DEFAULT_FOV_DEG) -> list[dict]:
    """Return the named APCs inside the viewer's forward view, nearest first.

    ``others`` are ``{"name": str, "x": float, "y": float}``. Someone behind the
    agent or beyond ``max_cm`` is omitted — proximity alone is not sighting, and
    recording it would let an APC "recognize" a person it cannot see.

    Example::

        visible_characters((0.0, 0.0), 0.0,
                           [{"name": "Maren", "x": 400.0, "y": 0.0}])
        # -> [{"name": "Maren", "distance_cm": 400.0, "bearing": "center",
        #      "distance": "near", "relative_deg": 0.0}]
    """
    seen = []
    for other in others:
        name = str(other.get("name") or "").strip()
        if not name:
            continue
        try:
            dx = float(other["x"]) - here[0]
            dy = float(other["y"]) - here[1]
        except (KeyError, TypeError, ValueError):
            continue
        distance = math.hypot(dx, dy)
        if distance > max_cm:
            continue
        relative = relative_angle(yaw_deg, dx, dy)
        if abs(relative) > fov_deg / 2.0:
            continue
        seen.append({
            "name": name,
            "distance_cm": round(distance, 1),
            "bearing": bearing_label(relative),
            "distance": distance_label(distance),
            "relative_deg": round(relative, 1),
        })
    return sorted(seen, key=lambda item: item["distance_cm"])


def merge_identities(perceived: list[dict], identified: list[dict]) -> list[dict]:
    """Fold recognized APCs into a vision character list, without double-counting.

    An identified APC replaces at most one anonymous sighting in the same
    bearing bucket — that blob was almost certainly them. Remaining anonymous
    figures are kept: this world contains people who are not APCs, and dropping
    them would hide real bystanders from the decision layer.
    """
    from .social_memory import is_anonymous

    anonymous = [c for c in perceived if is_anonymous(str(c.get("label", "")))]
    named = [c for c in perceived if not is_anonymous(str(c.get("label", "")))]

    claimed: list[int] = []
    for person in identified:
        for index, blob in enumerate(anonymous):
            if index in claimed:
                continue
            if str(blob.get("bearing") or "") == person["bearing"]:
                claimed.append(index)
                break

    merged = [{
        "label": person["name"],
        "bearing": person["bearing"],
        "distance": person["distance"],
        "distance_cm": person["distance_cm"],
        "confidence": 1.0,          # engine geometry, not a model guess
        "source": "engine",
    } for person in identified]
    merged.extend(named)
    merged.extend(blob for index, blob in enumerate(anonymous) if index not in claimed)
    return merged
