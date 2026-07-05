"""Daily-schedule planner — Master Plan Milestone 1 (first slice).

Gives an AIPC a *life* instead of an idle loop: a day is broken into time blocks
(`{start, end, activity, place}`), and at any sim-time the planner answers the one
load-bearing question — **"what should I be doing right now?"** — so the tick loop
can follow a routine rather than re-deciding from scratch every tick.

Per the Master Plan, the daily plan is the **spine** of the cognitive loop and the
reactive tick becomes the interrupt handler. This module is the spine's
deterministic core; wiring it into `agent_manager`'s tick (and the reaction gate
that interrupts it) is the next slice and needs live PIE verification.

Design seams that keep this offline-testable and loop-safe:
  * **Time selection is pure** — `current_block(schedule, minute_of_day)` is a
    plain function over data; no clock, no I/O.
  * **The LLM is injected** — `generate_daily_plan(..., ask=<callable>)` takes the
    decision LLM as a `prompt -> text` callable. With `ask=None` (or on any
    failure) it returns a deterministic fallback, so the module has no provider
    dependency and tests run with zero LLM calls.
  * **Places are names, not coordinates** — a block's ``place`` is a name like
    ``"village square"``; resolving it to a world location is the existing
    named-place navigation's job (`walk_to`), keeping spatial knowledge learned
    and grounded (Master Plan §16), not declared here.

A block::

    {"start": "08:00", "end": "12:00", "activity": "tend the vegetable stall",
     "place": "vegetable truck"}
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger("AgentRuntime")

_DAY_MINUTES = 24 * 60
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_DAY_RE = re.compile(r"[Dd]ay\s+(\d+)")

# Used when there is no LLM (ask=None) or generation fails — the agent still has a
# valid all-day block so the loop never falls back to a hard-coded behavior rule.
FALLBACK_ACTIVITY = "go about my day following my goals"


def to_minutes(hhmm: str) -> int:
    """``"08:30"`` -> ``510`` (minute of day, 0..1440).

    Accepts ``"24:00"`` as end-of-day (1440). Raises ``ValueError`` on a malformed
    or out-of-range time so callers can drop a bad block rather than mis-schedule.
    """
    m = _TIME_RE.fullmatch(str(hhmm).strip())
    if not m:
        raise ValueError(f"bad time {hhmm!r}")
    hours, mins = int(m.group(1)), int(m.group(2))
    total = hours * 60 + mins
    if mins >= 60 or total > _DAY_MINUTES:
        raise ValueError(f"out-of-range time {hhmm!r}")
    return total


def minute_of_day(clock_text: str) -> int:
    """Parse a `WorldClock.now_text()` string (``"Day 1, 08:23"``) to minute-of-day.

    Tolerant: pulls the first ``HH:MM`` it finds. Returns 0 if none is present
    (treated as start-of-day) rather than raising into the tick loop.
    """
    m = _TIME_RE.search(str(clock_text))
    if not m:
        return 0
    return int(m.group(1)) * 60 + int(m.group(2))


def absolute_minute(clock_text: str) -> int:
    """Minutes since the start of Day 1 from a `WorldClock.now_text()` string.

    ``"Day 2, 08:00"`` -> ``1*1440 + 480 = 1920``. Day 1 is the origin; a missing
    day counts as Day 1. Lets callers measure elapsed sim-time across day rollover
    (e.g. the greet cooldown, #12.1). Example: ``absolute_minute("Day 1, 00:30")``
    -> ``30``.
    """
    m = _DAY_RE.search(str(clock_text))
    day = int(m.group(1)) if m else 1
    return (day - 1) * _DAY_MINUTES + minute_of_day(clock_text)


def minutes_between(earlier: str, later: str) -> int:
    """Signed sim-minutes from ``earlier`` to ``later`` (both WorldClock strings).

    Positive when ``later`` is after ``earlier``; negative if the clock went
    backwards (e.g. a day was restarted). Example:
    ``minutes_between("Day 1, 08:00", "Day 1, 09:30")`` -> ``90``.
    """
    return absolute_minute(later) - absolute_minute(earlier)


def normalize_schedule(blocks: list) -> list[dict]:
    """Coerce a raw block list into a clean, sorted schedule.

    Drops anything malformed (bad/missing times, ``start >= end``, non-dict),
    defaults ``activity``/``place`` to safe strings, and sorts by start time.
    Never raises — a fully bad input yields ``[]`` (caller falls back).
    """
    clean: list[dict] = []
    for raw in blocks or []:
        if not isinstance(raw, dict):
            continue
        try:
            start = to_minutes(raw["start"])
            end = to_minutes(raw["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if start >= end:
            continue
        clean.append({
            "start": _fmt(start),
            "end": _fmt(end),
            "activity": str(raw.get("activity", "")).strip() or FALLBACK_ACTIVITY,
            "place": str(raw.get("place", "")).strip(),
        })
    clean.sort(key=lambda b: to_minutes(b["start"]))
    return clean


def current_block(schedule: list[dict], minute: int) -> dict | None:
    """The block active at ``minute`` (``start <= minute < end``), or ``None``.

    The spine of the loop: pure, deterministic, no clock or I/O. On overlapping
    blocks the earliest-starting match wins (schedules are sorted by start).
    """
    for block in schedule:
        try:
            if to_minutes(block["start"]) <= minute < to_minutes(block["end"]):
                return block
        except (KeyError, ValueError, TypeError):
            continue
    return None


def current_activity(schedule: list[dict], clock_text: str) -> dict | None:
    """Convenience: the active block given a `WorldClock.now_text()` string."""
    return current_block(schedule, minute_of_day(clock_text))


def step(schedule: list[dict], minute: int, current_place: str = None,
         prev_activity: str = None, at_place: bool = None) -> dict:
    """Walk the schedule one tick: *what should I be doing right now?*

    This is the **sequencer** — the deterministic reasoning the Master Plan calls
    the spine: "I woke up, what time is it, where should I be, am I already there,
    and did a new block just start?". It does not decide the *sub-action* (that is
    the LLM's job, grounded by ``intent``); it decides the scaffolding around it.

    Inputs (all data — pure, testable):
      * ``minute`` — minute-of-day now (see `minute_of_day`).
      * ``current_place`` — the named place the agent is at, if known (e.g. from
        perception / nearest named place). ``None`` = unknown → treated as "not
        there yet".
      * ``prev_activity`` — the activity from the previous step, to detect a block
        boundary crossing. ``None`` on the first step (wake) = no transition.
      * ``at_place`` — geometric ground truth from the caller: is the agent
        physically inside the block's place cell? ``True``/``False`` overrides
        the name match (position beats labels — fixes "woke up at my stall but
        its name isn't in the DB yet, so I wandered off"); ``None`` = unknown,
        fall back to the ``current_place`` name match.

    Returns a directive::

        {"block": <active block or None>,
         "activity": "tend the stall",      # scheduled activity ("" when idle)
         "place": "vegetable truck",        # where it happens ("" = anywhere)
         "status": "travel" | "act" | "idle",
         "transition": True,                # a new block just began this step
         "intent": "Head to ... first — your scheduled activity there is ..."}   # for the LLM / the log

    ``status``: **travel** = go to ``place``; **act** = you're where you should be
    (or the activity has no place) so do it; **idle** = nothing scheduled, free to
    choose.
    """
    block = current_block(schedule, minute)
    if block is None:
        activity, place, status = "", "", "idle"
        intent = "Nothing is scheduled right now — free to choose what to do."
    else:
        activity = block["activity"]
        place = block.get("place", "")
        here = at_place if at_place is not None else _same_place(current_place, place)
        if place and not here:
            status = "travel"
            # Destination-first: naming the activity first ("It's time to greet
            # passers-by — head to...") makes the LLM start the activity en
            # route (seen live 2026-07-01: Dufus greeting strangers at the gas
            # station instead of arriving). The activity is stated as deferred.
            intent = (f"Head to {place} first — your scheduled activity there is: "
                      f"{activity}. It starts when you arrive.")
        else:
            status = "act"
            intent = (f"You're at {place} where you should be — {activity}."
                      if place else f"Time to {activity}.")
    transition = prev_activity is not None and prev_activity != activity
    return {"block": block, "activity": activity, "place": place,
            "status": status, "transition": transition, "intent": intent}


def generate_daily_plan(character_text: str, goals_text: str, *,
                        ask=None, day: str = "Day 1") -> list[dict]:
    """Build a day's schedule from the agent's persona + goals.

    ``ask`` is the decision LLM as a ``prompt -> text`` callable (injected so this
    stays provider-free and testable). With ``ask=None``, or if the model output
    can't be parsed into at least one valid block, returns a deterministic
    single-block fallback. Never raises — planning failure degrades to a routine,
    it does not crash the loop.
    """
    if ask is None:
        return _fallback(goals_text)
    try:
        text = ask(_prompt(character_text, goals_text, day))
        blocks = normalize_schedule(json.loads(_strip_fences(text)))
    except Exception as e:  # parse / model / shape failure — degrade, don't crash
        logger.warning("generate_daily_plan: %s — using fallback", e)
        return _fallback(goals_text)
    return blocks or _fallback(goals_text)


def day_of(clock_text: str) -> str:
    """Day label from a `WorldClock.now_text()` string: ``"Day 1, 08:23"`` -> ``"Day 1"``."""
    return str(clock_text).split(",")[0].strip() or "Day 1"


def ensure_daily_plan(agent, day: str, *, ask=None, agents_dir=None) -> list[dict]:
    """Return ``agent``'s schedule for ``day``, generating + persisting it when the
    stored one is for a different day (or absent).

    Idempotent within a sim-day, so the tick loop can call it every tick cheaply —
    only the first call per day invokes ``ask`` (the LLM). ``agent`` is duck-typed
    (an `Agent`): reads ``character_text``/``goals_text`` + ``daily_schedule_day``/
    ``daily_schedule_blocks`` and writes via ``set_daily_schedule``.
    """
    if agent.daily_schedule_day == day and agent.daily_schedule_blocks:
        return agent.daily_schedule_blocks
    blocks = generate_daily_plan(agent.character_text, agent.goals_text, ask=ask, day=day)
    agent.set_daily_schedule(blocks, day, agents_dir)
    return blocks


# Internals


def _fmt(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _same_place(current: str, target: str) -> bool:
    """Loose place-name match for "am I already there?".

    Case-insensitive, with containment either way so a coarse schedule name
    ("vegetable truck") matches a richer perceived label ("vegetable truck stand
    on main street"). Unknown current place (``None``/empty) is never a match — if
    we can't confirm we're there, the sequencer says travel.
    """
    if not current or not target:
        return False
    c, t = current.strip().lower(), target.strip().lower()
    return c == t or c in t or t in c


def _fallback(goals_text: str) -> list[dict]:
    """A single all-day block so the agent always has something to do."""
    activity = _first_line(goals_text) or FALLBACK_ACTIVITY
    return [{"start": "00:00", "end": "24:00", "activity": activity, "place": ""}]


def _first_line(text: str) -> str:
    for line in (text or "").splitlines():
        stripped = line.strip().lstrip("#-* ").strip()
        if stripped:
            return stripped
    return ""


def _strip_fences(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
    return raw.strip()


def _prompt(character_text: str, goals_text: str, day: str) -> str:
    return _PROMPT.format(day=day, character=character_text.strip(), goals=goals_text.strip())


_PROMPT = """\
You are planning {day} for a character living in a small town. Based on who they
are and what they want, write their daily routine as a schedule.

WHO THEY ARE:
{character}

WHAT THEY WANT:
{goals}

Return JSON ONLY — no prose, no markdown fences — as an array of time blocks that
cover the waking day in order, each:
  {{"start": "HH:MM", "end": "HH:MM", "activity": "<what they do>", "place": "<named place, or empty>"}}

Rules: 24-hour times; blocks in order and non-overlapping; "place" is a place
NAME they would go to (e.g. "village square", "home"), not coordinates; keep it to
a handful of blocks for the day."""
