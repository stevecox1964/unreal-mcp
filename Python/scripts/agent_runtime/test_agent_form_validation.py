"""Offline tests: bad numeric agent-form values are rejected, not defaulted.

save_agent used `int(form.get("tier") or 2)`: a blank field quietly became the
default (acceptable) and a non-number crashed the route with a raw 500 (not
acceptable). Fail-loud contract: a non-number is named back to the user, the
files on disk are untouched, and a rejected CREATE leaves no half-made agent
folder behind to block the retry.

Runs against a temp world via TestClient. No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_agent_form_validation.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient       # noqa: E402

import web_ui.main as wm                        # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


AUTHORED = {"character.md": "# Dufus\n", "goals.md": "# Goals\n",
            "rules.md": "# Rules\n", "tools.json": '{"allowed_actions": ["idle"]}',
            "state.json": json.dumps({"agent_id": "dufus", "tier": 2,
                                      "tick_interval_seconds": 10})}


def build_world(root: Path) -> Path:
    agent = root / "MCP_World" / "agents" / "dufus"
    agent.mkdir(parents=True)
    for name, text in AUTHORED.items():
        (agent / name).write_text(text, encoding="utf-8")
    return agent


tmp = Path(tempfile.mkdtemp())
agent_dir = build_world(tmp)
old_worlds = wm.WORLDS_DIR
wm.WORLDS_DIR = tmp
client = TestClient(wm.app)

try:
    form = {"character": "# Dufus\n", "goals": "# Goals\n", "rules": "# Rules\n",
            "allowed_actions": "idle", "current_goal": "survey"}

    # ── Update: a non-number is named, nothing is written ────────────────────
    before = (agent_dir / "state.json").read_text(encoding="utf-8")
    resp = client.post("/worlds/MCP_World/agents/dufus",
                       data={**form, "tier": "banana"})
    check("bad tier re-renders instead of crashing", resp.status_code == 200)
    check("the rejection names the field", "tier" in resp.text and "banana" in resp.text)
    check("state.json untouched by the rejected save",
          (agent_dir / "state.json").read_text(encoding="utf-8") == before)

    resp = client.post("/worlds/MCP_World/agents/dufus",
                       data={**form, "tick_interval_seconds": "fast"})
    check("bad interval is rejected too", "tick_interval_seconds" in resp.text)

    # ── Blank still means default; a good save still saves ───────────────────
    resp = client.post("/worlds/MCP_World/agents/dufus",
                       data={**form, "tier": "", "tick_interval_seconds": "15"},
                       follow_redirects=False)
    check("a valid save still redirects", resp.status_code == 303)
    state = json.loads((agent_dir / "state.json").read_text(encoding="utf-8"))
    check("blank tier fell back to the default", state["tier"] == 2)
    check("a stated interval is stored", state["tick_interval_seconds"] == 15)

    # ── Create: a rejected create leaves no folder behind ────────────────────
    resp = client.post("/worlds/MCP_World/agents/new",
                       data={**form, "agent_id": "newbie", "tier": "x"})
    check("rejected create re-renders with the reason",
          resp.status_code == 200 and "tier" in resp.text)
    check("no half-made agent folder was left",
          not (tmp / "MCP_World" / "agents" / "newbie").exists())

    resp = client.post("/worlds/MCP_World/agents/new",
                       data={**form, "agent_id": "newbie", "tier": "3"},
                       follow_redirects=False)
    check("the retry with a fixed value succeeds", resp.status_code == 303)
    check("the agent now exists",
          (tmp / "MCP_World" / "agents" / "newbie" / "state.json").exists())
finally:
    wm.WORLDS_DIR = old_worlds

print("\nAll agent-form validation tests passed.")
