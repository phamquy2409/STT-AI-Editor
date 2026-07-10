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



def create_panel_command_bridge(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root)
    out = ensure_report_dir(project_root, "panel_command_bridge")
    commands = [
        {"id": "health", "label": "Health", "endpoint": "/health", "method": "GET"},
        {"id": "status", "label": "Status", "endpoint": "/status", "method": "GET"},
        {"id": "latest_xml", "label": "Refresh Latest XML", "endpoint": "/latest_xml", "method": "GET"},
        {"id": "run_reel_60s", "label": "Run Prewedding 60s", "endpoint": "/run_prewedding_pipeline?intent=prewedding_reel_60s", "method": "GET"},
        {"id": "run_reel_30s", "label": "Run Prewedding 30s", "endpoint": "/run_prewedding_pipeline?intent=prewedding_reel_30s", "method": "GET"},
        {"id": "run_cinematic", "label": "Run Cinematic", "endpoint": "/run_prewedding_pipeline?intent=prewedding_cinematic", "method": "GET"},
    ]
    write_json(out / "panel_command_bridge_manifest.json", {"ok": True, "module": "083_panel_command_bridge", "server": "http://127.0.0.1:8790", "commands": commands})
    write_csv(out / "PANEL_COMMAND_BRIDGE.csv", commands, ["id", "label", "endpoint", "method"])
    (out / "PANEL_COMMAND_BRIDGE.html").write_text(simple_html("Panel Command Bridge", commands, ["id", "label", "endpoint", "method"], "Danh sách command để panel gọi local server."), encoding="utf-8")
    test = call_local_server("/health")
    write_json(out / "panel_command_bridge_health_test.json", test)
    if open_folder:
        open_path(out)
    return {"ok": True, "output_dir": str(out), "report_dir": str(out), "command_count": len(commands), "server_test": test}

