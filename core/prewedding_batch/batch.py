
from __future__ import annotations
import json, os
from datetime import datetime
from pathlib import Path
from typing import Any
DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_INTENTS = ["prewedding_reel_30s", "prewedding_reel_60s", "prewedding_cinematic"]
def create_prewedding_batch_plan(project_root: str | Path = DEFAULT_PROJECT_ROOT, intents: list[str] | None = None, run: bool = False, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root); intents = intents or DEFAULT_INTENTS
    output_dir = project_root / "exports" / f"prewedding_batch_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs, results = [], []
    for intent in intents:
        preset = "vertical_1080_25p" if ("reel" in intent or "fashion" in intent) else "fhd_1080_25p"
        jobs.append({"intent": intent, "preset": preset, "command": f"python scripts/run_prewedding_pipeline.py --intent {intent} --preset {preset}", "status": "planned"})
    if run:
        from core.prewedding_pipeline import run_prewedding_pipeline
        for job in jobs:
            try:
                result = run_prewedding_pipeline(project_root=project_root, intent=job["intent"], preset=job["preset"], open_folder=False)
                job["status"] = "done" if result.get("ok") else "error"; results.append(result)
            except Exception as exc:
                job["status"] = "error"; job["error"] = repr(exc)
    plan = {"ok": True, "module": "055_prewedding_batch_plan", "project_root": str(project_root), "run": run, "jobs": jobs, "results": results}
    (output_dir / "prewedding_batch_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "BATCH_COMMANDS.txt").write_text("\n".join(j["command"] for j in jobs), encoding="utf-8")
    (output_dir / "BATCH_PLAN.html").write_text(render_html(plan), encoding="utf-8")
    if open_folder:
        try: os.startfile(output_dir)
        except Exception: pass
    return {"ok": True, "output_dir": str(output_dir), "report_dir": str(output_dir), "jobs": len(jobs), "run": run}
def render_html(plan: dict[str, Any]) -> str:
    rows = "".join(f"<tr><td>{j['intent']}</td><td>{j['preset']}</td><td><code>{j['command']}</code></td><td>{j['status']}</td></tr>" for j in plan["jobs"])
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Batch Plan</title><style>body{{font-family:Arial;background:#111;color:#eee;margin:32px}}.card{{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}}td,th{{border-bottom:1px solid #333;padding:8px}}code{{background:#000;padding:4px 8px;border-radius:8px}}</style></head><body><div class='card'><h1>Prewedding Batch Plan</h1><table><tr><th>Intent</th><th>Preset</th><th>Command</th><th>Status</th></tr>{rows}</table></div></body></html>"""
