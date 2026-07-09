
from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


REQUIRED_MODULES = [
    ("046", "core.ai_shot_scorer", "AI Shot Scorer"),
    ("047", "core.prewedding_selector", "Prewedding Selector"),
    ("048", "core.prewedding_roughcut", "Prewedding Roughcut"),
    ("050", "core.prewedding_refiner", "Prewedding Smart Refiner"),
    ("049", "core.prewedding_xml", "Prewedding XML Exporter"),
    ("051", "core.prewedding_pipeline", "Prewedding One-Click Pipeline"),
]

REQUIRED_SCRIPTS = [
    "scripts/run_ai_shot_scorer.py",
    "scripts/build_prewedding_selection.py",
    "scripts/build_prewedding_roughcut.py",
    "scripts/refine_prewedding_roughcut.py",
    "scripts/export_prewedding_xml.py",
    "scripts/run_prewedding_pipeline.py",
]

IMPORTANT_PROJECT_FILES = [
    "manual_selection.json",
    "stt_ai_style_memory_v2.json",
    "stt_ai_shot_scores_v1.json",
    "stt_prewedding_selection_v1.json",
    "stt_prewedding_roughcut_v1.json",
    "stt_prewedding_refined_v1.json",
    "stt_prewedding_premiere_import.xml",
    "stt_prewedding_pipeline_v1.json",
]


@dataclass
class PreweddingDoctorConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    repo_root: str | None = None
    open_folder: bool = True


