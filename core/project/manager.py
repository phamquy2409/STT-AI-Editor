from __future__ import annotations

import json
import re
from pathlib import Path

from .exceptions import InvalidProjectError, ProjectAlreadyExistsError, ProjectConfigError
from .project import STTProject
from .settings import ProjectSettings


def slugify_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\s\-\.]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name)
    return name or "Untitled_Project"


class ProjectManager:
    def __init__(self) -> None:
        self.app_data_dir = Path.home() / ".stt_ai_editor"
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.recent_projects_file = self.app_data_dir / "recent_projects.json"

    def create_project(
        self,
        projects_root: str | Path,
        name: str,
        source_folder: str | Path | None = None,
        overwrite: bool = False,
    ) -> STTProject:
        projects_root = Path(projects_root)
        projects_root.mkdir(parents=True, exist_ok=True)

        project_root = projects_root / slugify_name(name)

        if project_root.exists() and not overwrite:
            raise ProjectAlreadyExistsError(f"Project folder already exists: {project_root}")

        project = STTProject(
            name=name.strip() or "Untitled Project",
            root=project_root,
            source_folder=Path(source_folder) if source_folder else None,
            settings=ProjectSettings(),
        )

        project.paths.create_all()
        self.save_project(project)
        self.add_recent_project(project.root)
        return project

    def open_project(self, project_root: str | Path) -> STTProject:
        project_root = Path(project_root)
        config_file = project_root / "project.json"

        if not config_file.exists():
            raise InvalidProjectError(f"Missing project config: {config_file}")

        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ProjectConfigError(f"Cannot read project config: {exc}") from exc

        project = STTProject.from_dict(data)
        self.add_recent_project(project.root)
        return project

    def save_project(self, project: STTProject) -> None:
        project.touch()
        project.paths.create_all()

        try:
            project.paths.config_file.write_text(
                json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            raise ProjectConfigError(f"Cannot save project config: {exc}") from exc

    def validate_project(self, project_root: str | Path) -> bool:
        return (Path(project_root) / "project.json").exists()

    def add_recent_project(self, project_root: str | Path) -> None:
        project_root = str(Path(project_root).resolve())
        recent = self.list_recent_projects()
        recent = [p for p in recent if p != project_root]
        recent.insert(0, project_root)
        recent = recent[:20]
        self.recent_projects_file.write_text(
            json.dumps(recent, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_recent_projects(self) -> list[str]:
        if not self.recent_projects_file.exists():
            return []
        try:
            data = json.loads(self.recent_projects_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception:
            pass
        return []
