
from __future__ import annotations
import json, os
from datetime import datetime
from pathlib import Path
from typing import Any
DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
TEMPLATES = {
 "prewedding_reel_60s":{"intent":"prewedding_reel_60s","preset":"vertical_1080_25p","duration":60,"style":"fast_but_emotional","commands":["python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s"]},
 "prewedding_reel_30s":{"intent":"prewedding_reel_30s","preset":"vertical_1080_25p","duration":30,"style":"fast_hook_beat_cut","commands":["python scripts/run_prewedding_pipeline.py --intent prewedding_reel_30s"]},
 "prewedding_cinematic":{"intent":"prewedding_cinematic","preset":"fhd_1080_25p","duration":120,"style":"smooth_cinematic","commands":["python scripts/run_prewedding_pipeline.py --intent prewedding_cinematic"]},
 "wedding_highlight_safe":{"intent":"wedding_highlight_3min","preset":"uhd_4k_25p","duration":180,"style":"wedding emotional, mix gia tien with reception, dance party ending","commands":["python scripts/run_gui.py","Run Final Wedding V2 + Live Review"]},
}
def create_workflow_templates(project_root: str | Path = DEFAULT_PROJECT_ROOT, open_folder: bool = True) -> dict[str, Any]:
    project_root=Path(project_root); out=project_root/"workflow_templates"; out.mkdir(parents=True, exist_ok=True)
    for name,data in TEMPLATES.items(): (out/f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    index={"ok":True,"module":"059_workflow_templates","created_at":datetime.now().isoformat(timespec="seconds"),"templates":list(TEMPLATES),"folder":str(out)}
    (out/"workflow_templates_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    (out/"WORKFLOW_TEMPLATES.html").write_text(render_html(index), encoding="utf-8")
    if open_folder:
        try: os.startfile(out)
        except Exception: pass
    return {"ok":True,"output_dir":str(out),"report_dir":str(out),"template_count":len(TEMPLATES)}
def render_html(index: dict[str, Any]) -> str:
    rows="".join(f"<tr><td>{name}</td></tr>" for name in index["templates"])
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Workflow Templates</title><style>body{{font-family:Arial;background:#111;color:#eee;margin:32px}}.card{{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}}td,th{{border-bottom:1px solid #333;padding:8px}}</style></head><body><div class='card'><h1>Workflow Templates</h1><p>{index['folder']}</p><table><tr><th>Template</th></tr>{rows}</table></div></body></html>"""
