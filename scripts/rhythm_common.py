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


def find_music(project: Path, music_folder: str | Path = "", explicit_music: str = "") -> str:
    if explicit_music and Path(explicit_music).exists():
        return str(Path(explicit_music))
    bridge = read_json(project / "stt_profile_music_sync_bridge_v1.json")
    mf = str(bridge.get("music_file") or "")
    if mf and Path(mf).exists():
        return mf
    folder = Path(music_folder) if music_folder else Path("D:/27thang6pschh")
    if folder.exists():
        files = []
        for ext in AUDIO_EXTS:
            files += list(folder.rglob(f"*{ext}"))
        files = sorted(files, key=lambda p: str(p).lower())
        if files:
            return str(files[0])
    return ""


def ffmpeg_pcm_mono(path: str | Path, sample_rate: int = 8000, duration_limit: int = 900) -> list[float]:
    try:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", str(path),
            "-t", str(duration_limit),
            "-vn",
            "-ac", "1",
            "-ar", str(sample_rate),
            "-f", "s16le",
            "pipe:1",
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        if r.returncode != 0 or not r.stdout:
            return []
        data = r.stdout
        vals = []
        # convert int16 little endian to float abs amplitude
        for i in range(0, len(data) - 1, 2):
            x = int.from_bytes(data[i:i+2], "little", signed=True)
            vals.append(x / 32768.0)
        return vals
    except Exception:
        return []


def energy_envelope(samples: list[float], sr: int = 8000, win_ms: int = 100) -> list[dict[str, float]]:
    if not samples:
        return []
    win = max(1, int(sr * win_ms / 1000))
    out = []
    for i in range(0, len(samples), win):
        chunk = samples[i:i+win]
        if not chunk:
            continue
        rms = math.sqrt(sum(x*x for x in chunk) / len(chunk))
        peak = max(abs(x) for x in chunk)
        out.append({"time_sec": round(i / sr, 3), "rms": round(rms, 6), "peak": round(peak, 6)})
    return out


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


def load_timeline(project: Path) -> dict[str, Any]:
    for name in [
        "stt_gapless_safe_timeline_v1.json",
        "stt_learned_inout_timeline_v1.json",
        "stt_profile_rhythm_timeline_v1.json",
        "stt_profile_story_timeline_v1.json",
    ]:
        d = read_json(project / name)
        if d:
            return d
    return {}
