from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class HealthCheckConfig:
    project_root: str = "D:/STT Projects/Wedding_Test_001"
    repo_root: str = "D:/Projects/STT-AI-Editor"


class STTHealthCheck:
    # Module 035.
    # Quick health check before calling the app stable.

    def __init__(self, project_root: str | Path, repo_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.repo_root = Path(repo_root)

    def run(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "repo_root": str(self.repo_root),
            "project_root": str(self.project_root),
            "python": sys.version,
            "checks": [],
            "summary": {
                "ok": 0,
                "warn": 0,
                "fail": 0,
            },
        }

        self._check_path(result, "Repo folder", self.repo_root, must_exist=True)
        self._check_path(result, "Project folder", self.project_root, must_exist=True)
        self._check_path(result, "Project JSON", self.project_root / "project.json", must_exist=True)
        self._check_path(result, "Database", self.project_root / "database" / "stt_ai.db", must_exist=True)
        self._check_path(result, "Exports folder", self.project_root / "exports", must_exist=True)
        self._check_path(result, "Manual selection", self.project_root / "manual_selection.json", must_exist=False)
        self._check_path(result, "Feedback profile", self.project_root / "stt_feedback_profile.json", must_exist=False)
        self._check_path(result, "XML export settings", self.project_root / "stt_xml_export_settings.json", must_exist=False)

        self._check_path(result, "GUI runner", self.repo_root / "scripts" / "run_gui.py", must_exist=True)
        self._check_path(result, "Build EXE script", self.repo_root / "scripts" / "build_exe.py", must_exist=True)
        self._check_path(result, "EXE folder", self.repo_root / "dist" / "STT AI Editor", must_exist=False)
        self._check_path(result, "EXE file", self.repo_root / "dist" / "STT AI Editor" / "STT AI Editor.exe", must_exist=False)

        for package in ["PySide6", "cv2", "numpy", "sqlalchemy"]:
            self._check_import(result, package)

        self._check_command(result, "git")
        self._check_command(result, "ffmpeg")

        latest_xml = self._latest_file(self.project_root / "exports", "stt_ai_premiere_import.xml")
        if latest_xml:
            self._add(result, "Latest Premiere XML", "ok", str(latest_xml))
        else:
            self._add(result, "Latest Premiere XML", "warn", "No XML found yet.")

        latest_manual = self._latest_file(self.project_root / "exports", "manual_review.html")
        if latest_manual:
            self._add(result, "Latest manual review", "ok", str(latest_manual))
        else:
            self._add(result, "Latest manual review", "warn", "No manual_review.html found yet.")

        report_dir = self.project_root / "exports" / f"app_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_json = report_dir / "health_report.json"
        report_txt = report_dir / "health_report.txt"

        result["report_dir"] = str(report_dir)
        result["report_json"] = str(report_json)
        result["report_txt"] = str(report_txt)

        report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        report_txt.write_text(self._render_text(result), encoding="utf-8")

        return result

    def _check_path(self, result: dict[str, Any], name: str, path: Path, must_exist: bool) -> None:
        exists = path.exists()
        if exists:
            self._add(result, name, "ok", str(path))
        elif must_exist:
            self._add(result, name, "fail", f"Missing: {path}")
        else:
            self._add(result, name, "warn", f"Optional missing: {path}")

    def _check_import(self, result: dict[str, Any], package: str) -> None:
        if importlib.util.find_spec(package) is not None:
            self._add(result, f"Python package {package}", "ok", "installed")
        else:
            self._add(result, f"Python package {package}", "fail", "not installed")

    def _check_command(self, result: dict[str, Any], command: str) -> None:
        path = shutil.which(command)
        if path:
            self._add(result, f"Command {command}", "ok", path)
        else:
            self._add(result, f"Command {command}", "warn", "not found in PATH")

    @staticmethod
    def _latest_file(root: Path, filename: str) -> Path | None:
        if not root.exists():
            return None

        files = [p for p in root.glob(f"**/{filename}") if p.is_file()]
        if not files:
            return None

        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    @staticmethod
    def _add(result: dict[str, Any], name: str, status: str, detail: str) -> None:
        result["checks"].append(
            {
                "name": name,
                "status": status,
                "detail": detail,
            }
        )
        result["summary"][status] = int(result["summary"].get(status, 0)) + 1

    @staticmethod
    def _render_text(result: dict[str, Any]) -> str:
        lines = [
            "STT AI Editor - Health Report",
            "=" * 70,
            f"Created: {result.get('created_at')}",
            f"Repo: {result.get('repo_root')}",
            f"Project: {result.get('project_root')}",
            "",
            "Summary:",
            f"OK: {result['summary'].get('ok', 0)}",
            f"WARN: {result['summary'].get('warn', 0)}",
            f"FAIL: {result['summary'].get('fail', 0)}",
            "",
            "Checks:",
        ]

        for check in result.get("checks", []):
            lines.append(f"[{check['status'].upper()}] {check['name']} - {check['detail']}")

        return "\n".join(lines)


def run_health_check(
    project_root: str | Path = "D:/STT Projects/Wedding_Test_001",
    repo_root: str | Path = "D:/Projects/STT-AI-Editor",
) -> dict[str, Any]:
    return STTHealthCheck(project_root=project_root, repo_root=repo_root).run()
