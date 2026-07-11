
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
DEFAULT_AI_XML = "D:/STT Projects/Wedding_Test_001/stt_final_wedding_music_cut_premiere_import.xml"

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}
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
    exts = VIDEO_EXTS | AUDIO_EXTS | {".png", ".jpg", ".jpeg"}
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
        if name_m or path_m:
            file_map[fid] = {
                "id": fid,
                "name": (name_m.group(1).strip() if name_m else ""),
                "pathurl": (path_m.group(1).strip() if path_m else ""),
            }
    return file_map


def file_id_from_file_el(file_el: ET.Element | None) -> str:
    if file_el is None:
        return ""
    return str(file_el.attrib.get("id") or "").strip()


def should_skip_by_ext(file_name: str, pathurl: str, video_only: bool) -> bool:
    if not video_only:
        return False
    decoded = decode_pathurl(pathurl)
    ext = Path(file_name).suffix.lower() if file_name else ""
    ext2 = Path(decoded).suffix.lower() if decoded else ""
    final_ext = ext2 or ext
    if final_ext in AUDIO_EXTS:
        return True
    return False


def sequence_name_from_text(xml_text: str) -> str:
    m = re.search(r"<sequence[^>]*>.*?<name>(.*?)</name>", xml_text, re.S | re.I)
    return m.group(1).strip() if m else "sequence"


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

    if video_only and Path(filename).suffix.lower() in AUDIO_EXTS:
        return None

    return {
        "index": idx,
        "xml_clip_index": idx,
        "sequence_name": sequence_name,
        "clip_name": name,
        "file_id": fid,
        "filename": filename,
        "basename": Path(filename).name.lower(),
        "stem": Path(filename).stem.lower(),
        "xml_file_name": file_name,
        "pathurl": pathurl,
        "file": resolved_path,
        "resolve_status": resolve_status,
        "file_exists": bool(resolved_path and Path(resolved_path).exists()),
        "size_bytes": size_bytes,
        "timeline_start": start,
        "timeline_end": end,
        "timeline_duration_frames": max(0, end - start),
        "timeline_start_sec": round(start / timebase, 3),
        "timeline_end_sec": round(end / timebase, 3),
        "timeline_duration_sec": round(max(0, end - start) / timebase, 3),
        "source_in": src_in,
        "source_out": src_out,
        "source_duration_frames": max(0, src_out - src_in),
        "source_in_sec": round(src_in / timebase, 3),
        "source_out_sec": round(src_out / timebase, 3),
        "source_duration_sec": round(max(0, src_out - src_in) / timebase, 3),
        "xml_duration": duration,
        "timebase": timebase,
    }


def parse_xml(xml_path: Path, source_folder: Path, default_timebase: int = 25, video_only: bool = True) -> dict[str, Any]:
    xml_text = strip_ns(read_text_safe(xml_path))
    source_index = build_source_index(source_folder)
    file_id_map = build_file_id_map_from_xml(xml_text)

    try:
        root = ET.fromstring(xml_text)
        seq = root.find(".//sequence")
        sequence_name = elem_text(seq, "name", xml_path.stem)
        timebase = get_rate(seq, default_timebase)
        clipitems = root.findall(".//sequence/media/video/track/clipitem")
        if not clipitems:
            clipitems = root.findall(".//clipitem")
        parse_mode = "normal_xml"
        parse_error = ""
        failed = 0
        blocks_count = len(clipitems)
        clips = []
        for raw_idx, clip in enumerate(clipitems, start=1):
            c = parse_clip_element(clip, raw_idx, sequence_name, timebase, source_index, file_id_map, video_only=video_only)
            if c:
                c["index"] = len(clips) + 1
                clips.append(c)
    except Exception as exc:
        sequence_name = sequence_name_from_text(xml_text)
        timebase = get_rate_from_text(xml_text, default_timebase)
        blocks = re.findall(r"<clipitem\b[^>]*>.*?</clipitem>", xml_text, re.S | re.I)
        clips = []
        failed = 0
        for raw_idx, block in enumerate(blocks, start=1):
            try:
                clip = ET.fromstring(strip_ns(block))
                c = parse_clip_element(clip, raw_idx, sequence_name, timebase, source_index, file_id_map, video_only=video_only)
                if c:
                    c["index"] = len(clips) + 1
                    clips.append(c)
            except Exception:
                failed += 1
        parse_mode = "recovery_all_clipitems_fileid_filter"
        parse_error = repr(exc)
        blocks_count = len(blocks)

    used_files = sorted({c["file"] for c in clips if c.get("file")})
    unresolved = [c for c in clips if not c.get("file_exists")]

    return {
        "xml": str(xml_path),
        "sequence_name": sequence_name,
        "timebase": timebase,
        "parse_mode": parse_mode,
        "parse_error": parse_error,
        "file_id_map_count": len(file_id_map),
        "scan_clipitem_blocks": blocks_count,
        "failed_blocks": failed,
        "clip_count": len(clips),
        "used_file_count": len(used_files),
        "unresolved_count": len(unresolved),
        "clips": clips,
        "used_files": used_files,
    }


