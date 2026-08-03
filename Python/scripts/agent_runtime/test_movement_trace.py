"""Offline tests for auditable movement in the decision log (backlog #55).

SR33 recorded two consecutive walks, both thinking "turn back the way I came",
both `walk_to success` — with no position, target or heading. One walked 15 m
deeper into a corn field, the other walked back out, and the log could not tell
them apart. These tests pin the fields that make that distinguishable.

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_movement_trace.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.memory_store import MemoryStore, movement_trace   # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _obs(x, y, **extra):
    obs = {"location": {"x": x, "y": y, "z": 90.0},
           "grid": {"key": "5,6", "col": 5, "row": 6}}
    obs.update(extra)
    return obs


# ── Where the APC stood ───────────────────────────────────────────────────────

def test_standing_facts():
    trace = movement_trace(
        _obs(-10491.7, 718.6, seen={"footing": "cultivated_field"},
             rotation={"x": 0.0, "y": 180.0, "z": 0.0}),
        {"type": "idle"},
    )
    check("logs the position it decided from", trace["at"] == [-10491.7, 718.6])
    check("logs the cell", trace["cell"] == "5,6")
    check("logs the footing it is standing on", trace["footing"] == "cultivated_field")
    check("logs the facing the direction words are relative to",
          trace["facing_yaw"] == 180.0)
    check("a non-movement action has no move block", "move" not in trace)


def test_missing_facts_are_omitted_not_invented():
    trace = movement_trace({}, {"type": "walk_to", "direction": "back"})
    check("no location -> no position", "at" not in trace)
    check("no grid -> no cell", "cell" not in trace)
    check("no vision -> no footing", "footing" not in trace)
    check("no previous position -> no distance", "moved_cm" not in trace)
    check("intent still survives", trace["move"]["intent"] == "direction:back")


# ── Where the action aimed ────────────────────────────────────────────────────

def test_the_two_sr33_walks_are_distinguishable():
    """The exact SR33 pair: same thought, same status, opposite directions."""
    # UE yaw: +y is south. Walking to y+1500 goes south, deeper into the field.
    deeper = movement_trace(
        _obs(-10491.7, 718.6),
        {"type": "walk_to", "direction": "back", "location": [-10491.7, 2218.6, 89.9]},
    )
    back_out = movement_trace(
        _obs(-10491.7, 2184.5),
        {"type": "walk_to", "direction": "back", "location": [-10491.7, 684.5, 89.9]},
        previous_xy=(-10491.7, 718.6),
    )
    check("outbound walk logs its heading", deeper["move"]["heading"] == "S")
    check("return walk logs the opposite heading", back_out["move"]["heading"] == "N")
    check("both carry the same intent, which is the point",
          deeper["move"]["intent"] == back_out["move"]["intent"] == "direction:back")
    check("step distance is recorded", deeper["move"]["distance_cm"] == 1500.0)
    check("the previous walk's real displacement is recorded",
          back_out["moved_cm"] == 1465.9)


def test_intent_names_the_form_of_the_request():
    def intent(action):
        return movement_trace(_obs(0.0, 0.0), action).get("move", {}).get("intent")

    check("facing-relative direction", intent({"type": "walk_to", "direction": "forward-left"})
          == "direction:forward-left")
    check("named place", intent({"type": "walk_to", "target_location": "village square"})
          == "place:village square")
    check("character", intent({"type": "walk_to", "target_actor": "Maren"}) == "actor:Maren")
    check("grid cell", intent({"type": "walk_to", "target_cell": "4,6"}) == "cell:4,6")
    check("raw coordinates", intent({"type": "walk_to", "location": [100.0, 0.0, 0.0]})
          == "location")
    check("survey leg", intent({"type": "walk_to", "location": [100.0, 0.0, 0.0],
                                "_sweep": "goto_center"}) == "survey:goto_center")


def test_no_heading_without_displacement():
    trace = movement_trace(_obs(100.0, 100.0),
                           {"type": "walk_to", "location": [100.0, 100.0, 0.0]})
    check("a zero-length move claims no heading", "heading" not in trace["move"])
    check("but its distance is still honest", trace["move"]["distance_cm"] == 0.0)


# ── End to end through the log ────────────────────────────────────────────────

def test_record_writes_movement_and_tracks_displacement():
    with tempfile.TemporaryDirectory() as tmp:
        agents = Path(tmp) / "agents"
        (agents / "dufus").mkdir(parents=True)
        store = MemoryStore(Path(tmp))
        store.update_agents_dir(agents)
        store.sim_run_id = "SR34"

        store.record("dufus", _obs(0.0, 0.0, _thought="pushing west"),
                     {"type": "walk_to", "location": [0.0, 1500.0, 0.0]},
                     {"status": "success"})
        store.record("dufus", _obs(0.0, 1480.0, _thought="turning back"),
                     {"type": "walk_to", "location": [0.0, -20.0, 0.0]},
                     {"status": "success"})

        rows = [json.loads(line) for line in
                store.decisions_log.read_text(encoding="utf-8").splitlines()]
        check("first row has no displacement to report", "moved_cm" not in rows[0])
        check("second row reports how far the first walk actually got",
              rows[1]["moved_cm"] == 1480.0)
        check("headings are opposite",
              (rows[0]["move"]["heading"], rows[1]["move"]["heading"]) == ("S", "N"))
        check("the thought is still there", rows[1]["thought"] == "turning back")

        # Displacement is per agent, never blended across APCs.
        store.record("maren", _obs(9000.0, 9000.0, _thought="tending"),
                     {"type": "idle"}, {"status": "accepted"})
        rows = [json.loads(line) for line in
                store.decisions_log.read_text(encoding="utf-8").splitlines()]
        check("a different APC does not inherit dufus's position",
              "moved_cm" not in rows[2])


if __name__ == "__main__":
    test_standing_facts()
    test_missing_facts_are_omitted_not_invented()
    test_the_two_sr33_walks_are_distinguishable()
    test_intent_names_the_form_of_the_request()
    test_no_heading_without_displacement()
    test_record_writes_movement_and_tracks_displacement()
    print("\nAll movement-trace checks passed.")
