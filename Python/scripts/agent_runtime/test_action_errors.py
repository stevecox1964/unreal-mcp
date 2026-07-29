"""Offline tests for bounded bridge/action error diagnostics (backlog #42).

SR28 recorded a ``speak_to`` failure after ~15 s but kept only the status, so
the cause could not be distinguished among timeout, target resolution and
transport. These tests pin the classifier's categories, its safety bounds, and
that successful entries stay exactly as compact as before.

No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_action_errors.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.memory_store import (MemoryStore,          # noqa: E402
                                        classify_action_error)


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


# ── Non-failures are not diagnostics ──────────────────────────────────────────

check("success returns None", classify_action_error({"status": "success"}) is None)
check("accepted returns None",
      classify_action_error({"status": "accepted", "action": "idle"}) is None)
check("accepted-with-note is a recovery, not a failure",
      classify_action_error({"status": "accepted", "action": "idle",
                             "note": "walk forward blocked: wall"}) is None)
check("non-dict returns None", classify_action_error("boom") is None)

# ── Each failure shape maps to its actionable category ────────────────────────

cases = [
    ({"success": False, "error": "Unreal not connected"}, "not_connected"),
    ({"status": "error", "error": "send_command timed out after 15s"}, "timeout"),
    ({"success": False, "error": "Actor 'Maren' not found"}, "target_unresolved"),
    ({"success": False, "error": "[Errno 104] Connection reset by peer"}, "transport"),
    ({"success": False, "error": "something else broke"}, "runtime"),
]
for result, expected in cases:
    got = classify_action_error(result, 100)
    check(f"{expected} classified from {result['error']!r}", got["code"] == expected)

check("elapsed phase is carried",
      classify_action_error({"success": False, "error": "x"}, 15021.4)["elapsed_ms"] == 15021.4)
check("elapsed omitted when unknown",
      "elapsed_ms" not in classify_action_error({"success": False, "error": "x"}))

# ── Safety bounds ─────────────────────────────────────────────────────────────

long = classify_action_error({"success": False, "error": "x" * 5000}, 1)
check("message is capped", len(long["message"]) == 240)

redacted = classify_action_error(
    {"success": False, "error": "auth failed api_key=sk-abcd1234567890EFGH rejected"}, 1)
check("key value is redacted", "sk-abcd1234567890EFGH" not in redacted["message"])
check("redaction marker present", "[redacted]" in redacted["message"])

check("missing detail is stated, not blank",
      classify_action_error({"success": False}, 5)["message"] == "(no detail reported)")
check("non-string error is coerced",
      classify_action_error({"success": False, "error": 12345})["message"] == "12345")
check("whitespace is collapsed",
      classify_action_error({"success": False,
                             "error": "a\n\n  b"})["message"] == "a b")

# ── The decision feed carries it, and only on failure ─────────────────────────

tmp = Path(tempfile.mkdtemp())
agents = tmp / "agents"
(agents / "dufus").mkdir(parents=True)
store = MemoryStore(tmp)
store.update_agents_dir(agents)
store.sim_run_id = "SR29"

store.record("dufus", {"_thought": "greeting Maren"}, {"type": "speak_to"},
             {"success": False, "error": "send_command timed out"},
             timing={"act_ms": 15021.4})
store.record("dufus", {"_thought": "walking on"}, {"type": "walk_to"},
             {"status": "success"}, timing={"act_ms": 120.0})

entries = [json.loads(line) for line
           in store.decisions_log.read_text(encoding="utf-8").strip().splitlines()]
check("both decisions logged", len(entries) == 2)

failed, ok = entries
check("failure carries a diagnostic", "error" in failed)
check("SR28's case reads as timeout", failed["error"]["code"] == "timeout")
check("SR28's elapsed phase survives", failed["error"]["elapsed_ms"] == 15021.4)
check("failure stays run-attributed", failed["sim_run"] == "SR29")
check("success carries no error key", "error" not in ok)
check("success entry is otherwise unchanged",
      sorted(ok) == ["action_type", "agent_id", "result_status",
                     "sim_run", "thought", "timestamp", "timing"])

print("\nAll action-error tests passed.")
