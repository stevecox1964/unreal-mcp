"""Offline tests for the first-run setup banner (backlog #13.1).

A fresh clone has no .env — nothing told a new user how to fix that. This
tests config_store.setup_status() plus the /api/setup route and the banner
rendered on / and /sim when the sim isn't ready. Pattern = test_settings_page.py
(TestClient + temp .env via the same ENV_PATH override). Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_first_run.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient   # noqa: E402
import web_ui.main as wm                     # noqa: E402
from agent_runtime.config_store import setup_status   # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _with_env(text, fn):
    """Run fn(env_path, TestClient) with wm.ENV_PATH pointed at a temp .env.
    ``text=None`` means no .env file is created at all (missing-file case)."""
    with tempfile.TemporaryDirectory() as tmp:
        env = Path(tmp) / ".env"
        if text is not None:
            env.write_text(text, encoding="utf-8")
        old = wm.ENV_PATH
        wm.ENV_PATH = env
        try:
            fn(env, TestClient(wm.app))
        finally:
            wm.ENV_PATH = old


def test_missing_env_not_ready():
    def body(env, client):
        status = setup_status(env)
        check("missing .env: env_exists False", status["env_exists"] is False)
        check("missing .env: provider_ready False", status["provider_ready"] is False)
        check("missing .env: ready False", status["ready"] is False)
    _with_env(None, body)


def test_ollama_no_key_is_ready():
    def body(env, client):
        status = setup_status(env)
        check("ollama: env_exists True", status["env_exists"] is True)
        check("ollama needs no key: provider_ready True", status["provider_ready"] is True)
        check("ollama: ready True", status["ready"] is True)
    _with_env("LLM_PROVIDER=ollama\n", body)


def test_anthropic_with_key_is_ready():
    def body(env, client):
        status = setup_status(env)
        check("anthropic+key: provider_ready True", status["provider_ready"] is True)
        check("anthropic+key: ready True", status["ready"] is True)
    _with_env("LLM_PROVIDER=anthropic\nANTHROPIC_API_KEY=sk-secret-123\n", body)


def test_anthropic_without_key_not_ready():
    def body(env, client):
        status = setup_status(env)
        check("anthropic no key: provider_ready False", status["provider_ready"] is False)
        check("anthropic no key: ready False", status["ready"] is False)
    _with_env("LLM_PROVIDER=anthropic\n", body)


def test_setup_status_never_raises_on_garbage():
    def body(env, client):
        env.write_text("\x00\x01 not really an env file", encoding="utf-8")
        status = setup_status(env)   # must not raise
        check("garbage file: dict shape stays intact",
              set(status) == {"env_exists", "provider_ready", "ready"})
    _with_env("placeholder\n", body)


def test_api_setup_route():
    def body(env, client):
        r = client.get("/api/setup")
        check("route returns 200", r.status_code == 200)
        data = r.json()
        check("route reports ready", data["ready"] is True)
    _with_env("LLM_PROVIDER=ollama\n", body)


BANNER_MARK = 'id="setup-banner"'   # the rendered div, not the always-present .setup-banner CSS rule


def test_banner_present_when_not_ready():
    def body(env, client):
        index_text = client.get("/").text
        sim_text = client.get("/sim").text
        check("banner on / when not ready", BANNER_MARK in index_text)
        check("banner text on /", "Add your model provider key" in index_text)
        check("banner links to /settings", 'href="/settings"' in index_text)
        check("banner on /sim when not ready", BANNER_MARK in sim_text)
    _with_env(None, body)


def test_banner_absent_when_ready():
    def body(env, client):
        index_text = client.get("/").text
        sim_text = client.get("/sim").text
        check("no banner on / when ready", BANNER_MARK not in index_text)
        check("no banner on /sim when ready", BANNER_MARK not in sim_text)
    _with_env("LLM_PROVIDER=ollama\n", body)


def main():
    test_missing_env_not_ready()
    test_ollama_no_key_is_ready()
    test_anthropic_with_key_is_ready()
    test_anthropic_without_key_not_ready()
    test_setup_status_never_raises_on_garbage()
    test_api_setup_route()
    test_banner_present_when_not_ready()
    test_banner_absent_when_ready()
    print("\nAll first-run setup checks passed.")


if __name__ == "__main__":
    main()
