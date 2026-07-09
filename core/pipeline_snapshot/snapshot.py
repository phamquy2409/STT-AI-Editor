
from __future__ import annotations
import json, os, shutil
from datetime import datetime
from pathlib import Path
from typing import Any
DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
SNAPSHOT_FILES = ["manual_selection.json","stt_feedback_profile.json","stt_wedding_style_profile.json","stt_ai_style_memory_v2.json","stt_ai_shot_scores_v1.json","stt_prewedding_selection_v1.json","stt_prewedding_roughcut_v1.json","stt_prewedding_refined_v1.json","stt_prewedding_premiere_import.xml","stt_prewedding_pipeline_v1.json"]
def create_pipeline_snapshot(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root); exports = project_root / "exports"
    output_dir = exports / f"pipeline_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    files_dir = output_dir / "project_files"; files_dir.mkdir(parents=True, exist_ok=True)
    copied, missing = [], []
    for name in SNAPSHOT_FILES:
        src = project_root / name
        if src.exists():
            dst = files_dir / name; shutil.copy2(src, dst)
            copied.append({"name": name, "source": str(src), "copy": str(dst), "size_bytes": dst.stat().st_size})
        else: missing.append(name)
    latest = []
    if exports.exists():
        dirs = [p for p in exports.iterdir() if p.is_dir() and p.name != "_archive" and p != output_dir]
        for p in sorted(dirs, key=lambda x: x.stat().st_mtime, reverse=True)[:15]:
            latest.append({"name": p.name, "path": str(p), "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")})
    data = {"ok": True, "module": "054_pipeline_snapshot", "project_root": str(project_root), "output_dir": str(output_dir), "copied": copied, "missing": missing, "latest_exports": latest}
    (output_dir / "snapshot_manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "SNAPSHOT_README.txt").write_text(render_text(data), encoding="utf-8")
    (output_dir / "SNAPSHOT_REPORT.html").write_text(render_html(data), encoding="utf-8")
    if open_folder:
        try: os.startfile(output_dir)
        except Exception: pass
    return {"ok": True, "output_dir": str(output_dir), "report_dir": str(output_dir), "copied_count": len(copied), "missing_count": len(missing)}
def render_text(data: dict[str, Any]) -> str:
    lines = ["STT AI Editor - Pipeline Snapshot", "="*72, f"Project: {data['project_root']}", f"Output: {data['output_dir']}", "", "Copied:"]
    lines += [f"- {x['name']}" for x in data["copied"]]; lines += ["", "Missing:"]; lines += [f"- {x}" for x in data["missing"]] or ["- none"]
    return "\n".join(lines)
def render_html(data: dict[str, Any]) -> str:
    rows = "".join(f"<tr><td>{x['name']}</td><td>{x['size_bytes']}</td></tr>" for x in data["copied"])
    missing = "".join(f"<li>{x}</li>" for x in data["missing"]) or "<li>none</li>"
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Snapshot</title><style>body{{font-family:Arial;background:#111;color:#eee;margin:32px}}.card{{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}}td,th{{border-bottom:1px solid #333;padding:8px}}</style></head><body><div class='card'><h1>Pipeline Snapshot</h1><p>{data['output_dir']}</p><table><tr><th>File</th><th>Bytes</th></tr>{rows}</table><h2>Missing</h2><ul>{missing}</ul></div></body></html>"""
