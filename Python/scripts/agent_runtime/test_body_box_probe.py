"""#81 body-box probe + #83 identity from engine signals.

SR46 is the case these guard. Dufus spent 4.5 minutes bouncing between a van and
a baseball field: the probe told him "vehicle 36 cm ahead" and nothing about
which side was open, and a 9 m refusal cannot be obeyed with a 15 m step. The
fix is a measurement — does the BODY fit, and where is the gap — so these checks
are about the fact reaching the prompt, not about the trace firing.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime import llm_router                                   # noqa: E402
from agent_runtime.agent_manager import _classify_blocker              # noqa: E402

_failures = []


def check(label, ok):
    print(f"{'ok' if ok else 'FAIL'}: {label}")
    if not ok:
        _failures.append(label)


# --------------------------------------------------------------------------
# #83 — identity from engine signals, names only as a last resort
# --------------------------------------------------------------------------

def test_signal_precedence():
    # A tag is the author SAYING what a thing is; an asset name is a file name
    # they typed. When they disagree, the deliberate statement wins.
    check("an explicit tag outranks a misleading name",
          _classify_blocker("shopFront_01", "StaticMeshActor",
                            {"tags": ["Vehicle"]}) == "vehicle")
    check("the engine knowing it is a pawn outranks its name",
          _classify_blocker("prop_thing_3", "Weird",
                            {"is_pawn": True}) == "person")
    check("physical material classifies an unnamed mesh",
          _classify_blocker("mesh_8842", "StaticMeshActor",
                            {"physical_material": "PM_Foliage_Corn"}) == "foliage")
    check("a vehicle collision profile is enough",
          _classify_blocker("xyz", "Foo",
                            {"collision_profile": "Vehicle"}) == "vehicle")


def test_crowd_mannequin_is_never_a_person():
    # The visible failure to test for: an APC walking up to greet scenery.
    immovable_skeletal = {"component_class": "SkeletalMeshComponent",
                          "is_movable": False}
    check("an immovable skeletal mesh reads as a figure, not a person",
          _classify_blocker("unnamed_42", "SkeletalMeshActor",
                            immovable_skeletal) == "figure")
    check("the SR46 crowd props are figures by name too",
          _classify_blocker("pose_standing_24", "SkeletalMeshActor") == "figure")
    check("a real APC is still a person",
          _classify_blocker("APC_Maren_BP_C_1", "APC_BP_C",
                            {"is_pawn": True}) == "person")


def test_unclassified_still_reported_never_dropped():
    # SR46's one unknown. It must come back as a generic obstacle — the whole
    # #61 bug was a hit being classified and then thrown away.
    check("an unknown actor is still an obstacle, not nothing",
          _classify_blocker("receptionCounter_7", "StaticMeshActor") == "obstacle")


def test_signals_absent_degrades_to_names():
    # The old single ray supplies no signals; it must keep working.
    check("no signals still classifies by name",
          _classify_blocker("veh_VegetableTruck2", "SkeletalMeshActor") == "vehicle")
    check("no signals, unknown name, still an obstacle",
          _classify_blocker("zzz_1", "Foo", None) == "obstacle")


# --------------------------------------------------------------------------
# #81 — the fit/gap facts reach the prompt as measurements
# --------------------------------------------------------------------------

def test_does_not_fit_names_the_open_side():
    note = llm_router._sense_note({"blocker": {
        "category": "vehicle", "distance_cm": 36.0, "fits": False,
        "open_columns": ["far_left", "left"], "clearance_cm": 36.0,
    }})
    check("the body-does-not-fit fact renders", "DOES NOT FIT" in note)
    check("the open side is named", "far left, left" in note)
    check("the clearance is stated in metres", "0.4 m" in note)
    check("it is framed as measured, not advised",
          "should" not in note and "go around" not in note)


def test_fully_blocked_says_so():
    note = llm_router._sense_note({"blocker": {
        "category": "structure", "distance_cm": 120.0, "fits": False,
        "open_columns": [], "fully_blocked": True,
    }})
    check("completely blocked renders", "NO side is open" in note)
    check("it says the measurement is real", "measured, not guessed" in note)


def test_fits_true_is_also_a_fact():
    note = llm_router._sense_note({"blocker": {
        "category": "prop", "distance_cm": 250.0, "fits": True,
        "open_columns": ["centre", "right"],
    }})
    check("fitting past something is stated", "DOES fit" in note)
    check("no false alarm when it fits", "DOES NOT FIT" not in note)


def test_unmeasured_is_not_blocked():
    # The ray fallback sets fits=None. None must never read as False, or the APC
    # is told it cannot fit through gaps nobody measured.
    note = llm_router._sense_note({"blocker": {
        "category": "vehicle", "distance_cm": 250.0,
    }})
    check("an unmeasured probe claims nothing about fitting",
          "DOES NOT FIT" not in note and "DOES fit" not in note)
    check("the plain blocker fact still renders", "vehicle 2.5 m" in note)


# --------------------------------------------------------------------------
# The probe itself: prefers the body-box, falls back loudly, never lies
# --------------------------------------------------------------------------

class _Bridge:
    """Bridge stub. ``volume`` None means the engine has no #81 handler yet."""

    def __init__(self, volume=None, trace=None):
        self._volume = volume
        self._trace = trace or {"hit": False}
        self.volume_calls = 0
        self.trace_calls = 0

    def forward_volume(self, actor_name, distance_cm=500.0, yaw_offset_deg=0.0):
        self.volume_calls += 1
        return self._volume or {"success": False, "error": "Unknown command"}

    def line_trace_forward(self, actor_name, distance_cm=300.0):
        self.trace_calls += 1
        return self._trace


