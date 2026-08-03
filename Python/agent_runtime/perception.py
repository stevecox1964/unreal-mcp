from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("AgentRuntime")

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

# Gemini speaks the OpenAI chat-completions shape through this compatibility
# endpoint, so no google SDK is needed — and a future local VLM that exposes the
# same OpenAI-compatible API drops in by changing only the endpoint + model.
_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
_DEFAULT_MODEL = "gemini-2.5-flash-lite"  # fast, cheap, non-thinking; thinking models truncate short JSON
_DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"  # Haiku 4.5 is multimodal — does vision too

_PROMPT = """\
You are the eyes of an NPC exploring a 3-D town. Look at the image and report
what you see as JSON ONLY — no prose, no markdown fences.

Separate STATIC places (buildings, signs, fixed structures — things that stay
put and help map the town) from DYNAMIC characters (any human or person-shaped
figure; game models may look blocky but are still people).

{known_line}
Also report what you are standing on: one of "pavement", "road", "dirt_path",
"grass", "cultivated_field", "water", or "other" (use "other" and describe it
in the caption if none fit).

Schema:
{{
  "landmarks":  [{{"label": "<place>", "bearing": "left|center|right", "distance": "near|mid|far", "confidence": 0.0}}],
  "characters": [{{"label": "<who, or 'unknown person'>", "bearing": "left|center|right", "distance": "near|mid|far", "confidence": 0.0}}],
  "footing": "pavement|road|dirt_path|grass|cultivated_field|water|other",
  "caption": "one sentence describing the scene"
}}

Use [] for an array with nothing to report. Confidence is 0.0-1.0."""


def _empty(reason: str) -> dict:
    logger.debug("perceive: %s", reason)
    return {"landmarks": [], "characters": [], "footing": "", "caption": "", "error": reason}


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
    return raw.strip()


