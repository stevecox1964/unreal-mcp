# Backlog

Rolling list of outstanding work — add items as they come up, check off or
delete them as they land. Not session-scoped; this is the durable home for
approved scope and priority. Handoffs are chronological session state.
Newest grooming: **2026-08-20** — see *THE EXIT CONDITION* below; Phase B is blocked.

## Active view — groomed 2026-08-19

### Direction reset (#62–#72): get the town out of the corn field — see "Now" below for 2026-08-19 priority

**This supersedes the survey-navigation queue as the active priority.** Full analysis and all eleven
item write-ups are under *"Direction reset 2026-08-12"* below; the short version:

Maren was parked on 2026-07-30 *"until Dufus reliably does his one job"* — a condition with **no pass
criterion**, so it never opens, so six weeks of work could only ever be Dufus navigation. Meanwhile
MASTER_PLAN §0.2's success criteria all need 2–3 agents, Dufus has **already surveyed the places Maren's
authored day needs** (5 of her 7 agenda tasks resolve against `world_places.db` today, lunch at Don's
Donuts included), and the entire social substrate — earshot speech, recognition, social memory,
episodic recall — is **built and has never been switched on**.

**Phase A is BUILT and offline-green at 57/57 (2026-08-12) — and entirely unverified live.** The next
concrete step is one run with both APCs, graded on Maren's day rather than Dufus's footing:

