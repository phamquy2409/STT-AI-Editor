
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


def create_story_builder_v4(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "story_builder_v4")
    tl = load_timeline(project_root)
    if not tl:
        return {"ok": False, "error": "NO_TIMELINE", "message": "Run 102/105 first"}

    buckets = {"hook": [], "location": [], "couple": [], "detail": [], "story": [], "ending": []}
    for item in tl:
        role = str(item.get("role","general"))
        if role in {"bride","groom","vow"}:
            buckets["couple"].append(item)
        elif role == "detail":
            buckets["detail"].append(item)
        elif role == "location":
            buckets["location"].append(item)
        else:
            buckets["story"].append(item)

    ordered = []
    # Hook: 3 shot mạnh đầu
    pool = sorted(tl, key=lambda x: -float(x.get("score",50)))
    ordered += [dict(x, section="hook", story_reason="strong_opening") for x in pool[:3]]
    used = {str(x.get("file")) for x in ordered}
    # Middle: location -> couple -> detail -> story xen kẽ
    cycle = ["location","couple","detail","story","couple","detail"]
    pos = {k:0 for k in buckets}
    while len(ordered) < len(tl):
        added = False
        for k in cycle:
            while pos[k] < len(buckets[k]) and str(buckets[k][pos[k]].get("file")) in used:
                pos[k] += 1
            if pos[k] < len(buckets[k]):
                item = buckets[k][pos[k]]
                ordered.append(dict(item, section="middle", story_reason=f"alternate_{k}"))
                used.add(str(item.get("file")))
                pos[k] += 1
                added = True
                if len(ordered) >= len(tl):
                    break
        if not added:
            break
    # Ending: đổi 3 shot cuối thành ending
    for i, item in enumerate(ordered):
        item["index"] = i+1
        if i >= max(0, len(ordered)-3):
            item["section"] = "ending"
            item["story_reason"] = "ending_release"

    data = save_refined(project_root, ordered, "106_story_builder_v4", {"timeline_count": len(ordered)})
    write_json(project_root/"stt_story_builder_v4_timeline.json", data)
    write_json(out/"stt_story_builder_v4_timeline.json", data)
    write_csv(out/"STORY_BUILDER_V4_TIMELINE.csv", ordered, ["index","filename","role","section","story_reason","source_in","source_out","duration","file"])
    (out/"STORY_BUILDER_V4_TIMELINE.html").write_text(html("Story Builder V4", ordered, ["index","filename","role","section","story_reason","duration"], "Sắp xếp lại source theo hook/location/couple/detail/story/ending."), encoding="utf-8")
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "timeline_count": len(ordered)}
