
from __future__ import annotations

import html
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .validator import PremiereXMLValidator


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


@dataclass
class PremiereBridgeConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    xml_path: str | None = None
    open_folder: bool = True


class PremiereBridgeExporter:
    # Module 038 enhances Module 037.
    # Creates a clean Premiere import package + XML validation report.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"

    def find_latest_xml(self) -> Path | None:
        if not self.exports_dir.exists():
            return None

        preferred = [
            p for p in self.exports_dir.glob("**/stt_ai_premiere_import.xml")
            if p.is_file() and "_archive" not in p.parts
        ]

        if preferred:
            return sorted(preferred, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        named = [
            p for p in self.exports_dir.glob("**/01_STT_AI_Premiere_Import.xml")
            if p.is_file() and "_archive" not in p.parts
        ]

        if named:
            return sorted(named, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        fallback = [
            p for p in self.exports_dir.glob("**/*.xml")
            if p.is_file() and "_archive" not in p.parts
        ]

        if fallback:
            return sorted(fallback, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        return None

    def create_package(self, xml_path: str | Path | None = None, open_folder: bool = True) -> dict[str, Any]:
        xml = Path(xml_path) if xml_path else self.find_latest_xml()

        if not xml or not xml.exists():
            raise FileNotFoundError(
                "Không tìm thấy XML để import Premiere.\n"
                "Hãy bấm 'Export Latest Manual XML' trước, rồi chạy Premiere Bridge lại."
            )

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.exports_dir / f"premiere_bridge_{stamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        target_xml = out_dir / "01_STT_AI_Premiere_Import.xml"
        shutil.copy2(xml, target_xml)

        validator = PremiereXMLValidator(target_xml)
        validation = validator.validate()
        validation_reports = validator.write_reports(out_dir)

        manifest = self._create_manifest(
            original_xml=xml,
            target_xml=target_xml,
            out_dir=out_dir,
            validation=validation,
            validation_reports=validation_reports,
        )

        manifest_path = out_dir / "premiere_bridge_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        readme_path = out_dir / "README_IMPORT_PREMIERE.txt"
        readme_path.write_text(self._render_readme(manifest), encoding="utf-8")

        html_path = out_dir / "PREMIERE_IMPORT_STEPS.html"
        html_path.write_text(self._render_html(manifest), encoding="utf-8")

        jsx_path = out_dir / "premiere_import_helper.jsx"
        jsx_path.write_text(self._render_jsx(target_xml), encoding="utf-8")

        open_bat = out_dir / "Open_This_Folder.bat"
        open_bat.write_text(f'@echo off\nstart "" "{out_dir}"\n', encoding="utf-8")

        copy_path_bat = out_dir / "Copy_XML_Path_To_Clipboard.bat"
        copy_path_bat.write_text(
            f'@echo off\necho {target_xml} | clip\necho XML path copied:\necho {target_xml}\npause\n',
            encoding="utf-8",
        )

        result = {
            "ok": True,
            "project_root": str(self.project_root),
            "source_xml": str(xml),
            "package_dir": str(out_dir),
            "xml": str(target_xml),
            "readme": str(readme_path),
            "html": str(html_path),
            "jsx": str(jsx_path),
            "manifest": str(manifest_path),
            "validation_status": validation.get("status"),
            "validation_json": validation_reports.get("json"),
            "validation_html": validation_reports.get("html"),
            "validation_txt": validation_reports.get("txt"),
        }

        result_path = out_dir / "premiere_bridge_result.json"
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        if open_folder:
            try:
                os.startfile(out_dir)
            except Exception:
                pass

        return result

    def _create_manifest(
        self,
        original_xml: Path,
        target_xml: Path,
        out_dir: Path,
        validation: dict[str, Any],
        validation_reports: dict[str, str],
    ) -> dict[str, Any]:
        manual_selection = self.project_root / "manual_selection.json"
        feedback_profile = self.project_root / "stt_feedback_profile.json"
        xml_settings = self.project_root / "stt_xml_export_settings.json"
        workflow_preset = self.project_root / "stt_workflow_preset.json"

        manifest: dict[str, Any] = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "module": "038_premiere_bridge_validator",
            "project_root": str(self.project_root),
            "package_dir": str(out_dir),
            "original_xml": str(original_xml),
            "premiere_xml": str(target_xml),
            "xml_size_bytes": target_xml.stat().st_size if target_xml.exists() else 0,
            "validation_status": validation.get("status"),
            "validation_ok": validation.get("ok"),
            "validation_errors": validation.get("errors", []),
            "validation_warnings": validation.get("warnings", []),
            "validation_reports": validation_reports,
            "audio_note": "XML hiện dùng audio dual mono an toàn: A1 = Left, A2 = Right.",
            "premiere_import_method": "Premiere Pro > File > Import > chọn 01_STT_AI_Premiere_Import.xml",
            "optional_files": {},
        }

        for label, path in [
            ("manual_selection", manual_selection),
            ("feedback_profile", feedback_profile),
            ("xml_settings", xml_settings),
            ("workflow_preset", workflow_preset),
        ]:
            if path.exists() and path.is_file():
                manifest["optional_files"][label] = str(path)
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if label == "manual_selection":
                        items = data.get("items", [])
                        manifest["manual_selection_count"] = len(items) if isinstance(items, list) else None
                    if label == "xml_settings":
                        manifest["xml_settings"] = data
                    if label == "workflow_preset":
                        manifest["workflow_preset"] = data
                except Exception:
                    pass

        return manifest

    @staticmethod
    def _render_readme(manifest: dict[str, Any]) -> str:
        xml = manifest["premiere_xml"]
        status = str(manifest.get("validation_status", "unknown")).upper()

        lines = [
            "STT AI Editor - Premiere Bridge Package",
            "=" * 72,
            "",
            f"XML VALIDATION STATUS: {status}",
            "",
        ]

        errors = manifest.get("validation_errors") or []
        warnings = manifest.get("validation_warnings") or []

        if errors:
            lines += ["ERRORS:"]
            lines += [f"- {x}" for x in errors]
            lines += [""]

        if warnings:
            lines += ["WARNINGS:"]
            lines += [f"- {x}" for x in warnings]
            lines += [""]

        lines += [
            "IMPORT VÀO PREMIERE:",
            "",
            "1. Mở Premiere Pro.",
            "2. Mở project Premiere cần dựng.",
            "3. Vào File > Import.",
            "4. Chọn file:",
            "",
            f"   {xml}",
            "",
            "5. Premiere sẽ tạo sequence rough cut từ STT AI Editor.",
            "",
            "LƯU Ý AUDIO:",
            "",
            "- XML đang giữ kiểu audio an toàn:",
            "  A1 = Left",
            "  A2 = Right",
            "- Đừng dùng lại bản fix stereo single cũ vì bản đó từng mất kênh R.",
            "",
            "FILE TRONG FOLDER NÀY:",
            "",
            "- 01_STT_AI_Premiere_Import.xml: file chính để import Premiere.",
            "- XML_VALIDATION_REPORT.html/txt/json: report kiểm tra XML trước khi import.",
            "- PREMIERE_IMPORT_STEPS.html: hướng dẫn import dạng đẹp hơn.",
            "- premiere_import_helper.jsx: script thử nghiệm.",
            "- Copy_XML_Path_To_Clipboard.bat: copy đường dẫn XML.",
            "- premiere_bridge_manifest.json: thông tin package.",
            "",
            "KHUYẾN NGHỊ:",
            "",
            "Cách ổn định nhất hiện tại vẫn là File > Import XML thủ công trong Premiere.",
            "JSX chỉ là helper thử nghiệm vì Premiere có thể giới hạn import XML tự động tùy phiên bản.",
            "",
        ]

        return "\n".join(lines)

    @staticmethod
    def _render_html(manifest: dict[str, Any]) -> str:
        xml = html.escape(manifest["premiere_xml"])
        package_dir = html.escape(manifest["package_dir"])
        source_xml = html.escape(manifest["original_xml"])
        audio_note = html.escape(manifest.get("audio_note", ""))
        status = html.escape(str(manifest.get("validation_status", "unknown")).upper())

        errors = manifest.get("validation_errors") or []
        warnings = manifest.get("validation_warnings") or []

        def li(items: list[str]) -> str:
            if not items:
                return "<li>None</li>"
            return "\n".join(f"<li>{html.escape(str(x))}</li>" for x in items)

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT AI Editor - Premiere Bridge</title>
<style>
body {{
  font-family: Arial, sans-serif;
  margin: 32px;
  line-height: 1.55;
  background: #111;
  color: #eee;
}}
.card {{
  max-width: 980px;
  border: 1px solid #333;
  border-radius: 16px;
  padding: 24px;
  background: #181818;
}}
h1 {{ margin-top: 0; }}
code {{
  display: block;
  background: #000;
  border: 1px solid #333;
  padding: 12px;
  border-radius: 10px;
  overflow-wrap: anywhere;
}}
.step {{
  padding: 12px 0;
  border-bottom: 1px solid #292929;
}}
.badge {{
  display: inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #555;
  margin-bottom: 12px;
  font-weight: 700;
}}
</style>
</head>
<body>
<div class="card">
  <div class="badge">XML VALIDATION: {status}</div>
  <h1>STT AI Editor → Premiere Bridge</h1>

  <p>Import file XML này vào Premiere:</p>
  <code>{xml}</code>

  <h2>Validation warnings</h2>
  <ul>{li(warnings)}</ul>

  <h2>Validation errors</h2>
  <ul>{li(errors)}</ul>

  <div class="step"><b>1.</b> Mở Premiere Pro.</div>
  <div class="step"><b>2.</b> Mở project Premiere cần dựng.</div>
  <div class="step"><b>3.</b> Chọn <b>File &gt; Import</b>.</div>
  <div class="step"><b>4.</b> Chọn file <b>01_STT_AI_Premiere_Import.xml</b>.</div>
  <div class="step"><b>5.</b> Premiere sẽ tạo sequence rough cut.</div>

  <h2>Audio</h2>
  <p>{audio_note}</p>

  <h2>Package folder</h2>
  <code>{package_dir}</code>

  <h2>Source XML gốc</h2>
  <code>{source_xml}</code>

  <p><b>Lưu ý:</b> JSX helper chỉ là thử nghiệm. Cách chắc nhất hiện tại vẫn là import XML thủ công.</p>
</div>
</body>
</html>
'''

    @staticmethod
    def _render_jsx(xml_path: Path) -> str:
        xml_js_path = str(xml_path).replace("\\", "/").replace('"', '\\"')

        return f'''/*
STT AI Editor - Premiere Import Helper
Module 038

Premiere Pro > File > Scripts > Run Script File
Chọn file này.

Nếu không import được, dùng File > Import thủ công:
{xml_js_path}
*/

(function () {{
    var xmlPath = "{xml_js_path}";
    var f = new File(xmlPath);

    if (!f.exists) {{
        alert("Không thấy XML:\\n" + xmlPath);
        return;
    }}

    try {{
        if (!app.project) {{
            app.newProject();
        }}

        app.project.importFiles([f.fsName], false, app.project.rootItem, false);

        alert(
            "Đã gửi lệnh import XML vào Premiere.\\n\\n" +
            "Nếu Premiere không tạo sequence, hãy import thủ công:\\n" +
            "File > Import > " + f.fsName
        );
    }} catch (e) {{
        alert(
            "Premiere không import XML tự động được qua script này.\\n\\n" +
            "Hãy import thủ công:\\n" +
            "File > Import > " + f.fsName + "\\n\\n" +
            "Lỗi: " + e
        );
    }}
}})();
'''


def export_premiere_bridge(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    xml_path: str | Path | None = None,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PremiereBridgeExporter(project_root=project_root).create_package(
        xml_path=xml_path,
        open_folder=open_folder,
    )
