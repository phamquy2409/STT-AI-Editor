from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from core.database import ShotSegment, VideoFile, create_session_factory
from core.project import ProjectManager, STTProject

from .frame_metrics import analyze_segment_frames


@dataclass
class VisionAnalyzerConfig:
    limit: int | None = None
    only_pending: bool = True
    commit_every: int = 20


class VisionAnalyzer:
    """
    Build 004 Vision Analyzer.

    It reads shot_segments, samples frames, calculates basic technical scores,
    and saves the scores back to SQLite.
    """

    def __init__(
        self,
        project: STTProject,
        config: VisionAnalyzerConfig | None = None,
    ) -> None:
        self.project = project
        self.config = config or VisionAnalyzerConfig()
        self.SessionLocal = create_session_factory(project.paths.database_file)

    def analyze(self) -> dict[str, int]:
        analyzed = 0
        errors = 0

        print("STT AI Vision Analyzer")
        print(f"Project: {self.project.name}")
        print(f"Database: {self.project.paths.database_file}")
        print(f"Limit: {self.config.limit if self.config.limit else 'all'}")
        print("-" * 60)

        with self.SessionLocal() as session:
            stmt = (
                select(ShotSegment, VideoFile)
                .join(VideoFile, ShotSegment.video_id == VideoFile.id)
                .order_by(VideoFile.filepath.asc(), ShotSegment.segment_index.asc())
            )

            if self.config.only_pending:
                stmt = stmt.where(ShotSegment.status == "pending_vision")

            if self.config.limit:
                stmt = stmt.limit(self.config.limit)

            rows = session.execute(stmt).all()
            total = len(rows)

            for index, (segment, video) in enumerate(rows, start=1):
                try:
                    metrics = analyze_segment_frames(
                        video.filepath,
                        segment.start_seconds,
                        segment.end_seconds,
                    )

                    segment.blur_score = metrics.sharpness_score
                    segment.exposure_score = metrics.exposure_score
                    segment.motion_score = metrics.motion_score
                    segment.shake_score = metrics.stability_score
                    segment.beauty_score = metrics.beauty_score
                    segment.ai_keep_score = metrics.ai_keep_score
                    segment.status = "vision_done"
                    segment.note = (
                        f"brightness={metrics.brightness_mean}; "
                        f"{metrics.note}"
                    )

                    analyzed += 1

                    print(
                        f"[{index}/{total}] {video.filename} "
                        f"seg#{segment.segment_index} "
                        f"{segment.start_seconds:.1f}-{segment.end_seconds:.1f}s | "
                        f"sharp={segment.blur_score:.1f} "
                        f"exp={segment.exposure_score:.1f} "
                        f"stable={segment.shake_score:.1f} "
                        f"keep={segment.ai_keep_score:.1f}"
                    )

                except Exception as exc:
                    segment.status = "vision_error"
                    segment.note = str(exc)
                    errors += 1

                    print(
                        f"[{index}/{total}] ERROR {video.filename} "
                        f"seg#{segment.segment_index}: {exc}"
                    )

                if index % self.config.commit_every == 0 or index == total:
                    session.commit()

            session.commit()

        print("-" * 60)
        print("VISION ANALYSIS COMPLETE")
        print(f"Analyzed: {analyzed}")
        print(f"Errors: {errors}")

        return {
            "analyzed": analyzed,
            "errors": errors,
        }


def analyze_vision_existing_project(
    project_root: str | Path,
    limit: int | None = None,
    only_pending: bool = True,
) -> dict[str, int]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    analyzer = VisionAnalyzer(
        project,
        config=VisionAnalyzerConfig(
            limit=limit,
            only_pending=only_pending,
        ),
    )

    return analyzer.analyze()
