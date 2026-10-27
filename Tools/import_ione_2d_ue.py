"""Run in Unreal Editor's Python console to import Ione's four transparent poses.

Example (with this repository open as the UE project):
    exec(open(r'C:/path/to/repo/Tools/import_ione_2d_ue.py', encoding='utf-8').read())
"""

from pathlib import Path
import unreal


repo = Path(unreal.Paths.project_dir()).resolve()
source = repo / "Content" / "Character" / "Performance2D"
destination = "/Game/Character/Performance2D"
names = (
    "Ione_Listen_Front.png",
    "Ione_Speak_Front.png",
    "Ione_Interrupted_Front.png",
    "Ione_Warn_Front.png",
)

tasks = []
for name in names:
    path = source / name
    if not path.is_file():
        raise FileNotFoundError(path)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("destination_name", path.stem)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    tasks.append(task)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for task in tasks:
    unreal.log(f"Ione import: {task.get_editor_property('imported_object_paths')}")
