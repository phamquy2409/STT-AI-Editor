
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


def beat_duration_options(event: str, section: str, bpm: float) -> list[int]:
    # số beat/clip
    event = str(event or "")
    section = str(section or "")
    if section == "climax":
        return [2, 1, 4]
    if event in {"gia_tien", "vow_speech"}:
        return [8, 6, 4]
    if event in {"getting_ready", "details", "ruoc_dau", "reception"}:
        return [4, 6, 3]
    if event == "dance_party":
        return [2, 4, 1]
    return [4, 3, 2]

def choose_beat_span(desired_sec: float, beat_sec: float, event: str, section: str) -> float:
    opts = beat_duration_options(event, section, 60.0 / max(0.1, beat_sec))
    best = opts[0]
    best_diff = 9999.0
    for beats in opts:
        dur = beats * beat_sec
        diff = abs(dur - desired_sec)
        if diff < best_diff:
            best = beats
            best_diff = diff
    return max(0.5, best * beat_sec)

def create_music_sync_timeline_builder(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    target_seconds: float = 180.0,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "music_sync_timeline_builder")
    timeline = load_current_timeline(project_root)
    beatmap = read_json(project_root / "stt_music_beat_map_v1.json") or read_json(appdata_dir() / "stt_music_beat_map_v1.json")
    if not timeline:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 111B first."}
        write_json(out / "music_sync_timeline_builder_error.json", res)
        if open_folder:
            open_path(out)
        return res
    if not isinstance(beatmap.get("beats"), list):
        res = {"ok": False, "error": "NO_BEAT_MAP", "message": "Run 114 first."}
        write_json(out / "music_sync_timeline_builder_error.json", res)
        if open_folder:
            open_path(out)
        return res

    bpm = fnum(beatmap.get("bpm"), 80)
    beat_sec = 60.0 / max(40.0, min(200.0, bpm))
    music_duration = fnum(beatmap.get("duration_sec"), target_seconds)
    target = min(target_seconds, music_duration) if target_seconds > 0 else music_duration

    new_timeline: list[dict[str, Any]] = []
    cursor = 0.0
    n = len(timeline)

    for idx, item in enumerate(timeline, start=1):
        event = str(item.get("event") or item.get("role") or "general")
        pos = idx / max(1, n)
        if idx <= 3:
            section = "intro"
        elif 0.62 <= pos <= 0.84:
            section = "climax"
        elif pos >= 0.88:
            section = "ending"
        else:
            section = str(item.get("section") or "story")

        desired = fnum(item.get("duration"), fnum(item.get("duration_sec"), 2.5))
        dur = choose_beat_span(desired, beat_sec, event, section)

        remaining_items = max(1, n - idx + 1)
        remaining_time = max(0.75 * remaining_items, target - cursor)
        if cursor + dur > target and idx < n:
            dur = max(0.75, remaining_time / remaining_items)

        src_dur = max(1.0, fnum(item.get("source_duration_sec"), fnum(item.get("duration_sec"), 10.0)))
        src_in_sec = fnum(item.get("source_in"), 0) / timebase
        if src_in_sec + dur > src_dur:
            src_in_sec = max(0.0, src_dur - dur - 0.1)
        src_out_sec = min(src_dur, src_in_sec + dur)

        new = dict(item)
        new.update({
            "index": len(new_timeline) + 1,
            "timeline_start": sec_to_frames(cursor, timebase),
            "timeline_end": sec_to_frames(cursor + (src_out_sec - src_in_sec), timebase),
            "source_in": sec_to_frames(src_in_sec, timebase),
            "source_out": sec_to_frames(src_out_sec, timebase),
            "duration": round(src_out_sec - src_in_sec, 3),
            "duration_sec": round(src_out_sec - src_in_sec, 3),
            "music_section": section,
            "music_sync": True,
            "reason": str(item.get("reason","")) + f"__115_music_sync bpm={bpm} section={section}",
        })
        new_timeline.append(new)
        cursor += max(0.1, src_out_sec - src_in_sec)
        if cursor >= target:
            break

    data = {
        "ok": True,
        "module": "115_music_sync_timeline_builder",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "target_seconds": target_seconds,
        "music_duration_sec": music_duration,
        "timeline_seconds": round(sum(fnum(x.get("duration"),0) for x in new_timeline), 3),
        "bpm": bpm,
        "timeline_count": len(new_timeline),
        "timeline": new_timeline,
    }
    for name in [
        "stt_music_synced_timeline_v1.json",
        "stt_smart_wedding_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        write_json(project_root / name, data)
    write_json(appdata_dir() / "stt_prewedding_refined_v1.json", data)
    write_json(out / "stt_music_synced_timeline_v1.json", data)
    write_csv(out / "MUSIC_SYNC_TIMELINE.csv", new_timeline, ["index","filename","event","music_section","timeline_start","timeline_end","source_in","source_out","duration","music_sync","file"])
    (out / "MUSIC_SYNC_TIMELINE_REPORT.html").write_text(
        html_table("Music Sync Timeline Builder", new_timeline, ["index","filename","event","music_section","duration","timeline_start","timeline_end"], "Timeline đã co duration theo nhịp beat."),
        encoding="utf-8",
    )
    if open_folder:
        open_path(out)
    return {"ok": True, "report_dir": str(out), "timeline_count": len(new_timeline), "timeline_seconds": data["timeline_seconds"], "bpm": bpm}
