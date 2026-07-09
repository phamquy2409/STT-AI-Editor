from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, func, select

from core.database import ShotSegment, VideoFile, create_session_factory
from core.project import ProjectManager, STTProject


@dataclass
class DetectorConfig:
    segment_seconds: float = 3.0
    min_segment_seconds: float = 1.2
    reset_existing: bool = True


class ShotDetector:
    """
    Build 003 detector.

    This first version creates fixed-length timeline segments from scanned video files.
    It does not decide good/bad yet. It prepares the database for Vision AI.
    """

    def __init__(self, project: STTProject, config: DetectorConfig | None = None) -> None:
        self.project = project
        self.config = config or DetectorConfig()
        self.SessionLocal = create_session_factory(project.paths.database_file)

    def detect(self) -> dict[str, int]:
        total_videos = 0
        total_segments = 0
        skipped = 0

        print("STT AI Shot Detector")
        print(f"Project: {self.project.name}")
        print(f"Database: {self.project.paths.database_file}")
        print(f"Segment length: {self.config.segment_seconds}s")
        print("-" * 60)

        with self.SessionLocal() as session:
            videos = session.execute(
                select(VideoFile).order_by(VideoFile.filepath.asc())
            ).scalars().all()

            total_videos = len(videos)

            if self.config.reset_existing:
                session.execute(delete(ShotSegment))
                session.commit()

            for video_index, video in enumerate(videos, start=1):
                segments = self._create_segments_for_video(video)

                if not segments:
                    skipped += 1
                    print(
                        f"[{video_index}/{total_videos}] SKIP {video.filename} | "
                        f"duration={video.duration_seconds:.2f}s"
                    )
                    continue

                for seg in segments:
                    session.add(seg)

                total_segments += len(segments)

                if video_index % 20 == 0 or video_index == total_videos:
                    session.commit()

                print(
                    f"[{video_index}/{total_videos}] {video.filename} | "
                    f"{video.duration_seconds:.2f}s -> {len(segments)} segments"
                )

            session.commit()

            db_count = session.execute(select(func.count(ShotSegment.id))).scalar_one()

        print("-" * 60)
        print("SHOT DETECTION COMPLETE")
        print(f"Videos: {total_videos}")
        print(f"Segments created: {total_segments}")
        print(f"Skipped: {skipped}")
        print(f"DB shot_segments count: {db_count}")

        return {
            "videos": total_videos,
            "segments_created": total_segments,
            "skipped": skipped,
            "db_segments": int(db_count),
        }

    def _create_segments_for_video(self, video: VideoFile) -> list[ShotSegment]:
        duration = float(video.duration_seconds or 0.0)

        if duration < self.config.min_segment_seconds:
            return []

        segments: list[ShotSegment] = []
        start = 0.0
        index = 0

        while start < duration:
            end = min(start + self.config.segment_seconds, duration)
            seg_duration = end - start

            if seg_duration < self.config.min_segment_seconds:
                break

            segments.append(
                ShotSegment(
                    video_id=video.id,
                    segment_index=index,
                    start_seconds=round(start, 3),
                    end_seconds=round(end, 3),
                    duration_seconds=round(seg_duration, 3),
                    detector_name="fixed_segment_v001",
                    detector_version="0.3.0",
                    status="pending_vision",
                    note="Fixed segment prepared for Vision AI analysis.",
                )
            )

            index += 1
            start = end

        return segments


def detect_shots_existing_project(
    project_root: str | Path,
    segment_seconds: float = 3.0,
    reset_existing: bool = True,
) -> dict[str, int]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    detector = ShotDetector(
        project,
        config=DetectorConfig(
            segment_seconds=segment_seconds,
            reset_existing=reset_existing,
        ),
    )

    return detector.detect()
