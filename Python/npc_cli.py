"""
NPC CLI — author and manage agent definition files for the simulator.

Usage:
  python npc_cli.py create <agent_id>       Interactive create with prompts
  python npc_cli.py list                    List all agents with key info
  python npc_cli.py show <agent_id>         Dump full agent config
  python npc_cli.py set <agent_id> <field> <value>   Update a state.json field
  python npc_cli.py delete <agent_id>       Delete agent folder (with confirmation)
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

AGENTS_DIR = Path(__file__).parent / "agents"

ALL_ACTIONS = [
    "idle", "walk_to", "speak_to", "inspect_object",
    "follow_character", "attack", "flee", "observe", "remember",
]

TIERS = {"1": "Hero (full LLM)", "2": "Simulated (light LLM)", "3": "Lightweight (no LLM)"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def agent_path(agent_id: str) -> Path:
    return AGENTS_DIR / agent_id


def load_state(agent_id: str) -> dict:
    p = agent_path(agent_id) / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_state(agent_id: str, state: dict):
    p = agent_path(agent_id) / "state.json"
    p.write_text(json.dumps(state, indent=2))


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {label}{suffix}: ").strip()
    return val if val else default


def prompt_yn(label: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    val = input(f"  {label} ({suffix}): ").strip().lower()
    if not val:
        return default
    return val.startswith("y")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_create(args):
    agent_id = args.agent_id
    path = agent_path(agent_id)

    if path.exists():
        print(f"Agent '{agent_id}' already exists. Use 'show' or 'set' to modify it.")
        sys.exit(1)

    print(f"\n=== Creating agent: {agent_id} ===\n")
    print("Unreal binding:")
    unreal_actor_name = prompt("Unreal Actor Name (label in Outliner)", default=agent_id.capitalize())
    blueprint_class   = prompt("Blueprint Class (e.g. BP_Gondolf_C)", default="")

    print("\nAgent tier:")
    for k, v in TIERS.items():
        print(f"  {k} = {v}")
    tier = prompt("Tier", default="1")
    if tier not in TIERS:
        tier = "1"

    print("\nBehaviour:")
    goal          = prompt("Starting goal (e.g. patrol_village)", default="idle")
    tick_interval = prompt("Tick interval seconds", default="10")
    speech_cd     = prompt("Speech cooldown seconds", default="30")

    print("\nPersonality (press Enter to fill in later):")
    role        = prompt("Role / one-line description", default="")
    personality = prompt("Personality traits", default="")

    # Build files
    path.mkdir(parents=True)

    (path / "character.md").write_text(
        f"# Agent: {agent_id}\n\n"
        f"## Role\n\n{role}\n\n"
        f"## Personality\n\n{personality}\n\n"
        f"## Speaking Style\n\n\n\n"
        f"## Backstory\n\n\n",
        encoding="utf-8",
    )

    (path / "goals.md").write_text(
        f"# Goals\n\n## Long-Term Goals\n\n\n\n## Current Goal\n\n{goal}\n",
        encoding="utf-8",
    )

    (path / "rules.md").write_text(
        "# Rules\n\n"
        "- Do not invent tools or actions.\n"
        "- Do not control other characters.\n"
        "- Return structured JSON decisions only.\n"
        "- Do not output prose outside JSON.\n",
        encoding="utf-8",
    )

    (path / "tools.json").write_text(
        json.dumps({"allowed_actions": ALL_ACTIONS}, indent=2),
        encoding="utf-8",
    )

    state = {
        "agent_id":            agent_id,
        "unreal_actor_name":   unreal_actor_name,
        "blueprint_class":     blueprint_class,
        "tier":                int(tier),
        "is_active":           True,
        "is_busy":             False,
        "current_goal":        goal,
        "tick_interval_seconds":   int(tick_interval),
        "speech_cooldown_seconds": int(speech_cd),
        "last_tick_time":      None,
        "last_spoke_time":     None,
    }
    save_state(agent_id, state)

    (path / "memory.json").write_text(
        json.dumps({"agent_id": agent_id, "memories": []}, indent=2),
        encoding="utf-8",
    )

    print(f"\n✓ Agent '{agent_id}' created at {path}")
    print(f"  Unreal actor : {unreal_actor_name}")
    print(f"  Blueprint    : {blueprint_class or '(not set)'}")
    print(f"  Tier         : {tier} — {TIERS[tier]}")
    print(f"  Goal         : {goal}")
    print(f"\nEdit character/goals/rules in:\n  {path}")


def cmd_list(args):
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    agents = sorted(d.name for d in AGENTS_DIR.iterdir() if d.is_dir())

    if not agents:
        print("No agents found. Run: python npc_cli.py create <agent_id>")
        return

    print(f"\n{'AGENT':<18} {'ACTOR':<20} {'TIER':<4} {'GOAL':<24} {'ACTIVE'}")
    print("-" * 76)
    for aid in agents:
        s = load_state(aid)
        print(
            f"{aid:<18} "
            f"{s.get('unreal_actor_name', '?'):<20} "
            f"{s.get('tier', '?'):<4} "
            f"{s.get('current_goal', ''):<24} "
            f"{'yes' if s.get('is_active', True) else 'no'}"
        )
    print()


def cmd_show(args):
    agent_id = args.agent_id
    path = agent_path(agent_id)

    if not path.exists():
        print(f"Agent '{agent_id}' not found.")
        sys.exit(1)

    print(f"\n=== Agent: {agent_id} ===\n")

    for fname in ("character.md", "goals.md", "rules.md"):
        p = path / fname
        if p.exists():
            print(f"── {fname} ──")
            print(p.read_text(encoding="utf-8").strip())
            print()

    for fname in ("tools.json", "state.json", "memory.json"):
        p = path / fname
        if p.exists():
            print(f"── {fname} ──")
            print(json.dumps(json.loads(p.read_text()), indent=2))
            print()


def cmd_set(args):
    agent_id = args.agent_id
    field    = args.field
    value    = args.value

    if not agent_path(agent_id).exists():
        print(f"Agent '{agent_id}' not found.")
        sys.exit(1)

    state = load_state(agent_id)

    # Coerce type to match existing value where possible
    if field in state and isinstance(state[field], bool):
        value = value.lower() in ("true", "1", "yes")
    elif field in state and isinstance(state[field], int):
        value = int(value)
    elif field in state and isinstance(state[field], float):
        value = float(value)

    state[field] = value
    save_state(agent_id, state)
    print(f"✓ {agent_id}.{field} = {value}")


def cmd_delete(args):
    agent_id = args.agent_id
    path = agent_path(agent_id)

    if not path.exists():
        print(f"Agent '{agent_id}' not found.")
        sys.exit(1)

    confirm = input(f"Delete agent '{agent_id}'? This cannot be undone. (y/N): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    shutil.rmtree(path)
    print(f"✓ Agent '{agent_id}' deleted.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="npc_cli",
        description="Author and manage NPC agent definitions for the simulator.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Create a new agent interactively")
    p_create.add_argument("agent_id")
    p_create.set_defaults(func=cmd_create)

    p_list = sub.add_parser("list", help="List all agents")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show full agent config")
    p_show.add_argument("agent_id")
    p_show.set_defaults(func=cmd_show)

    p_set = sub.add_parser("set", help="Update a field in state.json")
    p_set.add_argument("agent_id")
    p_set.add_argument("field")
    p_set.add_argument("value")
    p_set.set_defaults(func=cmd_set)

    p_del = sub.add_parser("delete", help="Delete an agent")
    p_del.add_argument("agent_id")
    p_del.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
