"""Offline tests for decision-prompt context rendering (WP1) — no LLM, no Unreal.

Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_prompt_context.py

Covers the pure renderers that surface the recall context (acquaintances,
known places, relevant episodes) into _USER_TEMPLATE_VISION, and pins the
template contract so an edit can't silently drop the sections.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.llm_router import (             # noqa: E402
    _USER_TEMPLATE_VISION,
    _acquaintance_lines,
    _episode_lines,
    _known_place_lines,
    _schedule_note,
)


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_acquaintance_lines():
    full = _acquaintance_lines([{
        "name": "Maren", "meet_count": 4, "interaction_count": 2,
        "last_seen": "Day 1, 09:12",
    }])
    check("acquaintance renders name", "Maren" in full)
    check("acquaintance renders meet count", "met 4 times" in full)
    check("acquaintance renders interactions", "spoken with 2 times" in full)
    check("acquaintance renders last seen", "last seen Day 1, 09:12" in full)

    sparse = _acquaintance_lines([{"name": "Dufus", "meet_count": 1}])
    check("falsy clauses omitted", "spoken" not in sparse and "last seen" not in sparse)

    check("empty -> placeholder", _acquaintance_lines([]) == "Nobody yet — you have not met anyone.")
    check("None -> placeholder", _acquaintance_lines(None) == "Nobody yet — you have not met anyone.")

    many = _acquaintance_lines([{"name": f"P{i}", "meet_count": 1} for i in range(10)])
    check("capped at 8 lines", len(many.splitlines()) == 8)
    check("nameless items skipped", "None" not in _acquaintance_lines([{"meet_count": 3}]))

    # #12.1: a recently-greeted acquaintance is marked so the gate won't re-greet.
    greeted = _acquaintance_lines([{"name": "Maren", "meet_count": 4, "recently_greeted": True}])
    check("recently-greeted mark rendered", "already greeted recently" in greeted)
    not_greeted = _acquaintance_lines([{"name": "Maren", "meet_count": 4, "recently_greeted": False}])
    check("no mark when not recently greeted", "already greeted recently" not in not_greeted)


def test_known_place_lines():
    out = _known_place_lines([{"name": "village square", "bearing": "SE", "distance_m": 34.4}])
    check("place renders name/bearing/distance", "- village square — SE, 34 m" in out)
    out = _known_place_lines([{"name": "home", "bearing": "N", "distance_m": 11.6}])
    check("distance rounds to whole meters", "12 m" in out)
    out = _known_place_lines([{"name": "My Home", "bearing": "N", "distance_m": 12.0,
                               "owner": "maren"}])
    check("owned place renders its owner (#11.2)",
          "- My Home — N, 12 m (maren's place)" in out)
    out = _known_place_lines([{"name": "village square", "bearing": "SE", "distance_m": 34.4}])
    check("community place has no owner suffix", "place)" not in out)
    placeholder = "No named places yet — name places as you discover them."
    check("empty -> placeholder", _known_place_lines([]) == placeholder)
    check("None -> placeholder", _known_place_lines(None) == placeholder)


def test_episode_lines():
    event = _episode_lines([{
        "world_time": "Day 1, 09:12", "grid_cell": "0,0",
        "place": "vegetable truck", "saw": ["Maren"], "action": "speak_to",
        "outcome": "success",
    }])
    check("event renders time", "[Day 1, 09:12]" in event)
    check("event renders place", "at vegetable truck" in event)
    check("event renders action + saw", "speak_to" in event and "saw Maren" in event)

    summary = _episode_lines([{
        "kind": "summary", "place": "vegetable truck", "count": 14,
        "first_time": "Day 1, 08:00", "last_time": "Day 1, 11:40",
    }])
    check("summary renders span + count",
          "[Day 1, 08:00–Day 1, 11:40]" in summary and "14 events" in summary)

    check("empty -> placeholder", _episode_lines([]) == "Nothing memorable yet.")
    check("None -> placeholder", _episode_lines(None) == "Nothing memorable yet.")


def test_template_contract():
    for placeholder in ("{acquaintance_lines}", "{known_place_lines}", "{episode_lines}"):
        check(f"template has {placeholder}", placeholder in _USER_TEMPLATE_VISION)
    check("template has People You Know heading", "## People You Know" in _USER_TEMPLATE_VISION)
    check("template has Places You Know heading", "## Places You Know" in _USER_TEMPLATE_VISION)
    check("sighting rule references People You Know",
          'A CHARACTER sighting matching\na name under "People You Know"' in _USER_TEMPLATE_VISION)


def test_reaction_gate_template():
    """WP2 (#10.5 BALANCED gate): routine wins; only a known person or being
    spoken to interrupts; exploration only when nothing is scheduled."""
    check("priorities block present", "## What Wins Right Now" in _USER_TEMPLATE_VISION)
    check("strangers do not interrupt", "Do NOT stop for\nstrangers" in _USER_TEMPLATE_VISION
          or "Do NOT stop for strangers" in _USER_TEMPLATE_VISION.replace("\n", " "))
    check("unconditional greeting pull removed",
          "consider greeting or\napproaching them" not in _USER_TEMPLATE_VISION
          and "consider greeting or approaching them" not in _USER_TEMPLATE_VISION)
    check("exploration gated on empty schedule",
          "If nothing is scheduled right now and nothing in view" in _USER_TEMPLATE_VISION)
    check("resume after interrupt stated",
          "goes back to the scheduled destination" in _USER_TEMPLATE_VISION)
    check("quirks are a nudge, not an override",
          "they do not cancel WHERE you are going" in _USER_TEMPLATE_VISION)
    # #12.1: the greet gate excludes someone already greeted this encounter.
    flat = _USER_TEMPLATE_VISION.replace("\n", " ")
    check("greet gate skips a recently-greeted person",
          'have NOT already greeted recently' in flat)
    check("already-greeted -> keep going, don't stop again",
          'do not stop again' in flat)
    check("being spoken to still gets a response even if already greeted",
          "respond (even if you already greeted them)" in flat)


def test_schedule_note_weighting():
    travel = _schedule_note({
        "status": "travel", "place": "village square",
        "intent": "It's time to sell — head to village square.",
    })
    check("travel is stated as the priority", "This is your priority right now" in travel)
    check("travel names the walk_to target", 'target_location "village square"' in travel)
    check("travel names the only valid interrupts",
          "a person you know or someone speaking to you" in travel)
    check("activity is deferred to the destination",
          "Do NOT start the scheduled activity on the way" in travel)

    act = _schedule_note({"status": "act", "place": "stall",
                          "intent": "You're at stall where you should be — sell."})
    check("act branch unchanged", "You are where you should be" in act)
    idle = _schedule_note(None)
    check("idle/None branch unchanged", "nothing fixed right now" in idle)


def main():
    test_acquaintance_lines()
    test_known_place_lines()
    test_episode_lines()
    test_template_contract()
    test_reaction_gate_template()
    test_schedule_note_weighting()
    print("\nAll prompt-context checks passed.")


if __name__ == "__main__":
    main()
