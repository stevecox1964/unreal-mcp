"""Offline packaging contract for RunnerClient's direct HTTP dependency (#30)."""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime.runner_client import RunnerClient  # noqa: E402


def check(label: str, condition: bool) -> None:
    if not condition:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def main() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    check("httpx is a direct runtime dependency",
          any(dep.split("[", 1)[0].split("<", 1)[0].split(">", 1)[0]
              .split("=", 1)[0].strip().lower() == "httpx" for dep in dependencies))

    client = RunnerClient()
    try:
        check("RunnerClient constructs its default HTTP client",
              client._client.__class__.__module__.startswith("httpx"))
    finally:
        client._client.close()

    print("\nAll RunnerClient dependency checks passed.")


if __name__ == "__main__":
    main()
