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

# The longest single order, however open the ground looks. Three 30 m cells:
# far enough that crossing done ground is cheap, short enough that the APC
# still re-decides several times inside a district.
MAX_STEP_CM = 9000.0

# What the model's coarse distance word is worth. A word is a judgement it can
# make from a picture; a number in centimetres is not.
PREFERRED_CM = {"close": 400.0, "normal": NOMINAL_STEP_CM, "far": 4500.0}

# Stop this far short of ground that must not be entered, so arriving at the
# edge of a refused patch is not the same as standing in it.
STOP_SHORT_MARGIN_CM = 100.0


def plan_step(prefer: str | None = None,
              open_run_cm: float = 0.0,
              stop_short_cm: float | None = None,
              clearance_cm: float | None = None,
              fits: bool | None = None,
              standoff_cm: float = 300.0,
              nominal_cm: float = NOMINAL_STEP_CM,
              min_cm: float = MIN_STEP_CM,
              max_cm: float = MAX_STEP_CM) -> dict:
    """Decide how far this step travels.

    ``prefer`` is the model's coarse word ("close"/"normal"/"far") or None.
    ``open_run_cm`` is how far the shared map says the ground ahead has already
    been walked with good footing — the reason to grow. ``stop_short_cm`` is the
    distance to the first ground that must not be entered (a no-go patch, a
    refused cell), ``clearance_cm``/``fits`` are the body-box probe (#81) — the
    reasons to shrink. ``None`` means *not measured*, which is never treated as
    *clear*: an unmeasured cap simply does not apply.

    Returns ``{"distance_cm", "wanted_cm", "capped_by", "grew", "why"}``.
    ``distance_cm == 0.0`` means there is no room to step at all — the caller
    reports that as a fact instead of ordering a move.
    """
    wanted = PREFERRED_CM.get(str(prefer or "").strip().lower(), nominal_cm)

    # Grow across proven ground. Only a run LONGER than the step we already
    # wanted is a reason to change anything — a single open cell ahead is the
    # ordinary case, not an invitation to sprint.
    grew = False
    if open_run_cm and open_run_cm > wanted:
        wanted = open_run_cm
        grew = True
    wanted = min(wanted, max_cm)

    # Shrink for anything ahead. Every cap is a distance the body may travel.
    caps: list[tuple[str, float]] = []
    if stop_short_cm is not None:
        caps.append(("refused ground", stop_short_cm - STOP_SHORT_MARGIN_CM))
    if clearance_cm is not None:
        caps.append(("something in the way", clearance_cm - standoff_cm))

    distance = wanted
    capped_by = None
    for name, limit in caps:
        if limit < distance:
            distance = limit
            capped_by = name
    if capped_by:
        grew = False  # a capped step never grew, whatever the map said

    if distance < min_cm:
        return {"distance_cm": 0.0, "wanted_cm": round(wanted, 1),
                "capped_by": capped_by or ("no fit" if fits is False else "no room"),
                "grew": False,
                "why": _why_none(capped_by, fits)}

    distance = min(distance, max_cm)
    return {"distance_cm": round(distance, 1), "wanted_cm": round(wanted, 1),
            "capped_by": capped_by, "grew": grew,
            "why": _why(distance, wanted, capped_by, grew, open_run_cm)}


def _m(cm: float) -> str:
    return f"{round(cm / 100.0, 1)} m"


def _why(distance: float, wanted: float, capped_by: str | None,
         grew: bool, open_run_cm: float) -> str:
    """One plain line of fact for the prompt and the log. No advice."""
    if capped_by:
        return (f"your step was cut to {_m(distance)} — {capped_by} "
                f"stopped it short of the {_m(wanted)} it would have covered")
    if grew:
        return (f"your step was {_m(distance)}: the map says the ground that far "
                f"ahead has already been walked, so crossing it took one order")
    return ""


def _why_none(capped_by: str | None, fits: bool | None) -> str:
    if fits is False:
        return "there was no room to step: your body does not fit that way"
    if capped_by:
        return f"there was no room to step: {capped_by} is directly ahead"
    return "there was no room to step"
