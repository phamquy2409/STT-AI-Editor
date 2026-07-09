from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.project import ProjectManager, STTProject


@dataclass
class FinalRoughCutConfig:
    target_duration_seconds: float = 60.0
    min_final_score: float = 20.0
    max_segments_per_video: int = 2
    output_prefix: str = "final_roughcut"


class FinalRoughCutBuilder:
    # Build 011.
    # Rebuilds roughcut using the newest people/composition score.
    # This makes Premiere XML use the improved ranking instead of the older roughcut.

    def __init__(
        self,
        project: STTProject,
        input_json: str | Path | None = None,
        config: FinalRoughCutConfig | None = None,
    ) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.config = config or FinalRoughCutConfig()

    def build(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Input people/composition json not found: {self.input_json}")

        rows = json.loads(self.input_json.read_text(encoding="utf-8"))

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        final_json = output_dir / "roughcut_final.json"
        final_csv = output_dir / "roughcut_final.csv"
        premiere_compatible_json = output_dir / "roughcut_plan.json"
        summary_txt = output_dir / "final_roughcut_summary.txt"

        print("STT AI Final Rough Cut Builder")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"Target duration: {self.config.target_duration_seconds}s")
        print(f"Min final score: {self.config.min_final_score}")
        print(f"Max segments per video: {self.config.max_segments_per_video}")
        print(f"Output: {output_dir}")
        print("-" * 60)

        selected = self._select_rows(rows)
        self._retimeline(selected)

        final_json.write_text(
            json.dumps(selected, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Compatibility copy. Existing Premiere exporter can read this too.
        premiere_compatible_json.write_text(
            json.dumps(selected, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._write_csv(final_csv, selected)
        self._write_summary(summary_txt, selected)

        total_duration = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        print("FINAL ROUGH CUT COMPLETE")
        print(f"Selected segments: {len(selected)}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"JSON: {final_json}")
        print(f"CSV: {final_csv}")
        print(f"Premiere-compatible plan: {premiere_compatible_json}")
        print("-" * 60)

        return {
            "output_dir": str(output_dir),
            "final_json": str(final_json),
            "final_csv": str(final_csv),
            "roughcut_plan_json": str(premiere_compatible_json),
            "summary": str(summary_txt),
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            "roughcut_*/roughcut_plan_people_composition.json",
            "roughcut_*/roughcut_plan_best_moments.json",
            "roughcut_*/roughcut_plan.json",
        ]

        candidates: list[Path] = []

        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan_people_composition.json"

        return candidates[0]

    def _select_rows(self, rows: list[dict]) -> list[dict]:
        ranked = sorted(
            rows,
            key=lambda r: (
                float(r.get("final_wedding_score", r.get("ai_keep_score", 0.0))),
                float(r.get("best_moment_score", 0.0)),
                float(r.get("ai_keep_score", 0.0)),
            ),
            reverse=True,
        )

        selected: list[dict] = []
        per_video_count: dict[str, int] = {}
        total = 0.0

        # Pass 1: strict score + max per video.
        for row in ranked:
            score = float(row.get("final_wedding_score", row.get("ai_keep_score", 0.0)))
            if score < self.config.min_final_score:
                continue

            video_path = str(row.get("video_path", row.get("video_filename", "")))
            used = per_video_count.get(video_path, 0)
            if used >= self.config.max_segments_per_video:
                continue

            duration = float(row.get("duration_seconds", 0.0))
            if duration <= 0:
                continue

            selected.append(dict(row))
            per_video_count[video_path] = used + 1
            total += duration

            if total >= self.config.target_duration_seconds:
                return selected

        # Pass 2: relax per-video limit if still short.
        if total < self.config.target_duration_seconds:
            already = self._identity_set(selected)

            for row in ranked:
                identity = self._row_identity(row)
                if identity in already:
                    continue

                score = float(row.get("final_wedding_score", row.get("ai_keep_score", 0.0)))
                if score < self.config.min_final_score:
                    continue

                duration = float(row.get("duration_seconds", 0.0))
                if duration <= 0:
                    continue

                selected.append(dict(row))
                total += duration
                already.add(identity)

                if total >= self.config.target_duration_seconds:
                    return selected

        # Pass 3: if still short, use any best rows.
        if total < self.config.target_duration_seconds:
            already = self._identity_set(selected)

            for row in ranked:
                identity = self._row_identity(row)
                if identity in already:
                    continue

                duration = float(row.get("duration_seconds", 0.0))
                if duration <= 0:
                    continue

                selected.append(dict(row))
                total += duration
                already.add(identity)

                if total >= self.config.target_duration_seconds:
                    break

        return selected

    @staticmethod
    def _row_identity(row: dict) -> tuple:
        return (
            str(row.get("video_path", "")),
            round(float(row.get("source_start_seconds", 0.0)), 3),
            round(float(row.get("source_end_seconds", 0.0)), 3),
        )

    def _identity_set(self, rows: list[dict]) -> set[tuple]:
        return {self._row_identity(r) for r in rows}

    @staticmethod
    def _retimeline(rows: list[dict]) -> None:
        cursor = 0.0

        for index, row in enumerate(rows, start=1):
            duration = float(row.get("duration_seconds", 0.0))

            row["order"] = index
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + duration, 3)
            row["final_cut_order"] = index
            row["final_cut_selected"] = True

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
        total_duration = sum(float(r.get("duration_seconds", 0.0)) for r in rows)
        avg_final = 0.0
        avg_moment = 0.0

        if rows:
            avg_final = sum(float(r.get("final_wedding_score", 0.0)) for r in rows) / len(rows)
            avg_moment = sum(float(r.get("best_moment_score", 0.0)) for r in rows) / len(rows)

        lines = [
            "STT AI Editor - Final Rough Cut Summary",
            "=" * 50,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Segments: {len(rows)}",
            f"Total duration: {total_duration:.2f}s",
            f"Average final wedding score: {avg_final:.2f}",
            f"Average best moment score: {avg_moment:.2f}",
            "",
            "Final sequence:",
        ]

        for row in rows:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s "
                f"final={float(row.get('final_wedding_score', 0.0)):.1f} "
                f"moment={float(row.get('best_moment_score', 0.0)):.1f} "
                f"label={row.get('content_label', '')}"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def build_final_roughcut_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
    target_duration_seconds: float = 60.0,
    min_final_score: float = 20.0,
    max_segments_per_video: int = 2,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    builder = FinalRoughCutBuilder(
        project=project,
        input_json=input_json,
        config=FinalRoughCutConfig(
            target_duration_seconds=target_duration_seconds,
            min_final_score=min_final_score,
            max_segments_per_video=max_segments_per_video,
        ),
    )

    return builder.build()
