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



DEFAULT_TRACKS = [
    {"source": "Artlist", "title": "CHUA_CHON_BAI", "artist": "", "url": "", "bpm": "90-120", "mood": "romantic modern cinematic", "intent": "prewedding_reel_60s", "score": 70, "notes": "Điền bài Artlist preview ở đây"},
    {"source": "Musicbed", "title": "CHUA_CHON_BAI", "artist": "", "url": "", "bpm": "70-100", "mood": "cinematic emotional wedding", "intent": "prewedding_cinematic", "score": 70, "notes": "Điền bài Musicbed preview ở đây"},
    {"source": "YouTube Audio Library", "title": "CHUA_CHON_BAI", "artist": "", "url": "", "bpm": "100-140", "mood": "reel fashion upbeat", "intent": "prewedding_reel_30s", "score": 70, "notes": "Chỉ dùng nhạc tải hợp lệ từ Audio Library"},
]

def create_music_candidate_library(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root)
    out = ensure_report_dir(project_root, "music_candidate_library")
    music_dir = project_root / "music"
    library_dir = music_dir / "library"
    library_dir.mkdir(parents=True, exist_ok=True)

    rows = DEFAULT_TRACKS
    csv_path = out / "MUSIC_CANDIDATE_LIBRARY.csv"
    stable_csv = library_dir / "MUSIC_CANDIDATE_LIBRARY.csv"
    columns = ["source", "title", "artist", "url", "bpm", "mood", "intent", "score", "notes"]
    write_csv(csv_path, rows, columns)
    write_csv(stable_csv, rows, columns)

    data = {"ok": True, "module": "063_music_candidate_library", "project_root": str(project_root), "rows": rows, "stable_csv": str(stable_csv)}
    write_json(out / "music_candidate_library.json", data)
    (out / "MUSIC_CANDIDATE_LIBRARY.html").write_text(simple_html("Music Candidate Library", rows, columns, "Điền bài nhạc hợp lệ vào CSV này để dùng cho cue sheet."), encoding="utf-8")
    (out / "HOW_TO_USE.txt").write_text("Điền title/artist/url của bài trên Artlist/Musicbed/YouTube Audio Library. Sau đó dùng Module 062 với --candidates CSV này.", encoding="utf-8")
    if open_folder:
        try: os.startfile(out)
        except Exception: pass
    return {"ok": True, "output_dir": str(out), "report_dir": str(out), "stable_csv": str(stable_csv), "track_count": len(rows)}