def occurrence_key(clip: dict[str, Any]) -> str:
    # filename occurrence matching; source_in can change between AI/final so keep filename as primary.
    return str(clip.get("basename") or Path(str(clip.get("filename") or "")).name.lower())


def group_by_basename(clips: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    d: dict[str, list[dict[str, Any]]] = {}
    for c in clips:
        d.setdefault(occurrence_key(c), []).append(c)
    return d


def make_sections(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not clips:
        return []
    total = max([fnum(c.get("timeline_end_sec"), 0) for c in clips] + [1.0])
    rows = []
    for c in clips:
        start = fnum(c.get("timeline_start_sec"), 0)
        pos = start / max(1.0, total)
        if pos < 0.12:
            section = "intro"
        elif pos < 0.42:
            section = "story"
        elif pos < 0.58:
            section = "build"
        elif pos < 0.82:
            section = "climax"
        else:
            section = "ending"
        r = dict(c)
        r["learned_section"] = section
        r["timeline_pos"] = round(pos, 4)
        rows.append(r)
    return rows


def compare_ai_vs_final(ai: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    ai_clips = make_sections(list(ai.get("clips") or []))
    final_clips = make_sections(list(final.get("clips") or []))

    ai_by = group_by_basename(ai_clips)
    final_by = group_by_basename(final_clips)

    ai_names = set(ai_by.keys())
    final_names = set(final_by.keys())

    common_names = sorted(ai_names & final_names)
    added_names = sorted(final_names - ai_names)
    removed_names = sorted(ai_names - final_names)

    added = []
    for name in added_names:
        for c in final_by[name]:
            row = dict(c)
            row["learn_action"] = "user_added_or_ai_missed"
            added.append(row)

    removed = []
    for name in removed_names:
        for c in ai_by[name]:
            row = dict(c)
            row["learn_action"] = "user_removed_ai_choice"
            removed.append(row)

    common = []
    duration_deltas = []
    order_deltas = []
    for name in common_names:
        ai_list = ai_by[name]
        final_list = final_by[name]
        n = min(len(ai_list), len(final_list))
        for i in range(n):
            a = ai_list[i]
            f = final_list[i]
            dur_delta = fnum(f.get("timeline_duration_sec"), 0) - fnum(a.get("timeline_duration_sec"), 0)
            order_delta = inum(f.get("index"), 0) - inum(a.get("index"), 0)
            source_in_delta = fnum(f.get("source_in_sec"), 0) - fnum(a.get("source_in_sec"), 0)
            row = {
                "filename": f.get("filename") or a.get("filename"),
                "ai_index": a.get("index"),
                "final_index": f.get("index"),
                "order_delta": order_delta,
                "ai_section": a.get("learned_section"),
                "final_section": f.get("learned_section"),
                "ai_duration_sec": a.get("timeline_duration_sec"),
                "final_duration_sec": f.get("timeline_duration_sec"),
                "duration_delta_sec": round(dur_delta, 3),
                "ai_source_in_sec": a.get("source_in_sec"),
                "final_source_in_sec": f.get("source_in_sec"),
                "source_in_delta_sec": round(source_in_delta, 3),
                "file": f.get("file") or a.get("file"),
                "learn_action": "kept_but_adjusted" if abs(dur_delta) > 0.15 or abs(order_delta) > 2 or abs(source_in_delta) > 0.5 else "kept_similar",
            }
            common.append(row)
            if abs(dur_delta) > 0.15:
                duration_deltas.append(row)
            if abs(order_delta) > 2:
                order_deltas.append(row)

    # Section preferences from final
    section_counts: dict[str, int] = {}
    section_avg_duration: dict[str, list[float]] = {}
    for c in final_clips:
        sec = str(c.get("learned_section") or "unknown")
        section_counts[sec] = section_counts.get(sec, 0) + 1
        section_avg_duration.setdefault(sec, []).append(fnum(c.get("timeline_duration_sec"), 0))
    section_duration_summary = {
        k: round(sum(v)/len(v), 3) for k, v in section_avg_duration.items() if v
    }

    return {
        "ai_clip_count": len(ai_clips),
        "final_clip_count": len(final_clips),
        "common_file_count": len(common_names),
        "user_added_file_count": len(added_names),
        "user_removed_file_count": len(removed_names),
        "common_clip_comparisons": common,
        "user_added_clips": added,
        "user_removed_ai_clips": removed,
        "duration_change_clips": duration_deltas,
        "order_change_clips": order_deltas,
        "final_section_counts": section_counts,
        "final_section_avg_duration_sec": section_duration_summary,
        "final_order": final_clips,
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


def create_ai_vs_final_xml_comparator(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    ai_xml: str | Path = DEFAULT_AI_XML,
    final_xml: str | Path = DEFAULT_FINAL_XML,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    source_folder = Path(source_folder)
    ai_xml = Path(ai_xml)
    final_xml = Path(final_xml)
    out = outdir(project_root, "ai_vs_final_xml_comparator_092")

    if not ai_xml.exists():
        res = {"ok": False, "error": "AI_XML_NOT_FOUND", "ai_xml": str(ai_xml)}
        write_json(out / "ai_vs_final_error.json", res)
        if open_folder:
            open_path(out)
        return res

    if not final_xml.exists():
        res = {"ok": False, "error": "FINAL_XML_NOT_FOUND", "final_xml": str(final_xml)}
        write_json(out / "ai_vs_final_error.json", res)
        if open_folder:
            open_path(out)
        return res

    ai = parse_xml(ai_xml, source_folder, default_timebase=timebase, video_only=True)
    final = parse_xml(final_xml, source_folder, default_timebase=timebase, video_only=True)
    cmp = compare_ai_vs_final(ai, final)

    data = {
        "ok": True,
        "module": "092_ai_vs_final_xml_comparator",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "source_folder": str(source_folder),
        "ai_xml": str(ai_xml),
        "final_xml": str(final_xml),
        "ai_parse": {k: ai.get(k) for k in ["parse_mode","parse_error","sequence_name","clip_count","used_file_count","unresolved_count","timebase"]},
        "final_parse": {k: final.get(k) for k in ["parse_mode","parse_error","sequence_name","clip_count","used_file_count","unresolved_count","timebase"]},
        **cmp,
    }

    write_json(project_root / "stt_ai_vs_final_comparison_v1.json", data)
    write_json(appdata_dir() / "stt_ai_vs_final_comparison_v1.json", data)
    write_json(out / "stt_ai_vs_final_comparison_v1.json", data)

    write_csv(out / "USER_ADDED_CLIPS.csv", cmp["user_added_clips"], [
        "index","filename","learned_section","timeline_start_sec","timeline_duration_sec","source_in_sec","source_duration_sec","file","learn_action"
    ])
    write_csv(out / "USER_REMOVED_AI_CLIPS.csv", cmp["user_removed_ai_clips"], [
        "index","filename","learned_section","timeline_start_sec","timeline_duration_sec","source_in_sec","source_duration_sec","file","learn_action"
    ])
    write_csv(out / "COMMON_CLIP_COMPARISON.csv", cmp["common_clip_comparisons"], [
        "filename","ai_index","final_index","order_delta","ai_section","final_section","ai_duration_sec","final_duration_sec","duration_delta_sec","ai_source_in_sec","final_source_in_sec","source_in_delta_sec","learn_action","file"
    ])
    write_csv(out / "FINAL_CLIP_ORDER_FOR_LEARNING.csv", cmp["final_order"], [
        "index","filename","learned_section","timeline_pos","timeline_start_sec","timeline_duration_sec","source_in_sec","source_duration_sec","file"
    ])

    summary_rows = [
        {"key": "ai_clip_count", "value": cmp["ai_clip_count"]},
        {"key": "final_clip_count", "value": cmp["final_clip_count"]},
        {"key": "common_file_count", "value": cmp["common_file_count"]},
        {"key": "user_added_file_count", "value": cmp["user_added_file_count"]},
        {"key": "user_removed_file_count", "value": cmp["user_removed_file_count"]},
        {"key": "final_section_counts", "value": json.dumps(cmp["final_section_counts"], ensure_ascii=False)},
        {"key": "final_section_avg_duration_sec", "value": json.dumps(cmp["final_section_avg_duration_sec"], ensure_ascii=False)},
    ]
    write_csv(out / "AI_VS_FINAL_SUMMARY.csv", summary_rows, ["key", "value"])

    (out / "AI_VS_FINAL_REPORT.html").write_text(
        make_html(
            "092 AI vs Final XML Comparator",
            cmp["common_clip_comparisons"][:500],
            ["filename","ai_index","final_index","order_delta","ai_section","final_section","ai_duration_sec","final_duration_sec","duration_delta_sec","learn_action"],
            f"AI: {ai_xml.name} | Final: {final_xml.name}",
        ),
        encoding="utf-8",
    )

    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "ai_clip_count": cmp["ai_clip_count"],
        "final_clip_count": cmp["final_clip_count"],
        "common_file_count": cmp["common_file_count"],
        "user_added_file_count": cmp["user_added_file_count"],
        "user_removed_file_count": cmp["user_removed_file_count"],
        "final_section_counts": cmp["final_section_counts"],
        "ai_unresolved_count": ai.get("unresolved_count"),
        "final_unresolved_count": final.get("unresolved_count"),
        "fix": "092_ai_vs_final_xml_comparator",
    }
