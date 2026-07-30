"""Offline test aggregator — one PASS/FAIL signal for the loop-safe suite.

The autonomous loop (backlog #4) needs a single green/red signal. The
loop-safe tests are the ones under ``scripts/agent_runtime/`` that stub Unreal
entirely (no socket, no editor, no network).

Each test file is a standalone script that ``sys.exit(1)`` on failure, so we
run each as a subprocess and treat a non-zero exit (or timeout) as FAIL.

Run:
    .venv\\Scripts\\python.exe scripts\\run_tests.py
    .venv\\Scripts\\python.exe scripts\\run_tests.py --only test_place_resolver
    .venv\\Scripts\\python.exe scripts\\run_tests.py --only "test_world*"

Exit code is 0 only when every discovered test passes.
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
import time
from pathlib import Path

PY_ROOT = Path(__file__).resolve().parents[1]          # Python/
OFFLINE_DIR = PY_ROOT / "scripts" / "agent_runtime"    # the loop-safe, Unreal-stubbed suite
PER_TEST_TIMEOUT = 120                                  # seconds; a hung test is a FAIL


def discover(only: str | None) -> list[Path]:
    tests = sorted(OFFLINE_DIR.glob("test_*.py"))
    if only:
        pat = only if any(c in only for c in "*?[") else f"*{only}*"
        tests = [t for t in tests if fnmatch.fnmatch(t.stem, pat)]
    return tests


def run_one(test: Path) -> tuple[bool, float, str]:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(test)],
            cwd=str(PY_ROOT),
            capture_output=True,
            text=True,
            timeout=PER_TEST_TIMEOUT,
        )
        ok = proc.returncode == 0
        out = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        ok, out = False, f"TIMEOUT after {PER_TEST_TIMEOUT}s\n{e.output or ''}"
    return ok, time.monotonic() - start, out


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the offline (Unreal-stubbed) test suite.")
    ap.add_argument("--only", help="glob/substring to filter test filenames (e.g. test_place_resolver)")
    ap.add_argument("-v", "--verbose", action="store_true", help="print each test's output")
    args = ap.parse_args()

    tests = discover(args.only)
    if not tests:
        print(f"No tests matched (dir={OFFLINE_DIR}, only={args.only!r}).")
        return 1

    failures: list[tuple[Path, str]] = []
    for test in tests:
        ok, secs, out = run_one(test)
        rel = test.relative_to(PY_ROOT)
        print(f"{'PASS' if ok else 'FAIL'}  {rel}  ({secs:.1f}s)")
        if args.verbose or not ok:
            tail = "\n".join(out.strip().splitlines()[-15:])
            if tail:
                print("    " + tail.replace("\n", "\n    "))
        if not ok:
            failures.append((rel, out))

    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed.")
    if failures:
        print("FAILED: " + ", ".join(str(r) for r, _ in failures))
        return 1
    print("All offline tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