class _Agent:
    bound_unreal_actor_name = "APC_Test_BP_C_1"


def _manager(bridge):
    from agent_runtime.agent_manager import AgentManager
    mgr = AgentManager.__new__(AgentManager)
    mgr.bridge = bridge
    mgr._volume_probe_unavailable = False
    return mgr


def test_volume_probe_is_preferred():
    bridge = _Bridge(volume={
        "success": True, "hit": True, "fits": False, "clearance_cm": 36.0,
        "open_columns": ["left"], "blocked_columns": ["centre", "right"],
        "fully_blocked": False, "nearest_cm": 36.0,
        "contact": {"actor_name": "veh_Van_6", "actor_class": "SkeletalMeshActor",
                    "distance_cm": 36.0, "physical_material": "PM_CarBody"},
    })
    out = _manager(bridge)._probe_ahead(_Agent(), 500.0)
    check("the body-box probe is used when available", bridge.volume_calls == 1)
    check("the ray is not also fired", bridge.trace_calls == 0)
    check("fits comes through", out["fits"] is False)
    check("the open side comes through", out["open_columns"] == ["left"])
    check("the contact distance comes through", out["distance_cm"] == 36.0)
    check("engine signals are carried for classification",
          (out["signals"] or {}).get("physical_material") == "PM_CarBody")


def test_falls_back_to_the_ray_and_never_claims_a_measurement():
    bridge = _Bridge(volume=None, trace={
        "hit": True, "actor_name": "veh_Van_6",
        "actor_class": "SkeletalMeshActor", "distance_cm": 210.0,
    })
    mgr = _manager(bridge)
    out = mgr._probe_ahead(_Agent(), 300.0)
    check("the ray answers when the engine has no volume handler",
          bridge.trace_calls == 1 and out["hit"] is True)
    check("fits is None, NOT False, when nothing was measured",
          out["fits"] is None)
    check("the fallback is latched so it warns once, not every tick",
          mgr._volume_probe_unavailable is True)

    mgr._probe_ahead(_Agent(), 300.0)
    check("the volume probe is not retried after it failed",
          bridge.volume_calls == 1)


def test_clean_volume_probe_reports_no_hit():
    bridge = _Bridge(volume={
        "success": True, "hit": False, "fits": True, "clearance_cm": 500.0,
        "open_columns": ["far_left", "left", "centre", "right", "far_right"],
        "fully_blocked": False, "nearest_cm": 500.0,
    })
    out = _manager(bridge)._probe_ahead(_Agent(), 500.0)
    check("open ground reports no hit", out["hit"] is False)
    check("open ground reports fitting", out["fits"] is True)
    check("every column open", len(out["open_columns"]) == 5)


def main():
    test_signal_precedence()
    test_crowd_mannequin_is_never_a_person()
    test_unclassified_still_reported_never_dropped()
    test_signals_absent_degrades_to_names()
    test_does_not_fit_names_the_open_side()
    test_fully_blocked_says_so()
    test_fits_true_is_also_a_fact()
    test_unmeasured_is_not_blocked()
    test_volume_probe_is_preferred()
    test_falls_back_to_the_ray_and_never_claims_a_measurement()
    test_clean_volume_probe_reports_no_hit()
    if _failures:
        print(f"\n{len(_failures)} body-box check(s) FAILED")
        sys.exit(1)
    print("\nAll body-box probe checks passed.")


if __name__ == "__main__":
    main()
