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
class PeopleCompositionConfig:
    thumbnail_width: int = 960
    skin_weight: float = 0.42
    composition_weight: float = 0.35
    detail_weight: float = 0.23


@dataclass
class PeopleCompositionResult:
    people_score: float
    face_score: float
    composition_score: float
    subject_score: float
    face_count: int
    largest_face_area_ratio: float
    center_score: float
    thirds_score: float
    content_label: str
    final_wedding_score: float
    note: str


class PeopleCompositionAnalyzer:
    # Build 010 FIX.
    # No cv2.CascadeClassifier, because OpenCV 5 alpha on Python 3.14 may not include it.
    # Uses skin-color regions + subject/detail + composition heuristics.

    def __init__(
        self,
        project: STTProject,
        input_json: str | Path | None = None,
        config: PeopleCompositionConfig | None = None,
    ) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.config = config or PeopleCompositionConfig()

    def run(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Input roughcut json not found: {self.input_json}")

        items = json.loads(self.input_json.read_text(encoding="utf-8"))

        output_dir = self.input_json.parent
        output_json = output_dir / "roughcut_plan_people_composition.json"
        output_csv = output_dir / "roughcut_plan_people_composition.csv"
        summary_txt = output_dir / "people_composition_summary.txt"

        print("STT AI People / Composition Analyzer - FIX")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"Segments: {len(items)}")
        print("-" * 60)

        rows: list[dict] = []

        for idx, item in enumerate(items, start=1):
            try:
                second = float(item.get("best_frame_seconds", item.get("thumbnail_second", 0.0)))
                if second <= 0:
                    start = float(item.get("source_start_seconds", 0.0))
                    end = float(item.get("source_end_seconds", start))
                    second = (start + end) / 2.0

                frame = self._read_frame(str(item["video_path"]), second)
                result = self._analyze_frame(frame)

                row = dict(item)
                row.update({
                    "people_score": result.people_score,
                    "face_score": result.face_score,
                    "composition_score": result.composition_score,
                    "subject_score": result.subject_score,
                    "face_count": result.face_count,
                    "largest_face_area_ratio": result.largest_face_area_ratio,
                    "center_score": result.center_score,
                    "thirds_score": result.thirds_score,
                    "content_label": result.content_label,
                    "final_wedding_score": result.final_wedding_score,
                    "people_composition_note": result.note,
                    "people_composition_status": "ok",
                })

                print(
                    f"[{idx}/{len(items)}] {item.get('video_filename')} | "
                    f"skin_regions={result.face_count} "
                    f"people={result.people_score:.1f} "
                    f"comp={result.composition_score:.1f} "
                    f"final={result.final_wedding_score:.1f} "
                    f"label={result.content_label}"
                )

            except Exception as exc:
                row = dict(item)
                row.update({
                    "people_score": 0.0,
                    "face_score": 0.0,
                    "composition_score": 0.0,
                    "subject_score": 0.0,
                    "face_count": 0,
                    "largest_face_area_ratio": 0.0,
                    "center_score": 0.0,
                    "thirds_score": 0.0,
                    "content_label": "error",
                    "final_wedding_score": float(item.get("ai_keep_score", 0.0)),
                    "people_composition_note": str(exc),
                    "people_composition_status": "error",
                })

                print(f"[{idx}/{len(items)}] ERROR {item.get('video_filename')}: {exc}")

            rows.append(row)

        self._sort_and_retimeline(rows)

        output_json.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._write_csv(output_csv, rows)
        self._write_summary(summary_txt, rows)

        print("-" * 60)
        print("PEOPLE / COMPOSITION COMPLETE")
        print(f"JSON: {output_json}")
        print(f"CSV: {output_csv}")
        print(f"Summary: {summary_txt}")
        print("-" * 60)

        return {
            "people_json": str(output_json),
            "people_csv": str(output_csv),
            "summary": str(summary_txt),
            "output_dir": str(output_dir),
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            "roughcut_*/roughcut_plan_best_moments.json",
            "roughcut_*/roughcut_plan.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan_best_moments.json"

        return candidates[0]

    def _read_frame(self, video_path: str, second: float):
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps <= 0:
                raise RuntimeError("Invalid FPS")

            frame_index = max(0, int(second * fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("Cannot read frame")

            return self._resize_frame(frame, self.config.thumbnail_width)

        finally:
            cap.release()

    @staticmethod
    def _resize_frame(frame, target_width: int):
        h, w = frame.shape[:2]
        if w <= target_width:
            return frame

        scale = target_width / float(w)
        new_w = int(w * scale)
        new_h = int(h * scale)

        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _analyze_frame(self, frame) -> PeopleCompositionResult:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        skin_mask = self._skin_mask(frame)
        regions = self._skin_regions(skin_mask, w, h)

        frame_area = float(w * h)

        region_count = len(regions)
        largest_area = 0.0
        center_score = 0.0
        thirds_score = 0.0

        if regions:
            largest = max(regions, key=lambda r: r[2] * r[3])
            x, y, rw, rh = largest
            largest_area = float(rw * rh) / frame_area

            cx = x + rw / 2.0
            cy = y + rh / 2.0

            center_score = self._center_score(cx, cy, w, h)
            thirds_score = self._thirds_score(cx, cy, w, h)

        skin_density = float(np.mean(skin_mask > 0))
        face_score = self._skin_region_score(region_count, largest_area, skin_density)
        subject_score = self._subject_score(gray)
        composition_score = self._composition_score(center_score, thirds_score, face_score, subject_score)
        people_score = clamp(face_score * 0.70 + subject_score * 0.30)

        content_label = self._content_label(region_count, people_score, subject_score, largest_area, skin_density)

        final = (
            people_score * self.config.skin_weight
            + composition_score * self.config.composition_weight
            + subject_score * self.config.detail_weight
        )

        if content_label == "empty_or_decor":
            final *= 0.70
        elif content_label == "possible_people_or_detail":
            final *= 0.92
        elif content_label == "wide_people":
            final *= 1.02
        elif content_label == "skin_people":
            final *= 1.08

        final = clamp(final)

        note = (
            f"skin_regions={region_count}; skin_density={skin_density:.4f}; "
            f"largest={largest_area:.4f}; center={center_score:.1f}; "
            f"thirds={thirds_score:.1f}; label={content_label}"
        )

        return PeopleCompositionResult(
            people_score=round(people_score, 2),
            face_score=round(face_score, 2),
            composition_score=round(composition_score, 2),
            subject_score=round(subject_score, 2),
            face_count=region_count,
            largest_face_area_ratio=round(largest_area, 5),
            center_score=round(center_score, 2),
            thirds_score=round(thirds_score, 2),
            content_label=content_label,
            final_wedding_score=round(final, 2),
            note=note,
        )

    @staticmethod
    def _skin_mask(frame):
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        y, cr, cb = cv2.split(ycrcb)
        h, s, v = cv2.split(hsv)

        # Broad skin color heuristic for mixed wedding light.
        mask_ycrcb = (
            (cr >= 130) & (cr <= 180) &
            (cb >= 75) & (cb <= 140) &
            (y >= 40)
        )

        mask_hsv = (
            ((h <= 25) | (h >= 170)) &
            (s >= 18) & (s <= 180) &
            (v >= 45)
        )

        mask = (mask_ycrcb & mask_hsv).astype(np.uint8) * 255

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        return mask

    @staticmethod
    def _skin_regions(mask, frame_w: int, frame_h: int) -> list[tuple[int, int, int, int]]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions: list[tuple[int, int, int, int]] = []
        frame_area = frame_w * frame_h

        for c in contours:
            area = cv2.contourArea(c)
            if area < frame_area * 0.00025:
                continue

            x, y, w, h = cv2.boundingRect(c)
            if w <= 8 or h <= 8:
                continue

            ratio = w / float(h)
            if ratio < 0.25 or ratio > 3.2:
                continue

            regions.append((x, y, w, h))

        regions = sorted(regions, key=lambda r: r[2] * r[3], reverse=True)[:12]
        return regions

    @staticmethod
    def _center_score(cx: float, cy: float, w: int, h: int) -> float:
        dx = abs(cx - w / 2.0) / (w / 2.0)
        dy = abs(cy - h / 2.0) / (h / 2.0)
        dist = (dx * 0.65 + dy * 0.35)
        return clamp(100.0 - dist * 100.0)

    @staticmethod
    def _thirds_score(cx: float, cy: float, w: int, h: int) -> float:
        points = [
            (w / 3.0, h / 3.0),
            (2 * w / 3.0, h / 3.0),
            (w / 3.0, 2 * h / 3.0),
            (2 * w / 3.0, 2 * h / 3.0),
            (w / 2.0, h / 2.0),
        ]

        best = 0.0

        for px, py in points:
            dx = abs(cx - px) / w
            dy = abs(cy - py) / h
            dist = (dx ** 2 + dy ** 2) ** 0.5
            score = clamp(100.0 - dist * 220.0)
            best = max(best, score)

        return best

    @staticmethod
    def _skin_region_score(region_count: int, area_ratio: float, skin_density: float) -> float:
        if region_count <= 0 and skin_density < 0.006:
            return 0.0

        count_score = clamp(region_count * 20.0, 0.0, 75.0)

        if area_ratio <= 0:
            size_score = clamp(skin_density * 800.0, 0, 25)
        elif area_ratio < 0.001:
            size_score = 25.0
        elif area_ratio < 0.004:
            size_score = 48.0
        elif area_ratio < 0.018:
            size_score = 78.0
        else:
            size_score = 95.0

        density_score = clamp(skin_density * 1100.0)

        return clamp(count_score * 0.35 + size_score * 0.45 + density_score * 0.20)

    @staticmethod
    def _subject_score(gray) -> float:
        contrast = float(np.std(gray))
        edges = cv2.Canny(gray, 80, 160)
        edge_density = float(np.mean(edges > 0))

        detail_score = clamp(edge_density * 520.0)
        contrast_score = clamp(contrast * 1.75)

        return clamp(detail_score * 0.60 + contrast_score * 0.40)

    @staticmethod
    def _composition_score(center_score: float, thirds_score: float, face_score: float, subject_score: float) -> float:
        if face_score <= 0:
            return clamp(subject_score * 0.55)
        return clamp(center_score * 0.38 + thirds_score * 0.42 + face_score * 0.20)

    @staticmethod
    def _content_label(region_count: int, people_score: float, subject_score: float, area_ratio: float, skin_density: float) -> str:
        if region_count >= 1 and (area_ratio >= 0.003 or skin_density >= 0.018):
            return "skin_people"

        if region_count >= 1:
            return "wide_people"

        if subject_score >= 55:
            return "possible_people_or_detail"

        return "empty_or_decor"

    @staticmethod
    def _sort_and_retimeline(rows: list[dict]) -> None:
        rows.sort(
            key=lambda r: (
                float(r.get("final_wedding_score", 0.0)),
                float(r.get("best_moment_score", 0.0)),
                float(r.get("ai_keep_score", 0.0)),
            ),
            reverse=True,
        )

        cursor = 0.0

        for index, row in enumerate(rows, start=1):
            duration = float(row.get("duration_seconds", 0.0))
            row["order"] = index
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + duration, 3)
            cursor += duration

    @staticmethod
    def _write_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return

        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_summary(path: Path, rows: list[dict]) -> None:
        labels: dict[str, int] = {}

        for row in rows:
            label = str(row.get("content_label", "unknown"))
            labels[label] = labels.get(label, 0) + 1

        avg_final = 0.0
        if rows:
            avg_final = sum(float(r.get("final_wedding_score", 0.0)) for r in rows) / len(rows)

        lines = [
            "STT AI Editor - People / Composition Summary",
            "=" * 55,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Segments: {len(rows)}",
            f"Average final wedding score: {avg_final:.2f}",
            "",
            "Content labels:",
        ]

        for label, count in sorted(labels.items()):
            lines.append(f"- {label}: {count}")

        lines.append("")
        lines.append("Top ranked:")

        for row in rows[:30]:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"{row.get('video_filename')} "
                f"final={float(row.get('final_wedding_score', 0.0)):.1f} "
                f"skin_regions={int(row.get('face_count', 0))} "
                f"label={row.get('content_label')}"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def analyze_people_composition_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    analyzer = PeopleCompositionAnalyzer(
        project=project,
        input_json=input_json,
    )

    return analyzer.run()
