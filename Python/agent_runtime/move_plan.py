"""The move plan — how far a step goes, decided by the lizard brain (#86).

WHERE to go is the mind's call: a compass word, a place name, a character. HOW
FAR that word carries is a *body* question, and until this module existed there
was no answer to it — every direction-relative move was exactly
``_STEP_DISTANCE`` (15 m), forever, whatever was in front of the body and
however close the goal was.

Two failures came out of that one constant, and they are opposites:

* **Overshoot.** A refused yard 5 m ahead is entered by a 15 m step, because a
  15 m step cannot aim finer than the trap is wide (SR46: three patches refused
  accurately, then landed in). The only correction available was another 15 m
  step the other way, which overshoots back — so the loop rings instead of
  converging. The action vocabulary could not say *a bit closer*.
* **Crawling.** Crossing ground the shared map already says is walked, surveyed
  and clear costs one paid decision per 15 m. An overnight survey spends its
  night re-deciding its way across ground nobody needed to think about.

So the plan is computed from evidence, not from a rule the model has to be
told: it **shrinks** toward whatever must not be walked into, and **grows**
across ground the shared map has already proven. The model keeps saying only
which way; nothing here decides direction, and nothing here refuses a move.

Pure functions — the caller gathers the evidence (`AgentManager._scan_ahead`
reads PlaceDB, `_probe_ahead` reads the engine) and this decides the number.
"""
from __future__ import annotations

# The step a direction word means when nothing is known either way.
NOMINAL_STEP_CM = 1500.0

# Below this a "step" is not travel, it is a shuffle that burns a paid tick and
# proves nothing. A plan that cannot clear it returns zero, and the caller says
# so out loud rather than ordering a move that cannot help.
MIN_STEP_CM = 200.0

# The longest single order, however open the ground looks. Three 30 m cells —
# the user's "nothing ahead for the next 100 metres".
#
# SR47 proved this number is only safe because of how a long step is WALKED. A
# step is a straight line on the map, but the engine walks a navmesh PATH to the
# point it is given, and the further away that point is the more freedom the
# path has to go somewhere else: Dufus asked for 45 m north twice and arrived
# 52 m east, then 48 m west, routed around a building both times. The user
# watched him strike out, come back to his starting point and walk into a
# trailer house.
#
# So a grown step is never handed to the engine whole. `leg_distances` cuts it
# into hops of one nominal step, and `AgentManager._pulse_walk` walks them one
# per tick with no model call — the engine is never given a target further away
# than the fixed 15 m it always handled correctly, and the APC re-checks the
# ground between every hop.
MAX_STEP_CM = 9000.0

# What the model's coarse distance word is worth. A word is a judgement it can
# make from a picture; a number in centimetres is not.
PREFERRED_CM = {"close": 400.0, "normal": NOMINAL_STEP_CM, "far": 4500.0}

# Stop this far short of ground that must not be entered, so arriving at the
# edge of a refused patch is not the same as standing in it.
STOP_SHORT_MARGIN_CM = 100.0


