
from __future__ import annotations

import html
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .pointer import update_premiere_xml_pointer

try:
    from .validator import PremiereXMLValidator
except Exception:
    PremiereXMLValidator = None  # type: ignore


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


@dataclass
class PremiereBridgeConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    xml_path: str | None = None
    open_folder: bool = True


class PremiereBridgeExporter:
    # Module 042: bridge auto-updates Premiere latest XML pointer.

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

        validation: dict[str, Any] = {}
        validation_reports: dict[str, str] = {}

        if PremiereXMLValidator is not None:
            try:
                validator = PremiereXMLValidator(target_xml)
                validation = validator.validate()
                validation_reports = validator.write_reports(out_dir)
            except Exception as exc:
                validation = {"status": "validator_error", "error": repr(exc)}

        pointer = update_premiere_xml_pointer(
            project_root=self.project_root,
            xml_path=target_xml,
            source="module_042_premiere_bridge",
        )

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "module": "042_premiere_bridge_auto_pointer",
            "project_root": str(self.project_root),
            "package_dir": str(out_dir),
            "original_xml": str(xml),
            "premiere_xml": str(target_xml),
            "premiere_pointer": pointer,
            "validation": validation,
            "validation_reports": validation_reports,
            "audio_note": "XML hiện dùng audio dual mono an toàn: A1 = Left, A2 = Right.",
            "premiere_import_method": "Premiere Pro > File > Import > chọn 01_STT_AI_Premiere_Import.xml",
        }

        manifest_path = out_dir / "premiere_bridge_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        readme_path = out_dir / "README_IMPORT_PREMIERE.txt"
        readme_path.write_text(self._render_readme(manifest), encoding="utf-8")

        html_path = out_dir / "PREMIERE_IMPORT_STEPS.html"
        html_path.write_text(self._render_html(manifest), encoding="utf-8")

        jsx_path = out_dir / "premiere_import_helper.jsx"
        jsx_path.write_text(self._render_jsx(target_xml), encoding="utf-8")

        (out_dir / "Open_This_Folder.bat").write_text(f'@echo off\nstart "" "{out_dir}"\n', encoding="utf-8")
        (out_dir / "Copy_XML_Path_To_Clipboard.bat").write_text(
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
            "premiere_pointer": pointer,
        }

        (out_dir / "premiere_bridge_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(out_dir)
            except Exception:
                pass

        return result

    @staticmethod
    def _render_readme(manifest: dict[str, Any]) -> str:
        xml = manifest["premiere_xml"]
        status = str((manifest.get("validation") or {}).get("status", "unknown")).upper()
        pointer = (manifest.get("premiere_pointer") or {}).get("pointer_txt", "")

        return "\n".join(
            [
                "STT AI Editor - Premiere Bridge Package",
                "=" * 72,
                "",
                f"XML VALIDATION STATUS: {status}",
                "",
                "IMPORT VÀO PREMIERE:",
                "",
                "Premiere Pro > File > Import > chọn file:",
                "",
                f"   {xml}",
                "",
                "PREMIERE PANEL POINTER:",
                "",
                f"   {pointer}",
                "",
                "Panel trong Premiere sẽ đọc pointer này để import XML mới nhất.",
                "",
            ]
        )

    @staticmethod
    def _render_html(manifest: dict[str, Any]) -> str:
        xml = html.escape(manifest["premiere_xml"])
        pointer = html.escape(str((manifest.get("premiere_pointer") or {}).get("pointer_txt", "")))
        status = html.escape(str((manifest.get("validation") or {}).get("status", "unknown")).upper())

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT AI Editor - Premiere Bridge</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; background: #111; color: #eee; line-height: 1.55; }}
.card {{ max-width: 980px; border: 1px solid #333; border-radius: 16px; padding: 24px; background: #181818; }}
code {{ display: block; background: #000; padding: 12px; border-radius: 10px; overflow-wrap: anywhere; }}
.badge {{ display: inline-block; padding: 4px 8px; border-radius: 999px; border: 1px solid #555; font-weight: 700; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">XML VALIDATION: {status}</div>
  <h1>STT AI Editor → Premiere Bridge</h1>
  <p>Import file XML này vào Premiere:</p>
  <code>{xml}</code>
  <h2>Panel pointer</h2>
  <code>{pointer}</code>
  <p>Premiere panel sẽ đọc pointer này để import XML mới nhất.</p>
</div>
</body>
</html>
'''

    @staticmethod
    def _render_jsx(xml_path: Path) -> str:
        xml_js_path = str(xml_path).replace("\\", "/").replace('"', '\\"')
        return f'''(function () {{
    var xmlFile = new File("{xml_js_path}");
    if (!xmlFile.exists) {{
        alert("Không thấy XML:\\n" + xmlFile.fsName);
        return;
    }}
    try {{
        if (!app.project) app.newProject();
        app.project.importFiles([xmlFile.fsName], false, app.project.rootItem, false);
        alert("Đã gửi lệnh import XML vào Premiere.");
    }} catch (e) {{
        alert("Import lỗi. Dùng File > Import thủ công.\\n\\n" + e);
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
