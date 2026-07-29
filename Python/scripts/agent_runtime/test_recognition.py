"""Offline tests for APC identity resolution and speech delivery (#44, #45).

Before this, the VLM's "unknown person" was the only character label social
memory ever received, so no APC recognized another and every encounter was a
first meeting; and speech was written to the engine but delivered to nobody, so
the reaction gate's "someone is speaking to you" clause could never fire.

No Unreal, no model call, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_recognition.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import recognition                    # noqa: E402
from agent_runtime.llm_router import _heard_note         # noqa: E402
from agent_runtime.social_memory import SocialMemory     # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def maren(x, y):
    return [{"name": "Maren", "x": float(x), "y": float(y)}]


# ── Geometry: who is actually in view ─────────────────────────────────────────

ahead = recognition.visible_characters((0.0, 0.0), 0.0, maren(400, 0))
check("APC straight ahead is recognized", len(ahead) == 1)
check("recognized by display name", ahead[0]["name"] == "Maren")
check("distance reported", ahead[0]["distance_cm"] == 400.0)
check("bearing is center", ahead[0]["bearing"] == "center")
check("distance bucket is near", ahead[0]["distance"] == "near")

check("APC directly behind is NOT recognized",
      recognition.visible_characters((0.0, 0.0), 0.0, maren(-400, 0)) == [])
check("APC beyond range is NOT recognized",
      recognition.visible_characters((0.0, 0.0), 0.0, maren(9000, 0)) == [])
check("proximity alone is not sighting (90 deg to the side)",
      recognition.visible_characters((0.0, 0.0), 0.0, maren(0, 400)) == [])

# +Y is right in UE's left-handed frame.
right = recognition.visible_characters((0.0, 0.0), 0.0, maren(400, 300))
check("APC to the right reads as right", right and right[0]["bearing"] == "right")
left = recognition.visible_characters((0.0, 0.0), 0.0, maren(400, -300))
check("APC to the left reads as left", left and left[0]["bearing"] == "left")

# Facing rotates the whole view.
check("yaw 180 sees someone behind the origin",
      len(recognition.visible_characters((0.0, 0.0), 180.0, maren(-400, 0))) == 1)

far = recognition.visible_characters((0.0, 0.0), 0.0, maren(2000, 0))
check("mid/far bucketing works", far and far[0]["distance"] == "far")

many = recognition.visible_characters((0.0, 0.0), 0.0, [
    {"name": "Far", "x": 1500.0, "y": 0.0},
    {"name": "Close", "x": 300.0, "y": 0.0},
])
check("nearest first", [p["name"] for p in many] == ["Close", "Far"])

check("nameless entries are skipped",
      recognition.visible_characters((0.0, 0.0), 0.0, [{"name": "", "x": 1.0, "y": 0.0}]) == [])
check("malformed entries are skipped",
      recognition.visible_characters((0.0, 0.0), 0.0, [{"name": "X", "x": None}]) == [])

# ── Merging identities into what vision reported ──────────────────────────────

perceived = [
    {"label": "unknown person", "bearing": "center", "distance": "near"},
    {"label": "unknown person", "bearing": "left", "distance": "far"},
]
merged = recognition.merge_identities(perceived, ahead)
labels = [c["label"] for c in merged]
check("Maren appears by name after merge", "Maren" in labels)
check("the matching anonymous blob is replaced, not duplicated",
      labels.count("unknown person") == 1)
check("a non-APC bystander is preserved",
      any(c["bearing"] == "left" for c in merged if c["label"] == "unknown person"))
check("engine identity is marked as such",
      next(c for c in merged if c["label"] == "Maren")["source"] == "engine")
check("engine identity is not a guess",
      next(c for c in merged if c["label"] == "Maren")["confidence"] == 1.0)

already_named = [{"label": "Maren", "bearing": "center", "distance": "near"}]
check("an already-named vision sighting survives merging",
      "Maren" in [c["label"] for c in recognition.merge_identities(already_named, [])])
check("no identities means the list is unchanged in length",
      len(recognition.merge_identities(perceived, [])) == 2)

# ── The payoff: social memory stops being empty ────────────────────────────────

social = SocialMemory()
for character in merged:
    social.record_sighting(character["label"], "6,6", "Day 1, 09:00")
names = [p["name"] for p in social.acquaintances()]
check("recognition populates social memory", names == ["Maren"])
check("anonymous figures are still not remembered as people", len(names) == 1)

social.record_sighting("Maren", "6,6", "Day 1, 09:03")
check("a second sighting is the same person, not a new one",
      len(social.acquaintances()) == 1)
check("meet_count accumulates", social.acquaintances()[0]["meet_count"] == 2)

# ── Heard speech is grounded, and silence is stated ───────────────────────────

silence = _heard_note({})
check("silence is explicit", "Nobody has spoken to you" in silence)
check("silence forbids inventing a reply", "Do not answer" in silence)

spoken = _heard_note({"heard": [
    {"speaker": "Maren", "text": "Morning, Dufus!", "distance_cm": 250.0}]})
check("the speaker is named", "Maren" in spoken)
check("the words are quoted", "Morning, Dufus!" in spoken)
check("distance is surfaced", "250 cm" in spoken)
check("the interrupt clause is licensed", "interrupt your routine" in spoken)

crowd = _heard_note({"heard": [{"speaker": f"P{i}", "text": "hi"} for i in range(9)]})
check("heard lines are capped", crowd.count("said:") == 5)

print("\nAll recognition + speech tests passed.")


# ── Integration: the manager wiring, end to end ───────────────────────────────

import tempfile                                          # noqa: E402
from types import SimpleNamespace                         # noqa: E402

from agent_runtime.agent_manager import AgentManager       # noqa: E402


class _StubMemory:
    def update_agents_dir(self, d):
        pass

    def record(self, **kwargs):
        pass


def _agent(agent_id, display):
    return SimpleNamespace(agent_id=agent_id, display_name=display)


def _obs(x, y, yaw):
    return {"location": {"x": float(x), "y": float(y), "z": 90.0},
            "rotation": {"x": 0.0, "y": float(yaw), "z": 0.0},
            "grid": {"key": "6,6", "col": 6, "row": 6},
            "world_time": "Day 1, 09:00"}


tmp = Path(tempfile.mkdtemp())
mgr = AgentManager(worlds_dir=tmp, llm_router=None, unreal_bridge=None,
                   memory_store=_StubMemory())
mgr._agents_dir = tmp / "agents"
(mgr._agents_dir / "dufus").mkdir(parents=True)
(mgr._agents_dir / "maren").mkdir(parents=True)
mgr.agents = {"dufus": _agent("dufus", "Dufus"), "maren": _agent("maren", "Maren")}
mgr._live_pos = {"dufus": {"x": 0.0, "y": 0.0}, "maren": {"x": 500.0, "y": 0.0}}

# Dufus faces Maren (+X): he should recognize her by name.
dufus_obs = _obs(0, 0, 0)
mgr._identify_visible_apcs(mgr.agents["dufus"], dufus_obs)
check("manager recognizes the other APC",
      [c["label"] for c in dufus_obs["seen"]["characters"]] == ["Maren"])
check("recognition is exposed for the prompt", dufus_obs["recognized"][0]["name"] == "Maren")

# Facing away, she is not "seen" even though she is 5 m away.
away = _obs(0, 0, 180)
mgr._identify_visible_apcs(mgr.agents["maren"], away)
check("facing away yields no recognition", "recognized" not in away)

# Speaking publishes an utterance; the hearer in range receives it exactly once.
mgr._record_utterance(mgr.agents["maren"],
                      {"type": "speak_to", "message": "Morning, Dufus!"},
                      _obs(500, 0, 180))
heard_obs = _obs(0, 0, 0)
mgr._attach_heard_speech(mgr.agents["dufus"], heard_obs)
check("speech reaches a hearer in range", len(heard_obs.get("heard") or []) == 1)
check("the hearer learns who spoke", heard_obs["heard"][0]["speaker"] == "Maren")
check("the hearer learns what was said", heard_obs["heard"][0]["text"] == "Morning, Dufus!")

again = _obs(0, 0, 0)
mgr._attach_heard_speech(mgr.agents["dufus"], again)
check("the same line is not heard twice", "heard" not in again)

# A speaker never hears themself, and distance gates delivery.
mgr._record_utterance(mgr.agents["maren"], {"type": "speak_to", "message": "Hello?"},
                      _obs(500, 0, 180))
own = _obs(500, 0, 180)
mgr._attach_heard_speech(mgr.agents["maren"], own)
check("an APC never hears its own speech", "heard" not in own)

# Drain Dufus first, so the next check isolates the distance gate rather than
# re-delivering the in-range "Hello?" he had not yet consumed.
mgr._attach_heard_speech(mgr.agents["dufus"], _obs(0, 0, 0))

mgr._record_utterance(mgr.agents["maren"], {"type": "speak_to", "message": "Too far!"},
                      _obs(50000, 0, 180))
distant = _obs(0, 0, 0)
mgr._attach_heard_speech(mgr.agents["dufus"], distant)
check("speech out of earshot is not delivered", "heard" not in distant)

check("an empty message publishes nothing",
      mgr._record_utterance(mgr.agents["maren"], {"type": "speak_to", "message": "  "},
                            _obs(500, 0, 180)) is None
      and all(u["text"].strip() for u in mgr._utterances))

print("\nAll manager wiring tests passed.")
