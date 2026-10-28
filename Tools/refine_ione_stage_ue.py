"""Remove the obsolete checkerboard pedestal from the Ione game map."""

import unreal


unreal.EditorLevelLibrary.load_level("/Game/Maps/L_IoneStage")
removed = 0
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if actor.get_actor_label() == "Ione - small stage disc":
        if not unreal.EditorLevelLibrary.destroy_actor(actor):
            raise RuntimeError("Could not remove test pedestal")
        removed += 1
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("Could not save Ione stage")
unreal.log(f"Ione stage refined: removed {removed} pedestal actor(s)")
