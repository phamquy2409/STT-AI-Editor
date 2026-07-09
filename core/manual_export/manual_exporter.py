from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project import ProjectManager, STTProject


@dataclass
class ManualSelectionExportConfig:
    output_prefix: str = "manual_final"
    keep_statuses: tuple[str, ...] = ("keep",)
    fallback_statuses: tuple[str, ...] = ("maybe", "unset", "")


class ManualSelectionExporter:
    # Build 015B fix.
    # If user exports manual_selection.json before pressing KEEP/MAYBE,
    # all rows may be UNSET. This version does not crash:
    # - uses KEEP first
    # - then MAYBE
    # - then UNSET as test fallback
    # - always excludes REJECT

    def __init__(
        self,
        project: STTProject,
        selection_json: str | Path | None = None,
        config: ManualSelectionExportConfig | None = None,
    ) -> None:
        self.project = project
        self.selection_json = Path(selection_json) if selection_json else self._find_latest_selection_json()
        self.config = config or ManualSelectionExportConfig()

    def build(self) -> dict[str, str]:
        if not self.selection_json.exists():
            raise FileNotFoundError(
                "manual_selection.json not found. Export JSON from manual_review.html first, "
                "or place manual_selection.json in Downloads/project folder."
            )

        payload = json.loads(self.selection_json.read_text(encoding="utf-8"))
        selections = self._extract_selections(payload)
        status_counts = self._status_counts(selections)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        manual_json = output_dir / "manual_roughcut.json"
        manual_csv = output_dir / "manual_roughcut.csv"
        roughcut_plan_json = output_dir / "roughcut_plan.json"
        rejected_csv = output_dir / "manual_rejected.csv"
        summary_txt = output_dir / "manual_selection_summary.txt"

        print("STT AI Manual Selection Exporter - 015B")
        print(f"Project: {self.project.name}")
        print(f"Selection JSON: {self.selection_json}")
        print(f"Total selection rows: {len(selections)}")
        print(f"Status counts: {status_counts}")
        print(f"Output: {output_dir}")
        print("-" * 60)

        keep_rows = self._filter_by_status(selections, ("keep",))
        maybe_rows = self._filter_by_status(selections, ("maybe",))
        unset_rows = self._filter_by_status(selections, ("unset", ""))

        if keep_rows:
            selected_source = keep_rows
            used_statuses = ("keep",)
        elif maybe_rows:
            selected_source = maybe_rows
            used_statuses = ("maybe",)
        elif unset_rows:
            selected_source = unset_rows
            used_statuses = ("unset",)
        else:
            # Last safety fallback: use all non-reject rows.
            selected_source = [
                dict(row)
                for row in selections
                if str(row.get("status", "")).lower().strip() != "reject"
            ]
            used_statuses = ("non-reject",)

        if not selected_source:
            raise RuntimeError("No usable rows found. All rows are REJECT or video_path is missing.")

        rejected = self._filter_by_status(selections, ("reject",))

        selected = [self._normalize_row(row) for row in selected_source]
        selected = [row for row in selected if row is not None]

        if not selected:
            raise RuntimeError("Selected rows exist, but no row has valid video_path/start/end data.")

        selected.sort(key=lambda r: int(r.get("order", 0)))
        self._retimeline(selected)

        manual_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        roughcut_plan_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")

        self._write_csv(manual_csv, selected)
        self._write_csv(rejected_csv, rejected)
        self._write_summary(
            path=summary_txt,
            total_rows=len(selections),
            selected=selected,
            rejected=rejected,
            unset=unset_rows,
            status_counts=status_counts,
            used_statuses=used_statuses,
        )

        total_duration = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        print("MANUAL SELECTION EXPORT COMPLETE")
        print(f"Selected rows: {len(selected)}")
        print(f"Used statuses: {', '.join(used_statuses)}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Manual JSON: {manual_json}")
        print(f"Premiere-compatible plan: {roughcut_plan_json}")
        print("-" * 60)

        return {
            "output_dir": str(output_dir),
            "manual_json": str(manual_json),
            "manual_csv": str(manual_csv),
            "roughcut_plan_json": str(roughcut_plan_json),
            "rejected_csv": str(rejected_csv),
            "summary": str(summary_txt),
            "selection_json": str(self.selection_json),
        }

    def _find_latest_selection_json(self) -> Path:
        candidates: list[Path] = []

        candidates.extend(self.project.paths.exports_dir.glob("**/manual_selection.json"))

        downloads = Path.home() / "Downloads"
        if downloads.exists():
            candidates.extend(downloads.glob("manual_selection.json"))
            candidates.extend(downloads.glob("manual_selection*.json"))

        candidates.extend(Path.cwd().glob("manual_selection.json"))
        candidates.extend(Path.cwd().glob("manual_selection*.json"))

        project_root = Path(self.project.root)
        candidates.extend(project_root.glob("manual_selection.json"))
        candidates.extend(project_root.glob("manual_selection*.json"))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if candidates:
            return candidates[0]

        return self.project.paths.exports_dir / "manual_selection.json"

    @staticmethod
    def _extract_selections(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [dict(x) for x in payload if isinstance(x, dict)]

        if isinstance(payload, dict):
            if isinstance(payload.get("selections"), list):
                return [dict(x) for x in payload["selections"] if isinstance(x, dict)]

            if isinstance(payload.get("items"), list):
                return [dict(x) for x in payload["items"] if isinstance(x, dict)]

        raise RuntimeError("Unsupported manual_selection.json format")

    @staticmethod
    def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            status = str(row.get("status", "")).lower().strip()
            if not status:
                status = "blank"
            counts[status] = counts.get(status, 0) + 1
        return counts

    @staticmethod
    def _filter_by_status(rows: list[dict[str, Any]], statuses: tuple[str, ...]) -> list[dict[str, Any]]:
        wanted = {s.lower().strip() for s in statuses}
        result: list[dict[str, Any]] = []

        for row in rows:
            status = str(row.get("status", "")).lower().strip()
            if status in wanted:
                result.append(dict(row))

        return result

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any] | None:
        video_path = str(row.get("video_path", "")).strip()
        if not video_path:
            return None

        start = ManualSelectionExporter._to_float(row.get("source_start_seconds"), 0.0)
        end = ManualSelectionExporter._to_float(row.get("source_end_seconds"), start)
        duration = ManualSelectionExporter._to_float(row.get("duration_seconds"), end - start)

        if end <= start and duration > 0:
            end = start + duration

        duration = max(0.0, end - start)
        if duration <= 0:
            return None

        filename = str(row.get("video_filename", Path(video_path).name))

        out = dict(row)
        out["order"] = int(ManualSelectionExporter._to_float(row.get("order"), 0))
        out["video_filename"] = filename
        out["video_path"] = video_path
        out["source_start_seconds"] = round(start, 3)
        out["source_end_seconds"] = round(end, 3)
        out["duration_seconds"] = round(duration, 3)
        out["manual_selected"] = True
        out["manual_status"] = str(row.get("status", "")).lower().strip() or "blank"
        out["manual_note"] = str(row.get("note", ""))

        return out

    @staticmethod
    def _retimeline(rows: list[dict[str, Any]]) -> None:
        cursor = 0.0

        for index, row in enumerate(rows, start=1):
            duration = float(row.get("duration_seconds", 0.0))
            row["order"] = index
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + duration, 3)
            cursor += duration

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
    def _write_summary(
        path: Path,
        total_rows: int,
        selected: list[dict[str, Any]],
        rejected: list[dict[str, Any]],
        unset: list[dict[str, Any]],
        status_counts: dict[str, int],
        used_statuses: tuple[str, ...],
    ) -> None:
        total_duration = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        lines = [
            "STT AI Editor - Manual Selection Summary - 015B",
            "=" * 60,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Total review rows: {total_rows}",
            f"Status counts: {status_counts}",
            f"Selected rows: {len(selected)}",
            f"Selected statuses: {', '.join(used_statuses)}",
            f"Rejected rows: {len(rejected)}",
            f"Unset rows: {len(unset)}",
            f"Total selected duration: {total_duration:.2f}s",
            "",
            "Selected timeline:",
        ]

        for row in selected:
            note = str(row.get("manual_note", "")).strip()
            note_text = f" note={note}" if note else ""

            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s "
                f"status={row.get('manual_status', '')}"
                f"{note_text}"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def build_manual_selection_existing_project(
    project_root: str | Path,
    selection_json: str | Path | None = None,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    exporter = ManualSelectionExporter(project=project, selection_json=selection_json)
    return exporter.build()
