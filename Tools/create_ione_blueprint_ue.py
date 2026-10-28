"""Create BP_IoneNPC and assign the imported portrait textures in Unreal Editor."""

import unreal


asset_path = "/Game/Character/BP_IoneNPC"
asset = (
    unreal.EditorAssetLibrary.load_asset(asset_path)
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path)
    else None
)
if asset is None:
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.AsterNPCActor)
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "BP_IoneNPC", "/Game/Character", unreal.Blueprint, factory
    )
if asset is None:
    raise RuntimeError(f"Could not create {asset_path}")

defaults = unreal.get_default_object(asset.generated_class())
defaults.set_editor_property("enable_portrait_debug_keys", True)
textures = {
    "listening_portrait": "Ione_Listen_Front",
    "speaking_portrait": "Ione_Speak_Front",
    "interrupted_portrait": "Ione_Interrupted_Front",
    "warning_portrait": "Ione_Warn_Front",
}
for property_name, texture_name in textures.items():
    texture = unreal.EditorAssetLibrary.load_asset(
        f"/Game/Character/Performance2D/{texture_name}"
    )
    if texture is None:
        raise RuntimeError(f"Missing texture {texture_name}")
    defaults.set_editor_property(property_name, texture)

if not unreal.EditorAssetLibrary.save_loaded_asset(asset):
    raise RuntimeError(f"Could not save {asset_path}")
unreal.log(f"Ione Blueprint ready: {asset_path}")
