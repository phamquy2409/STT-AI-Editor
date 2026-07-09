from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .paths import ProjectPaths
from .settings import ProjectSettings


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass
class STTProject:
    name: str
    root: Path
    source_folder: Path | None = None
    project_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    settings: ProjectSettings = field(default_factory=ProjectSettings)

    @property
    def paths(self) -> ProjectPaths:
        return ProjectPaths(self.root)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "root": str(self.root),
            "source_folder": str(self.source_folder) if self.source_folder else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "STTProject":
        source = data.get("source_folder")
        return cls(
            project_id=data["project_id"],
            name=data["name"],
            root=Path(data["root"]),
            source_folder=Path(source) if source else None,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            settings=ProjectSettings.from_dict(data.get("settings", {})),
        )
