
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .pointer import PremiereXMLPointer, update_premiere_xml_pointer

try:
    from .validator import PremiereXMLValidator
except Exception:
    PremiereXMLValidator = None  # type: ignore


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


@dataclass
class PremierePanelSyncConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    xml_path: str | None = None
    validate_xml: bool = True
    open_folder: bool = True


class PremierePanelSync:
    # Module 043.
    # One-click sync between STT AI Editor and the Premiere panel.
    #
    # What it does:
    # - Finds latest XML
    # - Updates latest XML pointer for Premiere panel
    # - Writes panel status JSON/TXT into %APPDATA%/STT_AI_Editor
    # - Optionally validates XML
    # - Creates a sync report folder under project exports
    #
    # It does not create a new rough cut. It syncs the latest XML already exported.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.pointer = PremiereXMLPointer(project_root=self.project_root)
        self.appdata_dir = self.pointer.appdata_dir
        self.status_json = self.appdata_dir / "premiere_panel_status.json"
        self.status_txt = self.appdata_dir / "premiere_panel_status.txt"

    def sync(
        self,
        xml_path: str | Path | None = None,
        validate_xml: bool = True,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        xml = Path(xml_path) if xml_path else self.pointer.find_latest_xml()

        if not xml or not xml.exists():
            raise FileNotFoundError(
                "Không tìm thấy XML để sync với Premiere panel.\n"
                "Hãy bấm Export Latest Manual XML trước."
            )

        xml = xml.resolve()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.exports_dir / f"premiere_panel_sync_{stamp}"
        report_dir.mkdir(parents=True, exist_ok=True)

        sync_xml = report_dir / "latest_synced_to_premiere_panel.xml"
        shutil.copy2(xml, sync_xml)

        pointer_data = update_premiere_xml_pointer(
            project_root=self.project_root,
            xml_path=xml,
            source="module_043_panel_sync",
        )

        validation: dict[str, Any] = {
            "status": "skipped",
            "ok": True,
            "errors": [],
            "warnings": [],
        }
        validation_reports: dict[str, str] = {}

        if validate_xml and PremiereXMLValidator is not None:
            try:
                validator = PremiereXMLValidator(xml)
                validation = validator.validate()
                validation_reports = validator.write_reports(report_dir)
            except Exception as exc:
                validation = {
                    "status": "validator_error",
                    "ok": False,
                    "errors": [repr(exc)],
                    "warnings": [],
                }

        status = self._status_from_validation(validation)

        result = {
            "ok": status != "fail",
            "status": status,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "module": "043_premiere_panel_sync",
            "project_root": str(self.project_root),
            "xml": str(xml),
            "synced_xml_copy": str(sync_xml),
            "xml_exists": xml.exists(),
            "xml_size_bytes": xml.stat().st_size if xml.exists() else 0,
            "pointer_txt": pointer_data.get("pointer_txt"),
            "pointer_json": pointer_data.get("pointer_json"),
            "panel_status_json": str(self.status_json),
            "panel_status_txt": str(self.status_txt),
            "report_dir": str(report_dir),
            "validation": validation,
            "validation_reports": validation_reports,
            "next_steps": [
                "Premiere > Window > Extensions > STT AI Editor",
                "Bấm Refresh Latest XML",
                "Bấm Import Latest XML",
            ],
        }

        self.write_panel_status(result)
        self.write_reports(result, report_dir)

        if open_folder:
            try:
                os.startfile(report_dir)
            except Exception:
                pass

        return result

    def write_panel_status(self, result: dict[str, Any]) -> None:
        self.appdata_dir.mkdir(parents=True, exist_ok=True)
        self.status_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_txt.write_text(self.render_status_text(result), encoding="utf-8")

    def write_reports(self, result: dict[str, Any], report_dir: Path) -> None:
        (report_dir / "premiere_panel_sync_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (report_dir / "premiere_panel_sync_report.txt").write_text(
            self.render_status_text(result),
            encoding="utf-8",
        )
        (report_dir / "premiere_panel_sync_report.html").write_text(
            self.render_status_html(result),
            encoding="utf-8",
        )
        (report_dir / "Open_This_Folder.bat").write_text(
            f'@echo off\nstart "" "{report_dir}"\n',
            encoding="utf-8",
        )

    @staticmethod
    def _status_from_validation(validation: dict[str, Any]) -> str:
        status = str(validation.get("status", "unknown")).lower()

        if status in {"fail", "validator_error"}:
            return "fail"

        if validation.get("errors"):
            return "fail"

        if validation.get("warnings"):
            return "warn"

        if status in {"ok", "skipped"}:
            return "ok"

        return status or "ok"

    @staticmethod
    def render_status_text(result: dict[str, Any]) -> str:
        validation = result.get("validation", {})
        lines = [
            "STT AI Editor - Premiere Panel Sync",
            "=" * 72,
            f"Status: {str(result.get('status')).upper()}",
            f"Updated: {result.get('created_at')}",
            "",
            "XML:",
            str(result.get("xml")),
            "",
            "Pointer:",
            str(result.get("pointer_txt")),
            "",
            "Report folder:",
            str(result.get("report_dir")),
            "",
            "Validation:",
            f"- status: {validation.get('status')}",
            f"- errors: {len(validation.get('errors', []))}",
            f"- warnings: {len(validation.get('warnings', []))}",
            "",
            "Next steps:",
            "1. Premiere > Window > Extensions > STT AI Editor",
            "2. Refresh Latest XML",
            "3. Import Latest XML",
        ]

        errors = validation.get("errors", [])
        warnings = validation.get("warnings", [])

        if errors:
            lines += ["", "Errors:"]
            lines += [f"- {x}" for x in errors]

        if warnings:
            lines += ["", "Warnings:"]
            lines += [f"- {x}" for x in warnings]

        return "\n".join(lines)

    @staticmethod
    def render_status_html(result: dict[str, Any]) -> str:
        import html

        validation = result.get("validation", {})
        status = html.escape(str(result.get("status", "unknown")).upper())
        xml = html.escape(str(result.get("xml", "")))
        pointer = html.escape(str(result.get("pointer_txt", "")))
        report_dir = html.escape(str(result.get("report_dir", "")))
        updated = html.escape(str(result.get("created_at", "")))

        def li(items: list[str]) -> str:
            if not items:
                return "<li>None</li>"
            return "\n".join(f"<li>{html.escape(str(x))}</li>" for x in items)

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT AI Editor - Premiere Panel Sync</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 980px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; padding: 6px 10px; border: 1px solid #666; border-radius: 999px; font-weight: 700; }}
code {{ display: block; background: #000; padding: 12px; border-radius: 10px; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">SYNC STATUS: {status}</div>
  <h1>Premiere Panel Sync</h1>
  <p>Updated: {updated}</p>

  <h2>XML</h2>
  <code>{xml}</code>

  <h2>Pointer</h2>
  <code>{pointer}</code>

  <h2>Report folder</h2>
  <code>{report_dir}</code>

  <h2>Validation errors</h2>
  <ul>{li(validation.get("errors", []))}</ul>

  <h2>Validation warnings</h2>
  <ul>{li(validation.get("warnings", []))}</ul>

  <h2>Next steps</h2>
  <ol>
    <li>Premiere &gt; Window &gt; Extensions &gt; STT AI Editor</li>
    <li>Refresh Latest XML</li>
    <li>Import Latest XML</li>
  </ol>
</div>
</body>
</html>
'''


def sync_premiere_panel(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    xml_path: str | Path | None = None,
    validate_xml: bool = True,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PremierePanelSync(project_root=project_root).sync(
        xml_path=xml_path,
        validate_xml=validate_xml,
        open_folder=open_folder,
    )
