"""Deterministic place-survey mechanics and survey-claim grounding.

TEST-FLAG (#40): ``filter_survey_claims`` must drop a saved-capture claim when
no survey heading ran this tick, drop a still-needs-surveying claim when the
cell's survey is current, keep both claims when the deterministic facts support
them, and leave ordinary in-character narration (including unrelated uses of
"saved") untouched; ``_cell_survey_note`` must render the fresh/due/active/
unavailable verdicts. Edge cases: empty or non-string text, a sentence carrying
both claims, and text whose every sentence is dropped. Suggested level: offline
unit coverage in ``scripts/agent_runtime``; no Unreal or model call required.
Live/PIE still owes the visible-yaw check and a post-survey model verification.
"""
from __future__ import annotations

import math
import re

from .world_grid import WorldGrid

# A place survey samples the four absolute cardinal headings. In UE yaw,
# East=0, South=90, West=180, North=270.
_CARDINAL_HEADINGS = [0.0, 90.0, 180.0, 270.0]

# Sentence-level detectors for the two narration failures SR28 exposed (#40).
# Deliberately narrow: they match a *claim about surveying*, not any mention of
# looking around, so ordinary in-character description survives untouched.
_CLAIMED_CAPTURE = re.compile(
    r"\b(saved|captured|recorded|took|stored|surveyed|photographed|snapped)\b"
    r"[^.!?]{0,60}?"
    r"\b(view|views|image|images|snapshot|snapshots|photo|photos|capture|captures|"
    r"heading|headings|survey|surveys|direction|directions|cell)\b",
    re.IGNORECASE,
)
_CLAIMED_NEED = re.compile(
    r"\b(need|needs|needed|still|must|should|have to|going to|will)\b"
    r"[^.!?]{0,60}?"
    r"\b(survey|surveying|observe|observing|capture|capturing|record|recording)\b"
    r"[^.!?]{0,60}?"
    r"\b(heading|headings|view|views|direction|directions|cell|here|this cell)\b",
    re.IGNORECASE,
)

# A sentence *about* survey state is not a claim to have captured anything.
# Once surveying became the model's own decision (#57), reading that state aloud
# is how it reasons — "this cell is already surveyed, move on" is repeating the
# fact we hand it. SR37 deleted three such thoughts as fabrications and replaced
# them with "Nothing about surveying this cell can be stated", silencing exactly
# the reasoning the new action depends on.
_DESCRIBES_STATE = re.compile(
    r"\balready\b|\bpreviously\b"
    r"|\b(?:is|was|are|were|been|isn't|wasn't)\s+(?:\w+\s+){0,2}surveyed\b"
    r"|\bsurvey\s+(?:is|was|here is|here was)\b"
    r"|\bneeds?\s+(?:no|another)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def compass_headings() -> list[float]:
    """The absolute yaws for a full 360 place survey — four 90-degree turns.

    Example: ``[0, 90, 180, 270]`` (E, S, W, N in UE coordinates).
    """
    return list(_CARDINAL_HEADINGS)


def filter_survey_claims(text: str, *, captured: bool,
                         needs_survey: bool) -> tuple[str, list[str]]:
    """Drop survey claims the deterministic record does not support (#40).

    ``captured`` is whether this tick actually completed a survey heading, and
    ``needs_survey`` whether the database says the current cell is still due
    one. Sentences making an unsupported claim are removed whole — editing
    natural language in place cannot be done reliably, so the honest option is
    to say less. Returns the surviving text and one reason per dropped claim.

    Example::

        filter_survey_claims("I saved the north view. I keep walking.",
                             captured=False, needs_survey=False)
        # -> ("I keep walking.", ["claimed a saved capture with no survey this tick"])
    """
    if not isinstance(text, str) or not text.strip():
        return "", []

    kept, reasons = [], []
    for sentence in _SENTENCE_SPLIT.split(text.strip()):
        if not sentence.strip():
            continue
        if (not captured and _CLAIMED_CAPTURE.search(sentence)
                and not _DESCRIBES_STATE.search(sentence)):
            reasons.append("claimed a saved capture with no survey heading this tick")
            continue
        if not needs_survey and _CLAIMED_NEED.search(sentence):
            reasons.append("claimed this cell still needs surveying when its survey is current")
            continue
        kept.append(sentence.strip())
    return " ".join(kept), reasons


class CellSweep:
    """Deterministic state machine for sweeping one grid cell.

    Sequences a single, personality-free routine: **walk to the cell center**,
    then **observe each compass heading** in turn, then **done**. Pure — it emits
    the next sub-action given the agent's current position; the live layer
    executes movement/rotation/capture and, on completion, drops the community
    breadcrumb (``PlaceDB.mark_swept``).

    Arrival is sticky: once within ``arrive_tolerance`` of the center, the sweep
    proceeds to observing and never reverts to travelling even if the avatar
    drifts (it's spinning in place, so position may jitter).
    """

    def __init__(self, center: tuple[float, float], z: float,
                 headings: list[float] = None, arrive_tolerance: float = 100.0):
        self.center = center
        self.z = z
        self._headings = list(headings if headings is not None else compass_headings())
        self._tolerance = arrive_tolerance
        self._arrived = False
        self._done = False

    @property
    def is_done(self) -> bool:
        return self._done

    def next_action(self, agent_xy: tuple[float, float]) -> dict:
        """Return the next sub-action: walk-to-center, observe-heading, or done."""
        if self._done:
            return {"type": "sweep_done"}

        if not self._arrived:
            dist = math.hypot(agent_xy[0] - self.center[0], agent_xy[1] - self.center[1])
            if dist > self._tolerance:
                return {"type": "walk_to",
                        "location": [self.center[0], self.center[1], self.z],
                        "_sweep": "goto_center"}
            self._arrived = True  # sticky

        if self._headings:
            yaw = self._headings.pop(0)
            return {"type": "observe_heading", "yaw": yaw, "_sweep": "observe"}

        self._done = True
        return {"type": "sweep_done"}


def default_sweep(world_grid: WorldGrid, col: int, row: int, z: float,
                  arrive_tolerance: float = None,
                  headings: list[float] = None) -> CellSweep | None:
    """Build a :class:`CellSweep` targeting the center of cell ``(col, row)``.

    Returns None when the grid is unbounded (no cell center exists). The default
    arrival tolerance is a quarter of a cell, so "at the center" is forgiving.
    """
    center = world_grid.cell_center(col, row)
    if center is None:
        return None
    tol = arrive_tolerance if arrive_tolerance is not None else world_grid.cell_size / 4.0
    return CellSweep(center=center, z=z, headings=headings, arrive_tolerance=tol)
