# Autonomous loop — run contract

The contract the self-paced coding loop (backlog #4) reads at the start of each
session. Goal: work the backlog unattended — build, test, commit on green —
until usage limits stop the session, then resume next session from the handoff.

## Allowed surface (loop-safe)

- **Python only**, under `Python/agent_runtime/**` and `Python/scripts/**`.
- Work that is **verifiable by an offline test** — the `scripts/agent_runtime/`
  suite stubs Unreal entirely (no socket, no editor, no network, no LLM call).
- Planning/docs under `plan/**`.

## Hard NOs (never, unattended)

- **Never `git push`** and never auto-merge to `main`. Human reviews the branch.
- **Never** edit C++ (`MCPGameProject/**`, `*.cpp/*.h`), Blueprints, or UMG.
- **Never** edit `.env` or touch secrets/provider config.
- **Never** start the sim, need PIE, or run the socket-based
  `scripts/{actors,node,blueprints}` tests (they require a live editor).
- **Never** make an LLM/vision API call from loop code (burns credits — the
  whole point is to *not* spend them; the build/test loop itself makes no calls).

## Stop / skip conditions

- **Skip + log** (don't guess) anything needing: the editor, a C++ rebuild, a
  design decision (e.g. which mesh, UX layout), or live-sim verification. Record
  it in the backlog under the item so the human can pick it up.
- **Stop the item** if its tests fail and can't be fixed in ~2 tries; leave it
  red-but-isolated on its own branch, note it, move to the next item.
- **Stay on a dedicated branch** (`auto-loop/*`), never `main`.

## Per-item cycle

1. Pick the next loop-safe backlog item (prefer self-contained, testable).
2. Write a **failing** offline test first (`scripts/agent_runtime/test_*.py`).
3. Implement the minimum code to pass it.
4. `python scripts/run_tests.py` — the whole offline suite must be green.
5. **Commit** on green (never push). Check off the backlog item.
6. Keep `plan/handoffs/LATEST.md` current so the loop is resumable when limits hit.

## Signals

- One green/red signal: `Python/scripts/run_tests.py` (`--only <glob>` for the
  in-progress test). Preflight (clean tree, on a loop branch, baseline green) is
  `Python/scripts/loop/preflight.py` when present.
- Recoverability = `plan/handoffs/LATEST.md` + `plan/backlog.md`, both kept
  current as the loop runs.

## Loop-safe backlog targets (today)

Good: #1 place nav (done), #5 episodic/social memory (data layer), #6 map query
surface, #3 runner scaffolding + control API (offline), #2 `config_store.py`.
Blocked (needs human/editor): Child Blueprints, #2 settings UI verification,
live-sim runs, anything C++/UMG.
