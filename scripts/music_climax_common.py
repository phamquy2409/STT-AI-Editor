from __future__ import annotations

import csv
import json
import math
import os
import statistics
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

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

def inum(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def mean(vals: list[float], default: float = 0.0) -> float:
    return sum(vals) / len(vals) if vals else default

def median(vals: list[float], default: float = 0.0) -> float:
    return float(statistics.median(vals)) if vals else default

def percentile(vals: list[float], p: float, default: float = 0.0) -> float:
    if not vals:
        return default
    xs = sorted(vals)
    idx = int(round((len(xs) - 1) * clamp(p, 0.0, 1.0)))
    return float(xs[idx])

def norm_path(v: Any) -> str:
    return str(v or "").replace("\\", "/").strip().lower()

def file_url(path: str | Path) -> str:
    p = str(path).replace("\\", "/")
    return "file://localhost/" + quote(p, safe="/:")

def media_duration(path: str | Path) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
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

def ffmpeg_pcm(path: str | Path, sample_rate: int = 11025, duration_limit: float = 0.0) -> list[float]:
    try:
        cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sample_rate)]
        if duration_limit > 0:
            cmd += ["-t", str(duration_limit)]
        cmd += ["-f", "f32le", "-"]
        r = subprocess.run(cmd, capture_output=True, timeout=240)
        if r.returncode != 0 or not r.stdout:
            return []
        import array
        a = array.array("f")
        a.frombytes(r.stdout)
        return [float(x) for x in a]
    except Exception:
        return []

def smooth(vals: list[float], radius: int = 2) -> list[float]:
    if not vals:
        return []
    out = []
    for i in range(len(vals)):
        a = max(0, i - radius)
        b = min(len(vals), i + radius + 1)
        out.append(mean(vals[a:b]))
    return out

def current_timeline(project: Path) -> dict[str, Any]:
    for name in [
        "stt_quality_moment_timeline_v1.json",
        "stt_taste_boosted_timeline_v1.json",
        "stt_beat_snapped_beauty_timeline_v1.json",
    ]:
        d = read_json(project / name)
        if d.get("items"):
            return d
    return {}

def timeline_duration(data: dict[str, Any]) -> float:
    if fnum(data.get("timeline_seconds"), 0) > 0:
        return fnum(data.get("timeline_seconds"), 0)
    rows = list(data.get("items") or [])
    return max([fnum(x.get("timeline_end_sec"), 0) for x in rows] + [0])

def load_quality(project: Path):
    d = read_json(project / "stt_shot_quality_windows_v3.json")
    by_path: dict[str, dict[str, Any]] = {}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for r in d.get("items") or []:
        p = norm_path(r.get("file"))
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name.setdefault(n, []).append(r)
    return by_path, by_name

def load_beauty(project: Path):
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for r in d.get("items") or []:
        p = norm_path(r.get("file"))
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name.setdefault(n, r)
    return by_path, by_name

def duration_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [fnum(x.get("duration_sec"), 0) for x in items if fnum(x.get("duration_sec"), 0) > 0]
    if not vals:
        return {}
    return {
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(mean(vals), 3),
        "p10": round(percentile(vals, 0.10), 3),
        "p50": round(percentile(vals, 0.50), 3),
        "p90": round(percentile(vals, 0.90), 3),
        "under_0_7s": sum(1 for v in vals if v < 0.7),
        "over_3s": sum(1 for v in vals if v > 3.0),
        "over_5s": sum(1 for v in vals if v > 5.0),
    }

def preset_size(preset: str) -> tuple[int, int]:
    low = preset.lower()
    if "vertical" in low or "1080_1920" in low:
        return 1080, 1920
    if "4k" in low:
        return 3840, 2160
    return 1920, 1080

def frames(sec: float, fps: int) -> int:
    return max(0, int(round(sec * fps)))

def seconds(fr: int, fps: int) -> float:
    return round(fr / max(1, fps), 4)