class VisionPerceiver:
    """Structured landmark/character extraction from a screenshot via a VLM.

    Providers: ``anthropic`` (Haiku 4.5, multimodal — shares the decision LLM's
    key), ``gemini`` (OpenAI-compatible endpoint), or ``ollama`` (local VLM). The
    single judgement call here is perception — turning pixels into a labelled
    scene — which is exactly what an LLM/VLM is for. Everything downstream
    (mapping, routing) is deterministic code.
    """

    def __init__(self, model: str | None = None, timeout: int = 30):
        self._model = model
        self._timeout = timeout

    def _resolve(self) -> tuple[str, str, str]:
        """Return ``(provider, key, model)``. Provider is ``VISION_PROVIDER`` env
        (``gemini`` default; ``anthropic`` for Haiku; ``ollama`` for a local
        multimodal model)."""
        load_dotenv(_ENV_PATH, override=True)
        provider = (os.environ.get("VISION_PROVIDER") or "gemini").strip().lower()
        if provider == "ollama":
            model = (self._model or os.environ.get("VISION_MODEL")
                     or os.environ.get("OLLAMA_MODEL") or "qwen3.5:4b")
            return provider, "", model
        if provider == "anthropic":
            # Provider-specific model var (like GEMINI_MODEL) — not the generic
            # VISION_MODEL, which is reserved for the local/ollama model.
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            model = (self._model or os.environ.get("ANTHROPIC_VISION_MODEL")
                     or _DEFAULT_ANTHROPIC_MODEL)
            return provider, key, model
        key = os.environ.get("GEMINI_API_KEY", "")
        model = self._model or os.environ.get("GEMINI_MODEL") or _DEFAULT_MODEL
        return provider, key, model

    def perceive(self, image_path: str, known_characters: list[str] | None = None) -> dict:
        """Return ``{"landmarks", "characters", "footing", "caption"}`` for a screenshot.

        Example return::

            {"landmarks": [{"label": "Don's Donuts", "bearing": "right",
                            "distance": "mid", "confidence": 0.85}],
             "characters": [], "footing": "pavement",
             "caption": "A small-town main street."}

        Never raises: on missing key, missing file, or a bad response it returns
        an empty result carrying an ``"error"`` key, so a perception failure
        degrades the tick instead of crashing the simulation loop.
        """
        import requests

        provider, key, model = self._resolve()
        if provider != "ollama" and not key:
            env_key = "ANTHROPIC_API_KEY" if provider == "anthropic" else "GEMINI_API_KEY"
            return _empty(f"{env_key} not set")
        if not image_path or not Path(image_path).exists():
            return _empty(f"image not found: {image_path}")

        known = known_characters or []
        known_line = (
            f"Known characters you may see: {', '.join(known)}. "
            "If a figure matches one, use that name; otherwise 'unknown person'.\n"
            if known else ""
        )
        prompt = _PROMPT.format(known_line=known_line)

        try:
            if provider == "ollama":
                # Local multimodal model (e.g. qwen3.5:4b) reads the screenshot.
                # Vision on a small local model is slower than Gemini — give it room.
                from .ollama_adapter import chat
                content = chat(model, "", prompt, image_path=image_path,
                               timeout=max(self._timeout, 180))
            elif provider == "anthropic":
                content = self._perceive_anthropic(model, key, prompt, image_path)
            else:
                raw = Path(image_path).read_bytes()
                b64 = base64.standard_b64encode(raw).decode()
                response = requests.post(
                    _GEMINI_ENDPOINT,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{_media_type(raw)};base64,{b64}"}},
                            ],
                        }],
                        "max_tokens": 800,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=self._timeout,
                )
                if response.status_code >= 400:
                    return _empty(f"Gemini {response.status_code}: {response.text[:300]}")
                content = response.json()["choices"][0]["message"]["content"]

            data = json.loads(_strip_fences(content))
        except Exception as e:
            return _empty(f"{type(e).__name__}: {e}")

        return {
            "landmarks": _clean(data.get("landmarks")),
            "characters": _clean(data.get("characters")),
            "footing": str(data.get("footing", "")),
            "caption": str(data.get("caption", "")),
            "model": model,
        }

    def _make_anthropic_client(self, key: str):
        """Build the Anthropic SDK client. Isolated so tests can stub it."""
        import anthropic
        return anthropic.Anthropic(api_key=key)

    def _perceive_anthropic(self, model: str, key: str, prompt: str, image_path: str) -> str:
        """Perceive a screenshot via a multimodal Claude model (e.g. Haiku 4.5).

        Returns the raw text content (expected to be the JSON object the prompt
        asks for); ``perceive`` strips any fences and parses it.
        """
        raw = Path(image_path).read_bytes()
        b64 = base64.standard_b64encode(raw).decode()
        client = self._make_anthropic_client(key)
        response = client.messages.create(
            model=model,
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64",
                                                 "media_type": _media_type(raw), "data": b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        # Skip any thinking blocks — content[0] is a ThinkingBlock on models with
        # thinking enabled (e.g. Sonnet 5).
        text = "".join(b.text for b in response.content if b.type == "text")
        if not text:
            blocks = [b.type for b in response.content]
            if response.stop_reason == "max_tokens":
                # A thinking model configured here would spend this budget
                # reasoning and never describe the frame. The default (Haiku 4.5)
                # does not think, so this points at the configured model.
                raise ValueError(
                    f"ran out of tokens before describing the view — spent all "
                    f"{response.usage.output_tokens} output tokens on {blocks}; "
                    f"raise max_tokens or use a non-thinking model for perception"
                )
            raise ValueError(f"No text block in response (blocks: {blocks}, "
                             f"stop_reason: {response.stop_reason})")
        return text


def _media_type(raw: bytes) -> str:
    """Sniff an image's media type from its magic bytes.

    Anthropic validates the declared ``media_type`` against the actual content
    and 400s on a mismatch (Gemini was lenient). The sim's captures are JPEG even
    though they carry a ``.png`` name, so we must report the real type. Defaults
    to ``image/png`` when unrecognized.
    """
    if raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _clean(items) -> list[dict]:
    """Coerce model output into well-formed sighting dicts; drop unusable rows."""
    out: list[dict] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        label = str(it.get("label", "")).strip()
        if not label:
            continue
        try:
            conf = float(it.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        out.append({
            "label": label,
            "bearing": str(it.get("bearing", "center")),
            "distance": str(it.get("distance", "mid")),
            "confidence": conf,
        })
    return out
