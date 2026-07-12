---
name: autonomous-loop
description: Work through approved loop-safe backlog items autonomously using test-first, reviewable commits on a dedicated branch. Use when the user says "run the autonomous loop", "continue autonomous work", "grind the backlog", "work the safe queue", or invokes $autonomous-loop.
---

# Autonomous Loop

Read `plan/autonomous_loop.md` completely and follow it as the run contract.

At the start, use the `$read-handoff` procedure internally, then read the active backlog view and the applicable spec. Do not pause merely to repeat the handoff unless it exposes a conflict or required user decision.

For each approved loop-safe item:

1. Preflight a clean baseline on an `auto-loop/*` branch.
2. Add a failing offline test that expresses the acceptance behavior.
3. Implement the smallest coherent change.
4. Run the focused test, then `Python/scripts/run_tests.py`.
5. Update the backlog with verified status and remaining live verification.
6. Commit the green slice. Never push or merge.
7. Continue only while another approved loop-safe item exists.

At a stop condition, leave the tree understandable, update the backlog, and use the `$create-handoff` procedure. Never start PIE, call paid models, edit secrets, or treat offline success as live verification.
