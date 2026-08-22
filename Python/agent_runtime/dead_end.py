"""Sealing ground the body has PROVED it cannot enter (#91).

The world already had a place to write "do not go here": a no-go patch — a
point, a radius and a stated reason, filed in PlaceDB and shown back to every
APC (#78). What it never had was anything that *wrote one from experience*.
A patch appeared only when the mind chose the `refuse` action, and a wedged
mind never does: it is busy picking another heading.

SR50 is the whole argument. Dufus stood on one spot and ordered northeast,
north, northwest — each refused by the body with "there was no room to step" —
took the escape west, walked 22 m, and on the very next tick ordered northwest
again. Nine paid decisions, zero metres, and the reasoning was correct every
time. He was not being stupid. He was being told the truth about *this instant*
and nothing about the wall, because the only memory of a failed heading
(`_record_attempt`) is deliberately wiped the moment the body moves.

That scope is right for "a mailbox blocks east from here". It is wrong for a
building. A building is not a fact about where you stand; it is a fact about
*where it stands*, and it is still there after you walk away.

So this module answers one question — **given that the body just failed to move
one way, what volume of the world should be marked, and how big?** — and the
answers are geometry, not judgement:

* the seal sits in FRONT of the body, starting at the face of whatever stopped
  it (the engine measured that distance), never on the ground underfoot;
* it starts about a body's width and grows each time the same volume stops the
  APC again, because a wall that stops you three times is wider than one that
  stopped you once;
* it never grows past a place-cell radius, so a wall can never swallow a whole
  district the way a cell refusal would.

Pure functions. The caller gathers the evidence and PlaceDB stores the result;
nothing here touches either, and per [[feedback_facts_not_blocking]] a sealed
volume is still only a fact shown back to the APC — it caps how FAR a step
travels, it never overrides which way the mind chose to go.
"""
from __future__ import annotations

import math

# A first seal is about as wide as the body that proved it.
#
# The size of this number is the whole design, and it wants to be SMALL. A seal
# is a circle, and a circle whose near edge touches your feet covers a fifty-
# degree slice of everything in front of you, not just the heading that proved
# it. Sized generously the first version of this marked Dufus's escape west as
# no-go on the strength of three walls to the north — trading the SR50 loop for
# a worse one, an APC that shuffles because every way out reads forbidden.
#
# So: mark the MOUTH of the trap, about a body across, and let repeats do the
# widening. A circle this size cannot be missed either — the line scan samples
# every 150 cm and the seal is 200 cm wide.
BASE_RADIUS_CM = 100.0

# Each further proof against the same volume widens it. A wall you bounce off
# three times is not a post.
GROWTH_PER_PROOF_CM = 100.0

# What a full raster of solid is worth on top. Deliberately small: the probe fan
# is five columns over a couple of metres, so "all of it is blocked" measures
# that this thing spans the fan — it does not measure a building.
RASTER_WIDENING_CM = 50.0

# Never wider than a third of a place cell (#78's PLACE_EXTENT_CM). Past that a
# patch stops being sub-cell ground and starts being a district, and districts
# are what `cell_refusals` is for.
MAX_RADIUS_CM = 300.0

# Gap left between the body and the near edge of the seal, so an APC can never
# end up standing inside a volume it just marked.
BODY_CLEAR_CM = 50.0

# The widest slice of the compass one seal is allowed to cover, measured from
# the APC standing in front of it.
#
# This is the constant that decides whether the whole idea helps or hurts, and
# it is pure geometry: a circle of radius r whose centre is d away covers an arc
# of +/- asin(r / d). Park that circle right against the body and it swallows a
# fifty-degree slice — so proving a wall to the NORTHEAST also marks east and
# north, and three walls in a corner mark every heading the APC has. The first
# build did exactly that: it sealed Dufus's one working escape west on the
# strength of three walls to the north.
#
# A heading is 45 degrees wide, so a seal must stay inside +/- 30 to leave its
# neighbours alone. That fixes the minimum distance at r / sin(30) = 2r, and it
# is why the centre is pushed out rather than the radius pulled in: a mark that
# hugs the body cannot be narrow, whatever its size.
MAX_ARC_HALF_DEG = 30.0
MIN_CENTRE_FACTOR = 1.0 / math.sin(math.radians(MAX_ARC_HALF_DEG))   # 2.0

# A stall with no measurement behind it is ambiguous — a person stepped across,
# the navmesh hiccuped. Two of them in the same volume is not.
PROOFS_TO_SEAL = {"measured": 1, "stalled": 2}

# How long a body-measured seal is believed. The mind's own refusals are
# judgements and keep forever; this one is a reading taken at one moment, and
# the pickup truck that took it drives away. Half an hour of real time.
MEASURED_TTL_S = 1800.0


