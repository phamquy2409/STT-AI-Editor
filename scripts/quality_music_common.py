from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.sax.saxutils import escape

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


def read_csv(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def write_csv(path: str | Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def outdir(project: Path, name: str) -> Path:
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def fr(sec: float, fps: int) -> int:
    return max(0, int(round(float(sec) * fps)))


def sec(frames: int, fps: int) -> float:
    return round(frames / fps, 3) if fps else 0.0


def pathurl_for(path: str | Path) -> str:
    p = str(path).replace("\\", "/")
    return "file://localhost/" + quote(p, safe="/:")


def preset_size(preset: str) -> tuple[int, int]:
    p = preset.lower()
    if "vertical" in p or "9x16" in p:
        return 1080, 1920
    if "1080" in p:
        return 1920, 1080
    return 3840, 2160


def norm_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").lower()


def media_duration_ffprobe(path: str | Path) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and (r.stdout or "").strip():
            return float((r.stdout or "").strip())
    except Exception:
        pass
    return 0.0


def media_duration_cv2(path: str | Path) -> float:
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return 0.0
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        cap.release()
        if fps > 0 and frames > 0:
            return float(frames / fps)
    except Exception:
        pass
    return 0.0


_duration_cache: dict[str, float] = {}


def media_duration(path: str | Path) -> float:
    key = norm_path(path)
    if key in _duration_cache:
        return _duration_cache[key]
    d = media_duration_ffprobe(path)
    if d <= 0:
        d = media_duration_cv2(path)
    _duration_cache[key] = round(d, 3) if d > 0 else 0.0
    return _duration_cache[key]


def load_base_timeline(project: Path) -> dict[str, Any]:
    for name in [
        "stt_quality_filtered_source_timeline_v1.json",
        "stt_profile_story_timeline_v1.json",
        "stt_learned_inout_timeline_v1.json",
        "stt_profile_rhythm_timeline_v1.json",
    ]:
        d = read_json(project / name)
        if d and d.get("items"):
            return d
    return {}


def load_director_blocks(project: Path) -> list[dict[str, Any]]:
    manual = project / "stt_music_director_manual.csv"
    rows = read_csv(manual)
    allowed = {"quiet_hold", "emotion_long", "story_medium", "build_fast", "climax_fast", "impact_cut", "ending_hold"}
    good: list[dict[str, Any]] = []
    for r in rows:
        st = fnum(r.get("start_sec"), -1)
        en = fnum(r.get("end_sec"), -1)
        mode = str(r.get("mode") or "").strip()
        if st >= 0 and en > st and mode in allowed:
            good.append({
                "start_sec": round(st, 3),
                "end_sec": round(en, 3),
                "mode": mode,
                "note": (r.get("note") or "manual").strip(),
            })
    if good:
        return sorted(good, key=lambda x: fnum(x.get("start_sec"), 0))

    d = read_json(project / "stt_music_director_map_v1.json")
    return list(d.get("director_blocks") or [])


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


def quality_lookup(project: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    d = read_json(project / "stt_source_quality_v3.json")
    by_path: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for row in d.get("items", []):
        p = norm_path(row.get("file", ""))
        n = str(row.get("filename", "")).lower()
        if p:
            by_path[p] = row
        if n:
            # only first filename match, path is safer
            by_name.setdefault(n, row)
    return by_path, by_name


def get_quality_for_item(item: dict[str, Any], by_path: dict[str, dict[str, Any]], by_name: dict[str, dict[str, Any]]) -> dict[str, Any]:
    p = norm_path(item.get("file", ""))
    n = str(item.get("filename") or Path(str(item.get("file", ""))).name).lower()
    if p in by_path:
        return by_path[p]
    if n in by_name:
        return by_name[n]
    return {
        "quality_score": 45,
        "usable": False,
        "quality_class": "unknown_not_analyzed",
        "reject_reasons": "not_analyzed",
        "motion_class": "unknown",
        "filename": n,
        "file": item.get("file", ""),
    }
