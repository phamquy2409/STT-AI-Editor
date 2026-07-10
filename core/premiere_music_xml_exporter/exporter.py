
from __future__ import annotations

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


def file_url(path: str | Path) -> str:
    p = str(path).replace("\\", "/")
    return "file://localhost/" + quote(p, safe="/:")


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


def clip_duration_frames(item: dict[str, Any], timebase: int) -> int:
    dur = fnum(item.get("duration"), fnum(item.get("duration_sec"), 1.0))
    return max(1, sec_to_frames(dur, timebase))


def export_premiere_music_sync_xml(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    intent: str = "wedding_documentary",
    preset: str = "vertical_1080_25p",
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "premiere_music_sync_xml_116b")
    timeline = load_current_timeline(project_root)
    selected = read_json(project_root / "stt_selected_music_v1.json") or read_json(appdata_dir() / "stt_selected_music_v1.json")
    beatmap = read_json(project_root / "stt_music_beat_map_v1.json") or read_json(appdata_dir() / "stt_music_beat_map_v1.json")
    music = selected.get("selected") if isinstance(selected.get("selected"), dict) else {}

    if not timeline:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 115 first."}
        write_json(out / "premiere_music_sync_xml_error.json", res)
        if open_folder:
            open_path(out)
        return res

    width, height = preset_size(preset)
    sequence_frames = sum(clip_duration_frames(item, timebase) for item in timeline)
    if sequence_frames <= 0:
        sequence_frames = sec_to_frames(fnum(beatmap.get("duration_sec"), 180), timebase)

    root = ET.Element("xmeml", {"version": "4"})
    seq = ET.SubElement(root, "sequence", {"id": "sequence-1"})
    add_text(seq, "name", f"STT_{intent}_music_sync")
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
    cursor = 0
    file_id_map: dict[str, str] = {}

    for idx, item in enumerate(timeline, start=1):
        path = str(item.get("file") or "")
        if not path:
            continue

        name = str(item.get("filename") or Path(path).name)
        dur = clip_duration_frames(item, timebase)
        src_in = inum(item.get("source_in"), 0)
        src_out = inum(item.get("source_out"), src_in + dur)
        if src_out <= src_in:
            src_out = src_in + dur

        start = cursor
        end = cursor + (src_out - src_in)

        clip = ET.SubElement(vtrack, "clipitem", {"id": f"clipitem-{idx}"})
        add_text(clip, "name", name)
        add_rate(clip, timebase)
        add_text(clip, "duration", max(src_out, end))
        add_text(clip, "start", start)
        add_text(clip, "end", end)
        add_text(clip, "in", src_in)
        add_text(clip, "out", src_out)

        fid = file_id_map.get(path)
        if not fid:
            fid = f"file-{len(file_id_map) + 1}"
            file_id_map[path] = fid
            file_el = ET.SubElement(clip, "file", {"id": fid})
            add_text(file_el, "name", name)
            add_text(file_el, "pathurl", file_url(path))
            add_rate(file_el, timebase)
            add_text(file_el, "duration", max(src_out, end))

            fmedia = ET.SubElement(file_el, "media")
            fvideo = ET.SubElement(fmedia, "video")
            fsc = ET.SubElement(fvideo, "samplecharacteristics")
            add_rate(fsc, timebase)
            add_text(fsc, "width", width)
            add_text(fsc, "height", height)
            faudio = ET.SubElement(fmedia, "audio")
            add_text(faudio, "channelcount", 2)
        else:
            ET.SubElement(clip, "file", {"id": fid})

        cursor = end

    audio = ET.SubElement(media, "audio")
    add_text(audio, "numOutputChannels", 2)
    atrack = ET.SubElement(audio, "track")

    music_file = str(music.get("file") or "")
    music_name = str(music.get("filename") or Path(music_file).name or "music")

    if music_file:
        mclip = ET.SubElement(atrack, "clipitem", {"id": "music-clip-1"})
        add_text(mclip, "name", music_name)
        add_rate(mclip, timebase)
        add_text(mclip, "duration", sequence_frames)
        add_text(mclip, "start", 0)
        add_text(mclip, "end", sequence_frames)
        add_text(mclip, "in", 0)
        add_text(mclip, "out", sequence_frames)

        mf = ET.SubElement(mclip, "file", {"id": "music-file-1"})
        add_text(mf, "name", music_name)
        add_text(mf, "pathurl", file_url(music_file))
        add_rate(mf, timebase)
        add_text(mf, "duration", sequence_frames)

        mm = ET.SubElement(mf, "media")
        ma = ET.SubElement(mm, "audio")
        add_text(ma, "channelcount", 2)

    for mi, marker in enumerate(list(beatmap.get("markers") or [])[:120], start=1):
        frame = inum(marker.get("frame"), 0)
        if frame > sequence_frames:
            break
        mk = ET.SubElement(seq, "marker")
        add_text(mk, "name", str(marker.get("name") or f"M{mi}"))
        add_text(mk, "comment", str(marker.get("section") or "beat"))
        add_text(mk, "in", frame)
        add_text(mk, "out", frame + 1)

    xml_text = pretty_xml(root)
    xml_path = out / "stt_wedding_music_sync_premiere_import.xml"
    stable = project_root / "stt_wedding_music_sync_premiere_import.xml"
    latest = project_root / "stt_prewedding_premiere_import.xml"

    xml_path.write_text(xml_text, encoding="utf-8")
    stable.write_text(xml_text, encoding="utf-8")
    latest.write_text(xml_text, encoding="utf-8")

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
        "marker_count": len(list(beatmap.get("markers") or [])[:120]),
        "fix": "116B_timecode_fix",
    }
    write_json(out / "premiere_music_sync_xml_result.json", data)

    if open_folder:
        open_path(out)
    return data
