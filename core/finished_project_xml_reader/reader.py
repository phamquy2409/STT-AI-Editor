
from __future__ import annotations

import csv
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/27thang6pschh/souce"
DEFAULT_FINAL_XML = "D:/STT Projects/Wedding_Test_001/final_by_user.xml"

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".ogg", ".wma", ".flac"}


def appdata_dir() -> Path:
    p = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_text_safe(path: Path) -> str:
    for enc in ["utf-8-sig", "utf-8", "utf-16", "cp1258", "latin-1"]:
        try:
            return path.read_text(encoding=enc)
        except Exception:
            pass
    return path.read_bytes().decode("utf-8", errors="ignore")


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


def inum(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def elem_text(elem: ET.Element | None, path: str, default: str = "") -> str:
    if elem is None:
        return default
    found = elem.find(path)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def strip_ns(xml_text: str) -> str:
    xml_text = re.sub(r'\sxmlns(:\w+)?="[^"]+"', "", xml_text)
    xml_text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", xml_text)
    return xml_text


def decode_pathurl(pathurl: str) -> str:
    if not pathurl:
        return ""
    s = pathurl.strip()
    if s.startswith("file://"):
        parsed = urlparse(s)
        path = unquote(parsed.path or "")
        if re.match(r"^/[A-Za-z]:/", path):
            path = path[1:]
        return path.replace("/", "\\")
    return unquote(s).replace("/", "\\")


def file_size(path: str) -> int:
    try:
        return Path(path).stat().st_size
    except Exception:
        return 0


def build_source_index(source_folder: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    exts = VIDEO_EXTS | AUDIO_EXTS
    if not source_folder.exists():
        return index
    for p in source_folder.rglob("*"):
        try:
            if p.is_file() and p.suffix.lower() in exts:
                index.setdefault(p.name.lower(), []).append(str(p))
        except Exception:
            pass
    return index


def resolve_source_path(pathurl: str, filename: str, source_index: dict[str, list[str]]) -> tuple[str, str, int]:
    direct = decode_pathurl(pathurl)
    if direct and Path(direct).exists():
        return str(Path(direct)), "pathurl_exists", file_size(direct)

    name = Path(filename).name.lower() if filename else ""
    candidates = source_index.get(name, []) if name else []
    if len(candidates) == 1:
        return candidates[0], "matched_by_filename", file_size(candidates[0])
    if len(candidates) > 1:
        candidates = sorted(candidates, key=lambda x: file_size(x), reverse=True)
        return candidates[0], f"matched_by_filename_duplicate_{len(candidates)}", file_size(candidates[0])

    if direct:
        return direct, "missing_pathurl_file", 0
    return "", "unresolved", 0


def get_rate_from_text(xml_text: str, fallback: int = 25) -> int:
    m = re.search(r"<timebase>\s*(\d+)\s*</timebase>", xml_text, re.I)
    if m:
        return max(1, inum(m.group(1), fallback))
    return fallback


def get_rate(elem: ET.Element | None, fallback: int = 25) -> int:
    if elem is None:
        return fallback
    txt = elem_text(elem, "rate/timebase", "")
    if txt:
        return max(1, inum(txt, fallback))
    for node in elem.iter("rate"):
        tb = elem_text(node, "timebase", "")
        if tb:
            return max(1, inum(tb, fallback))
    return fallback


def file_id_from_file_el(file_el: ET.Element | None) -> str:
    if file_el is None:
        return ""
    return str(file_el.attrib.get("id") or "").strip()


def build_file_id_map_from_xml(xml_text: str) -> dict[str, dict[str, str]]:
    file_map: dict[str, dict[str, str]] = {}
    for m in re.finditer(r'<file\b([^>]*)>(.*?)</file>', xml_text, re.S | re.I):
        attrs = m.group(1)
        body = m.group(2)
        idm = re.search(r'id="([^"]+)"', attrs)
        if not idm:
            continue
        fid = idm.group(1)
        name_m = re.search(r'<name>(.*?)</name>', body, re.S | re.I)
        path_m = re.search(r'<pathurl>(.*?)</pathurl>', body, re.S | re.I)
        dur_m = re.search(r'<duration>(.*?)</duration>', body, re.S | re.I)
        if name_m or path_m:
            file_map[fid] = {
                "id": fid,
                "name": (name_m.group(1).strip() if name_m else ""),
                "pathurl": (path_m.group(1).strip() if path_m else ""),
                "duration": (dur_m.group(1).strip() if dur_m else ""),
            }
    return file_map


def should_skip_by_ext(file_name: str, pathurl: str, video_only: bool) -> bool:
    if not video_only:
        return False
    decoded = decode_pathurl(pathurl)
    ext = Path(file_name).suffix.lower() if file_name else ""
    ext2 = Path(decoded).suffix.lower() if decoded else ""
    final_ext = ext2 or ext
    # Only skip known audio. Keep unknown/no ext because some Premiere generated file refs are odd.
    if final_ext in AUDIO_EXTS:
        return True
    return False


def parse_clip_element(
    clip: ET.Element,
    idx: int,
    sequence_name: str,
    timebase: int,
    source_index: dict[str, list[str]],
    file_id_map: dict[str, dict[str, str]],
    video_only: bool = True,
) -> dict[str, Any] | None:
    name = elem_text(clip, "name", "")
    file_el = clip.find("file")
    fid = file_id_from_file_el(file_el)
    mapped = file_id_map.get(fid, {}) if fid else {}

    file_name = elem_text(file_el, "name", "") or mapped.get("name", "") or name
    pathurl = elem_text(file_el, "pathurl", "") or mapped.get("pathurl", "")

    if not file_name and not pathurl:
        return None
    if should_skip_by_ext(file_name, pathurl, video_only=video_only):
        return None

    start = inum(elem_text(clip, "start", "0"), 0)
    end = inum(elem_text(clip, "end", "0"), 0)
    src_in = inum(elem_text(clip, "in", "0"), 0)
    src_out = inum(elem_text(clip, "out", "0"), 0)
    duration = inum(elem_text(clip, "duration", "0"), 0)

    if end <= start and src_out <= src_in:
        return None

    resolved_path, resolve_status, size_bytes = resolve_source_path(pathurl, file_name, source_index)
    filename = Path(resolved_path).name if resolved_path else Path(file_name).name

    # After resolving, remove audio if video_only.
    if video_only and Path(filename).suffix.lower() in AUDIO_EXTS:
        return None

    clip_duration_frames = max(0, end - start)
    src_duration_frames = max(0, src_out - src_in)

    return {
        "index": idx,
        "xml_clip_index": idx,
        "sequence_name": sequence_name,
        "clip_name": name,
        "file_id": fid,
        "filename": filename,
        "xml_file_name": file_name,
        "pathurl": pathurl,
        "file": resolved_path,
        "resolve_status": resolve_status,
        "file_exists": bool(resolved_path and Path(resolved_path).exists()),
        "size_bytes": size_bytes,
        "timeline_start": start,
        "timeline_end": end,
        "timeline_duration_frames": clip_duration_frames,
        "timeline_start_sec": round(start / timebase, 3),
        "timeline_end_sec": round(end / timebase, 3),
        "timeline_duration_sec": round(clip_duration_frames / timebase, 3),
        "source_in": src_in,
        "source_out": src_out,
        "source_duration_frames": src_duration_frames,
        "source_in_sec": round(src_in / timebase, 3),
        "source_out_sec": round(src_out / timebase, 3),
        "source_duration_sec": round(src_duration_frames / timebase, 3),
        "xml_duration": duration,
        "timebase": timebase,
        "video_only": video_only,
    }


def sequence_name_from_text(xml_text: str) -> str:
    m = re.search(r"<sequence[^>]*>.*?<name>(.*?)</name>", xml_text, re.S | re.I)
    return m.group(1).strip() if m else "final_sequence"


def parse_normal(xml_text: str, source_index: dict[str, list[str]], default_timebase: int, video_only: bool) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    seq = root.find(".//sequence")
    sequence_name = elem_text(seq, "name", "final_sequence")
    timebase = get_rate(seq, default_timebase)
    file_id_map = build_file_id_map_from_xml(xml_text)

    # normal mode can safely prefer video path
    clipitems = root.findall(".//sequence/media/video/track/clipitem")
    if not clipitems:
        clipitems = root.findall(".//clipitem")

    clips = []
    for raw_idx, clip in enumerate(clipitems, start=1):
        c = parse_clip_element(clip, raw_idx, sequence_name, timebase, source_index, file_id_map, video_only=video_only)
        if c:
            c["index"] = len(clips) + 1
            clips.append(c)

    return {
        "parse_mode": "normal_xml",
        "sequence_name": sequence_name,
        "timebase": timebase,
        "clips": clips,
        "file_id_map_count": len(file_id_map),
        "scan_clipitem_blocks": len(clipitems),
        "failed_blocks": 0,
    }


def parse_recovery(xml_text: str, source_index: dict[str, list[str]], default_timebase: int, parse_error: str, video_only: bool) -> dict[str, Any]:
    # 091D: scan ALL complete clipitem blocks. Do not depend on <video>...</video> because bad XML can truncate that region.
    sequence_name = sequence_name_from_text(xml_text)
    timebase = get_rate_from_text(xml_text, default_timebase)
    file_id_map = build_file_id_map_from_xml(xml_text)

    blocks = re.findall(r"<clipitem\b[^>]*>.*?</clipitem>", xml_text, re.S | re.I)

    clips = []
    failed_blocks = 0
    skipped_audio = 0
    skipped_empty = 0

    for raw_idx, block in enumerate(blocks, start=1):
        try:
            clip = ET.fromstring(strip_ns(block))
            before_len = len(clips)
            c = parse_clip_element(clip, raw_idx, sequence_name, timebase, source_index, file_id_map, video_only=video_only)
            if c:
                c["index"] = len(clips) + 1
                clips.append(c)
            else:
                # rough reason for debug
                if re.search(r"\.(mp3|wav|m4a|aac|aif|aiff|ogg|wma|flac)\b", block, re.I):
                    skipped_audio += 1
                else:
                    skipped_empty += 1
        except Exception:
            failed_blocks += 1

    return {
        "parse_mode": "recovery_all_clipitems_fileid_filter",
        "parse_error": parse_error,
        "sequence_name": sequence_name,
        "timebase": timebase,
        "clips": clips,
        "file_id_map_count": len(file_id_map),
        "scan_clipitem_blocks": len(blocks),
        "failed_blocks": failed_blocks,
        "skipped_audio_like_blocks": skipped_audio,
        "skipped_empty_blocks": skipped_empty,
    }


def parse_xml_clipitems(final_xml: Path, source_folder: Path, default_timebase: int = 25, video_only: bool = True) -> dict[str, Any]:
    xml_text = strip_ns(read_text_safe(final_xml))
    source_index = build_source_index(source_folder)

    try:
        parsed = parse_normal(xml_text, source_index, default_timebase, video_only=video_only)
    except Exception as exc:
        parsed = parse_recovery(xml_text, source_index, default_timebase, repr(exc), video_only=video_only)

    clips = parsed["clips"]
    used_files = sorted({c["file"] for c in clips if c.get("file")})
    unresolved = [c for c in clips if not c.get("file_exists")]

    status_counts: dict[str, int] = {}
    ext_counts: dict[str, int] = {}
    for c in clips:
        s = str(c.get("resolve_status") or "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
        ext = Path(str(c.get("filename") or "")).suffix.lower() or "no_ext"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    return {
        **parsed,
        "clip_count": len(clips),
        "used_file_count": len(used_files),
        "unresolved_count": len(unresolved),
        "resolve_status_counts": status_counts,
        "ext_counts": ext_counts,
        "used_files": used_files,
        "source_index_count": sum(len(v) for v in source_index.values()),
        "video_only": video_only,
    }


def make_html(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
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


def create_finished_project_xml_reader(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    final_xml: str | Path = DEFAULT_FINAL_XML,
    timebase: int = 25,
    video_only: bool = True,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    source_folder = Path(source_folder)
    final_xml = Path(final_xml)

    out = outdir(project_root, "finished_project_xml_reader_091d")

    if not final_xml.exists():
        res = {
            "ok": False,
            "error": "FINAL_XML_NOT_FOUND",
            "final_xml": str(final_xml),
            "message": "Export Final Cut Pro XML from Premiere first.",
        }
        write_json(out / "finished_project_xml_reader_error.json", res)
        if open_folder:
            open_path(out)
        return res

    parsed = parse_xml_clipitems(final_xml, source_folder, default_timebase=timebase, video_only=video_only)
    clips = parsed["clips"]

    data = {
        "ok": True,
        "module": "091D_recovery_scan_all_clipitems",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "source_folder": str(source_folder),
        "final_xml": str(final_xml),
        **parsed,
    }

    write_json(project_root / "stt_finished_project_xml_v1.json", data)
    write_json(appdata_dir() / "stt_finished_project_xml_v1.json", data)
    write_json(out / "stt_finished_project_xml_v1.json", data)

    write_csv(out / "FINISHED_XML_CLIPS.csv", clips, [
        "index", "filename", "file_id", "resolve_status", "file_exists",
        "timeline_start_sec", "timeline_end_sec", "timeline_duration_sec",
        "source_in_sec", "source_out_sec", "source_duration_sec",
        "file",
    ])

    unresolved = [c for c in clips if not c.get("file_exists")]
    write_csv(out / "UNRESOLVED_XML_CLIPS.csv", unresolved, [
        "index", "filename", "file_id", "xml_file_name", "pathurl", "resolve_status", "timeline_start_sec", "source_in_sec", "file",
    ])

    summary_rows = [
        {"key": "parse_mode", "value": parsed.get("parse_mode")},
        {"key": "parse_error", "value": parsed.get("parse_error", "")},
        {"key": "sequence_name", "value": parsed.get("sequence_name")},
        {"key": "clip_count", "value": parsed.get("clip_count")},
        {"key": "used_file_count", "value": parsed.get("used_file_count")},
        {"key": "unresolved_count", "value": parsed.get("unresolved_count")},
        {"key": "source_index_count", "value": parsed.get("source_index_count")},
        {"key": "file_id_map_count", "value": parsed.get("file_id_map_count")},
        {"key": "scan_clipitem_blocks", "value": parsed.get("scan_clipitem_blocks")},
        {"key": "failed_blocks", "value": parsed.get("failed_blocks")},
        {"key": "skipped_audio_like_blocks", "value": parsed.get("skipped_audio_like_blocks", "")},
        {"key": "skipped_empty_blocks", "value": parsed.get("skipped_empty_blocks", "")},
        {"key": "resolve_status_counts", "value": json.dumps(parsed.get("resolve_status_counts", {}), ensure_ascii=False)},
        {"key": "ext_counts", "value": json.dumps(parsed.get("ext_counts", {}), ensure_ascii=False)},
        {"key": "timebase", "value": parsed.get("timebase")},
        {"key": "video_only", "value": parsed.get("video_only")},
    ]
    write_csv(out / "FINISHED_XML_SUMMARY.csv", summary_rows, ["key", "value"])

    html = make_html(
        "091D Recovery Scan All Clipitems",
        clips,
        ["index", "filename", "file_id", "resolve_status", "file_exists", "timeline_start_sec", "timeline_duration_sec", "source_in_sec", "source_duration_sec"],
        f"parse_mode={parsed.get('parse_mode')} | scan_blocks={parsed.get('scan_clipitem_blocks')} | file_id_map={parsed.get('file_id_map_count')}",
    )
    (out / "FINISHED_XML_REPORT.html").write_text(html, encoding="utf-8")

    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "final_xml": str(final_xml),
        "source_folder": str(source_folder),
        "parse_mode": parsed.get("parse_mode"),
        "parse_error": parsed.get("parse_error", ""),
        "sequence_name": parsed.get("sequence_name"),
        "clip_count": parsed.get("clip_count"),
        "used_file_count": parsed.get("used_file_count"),
        "unresolved_count": parsed.get("unresolved_count"),
        "file_id_map_count": parsed.get("file_id_map_count"),
        "scan_clipitem_blocks": parsed.get("scan_clipitem_blocks"),
        "failed_blocks": parsed.get("failed_blocks"),
        "resolve_status_counts": parsed.get("resolve_status_counts"),
        "ext_counts": parsed.get("ext_counts"),
        "timebase": parsed.get("timebase"),
        "video_only": video_only,
        "fix": "091D_recovery_scan_all_clipitems",
    }
