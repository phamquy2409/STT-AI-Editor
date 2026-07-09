
from __future__ import annotations
import json, os
from datetime import datetime
from pathlib import Path
from typing import Any
DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
def create_master_dashboard(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root=Path(project_root); output_dir=project_root/"exports"/f"master_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    files={}
    for name in ["manual_selection.json","stt_ai_shot_scores_v1.json","stt_prewedding_selection_v1.json","stt_prewedding_roughcut_v1.json","stt_prewedding_refined_v1.json","stt_prewedding_premiere_import.xml","stt_prewedding_pipeline_v1.json"]:
        p=project_root/name; files[name]={"exists":p.exists(),"path":str(p),"size_bytes":p.stat().st_size if p.exists() else 0}
    latest=[]; exports=project_root/"exports"
    if exports.exists():
        dirs=[p for p in exports.iterdir() if p.is_dir() and p.name != "_archive"]
        for p in sorted(dirs,key=lambda x:x.stat().st_mtime, reverse=True)[:30]:
            latest.append({"name":p.name,"path":str(p),"modified":datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")})
    try:
        from core.prewedding_doctor import check_prewedding_pipeline
        doctor=check_prewedding_pipeline(project_root=project_root, open_folder=False)
    except Exception as exc:
        doctor={"ok":False,"error":repr(exc)}
    dash={"ok":True,"module":"060_master_dashboard","created_at":datetime.now().isoformat(timespec="seconds"),"project_root":str(project_root),"files":files,"latest_exports":latest,"doctor":doctor}
    html_path=output_dir/"STT_MASTER_DASHBOARD.html"; json_path=output_dir/"stt_master_dashboard.json"
    json_path.write_text(json.dumps(dash, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_html(dash), encoding="utf-8")
    if open_folder:
        try: os.startfile(html_path)
        except Exception:
            try: os.startfile(output_dir)
            except Exception: pass
    return {"ok":True,"output_dir":str(output_dir),"report_dir":str(output_dir),"dashboard_html":str(html_path),"file_count":len(files),"latest_exports":len(latest)}
def render_html(d: dict[str, Any]) -> str:
    file_rows="".join(f"<tr><td>{n}</td><td>{i['exists']}</td><td>{i['size_bytes']}</td></tr>" for n,i in d["files"].items())
    export_rows="".join(f"<tr><td>{x['name']}</td><td>{x['modified']}</td></tr>" for x in d["latest_exports"])
    doctor=d.get("doctor") or {}
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>STT Master Dashboard</title><style>body{{font-family:Arial;background:#111;color:#eee;margin:32px}}.card{{background:#181818;border:1px solid #333;border-radius:16px;padding:24px;margin-bottom:18px}}td,th{{border-bottom:1px solid #333;padding:8px;text-align:left}}code{{background:#000;padding:4px 8px;border-radius:8px}}</style></head><body><div class='card'><h1>STT AI Editor Master Dashboard</h1><p>Project: <code>{d['project_root']}</code></p><p>Doctor ready pipeline: {doctor.get('ready_for_pipeline')}</p><p>Doctor ready Premiere: {doctor.get('ready_for_premiere')}</p></div><div class='card'><h2>Project Files</h2><table><tr><th>File</th><th>Exists</th><th>Bytes</th></tr>{file_rows}</table></div><div class='card'><h2>Latest Exports</h2><table><tr><th>Folder</th><th>Modified</th></tr>{export_rows}</table></div><div class='card'><h2>Useful Commands</h2><ol><li><code>python scripts/check_prewedding_pipeline.py</code></li><li><code>python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s</code></li><li><code>python scripts/build_exe.py</code></li><li><code>python scripts/package_release.py</code></li></ol></div></body></html>"""
