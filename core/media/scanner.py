from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from sqlalchemy import select

from core.database import VideoFile, create_session_factory
from core.project import ProjectManager, STTProject

from .video_metadata import VideoMetadata, read_video_metadata


DEFAULT_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mxf",
    ".mts",
    ".m2ts",
    ".avi",
    ".mkv",
    ".wmv",
}


def find_video_files(
    source_folder: str | Path,
    extensions: Iterable[str] | None = None,
    recursive: bool = True,
) -> list[Path]:
    source = Path(source_folder)

    if not source.exists():
        raise FileNotFoundError(f"Source folder not found: {source}")

    exts = {e.lower() for e in (extensions or DEFAULT_VIDEO_EXTENSIONS)}

    iterator = source.rglob("*") if recursive else source.glob("*")
    videos = [
        p for p in iterator
        if p.is_file() and p.suffix.lower() in exts
    ]

    return sorted(videos, key=lambda p: str(p).lower())


class MediaScanner:
    def __init__(self, project: STTProject) -> None:
        self.project = project
        self.SessionLocal = create_session_factory(project.paths.database_file)

    def scan(self, source_folder: str | Path | None = None) -> dict[str, int]:
        source = Path(source_folder) if source_folder else self.project.source_folder

        if source is None:
            raise ValueError("Project has no source_folder. Please provide source_folder.")

        video_files = find_video_files(
            source_folder=source,
            extensions=self.project.settings.scan.video_extensions,
            recursive=self.project.settings.scan.recursive,
        )

        total = len(video_files)
        inserted = 0
        updated = 0
        errors = 0

        print(f"STT AI Media Scanner")
        print(f"Project: {self.project.name}")
        print(f"Source: {source}")
        print(f"Found: {total} video files")
        print("-" * 60)

        with self.SessionLocal() as session:
            for index, video_path in enumerate(video_files, start=1):
                metadata = read_video_metadata(video_path)

                if metadata.scan_status == "error":
                    errors += 1

                existing = session.execute(
                    select(VideoFile).where(VideoFile.filepath == metadata.filepath)
                ).scalar_one_or_none()

                if existing is None:
                    row = VideoFile(**asdict(metadata))
                    session.add(row)
                    inserted += 1
                else:
                    self._update_existing(existing, metadata)
                    updated += 1

                if index % 10 == 0 or index == total:
                    session.commit()

                duration = self._format_duration(metadata.duration_seconds)
                print(
                    f"[{index}/{total}] {metadata.filename} | "
                    f"{metadata.width}x{metadata.height} | "
                    f"{metadata.fps}fps | {duration} | {metadata.scan_status}"
                )

            session.commit()

        print("-" * 60)
        print("SCAN COMPLETE")
        print(f"Inserted: {inserted}")
        print(f"Updated: {updated}")
        print(f"Errors: {errors}")
        print(f"Database: {self.project.paths.database_file}")

        return {
            "total": total,
            "inserted": inserted,
            "updated": updated,
            "errors": errors,
        }

    @staticmethod
    def _update_existing(row: VideoFile, metadata: VideoMetadata) -> None:
        data = asdict(metadata)
        for key, value in data.items():
            setattr(row, key, value)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        seconds = int(seconds or 0)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


def scan_existing_project(project_root: str | Path, source_folder: str | Path | None = None):
    manager = ProjectManager()
    project = manager.open_project(project_root)
    scanner = MediaScanner(project)
    return scanner.scan(source_folder=source_folder)
