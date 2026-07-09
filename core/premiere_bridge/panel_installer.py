
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
EXTENSION_ID = "com.stt.ai.editor.panel"
EXTENSION_NAME = "STT AI Editor"


@dataclass
class PremierePanelInstallerConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    xml_path: str | None = None
    install_to_user_cep: bool = True
    open_folder: bool = True


class PremierePanelInstaller:
    # Module 041.
    # Creates a CEP Premiere panel starter package.
    #
    # This is the first real Premiere panel step.
    # It creates:
    # - CEP extension folder
    # - manifest.xml
    # - index.html UI
    # - JS bridge using CSInterface
    # - ExtendScript host.jsx
    # - installer BAT to copy into %APPDATA%/Adobe/CEP/extensions
    # - enable debug BAT for unsigned CEP extensions
    #
    # The panel reads the latest XML pointer written by Module 040:
    # %APPDATA%/STT_AI_Editor/premiere_latest_xml.txt

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()
        self.latest_xml_pointer = self.appdata_dir / "premiere_latest_xml.txt"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    @staticmethod
    def get_user_cep_extensions_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Adobe" / "CEP" / "extensions"
        return Path.home() / "AppData" / "Roaming" / "Adobe" / "CEP" / "extensions"

    def create_panel_package(
        self,
        xml_path: str | Path | None = None,
        install_to_user_cep: bool = True,
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
        out_dir = self.exports_dir / f"premiere_panel_starter_{stamp}"
        extension_dir = out_dir / EXTENSION_ID

        self._write_extension_files(extension_dir)

        readme = out_dir / "README_INSTALL_PREMIERE_PANEL.txt"
        readme.write_text(self.render_readme(extension_dir), encoding="utf-8")

        install_bat = out_dir / "INSTALL_PANEL_TO_USER_CEP.bat"
        install_bat.write_text(self.render_install_bat(extension_dir), encoding="utf-8")

        enable_debug_bat = out_dir / "ENABLE_CEP_DEBUG_MODE.bat"
        enable_debug_bat.write_text(self.render_debug_bat(), encoding="utf-8")

        uninstall_bat = out_dir / "UNINSTALL_PANEL_FROM_USER_CEP.bat"
        uninstall_bat.write_text(self.render_uninstall_bat(), encoding="utf-8")

        copy_pointer_bat = out_dir / "Update_Latest_XML_Pointer.bat"
        copy_pointer_bat.write_text(
            f'@echo off\n'
            f'if not exist "%APPDATA%\\STT_AI_Editor" mkdir "%APPDATA%\\STT_AI_Editor"\n'
            f'echo {xml}> "%APPDATA%\\STT_AI_Editor\\premiere_latest_xml.txt"\n'
            f'echo Latest XML pointer updated:\n'
            f'type "%APPDATA%\\STT_AI_Editor\\premiere_latest_xml.txt"\n'
            f'pause\n',
            encoding="utf-8",
        )

        installed_to = None
        install_error = None

        if install_to_user_cep:
            try:
                installed_to = self.install_extension_to_user_cep(extension_dir)
            except Exception as exc:
                install_error = repr(exc)

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "module": "041_premiere_panel_starter",
            "project_root": str(self.project_root),
            "xml": str(xml),
            "latest_xml_pointer": str(self.latest_xml_pointer),
            "package_dir": str(out_dir),
            "extension_id": EXTENSION_ID,
            "extension_dir": str(extension_dir),
            "user_cep_extensions_dir": str(self.get_user_cep_extensions_dir()),
            "installed_to_user_cep": str(installed_to) if installed_to else None,
            "install_error": install_error,
            "premiere_menu_path": "Premiere Pro > Window > Extensions > STT AI Editor",
            "note": "Nếu panel không hiện, chạy ENABLE_CEP_DEBUG_MODE.bat rồi restart Premiere.",
        }

        manifest_path = out_dir / "premiere_panel_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        result = {
            "ok": True,
            "project_root": str(self.project_root),
            "xml": str(xml),
            "latest_xml_pointer": str(self.latest_xml_pointer),
            "package_dir": str(out_dir),
            "extension_dir": str(extension_dir),
            "installed_to_user_cep": str(installed_to) if installed_to else None,
            "install_error": install_error,
            "readme": str(readme),
            "install_bat": str(install_bat),
            "enable_debug_bat": str(enable_debug_bat),
            "uninstall_bat": str(uninstall_bat),
            "manifest": str(manifest_path),
        }

        (out_dir / "premiere_panel_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(out_dir)
            except Exception:
                pass

        return result

    def install_extension_to_user_cep(self, extension_dir: Path) -> Path:
        target_root = self.get_user_cep_extensions_dir()
        target_root.mkdir(parents=True, exist_ok=True)

        target = target_root / EXTENSION_ID
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)

        shutil.copytree(extension_dir, target)
        return target

    def _write_extension_files(self, extension_dir: Path) -> None:
        (extension_dir / "CSXS").mkdir(parents=True, exist_ok=True)
        (extension_dir / "js").mkdir(parents=True, exist_ok=True)
        (extension_dir / "jsx").mkdir(parents=True, exist_ok=True)
        (extension_dir / "css").mkdir(parents=True, exist_ok=True)

        (extension_dir / "CSXS" / "manifest.xml").write_text(self.render_manifest_xml(), encoding="utf-8")
        (extension_dir / "index.html").write_text(self.render_index_html(), encoding="utf-8")
        (extension_dir / "js" / "CSInterface.js").write_text(self.render_csinterface_stub(), encoding="utf-8")
        (extension_dir / "js" / "main.js").write_text(self.render_main_js(), encoding="utf-8")
        (extension_dir / "jsx" / "host.jsx").write_text(self.render_host_jsx(), encoding="utf-8")
        (extension_dir / "css" / "style.css").write_text(self.render_style_css(), encoding="utf-8")
        (extension_dir / ".debug").write_text("CEP debug extension for STT AI Editor\n", encoding="utf-8")

    @staticmethod
    def render_manifest_xml() -> str:
        # Host version range is intentionally broad for Premiere Pro.
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<ExtensionManifest Version="7.0" ExtensionBundleId="{EXTENSION_ID}" ExtensionBundleVersion="1.0.0" ExtensionBundleName="{EXTENSION_NAME}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <ExtensionList>
    <Extension Id="{EXTENSION_ID}" Version="1.0.0" />
  </ExtensionList>
  <ExecutionEnvironment>
    <HostList>
      <Host Name="PPRO" Version="[14.0,99.9]" />
    </HostList>
    <LocaleList>
      <Locale Code="All" />
    </LocaleList>
    <RequiredRuntimeList>
      <RequiredRuntime Name="CSXS" Version="9.0" />
    </RequiredRuntimeList>
  </ExecutionEnvironment>
  <DispatchInfoList>
    <Extension Id="{EXTENSION_ID}">
      <DispatchInfo>
        <Resources>
          <MainPath>./index.html</MainPath>
          <ScriptPath>./jsx/host.jsx</ScriptPath>
          <CEFCommandLine>
            <Parameter>--allow-file-access</Parameter>
            <Parameter>--allow-file-access-from-files</Parameter>
          </CEFCommandLine>
        </Resources>
        <Lifecycle>
          <AutoVisible>true</AutoVisible>
        </Lifecycle>
        <UI>
          <Type>Panel</Type>
          <Menu>{EXTENSION_NAME}</Menu>
          <Geometry>
            <Size>
              <Height>560</Height>
              <Width>380</Width>
            </Size>
            <MinSize>
              <Height>420</Height>
              <Width>320</Width>
            </MinSize>
          </Geometry>
        </UI>
      </DispatchInfo>
    </Extension>
  </DispatchInfoList>
