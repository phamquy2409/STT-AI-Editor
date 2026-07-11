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


def media_duration(path: str | Path) -> float:
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


def load_base_timeline(project: Path) -> dict[str, Any]:
    for name in [
        "stt_profile_story_timeline_v1.json",
        "stt_learned_inout_timeline_v1.json",
        "stt_profile_rhythm_timeline_v1.json",
        "stt_gapless_safe_timeline_v1.json",
    ]:
        d = read_json(project / name)
        if d and d.get("items"):
            return d
    return {}


def energy_at(sections: list[dict[str, Any]], t: float) -> str:
    for s in sections:
        if fnum(s.get("start_sec"), 0) <= t < fnum(s.get("end_sec"), 0):
            return str(s.get("mood") or "mid_energy")
    return "mid_energy"


def nearest_beat(beats: list[dict[str, Any]], t: float, tolerance: float = 0.16) -> tuple[float, bool]:
    if not beats:
        return t, False
    best = None
    best_dist = 999
    for b in beats:
        bt = fnum(b.get("time_sec"), 0)
        d = abs(bt - t)
        if d < best_dist:
            best = bt
            best_dist = d
        if bt > t + tolerance + 1:
            break
    if best is not None and best_dist <= tolerance:
        return best, True
    return t, False


def section_duration_recipe(section: str, index: int, energy: str, voice_hold: bool, target_kind: str = "intimate") -> tuple[float, str]:
    if voice_hold:
        pattern = [4.2, 6.0, 3.4, 7.2, 5.0, 8.0, 3.8]
        return pattern[index % len(pattern)], "voice_emotion_hold"

    # stronger contrast; no more almost-equal cuts
    if section == "intro":
        pattern = [0.35, 0.48, 0.62, 1.25, 0.40, 1.85, 0.55, 2.60, 0.32, 0.80]
    elif section == "story":
        pattern = [0.90, 1.70, 0.65, 2.80, 1.10, 3.80, 0.80, 2.20, 4.80, 1.30]
    elif section == "build":
        pattern = [1.20, 2.60, 0.80, 3.70, 1.60, 5.40, 1.00, 2.20]
    elif section == "climax":
        pattern = [0.30, 0.42, 0.55, 0.85, 0.35, 1.40, 0.48, 2.40, 0.32, 3.20]
    elif section == "ending":
        pattern = [1.80, 3.20, 1.20, 4.80, 2.30, 6.80, 1.60]
    else:
        pattern = [1.0, 1.8, 0.8, 3.2, 1.2, 4.0]

    d = pattern[index % len(pattern)]

    # occasional very long emotional hold
    if index % 17 == 0 and section in {"story", "build", "ending"}:
        d *= 1.8
    # occasional burst
    if index % 11 == 0 and section in {"intro", "climax"}:
        d *= 0.55

    if energy == "high_energy":
        d *= 0.82
    elif energy == "low_energy":
        d *= 1.28

    return max(0.25, min(9.0, d)), "cinematic_short_long_pattern"


def voice_window_at(t: float, windows: list[dict[str, Any]]) -> bool:
    for w in windows:
        if fnum(w.get("start_sec"), 0) <= t <= fnum(w.get("end_sec"), 0):
            return True
    return False


def duration_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [fnum(x.get("duration_sec"), 0) for x in items if fnum(x.get("duration_sec"), 0) > 0]
    if not vals:
        return {}
    vals_sorted = sorted(vals)
    def pct(p: float) -> float:
        k = int(round((len(vals_sorted) - 1) * p))
        return round(vals_sorted[max(0, min(k, len(vals_sorted)-1))], 3)
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
