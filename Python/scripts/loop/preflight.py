"""Autonomous-loop preflight gate (backlog #4.2).

Refuses to start the loop unless it is safe to: the working tree is clean, we're
on a dedicated loop branch (never `main`), and the offline baseline is green.
Run before a self-paced /loop session:

    .venv\\Scripts\\python.exe scripts\\loop\\preflight.py

Exit 0 = safe to start; exit 1 = blocked (reasons printed). The decision logic
(is_loop_branch / tree_is_clean / evaluate) is pure so it can be unit-tested;
main() gathers the live git + test state.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PY_ROOT = Path(__file__).resolve().parents[2]      # Python/
_PROTECTED = {"main", "master", ""}


def is_loop_branch(branch: str) -> bool:
    """True if ``branch`` is a dedicated loop branch (not main/master/empty)."""
    return branch.strip() not in _PROTECTED


def tree_is_clean(porcelain: str) -> bool:
    """True if ``git status --porcelain`` output indicates no changes."""
    return porcelain.strip() == ""


def evaluate(branch: str, porcelain: str, tests_ok: bool) -> tuple[bool, list[str]]:
    """Combine the three guards into (ok, problems). Pure — no I/O."""
    problems: list[str] = []
    if not is_loop_branch(branch):
        problems.append(f"on protected branch '{branch}' — switch to a dedicated loop branch")
    if not tree_is_clean(porcelain):
        problems.append("working tree is not clean — commit or stash first")
    if not tests_ok:
        problems.append("baseline tests are failing — green the suite before looping")
    return (not problems, problems)


# ── Live state gathering (not unit-tested; thin wrappers over git/tests) ─────────

def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(PY_ROOT.parent),
                          capture_output=True, text=True).stdout


def _current_branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD").strip()


def _porcelain() -> str:
    return _git("status", "--porcelain")


def _baseline_green() -> bool:
    proc = subprocess.run([sys.executable, str(PY_ROOT / "scripts" / "run_tests.py")],
                          cwd=str(PY_ROOT), capture_output=True, text=True)
    return proc.returncode == 0


def main() -> int:
    branch = _current_branch()
    ok, problems = evaluate(branch, _porcelain(), _baseline_green())
    if ok:
        print(f"preflight OK — branch '{branch}', clean tree, baseline green. Safe to loop.")
        return 0
    print("preflight BLOCKED:")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
