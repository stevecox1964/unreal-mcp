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
from agent_runtime.perception import VisionPerceiver, _media_type  # noqa: E402

# Real JPEG/PNG magic-byte prefixes (the sim captures JPEG under a .png name).
_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
_PNG = b"\x89PNG\r\n\x1a\n\x00\x00"


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


class _FakeHTTPResponse:
    def __init__(self, payload):
        self.status_code = 200
        self.text = ""
        self._payload = payload

    def json(self):
        return self._payload


class _FakeRequestsModule:
    """Stands in for the lazily-imported ``requests`` module (Gemini branch)."""

    def __init__(self, payload):
        self._payload = payload
        self.last = None

    def post(self, url, headers=None, json=None, timeout=None):
        self.last = {"url": url, "headers": headers, "json": json, "timeout": timeout}
        return _FakeHTTPResponse(self._payload)


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
        check("footing defaults to empty when the model omits it", seen["footing"] == "")

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


def test_perceive_parses_footing():
    reply = (
        '{"landmarks": [], "characters": [], "footing": "cultivated_field", '
        '"caption": "Rows of corn."}'
    )

    @_with_env("VISION_PROVIDER=anthropic\nANTHROPIC_API_KEY=sk-test-123\n")
    def body(img):
        p = VisionPerceiver()
        p._make_anthropic_client = lambda key: _FakeAnthropic(reply)
        seen = p.perceive(str(img))
        check("footing parsed from the model reply", seen["footing"] == "cultivated_field")


def test_media_type_sniffs_real_bytes():
    # The regression: captures are JPEG bytes with a .png name. Anthropic 400s if
    # we declare image/png for JPEG content, so we must sniff the real type.
    check("JPEG magic -> image/jpeg", _media_type(_JPEG) == "image/jpeg")
    check("PNG magic -> image/png", _media_type(_PNG) == "image/png")
    check("GIF magic -> image/gif", _media_type(b"GIF89a....") == "image/gif")
    check("WEBP magic -> image/webp", _media_type(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp")
    check("unknown defaults to png", _media_type(b"garbage") == "image/png")


def test_perceive_sends_sniffed_media_type_for_jpeg():
    # A .png-named file that is actually JPEG must go out as image/jpeg.
    @_with_env("VISION_PROVIDER=anthropic\nANTHROPIC_API_KEY=sk-test-123\n")
    def body(img):
        img.write_bytes(_JPEG + b" rest of a jpeg")
        p = VisionPerceiver()
        fake = _FakeAnthropic(REPLY)
        p._make_anthropic_client = lambda key: fake
        p.perceive(str(img))
        block = next(b for b in fake.last_kwargs["messages"][0]["content"]
                     if b.get("type") == "image")
        check("jpeg-bytes .png sent as image/jpeg", block["source"]["media_type"] == "image/jpeg")


def test_gemini_sends_sniffed_media_type_for_jpeg():
    # Same JPEG-under-.png bug on the Gemini branch: the data URL must declare the
    # real media type, not a hardcoded image/png (Gemini is lenient, but lying is
    # still wrong and a stricter endpoint would reject it).
    @_with_env("GEMINI_API_KEY=g-key\n")
    def body(img):
        img.write_bytes(_JPEG + b" rest of a jpeg")
        saved_env = os.environ.pop("VISION_PROVIDER", None)   # default branch -> gemini
        fake = _FakeRequestsModule({"choices": [{"message": {"content": REPLY}}]})
        saved_mod = sys.modules.get("requests")
        sys.modules["requests"] = fake                        # the lazy `import requests` picks this up
        try:
            seen = VisionPerceiver().perceive(str(img))
        finally:
            if saved_mod is not None:
                sys.modules["requests"] = saved_mod
            else:
                sys.modules.pop("requests", None)
            if saved_env is not None:
                os.environ["VISION_PROVIDER"] = saved_env
        check("gemini perceive parsed ok", seen["landmarks"][0]["label"] == "Don's Donuts")
        url = fake.last["json"]["messages"][0]["content"][1]["image_url"]["url"]
        check("jpeg-bytes .png sent to gemini as image/jpeg",
              url.startswith("data:image/jpeg;base64,"))


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
    test_perceive_parses_footing()
    test_media_type_sniffs_real_bytes()
    test_perceive_sends_sniffed_media_type_for_jpeg()
    test_missing_anthropic_key_degrades()
    test_gemini_sends_sniffed_media_type_for_jpeg()
    test_gemini_still_default()
    print("\nAll vision-perceiver checks passed.")


if __name__ == "__main__":
    main()
