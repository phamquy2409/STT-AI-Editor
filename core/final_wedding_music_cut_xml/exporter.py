
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


def export_final_wedding_music_cut_xml(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    intent: str = "wedding_documentary",
    preset: str = "vertical_1080_25p",
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "final_wedding_music_cut_xml")
    timeline = load_timeline(project_root)
    music = load_music(project_root)
    plan = load_music_plan(project_root)
    duck = read_json(project_root / "stt_audio_ducking_fade_plan_v1.json") or read_json(appdata_dir() / "stt_audio_ducking_fade_plan_v1.json")
    beat = load_beat_data(project_root)

    if not timeline:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 123/124 first."}
        write_json(out / "final_wedding_music_cut_xml_error.json", res)
        if open_folder:
            open_path(out)
        return res

    width, height = preset_size(preset)
    sequence_frames = max([inum(x.get("timeline_end"), 0) for x in timeline] + [0])
    if sequence_frames <= 0:
        sequence_frames = sum(sec_to_frames(fnum(x.get("duration"), fnum(x.get("duration_sec"), 1)), timebase) for x in timeline)

    root = ET.Element("xmeml", {"version": "4"})
    seq = ET.SubElement(root, "sequence", {"id": "sequence-1"})
    add_text(seq, "name", f"STT_FINAL_{intent}_MUSIC_CUT")
    add_rate(seq, timebase)
    add_text(seq, "duration", sequence_frames)
    add_timecode(seq, timebase)

    media = ET.SubElement(seq, "media")

    video = ET.SubElement(media, "video")
    fmt = ET.SubElement(video, "format")
    sc = ET.SubElement(fmt, "samplecharacteristics")
    add_rate(sc, timebase)
    add_text(sc, "width", width)
    add_text(sc, "height", height)
    add_text(sc, "anamorphic", "FALSE")
    add_text(sc, "pixelaspectratio", "square")
    add_text(sc, "fielddominance", "none")

    vtrack = ET.SubElement(video, "track")
    file_map: dict[str, str] = {}

    cursor = 0
    for idx, item in enumerate(timeline, start=1):
        path = str(item.get("file") or "")
        if not path:
            continue
        name = str(item.get("filename") or Path(path).name)
        src_in = inum(item.get("source_in"), 0)
        src_out = inum(item.get("source_out"), src_in + sec_to_frames(fnum(item.get("duration"), 1), timebase))
        if src_out <= src_in:
            src_out = src_in + 1

        start = inum(item.get("timeline_start"), cursor)
        end = inum(item.get("timeline_end"), start + (src_out - src_in))
        if end <= start:
            end = start + (src_out - src_in)

        clip = ET.SubElement(vtrack, "clipitem", {"id": f"clipitem-{idx}"})
        add_text(clip, "name", name)
        add_rate(clip, timebase)
        add_text(clip, "duration", max(src_out, end))
        add_text(clip, "start", start)
        add_text(clip, "end", end)
        add_text(clip, "in", src_in)
        add_text(clip, "out", src_out)

        fid = file_map.get(path)
        if not fid:
            fid = f"file-{len(file_map)+1}"
            file_map[path] = fid
            fe = ET.SubElement(clip, "file", {"id": fid})
            add_text(fe, "name", name)
            add_text(fe, "pathurl", file_url(path))
            add_rate(fe, timebase)
            add_text(fe, "duration", max(src_out, end))
            fm = ET.SubElement(fe, "media")
            fv = ET.SubElement(fm, "video")
            fsc = ET.SubElement(fv, "samplecharacteristics")
            add_rate(fsc, timebase)
            add_text(fsc, "width", width)
            add_text(fsc, "height", height)
            fa = ET.SubElement(fm, "audio")
            add_text(fa, "channelcount", 2)
        else:
            ET.SubElement(clip, "file", {"id": fid})

        cursor = end

    audio = ET.SubElement(media, "audio")
    add_text(audio, "numOutputChannels", 2)
    atrack = ET.SubElement(audio, "track")

    music_file = str(music.get("file") or "")
    music_name = str(music.get("filename") or Path(music_file).name or "music")
    music_in_frames = sec_to_frames(fnum(plan.get("music_in_sec"), 0), timebase)
    music_out_frames = music_in_frames + sequence_frames

    if music_file:
        mclip = ET.SubElement(atrack, "clipitem", {"id": "music-clip-1"})
        add_text(mclip, "name", music_name)
        add_rate(mclip, timebase)
        add_text(mclip, "duration", music_out_frames)
        add_text(mclip, "start", 0)
        add_text(mclip, "end", sequence_frames)
        add_text(mclip, "in", music_in_frames)
        add_text(mclip, "out", music_out_frames)
        mf = ET.SubElement(mclip, "file", {"id": "music-file-1"})
        add_text(mf, "name", music_name)
        add_text(mf, "pathurl", file_url(music_file))
        add_rate(mf, timebase)
        add_text(mf, "duration", music_out_frames)
        mm = ET.SubElement(mf, "media")
        ma = ET.SubElement(mm, "audio")
        add_text(ma, "channelcount", 2)

    # Real beat/cut markers.
    marker_count = 0
    for i, marker in enumerate(list(beat.get("markers") or [])[:220], start=1):
        frame = inum(marker.get("frame"), 0)
        if frame > sequence_frames:
            break
        mk = ET.SubElement(seq, "marker")
        add_text(mk, "name", str(marker.get("name") or f"CUT {i:03d}"))
        add_text(mk, "comment", str(marker.get("source") or marker.get("section") or "real_audio_cut"))
        add_text(mk, "in", frame)
        add_text(mk, "out", frame + 1)
        marker_count += 1

    # Section markers from final timeline.
    for item in timeline:
        start = inum(item.get("timeline_start"), 0)
        mk = ET.SubElement(seq, "marker")
        add_text(mk, "name", f"SHOT {item.get('index')} {item.get('music_section') or item.get('section') or ''}")
        add_text(mk, "comment", str(item.get("event") or item.get("reason") or ""))
        add_text(mk, "in", start)
        add_text(mk, "out", start + 1)
        marker_count += 1

    # Duck/fade markers as instructions.
    for seg in list(duck.get("duck_segments") or []):
        mk = ET.SubElement(seq, "marker")
        add_text(mk, "name", str(seg.get("name") or "DUCK MUSIC"))
        add_text(mk, "comment", f"Music duck to {seg.get('music_db')} dB: {seg.get('reason')}")
        fr = sec_to_frames(fnum(seg.get("start_sec"), 0), timebase)
        add_text(mk, "in", fr)
        add_text(mk, "out", sec_to_frames(fnum(seg.get("end_sec"), 0), timebase))
        marker_count += 1

    for seg in list(duck.get("fade_segments") or []):
        mk = ET.SubElement(seq, "marker")
        add_text(mk, "name", str(seg.get("name") or "MUSIC FADE"))
        add_text(mk, "comment", f"Fade {seg.get('from_db')}dB to {seg.get('to_db')}dB")
        fr = sec_to_frames(fnum(seg.get("start_sec"), 0), timebase)
        add_text(mk, "in", fr)
        add_text(mk, "out", sec_to_frames(fnum(seg.get("end_sec"), 0), timebase))
        marker_count += 1

    xml = pretty_xml(root)
    xml_path = out / "stt_final_wedding_music_cut_premiere_import.xml"
    stable = project_root / "stt_final_wedding_music_cut_premiere_import.xml"
    latest = project_root / "stt_prewedding_premiere_import.xml"
    xml_path.write_text(xml, encoding="utf-8")
    stable.write_text(xml, encoding="utf-8")
    latest.write_text(xml, encoding="utf-8")
    ET.parse(str(xml_path))

    data = {
        "ok": True,
        "xml": str(xml_path),
        "stable_xml": str(stable),
        "latest_xml": str(latest),
        "timeline_items": len(timeline),
        "music_file": music_file,
        "music_name": music_name,
        "sequence_frames": sequence_frames,
        "sequence_seconds": round(frames_to_sec(sequence_frames, timebase), 3),
        "marker_count": marker_count,
        "duck_count": len(list(duck.get("duck_segments") or [])),
        "fix": "125_final_wedding_music_cut_xml",
    }
    write_json(out / "final_wedding_music_cut_xml_result.json", data)
    if open_folder:
        open_path(out)
    return data
