from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ScanSettings:
    recursive: bool = True
    min_file_size_mb: int = 3
    video_extensions: list[str] = field(
        default_factory=lambda: [
            ".mp4",
            ".mov",
            ".mxf",
            ".mts",
            ".m2ts",
            ".avi",
            ".mkv",
        ]
    )


@dataclass
class VisionSettings:
    enabled: bool = True
    sample_every_seconds: float = 1.0
    default_segment_seconds: float = 3.0
    max_video_analyze_count: int = 500


@dataclass
class ExportSettings:
    fps: int = 25
    width: int = 1920
    height: int = 1080
    audio_sample_rate: int = 48000


@dataclass
class ProjectSettings:
    app_version: str = "0.1.0"
    scan: ScanSettings = field(default_factory=ScanSettings)
    vision: VisionSettings = field(default_factory=VisionSettings)
    export: ExportSettings = field(default_factory=ExportSettings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectSettings":
        return cls(
            app_version=data.get("app_version", "0.1.0"),
            scan=ScanSettings(**data.get("scan", {})),
            vision=VisionSettings(**data.get("vision", {})),
            export=ExportSettings(**data.get("export", {})),
        )
