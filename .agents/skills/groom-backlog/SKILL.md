---
name: groom-backlog
description: Reconcile, deduplicate, classify, and prioritize this project's backlog against handoffs, specs, code, tests, and recent commits. Use when the user says "groom backlog", "clean up the backlog", "what should we do next", "prioritize the backlog", or invokes $groom-backlog.
---

# Groom Backlog

Groom planning state only; do not implement product code.

1. Read `AGENTS.md`, `plan/backlog.md`, `plan/handoffs/LATEST.md` and its target, `plan/specs/README.md`, `git status`, and recent commits.
2. Reconcile claims against evidence:
   - completed and verified;
   - built offline but awaiting live verification;
   - in progress;
   - blocked on user/editor/PIE/C++;
   - superseded or duplicate;
   - ready and loop-safe.
3. Merge duplicate items by retaining the best canonical section and leaving a short cross-reference where history would otherwise become confusing.
4. Keep a small active view near the top:
   - **Now:** one highest-value executable item;
   - **Next:** up to three ordered follow-ups;
   - **Waiting:** user/editor/live decisions;
   - **Loop-safe:** offline items suitable for `$autonomous-loop`.
5. Move completed detail out of active queues without erasing useful history. Prefer links to specs, commits, and handoffs over repeating long narratives.
6. Do not silently make product decisions. Mark unresolved choices and state what evidence or user answer would unblock them.
7. Preserve item numbers whenever possible. Update status dates and test counts only from verified evidence.
8. Finish with a short grooming report: items merged, reclassified, promoted, blocked, and the recommended `Now` item.
