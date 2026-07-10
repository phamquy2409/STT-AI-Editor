
from __future__ import annotations

import csv
import json
import os
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"

PRESETS = {
    "vertical_1080_25p": {"width": 1080, "height": 1920, "timebase": 25},
    "vertical_1080_30p": {"width": 1080, "height": 1920, "timebase": 30},
    "fhd_1080_25p": {"width": 1920, "height": 1080, "timebase": 25},
    "uhd_4k_25p": {"width": 3840, "height": 2160, "timebase": 25},
}
PREWEDDING_XML_PRESETS = PRESETS

MEDIA_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".wav", ".mp3", ".m4a"}


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


def open_path(path: Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def to_pathurl(path: Path) -> str:
    # Premiere/FCP7 cần URI sạch. Encode space/unicode, giữ D:/.
    s = path.resolve().as_posix()
    return "file://localhost/" + urllib.parse.quote(s, safe="/:._-()[]")


def get_source_folder(project_root: Path, source_folder: str | Path | None = None) -> Path | None:
    if source_folder and Path(source_folder).exists():
        return Path(source_folder)

    for p in [appdata_dir() / "gui_settings.json", appdata_dir() / "panel_source_folder_config.json"]:
        d = read_json(p)
        for k in ["source_folder", "source_root", "media_folder", "input_folder"]:
            if d.get(k) and Path(str(d[k])).exists():
                return Path(str(d[k]))

    d = Path("D:/5thang5test")
    return d if d.exists() else None


def source_media_files(source_folder: Path | None) -> list[Path]:
    if not source_folder or not source_folder.exists():
        return []
    return sorted(
        [p for p in source_folder.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXTS],
        key=lambda p: str(p).lower(),
    )


def load_timeline(project_root: Path) -> list[dict[str, Any]]:
    for p in [
        project_root / "stt_prewedding_refined_v1.json",
        project_root / "stt_prewedding_roughcut_v1.json",
        project_root / "stt_prewedding_selection_v1.json",
        project_root / "stt_prewedding_pipeline_v1.json",
    ]:
        d = read_json(p)
        for k in ["timeline", "selected", "selected_shots", "clips", "items"]:
            if isinstance(d.get(k), list):
                return list(d[k])
        if isinstance(d.get("result"), dict):
            r = d["result"]
            for k in ["timeline", "selected", "selected_shots", "clips", "items"]:
                if isinstance(r.get(k), list):
                    return list(r[k])
    return []


def media_index(files: list[Path]) -> dict[str, Path]:
    idx: dict[str, Path] = {}
    for p in files:
        idx[p.name.lower()] = p
        idx[p.stem.lower()] = p
    return idx


def find_media_in_item(item: dict[str, Any], idx: dict[str, Path]) -> Path | None:
    for k in [
        "file",
        "file_path",
        "source_file",
        "source_path",
        "path",
        "media_path",
        "abs_path",
        "absolute_path",
        "filename",
        "name",
        "clip_name",
        "source_name",
    ]:
        v = item.get(k)
        if not v:
            continue
        raw = str(v).replace("file://localhost/", "").replace("file:///", "")
        p = Path(raw)
        if p.exists():
            return p
        if p.name.lower() in idx:
            return idx[p.name.lower()]
        if p.stem.lower() in idx:
            return idx[p.stem.lower()]
    return None


def as_frames(value: Any, timebase: int) -> int:
    try:
        f = float(value)
    except Exception:
        return 0
    if abs(f) < 1000 and "." in str(value):
        return int(round(f * timebase))
    return int(round(f))


def source_in_out(item: dict[str, Any], timebase: int) -> tuple[int, int]:
    inn = None
    out = None
    for k in ["source_in_frames", "source_in", "in_frames", "in", "start_frame"]:
        if item.get(k) is not None:
            inn = as_frames(item.get(k), timebase)
            break
    for k in ["source_out_frames", "source_out", "out_frames", "out", "end_frame"]:
        if item.get(k) is not None:
            out = as_frames(item.get(k), timebase)
            break
    if inn is None:
        inn = 0
    if out is None or out <= inn:
        dur = 0
        for k in ["timeline_duration_frames", "duration_frames", "duration", "duration_sec", "duration_seconds"]:
            if item.get(k) is not None:
                dur = as_frames(item.get(k), timebase)
                break
        if dur <= 0:
            dur = timebase * 3
        out = inn + dur
    return max(0, inn), max(1, out)


def build_resolved_clips(
    timeline: list[dict[str, Any]],
    files: list[Path],
    timebase: int,
    fallback_clip_count: int = 20,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    idx = media_index(files)
    clips: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    used: set[Path] = set()

    for i, item in enumerate(timeline, 1):
        p = find_media_in_item(item, idx)
        if not p:
            unresolved.append({"index": i, "item": item})
            continue
        inn, out = source_in_out(item, timebase)
        clips.append({
            "index": len(clips) + 1,
            "path": p,
            "name": p.name,
            "in": inn,
            "out": out,
            "duration": max(1, out - inn),
        })
        used.add(p)

    fallback = False
    if not clips and files:
        fallback = True
        for p in files[:fallback_clip_count]:
            clips.append({
                "index": len(clips) + 1,
                "path": p,
                "name": p.name,
                "in": 0,
                "out": timebase * 3,
                "duration": timebase * 3,
            })
    elif unresolved and files:
        fallback = True
        remaining = [p for p in files if p not in used]
        for p in remaining[:len(unresolved)]:
            clips.append({
                "index": len(clips) + 1,
                "path": p,
                "name": p.name,
                "in": 0,
                "out": timebase * 3,
                "duration": timebase * 3,
            })

    return clips, unresolved, fallback


def add_rate(parent: ET.Element, timebase: int) -> ET.Element:
    rate = ET.SubElement(parent, "rate")
    ET.SubElement(rate, "timebase").text = str(timebase)
    ET.SubElement(rate, "ntsc").text = "FALSE"
    return rate


def add_file_full(parent: ET.Element, c: dict[str, Any], file_id: str, timebase: int, width: int, height: int) -> ET.Element:
    f = ET.SubElement(parent, "file", id=file_id)
    ET.SubElement(f, "name").text = c["name"]
    ET.SubElement(f, "pathurl").text = to_pathurl(c["path"])
    add_rate(f, timebase)
    ET.SubElement(f, "duration").text = str(max(int(c["out"]), int(c["duration"])))

    media = ET.SubElement(f, "media")
    video = ET.SubElement(media, "video")
    sc = ET.SubElement(video, "samplecharacteristics")
    add_rate(sc, timebase)
    ET.SubElement(sc, "width").text = str(width)
    ET.SubElement(sc, "height").text = str(height)
    ET.SubElement(sc, "anamorphic").text = "FALSE"
    ET.SubElement(sc, "pixelaspectratio").text = "square"
    ET.SubElement(sc, "fielddominance").text = "none"

    audio = ET.SubElement(media, "audio")
    ET.SubElement(audio, "channelcount").text = "2"
    asc = ET.SubElement(audio, "samplecharacteristics")
    ET.SubElement(asc, "depth").text = "16"
    ET.SubElement(asc, "samplerate").text = "48000"
    return f


def add_file_ref(parent: ET.Element, file_id: str) -> ET.Element:
    return ET.SubElement(parent, "file", id=file_id)


def add_link(item: ET.Element, ref: str, mediatype: str, trackindex: int, clipindex: int) -> None:
    link = ET.SubElement(item, "link")
    ET.SubElement(link, "linkclipref").text = ref
    ET.SubElement(link, "mediatype").text = mediatype
    ET.SubElement(link, "trackindex").text = str(trackindex)
    ET.SubElement(link, "clipindex").text = str(clipindex)


def add_clipitem(
    track: ET.Element,
    c: dict[str, Any],
    start: int,
    end: int,
    media_type: str,
    channel: int,
    timebase: int,
    width: int,
    height: int,
) -> str:
    suffix = "v" if media_type == "video" else f"a{channel}"
    clip_id = f"clipitem-{suffix}-{c['index']}"
    file_id = f"file-{c['index']}"

    item = ET.SubElement(track, "clipitem", id=clip_id)
    ET.SubElement(item, "masterclipid").text = f"masterclip-{c['index']}"
    ET.SubElement(item, "name").text = c["name"]
    ET.SubElement(item, "enabled").text = "TRUE"
    ET.SubElement(item, "duration").text = str(c["duration"])
    add_rate(item, timebase)
    ET.SubElement(item, "start").text = str(start)
    ET.SubElement(item, "end").text = str(end)
    ET.SubElement(item, "in").text = str(c["in"])
    ET.SubElement(item, "out").text = str(c["out"])

    if media_type == "video":
        add_file_full(item, c, file_id=file_id, timebase=timebase, width=width, height=height)
    else:
        add_file_ref(item, file_id=file_id)
        source = ET.SubElement(item, "sourcetrack")
        ET.SubElement(source, "mediatype").text = "audio"
        ET.SubElement(source, "trackindex").text = str(channel)

    return clip_id


def build_xml(clips: list[dict[str, Any]], preset: str, timebase: int, width: int, height: int) -> str:
    xmeml = ET.Element("xmeml", version="4")
    seq = ET.SubElement(xmeml, "sequence", id="sequence-1")
    ET.SubElement(seq, "uuid").text = f"stt-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    ET.SubElement(seq, "name").text = f"STT Prewedding Reel 60s {preset} {datetime.now().strftime('%Y%m%d_%H%M')}"
    ET.SubElement(seq, "duration").text = str(sum(int(c["duration"]) for c in clips))
    add_rate(seq, timebase)

    timecode = ET.SubElement(seq, "timecode")
    add_rate(timecode, timebase)
    ET.SubElement(timecode, "string").text = "00:00:00:00"
    ET.SubElement(timecode, "frame").text = "0"
    ET.SubElement(timecode, "displayformat").text = "NDF"

    media = ET.SubElement(seq, "media")

    video = ET.SubElement(media, "video")
    fmt = ET.SubElement(video, "format")
    sc = ET.SubElement(fmt, "samplecharacteristics")
    add_rate(sc, timebase)
    ET.SubElement(sc, "width").text = str(width)
    ET.SubElement(sc, "height").text = str(height)
    ET.SubElement(sc, "anamorphic").text = "FALSE"
    ET.SubElement(sc, "pixelaspectratio").text = "square"
    ET.SubElement(sc, "fielddominance").text = "none"
    vtrack = ET.SubElement(video, "track")

    audio = ET.SubElement(media, "audio")
    ET.SubElement(audio, "numOutputChannels").text = "2"
    afmt = ET.SubElement(audio, "format")
    asc = ET.SubElement(afmt, "samplecharacteristics")
    ET.SubElement(asc, "depth").text = "16"
    ET.SubElement(asc, "samplerate").text = "48000"
    outputs = ET.SubElement(audio, "outputs")
    for i in [1, 2]:
        group = ET.SubElement(outputs, "group")
        ET.SubElement(group, "index").text = str(i)
        ET.SubElement(group, "numchannels").text = "1"
        ET.SubElement(group, "downmix").text = "0"
    a1 = ET.SubElement(audio, "track")
    a2 = ET.SubElement(audio, "track")

    cursor = 0
    for c in clips:
        dur = int(c["duration"])
        st, en = cursor, cursor + dur
        cursor = en

        v_id = add_clipitem(vtrack, c, st, en, "video", 0, timebase, width, height)
        a1_id = add_clipitem(a1, c, st, en, "audio", 1, timebase, width, height)
        a2_id = add_clipitem(a2, c, st, en, "audio", 2, timebase, width, height)

        # Link giữ video + dual mono A1/A2.
        # ElementTree không hỗ trợ tìm ngược parent nên tạo link bằng cách duyệt lại clipitem id.
        for item in [x for x in vtrack.findall("clipitem") if x.get("id") == v_id]:
            add_link(item, v_id, "video", 1, 1)
            add_link(item, a1_id, "audio", 1, 1)
            add_link(item, a2_id, "audio", 2, 1)
        for item in [x for x in a1.findall("clipitem") if x.get("id") == a1_id]:
            add_link(item, v_id, "video", 1, 1)
            add_link(item, a1_id, "audio", 1, 1)
            add_link(item, a2_id, "audio", 2, 1)
        for item in [x for x in a2.findall("clipitem") if x.get("id") == a2_id]:
            add_link(item, v_id, "video", 1, 1)
            add_link(item, a1_id, "audio", 1, 1)
            add_link(item, a2_id, "audio", 2, 1)

    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + ET.tostring(xmeml, encoding="unicode")


def export_prewedding_xml(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str = "prewedding_reel_60s",
    preset: str = "vertical_1080_25p",
    source_folder: str | Path | None = None,
    open_folder: bool = True,
    fallback_clip_count: int = 20,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    settings = PRESETS.get(preset, PRESETS["vertical_1080_25p"])
    timebase = int(settings["timebase"])
    src = get_source_folder(project_root, source_folder)
    files = source_media_files(src)
    timeline = load_timeline(project_root)
    clips, unresolved, fallback = build_resolved_clips(
        timeline, files, timebase, fallback_clip_count=fallback_clip_count
    )

    report = project_root / "exports" / f"prewedding_xml_safe_fcp7_{intent}_{preset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report.mkdir(parents=True, exist_ok=True)

    if not clips:
        res = {
            "ok": False,
            "error": "NO_MEDIA_FILES_FOUND",
            "message": "Không tìm được file video/audio trong source folder.",
            "source_folder": str(src) if src else None,
            "timeline_items": len(timeline),
            "source_media_count": len(files),
            "report_dir": str(report),
        }
        write_json(report / "PREMIERE_XML_SAFE_ERROR.json", res)
        if open_folder:
            open_path(report)
        return res

    xml_path = report / "stt_prewedding_premiere_import.xml"
    xml_text = build_xml(clips, preset, timebase, int(settings["width"]), int(settings["height"]))
    xml_path.write_text(xml_text, encoding="utf-8")

    # Validate parse ngay sau khi ghi.
    ET.parse(xml_path)

    stable = project_root / "stt_prewedding_premiere_import.xml"
    shutil.copy2(xml_path, stable)

    with (report / "PREMIERE_RELINK_SOURCE_LIST.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["index", "filename", "path", "pathurl"])
        w.writeheader()
        for c in clips:
            w.writerow({
                "index": c["index"],
                "filename": c["name"],
                "path": str(c["path"]),
                "pathurl": to_pathurl(c["path"]),
            })

    (report / "README_IMPORT_PREMIERE.txt").write_text(
        "101E Safe FCP7 XML.\n"
        "Nếu Import Latest XML trên panel lỗi, thử Premiere: File > Import và chọn XML này.\n"
        "Nếu vẫn lỗi, gửi file PREMIERE_RELINK_SOURCE_LIST.csv và XML 20 dòng đầu.\n",
        encoding="utf-8",
    )

    appdata_dir().mkdir(parents=True, exist_ok=True)
    (appdata_dir() / "premiere_latest_xml.txt").write_text(str(stable), encoding="utf-8")
    write_json(appdata_dir() / "premiere_latest_xml.json", {
        "ok": True,
        "latest_xml": str(stable),
        "export_xml": str(xml_path),
        "source_folder": str(src) if src else None,
        "fix": "101E_safe_fcp7_xml",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    })

    res = {
        "ok": True,
        "xml": str(xml_path),
        "stable_xml": str(stable),
        "latest_xml": str(stable),
        "report_dir": str(report),
        "source_folder": str(src) if src else None,
        "source_media_count": len(files),
        "timeline_items": len(timeline),
        "resolved_count": len(clips),
        "unresolved_count": len(unresolved),
        "fallback_from_source_folder": fallback,
        "fix": "101E_safe_fcp7_xml",
    }
    write_json(report / "premiere_xml_safe_fcp7_result.json", res)
    if open_folder:
        open_path(report)
    return res
