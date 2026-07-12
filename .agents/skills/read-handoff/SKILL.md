---
name: read-handoff
description: Load and summarize this project's latest session handoff. Use when the user says "read hand off", "read handoff", "resume the handoff", "where did we leave off", or invokes $read-handoff.
---

# Read Handoff

1. Resolve the repository root with `git rev-parse --show-toplevel`.
2. Read `plan/handoffs/LATEST.md`, then read the handoff it links to. If either is missing, list `plan/handoffs/HANDOFF_*.md` newest first and use the newest only after telling the user.
3. Read `plan/backlog.md` only around items named by the handoff. Treat the backlog as current scope and the handoff as session state. If they conflict, report the conflict; prefer newer dated evidence and direct user decisions.
4. Inspect `git status --short --branch` and the five most recent commits. Note any drift from the recorded handoff state.
5. Return a compact resume brief:
   - current branch and worktree state;
   - last completed outcome;
   - locked decisions;
   - in-flight work and blockers;
   - relevant backlog item;
   - one next concrete step.
6. Do not edit files, run the sim, or begin implementation. Wait for the user's direction.

Never replay every historical handoff unless the latest one explicitly requires older context.