def wall_point(x: float, y: float, yaw_deg: float, reach_cm: float,
               radius_cm: float) -> tuple[float, float]:
    """Where the centre of the seal goes: beyond the wall, not on the APC.

    ``reach_cm`` is how far the engine's capsule sweep said this body could
    travel along ``yaw_deg`` before something stopped it — so the wall's face is
    exactly that far ahead. Putting the seal's NEAR EDGE on that face means the
    circle covers the ground that cannot be entered and nothing else; the centre
    therefore sits a further ``radius_cm`` out, plus a body's clearance so the
    APC is never inside its own mark.
    """
    ahead = max(float(reach_cm), 0.0) + radius_cm + BODY_CLEAR_CM
    # ...but never so close that the mark spills onto the neighbouring headings.
    ahead = max(ahead, radius_cm * MIN_CENTRE_FACTOR)
    rad = math.radians(yaw_deg)
    return (x + math.cos(rad) * ahead, y + math.sin(rad) * ahead)


def seal_radius(proofs: int, blocked_fraction: float | None = None) -> float:
    """How wide to mark it: one body, grown by every repeat, capped at half a cell.

    ``blocked_fraction`` is the share of the engine's probe raster that came back
    solid — 1.0 is a face of wall across the whole fan, 0.2 is a post with air
    around it. It is a measurement of how WIDE the thing is, so it belongs in the
    width of the mark. Absent (no raster) the base width stands: never guess a
    wall wider than what was actually read.
    """
    radius = BASE_RADIUS_CM + GROWTH_PER_PROOF_CM * max(int(proofs) - 1, 0)
    if blocked_fraction is not None:
        radius += RASTER_WIDENING_CM * max(min(float(blocked_fraction), 1.0), 0.0)
    return min(radius, MAX_RADIUS_CM)


def should_seal(kind: str, proofs: int) -> bool:
    """Is there enough evidence yet to mark this volume?

    A measured refusal is the engine sweeping this exact body along this exact
    heading and reporting it does not fit — one is enough, it is not an opinion.
    A bare stall says only that an accepted order produced no movement, which has
    innocent causes, so it waits for a second.
    """
    return int(proofs) >= PROOFS_TO_SEAL.get(kind, 2)


def seal_reason(kind: str, headings: list[str], proofs: int,
                reach_cm: float | None, blocker: str = "") -> str:
    """One plain sentence of what the body found. Read back to the APC verbatim.

    Names the measurement and the count, because those are the two things the
    APC could not otherwise know: that this is its own body's reading rather
    than somebody's opinion, and that it has already spent tries here.
    """
    ways = ", ".join(dict.fromkeys(headings)) or "ahead"
    tries = f"{proofs} attempt{'s' if proofs != 1 else ''}"
    what = f" ({blocker})" if blocker else ""
    if kind == "measured" and reach_cm is not None:
        return (f"my own body does not fit here — the engine measured "
                f"{reach_cm / 100:.1f} m of travel going {ways}{what}, "
                f"less than one step, over {tries}")
    return (f"walking {ways} from here moved me nowhere over {tries}"
            f"{what} — the ground is not passable")


def find_candidate(candidates: list[dict], x: float, y: float) -> dict | None:
    """The already-known wall this new proof belongs to, if any.

    Containment, not nearest: the same test PlaceDB uses to decide a patch is a
    repeat rather than a new circle, so the ledger and the stored patches agree
    about what counts as "the same wall".
    """
    for c in candidates:
        if math.hypot(x - c["x"], y - c["y"]) <= c["radius_cm"]:
            return c
    return None


def push_clear(cx: float, cy: float, x: float, y: float,
               radius_cm: float) -> tuple[float, float]:
    """Slide a seal's centre out until the APC at (x, y) is not inside it.

    A wall stays ONE circle on the ledger and grows in place, so its centre is
    fixed at first sighting while its radius climbs with every repeat. Left
    alone that circle eventually reaches back over the feet of the APC widening
    it — and an APC standing in ground it just marked can only read that as
    somebody else's mistake (SR44). Pushing the centre along the same line keeps
    the mark on the same wall, in the same direction, off the same body.

    Unchanged when the APC is already outside.
    """
    dx, dy = cx - x, cy - y
    span = math.hypot(dx, dy)
    want = max(radius_cm + BODY_CLEAR_CM, radius_cm * MIN_CENTRE_FACTOR)
    if span >= want:
        return (cx, cy)
    if span <= 0.0:
        return (cx, cy)      # no direction to push along; caller placed it badly
    scale = want / span
    return (x + dx * scale, y + dy * scale)
