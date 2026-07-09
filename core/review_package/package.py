
from __future__ import annotations
import csv, json, os, zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
def create_review_package(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root=Path(project_root); stamp=datetime.now().strftime("%Y%m%d_%H%M%S"); output_dir=project_root/"exports"/f"review_package_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=True); timeline=load_latest_timeline(project_root)
    rows=[{"index":c.get("timeline_index"),"time":f"{c.get('timeline_start')}-{c.get('timeline_end')}","role":c.get("roughcut_role") or c.get("section"),"score":c.get("ai_score"),"note":c.get("review_note") or c.get("refiner_reason") or "","file":c.get("file")} for c in timeline]
    with (output_dir/"REVIEW_CLIP_LIST.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=["index","time","role","score","note","file"]); w.writeheader(); w.writerows(rows)
    package={"ok":True,"module":"058_review_package","project_root":str(project_root),"clip_count":len(rows),"clips":rows}
    (output_dir/"review_package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir/"REVIEW_PACKAGE.html").write_text(render_html(package), encoding="utf-8")
    (output_dir/"REVIEW_NOTES_FOR_EDITOR.txt").write_text(render_text(package), encoding="utf-8")
    zip_path=project_root/"exports"/f"review_package_{stamp}.zip"
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
        for p in output_dir.rglob("*"):
            if p.is_file(): z.write(p, p.relative_to(output_dir.parent))
    if open_folder:
        try: os.startfile(output_dir)
        except Exception: pass
    return {"ok":True,"output_dir":str(output_dir),"report_dir":str(output_dir),"zip":str(zip_path),"clip_count":len(rows)}
def load_latest_timeline(project_root: Path) -> list[dict[str, Any]]:
    for name in ["stt_prewedding_refined_v1.json","stt_prewedding_roughcut_v1.json","stt_prewedding_selection_v1.json"]:
        p=project_root/name
        if p.exists():
            data=json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data.get("timeline"), list): return data["timeline"]
    return []
def render_text(package: dict[str, Any]) -> str:
    lines=["STT AI Editor - Review Package","="*72,f"Clips: {package['clip_count']}",""]
    for c in package["clips"]: lines.append(f"{c['index']}. {c['time']} | {c['role']} | score {c['score']} | {c['file']}")
    return "\n".join(lines)
def render_html(package: dict[str, Any]) -> str:
    rows="".join(f"<tr><td>{c['index']}</td><td>{c['time']}</td><td>{c['role']}</td><td>{c['score']}</td><td>{c['note']}</td><td>{c['file']}</td></tr>" for c in package["clips"])
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Review Package</title><style>body{{font-family:Arial;background:#111;color:#eee;margin:32px}}.card{{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}}td,th{{border-bottom:1px solid #333;padding:8px}}</style></head><body><div class='card'><h1>Review Package</h1><p>Clips: {package['clip_count']}</p><table><tr><th>#</th><th>Time</th><th>Role</th><th>Score</th><th>Note</th><th>File</th></tr>{rows}</table></div></body></html>"""
