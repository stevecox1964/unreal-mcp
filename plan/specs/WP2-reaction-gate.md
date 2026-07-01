# WP2 — Balanced reaction gate (#10.5, offline slice)

**Item:** backlog #10.5 · **Decision locked (user, 2026-07-01):** BALANCED gate —
the routine destination wins by default; only a **known friend** or **being
spoken to** may interrupt; after the interrupt the agent **resumes** the
scheduled destination. Persona distractibility is a low-weight nudge, never an
override.
**Gate:** the offline slice below is hands-off. The *tune-and-verify* half is
**B3** (PIE: confirm Dufus reaches the village square) — not this WP.
**Depends on:** WP1 (the prompt must show "People You Know" before "a known
friend" can mean anything). **Blocks:** nothing.

## Where the problem lives (verified 2026-07-01)

`Python/agent_runtime/llm_router.py`:

1. `_USER_TEMPLATE_VISION` (~line 84) currently says:
   > "A CHARACTER sighting matching one of the known characters above is that
   > person — consider greeting or approaching them."

   That is an unconditional pull toward every passer-by — exactly the observed
   failure (agent greets everyone, never arrives).

2. The exploration paragraph (~line 88, "If nothing in view needs your
   attention, keep exploring…") competes with a travel directive: while the
   routine says "head to the village square", the template still invites
   detours to unexplored cells.

3. `_schedule_note` (~line 616) renders the travel directive as a suggestion
   with no stated priority.

The schema is untouched — this is prompt weighting only, which is why the
offline slice is string-level and the real verification is live (B3).

## Change (all in `llm_router.py`)

### 1. Replace the reaction sentence with a priorities block

In `_USER_TEMPLATE_VISION`, replace the paragraph that begins
`Anything listed under "You See" is really there.` (through the end of that
sentence about greeting/approaching) with:

```
Anything listed under "You See" is really there. A CHARACTER sighting matching
a name under "People You Know" is someone you have met before; one matching
"Characters You May Encounter" is that person.

## What Wins Right Now
Your routine (see "Your Routine Right Now") is your default. When it says to
head somewhere, your action this tick should move you there. Do NOT stop for
strangers, scenery, or cells you could explore — those can wait.
Exactly two things justify pausing your routine:
1. You see someone listed under "People You Know" — you may greet them briefly.
2. Someone is speaking to you — respond.
After such a pause, your next action goes back to the scheduled destination.
Staying in character is good, but character quirks (curiosity, distraction)
color HOW you travel — they do not cancel WHERE you are going.
```

### 2. Make the exploration paragraph conditional

Change the paragraph starting `If nothing in view needs your attention, keep
exploring:` to start with:

```
If nothing is scheduled right now and nothing in view needs your attention,
keep exploring: ...
```
(rest of the paragraph unchanged).

### 3. Strengthen the travel directive in `_schedule_note`

In the `status == "travel"` branch, change the returned string to:

```python
return (f"{intent}\nThis is your priority right now: use walk_to with "
        f"target_location \"{directive['place']}\" and keep going until you "
        f"arrive. Only a person you know or someone speaking to you is worth "
        f"a brief pause.")
```

Leave the `idle` and `act` branches unchanged.

## Tests

Extend/create `Python/scripts/agent_runtime/test_prompt_context.py` (from WP1;
same `check()` style):

1. `_USER_TEMPLATE_VISION` contains `## What Wins Right Now`, contains
   `Do NOT stop for strangers`, and no longer contains
   `consider greeting or approaching them`.
2. Exploration paragraph is gated: template contains
   `If nothing is scheduled right now and nothing in view`.
3. `_schedule_note({"status": "travel", "place": "village square", "intent": "It's time to sell — head to village square."})`
   returns a string containing `This is your priority right now` and
   `target_location "village square"`.
4. `_schedule_note({"status": "act", ...})` and `_schedule_note(None)` outputs are
   unchanged from today (pin them: "You are where you should be" / "nothing fixed
   right now").

These are contract-pinning tests (string presence). They cannot prove the tune
works — that is B3 (live PIE). Say so in the commit message.

## Acceptance

- [ ] `python scripts/run_tests.py` green.
- [ ] Only `llm_router.py` + the test file changed.
- [ ] `plan/backlog.md` #10.5: check the offline slice, leave the live-tune line
      open, pointing at B3.

## Deliberately out of scope

- Any Python-side gating/filtering of decisions (the LLM stays the decider —
  the gate is prompt weight, per the Master Plan §14 framing).
- Detecting "being spoken to" as a structured signal (the bridge does not report
  incoming speech today; the prompt phrasing covers it via "You See"/memories).
  If live tuning shows this matters, it becomes its own backlog item.
- The navmesh `stuck` wedge robustness item (separate, live).

## Executor notes

*(append findings/deviations here)*
