"""Offline tests for VisionPerceiver provider routing (backlog #7.0).

Haiku 4.5 is multimodal, so vision can run on Anthropic (one provider/key for
both decisions and vision) instead of Gemini. These tests stub the Anthropic
client and drive a temp .env — no SDK install, no network, no screenshot beyond
a tiny temp file. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_vision_perceiver.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Python/
sys.path.insert(0, str(ROOT))

import agent_runtime.perception as perception   # noqa: E402
from agent_runtime.perception import VisionPerceiver  # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


class _FakeContent:
    def __init__(self, text):
        self.text = text


class _FakeResponse:
    def __init__(self, text):
        self.content = [_FakeContent(text)]


class _FakeAnthropic:
    """Records the messages.create call and returns canned JSON text."""

    def __init__(self, reply):
        self._reply = reply
        self.last_kwargs = None
        self.messages = self  # so client.messages.create(...) lands here

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self._reply)


def _with_env(text):
    """Run a body with perception._ENV_PATH pointed at a temp .env."""
    def deco(fn):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text(text, encoding="utf-8")
            img = Path(tmp) / "shot.png"
            img.write_bytes(b"\x89PNG\r\n\x1a\n fake bytes")
            old = perception._ENV_PATH
            perception._ENV_PATH = env
            try:
                fn(img)
            finally:
                perception._ENV_PATH = old
    return deco


REPLY = (
    '{"landmarks": [{"label": "Don\'s Donuts", "bearing": "right", '
    '"distance": "mid", "confidence": 0.9}], '
    '"characters": [{"label": "unknown person", "bearing": "left", '
    '"distance": "near", "confidence": 0.7}], '
    '"caption": "A small-town street."}'
)


def test_resolves_anthropic_haiku_default():
    @_with_env("VISION_PROVIDER=anthropic\nANTHROPIC_API_KEY=sk-test-123\n")
    def body(img):
        provider, key, model = VisionPerceiver()._resolve()
        check("provider is anthropic", provider == "anthropic")
        check("key read from ANTHROPIC_API_KEY", key == "sk-test-123")
        check("model defaults to Haiku 4.5", model == "claude-haiku-4-5-20251001")


def test_perceive_via_anthropic_parses_and_passes_image():
    @_with_env("VISION_PROVIDER=anthropic\nANTHROPIC_API_KEY=sk-test-123\n")
    def body(img):
        p = VisionPerceiver()
        fake = _FakeAnthropic(REPLY)
        p._make_anthropic_client = lambda key: fake

        seen = p.perceive(str(img), known_characters=["Dufus"])

        check("no error on the result", "error" not in seen)
        check("landmark parsed", seen["landmarks"][0]["label"] == "Don's Donuts")
        check("character parsed", seen["characters"][0]["label"] == "unknown person")
        check("caption parsed", seen["caption"] == "A small-town street.")
        check("model reported back", seen["model"] == "claude-haiku-4-5-20251001")

        # The call carried an image block and the right model.
        kw = fake.last_kwargs
        check("model sent to API", kw["model"] == "claude-haiku-4-5-20251001")
        blocks = kw["messages"][0]["content"]
        check("an image block was sent", any(b.get("type") == "image" for b in blocks))
        check("a text prompt was sent", any(b.get("type") == "text" for b in blocks))
        check("known character reached the prompt",
              "Dufus" in next(b["text"] for b in blocks if b.get("type") == "text"))


def test_missing_anthropic_key_degrades():
    @_with_env("VISION_PROVIDER=anthropic\n")
    def body(img):
        # The .env omits the key; ensure the shell env doesn't leak one in.
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            seen = VisionPerceiver().perceive(str(img))
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved
        check("missing key returns empty result", seen["landmarks"] == [])
        check("error names the right key", "ANTHROPIC_API_KEY" in seen.get("error", ""))


def test_gemini_still_default():
    @_with_env("GEMINI_API_KEY=g-key\n")
    def body(img):
        # No VISION_PROVIDER set anywhere -> gemini is the default branch.
        saved = os.environ.pop("VISION_PROVIDER", None)
        try:
            provider, key, model = VisionPerceiver()._resolve()
        finally:
            if saved is not None:
                os.environ["VISION_PROVIDER"] = saved
        check("default provider stays gemini", provider == "gemini")
        check("gemini key resolved", key == "g-key")


def main():
    test_resolves_anthropic_haiku_default()
    test_perceive_via_anthropic_parses_and_passes_image()
    test_missing_anthropic_key_degrades()
    test_gemini_still_default()
    print("\nAll vision-perceiver checks passed.")


if __name__ == "__main__":
    main()
