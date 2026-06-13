import unreal

# Half-extents of the carve box (cm). Vehicles ~5 m long → ~260 x 120 x 120.
EXTENT = unreal.Vector(260.0, 120.0, 120.0)
PREFIX = "veh_van_2"          # narrow to one actor (e.g. "veh_van_2") to test first

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
vehicles = [a for a in eas.get_all_level_actors()
            if a.get_actor_label().lower().startswith(PREFIX.lower())
            and isinstance(a, unreal.SkeletalMeshActor)]

done = 0
for a in vehicles:
    # Strip nav relevance from the skeletal mesh so the modifier uses its
    # FailsafeExtent (a clean box) instead of ambiguous skeletal geometry.
    skm = a.skeletal_mesh_component
    if skm:
        try:
            skm.set_editor_property("can_ever_affect_navigation", False)
        except Exception as e:
            unreal.log_warning(f"nav-relevance not disabled on {a.get_actor_label()}: {e}")

    comp = a.add_component_by_class(unreal.NavModifierComponent, False,
                                    unreal.Transform(), False)
    if not comp:
        unreal.log_warning(f"skip {a.get_actor_label()} (no component)")
        continue
    comp.set_editor_property("area_class", unreal.NavArea_Null)   # remove cells
    comp.set_editor_property("failsafe_extent", EXTENT)
    done += 1

unreal.log(f"NavModifier(Null) added to {done} / {len(vehicles)} vehicles")