1. **#62** wake Maren — `is_active: true`, no other change. ✅ built
2. **#63** an unresolvable agenda place fails loud *before* the run. ✅ built; both live misses closed
   (`"Sheriff's office"` → nothing, now repointed; `"home"` → the mobile-home community, survives only
   on authored precedence — the real fix is #71).
3. **#64** suppressive social clauses moved out of the shared prompt into each agent's `rules.md`. ✅
   built; two more copies of the doctrine were found hard-coded in `_schedule_note` and fixed too.
4. **#65** the wedge budget — **built as an escalating fact, not a recovery override.** See the item for
   why the scope changed; the short version is that a sixth code-over-LLM override contradicts
   [[feedback_facts_not_blocking]] and would pre-empt #60's live verification.

Then Phase B (**#66** reaction gate, **#67** APC↔APC conversation, **#68** work that leaves a mark),
Phase C (**#69** memory stream, **#70** reflection), Phase D (**#71** usable place names, **#72** the
survey gets a customer).

The carried live check from the SR40 handoff — does a `blocker` line ever appear, which gates #61 —
rides along on that same run.

**SR41 (2026-08-12) ran it.** 48 ticks, both APCs, zero errors. Locomotion was the cleanest yet — four
new cells surveyed, zero `cultivated_field` footings, no `WEDGED:` warning, no `blocker` line (so #61
stays gated). Three defects found, all **BUILT the same session**: **#74** Dufus heard Maren, decided to
answer, and chose `idle` — the reply was never spoken; **#73** the survey has mapped 15 cells of 204 in
a strip 7 wide and 2 tall, because every navigation fact it had was one cell wide; and **#75** Maren's
truck sits astride a cell boundary and was recorded as two owned rows 134 cm apart, so her prompt
listed it twice and the resolver named a cell she was not standing in. Maren's day is still untested
past 09:17 sim time.

### THE EXIT CONDITION (user, 2026-08-20) — Phase B is BLOCKED until the survey is a product

**Source:** user, 2026-08-20: *"I don't think we are out of the woods yet with regards to getting
Dufus to survey correctly. He is getting better. This perception behavior will be used by other APCs
that don't 'survey' but consume the same locomotion/nav logic. When Dufus can run a survey over night
and fill the world up with grid/place data that other APCs can just use, and where we can get a VLM
built out of all this data, then we are done."*

This replaces the old, softer exit condition ("the lane's exit condition is met once SR45 is clean").
SR45 being clean is **not** the finish line — it was one bug-fix confirmation. The finish line is
three things, all measurable:

1. **Unattended overnight survey.** Dufus runs a multi-hour survey with nobody watching: no wedge that
   ends the run, no repeated ground, no stall, no crash. Measured on a real overnight run, not a
   12-minute SR.
2. **The world fills with reusable grid/place data.** The output is `world_places.db` grid cells and
   place rows that **another APC can consume without surveying anything itself** — coverage that grows
   run over run, not the same strip re-walked.
3. **The corpus is big and clean enough to train a VLM.** `perception_log.jsonl` plus the place images
   are the training set (#79, [[project_dufus_vlm_training_corpus]]). Dense, varied, correctly filed.

**Consequence — Phase B is BLOCKED.** #66 reaction gate, #67 APC↔APC conversation, #68 work that
leaves a mark: all three stay unbuilt until the three criteria above are met. Walking around and
talking is not the next lane. Do not start it, and do not re-argue the ordering from the
2026-08-12 direction reset — the user has re-decided on top of it.

**Why perception/locomotion is not "Dufus work".** The perception and navigation behaviour built in
#77/#78/#26/#61 is **shared runtime**, not survey code. Other APCs never survey, but they walk on the
same locomotion and nav logic, so every fix here is a fix for every APC that will ever exist. This is
why the lane is worth grinding past "good enough for Dufus".

**Grading rule for every live run from here:** grade the run on survey throughput and cleanliness —
new cells covered, repeats, stalls, wedges, corpus lines written — **not** on whether something social
happened. The 2026-08-12 reframe (grade on social) is suspended until the exit condition is met.

### Now (groomed 2026-08-19) — perception-guided exploration, bounded, then Phase B

**Source:** user, 2026-08-19: *"concentrate on perception and how Dufus can explore/survey the world
from center of world out... not go into areas that can get him stuck regardless of navmesh saying he
can. Like, I see corn field, I can't go there... vehicles are obstructions and the system needs to keep
Dufus from running into them even though navmesh says area clear. I need the LLM to guide the
navigation more... get beyond back-and-forth surveying and get back to people talking and doing
things."*

That decomposes into exactly three items, two of them new:

- **#76 — center-out exploration.** The survey grows rings outward from the town center, stated as
  facts on top of #73's frontier machinery. New item below.
- **#77 — look before you step.** Terrain the APC can *see* (corn field, water, ploughed ground) vetoes
  a move **before** the step is taken, navmesh notwithstanding — per-direction footing probes as facts
  plus a rules.md clause that the model's own eyes outrank the navmesh. Promotes the #55 follow-on to a
  numbered item. New item below.
- **#61 (existing) — the reflex half covers vehicles.** Props and vehicles occupy space the navmesh
  calls clear; that is the lizard-brain probe's job ("vehicle 183 cm ahead" as a fact, reflex standoff
  at engine cadence), not the VLM's. #61's gate is unchanged: first prove the forward trace hits
  anything at all (`blocker` line has still never been seen live).

**Build slice (spec'd 2026-08-19, Fable — after SR42): BUILT same day, offline 59/59
(`test_look_before_step.py`, 35 checks). Needs live verification (SR43): a pre-emptive
refusal from the eyes' facts, a spot patch surviving to the next run, and the north trap
not re-entered.**

- **#77 look-before-step, concretely.** Two eyes-first facts, both rendered onto the existing
  per-direction lines (`_direction_places` → `_direction_lines`):
  1. Perception (`perception.py`) additionally reports `ground_ahead` (same footing vocabulary +
     `building_interior`) — the ground filling the walkable path in the frame, where the APC would
     stand after a few steps — and `path_ahead` (`open|dead_end|blocked`). SR42's traps (backyard
     pergola, mobile-home bedroom, trash alley) were all *visible* before the step; nothing carried
     that pixel fact to the step decision.
  2. An eyes cache per agent: every perceived view with a known facing (tick view, wake sweep,
     survey sweep) files `ground_ahead`/`path_ahead` under its compass word, valid only while the
     APC stays on the spot (cleared on ~3 m displacement, same idea as `_record_attempt`). The
     direction line for a heading the APC has actually looked down says "your eyes: grass ahead,
     dead end". Facts only; rules.md tells Dufus his eyes outrank the navmesh.
- **#78 sub-cell no-go patches (user, 2026-08-19: "subgrid" idea).** `refuse_cell` today paints a
  whole 30 m cell — right for a cornfield, wrong for one bad backyard in an otherwise surveyable
  cell (SR42's cell 6,4 problem: the cell must stay a survey target while its south approach is
  poisoned). New `no_go_patches` table in PlaceDB: point + radius (default 9 m = place-cell
  extent), reason, refused_by. Surfaced to the model as
  `{"type": "refuse_cell", "direction": "<compass>", "scope": "spot", "reason": ...}` — refuses
  just the patch one step that way; `allow_cell` with `scope: "spot"` withdraws. Patches do NOT
  touch the frontier (the cell stays offered); they only mark the ground on the direction lines:
  "NO-GO ground (refused by dufus: private backyard)". Facts, not blockers — nothing stops a step
  onto a patch.
- **#26 slice — bounce fact (dead-end recognition, facts-only; the full controller stays in #27).**
  `_drop_crumb` already sees every walked leg; two consecutive legs with opposite headings are a
  bounce, counted per trap cell for the run. At ≥2 the prompt states: "you have stepped into cell
  X and straight back out N times this run" with the refuse-the-spot escape named. This is SR32's
  "louder facts" watch item, now a fact.

**#79 — perception dataset recorder (spec'd 2026-08-19, Fable; source: user — "I am thinking
ahead for a VLM and want to build a training dataset"). BUILT same day, offline 60/60
(`test_perception_dataset.py`, 18 checks). Live check (SR43): `perception_log.jsonl` grows in
dufus's observations folder, one line per capture, tick + wake + survey contexts all present.** Dufus's captures are the VLM training
corpus ([[project_dufus_vlm_training_corpus]]), but only the survey pipeline keeps its text: 21
`place_images` rows carry descriptions, while the per-tick stream — 348 PNGs in dufus's
observations folder alone — computes a full VLM label every tick (caption, landmarks, footing,
now `ground_ahead`/`path_ahead`) and throws it away; `last_perception.json` is overwritten each
tick. The recorder makes every perceived frame a training pair at the moment it is perceived:

- One method, `_record_perception_pair`, appends one JSON line per perceived image to
  `agents/<id>/observations/perception_log.jsonl` — the label lives next to the pixels it labels.
- Line: `recorded_at`, `sim_run`, `world_time`, `image` (basename — the pair survives a folder
  move), `context` (`tick|wake|survey_sweep|explore`), `heading` (compass, when the facing is
  known), `at` [x,y], `cell`, `model`, `caption`, `footing`, `ground_ahead`, `path_ahead`,
  `landmarks`, `characters`, and `error` when perception failed (recorded, not hidden — the
  dataset builder filters, per fail-loud).
- Called from all four perceive sites: the tick view, the wake look-around, the survey sweep
  heading, and legacy explore. Append-only, never raises; a write failure warns and degrades the
  tick, exactly like perception itself.
- Out of scope on purpose: dataset packaging/export, dedup, train/val splits — that is a
  build-time job over the JSONL, not a sim-time one.

**#80 — refused ground on the /map (spec'd 2026-08-19; source: user — "update the map UI to show
cells that are off limits, refused and why"). BUILT same day, offline 61/61. Live check (SR43):
after Dufus refuses the corn field, /map shows the red-hatched cell with his reason in the
tooltip and the legend count at 1.** The refusal record exists (#59 cells, #78
patches) and the APCs read it every tick, but the operator cannot see it: a refused cell renders
as plain "unexplored", which visually re-invites exactly the ground someone ruled out.

- `build_map` additionally returns `refusals` (`cell_refusals` rows: col, row, refused_by,
  reason, refused_at) and `no_go` (`no_go_patches` rows: x, y, radius_cm, refused_by, reason),
  plus `counts.refused` (distinct refused cells) and `counts.no_go`.
- `/map` paints a refused cell with a red diagonal hatch — over whatever survey state it also has,
  since refused-after-swept is a real combination — and its tooltip leads with
  `REFUSED by <who>: <reason> (<world time>)`. A no-go patch draws as a red dashed circle of its
  true radius at its true anchor, tooltip likewise. Legend gains both, with the refused count.
- Read-only: the map shows the record; withdrawing a refusal stays the APC's own act
  (`allow_cell`), not a map click.

**This lane is capped on purpose.** #76 and #77 are prompt-and-facts work on machinery that already
exists (#73 frontier, footing probes, `mark_blocked`) — no new navigation subsystem. Once one live run
shows (a) rings instead of a ribbon and (b) at least one *pre-emptive* refusal ("I see corn, going
around") with zero bad-footing entries, exploration goes back to being a background service and **the
headline moves to Phase B — #66 reaction gate, #67 APC↔APC conversation, #68 work that leaves a
mark.** People talking and doing things is the destination; this lane exists so survey defects stop
eating the sessions that should be spent there.

### Also open (survey/navigation line — no longer the headline)

- **SR44 (2026-08-19, 31 ticks, 11 min) — the #77/#78 lane works. Three bugs found, all fixed
  same session; needs SR45 to confirm.**
  - **VERIFIED LIVE:** the wake `refuse_cell` fix (SR43 12:27:02 — Dufus refused cell (5,6),
    "cultivated field, corn growing thick", no "Unknown action"); **#78 spot patches** (8 patch
    refusals with real reasons — pergola yards, fenced lots, mailboxes); **#80 map paint** — user
    saw "a whole cell stripped red plus a few circles". Dufus stayed out of the corn all run.
    Zero LLM errors.
  - **BUG 1 (FIXED): re-refusing the same ground, tick after tick.** Ticks 6-15: Dufus stood in
    the pergola yard at (-9432, -1827) and refused it four times, plus (-8372, -2888) three
    times — 8 ticks burned on already-recorded facts. Cause: a patch only rendered on *step
    targets*, never underfoot, so standing in refused ground was invisible. Fix: `here_no_go`
    observation fact + sense line ("you are STANDING in ground already refused — do NOT refuse
    it again; leave it this tick") + a rules.md clause that ground is refused once.
  - **BUG 2 (FIXED): "things sort of stopped" after a survey.** Ticks 29-31 idle
    (`scene_unchanged`) then the run ended. Cause: a finished survey leaves the APC stationary
    with an unchanged view, so the scene gate slept cognition until the every-Nth-tick
    re-decide. Fix: `_force_next_decide` — a resolved sweep owes exactly one forced cognition
    tick, because finishing a survey IS a decision point.
  - **BUG 3 (FIXED, user call): re-surveying covered ground.** The 24 h staleness window marked
    every July survey eligible again. `SURVEY_STALE_REFRESH = False` in `agent_manager.py`:
    surveyed is surveyed, forever. #39's refresh machinery is kept and still tested under the
    explicit toggle, for the day re-surveying becomes a deliberate act again. `/map` still
    *labels* old surveys stale — display only, no behaviour.
  - **Maren took off walking (user observed).** She spent the run alternating `walk_to vegetable
    truck` / stalled / observe, never settling — the (5,5)-vs-(6,5) truck-row split from #75.
    **Still parked** per user; noted here so SR45 is not misread as a new fault.

### The plan, in order (2026-08-19, after SR44)

1. ~~**SR45 — confirm the three fixes.**~~ **DONE 2026-08-19 (commit `1dc73c5`): 56 ticks,
   0 errors. Patch loop gone (2 refusals, both new ground). Post-survey stall gone (3
   `sweep_done` ticks, each followed by `walk_to`). Re-survey gone (3 surveys, all on cells with
   no composite: 10,5 / 10,4 / 11,5). `perception_log.jsonl` filling — 84 lines.**
2. ~~**#61 forward blocker trace**~~ **reflex half BUILT 2026-08-20 (offline 61/61), and
   immediately superseded in scope by #81.** The gate is cleared: SR45's log proves the trace hits
   (42 hits in one run). It also proved 15 of them were classified and thrown away — see #61 for
   both fixes. **SR46 verifies what was built.** But what was built still stands on **one thin ray
   at hip height on the wrong collision channel**; see #81.
   The data half of #61 (dense capture along the leg) is still open and feeds the corpus criterion.

3. **#85 shared APC doctrine — do this FIRST of the new items; it is the cheapest large win.**
   SR46 measured it: `dufus/rules.md` is 94 lines, `maren/rules.md` is 21, and Maren reasoned
   *"time to refuse this ground"* then could not, because her file never mentions `refuse_cell`.
   Six weeks of navigation doctrine lives in one character's file. `rules.md` needs imports.
4. **#81 body-box probe — the highest-value navigation item.** SR46 is the argument: Dufus spent
   4½ minutes bouncing between a van and a baseball field, refused three patches accurately, and
   kept landing in them, because a 9-m refusal cannot be obeyed with a 15-m step and a thin ray
   never says *where the gap is*. Capsule sweep + coarse raster → "I fit" / "the gap is on my left".
5. **#83 real object identity / #84 the prompt payload contract (absorbs #82).** #83: substring
   matching the level author's file names is not object detection — SR46's one unclassified actor
   (`receptionCounter_7`) proves the fail-loud log works and that the table is a treadmill.
   #84: one declared payload, one code path, allow-list by construction. **#84 must not start while
   a live-run lane is open** — it touches every prompt.
6. **#76 center-out exploration** — the last unbuilt item of the original three. Wait for SR45:
   if rings now grow on their own from the frontier facts plus refusals, #76 may need nothing.
7. **Phase B — BLOCKED (user, 2026-08-20).** #66 reaction gate → #67 APC↔APC conversation →
   #68 work that leaves a mark are **not startable** until "THE EXIT CONDITION" above is met:
   an unattended overnight survey, reusable grid/place data other APCs consume, and a
   VLM-grade corpus. Exploration is NOT yet a background service; it is still the headline.
8. **Catch-up lane (away-time work):** the "Needs tests (speed mode)" ledger, then the remaining
   cleanup advisories (bridge reconnect noise, `agent_manager.py` / `web_ui/main.py` splits).

- **SR46 (2026-08-20) — 30 ticks, 616.8 s, 2 APCs, clean stop, ZERO errors. The #61 blocker fix is
  verified live; the run also exposed the doctrine-distribution bug (#85) and made the case for #81.**

  - **#61 reflex half VERIFIED.** 17 `blocker:` lines, 2 reflex stops, and — the point of the fix —
    **`veh_Van_6` was reported at 400 cm, 37 cm and 36 cm.** Under the pre-2026-08-20 code that name
    matched no keyword, classified as `"obstacle"`, and was **dropped**: Dufus would have been told
    nothing at all while standing 36 cm from a van. `veh_VegetableTruck2` reported 13 times.
  - **The fail-loud classifier earned its keep on the first run.** Exactly one unmatched actor:
    `blocker classifier: no keyword matched actor 'receptionCounter_7' (class 'StaticMeshActor')` —
    the office lobby Dufus walked into at 11:37:47. Silent degradation is now visible degradation.
    Do **not** just add "counter" to the table; that is #83's whole point.
  - **Dufus: 4½ minutes trapped in cell (7,7), oscillating between a van and a baseball field**
    (11:41:53 → 11:46:28), which is what the user reported watching. Footing cycled
    pavement → grass → other → grass → water → pavement → grass → water → grass → pavement →
    `cultivated_field` (the baseball infield in 8,7). He refused **three** 9-m patches with accurate
    reasons ("baseball diamond infield dirt and outfield grass", "shallow water basin edge, dead end
    with boats moored", "grassy field with earthen mounds") — and **kept landing back in them**.
    - **Why the refusals did not help, and it is not a refusal bug.** A patch is 9 m across; a step is
      **~15 m**. He cannot aim finer than the trap is wide, so "do not go there" is unactionable — the
      step lands where it lands. His own words at 11:44:27: *"Standing on refused grassy pocket for
      the third time."* He knew. He had no move that respected the knowledge.
    - **This is the argument for #81.** A thin ray at hip height told him "vehicle 36 cm ahead" and
      nothing about **where the gap was**. With `open_columns` the fact becomes "your body does not
      fit ahead; it fits to your left" and a sidestep is a measured 2 m, not a blind 15 m. Consider a
      short-step action as part of #81's follow-on: refusals smaller than the step length cannot be
      obeyed.
  - **Maren: 20 of her decisions moved her 0.0 cm**, then one finally executed and flung her ~28 m
    into the cornfield in cell (6,6) (11:44:45 → 11:46:29). Two causes, and only the first is known:
    1. **#75's truck-row split, still parked.** Every prompt told her she was at her post *and* that
       she had to walk to her post. Twenty stalled `walk_to place:vegetable truck` orders followed.
       The contradiction reaching the model in one prompt is #84's example case.
    2. **NEW — she does not have the doctrine (#85).** `maren/rules.md` is **21 lines**;
       `dufus/rules.md` is **94**. She has no look-before-you-step, no refusal doctrine, no
       breadcrumbs, no bounce fact, no tried-headings rule. **At 11:45:58 she decided *"I keep
       looping through this cornfield pocket; time to refuse this ground"* — and emitted `walk_to`,**
       because nothing in her file tells her `refuse_cell` exists. All three refusals in SR46 were
       Dufus's. Six weeks of navigation lessons were written into one character's file.
  - **Carried forward:** #81 (body-box probe) is now the highest-value navigation item; #85 is the
    cheapest large win in the run; #84 owns the contradiction Maren was shown.


- **SR42 (2026-08-19) — first run of the #76/#77 lane. 53 ticks, 12.4 min, clean stop; the CLI
  session driving it crashed, but the runner shut down properly and all data persisted.**
  - **Worked:** 4 cells surveyed — (5,5), (6,5), (7,4), (7,3) — all 16 headings succeeded. #75
    preflight merged the duplicate 'vegetable truck' row on startup as designed. Zero LLM errors
    after wake. Stall recovery worked: 3× "ordered north, achieved 0.0 cm" and the model rerouted
    northeast each time without code help.
  - **Bug (FIXED this session, offline 58/58): wake `refuse_cell` never reached its handler.**
    Dufus opened the run refusing the cornfield cell — exactly the pre-emptive refusal #77 wants —
    and the wake path sent the verb straight to the bridge: "Unknown action: refuse_cell". Same
    class as SR39's `survey_here` wake bug; `_apply_cell_verdict` now runs on the wake path too.
    Needs live verification next run.
  - **#77 not yet satisfied: the "north trap".** North from the (5,5)/(6,5) road repeatedly leads
    into a grassy yard (pergola) or *inside a mobile home bedroom*; Dufus stepped in and retreated
    5 times (ticks 8-9, 11-12, 23-24, 28-29, and at run end). Cell (6,4) is still unsurveyed
    because every approach lands on bad footing. All discoveries were post-step — zero pre-emptive
    vetoes. This is precisely the per-direction footing-probe gap #77 exists to close.
    User screenshots (11:14) confirm it visually: Dufus wedged in a dead-end trash alley behind a
    building, and pressed flat against a mobile home's back wall on grass. "Behind buildings" is
    ground the navmesh calls walkable but no APC should route through — #77 (see it first) plus
    #26 dead-end recognition are the planned closers; no new mechanism needed.
  - **Maren place/view mismatch — PARKED (user, 2026-08-19: "Forget about Maren for next few
    sessions").** Twice she reasoned "the system marks me at my truck post but the view shows the
    mobile home community". She stands at (-8950, 160), cell (6,5); the kept truck row is at
    (5,5) — the boundary-straddling truck from #75. When picked back up: check whether her
    spawn/anchor should move with the kept row. Do not spend session time on her until then.

- **#55 SR33 (2026-08-02) — the survey was photographing cells it was not standing in. FIXED, needs
  live verification.** SR33 ran 2 walks and 8 survey headings and never moved from
  `(-10491.7, 718.6)` — grid cell **(5,6)**. From that one spot it wrote `community:5:5` rev 4 *and*
  `community:5:6` rev 2: two cells, one set of four frames, both described as "standing in a corn
  field". Two causes, both closed:
  - Arrival was a **distance** test with the explorer tolerance widened to a full cell (#48), so
    "at the center" was true 15.7 m outside the cell; and a persisted survey interrupt keeps its
    target across ticks *and runs*, so Dufus woke owing a survey for a cell he had left.
    Containment is now the authority — outside the target cell the only legal sweep step is walking
    into it — and `_save_place_visual` refuses to file frames whose capture point is in another cell.
  - `place_images` now stores `captured_x`/`captured_y` (#49 partially landed): a mis-filed
    revision is detectable instead of invisible. Pre-existing rows are NULL — never guessed.
  - Containment could have become an infinite walk into a walled-off cell, so a survey gets
    4 travel ticks; legs that move < 150 cm don't count, and exhausting them abandons the survey and
    marks the cell blocked on the APC's own map, which the sweep start gate now honours.
  - **The corpus still holds the bad rows.** `community:5:5` rev 4 was shot from cell (5,6) and
    `community:5:5` is named "Utility Pole Forest" while every SR32/SR33 revision describes a corn
    field. Needs a user decision: purge the mis-filed revisions or leave them and re-survey.
- **#55 decision log is now auditable.** SR33's two walks both logged
  `walk_to success` + "turning back the way I came" and nothing else — one walked 15 m *into* the
  corn, the other walked back out, and only the raw socket dump in `sim_runner.log` could tell them
  apart. Rows now carry `at`, `cell`, `footing`, `facing_yaw`, `moved_cm` (real displacement since
  the previous decision) and `move: {intent, target, heading, distance_cm}`, where `intent`
  distinguishes a facing-relative `direction:back` from an absolute place/actor/cell/location.
- **Promoted to #77 (2026-08-19) — kept here for history. (#55 follow-on, was: not started): the
  LLM's "don't go there" has no way to reach the engine.**
  `walk_to direction` is a yaw offset from *current facing*, and after a survey the facing is the
  last cardinal sweep yaw — so "turn back the way I came" is unrepresentable and in SR33 executed as
  a step **deeper into** the field. Nothing records the inbound heading, and footing is only sampled
  where the APC already stands, so bad ground can only ever be discovered by walking onto it.
  Direction: give the LLM absolute compass directions (the survey already thinks in cardinals), a
  "you came from <compass>" fact, per-candidate-direction footing probes as facts, and let it name a
  grid cell as one to stay out of — mapping onto the existing `SpatialMap.mark_blocked`.
  Facts, not blockers.

- **SR32 (2026-07-30) — first working Sonnet 5 run; survey-only Dufus verified live.** 49 ticks,
  zero LLM errors (after fixing `content[0].text` → ThinkingBlock crash in `llm_router.py` /
  `perception.py`). Six new survey composites (cells 5,5 / 5,6 / 4,6 / 4,5 / 3,5 / 3,6;
  `place_images` 10 → 16), contiguous westward push, zero daily-life detours. **FOOTING observed
  working**: the LLM itself turned back from corn field, lawn, building interior, pitch-black view —
  answers the open question carried since 07-29. Watch item: last ~4 decisions were a possible
  footing ping-pong near the farmhouse (retreat → land in grass → retreat); if it recurs, fix with
  louder facts ("you have retreated from this spot N times"), not a code blocker.
- **Live/PIE verification bundle:** #39 stale refresh and #41 truthful counts passed in SR28; finish
  #40 visible-yaw/narration grounding and verify #37 chat on its dedicated page with Dufus and Maren.

### Next

1. **#36 JSON agenda + daily ledger:** implementation and offline coverage are complete at 51/51;
   user-run live verification still needs interruption/resume plus the post-arrival `current_goal` sync fix.
2. **#37 direct APC chat live verification:** verify the moved UI still stops Dufus, supports multiple
   turns and temporary guidance, resumes prior work, and leaves Maren unaffected.
3. **#35 survey expeditions:** choose the expedition cadence, target-selection surface, chaining/return
   policy, and retry bounds before extending the now-durable survey interruption.

**Offline work built + tested 2026-07-24:** **#43** drill-down + agenda editor, **#40** survey narration
grounding, **#42** bounded action-error diagnostics. Three new test files landed at the user's explicit
request (`test_apc_agenda_ui.py`, `test_survey_grounding.py`, `test_action_errors.py`); the full offline
suite passes at **54/54**, with no regression in the previously green 51. All three still await their live
verification, which folds into the #36/#37 live session.

### The plan, right now (2026-08-20, after SR46)

1. **Rebuild the UnrealMCP plugin in the editor.** #81's `get_character_forward_volume` is C++ and
   does nothing until it is compiled. Until then every APC silently uses the old single ray — the
   runtime warns once per run when that happens, so check the log for
   `body-box probe (#81) unavailable`.
2. **SR47 ran and was killed at 5 ticks (2026-08-20).** See the SR47 section under #86: the shrink
   half worked, the grow half was wrong (a 45 m order is walked as a navmesh path and arrived 50 m
   sideways), and #81's `open_columns` was naming gaps that were not gaps. All three are fixed;
   **SR48 is the re-run.** Grade SR48 on: `walk plan: <dir> N m in K hops` appearing, followed by
   `hop 2/K`, `hop 3/K` … and ending in `all hops walked` rather than an abort; no `DRIFT:` line over
   45 degrees on a grown step; `cut to` still stopping short of refused ground; and new ground
   surveyed. A plan that always ends early is the thing to look at — the reason is logged verbatim
   (`walk plan ended: ...`). Original SR47 criteria follow.
3. **SR47 (superseded).** Grade it on: a `fits=false` line with `open` naming a real side; Maren emitting
   `refuse_cell` (she now has the doctrine — this is #85's pass criterion); no engine identity in the
   prompts (`prompt leak` warnings should be zero); and the survey covering new ground.
4. **Then the exit condition** — the overnight run. Everything above is in service of it.

4. **#86 adaptive step length** (new, user 2026-08-20) — every move is a fixed 15 m, so a target 4 m
   away can only be overshot and then overshot back: **the action vocabulary cannot express "a bit
   closer", so the loop rings instead of converging.** Deterministic, no engine rebuild, and it is
   shared locomotion — squarely inside the exit-condition lane. **While SR47 runs, count reverse legs
   and wedge runs per 100 ticks**; that is the baseline #86 must beat. **#87** (make the lizard brain an
   LLM) is **analysis only** and is explicitly parked behind the overnight run — it doubles per-tick
   cost, and most of the gap it would close is closed by #86 + #81 + #77 for free.

### Needs tests (speed mode — user, 2026-08-19)

Features built WITHOUT tests to speed up code-done → live-testing. One line per
feature as it lands; the suite catches up here later. (Everything built before
this banner on 2026-08-19 — #77/#78/#26/#79/#80 — already has tests.)

- **#88 open headings** (2026-08-20) — `_open_headings` needs a fake bridge where straight ahead and
  one side are blocked and the other side is clear: it must return compass words (not body-relative),
  nearest-turn first, and an EMPTY list must stay distinguishable in the prompt from "never probed".
- **#86 the walk plan** (2026-08-20) — `move_plan.leg_distances` is pure and trivial to cover
  (exact multiples, a remainder, a remainder too small to be its own hop). `_pulse_walk` needs a fake
  bridge and one case per abort path: drift off the line, something ahead, no ground made, someone
  arriving, tick budget — all five were exercised by hand when built, none are pinned.
- **#86 heading drift + #81 open-column strictness** (2026-08-20, after SR47) — `_open_columns` has
  the two SR47 shapes as obvious cases (a column blocked at body height is not a gap; `fits=False`
  with an unstruck raster names no side at all), and the `last_move.went` drift fact needs one case
  where the achieved heading is 90 degrees off the ordered one.
- **#86 adaptive step length** (2026-08-20) — `move_plan.plan_step` is a pure function and is the
  obvious unit test: shrink caps, the grow case, "no room" at zero, and that an unmeasured input
  (`None`) never reads as clear. `AgentManager._scan_ahead` needs a PlaceDB fixture with one no-go
  patch and one refused cell.

### Cleanup advisories (observed, not scheduled)

- **`action["_resolved_target"]` never reaches the caller** (found while building #86).
  `_execute_world_action` starts with `action = self._resolve_action_actor_refs(action)`, which
  returns a **copy** — so the `_resolved_target` written at `agent_manager.py:4384` is discarded, and
  `memory_store.py:196`, the only reader, always falls back to `action["location"]`. Harmless today
  (the fallback is usually right) but it means the movement trace silently loses the resolved
  heading for direction walks. #86 sidestepped it by carrying the move plan on the *observation*,
  which is not copied.

Raised while working, parked here on purpose — none is urgent, none should be done as a drive-by.
Add to this list rather than refactoring adjacent code mid-task.

- ~~**`test_apc_agenda_ui.py` is not hermetic.**~~ **DONE 2026-08-19:** the runner-down checks
  now point at a dead port and restore the URL after.
- ~~**`plan/backlog.md` is expensive to read.**~~ **DONE 2026-08-19:** dated ⚑ banners and the
  completed 2026-07 queues (581 lines) moved to `plan/backlog_history.md`; numbered spec sections
  stayed because live items reference them.
- **`agent_runtime/agent_manager.py` is ~3,800 lines.** Tick phases, survey/interruption mechanics,
  agenda wiring, place resolution, and bridge execution all live in one class. A split along those
  seams would make each testable alone; the survey helpers are the most self-contained starting point.
- **`web_ui/main.py` is ~1,100 lines** covering world/agent CRUD, map, replay, sim proxying, settings,
  providers, and logs. FastAPI routers per concern would match how the pages already divide.
- **`templates/agent.html` nests a `<form>` inside a `<form>`** (Delete NPC inside the main edit form).
  Invalid HTML that browsers resolve inconsistently; predates this work and was left alone deliberately.
- **Template `<script>` blocks duplicate fetch/poll helpers** across `index`, `sim`, `map`, and `agent`.
  `web_ui/static/apc_drilldown.js` (#43) establishes the precedent for extracting shared JS.
- ~~**`save_agent` silently defaults malformed form values.**~~ **DONE 2026-08-19:** non-numeric
  tier/interval/cooldown is rejected with the field named, nothing written, and a rejected create
  leaves no half-made agent folder (`test_agent_form_validation.py`). Blank still means default.
- **Bridge client reconnect noise:** SR32's log is ~400 lines of
  `Existing connection failed: 'NoneType' object has no attribute 'sendall'` — the socket client
  drops/rebuilds the connection around every command. Harmless (every command succeeded) but it is
  most of the log volume and buries real warnings. *(Observed 2026-07-30, SR32.)*

### Waiting

- **#16 map authoring:** lock the required name/description fields, exact-click versus grid-center
  anchoring, default APC-place extent, and the migration/precedence rule if it replaces landmarks.
- **#35 survey expeditions + #13.4 pristine survey reset:** choose cadence/target-selection,
  chaining/return policy, and the exact purge boundary while preserving LLM agency and authored world
  configuration.
- **#32 visual cortex:** choose transient gaze retention/dedup and unique-frame retention; semantic
  place recall remains an approved implementation slice once its query surface is selected.
- **#27 later slices:** community-landmark final-approach geometry and the bounded local-recovery/
  road/dead-end policy still need their explicit design choices.
- **PIE/live verification bundle:** #23 landmarks after editor moves, #24 launcher, #14 replay,
  B7b personal space, and remaining cockpit/onboarding checks.
- **Child Blueprint meshes:** actor rebind is done; mesh selection remains an editor choice.
- **#12.2 interaction memory:** needs a compact event-schema decision before implementation.

### Loop-safe

The approved 2026-07-21 offline queue—**#39**, **#40**, **#41**, and the dedicated Chat-page slice of
**#37**—is complete at 50/50. Each item retains its listed PIE verification. #36 remains design-gated:
survey completion is now authoritative, but no structured goal-to-interruption link exists yet, so a
free-form text match must not silently clear a goal.

**Execution note 2026-07-21:** autonomous preflight was attempted after approval and correctly blocked
on the pre-existing dirty tree: the uncommitted #37 direct-chat implementation overlaps runtime, runner,
web, tests, backlog, handoff, and spec files, with `places.json` also untracked. Preserve and reconcile
that work into a reviewed clean baseline before starting #39; do not stash, discard, or absorb it into an
unrelated survey commit.

> **Historical status log moved.** Dated ⚑ banners and the completed
> 2026-07 staged/autonomous queues now live in `plan/backlog_history.md`
> (evidence only). The active view above is authoritative; the numbered
> spec sections below remain because live items still reference them.

## 12. Interaction memory (met-someone events + "no need to re-greet")

**Status:** 12.1 BUILT (offline) 2026-07-03; 12.2 not started · **Independence:** Self-contained (loop-safe) · *(user, 2026-07-03)*

Fallout from B7b working: now that Dufus **stops ~3 m short and faces people** instead of walking
through them, greetings become real *interactions* with state — and that adds detail/complexity we
have to remember. Two related pieces, in priority order:

- [x] **12.1 — Don't re-greet.** ✓ 2026-07-03 *(user's higher priority — "I have been here before and
  talked to these people, no need to go back and say Hi.")* `SocialMemory` now stamps a
  **`last_interacted`** world-time on every `record_interaction` (distinct from a mere sighting's
  `last_seen`) + a `last_interacted(name)` reader. New `planner.absolute_minute`/`minutes_between`
  measure sim-time across day rollover. `AgentManager._mark_recent_greetings` tags each surfaced
  acquaintance `recently_greeted` when spoken with inside **`_GREET_COOLDOWN_MINUTES` (60)** (copies,
  never mutates the store; a backwards clock / new day reads as not-recent → greet again). The reaction
  gate reads it: `_acquaintance_lines` marks "already greeted recently — no need to say hi again", and
  the #10.5 doctrine's greet rule now excludes an already-greeted person (a nod is enough; being
  *spoken to* still gets a response). Tests: `test_social_memory.py`, `test_planner.py`,
  `test_prompt_context.py`. Suite 34/34. **Live verify:** two agents meet, greet once, then pass
  without re-greeting each tick.
- **12.2 — Interaction memory proper.** A greeting is an **interaction** with content worth keeping: who,
  when, where (grid/place), what was said, sentiment. Today speech→interaction feeds `SocialMemory`
  + episodic, but there's no first-class "interaction" record an agent can recall ("last time I saw
  Maren she was heading to her truck"). Design a compact interaction event (likely a specialization of
  the episodic log) that the decision prompt can surface under "People You Know."

Relates to: #5 (social/episodic memory), #10.5 (reaction gate — the greet interrupt), B7b (the standoff
that turns a pass-by into a face-to-face interaction).

---

## 13. World initialization + "make all the things" generation

**Status:** **In progress** — 13.1–13.3 built offline 2026-07-09 (suite 42/42 at
those commits); plugin-install guidance, clean-clone QUICKSTART validation, and broader generation
remain open. · *(user, 2026-07-03; reframed 2026-07-05 as the **downloader bootstrap**;
re-reframed 2026-07-09 to the landmark era — "paramount to making this project useful to others")*

> **⚑ Re-reframed (user, 2026-07-09):** "The world grid gen and landmark items plus dropping APCs
> into the world is paramount to making this project useful to others. We are both experimenting
> but will need to harden the **git download and set things up** sequence." The 2026-07-05 flow
> below is updated to the **landmark era** (#23/#25 replaced the click-authoring path — the level
> is the source of truth, not a web UI). **New-user sequence to harden:**
> 1. **git clone → `Python/start_sim.bat`** — uv bootstraps deps, runner + cockpit come up, tab
>    opens itself (#24 ✓). Harden: a fresh clone has **no `.env`** — first run must land on the
>    settings page saying "add your API key here", never a stack trace ([[drag-and-drop]]: fail
>    loud *with instructions*).
> 2. **Plugin into *their* Unreal project** — copy/enable the bridge plugin, confirm the 55557
>    listener in the Output Log. Harden: document it; cockpit shows "Unreal not connected — did
>    the plugin load?" instead of silent 0-agent starts (the 2026-07-08 failure, now a known class).
> 3. **Author the world in the editor** (#23): drop `Landmark_<owner>_<name>` actors + drop APC
>    child BPs at their day-start posts (editor placement = wake spot — put each APC *at* its
>    first-block landmark).
> 4. **Generate `world_grid.json`** for a fresh level — `generate_world_grid` exists but needs a
>    zero-knowledge path (cockpit button / first-run prompt), not a Claude-driven call.
> 5. **Create agents** — `/create-npc` or web form → `agents/<id>/` md files + actor binding.
> 6. **`/map` → Sync world** (landmarks listed, suspects flagged, #25 ✓) → **Start**.
> Steps 1/2/4 are the hardening gaps; 3/5/6 exist. A `QUICKSTART.md` walking exactly this
> sequence, verified against a scratch clone on a clean machine, is the acceptance test.

### Executor slices (spec'd 2026-07-09, Fable — both loop-safe, both web-layer only)

- [x] **13.1 · First-run setup banner (gap 1).** ✓ 2026-07-09 (Sonnet executor `f88f8b9`,
      worktree; merged, suite 42/42). A fresh clone has no `.env`; today nothing tells
      the user. Build: **(a)** `config_store.setup_status(env_path) -> dict` —
      `{"env_exists": bool, "provider_ready": bool, "ready": bool}`; `provider_ready` = the
      configured `LLM_PROVIDER` is `ollama` (needs no key) **or** any key matching
      `is_secret`-style `*_API_KEY` is set non-empty; `ready = env_exists and provider_ready`;
      missing `.env` → all False, **never raises**. **(b)** `web_ui`: `GET /api/setup` returns it;
      the `/` (index) and `/sim` page routes pass `setup` into their template context, and the
      templates render a dismissable banner when `not ready`: "First run? Add your model provider
      key in **Settings** →" linking `/settings` (which already exists and works). No redirect, no
      gating of routes — a loud banner only. **(c)** Offline tests (`test_first_run.py`, pattern =
      `test_settings_page.py`): status dict for missing .env / ollama-no-key / anthropic+key;
      banner present when not ready, absent when ready (TestClient + tmp .env via the same
      ENV_PATH override the settings tests use). Files: `agent_runtime/config_store.py`,
      `web_ui/main.py`, `web_ui/templates/index.html` + `sim.html` (or `base.html` if both
      inherit a block), new test. **Do not** touch llm_router/perception key resolution.
- [x] **13.2 · Grid-gen from the cockpit (gap 4).** ✓ 2026-07-09 (Sonnet executor `75ae079`,
      worktree; merged, suite 42/42; live verify: press the /map button on a fresh level).
      Executor's sound extras: proper `{ok, error}` envelope (503 runner-down / 400 manager
      error) so the callout can show failures. **Fallout fix, same session:** both worktree
      venvs failed at import on Python 3.11 — `llm_router.py:308` uses PEP-701 f-string
      syntax; `requires-python` bumped `>=3.10` → `>=3.12` (+ re-lock + smoke import), so a
      fresh clone's uv provisions a parseable interpreter (an onboarding bug #13 exists to
      kill). `generate_world_grid` exists end-to-end
      (manager → runner `POST /world_grid` → `RunnerClient.generate_world_grid`) but a new user
      has no way to invoke it. Build: **(a)** `web_ui` `POST /api/world/grid` — proxy to
      `RunnerClient.generate_world_grid()` (accept optional `cell_size`/`padding` in the JSON
      body, default 3000/800), with the same "no sim runner running" error envelope the other
      `/api/sim/*` proxies use. **(b)** `/map` page: when the level has no `world_grid.json`
      (the existing no-bounds/no-grid error path in `/api/map`), render a callout — "This level
      has no grid yet — **Generate world grid**" — whose button POSTs the new route and reloads
      the map on `ok`. Keep the existing behavior when a grid exists (no new UI). **(c)** Offline
      tests (extend `test_map_view.py` / `test_sim_controller.py` patterns): route proxies to a
      stub runner + surfaces its error when unreachable; map page HTML carries the callout when
      the grid file is absent and not when present. Files: `web_ui/main.py`,
      `web_ui/templates/map.html`, tests. **Do not** change `AgentManager.generate_world_grid`
      or the runner routes.

- [x] **13.3 · Cockpit buttons for the deep resets.** ✓ 2026-07-09 (Sonnet executor `0648b10`,
      worktree; merged, suite 42/42; live verify: click both buttons in a browser). 🧠 Reset
      agents + 🗺 Reset places now sit beside ☀ Restart day with honest confirm() text.
      **Caveat surfaced during the hand-wipe that prompted this:** maren's `memory.seed.json`
      is stale (May world: "shop canopy", "pawn shop") — Reset agents re-injects it; rewrite or
      delete the seed. (Spec'd 2026-07-09, Fable.) The user asked
      "do we have a webUI button for all this?" while we hand-wiped agent brains + the place DB —
      answer was no. `reset_agents` and `reset_places` exist end-to-end (manager → runner
      `POST /reset_agents`/`/reset_places` → `RunnerClient.reset_agents()`/`.reset_places()`)
      but the `/sim` cockpit only exposes `reset_day`. Build, mirroring the existing reset_day
      pattern exactly: **(a)** `web_ui/main.py`: `POST /api/sim/reset_agents` and
      `POST /api/sim/reset_places` proxying the client methods (same error handling as
      `/api/sim/reset_day`). **(b)** `sim.html`: two buttons beside ☀ Restart day, each with a
      `confirm()` whose text says what it really does — "Reset agents: teleport agents to their
      start spots and wipe learned memories (restores memory.seed.json if present)" / "Reset
      places: wipe the shared world map DB (landmarks re-apply on next sim start)". **(c)**
      Tests: extend `test_sim_controller.py` (stub runner grows the two methods; routes proxy +
      surface stub payloads; degrade cleanly when the runner is down, same as reset_day's test).
      Files: `web_ui/main.py`, `web_ui/templates/sim.html`, `test_sim_controller.py`. **Do not**
      touch `runner_app.py`, `runner_client.py`, `agent_manager.py`, or any #13.1/#13.2 files
      beyond these three.

- [ ] **13.4 · One reviewed “pristine survey run” reset.** Requested 2026-07-15 for the future
      whole-map survey experiment: the user wants to “clean everything out / files / db / etc” and
      let Dufus start fresh. Existing **Reset agents** + **Reset places** do not clearly cover every
      generated observation, place composite/history link, replay/log artifact, runtime schedule,
      and stale seed-memory source as one auditable operation. Design the purge boundary before
      implementation: preserve authored agent identity/goals, landmarks, `places.json`, grid/map
      calibration, and provider config by default; enumerate generated knowledge/artifacts to remove;
      preview/report every target; then perform the reset only after explicit confirmation. Decide
      whether hand-authored `memory.seed.json` is retained, ignored for this run, or separately reset.
      Acceptance requires an offline temp-world fixture proving no target escapes the world root and
      a fresh start contains no prior learned place/visual/replay state while authored world truth
      still re-applies. **Classification:** design decision first; then loop-safe filesystem/reset
      transaction plus one live cockpit verification. **Supports:** #35.

The long-term goal: **initialize a world from scratch** with **generation code that builds all the
things** — spawns/wires the actors, child BPs, agents, grid, and place cells automatically, so a new
world stands itself up. This is the automated end-state of the [[drag-and-drop]] philosophy: the end
user adds content, the system makes it work; config complexity is ours, never theirs.

**Interim (now):** until that generation code exists, **Claude Code (dev mode) does the linking by
hand when the user adds things in Unreal.** Concretely, what the child-BP rework needed this session:
- A user drops a new actor / child BP in the level (e.g. `APC_Maren_BP`, `APC_Dufus_BP`).
- CC relinks the agent config: `unreal_actor_name` (find/bind hint), `blueprint_class` (spawn
  fallback), and `display_name` (the clean name others use — engine label stays out of the sim).
- CC verifies the binding round-trips (known_characters shows the clean name; targeted actions
  resolve back to the actor) and the suite stays green.

**Toward generation (future pieces to design):**
- A world-init routine that takes an inventory of placed actors + intended agents and **emits the
  agent `state.json` + bindings** (the manual step above, automated).
- Auto-discovery of placed actors from the running level (the bridge can already `find_actor`) so the
  config can be **generated from what's actually in the world**, not hand-authored.
- Bootstrapping the grid + community place cells for a fresh level (relates to #11 activation / the
  30 m district grid — see [[grid-place-cell-sizes]]).
- Scaffolding a new agent end-to-end (the `/create-npc` skill is the seed of this).

Relates to: `feedback_drag_and_drop`, `feedback_dev_sim_modes` (dev-mode CC operates), #11 (grid/place
build-out), the child-BP rework (the first hand-linked example), `/create-npc`, **#23/#25 landmarks
(the authoring path this flow now routes through — #15 `places.json` is the secondary source, #16
click-authoring is fallback only)**, #24 (`start_sim.bat`, step 1's one-click).

---

## 14. Run replay — single-step through a sim run's observations

**Status:** BUILT (offline) 2026-07-03; further replay expansion paused behind #32 image-lifecycle
design · **Depends on:** #9 attribution + #32 artifact policy · *(user, 2026-07-03)*

> **✓ Landed 2026-07-03:** `agent_runtime/run_replay.py` (pure index/join —
> `list_runs`/`list_agents`/`list_frames`, joining each observation frame to its nearest
> decision-log entry by run+agent+time) + web routes `/replay`, `/api/replay/runs|frames|image`
> (image serve is path-traversal-guarded to well-formed SR names inside the agent's obs dir) +
> `replay.html` (run/agent pickers, prev/next + scrubber + ←/→ keys, frame beside its decision) +
> a Replay nav link. Test: `test_run_replay.py` (index, join, name-guard, routes). Suite 34/34.
> **Live verify:** run the web app after a PIE run and scrub `SR2` frame by frame.

The point of the SR<n> tag (#9): **be able to single-step through the sim runs** for debugging — scrub
the captured observation frames of a run in order (and jump between runs), seeing what each agent saw
and decided tick by tick. #9 tagged the artifacts (`SR<n>_observation_<ts>.png` + a `sim_run` field on
every `agent_decisions.log` entry); this item is the **review surface** that consumes them.

Pieces to design:
- **Group by run + agent:** list runs (from `sim_run.json` / distinct `SR<n>` in the observations dir),
  and within a run, each agent's frames in timestamp order. The filename already carries `SR<n>` +
  agent (via the per-agent `observations/` dir) + timestamp, so this is a directory/filename scan.
- **Step UI (web cockpit):** prev/next through frames, showing the observation image alongside the
  matching decision (join `agent_decisions.log` rows on `sim_run` + nearest timestamp — action,
  thought, result). A scrubber + keyboard step. Lives in `web_ui` next to the `/sim` cockpit + `/map`.
- **Cross-run compare (later):** step the *same* tick/time across two runs to see how a change moved
  behavior.

Loop-safe core: the run/frame indexing + the log-join are pure and offline-testable; the page is a
`TestClient` route like the other `web_ui` pages. Live value: watch a real run back frame by frame.

Relates to: #9 (the tag it consumes), #6/#6b (map + route images), the `web_ui` cockpit (`/sim`).
The deferred #9 observation/image artifact review is the design gate for further replay expansion.

---

## 15. Authored places manifest — the world's root configuration

**Status:** ✅ **DONE 2026-07-07** (built per `plan/specs/WP6-authored-places-manifest.md`; suite
36/36). `places_manifest.py` (load + declarative converging apply), `source` column
(authored/runtime/wake-seed) with migration, loader call in `start_simulation`,
`_validate_schedule` fail-loud at plan time, wake seed demoted (WARNING when a manifest exists).
**No `places.json` authored for MCP_World — the user places things** (spec D7; 2026-07-06 facts:
truck (-8950, 160) owner maren; dufus home (-10460, -800) owner dufus). · **Source:** user,
2026-07-05 ("the APCs don't have a root configuration — my house is over here, my vegetable truck
is over here") · **Independence:** self-contained (loop-safe); #16/#17 build on it

Today places only exist if an LLM *discovers* one at runtime or the wake-seed *guesses* one
("editor placement = day-start spot" — a convention, and SR2 showed how fragile it is: the seed
stamped the truck mid-walk). The sequencer can already answer "what time is it, where should I be"
(`planner.step`) — what it can't do on a fresh world is resolve the *where* to a real position.
The fix is **authored ground truth**: a per-world manifest of canonical places loaded into PlaceDB
at world load, before any tick.

Pieces:
- **`worlds/<level>/places.json`** — the manifest. Per entry: `name`, world `x/y` (anchor),
  `extent_cm` (default 900 = the 9×9 m place cell; bigger for buildings), optional `owner`
  (agent_id → an owned place cell: "maren's vegetable truck", "dufus's home") and optional
  `community: true` (also community-name the containing grid cell, e.g. "village square").
- **Loader** — on world load (AgentManager `_load_agents` / `start_simulation`), upsert manifest
  entries into PlaceDB (idempotent; authored entries win over runtime discoveries of the same
  name — re-running never duplicates). Grid (col,row) + dx/dy are *derived* from x/y via
  `WorldGrid`, never hand-authored.
- **Schedule validation (fail loud)** — after `generate_daily_plan`, log a warning for any block
  whose `place` resolves to nothing (manifest, community, or owned): the agent will be told to
  travel somewhere unreachable. Surfaces the "hunting for a place nobody recorded" class of bug at
  plan time instead of tick 40.
- **Wake-seed demoted to fallback** — with a manifest present, `_wake_directive` resolves
  authored places and only seeds when the world is genuinely unauthored (keep the mechanism,
  document the priority: authored > discovered > wake-seeded).
- **Offline tests:** loader idempotency, owner vs community writes, derived col/row round-trip,
  schedule-validation warning.

Relates to: #11.2 (owned place cells — the storage this fills), #13 (bootstrap flow — the manifest
is its config artifact), #16 (the editor that writes this file), [[grid-place-cell-sizes]],
`feedback_drag_and_drop`.

---

## 16. Click-to-author places on the /map — the no-Unreal place editor

**Status:** **USER LIVE-VERIFIED 2026-07-21** (author-place flow “looks good”); original implementation ✅ **DONE
2026-07-07** (suite 41/41). "Author places" toggle on `/map`: fill
name/owner/extent, click the registered map → `POST /api/places` writes `places.json` (same
normalized name = move/edit, no duplicates) and **re-applies the whole manifest to PlaceDB
immediately** (WP6's declarative converge — no sim restart). Panel lists authored entries with
per-entry delete (`DELETE /api/places`); `GET /api/places` serves the raw manifest. Fail-loud
validation mirrors the loader (blank/placeholder names, non-numeric or out-of-bounds coords,
unbounded grid); a **corrupt places.json is surfaced with a 500 and never rewritten**. Runtime
LLM-discovered rows survive every authored edit. **The user now authors MCP_World's places by
clicking** — WP6 D7 satisfied without anyone typing coordinates. · **Source:** user, 2026-07-05 ·
**Depends on:** #15 ✅, #18 ✅ (the registered map)

The #6c map is registered world↔pixel in both directions, which makes it the natural authoring
surface: **click a spot on the real top-down map → name it → optionally assign an owner/extent →
saved to `places.json` + PlaceDB.** This is the [[drag-and-drop]] answer to "how does a user say
'Maren's truck is here' without opening Unreal": they don't touch the engine at all — one
screenshot, then everything is clicks in the browser.

Pieces:
- **Pixel→world inverse** on the map page (the overlay already does world→pixel; the inverse is
  the same linear map) — click yields world (x, y), display the target cell + snap preview.
- **An "author" mode toggle** on `/map`: click → small form (name, owner dropdown from the world's
  agents or "community", extent) → `POST /api/places` → validates, writes `places.json`, upserts
  PlaceDB, map refreshes (the new box appears immediately).
- **Edit/delete** for authored entries (click an existing authored box) — runtime-discovered
  places stay read-only here.
- **Offline tests:** the POST round-trip (TestClient + temp world), pixel↔world inverse math,
  authored-vs-discovered edit guard.

**Reopened authoring direction (user, 2026-07-17):** “click somewhere in a grid, and then click an
author button” to open a focused dialog. The dialog must let the author choose **community place
cell** or **APC place cell**; choosing APC reveals a selector populated from the world's APCs. It
then accepts a brief description and offers explicit **Save** and **Cancel** actions. Save creates
the place at the clicked grid/location and refreshes the map; Cancel leaves authored state untouched.
The user expects this map-first workflow will **most likely replace landmarks**, reversing #23's
earlier editor-first direction, but that replacement is not yet locked and must not silently delete
or ignore existing landmark-authored places.

Acceptance evidence for the reopened slice: the selected point/grid is visibly retained while the
dialog is open; community versus APC ownership is persisted correctly; the APC list comes from the
current world; description round-trips through the authoring store and edit UI; Save produces one
immediate map result; Cancel produces none; malformed or conflicting entries fail visibly. Open
decisions: whether a separate place name is required or derived from the description, whether a
community place anchors at the exact click or grid center, default APC-place extent, and the explicit
migration/precedence rule among map-authored entries, `places.json`, existing landmark actors, and
runtime discoveries. **Classification:** design decision for the source-of-truth migration, then
loop-safe web/API/storage work plus live map QA.

Relates to: #15 (writes its manifest), #6c (the map surface), #2 (web app), #13 (bootstrap step 3).

---

## 17. Grid-first navigation — multi-leg routing between grid cells

**Status:** ✅ **DONE 2026-07-07; LIVE VERIFIED SR15 2026-07-13** — Dufus traveled from his authored
start to the authored village-square community cell and began greeting there. (Built per
`plan/specs/WP8-grid-first-routing.md`; suite
38/38). `route_planner.py` (pinned Bresenham cell line + leg state machine w/ skip-ahead +
B7b box-edge fine-approach), `_execute_routed_walk` leg executor (stuck replans, arrival idles),
en-route prompt narration, route-map path dots. LLM contract unchanged. v1 = straight-line legs;
sweep-data/no-go weighting is the #19c seam in `line_cells`. SR15 satisfied the coarse multi-district
live verification; landmark-level final approach and recovery remain canonical in #27. ·
**Source:** user, 2026-07-05 ("we don't really have a navigation system") ·
**Depends on:** #15 (✅ done); consumed #6b's corridor work

What exists: name→position resolution, the engine navmesh for *local* walking, lizard-brain
blocker facts + the B7b standoff, and the #6b route-map PNG on travel ticks. What's missing is the
**mid-scale**: agents travel greedily by vision, so when the destination isn't in frame they orbit
(Maren, SR2). A destination several districts away should become a *plan*: a sequence of grid-cell
legs, each leg a short navmesh walk the engine can actually do.

Pieces:
- **Route planner (pure, loop-safe):** grid A → grid B as a cell path (starts as a straight-line
  cell walk; obstacles/no-go cells can come later from sweep data) → waypoint list of cell centers,
  ending with a fine-approach to the place-cell anchor (stop at the 9×9 m box edge, B7b-style).
- **Leg executor:** a travel tick walks the *current leg's* waypoint (not the final destination),
  advancing legs on arrival; a blocked leg re-plans rather than wedging (re-uses the stuck/blocker
  facts — the cognitive loop stays the obstacle-solver per
  [[architecture-engine-agnostic-navigation]]; no engine patches).
- **Prompt surface:** the travel directive names the leg ("heading N toward cell (6,4) — 2 legs to
  the vegetable truck") so decisions and the decision log stay legible; the #6b route map draws the
  planned corridor instead of just the straight line.
- **Offline tests:** path generation, leg advance/replan state machine, arrival at box edge.

Relates to: #11.2 (grid-first decision + fine-approach), #6b (route map = the visualization of this
plan), #1 (resolution), B7b (standoff at arrival), `architecture_engine_agnostic_navigation`.

---

## 18. Live registered top-down map camera — real-time /map, registration by construction

**Status:** ✅ **Capture half DONE 2026-07-07** (user placed a `MAP_Camera` pawn — a
CameraCaptureActor subclass — and it's wired end-to-end): `POST /api/map/capture` aims the pawn
top-down over the world bounds (pitch −90, yaw −90 = north up/east right), captures 1920×1080 to
`web_ui/images/<level>.png`, and writes the exact camera footprint as `image_bounds` (the engine
capture's 90° horizontal FOV makes the frame computable — registration by construction, zero hand
calibration). "Re-shoot map" button on `/map`; image URL is mtime-versioned so a re-shoot shows
immediately. **Verified live in the editor (no PIE needed):** Maren's truck at (−8950, 160) lands
within ~4 m of its predicted pixel (the old hand shot was ~120 m off). MCP_World's registered
capture + calibration committed. **Live half DONE 2026-07-07 too:** the observe phase records each
agent's last seen position/facing (no extra engine traffic), runner serves `GET /positions`, web UI
proxies `/api/map/agents`, and `/map` draws red dots + facing tick + name every 3 s poll (runner
offline = no dots, never stale ones). Suite 40/40. **Also:** `generate_world_grid` now takes the
registration shot automatically (regrid → fresh registered map + calibration in one step; missing
MAP_Camera reported honestly, grid unaffected) — pose math shared in `agent_runtime/map_capture.py`.
**Still open:** optional re-shoot-on-timer; PIE verify of the dots during a real run. ·
**Source:** user, 2026-07-06 ·
**Supersedes:** the manual screenshot and #6c's open registration question; `image_bounds` stays
as the calibration mechanism (now machine-written).

The 2026-07-06 skew hurt twice: the overlay was wrong, *and the user placed actors against the
wrong map* (read "(2,6)" for what is really (6,6)). A hand screenshot can never be trusted; the
sim should shoot its own map with a camera whose frame is *defined* to be the world bounds — then
world→pixel is exact with zero calibration.

Pieces:
- **Engine-side capture:** an orthographic top-down capture (SceneCapture2D or equivalent bridge
  command) centered on the bounds rect, ortho width = bounds width, output aspect = bounds aspect
  → written to `images/<level>.png` on demand. No HUD, no toolbar, no guessing.
- **Bridge + runner surface:** `capture_world_map` callable from the web UI (a "re-shoot map"
  button — pairs with #21's sync) and optionally on a timer while the sim runs.
- **Real-time layer (loop-safe):** `/api/map` gains live agent positions from the runner
  (`get_character_transform` already exists); `map.html` draws moving agent dots + facing + name
  labels over the registered image, polling with the existing 3 s refresh. The *terrain* image
  refreshes on capture; the *agents* move every poll — that's the "see what's going on" view.
- **Offline tests:** agent-marker payload + rendering (TestClient); the capture itself is
  live-verify.

Relates to: #6c (the overlay engine this feeds), #16 (authoring needs a trustworthy map), #21
(same "world changed" workflow), #9 (dev-mode observability), #33 (logical grid offset; distinct
from image registration).

---

## 19. Keep APCs on sidewalks and roads

**Status:** **Folded into #27** on 2026-07-11; this section preserves the original problem and
option analysis. Do not implement (a)/(b)/(c) independently. · **Source:** user, 2026-07-06
("Maren is wandering into the corn field and people's back yards") · **Depends on:** #17

Agents cut straight lines through anything walkable — corn fields, yards. Navmesh says "walkable";
nothing says "socially, stay on the pavement." Options, not mutually exclusive:

- **(a) Engine-side navmesh area costs** — nav-modifier volumes over roads/sidewalks (cheap cost)
  vs everything else (expensive). Zero runtime code, immediate effect on every navmesh walk — but
  per-level editor work, invisible to the cognitive loop, and leans against
  [[architecture-engine-agnostic-navigation]] ("obstacles are solved by the cognitive loop, not
  engine patches"). Cheap immediate win if the user wants it; needs their call.
- **(b) Lizard-brain surface fact** — a ground probe reports *facts only* per the
  [[lizard-brain-contract]]: "surface underfoot: grass/road/pavement; nearest road ~4 m north."
  The LLM (and travel directive) get a standing rule: prefer pavement when traveling. Engine
  primitive inside, generic semantic label out.
- **(c) Route-planner weighting (#17)** — the grid-first planner prefers legs through cells whose
  sweep observations look road-like (community names/landmarks: "main street", "rural town road"),
  so multi-leg routes follow the street grid structurally instead of beelining.

Likely shape: (c) for the mid-scale + (b) for the local scale; (a) only if the user wants the
instant version. Offline tests: planner weighting (c) and the fact formatting (b) are both
loop-safe.

**(b) landed 2026-07-29, VLM variant.** User's explicit call this session: enforcement stays in the
LLM (no code-side blocking of `walk_to`) — the fix is making the disagreement between "navmesh says
walkable" and "you should not be here" an unmissable fact each tick, not a rule buried in prose the
LLM has to notice on its own. Rather than an engine ground probe (which would need per-level
authoring nothing in the repo currently has — see #53), `perception.py`'s existing per-tick VLM call
now also classifies `footing` (`pavement|road|dirt_path|grass|cultivated_field|water|other`) straight
from the image; `llm_router._seen_text` renders it as an explicit `FOOTING: <value>` prompt line
(`llm_router.py`); both `rules.md` files gained a non-negotiable line telling the LLM to turn back
when footing isn't pavement/road/dirt_path. Same session also added a companion fact for the
"moved farther from goal" half of the complaint: `agent_manager._attach_route_progress` now tracks
distance-to-destination tick over tick and stamps `delta_cm` on the route fact; `llm_router._schedule_note`
renders an explicit `PROGRESS WARNING` line when it's positive (noise-floored at `_PROGRESS_NOISE_CM`
= 200 cm). Offline: `test_seen_text_footing`, `test_perceive_parses_footing`, and the extended
`test_schedule_route_narration` in `test_route_planner.py`. **Not done, and deliberately not
attempted:** no action is blocked or auto-corrected — this is facts-plus-rules only, per the user's
choice. Live-run verification still owed: does the louder fact actually change behavior, or does the
LLM still walk into the field.

---

## 20. Movement pacing — Dufus is slow to get going

**Status:** ✅ **INSTRUMENTATION DONE 2026-07-15 — 47/47 offline green; tuning remains evidence-gated** ·
**Source:** user, 2026-07-06 ("Dufus takes a long time to move, but eventually does. Goes down street.")

Might be real (tick cadence, cooldowns, walk speed, LLM latency per decision) or might be persona
+ schedule (his own plan keeps him home until 08:30 sim time — flagged 2026-07-05 as "looks
stuck"). Don't tune blind: instrument first. Add per-agent timing to the decision log / replay
(#14): wall-clock from wake → first `walk_to` accepted → first actual displacement, and per-tick
latency broken into observe/LLM/act. Then decide whether the fix is pacing config, schedule
trimming, or nothing.

**Built:** each recorded decision now carries wall-clock `observe_ms`, per-agent parallel `llm_ms`,
and `act_ms`. Per-run movement startup tracks wake → first accepted walk and wake → first observed
displacement (10 cm jitter threshold), and adds each available milestone to subsequent timing data.
Wake entries carry available startup timing; replay's joined decision exposes the same timing object.
No cadence, schedule, persona, or walk-speed tuning was guessed.

---

## 21. "I moved things — sync the world" button

**Status:** ✅ **v1 DONE 2026-07-07** (built per `plan/specs/WP7-sync-world-button.md`; suite
37/37). `PlaceDB.purge_wake_seeds()` + `POST /api/world/sync` + a "Sync world" button on `/map`
that reports exactly what was deleted into the tip line and redraws. Deletes only
`source='wake-seed'` rows — authored (ground truth) and runtime (agent memories) rows survive;
legacy pre-WP6 rows are never guessed at. **v2 (manifest re-anchor from `actor` transforms) still
open — live-gated.** · **Source:** user, 2026-07-06 ("we also need a 'I moved things, sync the
world' button somewhere") · **Depends on:** nothing for v1; #15 for v2

Today, moving an actor in the editor silently invalidates wake-seeded owned places (and the map
png): Maren hunted a truck that was 9 m from where the DB said. The 2026-07-06 fix was Claude
deleting rows out-of-band — that must become a button.

Pieces:
- **v1 (pre-#15): re-seed from reality.** A button on `/map` or `/sim`: for every bound agent,
  read the live transform via the bridge, then delete that agent's *wake-seeded* owned rows and
  let the next wake re-seed at the new day-start spot. Reports exactly what it deleted (fail loud,
  per [[global-fail-loud]] — no silent "synced ✓"). Offline-testable logic + TestClient route;
  live transform read is thin.
- **v2 (with #15): manifest re-anchor.** Manifest entries optionally bind to an Unreal actor name
  (the truck mesh, the house). Sync reads those actors' transforms, rewrites `places.json` x/y,
  re-upserts PlaceDB, and re-runs schedule validation — authored places move *with* the world.
  Community cells whose landmarks moved get flagged stale for re-observation rather than deleted.
- **Pairs with #18's "re-shoot map" button** — one "the world changed" workflow: re-shoot +
  re-sync.

Relates to: #15 (authored ground truth), #18 (same trigger), #13 (bootstrap = the first-ever sync),
`feedback_drag_and_drop` (config complexity is our problem, not the user's).

---

## 22. Retire the MCP layer — the sim is standalone; the socket class moves to agent_runtime

**Status:** ✅ DONE 2026-07-08 (Sonnet executor) — suite 40/40 with mcp/fastmcp uninstalled ·
**Source:** user, 2026-07-08 ("we don't use mcp anymore. Do we have mcp code still?") ·
**Depends on:** nothing

MCP is dead weight now: the sim runs via `sim_runner.py` + the web UI, and dev-mode driving goes
over the runner's localhost HTTP API (`RunnerClient`), not MCP tools. But the raw Unreal socket
class (`UnrealConnection`, TCP 55557) still lives *inside* `unreal_sim_server.py`, so every
process — runner, web UI, offline suite — transitively imports the `mcp` pip package just to
borrow the socket (`unreal_bridge.py:38`). That's why the suite broke when `mcp` vanished from
the venv (2026-07-07 handoff) and why "pip install mcp" logs still appear in a repo that
supposedly dropped MCP.

Plan (all offline-testable):

1. **New `Python/agent_runtime/unreal_connection.py`** — move `UNREAL_HOST`/`UNREAL_PORT`, the
   `UnrealConnection` class, the module singleton, and `get_unreal_connection()` verbatim from
   `unreal_sim_server.py` (lines 32–255). Module logger `logging.getLogger("UnrealConnection")`;
   **no `logging.basicConfig`** — each process owns its logging (side effect: the stray
   DEBUG-to-`unreal_mcp.log` config that piggybacked on this import dies; `sim_runner.py` already
   configures its own).
2. **`agent_runtime/unreal_bridge.py`** `_send()` imports
   `from .unreal_connection import get_unreal_connection` instead of `from unreal_sim_server …`.
3. **Delete:** `Python/unreal_sim_server.py`, `Python/tools/` (only `simulation_tools.py` in it),
   `Python/scripts/agent_runtime/test_sim_tools_attach.py` (suite 41 → 40 by design — the surface
   under test is gone), `mcp.json`, `restart_unreal_sim_server.bat`,
   `Python/restart_unreal_mcp_stdio.ps1`. (`RunnerClient` **stays** — web UI + sim_runner use it.)
4. **`Python/pyproject.toml`:** drop `mcp[cli]` and `fastmcp` deps; drop
   `py-modules = ["unreal_sim_server"]`; fix the project description (it still says "MCP is the
   communication layer").
5. **Docs (light touch, only where misleading):** `README.md` (MCP-server section, restart
   section, `mcp.json` snippet), `Python/README.md` (add-a-tool paragraph → point at
   `unreal_bridge` + runner API). Historical docs (`Docs/`, handoffs, this backlog's history)
   stay as written.
6. **Verify (success criteria):** `pip uninstall -y mcp fastmcp` from the venv, then
   `scripts/run_tests.py` → **40/40 green** — the suite passing *without* the package installed
   is the proof the dependency is really gone. Plus `grep`-clean: no live `from mcp`/`import mcp`
   outside `plan/`/`Docs/`.

Relates to: #3 (independent sim lifetime — this finishes the decoupling), #8 in the autonomous
queue (retired the authoring half on 2026-06-28; this retires the rest),
`project_identity` (sim, not MCP bridge).

---

## 23. Landmarks — BP-authored ground-truth places (author the world in the editor, not a UI)

**Status:** ✅ Python half DONE 2026-07-08 (Sonnet executor) — suite 41/41; further landmark rollout
is paused while reopened #16 decides whether map authoring replaces landmarks · **Source:** user,
2026-07-08 ("during a
setup phase, the world author should place BPs at certain locations before sim runs… back away
from building a full blown sim UI, and just let the APCs build things") ·
**Depends on:** #15 (reuses the manifest pipeline as-is)

**Direction reset.** Authored ground truth moves *into the level*: the author drops a marker BP
where a place is; the sim reads it. The level becomes the single source of truth, so the whole
drift class of bugs (truck 9 m from where the DB said, wake-seed guessing, stale map coords)
stops existing — move the actor, the place moved. `/map` demotes to viewer/debug; #16
click-authoring stays as a fallback but is no longer the recommended path; `places.json` stays
supported (landmarks are simply a **second entry source** feeding the same `apply_manifest`).
Full sim-authoring-UI ambitions are parked: APCs build everything else themselves — landmarks
are their starting points.

**Vocabulary (locked, user 2026-07-08):** the term is **landmark** ("anchor" rejected — means
too much). Tiers: **landmarks** (author, editor, ground truth) → **community cells** (APC-built
at runtime) → **memories** (episodic/social/spatial).

**Authoring contract (user side, editor):**
- Create `Landmark_BP`: a cheap marker actor — editor billboard/sprite, `bHiddenInGame`, no
  collision, no variables needed for v1.
- Drop an instance and set its **actor label** to `Landmark_<owner>_<place name with
  underscores>`: `Landmark_maren_vegetable_truck`, `Landmark_dufus_home`,
  `Landmark_community_town_square`. Owner token = text up to the next underscore;
  `community` = shared/unowned. Name = the remainder, underscores → spaces.
- Detection is by **label prefix, class-agnostic** — renaming a real prop's label (the actual
  truck mesh) also works and pins the place to the prop itself.
- Caveat: UE auto-suffixes duplicated labels (`…_home2`) — the wrong name shows loud on /map;
  fix the label.

**Why label, not BP variables:** `get_actors_in_level` already returns
name/label/class/location for every actor (`UnrealMCPCommonUtils::ActorToJson`) — **zero C++,
no plugin rebuild**. Reading BP variables over the socket is a v2 (new plugin command +
rebuild) if labels ever feel clunky.

**Plan (Python half, all offline-testable):**
1. New `Python/agent_runtime/landmarks.py`:
   - `landmark_from_actor(actor: dict) -> dict | None` — `None` (silently) for non-`Landmark_`
     labels; malformed landmark labels (`Landmark_`, `Landmark_maren_`, blank name) are
     `logger.error`-ed and skipped (fail loud). Valid → the same normalized entry shape
     `load_manifest` returns: `{name, x, y, owner, community, extent_cm, actor}` with x/y from
     `actor["location"][0..1]`, `owner=None` + `community=True` for the `community` token,
     `extent_cm=PLACE_EXTENT_CM`, `actor=actor["name"]` (free #21-v2 provenance).
   - `landmarks_from_actors(actors: list) -> list[dict]`.
   - `merge_entries(landmarks, manifest_entries) -> list[dict]` — dedupe key
     `(owner or "", name.casefold())`; **landmark wins**, shadowed `places.json` entry is
     `logger.warning`-ed. Landmarks first in the returned list (apply's first-wins cell rule).
2. `agent_manager.py` `start_simulation` (the `places.json` block, ~line 249): fetch
   `self.bridge.get_level_actors()`, parse landmarks, merge with `load_manifest` entries, apply
   the merged list. `_manifest_present = True` iff the merged list is non-empty. Log counts
   separately: `landmarks: N (level), places.json: M, applied: {summary}`. Unreal unreachable →
   `get_level_actors()` returns `[]` → places.json only, `logger.info` says no landmarks found.
3. `/api/world/sync` (`web_ui/main.py`, #21): after `purge_wake_seeds`, rescan —
   `unreal_client.get_actors()` → landmarks → merge with places.json → `apply_manifest`.
   Response gains `landmarks` + `applied`; the `/map` tip line reports them. (`unreal_client`
   is already stubbed by existing tests — same pattern.)
4. **No schema change:** landmark rows are written `source='authored'` (they *are* authored
   ground truth); provenance is logged, not stored. `clear_authored()` convergence covers them.
5. Tests: new `test_landmarks.py` (parser valid/malformed/non-landmark cases, community token,
   underscore names, merge precedence, stub-actors → PlaceDB end-to-end: right cell + dx/dy +
   owner) + extend the sync-route test with stubbed `unreal_client`. Suite 40 → 41.

**Live half (user, next session):** create `Landmark_BP`, drop `Landmark_maren_vegetable_truck`
at the truck and `Landmark_dufus_home` at the house, press **Sync world** (or start a run) —
then watch wake behavior: Maren stays at her truck, Dufus home until 08:30. This replaces the
"click places on /map" step from HANDOFF_2026-07-07.

Relates to: #15 (pipeline reused), #16 (demoted to fallback), #21 (v2 re-anchor subsumed —
landmark rescan *is* the re-anchor), #18 (map viewer unchanged), memory
`project_landmarks_direction`.

---

## 24. start_sim.bat opens the cockpit page itself (one batch file, one double-click)

**Status:** ✅ Built 2026-07-08 (Sonnet executor) — live double-click verify remains the user's ·
**Source:** user, 2026-07-08 ("make the start_sim bat run so the web page just opens
and we only have one batch file") · **Depends on:** nothing

Half is already true: after #22, `Python/start_sim.bat` is the repo's **only** batch file
(engine build scripts aside). Remaining: today the user must read the console and type
`http://127.0.0.1:8765/sim` — the bat should open it in the default browser once the cockpit
is actually listening.

Plan:
- Before the blocking `uvicorn` line, launch a minimized background waiter:
  `start "" /min powershell -NoProfile -Command "for($i=0;$i -lt 30;$i++){ if(Test-NetConnection
  127.0.0.1 -Port 8765 -InformationLevel Quiet -WarningAction SilentlyContinue){ Start-Process
  'http://127.0.0.1:8765/sim'; exit } Start-Sleep 1 }"` — polls up to 30 s (first run can be
  slow while `uv` resolves), opens `/sim` exactly once when the port is live, exits silently if
  the server never comes up (the console error is already loud in that case).
- Banner text gains "the cockpit page opens automatically".
- No second .bat, no .ps1 file — the waiter stays inline so the one-file rule holds.

**Verify:** executor = static + snippet check only (run the waiter loop standalone against a
closed port with a short count → exits quietly; confirm exactly one repo .bat). **Live
double-click = user** (server boots + browser tab appears).

---

## 25. Landmark hardening — the author's typos are our problem

**Status:** ✅ DONE 2026-07-08 (Sonnet executor) — suite 41/41 · **Source:** user's first live
authoring attempt, 2026-07-08 — three landmarks, three hazards (screenshot):
`Landmarlk_Dufus_Home` (prefix typo → silently invisible), `Landmark_Maren_Vegitable_truck`
(owner case + name spelling), `Landmark_Maren_home` (owner case breaks the case-sensitive
`preferred_owner` tie-break in `find_owned_place` — Dufus resolving "home" could get Maren's) ·
**Depends on:** #23

Per `feedback_drag_and_drop`: config complexity is ours. Three fixes, all in the #23 scan layer —
**`place_db.py` matching stays untouched** (normalize at the boundary, not in the store):

1. **Owner casefold + case-insensitive prefix** (`agent_runtime/landmarks.py`):
   `owner = owner_token.casefold()` (agent ids are lowercase; `Community`≡`community` too), and
   the `Landmark_` prefix match becomes case-insensitive (`landmark_maren_home` works). Display
   name stays as authored (name matching is already case-insensitive downstream).
2. **Near-miss prefix detection.** New `scan_landmarks(actors) -> {"entries": [...], "suspects":
   [...]}`: a label whose first underscore-token casefolds to within **Levenshtein distance 1–2**
   of `landmark` (but isn't it) is a *suspect* — `logger.error`-ed and returned, never guessed
   into a place. Tiny inline DP levenshtein, no new deps. `landmarks_from_actors` stays as a thin
   entries-only wrapper (API compat).
3. **Visible sync report.** `agent_manager` logs suspects at error level at sim start.
   `/api/world/sync` response gains `landmark_places` (`["maren/vegetable truck", …]`,
   `community/<name>` for community) and `suspects` (raw labels); the `/map` tip line prints
   both — applied names in one glance, and `⚠ ignored near-landmark labels: … (check spelling)`
   when a suspect exists. The un-fixable case (a *spelled-wrong name* like "Vegitable") becomes
   visible by reading the applied list.

Tests (`test_landmarks.py` + `test_world_sync.py`): case-insensitive prefix accept; owner
casefold (`Landmark_Maren_home` → owner `maren`); `Landmark_Community_town_square` → community;
suspect detection (`Landmarlk_Dufus_Home` → suspect, `PlayerStart`/`MAP_Camera` → not);
`scan_landmarks` shape; sync response carries `landmark_places` + `suspects`.

---

## 26. Dead-end recognition — navmesh-reachable ≠ worth walking

**Status:** **Folded into #27** on 2026-07-11; this section preserves the observed failure and
candidate signals. Do not build a separate memory-only patch before the movement-controller
contract is approved. · **Source:** user, 2026-07-09, watching SR9+: *"Dufus took off down the street, came back
and oscillated back and forth into/out of a yard. Just because a nav mesh says a bot can walk
there doesn't mean they should. Dead end recognition another backlog item."*

The failure: greedy-by-vision travel wanders into pockets (yards, alcoves, fenced corners) that
are navmesh-legal but lead nowhere, then oscillates in/out because each re-decide sees the same
tempting opening. Engine-agnostic per [[architecture_engine_agnostic_navigation]] — the fix is
cognitive, not a navmesh patch:

- **Recognize** ("I entered this pocket and had to come back out") — candidate signals we already
  have: `_no_progress` / same-cell stuck counts, revisit-within-N-ticks of a just-left cell,
  route-leg regression (#17's leg counter going backwards).
- **Remember** — a "dead end toward X" note (place/episodic layer) so the *next* travel decision
  is told "the yard on your right dead-ends" as a fact ([[feedback_lizard_brain_contract]]: facts,
  not advice).
- **Route around** — #17's grid-first legs shrink the problem (a routed agent has less reason to
  enter a yard at all); #19's sidewalk/road preference then biases the fine legs. Spec after #17
  lands; this item holds the user's framing so it isn't lost.

---

## 27. Navigation executive + deterministic movement controller

**Status:** **APPROVED / IN PROGRESS** — authoritative scheduled-travel slice **LIVE VERIFIED
2026-07-15**; earlier robustness slices are also built. SR14 proved correct
semantic destination choice and progress, and SR15 (2026-07-13) proved arrival at the authored village
square with no stuck event. Persistent navigation-ticket, road preference, and deliberate obstacle/
dead-end recovery remain. · **Canonical for:** #19 road/sidewalk preference and #26 dead-end recognition ·
**Builds on:** #17 routed semantic travel (live arrival verified in SR15)

The current navigation path mixes two control models. A scheduled destination creates a routed
semantic trip, but the decision prompt still encourages frame-by-frame directional `walk_to`
actions. The model can therefore bypass or destabilize the cached route while deterministic state
only reacts after the movement has already gone wrong.

Proposed responsibility boundary:

- **AI executive:** choose or change durable semantic intent — destination, activity, interaction,
  or explicit cancellation. It does not steer every movement frame.
- **Persistent navigation ticket:** destination identity, endpoint, route cells, current leg,
  progress, retries, arrival, cancellation, and terminal failure survive across decisions.
- **Deterministic movement controller (lizard brain):** advance the ticket, keep personal space,
  follow socially valid surfaces, detect no-progress/regression/dead ends, retry locally, and report
  facts/outcomes to the executive.
- **Engine-neutral embodiment port:** expose pose, movement command/status, obstacle/person/surface
  facts, and stop; keep Unreal TCP details in the first adapter.
- **Spatial roles stay distinct:** grids index exploration/routing, place cells define semantic
  arrival, and `Landmark_*` actors provide authored anchors.
- **Headless reference world:** a tiny deterministic adapter proves route progress, recovery,
  arrival, and failure without Unreal or an LLM.

Approval gate satisfied 2026-07-11 when the user asked Codex to make the APC body less brittle and
write the movement code. Continue in small acceptance-tested slices; the persistent ticket/headless
adapter comes next, with road preference and dead-end recovery behind that seam.

**First slice landed offline (2026-07-11):** scheduled `wander`/directional movement is clamped
inside the active community cell or owned-place box (fixes Dufus's square→leave→return loop);
authored owned landmarks outrank runtime community aliases and wake seeds with conservative
one-edit typo tolerance (`vegitable truck` resolves for `the vegetable truck`); every decision gets
deterministic nearby-APC distance facts in addition to VLM sightings; the latest structured vision
result persists as `last_perception.json`; and the cockpit gained **Capture starts** so deliberate
editor placement can replace stale reset coordinates without hand-editing JSON. These are seams
toward the proposed controller, not the persistent navigation ticket itself.

**SR15 arrival finding (user visual acceptance, 2026-07-13):** Dufus traveled down the street and
stopped near the lower-left corner of the destination grid cell, not near the physical
`Landmark_Community_village_square` actor. That matches current code: community landmarks name a
30 m district, `_resolve_place_endpoint` returns `extent_cm=0`, and entering anywhere in the cell is
arrival. This proves coarse routing but exposes the missing fine leg. Design decision for the next
slice: a community landmark should continue naming the broad district while also retaining its actor
XY/extent as the scheduled-trip endpoint; shifting the whole grid (#33) may improve layout but must not
stand in for landmark-level arrival semantics. Acceptance: a trip first reaches the correct district,
then approaches the landmark extent, while generic community exploration may still treat cell entry as
sufficient.

**SR19 controller finding (2026-07-14):** the corrected start and #34 travel-sweep gate both worked.
Wake issued the correct deterministic eastbound waypoint from `(-10460,-800)` to `(-7500,-850)`, but
subsequent LLM decisions repeatedly said "east" while emitting relative ~15 m movement steps. Once the
avatar had turned, relative `forward` physically sent it west and then northwest into woods. The live
`route_map.png` made the split explicit: A (actual cell `(5,3)`) was disconnected from the still-cached
row-5 route to B (village square `(8,5)`). Next slice should make a scheduled named-place ticket
authoritative, reject ordinary relative movement while it is active, allow bounded directional motion
only for confirmed blocker/stuck recovery, and reconnect/replan when actual position is genuinely off
route.

Acceptance for the eventual umbrella item: a named-place trip cannot be replaced accidentally by
directional steering; local avoidance does not discard the destination; progress/failure is
observable; and the same navigator passes in both the headless adapter and Unreal integration.

**Authoritative-travel slice built (2026-07-15):** `_execute_world_action` now rewrites ordinary
scheduled `wander` and directional `walk_to` actions to the active named schedule destination before
relative movement can execute. This seam covers normal decisions and wake first-actions; the existing
grid router emits the deterministic next cell-center waypoint and replans from the observed cell on a
stuck report. The SR19 regression pins Dufus at cell `(5,5)`, facing west, while traveling to village
square `(8,5)`: an LLM `forward` action sends `[600,200,90]` east and caches the village-square route,
not a westward relative step. Recovery exceptions remain a later explicit policy decision. Full
offline suite: **44/44 passed**.

**Live acceptance (2026-07-15, user run):** Dufus went straight to the village instead of turning
west/east and leaving the route for the weeds. This closes the SR19 authoritative-control defect.
The umbrella item remains open only for the separately waiting community-landmark fine arrival and
bounded blocker/stuck recovery, road, and dead-end policies.

---

## 28. Runner tick safety — serialize entry points and validate cadence

**Status:** ✅ **DONE 2026-07-11** — manager-owned non-waiting tick gate; runner returns HTTP 409
for conflicting whole-sim/per-agent requests; `/status` exposes the active entry for cockpit UX;
invalid cadence rejected at runner and manager boundaries; full offline suite 42/42. ·
**Source:** architecture/correctness audit

`AgentManager._loop()` awaits `tick()`, but the HTTP `POST /tick` and
`POST /agents/{id}/tick` entry points can invoke the same manager concurrently while an automatic
tick is waiting on LLM work. That can overlap bridge calls, route/sweep state, decisions, and acts.
`start_simulation()` also accepts zero or negative `tick_seconds`, so the loop can become a tight
or invalid cadence.

Required behavior:

- one manager-owned async lock covers automatic ticks, whole-sim manual ticks, and per-agent pulses;
- a concurrent manual request returns an explicit busy/conflict result rather than waiting behind a
  long LLM call or entering the bridge;
- `tick_seconds <= 0` is rejected at the runner boundary and defensively by the manager;
- offline tests force overlap with a controllable await and prove only one tick reaches observe/act;
- existing sequential bridge and parallel-per-agent LLM behavior inside one tick stays unchanged.

Implemented in `agent_manager.py` and `runner_app.py`; regression coverage lives in
`test_pacing_and_reset.py` and `test_runner_api.py`.

---

## 29. Contain cockpit world and agent filesystem paths

**Status:** ✅ **DONE 2026-07-15 — 45/45 offline green** · **Source:** architecture/correctness audit ·
**Touches:** `web_ui/main.py` and web-route tests

Several cockpit routes join untrusted `{level}` and `{agent_id}` values directly under
`WORLDS_DIR`; the delete route passes that result to `shutil.rmtree`. Creation validates a new
agent id, but edit/read/delete paths and level names do not share a containment check.

Required behavior:

- one resolver validates identifiers and proves the resolved path remains under the expected
  world/agents root before every read, write, mkdir, or delete;
- reject traversal, separators, absolute paths, empty/reserved segments, and symlink escapes with a
  400/404 response; never normalize them into a different valid target;
- recursive delete operates only on the already-contained resolved agent directory;
- route tests cover encoded traversal and verify that an outside sentinel is untouched.

**Built:** one shared identifier/containment boundary now anchors world, agent, fixed child-file,
map-image, place, and replay paths beneath their trusted resolved roots before reads, writes, mkdir,
serving, or deletion. World/agent listings skip escaping links; replay indexing also rejects frame
symlink escapes. Regression coverage includes valid routes plus traversal, encoded backslashes,
absolute/reserved segments, world/agent symlinks, writes, replay, and recursive delete with outside
files and sentinels unchanged.

---

## 30. Declare the runner client's direct HTTP dependency

**Status:** ✅ **DONE 2026-07-15 — 46/46 offline green** · **Source:** architecture/correctness audit ·
**Touches:** `Python/pyproject.toml`, lockfile, dependency/import smoke test

`RunnerClient` imports `httpx` directly, but `pyproject.toml` does not declare it. The current
environment receives it transitively, which makes clean installs dependent on another package's
implementation details.

Add a compatible direct `httpx` dependency, refresh the lockfile, and verify a clean project
environment can import and construct `RunnerClient` without relying on test-only dependencies.

**Built:** `httpx>=0.25.0,<1` is now an explicit application dependency and `uv.lock` was refreshed.
The offline packaging contract parses `pyproject.toml`, requires the direct declaration, constructs
the default `RunnerClient`, and closes its HTTP client.

---

## 31. Event-driven cognition for agents settled at a known place

**Status:** ✅ **LIVE VERIFIED SR15 2026-07-13 — 43/43 offline green** · **Source:** user after SR14:
“Maren was observing a lot… if she is at a place / landmark and she knows she should stay put” ·
**Touches:** `agent_manager.py`, activity-state wording, and offline tick/pacing tests

The scene-diff gate currently forces every fourth stationary tick through the full perception and
decision path so an aimless stopped agent cannot freeze forever. That fallback is too broad for an
agent whose deterministic schedule and landmark geometry already say it should remain where it is.
In SR14, Maren was correctly at the authored vegetable truck but still produced five repeated
`idle` decisions. With both active roles on Anthropic, those decisions imply five paid vision calls
plus five paid decision calls, in addition to wake orientation.

Desired behavior:

- keep cheap engine/state sampling (position, movement, schedule time, place containment, nearby APC
  facts), but do not invoke vision or the decision LLM merely because a stationary-tick counter elapsed;
- suppress recurring model work when the current schedule says `act`, geometric place resolution
  confirms the APC is at the scheduled authored/known place, it is intentionally stationary, the scene
  is unchanged, and no relevant event is present;
- wake cognition immediately for a schedule/block transition, displacement/place change, movement or
  stuck/blocker state, a nearby APC arriving/leaving or interaction signal, a genuinely changed scene,
  or an explicit manual pulse; no paid periodic heartbeat by default for a settled routine;
- keep the anti-freeze fallback for agents that are idle without a grounded routine or whose place is
  unknown, so cost control cannot strand an agent that still needs to choose what to do;
- make cockpit/in-world activity truthful: distinguish cheap state sampling from an actual paid
  perception/decision phase rather than showing every eligibility check as `observing`.

Acceptance evidence (offline): a test runs a settled, at-landmark `act` agent beyond the old four-tick
threshold and proves the perceiver/decision router are not called; companion tests prove a schedule
transition and a relevant nearby/scene event re-enable cognition, while an ungrounded stationary agent
still receives the anti-freeze re-decision. The full offline suite must remain green. Final PIE
acceptance: in a short run Maren stays at the truck with no repeated `idle` decision rows until an
event or schedule transition occurs.

**Built:** `_observe_agent` now uses the persisted schedule and place geometry as a model-free sleep
gate; schedule/place/movement/scene/proximity events wake cognition, and explicit operator pulses bypass
the gate. Ungrounded agents retain the four-tick anti-freeze fallback. Cheap bridge checks now display
`sampling`, with `thinking` reserved for actual cognition. Regression coverage lives in
`test_event_driven_cognition.py`; `test_world_grid.py` now exercises its no-perception report directly
because manual pulse intentionally means “think now.” Full offline suite: **43/43 passed**.

**Live acceptance (SR15):** the run stopped at tick 8. Maren woke at the authored vegetable truck and
made two early `idle` decisions while Dufus was nearby/moving through her scene, then made **zero**
additional decisions from ticks 3–8 while she remained settled. Dufus continued independently, reached
the authored village square, and began greeting there. This is the intended event-driven result: paid
cognition occurred for the nearby/changed-scene events and slept once the settled scene stabilized.

**Classification:** loop-safe implementation with a focused live/PIE cost verification.

---

## 32. Visual cortex + two-tier image lifecycle

**Status:** **IN PROGRESS — core place visual memory and map inspection are live-proven; semantic
recall and transient-frame policy remain** (2026-07-15) ·
**Source:** user stopping-point review: “rebuild this image scene capture code so that a place image is
actually 4 images with north east south west as well as grid/place xy data”; follow-up: “We are
building visual memories” and every community or individual place cell needs a corresponding place
image · **Canonical for:** the
#9 observation-artifact review, #14 replay inputs, #7/#11 place surveys, and #31 event-driven cognition

The current capture path conflates three different things in one per-agent `observations/` directory:
ordinary forward-view samples, wake/sweep views, and replay evidence. `get_observation` writes a new
`SR<n>_observation_<timestamp>.png` before the image hash decides whether the scene changed, so identical
stationary scenes accumulate even when no VLM or decision call follows. Meanwhile `place_observations`
stores compass labels but not the durable source images that describe shared geography.

### Locked direction

- Introduce an engine-neutral **visual cortex** between the Unreal adapter and cognition. The engine
  port supplies raw pose/movement/proximity/capture facts; the visual cortex owns change detection,
  cached perception, image lifecycle, and the decision to request a VLM interpretation. Lizard brain
  consumes engine-neutral facts/reflex events; the executive LLM never sees Unreal actors, sockets,
  traces, capture commands, or raw coordinate plumbing.
- Separate **APC gaze/decision frames** from **place survey images**. A frame showing what Dufus or
  Maren looked at is transient evidence tied to a cognition event; it is not shared geographic memory.
- Every durable place, whether a community cell or an individual/authored/owned place, has a stable
  place identity and a corresponding **place-image record**. The rendered place image is one composite
  backed by exactly four cardinal source views: **N, S, E, W**. Its header/label band uses a black
  background with large white direction text so a VLM can reliably distinguish the views. Per the
  user's 2026-07-17 grounding requirement, the black label band also places
  `GRID X: <col>  Y: <row>` between N and S so the VLM can explicitly identify the source grid;
  precise world-coordinate overlays remain excluded.
- Store level, grid `(col,row)`, world anchor/extent, place identity/source, capture time, content hashes,
  and image revision as database metadata rather than drawing coordinates into the pixels. The stable
  place record points to its current `place_image_id`; each place-image revision points back to exactly
  one place. Filenames and identifiers are place/revision based, never `SR<n>` based.
- Place images are shared world facts rather than copies owned by whichever APC captured them. APC
  visual history is represented by visit/observation records linking `(agent, place, visited_at)` to the
  exact `place_image_id` revision seen then. Refreshing a place creates or promotes a new revision without
  rewriting the APC's historical visit. This yields a living, chronological record of where each APC
  has been without duplicating the same composite for every visitor.
- Place-scoped episodic memories remain distinct records linked to the same stable place identity. A
  place recall query can return the PlaceDB text description, current or historically seen composite,
  APC visits, and memories formed there.
- Semantic intent and routing stay separate: the LLM may resolve “the coffee shop I visited” from known
  places, descriptions, images, visits, and memories; the deterministic lizard brain then reads the
  resolved place's stored grid key and returns the grid route array. Coordinates belong in metadata and
  route facts, not in the VLM-facing composite.
- Place-survey images survive agent resets, day restarts, and ordinary sim runs. A full PlaceDB clean-out
  deletes their DB index and files together. An explicit refresh/re-sweep may replace a direction, but
  ordinary visits must reuse the existing set.
- Cheap event sampling should precede image capture where engine-neutral facts are sufficient. When a
  pixel sample is still needed for change detection, it may use a rolling scratch frame; durable storage
  occurs only under an explicit gaze/replay or place-survey policy.

### Open decisions before implementation

- **Transient gaze retention:** (a) overwrite one latest frame per APC, (b) keep a bounded ring per APC,
  or (c) content-address/deduplicate image blobs while decision/run metadata references the hash.
  **Recommendation:** (c), with a rolling scratch capture—identical pixels are stored once, replay can
  still prove what an APC saw in multiple runs, and `SR<n>` remains metadata rather than multiplying
  filenames. The user has not locked this choice yet.
- Retention for unique transient decision frames: forever, last N runs, size/time budget, or manual
  promotion. Place surveys are already decided: retain until full geographic DB reset.
- #14 replay must be redesigned around decision→image references rather than assuming every timestamped
  file in an agent directory is a meaningful frame. Existing SR-tagged files need a non-destructive
  migration/compatibility path.

### Cleanup and build plan

1. Inventory every image producer, consumer, directory, filename rule, PlaceDB observation field, replay
   assumption, and reset/delete path; classify each artifact as scratch sample, transient gaze evidence,
   cardinal source view, rendered place image, or legacy/unknown.
2. Write the engine-neutral visual-cortex contract and place-image state model. Lock stable place IDs,
   immutable image revisions, the `place_image_id` relationship, APC visit links, memory links, refresh
   semantics, and ownership/deletion rules before moving files.
3. Add schema migrations and repositories for place images, their four source views, APC place visits,
   and place-scoped memory lookup. Preserve existing PlaceDB descriptions and legacy observation rows;
   migration must be non-destructive and restartable.
4. Build and test the N/S/E/W compositor, including deterministic panel ordering, large white headings on
   black, a centered logical grid X/Y heading, consistent dimensions, missing-view rejection, and
   content hashes, without precise world-coordinate overlays.
5. Route capture through the visual cortex: cheap facts first, rolling scratch only when pixels are
   needed, durable place-image creation/refresh only for a place lifecycle event, and transient gaze
   persistence only under the separately chosen retention policy.
6. Expose engine-neutral recall operations for known/visited places, a place's image and memories, and
   an APC's chronological visual history. Resolve semantic place intent first; pass only the resolved
   grid key to deterministic route planning.
7. Update replay, reset, PlaceDB clean-out, cockpit/map inspection, and metrics around the new IDs;
   migrate or quarantine legacy SR-tagged images only after referential-integrity checks.
8. Verify offline with a fake engine and then in PIE with one community cell and one individual place,
   two APC visitors, a refreshed place image, semantic coffee-shop recall, and deterministic grid-route
   output.

### Implementation progress — 2026-07-14

- Wake surveys and travel-cell surveys now use exactly four absolute cardinal views instead of the old
  five relative wake views / eight 45-degree cell views. A place becomes survey-complete only when all
  N/S/E/W captures succeed; a name or breadcrumb alone no longer suppresses the missing visual.
- `place_images` stores immutable revisions, four source paths, the composite path, scene description,
  capture attribution, and place identity. Community and owned-place rows carry their current
  `place_image_id`; `agent_visual_history` links each APC to the exact shared revision it encountered.
- Pillow renders a deterministic 2x2 composite with large white N/S/E/W headings on black and no
  coordinate overlay. Shared composites have no sim-run identifier and are exposed under each APC's
  `observations/place_history/` by hard link when available (copy fallback).
- Wake reuses an existing place image and its saved textual description instead of re-surveying. A
  settled APC with a mapped scheduled place suppresses routine changed-pixel VLM work; manual pulses,
  schedule/movement changes, stuck/blocker state, and APC proximity events remain separate cognition
  paths.
- PlaceDB full reset removes place-image rows, shared composites, and APC history links. Agent/day reset
  preserves them. Focused compositor/schema/history/reset/suppression tests were added; full offline
  suite: **44/44 passed**.
- Still required before completion: live PIE proof of real camera composition and wake reuse; cockpit or
  model-facing semantic recall that can fetch a selected historical composite plus place episodes;
  migration/quarantine of existing SR-tagged observations; and the transient gaze retention decision.
- **SR21 map inspection follow-up (user, 2026-07-15):** Dufus live-produced community composites for
  cells `(5,5)`, `(7,5)`, `(7,4)`, and `(8,4)`, but `/map` represented them only by cell fill while
  authored owned places retained distinct purple markers. Add a center marker for every surveyed
  community cell; clicking it must expose the current N/S/E/W composite plus capture metadata without
  confusing it with an owned-place extent. The hover's current “N landmarks” is actually a count of
  confidence-qualified `(direction, VLM label)` rows (for SR21 `(7,5)`: 47 rows, 43 lowercased labels,
  52 sightings), not unique physical landmarks. Rename it to honest visual-observation metrics now and
  report label-row, distinct-label, and total-sighting counts; semantic synonym deduplication remains a
  later visual-cortex improvement. **Classification:** loop-safe API/UI/tests plus focused live map QA.
- **Map follow-up landed 2026-07-15:** `/map` now renders a blue center marker for every community
  cell with a current place image; its dialog serves the N/S/E/W composite plus revision, capturer,
  timestamp, and description. Hover reports visual-observation rows, normalized textual labels, and
  total sightings instead of claiming unique physical landmarks. Verified against the live SR21 DB:
  five markers rendered and Dufus's `(7,5)` 1280×848 composite loaded with no browser errors. Full
  offline suite: **44/44 passed**.
- **Marker cleanup 2026-07-17:** follow-up live inspection confirmed the 10 px blue community markers
  were still oversized and appeared off-center. Their visible footprint is now a centered 3×3 px blue
  square inside a transparent centered 11×11 px click target, so dialog behavior remains usable.
  Focused map-view coverage passes (58 checks); Terra independently ran the full offline suite, 47/47.
- **Grid-heading follow-up landed 2026-07-17:** place-history composites now show
  `GRID X: <col>  Y: <row>` between the N and S labels so the VLM's text response can explicitly state
  which logical grid produced the image. This intentionally supersedes the earlier blanket ban on
  coordinate text while retaining the ban on precise world-coordinate scene overlays. The production
  survey path supplies the place cell's actual col/row, and focused pixel/layout coverage plus the full
  offline suite pass (**47/47**). **Classification:** loop-safe compositor integration + focused image
  regression.

**Acceptance:** a written capture/state model names every image class and owner; an offline fake engine
proves unchanged samples cause neither a new durable file nor a VLM call; repeated identical decision
frames deduplicate under the chosen policy; both a community cell and an individual place receive a
valid N/S/E/W composite with readable white-on-black headings and its logical grid X/Y between N and S,
with no precise world-coordinate overlay; every place
record resolves its current `place_image_id`; APC visits retain the exact historical image revision;
place recall returns description + image + visits + memories; semantic recall of a previously visited
coffee shop resolves its grid and deterministic routing returns a grid array without asking a VLM to
read coordinates from the image; PlaceDB reset removes place-image rows/files, while agent reset does
not; and the same visual-cortex contract runs against a headless adapter and Unreal. Instrument image
writes, cache hits, VLM calls, and trigger reason so #20 can measure cost. **Classification:** design
decision now; then loop-safe Python/storage tests + focused live/PIE capture verification. Existing
bridge primitives appear sufficient; no C++ is assumed.

---

## 33. Configurable logical grid origin aligned to the authored world

**Status:** ✅ **DONE 2026-07-14 — implementation, MCP_World alignment, and live reuse verified** ·
**Source:** user map review: Maren’s place cell/landmark nearly crosses two cells and the grid should
align with streets/buildings · **Depends on:** #18 registered map; invalidates grid-keyed #11/#32 data

This is not another image-registration fix. `image_bounds` correctly maps the captured world image to
world coordinates but intentionally does not affect navigation. `WorldGrid` currently computes
`floor(world_coord / 3000)`; for MCP_World that forces the logical grid origin to approximately
`(-27000,-18000)` cm. The lattice therefore follows arbitrary world-zero multiples rather than the
authored street/building layout, which can put one semantic place or 9 m owned extent across a district
edge even while the overlay is pixel-perfect.

Desired behavior:

- `world_grid.json` can pin an explicit logical `origin_x/origin_y` (or equivalent offset modulo cell
  size), independent of world/image bounds; `locate`, `origin`, `cell_center`, route planning, place
  offsets, SpatialMap keys, web overlays, cursor readout, and generation all use the same transform;
- `/map` provides a preview-first way to adjust the lattice over the registered image and inspect which
  landmarks/owned extents straddle boundaries before applying it;
- applying an offset is treated as a **regrid**, never a cosmetic CSS shift: require confirmation, clear
  all grid-keyed PlaceDB/spatial/route data and #32 place-survey images, then rescan authored landmarks;
- world/grid round trips remain stable for negative UE coordinates and edge cells; image registration
  remains unchanged when only the logical grid offset moves.

Open decision: manual numeric offset, drag-the-grid UI, landmark/street-assisted suggestion, or a blend.
**Recommendation:** direct drag/numeric controls with snap + a preview report, optionally offering a
non-authoritative heuristic; the world author—not an algorithm—chooses which streets/buildings define
good district boundaries. Acceptance: offline transform/round-trip tests, map/API parity tests, a reset
transaction test proving no old `(col,row)` data survives, and PIE visual acceptance that Maren’s chosen
place/landmark grouping lies inside the intended cell. **Classification:** design decision + loop-safe
grid/map/storage work; final alignment is live/editor acceptance.

### Implementation progress — 2026-07-14

- `world_grid.json` now accepts `origin_x`/`origin_y`; WorldGrid locate/origin/cell-center math and
  per-agent SpatialMap use the same offset-aware transform while omitted/zero values preserve the old
  world-zero behavior.
- `/map` now has an **Align grid** panel with numeric 100 cm controls and a non-destructive preview.
  Preview redraws the empty lattice over the registered image and hides old place overlays so stale
  cell keys cannot be mistaken for the proposed layout.
- Applying requires an explicit destructive confirmation and runs through the standalone runner. The
  transaction stops the sim, preserves authored positions/bounds/image calibration, writes the new
  logical origin, and clears PlaceDB cells/images/history links, agent spatial maps, rendered/cached
  routes, and in-progress sweeps tied to the old grid.
- Offset round trips, SpatialMap parity, reset integrity, runner/client transport, confirmation gating,
  and map controls are covered offline. Full suite: **44/44 passed**.
- MCP_World accepted and applied logical origin X `0`, Y `650` cm. SR18–SR21 rebuilt place images and
  exercised cell centers/routes under that lattice. Future origin changes remain deliberate regrids,
  not normal run setup.

---

## 34. Defer community-cell surveys during scheduled travel

**Status:** ✅ **DONE 2026-07-15 — ordinary and survey-priority policies live-observed** · **Source:** SR18 live
review: Dufus began
the correct village-square route, briefly entered an adjacent unsurveyed cell while navigating around
the blue house/car, then the sweep interrupt replaced his route action and sent him backward to that
cell's center · **Depends on:** #11.1 sweep capability and #17 routed travel

The sweep gate currently fires on entry to any unexplored cell even when the schedule directive is
`travel`. A transient boundary crossing can therefore replace the deterministic route action, pull the
APC to an unrelated cell center for a four-view survey, and only resume the route roughly a minute
later. This makes a correct route look like a motel/house detour and lets exploration override the
agent's scheduled destination.

Desired behavior: scheduled travel has priority for ordinary APCs. Entering or clipping an unexplored
cell while en route must not start a survey or replace the routed movement action. An APC explicitly
configured with `survey_priority`, however, deliberately reverses that order: it routes to the exact
center of each encountered unexplored cell, completes N/S/E/W, and only then resumes its unchanged
scheduled destination. Existing in-progress sweeps may finish; wake surveys and non-travel survey
behavior remain unchanged.

Acceptance: an offline regression presents an unexplored current cell with schedule status `travel`
and proves the LLM's routed `walk_to` survives unchanged and no sweep state starts; companion coverage
proves a non-travel tick still starts the survey. A fresh PIE run should show Dufus follow the
village-square route without being pulled to a newly crossed cell center. **Classification:** loop-safe
Python behavior + live/PIE verification.

### Implementation progress — 2026-07-14

- `_act_agent` now gives both scheduled `travel` and `act` directives priority over starting a new
  community-cell survey. Unscheduled/idle survey behavior is unchanged, and the separate active-sweep
  continuation path still finishes a survey already in progress.
- **Policy update 2026-07-15:** the user requested a per-APC surveyor exception. `survey_priority=true`
  now makes surveys outrank `travel`/`act`; Dufus has this setting plus matching surveyor goals. The
  deterministic sweep still owns center arrival and all four cardinal captures before schedule resume.
- Regression coverage proves a named-place routed `walk_to` survives entry into an unexplored cell,
  starts no sweep state, and retains its deterministic waypoint; companion idle and continuation tests
  remain green. Full offline suite: **44/44 passed**.
- **Live evidence:** SR19 showed the ordinary travel gate caused no survey detour; its remaining
  west/north deviation was the separate #27 mixed-control defect. SR21 then live-proved the explicit
  surveyor exception: Dufus completed durable community composites at `(5,5)`, `(7,5)`, `(7,4)`, and
  `(8,4)` before resuming schedule travel.
- **Live follow-up 2026-07-17:** another user-observed run confirmed Dufus recognizes an unsurveyed
  grid cell, interrupts his current activity, and begins its survey. This reinforces the survey-priority
  behavior; the broader village-to-frontier expedition contract remains separate in #35.

---

## 35. LLM-directed survey expeditions from the village

**Status:** **IDEA / DESIGN GATE — requested 2026-07-15** · **Source:** user: “Dufus is the surveyor
and periodically does random unknown cell explorations, then heads back to village… survey the whole
map visually” · **Builds on:** #7/#11.1 sweep capability, #17/#27 routing, #32 place visual memory,
#34 `survey_priority`, #38's generic interruption lifecycle, and #13.4 pristine-run reset

Going straight to the village was the first live step, not the final survey behavior. Dufus should
periodically leave the village on a survey expedition, choose an unknown reachable grid cell, travel
there, center in the cell, capture the complete N/S/E/W visual survey, and return to the village. Over
repeated expeditions, shared visual coverage should be able to reach every reachable grid cell and the
map should make remaining unknown coverage obvious.

The behavior must preserve LLM agency. Do **not** hardcode a global “random walk then return” state
machine or a fixed cell sequence into `AgentManager`. The deterministic layer may expose grounded
facts/capabilities—unknown frontier candidates, reachability, coverage, route progress, survey
completion, and a durable current destination—and must own safe movement execution once the LLM has
chosen an intent. Dufus’s surveyor identity, desire to explore, decision to depart/return, and choice
among reasonable candidate cells should come from his goals/planning prompt and model decision. A
bounded fallback may prevent a lost/stalled expedition, but must be reported as a fact rather than
silently replacing the model’s intent.

Desired acceptance evidence:

- on a pristine #13.4 run, Dufus reaches the village, later chooses an unknown reachable cell from
  map facts, surveys it completely, and returns to the village without a hardcoded route;
- multiple excursions select new unknown cells rather than repeatedly revisiting completed cells;
- coverage reports reachable/visually surveyed/unknown counts and can eventually reach 100% of the
  reachable bounded grid (with unreachable cells reported, not retried forever);
- decision/replay logs show what facts the LLM saw, why it chose the target, the durable intent, and
  deterministic route/survey outcomes;
- ordinary APCs remain unaffected unless given the same explicit surveyor goal/policy.

**Open decisions for next session:** what event/cadence invites an expedition; whether the model sees
all unknown cells, a small frontier shortlist, or a tool query; how “random” is expressed without
making selection deterministic infrastructure policy; expedition retry/timeout bounds; whether every
trip must return to the village or the LLM may chain nearby surveys; and the #13.4 purge/retention
boundary. **Classification:** design decision, then loop-safe planner/context tests plus live/PIE
whole-map coverage verification.

---

## 36. Ordered primary and secondary goals per APC

**Status:** **IMPLEMENTATION + OFFLINE TESTS COMPLETE 2026-07-22 — 51/51; LIVE VERIFY PARTIAL** · **Source:** user: “Dufus and other APCs
to have multiple goals, primary and secondary etc. So when a goal is met, start running the next
goal.” · **Builds on:** #10 planner/sequencer, #31 event-driven cognition, #35's durable survey
intent, and the generic interruption lifecycle in #38

Each APC should have an authored or model-visible ordered portfolio of goals rather than one effective
goal. One goal is active, lower-priority goals remain available, and satisfying the active goal advances
the APC to the next eligible goal without a manual state edit. Goal priority, active state, completion
evidence, and transition history must be inspectable; completing one action or arriving at one waypoint
must not silently count as completing a larger goal.

Desired acceptance evidence: Dufus completes a primary goal, records why it is complete, activates his
secondary goal, and begins pursuing it on the next appropriate cognition event; an interruption pauses
and later resumes the same active goal unless an explicit reprioritization occurs; each APC advances its
own list independently; blocked, abandoned, and completed goals remain distinguishable in state and
logs. Open decisions: whether ordering is strictly primary/secondary or numeric priority, who may declare
completion (LLM, deterministic facts, user, or a combination), how recurring and blocked goals behave,
and how goals interact with daily schedules and direct user directions from #37. **Classification:**
design decision, then loop-safe goal-state/sequencer tests plus live/PIE behavior verification.

**New evidence 2026-07-21:** SR27 deterministically resolved `survey:6,6` with outcome `survey completed`,
but Dufus retained “I need to survey this cell thoroughly” as his current goal and immediately resumed
narrating more survey work. When a deterministic completion corresponds to the active goal, #36 must
consume that evidence exactly once and visibly clear or advance the goal; it must not infer completion
from free-form model narration.

**Additional live evidence 2026-07-21 (SR28):** Dufus immediately pursued the authored “go home and
find my hat” goal, reached his motel-room home, returned to his starting area for a deterministic survey,
went home again, and after the interruption resolved headed back toward the village. His persisted goal,
daily schedule destination, suspended route, and survey interruption each behaved plausibly in isolation,
but their arbitration produced visible backtracking. The #36 design must define which intent wins after
arrival and interruption resolution, preserve the exact suspended intent, and prevent schedule/goal
oscillation unless a logged goal transition or new fact justifies it. Acceptance evidence must include
this home → survey → resume scenario with no unexplained return to a superseded destination.

**Design locked 2026-07-21:** use an editable JSON agenda with deterministic execution state, not a
general-purpose behavior tree. Authored tasks use this minimum schema:

```json
{
  "tasks": [
    {
      "id": "morning_square",
      "start": "08:30",
      "end": "09:00",
      "place": "village square",
      "objective": "Travel to the village square",
      "completion": {"type": "arrive_at_place"}
    }
  ]
}
```

Keep authored agenda data separate from runtime execution. Runtime tracks each task as `pending`,
`active`, `interrupted`, `completed`, or `blocked`, with timestamps and grounded completion evidence.
Supported first-slice completion policies are `arrive_at_place`, `time_block_ends`, and
`time_or_llm_confirmed`; implementation must validate unknown policy names rather than silently guessing.
Unknown/stale community-cell surveys and direct chat are interruptions: they suspend the exact active
task and resume it afterward unless an explicit, logged reprioritization changes the agenda.

Existing `episodes.jsonl` remains episodic memory, but it is not the authoritative daily ledger: prompt
retrieval is relevance-based and `last_activity` stores only one string. Build a compact chronological
daily ledger from task transitions and interruption outcomes, then provide the decision LLM these three
grounded sections on every applicable cognition event:

- **Today so far:** completed/blocked work and serviced interruptions, with time ranges and evidence;
- **Right now:** the one active task, current place/destination, arrival verdict, and grounded route;
- **Next:** the next eligible unfinished task and the deterministic condition that activates it.

The deterministic executive selects/advances/resumes the task; the LLM chooses the in-character actions
used to carry out its objective. When Dufus arrives in `village square`, `arrive_at_place` completes the
travel task and the next eligible square activity becomes active, instead of asking the model to invent
a new goal. Other than bounded unknown/stale cell interruptions, Dufus follows his agenda until all
eligible tasks are done; only then does free goal-driven behavior become the default.

Acceptance evidence: schema validation and migration/fallback tests; deterministic transitions for
arrival, time expiry, LLM-confirmed completion, blocked work, and day rollover; Today so far / Right now /
Next prompt snapshots derived from runtime facts; survey and chat interrupt/resume tests preserving the
same task; no duplicate completion; and a live run in which Dufus completes morning work, services a
survey, reaches the named village square, advances to its next activity, and does not backtrack to a
completed destination. **Classification:** loop-safe data/sequencer/prompt work plus live/PIE behavior
verification.

**Implementation and verification evidence 2026-07-22:** authored data now lives in validated, atomically written
per-APC `agenda.json` files using schema version 1; deterministic execution and the chronological ledger
remain separate in ignored `runtime.json`. Dufus and Maren have tracked authored agendas, while APCs
without one retain a generated-schedule compatibility fallback. Runtime transitions cover pending,
active, interrupted, completed, and blocked work; arrival and time policies use deterministic facts;
`time_or_llm_confirmed` accepts only the exact active task, at its required place, after a successful
world action, with a bounded explicit evidence statement. Decision prompts receive authoritative Today
so far / Right now / Next sections, route/arrival facts, and interruption state. Agent inspection exposes
authored data, validation errors, execution state, and ledger context. Sol authored schema, persistence,
transition, interruption, prompt, manager-boundary, state, navigation, and real-agenda tests; Terra ran
the complete offline suite with **51/51 passing**. In the user's live run, Dufus completed
`morning_home`, traveled to the square with grounded arrival, and activated `square_morning` without
runtime agenda errors. That run exposed stale legacy `current_goal` text after the task transition; the
executive now synchronizes it to the active agenda objective. Restarted-process live verification of
that fix and an interruption/resume cycle remain required.

---

## 37. Direct operator chat and direction for a selected APC

**Status:** **OFFLINE COMPLETE 2026-07-21 — 50/50; LIVE PIE/MODEL VERIFY NEXT** · **Source:** user: “I want to have a
feature where I can ‘chat’ with a particular APC… interrupt [its] current goal… and give direction
to the APC.” · **Builds on:** #10.5 interrupt/resume policy, #12 interaction memory, #31 event-driven
cognition, #36 multi-goal state, and the generic interruption lifecycle in #38

Provide a user-facing control that selects one APC and opens a direct conversation with it. A new
message is a deliberate cognition event: the selected APC safely pauses its current activity/goal,
receives the user's words in character and with its relevant memory/context, and can accept grounded
direction. Other APCs continue unaffected. The paused goal and movement intent must remain explicit so
chat does not accidentally erase work or leave an invisible route running underneath the conversation.

Desired acceptance evidence: the user selects Dufus, sends and receives multiple chat turns, gives a
direction, and sees whether Dufus accepted, questioned, or declined it; his prior goal is visibly paused;
ending chat either resumes it or applies the new direction according to an explicit choice; the exchange
and resulting goal transition are auditable and available to appropriate memory. Open decisions: where
chat lives (cockpit, map, or both), whether movement freezes during the session, whether a direction is
a temporary interrupt or may insert/reprioritize #36 goals, how the user ends/releases the conversation,
and which transcript details persist. **Implemented MVP:** Simulation-cockpit selector and explicit
operator identity; open chat freezes the selected APC; multiple turns persist in the interruption;
“Guide with this” converts chat into temporary prompt-grounded direction; “Resume prior work” resolves
it without changing the prior goal/schedule/route. Permanent goal promotion remains #36 and permanent
transcript memory remains #12.2. See `plan/specs/WP10-direct-apc-chat.md`. **Classification:** offline
UI/control/state complete; live/PIE conversation, physical stop/guidance, and unaffected-peer verify pending.

**Approved UI follow-up 2026-07-21:** move all direct-chat cockpit controls to their own `/chat` page.
Place **Chat** immediately next to **Sim** in the primary navigation, remove the chat panel from `/sim`
rather than duplicating it, and preserve APC selection, operator identity, transcript, send, guide, and
resume behavior. Acceptance evidence: offline route/template tests prove `/chat` contains the complete
chat surface, `/sim` no longer contains it, navigation order is Sim then Chat, and existing API/control
tests remain green. **Classification:** loop-safe web UI; live/PIE chat verification remains required.

**Implementation evidence 2026-07-21:** `/chat` now owns APC selection, operator identity, transcript,
send, guide, and resume controls; `/sim` retains simulation status, survey progress, controls, and the
decision feed without chat duplication; shared navigation is Sim → Chat → Map. Focused web tests and
the full offline suite passed (50/50). Live chat behavior still requires PIE/model verification.

---

## 38. Generic APC interruption, resolution, and resume lifecycle

**Status:** **✅ OFFLINE COMPLETE 2026-07-17 — 49/49; live role-play remains #37** · **Source:** user: “APCs need a generic
interruption ability. Dufus has a ‘I need to survey this unknown cell’; Maren may have a ‘Root user
wants to talk to me’… This way, I can role play with the APCs and fine tune their behaviors.” ·
**Unifies:** #10.5 reaction gating, #11.1/#34 survey interruption, #31 cognition wake events, #36 goal
progression, and #37 direct operator chat

Create one engine-neutral interruption lifecycle rather than adding a separate override path for every
feature. An interruption identifies its source/requester, reason, relevant grounded facts, urgency or
priority, and what work should be resumed afterward. It can be queued/presented, accepted, deferred or
declined when agency allows, activated, resolved, and then either resume the suspended activity/goal or
explicitly convert into a new/reprioritized goal. The paused movement ticket, schedule directive, and
active #36 goal must remain inspectable throughout; an interrupt may not silently discard or continue
them underneath the new activity.

The same lifecycle should express at least these first cases:

- Dufus receives an internal/world opportunity: an unknown grid cell needs a survey.
- Maren receives a social/operator request: the world user's configured persona wants to talk with her.

The operator identity must come from world/user configuration or an explicit role-play identity, not be
hardcoded as “Root.” Conversation and accepted directions should reach the APC as in-world context so
the user can role-play and refine behavior, with an explicit policy for whether those directions are
temporary, remembered, or promoted into #36 goals.

Acceptance evidence: an APC with an active goal can service a survey interruption and resume the exact
suspended work; a selected APC receives a named-user chat interruption through the same lifecycle while
other APCs continue; simultaneous interrupts are ordered visibly; deferred/declined/expired interrupts
do not vanish; resolution and resume/goal-transition outcomes appear in state and decision logs. Open
decisions: priority and preemption rules, interrupt stacking versus a single active interrupt, optional
versus mandatory events, expiry/retry behavior, persistence across restarts, the player's in-world
identity model, and how lasting behavioral directions differ from ordinary conversation. **Classification:**
design decision, then loop-safe interruption/state-machine tests plus live/PIE survey and role-play
verification.

### Implementation progress — 2026-07-17

- Locked and built one durable `active_interrupt` plus a priority/FIFO queue in APC `runtime.json`.
  Safety/system defaults to priority 300, explicit operator/user work to 200, and surveys to 100;
  higher-priority work only preempts an active record while it is marked preemptible.
- Migrated Dufus's deterministic unknown-cell survey into the generic lifecycle. Its target cell
  persists, restart recovery reconstructs manager-local sweep state, the first deterministic step
  closes the preemption window, and terminal outcomes return control to the unchanged schedule/goal.
- Added generic request/resolve manager methods and localhost runner/client routes with an explicit
  requester identity. Active operator work wakes settled cognition and appears as a grounded prompt
  fact above routine activity; no `Root` identity is hardcoded.
- List/inspect surfaces now expose active, queued, and last-terminal interruption state. Lifecycle
  transitions append compact, sim-run-attributed entries to the existing decision feed.
- Reset day/agents clears interruption runtime; regrid cancels survey interruptions without discarding
  unrelated future kinds. Malformed persisted records fail closed.
- Test-first implementation landed in `a4937ad`, `52cee1b`, `f77616f`, `18056e0`, and `485a00c`;
  the last commit makes the promised pre-dispatch survey preemption window externally reachable and
  corrects preemption audit attribution. Terra's final delegated full offline run passed **49/49**.
  No Unreal/PIE or paid-model call was made.
- #38 deliberately stops at the generic control surface. Multi-turn chat/transcripts and accepted
  direction semantics remain #37; ordered/reprioritized goals remain #36.

---

## 39. Refresh stale community-cell surveys

**Status:** **OFFLINE + LIVE VERIFIED 2026-07-21 (SR28)** · **Source:** user after SR27: “cockpit
says cells that have place cell in center but text says needs reobservation” · **Builds on:** #7 survey
mechanics, #32 place-image lifecycle, and #38 survey interruptions

A saved center composite and a stale outline describe different facts: the composite exists, while the
cell has not been updated in over 24 real hours. The cockpit currently labels that state “needs
re-observation,” but `_should_sweep_here` rejects every cell that already has a current place image, so
no automatic path can perform the advertised refresh.

Desired behavior: an otherwise eligible APC visit may offer one deterministic survey interruption for
a stale community cell even when a prior composite exists; a fresh composite still suppresses redundant
surveys; completing the refresh replaces/advances the current place image and updates the cell timestamp
so it is no longer stale. Queueing and duplicate suppression must continue to use #38.

Acceptance evidence: offline tests establish fresh-existing → no sweep, stale-existing → one survey,
active/queued duplicate → no second survey, and completed refresh → fresh cell with a current composite.
Do not call vision or PIE in the offline test. Live verification should confirm one red cell refreshes
without sending an APC on repeated surveys. **Classification:** loop-safe runtime/database behavior plus
live/PIE verification.

**Implementation evidence 2026-07-21:** survey eligibility now requires a present, non-stale community
composite. A stale existing image proceeds through #38, creates the next immutable visual revision, and
becomes fresh when the capture is recorded; a fresh image still suppresses the survey. Focused
`test_cell_sweep.py` and the full offline suite passed (50/50). Live verification should confirm one red
cell refreshes once without repeat surveying.

**Live evidence 2026-07-21 (SR28):** Dufus refreshed stale cells `(5,5)`, `(6,5)`, and `(7,5)` exactly
once, producing revision-2 place-history composites and leaving the map at zero stale cells. Mark the
stale-refresh behavior live-verified; retain broader expedition/goal behavior under #35/#36.

---

## 40. Ground and expose deterministic survey progress

**Status:** **TELEMETRY LIVE-VERIFIED 2026-07-21 (SR28); VISIBLE YAW + NARRATION FIX PENDING** · **Source:** user after SR27: “Dufus says
he needs to survey cells, but I do not see him rotating.”

SR27 did execute distinct E/S/W/N captures and resolve `survey:6,6`, but each facing change is an
instant teleport rotation, individual heading steps are absent from the decision feed/cockpit, and the
ordinary LLM loop claimed views were saved both before and after the real deterministic sweep. Operators
therefore cannot distinguish actual survey work from invented narration.

Desired behavior: publish the active survey cell, phase, current heading, completed headings, and capture
result through inspect/API state and compact sim-attributed decision events; show that progress on the
web surface; ground cognition with that authoritative state and prohibit claims that an uncaptured
heading was saved. Completion clears transient progress. This item does not require a turn animation;
PIE must still verify that the actor's yaw changes for each real heading.

Acceptance evidence: offline tests observe ordered E/S/W/N progress, one event per attempted heading,
accurate success/failure sets, prompt facts derived only from deterministic state, no stale progress after
resolution/restart, and rendering of active heading/progress. Live verification confirms visible yaw
changes and matching captures. **Classification:** loop-safe runtime/log/API/web work plus live/PIE
verification.

**Implementation evidence 2026-07-21:** the persisted survey interruption now owns phase, current
heading, successful headings, failed headings, and the last result. Agent inspection/status and the Sim
cockpit expose it; each attempt emits a sim-run-attributed `survey_heading` event; restart recovery skips
already attempted headings; and prompts explicitly distinguish deterministic saved views from model
narration. Focused sweep/feed/prompt/web tests and the full offline suite passed (50/50). PIE must still
confirm visible yaw changes align with the E/S/W/N capture files.

**Live evidence and remaining defect 2026-07-21 (SR28):** all three surveys emitted successful ordered
E/S/W/N heading events and distinct capture files with no failed headings, confirming that deterministic
survey progress is live. After `(7,5)` resolved, however, ordinary cognition again narrated that headings
still needed surveying and claimed views had been saved even though no `survey_heading` action occurred.
The data layer correctly rejected redundant work, but prompt-only grounding was insufficient. Desired
behavior now includes a compact authoritative current-cell survey fact (fresh/active/completed headings)
and deterministic validation or suppression of unsupported “saved/surveyed” claims. Acceptance evidence:
after a completed survey, subsequent ordinary decisions neither claim missing headings nor claim a saved
capture without a matching deterministic event. **Classification:** loop-safe cognition/action-policy
work plus live/PIE model verification.

**Implementation evidence 2026-07-24:** every decide tick now attaches `observation["cell_survey"]` — the
deterministic fresh/due/active verdict for the cell underfoot, read from `current_place_image` + staleness
rather than from any interruption — and both prompt templates render it as a **Survey State Of The Cell
You Are Standing In** section that forbids both inventions explicitly. Prompt grounding alone was
insufficient in SR28, so `cell_sweep.filter_survey_claims` additionally drops, in code, any narration
sentence claiming a saved capture when no `survey_heading` ran that tick or claiming the cell still needs
surveying when its survey is current; dropped claims are logged as warnings rather than silently smoothed.
Unrelated uses of "saved" pass through untouched. Offline coverage: `test_survey_grounding.py` (the exact
SR28 string, supported claims surviving, ordinary narration untouched, empty/non-string/all-dropped edge
cases, and all four prompt verdicts). Full suite **54/54**. **Still owed:** the PIE visible-yaw check, and
a live model run confirming post-survey decisions stop inventing headings.

---

## 41. Make map survey counts and stale wording truthful

**Status:** **OFFLINE + LIVE VERIFIED 2026-07-21 (SR28)** · **Source:** SR27 cockpit review

The map assigns one exclusive display state: a named cell is `named` even when it also has `swept_at`
and a saved composite. This produced `named 8, swept 0` while multiple blue center markers proved survey
history existed. The stale tooltip simultaneously promises “needs re-observation” although the current
scheduler cannot refresh such cells.

Desired behavior: expose and count independent facts—named, has completed survey/composite, stale, and
owned—rather than treating named and swept as mutually exclusive. Until #39 is active, stale copy must
describe age without promising an unavailable action; after #39 lands it may explicitly say the cell is
eligible for refresh. Preserve the existing visual distinctions and center-marker click target.

Acceptance evidence: offline map/API/template tests cover a named surveyed cell contributing to both
counts, an unnamed surveyed cell, a stale surveyed cell with its blue marker intact, and wording that
matches refresh capability. **Classification:** loop-safe database/web UI work.

**Implementation evidence 2026-07-21:** `map_cells` now exposes independent `named`, `swept`, and
`surveyed` booleans. The API counts named, surveyed, mapped, stale, and owned without overlap errors;
the legend counts blue-marker community surveys rather than unnamed-only sweep state; and stale copy
states that an older saved survey is eligible for refresh under #39. Focused map tests and the full
offline suite passed (50/50).

**Live evidence 2026-07-21 (SR28):** after the three refreshes, the database/map facts reported 8 named,
6 surveyed, and 0 stale cells. The independent survey/stale accounting is live-verified.

---

## 42. Preserve actionable bridge/action error details in the decision feed

**Status:** **INVESTIGATION / BACKLOGGED 2026-07-21** · **Source:** SR28 log review

SR28 recorded one Dufus `speak_to` action as an error after roughly 15 seconds, then recovered on the
next attempt. The decision feed retained the action and error status but not the underlying bridge/error
detail, so the cause cannot be distinguished among timeout, target resolution, transport, or another
runtime failure.

Desired behavior: failed actions retain a bounded, safe diagnostic code/message and elapsed phase in the
sim-run-attributed decision event, without exposing secrets or unbounded provider output. Acceptance
evidence: an induced bridge/action failure can be traced from the decision feed to a specific failure
category, while successful events remain compact and existing recovery behavior is unchanged.
**Classification:** loop-safe logging/tests, with live/PIE verification for a real bridge failure.

**Implementation evidence 2026-07-24:** `memory_store.classify_action_error` maps a failed result to one
of `not_connected` / `timeout` / `target_unresolved` / `transport` / `runtime`, with the message whitespace-
collapsed, key-redacted, and capped at 240 characters, plus the elapsed act phase. `MemoryStore.record`
attaches it as `error` only when the action failed — successful entries keep exactly their previous keys —
and the console log line carries the category too. The Sim feed renders `⚠ <code>: <message> after <n>ms`.
An accepted-with-note recovery is deliberately not treated as a failure, so existing recovery behavior is
unchanged. SR28's case now reads as `timeout` at ~15021 ms instead of a bare error status. Offline
coverage: `test_action_errors.py` (every category, non-failures including accepted-with-note, message cap,
key redaction, and a feed entry that stays compact on success). Full suite **54/54**. **Still owed:**
live/PIE verification against a real induced bridge failure.

---

## 43. Make APC profiles discoverable and edit the JSON agenda

**Status:** **APPROVED 2026-07-21; NAV ENTRY IMPLEMENTED 2026-07-22; DRILL-DOWN/EDITOR PENDING** · **Source:** user: “I don't see the APC
profile page anywhere, did we lose that? I thought we had a way to set goals and etc on APCs in the
webUI?” · **Depends on:** #36 authored/runtime agenda contract

The APC editor still exists at `/worlds/{level}/agents/{agent_id}` and currently edits identity,
behavior settings, `current_goal`, `character.md`, `goals.md`, `rules.md`, and allowed actions. It appears
lost because the primary navigation has no clearly labeled APC/Worlds entry; users must click the
`Unreal World Sim` brand to return to the world list and then click an agent's `Edit` button. The page
also cannot edit the generated daily schedule or show structured task completion state.

Desired behavior: add an obvious **APCs** primary-navigation destination; keep the per-world agent list
and existing editor reachable from it; add a validated editor for #36's authored JSON agenda; and add a
read-only live panel showing **Today so far**, **Right now**, and **Next**, including active task state,
completion evidence, and any suspended interruption. Preserve the existing character/goals/rules/action
editing rather than replacing it.

**Cockpit drill-down requirement added 2026-07-22:** the user found raw endpoint JSON too painful to
read and requested “a way to see these JSON files in the cockpit in a nice drill down way, not just raw
web view file dump.” The cockpit/APC profile should render authored agenda tasks, runtime task states,
ledger events, completion evidence, interruptions, and other useful per-APC JSON as labeled summaries
with expandable nested details. Users should be able to collapse noise, distinguish authored data from
runtime facts at a glance, and navigate directly from the APC list. A raw JSON view may remain for
diagnostics but must be secondary/advanced, not the primary experience.

Acceptance evidence: navigation/template tests prove APCs are reachable without knowing a URL; Dufus's
profile round-trips a valid agenda without overwriting unrelated authored files; invalid JSON/schema is
rejected with actionable inline errors and no partial write; the runtime panel distinguishes authored
agenda from execution state; and live verification shows task transitions without a page restart.
The drill-down acceptance additionally requires nested objects/arrays to expand and collapse without
losing labels, task statuses and completion evidence to be readable without inspecting JSON syntax,
and malformed or unavailable runtime data to render a bounded error state rather than a file dump.
**Classification:** loop-safe web/storage tests plus live web/PIE verification. ~~**Open implementation
choice:** structured task-row editor and dedicated state components versus a reusable recursive JSON
viewer; retain a raw/advanced view either way.~~ **Resolved 2026-07-24 (Claude's call, user delegated —
open to veto): both.** Dedicated components own the shapes we know; a generic recursive renderer handles
nested/unknown data beneath them; raw JSON is a collapsed advanced view.

**Implementation evidence 2026-07-24:** `web_ui/static/apc_drilldown.js` provides the recursive renderer
(depth- and item-capped, `textContent` only so authored files cannot inject markup) plus dedicated Right
now / Next / Agenda tasks / Today so far / Survey / Other-state components. The APC profile page gained a
**live task state** panel polling `/api/sim/agents/{id}` every 3 s — task transitions appear without a page
reload — and an **Agenda** editor posting to a new `POST /worlds/{level}/agents/{id}/agenda` route that is
deliberately separate from `update_agent`, so saving an agenda cannot rewrite character/goals/rules.
`validate_agenda_text` mirrors `Agent.load`'s wording, and rejection re-renders the submitted text with
inline errors while leaving `agenda.json` untouched (verified: malformed JSON and a bad
`completion.type` both left the file byte-identical; a valid document round-tripped). A down runner or a
malformed payload renders a bounded message, never a file dump. Offline coverage:
`test_apc_agenda_ui.py` (editor + live panel + renderer present, reachable from the index, malformed JSON
and schema violations both rejected inline with the file byte-identical, valid round-trip, other authored
files untouched, starter template valid, bounded runner-down envelope). Full suite **54/54**. **Still
owed:** live verification in a browser against a running sim.

---

## 44. Resolve APC identity from engine facts, not from vision

**Status:** **DIAGNOSED 2026-07-24, NOT STARTED** · **Source:** Claude code/data audit ·
**Blocks:** #5 social memory, #12.1 don't-re-greet, #10.5 friend-interrupt, #12.2 interaction memory

Evidence: `last_perception.json` shows every character sighting labeled `unknown person`, while the same
tick's `observation["nearby_characters"]` carries the exact engine truth (`{"name": "Maren",
"distance_cm": ...}`). `SocialMemory` deliberately drops anonymous labels, so **no `social.json` has ever
been created for any APC**, `episodes.jsonl` records `saw: []` on every event, and `memory.json` fills
with interchangeable "Met someone new" entries. The identity exists and is discarded one layer earlier.

Desired behavior: identity resolution is deterministic and belongs to the lizard brain — when another APC
is within a plausible sighting range and inside the forward view (positions + yaw are already known),
that sighting is recorded under its `display_name`. Vision keeps describing appearance; it never decides
who someone is. The LLM still receives only semantic labels, never engine actor names.

Acceptance evidence: two APCs in view of each other produce `social.json` entries naming each other;
`episodes.jsonl` records non-empty `saw`; "People You Know" is non-empty on the next encounter; an APC out
of view or out of range is not recorded. **Classification:** loop-safe geometry/memory work plus live
verification that Dufus and Maren recognize each other.

**IMPLEMENTED 2026-07-24.** New pure module `agent_runtime/recognition.py`: `visible_characters` resolves
who is inside the forward view from position + yaw (2500 cm range, 110 degree FOV, left/center/right and
near/mid/far buckets), and `merge_identities` folds them into the vision character list — an identified APC
replaces at most one anonymous blob in the same bearing bucket, so Maren is not double-counted, while
genuine non-APC bystanders survive. `AgentManager._identify_visible_apcs` runs every tick *before*
`_record_sightings`, deliberately outside the `image_path` guard: recognition is geometry and needs no
frame. Someone behind the agent is skipped — proximity is not sighting. Offline coverage in
`test_recognition.py`, including the payoff assertion that social memory now populates and `meet_count`
accumulates across sightings. Suite **55/55**. **Still owed:** live confirmation that `social.json` appears
for both APCs and that "People You Know" is non-empty on a second encounter.

---

## 45. Deliver speech to the APCs who can hear it

**Status:** **DIAGNOSED 2026-07-24, NOT STARTED** · **Source:** Claude code/data audit ·
**Blocks:** #10.5 reaction gate, #12.2 interaction memory, #46

Evidence: `speak_to` sends the line to the engine and nothing else. There is no `heard`/`spoken_to`
concept anywhere in `agent_runtime/`. The decision prompt names exactly two things that may interrupt a
routine — seeing a known person, and *being spoken to* — and **neither is reachable**: the first is
blocked by #44, the second because speech is never delivered to another agent's observation. Both social
affordances in the reaction gate are currently dead code.

Desired behavior: an utterance becomes a fact for every APC within hearing range, surfaced in the next
decision as who said what, so responding is a grounded choice rather than an invention. Bounded: recent
utterances only, capped count, no replay of an entire conversation history.

**IMPLEMENTED 2026-07-24.** `speak_to` now publishes through `_record_utterance` into a bounded 20-entry
buffer carrying speaker display name, text (capped at 400 chars), world time, and position;
`_attach_heard_speech` delivers to any APC within `_HEARING_CM` (1200 cm — wider than the 300 cm standoff
so a greeting reaches someone approaching, narrower than sighting range so nobody overhears across the
district). A monotonic id plus a per-agent consumed marker means a line is heard exactly once and never
re-surfaces a tick later from across the square; an APC never hears itself. The prompt gained a **What You
Just Heard** section in both the vision and text-only (OpenAI) templates, which states plainly that nobody
spoke when the list is empty — otherwise the model is free to imagine a conversation. Offline coverage in
`test_recognition.py`, including manager-level delivery, the heard-once guarantee, self-exclusion, and the
distance gate. Suite **55/55**. **Still owed:** live confirmation that Dufus answers something Maren
actually said.

Acceptance evidence: Maren speaking near Dufus puts an attributed utterance in Dufus's next observation
and prompt; an APC out of range hears nothing; the reaction gate's "someone is speaking to you" clause can
actually fire. **Classification:** loop-safe runtime/prompt work plus live verification.

---

## 46. Multi-turn APC-to-APC conversation with retained content

**Status:** **PROPOSED 2026-07-24** · **Depends on:** #44, #45 · **Relates to:** #12.2

Once APCs can recognize and hear each other, a greeting should be able to become an exchange: turn-taking
between two APCs over several ticks, with what was actually said retained and recallable later ("last time
I saw Maren she was heading to her truck"). Today `_record_interactions` logs that *an* interaction
happened, with neutral sentiment and no content.

Open design choices before implementation: whether a conversation is a first-class interruption (reusing
#38's machinery) or a lighter per-tick state; how many turns before it must yield to the agenda; and
whether content lands in the episodic log or the dedicated store #12.2 has been waiting on.
**Classification:** design decision, then loop-safe implementation.

---

## 47. Reflection — synthesize observations into higher-level insights

**Status:** **PROPOSED 2026-07-24** · **Source:** Claude code/data audit ·
**Relates to:** the Stanford Generative Agents north star

Evidence: `EpisodicLog.consolidate()` compacts old events into count/place *summary rows*; nothing ever
produces an insight. `memory.json` is a flat list of same-shaped observations, so an APC never concludes
anything from its own history. Reflection is the mechanism in the reference architecture that turns a
memory stream into apparent understanding, and it is the one major component this sim has no analogue for.

Desired behavior: periodically (importance-triggered, not every tick — cost matters), an APC asks what its
recent memories imply, and stores a small number of durable higher-level statements that then feed recall
alongside raw episodes. Reflections must be attributable to the observations that produced them.

Open choices: trigger (accumulated importance vs. daily), how many insights to keep, and whether they
influence the agenda or only cognition. **Classification:** design decision, then loop-safe implementation
with one model call per reflection.

---

## 48. Separate character from engine chores in authored goals

**Status:** **DONE 2026-07-24** · **Source:** Claude code/data audit

Dufus's `goals.md` opened with "Be the village surveyor. In every cell that has not been visually surveyed,
go to the exact center and complete the full north, south, east, and west survey…" — survey *mechanism*
authored into *character*. It was presumably added to force surveying before the deterministic survey
interruption existed; that machinery now exists (#38/#39/#40), so the instruction competed with it and
crowded out the personality that makes Dufus legible as a person.

**Resolved:** the mechanism clause is cut and the authored content is re-pointed at what the user actually
wants Dufus to be — a forward explorer who ranges outward, captures what he sees, and gravitates back to
the village square to report. `goals.md` is motivation-only (see somewhere new, bring it home, never walk
back over covered ground, square is home base); `agenda.json` replaces the home/square/market loop with two
long open-destination expedition blocks (`place: ""`, `time_block_ends`) bracketed by `arrive_at_place`
returns to the square; `character.md` Role gains "accidental explorer".

**Code change — capture in place, no backtracking.** The doubling-back the user objected to is the sweep's
`goto_center` leg (`cell_sweep.py:119-124`): the APC walks back to the cell center before the N/S/E/W
capture. `_sweep_step` now passes `arrive_tolerance=world_grid.cell_size` for a `survey_priority` APC, so
"arrived" is already true anywhere inside the cell (max half-diagonal ≈0.71 cells) and the walk leg never
emits. Ordinary APCs keep walk-to-center. Covered by
`test_cell_sweep.test_explorer_surveys_in_place_without_backtracking` (verified failing without the fix).

**Constraint found while doing this:** `PlaceDB.record_place_image` *requires* all four cardinal views and
raises `ValueError` otherwise (`place_db.py:784-787`), and the community place image is the only shared
visual store — so "other APCs can use his knowledge" structurally depends on the four-heading capture.
Hence the fix drops the walk, not the survey. Removing the survey entirely (e.g. `survey_priority: false`)
would make Dufus explore without contributing anything other APCs can read.

Follow-on effects: the old absolute-priority clause no longer outranks the social reactions #44/#45 just
unblocked, #40's `filter_survey_claims` is no longer fed narration it must drop as warnings, and the goal
slots carry Dufus's actual hooks again. **Live check still owed:** confirm on a real run that he ranges
outward instead of orbiting the square, and that off-center captures still yield usable composites.

---

## 49. Record capture pose on place images (VLM training metadata)

**Status:** **OPEN 2026-07-24** · **Source:** raised by #48's capture-in-place change

Context the user supplied 2026-07-24: the survey behavior exists substantially to build a **custom VLM**,
and **Dufus is the training-data source** — he is the world-scanning APC, now expressed as an ordinary APC
carrying the survey attribute rather than a dedicated role (see the #7/#11.1 retirement).

`place_images` (`place_db.py:81-96`) records `col`, `row`, the four view paths, `description`,
`captured_by`, `captured_at`. It does **not** record camera x/y/z or per-view yaw, despite the schema
comment claiming "precise world coordinates remain metadata" — there is no such column. Camera pose is
therefore only inferable as "somewhere in cell (col,row)".

That was a tight bound while every capture happened at the cell center (±100 cm tolerance). #48's
capture-in-place change loosens it to anywhere inside a 30 m cell — up to ~21 m from center — so the same
`col,row` label now covers a much wider range of true camera poses. Fine for the in-sim lookup ("what does
this cell look like"); lossy for a training corpus where pose is a natural label.

Proposed: add `capture_x`, `capture_y`, `capture_z` to `place_images` (migration in `PlaceDB.__init__`,
same pattern as the existing `swept_at`/`swept_by` migration) and persist the per-view yaw alongside each
cardinal path. `_save_place_visual` already has the observation in hand at capture time.

**Classification:** loop-safe (schema migration + offline test); needs the user's go-ahead because it is
dataset design, not a bug. Alternative if pose is not wanted in the corpus: revert #48 to center capture
and accept the backtracking — explicitly rejected by the user on 2026-07-24.

---

## 50. Experiment: APC cognition on Sonnet 5 instead of Haiku 4.5

**Status:** **RUNNING 2026-07-24** · **Source:** user call — "see if switching from Haiku to Sonnet solves a lot of the problems"

Every APC ran its decision role on Haiku 4.5 (both Dufus and Maren are `tier: 2`, and the tier-2 default was
`claude-haiku-4-5-20251001`). Hypothesis: a chunk of what reads as puppet-like behaviour is model capability,
not missing machinery.

Changed in `llm_router._resolve_model`: both tiers now return `claude-sonnet-5`. Tiers are deliberately
collapsed so the live run is a clean A/B — model is the only variable. `_anthropic_call` `max_tokens` went
512 → 1024, because Sonnet 5 tokenizes ~30% heavier than Haiku and a truncated decision JSON costs a whole
tick. **Vision is untouched** — `perception.py` resolves the VLM independently and stays on Haiku 4.5.

Cost: roughly 3× per token vs Haiku ($3/$15 per MTok, intro $2/$10 through 2026-08-31, vs $1/$5).

Not yet evaluated — needs the live run. **To revert:** restore the two-tier map in `_resolve_model`.
Opus 5 is the next rung but needs `_anthropic_call` made thinking-safe first (thinking is on by default
there; `content[0]` becomes a thinking block and `max_tokens` would cap thinking + answer together).

---

## 51. Durable runner log — stop losing the only record of what a run did

**Status:** **OPEN 2026-07-24** · **Source:** Claude, blocked while diagnosing SR30 · **Blocks:** every
live-run diagnosis, including #50's evaluation

SR30 (2026-07-24, ~4½ min) could not be diagnosed after the fact. From disk it looked as if the agents had
stopped thinking: Dufus wrote **23 observation captures but zero decisions**, Maren wrote 6 captures and a
single decision, then both went quiet. Nothing on disk said why, because:

- `agent_decisions.log` records **completed decisions only**. Every skip, exclusion, and exception is
  invisible to it by design — an agent that never decides leaves no trace at all.
- `sim_runner` logs everything else to **stdout only** (`logging.basicConfig` with the default stream
  handler, `sim_runner.py:47`). No `FileHandler` is attached anywhere in the codebase. When the console
  window closes, the entire run narrative is gone. `AgentManager.start` already contains truncate-on-start
  logic that looks for a `logging.FileHandler` (`agent_manager.py:249-253`) — that branch has never had a
  handler to find.

The irony: the reasons *are* logged. `_observe_agent` explains every cognition skip at INFO ("settled at
scheduled place, cognition sleeping", "scene unchanged (idle 3/N), skipping LLM"), and `_act_agent` logs
`LLM phase exception` / `No decision - idling`. All of it went to a window that no longer exists.

One genuine blind spot remains beyond durability: agents dropped from the `ready` filter in `_tick_impl`
(`is_busy`, cooldown, open chat, inactive) are logged **nowhere**. An APC wedged `is_busy` silently
vanishes from the sim and no log line marks its disappearance — the leading suspect for Maren going quiet
after 22:27:00.

Desired behavior:

1. The runner writes its full log to a file next to `agent_decisions.log`, truncated per run, so a closed
   console costs nothing.
2. Every tick accounts for **every** active agent — decided, skipped (with reason), or excluded (with
   reason). A silent disappearance becomes impossible.

Acceptance evidence: after a run, `logs/sim_runner.log` explains each agent's every tick without the
console; an agent stuck `is_busy` produces a visible per-tick line naming the cause.

**Classification:** loop-safe logging work. This is the "fail loud" rule applied to the sim's own loop —
"nothing in the log" must never again be the same observation as "nothing happened".

**IMPLEMENTED 2026-07-24.** Three changes, all in `agent_manager.py` plus a RUNBOOK correction:

- `_attach_run_log` adds a root `FileHandler` at `logs/sim_runner.log`, alongside `agent_decisions.log`,
  carrying the runner's own format and `SimRunFilter` so entries stay SR-tagged. Called from `start()`
  immediately after the SR tag is allocated — the log directory is only known once a level's agents load,
  which is why this lives in the manager rather than in `sim_runner.py`. Opened `mode="w"` (truncate per
  run, matching the decision log) and idempotent, so repeated runs in one process reuse one handler. It
  also raises the `AgentRuntime` logger to INFO explicitly: hosts that never call `basicConfig` (web UI,
  MCP) leave root at WARNING, which would drop every INFO record before any handler saw it. A failed open
  logs an error and leaves the console path working rather than taking the run down.
- `_tick_impl` now names every active agent excluded from the tick — `busy`, `cooling down (Ns)`,
  `chat open` — via `_not_ready_reason`, which mirrors the ready filter's own order. This was the one
  genuinely unlogged path: a wedged `is_busy` APC previously left the simulation in total silence.
- `_loop`'s existing `Tick #N` line gained a per-agent outcome roll-up from `_tick_outcomes`
  (`dufus=idle(scene_unchanged), maren=speak_to`), and a tick where **no** agent ran now logs that fact
  instead of passing unremarked — the exact shape of the SR30 blackout.

Verified by direct exercise of the three helpers (not the offline suite): the handler creates and writes
the file, a second call adds no duplicate handler, the roll-up renders reasons and returns empty for an
empty tick, and each not-ready branch returns its expected label. **Still owed:** the next live run — read
`logs/sim_runner.log` afterwards and it should explain every one of Dufus's silent ticks.

---

## 52. Simplify Dufus's goal stack — explore-and-survey only, drop the agenda juggling

**Status:** **RESOLVED 2026-07-30 (built; live verify owed)** · **Source:** user, live-run frustration: "we are asking too much of Dufus
with regards to our software technology. First he tries to go home and eat breakfast then he says go to get
his hat, then he gets interrupted."

> **⚑ Resolution (user decisions, 2026-07-30):** all three design questions answered and built.
> **(1)** Dufus **keeps** `agenda.json`/the scheduler — but the agenda is now a single all-day
> `survey_expedition` task (07:00–22:00, empty place, `time_block_ends`); no bypass code needed.
> **(2)** **Silent surveyor** — `speak_to`/`inspect_object`/`follow_character`/`attack`/`flee` dropped
> from `tools.json`; greet-everyone rule, "be friends with everybody", and the hat goal removed from
> the authored files. `goals.md`/`character.md`/`rules.md` re-pointed at one job: survey unsurveyed
> ground, never re-walk covered ground. **(3)** Dufus-only for now — no generic role abstraction
> (simplicity first; generalize when a second surveyor exists). **Also: Maren parked**
> (`is_active: false` — she still spawns/binds but never ticks) until Dufus does his one job.
> User framing to preserve: this is not just exploring — the survey task is how the system builds a
> **custom VLM** ([[project_dufus_vlm_training_corpus]], #49, #53); the surveyor APC is the
> load-bearing character. Shared prompt code deliberately untouched. Live verify: coverage grows past
> 6/204 cells with zero home/square/social detours.

Dufus is [[Dufus = VLM Training Corpus]]-scoped already (the world-scanning survey APC), but his
agenda/schedule still carries ordinary-life tasks (breakfast, fetch hat, etc.) that compete with survey
work for the same cognition slot and get preempted mid-chain. Each preemption is itself a source of the
"asks too much of the LLM" problem raised this session (agenda item, then override, then resume — more
state for the LLM to track correctly, more surface for it to get wrong). The user's proposed fix: strip
Dufus down to one job — wander the world and capture pictures (survey) — and remove the daily-life
schedule entirely for this character, rather than fixing the interruption/resume plumbing under it.

Needs a design pass before implementation:
- Does Dufus keep `agenda.json`/`goals.md` at all, or does his loop bypass the scheduler entirely and run
  survey/explore as the only behavior?
- Does he keep recognition/greeting/speech (social behaviors), or is he purely a silent camera?
- Does this apply only to Dufus, or does it imply a general "role" simplification for any future
  survey-only APC?

**Classification:** design-gated, not loop-safe — a character-scope decision, needs the user's call before
touching `agenda.json`/`goals.md`/`rules.md` or the scheduler's handling of him.

---

## 53. Capture navmesh-vs-semantic traversability disagreement as VLM training signal

**Status:** **OPEN 2026-07-29 — not building yet, explicit user call** · **Source:** user, this session:
"I know I can go forward (Unreal Nav Mesh), but I know I am blocked via LLM thoughts. I think this is the
big value of the system... Dufus or any 'surveyor' should be returning this information. This information
will be used to build a VLM for the particular world."

Distinct from what's already tracked:
- **#19/#27** (folded together) already identified the underlying disagreement — "navmesh says walkable;
  nothing says socially, stay off" (the corn-field/yard case, verbatim from 2026-07-06) — and proposed a
  lizard-brain surface fact (ground probe: "surface underfoot: grass/road/pavement") as one fix option. That
  is a same-tick *runtime* fact for the LLM to act on, not a stored training example.
- **#49** already establishes Dufus as the training-data source for a future custom VLM and proposes storing
  camera pose (`capture_x/y/z`, yaw) on place images — but only geometry, not any semantic/behavioral label.

What's net-new here: whenever a survey-flagged APC's navmesh reports a location as walkable **and** the
LLM's own reasoning rejects it (rules-driven refusal, "that's the corn field", "that moves away from my
goal"), that disagreement is itself a labeled example — pairs the frame Dufus already captures with a
ground-truth "physically possible, semantically rejected" tag and the LLM's stated reason. A future VLM
trained on this corpus could eventually report "cultivated field ahead, avoid" as a sensed fact the same way
the lizard brain already reports surface/obstacle facts ([[feedback_lizard_brain_contract]]), closing the
loop without ever hand-authoring zone geometry (e.g. the corn field's bounds, which nothing in the repo
currently records).

Needs before implementation (none of this is decided):
- Where the disagreement gets logged — a new capture record tied to `place_images`, or its own table —
  and whether it's Dufus-only or any APC carrying the survey attribute.
- What counts as "the LLM blocked it": a structured field the decision schema doesn't carry yet (today
  `thought_summary` is free text), vs. a rules.md-driven rejection the validator can detect deterministically.

**Classification:** design-gated, explicitly deferred — dataset design for a not-yet-started custom VLM,
not a bug fix. Relates to: #49, #19/#27, [[project_dufus_vlm_training_corpus]].

---

## 58. Breadcrumbs + remembered ground — escaping an obstacle with facts, not guesses

**Status:** **BUILT 2026-08-12, unverified live** · **Source:** user, this session: *"when the LLM says
'Looks like I cannot pass this obstacle, corn, etc' it should know to back track and maybe that's where
a breadcrumb idea needs to happen. I would much rather have the APC look at existing surveys in its
immediate area and say hey, this looks like a clear path, even if that path was walked through before."*

Supersedes the `RECENT FOOTING` fact from #57, which was necessary but not sufficient: it listed
*surfaces* with no *places* attached, so `cultivated_field -> grass -> cultivated_field` named the trap
without naming anywhere to go. The rule it fed ("pick a heading at right angles") was a guess dressed as
guidance — and the ground truth needed to answer properly was being thrown away every tick.

Landed:
- **`cell_ground` table (`place_db.py`)** — every footing reading an APC reports is banked against its
  cell, shared across agents like all PlaceDB geography. Keyed by `(col, row, footing)` with counts, so a
  30 m cell that is half road and half field reports both rather than flip-flopping between two truths.
  `record_ground` / `get_ground`; included in `reset()`.
- **Known ground in the direction sense** (`_direction_places` → `_direction_lines`) — each neighbour cell
  now reads `cell 4,5 — unexplored, ground walked: gravel_road x7`. A name meant a cell was *seen*;
  footing means it was *walked*. "Ground never walked" is stated explicitly so a gap never reads as a
  clean bill of health.
- **BREADCRUMBS replaces RECENT FOOTING** (`_drop_crumb` / `_stamp_footing` → `_breadcrumb_text`) — the
  last 8 *legs* with cell, heading, distance and the footing each ended on, plus `RETRACE`, the recorded
  headings reversed in order. Per leg, not per cell: SR37's whole ping-pong happened inside two cells and
  a per-cell trail would have rendered it as one motionless crumb.
- **`rules.md`** — reach for known-good ground first (walking it again is not wasted motion), then the
  most recent proper-footing crumb; retrace *as many legs as it takes*, since one step back out of a field
  walked four steps into just puts you back in the field.

All facts, no blockers — consistent with [[feedback_facts_not_blocking]] and the lizard-brain contract
(`RETRACE` is arithmetic on headings already stated, the same derivation as `came_from`, not advice).

**Open for the next live run:** whether Dufus actually reaches for a previously-walked road instead of
reversing blindly, and whether the per-direction ground line is enough on a *cold* DB — on a fresh world
every neighbour reads "ground never walked" until he has been somewhere, so early ticks still fall back to
breadcrumbs and the view. Suite 57/57 after the change; nothing yet pins the new behaviour (build → verify
live → pin with tests).

---

## 59. SR39 — three broken instruments, and the corn field's real cause

**Status:** **BUILT 2026-08-12, unverified live** · **Source:** SR39 log review.

SR39 was the first run on #58. Two good signals: **`survey_here` fired three times** (5,5 / 6,5 / 6,6,
twelve headings, zero failures) against once-in-twenty in SR37, so the low survey rate was the footing
trap, not reluctance; and `cell_ground` recorded correctly, including the mixed cell 6,6
(`pavement x10` + `cultivated_field x3`). Dufus's own words carried the new facts back — *"aim for the
pavement patch I know first"*, *"need to retrace toward the pavement"*.

Then five defects, three of which were corrupting **every** run before this one:

1. **`survey_here` died at wake.** The wake path called `_execute_world_action` directly, so the verb
   reached the bridge, which answered `Unknown action: survey_here`. The first decision of every run was
   discarded. Both paths now share `_resolve_survey_here`.
2. **Stalled orders reported `success`.** The last four ticks are identical — `(-6013.2, 2609.9)`,
   `moved_cm: 0.0`, `result_status: success` — and Dufus worked out he was wedged (*"I'm stuck moving"*)
   before we told him. Accepted is not moved: `_last_move_fact` states the achieved displacement against
   the order that asked for it, `_sense_note` tells the model, and a stalled order now logs a WARNING and
   a `stalled_order` field.
3. **The model's survey decision never got a log row** (early return skipped it), and the interrupt still
   said `source: "world"` / *"needs a community survey"* — text that was true when code seized the tick
   and a lie once surveying became the model's own action. Now `source: "agent"` and the decision is
   logged before the handoff tick.
4. **Two coordinate systems, both shown to the model.** `WorldGrid.locate` returns `key` (raw signed
   index, "-3,0") and `col`/`row` (bounds-relative, "6,6"); `_grid_text` printed both in one line. SR39
   has Dufus reasoning about "cell -3,0" all run while PlaceDB, the decision log and the survey messages
   recorded "6,6". **We were grading his map sense through a mistranslation.** `col,row` wins everywhere
   the model can see (`_cell_label`); `key` stays internal to SpatialMap.
5. **The corn.** Not a facts problem — he had the facts. SR39, verbatim: *"the lime cornfield edge to my
   right is unwalked ground worth pushing toward — but it's crop field, so I should aim for the pavement
   patch I know first"* — and then walked `direction:right`, into the field. Two causes, both ours:
   - **"Never walked" is a reward.** His one job is unsurveyed ground and the direction list advertised
     the corn cell as exactly that. No warning beats a goal. Fixed by giving the map a third state:
     `refuse_cell` / `allow_cell` (new `cell_refusals` table, reason mandatory, shared across APCs,
     withdrawable). A refused cell stops reading "unexplored" — **it stops being work**. Nothing in code
     blocks the walk; the APC declares, code only stops forgetting.
   - **The next-cell map was keyed by forward/left/right** while doctrine told him compass words are the
     vocabulary — so the only map he had spoke the words we told him not to trust. 13 of SR39's 15 walks
     were body-relative. `_direction_places` is now compass-keyed and no longer needs rotation at all.
   - Also: this tick's sightings are folded onto the matching compass line (`you can see tall corn rows
     (near)`), so the reason not to go and the invitation to go are finally on the same line.

Also fixed: a decision lost to `Extra data: line 1 column 207` (valid JSON with prose after it — now
parsed via `raw_decode`); 312 lines of `Existing connection failed: 'NoneType'...` (a cached connection
whose socket is already None is the ordinary state, not a warning); `_offset_location` snapped to the
nanometre, because `cos(270°) = -1.8e-16` put a due-north step a hair west and could file a **durable**
refusal against the neighbouring cell; `_pie_activity` no longer crashes a decision when there is no
bridge.

**Open for the next run:** does he refuse the corn from outside instead of entering it; does he use
compass words now that his map does; does `stalled_order` appear when he wedges. Suite 57/57; the new
behaviour is smoke-tested but not pinned (build → verify live → pin with tests).

---

## 60. SR40 — the corn field is solved; the new wall is a mailbox

**Status:** **#59 VERIFIED LIVE 2026-08-12. Follow-on fix BUILT, unverified.** · **Source:** SR40 log review.

**SR40 is the first run with no cultivated_field footing at all.** Every reading was road or pavement.
Dufus named the hazard at wake — *"south is a cornfield edge I should not enter"* — and never went near
it. Note *how*: he never called `refuse_cell`. The corn cells (5,6 / 6,6 / 6,7) were already recorded as
`cultivated_field` in `cell_ground` from SR39, so the compass-keyed direction lines showed him rough
ground before he stepped in it. **#58's ground memory did the work; #59's refusal state was not needed
and remains unexercised.** Do not claim it as verified.

Every #59 fix confirmed live:

| Fix | SR39 | SR40 |
|---|---|---|
| `survey_here` at wake | `error: Unknown action` | `success` |
| Compass vs body-relative walks | 2 of 15 compass | **15 of 15 compass** |
| Cell naming in his thoughts | "cell -3,0" (log said 6,6) | "cell 7,5", "cell 8,6" — matches |
| Survey decision rows | none (invisible) | `action_type: survey_here`, `survey_pending` |
| Interrupt provenance | `source: "world"` (false) | `source: "agent"`, "dufus asked to survey (7,5)" |
| Stalled orders | `success`, silent | `stalled_order` on 8 rows + WARNING |
| Reconnect noise | 312 WARNING | 0 WARNING (292 INFO — see below) |
| Malformed JSON drops | 1 | 0 |

**The new failure:** eight ticks wedged at `(-3200.7, 670.2)` between a person and a mailbox, alternating
`east → southeast → east → southeast`, each thought correct in isolation — *"east is blocked, so I'll
angle southeast"*, then *"southeast is blocked, so I'll head east"*. Structurally identical to SR37's
footing ping-pong: `stalled_order` reports only the *immediately previous* order, so the other heading
always looked untried. One tick of memory cannot see a two-item loop from inside it.

Fixed the same way that one was — by accumulating:
- **`_record_attempt` / `tried_here`** — every heading attempted from this exact spot with its achieved
  distance, cleared the moment the APC actually moves (these are facts about a spot, not the world).
  Rendered with **both** halves: what has failed here, and what has *not been tried* from here. The
  second is what ends the loop.
- **The forward trace was switched off for the entire wedge.** `blocker` fired **zero** times in SR40:
  the trace is gated on `moving or stuck`, `moving` reads the engine's AI state, and a walk that never
  starts leaves that state idle. A stalled order is the strongest possible reason to look ahead and was
  the one case that never did. Gate now includes `stalled`.
- `rules.md`: don't alternate between two blocked headings; and a person in the way is not a wall —
  standing still one tick is a fine answer.

**Still open:** 292 reconnects in one run. No longer log noise (INFO, and the `NoneType` warning is
gone), but the socket is being torn down and rebuilt constantly — that is churn, not a logging problem,
and nobody has looked at why. Also unknown whether the forward trace would have *hit* the mailbox: it
never ran, so `blocker: 0` proves the gate was shut, not that the trace works. Watch for a `blocker`
line in the next run before trusting it.

---

## 61. Intra-cell perception — see the world along the leg, not just at the cell

**Status:** **reflex half (a) BUILT 2026-08-20, offline 61/61, needs SR46** · data half (b) still open · **Source:** user, 2026-08-12: *"we need to
work on intra grid observations at a regular interval so that the APCs can see what happening as they are
moving along... before Dufus or any APC gets ready to run into something, a plan is generated to avoid
moving into that situation. This will give us a finer grained visual guide and not just a survey to go
by."*

Today an APC's picture of the world updates **once per decision tick**, from **one** forward screenshot,
and it walks **15 m** between ticks. Everything in between is unobserved. The only dense visual record is
the survey: four fixed headings per 30 m cell, taken while standing still. A 30 m district is described
by four photographs from its centre.

### The ask splits in two, and they belong in different layers

The request bundles a *control* problem with a *data* problem. They want opposite things and must not be
built as one feature.

**(a) Not colliding is a reflex, not a plan.** SR40's timings: `observe_ms` ~950, **`llm_ms` ~8,000–10,000**,
`act_ms` ~150. An LLM-generated avoidance plan cannot react to something 3 m ahead — the decision arrives
nine seconds later, long after contact. Putting cognition in charge of collision avoidance means a
9-second loop steering a 1-second problem, and it contradicts the lizard-brain contract
([[feedback_lizard_brain_contract]]): sensing and reflexes are the lizard brain's job, reasoning is the
model's. The machinery already exists and is nearly free — `line_trace_forward`, `_classify_blocker`, the
`_STANDOFF_CM` reflex stop. What it lacks is **rate and coverage**: it fires once per tick, forward only.
The fix is a faster probe at engine cadence with side rays, not a VLM.

**Augmented 2026-08-19 (user):** *"vehicles are obstructions and the system needs to keep Dufus from
running into them even though navmesh says area clear."* Vehicles and props are the canonical case for
this reflex half: the navmesh is generated once and knows nothing about a truck parked on it, so
"navmesh clear" and "path physically blocked" disagree exactly there. The probe reports it as a fact in
the lizard-brain contract's shape — *"vehicle 183 cm ahead"*, never "go around" — and the standoff stop
is the only code-side reflex; steering around it stays with the LLM
([[feedback_lizard_brain_contract]], [[architecture_engine_agnostic_navigation]]). #77 handles the
terrain-you-can-see half; this item owns the things-that-occupy-space half.

**(b) Finer-grained visual coverage is the valuable half — and it serves the actual purpose.** Per
[[project_dufus_vlm_training_corpus]], Dufus exists to produce a VLM training corpus. Four static
headings per 30 m cell is a **sparse and repetitive** dataset: no motion parallax, no approach sequences,
no "what does this look like from 12 m out vs 4 m out". Sampling along the walked path is exactly the
data a navigation VLM needs and we currently throw away — the avatar walks through it every leg and
photographs none of it.

### The enabler: capture is already separate from interpretation

`bridge.capture_view` (`agent_manager.py:1000`, `:3568`) and `perceiver.perceive` are separate calls.
**Screenshots are cheap; VLM calls are not** (~750–1,000 ms and a per-call charge). So:

- **Capture densely** — every N metres of actual displacement, stamped with position, yaw, cell and
  footing. Corpus-grade data, no model in the loop.
- **Interpret selectively** — run the VLM only when a decision needs it, or when the reflex probe reports
  something ahead ("something 4 m out — look at it"). That trigger is the join between the layers and is
  precisely the user's "before he runs into something".

This keeps the training corpus dense and the running cost roughly flat, and it is a small change rather
than an architecture rewrite.

### Open questions (none decided)

- **Cadence: distance or time?** Distance (every ~5 m) gives even spatial coverage and no frames while
  standing still; time gives even temporal coverage and captures moving traffic. Probably distance, with
  a time floor while stationary and something in view.
- **Storage.** A full world reset already cleared 318 frames. Sampling every 5 m over a long run is
  thousands of images. Needs a retention policy *before* building, not after — and per the purpose memory,
  a visible gap beats a skew, so whatever gets dropped must be recorded as dropped.
- **Do sampled frames reach the decision, or only the corpus?** Feeding every frame to the LLM re-creates
  the cost problem. Suggest: corpus by default, decision only on the reflex trigger.
- **Does the survey survive?** If path sampling is dense enough, the 4-heading composite may be redundant
  for training and still worth keeping as the canonical, comparable, per-cell record. Do not delete it as
  a side effect of this work.
- **Reflex probe rate** is an engine-side question (Blueprint tick vs Python bridge poll) and the bridge
  is single-socket — a per-frame Python probe is not viable. Likely wants to live in the APC Blueprint and
  report *events* to Python, which is a different shape from everything else here.

**Do first, cheaply:** ~~confirm the forward trace actually hits things.~~ **GATE CLEARED
2026-08-20 from SR45's log — and it exposed a worse bug than the one it was testing for.**

The trace works and always did. SR45 fired it 88 times and got **42 hits**: Dufus 15, Maren 27.
Real actors, real distances — `veh_SportClassic_2`, `shopFront_01`, `shopFront_03a3`,
`road_sign_11`, three `pose_standing_*` crowd figures, `veh_VegetableTruck2` at 345.7 cm.

**The bug: 15 of those hits were classified and then silently thrown away.** Two causes, both fixed
2026-08-20 (offline 61/61):

1. **The keyword table never matched the level's actual naming.** It knew `"truck"` (so Maren's
   `veh_VegetableTruck2` survived) but not `veh_` (a parked sports car → `"obstacle"`), not
   `shopFront` (→ `"obstacle"`), not `pose_standing` (→ `"obstacle"`). Table rebuilt from the
   engine's real names: `veh_` → vehicle, `shopFront`/`storefront`/`house`/`porch` → structure,
   a new `prop` category for signs/poles/mailboxes/bins, and a new **`figure`** category for
   `pose_standing_*` SkeletalMeshActor crowd props — deliberately *not* `"person"`, so an APC is
   never invited to greet a mannequin. An unmatched name is now **logged with its raw actor name**
   instead of degrading silently (rule 12).
2. **`if stuck or stalled or category in _MOBILE_BLOCKERS:` dropped every static hit.** A parked
   vehicle on clear navmesh is *static by definition* — the exact case the user asked for was the
   one the gate excluded. Now **every hit becomes `observation["blocker"]`**, carrying
   `category`, `distance_cm`, the raw `actor_name`, and `urgent`. Only `urgent`
   (stuck / stalled / mobile / inside the 300 cm standoff) may **wake** cognition, so a wall passed
   at 4 m is a line in the prompt and does not buy a paid tick. The reflex halt is unchanged and
   still mobile-only. The prompt line now states the disagreement plainly: *"your forward probe
   struck a vehicle 3.5 m directly ahead of you. The navmesh does not know it is there."*

**Still open on this item** (the data half, (b) above): dense capture along the leg. Unchanged.

**Needs live verification (SR46):** a `blocker:` line for a static object in `sim_runner.log`, at
least one `blocker classifier: no keyword matched` line telling us what else to name, and no cost
blow-up from the widened fact (urgent-only waking should hold ticks roughly flat).

**Relates to:** #53 (navmesh-vs-semantic disagreement as training signal — the approach frames are where
that disagreement is visible), #49 (capture pose metadata), #19/#27, #60.

---

# Direction reset 2026-08-12 — get the town out of the corn field (#62–#72)

**Source:** user, this session: *"take a higher view of this project... move away from back and forth
with moving Dufus around and more having him really exploring the world and surveying for others...
I want to get APCs moving around and chatting, doing virtual work. Going to lunch etc."* Plus the
concern that scope was being followed too literally instead of being pushed
([[feedback_fill_the_gaps]], [[feedback_take_control_be_brief]]).

## The finding that reframes everything

Commit `2026-07-30 refactor: Dufus is the surveyor` parked Maren with the condition:

> **Maren parked (`is_active: false`) until Dufus reliably does his one job.**

**"Reliably" has no pass criterion.** Every live run surfaces a navigation defect — there is always
another one — so the gate never opens, so the only available work is Dufus navigation, so the next run
surfaces the next navigation defect. Six weeks and ten commits (SR32 → SR40) have run inside that loop.
It is not drift; it is the gate working exactly as written.

The consequence is structural: **MASTER_PLAN §0.2's four success criteria all require 2–3 free-running
agents.** With one APC active they are unreachable by construction. Live runs have been graded on the
only thing observable in a single-agent world — *did he get stuck* — and so locomotion became the
project.

### The survey already paid off; nobody cashed it in

`world_places.db` today holds `village square` (8,5), `Don's Donuts building with large donut sign`
(7,5, **named by dufus**), `sheriff station square` (7,6, **dufus**), `Four Ways Crossing` (5,5,
**dufus**), plus Maren's authored `vegetable truck` (5,5) and `home` (11,8).

Maren's authored agenda — sitting on disk, disabled — is: walk the square 06:00 · open the truck 07:00 ·
sales 08:00 · **lunch at Don's Donuts 12:00** · afternoon sales 13:00 · swap news at the Sheriff's
office 18:00 · home 19:00. Resolved against the live DB: **5 of 7 tasks resolve right now.** The map
Dufus built is the map she needs.

### The social substrate is built and has never been switched on

Not planned — built, and only ever exercised in an empty world: `_record_utterance` /
`_attach_heard_speech` (speech published with a position, delivered within `_HEARING_CM`),
`_identify_visible_apcs` (deterministic identity from position + yaw), `SocialMemory` (sentiment,
`last_interacted`, greet cooldown), `EpisodicLog` (append-only + relevance blend), and the prompt's
`## People You Know` / `## Nearby APCs` / `## What You Just Heard`. The comment on `_record_utterance`
states the problem outright: *"the reaction gate's 'someone is speaking to you' clause could never fire
because no agent ever received another's speech."*

### Where the Master Plan actually stands

Milestone 1 (planner/agenda) is built and solid. **Milestones 2, 3 and 4 were never started:**
`memory_store.py` is still the flat list with `_MAX_MEMORIES = 30`; `grep -rn "reflect"
agent_runtime/*.py` returns **no matches**; `should_react` does not exist; chat is director→APC only.
One milestone into six, and six weeks spent below milestone one.

## The reframe

**Stop grading live runs on locomotion.** Locomotion becomes a background service with a failure
budget — a wedge costs one tick, not a run — and stops being headline work. A run's success criterion
becomes *did something social happen, and did both parties remember it*, which is the Master Plan's own
criterion and has never once been measured.

**And the survey acquires a customer.** Today Dufus surveys for a corpus: valuable, but unfalsifiable
session to session. The moment Maren needs the Sheriff's office and can't get there, his map is either
the answer or it isn't — visibly. That is "surveying for others" literally, and it is what finally makes
#35 concrete: an expedition target is another APC's unmet need, not a frontier heuristic.

---

## 62. Retire the unfalsifiable gate — wake Maren

**Status:** **BUILT 2026-08-12, unverified live** · **Phase A** · **Loop-safe:** no (needs a live run to
mean anything). `maren/state.json` `is_active: true`. Nothing else changed — she has been a fully
configured tier-2 APC the whole time. **The live run is the verification and it has not happened.**

Replace *"until Dufus reliably does his one job"* with a **measured** bar, and record that SR40 already
cleared a reasonable version of it: 15/15 compass-keyed walks, zero `cultivated_field` footings, a
contiguous westward survey, six composites. Set `maren/state.json` `is_active: true` — that is a
checkbox in the web UI (`web_ui/main.py:220`), not a code change.

Expect a pile of two-agent bugs on the first run: bridge contention (single socket, sequential act
phase), identity mix-ups, agenda-vs-agenda timing, a much noisier log. **That is the point.** Those bugs
are on the path to the goal in a way another wedge fix is not.

**Done when:** one run has both APCs ticking, each appearing in the other's `## Nearby APCs`, and both
`social.json` files naming the other.

---

## 63. An unresolvable agenda place must fail loud, before the run

**Status:** **BUILT 2026-08-12, offline-tested** · **Phase A** · **Loop-safe:** yes.
`AgentManager.preflight_places()` walks every active agent's *authored* agenda (`generate=False`, so no
LLM call on the start path), logs each miss at ERROR, returns the rows in the `start_simulation`
response, and the cockpit alerts on them before the first tick. `_place_resolves()` is now the single
definition of "resolves", shared with `_validate_schedule` so the two can never disagree. Maren's 18:00
task was repointed at `sheriff station square` — the name Dufus actually put on the map — and all 7 of
her tasks now resolve. Coverage in `test_place_resolver.py`.

`_validate_schedule` (`agent_manager.py:1907`) already resolves every block through the same chain as
`_at_scheduled_place` and logs `place '<name>' resolves to NOTHING — agent will hunt`. It fires **mid-run,
into a log nobody reads**, and then the APC hunts. Move the check to sim start and surface it in the
start report and the cockpit, so a broken destination is on screen *before* Start.

**Two live misses found while checking Maren's day** (resolved against `world_places.db`):

- **`"Sheriff's office"` → nothing.** The cell is named `"sheriff station square"`; neither string
  contains the other, so `find_named_cell`'s exact-then-substring match misses. Her 18:00 task has no
  destination.
- **`"home"` → community cell (6,5), `"Mobile **home** community with pergola"`.** Bare substring match
  hijacks it. Maren survives only because her owned `home` row is `source: "authored"`, which takes
  precedence in `_resolve_place_endpoint`. Any runtime-named home would route to the wrong side of town.

Global rule 12 (fail loud). This is precisely the class of defect that silently eats a live run.

**Done when:** starting a sim with an unresolvable agenda place shows it in the start report, and both
live misses above are fixed (name the cell, or author the alias).

---

## 64. Per-role standing instructions — get the suppression clauses out of the shared prompt

**Status:** **BUILT 2026-08-12, offline-tested** · **Phase A** · **Loop-safe:** yes. The shared template
keeps the *mechanic* (interruption outranks routine, routine outranks whim, resume afterwards) and
delegates the *policy* to `rules.md`. Dufus keeps every clause; Maren gets the inverse ("stopping to
talk is part of your work", "stay at the truck when unscheduled"). **Two further code-side copies of the
same doctrine surfaced during the move and were fixed with it:** `_schedule_note`'s idle branch told
*every* APC to "keep exploring unmapped cells", and its travel branch hard-coded which interruptions
counted. `test_prompt_context.py` now pins both halves — mechanic in the template, policy in each
agent's rules — so deleting a clause instead of moving it fails the suite.

`_USER_TEMPLATE_VISION` in `llm_router.py` carries ~68 lines of standing instruction after the fact
sections. **About 45 are navigation, obstacles and unwedging.** The social clauses are *suppressive*:

> "Do NOT stop for strangers, scenery, or cells you could explore — those can wait."
> "...a nod is enough, keep going; do not stop again."

Correct for a lone surveyor on a 15-hour survey block. **Exactly backwards for a town** — and Maren
inherits them the moment she wakes, because they live in the shared template.

Move them (and the survey-specific travel doctrine) into `dufus/rules.md`, where per-agent behavior
already belongs — MASTER_PLAN Part V rule 4, *behavior comes from the agent's authored files; code
supplies senses* — and [[feedback_facts_not_blocking]]. Maren's `rules.md` gets the inverse: stopping to
talk **is** her job. Side benefit: the shared template shrinks toward facts, which is what it is for.

**Done when:** the shared template holds no agent-specific behavioral doctrine, and Dufus's run is
unchanged by the move.

---

## 65. Bounded stuck-recovery — then stop working on wedges

**Status:** **BUILT 2026-08-12 as a fact, not a recovery — scope changed on purpose** · **Phase A** ·
**Loop-safe:** yes.

**Deviation, stated rather than averaged.** This item was written as a deterministic recovery: N stalls
→ code picks a known-good neighbour and walks there. Building it that way would have added a sixth
code-over-LLM override to the five the SR40 handoff already lists as *problems to remove*, and it
contradicts [[feedback_facts_not_blocking]] — the standing ruling that "the LLM keeps doing X wrong" is
answered with louder facts and a `rules.md` line, never a code-side blocker. It would also have
pre-empted the live verification of #60's `tried_here`, which has never been observed working.

**What was built instead:** `_wedge_fact` counts consecutive stalled orders per APC and, at
`_WEDGE_BUDGET_TICKS` (3), states the run length *and* the measured ways out — neighbouring cells with
`cell_ground` footing somebody has actually walked, minus headings already tried from this spot, minus
refused cells, most-walked first. `_wedge_text` renders it; both agents get a `rules.md` line saying
three in a row means the thing you keep trying does not work. "No proven ground nearby" is stated
explicitly rather than rendering as silence — an APC with no options is in a different situation from
one ignoring an open road. A loud WARNING names the whole wedge as one event in the log.

**What this does and does not buy.** A wedge is now *legible* — one log line, one escalating fact, the
answer already computed from the shared map. It is not yet *bounded*: if the model ignores the fact, the
stall still runs on. Whether the fact is enough is exactly what the next live run measures, alongside
#60's `tried_here`. If SR41 shows an APC reading a listed escape and still alternating, the override
argument gets made on evidence instead of in advance. Coverage in `test_stuck_detection.py`.

**Original scope, for the record:** yes (offline-replayable against SR40's wedge sequence)

`_detect_stuck` exists (`agent_manager.py:1575`). Give it a budget: **N consecutive zero-displacement
ticks → deterministic recovery** (step toward a known-good neighbouring cell — `cell_ground` from #58
already banks exactly this) → **log it loudly as a recovery event** → carry on.

The goal is explicitly **not** to perfect navigation. It is to make a wedge cost one tick so it can
never again consume a run or a session. After this lands, navigation defects go on the list; they do
not become the session.

**Done when:** a wedge produces a recovery event within N ticks instead of a run of identical
`stalled_order` rows, and the recovery is visible in `agent_decisions.log`.

---

## 66. The reaction gate (`should_react`)

**Status:** **OPEN 2026-08-12, design small** · **Phase B** · MASTER_PLAN §14, never built · **BLOCKED 2026-08-20** until the overnight-survey exit condition is met (see *THE EXIT CONDITION*)

The piece that makes a routine interruptible, and the source of emergence. Cheap heuristic for tier
2/3, LLM for tier 1. **Every input already exists:** `observation["heard"]`, `observation["recognized"]`,
acquaintances carrying `recently_greeted` (`_mark_recent_greetings`), and the agenda's `right_now`.
Output: continue / greet / converse / re-plan.

Note this demotes the current "one validated action per tick" to exactly this interrupt path, as the
Master Plan intends — and the generic interruption lifecycle (#12/#17) is already the machinery to
carry it.

---

## 67. APC↔APC conversation, summarized into both streams

**Status:** **OPEN 2026-08-12** · **Phase B** · MASTER_PLAN Milestone 4 + success criterion #2 · **BLOCKED 2026-08-20** until the overnight-survey exit condition is met (see *THE EXIT CONDITION*)

The **transport is done**: `_record_utterance` → earshot → `_attach_heard_speech`. What is missing is
turn-taking, a close condition, and the exchange being summarized into **both** agents' memory. That
last part is how a town knows things — it is the diffusion mechanism, and nothing in the project has it.

Depends on #62 (there must be someone to talk to) and reads best after #66.

**Done when:** Maren and Dufus hold an exchange neither was scripted to start, and it is recoverable
from **both** `episodes.jsonl` files the next day.

---

## 68. Work that leaves a mark

**Status:** **OPEN 2026-08-12, needs one design call** · **Phase B** · **BLOCKED 2026-08-20** until the overnight-survey exit condition is met (see *THE EXIT CONDITION*)

"Tend the vegetables and greet customers" is currently **pantomime**: nothing in the world changes, so
no one can observe it, remember it, or react to it. Until an APC's work alters shared state, "virtual
work" can only ever be narration.

Smallest honest version: **one** shared, persistent piece of state that an APC's work modifies and
another APC can perceive — stock level on the truck, a note left at the sheriff's office. Keep it to
one; the question this answers is "can work be observed", not "can we model an economy".

**Design call needed:** where that state lives (PlaceDB has the shared-store precedent) and how it
reaches perception as a *fact*, not a special case.

---

## 69. Retire the 30-item memory cap — promote `EpisodicLog` to the memory stream

**Status:** **OPEN 2026-08-12** · **Phase C** · MASTER_PLAN Milestone 2

`memory_store.py` still caps at `_MAX_MEMORIES = 30`, and `get_relevant_memories` is "importance ≥ 0.7
plus the last 5". No embeddings, no poignancy, no recency·importance·relevance.

**Do not build the `ConceptNode` SQLite design from scratch.** `episodic_memory.py` is *already* an
append-only stream with consolidation and a relevance blend (recency + same cell + same place + known
person present). Add poignancy and a real relevance signal to **that**, and delete the `memory.json`
window. Reuse over new code (global rules 2 and 8) — Milestone 2 at a fraction of the cost.

---

## 70. Reflection, throttled, tier 1 only

**Status:** **OPEN 2026-08-12** · **Phase C** · MASTER_PLAN Milestone 3 — `reflection.py` does not exist

Poignancy-threshold trigger, question → insight → evidence-pointer procedure, insights stored as
`thought` nodes that are themselves retrievable. **Only worth doing after #69** gives it a stream worth
reflecting on.

---

## 71. Place names that survive being used by someone else

**Status:** **OPEN 2026-08-12** · **Phase D** · Prerequisite for anyone navigating by Dufus's map

Dufus names places in long descriptive VLM prose — `"blue house with FOR SALE sign"`, `"red corrugated
metal building, misty lake"`, `"Mobile home community with pergola"` — and `find_named_cell` /
`find_owned_place` resolve queries by **bare substring** over those names. Verified live: **`"home"`
resolves to the mobile-home community.** As the map grows, collisions grow.

Needs a short canonical name distinct from the long description, and a resolution rule that does not
hand a query to the first cell that happens to contain the word. **If Dufus is to survey *for others*,
his names must be usable *by* others** — nobody has looked at that yet.

---

## 72. The survey gets a customer (makes #35 concrete)

**Status:** **OPEN 2026-08-12, design** · **Phase D**

When another APC's agenda names a place that does not resolve (#63 now makes that visible), it becomes
a **survey request** Dufus can accept. Expedition target selection stops being a frontier heuristic and
becomes somebody's unmet need — more legible, and directly testable: *did Maren reach the Sheriff's
office because Dufus went and found it?*

This is the concrete form #35 has been waiting on, and it is what turns the survey from a treadmill into
a service.

---

## 73. The wider map — a survey that grows a blob, not a line

**Status:** **BUILT 2026-08-12** (offline 58/58) · unverified live · from SR41

SR41's map is 15 cells of a **17×12** grid, and they are a strip **7 wide and 2 tall**: rows 5 and 6
saturated across seven columns, rows 4 and 7 holding one cell each. Nothing malfunctioned. Every
navigation fact an APC had was **one cell wide** — the eight neighbours and whether each was named —
which answers *where do I put my foot* and cannot answer *where should the survey go next*. With no
wider fact the tie went to whichever way the body already pointed, and a random walk with no sense of
extent draws a line. Dufus's own rules made it worse: *"pick a direction whose neighbouring cell is
still unexplored"* is precisely the greedy local rule that produces a ribbon.

Every one of his 48 thoughts that run was a variant of *"this cell's already mapped, so I'll keep
pushing east."*

**Considered and rejected: walk to the centroid of the map, then fan out.** The centroid of a mapped
blob is always *inside* it — SR41's centroid is (6, 5.4) and Dufus woke standing on it — so the
instruction resolves to a no-op or a walk backwards over known ground, and "fan out" is the thing
already being done badly. The ribbon is created one cell at a time, at the moment the next direction is
chosen; that is the only place it can be fixed.

**Built as a fact, per [[feedback_facts_not_blocking]]** — `AgentManager._frontier_fact` →
`observation["frontier"]` → a new *"The Wider Map"* prompt section:

- how big the grid is (17 across, 12 deep, 204 cells) and how much is mapped;
- the **bounding box of mapped ground**, stated as a shape — *"7 cells wide and 2 tall"* is the sentence
  that makes going north thinkable;
- the nearest unmapped cell **touching** mapped ground, by compass bearing and distance in cells.

Three properties that are load-bearing, each pinned by a test:

- **Frontier means adjacent to mapped ground**, not merely unmapped — an APC cannot usefully be sent to
  a grid corner it has no route to, and the edge of the blob is exactly the set of cells that grow it.
- **Refused cells are excluded.** A cell someone ruled out must not return as "unexplored ground", which
  is the regression #59 fixed once already.
- **One cell per bearing.** Sorting by distance alone fills a short list from whichever side of the blob
  happens to be nearest — the same "everything points that way" input that drew the line. A truncated
  list that all points one way is not a choice.

`place_db.explored_cells()` already existed and had **no production caller** — only a test. Reused.

Dufus's rules gained one clause: read the wider map, not just the eight cells at your feet; a good
survey grows a blob, and when the block is far wider than tall the ground worth having is off its long
side. No new override; the model still picks.

**Live check:** does the mapped block's *height* grow in SR42? Ribbon → blob is the whole measurement.

## 74. Answering someone is an action with a name

**Status:** **BUILT 2026-08-12** (offline 58/58) · unverified live · from SR41

The one social exchange the whole direction reset was built to produce, half-completed. Maren greeted
Dufus (*"Morning, Dufus. Hat still on your head, I see."*). Dufus **heard** it — `[dufus] heard:` is in
the log — and decided, in his own words, *"Maren greeted me, so I'll answer her before continuing east"*
— then chose **`idle`**, which is silent. His `social.json` `interaction_count` stayed **0**; Maren's
reached 1.

Every component worked. Earshot delivered the line (#45), the reaction gate let him react (#64), and
cognition *chose to answer*. The intent to speak never became speech because nothing in the prompt said
that answering **is** an action with a name:

- `speak_to` was the one action in `_ACTION_SCHEMAS` with no gloss — a bare JSON shape among fifteen
  entries that each explain what they do.
- `_heard_note` said *"you may answer this tick"* and never named `speak_to` as the way.

Both closed. `speak_to` now states it is the only action that produces speech and that `idle`/`observe`
are silent; `_heard_note` names the speakers, names the action, and says outright that deciding to
answer and then choosing `idle` leaves them standing in silence.

Cheap, and it is the criterion the direction reset actually set: *did something social happen and did
both parties remember it.* SR41 scored half a point on the only test that counts.

**Live check:** does `dufus/social.json` reach `interaction_count ≥ 1` in SR42?

## 75. One place, one row — a truck astride a cell boundary

**Status:** **BUILT 2026-08-12** (offline 58/58) · unverified live · from SR41

`owned_place_cells` keys on **`(col, row, owner, name)`**, so the grid cell is part of an owned place's
identity. A place near a cell boundary therefore gets a *second row* the moment its owner stands on the
other side of that line — and the two rows are the same physical thing recorded twice.

Maren's vegetable truck is the live case. Authored at cell **(5,5)**, recorded again at runtime as
**(6,5)**, the two anchors **134 cm apart** across the boundary at `x = -9000`. Consequences through
SR41:

- `known_places` does not dedupe, so **her prompt listed the truck twice** as her two nearest places —
  the prompt she then reasoned over to say *"My position confirms I'm at the truck even though the view
  shows mobile homes."*
- `Resolved owned place 'vegetable truck' -> cell (5,5)` fired on **every tick** of a run she spent
  standing in (6,5).

Initially misread as #71 (place names that survive being used by someone else). It is not a naming
problem — the names are identical. It is cell quantization, and worth separating because the fix is
different and #71 is still open on its own terms.

**Not broken, and deliberately not touched:** arrival. `_at_scheduled_place` already tests the world-
space extent box, so Maren was correctly judged to be *at* her truck (120 cm off a 450 cm half-box)
even while the map disagreed about the cell. That existing test is what the fix reuses.

Two halves:

- **Cause** — `_record_place` minted the second row. It now checks `_owned_place_here` first: standing
  inside a place you already own under that name means there is nothing to record. Same box test as
  arrival, so an APC cannot be *at* its truck by the schedule's reckoning and somewhere new by the
  map's.
- **The data already written** — `preflight_duplicate_places()` runs beside `preflight_places` on the
  start path and merges rows whose boxes overlap, keeping the **authored** row (else the oldest), at
  WARNING and surfaced in the cockpit. Verified on a copy of the live world: 7 owned rows → 6, exactly
  the one merge, `maren/'vegetable truck'` (5,5) kept and (6,5) dropped.

Rows that merely share a name across a real distance are two different places and are left alone —
`maren/'home'` and `maren/'Marens Home Place'` both survive, which is #71's problem, not this one.

---

## 76. Center-out exploration — the survey grows rings from the town center

**Status:** **OPEN 2026-08-19, design small** · **Source:** user, 2026-08-19: *"how Dufus can
explore/survey the world from center of world out"* · Builds directly on #73

#73 gave the APC a wider map — grid size, mapped-block shape, nearest frontier cell per bearing — but
every frontier candidate is presented as equally good. The tiebreak is still the model's whim, and
SR41's whim was "keep pushing east". The user's ask names the missing ordering principle: **grow
outward from the center**, ring by ring, so coverage stays contiguous, stays near the town where the
other APCs live and work, and never sprints down a map edge.

**Built as facts on #73's machinery, per [[feedback_facts_not_blocking]]** — no route planner, no
override:

- The *"Wider Map"* prompt section states the **world center** (the town origin — decide whether that
  is the grid's geometric center or an authored landmark; probably the authored town square, since
  "center of the world" should mean the town, not the coordinate system) and the APC's distance from
  it in cells.
- Each frontier candidate carries its **distance from center**, alongside the existing bearing and
  distance-from-here.
- `dufus/rules.md` gains one clause: *prefer the frontier cell closest to the center; the survey grows
  in rings — far ground is not lost, it becomes the next ring.*

The model still picks. If it reads "north frontier is 2 cells from center, east frontier is 6" and
still walks east, that is data, and the run will have measured it.

**Why this also serves the real goal:** a center-out survey saturates the cells Maren's day actually
uses (truck, Don's, sheriff station are all within ~3 cells of the square) before it spends a session
photographing the map's rim. Coverage where the people are is what makes #72 (survey gets a customer)
cheap.

**Done when:** a live run shows frontier candidates carrying distance-from-center, and the mapped
block grows around the center rather than extending its longest axis. Ring-shaped-ness is the
measurement; SR42+ grades it next to #73's height check.

---

## 77. Look before you step — what the APC sees vetoes the move, navmesh notwithstanding

**Status:** **OPEN 2026-08-19** — promotes the #55 follow-on to a numbered item · **Source:** user,
2026-08-19: *"I want Dufus to not go into areas that can get him stuck regardless of navmesh saying he
can. Like, I see corn field, I can't go there... I need the LLM to guide the navigation more."*

Today bad ground is discovered **by standing on it**. Footing is sampled where the APC already is;
SR32's celebrated "FOOTING works" moments were all *retreats* — the corn was entered, then left. The
navmesh happily paths through cultivated fields, so nothing code-side ever says no, and nothing
prompt-side asks the model to check its own eyes before ordering the step. The forward frame **shows
the corn**; the VLM describes it; and then `walk_to` walks into it anyway, because seeing and stepping
are not connected anywhere.

Per [[architecture_engine_agnostic_navigation]] this is solved in the cognitive loop, not with engine
patches — and per [[feedback_facts_not_blocking]], with facts and rules, not a code blocker. Three
pieces, all on existing machinery:

- **Per-direction ground probes as facts.** Before the move is chosen, the lizard brain samples the
  footing of each candidate neighbour cell (nav probe / raycast at the cell center — any engine
  primitive, output is the generic label per [[architecture_lizard_brain_sensing]]): *"north:
  cultivated_field · east: cell_ground · south: grass"*. The #65 wedge fact already computes
  known-good neighbours from walked history; this extends it to *probed* ground for cells nobody has
  walked. The APC learns the corn is there **without paying a tick to stand in it**.
- **The prompt connects eyes to feet.** One template line in the decision section: *what you can see
  ahead of you outranks the pathfinder — if the ground you are about to walk looks like field, crop,
  water, or a place you have refused before, do not order the step.* Plus a `rules.md` clause in the
  same voice. This is the "LLM guides the navigation more" ask, stated as the standing instruction it
  actually is.
- **The refusal must land somewhere durable.** The model can already name a cell as off-limits →
  `SpatialMap.mark_blocked`, and #73's frontier fact already excludes refused cells, so a cell refused
  once stops being re-offered. Verify that path fires when the model refuses on sight; if the action
  surface makes it awkward (refusal today is only implicit in choosing another direction), give it a
  name the way #74 gave answering a name — an explicit `avoid_cell`-shaped action or argument, so *"I
  see corn, I am not going there"* is one decision, recorded once, instead of a mood re-derived every
  tick.

**Explicitly out of scope:** moving obstructions. Vehicles and props are #61's reflex probe (navmesh
says clear, world says truck — a lizard-brain fact at engine cadence, see #61's 2026-08-19
augmentation). This item is *static terrain you can see and reason about at decision speed*; #61 is
*things that occupy space at reflex speed*. Same contract — facts in, model decides, one reflex stop —
different clock rates, kept apart on purpose.

**Done when:** a live run shows at least one **pre-emptive** refusal — a decision row that names bad
ground ahead as the reason for turning, with the APC never entering it — and zero
`cultivated_field`-class footings for the run. The retreat count going to zero *because entries went to
zero* is the whole point.

---

## 81. The body-box probe — "can I fit", not "can a line pass"

**Status:** **BUILT 2026-08-20, offline 64/64 — NEEDS AN UNREAL PLUGIN REBUILD, then SR47.**
`get_character_forward_volume` is new C++: a capsule sweep on `ECC_Pawn` using the character's own
`UCapsuleComponent`, lifted by its `MaxStepHeight` so a kerb is not called a wall, plus a 5x3 ray
raster returning `open_columns` / `open_rows` / `blocked_fraction`. Python calls it through
`AgentManager._probe_ahead`, which **falls back to the old single ray and says so once per run** if
the engine does not know the command — so nothing breaks before the rebuild, and `fits` is `None`
(never `False`) when nothing was measured. Decisions taken: capsule read from the engine, `ECC_Pawn`
not a custom channel, step-height allowance for kerbs, navmesh pairing deferred to #53.
The prompt fact reads *"your body DOES NOT FIT straight ahead. Measured clearance 0.4 m. The gap is
on your: far left, left."* Original spec follows. · **Source:** user,
2026-08-20: *"We need to make sure any ray casting in Unreal to detect things is done in a way that
scans a beam from left to right and top to bottom so that a virtual 'BOX' the size of an APC is built
and used so we can say 'I can fit' or 'I am completely blocked'. Not just one 'ray' from the APC's
viewpoint."*

### What the probe actually is today

`HandleGetCharacterForwardTrace`
(`MCPGameProject/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/UnrealMCPCharacterCommands.cpp:105`)
is **one** `LineTraceSingleByChannel`. Start is `ActorLocation + (0,0,60)`, end is start plus the forward
vector times the distance. One infinitely thin line, at one height, dead centre. Three independent
failures follow, and they are not degrees of the same problem:

1. **It has no width.** An APC capsule is roughly 34 cm in radius — about 68 cm of body. The probe
   samples 0 cm of it. A post 30 cm off-centre is struck by the shoulder and never by the ray. This is
   why "clear ahead" and "wedged" coexist happily today.
2. **It has no height.** At Z+60 it rides hip height. A kerb, a step, a low wall, a bin at 30 cm are all
   invisible — and so is an awning, a low branch or a doorway lintel at 210 cm. `road_sign_11` was hit
   in SR45 at exactly the height its post crosses Z+60; the same sign one metre taller reports nothing.
3. **It asks the wrong channel.** `ECC_Visibility` answers *"what can I see?"*. Movement is blocked by
   `ECC_Pawn`. The two disagree precisely on the actors that cause wedges: a `BlockingVolume`, a nav
   modifier, invisible collision around a prop — all block a pawn and are transparent to Visibility.
   **The probe cannot see the thing most likely to stop the body.**

A per-heading version of this ray is also what `_direction_places` / #77 leans on, so the same three
holes are present in look-before-step.

### The two questions, and why one call cannot be one shape

The user's phrasing contains two different questions, and they need two different engine primitives:

- **"Can I fit?"** — a **capsule sweep**. `SweepSingleByChannel` with the APC's *own* capsule
  (radius and half-height read from its `UCapsuleComponent`, never hard-coded) against `ECC_Pawn`, from
  the current location forward. One engine call, cheap, and it answers the fit question *exactly*: if
  the swept body contacts nothing, the body fits, by construction. It also yields **`clearance_cm`** —
  how far the body may advance before contact — which is the honest replacement for today's
  `distance_cm`.
- **"Where is the gap?"** — a **coarse ray raster**, which is the left-to-right / top-to-bottom scan the
  user described. The sweep returns a single yes/no plus a first contact; it cannot say *clear on the
  left, blocked on the right* or *blocked at knee height, open above*. A grid of rays across the
  capsule's frontal rectangle can. Suggested resolution **5 columns × 3 rows = 15 rays** — enough to
  name a side and a band, cheap enough to run every tick, and coarse enough that it never pretends to be
  a depth camera.

**Recommendation: build both, return both, in ONE bridge command.** The bridge is a single socket
([[architecture_engine_agnostic_navigation]] and #61's own note) — fifteen round trips per tick is not
viable, and fifteen rays inside one C++ handler cost nothing. Proposed command
`get_character_forward_volume`, returning something in the shape of:

- `fits` (bool) — the capsule sweep result
- `clearance_cm` (float) — free travel before first contact
- `blocked_fraction` (float) — of the 15 raster cells, how many are struck
- `open_columns` / `open_rows` — which side and which height band are clear
- `contact` — the first-contact facts (category, distance), classified per #83

### Why this replaces the current probe rather than sitting beside it

Two probes with different answers is rule 7 territory — pick one and say which. The volume probe
strictly dominates the ray: it answers everything the ray answered and three things it could not.
The single ray should be **deleted**, not kept as a fast path.

### The prize: "step around" stops being a guess

Today, when the LLM is told something is ahead, its only options are to re-issue the same walk or pick a
direction blind, which is exactly the SR40 east/southeast ping-pong. With `open_columns`, the fact
becomes *"your body does not fit straight ahead; it fits to your left"* — a fact, not advice, and the
model still chooses ([[feedback_lizard_brain_contract]]). Running the same volume probe on
forward-left and forward-right makes sidestepping a measured option rather than a coin flip. That is
the mechanism most likely to end the wedge loops that have shaped the last six weeks.

### Open questions (none decided — do not guess these)

- **Capsule source.** Read the real `UCapsuleComponent` extents, or accept a size in the params? Reading
  is correct and author-independent; a param is testable offline. Probably read, and *log* the size once
  per run so a mismatch is visible.
- **Channel.** `ECC_Pawn` is the honest movement question. But a custom `APC_Probe` trace channel would
  let the level author mark "APCs must not path here" without physical collision — cheap to add, and it
  is the engine-side half of a refusal. Decide before building; do not add both.
- **Ground handling.** A forward sweep at body height cannot tell a 15 cm kerb (steppable) from a 60 cm
  wall (not). Needs either a downward component or a step-height allowance in the sweep start. Without
  it the probe will call every kerb a blockage and the APC will stop in the street.
- **Navmesh disagreement.** Should the same call also report whether the destination point is on the
  navmesh? That pairing — physics says blocked, navmesh says clear — is exactly #53's training signal
  and is nearly free here.
- **Cadence stays as it is.** This item changes the probe's *shape*, not its *rate*. Dense sampling
  along the leg is #61(b) and must not be smuggled in here.

**Blocks:** the honest version of #61's reflex half.
**Relates to:** #61 (which currently stands on the thin ray), #77 (same holes per heading), #53
(navmesh-vs-physics disagreement), #83 (what the contact *is*), #26.

**Done when:** a live run logs a `fits: false` with `open_columns` naming a clear side, the APC
sidesteps on the model's own decision, and no wedge in that run was preceded by a `hit: false`.

---

## 82. Engine identity must never reach the model

**Status:** **OPEN 2026-08-20 — ABSORBED into #84 as its engine-names clause (user asked for the whole prompt interface, not just this leak). Kept for the four documented leak channels.** · **Source:** user, 2026-08-20: *"I would
prefer Unreal engine actor names and things don't bleed into the LLM's thinking."*

This is the standing contract, not a new preference: [[architecture_lizard_brain_sensing]] puts the
abstraction boundary **at output** — the lizard brain may use any engine primitive it likes, and the LLM
receives generic semantic labels only. The boundary is currently porous. Four confirmed channels, found
2026-08-20 by reading the prompt builder, not by guessing:

1. **The structural one — the whole observation dict is serialized.** `llm_router.py:563`:
   `obs_for_text = {k: v for k, v in observation.items() if k != "image_path"}`, then
   `json.dumps(obs_for_text, indent=2)` straight into the user prompt. This is the no-image fallback
   path (capture failed / Unreal offline), and it is a **deny-list of exactly one key**. Every engine
   field the runtime has ever attached to an observation goes to the model verbatim, and **every new key
   leaks by default** — including `blocker.actor_name`, added 2026-08-20 for diagnosis. The rendered
   path is clean (`_sense_note` prints category and distance only); the fallback path undoes that.
2. **The model is asked to *emit* engine labels.** `_ACTION_SCHEMAS` (`llm_router.py:28`, `:33`, `:35`,
   `:36`, `:37`): `walk_to {"target_actor": "<actor_label>"}`, `speak_to {"target": "<actor_label>"}`,
   and `inspect_object` / `follow_character` / `attack` with `"<actor_name>"`. For these to work at all
   the model must have been told engine labels — so channel 2 forces channel 1 open.
3. **The engine is named in the prompt.** `llm_router.py:45` *"You are controlling one NPC in an Unreal
   Engine RPG world"*; `:652` *"a character in an Unreal Engine world"*; `:79` a section headed
   *"Nearby APCs (engine position fact…)"*.
4. **Category names that are engine artefacts.** The 2026-08-20 classifier reports `figure` for
   `pose_standing_*` — correct — but the table matches on `veh_`, `shopFront`, `pose_standing`. Those
   substrings are the level author's private vocabulary, which is #83's problem; here the point is only
   that the *outputs* must stay generic even as the *inputs* stay engine-shaped.

### Direction (not decided — the shape is the open question)

- **Allow-list, not deny-list.** The prompt should be built from an explicit projection of the
  observation — a named set of fields with generic names — and the raw dict must never be serialized.
  A new runtime key should be invisible to the model until someone deliberately exposes it. This
  inverts today's default and is the only fix that stays fixed.
- **Identity by display name, resolved in code.** The model refers to `Maren`, never to
  `APC_Maren_BP_C_1`; the router maps display name → actor label on the way out. Names it invents that
  do not resolve fail loud (rule 12) instead of reaching the bridge.
- **Drop the engine from the persona.** "an Unreal Engine RPG world" → "the world". This is not
  cosmetic: it is the same abstraction that lets a second engine drop in behind the runtime
  ([[architecture_engine_agnostic_navigation]], [[project_why_worlds_for_ai]]), and it removes a
  standing invitation for the model to reason about engine mechanics instead of about the world.
- **A test that can fail.** One offline check that builds a prompt from an observation seeded with
  engine-shaped junk (`APC_Dufus_BP_C_1`, `SkeletalMeshActor`, `veh_SportClassic_2`, `BP_`, `_C_1`)
  and asserts none of it appears in the rendered text — on **both** the image and the no-image path.
  Per rule 9, this is the test that catches the regression the deny-list guarantees.

**Note the cost.** Channel 2 is real functionality: `speak_to`, `follow_character` and
`walk_to target_actor` all address a character today. Closing this properly means the display-name
resolver, not just deleting fields — do not half-do it and silently break speech.

**Relates to:** #83, #61, [[architecture_lizard_brain_sensing]], [[feedback_lizard_brain_contract]].

**Done when:** the leak test passes on both prompt paths, and a live run's prompts contain no string
matching `BP_`, `_C_[0-9]`, `Actor`, or `Unreal`.

---

## 83. Object identity without depending on the level author's naming

**Status:** **BUILT 2026-08-20, offline 64/64 — needs the plugin rebuild to carry signals.**
`_classify_blocker` now resolves in order: actor **tags** (the author saying what a thing is) →
**pawn-ness** (the engine knowing it is a body) → **physical material** (set by the art pipeline,
survives renaming) → component/collision hints → the keyword table, last. An immovable
`SkeletalMeshComponent` reads as `figure`, never `person`, so no APC greets a mannequin. Nothing
matched still returns a generic obstacle and logs everything known about the contact. Path 3 (join
the VLM caption from #79) remains open. Original spec follows. · **Source:** user, 2026-08-20: *"Sounds
like we don't have good enough object detection, do we?"*

**Correct, and the 2026-08-20 classifier fix does not change it.** What we call "detection" is
`_classify_blocker`: substring matching against `GetActorLabel()` and the UClass name. That is not
object detection; it is reading the level author's file names and hoping. SR45 is the proof — three
whole name families (`veh_*`, `shopFront*`, `pose_standing_*`) fell through to `"obstacle"` at once, and
the fix was to type those three families into a table. **The next art pack breaks it again**, and it
breaks *silently* except for the fail-loud log line added the same day.

### The split that removes most of the pressure

The reflex and the reasoning need different things, and conflating them is why the classifier looks
load-bearing:

- **The reflex does not need to know what it is.** "My body does not fit; something solid fills the
  left half at 2.1 m" is a complete input for stopping and sidestepping. That is pure geometry — #81
  delivers it with no classifier in the loop at all. Every millisecond-scale decision can be made
  without identity.
- **The reasoning does need identity** — *"a parked vehicle"* vs *"a person"* changes whether you
  sidestep, wait, or speak. But that decision already costs 8–10 s of model time, so identity may
  arrive on the slow path where a VLM call is affordable.

Splitting them means a wrong or missing label degrades the *conversation*, never the *collision*.

### Sources of identity, most robust first

1. **Engine-side, author-independent:** gameplay tags, component class, collision profile, physical
   material. A `PhysicalMaterial` of "flesh" vs "metal" vs "foliage" is set by the art pipeline, not by
   whoever typed the actor label. Deterministic, free, and survives renaming — but needs the level's
   assets to actually carry it, which is unverified. **Check this before designing anything else.**
2. **The VLM caption we already pay for.** #79 records a caption per perceived frame; the thing 3 m
   ahead is *in that image*. This is real detection, it is already funded, and it is 8–10 s late —
   exactly the slow path above. Joining the probe's `contact` to the caption is the interesting work.
3. **The keyword table, demoted to last resort.** Keep it, keep the fail-loud log, stop treating it as
   the answer.

### Open questions

- Do this level's meshes carry usable physical materials or tags at all? One inspection answers it and
  decides whether path 1 exists.
- Does identity belong in the probe response (one round trip, engine does the work) or joined in Python
  from the perception log (engine stays dumb)? The lizard-brain contract permits either; the
  engine-agnostic goal prefers the second.
- `figure` (crowd mannequin) vs `person` (a real APC) must survive whatever replaces the table — an APC
  greeting a mannequin is the visible failure to test for.

**Relates to:** #81 (geometry without identity), #61, #79 (the caption corpus), #53, #82 (whatever the
answer is, it leaves as a generic label).

**Done when:** an actor with a name matching no keyword is still classified correctly, and the crowd
mannequins are never addressed as people.

---

## 84. The prompt payload contract — one clean interface for everything sent to the model

**Status:** **BUILT 2026-08-20, offline 64/64.** New `agent_runtime/prompt_payload.py`:
`ALLOWED_FIELDS` is a declared allow-list grouped into self / place / senses / people / task;
`project()` sends a field only if the contract names it, so a new runtime key is invisible by
default instead of shipping automatically; `NESTED_STRIPS` drops `blocker.actor_name/actor_class/
signals` at the boundary while keeping them in the log for diagnosis; `check_clean()` is the alarm
that reports (never rewrites) engine identity in a rendered prompt, and runs on both prompts every
decision. All four #82 channels are closed — the raw-dict dump is gone, the templates no longer name
the engine, and the action schemas ask for `<character name>` (the display-name resolver
`_resolve_action_actor_refs` already existed, so speech and follow still work). **Coverage audit 2026-08-20 (user asked whether #83's engine vocabulary is fully contained):**
`decide()` was guarded but **three other prompt paths were not** — `orient()` (wake), `chat()`
(operator chat) and `ask()` (the planner) each build and dispatch their own text. All four are now
guarded, and `test_every_prompt_path_is_guarded` enumerates the methods rather than trusting one
call site, so a fifth path added later fails the test instead of leaking quietly.
The audit also confirmed #83 itself is clean: the engine identity block (physical material,
component class, collision profile, tags) is an **input** to `_classify_blocker` and never enters
the observation — only the generic category does, and `_sense_note` reads no engine field.
Two renderers (`_seen_text`, `_nearby_character_lines`) *would* leak if fed engine strings, but
their real sources are clean by construction: `nearby_characters` uses `display_name`, and landmark
labels are parsed (`Landmark_maren_home` → `"home"`) before storage. The alarm now covers them.
**Still open:** the two render paths were not merged into one, and there is no golden-prompt diff
test yet — the allow-list and the alarm were the load-bearing half. Original spec follows. ·
**Source:** user, 2026-08-20: *"Add a backlog to clean up what gets sent to the model. We can figure
this out later but would like a cleaner interface."*

**#82 is absorbed into this item as its engine-names clause.** #82 asked a narrow question (stop
leaking Unreal actor labels); the user's ask is the general one: *what is the defined set of things an
APC's mind receives, and who decides?* Today the answer is "whatever accumulated", and that is the
actual defect — the leak was only a symptom.

### What the interface looks like today

There is no interface. There are two divergent code paths in `llm_router.py` and a pile of ad-hoc
renderers:

- **The vision path** (`llm_router.py:530`) formats **23 separate keyword arguments** into
  `_USER_TEMPLATE_VISION`, each produced by its own private function: `_grid_text`, `_place_text`,
  `_facing_text`, `_travel_note`, `_direction_lines`, `_frontier_note`, `_seen_text`,
  `_active_interrupt_note`, `_cell_survey_note`, `_heard_note`, `_sense_note`, `_schedule_note`,
  `_route_map_note`, `_acquaintance_lines`, `_known_place_lines`, `_episode_lines`,
  `_nearby_character_lines`, `_memory_lines`, plus raw `x` / `y` / `z` and `agenda.prompt_text`.
  Every new fact added over the last six weeks bolted on one more argument and one more renderer.
- **The no-vision path** (`llm_router.py:562`) ignores all of that and dumps the raw observation dict
  as JSON, minus one key.

So the same runtime state produces two completely different prompts depending on whether a screenshot
landed, and neither is a stated contract. Nobody can answer "what does an APC know?" without reading
600 lines.

### Why it matters beyond tidiness

- **Facts, not blockers is the whole strategy** ([[feedback_facts_not_blocking]]). Every fix for
  six weeks has been "add a louder fact". That strategy scales only as far as the prompt stays
  legible — and the prompt is now the product. An unstructured prompt is an unmeasurable one.
- **Cost.** Every fact is tokens on every tick, forever. Nobody currently knows which facts earn
  their place. A defined payload can be measured and pruned; a pile cannot.
- **Contradiction risk.** Two renderers can state opposite things about the same state and nothing
  catches it (rule 7). SR46 has a live example: Maren was told she was at her post *and* told to walk
  to her post, in the same prompt, twenty times.
- **Engine leakage** (#82's four channels) is a consequence of the missing allow-list, not a
  separate bug.
- **Portability.** A defined payload is what a second engine, or a second model, plugs into
  ([[architecture_engine_agnostic_navigation]], [[project_why_worlds_for_ai]]).

### Direction (shape not decided — that is the work)

- **One projection, one path.** Build a single explicit "what the mind receives" structure from the
  observation, and render *that*. No screenshot must not mean a different prompt — it should mean
  the same payload with the vision section empty.
- **Allow-list by construction.** A field reaches the model only if it is named in the projection.
  New runtime keys are invisible by default; today they are visible by default.
- **Sections with owners and a budget.** Each block (self, place, senses, map, people, memory,
  schedule) states what it is for. A rough token budget per section makes the pruning conversation
  possible at all.
- **Generic vocabulary at the boundary** — #82's rule: no `BP_`, no `_C_1`, no `Actor`, no "Unreal".
  Characters are referred to by display name and resolved back to actor labels in code.
- **A golden-prompt test.** Freeze a rendered prompt for a fixed observation and diff it. Per rule 9
  this is what makes a silent prompt regression fail loudly instead of showing up as odd behaviour
  three runs later.

**Do not start this while a live-run lane is open** — it touches every prompt and would confound
whatever run is being graded. It is the natural companion to the "Needs tests (speed mode)" catch-up
lane.

**Absorbs:** #82. **Relates to:** #61, #81, #83, #85.

**Done when:** one code path builds one declared payload; a field not on the list cannot reach the
model; the golden-prompt test exists and fails when a renderer changes.

---

## 85. Shared APC doctrine — rules.md needs imports, because Maren does not know what Dufus knows

**Status:** **BUILT 2026-08-20, offline 64/64.** `worlds/MCP_World/doctrine/` holds `basics.md`,
`ground.md`, `movement.md`, `obstacles.md`, `survey.md` (+ a README stating the split rule).
`resolve_rule_imports` in `agent_runtime/agent.py` expands `@import doctrine/<file>.md` at load:
literal inclusion, one level, no nesting, no path escape, and **every failure raises** —
missing file, empty path, nested import. Imports resolve before the character's own lines, so
character overrides doctrine. **Maren went from 21 lines to 100** and now carries refuse_cell,
allow_cell, look-before-you-step, breadcrumbs, tried-headings and the bounce rule; she is still not
told how to survey. Decisions taken: doctrine lives per world, character wins on conflict, an agent
with no imports loads but is warned. Original spec follows. · **Source:** user, 2026-08-20, after
SR46: *"Maren ended up walking into the cornfield... which makes me think the rules md or wherever
you save movement behavior is not synced with Dufus. We need a way to share these types of things
between APCs maybe by importing mds."*

**Confirmed by measurement, not inference. `dufus/rules.md` is 94 lines. `maren/rules.md` is 21.**

`Agent.load` (`Python/agent_runtime/agent.py:62`) does exactly one thing:
`rules = (path / "rules.md").read_text(...)`. One flat file per agent, no include, no shared base.
So every navigation lesson learned since 2026-07 — six weeks of live-run fixes — was written into
**Dufus's file only**, and Maren has never received any of it.

### What Maren is missing, and what it cost in SR46

Present in Dufus, absent in Maren:

| Doctrine (Dufus rules.md line) | What it prevents |
|---|---|
| Look before you step; your eyes outrank the navmesh (`:44`) | walking into visible corn |
| Behind buildings / indoors is never ground to cross (`:50`) | lobby and back-yard wedges |
| Refuse bad ground, whole cell or `scope: spot` (`:31`, `:53`) | re-entering the same trap |
| Refuse a piece of ground ONCE (`:58`) | the SR44 refusal loop |
| You have bounced in and out of this cell N times (`:62`) | pocket ping-pong |
| Read BREADCRUMBS; do not reverse blindly one leg at a time (`:72`, `:78`) | retracing into the trap |
| Which headings you already tried from this spot (`:82`) | the east/southeast loop |
| A person in your way is not a wall (`:91`) | freezing on a passer-by |

Maren has only the reactive footing rule (*"if FOOTING is grass/cultivated_field/water, turn back"*)
— which fires **after** she is already in the corn.

**The smoking gun, SR46 11:45:58:** Maren decided *"I keep looping through this cornfield pocket;
**time to refuse this ground** and head straight for..."* — and then emitted `walk_to`. She reasoned
her way to exactly the right action and could not take it, because nothing in her 21 lines tells her
`refuse_cell` exists or how it works. All three `refuse_cell` calls in SR46 were Dufus's.

This is not a Maren bug. It is a **distribution** bug: doctrine that is true for every body that
walks has been stored per-character. Any third APC starts at zero again — and per
[[project_why_worlds_for_ai]] and the drag-and-drop goal ([[feedback_drag_and_drop]]), APCs are
supposed to be cheap to add.

### Direction — the user's "importing mds", concretely

Split `rules.md` into two kinds of content and let a character file pull in shared ones:

- **`doctrine/` — shared, world-level, about having a body.** Movement, footing, refusal,
  breadcrumbs, stall recovery, obstacles, people-in-the-way. Written once. Suggested split:
  `doctrine/movement.md`, `doctrine/ground.md`, `doctrine/obstacles.md`, `doctrine/social.md`.
- **`agents/<id>/rules.md` — the character.** Who they are, what their job is, what they refuse to
  do. Maren's *"stay at the post, you are not an explorer"* and Dufus's *"your one job is to survey"*
  are genuinely per-agent and must stay per-agent.

An import line in `rules.md` — e.g. `@import doctrine/movement.md` — resolved at load time in
`Agent.load`. Keep it dumb: literal textual inclusion, no templating, no conditionals.

### The rule that decides where a line goes

**If the rule would be true for any body with legs, it is doctrine. If it is only true because of who
this character is, it is character.** #64 already moved *social* clauses the other way (out of the
shared prompt into per-agent rules) — that was right, and this is not a reversal of it: social
posture is character, locomotion is physics.

### Open questions (do not guess)

- **Resolution order and precedence.** If a character contradicts doctrine, who wins? Per rule 7,
  pick one and state it — probably character wins, and the override is *logged* so it is visible.
- **Fail loud on a missing import** (rule 12): a typo'd import must abort the run at preflight (#63's
  pattern), never silently produce a 21-line APC — which is exactly how this went unnoticed for six
  weeks.
- **Where does `doctrine/` live?** Per world (`worlds/<level>/doctrine/`) or per install? Footing
  vocabulary is world-specific; "do not walk into a person" is not.
- **Token cost.** Maren's prompt grows by ~70 lines on every tick, forever. That is real money and
  it argues for splitting doctrine into files an agent can decline, not one blob.
- **Does the survey doctrine come along?** Maren should know how to *avoid* bad ground; she should
  not be told how to survey. Suggests `ground.md` (everyone) separate from `survey.md` (surveyors).

**Relates to:** #84 (the same "what does the mind receive" question, one layer up), #64 (the mirror
decision), #63 (fail-loud preflight), #81, [[feedback_drag_and_drop]].

**Done when:** a new APC created by `/create-npc` inherits the full movement doctrine with no
copy-paste, Maren emits `refuse_cell` when she reasons her way to it, and a bad import stops the run
at preflight.

---

## 86. Adaptive step length — how far to walk is world evidence, not a constant

**Status:** **BUILT 2026-08-20 — needs a test, needs SR47.** New module
`Python/agent_runtime/move_plan.py` (`plan_step`, pure) plus `AgentManager._scan_ahead`,
`_plan_move` and `_direction_yaw`. The step now **shrinks** toward refused ground / a no-go patch /
a body-box contact and **grows** across cells the shared map says have been walked with good
footing, capped at 90 m. `walk_to`/`wander` gained an optional coarse `"distance":
"close|normal|far"`, and the length actually taken is stated back to the model next tick
(`last_move.plan.why`). No engine rebuild needed — every input was already in PlaceDB or the
observation. **Scope taken beyond the spec:** the spec's "cap at remaining distance to goal" was
*not* built, because the goal-bearing paths (routed legs, sweep centres) walk to exact coordinates
and never overshoot; the paths that DO overshoot are direction words, whose "goal" is the refused
patch or blocker ahead — so that is what caps them. Original spec follows. **Source:** user,
2026-08-20: *"Steps needs to be
adaptive. We seem to be running into bugs where 15 cm steps over shoots targets and we get into
oscillations. The steps need to be computed based on world evidence and not just blindly goto here."*

*(The constant is 15 **metres**, not 15 cm — `_STEP_DISTANCE = 1500.0` at `agent_manager.py:142`. The
failure described is real; only the decimal place is off, and 15 m makes it worse, not better.)*

### What is wrong

Every direction-relative move in the runtime is **exactly the same length**, forever, regardless of what
is in front of the body or how far the goal is. `_STEP_DISTANCE` is consumed by `_direction_target`
(`agent_manager.py:4098`), `wander` (`:4176`), the sweep view targets (`:1186`) and — the same constant —
the look-before-step neighbour lookup (`:3698`). Four consequences, and they compound:

1. **Overshoot, then oscillation.** A doorway 4 m away is reached by a 15 m step that ends 11 m past it.
   The only correction available is another 15 m step, back the other way, which ends 11 m short on the
   far side. **The action vocabulary cannot express "a bit closer", so the loop cannot converge** — it
   can only ring. This is the bug the user is reporting.
2. **It cannot aim finer than a trap is wide.** The code already admits this in a comment at `:1626`.
3. **A 15 m move is validated by one sample at its far end.** Look-before-step (#77) probes the point one
   step out; the fourteen metres of ground travelled to get there are never examined. The body commits to
   a distance the senses never measured.
4. **The prompt tells the model the truth and then gives it no lever.** `llm_router.py:30` describes
   `wander` as *"one step (~15m)"*. The model can pick a **direction** and nothing else. Every locomotion
   problem is therefore forced through the only free variable it has — heading — which is why heading
   thrash looks like indecision when it is actually a missing degree of freedom.

### The evidence is already in hand — every tick, no new engine work

- **`clearance_cm` and `fits`** from the #81 body-box probe: free travel before contact. This is
  *literally* "how far may I walk", already measured.
- **`_AHEAD_TRACE_CM`** (500) forward trace and its blocker distance.
- **`_STANDOFF_CM`** (300) personal space — the distance a walk must already stop short by.
- **Distance to the sweep target centre**, plus `arrive_tolerance` (`cell_size / 4`).
- **`PLACE_EXTENT_CM`** (900): a place is 9 m across, so a 15 m step **cannot deliberately land inside
  one**. The step is larger than the target it is aiming at.
- **Route distance-to-goal** and `_PROGRESS_NOISE_CM` (200).
- Footing underfoot, and the breadcrumb trail of legs actually walked.

Nothing here needs a plugin rebuild. The step length is computable from data the tick already collected.

### Proposed rule — deterministic, no LLM

`step = clamp(min(nominal, remaining_to_goal, clearance_cm − _STANDOFF_CM), floor, nominal)`

1. **Never step past the goal.** When the move has a target — a sweep centre, a place, a resolved name —
   cap the step at the remaining distance. **Overshoot dies here.** If only one thing on this list gets
   built, build this one; it is a handful of lines and it closes the reported bug.
2. **Never step into contact.** Cap at `clearance_cm − _STANDOFF_CM` when #81 reports contact. Below a
   floor (~100 cm) it is not a step, it is a wedge — fire the wedge fact (#65) instead of a token shuffle
   that burns a tick and proves nothing.
3. **Give the model three words, not fifteen metres.** Add `"distance": "close|normal|far"` to `walk_to`
   (~3 m / 15 m / 30 m), still capped by (1) and (2). A coarse word is a judgement a model can make from a
   picture; a number in centimetres is not. Consistent with [[feedback_facts_not_blocking]] — the cap is
   physics, the choice stays the model's.
4. **Report the length actually taken.** *"You asked for 15 m and moved 4 m; the doorway was the cap."*
   Without this the model cannot tell a short step from a stall, and a silently-shortened move is exactly
   the class of bug global rule 12 forbids. **Fail loud.**
5. **Decouple look from move.** `_direction_places` naming the cell one nominal step away is a *map*
   question and should stay at 15 m. The move length is a *body* question. One constant serving both is a
   coincidence, not a design.

### Open decisions

- **Does a shortened step cost a full LLM tick?** At ~9 s/tick, four 3 m steps spend 36 s of sim time and
  four decisions on one doorway. **Recommendation:** a shortened step continues **deterministically**
  (the pattern the sweep already uses — bridge-only, no LLM) until the goal is reached, a blocker appears,
  or the budget runs out. Fine motor control must not be priced at one decision per metre.
- **Does the neighbour-cell naming follow the shortened step?** Recommend **no** — see (5).

**Relates to:** #81 (supplies the clearance), #77 (shares the constant), #65 (most wedges are a step with
nowhere to go), #26, #61, #20 (movement pacing), #87.

### SR47 (2026-08-20) — the run was killed after 5 ticks. Both halves fired; the grow half was wrong.

**Killed by the user:** *"If the APCs act erratic and don't conform, no sense in keep running... Dufus
looked like he was doing the right thing, then came back to starting point and went into motor home and
stopped."* 5 ticks, 117 s, 2 APCs, zero engine errors.

**What worked.** Both mechanisms fired live on the first run: `move plan: east 90.0 m (wanted 90.0 m,
grew)` and `move plan: north 3.5 m (wanted 15.0 m, capped by refused ground)`. The `distance` word
reached the model unprompted — Dufus asked for `"distance": "far"` twice and `"close"` once, and the
close step moved him 2.0 m. The body-box probe (#81) ran for the first time; no `unavailable` warning.

**Why it was erratic — the step is a straight line, the engine walks a PATH.** `plan_step` names a
point `distance_cm` along a heading and hands it to the bridge, which is a navmesh `MoveTo`. The
navmesh routes *around* obstacles, so the further away the named point is, the more freedom the route
has to go somewhere else entirely:

| tick | ordered | achieved |
|---|---|---|
| 1 | north, `far` (45 m) | **52 m east**, 5.8 m north |
| 2 | north, `far` (45 m) | **48 m west**, 11 m north |

The engine confirmed the order was taken (`current_action: moving_to [-4691, -5884, 91]` is exactly
45 m due north of where he stood), so this is not a lost command — it is the path going round a
building. That is the user's "went out, came back to the starting point": the two legs are a 50 m
detour east and a 50 m detour back west. At the old fixed 15 m the same detour was a wobble; at 45–90 m
it eats the run. **The grow half was built on an assumption the engine does not honour.**

**Fixed, then fixed properly (2026-08-20).** The stopgap was `MAX_STEP_CM` 9000 → 3000. The real fix
landed the same day and the cap went back to **9000 (three cells, ~the user's "100 metres")**, because
the distance was never the problem — **handing the engine a far target was**.

**The walk plan (built).** A grown step is now cut into hops of one nominal step
(`move_plan.leg_distances`) and only the first is ordered. `AgentManager._pulse_walk` walks the rest,
one hop per tick, **bridge only — no perceive, no model call**, in a new tick phase beside the survey
sweep. The engine is never given a target further than the fixed 15 m it always walked correctly, so
the navmesh has almost no room to route around something and land somewhere else.

This is also the cost answer the exit condition needs: a 90 m crossing of proven ground is **one paid
decision and five free ticks**, where it used to be six paid decisions. Crossing ground the map has
already proved is not a thing worth thinking about.

**Five things end a plan and buy a full cognition tick** (`_end_walk_plan` sets `_force_next_decide`):
something ahead the body must reckon with (does not fit / inside the standoff / can move on its own);
drifting more than 7 m off the ordered line — the SR47 failure, now caught after **one hop** instead of
fifty metres; anyone arriving or leaving within sighting range, so a plan can never walk an APC past
someone it should have noticed; the hop making no ground for `_STUCK_TICKS` (a plan must never sit
silent against a wall for its tick budget — that is exactly what #65 exists to make loud); and a hard
ceiling of 12 ticks.

`_last_order` is deliberately untouched while a plan runs, so the achieved-versus-ordered check (#59)
and the new heading-drift fact measure the **whole** grown step against the one order the model gave.
A survey outranks a walk; an operator pulse ends the plan, because "pulse" must still mean "think now".

**Also fixed: the APC is now told when it did not go where it was sent.** `last_move.went` compares the
heading ordered against the heading achieved and states the drift as a fact (`DRIFT:` in the log). SR47
had Dufus ordering north twice and travelling east then west, with nothing anywhere saying so — the
prompt only ever reported the *distance* moved. Facts, not blockers: nothing corrects the heading.

**Also found — #81's `open_columns` names gaps that are not gaps.** The engine counts a column open when
**any** of its three rows is clear. In SR47 a sedan sat 17 cm into Dufus's `far_right` column at body
height, the row above it was clear, and the prompt told him *"the gap is on your: left, centre, right,
far right"*. Worse, `paint_set_10` produced `fits=False` with **all five columns open** — the capsule
struck something every ray missed, and the prompt claimed five gaps that did not exist. Dufus stepped
"left" into a gap he had been promised and ended up on a wooden dock over water.
**Fixed in Python, no rebuild needed** (`_open_columns` in `agent_manager.py`): a column is a gap only
when NOTHING in it is struck, and when the capsule says "does not fit" while no ray was struck at all,
the scan reports that it **cannot name a side** instead of naming five. The C++ `open_columns` is left
as it is and no longer read.

### SR49 (2026-08-20) — #86 VERIFIED LIVE. The blocker moves to #81's body-width raster.

22 ticks, 237 s, **zero errors, zero `DRIFT:` lines, zero `STALLED` lines.**

**The proof:** `move plan: east 90.0 m (grew)` → `walk plan: east 90.0 m in 6 hops of 15 m` → `hop 2/6`
… `hop 6/6` → `all hops walked`, and the decision log records **`moved 8971.4` cm ending on `y = -800.0`,
the exact y he started on.** Ninety metres, dead straight, no detour. SR47's failure did not recur.
The shrink half fired too: `northeast 38.0 m (wanted 45.0 m, capped by refused ground)`, capped by a
refusal Dufus had filed himself twelve ticks earlier.

**The cost win the exit condition needs:** walking ticks ran **1.66–1.89 s**; decision ticks ran
**10–24 s**. A 90 m crossing of proven ground is one paid decision and five near-free ticks.

**Where the run then stalled — Dufus bounced NE↔SW three times, ~30 m each way**, between
`trash_bin_bigOpen6` and `lantern8` at the village square. Every plan after the first died on a prop
within 5 m (`walk plan ended: prop 352 cm ahead`), he refused the ground northeast, went back, and
came again. His own words at tick 20: *"I've bounced here too many times"* — #26's bounce fact reached
him and he still had nowhere to go.

**Root cause, confirmed in the C++.** `UnrealMCPCharacterCommands.cpp:346` offsets each raster column by
`Right * (ColT * Radius)` with `Radius = 34` cm. **The scan is exactly as wide as the body — ±34 cm.**
`far_left` means 34 cm left of centre. So `open_columns` can only ever report gaps *inside the APC's own
shoulders*, which can never answer "how do I get around this". Dufus was told `open=none` while clear
pavement sat a metre either side. **This is a missing fact, not a reasoning failure** — exactly the
[[feedback_facts_not_blocking]] case.

**Fixed the same day as #88 — no rebuild needed.** The probe is turned instead of the body: -90/-45/
+45/+90, capsule sweep and all, and the APC is told which headings its body actually fits down. See
**#88** for why this beats widening the raster (which is still available later, but is no longer the
blocker). **SR50 is the test.**

**Also: Maren did nothing for the entire run.** 22 ticks, `moved 0.0`, 21 of them
`idle(scene_unchanged)` / `settled routine sampled; VLM sleeping`. She woke believing the schedule's
claim that the mobile home community is her truck post (*"Schedule says this spot counts as my truck
post despite the mobile home visuals"*), the settled-agent gate then suppressed cognition, and she never
moved again. #75/#71 place identity compounding with the settled gate into a fully asleep APC. Not
attempted; see the handoff's open questions.

### The step must grow as well as shrink (user, 2026-08-20)

*"As targets get closer, the steps need to get smaller. But when we have N grids in front of us, and
have all been cleared, surveyed, the steps need to increase. There is nothing ahead for the next 100
meters, right? I think we are missing a move plan."*

This is the half the original spec missed, and it is the half that pays for the overnight run.
Shrinking stops the APC landing in ground it refused; **growing stops it spending a paid decision
every 15 m to cross a district it has already surveyed.** Both come from the same scan of the shared
map along the heading, so they are one function, not two features: `_scan_ahead` returns
`open_run_cm` (how far the ground ahead has been *stood on* with good footing — the reason to grow)
and `stop_short_cm` (the first refusal along the line — the reason to shrink).

**"Proven" means walked, not seen.** A cell with a composite was *looked at*; a cell with good
footing in `cell_ground` was *stood in*. Only the second earns a 90 m order, which is why the run
grows over ground the survey has already crossed and never over ground it has only photographed.

**Done when:** an APC told to reach something 4 m away arrives at it without a reverse leg; an APC
crossing three surveyed cells does it in one order instead of six; and the movement log states the
requested and actual length whenever they differ.

---

## 87. Should the lizard brain be an LLM? — analysis, parked behind the overnight run

**Status:** ANALYSIS ONLY — deliberately not scheduled. **Source:** user, 2026-08-20: *"I'm starting to
think lizard brain needs to be more than a bunch of functions, but an LLM itself. Not sure it needs to be
integrated with a VLM, but maybe. This way the persona LLM living in the abstract world has a backstop
more tightly coupled to world brain."*

### The lizard brain already has two halves, and they answer differently

- **Senses** — `_probe_ahead` (#81), `_look_ahead` / `_direction_places` (#77), footing, grid `locate`,
  hearing, sighting. Pure measurement. **A VLM already lives inside this half**: perception turns the
  camera frame into labels.
- **Reflexes** — the standoff halt, the stuck detector, the wedge budget, deterministic sweep
  continuation. Code that *acts* without asking the persona.

**Making the senses an LLM is wrong and should never be done.** Raycasts, distances and cell arithmetic
are deterministic; a model there would be slower, cost more per tick, and could **hallucinate a
clearance** — a measurement that is confidently wrong is worse than no measurement. Global rule 5: if
code can answer, code answers.

**Making the reflexes a model is arguable**, and it is what the request is actually reaching for.

### The real gap — and it is real

**Nothing sits between the decision and the engine.** The persona emits `walk_to forward` and it executes
verbatim. The only cross-check is a fact printed in the *next* prompt, one tick (~9 s) later. That is
precisely the failing loop: wrong move → executed → observed → corrected → overshoot → repeat. An inner
motor loop running on raw measurements at engine cadence would close that inside the tick. The
architecture instinct — **fast inner loop on measurements, slow outer loop on meaning** — is right.

### But most of that gap closes without a model

#86's caps close overshoot. #81 closes "is it solid". #77 closes "what is over there". **Build those,
instrument the residual, then look.** If what is left is genuinely a judgement — *"the probe says the gap
is on my far left; is that gap a doorway or a hedge?"* — then it is a **visual** question, so the answer
is a **VLM**, not a text LLM. That resolves the "not sure it needs a VLM" doubt: if a model turns out to
be needed here at all, it is needed *because* the residual questions are ones only the picture can answer.

### Costs and conflicts, stated plainly

- **Per-tick cost.** A second model call per tick roughly doubles decision cost and adds latency, and the
  exit condition is an **unattended overnight run** — cost is the binding constraint (see the
  hybrid-provider note in the tail of this file). Any motor layer must be local or Haiku-class **and must
  be skipped entirely on clean ticks**.
- **It conflicts with [[feedback_facts_not_blocking]].** The standing rule is: when the model keeps doing
  X wrong, add louder facts and rules — not a code-side blocker. **An LLM veto is still a blocker, just a
  more expensive one.** Surfacing the conflict rather than averaging it (global rule 7).
  **Recommendation: a motor layer may SHAPE a move — shorten it, nudge the heading — but never REFUSE
  one.** Shaping is physics and belongs to the body; refusing is doctrine and belongs to the persona.
- **It amends [[feedback_lizard_brain_contract]].** Today's contract is *facts only, never advises*. A
  layer that shapes a move does act. If this is ever built, that contract changes on purpose and in
  writing — it does not drift.
- **Two brains that disagree need an arbiter, and there is no third.** Shaping-only avoids ever needing
  one; a veto layer does not.

### The shape it would take, if built

- **Where:** after the persona decides, before the bridge call — the seam #84's payload contract creates.
- **Input:** the requested action plus this tick's raw measurements. **No persona, no memory, no
  schedule.** It must not be able to reason about the character.
- **Output:** the same action with a length and heading, or `hold` plus a stated fact. Never a new action.
- **Model:** Haiku-class or local, sub-second, or it eats the tick.
- **Gate:** invoked **only** when a measurement contradicts the request (contact, standoff breach, goal
  nearer than one step). Clean ticks pass straight through in code and cost nothing.
- **Pass criterion:** fewer reverse legs and fewer wedge runs per 100 ticks than the #86-only build.
  **If it does not beat plain #86, it does not ship.**

### Recommendation

**Build #86 first**, and instrument *reverse legs per 100 ticks* and *wedge runs per 100 ticks* so there
is a baseline to beat. **Do not build #87 before the overnight run** — it adds per-tick cost and a second
failure mode to the exact loop the exit condition measures.

**Relates to:** #86, #81, #77, #84, #61, [[architecture_lizard_brain_sensing]],
[[feedback_lizard_brain_contract]], [[feedback_facts_not_blocking]],
[[project_dufus_vlm_training_corpus]].

---

## 88. Turn the probe, not the body — "which way CAN I go", measured

**Status:** **BUILT 2026-08-20, no rebuild needed — needs a test, needs SR50.** `AgentManager._open_headings`
probes `get_character_forward_volume` at -90/-45/+45/+90 whenever the body does not fit straight ahead,
and attaches `blocker.open_headings` (compass words, nearest-to-straight-ahead first, with the measured
clearance). `llm_router._open_headings_text` renders it. **Source:** SR49 — Dufus bounced 30 m back and
forth for fourteen ticks between a dumpster and a lantern, refusing ground and coming back, saying
*"I've bounced here too many times"*.

### Why the raster could never answer this

`UnrealMCPCharacterCommands.cpp:346` offsets each raster column by `Right * (ColT * Radius)` with
`Radius` read from the capsule — 34 cm. **The whole scan is exactly as wide as the body.** `far_left`
means 34 cm left of centre. So `open_columns` can only ever report gaps *inside the APC's own
shoulders*, and `open=none` is what a dumpster returns even with clear pavement a metre either side.
The APC was not reasoning badly; the only fact it had said "nowhere", so the only move left was to turn
around — and then the ground behind was fully surveyed, so it turned around again.

### Why turning the PROBE beats widening the raster

The C++ already reads `yaw_offset_deg` (`:224`) and builds `ProbeRotation` from it (`:258`) — and that
rotation drives the **capsule sweep quaternion**, not just the rays. So an angled call is a genuine
*"would my body fit if I walked that way"* test, which is the same question walking asks. A wider
raster would answer something smaller ("the gap is 80 cm to your left") and needs an editor rebuild.
**APCs steer by heading, not by raster column**, so the heading question is the one worth paying for.
Widening the raster stays available later for fine aiming inside a step; it is no longer the blocker.

**Cost:** four bridge calls, and only on a tick where the body is already blocked. Zero on a clean tick.

**Facts, not blockers** ([[feedback_facts_not_blocking]]): the sense names every heading that was
measured to fit and stops there. It never says which to take, and an APC with a reason to stay put
ignores all of them. "None of them fit" is stated as its own fact — being boxed in is real, and it must
stay distinguishable from never having asked.

**Relates to:** #81 (whose raster width this works around), #86 (the walk plan aborts on `fits=False`
and now hands cognition something to do about it), #26, #61, #65,
[[architecture_lizard_brain_sensing]], [[feedback_lizard_brain_contract]].

**Done when:** an APC blocked by a prop steps around it instead of retreating, and SR50 shows no
NE↔SW bounce at the village square.

---

## Order of work, and what is explicitly NOT proposed

**Do Phase A in order — #62, #63, #64, #65 — then run the sim with both APCs and grade the run on
Maren's day, not on Dufus's footing.** Most of Phase A is configuration and deletion. The carried live
check from the SR40 handoff (does a `blocker` line ever appear, proving the forward trace works — the
gate on #61) costs nothing and rides along on that same run; it does not need its own session.

**Not proposed:** no rewrite; no refactor of `agent_manager.py`'s 4,507 lines; no new navigation
subsystem; no abandoning the survey or the VLM corpus ([[project_dufus_vlm_training_corpus]] stands,
and #61 as written is good and stays parked until the `blocker` line is confirmed). The survey keeps
running — it just stops being the only thing that runs.

**Stated risk:** turning Maren on will break things, and testing Dufus's map against a real consumer
(#71) may look like a regression. It isn't — it is the first real test that map has ever been given.

---

## Outstanding — human / editor / live (not loop-safe)

- **#35/#13.4:** design the LLM-directed expedition contract and pristine-run purge boundary before
  implementing whole-map visual surveying.
- **#32:** choose transient gaze retention/dedup policy and whether owned landmarks receive their own
  four-image survey sets in addition to community cells. Community marker/composite inspection is done.
- **#27:** choose community-landmark anchor/extent semantics, then continue persistent-ticket and
  obstacle/dead-end work; coarse routed arrival itself passed in SR15.
- **PIE verification bundle:** #17 routed travel, #23 landmarks, #24 launcher, #13.2/#13.3 cockpit
  controls, #14 replay, B7b personal space, and sweep/map behavior. Record each result against its
  canonical item; do not create another status banner.
- **Child Blueprints:** choose and apply Maren/Dufus meshes in the editor; bindings already landed.
- **#12.2:** decide whether interaction content belongs in the episodic log or a dedicated store.

## Recently landed

- **Autonomous loop — 21 commits on `auto-loop/backlog`** (2026-06-26, offline-tested, unpushed):
  **#1** place-name nav (`walk_to "village square"` resolves to a location); the **loop harness**
  (`scripts/run_tests.py`, `plan/autonomous_loop.md`, `scripts/loop/preflight.py` — #4.1–4.3);
  green baseline (fixed a scene-unchanged grid/place regression + stale stubs); **#5** memory layer
  (`SocialMemory`, `EpisodicLog`, speech→interaction, relevance recall); **#6** map query
  (`known_places`); **#2.2** `config_store.py`; **#3/2.1** `factory.build_agent_manager`; and **#7**
  the **maintenance/monitor APC** (PlaceDB sweep state + community breadcrumbs, `cell_sweep` planner,
  `Agent.role`, `_maintenance_sweep`/`_nearest_unexplored_target`/`_pulse_maintenance`, tick routing).
  See `plan/handoffs/LATEST.md` for detail.
- **Agent activity display** (2026-06-25) — `observing`/`thinking` now push to
  each NPC's `AIState` from the sequential tick phases (`_set_activity` in
  `agent_manager.py`, `bridge.set_ai_state`). A Text Render component on
  `BP_CameraNPC` (bound to `AIState`, added in-editor) shows the word above each
  head. Verified live on cloud. *(Display lives on the shared base BP → child
  BPs in "Next up" inherit it for free.)*
- **Rename MCPCharacterComponent → APCCharacterComponent** (2026-06-25) — moving
  off MCP branding for the in-world component; `[CoreRedirects]` keeps existing
  Blueprints intact. Module/plugin stay `UnrealMCP` for now (larger separate job).
- **Place-cell DB reset** (2026-06-24) — `reset_world_places()` MCP tool wipes
  the shared `world_places.db` (place_cells, place_observations, agent_visits)
  for a true blank world; complements `reset_agents` which preserves the map.
  `PlaceDB.reset()` in `Python/agent_runtime/place_db.py`. *(Part of #1.)*

---

## ▶ Next up: Child Blueprints for per-agent meshes

**Status:** Rebind landed (2026-07-03); mesh choice pending · **Independence:** Self-contained

Dufus and Maren currently share one Blueprint (`BP_CameraNPC`) and look
identical. Give each its own mesh without duplicating logic.

- [x] Create child Blueprints of `BP_CameraNPC` — **user made `APC_Maren_BP` +
      `APC_Dufus_BP`** in-editor (2026-07-03), inheriting the shared
      `APCCharacterComponent` / AIState display / AI controller from the base.
- [x] **Rebind the agents (Python side) ✓ 2026-07-03.** Each `state.json` now
      binds to its child actor (`unreal_actor_name` = the placed label
      `APC_<Name>_BP`, `blueprint_class` = `/Game/Blueprints/APC_<Name>_BP.APC_<Name>_BP_C`).
      **Plus a display-name decoupling** so the engine label never leaks into the
      sim: new `Agent.display_name` ("Maren"/"Dufus") drives `known_characters`,
      and `_resolve_action_actor_refs`/`_actor_name_for` map a target back
      (display name / label / id → bound actor). Test: `test_actor_binding.py`.
- [ ] Pick the two meshes (project has `SkeletonCharacter` + AssetsvilleTown
      character skeletal meshes available). *(Editor + mesh choice — B-side.)*

*(The hand-linking done here is the first worked example of **#13** world-build
assistance — CC wires config when the user adds things, pending generation code.)*

Why child BPs not full copies: fix shared bugs once; the status-bubble display
and component come along automatically.

---

## 1. Named-place navigation + grid/place cells

**Status:** **Foundation complete** — name resolution and place/grid persistence landed; #17 added
multi-leg routing. Remaining navigation responsibility is canonical in #27. · **Independence:**
Self-contained (no dependency on #2/#3)

The real remaining navigation gap. A `walk_to` with a string place-name
("village square", "Don's Donuts", "Sheriff's office") currently short-circuits
to **idle** in `execute_action` (`Python/agent_runtime/unreal_bridge.py`) — there
is no resolver mapping a place name to a world location or scene actor. Agents
wander by direction/frontier but never navigate *to* a stated goal. (Dufus's
memory is a long loop of "still searching for village square.")

- [x] Build a place-name → PlaceDB cell-center resolver so `walk_to <place>`
      navigates instead of idling. ✓ 2026-06-26 — `PlaceDB.find_named_cell` +
      `WorldGrid.cell_center` + `AgentManager._resolve_place_target`, wired into
      `_execute_world_action`. Offline test: `scripts/agent_runtime/test_place_resolver.py`.
- [x] Finalize grid cells and place cells. Central community cells, APC-owned cells, extents,
      staleness, authored sources, and routed travel landed across A2/A5 and #15–#18.
- [x] Attach observations to grid/place cells through visits, compass observations, sweeps, and
      authored/runtime source tagging. Further movement policy belongs to #27.
- [x] Reset the place-cell DB to start from scratch (`reset_world_places()`). ✓ 2026-06-24

> Note: the walk_to *error* is already dead (no failures since 2026-05-14). This
> item is the genuine outstanding work — goal-directed navigation, not the error.

Relates to: engine-agnostic navigation, lizard-brain sensing.

---

## 2. World Sim web-app settings page + rename

**Status:** **Core built offline** — settings backend/page, provider profiles, navigation, and
surface rename landed; live UX spot-check/polish remains. · **Independence:** Coupled with #3
(shared web app)

The app's scope has grown past building individual NPCs — it's becoming the
control surface for the whole simulation.

- [x] Add a **settings/configuration page** to the web app — manage config
      (model/provider selection, sim parameters) through the UI instead of
      hand-editing `.env`. ✓ 2026-06-26; provider-profile CRUD followed 2026-06-28.
  - [x] Ollama/cloud selection is surfaced through named provider profiles.
- [x] Rename the active surface **"NPC Builder" → "Unreal World Sim"**. Legacy
      `npc_builder` code was later removed; #22 removed obsolete launch/MCP surfaces.

Config complexity is ours to solve in the UI, not the user's.

Action breakdown (from dreams iter 3, `plan/dreams/dreams_2026-06-25_1131.md` — subagent-ready):
- [x] **2.1** Rename surface strings only (`web_ui` templates, `main.py` title/docstring,
      `start_npc_builder.bat`, `/create-npc` skill prose); leave `npc_builder` *code identifiers* for a
      separate pass. ✓ 2026-06-26.
- [x] **2.2** New `agent_runtime/config_store.py` — `read_config()` (secrets as set/unset, never values)
      + `write_config()` that rewrites `.env` preserving comments/order, leaving omitted secrets intact.
      ✓ 2026-06-26. Offline test: `test_config_store.py`. *(Reload: callers invoke the existing
      `load_dotenv(override=True)` path — `reload_llm_environment`; not bundled into write_config.)*
- [x] **2.3** Settings page: `GET/POST /settings` in `web_ui/main.py` + `settings.html` + nav link.
- [x] **2.4** Provider selection generalized beyond the original toggle into named profiles with
      decision/vision role assignment. Live UX polish remains, not core implementation.

Decisions (human): persistence target `.env` vs new `config.json` (rec: `.env`)? secrets editable in the
form or set/unset display only (rec: display only)? rename scope surface-only now vs code identifiers too
(rec: surface-only)?

---

## 3. Independent sim lifetime

**Status:** **Built offline; live Unreal verification pending** — `sim_runner.py`, runner HTTP API,
`RunnerClient`, web cockpit, and one-click launcher exist. · **Size:** Potentially large ·
**Independence:** Coupled with #2

Originally Claude Code owned the simulator lifetime. The standalone runner now owns it and the
web cockpit controls it over localhost HTTP; remaining work is live verification and hardening.

The coupling is one line: `unreal_sim_server.py:417` `mcp.run(transport='stdio')` — the MCP
server is a stdio subprocess of Claude Code, and the `AgentManager` (async sim loop) lives inside
it. `UnrealBridge` (TCP 55557) + the web UI's direct socket are already Claude-independent.

Action breakdown (from dreams iter 2, `plan/dreams/dreams_2026-06-24_2327.md` — subagent-ready):
- [x] **2.1** Factor `AgentManager` construction into `agent_runtime/factory.py` (shared by MCP + runner).
      ✓ 2026-06-26 — `build_agent_manager(worlds_dir=None)`; `get_agent_manager` now delegates to it.
      No I/O at construction, so offline-testable: `test_factory.py`.
- [x] **2.2** New `Python/sim_runner.py` — standalone process that runs the loop with no MCP/Claude.
- [x] **2.3** Control surface on the runner (localhost HTTP: start/stop/status/tick).
- [x] **2.4** Make `simulation_tools.py` thin clients of the runner (attach, don't host).
      ✓ 2026-07-03 — every director tool goes through `RunnerClient`; no runner reachable = loud
      error with the start hint (never an in-process manager). Runner API + client grew the missing
      director surface; `generate_world_grid` moved into `AgentManager` (the runner owns the bridge).
      Offline end-to-end: `test_sim_tools_attach.py`. *Live verify: run `sim_runner` + drive one tool.*
- [x] **2.5** Point web_ui at the runner control API (→ theme #2/③ controller). Fleshed out in dreams
      iter 3 (`plan/dreams/dreams_2026-06-25_1131.md` Action 3.5): `sim_runner_client` in
      `web_ui/unreal_client.py` + a dashboard status panel and start/stop buttons; no auto-spawn (keep
      lifetime decoupled); if no runner is reachable, render "no sim runner running". ✓ 2026-06-26.

Decisions (human): IPC = HTTP (rec)? auto-spawn runner from MCP (rec: no)? Unreal socket owned by
runner exclusively (rec: yes — bridge isn't concurrency-safe)? one runner/machine vs per-world?

The sim is the product; Claude is a tool for building it, not a required host
process. The standalone launcher likely belongs in the same web app as #2.

---

## 4. Autonomous building loop (run unattended until limits, resume next session)

> **Split (dreams iter 5):** **#4a — the harness** (4.1 contract, 4.2 preflight, 4.3 aggregator) is pure
> Python/offline and can be built **now**, even exercised on #1 before #3 exists — it makes **no LLM calls**,
> so it's cheap on cloud. **#4b — running the *live* sim unattended** is what's gated by #3 + local models
> (per-tick inference cost). Don't let #4b's blockers stall #4a.

**Status:** **Harness built; Codex workflow refresh landed** — test runner/preflight and the five
project-local skills are committed on `main` as of `0d64b21`. Live-sim
autonomy remains gated by cost and Unreal/PIE. · **Size:** Process/setup, not a code feature ·
**Depends on:** #3 live verification for live-sim autonomy

Goal: put Claude into a **self-paced `/loop`** that works this backlog
unattended — building, testing, committing — until the daily credit/usage limit
cuts it off, then **resumes the next session** from the handoff. The idea is to
use up daily credits productively instead of leaving them unspent.

**How it would run:**
- [ ] `/loop` with no interval (self-paced): work backlog items, each as
      branch → failing test → implement → run tests → commit on green → update
      this backlog. Cross-session continuity comes from `plan/handoffs/LATEST.md`
      + this file (the loop reads them on each start). Optionally a daily
      `/schedule` routine kicks it off after credits refresh.
- [ ] There is **no "credits draining" signal** to detect — the session just
      stops when limits hit. The handoff is what makes it recoverable, so the
      loop must keep the handoff/backlog current as it goes.

**Guardrails (must have — unattended = errors compound):**
- [ ] Dedicated branch; commit every green step; **never push** unattended.
- [ ] **Never** touch C++, Blueprints/UMG, or `.env`; never start the sim / need
      PIE. (These need an editor rebuild + MCP restart Claude *cannot* do itself —
      see #3 — or a human decision.)
- [ ] Skip + log (don't guess) anything needing the editor, a rebuild, a design
      choice (e.g. meshes), or that's ambiguous. Stop if tests fail and can't be
      fixed in ~2 tries.

**What's actually loop-safe here:** Python-only, test-verifiable work. Best first
target is **#1 named-place navigation** (self-contained, testable). Blocked from
autonomy: Child-BP/meshes (editor + design), settings page UX, anything C++.

Action breakdown (from dreams iter 4, `plan/dreams/dreams_2026-06-25_1149.md` — subagent-ready).
Key grounding: tests here are **standalone offline scripts** under `Python/scripts/**/test_*.py` (14
today) that stub Unreal entirely — that offline-stub surface *is* the loop-safe zone (no pytest, no PIE).
- [x] **4.1** Write `plan/autonomous_loop.md` — the run-contract the loop reads each start (allowed
      surface, hard NOs, stop conditions, per-item cycle). ✓ 2026-06-26.
- [x] **4.2** `Python/scripts/loop/preflight.py` — refuse to start unless tree clean, on a dedicated
      loop branch (not `main`), and baseline tests green. ✓ 2026-06-26 — pure guards
      (`is_loop_branch`/`tree_is_clean`/`evaluate`) + live git/test gathering. Test: `test_preflight.py`.
- [x] **4.3** `Python/scripts/run_tests.py` — discover + run every offline `scripts/agent_runtime/test_*.py`,
      one PASS/FAIL signal; `--only <glob>` for the in-progress test. ✓ 2026-06-26. (Socket-based
      actors/node/blueprints tests need live Unreal — excluded.)
- [ ] **4.4** First target failing-test-first: `test_place_resolver.py` + a PlaceDB place-name→cell-center
      resolver, wiring `walk_to` to navigate instead of idle (drives backlog #1).
- [ ] **4.5** Recoverability: update `handoffs/LATEST.md` + check off backlog on every green commit
      (the `/handoff` skill already does most of this) — this is what makes the loop resumable.

Decisions (human): run on cloud now since the *build/test* loop makes no LLM calls (rec: yes; keep live-sim
for local models)? kickoff via `/schedule` vs manual `/loop` (rec: manual first)? branch-per-item (rec:
yes)? human reviews each loop branch before `main` (rec: yes — "never push" implies never auto-merge)?

**Why local models matter for this (the link):** an unattended loop on cloud
(Haiku + Gemini) burns paid credits fast and exactly defeats the "use unspent
credits" aim — the cost lands on API spend instead. **Full-local (or hybrid)
inference is what makes long autonomous/overnight running viable without blowing
up credits.** So local models (below) and #3 are the real enablers of this goal.

---

## 5. Episodic observation + social memory layer

**Status:** **Core memory layer built** — episodic/social stores, prompt recall, consolidation, and
recent-greeting suppression landed; #12.2 interaction schema and sentiment policy remain open. ·
**Independence:** Extends #1 · **Source:** dreams iteration 1
(`plan/dreams/dreams_2026-06-24_2308.md`)

Today observation is split: spatial facts → `world_places.db` (good); everything episodic →
free-text `memory.json`, capped at 30 and trimmed. No structured record of *what happened* or
*who an agent met*, and recall is just importance+recency. Long/overnight runs forget.

- [x] **Episodic observation record** — persist structured per-tick events
      `{world_time, grid_cell, place, saw[], action, outcome}`. ✓ 2026-06-26 — `EpisodicLog`
      (`episodic_memory.py`, append-only per-agent `episodes.jsonl`); `AgentManager._record_episode`
      records each acted tick in the live path; `query(place=/character=)` for recall. Offline test:
      `test_episodic_memory.py`. *(Wired in the live decision path; explore-mode ticks not yet logged.)*
- [x] **Social/acquaintance store** (per agent) — `{character: {first_met, last_seen, last_cell,
      meet_count, interaction_count, sentiment}}`. ✓ 2026-06-26 — `SocialMemory`
      (`social_memory.py`, per-agent `social.json`); fed from perceived characters via
      `AgentManager._record_sightings` in the perceive phase; acquaintances surfaced on the
      observation for recall. Offline test: `test_social_memory.py`.
      `speak_to` now logs an interaction with each perceived named person
      (`AgentManager._record_interactions`, neutral sentiment — affinity isn't inferred without a
      real signal). *Still open:* a sentiment policy (would need an LLM/heuristic signal).
- [ ] **Social goal hooks** — let the decision layer propose "greet <person not seen today>" /
      "go where people are" (needs #1 to resolve person/place → location to navigate).
- [x] **Memory retrieval** — relevance = recency ⊕ spatial (same cell/place) ⊕ social (known face
      present). ✓ 2026-06-26 — `EpisodicLog.relevant()`; surfaced as `observation["recent_episodes"]`
      (top 5) in recall. Tested by ordering properties, not magic constants (`test_episodic_memory.py`).
      *Still open:* periodic **consolidation** (summarising old episodes) — needs an LLM summariser,
      so deferred out of the loop.

Open Qs (for human): episodic obs shared vs private per agent? scripted vs LLM-chosen sociality?
rolling window + consolidation vs full episodic history?

---

## 6. Map feature — named-place query + manual capture + lizard-brain routing

**Status:** **QUERY/ROUTE-PROMPT SLICE REOPENED 2026-07-21** — query/authoring/visualization and
coarse routing landed through #1, #16, #17, #18, #23, and #27; the navmesh path-as-facts query and
guaranteed pre-decision delivery remain outstanding. · **Independence:**
Builds on #1 (place resolver) · **Source:** user, 2026-06-26

A first-class **"map"**: a queryable set of **named places**. An agent asks the map *what
places exist* (and roughly where), picks a destination, then asks **lizard brain** *how to get
there* — lizard brain returns a **path / road-map** (a route to follow). #1 already built the
*lookup half* (name → cell → world location, `find_named_cell` + `cell_center`); this item adds
the **map query surface**, a **manual authoring mode**, and the **routing call**.

**Two SIM modes for building the map:**
- [ ] **Explore mode** (exists today) — agents build the map out themselves via the
      frontier/explorer policy, naming cells as they go (`PlaceDB.set_name`).
- [ ] **Manual / authoring mode** (new) — the **end user** moves around the world and takes
      **"snapshots"** at a spot, creating a named place from that location (screenshot + name +
      world position → `PlaceDB.set_name`). Lets a human author the map without running agents.
      *(Per [[feedback_drag_and_drop]]: the user must not need Unreal knowledge — capture is a
      button + a name, the world position is ours to read.)*

**The agent → map → lizard-brain flow:**
- [x] **Map query** — expose the named places to an agent: "what places do I know?" returns the
      named cells. ✓ 2026-06-26 — `PlaceDB.all_named_places` + `AgentManager.known_places(location)`
      (name + compass bearing + distance_m, nearest first); surfaced as `observation["known_places"]`
      (nearest 8) for recall, so the agent can pick a destination by name and `walk_to` resolves it
      (#1). Offline test: `test_map_query.py`. *(Chose context-injection over an LLM tool for now —
      revisit if the place list grows large.)*
- [ ] **Lizard-brain routing** — agent asks "route me to <named place>"; lizard brain uses a nav
      primitive (navmesh **path query**) and returns a **path** — a sequence of waypoints/headings
      to the place. The LLM still *decides whether to follow it*; lizard brain only reports the route.

**Renewed requirement and live evidence 2026-07-21 (SR28):** the world now contains a named community
cell called `village square`, yet Dufus followed competing home/survey/schedule intents and backtracked
before heading toward the village. When cognition says “I have to go to the village square,” lizard brain
must query the canonical PlaceDB name resolver for the matching grid cell, query a traversable route from
the APC's current position to that cell, and place both facts in the same decision context: resolved name,
target `(col,row)`, target world center/arrival region, reachability, and a bounded semantic waypoint or
heading sequence. Do not depend on the LLM remembering where the name is, and do not let the model invent
engine coordinates. The route is factual context; the LLM retains the choice to follow or revise it.

Acceptance evidence: with `village square` named in PlaceDB, a travel decision receives its exact resolved
cell and a valid current-position-to-target path before choosing an action; an unknown or ambiguous name
produces an explicit grounded failure/candidate list; route progress is refreshed after deviation or an
interruption; and a live run reaches the village square without returning to an obsolete starting point.
**Classification:** C++/editor nav-query integration plus loop-safe resolver/context/policy tests and
live/PIE navigation verification. **Dependency/open decision:** reuse the existing UE navigation bridge
if it can return path points; otherwise add a read-only path-query primitive. Preserve #27's movement
execution and #36's intent arbitration rather than embedding goal priority in the route provider.

**Design tension to resolve (human):** returning a *path* brushes against the **lizard-brain
contract** ([[feedback_lizard_brain_contract]], [[architecture_lizard_brain_sensing]]): lizard
brain reports **facts**, never advises. Keep it on-contract by treating a path as **facts**
("waypoints: NE 40m → E past the fountain → N 15m"), **semantic** (per [[architecture_lizard_brain_sensing]]
the output is generic labels/headings, never raw engine waypoints or actor names), and
**non-prescriptive** (the LLM chooses to follow, deviate, or ignore it — consistent with
[[architecture_engine_agnostic_navigation]]: the cognitive loop owns navigation decisions, the
engine just answers "is there a path and what is it").

Decisions (human): map query as an LLM tool vs. context injection? manual-mode capture UI — where
(settings page #2 / a new authoring view) and what's in a "snapshot" (screenshot + name + pos)?
path granularity — coarse semantic directions vs. a waypoint list? does lizard brain *walk* the
path (follow waypoints) or just *hand it back* for the LLM to drive step by step?

Relates to: #1 (resolver — lookup half done), #5 (social/episodic — "places where people are"),
[[architecture_engine_agnostic_navigation]], [[architecture_lizard_brain_sensing]],
[[feedback_lizard_brain_contract]], [[feedback_drag_and_drop]].

---

## 6b. APC-generated top-down map — lizard-brain "chart me a course"

**Status:** **Built offline 2026-07-01; PIE attachment verify pending** · **Source:** user,
2026-07-01 · **Independence:** builds on #1/#6 + lizard brain

An APC needs to build its **own top-down map** to plan a route, generated on demand via **lizard brain**.
The scenario the user gave: *"I woke up, I'm at my house, but my schedule says I need to be at my
vegetable truck. Build a top-down map of where I am and where I need to be, so I can chart a course."*

- [x] **APC map-view component** ✓ 2026-07-01 (WP5 built — see sign-off note below) — `route_map.py`
      builds corridor facts from PlaceDB + WorldGrid and renders a top-down PNG; injected on travel
      ticks into the decision prompt + attached to the multimodal decision call.
- [x] **Charting a course** — the substrate is in the APC's hands (map facts + image on every travel
      tick; the LLM charts the course). ✓ 2026-07-01. *The navmesh path-as-facts query stays open as
      #6 "lizard-brain routing" — it would slot into `build_route_map` output as `"route": [...]`.*

Ties into: the "restart day / morning" flow (#10 + A3) — on wake with a schedule destination, the APC
builds this map to get moving; #6 (lizard-brain routing — path as facts); #1 (name→cell resolve);
[[architecture_lizard_brain_sensing]], [[feedback_lizard_brain_contract]] (map/route must stay **facts**,
never prescriptive advice).

*(Design questions for later — do not implement yet: is the "map" a semantic structure the LLM reads, or
a rendered image? how far around the APC does it extend — just the corridor between here↔there, or a
radius? shared with the web A1 view or separate?)*

**APPROVED + BUILT ✓ 2026-07-01** (user signed off the four decisions same session; see
`plan/specs/WP5-apc-topdown-map.md` executor notes). Sign-off: **Q1 = RENDERED IMAGE** (user's call,
diverging from the semantic-text rec — the facts dict is still built, the PNG is a projection of it,
attached to the multimodal decision call), Q2 corridor+1 cap 15×15, Q3 separate renderer over shared
PlaceDB, exposure = travel ticks only. Built: `route_map.py` (`corridor`/`build_route_map`/
`render_map_image`), `AgentManager.route_map_for` (community→owned resolution), travel-tick injection
in `_perceive_and_decide`, `{route_map_note}` prompt section, image passed to the anthropic/ollama
decision call (OpenAI text-only). Test: `test_route_map.py`. Suite 30/30. **Remaining: PIE verify**
(map attaches on a live travel tick; folds into B2).

---

## 6c. Real-world PNG map background — grid + place cells overlaid on the actual world

**Status:** **Superseded/completed by #18** — the registered live camera replaced manual
assume-bounds calibration and agent dots were user-verified. · **Source:** user, 2026-07-03 ·
**Independence:** extends A1 (web `/map`) + #6b

> **⚑ Built 2026-07-05:** calibration decision made by the user ("if the actual world is m×n, we
> carve that up into 30 m cells — calculate off that fact") = **assume-covers-bounds**: the capture
> frames the world bounds exactly, world→pixel is linear. Orientation follows the project compass
> convention (`place_db.py`): **+X = east = image right, +Y = south = image down, row 0 = north/top**
> (image 1023×670 aspect 1.527 ≈ bounds 47000×30859 aspect 1.523 — confirms whole-world framing).
> `WorldGrid.origin()` exposes the origin-anchored cell (0,0) corner (starts *outside* bounds —
> edge cells crop at the image edge, `overflow:hidden`). `/api/map` now carries
> `bounds/origin_x/origin_y/image_url` + owned `dx/dy/extent_cm`; `map.html` draws the capture as
> the background with translucent world-registered cell overlays + purple 9×9 m owned-place boxes
> (first consumer of `extent_cm`). Per-level `images/<level>.png` beats the shared
> `world_map_view.png`; no capture → plain background at the world's aspect (same overlay engine).
> Tests: `test_map_view.py`, `test_world_grid.py`. **Live verify:** open `/map` in a browser over
> the real capture; re-shoot the capture if the gridlines look offset from the town.
· **Asset in place:** `Python/web_ui/images/world_map_view.png` (1023×670, a top-down capture of the
whole level; the user added it "for future work").

Today both maps are **abstract**: the web `/map` (A1) is a bare CSS grid of colored cells, and the #6b
route map is a rendered top-down of cell states. The user wants the grid + place cells drawn **on top of
a real top-down image of the world**, so you see the actual town with the grid, named community cells,
and APC-owned place cells (the 3 m boxes / bigger building extents) registered over it. Applies to the
web `/map` first; could later back the #6b APC route map too.

**The crux is registration (world ↔ image-pixel mapping), not drawing.** Everything else is
straightforward overlay work; the hard part is knowing which world (X, Y) each pixel is.
- The capture already looks **whole-world framed**: image aspect 1.527 ≈ world-bounds aspect 1.523
  (`world_grid.json` bounds 47000×30859 cm). So a first cut can assume *the PNG covers exactly the grid
  bounds* and map linearly bounds→pixels. Verify before trusting it.
- **UE axis orientation must be reconciled:** X is forward/north-ish (red), Y is right/east (green),
  and our grid convention is **row 0 = north (−Y) at the top** (see A1 / `route_map.py`). The capture's
  in-editor axis gizmo (bottom-left of the screenshot) shows X/Y rotated from screen up/right, so the
  overlay needs an explicit `world→pixel` transform (which world axis → image u, which → image v, and
  the sign/flip), not an assumption.
- Make it **robust to re-capture:** store the image's world extent + orientation next to it (e.g.
  `world_map_view.json`: `{covers_bounds: {min_x,min_y,max_x,max_y}, x_axis:"right|left|up|down",
  y_axis:...}` or a 2-point calibration `pixel↔world`). Then a new screenshot at a different framing
  just updates that file, no code change. Decision below.

**Build sketch (once registration is settled):**
- `web_ui`: serve the PNG (static route/`/images/...`); add a `world→pixel` helper from the calibration.
- `map.html`: put the PNG as the `#grid` background (or an absolutely-positioned layer under it), size
  the grid to the image, and make cells a **semi-transparent overlay** with an opacity/hide toggle so
  you can see the town through them. Named/swept/owned styling unchanged.
- **Place-cell markers:** draw community names at their cell centers and owned places at
  `cell_center + (dx,dy)` (already in `all_owned_places`), sized by `extent_cm` (the 3 m box, bigger for
  buildings) — the first consumer of the extent field (#11.2 D5 left it unused).
- Keep the abstract grid as a fallback when no image/calibration exists (worlds without a capture).

**Decisions (human, later):** calibration method — assume-covers-bounds (simplest, works if every
capture is whole-world ortho) vs. a stored world-extent JSON vs. an in-UI 2-point click-calibration
(most robust to ad-hoc screenshots)? Is the capture **orthographic** (needed for a clean linear map) or
a perspective shot (parallax → non-linear, would need corner homography)? One shared background for the
web map and the #6b APC route map, or separate?

Ties into: A1 (web `/map`), #6b (APC route map), #11.2 (owned-place extents), #1 (name→cell resolve),
`generate_world_grid` (bounds source), [[architecture_lizard_brain_sensing]].

---

## 7. Community place-cell sweep — unexplored-cell 360 + breadcrumbs  *(mechanics; role RETIRED)*

**Status:** Mechanics built; **dedicated-role concept retired 2026-07-01** — behavior folded into **#11**
· **Independence:** Builds on #1/#6 + PlaceDB · **Source:** user, 2026-06-26

The **sweep mechanic**: in a grid cell that has **no place cell**, an APC walks to the cell **center**,
does a **360 observation**, then drops a **community place-cell breadcrumb** there. The breadcrumb marks
the cell explored so other APCs reuse it and **skip the costly 360** (vision calls) — shared knowledge,
paid once. This engine is built and offline-tested (below) and stays.

> **DIRECTION CHANGE (user, 2026-07-01):** the earlier "**dedicated maintenance/monitor APC** — a
> personality-free, LLM-free system worker" concept is **RETIRED**. There is **no** special maintenance
> role. **Any APC builds a community place cell when it needs one** (it enters an uninitialized cell it
> wants to use → detours to center → 360 → breadcrumb → resumes its task). The `role:"maintenance"`
> gating (`_pulse_maintenance` and the role branch in `pulse_agent`/`tick`) should be **collapsed** so the
> sweep is a capability any APC invokes, not a role. Tracked as **#11.1**. *(Superseded design note, kept
> for history: this was previously framed as a dedicated worker "not a personality NPC" — that framing is
> now dropped entirely.)*

- [x] **PlaceDB sweep state** ✓ 2026-06-26 — `is_explored(col,row)` (named OR swept),
      `mark_swept(agent,col,row,t)` drops an unnamed community breadcrumb (first sweep wins,
      never clobbers a name), `get_swept`. Schema migrates existing DBs (adds `swept_at`/`swept_by`).
      Test: `test_cell_sweep.py`.
- [x] **Pure sweep planner / state machine** (`cell_sweep.py`) ✓ 2026-06-26 — `CellSweep` sequences
      GOTO_CENTER → observe each of 8 compass headings → DONE (sticky arrival); `default_sweep`
      builds one from the world grid (None if unbounded). Test: `test_cell_sweep.py`.
- [x] **Maintenance role + sweep behavior** ✓ 2026-06-26 — `Agent.role`/`is_maintenance` (from
      `state.json`, default `npc`); `AgentManager._maintenance_sweep` runs the sweep on an unexplored
      current cell and drops the breadcrumb on finish. All offline-tested.
- [x] **Maintenance tick action (compose sweep + travel)** ✓ 2026-06-26 —
      `AgentManager._maintenance_tick_action`: sweep the current cell, else walk to the nearest
      unexplored cell (`_nearest_unexplored_target` + `PlaceDB.explored_cells`); None when the whole
      map is mapped. Offline-tested.
- [x] **Wire the tick by role** ✓ 2026-06-26 — `_pulse_maintenance` runs a maintenance agent's
      deterministic, no-LLM tick (build obs → `_maintenance_tick_action` → bridge); routed in both
      `pulse_agent` and the multi-agent `tick()` (peeled out of the perceive/decide phases, run in
      the sequential bridge phase). Offline-tested. Safe: only `role:"maintenance"` agents take this
      path, and none exist yet.
- [x] **Live 360 rotation+capture (`observe_heading`)** ✓ 2026-07-01 — **no C++ needed** (the assumed
      "bridge/C++ handler" was stale): composed in Python from the wake look-around's existing primitives
      — `AgentManager._execute_sweep_observe` does `set_facing` (rotate in place) → settle → `capture_view`
      → perceive → `PlaceDB.ingest_compass` under `yaw_to_compass(yaw)`; routed from
      `_execute_world_action` on `observe_heading`. Degrades per-heading (bad turn/capture/vision records
      nothing, never wedges the sweep). Offline-tested end-to-end with stubs (full 8-heading sweep
      populates 8 compass observations): `test_cell_sweep.py`. *Live PIE verify remains (B-side).*
- [~] ~~**Spawn/config a maintenance APC**~~ — **obsolete**: the dedicated role was retired (#11.1/WP3);
      any APC sweeps. Nothing to spawn.

Relates to: #1 (cell_center resolve), #6 (map/known_places), #5 (episodic), engine-agnostic nav.

---

## 8. Talk to Unreal without MCP (Claude-driven + standalone)

**Status:** **Standalone and HTTP operator paths built; custom MCP retired by #22.** Documentation
and higher-level dev-mode ergonomics remain under #9. · **Source:** user, 2026-06-28 ·
**Independence:** relates to #3

Two ways to drive Unreal, and the user wants **both** to work without the custom MCP:
- **Standalone (no Claude):** already largely solved — `UnrealBridge` talks to the engine over a
  **raw TCP socket (:55557)** that is independent of MCP/Claude, and `sim_runner` + the web cockpit
  drive the loop through it (#3/#6). This path doesn't touch MCP at all.
- **Claude-driving (when Claude is running):** today Claude reaches Unreal *through* the `unrealSIM`
  MCP tools. The question the user raised — *"how can you talk to Unreal but not use MCP?"* — is how
  Claude keeps a hands-on path once MCP is retired. Candidate: Claude calls the **runner's HTTP
  control API** (`sim_runner` on :8777) and/or a thin **bridge HTTP shim** over the existing TCP
  socket, instead of MCP tools. The web UI already proves the runner API is enough to drive the sim.

- [ ] Decide the Claude→Unreal path post-MCP: runner HTTP API (rec) vs a small bridge HTTP shim vs
      Epic's official Unreal MCP. (User likes Claude driving when it's running, but not via *our* MCP.)
- [ ] Document/expose whatever Claude needs on the runner's HTTP surface so a session with no
      `unrealSIM` tools can still inspect + nudge the sim.

Relates to: #3 (standalone runner), the MCP-deprecation idea below.

---

## 9. Dev mode vs sim mode — Claude as operator

**Status:** **Partially realized** — standalone sim mode and HTTP controls exist; a durable supervised
operator workflow and log-triage contract remain open. · **Source:** user, 2026-06-28 ·
**Independence:** uses computer/browser use, needs supervision first.

Two operating modes the user wants framed explicitly:
- **Sim mode** — the sim runs **standalone**, web-driven, no Claude/MCP (the #3/#6 work).
- **Dev mode** — Claude Code is running and acts as the **operator**: start/stop the sim on request,
  and **help read logs + debug when things break** (a core dev-mode job).

The goal is to grow Claude into a hands-on operator of the dev loop:
- [ ] **Start/stop the World Builder web UI** (and the sim) from Claude — today `start_sim.bat` /
      `start_npc_builder.bat` boot them; wire Claude to launch/kill them (background process control).
- [ ] **Iterate on code changes via the web UI** — make a change, (re)start the UI, drive it with
      **browser use**, observe, fix. Claude has **computer + browser use**.
- [ ] **Log triage** — fluent at pulling the sim/runner logs and pinpointing failures (dev-mode's
      bread and butter).
- [ ] **Autonomy progression** — *supervised first*; once it runs smoothly, Claude does the
      start/stop/test/iterate loop **itself until credits run out** (ties into #4 / [[project_autonomous_loop]]).

Decisions (human): which logs are canonical for triage? how does Claude detect "UI is up / healthy"
before driving it (health endpoint vs port check)? guardrails for unsupervised UI-driving runs?

---

## Later / ideas

- **Bridge as a Runtime module → run the sim from a *packaged* build (no editor)** (user, 2026-06-28).
  Today the sim **hard-requires the editor in PIE**: the `:55557` bridge lives in the
  `UnrealMCP.uplugin` module declared `"Type": "Editor"` (`UnrealMCPBridge.cpp`, `MCP_SERVER_PORT 55557`)
  and depends on **EditorScriptingUtilities**, so it is **not cooked into a packaged `.exe`** — a
  standalone build would never open the socket and every tick would fail. To take the editor "out of
  the equation" the bridge must be ported **`Editor` → `Runtime`**: flip the module type/loading phase,
  drop the EditorScriptingUtilities dependency, and replace every editor-only call (editor-world actor
  lookups via `GEditor`/editor subsystems, `EditorScriptingUtilities`, etc.) with runtime equivalents
  that work in a cooked game world. Deliberate C++ work, **needs an editor rebuild** (not loop-safe).
  Big payoff: one game window, no PIE-vs-editor-world ambiguity, no multi-instance confusion (see memory
  `feedback-single-unreal-instance`), and it's the natural host for the "runs overnight" standalone sim
  (#3) — Claude could launch/kill the packaged build directly (dev mode, #9). *Until this lands, the
  editor in PIE is required and there must be exactly one instance — the user's.*

- **Deprecate the custom MCP server** (user direction, 2026-06-26). Move Claude to plain **API calls**
  for coding help and back away from the bespoke `UnrealMCP` Python MCP server entirely — **Epic now
  ships an official Unreal MCP server**, so maintaining ours isn't worth it. Phased, and done *last*
  (once the web UI fully drives the sim): (a) sim fully drivable with **no MCP** (web UI → `sim_runner`);
  (b) anything Claude needs goes through API calls / the runner's HTTP API; (c) retire
  `unreal_sim_server.py` + the `tools/*` MCP registration. The standalone-sim + web-cockpit work
  (queue #6/#7) is the on-ramp to this.

- **Hybrid provider config (cloud + local mix).** Run some roles on cloud and
  others local — e.g. cloud Haiku for decisions, local qwen for vision, or vice
  versa. Already partly possible: `LLM_PROVIDER` and `VISION_PROVIDER` are
  independent in `.env`. The feature is making the mix easy to manage (per-role,
  maybe per-agent) and surfacing it in the settings page (#2/#7). **Note (2026-06-28):** Haiku 4.5
  is multimodal, so the simplest cloud setup is now **Haiku for *both* decisions and vision** (one
  provider, one key) — Gemini is no longer required for vision (#7.0). Cloud is clearly
  faster today (~9s/tick vs ~215s cold local first tick); full-local stays the
  long-term goal once the other pieces are in. **Local/hybrid is the cost enabler
  for the autonomous loop (#4)** — unattended cloud runs burn credits. Not a
  priority now, but it's the unlock for overnight autonomy.

- **Build-documentary for YouTube (LOW PRIORITY).** *(user, 2026-06-28)* Turn the project's progress into
  a documentary series — **one video per stage/milestone** — that Claude can largely assemble. The raw
  material is already accreting: **git history** (commits = stages), **`plan/handoffs/*`** (session diary),
  the dated **backlog status banners**, the **`MASTER_PLAN` milestones** (natural episode boundaries), and
  the sim's own visuals — **PIE screen-recordings**, per-agent **`observations/*.png`**, and the web
  cockpit feed. The "money shots" are live moments (e.g. *Dufus routing to the village square* on the day
  named-place nav first worked). Plan: (a) a per-stage **narration/script** generated from the milestone +
  its commits/handoff; (b) **capture** the matching live demo (screen-record a PIE run); (c) **assemble**
  via the existing **`fal-video-pipeline`** skill. Each episode = *what we set out to do → the problem →
  the fix → the live demo*. Decisions for later: capture tooling (OBS vs. in-engine), how much is
  AI-narrated vs. the user's voice, episode cadence (per milestone vs. per session). Not loop-safe (needs
  capture + the user's channel/voice) — park until the sim is more visually compelling.

## Notes

- **Current priority and classification live only in the Active view at the top.** Dated
  banners and old queues are evidence, not instructions.
- **The historical #32 → #33 → #27 direction and #29 → #20 → #30 offline queue are complete or
  superseded.** #38 interruption architecture is now offline-complete. Current priority is only the
  Active view at the top: #37 chat, then #36 ordered goals; #16 authoring and #35 expeditions wait on
  their listed choices.
- **#4's harness is built** (`run_tests.py`, `preflight.py`, `autonomous_loop.md`);
  running the live sim autonomously is still gated by Unreal/PIE reliability and inference cost.
- **Verification uses `python scripts/run_tests.py`.** Never copy an old suite count forward;
  record the count produced by the commit being described.
