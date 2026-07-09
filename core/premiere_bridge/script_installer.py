
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
class PremiereScriptInstallerConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    xml_path: str | None = None
    install_to_premiere: bool = True
    open_folder: bool = True


class PremiereScriptInstaller:
    # Module 040.
    # Installs a stable Premiere JSX script that reads the latest XML path from:
    #   %APPDATA%/STT_AI_Editor/premiere_latest_xml.txt
    #
    # This means:
    # - STT AI Editor updates the latest XML path.
    # - The Premiere menu script can stay installed.
    # - User runs it from Premiere: File > Scripts > STT_Import_Latest_XML

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()
        self.latest_xml_pointer = self.appdata_dir / "premiere_latest_xml.txt"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"

        return base / "STT_AI_Editor"

    def install(
        self,
        xml_path: str | Path | None = None,
        install_to_premiere: bool = True,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        xml = Path(xml_path) if xml_path else PremiereBridgeExporter(self.project_root).find_latest_xml()

        if not xml or not xml.exists():
            raise FileNotFoundError(
                "Không tìm thấy XML mới nhất.\n"
                "Hãy bấm Export Latest Manual XML hoặc Premiere Bridge Package trước."
            )

        self.appdata_dir.mkdir(parents=True, exist_ok=True)
        self.latest_xml_pointer.write_text(str(xml), encoding="utf-8")

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.exports_dir / f"premiere_script_installer_{stamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        jsx_path = out_dir / "STT_Import_Latest_XML.jsx"
        jsx_path.write_text(self.render_stable_import_jsx(), encoding="utf-8")

        open_folder_jsx = out_dir / "STT_Open_Latest_XML_Folder.jsx"
        open_folder_jsx.write_text(self.render_open_latest_xml_folder_jsx(), encoding="utf-8")

        readme_path = out_dir / "README_PREMIERE_SCRIPT_INSTALL.txt"
        readme_path.write_text(self.render_readme(xml, jsx_path), encoding="utf-8")

        install_bat = out_dir / "INSTALL_TO_PREMIERE_MENU.bat"
        install_bat.write_text(self.render_install_bat(jsx_path, open_folder_jsx), encoding="utf-8")

        update_pointer_bat = out_dir / "Update_Latest_XML_Path.bat"
        update_pointer_bat.write_text(
            f'@echo off\n'
            f'if not exist "%APPDATA%\\STT_AI_Editor" mkdir "%APPDATA%\\STT_AI_Editor"\n'
            f'echo {xml}> "%APPDATA%\\STT_AI_Editor\\premiere_latest_xml.txt"\n'
            f'echo Latest XML path updated:\n'
            f'type "%APPDATA%\\STT_AI_Editor\\premiere_latest_xml.txt"\n'
            f'pause\n',
            encoding="utf-8",
        )

        copy_xml_path_bat = out_dir / "Copy_Latest_XML_Path_To_Clipboard.bat"
        copy_xml_path_bat.write_text(
            f'@echo off\necho {xml} | clip\necho XML path copied:\necho {xml}\npause\n',
            encoding="utf-8",
        )

        copy_jsx_path_bat = out_dir / "Copy_JSX_Path_To_Clipboard.bat"
        copy_jsx_path_bat.write_text(
            f'@echo off\necho {jsx_path} | clip\necho JSX path copied:\necho {jsx_path}\npause\n',
            encoding="utf-8",
        )

        installed_results: list[dict[str, Any]] = []
        safe_scripts_folder = Path.home() / "Documents" / "STT AI Editor" / "Premiere Scripts"
        safe_scripts_folder.mkdir(parents=True, exist_ok=True)

        for src in [jsx_path, open_folder_jsx]:
            dst = safe_scripts_folder / src.name
            shutil.copy2(src, dst)
            installed_results.append(
                {
                    "target_folder": str(safe_scripts_folder),
                    "target_file": str(dst),
                    "ok": True,
                    "safe_copy": True,
                }
            )

        if install_to_premiere:
            for folder in self.find_premiere_script_folders():
                for src in [jsx_path, open_folder_jsx]:
                    try:
                        folder.mkdir(parents=True, exist_ok=True)
                        dst = folder / src.name
                        shutil.copy2(src, dst)
                        installed_results.append(
                            {
                                "target_folder": str(folder),
                                "target_file": str(dst),
                                "ok": True,
                                "safe_copy": False,
                            }
                        )
                    except Exception as exc:
                        installed_results.append(
                            {
                                "target_folder": str(folder),
                                "target_file": str(folder / src.name),
                                "ok": False,
                                "error": repr(exc),
                                "hint": "Nếu folder nằm trong Program Files, chạy INSTALL_TO_PREMIERE_MENU.bat bằng Run as Administrator.",
                            }
                        )

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "module": "040_premiere_script_installer",
            "project_root": str(self.project_root),
            "xml": str(xml),
            "appdata_dir": str(self.appdata_dir),
            "latest_xml_pointer": str(self.latest_xml_pointer),
            "package_dir": str(out_dir),
            "jsx_import": str(jsx_path),
            "jsx_open_folder": str(open_folder_jsx),
            "install_results": installed_results,
            "premiere_script_folders_detected": [str(p) for p in self.find_premiere_script_folders()],
            "safe_scripts_folder": str(safe_scripts_folder),
            "usage": "Restart Premiere > File > Scripts > STT_Import_Latest_XML",
        }

        manifest_path = out_dir / "premiere_script_installer_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        result = {
            "ok": True,
            "project_root": str(self.project_root),
            "xml": str(xml),
            "package_dir": str(out_dir),
            "appdata_dir": str(self.appdata_dir),
            "latest_xml_pointer": str(self.latest_xml_pointer),
            "jsx_import": str(jsx_path),
            "jsx_open_folder": str(open_folder_jsx),
            "readme": str(readme_path),
            "install_bat": str(install_bat),
            "manifest": str(manifest_path),
            "install_results": installed_results,
        }

        (out_dir / "premiere_script_installer_result.json").write_text(
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
    def find_premiere_script_folders() -> list[Path]:
        targets: list[Path] = []

        program_dirs = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]

        for root_text in program_dirs:
            if not root_text:
                continue

            adobe_root = Path(root_text) / "Adobe"
            if not adobe_root.exists():
                continue

            for app_dir in adobe_root.glob("Adobe Premiere Pro*"):
                if app_dir.is_dir():
                    targets.append(app_dir / "Scripts")

        unique: list[Path] = []
        seen: set[str] = set()
        for p in targets:
            key = str(p).lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return unique

    def render_readme(self, xml: Path, jsx_path: Path) -> str:
        return "\n".join(
            [
                "STT AI Editor - Premiere Script Installer",
                "=" * 72,
                "",
                "MỤC TIÊU:",
                "",
                "Cài script STT vào menu Premiere để gần giống tích hợp trực tiếp hơn.",
                "",
                "SAU KHI CÀI:",
                "",
                "1. Restart Premiere Pro.",
                "2. Mở project Premiere cần dựng.",
                "3. Vào File > Scripts.",
                "4. Chọn:",
                "",
                "   STT_Import_Latest_XML",
                "",
                "Script sẽ đọc XML mới nhất từ:",
                "",
                f"   {self.latest_xml_pointer}",
                "",
                "XML hiện tại:",
                "",
                f"   {xml}",
                "",
                "NẾU KHÔNG THẤY SCRIPT TRONG MENU:",
                "",
                "Cách 1:",
                "Premiere > File > Scripts > Run Script File",
                "Chọn file:",
                "",
                f"   {jsx_path}",
                "",
                "Cách 2:",
                "Chạy INSTALL_TO_PREMIERE_MENU.bat bằng Run as Administrator.",
                "",
                "LƯU Ý QUAN TRỌNG:",
                "",
                "- Đây vẫn chưa phải panel/plugin thật.",
                "- Nhưng đây là mức tích hợp tốt hơn JSX helper 039.",
                "- Mỗi lần STT AI Editor export XML mới, app sẽ update file premiere_latest_xml.txt.",
                "- Script trong Premiere không cần thay đổi nếu file pointer đã được update.",
                "",
                "NẾU SCRIPT KHÔNG IMPORT ĐƯỢC:",
                "",
                "Dùng cách ổn định:",
                "Premiere Pro > File > Import > chọn XML.",
                "",
            ]
        )

    @staticmethod
    def render_stable_import_jsx() -> str:
        return r'''/*
STT AI Editor - Import Latest XML
Module 040 Premiere Script Installer

This script reads latest XML path from:
Folder.userData/STT_AI_Editor/premiere_latest_xml.txt

Windows usually maps Folder.userData to:
%APPDATA%
*/

(function () {
    function sttAlert(text) {
        alert("[STT AI Editor]\n\n" + text);
    }

    function trimText(s) {
        return String(s).replace(/^\s+|\s+$/g, "");
    }

    var pointerPath = Folder.userData.fsName + "/STT_AI_Editor/premiere_latest_xml.txt";
    var pointerFile = new File(pointerPath);

    if (!pointerFile.exists) {
        sttAlert(
            "Không thấy file latest XML pointer:\n" + pointerPath + "\n\n" +
            "Hãy mở STT AI Editor và chạy Premiere Script Installer lại."
        );
        return;
    }

    if (!pointerFile.open("r")) {
        sttAlert("Không đọc được:\n" + pointerPath);
        return;
    }

    var xmlPath = trimText(pointerFile.read());
    pointerFile.close();

    if (!xmlPath) {
        sttAlert("File pointer rỗng:\n" + pointerPath);
        return;
    }

    var xmlFile = new File(xmlPath);

    if (!xmlFile.exists) {
        sttAlert(
            "Không thấy XML:\n" + xmlPath + "\n\n" +
            "Hãy Export Latest Manual XML lại trong STT AI Editor."
        );
        return;
    }

    try {
        if (!app.project) {
            app.newProject();
        }

        app.project.importFiles(
            [xmlFile.fsName],
            false,
            app.project.rootItem,
            false
        );

        sttAlert(
            "Đã gửi lệnh import XML vào Premiere.\n\n" +
            "XML:\n" + xmlFile.fsName + "\n\n" +
            "Nếu chưa thấy sequence, kiểm tra Project panel hoặc dùng File > Import thủ công."
        );
    } catch (e) {
        sttAlert(
            "Premiere không import XML tự động được qua script này.\n\n" +
            "Dùng cách thủ công:\n" +
            "File > Import > " + xmlFile.fsName + "\n\n" +
            "Lỗi:\n" + e
        );
    }
})();
'''

    @staticmethod
    def render_open_latest_xml_folder_jsx() -> str:
        return r'''/*
STT AI Editor - Open Latest XML Folder
Module 040
*/

(function () {
    function sttAlert(text) {
        alert("[STT AI Editor]\n\n" + text);
    }

    function trimText(s) {
        return String(s).replace(/^\s+|\s+$/g, "");
    }

    var pointerPath = Folder.userData.fsName + "/STT_AI_Editor/premiere_latest_xml.txt";
    var pointerFile = new File(pointerPath);

    if (!pointerFile.exists) {
        sttAlert("Không thấy latest XML pointer:\n" + pointerPath);
        return;
    }

    if (!pointerFile.open("r")) {
        sttAlert("Không đọc được:\n" + pointerPath);
        return;
    }

    var xmlPath = trimText(pointerFile.read());
    pointerFile.close();

    var xmlFile = new File(xmlPath);
    if (!xmlFile.exists) {
        sttAlert("Không thấy XML:\n" + xmlPath);
        return;
    }

    try {
        xmlFile.parent.execute();
    } catch (e) {
        sttAlert("Không mở được folder:\n" + xmlFile.parent.fsName + "\n\n" + e);
    }
})();
'''

    @staticmethod
    def render_install_bat(import_jsx: Path, open_folder_jsx: Path) -> str:
        return f'''@echo off
setlocal enabledelayedexpansion

echo ========================================
echo STT AI Editor - Install Premiere Menu Scripts
echo ========================================
echo.

set "IMPORT_JSX={import_jsx}"
set "OPEN_JSX={open_folder_jsx}"

if not exist "%IMPORT_JSX%" (
  echo ERROR: Missing:
  echo %IMPORT_JSX%
  pause
  exit /b 1
)

if not exist "%OPEN_JSX%" (
  echo ERROR: Missing:
  echo %OPEN_JSX%
  pause
  exit /b 1
)

set "INSTALLED=0"

for /d %%D in ("%ProgramFiles%\\Adobe\\Adobe Premiere Pro*") do (
  if exist "%%D" (
    echo Found Premiere:
    echo %%D

    if not exist "%%D\\Scripts" (
      mkdir "%%D\\Scripts" 2>nul
    )

    copy /Y "%IMPORT_JSX%" "%%D\\Scripts\\STT_Import_Latest_XML.jsx"
    if !errorlevel! EQU 0 (
      echo Installed: %%D\\Scripts\\STT_Import_Latest_XML.jsx
      set "INSTALLED=1"
    ) else (
      echo FAILED. Try Run as Administrator.
    )

    copy /Y "%OPEN_JSX%" "%%D\\Scripts\\STT_Open_Latest_XML_Folder.jsx"
    if !errorlevel! EQU 0 (
      echo Installed: %%D\\Scripts\\STT_Open_Latest_XML_Folder.jsx
      set "INSTALLED=1"
    ) else (
      echo FAILED. Try Run as Administrator.
    )

    echo.
  )
)

set "SAFE=%USERPROFILE%\\Documents\\STT AI Editor\\Premiere Scripts"
if not exist "%SAFE%" mkdir "%SAFE%"
copy /Y "%IMPORT_JSX%" "%SAFE%\\STT_Import_Latest_XML.jsx" >nul
copy /Y "%OPEN_JSX%" "%SAFE%\\STT_Open_Latest_XML_Folder.jsx" >nul

echo Safe copies:
echo %SAFE%\\STT_Import_Latest_XML.jsx
echo %SAFE%\\STT_Open_Latest_XML_Folder.jsx
echo.

if "%INSTALLED%"=="1" (
  echo Done. Restart Premiere, then open File ^> Scripts.
) else (
  echo Could not install to Premiere Program Files automatically.
  echo Run this BAT as Administrator, or use:
  echo Premiere ^> File ^> Scripts ^> Run Script File
  echo and choose the safe copy in Documents.
)

echo.
pause
'''


def install_premiere_script(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    xml_path: str | Path | None = None,
    install_to_premiere: bool = True,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PremiereScriptInstaller(project_root=project_root).install(
        xml_path=xml_path,
        install_to_premiere=install_to_premiere,
        open_folder=open_folder,
    )
