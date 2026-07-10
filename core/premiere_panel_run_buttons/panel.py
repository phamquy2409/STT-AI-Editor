from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.parse
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_PORT = 8790


def detect_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "scripts").exists() and (parent / "core").exists():
            return parent
    return Path.cwd()


def appdata_dir() -> Path:
    root = os.environ.get("APPDATA")
    if root:
        p = Path(root) / "STT_AI_Editor"
    else:
        p = Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_report_dir(project_root: Path, name: str) -> Path:
    out = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def open_path(path: str | Path) -> None:
    path = str(path)
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def latest_xml(project_root: Path) -> Path | None:
    candidates: list[Path] = []
    direct = project_root / "stt_prewedding_premiere_import.xml"
    if direct.exists():
        candidates.append(direct)
    exports = project_root / "exports"
    if exports.exists():
        candidates += [p for p in exports.glob("**/*.xml") if p.is_file() and "_archive" not in p.parts]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def update_latest_xml_pointer(project_root: Path) -> dict[str, Any]:
    xml = latest_xml(project_root)
    pointer_txt = appdata_dir() / "premiere_latest_xml.txt"
    pointer_json = appdata_dir() / "premiere_latest_xml.json"
    data = {
        "ok": xml is not None,
        "project_root": str(project_root),
        "latest_xml": str(xml) if xml else None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if xml:
        pointer_txt.write_text(str(xml), encoding="utf-8")
    write_json(pointer_json, data)
    return data


def simple_html(title: str, rows: list[dict[str, Any]], columns: list[str], note: str = "") -> str:
    import html
    header = "".join(f"<th>{html.escape(str(c))}</th>" for c in columns)
    body_html = ""
    for row in rows:
        body_html += "<tr>" + "".join(f"<td>{html.escape(str(row.get(c, '')))}</td>" for c in columns) + "</tr>"
    return (
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:32px;line-height:1.55}"
        ".card{max-width:1500px;background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "table{border-collapse:collapse;width:100%;margin-top:12px}th,td{border-bottom:1px solid #333;padding:8px;vertical-align:top;text-align:left}"
        "code{background:#000;padding:4px 8px;border-radius:8px}</style></head><body><div class='card'>"
        f"<h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{header}</tr>{body_html}</table></div></body></html>"
    )


def call_local_server(path: str, port: int = DEFAULT_PORT, timeout: int = 3) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "url": url}



def create_premiere_panel_run_buttons(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root)
    out = ensure_report_dir(project_root, "premiere_panel_run_buttons")
    panel_dir = out / "STT_AI_Editor_Run_Panel"
    csxs = panel_dir / "CSXS"
    csxs.mkdir(parents=True, exist_ok=True)

    (csxs / "manifest.xml").write_text(PANEL_MANIFEST, encoding="utf-8")
    (panel_dir / "index.html").write_text(PANEL_HTML, encoding="utf-8")
    (panel_dir / "stt-panel.js").write_text(PANEL_JS, encoding="utf-8")
    (panel_dir / "README_INSTALL.txt").write_text("Copy folder STT_AI_Editor_Run_Panel vào CEP/extensions nếu muốn test panel mới. Nhớ bật debug CEP nếu cần.\n", encoding="utf-8")

    rows = [
        {"file": "index.html", "purpose": "Panel có nút Run Prewedding 60s/30s/Cinematic"},
        {"file": "stt-panel.js", "purpose": "Gọi Local Command Server http://127.0.0.1:8790"},
        {"file": "manifest.xml", "purpose": "CEP extension manifest"},
    ]
    write_csv(out / "PREMIERE_PANEL_RUN_BUTTONS.csv", rows, ["file", "purpose"])
    write_json(out / "premiere_panel_run_buttons.json", {"ok": True, "module": "082_premiere_panel_run_buttons", "panel_dir": str(panel_dir), "rows": rows})
    (out / "PREMIERE_PANEL_RUN_BUTTONS.html").write_text(simple_html("Premiere Panel Run Buttons", rows, ["file", "purpose"], "Panel mẫu để bấm chạy pipeline từ Premiere."), encoding="utf-8")
    if open_folder:
        open_path(out)
    return {"ok": True, "output_dir": str(out), "report_dir": str(out), "panel_dir": str(panel_dir)}

PANEL_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>STT AI Editor Run</title>
<style>
body{font-family:Arial;background:#151515;color:#eee;margin:14px}
button{width:100%;padding:10px;margin:6px 0;background:#2d2d2d;color:#fff;border:1px solid #555;border-radius:8px}
pre{white-space:pre-wrap;background:#000;padding:8px;border-radius:8px}
</style>
</head>
<body>
<h2>STT AI Editor</h2>
<button onclick="runPipeline('prewedding_reel_60s')">Run Prewedding 60s</button>
<button onclick="runPipeline('prewedding_reel_30s')">Run Prewedding 30s</button>
<button onclick="runPipeline('prewedding_cinematic')">Run Cinematic</button>
<button onclick="latestXml()">Refresh Latest XML</button>
<button onclick="status()">Status</button>
<pre id="log">Ready. Open STT app / Local Server first.</pre>
<script src="stt-panel.js"></script>
</body>
</html>
"""

PANEL_JS = """
const SERVER='http://127.0.0.1:8790';
function log(x){document.getElementById('log').textContent = typeof x === 'string' ? x : JSON.stringify(x,null,2);}
async function call(path){
  try{
    const r=await fetch(SERVER+path);
    const j=await r.json();
    log(j);
    return j;
  }catch(e){ log('ERROR: '+e); }
}
function runPipeline(intent){ call('/run_prewedding_pipeline?intent='+encodeURIComponent(intent)); }
function latestXml(){ call('/latest_xml'); }
function status(){ call('/status'); }
"""

PANEL_MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<ExtensionManifest Version="7.0" ExtensionBundleId="com.stt.ai.editor.run" ExtensionBundleVersion="1.0" ExtensionBundleName="STT AI Editor Run" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <ExtensionList>
    <Extension Id="com.stt.ai.editor.run.panel" Version="1.0" />
  </ExtensionList>
  <ExecutionEnvironment>
    <HostList>
      <Host Name="PPRO" Version="[14.0,99.9]" />
    </HostList>
    <LocaleList><Locale Code="All" /></LocaleList>
    <RequiredRuntimeList><RequiredRuntime Name="CSXS" Version="9.0" /></RequiredRuntimeList>
  </ExecutionEnvironment>
  <DispatchInfoList>
    <Extension Id="com.stt.ai.editor.run.panel">
      <DispatchInfo>
        <Resources><MainPath>./index.html</MainPath><CEFCommandLine><Parameter>--allow-file-access</Parameter></CEFCommandLine></Resources>
        <Lifecycle><AutoVisible>true</AutoVisible></Lifecycle>
        <UI><Type>Panel</Type><Menu>STT AI Editor Run</Menu><Geometry><Size><Height>520</Height><Width>340</Width></Size></Geometry></UI>
      </DispatchInfo>
    </Extension>
  </DispatchInfoList>
</ExtensionManifest>
"""

