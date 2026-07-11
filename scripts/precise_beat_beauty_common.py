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
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".aif", ".aiff", ".flac"}
SECTION_ORDER = ["intro", "story", "build", "climax", "ending"]


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


def norm_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").lower()


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


def find_music(project: Path, music_folder: str = "", explicit_music: str = "") -> str:
    if explicit_music and Path(explicit_music).exists():
        return str(Path(explicit_music))
    for j in ["stt_music_director_map_v1.json", "stt_music_beat_map_v1.json"]:
        d = read_json(project / j)
        mf = str(d.get("music_file") or "")
        if mf and Path(mf).exists():
            return mf
    folder = Path(music_folder) if music_folder else Path("D:/27thang6pschh")
    files = []
    if folder.exists():
        for ext in AUDIO_EXTS:
            files.extend(folder.rglob(f"*{ext}"))
    files = sorted(set(files), key=lambda p: str(p).lower())
    return str(files[0]) if files else ""


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


def ffmpeg_pcm(path: str | Path, sample_rate: int = 11025, duration_limit: int = 900) -> list[float]:
    try:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", str(path),
            "-t", str(duration_limit),
            "-vn", "-ac", "1", "-ar", str(sample_rate),
            "-f", "s16le", "pipe:1",
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=90)
        if r.returncode != 0 or not r.stdout:
            return []
        data = r.stdout
        vals = []
        for i in range(0, len(data) - 1, 2):
            x = int.from_bytes(data[i:i+2], "little", signed=True)
            vals.append(x / 32768.0)
        return vals
    except Exception:
        return []


def percentile(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    xs = sorted(vals)
    k = int(round((len(xs) - 1) * p))
    return xs[max(0, min(k, len(xs)-1))]


def load_blocks(project: Path, target_seconds: int) -> list[dict[str, Any]]:
    manual = project / "stt_music_director_manual.csv"
    rows = read_csv(manual)
    allowed = {"quiet_hold", "emotion_long", "story_medium", "build_fast", "climax_fast", "impact_cut", "ending_hold"}
    blocks = []
    for r in rows:
        st = fnum(r.get("start_sec"), -1)
        en = fnum(r.get("end_sec"), -1)
        mode = str(r.get("mode") or "").strip()
        if st >= 0 and en > st and mode in allowed:
            blocks.append({"start_sec": st, "end_sec": min(en, target_seconds), "mode": mode, "note": r.get("note", "manual")})
    if blocks:
        return sorted(blocks, key=lambda x: fnum(x.get("start_sec"), 0))

    d = read_json(project / "stt_music_director_map_v1.json")
    blocks = list(d.get("director_blocks") or [])
    if blocks:
        return blocks

    return [
        {"start_sec": 0, "end_sec": 24, "mode": "quiet_hold", "note": "fallback"},
        {"start_sec": 24, "end_sec": 110, "mode": "story_medium", "note": "fallback"},
        {"start_sec": 110, "end_sec": 190, "mode": "emotion_long", "note": "fallback"},
        {"start_sec": 190, "end_sec": 285, "mode": "build_fast", "note": "fallback"},
        {"start_sec": 285, "end_sec": 375, "mode": "climax_fast", "note": "fallback"},
        {"start_sec": 375, "end_sec": target_seconds, "mode": "ending_hold", "note": "fallback"},
    ]


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
