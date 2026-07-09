from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExportCleanerConfig:
    keep_latest_per_prefix: int = 2
    archive_folder_name: str = "_archive"
    dry_run: bool = True


class ExportCleaner:
    # Build 029.
    # Safe cleanup for STT AI Editor exports.
    #
    # It does NOT delete anything.
    # It moves old export folders into:
    #   <project>/exports/_archive/archive_YYYYMMDD_HHMMSS/
    #
    # It keeps latest N folders per prefix:
    #   wedding_pipeline_v2
    #   duplicate_removed
    #   story_timeline_v2
    #   wedding_scene
    #   manual_final
    #   etc.

    def __init__(self, project_root: str | Path, config: ExportCleanerConfig | None = None) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.config = config or ExportCleanerConfig()

    def preview(self) -> dict[str, Any]:
        return self._run(dry_run=True)

    def archive_old_exports(self) -> dict[str, Any]:
        return self._run(dry_run=False)

    def _run(self, dry_run: bool) -> dict[str, Any]:
        if not self.project_root.exists():
            raise FileNotFoundError(f"Project root not found: {self.project_root}")

        if not self.exports_dir.exists():
            raise FileNotFoundError(f"Exports folder not found: {self.exports_dir}")

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_root = self.exports_dir / self.config.archive_folder_name
        archive_run_dir = archive_root / f"archive_{stamp}"

        folders = self._list_export_folders()
        groups = self._group_by_prefix(folders)

        keep: set[Path] = set()
        candidates: list[Path] = []

        for prefix, items in groups.items():
            items_sorted = sorted(items, key=lambda p: p.stat().st_mtime, reverse=True)
            keep.update(items_sorted[: self.config.keep_latest_per_prefix])
            candidates.extend(items_sorted[self.config.keep_latest_per_prefix:])

        # Never archive the archive folder itself.
        candidates = [
            p for p in candidates
            if p.name != self.config.archive_folder_name
            and self.config.archive_folder_name not in p.parts
        ]

        moved: list[dict[str, str]] = []
        skipped: list[dict[str, str]] = []

        if not dry_run and candidates:
            archive_run_dir.mkdir(parents=True, exist_ok=True)

        for folder in sorted(candidates, key=lambda p: p.stat().st_mtime):
            destination = archive_run_dir / folder.name

            if destination.exists():
                destination = archive_run_dir / f"{folder.name}_{stamp}"

            if dry_run:
                moved.append({
                    "from": str(folder),
                    "to": str(destination),
                    "action": "would_archive",
                    "size": self._format_bytes(self._folder_size(folder)),
                })
                continue

            try:
                shutil.move(str(folder), str(destination))
                moved.append({
                    "from": str(folder),
                    "to": str(destination),
                    "action": "archived",
                    "size": self._format_bytes(self._folder_size(destination)),
                })
            except Exception as exc:
                skipped.append({
                    "path": str(folder),
                    "reason": repr(exc),
                })

        kept_rows = [
            {
                "path": str(p),
                "prefix": self._prefix(p.name),
                "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
                "size": self._format_bytes(self._folder_size(p)),
            }
            for p in sorted(keep, key=lambda x: x.stat().st_mtime, reverse=True)
            if p.exists()
        ]

        result = {
            "project_root": str(self.project_root),
            "exports_dir": str(self.exports_dir),
            "dry_run": dry_run,
            "keep_latest_per_prefix": self.config.keep_latest_per_prefix,
            "archive_run_dir": str(archive_run_dir),
            "total_export_folders": len(folders),
            "kept_count": len(kept_rows),
            "archive_count": len(moved),
            "skipped_count": len(skipped),
            "kept": kept_rows,
            "archive": moved,
            "skipped": skipped,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        report_path = self._write_report(result, stamp, dry_run)
        result["report_json"] = str(report_path)

        return result

    def _list_export_folders(self) -> list[Path]:
        folders: list[Path] = []

        for p in self.exports_dir.iterdir():
            if not p.is_dir():
                continue

            if p.name == self.config.archive_folder_name:
                continue

            folders.append(p)

        return folders

    @staticmethod
    def _group_by_prefix(folders: list[Path]) -> dict[str, list[Path]]:
        groups: dict[str, list[Path]] = {}

        for folder in folders:
            prefix = ExportCleaner._prefix(folder.name)
            groups.setdefault(prefix, []).append(folder)

        return groups

    @staticmethod
    def _prefix(name: str) -> str:
        parts = name.split("_")

        if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
            return "_".join(parts[:-2])

        return name

    def _write_report(self, result: dict[str, Any], stamp: str, dry_run: bool) -> Path:
        reports_dir = self.exports_dir / "_cleanup_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        name = "cleanup_preview" if dry_run else "cleanup_archive"
        path = reports_dir / f"{name}_{stamp}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _folder_size(path: Path) -> int:
        total = 0

        if not path.exists():
            return 0

        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except Exception:
                    pass

        return total

    @staticmethod
    def _format_bytes(value: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(value)

        for unit in units:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0

        return f"{size:.1f} PB"


def preview_export_cleanup_existing_project(
    project_root: str | Path,
    keep_latest_per_prefix: int = 2,
) -> dict[str, Any]:
    cleaner = ExportCleaner(
        project_root=project_root,
        config=ExportCleanerConfig(
            keep_latest_per_prefix=keep_latest_per_prefix,
            dry_run=True,
        ),
    )
    return cleaner.preview()


def archive_old_exports_existing_project(
    project_root: str | Path,
    keep_latest_per_prefix: int = 2,
) -> dict[str, Any]:
    cleaner = ExportCleaner(
        project_root=project_root,
        config=ExportCleanerConfig(
            keep_latest_per_prefix=keep_latest_per_prefix,
            dry_run=False,
        ),
    )
    return cleaner.archive_old_exports()
