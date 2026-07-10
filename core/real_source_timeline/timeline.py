
from __future__ import annotations
import csv, json, os, math, statistics
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/5thang5test"
MEDIA_EXTS = {".mp4",".mov",".mxf",".mts",".m2ts",".avi"}

def appdata_dir() -> Path:
    p = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}

def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

def outdir(project_root: Path, name: str) -> Path:
    p = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def open_path(path: Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass

def source_files(source_folder: str | Path) -> list[Path]:
    root = Path(source_folder)
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXTS], key=lambda p: str(p).lower())

def probe_media(path: Path) -> dict[str, Any]:
    # Metadata only, no heavy decode. If cv2 missing/fails, use safe defaults.
    info = {"fps": 25.0, "frames": 250, "duration_sec": 10.0, "width": 0, "height": 0, "ok": False}
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(path))
        if cap.isOpened():
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            dur = frames / fps if fps > 0 and frames > 0 else 10.0
            info.update({"fps": fps, "frames": frames, "duration_sec": max(1.0, dur), "width": width, "height": height, "ok": True})
        cap.release()
    except Exception:
        pass
    return info

def classify_file(path: Path) -> str:
    low = path.name.lower()
    if any(x in low for x in ["bride","codau","co_dau","cô","co-dau"]): return "bride"
    if any(x in low for x in ["groom","chure","chu_re","chú","chu-re"]): return "groom"
    if any(x in low for x in ["detail","ring","dress","flower","shoe","decor"]): return "detail"
    if any(x in low for x in ["drone","flycam","wide","establish"]): return "location"
    if any(x in low for x in ["vow","speech","voice"]): return "vow"
    if any(x in low for x in ["dance","party"]): return "party"
    return "general"

def base_score(path: Path, info: dict[str, Any]) -> float:
    role = classify_file(path)
    score = 50.0
    if role in {"bride","groom","vow"}: score += 18
    if role in {"detail","location"}: score += 10
    if role == "party": score += 6
    size_mb = path.stat().st_size / (1024*1024)
    if size_mb > 80: score += 8
    elif size_mb > 20: score += 4
    if info.get("duration_sec", 0) < 2.0: score -= 30
    if info.get("width",0) >= 3000: score += 3
    return round(score, 3)

def load_timeline(project_root: Path) -> list[dict[str, Any]]:
    for p in [
        project_root/"stt_beat_climax_timeline_v1.json",
        project_root/"stt_story_builder_v4_timeline.json",
        project_root/"stt_smart_inout_timeline_v1.json",
        project_root/"stt_real_source_timeline_v1.json",
        project_root/"stt_prewedding_refined_v1.json",
    ]:
        d = read_json(p)
        if isinstance(d.get("timeline"), list):
            return list(d["timeline"])
    return []

def load_report_items(project_root: Path, filenames: list[str]) -> dict[str, dict[str, Any]]:
    result = {}
    for fname in filenames:
        d = read_json(project_root / fname)
        for key in ["items", "shots", "timeline"]:
            if isinstance(d.get(key), list):
                for item in d[key]:
                    f = str(item.get("file") or item.get("path") or "")
                    if f:
                        result[Path(f).name.lower()] = item
    return result

def save_refined(project_root: Path, timeline: list[dict[str, Any]], module: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    data = {"ok": True, "module": module, "updated_at": datetime.now().isoformat(timespec="seconds"), "timeline": timeline}
    if extra:
        data.update(extra)
    write_json(project_root / "stt_prewedding_refined_v1.json", data)
    write_json(appdata_dir() / "stt_prewedding_refined_v1.json", data)
    return data

def html(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    import html as h
    th = "".join(f"<th>{h.escape(str(c))}</th>" for c in cols)
    tr = "".join("<tr>" + "".join(f"<td>{h.escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>" for r in rows)
    return "<!doctype html><html><head><meta charset='utf-8'><style>body{font-family:Arial;background:#111;color:#eee;margin:32px}.card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}td,th{border-bottom:1px solid #333;padding:8px;text-align:left}</style></head><body><div class='card'><h1>"+h.escape(title)+"</h1><p>"+h.escape(note)+"</p><table><tr>"+th+"</tr>"+tr+"</table></div></body></html>"

def sec_to_frames(sec: float, timebase: int = 25) -> int:
    return int(round(max(0.04, sec) * timebase))


def create_real_source_timeline(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    intent: str = "prewedding_reel_60s",
    target_seconds: float = 60.0,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    files = source_files(source_folder)
    out = outdir(project_root, "real_source_timeline")
    items = []
    for p in files:
        info = probe_media(p)
        items.append({
            "file": str(p),
            "filename": p.name,
            "role": classify_file(p),
            "score": base_score(p, info),
            "duration_sec_source": round(float(info.get("duration_sec", 10.0)), 3),
            "fps": info.get("fps", 25.0),
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "size_mb": round(p.stat().st_size/(1024*1024), 2),
        })

    # chọn source thật, không dùng prewedding_clip giả nữa
    items = sorted(items, key=lambda x: (-float(x["score"]), x["filename"]))
    timeline = []
    total = 0.0
    for i, it in enumerate(items, 1):
        if total >= target_seconds:
            break
        role = it["role"]
        dur = 1.2 if i <= 3 else (2.0 if role in {"detail","location"} else 2.8)
        if role in {"bride","groom","vow"}:
            dur = 3.4
        if total + dur > target_seconds:
            dur = max(0.8, target_seconds-total)
        source_dur = max(1.0, float(it["duration_sec_source"]))
        start_sec = min(max(0.0, source_dur*0.18), max(0.0, source_dur-dur-0.2))
        end_sec = min(source_dur, start_sec + dur)
        timeline.append({
            "index": len(timeline)+1,
            "file": it["file"],
            "filename": it["filename"],
            "role": role,
            "score": it["score"],
            "source_in": sec_to_frames(start_sec, timebase),
            "source_out": sec_to_frames(end_sec, timebase),
            "duration": round(end_sec-start_sec, 3),
            "duration_sec": round(end_sec-start_sec, 3),
            "reason": "real_source_path_selected",
        })
        total += max(0.1, end_sec-start_sec)

    data = save_refined(project_root, timeline, "102_pipeline_real_source_timeline_fix", {
        "intent": intent,
        "source_folder": str(source_folder),
        "source_media_count": len(files),
        "target_seconds": target_seconds,
        "timeline_seconds": round(sum(float(x["duration"]) for x in timeline), 3),
    })
    write_json(project_root/"stt_real_source_timeline_v1.json", data)
    write_json(out/"stt_real_source_timeline_v1.json", data)
    write_csv(out/"REAL_SOURCE_TIMELINE.csv", timeline, ["index","filename","role","score","source_in","source_out","duration","reason","file"])
    (out/"REAL_SOURCE_TIMELINE.html").write_text(html("Real Source Timeline", timeline, ["index","filename","role","score","source_in","source_out","duration","reason"], "Timeline có path source thật, không còn prewedding_clip_1."), encoding="utf-8")
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "timeline_count": len(timeline), "source_media_count": len(files), "refined_json": str(project_root/"stt_prewedding_refined_v1.json")}
