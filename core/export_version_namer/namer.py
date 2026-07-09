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


def load_timeline(project_root: Path) -> list[dict[str, Any]]:
    for name in ["stt_prewedding_refined_v1.json", "stt_prewedding_roughcut_v1.json", "stt_prewedding_selection_v1.json"]:
        data = load_json(project_root / name)
        if isinstance(data.get("timeline"), list):
            return data["timeline"]
    return []


def latest_files(root: Path, patterns: list[str], limit: int = 50) -> list[Path]:
    files: list[Path] = []
    if root.exists():
        for pattern in patterns:
            files.extend([p for p in root.glob(pattern) if p.is_file()])
    return sorted(set(files), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def simple_html(title: str, rows: list[dict[str, Any]], columns: list[str], note: str = "") -> str:
    import html
    header = "".join(f"<th>{html.escape(str(c))}</th>" for c in columns)
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



def create_export_version_namer(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root)
    out = ensure_report_dir(project_root, "export_version_namer")
    project_name = project_root.name.replace(" ", "_")
    today = datetime.now().strftime("%Y%m%d")
    rows = [
        {"type": "preview", "filename": f"{project_name}_PREVIEW_v01_{today}.mp4", "use_for": "gửi khách xem nháp"},
        {"type": "final_4k", "filename": f"{project_name}_FINAL_4K_v01_{today}.mp4", "use_for": "file final chính"},
        {"type": "final_reel", "filename": f"{project_name}_FINAL_REEL_1080x1920_v01_{today}.mp4", "use_for": "reel dọc"},
        {"type": "archive_master", "filename": f"{project_name}_MASTER_PRORES_v01_{today}.mov", "use_for": "master lưu trữ"},
    ]
    columns = ["type", "filename", "use_for"]
    write_csv(out / "EXPORT_VERSION_NAMING_PLAN.csv", rows, columns)
    write_json(out / "export_version_namer.json", {"ok": True, "module": "074_export_version_namer", "rows": rows})
    (out / "EXPORT_VERSION_NAMING_PLAN.html").write_text(simple_html("Export Version Namer", rows, columns, "Tên file export chuẩn để không nhầm bản."), encoding="utf-8")
    if open_folder:
        try: os.startfile(out)
        except Exception: pass
    return {"ok": True, "output_dir": str(out), "report_dir": str(out), "name_count": len(rows)}

