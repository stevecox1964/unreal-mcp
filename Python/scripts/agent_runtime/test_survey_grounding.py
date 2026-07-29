"""Offline tests for survey narration grounding (backlog #40).

SR28 proved the deterministic survey telemetry works but cognition still
narrated missing headings and invented saved captures after a survey resolved.
Two defences are covered here: the authoritative per-cell prompt verdict, and
the in-code filter that drops claims no deterministic fact supports.

No Unreal, no model call, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_survey_grounding.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.cell_sweep import filter_survey_claims   # noqa: E402
from agent_runtime.llm_router import _cell_survey_note      # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# ── The exact SR28 defect ─────────────────────────────────────────────────────

sr28 = ("I still need to survey the remaining headings here. "
        "I saved the north view. I keep walking toward the square.")
kept, reasons = filter_survey_claims(sr28, captured=False, needs_survey=False)
check("SR28: both invented claims dropped", kept == "I keep walking toward the square.")
check("SR28: two distinct reasons reported", len(reasons) == 2)
check("SR28: capture claim named", any("saved capture" in r for r in reasons))
check("SR28: needs-survey claim named", any("needs surveying" in r for r in reasons))

# ── Supported claims must survive ─────────────────────────────────────────────

kept, reasons = filter_survey_claims("I saved the north view.",
                                     captured=True, needs_survey=False)
check("a real capture this tick is kept", kept == "I saved the north view." and not reasons)

kept, reasons = filter_survey_claims("I need to survey this cell.",
                                     captured=False, needs_survey=True)
check("a genuinely due cell may state the need",
      kept == "I need to survey this cell." and not reasons)

kept, reasons = filter_survey_claims("I captured the east heading. I walk on.",
                                     captured=True, needs_survey=True)
check("both facts true keeps everything", reasons == [] and "captured" in kept)

# ── Ordinary narration is not collateral damage ───────────────────────────────

for sentence in ("I look around the square and greet Maren.",
                 "The market is busy; I head for my stall.",
                 "I saved a seat for Maren.",
                 "I observe that Maren seems tired."):
    kept, reasons = filter_survey_claims(sentence, captured=False, needs_survey=False)
    check(f"passthrough: {sentence!r}", kept == sentence and reasons == [])

# ── Edge cases ────────────────────────────────────────────────────────────────

check("empty text", filter_survey_claims("", captured=False, needs_survey=False) == ("", []))
check("non-string text",
      filter_survey_claims(None, captured=False, needs_survey=False) == ("", []))

kept, reasons = filter_survey_claims("I saved the north view.",
                                     captured=False, needs_survey=False)
check("every sentence dropped yields empty text", kept == "" and len(reasons) == 1)

kept, reasons = filter_survey_claims(
    "I still need to survey here so I saved the west view.",
    captured=False, needs_survey=False)
check("one sentence carrying both claims is dropped once",
      kept == "" and len(reasons) == 1)

# ── The authoritative prompt verdict ──────────────────────────────────────────

fresh = _cell_survey_note({"cell_survey": {
    "cell": "7,5", "fresh": True, "needs_survey": False,
    "active_here": False, "total_headings": 4}})
check("fresh cell states it does NOT need surveying", "does NOT need" in fresh)
check("fresh cell forbids claiming a save", "do not claim you saved" in fresh.lower())
check("fresh cell names the cell", "(7,5)" in fresh)

due = _cell_survey_note({"cell_survey": {
    "cell": "8,5", "fresh": False, "needs_survey": True,
    "active_here": False, "total_headings": 4}})
check("due cell is eligible, not in progress", "eligible" in due and "not surveying it" in due)
check("due cell still forbids a capture claim", "captured or saved" in due)

active = _cell_survey_note({"cell_survey": {
    "cell": "8,5", "fresh": False, "needs_survey": True, "active_here": True,
    "completed_headings": ["E", "S"], "failed_headings": [], "total_headings": 4}})
check("active survey reports saved count", "2/4 headings saved" in active)
check("active survey lists the saved headings", "E, S" in active)

missing = _cell_survey_note({})
check("absent facts render the unavailable verdict", "unavailable" in missing)
check("absent facts still forbid both inventions",
      "needs surveying" in missing and "captured or saved" in missing)

print("\nAll survey-grounding tests passed.")
