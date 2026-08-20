"""#84 — the prompt payload contract, and #82's engine-identity boundary.

The defect this guards is structural, not cosmetic. The no-vision path used to
be `{k: v for k, v in observation.items() if k != "image_path"}` — a deny-list of
exactly ONE key — so every engine field the runtime had ever attached went to the
model verbatim, and every new key leaked by default.

Per rule 9 these must be able to fail: the seeded observation below carries
engine junk in fields that a future renderer might innocently pass through.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime import prompt_payload                                # noqa: E402
from agent_runtime import llm_router                                    # noqa: E402

_failures = []


def check(label, ok):
    print(f"{'ok' if ok else 'FAIL'}: {label}")
    if not ok:
        _failures.append(label)


def _dirty_observation() -> dict:
    """An observation seeded with engine identity in every plausible place."""
    return {
        # allowed, and clean
        "location": {"x": 1.0, "y": 2.0, "z": 90.0},
        "current_action": "moving",
        "footing": "pavement",
        "grid": {"key": "7,7"},
        "known_characters": ["Maren"],
        # allowed, but carrying engine identity in a nested key
        "blocker": {
            "category": "vehicle", "distance_cm": 36.0, "urgent": True,
            "actor_name": "veh_Van_6",
            "actor_class": "SkeletalMeshActor",
            "signals": {"component_class": "SkeletalMeshComponent"},
        },
        # never allowed
        "image_path": "C:/worlds/MCP_World/agents/dufus/observations/x.png",
        "place_image_id": 4471,
        "bound_unreal_actor_name": "APC_Dufus_BP_C_1",
        "bound_unreal_actor_class": "APC_BP_C",
        # a brand-new runtime key nobody has audited — the real regression case
        "some_new_debug_field": "BP_Whatever_C_3",
    }


def test_projection_is_an_allow_list():
    payload = prompt_payload.project(_dirty_observation())
    flat = repr(payload)
    check("an allowed field is present", "pavement" in flat)
    check("the never-send image path is gone", "observations/x.png" not in flat)
    check("the database row id is gone", "4471" not in flat)
    check("the bound actor name is gone", "APC_Dufus_BP_C_1" not in flat)
    check("the bound actor class is gone", "APC_BP_C" not in flat)
    check("A NEW UNAUDITED KEY IS NOT SENT (the whole point)",
          "some_new_debug_field" not in flat and "BP_Whatever_C_3" not in flat)


def test_nested_engine_identity_is_stripped():
    payload = prompt_payload.project(_dirty_observation())
    blocker = payload["senses"]["blocker"]
    check("the blocker fact still reaches the model",
          blocker["category"] == "vehicle" and blocker["distance_cm"] == 36.0)
    check("blocker.actor_name is stripped at the boundary",
          "actor_name" not in blocker)
    check("blocker.actor_class is stripped", "actor_class" not in blocker)
    check("the raw engine signals are stripped", "signals" not in blocker)


def test_dropped_fields_are_knowable():
    dropped = prompt_payload.dropped_fields(_dirty_observation())
    check("the contract can say what it withheld",
          "bound_unreal_actor_name" in dropped and "some_new_debug_field" in dropped)


def test_absent_fields_are_omitted_not_nulled():
    payload = prompt_payload.project({"footing": "road", "grid": None})
    check("a None field is omitted, not sent as null",
          "place" not in payload)
    check("an empty section is not emitted", list(payload) == ["self"])


def test_check_clean_detects_each_leak_shape():
    for text, label in [
        ("the actor BP_Maren_2 is here", "blueprint label"),
        ("APC_Dufus_BP_C_1 stands there", "blueprint class instance"),
        ("a StaticMeshActor blocks you", "engine actor class"),
        ("You are in an Unreal Engine world", "the engine name"),
        ("traced on ECC_Pawn", "collision channel"),
    ]:
        check(f"leak detected: {label}",
              bool(prompt_payload.check_clean(text, "test", "unit")))

    clean = ("Sense: your forward probe struck a vehicle 0.4 m directly ahead. "
             "Your body DOES NOT FIT. The gap is on your: left. Maren is nearby.")
    check("clean prompt text raises no alarm",
          prompt_payload.check_clean(clean, "test", "unit") == [])


def test_the_real_prompt_templates_are_clean():
    # The templates themselves must not name the engine — this is #82's
    # channels 2 and 3, checked against the shipped strings rather than a mock.
    for name in ("_SYSTEM_TEMPLATE", "_USER_TEMPLATE", "_USER_TEMPLATE_VISION"):
        template = getattr(llm_router, name, "")
        # Assert the template EXISTS first: `"Unreal" not in ""` passes for a
        # renamed attribute, which would be a check that cannot fail (rule 9).
        check(f"{name} still exists to be checked", len(template) > 100)
        check(f"{name} does not name the engine",
              "Unreal" not in template)

    schemas = " ".join(llm_router._ACTION_SCHEMAS.values())
    check("no action asks the model for an engine actor label",
          "actor_label" not in schemas)
    check("no action asks the model for an engine actor name",
          "<actor_name>" not in schemas)
    check("targeted actions ask for a character name instead",
          "<character name>" in schemas)


def test_rendered_payload_survives_the_boundary_check():
    import json
    payload = prompt_payload.project(_dirty_observation())
    rendered = json.dumps(payload, indent=2)
    leaks = prompt_payload.check_clean(rendered, "test", "projection")
    check("the projected payload contains no engine identity at all", leaks == [])


def test_the_lizard_brain_keeps_engine_signals_to_itself():
    """#83's signals must never leave the classifier.

    The identity block from the engine (physical material, component class,
    collision profile, tags) is raw engine vocabulary. It is an INPUT to the
    lizard brain's classification and must not appear in the observation the
    prompt is built from — only the generic category it produces.
    """
    from agent_runtime.agent_manager import _classify_blocker

    signals = {"physical_material": "PM_CarBody",
               "component_class": "SkeletalMeshComponent",
               "collision_profile": "Vehicle",
               "tags": ["Vehicle"], "is_pawn": False, "is_movable": False}
    category = _classify_blocker("veh_Van_6", "SkeletalMeshActor", signals)
    check("the classifier returns a generic word, not an engine one",
          category == "vehicle")
    check("the category is in the shared vocabulary",
          category in {"vehicle", "person", "figure", "animal",
                       "structure", "prop", "foliage", "obstacle"})

    # The blocker fact the runtime builds carries only the category outward.
    blocker = {"category": category, "distance_cm": 36.0,
               "actor_name": "veh_Van_6", "urgent": True}
    rendered = llm_router._sense_note({"blocker": blocker})
    check("the rendered sense names the category",
          "vehicle" in rendered)
    check("the rendered sense does NOT name the engine actor",
          "veh_Van_6" not in rendered)
    check("no engine identity survives the renderer",
          prompt_payload.check_clean(rendered, "test", "sense") == [])


def test_every_prompt_path_is_guarded():
    """#84's alarm is worthless if a path skips it.

    `decide()` has two branches (vision / no-vision); `orient()` (wake),
    `chat()` and `ask()` (the planner) each build and dispatch their own prompt.
    All of them must run the check. Three were missed on the first pass, which
    is why this test enumerates the methods rather than trusting one call site.
    """
    import inspect
    from agent_runtime.llm_router import LLMRouter

    # Every public method that sends text to a model. `orient` is the wake
    # prompt and `ask` is the planner's — both were missed on the first pass,
    # which is exactly why this enumerates them instead of trusting one call site.
    for method, label in [("decide", "decision"), ("orient", "wake"),
                          ("chat", "chat"), ("ask", "planner")]:
        src = inspect.getsource(getattr(LLMRouter, method))
        check(f"the {label} path runs the boundary check",
              "check_clean" in src)

    decide_src = inspect.getsource(LLMRouter.decide)
    check("the decision check sits after BOTH render branches, so it covers both",
          decide_src.index("_USER_TEMPLATE_VISION") < decide_src.index("check_clean")
          and decide_src.index("_USER_TEMPLATE.format") < decide_src.index("check_clean"))


def main():
    test_projection_is_an_allow_list()
    test_nested_engine_identity_is_stripped()
    test_dropped_fields_are_knowable()
    test_absent_fields_are_omitted_not_nulled()
    test_check_clean_detects_each_leak_shape()
    test_the_real_prompt_templates_are_clean()
    test_rendered_payload_survives_the_boundary_check()
    test_the_lizard_brain_keeps_engine_signals_to_itself()
    test_every_prompt_path_is_guarded()
    if _failures:
        print(f"\n{len(_failures)} prompt-payload check(s) FAILED")
        sys.exit(1)
    print("\nAll prompt-payload checks passed.")


if __name__ == "__main__":
    main()
