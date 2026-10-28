"""Import the three independently editable game-screen image layers into UE."""

from pathlib import Path
import unreal


root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content" / "UI" / "Source"
names = (
    "Ione_ArchiveRoom_Background_v2.png",
    "Ione_ContactShadow.png",
    "Ione_DialogueFrame.png",
)
tasks = []
for name in names:
    path = source / name
    if not path.is_file():
        raise FileNotFoundError(path)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", "/Game/UI")
    task.set_editor_property("destination_name", path.stem)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    tasks.append(task)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for task in tasks:
    imported = task.get_editor_property("imported_object_paths")
    if not imported:
        raise RuntimeError(f"Import failed: {task.get_editor_property('filename')}")
    unreal.log(f"Ione scene UI import: {imported}")
