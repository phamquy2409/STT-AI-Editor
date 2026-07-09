
from __future__ import annotations
import csv, json, os
from datetime import datetime
from pathlib import Path
from typing import Any
DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
def create_music_beat_plan(project_root: str | Path = DEFAULT_PROJECT_ROOT, bpm: float = 90.0, open_folder: bool = True) -> dict[str, Any]:
    project_root = Path(project_root); output_dir = project_root / "exports" / f"music_beat_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True); timeline = load_latest_timeline(project_root)
    interval = 60.0 / float(bpm); total = sum(float(x.get("timeline_duration",0) or 0) for x in timeline)
    beats=[]; t=0.0; i=1
    while t <= total + 0.001:
        beats.append({"beat": i, "time_seconds": round(t,3), "bar": ((i-1)//4)+1, "beat_in_bar": ((i-1)%4)+1}); t += interval; i += 1
    clips=[]
    for clip in timeline:
        start=float(clip.get("timeline_start",0) or 0); end=float(clip.get("timeline_end", start+float(clip.get("timeline_duration",0) or 0)) or 0)
        nearest=min(beats, key=lambda b: abs(b["time_seconds"]-start)) if beats else None
        clips.append({"timeline_index":clip.get("timeline_index"),"start":start,"end":end,"role":clip.get("roughcut_role") or clip.get("section"),"nearest_beat": nearest["beat"] if nearest else "", "nearest_beat_time": nearest["time_seconds"] if nearest else "", "file":clip.get("file")})
    with (output_dir/"MUSIC_BEAT_MARKERS.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=["beat","time_seconds","bar","beat_in_bar"]); w.writeheader(); w.writerows(beats)
    with (output_dir/"CLIP_BEAT_CUT_PLAN.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=["timeline_index","start","end","role","nearest_beat","nearest_beat_time","file"]); w.writeheader(); w.writerows(clips)
    plan={"ok":True,"module":"057_music_beat_plan","bpm":bpm,"duration":round(total,3),"beats":beats,"clips":clips}
    (output_dir/"music_beat_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir/"MUSIC_BEAT_PLAN.html").write_text(render_html(plan), encoding="utf-8")
    if open_folder:
        try: os.startfile(output_dir)
        except Exception: pass
    return {"ok": True, "output_dir": str(output_dir), "report_dir": str(output_dir), "bpm": bpm, "duration": round(total,3), "beats": len(beats), "clips": len(clips)}
def load_latest_timeline(project_root: Path) -> list[dict[str, Any]]:
    for name in ["stt_prewedding_refined_v1.json","stt_prewedding_roughcut_v1.json","stt_prewedding_selection_v1.json"]:
        p=project_root/name
        if p.exists():
            data=json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data.get("timeline"), list): return data["timeline"]
    return []
def render_html(plan: dict[str, Any]) -> str:
    rows="".join(f"<tr><td>{c['timeline_index']}</td><td>{c['start']}</td><td>{c['role']}</td><td>{c['nearest_beat']}</td><td>{c['file']}</td></tr>" for c in plan["clips"])
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Beat Plan</title><style>body{{font-family:Arial;background:#111;color:#eee;margin:32px}}.card{{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}}td,th{{border-bottom:1px solid #333;padding:8px}}</style></head><body><div class='card'><h1>Music Beat Plan</h1><p>BPM: {plan['bpm']} / Duration: {plan['duration']}s</p><table><tr><th>#</th><th>Start</th><th>Role</th><th>Nearest beat</th><th>File</th></tr>{rows}</table></div></body></html>"""
