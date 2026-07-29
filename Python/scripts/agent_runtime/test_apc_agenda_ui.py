"""Offline tests for the APC drill-down + agenda editor (backlog #43).

The user could not read raw endpoint JSON and could not edit an APC's authored
agenda from the cockpit. These tests pin the parts that must hold without a
browser: the profile page carries the editor and the live panel, a valid agenda
round-trips, and an invalid one is rejected inline with the file left untouched
— no partial write, and no collateral damage to character/goals/rules.

Runs against a temp world via TestClient. No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_apc_agenda_ui.py
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


VALID = {
    "schema_version": 1,
    "tasks": [
        {"id": "morning_home", "start": "07:00", "end": "08:30", "place": "home",
         "objective": "get ready", "completion": {"type": "time_block_ends"}},
        {"id": "travel_square", "start": "08:30", "end": "09:00",
         "place": "village square", "objective": "walk to the square",
         "completion": {"type": "arrive_at_place"}},
    ],
}

AUTHORED = {"character.md": "# Dufus\n", "goals.md": "# Goals\n",
            "rules.md": "# Rules\n", "tools.json": '{"allowed_actions": ["idle"]}',
            "state.json": '{"agent_id": "dufus", "tier": 2}'}


def build_world(root: Path) -> Path:
    agent = root / "MCP_World" / "agents" / "dufus"
    agent.mkdir(parents=True)
    for name, text in AUTHORED.items():
        (agent / name).write_text(text, encoding="utf-8")
    (agent / "agenda.json").write_text(json.dumps(VALID, indent=2), encoding="utf-8")
    return agent


tmp = Path(tempfile.mkdtemp())
agent_dir = build_world(tmp)
agenda_path = agent_dir / "agenda.json"
original = agenda_path.read_text(encoding="utf-8")

old_worlds = wm.WORLDS_DIR
wm.WORLDS_DIR = tmp
try:
    client = TestClient(wm.app)

    # ── The profile is reachable and carries both new surfaces ────────────────
    page = client.get("/worlds/MCP_World/agents/dufus")
    check("profile renders", page.status_code == 200)
    check("agenda editor present", 'name="agenda_text"' in page.text)
    check("authored agenda shown in the editor", "morning_home" in page.text)
    check("live task panel present", 'id="apc-runtime"' in page.text)
    check("drill-down renderer loaded", "/static/apc_drilldown.js" in page.text)

    index = client.get("/")
    check("APCs reachable without knowing a URL",
          "/worlds/MCP_World/agents/dufus" in index.text)

    # ── Malformed JSON: rejected inline, nothing written ──────────────────────
    bad = client.post("/worlds/MCP_World/agents/dufus/agenda",
                      data={"agenda_text": "{not json"})
    check("malformed JSON re-renders the page", bad.status_code == 200)
    check("malformed JSON reports it was not saved", "Agenda not saved" in bad.text)
    check("malformed JSON names the syntax error", "invalid JSON" in bad.text)
    check("malformed JSON left the file untouched",
          agenda_path.read_text(encoding="utf-8") == original)

    # ── Schema violations: every error surfaced, still no partial write ───────
    broken = json.dumps({"schema_version": 1, "tasks": [
        {"id": "a", "start": "09:00", "end": "08:00", "place": "x",
         "objective": "y", "completion": {"type": "nope"}}]})
    rejected = client.post("/worlds/MCP_World/agents/dufus/agenda",
                           data={"agenda_text": broken})
    check("bad schema re-renders the page", rejected.status_code == 200)
    check("bad completion policy is named", "completion.type must be one of" in rejected.text)
    check("bad time window is named", "start must be before end" in rejected.text)
    check("bad schema left the file untouched",
          agenda_path.read_text(encoding="utf-8") == original)
    check("the rejected text stays on screen for editing", "nope" in rejected.text)

    # ── A valid agenda round-trips ────────────────────────────────────────────
    edited = json.loads(original)
    edited["tasks"][0]["objective"] = "search for the missing hat"
    saved = client.post("/worlds/MCP_World/agents/dufus/agenda",
                        data={"agenda_text": json.dumps(edited)},
                        follow_redirects=False)
    check("valid agenda redirects", saved.status_code == 303)
    on_disk = json.loads(agenda_path.read_text(encoding="utf-8"))
    check("valid agenda persisted",
          on_disk["tasks"][0]["objective"] == "search for the missing hat")
    check("unrelated tasks survive the edit",
          [t["id"] for t in on_disk["tasks"]] == ["morning_home", "travel_square"])

    # ── Saving an agenda must not touch other authored files ─────────────────
    for name, text in AUTHORED.items():
        check(f"{name} untouched by an agenda save",
              (agent_dir / name).read_text(encoding="utf-8") == text)

    # ── A missing agenda offers a valid starting point ───────────────────────
    agenda_path.unlink()
    fresh = client.get("/worlds/MCP_World/agents/dufus")
    check("missing agenda still renders the editor", 'name="agenda_text"' in fresh.text)
    check("starter template is valid",
          wm.validate_agenda_text(wm.AGENDA_STARTER)[1] == [])

    # ── Runner down is a bounded message, not a stack trace ──────────────────
    down = client.get("/api/sim/agents/dufus")
    check("no runner yields the bounded envelope", down.status_code == 503)
    check("no runner explains itself", down.json().get("error") == "no sim runner running")
finally:
    wm.WORLDS_DIR = old_worlds

print("\nAll APC agenda UI tests passed.")
