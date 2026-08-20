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
WORLDS = ROOT / "worlds"                        # authored agent files (#64)
sys.path.insert(0, str(ROOT))

from agent_runtime import agenda  # noqa: E402
from agent_runtime.llm_router import (             # noqa: E402
    _ACTION_SCHEMAS,
    _USER_TEMPLATE_VISION,
    _USER_TEMPLATE,
    _acquaintance_lines,
    _episode_lines,
    _heard_note,
    _known_place_lines,
    _nearby_character_lines,
    _schedule_note,
    _active_interrupt_note,
    _seen_text,
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


def test_nearby_character_lines():
    out = _nearby_character_lines([{"name": "Dufus", "distance_cm": 1696.0}])
    check("engine-nearby fact renders name and distance", "Dufus" in out and "17 m" in out)
    check("empty nearby facts are explicit", "no other apc" in _nearby_character_lines([]).lower())


def test_template_contract():
    for placeholder in ("{acquaintance_lines}", "{known_place_lines}", "{episode_lines}",
                        "{nearby_character_lines}", "{agenda_context}", "{frontier_note}"):
        check(f"template has {placeholder}", placeholder in _USER_TEMPLATE_VISION)
    check("template has the wider-map heading", "## The Wider Map" in _USER_TEMPLATE_VISION)
    check("template has People You Know heading", "## People You Know" in _USER_TEMPLATE_VISION)
    check("template has Places You Know heading", "## Places You Know" in _USER_TEMPLATE_VISION)
    check("sighting rule references People You Know",
          'A CHARACTER sighting matching\na name under "People You Know"' in _USER_TEMPLATE_VISION)
    check("fallback template also receives agenda context", "{agenda_context}" in _USER_TEMPLATE)
    check("vision output reserves bounded completion claim", '"task_completion": null' in _USER_TEMPLATE_VISION)
    check("fallback output reserves bounded completion claim", '"task_completion": null' in _USER_TEMPLATE)
    check("completion guidance names exact policy/task/evidence",
          "time_or_llm_confirmed" in _USER_TEMPLATE_VISION
          and "exact active id" in _USER_TEMPLATE_VISION
          and "grounded sentence" in _USER_TEMPLATE_VISION)


def test_agenda_prompt_context():
    facts = {
        "today_so_far": [{
            "world_time": "Day 1, 08:30", "event": "completed",
            "task_id": "home", "objective": "Eat breakfast",
        }],
        "right_now": {
            "task_id": "square", "status": "active", "objective": "Travel to square",
            "place": "village square", "arrival_verdict": "not_at_place",
            "completion": {"type": "arrive_at_place"},
            "route": {"leg": 1, "total": 3, "to_cell": [6, 5]},
        },
        "next": {
            "task_id": "greet", "objective": "Greet people", "place": "village square",
            "activates_at": "09:00",
            "activation_condition": "start time reached and all earlier tasks are terminal",
        },
    }
    rendered = agenda.prompt_text(facts)
    check("agenda prompt has three authority sections",
          all(heading in rendered for heading in ("## Today so far", "## Right now", "## Next")))
    check("ledger completion rendered", "completed" in rendered and "Eat breakfast" in rendered)
    check("active task policy and arrival rendered",
          "Task square" in rendered and "arrive_at_place" in rendered and "not_at_place" in rendered)
    check("grounded route rendered", "Route leg 1 of 3" in rendered and "[6, 5]" in rendered)
    check("next activation condition rendered", "all earlier tasks are terminal" in rendered)

    waiting = agenda.prompt_text({
        "today_so_far": [],
        "right_now": {"task_id": None, "status": "waiting"},
        "next": facts["next"],
    })
    check("between-task prompt forbids free-goal work", "do not begin free-goal work" in waiting)


def test_reaction_gate_template():
    """WP2 (#10.5 BALANCED gate) as revised by #64: the shared template keeps the
    *mechanic* — an interruption outranks the routine, the routine outranks a
    whim, you resume afterwards — and delegates the *policy* (is this person
    worth stopping for?) to the agent's own rules.md. A surveyor who must not
    stop and a shopkeeper whose whole job is stopping cannot share one line."""
    check("priorities block present", "## What Wins Right Now" in _USER_TEMPLATE_VISION)
    flat = _USER_TEMPLATE_VISION.replace("\n", " ")
    check("interruption still outranks the routine",
          "it outranks your routine" in flat)
    check("routine is still the default", "is your default" in flat)
    check("resume after a pause stated", "goes back to that destination" in flat)
    check("quirks are a nudge, not an override",
          "they do not cancel WHERE you are going" in flat)
    check("pausing policy is delegated to rules",
          "is a judgement your Rules" in flat and "written for you specifically" in flat)
    check("free time is delegated to the persona",
          "up to your Character, Goals and Rules" in flat)

    # The clauses did not evaporate — they moved to the one agent they were
    # written for. Deleting them instead would quietly hand Dufus a reason to
    # stop surveying, which is the regression this half guards.
    # Markdown wraps mid-sentence, so collapse all whitespace before matching.
    # Read the rules the AGENT actually gets, not the raw file: since #85 a
    # rules.md pulls shared doctrine in with `@import`, so the file on disk is no
    # longer the whole of what reaches the prompt.
    def _rules(agent_id):
        from agent_runtime.agent import resolve_rule_imports
        world = WORLDS / "MCP_World"
        text = (world / "agents" / agent_id / "rules.md").read_text(encoding="utf-8")
        return " ".join(resolve_rule_imports(text, world, agent_id).split())

    dufus_rules = _rules("dufus")
    check("dufus still must not stop for strangers",
          "Do NOT stop for strangers" in dufus_rules)
    check("dufus greet gate skips a recently-greeted person",
          "have NOT already greeted recently" in dufus_rules)
    check("dufus still answers someone speaking to him",
          "even if you already greeted them" in dufus_rules)
    check("dufus still explores when unscheduled",
          "keep exploring" in dufus_rules and "unexplored" in dufus_rules)
    check("dufus reads the wider map, not only his eight neighbours (#73)",
          "The Wider Map" in dufus_rules and "grows a blob, not a line" in dufus_rules)

    # And Maren carries the opposite policy, which is the whole point of the move.
    maren_rules = _rules("maren")
    check("maren treats stopping to talk as the work",
          "part of your work" in maren_rules)
    check("maren stays at her post when unscheduled", "stay at the truck" in maren_rules)
    check("maren does not inherit the surveyor's suppression",
          "Do NOT stop for strangers" not in maren_rules)


def test_answering_requires_speak_to():
    """SR41's one social exchange, half-completed (#74).

    Maren greeted Dufus. Dufus heard it, and decided: "Maren greeted me, so I'll
    answer her before continuing east" — then chose ``idle``, which is silent.
    His ``social.json`` interaction_count stayed 0. Every component worked:
    earshot delivered the line, the gate let him react, cognition chose to
    answer. Nothing anywhere said that answering *is* an action with a name, so
    the intent to speak never became speech.
    """
    quiet = _heard_note({})
    check("silence is stated so no conversation is imagined",
          "Nobody has spoken to you" in quiet)

    heard = _heard_note({"heard": [
        {"speaker": "Maren", "text": "Morning, Dufus.", "distance_cm": 1378.0},
    ]})
    check("the speaker and their words are quoted",
          "Maren" in heard and "Morning, Dufus." in heard)
    check("reacting this tick is still permitted", "you may answer this tick" in heard)
    check("the action that answers is named", "speak_to" in heard)
    check("the silent actions are named as silent",
          "idle" in heard and "observe" in heard)
    check("choosing to answer without speaking is called out",
          "leaves them standing in silence" in heard)

    # Two speakers must both be addressable, not collapsed into "someone".
    both = _heard_note({"heard": [{"speaker": "Maren", "text": "Morning."},
                                  {"speaker": "Cal", "text": "Hey."}]})
    check("every speaker is named in the answer prompt",
          "Maren, Cal" in both)

    check("speak_to's schema says it is the only action that makes sound",
          "ONLY action that produces speech" in _ACTION_SCHEMAS["speak_to"])
    check("speak_to's schema still shows the JSON shape",
          '"type": "speak_to"' in _ACTION_SCHEMAS["speak_to"]
          and '"message"' in _ACTION_SCHEMAS["speak_to"])


def test_schedule_note_weighting():
    travel = _schedule_note({
        "status": "travel", "place": "village square",
        "intent": "It's time to sell — head to village square.",
    })
    check("travel is stated as the priority", "This is your priority right now" in travel)
    check("travel names the walk_to target", 'target_location "village square"' in travel)
    check("travel defers the pause policy to the agent's rules (#64)",
          "worth a brief pause on the way is set by your rules" in travel)
    check("activity is deferred to the destination",
          "Do NOT start the scheduled activity on the way" in travel)

    act = _schedule_note({"status": "act", "place": "stall",
                          "intent": "You're at stall where you should be — sell."})
    check("act-at-place forbids walking to it (anti-orbit, 2026-07-05)",
          "position confirms" in act and "Do NOT walk_to" in act)
    act_placeless = _schedule_note({"status": "act", "place": "",
                                    "intent": "Time to sell."})
    check("placeless act keeps the generic line",
          "You are where you should be" in act_placeless)
    idle = _schedule_note(None)
    check("idle/None branch unchanged", "nothing fixed right now" in idle)


def test_active_interrupt_prompt_fact():
    note = _active_interrupt_note({
        "interrupt_id": "operator-1", "kind": "operator_chat", "source": "Avery",
        "reason": "Please talk with me at the gate.", "priority": 200,
    })
    check("active note renders explicit requester", "Avery" in note)
    check("active note renders grounded reason", "gate" in note)
    check("active note outranks routine", "outranks your routine" in note)
    check("template contains active interruption section", "## Active Interruption" in _USER_TEMPLATE_VISION)
    check("fallback prompt contains active interruption section", "## Active Interruption" in _USER_TEMPLATE)

    survey = _active_interrupt_note({
        "kind": "survey", "source": "world", "reason": "survey cell (5,5)",
        "priority": 100, "payload": {"col": 5, "row": 5, "survey_progress": {
            "phase": "surveying", "current_heading": None,
            "completed_headings": ["E", "S"], "failed_headings": [],
        }},
    })
    check("survey prompt renders only deterministic saved headings",
          "E, S" in survey and "2/4" in survey and "authoritative" in survey.lower())
    check("survey prompt forbids invented capture progress",
          "Do not claim" in survey and "uncaptured" in survey)
    check("no-active prompt also forbids invented survey completion",
          "No deterministic survey is active" in _active_interrupt_note(None))


def test_seen_text_footing():
    on_pavement = _seen_text({"caption": "A quiet street.", "footing": "pavement",
                              "landmarks": [], "characters": []})
    check("footing renders as an explicit fact line", "FOOTING: pavement" in on_pavement)

    in_field = _seen_text({"caption": "Rows of tall corn stalks.",
                           "footing": "cultivated_field", "landmarks": [], "characters": []})
    check("off-path footing renders too (LLM does the judging, not this renderer)",
          "FOOTING: cultivated_field" in in_field)

    no_footing = _seen_text({"caption": "A quiet street.", "landmarks": [], "characters": []})
    check("missing footing key renders nothing, no crash", "FOOTING" not in no_footing)


def main():
    test_acquaintance_lines()
    test_known_place_lines()
    test_episode_lines()
    test_nearby_character_lines()
    test_template_contract()
    test_agenda_prompt_context()
    test_reaction_gate_template()
    test_answering_requires_speak_to()
    test_schedule_note_weighting()
    test_active_interrupt_prompt_fact()
    test_seen_text_footing()
    print("\nAll prompt-context checks passed.")


if __name__ == "__main__":
    main()
