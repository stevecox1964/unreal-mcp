- Look before you step. A direction line may say what "your own eyes saw" that
  way - grass, a field, water, a building interior, a DEAD END. Your eyes
  outrank the ground being physically walkable: you will happily be walked into
  a backyard or a bedroom, and the picture told you first. Never walk a
  direction whose line shows grass, cultivated_field, water or building_interior
  ahead, or NO-GO ground - go around, or refuse it.
- If FOOTING is anything other than pavement, road, or dirt_path (e.g. grass,
  cultivated_field, water), you are somewhere you should not be. Head for proper
  ground before continuing any other goal.
- Behind buildings and indoors is never ground to cross. If your view is a
  building interior, or a pocket walled in on most sides, the way you came is
  the way out - take it, then refuse the spot so you are not lured back.
- Standing crops, water, private yards and fenced ground are not walkable
  ground, and "nobody has walked it" is not a reason to walk into one - it is
  just ground nobody has ruled on yet. When you can SEE that ground is like
  that, rule it out with
  {"type": "refuse_cell", "direction": "<compass word>", "reason": "<what you
  see>"} and move on. It stops being offered to you and to everyone else, so you
  never have to decide about it twice. Judge it from outside; you do not need to
  walk in to know what corn is.
- Not every bad spot is a bad cell. When one yard, alley or doorway is the
  problem but the rest of the cell is fine, refuse just that patch of ground:
  {"type": "refuse_cell", "direction": "<compass word>", "scope": "spot",
  "reason": "<what it is>"}. The whole-cell refusal is for ground that is bad
  wall to wall - corn, water, a fenced field.
- A refusal is not a failure and not a gap you should feel bad about - the
  reason you gave is itself worth recording. But do not refuse ground merely
  because it is awkward, far, or rough underfoot: refuse what should not be
  walked, not what is inconvenient. If you were wrong, take it back with
  {"type": "allow_cell", "direction": "<compass word>"}.
- Refuse a piece of ground ONCE. If a direction line already says NO-GO, or a
  sense says you are STANDING in refused ground, the record exists - refusing
  again does nothing but burn the tick. The move after a refusal is always the
  same: leave, by a proven direction or RETRACE, this tick, not later.
- If a sense says you have walked into a cell and straight back out N times,
  that pocket will not be different on try N+1. Refuse the bad ground and
  approach from another side.
