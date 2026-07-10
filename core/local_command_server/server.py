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



_SERVER_THREAD = None
_SERVER_OBJECT = None


def status_path() -> Path:
    return appdata_dir() / "local_command_server_status.json"


def write_status(data: dict[str, Any]) -> None:
    current = read_json(status_path())
    current.update(data)
    current["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(status_path(), current)


def read_status() -> dict[str, Any]:
    data = read_json(status_path())
    if not data:
        data = {"ok": False, "state": "not_started"}
    return data


def run_pipeline_background(project_root: Path, intent: str = "prewedding_reel_60s", preset: str | None = None) -> None:
    def worker() -> None:
        try:
            write_status({"ok": True, "state": "running", "step": "pipeline", "intent": intent, "project_root": str(project_root)})
            from core.prewedding_pipeline import run_prewedding_pipeline
            kwargs: dict[str, Any] = {"project_root": project_root, "intent": intent, "open_folder": False}
            if preset:
                kwargs["preset"] = preset
            result = run_prewedding_pipeline(**kwargs)
            pointer = update_latest_xml_pointer(project_root)
            write_status({"ok": bool(result.get("ok", True)), "state": "done", "step": "done", "result": result, "latest_xml": pointer.get("latest_xml")})
        except Exception as exc:
            write_status({"ok": False, "state": "error", "error": repr(exc)})

    threading.Thread(target=worker, daemon=True).start()


def make_handler(default_project_root: Path):
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def send_json(self, data: dict[str, Any]) -> None:
            raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()
            self.wfile.write(raw)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            project_root = Path(qs.get("project", [str(default_project_root)])[0])

            if parsed.path in ["/", "/health"]:
                self.send_json({"ok": True, "server": "STT Local Command Server", "port": DEFAULT_PORT, "time": datetime.now().isoformat(timespec="seconds")})
                return

            if parsed.path == "/status":
                self.send_json(read_status())
                return

            if parsed.path == "/latest_xml":
                self.send_json(update_latest_xml_pointer(project_root))
                return

            if parsed.path == "/run_prewedding_pipeline":
                intent = qs.get("intent", ["prewedding_reel_60s"])[0]
                preset = qs.get("preset", [None])[0]
                run_pipeline_background(project_root=project_root, intent=intent, preset=preset)
                self.send_json({"ok": True, "accepted": True, "intent": intent, "project_root": str(project_root), "status_url": "/status"})
                return

            self.send_json({"ok": False, "error": "unknown_path", "path": parsed.path})

    return Handler


def start_local_command_server(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    block: bool = True,
) -> Any:
    from http.server import ThreadingHTTPServer

    global _SERVER_OBJECT

    project_root = Path(project_root)
    handler = make_handler(project_root)
    server = ThreadingHTTPServer((host, port), handler)
    _SERVER_OBJECT = server
    write_status({"ok": True, "state": "server_started", "host": host, "port": port, "project_root": str(project_root)})

    if block:
        print(f"STT Local Command Server running: http://{host}:{port}/health")
        server.serve_forever()
    return server


def start_local_command_server_background(project_root: str | Path = DEFAULT_PROJECT_ROOT, port: int = DEFAULT_PORT) -> dict[str, Any]:
    global _SERVER_THREAD, _SERVER_OBJECT

    if _SERVER_THREAD and _SERVER_THREAD.is_alive():
        return {"ok": True, "already_running": True, "port": port, "status": read_status()}

    def worker() -> None:
        start_local_command_server(project_root=project_root, port=port, block=True)

    _SERVER_THREAD = threading.Thread(target=worker, daemon=True)
    _SERVER_THREAD.start()
    time.sleep(0.5)
    return call_local_server("/health", port=port, timeout=2)


def create_local_command_server_report(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root)
    out = ensure_report_dir(project_root, "local_command_server")
    result = start_local_command_server_background(project_root=project_root)
    rows = [
        {"item": "health_url", "value": "http://127.0.0.1:8790/health"},
        {"item": "status_url", "value": "http://127.0.0.1:8790/status"},
        {"item": "run_reel_60s", "value": "http://127.0.0.1:8790/run_prewedding_pipeline?intent=prewedding_reel_60s"},
        {"item": "latest_xml", "value": "http://127.0.0.1:8790/latest_xml"},
        {"item": "server_result", "value": json.dumps(result, ensure_ascii=False)},
    ]
    write_csv(out / "LOCAL_COMMAND_SERVER.csv", rows, ["item", "value"])
    write_json(out / "local_command_server_report.json", {"ok": True, "module": "081_local_command_server", "result": result, "rows": rows})
    (out / "LOCAL_COMMAND_SERVER.html").write_text(simple_html("Local Command Server", rows, ["item", "value"], "Premiere panel sẽ gọi các URL local này để chạy pipeline."), encoding="utf-8")
    if open_folder:
        open_path(out)
    return {"ok": True, "output_dir": str(out), "report_dir": str(out), "server": result, "port": DEFAULT_PORT}

