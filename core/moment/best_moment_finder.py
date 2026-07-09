from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from core.project import ProjectManager, STTProject


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


@dataclass
class MomentFinderConfig:
    sample_step_seconds: float = 0.25
    refined_segment_seconds: float = 2.2
    thumbnail_width: int = 960


@dataclass
class FrameCandidate:
    second: float
    total_score: float
    sharpness_score: float
    exposure_score: float
    contrast_score: float
    saturation_score: float
    detail_score: float
    brightness_mean: float


class BestMomentFinder:
    def __init__(
        self,
        project: STTProject,
        roughcut_json: str | Path | None = None,
        config: MomentFinderConfig | None = None,
    ) -> None:
        self.project = project
        self.roughcut_json = Path(roughcut_json) if roughcut_json else self._find_latest_roughcut_json()
        self.config = config or MomentFinderConfig()

    def run(self) -> dict[str, str]:
        if not self.roughcut_json.exists():
            raise FileNotFoundError(f"roughcut_plan.json not found: {self.roughcut_json}")

        items = json.loads(self.roughcut_json.read_text(encoding="utf-8"))
        output_dir = self.roughcut_json.parent

        refined_json = output_dir / "roughcut_plan_best_moments.json"
        refined_csv = output_dir / "roughcut_plan_best_moments.csv"
        summary_txt = output_dir / "best_moment_summary.txt"

        print("STT AI Best Moment Finder")
        print(f"Project: {self.project.name}")
        print(f"Roughcut: {self.roughcut_json}")
        print(f"Segments: {len(items)}")
        print("-" * 60)

        refined_items: list[dict] = []
        timeline_cursor = 0.0

        for idx, item in enumerate(items, start=1):
            try:
                candidate = self._find_best_frame_for_item(item)
                new_start, new_end = self._refine_range(item, candidate.second)
                new_duration = max(0.0, new_end - new_start)

                row = dict(item)
                row["original_source_start_seconds"] = float(item.get("source_start_seconds", 0.0))
                row["original_source_end_seconds"] = float(item.get("source_end_seconds", 0.0))
                row["source_start_seconds"] = round(new_start, 3)
                row["source_end_seconds"] = round(new_end, 3)
                row["duration_seconds"] = round(new_duration, 3)
                row["timeline_start_seconds"] = round(timeline_cursor, 3)
                row["timeline_end_seconds"] = round(timeline_cursor + new_duration, 3)
                row["best_frame_seconds"] = round(candidate.second, 3)
                row["best_moment_score"] = round(candidate.total_score, 2)
                row["best_sharpness_score"] = round(candidate.sharpness_score, 2)
                row["best_exposure_score"] = round(candidate.exposure_score, 2)
                row["best_contrast_score"] = round(candidate.contrast_score, 2)
                row["best_saturation_score"] = round(candidate.saturation_score, 2)
                row["best_detail_score"] = round(candidate.detail_score, 2)
                row["best_brightness_mean"] = round(candidate.brightness_mean, 2)
                row["moment_status"] = "ok"

                timeline_cursor += new_duration

                print(
                    f"[{idx}/{len(items)}] {item.get('video_filename')} | "
                    f"best={candidate.second:.2f}s score={candidate.total_score:.1f} | "
                    f"range {new_start:.2f}-{new_end:.2f}s"
                )

            except Exception as exc:
                row = dict(item)
                row["best_frame_seconds"] = (
                    float(item.get("source_start_seconds", 0.0))
                    + float(item.get("source_end_seconds", 0.0))
                ) / 2.0
                row["best_moment_score"] = 0.0
                row["moment_status"] = f"error: {exc}"

                duration = float(row.get("duration_seconds", 0.0))
                row["timeline_start_seconds"] = round(timeline_cursor, 3)
                row["timeline_end_seconds"] = round(timeline_cursor + duration, 3)
                timeline_cursor += duration

                print(f"[{idx}/{len(items)}] ERROR {item.get('video_filename')}: {exc}")

            refined_items.append(row)

        refined_json.write_text(
            json.dumps(refined_items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._write_csv(refined_csv, refined_items)
        self._write_summary(summary_txt, refined_items)

        print("-" * 60)
        print("BEST MOMENT FINDER COMPLETE")
        print(f"Refined JSON: {refined_json}")
        print(f"Refined CSV: {refined_csv}")
        print(f"Summary: {summary_txt}")
        print("-" * 60)

        return {
            "refined_json": str(refined_json),
            "refined_csv": str(refined_csv),
            "summary": str(summary_txt),
            "output_dir": str(output_dir),
        }

    def _find_latest_roughcut_json(self) -> Path:
        candidates = sorted(
            self.project.paths.exports_dir.glob("roughcut_*/roughcut_plan.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan.json"
        return candidates[0]

    def _find_best_frame_for_item(self, item: dict) -> FrameCandidate:
        video_path = str(item["video_path"])
        start = float(item.get("source_start_seconds", 0.0))
        end = float(item.get("source_end_seconds", start))

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps <= 0:
                raise RuntimeError("Invalid FPS")

            candidates: list[FrameCandidate] = []
            t = start

            while t <= end + 0.001:
                frame = self._read_frame(cap, fps, t)
                if frame is not None:
                    candidates.append(self._score_frame(frame, t))
                t += self.config.sample_step_seconds

            if not candidates:
                raise RuntimeError("No readable frames in segment")

            center = (start + end) / 2.0
            half = max(0.001, (end - start) / 2.0)

            def rank(c: FrameCandidate) -> float:
                edge_penalty = abs(c.second - center) / half * 4.0
                return c.total_score - edge_penalty

            return max(candidates, key=rank)

        finally:
            cap.release()

    @staticmethod
    def _read_frame(cap: cv2.VideoCapture, fps: float, second: float):
        frame_index = max(0, int(second * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok or frame is None:
            return None
        return frame

    def _score_frame(self, frame, second: float) -> FrameCandidate:
        small = self._resize_frame(frame, self.config.thumbnail_width)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        sharpness = clamp(lap_var / 4.0)

        brightness = float(np.mean(gray))
        exposure = clamp(100.0 - (abs(brightness - 128.0) / 128.0 * 100.0))

        contrast = clamp(float(np.std(gray)) * 2.0)

        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        saturation = clamp(float(np.mean(hsv[:, :, 1])) / 1.8)

        edges = cv2.Canny(gray, 80, 160)
        edge_density = float(np.mean(edges > 0))
        detail = clamp(edge_density * 450.0)

        blank_penalty = 0.0
        if contrast < 18:
            blank_penalty += 12.0
        if detail < 4:
            blank_penalty += 10.0
        if brightness < 35 or brightness > 225:
            blank_penalty += 15.0

        total = (
            sharpness * 0.34
            + exposure * 0.22
            + contrast * 0.18
            + saturation * 0.10
            + detail * 0.16
            - blank_penalty
        )

        return FrameCandidate(
            second=round(float(second), 3),
            total_score=round(clamp(total), 2),
            sharpness_score=round(sharpness, 2),
            exposure_score=round(exposure, 2),
            contrast_score=round(contrast, 2),
            saturation_score=round(saturation, 2),
            detail_score=round(detail, 2),
            brightness_mean=round(brightness, 2),
        )

    @staticmethod
    def _resize_frame(frame, target_width: int):
        h, w = frame.shape[:2]
        if w <= target_width:
            return frame
        scale = target_width / float(w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _refine_range(self, item: dict, best_second: float) -> tuple[float, float]:
        original_start = float(item.get("source_start_seconds", 0.0))
        original_end = float(item.get("source_end_seconds", original_start))
        original_duration = max(0.0, original_end - original_start)

        target_duration = min(
            float(self.config.refined_segment_seconds),
            original_duration if original_duration > 0 else float(self.config.refined_segment_seconds),
        )

        start = best_second - target_duration / 2.0
        end = start + target_duration

        if start < original_start:
            start = original_start
            end = start + target_duration

        if end > original_end:
            end = original_end
            start = end - target_duration

        start = max(original_start, start)
        end = min(original_end, end)

        if end <= start:
            start = original_start
            end = original_end

        return round(start, 3), round(end, 3)

    @staticmethod
    def _write_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return

        all_keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in all_keys:
                    all_keys.append(key)

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_summary(path: Path, rows: list[dict]) -> None:
        total_duration = sum(float(r.get("duration_seconds", 0.0)) for r in rows)
        avg_moment = 0.0
        if rows:
            avg_moment = sum(float(r.get("best_moment_score", 0.0)) for r in rows) / len(rows)

        lines = [
            "STT AI Editor - Best Moment Summary",
            "=" * 45,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Segments: {len(rows)}",
            f"Total refined duration: {total_duration:.2f}s",
            f"Average best moment score: {avg_moment:.2f}",
            "",
            "Selected best moments:",
        ]

        for row in rows:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"{row.get('video_filename')} "
                f"best={float(row.get('best_frame_seconds', 0.0)):.2f}s "
                f"range={float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s "
                f"score={float(row.get('best_moment_score', 0.0)):.1f}"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def find_best_moments_existing_project(
    project_root: str | Path,
    roughcut_json: str | Path | None = None,
    refined_segment_seconds: float = 2.2,
    sample_step_seconds: float = 0.25,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    finder = BestMomentFinder(
        project=project,
        roughcut_json=roughcut_json,
        config=MomentFinderConfig(
            refined_segment_seconds=refined_segment_seconds,
            sample_step_seconds=sample_step_seconds,
        ),
    )

    return finder.run()
