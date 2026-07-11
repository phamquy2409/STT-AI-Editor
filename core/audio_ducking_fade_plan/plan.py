
from __future__ import annotations

import csv
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.dom import minidom

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/5thang5test"


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


def html_table(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    import html
    th = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    tr = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>"
        for r in rows
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Arial;background:#111;color:#eee;margin:32px}"
        ".card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}</style></head>"
        f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{th}</tr>{tr}</table></div></body></html>"
    )


def load_timeline(project_root: Path) -> list[dict[str, Any]]:
    for name in [
        "stt_music_section_aware_timeline_v1.json",
        "stt_emotion_rhythm_timeline_v1.json",
        "stt_beat_sync_v2_timeline_v1.json",
        "stt_beat_locked_timeline_v1.json",
        "stt_music_synced_timeline_v1.json",
        "stt_smart_wedding_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        d = read_json(project_root / name)
        if isinstance(d.get("timeline"), list):
            return list(d["timeline"])
    return []


def load_analyzer_items(project_root: Path) -> list[dict[str, Any]]:
    d = read_json(project_root / "stt_wedding_source_analyzer_v2.json") or read_json(appdata_dir() / "stt_wedding_source_analyzer_v2.json")
    return list(d.get("items") or [])


def load_music(project_root: Path) -> dict[str, Any]:
    d = read_json(project_root / "stt_selected_music_v1.json") or read_json(appdata_dir() / "stt_selected_music_v1.json")
    if isinstance(d.get("selected"), dict):
        return d["selected"]
    return {}


def load_music_plan(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / "stt_music_plan_v1.json") or read_json(appdata_dir() / "stt_music_plan_v1.json")


def load_beat_data(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / "stt_real_audio_beat_energy_v1.json") or read_json(appdata_dir() / "stt_real_audio_beat_energy_v1.json")


def norm_event(event: str) -> str:
    event = str(event or "general")
    aliases = {
        "family": "gia_tien",
        "ceremony": "gia_tien",
        "traditional": "gia_tien",
        "speech": "vow_speech",
        "vow": "vow_speech",
        "party": "dance_party",
        "dance": "dance_party",
    }
    return aliases.get(event, event)


def event_rank_for_section(event: str, section: str) -> int:
    event = norm_event(event)
    prefs = {
        "intro": ["details", "getting_ready", "gia_tien", "reception", "ruoc_dau", "vow_speech", "dance_party"],
        "story": ["getting_ready", "details", "gia_tien", "ruoc_dau", "reception", "vow_speech", "dance_party"],
        "build": ["gia_tien", "ruoc_dau", "reception", "vow_speech", "details", "dance_party", "getting_ready"],
        "climax": ["vow_speech", "reception", "dance_party", "gia_tien", "ruoc_dau", "details", "getting_ready"],
        "ending": ["vow_speech", "dance_party", "reception", "details", "gia_tien", "ruoc_dau", "getting_ready"],
    }.get(section, [])
    return prefs.index(event) if event in prefs else 99


def quality_rank(item: dict[str, Any]) -> float:
    score = fnum(item.get("score"), 0)
    decision = str(item.get("decision") or "").lower()
    flags = str(item.get("quality_flags") or "")
    motion = fnum(item.get("motion_score"), 0)
    blur = fnum(item.get("blur_score"), 0)
    if decision == "strong_pick":
        score += 25
    elif decision == "keep":
        score += 12
    elif decision == "review":
        score -= 2
    if "possible_out_focus" in flags:
        score -= 25
    if "too_dark" in flags or "too_bright" in flags:
        score -= 20
    if motion > 55:
        score -= 12
    elif 4 <= motion <= 35:
        score += 5
    if blur >= 120:
        score += 6
    elif 0 < blur < 35:
        score -= 12
    return round(score, 3)


def section_for_time(t: float, target_seconds: float) -> str:
    pos = t / max(1.0, target_seconds)
    if pos < 0.12:
        return "intro"
    if pos < 0.42:
        return "story"
    if pos < 0.58:
        return "build"
    if pos < 0.82:
        return "climax"
    return "ending"


def add_text(parent: ET.Element, tag: str, text: Any = "") -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = str(text)
    return el


def add_rate(parent: ET.Element, timebase: int) -> None:
    rate = ET.SubElement(parent, "rate")
    add_text(rate, "timebase", timebase)
    add_text(rate, "ntsc", "FALSE")


def add_timecode(parent: ET.Element, timebase: int) -> None:
    tc = ET.SubElement(parent, "timecode")
    add_rate(tc, timebase)
    add_text(tc, "string", "00:00:00:00")
    add_text(tc, "frame", 0)
    add_text(tc, "displayformat", "NDF")


def pretty_xml(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def preset_size(preset: str) -> tuple[int, int]:
    low = preset.lower()
    if "vertical" in low or "1080_1920" in low:
        return 1080, 1920
    if "4k" in low:
        return 3840, 2160
    return 1920, 1080


def save_timeline_outputs(project_root: Path, data: dict[str, Any], names: list[str]) -> None:
    for name in names:
        write_json(project_root / name, data)
    write_json(appdata_dir() / "stt_prewedding_refined_v1.json", data)


def create_audio_ducking_fade_plan(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    target_seconds: float = 180.0,
    timebase: int = 25,
    music_volume_db: float = -6.0,
    duck_volume_db: float = -18.0,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "audio_ducking_fade_plan")
    timeline = load_timeline(project_root)
    plan = load_music_plan(project_root)
    music = load_music(project_root)

    if not timeline:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 123 first."}
        write_json(out / "audio_ducking_error.json", res)
        if open_folder:
            open_path(out)
        return res

    fade_in = fnum(plan.get("fade_in_sec"), 2.0)
    fade_out = fnum(plan.get("fade_out_sec"), 3.0)
    sequence_seconds = max([frames_to_sec(inum(x.get("timeline_end"), 0), timebase) for x in timeline] + [target_seconds])

    duck_segments = []
    for item in timeline:
        event = norm_event(str(item.get("event") or item.get("role") or ""))
        section = str(item.get("music_section") or item.get("section") or "")
        if event in {"vow_speech", "gia_tien"}:
            start = frames_to_sec(inum(item.get("timeline_start"), 0), timebase)
            end = frames_to_sec(inum(item.get("timeline_end"), 0), timebase)
            duck_segments.append({
                "name": f"DUCK_{event}_{item.get('index')}",
                "start_sec": round(max(0, start - 0.35), 3),
                "end_sec": round(min(sequence_seconds, end + 0.35), 3),
                "event": event,
                "section": section,
                "music_db": duck_volume_db,
                "reason": "reduce music for vow/gia_tien/emotion",
            })

    fade_segments = [
        {"name": "MUSIC_FADE_IN", "start_sec": 0.0, "end_sec": fade_in, "from_db": -60, "to_db": music_volume_db},
        {"name": "MUSIC_FADE_OUT", "start_sec": max(0, sequence_seconds - fade_out), "end_sec": sequence_seconds, "from_db": music_volume_db, "to_db": -60},
    ]

    data = {
        "ok": True,
        "module": "124_audio_ducking_fade_plan",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "music_file": music.get("file"),
        "music_name": music.get("filename"),
        "sequence_seconds": round(sequence_seconds, 3),
        "music_volume_db": music_volume_db,
        "duck_volume_db": duck_volume_db,
        "duck_count": len(duck_segments),
        "duck_segments": duck_segments,
        "fade_segments": fade_segments,
    }

    write_json(project_root / "stt_audio_ducking_fade_plan_v1.json", data)
    write_json(appdata_dir() / "stt_audio_ducking_fade_plan_v1.json", data)
    write_json(out / "stt_audio_ducking_fade_plan_v1.json", data)
    write_csv(out / "AUDIO_DUCKING_SEGMENTS.csv", duck_segments, ["name","start_sec","end_sec","event","section","music_db","reason"])
    write_csv(out / "MUSIC_FADE_SEGMENTS.csv", fade_segments, ["name","start_sec","end_sec","from_db","to_db"])
    (out / "AUDIO_DUCKING_FADE_REPORT.html").write_text(
        html_table("Audio Ducking + Fade Plan", duck_segments, ["name","start_sec","end_sec","event","music_db","reason"], "124 tạo marker/plan giảm nhạc ở đoạn vow/gia tiên. XML 125 sẽ đưa marker vào Premiere."),
        encoding="utf-8",
    )
    if open_folder:
        open_path(out)
    return {"ok": True, "report_dir": str(out), "duck_count": len(duck_segments), "sequence_seconds": round(sequence_seconds,3), "fix": "124_audio_ducking_fade_plan"}
