---
name: create-handoff
description: Save a precise project session handoff for another AI or a fresh session. Use when the user says "create handoff", "create hand off", "save the session", "save context", "I'm stopping", or invokes $create-handoff.
---

# Create Handoff

Create a session snapshot, not a second roadmap.

1. From the repository root, gather in parallel:
   - `git status --short --branch`
   - `git diff --stat HEAD`
   - `git log --oneline -10`
   - existing `plan/handoffs/HANDOFF_*.md`
   - the relevant sections of `plan/backlog.md`
2. Use local time for `plan/handoffs/HANDOFF_<YYYY-MM-DD_HHMM>.md` and link the prior handoff.
3. Write these sections with concrete session facts:

```markdown
# Handoff — <outcome-oriented title>

**Date:** <local date and time>
**Branch:** <branch>
**Prior handoff:** <relative link or none>

## TL;DR
## What was done this session
## In flight
## Decisions locked in this session
## Open questions
## Relevant backlog items
## Next concrete step
## Files touched this session
## How to resume
## Git state at handoff
```

4. Make `Next concrete step` one immediately executable action, not a list.
5. Update `plan/handoffs/LATEST.md` to point to the new file.
6. Do not rewrite old handoffs, invent work, duplicate the full backlog, commit, or push.
7. Confirm the saved path and give the resume phrase: `Read hand off.`

If the backlog is stale because of completed session work, update it first or explicitly record the mismatch in the handoff.
