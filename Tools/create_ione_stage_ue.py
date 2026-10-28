"""Create a minimal UE test level for Ione's camera-facing portrait actor."""

import unreal


level_path = "/Game/Maps/L_IoneStage"
if unreal.EditorAssetLibrary.does_asset_exist(level_path):
    raise RuntimeError(f"Refusing to overwrite existing level: {level_path}")
if not unreal.EditorLevelLibrary.new_level_from_template(
    level_path, "/Engine/Maps/Templates/Template_Default"
):
    raise RuntimeError(f"Could not create level: {level_path}")

blueprint = unreal.EditorAssetLibrary.load_asset("/Game/Character/BP_IoneNPC")
if blueprint is None:
    raise RuntimeError("BP_IoneNPC is missing")
ione = unreal.EditorLevelLibrary.spawn_actor_from_class(
    blueprint.generated_class(), unreal.Vector(0, 100, 0), unreal.Rotator()
)
if ione is None:
    raise RuntimeError("Could not spawn BP_IoneNPC")
ione.set_actor_label("Ione - portrait performance")

starts = [
    actor
    for actor in unreal.EditorLevelLibrary.get_all_level_actors()
    if isinstance(actor, unreal.PlayerStart)
]
player = starts[0] if starts else unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.PlayerStart, unreal.Vector(), unreal.Rotator()
)
if player is None:
    raise RuntimeError("Could not spawn PlayerStart")
player.set_actor_location(unreal.Vector(330, 0, 120), False, False)
player.set_actor_rotation(unreal.Rotator(0, 0, 180), False)

disc = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.StaticMeshActor, unreal.Vector(0, 100, -12), unreal.Rotator()
)
mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder")
if disc is None or mesh is None:
    raise RuntimeError("Could not create stage disc")
disc.static_mesh_component.set_static_mesh(mesh)
disc.set_actor_scale3d(unreal.Vector(1.6, 1.6, 0.25))
disc.set_actor_label("Ione - small stage disc")

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError(f"Could not save level: {level_path}")
unreal.log(f"Ione stage ready: {level_path}")
