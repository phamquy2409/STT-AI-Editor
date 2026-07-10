
from __future__ import annotations
import csv
import json
import math
import os
import re
import shutil
import subprocess
import wave
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/5thang5test"
DEFAULT_MUSIC_FOLDER = "D:/STT Music"

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".aif", ".aiff", ".ogg", ".wma"}
VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi"}

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

def sec_to_frames(sec: float, timebase: int = 25) -> int:
    return int(round(max(0.0, sec) * timebase))

def frames_to_sec(frames: int, timebase: int = 25) -> float:
    return max(0.0, frames / max(1, timebase))

def file_url(path: str | Path) -> str:
    p = str(path).replace("\\", "/")
    return "file://localhost/" + quote(p, safe="/:")

def media_duration(path: Path, fallback: float = 180.0) -> float:
    # Try mutagen for audio.
    try:
        from mutagen import File as MutagenFile  # type: ignore
        m = MutagenFile(str(path))
        if m is not None and getattr(m, "info", None) is not None and getattr(m.info, "length", None):
            return round(float(m.info.length), 3)
    except Exception:
        pass

    # Try wav stdlib.
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w:
                frames = w.getnframes()
                rate = w.getframerate()
                if rate:
                    return round(frames / rate, 3)
        except Exception:
            pass

    # Try ffprobe if installed.
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            val = float(res.stdout.strip())
            if val > 0:
                return round(val, 3)
    except Exception:
        pass

    return fallback

def scan_audio_files(music_folder: str | Path) -> list[Path]:
    root = Path(music_folder)
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS], key=lambda p: str(p).lower())

def infer_bpm_from_name(name: str) -> float | None:
    low = name.lower()
    m = re.search(r"(\d{2,3})\s*bpm", low)
    if m:
        val = float(m.group(1))
        if 50 <= val <= 190:
            return val
    return None

def infer_mood_from_name(name: str) -> list[str]:
    low = name.lower()
    moods: list[str] = []
    checks = {
        "emotional": ["emotional", "emotion", "love", "romantic", "warm", "soft", "touching", "piano", "violin"],
        "cinematic": ["cinematic", "film", "trailer", "epic", "ambient", "atmos", "orchestra", "strings"],
        "wedding": ["wedding", "bride", "groom", "vow", "ceremony"],
        "party": ["party", "dance", "dj", "club", "beat", "funk", "disco"],
        "happy": ["happy", "joy", "bright", "uplift", "fun"],
        "sad": ["sad", "slow", "melancholy", "deep"],
    }
    for mood, words in checks.items():
        if any(w in low for w in words):
            moods.append(mood)
    if not moods:
        moods.append("unknown")
    return moods

def infer_bpm_default(moods: list[str], name: str = "") -> float:
    found = infer_bpm_from_name(name)
    if found:
        return found
    if "party" in moods:
        return 120.0
    if "happy" in moods:
        return 105.0
    if "cinematic" in moods:
        return 82.0
    if "emotional" in moods or "wedding" in moods:
        return 76.0
    return 90.0

def intent_music_profile(intent: str) -> dict[str, Any]:
    if intent == "wedding_teaser_60s":
        return {"moods": ["cinematic", "emotional", "wedding", "happy"], "bpm_min": 75, "bpm_max": 125, "target_seconds": 60}
    if intent == "wedding_highlight_3min":
        return {"moods": ["emotional", "cinematic", "wedding"], "bpm_min": 65, "bpm_max": 110, "target_seconds": 180}
    if intent == "gia_tien_story":
        return {"moods": ["emotional", "wedding", "cinematic"], "bpm_min": 55, "bpm_max": 90, "target_seconds": 180}
    if intent == "reception_story":
        return {"moods": ["happy", "party", "cinematic"], "bpm_min": 80, "bpm_max": 130, "target_seconds": 180}
    if intent == "dance_party":
        return {"moods": ["party", "happy"], "bpm_min": 100, "bpm_max": 140, "target_seconds": 60}
    return {"moods": ["emotional", "cinematic", "wedding"], "bpm_min": 60, "bpm_max": 105, "target_seconds": 180}

