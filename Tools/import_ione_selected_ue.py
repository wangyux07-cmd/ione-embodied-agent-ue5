"""Import the two user-selected final preview assets without altering originals."""
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir()).resolve()
for relative,destination in [
    ('Content/Character/Performance2D/Selected/Ione_Listen_Selected.png','/Game/Character/Performance2D/Selected'),
    ('Content/UI/Source/Ione_ArchiveRoom_Background_Selected.png','/Game/UI')]:
    source=root/relative
    task=unreal.AssetImportTask()
    for key,value in [('filename',str(source)),('destination_path',destination),
                      ('destination_name',source.stem),('automated',True),('replace_existing',True),('save',True)]:
        task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.get_editor_property('imported_object_paths'):
        raise RuntimeError(f'Import failed: {source}')
