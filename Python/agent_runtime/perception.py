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

_PROMPT = """\
You are the eyes of an NPC exploring a 3-D town. Look at the image and report
what you see as JSON ONLY — no prose, no markdown fences.

Separate STATIC places (buildings, signs, fixed structures — things that stay
put and help map the town) from DYNAMIC characters (any human or person-shaped
figure; game models may look blocky but are still people).

{known_line}
Schema:
{{
  "landmarks":  [{{"label": "<place>", "bearing": "left|center|right", "distance": "near|mid|far", "confidence": 0.0}}],
  "characters": [{{"label": "<who, or 'unknown person'>", "bearing": "left|center|right", "distance": "near|mid|far", "confidence": 0.0}}],
  "caption": "one sentence describing the scene"
}}

Use [] for an array with nothing to report. Confidence is 0.0-1.0."""


def _empty(reason: str) -> dict:
    logger.debug("perceive: %s", reason)
    return {"landmarks": [], "characters": [], "caption": "", "error": reason}


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
    return raw.strip()


class VisionPerceiver:
    """Structured landmark/character extraction from a screenshot via a VLM.

    Provider is Gemini (OpenAI-compatible endpoint) for now. The single
    judgement call here is perception — turning pixels into a labelled scene —
    which is exactly what an LLM/VLM is for. Everything downstream (mapping,
    routing) is deterministic code.
    """

    def __init__(self, model: str | None = None, timeout: int = 30):
        self._model = model
        self._timeout = timeout

    def _resolve(self) -> tuple[str, str]:
        load_dotenv(_ENV_PATH, override=True)
        key = os.environ.get("GEMINI_API_KEY", "")
        model = self._model or os.environ.get("GEMINI_MODEL") or _DEFAULT_MODEL
        return key, model

    def perceive(self, image_path: str, known_characters: list[str] | None = None) -> dict:
        """Return ``{"landmarks", "characters", "caption"}`` for a screenshot.

        Example return::

            {"landmarks": [{"label": "Don's Donuts", "bearing": "right",
                            "distance": "mid", "confidence": 0.85}],
             "characters": [], "caption": "A small-town main street."}

        Never raises: on missing key, missing file, or a bad response it returns
        an empty result carrying an ``"error"`` key, so a perception failure
        degrades the tick instead of crashing the simulation loop.
        """
        import requests

        key, model = self._resolve()
        if not key:
            return _empty("GEMINI_API_KEY not set")
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
            b64 = base64.standard_b64encode(Path(image_path).read_bytes()).decode()
            response = requests.post(
                _GEMINI_ENDPOINT,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
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
            "caption": str(data.get("caption", "")),
            "model": model,
        }


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
