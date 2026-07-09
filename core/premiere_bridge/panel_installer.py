
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .bridge import PremiereBridgeExporter
from .panel_sync import PremierePanelSync
from .pointer import PremiereXMLPointer


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
    # Module 043:
    # - Builds status-aware Premiere CEP panel.
    # - Installs to user CEP folder.
    # - Runs panel sync before packaging.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.pointer = PremiereXMLPointer(project_root=self.project_root)
        self.appdata_dir = self.pointer.appdata_dir
        self.latest_xml_pointer = self.pointer.pointer_txt
        self.latest_xml_pointer_json = self.pointer.pointer_json
        self.status_json = self.appdata_dir / "premiere_panel_status.json"

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

        sync_result = PremierePanelSync(self.project_root).sync(
            xml_path=xml,
            validate_xml=True,
            open_folder=False,
        )

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

        installed_to = None
        install_error = None

        if install_to_user_cep:
            try:
                installed_to = self.install_extension_to_user_cep(extension_dir)
            except Exception as exc:
                install_error = repr(exc)

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "module": "043_premiere_panel_sync",
            "project_root": str(self.project_root),
            "xml": str(xml.resolve()),
            "sync_result": sync_result,
            "latest_xml_pointer": str(self.latest_xml_pointer),
            "latest_xml_pointer_json": str(self.latest_xml_pointer_json),
            "panel_status_json": str(self.status_json),
            "package_dir": str(out_dir),
            "extension_id": EXTENSION_ID,
            "extension_dir": str(extension_dir),
            "installed_to_user_cep": str(installed_to) if installed_to else None,
            "install_error": install_error,
        }

        manifest_path = out_dir / "premiere_panel_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        result = {
            "ok": True,
            "project_root": str(self.project_root),
            "xml": str(xml.resolve()),
            "sync_status": sync_result.get("status"),
            "latest_xml_pointer": str(self.latest_xml_pointer),
            "panel_status_json": str(self.status_json),
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
            <Size><Height>660</Height><Width>430</Width></Size>
            <MinSize><Height>500</Height><Width>350</Width></MinSize>
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
    <div class="top">
      <div class="badge">STT AI Editor</div>
      <div id="dot" class="dot wait"></div>
    </div>

    <h1>Premiere Panel</h1>
    <p class="muted">Module 043 - panel sync</p>

    <button id="btnRefresh">Refresh Latest XML</button>
    <button id="btnImport" class="primary">Import Latest XML</button>
    <button id="btnOpenFolder">Open XML Folder</button>
    <button id="btnOpenSyncReport">Open Sync Report</button>

    <div class="box">
      <div class="label">Latest XML</div>
      <div id="xmlPath" class="path">Loading...</div>
    </div>

    <div class="box grid">
      <div>
        <div class="label">Exists</div>
        <div id="xmlExists">-</div>
      </div>
      <div>
        <div class="label">Sync</div>
        <div id="syncStatus">-</div>
      </div>
    </div>

    <div class="box grid">
      <div>
        <div class="label">Updated</div>
        <div id="xmlUpdated">-</div>
      </div>
      <div>
        <div class="label">Validation</div>
        <div id="validationStatus">-</div>
      </div>
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
        return r'''/* STT AI Editor - CEP Panel main.js - Module 043 */

var csInterface = null;

function el(id) { return document.getElementById(id); }

function setText(id, text) {
  var node = el(id);
  if (node) node.textContent = text;
}

function setDot(state) {
  var dot = el("dot");
  if (!dot) return;
  dot.className = "dot " + state;
}

function evalHost(script, cb) {
  if (!csInterface) {
    setText("status", "CSInterface chưa sẵn sàng.");
    setDot("bad");
    if (cb) cb("");
    return;
  }

  csInterface.evalScript(script, function (res) {
    if (cb) cb(res);
  });
}

function parseMaybeJSON(res) {
  try { return JSON.parse(res); } catch (e) { return null; }
}

function refreshLatestXML() {
  setText("status", "Reading latest XML...");
  setDot("wait");

  evalHost("sttGetLatestPanelInfo()", function (res) {
    var data = parseMaybeJSON(res);

    if (!data) {
      setText("status", res || "No panel info.");
      setDot("bad");
      return;
    }

    setText("xmlPath", data.xml || "Không thấy XML.");
    setText("xmlExists", data.exists ? "YES" : "NO");
    setText("syncStatus", (data.sync_status || "-").toUpperCase());
    setText("xmlUpdated", data.updated_at || "-");
    setText("validationStatus", (data.validation_status || "-").toUpperCase());
    setText("status", data.message || "Ready");

    if (data.exists && data.sync_status !== "fail") {
      setDot("ok");
    } else if (data.sync_status === "warn") {
      setDot("wait");
    } else {
      setDot("bad");
    }
  });
}

function importLatestXML() {
  setText("status", "Importing XML...");
  setDot("wait");

  evalHost("sttImportLatestXML()", function (res) {
    setText("status", res || "Done.");
    setDot("ok");
    refreshLatestXML();
  });
}

function openLatestXMLFolder() {
  setText("status", "Opening XML folder...");
  evalHost("sttOpenLatestXMLFolder()", function (res) {
    setText("status", res || "Done.");
  });
}

function openSyncReport() {
  setText("status", "Opening sync report...");
  evalHost("sttOpenSyncReportFolder()", function (res) {
    setText("status", res || "Done.");
  });
}

window.onload = function () {
  try {
    csInterface = new CSInterface();
  } catch (e) {
    setText("status", "CSInterface lỗi: " + e);
    setDot("bad");
  }

  el("btnRefresh").onclick = refreshLatestXML;
  el("btnImport").onclick = importLatestXML;
  el("btnOpenFolder").onclick = openLatestXMLFolder;
  el("btnOpenSyncReport").onclick = openSyncReport;

  refreshLatestXML();
};
'''

    @staticmethod
    def render_host_jsx() -> str:
        return r'''/*
STT AI Editor - Premiere CEP Panel host.jsx
Module 043
*/

function sttTrimText(s) {
    return String(s).replace(/^\s+|\s+$/g, "");
}

function sttEscapeJSON(s) {
    return String(s)
        .replace(/\\/g, "\\\\")
        .replace(/"/g, "\\\"")
        .replace(/\r/g, "\\r")
        .replace(/\n/g, "\\n");
}

function sttReadTextFile(f) {
    if (!f.exists) return "";
    if (!f.open("r")) return "";
    var txt = f.read();
    f.close();
    return sttTrimText(txt);
}

function sttPointerFile() {
    return new File(Folder.userData.fsName + "/STT_AI_Editor/premiere_latest_xml.txt");
}

function sttStatusFile() {
    return new File(Folder.userData.fsName + "/STT_AI_Editor/premiere_panel_status.json");
}

function sttGetLatestXMLPath() {
    try {
        return sttReadTextFile(sttPointerFile());
    } catch (e) {
        return "";
    }
}

function sttExtractJSONField(jsonText, key) {
    var re = new RegExp('"' + key + '"\\s*:\\s*"([^"]*)"', "m");
    var m = jsonText.match(re);
    if (m && m[1]) return m[1];
    return "";
}

function sttGetLatestPanelInfo() {
    try {
        var xmlPath = sttGetLatestXMLPath();
        var xmlFile = xmlPath ? new File(xmlPath) : null;
        var exists = xmlFile && xmlFile.exists;

        var statusFile = sttStatusFile();
        var syncStatus = "";
        var updated = "";
        var validationStatus = "";
        var reportDir = "";

        if (statusFile.exists && statusFile.open("r")) {
            var statusText = statusFile.read();
            statusFile.close();

            syncStatus = sttExtractJSONField(statusText, "status");
            updated = sttExtractJSONField(statusText, "created_at");
            reportDir = sttExtractJSONField(statusText, "report_dir");
            validationStatus = sttExtractJSONField(statusText, "validation_status");

            if (!validationStatus) {
                var m = statusText.match(/"validation"\s*:\s*\{[\s\S]*?"status"\s*:\s*"([^"]+)"/m);
                if (m && m[1]) validationStatus = m[1];
            }
        }

        if (!syncStatus) syncStatus = exists ? "ok" : "fail";

        var message = exists ? "XML ready. Bấm Import Latest XML." : "XML missing. Export XML lại từ STT AI Editor.";

        return "{" +
            "\"xml\":\"" + sttEscapeJSON(xmlPath) + "\"," +
            "\"exists\":" + (exists ? "true" : "false") + "," +
            "\"sync_status\":\"" + sttEscapeJSON(syncStatus) + "\"," +
            "\"updated_at\":\"" + sttEscapeJSON(updated) + "\"," +
            "\"validation_status\":\"" + sttEscapeJSON(validationStatus) + "\"," +
            "\"report_dir\":\"" + sttEscapeJSON(reportDir) + "\"," +
            "\"message\":\"" + sttEscapeJSON(message) + "\"" +
        "}";
    } catch (e) {
        return "{" +
            "\"xml\":\"\"," +
            "\"exists\":false," +
            "\"sync_status\":\"fail\"," +
            "\"updated_at\":\"\"," +
            "\"validation_status\":\"error\"," +
            "\"report_dir\":\"\"," +
            "\"message\":\"ERROR: " + sttEscapeJSON(e) + "\"" +
        "}";
    }
}

function sttImportLatestXML() {
    try {
        var xmlPath = sttGetLatestXMLPath();

        if (!xmlPath) {
            return "Không thấy latest XML. Hãy export XML từ STT AI Editor trước.";
        }

        var xmlFile = new File(xmlPath);

        if (!xmlFile.exists) {
            return "Không thấy XML: " + xmlPath;
        }

        if (!app.project) {
            app.newProject();
        }

        app.project.importFiles([xmlFile.fsName], false, app.project.rootItem, false);

        return "Đã gửi lệnh import XML. Kiểm tra Project panel: " + xmlFile.fsName;
    } catch (e) {
        return "Import lỗi: " + e + ". Nếu cần, dùng File > Import thủ công.";
    }
}

function sttOpenLatestXMLFolder() {
    try {
        var xmlPath = sttGetLatestXMLPath();

        if (!xmlPath) return "Không thấy latest XML.";

        var xmlFile = new File(xmlPath);
        if (!xmlFile.exists) return "Không thấy XML: " + xmlPath;

        xmlFile.parent.execute();
        return "Đã mở folder XML.";
    } catch (e) {
        return "Open folder lỗi: " + e;
    }
}

function sttOpenSyncReportFolder() {
    try {
        var statusFile = sttStatusFile();

        if (!statusFile.exists) return "Không thấy sync status report.";

        if (!statusFile.open("r")) return "Không đọc được sync status report.";

        var statusText = statusFile.read();
        statusFile.close();

        var reportDir = sttExtractJSONField(statusText, "report_dir");

        if (!reportDir) return "Không thấy report_dir trong status.";

        var folder = new Folder(reportDir);
        if (!folder.exists) return "Report folder không tồn tại: " + reportDir;

        folder.execute();
        return "Đã mở sync report folder.";
    } catch (e) {
        return "Open report lỗi: " + e;
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

.wrap { padding: 18px; }

.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.badge {
  display: inline-block;
  padding: 5px 9px;
  border: 1px solid #555;
  border-radius: 999px;
  font-weight: bold;
  margin-bottom: 12px;
}

.dot {
  width: 11px;
  height: 11px;
  border-radius: 99px;
  border: 1px solid #777;
}

.dot.ok { background: #55d17a; }
.dot.bad { background: #e45f5f; }
.dot.wait { background: #e1c65d; }

h1 { margin: 0 0 6px; font-size: 22px; }

.muted { opacity: .65; margin-top: 0; }

button {
  width: 100%;
  min-height: 38px;
  margin: 7px 0;
  border-radius: 8px;
  border: 1px solid #555;
  background: #242424;
  color: #fff;
  cursor: pointer;
}

button:hover { background: #303030; }

button.primary {
  font-weight: bold;
  background: #2e2e2e;
  border-color: #999;
}

.box {
  border: 1px solid #333;
  border-radius: 10px;
  padding: 12px;
  margin-top: 12px;
  background: #1f1f1f;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
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

.hint { opacity: .72; line-height: 1.45; }
'''

    @staticmethod
    def render_csinterface_stub() -> str:
        return r'''function CSInterface() {}

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
                "STT AI Editor - Premiere Panel Sync",
                "=" * 72,
                "",
                "Module 043 nâng cấp panel:",
                "",
                "- Hiển thị Sync status",
                "- Hiển thị Validation status",
                "- Có nút Open Sync Report",
                "- Có file premiere_panel_status.json",
                "- Có lệnh sync riêng trong STT app",
                "",
                "CÀI PANEL:",
                "",
                "1. Chạy ENABLE_CEP_DEBUG_MODE.bat",
                "2. Chạy INSTALL_PANEL_TO_USER_CEP.bat",
                "3. Restart Premiere",
                "4. Window > Extensions > STT AI Editor",
                "",
                "EXTENSION SOURCE:",
                str(extension_dir),
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