def load_current_timeline(project_root: Path) -> list[dict[str, Any]]:
    for name in [
        "stt_music_synced_timeline_v1.json",
        "stt_smart_wedding_timeline_v1.json",
        "stt_wedding_documentary_timeline_v1.json",
        "stt_beat_climax_timeline_v1.json",
        "stt_story_builder_v4_timeline.json",
        "stt_prewedding_refined_v1.json",
    ]:
        d = read_json(project_root / name)
        if isinstance(d.get("timeline"), list):
            return list(d["timeline"])
    return []

def html_table(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    import html
    th = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    tr = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>" for r in rows)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Arial;background:#111;color:#eee;margin:32px}"
        ".card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}</style></head>"
        f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{th}</tr>{tr}</table></div></body></html>"
    )


def music_score(track: dict[str, Any], intent: str, target_seconds: float) -> tuple[float, str]:
    profile = intent_music_profile(intent)
    moods = str(track.get("moods") or "").split("|")
    bpm = fnum(track.get("bpm"), 90)
    duration = fnum(track.get("duration_sec"), 180)

    score = 0.0
    reasons: list[str] = []

    for m in profile["moods"]:
        if m in moods:
            score += 25
            reasons.append(f"mood_{m}")

    if profile["bpm_min"] <= bpm <= profile["bpm_max"]:
        score += 22
        reasons.append("bpm_match")
    else:
        diff = min(abs(bpm - profile["bpm_min"]), abs(bpm - profile["bpm_max"]))
        score -= min(25, diff * 0.8)
        reasons.append("bpm_near" if diff < 20 else "bpm_far")

    if duration >= target_seconds:
        score += 18
        reasons.append("duration_enough")
    elif duration >= target_seconds * 0.75:
        score += 6
        reasons.append("duration_almost")
    else:
        score -= 20
        reasons.append("duration_short")

    low = str(track.get("filename") or "").lower()
    if "instrumental" in low or "no vocal" in low or "no-vocal" in low:
        score += 8
        reasons.append("instrumental_hint")
    if "preview" in low or "demo" in low:
        score -= 10
        reasons.append("preview_demo_hint")

    return round(score, 3), "|".join(reasons)

def create_auto_music_picker(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str = "wedding_documentary",
    target_seconds: float = 180.0,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "auto_music_picker")
    lib = read_json(project_root / "stt_music_library_v1.json") or read_json(appdata_dir() / "stt_music_library_v1.json")
    tracks = list(lib.get("tracks") or [])
    if not tracks:
        res = {"ok": False, "error": "NO_MUSIC_LIBRARY", "message": "Run 112 first with your music folder."}
        write_json(out / "auto_music_picker_error.json", res)
        if open_folder:
            open_path(out)
        return res

    scored = []
    for t in tracks:
        s, reason = music_score(t, intent=intent, target_seconds=target_seconds)
        new = dict(t)
        new["music_score"] = s
        new["pick_reason"] = reason
        scored.append(new)
    scored.sort(key=lambda x: (-fnum(x.get("music_score"), 0), str(x.get("filename","")).lower()))
    selected = scored[0] if scored else {}

    data = {
        "ok": True,
        "module": "113_auto_music_picker",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "intent": intent,
        "target_seconds": target_seconds,
        "selected": selected,
        "candidates": scored[:20],
    }
    write_json(project_root / "stt_selected_music_v1.json", data)
    write_json(appdata_dir() / "stt_selected_music_v1.json", data)
    write_json(out / "stt_selected_music_v1.json", data)
    write_csv(out / "AUTO_MUSIC_PICKER_TOP20.csv", scored[:20], ["filename","music_score","pick_reason","duration_sec","bpm","moods","file"])
    (out / "AUTO_MUSIC_PICKER_REPORT.html").write_text(
        html_table("Auto Music Picker", scored[:20], ["filename","music_score","pick_reason","duration_sec","bpm","moods"], f"Selected: {selected.get('filename','')}"),
        encoding="utf-8",
    )
    if open_folder:
        open_path(out)
    return {"ok": True, "report_dir": str(out), "selected_file": selected.get("file"), "selected_name": selected.get("filename"), "music_score": selected.get("music_score")}
