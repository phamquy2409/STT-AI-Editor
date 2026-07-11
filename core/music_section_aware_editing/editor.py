
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


def create_music_section_aware_editing(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    target_seconds: float = 180.0,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "music_section_aware_editing")

    timeline = load_timeline(project_root)
    analyzer = load_analyzer_items(project_root)
    if not timeline:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 121 first."}
        write_json(out / "music_section_aware_error.json", res)
        if open_folder:
            open_path(out)
        return res

    # Prepare candidate pool from analyzer to replace weak section-event matches.
    candidates = []
    for item in analyzer:
        f = str(item.get("file") or "")
        if not f:
            continue
        new = dict(item)
        new["event"] = norm_event(str(new.get("event") or "general"))
        new["rank_score"] = quality_rank(new)
        candidates.append(new)

    used = {str(x.get("file") or "") for x in timeline if str(x.get("file") or "")}
    output = []

    for idx, old in enumerate(timeline, start=1):
        start_sec = frames_to_sec(inum(old.get("timeline_start"), 0), timebase)
        section = str(old.get("section") or old.get("beat_section") or section_for_time(start_sec, target_seconds))
        current_event = norm_event(str(old.get("event") or old.get("role") or "general"))
        current_rank = event_rank_for_section(current_event, section)

        # Replace only if current shot is weak for the music section.
        chosen = dict(old)
        replaced = False
        if current_rank > 3 and candidates:
            pool = [
                c for c in candidates
                if str(c.get("file") or "") not in used
                and event_rank_for_section(str(c.get("event") or ""), section) <= 2
            ]
            pool.sort(key=lambda x: (event_rank_for_section(str(x.get("event") or ""), section), -fnum(x.get("rank_score"), 0), inum(x.get("source_order"), 999999)))
            if pool:
                repl = dict(pool[0])
                used.add(str(repl.get("file") or ""))
                chosen["file"] = str(repl.get("file") or "")
                chosen["filename"] = str(repl.get("filename") or Path(str(repl.get("file") or "")).name)
                chosen["event"] = str(repl.get("event") or "general")
                chosen["role"] = str(repl.get("event") or "general")
                chosen["score"] = fnum(repl.get("score"), fnum(chosen.get("score"), 0))
                chosen["rank_score"] = fnum(repl.get("rank_score"), fnum(chosen.get("rank_score"), 0))
                chosen["decision"] = str(repl.get("decision") or "")
                chosen["quality_flags"] = str(repl.get("quality_flags") or "")
                chosen["source_duration_sec"] = fnum(repl.get("duration_sec"), fnum(chosen.get("source_duration_sec"), 10))
                # keep same timeline timing, choose source segment inside replacement
                dur = fnum(chosen.get("duration"), fnum(chosen.get("duration_sec"), 1))
                src_dur = max(1.0, fnum(chosen.get("source_duration_sec"), dur + 0.5))
                src_in_sec = min(max(0.0, src_dur * 0.22), max(0.0, src_dur - dur - 0.1))
                chosen["source_in"] = sec_to_frames(src_in_sec, timebase)
                chosen["source_out"] = sec_to_frames(min(src_dur, src_in_sec + dur), timebase)
                replaced = True

        chosen["index"] = len(output) + 1
        chosen["music_section"] = section
        chosen["section_aware"] = True
        chosen["section_replace"] = replaced
        chosen["reason"] = str(chosen.get("reason", "")) + f"__122_section_aware section={section} replaced={replaced}"
        output.append(chosen)

    section_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    replaced_count = 0
    for item in output:
        section_counts[str(item.get("music_section") or item.get("section") or "")] = section_counts.get(str(item.get("music_section") or item.get("section") or ""), 0) + 1
        event_counts[str(item.get("event") or "")] = event_counts.get(str(item.get("event") or ""), 0) + 1
        if item.get("section_replace"):
            replaced_count += 1

    data = {
        "ok": True,
        "module": "122_music_section_aware_editing",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "target_seconds": target_seconds,
        "timeline_count": len(output),
        "timeline_seconds": round(max([frames_to_sec(inum(x.get("timeline_end"), 0), timebase) for x in output] + [0]), 3),
        "replaced_count": replaced_count,
        "section_counts": section_counts,
        "event_counts": event_counts,
        "timeline": output,
    }

    save_timeline_outputs(project_root, data, [
        "stt_music_section_aware_timeline_v1.json",
        "stt_beat_sync_v2_timeline_v1.json",
        "stt_beat_locked_timeline_v1.json",
        "stt_music_synced_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ])

    write_json(out / "stt_music_section_aware_timeline_v1.json", data)
    write_csv(out / "MUSIC_SECTION_AWARE_TIMELINE.csv", output, [
        "index", "filename", "event", "music_section", "section_replace", "duration", "timeline_start", "timeline_end", "file",
    ])
    (out / "MUSIC_SECTION_AWARE_REPORT.html").write_text(
        html_table("Music Section Aware Editing", output, ["index","filename","event","music_section","section_replace","duration"], "122 chọn shot đúng hơn theo intro/story/build/climax/ending."),
        encoding="utf-8",
    )
    if open_folder:
        open_path(out)
    return {"ok": True, "report_dir": str(out), "timeline_count": len(output), "replaced_count": replaced_count, "section_counts": section_counts, "fix": "122_music_section_aware_editing"}
