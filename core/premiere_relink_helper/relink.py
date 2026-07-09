
from __future__ import annotations
import csv, json, os
from datetime import datetime
from pathlib import Path
from typing import Any
DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
def create_premiere_relink_report(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root); output_dir = project_root / "exports" / f"premiere_relink_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True); timeline = load_latest_timeline(project_root)
    rows, seen = [], set()
    for item in timeline:
        path = str(item.get("file") or item.get("path") or "")
        if not path or path in seen: continue
        seen.add(path); p = Path(path)
        rows.append({"file": path, "filename": p.name, "exists": p.exists(), "parent": str(p.parent), "timeline_count": sum(1 for x in timeline if str(x.get("file") or x.get("path") or "") == path)})
    csv_path = output_dir / "PREMIERE_RELINK_SOURCE_LIST.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["exists","filename","parent","file","timeline_count"]); writer.writeheader(); writer.writerows(rows)
    report = {"ok": True, "module": "056_premiere_relink_helper", "sources": rows, "missing_count": sum(1 for r in rows if not r["exists"])}
    (output_dir / "premiere_relink_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "PREMIERE_RELINK_REPORT.html").write_text(render_html(report), encoding="utf-8")
    if open_folder:
        try: os.startfile(output_dir)
        except Exception: pass
    return {"ok": True, "output_dir": str(output_dir), "report_dir": str(output_dir), "source_count": len(rows), "missing_count": report["missing_count"], "csv": str(csv_path)}
def load_latest_timeline(project_root: Path) -> list[dict[str, Any]]:
    for name in ["stt_prewedding_refined_v1.json","stt_prewedding_roughcut_v1.json","stt_prewedding_selection_v1.json"]:
        p = project_root / name
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data.get("timeline"), list): return data["timeline"]
    return []
def render_html(report: dict[str, Any]) -> str:
    rows = "".join(f"<tr><td>{r['exists']}</td><td>{r['filename']}</td><td>{r['parent']}</td><td>{r['timeline_count']}</td></tr>" for r in report["sources"])
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Relink Report</title><style>body{{font-family:Arial;background:#111;color:#eee;margin:32px}}.card{{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}}td,th{{border-bottom:1px solid #333;padding:8px}}</style></head><body><div class='card'><h1>Premiere Relink Report</h1><p>Missing: {report['missing_count']}</p><table><tr><th>Exists</th><th>Filename</th><th>Folder</th><th>Uses</th></tr>{rows}</table></div></body></html>"""
