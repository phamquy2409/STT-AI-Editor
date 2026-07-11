from __future__ import annotations
import csv, json, os, subprocess, math
from datetime import datetime
from pathlib import Path
from typing import Any

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}

def read_json(path: str | Path) -> dict[str, Any]:
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def write_csv(path: str | Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

def outdir(project: Path, name: str) -> Path:
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass

def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def norm_path(v: Any) -> str:
    return str(v or "").replace("\\", "/").strip().lower()

def media_duration(path: str | Path) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and (r.stdout or "").strip():
            return float((r.stdout or "").strip())
    except Exception:
        pass
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(path))
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            if fps > 0 and frames > 0:
                return float(frames / fps)
    except Exception:
        pass
    return 0.0

def duration_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [fnum(x.get("duration_sec"), 0) for x in items if fnum(x.get("duration_sec"), 0) > 0]
    if not vals:
        return {}
    xs = sorted(vals)
    def pct(p: float) -> float:
        return round(xs[int(round((len(xs)-1)*p))], 3)
    return {
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(sum(vals)/len(vals), 3),
        "p10": pct(0.10),
        "p50": pct(0.50),
        "p90": pct(0.90),
        "under_0_7s": sum(1 for v in vals if v < 0.7),
        "over_3s": sum(1 for v in vals if v > 3.0),
        "over_5s": sum(1 for v in vals if v > 5.0),
    }

def load_beauty(project: Path):
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path, by_name = {}, {}
    for r in d.get("items", []):
        p = norm_path(r.get("file"))
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name.setdefault(n, r)
    return by_path, by_name
