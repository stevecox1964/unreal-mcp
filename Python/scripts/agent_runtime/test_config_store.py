"""Offline tests for the .env config store (backlog #2).

Lets the settings page read/write config without hand-editing .env. Secrets are
reported as set/unset only — never echoed back. No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_config_store.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

from agent_runtime.config_store import read_config, write_config, is_secret  # noqa: E402


SAMPLE = """\
# LLM provider settings
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001

# Secrets (do not commit)
ANTHROPIC_API_KEY=sk-secret-value-123
GEMINI_API_KEY=

VISION_PROVIDER=gemini
"""


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _write(tmp: str, text: str) -> Path:
    p = Path(tmp) / ".env"
    p.write_text(text, encoding="utf-8")
    return p


def test_secret_classification():
    check("api key is secret", is_secret("ANTHROPIC_API_KEY"))
    check("token is secret", is_secret("HF_TOKEN"))
    check("password is secret", is_secret("DB_PASSWORD"))
    check("provider is not secret", not is_secret("LLM_PROVIDER"))
    check("model is not secret", not is_secret("LLM_MODEL"))


def test_read_masks_secrets():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = read_config(_write(tmp, SAMPLE))
        check("non-secret value exposed", cfg["LLM_PROVIDER"]["value"] == "anthropic")
        check("non-secret marked set", cfg["LLM_PROVIDER"]["set"] is True)
        check("secret value never echoed", cfg["ANTHROPIC_API_KEY"]["value"] is None)
        check("set secret reported set", cfg["ANTHROPIC_API_KEY"]["set"] is True)
        check("secret flagged is_secret", cfg["ANTHROPIC_API_KEY"]["is_secret"] is True)
        check("empty secret reported unset", cfg["GEMINI_API_KEY"]["set"] is False)
        check("missing file -> empty config", read_config(Path(tmp) / "none.env") == {})


def test_write_preserves_and_updates():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, SAMPLE)
        write_config(p, {"LLM_PROVIDER": "ollama", "OLLAMA_MODEL": "qwen3.5:4b"})
        text = p.read_text(encoding="utf-8")

        check("comment preserved", "# LLM provider settings" in text)
        check("blank-line structure preserved", "\n\n" in text)
        check("existing key updated in place", "LLM_PROVIDER=ollama" in text)
        check("only one LLM_PROVIDER line", text.count("LLM_PROVIDER=") == 1)
        check("untouched key intact", "VISION_PROVIDER=gemini" in text)
        check("new key appended", "OLLAMA_MODEL=qwen3.5:4b" in text)

        cfg = read_config(p)
        check("round-trips through read", cfg["LLM_PROVIDER"]["value"] == "ollama")
        check("new key readable", cfg["OLLAMA_MODEL"]["value"] == "qwen3.5:4b")
        check("secret untouched by unrelated write", cfg["ANTHROPIC_API_KEY"]["set"] is True)


def test_write_omitted_secret_left_alone():
    """A settings form that doesn't resend a secret must not wipe it."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, SAMPLE)
        write_config(p, {"LLM_MODEL": "claude-opus-4-8"})  # secret not in the update
        check("secret preserved when omitted", "ANTHROPIC_API_KEY=sk-secret-value-123"
              in p.read_text(encoding="utf-8"))


def main():
    test_secret_classification()
    test_read_masks_secrets()
    test_write_preserves_and_updates()
    test_write_omitted_secret_left_alone()
    print("\nAll config-store checks passed.")


if __name__ == "__main__":
    main()