class PreweddingPipelineDoctor:
    # Module 052.
    #
    # Checks whether Modules 046-051 are installed correctly and whether the
    # current project has enough data to run the one-click prewedding pipeline.

    def __init__(
        self,
        project_root: str | Path = DEFAULT_PROJECT_ROOT,
        repo_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.repo_root = Path(repo_root) if repo_root else self.detect_repo_root()
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    @staticmethod
    def detect_repo_root() -> Path:
        # When called from scripts, repo root is usually parents[2] from this file.
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            if (parent / "scripts").exists() and (parent / "core").exists():
                return parent
        return Path.cwd()

    def check(self, open_folder: bool = True) -> dict[str, Any]:
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.appdata_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.exports_dir / f"prewedding_pipeline_doctor_{stamp}"
        report_dir.mkdir(parents=True, exist_ok=True)

        report = {
            "ok": False,
            "module": "052_prewedding_pipeline_doctor",
            "version": "0.52",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(self.project_root),
            "repo_root": str(self.repo_root),
            "python": sys.executable,
            "python_version": sys.version,
            "appdata_dir": str(self.appdata_dir),
            "checks": {
                "modules": self.check_modules(),
                "scripts": self.check_scripts(),
                "project_files": self.check_project_files(),
                "exports": self.check_exports(),
                "premiere_pointer": self.check_premiere_pointer(),
                "gui_patches": self.check_gui_patches(),
            },
            "summary": {},
            "recommended_next_commands": [],
        }

        report["summary"] = self.build_summary(report)
        report["ok"] = report["summary"]["ready_for_pipeline"]

        report["recommended_next_commands"] = self.recommend_commands(report)

        report_json = report_dir / "stt_prewedding_doctor_report.json"
        report_txt = report_dir / "PREWEDDING_DOCTOR_REPORT.txt"
        report_html = report_dir / "PREWEDDING_DOCTOR_REPORT.html"

        report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report_txt.write_text(self.render_text(report), encoding="utf-8")
        report_html.write_text(self.render_html(report), encoding="utf-8")

        result = {
            "ok": report["ok"],
            "ready_for_pipeline": report["summary"]["ready_for_pipeline"],
            "ready_for_xml": report["summary"]["ready_for_xml"],
            "ready_for_premiere": report["summary"]["ready_for_premiere"],
            "missing_modules": report["summary"]["missing_modules"],
            "missing_scripts": report["summary"]["missing_scripts"],
            "missing_project_files": report["summary"]["missing_project_files"],
            "report_dir": str(report_dir),
            "report_json": str(report_json),
            "report_txt": str(report_txt),
            "report_html": str(report_html),
            "recommended_next_commands": report["recommended_next_commands"],
        }

        (report_dir / "prewedding_doctor_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(report_dir)
            except Exception:
                pass

        return result

    def check_modules(self) -> list[dict[str, Any]]:
        results = []
        for module_no, module_name, label in REQUIRED_MODULES:
            item = {
                "module_no": module_no,
                "module": module_name,
                "label": label,
                "ok": False,
                "error": None,
            }
            try:
                importlib.import_module(module_name)
                item["ok"] = True
            except Exception as exc:
                item["error"] = repr(exc)
            results.append(item)
        return results

    def check_scripts(self) -> list[dict[str, Any]]:
        results = []
        for rel in REQUIRED_SCRIPTS:
            path = self.repo_root / rel
            results.append({
                "path": rel,
                "exists": path.exists(),
                "full_path": str(path),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            })
        return results

    def check_project_files(self) -> list[dict[str, Any]]:
        results = []
        for rel in IMPORTANT_PROJECT_FILES:
            path = self.project_root / rel
            results.append({
                "path": rel,
                "exists": path.exists(),
                "full_path": str(path),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if path.exists() else None,
            })
        return results

    def check_exports(self) -> dict[str, Any]:
        if not self.exports_dir.exists():
            return {
                "exists": False,
                "path": str(self.exports_dir),
                "latest_dirs": [],
            }

        dirs = [p for p in self.exports_dir.iterdir() if p.is_dir() and p.name != "_archive"]
        dirs = sorted(dirs, key=lambda p: p.stat().st_mtime, reverse=True)[:20]

        return {
            "exists": True,
            "path": str(self.exports_dir),
            "latest_dirs": [
                {
                    "name": p.name,
                    "path": str(p),
                    "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
                }
                for p in dirs
            ],
        }

    def check_premiere_pointer(self) -> dict[str, Any]:
        pointer_txt = self.appdata_dir / "premiere_latest_xml.txt"
        pointer_json = self.appdata_dir / "premiere_latest_xml.json"

        xml_path = None
        if pointer_txt.exists():
            try:
                text = pointer_txt.read_text(encoding="utf-8").strip()
                xml_path = Path(text) if text else None
            except Exception:
                xml_path = None

        return {
            "pointer_txt": str(pointer_txt),
            "pointer_txt_exists": pointer_txt.exists(),
            "pointer_json": str(pointer_json),
            "pointer_json_exists": pointer_json.exists(),
            "xml_from_pointer": str(xml_path) if xml_path else None,
            "xml_exists": xml_path.exists() if xml_path else False,
            "xml_size_bytes": xml_path.stat().st_size if xml_path and xml_path.exists() else 0,
        }

    def check_gui_patches(self) -> list[dict[str, Any]]:
        patches = [
            "core/gui/ai_shot_scorer_patch.py",
            "core/gui/prewedding_selector_patch.py",
            "core/gui/prewedding_roughcut_patch.py",
            "core/gui/prewedding_refiner_patch.py",
            "core/gui/prewedding_xml_patch.py",
            "core/gui/prewedding_pipeline_patch.py",
            "core/gui/compact_scroll_patch.py",
        ]
        results = []
        for rel in patches:
            path = self.repo_root / rel
            results.append({
                "path": rel,
                "exists": path.exists(),
                "full_path": str(path),
            })
        return results

    @staticmethod
    def build_summary(report: dict[str, Any]) -> dict[str, Any]:
        modules = report["checks"]["modules"]
        scripts = report["checks"]["scripts"]
        project_files = report["checks"]["project_files"]
        pointer = report["checks"]["premiere_pointer"]

        missing_modules = [x["module"] for x in modules if not x["ok"]]
        missing_scripts = [x["path"] for x in scripts if not x["exists"]]
        missing_project_files = [x["path"] for x in project_files if not x["exists"]]

        has_manual_or_score = any(
            x["path"] in {"manual_selection.json", "stt_ai_shot_scores_v1.json"} and x["exists"]
            for x in project_files
        )
        has_selection = any(x["path"] == "stt_prewedding_selection_v1.json" and x["exists"] for x in project_files)
        has_roughcut_or_refined = any(
            x["path"] in {"stt_prewedding_roughcut_v1.json", "stt_prewedding_refined_v1.json"} and x["exists"]
            for x in project_files
        )
        has_xml = any(x["path"] == "stt_prewedding_premiere_import.xml" and x["exists"] for x in project_files)

        modules_ok = not missing_modules
        scripts_ok = not missing_scripts

        return {
            "modules_ok": modules_ok,
            "scripts_ok": scripts_ok,
            "has_manual_or_score": has_manual_or_score,
            "has_selection": has_selection,
            "has_roughcut_or_refined": has_roughcut_or_refined,
            "has_xml": has_xml,
            "pointer_ok": bool(pointer.get("xml_exists")),
            "ready_for_pipeline": modules_ok and scripts_ok and has_manual_or_score,
            "ready_for_xml": modules_ok and scripts_ok and (has_selection or has_roughcut_or_refined),
            "ready_for_premiere": has_xml or bool(pointer.get("xml_exists")),
            "missing_modules": missing_modules,
            "missing_scripts": missing_scripts,
            "missing_project_files": missing_project_files,
        }

    @staticmethod
    def recommend_commands(report: dict[str, Any]) -> list[str]:
        summary = report["summary"]

        if summary["missing_modules"] or summary["missing_scripts"]:
            return [
                "Cài lại module bị thiếu trước.",
                "Copy ZIP module vào D:\\Projects\\STT-AI-Editor và chọn Replace.",
                "python scripts/test_prewedding_pipeline.py",
            ]

        if not summary["has_manual_or_score"]:
            return [
                "python scripts/run_gui.py",
                "Chạy Final Wedding V2 + Live Review hoặc tạo manual_selection.json trước.",
                "Sau đó chạy: python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s",
            ]

        if not summary["ready_for_premiere"]:
            return [
                "python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s",
                "Hoặc chạy XML riêng: python scripts/export_prewedding_xml.py --preset vertical_1080_25p",
            ]

        return [
            "python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s",
            "Premiere panel STT AI Editor > Refresh Latest XML > Import Latest XML",
        ]

    @staticmethod
    def render_text(report: dict[str, Any]) -> str:
        summary = report["summary"]

        lines = [
            "STT AI Editor - Prewedding Pipeline Doctor",
            "=" * 72,
            f"Ready for pipeline: {summary['ready_for_pipeline']}",
            f"Ready for XML: {summary['ready_for_xml']}",
            f"Ready for Premiere: {summary['ready_for_premiere']}",
            "",
            "Modules:",
        ]

        for item in report["checks"]["modules"]:
            status = "OK" if item["ok"] else "MISSING/ERROR"
            lines.append(f"- {status} | {item['module_no']} | {item['label']} | {item['module']}")
            if item.get("error"):
                lines.append(f"  Error: {item['error']}")

        lines += ["", "Scripts:"]
        for item in report["checks"]["scripts"]:
            status = "OK" if item["exists"] else "MISSING"
            lines.append(f"- {status} | {item['path']}")

        lines += ["", "Project files:"]
        for item in report["checks"]["project_files"]:
            status = "OK" if item["exists"] else "missing"
            lines.append(f"- {status} | {item['path']}")

        lines += ["", "Premiere pointer:"]
        pointer = report["checks"]["premiere_pointer"]
        lines.append(f"- pointer txt: {pointer['pointer_txt_exists']} | {pointer['pointer_txt']}")
        lines.append(f"- XML exists: {pointer['xml_exists']} | {pointer['xml_from_pointer']}")

        lines += ["", "Recommended next commands:"]
        for cmd in report["recommended_next_commands"]:
            lines.append(f"- {cmd}")

        return "\n".join(lines)

    @staticmethod
    def render_html(report: dict[str, Any]) -> str:
        import html

        summary = report["summary"]

        def badge(ok: bool) -> str:
            return "<span class='ok'>OK</span>" if ok else "<span class='bad'>NO</span>"

        module_rows = []
        for item in report["checks"]["modules"]:
            module_rows.append(
                "<tr>"
                f"<td>{html.escape(item['module_no'])}</td>"
                f"<td>{html.escape(item['label'])}</td>"
                f"<td>{badge(bool(item['ok']))}</td>"
                f"<td>{html.escape(item.get('error') or '')}</td>"
                "</tr>"
            )

        script_rows = []
        for item in report["checks"]["scripts"]:
            script_rows.append(
                "<tr>"
                f"<td>{badge(bool(item['exists']))}</td>"
                f"<td>{html.escape(item['path'])}</td>"
                "</tr>"
            )

        file_rows = []
        for item in report["checks"]["project_files"]:
            file_rows.append(
                "<tr>"
                f"<td>{badge(bool(item['exists']))}</td>"
                f"<td>{html.escape(item['path'])}</td>"
                f"<td>{html.escape(str(item.get('modified') or ''))}</td>"
                "</tr>"
            )

        commands = "".join(f"<li><code>{html.escape(str(cmd))}</code></li>" for cmd in report["recommended_next_commands"])

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT Prewedding Pipeline Doctor</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1300px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
.ok {{ color: #9f9; font-weight: 700; }}
.bad {{ color: #f99; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
th, td {{ border-bottom: 1px solid #333; padding: 8px; vertical-align: top; text-align: left; }}
code {{ background:#000; padding:4px 8px; border-radius:8px; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 052</div>
  <h1>Prewedding Pipeline Doctor</h1>
  <p>Ready for pipeline: {badge(bool(summary['ready_for_pipeline']))}</p>
  <p>Ready for XML: {badge(bool(summary['ready_for_xml']))}</p>
  <p>Ready for Premiere: {badge(bool(summary['ready_for_premiere']))}</p>

  <h2>Modules</h2>
  <table>
    <tr><th>#</th><th>Label</th><th>Status</th><th>Error</th></tr>
    {''.join(module_rows)}
  </table>

  <h2>Scripts</h2>
  <table>
    <tr><th>Status</th><th>Path</th></tr>
    {''.join(script_rows)}
  </table>

  <h2>Project files</h2>
  <table>
    <tr><th>Status</th><th>File</th><th>Modified</th></tr>
    {''.join(file_rows)}
  </table>

  <h2>Recommended next commands</h2>
  <ol>{commands}</ol>
</div>
</body>
</html>
'''


def check_prewedding_pipeline(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    repo_root: str | Path | None = None,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PreweddingPipelineDoctor(project_root=project_root, repo_root=repo_root).check(open_folder=open_folder)
