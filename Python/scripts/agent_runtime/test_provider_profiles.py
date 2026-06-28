"""Offline tests for provider profiles + role->env compilation (backlog #7.1).

Profiles are named {provider, model} pairs assigned to the decision/vision
roles; applying them compiles down to the plain .env keys the runtime already
reads. All file I/O is to a temp dir — no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_provider_profiles.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime import provider_profiles as pp   # noqa: E402
from agent_runtime.config_store import read_config   # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_missing_file_seeds_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        data = pp.read_profiles(Path(tmp) / "config.json")
        check("seeds the haiku profile", data["profiles"]["haiku"]["provider"] == "anthropic")
        check("haiku assigned to decision", data["roles"]["decision"] == "haiku")
        check("haiku assigned to vision", data["roles"]["vision"] == "haiku")


def test_round_trip_and_crud():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config.json"
        data = pp.default_config()
        pp.upsert_profile(data, "openai-dec", "openai", "gpt-5.4-mini")
        pp.assign_role(data, "decision", "openai-dec")
        pp.write_profiles(cfg, data)

        back = pp.read_profiles(cfg)
        check("new profile persisted", back["profiles"]["openai-dec"]["model"] == "gpt-5.4-mini")
        check("role assignment persisted", back["roles"]["decision"] == "openai-dec")

        pp.delete_profile(back, "openai-dec")
        check("profile deleted", "openai-dec" not in back["profiles"])
        check("dangling role unassigned on delete", back["roles"]["decision"] is None)


def test_assign_unknown_profile_rejected():
    data = pp.default_config()
    try:
        pp.assign_role(data, "vision", "does-not-exist")
        check("assigning a missing profile raises", False)
    except ValueError:
        check("assigning a missing profile raises", True)


def test_apply_compiles_roles_to_env():
    with tempfile.TemporaryDirectory() as tmp:
        env = Path(tmp) / ".env"
        env.write_text("ANTHROPIC_API_KEY=sk-keep-me\n", encoding="utf-8")

        data = pp.default_config()
        # decision = haiku (anthropic), vision = gemini-vision (gemini)
        pp.assign_role(data, "vision", "gemini-vision")
        pp.apply_to_env(data, env)

        cfg = read_config(env)
        check("decision provider written", cfg["LLM_PROVIDER"]["value"] == "anthropic")
        check("decision model -> LLM_MODEL", cfg["LLM_MODEL"]["value"] == "claude-haiku-4-5-20251001")
        check("vision provider written", cfg["VISION_PROVIDER"]["value"] == "gemini")
        check("gemini vision model -> GEMINI_MODEL",
              cfg["GEMINI_MODEL"]["value"] == "gemini-2.5-flash-lite")
        check("existing secret left intact", cfg["ANTHROPIC_API_KEY"]["set"] is True)


def test_apply_uses_provider_specific_vision_var():
    with tempfile.TemporaryDirectory() as tmp:
        env = Path(tmp) / ".env"
        data = pp.default_config()  # vision = haiku (anthropic)
        updates = pp.apply_to_env(data, env)
        check("anthropic vision -> ANTHROPIC_VISION_MODEL",
              updates.get("ANTHROPIC_VISION_MODEL") == "claude-haiku-4-5-20251001")
        check("no GEMINI_MODEL written for an anthropic vision profile",
              "GEMINI_MODEL" not in updates)


def main():
    test_missing_file_seeds_defaults()
    test_round_trip_and_crud()
    test_assign_unknown_profile_rejected()
    test_apply_compiles_roles_to_env()
    test_apply_uses_provider_specific_vision_var()
    print("\nAll provider-profile checks passed.")


if __name__ == "__main__":
    main()
