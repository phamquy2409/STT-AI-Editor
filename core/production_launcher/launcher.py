from __future__ import annotations

import csv
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


def appdata_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "STT_AI_Editor"
    return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"


def ensure_report_dir(project_root: Path, name: str) -> Path:
    out = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def latest_existing(project_root: Path, names: list[str]) -> Path | None:
    for name in names:
        p = project_root / name
        if p.exists():
            return p
    return None


def load_timeline(project_root: Path) -> list[dict[str, Any]]:
    for name in ["stt_prewedding_refined_v1.json", "stt_prewedding_roughcut_v1.json", "stt_prewedding_selection_v1.json"]:
        p = project_root / name
        data = load_json(p)
        if isinstance(data.get("timeline"), list):
            return data["timeline"]
    return []


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def simple_html(title: str, rows: list[dict[str, Any]], columns: list[str], note: str = "") -> str:
    import html
    header = "".join(f"<th>{html.escape(c)}</th>" for c in columns)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{html.escape(str(row.get(c, '')))}</td>" for c in columns) + "</tr>"
    return (
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:32px;line-height:1.55}"
        ".card{max-width:1500px;background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "table{border-collapse:collapse;width:100%;margin-top:12px}th,td{border-bottom:1px solid #333;padding:8px;vertical-align:top;text-align:left}"
        "code{background:#000;padding:4px 8px;border-radius:8px}</style></head><body><div class='card'>"
        f"<h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{header}</tr>{body}</table></div></body></html>"
    )



COMMANDS = [
    {"name": "Doctor", "command": "python scripts/check_prewedding_pipeline.py"},
    {"name": "Full Reel 60s", "command": "python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s"},
    {"name": "Music Cue Sheet", "command": "python scripts/create_music_placeholder_manager.py --intent prewedding_reel_60s"},
    {"name": "SFX Cue Sheet", "command": "python scripts/create_sfx_placeholder_manager.py"},
    {"name": "Audio Cue Plan", "command": "python scripts/create_audio_cue_plan.py"},
    {"name": "Final Replace Check", "command": "python scripts/check_final_replacements.py"},
    {"name": "Source Audit", "command": "python scripts/audit_source_media.py"},
    {"name": "Timeline QC", "command": "python scripts/create_timeline_qc_report.py"},
    {"name": "Handoff Package", "command": "python scripts/create_delivery_handoff_package.py"},
    {"name": "Build EXE", "command": "python scripts/build_exe.py"},
]

def create_production_launcher(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root)
    out = ensure_report_dir(project_root, "production_launcher")
    bat_dir = out / "launcher_bats"
    bat_dir.mkdir(parents=True, exist_ok=True)
    repo_root = detect_repo_root()
    rows = []
    for i, cmd in enumerate(COMMANDS, start=1):
        bat = bat_dir / f"{i:02d}_{cmd['name'].replace(' ', '_')}.bat"
        full = cmd["command"]
        if "--project" not in full:
            full += f' --project "{project_root}"'
        bat.write_text("@echo off\nchcp 65001 >nul\ncd /d \"" + str(repo_root) + "\"\n" + full + "\npause\n", encoding="utf-8")
        rows.append({"index": i, "name": cmd["name"], "command": full, "bat": str(bat)})
    columns = ["index", "name", "command", "bat"]
    write_csv(out / "PRODUCTION_LAUNCHER_COMMANDS.csv", rows, columns)
    write_json(out / "production_launcher.json", {"ok": True, "module": "070_production_launcher", "rows": rows})
    (out / "PRODUCTION_LAUNCHER.html").write_text(simple_html("Production Launcher", rows, columns, "Tổng hợp nút/lệnh từ 063-070."), encoding="utf-8")
    if open_folder:
        try: os.startfile(out)
        except Exception: pass
    return {"ok": True, "output_dir": str(out), "report_dir": str(out), "command_count": len(rows)}

def detect_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "scripts").exists() and (parent / "core").exists():
            return parent
    return Path.cwd()

