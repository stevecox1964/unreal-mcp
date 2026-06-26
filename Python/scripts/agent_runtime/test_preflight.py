"""Offline tests for the autonomous-loop preflight check (backlog #4.2).

Preflight refuses to start the loop unless the tree is clean, we're on a
dedicated loop branch (not main), and the baseline suite is green. The decision
logic is pure (string in -> verdict out); git/test gathering lives in main().
No Unreal, no network. Run:
    .venv\\Scripts\\python.exe scripts\\agent_runtime\\test_preflight.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # Python/
sys.path.insert(0, str(ROOT / "scripts" / "loop"))

import preflight  # noqa: E402


def check(label, cond):
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def test_branch_guard():
    check("main is not a loop branch", not preflight.is_loop_branch("main"))
    check("master is not a loop branch", not preflight.is_loop_branch("master"))
    check("empty branch rejected", not preflight.is_loop_branch(""))
    check("auto-loop branch accepted", preflight.is_loop_branch("auto-loop/backlog"))


def test_tree_guard():
    check("empty porcelain is clean", preflight.tree_is_clean(""))
    check("whitespace-only is clean", preflight.tree_is_clean("   \n"))
    check("modified file is dirty", not preflight.tree_is_clean(" M Python/x.py"))


def test_verdict_combines_all():
    ok, problems = preflight.evaluate(branch="auto-loop/backlog", porcelain="", tests_ok=True)
    check("all-good passes", ok and problems == [])

    ok, problems = preflight.evaluate(branch="main", porcelain=" M f.py", tests_ok=False)
    check("all-bad fails", not ok)
    check("reports the branch problem", any("branch" in p.lower() for p in problems))
    check("reports the dirty-tree problem", any("clean" in p.lower() or "dirty" in p.lower() for p in problems))
    check("reports the failing-tests problem", any("test" in p.lower() for p in problems))

    ok, problems = preflight.evaluate(branch="auto-loop/x", porcelain="", tests_ok=False)
    check("one failure is enough to block", not ok and len(problems) == 1)


def main():
    test_branch_guard()
    test_tree_guard()
    test_verdict_combines_all()
    print("\nAll preflight checks passed.")


if __name__ == "__main__":
    main()