def plan_step(prefer: str | None = None,
              reach_cm: float | None = None,
              stop_short_cm: float | None = None,
              open_run_cm: float = 0.0,
              standoff_cm: float = 300.0,
              nominal_cm: float = NOMINAL_STEP_CM,
              min_cm: float = MIN_STEP_CM,
              max_cm: float = MAX_STEP_CM) -> dict:
    """Decide how far this step travels. **The engine's answer IS the step.**

    ``reach_cm`` is what the engine said when asked *how far can this body travel
    along this heading* — a sweep of the APC's own capsule, so it measures the
    actual line of travel rather than estimating it. It is the SOURCE of the
    distance, not a limit on a constant. A step is *as far as the ground allows*,
    standoff subtracted; ``nominal_cm`` is only the fallback for when nothing
    could be measured at all, and a step taken that way is labelled a guess.

    ``stop_short_cm`` is the first ground somebody REFUSED — a no-go patch, a
    refused cell. The engine cannot know about that: it is a social fact, not a
    physical one, so it caps the engine's answer.

    ``prefer`` is the model's coarse word, and it is only ever a **ceiling**. The
    model may ask to stop sooner than the ground requires ("close" — I can see the
    thing I mean to stop at); it may never ask to travel further than it allows.

    ``open_run_cm`` is how far the shared map says this ground has been walked
    before. It decides nothing now. It is carried so the APC can be told whether
    the ground it is about to cross is known or new.

    Returns ``{"distance_cm", "wanted_cm", "capped_by", "grew", "measured",
    "why"}``. ``distance_cm == 0.0`` means there is no room to step at all.
    """
    asked = PREFERRED_CM.get(str(prefer or "").strip().lower())

    if reach_cm is None:
        wanted = asked if asked is not None else nominal_cm
        measured = False
    else:
        wanted = max(float(reach_cm) - standoff_cm, 0.0)
        measured = True
        if asked is not None:
            wanted = min(wanted, asked)
    wanted = min(wanted, max_cm)

    # Remember whether the model's word, rather than the ground, set the length.
    asked_shorter = (measured and asked is not None
                     and asked < max(float(reach_cm or 0.0) - standoff_cm, 0.0))

    distance = wanted
    capped_by = None
    if stop_short_cm is not None:
        limit = stop_short_cm - STOP_SHORT_MARGIN_CM
        if limit < distance:
            distance = limit
            capped_by = "refused ground"

    if distance < min_cm:
        return {"distance_cm": 0.0, "wanted_cm": round(wanted, 1),
                "capped_by": capped_by or "no room", "grew": False,
                "measured": measured,
                "why": (f"there was no room to step: {capped_by} is directly ahead"
                        if capped_by else
                        "there was no room to step: the ground ahead is blocked "
                        "within your own body's length")}

    return {"distance_cm": round(distance, 1), "wanted_cm": round(wanted, 1),
            "capped_by": capped_by, "grew": distance > nominal_cm,
            "measured": measured,
            "why": _why(distance, capped_by, measured, open_run_cm,
                        asked_shorter, reach_cm, standoff_cm)}


def leg_distances(distance_cm: float,
                  leg_cm: float = NOMINAL_STEP_CM) -> list[float]:
    """Cut a step into hops, as distances from the starting point.

    The engine gets one hop at a time. A hop is a distance the fixed 15 m step
    always walked correctly, so the navmesh has almost no room to route around
    something and end up somewhere else — which is why SR47's 45 m orders arrived
    fifty metres sideways and this one does not.

    Returns cumulative distances ending exactly on ``distance_cm``. A final
    remainder shorter than ``MIN_STEP_CM`` is absorbed into the hop before it
    rather than left as a shuffle at the end.
    """
    if distance_cm <= leg_cm:
        return [float(distance_cm)]
    legs: list[float] = []
    d = leg_cm
    while d < distance_cm:
        legs.append(d)
        d += leg_cm
    if legs and distance_cm - legs[-1] < MIN_STEP_CM:
        legs.pop()
    legs.append(float(distance_cm))
    return legs


def _m(cm: float) -> str:
    return f"{round(cm / 100.0, 1)} m"


def _why(distance: float, capped_by: str | None, measured: bool,
         open_run_cm: float, asked_shorter: bool = False,
         reach_cm: float | None = None, standoff_cm: float = 300.0) -> str:
    """One plain line of fact for the prompt and the log. No advice.

    A step is as far as the ground allowed, so the honest sentence names the
    ground, not the step. When the map has been there before, say so — crossing
    known ground and crossing new ground are different acts, and the APC should
    be able to tell them apart without having to infer it.
    """
    if capped_by:
        return (f"your step was {_m(distance)}, stopped short of the clear ground "
                f"because {capped_by} lies ahead")
    if not measured:
        return (f"your step was the default {_m(distance)} — nothing ahead of you "
                f"could be measured, so that distance is a guess, not a fact")
    if asked_shorter:
        clear = max(float(reach_cm or 0.0) - standoff_cm, 0.0)
        return (f"your step was {_m(distance)} because you asked to stop close; "
                f"the ground ahead measured clear for {_m(clear)}")
    # Only ever describe THIS step. A 90 m open run behind a wall 9 m away is
    # true and useless: the sentence must be about the ground being crossed.
    known_cm = min(open_run_cm, distance)
    if known_cm >= distance:
        known = " All of it is ground APCs have walked before."
    elif known_cm > 0:
        known = (f" The first {_m(known_cm)} of it is ground APCs have walked "
                 f"before; the rest is new.")
    else:
        known = " None of it has been walked before."
    return (f"your step was {_m(distance)}: that is how far the ground ahead "
            f"measured clear for your body.{known}")
