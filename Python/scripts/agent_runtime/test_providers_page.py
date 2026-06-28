"""Offline tests for the provider-profiles CRUD routes (backlog #7.2).

Drives the web_ui routes against a temp config.json + .env via TestClient — no
browser, no network. Verifies create/assign/delete and that assigning a role
compiles down to the .env keys the runtime reads. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_providers_page.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient   # noqa: E402
import web_ui.main as wm                     # noqa: E402
from agent_runtime.config_store import read_config  # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _with_temp(fn):
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config.json"
        env = Path(tmp) / ".env"
        env.write_text("ANTHROPIC_API_KEY=sk-keep\n", encoding="utf-8")
        old_cfg, old_env = wm.CONFIG_PATH, wm.ENV_PATH
        wm.CONFIG_PATH, wm.ENV_PATH = cfg, env
        try:
            fn(cfg, env, TestClient(wm.app))
        finally:
            wm.CONFIG_PATH, wm.ENV_PATH = old_cfg, old_env


def test_api_lists_seeded_profiles():
    def body(cfg, env, client):
        data = client.get("/api/providers").json()
        check("seeds the haiku profile", "haiku" in data["profiles"])
        check("haiku drives the decision role", data["roles"]["decision"] == "haiku")
    _with_temp(body)


def test_create_and_delete_profile():
    def body(cfg, env, client):
        r = client.post("/providers/save",
                        data={"name": "openai-dec", "provider": "openai", "model": "gpt-5.4-mini"},
                        follow_redirects=False)
        check("save redirects", r.status_code in (302, 303))
        data = client.get("/api/providers").json()
        check("new profile present", data["profiles"]["openai-dec"]["provider"] == "openai")

        client.post("/providers/delete", data={"name": "openai-dec"}, follow_redirects=False)
        data = client.get("/api/providers").json()
        check("profile removed", "openai-dec" not in data["profiles"])
    _with_temp(body)


def test_assign_role_writes_env():
    def body(cfg, env, client):
        client.post("/providers/assign", data={"role": "vision", "profile": "gemini-vision"},
                    follow_redirects=False)
        c = read_config(env)
        check("vision provider applied to .env", c["VISION_PROVIDER"]["value"] == "gemini")
        check("vision model applied to .env", c["GEMINI_MODEL"]["value"] == "gemini-2.5-flash-lite")
        check("secret in .env preserved", c["ANTHROPIC_API_KEY"]["set"] is True)
    _with_temp(body)


def test_page_renders():
    def body(cfg, env, client):
        r = client.get("/providers")
        check("providers page returns 200", r.status_code == 200)
        check("page lists a seeded profile", "haiku" in r.text)
        check("nav links to providers", 'href="/providers"' in r.text)
    _with_temp(body)


def main():
    test_api_lists_seeded_profiles()
    test_create_and_delete_profile()
    test_assign_role_writes_env()
    test_page_renders()
    print("\nAll providers-page checks passed.")


if __name__ == "__main__":
    main()
