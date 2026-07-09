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



DEFAULT_SFX = [
    {"cue": "whoosh_soft", "category": "transition", "source": "Artlist/SFX library", "filename": "", "timeline_time": "auto", "notes": "Whoosh nhẹ khi chuyển shot"},
    {"cue": "riser_short", "category": "build", "source": "Artlist/SFX library", "filename": "", "timeline_time": "hook", "notes": "Riser vào hook đầu"},
    {"cue": "hit_soft", "category": "impact", "source": "Artlist/SFX library", "filename": "", "timeline_time": "beat", "notes": "Hit nhẹ theo beat"},
    {"cue": "ambience_location", "category": "ambience", "source": "own/licensed", "filename": "", "timeline_time": "background", "notes": "Ambience nhẹ nếu cần"},
]

def create_sfx_placeholder_manager(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root)
    out = ensure_report_dir(project_root, "sfx_placeholder_manager")
    sfx_dir = project_root / "sfx"
    preview_dir = sfx_dir / "sfx_previews"
    final_dir = sfx_dir / "sfx_final"
    for d in [preview_dir, final_dir]:
        d.mkdir(parents=True, exist_ok=True)

    rows = DEFAULT_SFX
    columns = ["cue", "category", "source", "filename", "timeline_time", "notes"]
    write_csv(out / "SFX_CUE_SHEET.csv", rows, columns)
    write_csv(sfx_dir / "SFX_CUE_SHEET.csv", rows, columns)
    write_json(out / "sfx_placeholder_manager.json", {"ok": True, "module": "064_sfx_placeholder_manager", "rows": rows})
    (out / "SFX_CUE_SHEET.html").write_text(simple_html("SFX Cue Sheet", rows, columns, "Ghi SFX preview/final hợp lệ để chèn trong Premiere."), encoding="utf-8")
    if open_folder:
        try: os.startfile(out)
        except Exception: pass
    return {"ok": True, "output_dir": str(out), "report_dir": str(out), "sfx_dir": str(sfx_dir), "cue_count": len(rows)}

