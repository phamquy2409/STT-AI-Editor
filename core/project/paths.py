from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """All paths used by one STT AI Editor project."""

    root: Path

    @property
    def config_file(self) -> Path:
        return self.root / "project.json"

    @property
    def database_dir(self) -> Path:
        return self.root / "database"

    @property
    def database_file(self) -> Path:
        return self.database_dir / "stt_ai.db"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    @property
    def thumbnails_dir(self) -> Path:
        return self.cache_dir / "thumbnails"

    @property
    def previews_dir(self) -> Path:
        return self.cache_dir / "previews"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    @property
    def premiere_exports_dir(self) -> Path:
        return self.exports_dir / "premiere"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    def create_all(self) -> None:
        """Create all required project folders."""
        folders = [
            self.database_dir,
            self.cache_dir,
            self.thumbnails_dir,
            self.previews_dir,
            self.exports_dir,
            self.premiere_exports_dir,
            self.reports_dir,
            self.logs_dir,
        ]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
