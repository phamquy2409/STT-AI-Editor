
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


def desired_duration(event: str, section: str, old_dur: float) -> float:
    event = norm_event(event)
    section = str(section or "story")
    if section == "intro":
        return max(0.75, min(old_dur, 1.5))
    if section == "climax":
        if event in {"vow_speech", "gia_tien"}:
            return max(1.4, min(old_dur, 2.8))
        return max(0.75, min(old_dur, 1.6))
    if section == "ending":
        if event in {"vow_speech", "dance_party", "reception"}:
            return max(old_dur, 2.4)
        return max(1.6, old_dur)
    if event in {"gia_tien", "vow_speech"}:
        return max(old_dur, 2.8)
    if event in {"details", "dance_party"}:
        return max(0.9, min(old_dur, 2.1))
    return old_dur


def create_emotion_hold_fast_cut_rules(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    target_seconds: float = 180.0,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "emotion_hold_fast_cut_rules")
    timeline = load_timeline(project_root)
    if not timeline:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 122 first."}
        write_json(out / "emotion_rules_error.json", res)
        if open_folder:
            open_path(out)
        return res

    new_tl = []
    cursor = 0.0
    changed = 0

    for idx, item in enumerate(timeline, start=1):
        event = norm_event(str(item.get("event") or item.get("role") or "general"))
        section = str(item.get("music_section") or item.get("section") or section_for_time(cursor, target_seconds))
        old = fnum(item.get("duration"), fnum(item.get("duration_sec"), 1.0))
        dur = desired_duration(event, section, old)

        # Keep target full length by not letting any clip become too extreme.
        dur = max(0.65, min(6.0, dur))
        src_dur = max(1.0, fnum(item.get("source_duration_sec"), old + 0.5))
        src_in_sec = frames_to_sec(inum(item.get("source_in"), 0), timebase)
        if src_in_sec + dur > src_dur:
            src_in_sec = max(0.0, src_dur - dur - 0.1)
        src_out_sec = min(src_dur, src_in_sec + dur)
        dur = max(0.1, src_out_sec - src_in_sec)

        n = dict(item)
        n.update({
            "index": len(new_tl) + 1,
            "timeline_start": sec_to_frames(cursor, timebase),
            "timeline_end": sec_to_frames(cursor + dur, timebase),
            "source_in": sec_to_frames(src_in_sec, timebase),
            "source_out": sec_to_frames(src_out_sec, timebase),
            "duration": round(dur, 3),
            "duration_sec": round(dur, 3),
            "emotion_rhythm_rule": True,
            "music_section": section,
            "reason": str(item.get("reason", "")) + f"__123_emotion_fast_rule old={old} new={round(dur,3)}",
        })
        if abs(dur - old) > 0.08:
            changed += 1
        new_tl.append(n)
        cursor += dur
        if cursor >= target_seconds:
            break

    # If too short, stretch emotional/story clips slightly.
    if cursor < target_seconds * 0.94 and new_tl:
        remain = target_seconds - cursor
        expandable = [i for i, x in enumerate(new_tl) if norm_event(str(x.get("event"))) in {"gia_tien", "vow_speech", "reception"}]
        if not expandable:
            expandable = list(range(len(new_tl)))
        add_each = min(0.45, remain / max(1, len(expandable)))
        cursor = 0.0
        stretched = []
        for i, item in enumerate(new_tl):
            dur = fnum(item.get("duration"), 1)
            if i in expandable and remain > 0:
                dur += add_each
                remain -= add_each
            n = dict(item)
            src_dur = max(1.0, fnum(n.get("source_duration_sec"), dur + 0.5))
            src_in_sec = frames_to_sec(inum(n.get("source_in"), 0), timebase)
            src_out_sec = min(src_dur, src_in_sec + dur)
            dur = src_out_sec - src_in_sec
            n["timeline_start"] = sec_to_frames(cursor, timebase)
            n["timeline_end"] = sec_to_frames(cursor + dur, timebase)
            n["source_out"] = sec_to_frames(src_out_sec, timebase)
            n["duration"] = round(dur, 3)
            n["duration_sec"] = round(dur, 3)
            stretched.append(n)
            cursor += dur
        new_tl = stretched

    data = {
        "ok": True,
        "module": "123_emotion_hold_fast_cut_rules",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "target_seconds": target_seconds,
        "timeline_count": len(new_tl),
        "timeline_seconds": round(max([frames_to_sec(inum(x.get("timeline_end"), 0), timebase) for x in new_tl] + [0]), 3),
        "changed_count": changed,
        "timeline": new_tl,
    }

    save_timeline_outputs(project_root, data, [
        "stt_emotion_rhythm_timeline_v1.json",
        "stt_music_section_aware_timeline_v1.json",
        "stt_beat_sync_v2_timeline_v1.json",
        "stt_beat_locked_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ])

    write_json(out / "stt_emotion_rhythm_timeline_v1.json", data)
    write_csv(out / "EMOTION_FAST_RULE_TIMELINE.csv", new_tl, [
        "index", "filename", "event", "music_section", "duration", "timeline_start", "timeline_end", "emotion_rhythm_rule", "file",
    ])
    (out / "EMOTION_FAST_RULE_REPORT.html").write_text(
        html_table("Emotion Hold / Fast Cut Rules", new_tl, ["index","filename","event","music_section","duration"], "123 giữ lâu hơn ở gia tiên/vow, nhanh hơn ở intro/climax."),
        encoding="utf-8",
    )
    if open_folder:
        open_path(out)
    return {"ok": True, "report_dir": str(out), "timeline_count": len(new_tl), "timeline_seconds": data["timeline_seconds"], "changed_count": changed, "fix": "123_emotion_hold_fast_cut_rules"}
