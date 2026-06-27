"""Offline tests for the web settings page backend (autonomous queue #4).

The settings page lets the user manage provider/model config through the UI
instead of hand-editing .env, via config_store (secrets shown set/unset only).
Here we test the route handlers against an in-process app over a temp .env — no
browser, no real .env, no network. Visual polish is verified live. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_settings_page.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient   # noqa: E402
import web_ui.main as wm                     # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


SAMPLE = "LLM_PROVIDER=anthropic\nLLM_MODEL=claude-haiku-4-5\nANTHROPIC_API_KEY=sk-secret-123\n"


def _with_temp_env(fn):
    with tempfile.TemporaryDirectory() as tmp:
        env = Path(tmp) / ".env"
        env.write_text(SAMPLE, encoding="utf-8")
        old = wm.ENV_PATH
        wm.ENV_PATH = env
        try:
            fn(env, TestClient(wm.app))
        finally:
            wm.ENV_PATH = old


def test_api_settings_get_masks_secrets():
    def body(env, client):
        cfg = client.get("/api/settings").json()
        check("non-secret value exposed", cfg["LLM_PROVIDER"]["value"] == "anthropic")
        check("secret value masked", cfg["ANTHROPIC_API_KEY"]["value"] is None)
        check("secret reported set", cfg["ANTHROPIC_API_KEY"]["set"] is True)
    _with_temp_env(body)


def test_post_settings_writes_and_preserves_secret():
    def body(env, client):
        # Form post: change provider, leave the secret field blank.
        r = client.post("/settings", data={"LLM_PROVIDER": "ollama", "ANTHROPIC_API_KEY": ""},
                        follow_redirects=False)
        check("post redirects back to the page", r.status_code in (302, 303))

        text = env.read_text(encoding="utf-8")
        check("provider updated on disk", "LLM_PROVIDER=ollama" in text)
        check("blank secret did NOT wipe the key", "ANTHROPIC_API_KEY=sk-secret-123" in text)

        cfg = client.get("/api/settings").json()
        check("read-back reflects the change", cfg["LLM_PROVIDER"]["value"] == "ollama")
    _with_temp_env(body)


def test_settings_page_renders():
    def body(env, client):
        r = client.get("/settings")
        check("settings page returns 200", r.status_code == 200)
        check("page shows a known config key", "LLM_PROVIDER" in r.text)
    _with_temp_env(body)


def test_branding_renamed():
    """Surface strings renamed NPC Builder -> Unreal World Sim (queue #5)."""
    def body(env, client):
        text = client.get("/settings").text
        check("page shows the new brand", "Unreal World Sim" in text)
        check("old brand gone from the chrome", "NPC Builder" not in text)
        check("app title renamed", wm.app.title == "Unreal World Sim")
        check("nav links to the settings page", 'href="/settings"' in text)
    _with_temp_env(body)


def main():
    test_api_settings_get_masks_secrets()
    test_post_settings_writes_and_preserves_secret()
    test_settings_page_renders()
    test_branding_renamed()
    print("\nAll settings-page checks passed.")


if __name__ == "__main__":
    main()
