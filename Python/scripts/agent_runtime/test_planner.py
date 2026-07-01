"""Offline tests for the daily-schedule planner (Master Plan Milestone 1, slice 1).

Pure module: time selection is data-only and the LLM is injected, so these run
with no provider, no network, no Unreal. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_planner.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import planner   # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_to_minutes():
    check("08:30 -> 510", planner.to_minutes("08:30") == 510)
    check("00:00 -> 0", planner.to_minutes("00:00") == 0)
    check("24:00 -> 1440 (end of day)", planner.to_minutes("24:00") == 1440)
    for bad in ("8", "08:60", "25:00", "x:y", ""):
        raised = False
        try:
            planner.to_minutes(bad)
        except ValueError:
            raised = True
        check(f"bad time {bad!r} raises", raised)


def test_minute_of_day():
    check("Day 1, 08:23 -> 503", planner.minute_of_day("Day 1, 08:23") == 503)
    check("Day 12, 00:05 -> 5", planner.minute_of_day("Day 12, 00:05") == 5)
    check("no time -> 0 (start of day)", planner.minute_of_day("Day 1") == 0)


def test_normalize_drops_bad_and_sorts():
    raw = [
        {"start": "12:00", "end": "13:00", "activity": "lunch", "place": "diner"},
        {"start": "08:00", "end": "12:00", "activity": "work"},          # later in list, earlier start
        {"start": "14:00", "end": "13:00", "activity": "reversed"},      # start>=end -> drop
        {"start": "bad", "end": "10:00", "activity": "badtime"},          # bad time -> drop
        "not a dict",                                                      # -> drop
        {"end": "10:00", "activity": "no start"},                         # missing start -> drop
    ]
    out = planner.normalize_schedule(raw)
    check("only the 2 valid blocks survive", len(out) == 2)
    check("sorted by start (work first)", [b["activity"] for b in out] == ["work", "lunch"])
    check("missing place defaults to empty string", out[0]["place"] == "")


def test_normalize_blank_activity_gets_fallback():
    out = planner.normalize_schedule([{"start": "08:00", "end": "09:00", "activity": "   "}])
    check("blank activity -> FALLBACK_ACTIVITY", out[0]["activity"] == planner.FALLBACK_ACTIVITY)


def test_current_block_boundaries():
    sched = planner.normalize_schedule([
        {"start": "08:00", "end": "12:00", "activity": "work", "place": "stall"},
        {"start": "13:00", "end": "17:00", "activity": "wander", "place": "square"},
    ])
    check("start is inclusive", planner.current_block(sched, planner.to_minutes("08:00"))["activity"] == "work")
    check("mid-block selects it", planner.current_block(sched, planner.to_minutes("10:30"))["activity"] == "work")
    check("end is exclusive (12:00 not in work)", planner.current_block(sched, planner.to_minutes("12:00")) is None)
    check("gap between blocks -> None", planner.current_block(sched, planner.to_minutes("12:30")) is None)
    check("second block selected", planner.current_block(sched, planner.to_minutes("14:00"))["activity"] == "wander")
    check("before any block -> None", planner.current_block(sched, planner.to_minutes("06:00")) is None)


def test_current_block_overlap_earliest_wins():
    sched = planner.normalize_schedule([
        {"start": "08:00", "end": "12:00", "activity": "A"},
        {"start": "09:00", "end": "10:00", "activity": "B"},
    ])
    check("earliest-start block wins on overlap",
          planner.current_block(sched, planner.to_minutes("09:30"))["activity"] == "A")


def test_current_activity_from_clock_text():
    sched = planner.normalize_schedule([{"start": "08:00", "end": "12:00", "activity": "work"}])
    check("clock text resolves to active block",
          planner.current_activity(sched, "Day 1, 09:15")["activity"] == "work")
    check("clock text outside blocks -> None",
          planner.current_activity(sched, "Day 1, 20:00") is None)


def test_generate_uses_injected_llm():
    seen = {}

    def fake_ask(prompt):
        seen["prompt"] = prompt
        return ('```json\n[{"start":"08:00","end":"12:00","activity":"sell veg","place":"truck"},'
                '{"start":"12:00","end":"13:00","activity":"lunch","place":"diner"}]\n```')

    blocks = planner.generate_daily_plan("Maren, a grocer.", "Run the stall.", ask=fake_ask)
    check("parsed both blocks past the fences", len(blocks) == 2)
    check("activity parsed", blocks[0]["activity"] == "sell veg")
    check("place parsed", blocks[0]["place"] == "truck")
    check("persona reached the prompt", "Maren, a grocer." in seen["prompt"])
    check("goals reached the prompt", "Run the stall." in seen["prompt"])


def test_generate_fallback_without_llm():
    blocks = planner.generate_daily_plan("anyone", "Greet everyone in the village square.", ask=None)
    check("fallback is a single all-day block", len(blocks) == 1)
    check("covers the whole day", blocks[0]["start"] == "00:00" and blocks[0]["end"] == "24:00")
    check("activity seeded from goals first line",
          blocks[0]["activity"] == "Greet everyone in the village square.")


def test_generate_fallback_on_bad_llm():
    blocks = planner.generate_daily_plan("c", "g", ask=lambda p: "not json at all")
    check("unparseable model output -> fallback", len(blocks) == 1 and blocks[0]["end"] == "24:00")
    # An empty-but-valid JSON array must also fall back, not yield an empty plan.
    blocks2 = planner.generate_daily_plan("c", "g", ask=lambda p: "[]")
    check("empty schedule -> fallback", len(blocks2) == 1)


def _maren_day():
    return planner.normalize_schedule([
        {"start": "08:00", "end": "12:00", "activity": "sell veg", "place": "vegetable truck"},
        {"start": "12:00", "end": "13:00", "activity": "have lunch", "place": "diner"},
    ])


def test_sequencer_wake_then_travel_to_post():
    # "I wake up, what time is it, oh I should be at the vegetable stand" — and I'm
    # not there yet (unknown place on wake) -> travel; first step is no transition.
    d = planner.step(_maren_day(), planner.to_minutes("08:00"),
                     current_place=None, prev_activity=None)
    check("wake selects the morning block", d["activity"] == "sell veg")
    check("status is travel (not there yet)", d["status"] == "travel")
    check("travel target is the post", d["place"] == "vegetable truck")
    check("wake is not a transition", d["transition"] is False)
    check("intent names the place", "vegetable truck" in d["intent"])
    # Destination-first: leading with the activity ("It's time to greet...")
    # makes the LLM start it en route (live finding, 2026-07-01).
    check("intent leads with the destination", d["intent"].startswith("Head to"))
    check("intent defers the activity to arrival", "starts when you arrive" in d["intent"])


def test_sequencer_already_there_acts():
    # "oh wait, I am already there, what should I do next" -> act (LLM picks the
    # sub-action). Coarse schedule name matches a richer perceived label.
    d = planner.step(_maren_day(), planner.to_minutes("09:30"),
                     current_place="vegetable truck stand on main street",
                     prev_activity="sell veg")
    check("already at post -> act", d["status"] == "act")
    check("still the morning activity", d["activity"] == "sell veg")
    check("no transition mid-block", d["transition"] is False)


def test_sequencer_noon_transition_to_lunch():
    # "12:00 hits, time to go to lunch" -> block flips; transition fires; travel.
    d = planner.step(_maren_day(), planner.to_minutes("12:00"),
                     current_place="vegetable truck", prev_activity="sell veg")
    check("noon selects the lunch block", d["activity"] == "have lunch")
    check("block boundary is a transition", d["transition"] is True)
    check("must travel to the diner", d["status"] == "travel" and d["place"] == "diner")


def test_sequencer_idle_when_nothing_scheduled():
    d = planner.step(_maren_day(), planner.to_minutes("23:00"),
                     current_place="diner", prev_activity="have lunch")
    check("after the day -> idle", d["status"] == "idle")
    check("idle has no block", d["block"] is None)
    check("leaving the last block is a transition", d["transition"] is True)


def test_same_place_matching():
    check("exact match", planner._same_place("diner", "diner"))
    check("containment either way", planner._same_place("the old diner on 5th", "diner"))
    check("unknown current place is never a match", not planner._same_place(None, "diner"))
    check("different places don't match", not planner._same_place("home", "diner"))


class _FakeAgent:
    """Duck-typed stand-in for Agent (planner only needs these members)."""

    def __init__(self, character_text="Maren, a grocer.", goals_text="Run the stall."):
        self.character_text = character_text
        self.goals_text = goals_text
        self._sched = {}
        self.saves = 0

    @property
    def daily_schedule_day(self):
        return self._sched.get("day", "")

    @property
    def daily_schedule_blocks(self):
        return self._sched.get("blocks", [])

    def set_daily_schedule(self, blocks, day, agents_dir):
        self._sched = {"day": day, "blocks": blocks}
        self.saves += 1


def _counting_ask(reply):
    calls = {"n": 0}

    def ask(prompt):
        calls["n"] += 1
        return reply

    return ask, calls


def test_day_of():
    check("Day 1, 08:23 -> Day 1", planner.day_of("Day 1, 08:23") == "Day 1")
    check("Day 12, 00:00 -> Day 12", planner.day_of("Day 12, 00:00") == "Day 12")


def test_ensure_generates_and_persists_then_idempotent():
    agent = _FakeAgent()
    ask, calls = _counting_ask('[{"start":"08:00","end":"12:00","activity":"sell","place":"truck"}]')
    blocks = planner.ensure_daily_plan(agent, "Day 1", ask=ask)
    check("generated the schedule", blocks[0]["activity"] == "sell")
    check("persisted for the day", agent.daily_schedule_day == "Day 1")
    check("LLM asked once", calls["n"] == 1 and agent.saves == 1)
    # Second call same day: served from scratch, no new generation.
    planner.ensure_daily_plan(agent, "Day 1", ask=ask)
    check("idempotent within the day (no second ask)", calls["n"] == 1)
    check("no second save", agent.saves == 1)


def test_ensure_regenerates_on_new_day():
    agent = _FakeAgent()
    ask1, _ = _counting_ask('[{"start":"08:00","end":"12:00","activity":"sell"}]')
    planner.ensure_daily_plan(agent, "Day 1", ask=ask1)
    ask2, calls2 = _counting_ask('[{"start":"09:00","end":"10:00","activity":"market run"}]')
    blocks = planner.ensure_daily_plan(agent, "Day 2", ask=ask2)
    check("new day regenerates", agent.daily_schedule_day == "Day 2")
    check("new schedule reflects the new day", blocks[0]["activity"] == "market run")
    check("LLM asked for the new day", calls2["n"] == 1 and agent.saves == 2)


def main():
    test_to_minutes()
    test_minute_of_day()
    test_normalize_drops_bad_and_sorts()
    test_normalize_blank_activity_gets_fallback()
    test_current_block_boundaries()
    test_current_block_overlap_earliest_wins()
    test_current_activity_from_clock_text()
    test_generate_uses_injected_llm()
    test_generate_fallback_without_llm()
    test_generate_fallback_on_bad_llm()
    test_sequencer_wake_then_travel_to_post()
    test_sequencer_already_there_acts()
    test_sequencer_noon_transition_to_lunch()
    test_sequencer_idle_when_nothing_scheduled()
    test_same_place_matching()
    test_day_of()
    test_ensure_generates_and_persists_then_idempotent()
    test_ensure_regenerates_on_new_day()
    print("\nAll planner checks passed.")


if __name__ == "__main__":
    main()
