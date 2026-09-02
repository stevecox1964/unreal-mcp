# Surveyor (template APC, inactive)

The survey persona that Dufus carried through SR1-SR58. Kept here so a NEW world
gets a surveyor by activating one folder, not by rewriting an APC.

To use in a new world:

1. Place an `APC_Dufus_BP` body in the level and name the actor `APC_Surveyor_BP`
   (or change `unreal_actor_name` below to whatever actor you placed).
2. Set `start_location` to where it should wake.
3. Set `is_active` to `true` in `state.json`.
4. Run the sim in **Survey** mode.

`mission: "survey"` + `survey_priority: true` are what make the runtime treat an
APC as the surveyor; the four persona files just give it a voice.
