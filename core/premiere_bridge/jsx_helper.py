
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .bridge import PremiereBridgeExporter


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


@dataclass
class PremiereJSXHelperConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    xml_path: str | None = None
    open_folder: bool = True


class PremiereJSXHelper:
    # Module 039.
    # Creates a cleaner Premiere JSX helper package.
    #
    # This still is not a full Premiere plugin/panel.
    # It is the next safe step:
    # - generate a ready-to-run JSX
    # - generate instructions
    # - optionally copy JSX into common Premiere Scripts folders if found

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"

    def create_package(
        self,
        xml_path: str | Path | None = None,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        xml = Path(xml_path) if xml_path else PremiereBridgeExporter(self.project_root).find_latest_xml()

        if not xml or not xml.exists():
            raise FileNotFoundError(
                "Không tìm thấy XML.\n"
                "Hãy bấm Export Latest Manual XML hoặc Premiere Bridge Package trước."
            )

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.exports_dir / f"premiere_jsx_helper_{stamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        main_jsx = out_dir / "STT_Import_Latest_XML.jsx"
        main_jsx.write_text(self._render_jsx(xml), encoding="utf-8")

        readme = out_dir / "README_RUN_IN_PREMIERE.txt"
        readme.write_text(self._render_readme(xml, main_jsx), encoding="utf-8")

        bat_copy = out_dir / "Copy_JSX_Path_To_Clipboard.bat"
        bat_copy.write_text(
            f'@echo off\necho {main_jsx} | clip\necho JSX path copied:\necho {main_jsx}\npause\n',
            encoding="utf-8",
        )

        bat_open = out_dir / "Open_This_Folder.bat"
        bat_open.write_text(f'@echo off\nstart "" "{out_dir}"\n', encoding="utf-8")

        install_script = out_dir / "INSTALL_TO_PREMIERE_SCRIPTS_FOLDER.bat"
        install_script.write_text(self._render_install_bat(main_jsx), encoding="utf-8")

        possible_targets = self.find_possible_premiere_script_folders()

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "module": "039_premiere_jsx_helper",
            "project_root": str(self.project_root),
            "xml": str(xml),
            "package_dir": str(out_dir),
            "jsx": str(main_jsx),
            "possible_premiere_script_folders": [str(p) for p in possible_targets],
            "note": (
                "Cách ổn định nhất vẫn là Premiere > File > Scripts > Run Script File. "
                "Nếu copy vào Scripts folder thì có thể cần Run as Administrator."
            ),
        }

        manifest_path = out_dir / "premiere_jsx_helper_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        result = {
            "ok": True,
            "package_dir": str(out_dir),
            "xml": str(xml),
            "jsx": str(main_jsx),
            "readme": str(readme),
            "manifest": str(manifest_path),
            "possible_premiere_script_folders": [str(p) for p in possible_targets],
        }

        (out_dir / "premiere_jsx_helper_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(out_dir)
            except Exception:
                pass

        return result

    def copy_to_premiere_scripts_folder(
        self,
        jsx_path: str | Path,
        target_folder: str | Path,
    ) -> dict[str, Any]:
        src = Path(jsx_path)
        dst_dir = Path(target_folder)

        if not src.exists():
            raise FileNotFoundError(f"Không thấy JSX: {src}")

        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name
        shutil.copy2(src, dst)

        return {
            "ok": True,
            "source": str(src),
            "target": str(dst),
        }

    @staticmethod
    def find_possible_premiere_script_folders() -> list[Path]:
        targets: list[Path] = []

        program_files = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]

        for base in program_files:
            if not base:
                continue

            root = Path(base) / "Adobe"
            if not root.exists():
                continue

            for app_dir in root.glob("Adobe Premiere Pro*"):
                if app_dir.is_dir():
                    scripts = app_dir / "Scripts"
                    targets.append(scripts)

        # Also include user's Documents as a safe non-admin destination.
        documents = Path.home() / "Documents" / "STT AI Editor" / "Premiere Scripts"
        targets.append(documents)

        # Unique keep order.
        unique: list[Path] = []
        seen: set[str] = set()
        for p in targets:
            key = str(p).lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return unique

    @staticmethod
    def _render_readme(xml_path: Path, jsx_path: Path) -> str:
        return "\n".join(
            [
                "STT AI Editor - Premiere JSX Helper",
                "=" * 72,
                "",
                "CÁCH DÙNG AN TOÀN NHẤT:",
                "",
                "1. Mở Premiere Pro.",
                "2. Mở project Premiere cần dựng.",
                "3. Vào File > Scripts > Run Script File.",
                "4. Chọn file:",
                "",
                f"   {jsx_path}",
                "",
                "5. Script sẽ cố import XML vào Premiere:",
                "",
                f"   {xml_path}",
                "",
                "NẾU SCRIPT KHÔNG IMPORT ĐƯỢC:",
                "",
                "Dùng cách thủ công:",
                "Premiere Pro > File > Import > chọn XML.",
                "",
                "LƯU Ý:",
                "",
                "- Đây chưa phải Premiere Panel/plugin thật.",
                "- Đây là JSX helper để tiến gần hơn tới tích hợp Premiere.",
                "- Premiere có thể giới hạn import XML bằng script tùy version.",
                "- Cách File > Import XML thủ công vẫn là ổn định nhất hiện tại.",
                "",
                "CÀI VÀO MENU SCRIPTS:",
                "",
                "Có thể thử chạy:",
                "INSTALL_TO_PREMIERE_SCRIPTS_FOLDER.bat",
                "",
                "Nếu copy vào Program Files bị lỗi quyền, chạy .bat bằng Run as Administrator.",
                "",
            ]
        )

    @staticmethod
    def _render_jsx(xml_path: Path) -> str:
        xml_js_path = str(xml_path).replace("\\", "/").replace('"', '\\"')

        return f'''/*
STT AI Editor - Import Latest XML
Module 039 Premiere JSX Helper

Generated for:
{xml_js_path}

Usage:
Premiere Pro > File > Scripts > Run Script File
Choose this JSX file.

If automatic import does not work:
Premiere Pro > File > Import > choose the XML above.
*/

(function () {{
    var xmlPath = "{xml_js_path}";
    var xmlFile = new File(xmlPath);

    function msg(text) {{
        alert("[STT AI Editor]\\n\\n" + text);
    }}

    if (!xmlFile.exists) {{
        msg("Không thấy XML:\\n" + xmlPath);
        return;
    }}

    try {{
        if (!app.project) {{
            app.newProject();
        }}

        var imported = app.project.importFiles(
            [xmlFile.fsName],
            false,
            app.project.rootItem,
            false
        );

        msg(
            "Đã gửi lệnh import XML vào Premiere.\\n\\n" +
            "XML:\\n" + xmlFile.fsName + "\\n\\n" +
            "Nếu Premiere không tạo sequence, hãy dùng File > Import thủ công."
        );
    }} catch (e) {{
        msg(
            "Premiere không import XML tự động được qua JSX này.\\n\\n" +
            "Hãy import thủ công:\\n" +
            "File > Import > " + xmlFile.fsName + "\\n\\n" +
            "Lỗi:\\n" + e
        );
    }}
}})();
'''

    @staticmethod
    def _render_install_bat(jsx_path: Path) -> str:
        # The BAT tries common folders. If Program Files copy fails, it creates safe Documents folder.
        jsx = str(jsx_path)
        return f'''@echo off
setlocal enabledelayedexpansion

echo ========================================
echo STT AI Editor - Install Premiere JSX
echo ========================================
echo.

set "JSX={jsx}"

if not exist "%JSX%" (
  echo ERROR: JSX not found:
  echo %JSX%
  pause
  exit /b 1
)

set "DONE=0"

for /d %%D in ("%ProgramFiles%\\Adobe\\Adobe Premiere Pro*") do (
  if exist "%%D" (
    echo Found Premiere folder:
    echo %%D

    if not exist "%%D\\Scripts" (
      mkdir "%%D\\Scripts" 2>nul
    )

    copy /Y "%JSX%" "%%D\\Scripts\\STT_Import_Latest_XML.jsx"
    if !errorlevel! EQU 0 (
      echo Installed to:
      echo %%D\\Scripts\\STT_Import_Latest_XML.jsx
      set "DONE=1"
    ) else (
      echo Could not copy to Program Files. Try Run as Administrator.
    )
    echo.
  )
)

set "SAFE=%USERPROFILE%\\Documents\\STT AI Editor\\Premiere Scripts"
if not exist "%SAFE%" mkdir "%SAFE%"
copy /Y "%JSX%" "%SAFE%\\STT_Import_Latest_XML.jsx" >nul
echo Safe copy created:
echo %SAFE%\\STT_Import_Latest_XML.jsx

echo.
if "%DONE%"=="1" (
  echo Done. Restart Premiere, then check File > Scripts.
) else (
  echo Program Files install may need Administrator.
  echo You can still use:
  echo Premiere > File > Scripts > Run Script File
  echo and choose the safe copy above.
)

echo.
pause
'''


def create_premiere_jsx_helper(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    xml_path: str | Path | None = None,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PremiereJSXHelper(project_root=project_root).create_package(
        xml_path=xml_path,
        open_folder=open_folder,
    )
