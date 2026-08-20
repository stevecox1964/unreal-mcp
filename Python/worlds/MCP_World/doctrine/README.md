# Doctrine — rules every APC in this world shares

These files are pulled into an agent's `rules.md` with an import line:

```
@import doctrine/ground.md
```

The import is resolved when the agent loads (`agent_runtime/agent.py`). It is a
literal text include: no templating, no conditionals, no nesting. A doctrine file
that itself contains `@import` is rejected loudly, and so is an import that names
a file that does not exist — a typo must stop the run, never quietly produce an
APC that knows less than it should.

## The rule for deciding where a line goes

**If the rule would be true for any body with legs, it is doctrine.
If it is only true because of who this character is, it is character.**

Locomotion is physics and belongs here. Social posture is character and belongs in
`agents/<id>/rules.md` — that is the direction #64 moved the social clauses, and
this is not a reversal of it.

## Precedence

Imports are resolved in place, and an agent's own lines are written *after* its
imports. Later text wins: **a character may override doctrine**, and when the
files disagree the character's line is the one that stands. Overriding is a real
choice, so make it visible — say in the character line that it replaces doctrine.

## Why this exists

Before 2026-08-20 every navigation lesson learned in a live run was typed into
`dufus/rules.md`. It reached 94 lines while `maren/rules.md` stayed at 21. In SR46
Maren reasoned *"time to refuse this ground"* and then could not, because nothing
in her file said `refuse_cell` existed. Doctrine that is true for every body was
being stored per character. See backlog #85.

## The files

| File | Holds |
|---|---|
| `basics.md` | how to answer at all — output shape, honesty |
| `ground.md` | what ground you may walk on, and how to rule ground out |
| `movement.md` | how to get out of somewhere you should not be |
| `obstacles.md` | things that occupy space in front of you |
| `survey.md` | how to survey — for surveyors only, not every APC |
