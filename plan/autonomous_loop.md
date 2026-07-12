# Autonomous loop — Codex run contract

The autonomous loop converts approved, offline-testable backlog work into small green commits. It does not choose product direction, operate Unreal, or replace the user's review.

## Durable project workflow

The four planning actions have separate jobs:

1. **Read hand off** — recover the latest session state and compare it with the current repository.
2. **Create handoff** — save the session outcome, locked decisions, open questions, and one resume step.
3. **Add item to back log** — capture new scope without implementing it or silently prioritizing it.
4. **Groom backlog** — reconcile evidence, remove duplication, classify work, and choose the active order.

`plan/backlog.md` is the canonical roadmap. `plan/handoffs/*` are chronological session snapshots. When they disagree, investigate the repository and newer evidence rather than silently choosing one.

## Entry contract

1. Read `AGENTS.md`.
2. Follow the `read-handoff` skill.
3. Read the backlog's active view, the selected item, and any linked spec.
4. Inspect `git status --short --branch` and recent commits.
5. Require a clean baseline and a dedicated `auto-loop/*` branch. Do not discard user changes to obtain one.
6. Run `Python/.venv/Scripts/python.exe Python/scripts/loop/preflight.py` from the repository root when available. Otherwise run the complete offline suite manually.

If the baseline is red, the tree contains unexplained changes, or the selected item is not approved and loop-safe, stop and report the evidence.

## Allowed work

- `Python/agent_runtime/**`
- `Python/scripts/**`
- Python web UI work that is fully exercised offline
- `plan/**` and relevant project-local skill instructions
- Work with deterministic offline acceptance evidence

## Prohibited unattended work

- C++, Blueprints, UMG, Unreal assets, or editor automation
- PIE or socket-based live tests
- Paid LLM or vision calls
- `.env`, credentials, provider keys, or user runtime data
- Pushes, merges, releases, or changes directly on `main`
- Product decisions not already approved by the user or locked in a spec

## Per-item loop

1. Select the first approved `loop-safe` item from the groomed active queue.
2. Restate its acceptance behavior in the working notes.
3. Write or extend an offline test and confirm it fails for the intended reason.
4. Implement the minimum coherent behavior.
5. Run the focused test until green.
6. Run the entire offline suite with `Python/scripts/run_tests.py`.
7. Review the diff for scope creep, state-file churn, secrets, and accidental engine coupling.
8. Update the backlog with what is proven, the test signal, and any remaining live verification.
9. Commit the green slice with an outcome-oriented message. Never push.
10. Repeat only if another approved loop-safe item is ready.

## Stop conditions

Stop the current item when:

- it needs PIE, C++, an engine asset, a paid model call, or a user decision;
- the spec contradicts current code or omits a material design choice;
- the same failing approach has not converged after two focused correction attempts;
- the full offline suite cannot be returned to green without expanding scope;
- the worktree or branch state becomes ambiguous.

Record the blocker in the backlog. Keep an isolated failing test only when it clearly documents the missing behavior and does not leave the suite or branch misleadingly broken.

## Completion and handoff

Before stopping:

1. Verify `git status` and record whether the tree is clean.
2. Update the active backlog view and selected item from evidence only.
3. Create a handoff using the project `create-handoff` skill.
4. Make the next concrete step immediately executable.

A handoff is required at the end of an autonomous run, but not after every commit. The backlog remains the durable scope authority between runs.