</ExtensionManifest>
'''

    @staticmethod
    def render_index_html() -> str:
        return r'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>STT AI Editor</title>
  <link rel="stylesheet" href="css/style.css">
  <script src="js/CSInterface.js"></script>
  <script src="js/main.js"></script>
</head>
<body>
  <div class="wrap">
    <div class="badge">STT AI Editor</div>
    <h1>Premiere Panel</h1>
    <p class="muted">Module 041 - panel starter</p>

    <button id="btnRefresh">Refresh Latest XML</button>
    <button id="btnImport" class="primary">Import Latest XML</button>
    <button id="btnOpenFolder">Open XML Folder</button>

    <div class="box">
      <div class="label">Latest XML</div>
      <div id="xmlPath" class="path">Loading...</div>
    </div>

    <div class="box">
      <div class="label">Status</div>
      <div id="status">Ready</div>
    </div>

    <p class="hint">
      Nếu Import không tự tạo sequence, dùng Premiere: File &gt; Import và chọn XML.
    </p>
  </div>
</body>
</html>
'''

    @staticmethod
    def render_main_js() -> str:
        return r'''/* STT AI Editor - CEP Panel main.js */

var csInterface = null;

function setText(id, text) {
  var el = document.getElementById(id);
  if (el) el.textContent = text;
}

function evalHost(script, cb) {
  if (!csInterface) {
    setText("status", "CSInterface chưa sẵn sàng.");
    if (cb) cb("");
    return;
  }

  csInterface.evalScript(script, function (res) {
    if (cb) cb(res);
  });
}

function refreshLatestXML() {
  setText("status", "Reading latest XML...");
  evalHost("sttGetLatestXMLPath()", function (res) {
    setText("xmlPath", res || "Không thấy latest XML pointer.");
    setText("status", res ? "Latest XML loaded." : "No XML found.");
  });
}

function importLatestXML() {
  setText("status", "Importing XML...");
  evalHost("sttImportLatestXML()", function (res) {
    setText("status", res || "Done.");
    refreshLatestXML();
  });
}

function openLatestXMLFolder() {
  setText("status", "Opening folder...");
  evalHost("sttOpenLatestXMLFolder()", function (res) {
    setText("status", res || "Done.");
  });
}

window.onload = function () {
  try {
    csInterface = new CSInterface();
  } catch (e) {
    setText("status", "CSInterface lỗi: " + e);
  }

  document.getElementById("btnRefresh").onclick = refreshLatestXML;
  document.getElementById("btnImport").onclick = importLatestXML;
  document.getElementById("btnOpenFolder").onclick = openLatestXMLFolder;

  refreshLatestXML();
};
'''

    @staticmethod
    def render_host_jsx() -> str:
        return r'''/*
STT AI Editor - Premiere CEP Panel host.jsx
Module 041

Reads latest XML pointer:
Folder.userData/STT_AI_Editor/premiere_latest_xml.txt
*/

function sttTrimText(s) {
    return String(s).replace(/^\s+|\s+$/g, "");
}

function sttPointerFile() {
    return new File(Folder.userData.fsName + "/STT_AI_Editor/premiere_latest_xml.txt");
}

function sttGetLatestXMLPath() {
    try {
        var pointer = sttPointerFile();

        if (!pointer.exists) {
            return "";
        }

        if (!pointer.open("r")) {
            return "";
        }

        var xmlPath = sttTrimText(pointer.read());
        pointer.close();

        return xmlPath;
    } catch (e) {
        return "ERROR: " + e;
    }
}

function sttImportLatestXML() {
    try {
        var xmlPath = sttGetLatestXMLPath();

        if (!xmlPath || xmlPath.indexOf("ERROR:") === 0) {
            return "Không thấy latest XML. Hãy export XML từ STT AI Editor trước.";
        }

        var xmlFile = new File(xmlPath);

        if (!xmlFile.exists) {
            return "Không thấy XML: " + xmlPath;
        }

        if (!app.project) {
            app.newProject();
        }

        app.project.importFiles(
            [xmlFile.fsName],
            false,
            app.project.rootItem,
            false
        );

        return "Đã gửi lệnh import XML: " + xmlFile.fsName;
    } catch (e) {
        return "Import lỗi: " + e + ". Nếu cần, dùng File > Import thủ công.";
    }
}

function sttOpenLatestXMLFolder() {
    try {
        var xmlPath = sttGetLatestXMLPath();

        if (!xmlPath || xmlPath.indexOf("ERROR:") === 0) {
            return "Không thấy latest XML.";
        }

        var xmlFile = new File(xmlPath);

        if (!xmlFile.exists) {
            return "Không thấy XML: " + xmlPath;
        }

        xmlFile.parent.execute();
        return "Đã mở folder XML.";
    } catch (e) {
        return "Open folder lỗi: " + e;
    }
}
'''

    @staticmethod
    def render_style_css() -> str:
        return r'''body {
  margin: 0;
  background: #171717;
  color: #f1f1f1;
  font-family: Arial, sans-serif;
  font-size: 13px;
}

.wrap {
  padding: 18px;
}

.badge {
  display: inline-block;
  padding: 5px 9px;
  border: 1px solid #555;
  border-radius: 999px;
  font-weight: bold;
  margin-bottom: 12px;
}

h1 {
  margin: 0 0 6px;
  font-size: 22px;
}

.muted {
  opacity: .65;
  margin-top: 0;
}

button {
  width: 100%;
  height: 38px;
  margin: 7px 0;
  border-radius: 8px;
  border: 1px solid #555;
  background: #242424;
  color: #fff;
  cursor: pointer;
}

button:hover {
  background: #303030;
}

button.primary {
  font-weight: bold;
  background: #2e2e2e;
  border-color: #888;
}

.box {
  border: 1px solid #333;
  border-radius: 10px;
  padding: 12px;
  margin-top: 12px;
  background: #1f1f1f;
}

.label {
  opacity: .65;
  font-size: 11px;
  margin-bottom: 5px;
  text-transform: uppercase;
}

.path {
  overflow-wrap: anywhere;
  font-family: Consolas, monospace;
  font-size: 12px;
}

.hint {
  opacity: .72;
  line-height: 1.45;
}
'''

    @staticmethod
    def render_csinterface_stub() -> str:
        # Minimal CSInterface for evalScript. Premiere CEP provides window.__adobe_cep__.
        return r'''/*
Minimal CSInterface stub for STT AI Editor panel.
Enough for evalScript in CEP.
*/

function CSInterface() {}

CSInterface.prototype.evalScript = function (script, callback) {
  if (window.__adobe_cep__) {
    window.__adobe_cep__.evalScript(script, callback || function () {});
  } else {
    if (callback) callback("CEP host not available.");
  }
};
'''

    @staticmethod
    def render_debug_bat() -> str:
        # Add multiple CSXS versions to support many Premiere generations.
        return r'''@echo off
echo ========================================
echo Enable Adobe CEP Debug Mode
echo ========================================
echo.

for %%V in (9 10 11 12 13 14) do (
  reg add "HKCU\Software\Adobe\CSXS.%%V" /v PlayerDebugMode /t REG_SZ /d 1 /f
)

echo.
echo Done.
echo Restart Premiere Pro.
pause
'''

    @staticmethod
    def render_install_bat(extension_dir: Path) -> str:
        return f'''@echo off
setlocal

echo ========================================
echo Install STT AI Editor Premiere Panel
echo ========================================
echo.

set "SRC={extension_dir}"
set "DEST=%APPDATA%\\Adobe\\CEP\\extensions\\{EXTENSION_ID}"

if not exist "%SRC%" (
  echo ERROR: source extension missing:
  echo %SRC%
  pause
  exit /b 1
)

if not exist "%APPDATA%\\Adobe\\CEP\\extensions" (
  mkdir "%APPDATA%\\Adobe\\CEP\\extensions"
)

if exist "%DEST%" (
  echo Removing old extension:
  echo %DEST%
  rmdir /s /q "%DEST%"
)

xcopy "%SRC%" "%DEST%" /E /I /Y

echo.
echo Enabling CEP debug mode...
for %%V in (9 10 11 12 13 14) do (
  reg add "HKCU\\Software\\Adobe\\CSXS.%%V" /v PlayerDebugMode /t REG_SZ /d 1 /f
)

echo.
echo Installed to:
echo %DEST%
echo.
echo Restart Premiere Pro, then open:
echo Window ^> Extensions ^> STT AI Editor
echo.
pause
'''

    @staticmethod
    def render_uninstall_bat() -> str:
        return f'''@echo off
setlocal

set "DEST=%APPDATA%\\Adobe\\CEP\\extensions\\{EXTENSION_ID}"

if exist "%DEST%" (
  rmdir /s /q "%DEST%"
  echo Removed:
  echo %DEST%
) else (
  echo Extension not found:
  echo %DEST%
)

echo.
pause
'''

    def render_readme(self, extension_dir: Path) -> str:
        return "\n".join(
            [
                "STT AI Editor - Premiere Panel Starter",
                "=" * 72,
                "",
                "MỤC TIÊU:",
                "",
                "Tạo panel STT AI Editor bên trong Premiere:",
                "",
                "Premiere Pro > Window > Extensions > STT AI Editor",
                "",
                "PANEL CÓ NÚT:",
                "",
                "- Refresh Latest XML",
                "- Import Latest XML",
                "- Open XML Folder",
                "",
                "CÀI PANEL:",
                "",
                "1. Chạy:",
                "   ENABLE_CEP_DEBUG_MODE.bat",
                "",
                "2. Chạy:",
                "   INSTALL_PANEL_TO_USER_CEP.bat",
                "",
                "3. Restart Premiere Pro.",
                "",
                "4. Mở:",
                "   Window > Extensions > STT AI Editor",
                "",
                "NẾU KHÔNG THẤY PANEL:",
                "",
                "- Chạy lại ENABLE_CEP_DEBUG_MODE.bat",
                "- Restart Premiere",
                "- Kiểm tra folder:",
                f"  {self.get_user_cep_extensions_dir() / EXTENSION_ID}",
                "",
                "EXTENSION SOURCE:",
                "",
                str(extension_dir),
                "",
                "LƯU Ý:",
                "",
                "- Đây là panel starter đầu tiên, chưa phải bản plugin đóng gói chính thức.",
                "- Panel đọc latest XML từ Module 040:",
                f"  {self.latest_xml_pointer}",
                "- Nếu Import trong panel không chạy, vẫn dùng cách chắc chắn:",
                "  Premiere > File > Import > chọn XML",
                "",
            ]
        )


def create_premiere_panel(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    xml_path: str | Path | None = None,
    install_to_user_cep: bool = True,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PremierePanelInstaller(project_root=project_root).create_panel_package(
        xml_path=xml_path,
        install_to_user_cep=install_to_user_cep,
        open_folder=open_folder,
    )
