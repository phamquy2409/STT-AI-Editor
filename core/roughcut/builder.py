from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import select

from core.database import ShotSegment, VideoFile, create_session_factory
from core.project import ProjectManager, STTProject


@dataclass
class RoughCutConfig:
    target_duration_seconds: float = 60.0
    min_keep_score: float = 45.0
    min_segment_seconds: float = 1.2
    max_segments_per_video: int = 2
    sequence_fps: int = 25


@dataclass
class RoughCutItem:
    order: int
    video_filename: str
    video_path: str
    segment_index: int
    source_start_seconds: float
    source_end_seconds: float
    duration_seconds: float
    timeline_start_seconds: float
    timeline_end_seconds: float
    ai_keep_score: float
    beauty_score: float
    sharpness_score: float
    stability_score: float
    exposure_score: float
    motion_score: float


class RoughCutBuilder:
    def __init__(self, project: STTProject, config: RoughCutConfig | None = None) -> None:
        self.project = project
        self.config = config or RoughCutConfig()
        self.SessionLocal = create_session_factory(project.paths.database_file)

    def build(self) -> dict[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"roughcut_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        print("STT AI Rough Cut Builder")
        print(f"Project: {self.project.name}")
        print(f"Target duration: {self.config.target_duration_seconds}s")
        print(f"Min keep score: {self.config.min_keep_score}")
        print(f"Output: {output_dir}")
        print("-" * 60)

        items = self._select_items()

        csv_path = output_dir / "roughcut_plan.csv"
        json_path = output_dir / "roughcut_plan.json"
        summary_path = output_dir / "roughcut_summary.txt"
        xml_path = output_dir / "roughcut_premiere_experimental.xml"

        self._write_csv(csv_path, items)
        self._write_json(json_path, items)
        self._write_summary(summary_path, items)
        self._write_premiere_xml(xml_path, items)

        total_duration = sum(item.duration_seconds for item in items)

        print("ROUGH CUT COMPLETE")
        print(f"Segments selected: {len(items)}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"CSV: {csv_path}")
        print(f"JSON: {json_path}")
        print(f"XML experimental: {xml_path}")
        print("-" * 60)

        return {
            "output_dir": str(output_dir),
            "csv": str(csv_path),
            "json": str(json_path),
            "summary": str(summary_path),
            "premiere_xml_experimental": str(xml_path),
        }

    def _select_items(self) -> list[RoughCutItem]:
        with self.SessionLocal() as session:
            stmt = (
                select(ShotSegment, VideoFile)
                .join(VideoFile, ShotSegment.video_id == VideoFile.id)
                .where(ShotSegment.status == "vision_done")
                .where(ShotSegment.ai_keep_score >= self.config.min_keep_score)
                .where(ShotSegment.duration_seconds >= self.config.min_segment_seconds)
                .order_by(ShotSegment.ai_keep_score.desc())
            )
            rows = session.execute(stmt).all()

        selected: list[RoughCutItem] = []
        used_by_video: dict[str, int] = {}
        timeline_cursor = 0.0

        for segment, video in rows:
            count = used_by_video.get(video.filepath, 0)
            if count >= self.config.max_segments_per_video:
                continue

            duration = float(segment.duration_seconds or 0.0)
            if duration <= 0:
                continue

            item = RoughCutItem(
                order=len(selected) + 1,
                video_filename=video.filename,
                video_path=video.filepath,
                segment_index=int(segment.segment_index),
                source_start_seconds=round(float(segment.start_seconds), 3),
                source_end_seconds=round(float(segment.end_seconds), 3),
                duration_seconds=round(duration, 3),
                timeline_start_seconds=round(timeline_cursor, 3),
                timeline_end_seconds=round(timeline_cursor + duration, 3),
                ai_keep_score=round(float(segment.ai_keep_score or 0.0), 2),
                beauty_score=round(float(segment.beauty_score or 0.0), 2),
                sharpness_score=round(float(segment.blur_score or 0.0), 2),
                stability_score=round(float(segment.shake_score or 0.0), 2),
                exposure_score=round(float(segment.exposure_score or 0.0), 2),
                motion_score=round(float(segment.motion_score or 0.0), 2),
            )

            selected.append(item)
            used_by_video[video.filepath] = count + 1
            timeline_cursor += duration

            if timeline_cursor >= self.config.target_duration_seconds:
                break

        return selected

    @staticmethod
    def _write_csv(path: Path, items: list[RoughCutItem]) -> None:
        rows = [asdict(item) for item in items]
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_json(path: Path, items: list[RoughCutItem]) -> None:
        path.write_text(
            json.dumps([asdict(item) for item in items], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_summary(self, path: Path, items: list[RoughCutItem]) -> None:
        total = sum(i.duration_seconds for i in items)
        lines = [
            "STT AI Editor - Rough Cut Summary",
            "=" * 45,
            f"Project: {self.project.name}",
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Target duration: {self.config.target_duration_seconds:.2f}s",
            f"Actual duration: {total:.2f}s",
            f"Selected segments: {len(items)}",
            f"Min keep score: {self.config.min_keep_score}",
            f"Max segments per video: {self.config.max_segments_per_video}",
            "",
            "Top selected:",
        ]

        for item in items[:30]:
            lines.append(
                f"{item.order:03d}. {item.video_filename} "
                f"{item.source_start_seconds:.2f}-{item.source_end_seconds:.2f}s "
                f"keep={item.ai_keep_score:.2f}"
            )

        path.write_text("\\n".join(lines), encoding="utf-8")

    def _write_premiere_xml(self, path: Path, items: list[RoughCutItem]) -> None:
        fps = int(self.config.sequence_fps)

        def sec_to_frames(sec: float) -> int:
            return int(round(sec * fps))

        def pathurl(windows_path: str) -> str:
            p = Path(windows_path)
            text = p.as_posix()
            return "file://localhost/" + quote(text, safe="/:")

        total_frames = sec_to_frames(sum(i.duration_seconds for i in items))
        clip_xml = []

        for item in items:
            clip_id = f"clipitem-{item.order}"
            file_id = f"file-{item.order}"
            start_frame = sec_to_frames(item.timeline_start_seconds)
            end_frame = sec_to_frames(item.timeline_end_seconds)
            in_frame = sec_to_frames(item.source_start_seconds)
            out_frame = sec_to_frames(item.source_end_seconds)
            duration_frames = max(1, end_frame - start_frame)

            clip_xml.append(f'''          <clipitem id="{clip_id}">
            <name>{self._xml_escape(item.video_filename)}</name>
            <duration>{duration_frames}</duration>
            <rate>
              <timebase>{fps}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <start>{start_frame}</start>
            <end>{end_frame}</end>
            <in>{in_frame}</in>
            <out>{out_frame}</out>
            <enabled>TRUE</enabled>
            <file id="{file_id}">
              <name>{self._xml_escape(item.video_filename)}</name>
              <pathurl>{pathurl(item.video_path)}</pathurl>
              <rate>
                <timebase>{fps}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <duration>{out_frame + 1}</duration>
            </file>
          </clipitem>''')

        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<xmeml version="4">
  <sequence id="sequence-1">
    <name>STT AI Rough Cut</name>
    <duration>{total_frames}</duration>
    <rate>
      <timebase>{fps}</timebase>
      <ntsc>FALSE</ntsc>
    </rate>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <width>1920</width>
            <height>1080</height>
            <rate>
              <timebase>{fps}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
          </samplecharacteristics>
        </format>
        <track>
{chr(10).join(clip_xml)}
        </track>
      </video>
    </media>
  </sequence>
</xmeml>
'''
        path.write_text(xml, encoding="utf-8")

    @staticmethod
    def _xml_escape(text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )


def build_roughcut_existing_project(
    project_root: str | Path,
    target_duration_seconds: float = 60.0,
    min_keep_score: float = 45.0,
    max_segments_per_video: int = 2,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    builder = RoughCutBuilder(
        project,
        config=RoughCutConfig(
            target_duration_seconds=target_duration_seconds,
            min_keep_score=min_keep_score,
            max_segments_per_video=max_segments_per_video,
        ),
    )

    return builder.build()
