from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import func, select

from core.database import ShotSegment, VideoFile, create_session_factory
from core.project import ProjectManager, STTProject


@dataclass
class ReportConfig:
    limit: int = 200
    min_keep_score: float = 45.0
    min_duration_seconds: float = 1.2


class ReportGenerator:
    """
    Build 005 Report / Ranking.

    Reads analyzed shot segments and exports CSV reports so we can check
    whether Vision scoring is usable before building auto-edit timelines.
    """

    def __init__(self, project: STTProject, config: ReportConfig | None = None) -> None:
        self.project = project
        self.config = config or ReportConfig()
        self.SessionLocal = create_session_factory(project.paths.database_file)

    def generate_all(self) -> dict[str, str]:
        self.project.paths.reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_dir = self.project.paths.reports_dir / f'report_{timestamp}'
        report_dir.mkdir(parents=True, exist_ok=True)

        print('STT AI Report / Ranking')
        print(f'Project: {self.project.name}')
        print(f'Database: {self.project.paths.database_file}')
        print(f'Report dir: {report_dir}')
        print('-' * 60)

        with self.SessionLocal() as session:
            summary = self._summary(session)

            top_keep = self._query_segments(
                session=session,
                order_by=ShotSegment.ai_keep_score.desc(),
                limit=self.config.limit,
                where_done=True,
            )

            low_quality = self._query_segments(
                session=session,
                order_by=ShotSegment.ai_keep_score.asc(),
                limit=self.config.limit,
                where_done=True,
            )

            blurry = self._query_segments(
                session=session,
                order_by=ShotSegment.blur_score.asc(),
                limit=self.config.limit,
                where_done=True,
            )

            shaky = self._query_segments(
                session=session,
                order_by=ShotSegment.shake_score.asc(),
                limit=self.config.limit,
                where_done=True,
            )

            exposure_bad = self._query_segments(
                session=session,
                order_by=ShotSegment.exposure_score.asc(),
                limit=self.config.limit,
                where_done=True,
            )

            roughcut_candidates = [
                row for row in top_keep
                if row['ai_keep_score'] >= self.config.min_keep_score
                and row['duration_seconds'] >= self.config.min_duration_seconds
            ]

        paths: dict[str, str] = {}

        paths['summary_json'] = str(report_dir / 'summary.json')
        (report_dir / 'summary.json').write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

        paths['summary_txt'] = str(report_dir / 'summary.txt')
        (report_dir / 'summary.txt').write_text(
            self._summary_text(summary),
            encoding='utf-8',
        )

        paths['top_keep'] = str(report_dir / 'top_keep_segments.csv')
        self._write_csv(report_dir / 'top_keep_segments.csv', top_keep)

        paths['roughcut_candidates'] = str(report_dir / 'roughcut_candidates.csv')
        self._write_csv(report_dir / 'roughcut_candidates.csv', roughcut_candidates)

        paths['low_quality'] = str(report_dir / 'low_quality_segments.csv')
        self._write_csv(report_dir / 'low_quality_segments.csv', low_quality)

        paths['blurry'] = str(report_dir / 'blurry_segments.csv')
        self._write_csv(report_dir / 'blurry_segments.csv', blurry)

        paths['shaky'] = str(report_dir / 'shaky_segments.csv')
        self._write_csv(report_dir / 'shaky_segments.csv', shaky)

        paths['exposure_bad'] = str(report_dir / 'exposure_problem_segments.csv')
        self._write_csv(report_dir / 'exposure_problem_segments.csv', exposure_bad)

        print('REPORT COMPLETE')
        print(f"Videos: {summary['videos_total']}")
        print(f"Segments: {summary['segments_total']}")
        print(f"Vision done: {summary['vision_done']}")
        print(f"Top keep CSV: {paths['top_keep']}")
        print(f"Roughcut CSV: {paths['roughcut_candidates']}")
        print('-' * 60)

        return paths

    def _summary(self, session) -> dict:
        videos_total = session.execute(select(func.count(VideoFile.id))).scalar_one()
        segments_total = session.execute(select(func.count(ShotSegment.id))).scalar_one()

        def status_count(status: str) -> int:
            return session.execute(
                select(func.count(ShotSegment.id)).where(ShotSegment.status == status)
            ).scalar_one()

        avg_keep = session.execute(
            select(func.avg(ShotSegment.ai_keep_score)).where(ShotSegment.status == 'vision_done')
        ).scalar_one()

        avg_sharp = session.execute(
            select(func.avg(ShotSegment.blur_score)).where(ShotSegment.status == 'vision_done')
        ).scalar_one()

        avg_stable = session.execute(
            select(func.avg(ShotSegment.shake_score)).where(ShotSegment.status == 'vision_done')
        ).scalar_one()

        avg_exposure = session.execute(
            select(func.avg(ShotSegment.exposure_score)).where(ShotSegment.status == 'vision_done')
        ).scalar_one()

        return {
            'project_name': self.project.name,
            'project_root': str(self.project.root),
            'database': str(self.project.paths.database_file),
            'created_at': datetime.now().isoformat(timespec='seconds'),
            'videos_total': int(videos_total or 0),
            'segments_total': int(segments_total or 0),
            'vision_done': int(status_count('vision_done')),
            'vision_pending': int(status_count('pending_vision')),
            'vision_error': int(status_count('vision_error')),
            'avg_keep_score': round(float(avg_keep or 0.0), 2),
            'avg_sharpness_score': round(float(avg_sharp or 0.0), 2),
            'avg_stability_score': round(float(avg_stable or 0.0), 2),
            'avg_exposure_score': round(float(avg_exposure or 0.0), 2),
            'report_limit': self.config.limit,
            'roughcut_min_keep_score': self.config.min_keep_score,
        }

    def _query_segments(self, session, order_by, limit: int, where_done: bool = True) -> list[dict]:
        stmt = (
            select(ShotSegment, VideoFile)
            .join(VideoFile, ShotSegment.video_id == VideoFile.id)
            .order_by(order_by)
            .limit(limit)
        )

        if where_done:
            stmt = stmt.where(ShotSegment.status == 'vision_done')

        rows = session.execute(stmt).all()

        output: list[dict] = []

        for segment, video in rows:
            output.append(
                {
                    'video_filename': video.filename,
                    'video_path': video.filepath,
                    'segment_index': segment.segment_index,
                    'start_seconds': round(float(segment.start_seconds), 3),
                    'end_seconds': round(float(segment.end_seconds), 3),
                    'duration_seconds': round(float(segment.duration_seconds), 3),
                    'ai_keep_score': round(float(segment.ai_keep_score or 0.0), 2),
                    'beauty_score': round(float(segment.beauty_score or 0.0), 2),
                    'sharpness_score': round(float(segment.blur_score or 0.0), 2),
                    'stability_score': round(float(segment.shake_score or 0.0), 2),
                    'exposure_score': round(float(segment.exposure_score or 0.0), 2),
                    'motion_score': round(float(segment.motion_score or 0.0), 2),
                    'status': segment.status,
                    'note': segment.note or '',
                }
            )

        return output

    @staticmethod
    def _write_csv(path: Path, rows: Iterable[dict]) -> None:
        rows = list(rows)

        if not rows:
            path.write_text('', encoding='utf-8-sig')
            return

        with path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _summary_text(summary: dict) -> str:
        lines = [
            'STT AI Editor - Report Summary',
            '=' * 40,
            f"Project: {summary['project_name']}",
            f"Project root: {summary['project_root']}",
            f"Database: {summary['database']}",
            f"Created at: {summary['created_at']}",
            '',
            f"Videos total: {summary['videos_total']}",
            f"Segments total: {summary['segments_total']}",
            f"Vision done: {summary['vision_done']}",
            f"Vision pending: {summary['vision_pending']}",
            f"Vision error: {summary['vision_error']}",
            '',
            f"Average keep score: {summary['avg_keep_score']}",
            f"Average sharpness score: {summary['avg_sharpness_score']}",
            f"Average stability score: {summary['avg_stability_score']}",
            f"Average exposure score: {summary['avg_exposure_score']}",
            '',
            f"Report limit: {summary['report_limit']}",
            f"Roughcut min keep score: {summary['roughcut_min_keep_score']}",
            '',
        ]

        return '\n'.join(lines)


def generate_report_existing_project(
    project_root: str | Path,
    limit: int = 200,
    min_keep_score: float = 45.0,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    generator = ReportGenerator(
        project,
        config=ReportConfig(
            limit=limit,
            min_keep_score=min_keep_score,
        ),
    )

    return generator.generate_all()
