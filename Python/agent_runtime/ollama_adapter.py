from __future__ import annotations

import base64
import logging
import os
import re
import threading
import time
from pathlib import Path

logger = logging.getLogger("AgentRuntime")

# qwen3.5 is a thinking model; even with thinking disabled a stray <think> block
# can slip into the content and corrupt the short JSON both callers parse.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# Models whose cold load into VRAM we've already announced this process.
_loaded_models: set[str] = set()

# Model-load PIE lines are queued here from worker threads — perception/decision
# run in parallel (phase 2) but the Unreal socket is single-threaded, so the sim
# loop drains these to the overlay from its sequential phase via take_pending_pie().
_pie_lock = threading.Lock()
_pending_pie: list[str] = []


def host() -> str:
    """Base URL of the local Ollama server (no trailing slash)."""
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def strip_think(raw: str) -> str:
    return _THINK_RE.sub("", raw or "").strip()


def _queue_pie(message: str) -> None:
    with _pie_lock:
        _pending_pie.append(message)


def take_pending_pie() -> list[str]:
    """Drain queued model-load PIE lines. Call only from the sim's sequential phase."""
    with _pie_lock:
        msgs = _pending_pie[:]
        _pending_pie.clear()
    return msgs


def _keep_alive():
    """How long Ollama keeps the model resident after a call. Default ``-1`` =
    stay loaded for the whole run, so sparse ticks don't trigger reloads. Override
    with ``OLLAMA_KEEP_ALIVE`` (seconds, or a duration string like ``30m``)."""
    value = os.environ.get("OLLAMA_KEEP_ALIVE", "-1")
    try:
        return int(value)
    except ValueError:
        return value


def chat(
    model: str,
    system: str,
    user: str,
    image_path: str | None = None,
    json_mode: bool = True,
    timeout: int = 120,
) -> str:
    """Single-turn chat against a local Ollama model; returns the assistant text.

    One adapter serves both the decision LLM and the vision perceiver: a
    ``qwen3.5:4b`` (multimodal) model answers text-only decision prompts and,
    when ``image_path`` is given, reads the screenshot too. Uses Ollama's native
    ``/api/chat`` so thinking can be turned off (``think=False``) and JSON output
    enforced (``format="json"``) — the OpenAI-compat endpoint exposes neither
    cleanly. Thinking blocks are stripped defensively. Raises on HTTP error.

    Example::

        chat("qwen3.5:4b", "You are an NPC.", "What do you do?")
        chat("qwen3.5:4b", "", "Describe this scene as JSON.",
             image_path="obs.png", timeout=180)
    """
    import requests

    message: dict = {"role": "user", "content": user}
    if image_path:
        b64 = base64.standard_b64encode(Path(image_path).read_bytes()).decode()
        message["images"] = [b64]

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append(message)

    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": _keep_alive(),  # keep qwen resident for the whole run
    }
    if json_mode:
        payload["format"] = "json"

    cold = model not in _loaded_models
    if cold:
        logger.info("%s: model load start", model)

    t0 = time.monotonic()
    response = requests.post(f"{host()}/api/chat", json=payload, timeout=timeout)
    elapsed = time.monotonic() - t0
    if response.status_code >= 400:
        raise RuntimeError(f"Ollama {response.status_code}: {response.text[:300]}")

    body = response.json()
    # Ollama reports the load portion of this call (ns); large => a real (re)load.
    # With keep_alive=-1 this should fire once (cold) and then effectively never.
    load_s = (body.get("load_duration") or 0) / 1e9
    if cold or load_s >= 1.0:
        _loaded_models.add(model)
        verb = "model LOADED" if cold else "model RELOADED"
        msg = f"{model}: {verb} in {elapsed:.1f}s (load {load_s:.1f}s)"
        logger.info(msg)
        _queue_pie(msg)  # drained to PIE by the sim loop's sequential phase

    content = body.get("message", {}).get("content", "")
    return strip_think(content)
