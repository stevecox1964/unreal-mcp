# Work packages — architect specs for executor sessions

These specs are written by an architect session (Fable) so that executor sessions
(Opus / Sonnet) can build them **without making design decisions**. Every design
call is already made in the spec; if you (the executor) hit a decision the spec
doesn't cover, **stop and log it** in the spec's "Executor notes" section — do not
guess.

## Executor contract (read first, every session)

1. **Preflight:** clean tree, on an `auto-loop/*` branch (never `main`),
   `python scripts/run_tests.py` green before you start. (Same contract as
   `plan/autonomous_loop.md`; `Python/scripts/loop/preflight.py` checks this.)
2. **Order:** do the packages in the order listed below. Respect each spec's
   **Gate** line — a gated spec must not be built until the user has approved it
   in a session.
3. **Per-package cycle:** failing test first → implement exactly what the spec
   says → `python scripts/run_tests.py` green → commit (one package = one or few
   commits, message prefixed with the WP id) → tick the checkboxes in the spec →
   update `plan/backlog.md`'s matching item.
4. **Never push.** Work piles up on the branch for human review.
5. **Never touch:** C++, Blueprints/UMG, `.env`, anything needing PIE or the
   editor. Tests are the offline stub suite under `Python/scripts/agent_runtime/`
   (plain scripts with a `check()` helper — copy the style of an existing
   `test_*.py`, no pytest).
6. **Stop conditions:** tests can't be made green in ~2 attempts; the spec
   contradicts the code you find; anything requires a decision not in the spec.
   Write what you found in "Executor notes" and stop the package (move to the
   next non-blocked one).

## Packages (historical execution order)

| # | File | Item | Status | Gate |
|---|------|------|--------|------|
| WP1 | [WP1-recall-context.md](WP1-recall-context.md) | prompt renders acquaintances / known places / episodes | **DONE 2026-07-01** | live behavior covered by later runs |
| WP2 | [WP2-reaction-gate.md](WP2-reaction-gate.md) | #10.5 balanced reaction gate (offline slice) | **DONE 2026-07-01** | live-tuned and verified 2026-07-01 |
| WP3 | [WP3-sweep-capability.md](WP3-sweep-capability.md) | A4/#11.1 collapse maintenance role → sweep capability | **DONE 2026-07-01** | focused PIE sweep verify remains |
| WP4 | [WP4-owned-places.md](WP4-owned-places.md) | A5/#11.2 owned place cells + grid-first resolve | **DONE 2026-07-01** | user approved before build |
| WP5 | [WP5-apc-topdown-map.md](WP5-apc-topdown-map.md) | #6b APC top-down map | **DONE 2026-07-01** | PIE attachment verify remains |
| WP6 | [WP6-authored-places-manifest.md](WP6-authored-places-manifest.md) | #15 authored places manifest + `source` tagging | **DONE 2026-07-07** | none |
| WP7 | [WP7-sync-world-button.md](WP7-sync-world-button.md) | #21 v1 "sync the world" button (purge wake seeds) | **DONE 2026-07-07** | none |
| WP8 | [WP8-grid-first-routing.md](WP8-grid-first-routing.md) | #17 grid-first routing (multi-leg travel) | **DONE 2026-07-07** | none |
| WP9 | [WP9-generic-apc-interruptions.md](WP9-generic-apc-interruptions.md) | #38 generic APC interruption lifecycle | **DONE 2026-07-17 — 49/49** | user approved recommended v1 |

| WP10 | [WP10-direct-apc-chat.md](WP10-direct-apc-chat.md) | #37 direct APC chat + temporary guidance | **OFFLINE MVP 2026-07-21 — 50/50** | user approved stuck-rescue use case |

## Why these five existed

The loop-safe queue had been drained, so this architect pass converted five ambiguous
items into executor-ready packages. All five were subsequently approved where required
and built on 2026-07-01. This table is retained as execution history; current priority
lives in `plan/backlog.md`.

Line numbers in the specs are as of `6a75e20` and will drift — trust the
function names over the numbers.
