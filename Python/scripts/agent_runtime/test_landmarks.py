"""Offline tests for Landmark_* level-actor parsing (#23).

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_landmarks.py

Authored ground truth moves into the level: an actor label
``Landmark_<owner>_<name with underscores>`` becomes a place, read straight
from ``get_actors_in_level`` (no plugin rebuild). Covers:
  - landmark_from_actor: valid owned/community labels, multi-underscore
    names, non-landmark labels (None, no log), malformed labels (fail loud,
    skipped).
  - merge_entries: a landmark shadows a places.json entry with the same
    owner+name (case-insensitive); the landmark wins.
  - End-to-end: stub actor list -> landmarks_from_actors -> apply_manifest
    into a temp PlaceDB -> right cell, dx/dy, owner.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import places_manifest                     # noqa: E402
from agent_runtime.landmarks import (                          # noqa: E402
    _levenshtein, landmark_from_actor, landmarks_from_actors,
    merge_entries, scan_landmarks,
)
from agent_runtime.place_db import PLACE_EXTENT_CM, PlaceDB    # noqa: E402
from agent_runtime.world_grid import WorldGrid                 # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _actor(label, name="BP_Actor_1", location=(320.0, 120.0, 90.0)):
    return {"name": name, "label": label, "class": "StaticMeshActor",
            "location": list(location)}


# ── landmark_from_actor ─────────────────────────────────────────────────────────

def test_valid_owned_label():
    entry = landmark_from_actor(_actor("Landmark_dufus_home"))
    check("owned entry parsed", entry is not None)
    check("name from remainder", entry["name"] == "home")
    check("owner from token", entry["owner"] == "dufus")
    check("community False for an owned landmark", entry["community"] is False)
    check("x/y from location[0..1]", entry["x"] == 320.0 and entry["y"] == 120.0)
    check("extent_cm == PLACE_EXTENT_CM", entry["extent_cm"] == PLACE_EXTENT_CM)
    check("actor == actor['name']", entry["actor"] == "BP_Actor_1")


def test_valid_community_label():
    entry = landmark_from_actor(_actor("Landmark_community_town_square"))
    check("community entry parsed", entry is not None)
    check("owner None for community", entry["owner"] is None)
    check("community True", entry["community"] is True)
    check("underscores -> spaces", entry["name"] == "town square")


def test_multi_underscore_name():
    entry = landmark_from_actor(_actor("Landmark_maren_vegetable_truck"))
    check("multi-underscore name parsed", entry is not None)
    check("owner is just the first token", entry["owner"] == "maren")
    check("name is the remainder, underscores -> spaces",
          entry["name"] == "vegetable truck")


def test_non_landmark_label_returns_none_silently():
    entry = landmark_from_actor(_actor("BP_VegetableTruck_3"))
    check("non-Landmark label -> None", entry is None)


def test_malformed_labels_skipped():
    for label in ("Landmark_", "Landmark_maren_", "Landmark__x"):
        entry = landmark_from_actor(_actor(label))
        check(f"malformed label {label!r} -> None (skipped)", entry is None)


def test_landmarks_from_actors_mixes_valid_and_invalid():
    actors = [
        _actor("Landmark_maren_vegetable_truck", name="A"),
        _actor("BP_Prop_1", name="B"),               # not a landmark
        _actor("Landmark_", name="C"),                # malformed
        _actor("Landmark_dufus_home", name="D"),
    ]
    entries = landmarks_from_actors(actors)
    check("only the two valid landmarks survive", len(entries) == 2)
    check("order preserved", [e["actor"] for e in entries] == ["A", "D"])


def test_case_insensitive_prefix():
    entry = landmark_from_actor(_actor("landmark_maren_home"))
    check("lowercase prefix parses", entry is not None)
    check("owner still maren", entry["owner"] == "maren")
    check("name still home", entry["name"] == "home")


def test_owner_token_casefold():
    entry = landmark_from_actor(_actor("Landmark_Maren_home"))
    check("mixed-case owner token parses", entry is not None)
    check("owner casefolded to maren", entry["owner"] == "maren")


def test_community_token_casefold():
    entry = landmark_from_actor(_actor("Landmark_Community_town_square"))
    check("mixed-case community token parses", entry is not None)
    check("owner None for community", entry["owner"] is None)
    check("community True", entry["community"] is True)
    check("name from remainder", entry["name"] == "town square")


# ── merge_entries ────────────────────────────────────────────────────────────────

def test_merge_precedence_landmark_wins():
    landmarks = [{"name": "vegetable truck", "x": 1.0, "y": 2.0, "owner": "maren",
                  "community": False, "extent_cm": PLACE_EXTENT_CM, "actor": "BP_Truck"}]
    manifest_entries = [
        # Same owner, same name up to case -> shadowed by the landmark. (The
        # dedupe key is (owner, name.casefold()) — owner matches exactly,
        # name matching is case-insensitive.)
        {"name": "Vegetable Truck", "x": 999.0, "y": 999.0, "owner": "maren",
         "community": False, "extent_cm": 900.0, "actor": None},
        # Different name -> survives.
        {"name": "village square", "x": 5.0, "y": 5.0, "owner": None,
         "community": True, "extent_cm": 900.0, "actor": None},
    ]
    merged = merge_entries(landmarks, manifest_entries)
    check("landmark + surviving places.json entry only", len(merged) == 2)
    check("landmark listed first (first-wins cell rule)",
          merged[0]["actor"] == "BP_Truck")
    check("landmark's own x/y survive, not the shadowed places.json x/y",
          merged[0]["x"] == 1.0 and merged[0]["y"] == 2.0)
    check("unrelated places.json entry passes through",
          any(e["name"] == "village square" for e in merged))


def test_merge_no_collision_keeps_both():
    landmarks = [{"name": "home", "x": 1.0, "y": 1.0, "owner": "dufus",
                  "community": False, "extent_cm": PLACE_EXTENT_CM, "actor": "BP_House"}]
    manifest_entries = [{"name": "the vegetable truck", "x": 2.0, "y": 2.0, "owner": "maren",
                         "community": False, "extent_cm": 900.0, "actor": None}]
    merged = merge_entries(landmarks, manifest_entries)
    check("no collision -> both entries kept", len(merged) == 2)


# ── end-to-end: stub actors -> landmarks -> apply_manifest -> PlaceDB ────────────

# cell (5,5) covers x,y in [0,400): center (200,200) — same grid convention as
# test_places_manifest.py.
GRID = WorldGrid(cell_size=400.0,
                 bounds={"min_x": -2000, "min_y": -2000, "max_x": 1999, "max_y": 1999})


def test_end_to_end_actor_to_placedb():
    with tempfile.TemporaryDirectory() as tmp:
        db = PlaceDB(Path(tmp) / "world_places.db")
        actors = [
            _actor("Landmark_maren_vegetable_truck", name="BP_Truck_1",
                   location=(320.0, 120.0, 90.0)),
            _actor("Landmark_community_town_square", name="BP_Marker_2",
                   location=(-800.0, 900.0, 0.0)),
        ]
        landmarks = landmarks_from_actors(actors)
        check("both landmarks parsed", len(landmarks) == 2)

        summary = places_manifest.apply_manifest(db, GRID, landmarks)
        check("summary counts", summary == {"applied": 2, "owned": 1,
                                            "community": 1, "skipped": 0})

        owned = db.find_owned_place("vegetable truck")
        check("owned landmark lands at the derived cell",
              owned is not None and owned["col"] == 5 and owned["row"] == 5)
        check("owned landmark owner is maren", owned["owner"] == "maren")
        center = GRID.cell_center(5, 5)
        check("dx/dy offset from the cell center round-trips to the actor's (x,y)",
              (center[0] + owned["dx"], center[1] + owned["dy"]) == (320.0, 120.0))

        check("community landmark names its cell",
              db.find_named_cell("town square") == (3, 7))


# ── levenshtein / scan_landmarks (suspects) ────────────────────────────────────

def test_levenshtein_sanity():
    check("identical strings distance 0", _levenshtein("landmark", "landmark") == 0)
    check("landmarlk is within 2 of landmark",
          _levenshtein("landmarlk", "landmark") <= 2)
    check("wildly different strings are far apart",
          _levenshtein("apc", "landmark") > 2)


def test_scan_landmarks_suspect_detected():
    actors = [_actor("Landmarlk_Dufus_Home", name="Typo1")]
    result = scan_landmarks(actors)
    check("no entries parsed from the typo", result["entries"] == [])
    check("typo'd prefix is a suspect", result["suspects"] == ["Landmarlk_Dufus_Home"])


def test_scan_landmarks_ignores_unrelated_labels():
    actors = [_actor("PlayerStart", name="P1"),
              _actor("MAP_Camera", name="P2"),
              _actor("APC_Maren_BP", name="P3")]
    result = scan_landmarks(actors)
    check("unrelated labels produce no entries", result["entries"] == [])
    check("unrelated labels are not suspects either", result["suspects"] == [])


def test_scan_landmarks_malformed_true_prefix_not_a_suspect():
    actors = [_actor("Landmark_maren_", name="Malformed")]
    result = scan_landmarks(actors)
    check("malformed true-prefix label produces no entry", result["entries"] == [])
    check("malformed true-prefix label is not a suspect either", result["suspects"] == [])


def test_scan_landmarks_shape_and_mix():
    actors = [
        _actor("Landmark_maren_vegetable_truck", name="Good"),
        _actor("Landmarlk_Dufus_Home", name="Typo"),
        _actor("PlayerStart", name="Neither"),
    ]
    result = scan_landmarks(actors)
    check("scan_landmarks returns entries + suspects keys",
          set(result.keys()) == {"entries", "suspects"})
    check("one good landmark parsed", len(result["entries"]) == 1 and
          result["entries"][0]["actor"] == "Good")
    check("one suspect flagged", result["suspects"] == ["Landmarlk_Dufus_Home"])


def test_landmarks_from_actors_thin_wrapper_drops_suspects():
    actors = [_actor("Landmark_maren_vegetable_truck", name="Good"),
              _actor("Landmarlk_Dufus_Home", name="Typo")]
    entries = landmarks_from_actors(actors)
    check("thin wrapper returns only entries", len(entries) == 1 and
          entries[0]["actor"] == "Good")


def main():
    test_valid_owned_label()
    test_valid_community_label()
    test_multi_underscore_name()
    test_non_landmark_label_returns_none_silently()
    test_malformed_labels_skipped()
    test_landmarks_from_actors_mixes_valid_and_invalid()
    test_case_insensitive_prefix()
    test_owner_token_casefold()
    test_community_token_casefold()
    test_merge_precedence_landmark_wins()
    test_merge_no_collision_keeps_both()
    test_end_to_end_actor_to_placedb()
    test_levenshtein_sanity()
    test_scan_landmarks_suspect_detected()
    test_scan_landmarks_ignores_unrelated_labels()
    test_scan_landmarks_malformed_true_prefix_not_a_suspect()
    test_scan_landmarks_shape_and_mix()
    test_landmarks_from_actors_thin_wrapper_drops_suspects()
    print("\nAll landmark checks passed.")


if __name__ == "__main__":
    main()
