# WP10 — Direct APC chat and temporary guidance (#37)

**Gate:** User approved implementation 2026-07-21 for the concrete rescue case: “I want to be able
to guide Dufus via chat if he gets stuck.”

**Status:** Offline MVP complete 2026-07-21; full suite 50/50. Live PIE/model verification pending.

## Locked MVP contract

1. Chat lives in the Simulation cockpit and works for any loaded APC; Dufus is selected by default.
2. The operator supplies an explicit in-world name. No player identity is hardcoded.
3. Opening chat creates a priority-200 `operator_chat` through #38 and immediately stops movement
   when the chat receives active attention. A non-preemptible survey may make it wait in the queue.
4. While chat is open, automatic and manual APC ticks cannot move or independently decide for that
   APC. Other APCs continue normally.
5. Messages receive concise in-character plain-text replies grounded in character, goals, rules,
   relevant memories, and the interruption's captured resume context.
6. The transcript persists inside the interruption payload (up to 50 turns). The terminal
   `last_interrupt` retains it until a later terminal interruption replaces that slot. A permanent
   transcript/memory archive remains part of #12.2's future schema decision.
7. **Guide with this** converts the open chat into `operator_direction`. The direction is grounded in
   the normal action prompt and outranks routine work, but does not overwrite the prior goal,
   schedule, or cached route.
8. **Resume prior work** resolves either chat or guidance. Normal sequencing resumes the captured
   prior work. Permanent goal insertion/reprioritization remains #36.
9. Restart day and Reset agents inherit #38's existing policy and clear chat/guidance runtime.

## Offline acceptance evidence

- `test_direct_chat.py` proves movement freeze, cognition suppression, multi-turn persistence,
  grounded temporary guidance, and exact prior-goal preservation/resume.
- `test_runner_api.py` proves runner routes and client methods for start/message/guide/end.
- `test_sim_controller.py` proves cockpit controls and web proxy routes.
- Existing interruption, prompt, pacing/reset, and agent-state suites remain green.
- Full offline suite: **50/50 passed** on 2026-07-21.

## Live verification still required

With Unreal in PIE and the configured decision provider available: open Dufus chat while he is
moving, confirm he physically stops, exchange at least two turns, guide him around a real blocker,
then release him and confirm his prior route/goal resumes. Verify Maren continues unaffected.
