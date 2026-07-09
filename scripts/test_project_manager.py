from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.project import ProjectManager


def main() -> None:
    manager = ProjectManager()

    project = manager.create_project(
        projects_root=Path("D:/STT Projects"),
        name="Wedding Test 001",
        source_folder=Path("D:/5thang5 test/CLIP"),
        overwrite=True,
    )

    print("PROJECT CREATED")
    print("Name:", project.name)
    print("Root:", project.root)
    print("Config:", project.paths.config_file)
    print("Database:", project.paths.database_file)
    print("Exports:", project.paths.exports_dir)

    opened = manager.open_project(project.root)

    print()
    print("PROJECT OPENED")
    print("ID:", opened.project_id)
    print("Recent:", manager.list_recent_projects()[:3])


if __name__ == "__main__":
    main()
