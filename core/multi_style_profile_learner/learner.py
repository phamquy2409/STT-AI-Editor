
from __future__ import annotations

import csv
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_DATASET_ROOT = "D:/STT Learning Dataset"

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".ogg", ".wma", ".flac"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


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


def safe_avg(vals: list[float], default: float = 0.0) -> float:
    vals = [float(v) for v in vals if v is not None]
    if not vals:
        return default
    return round(sum(vals) / len(vals), 3)


def percentile(vals: list[float], p: float, default: float = 0.0) -> float:
    vals = sorted([float(v) for v in vals if v is not None])
    if not vals:
        return default
    k = int(round((len(vals) - 1) * p))
    return round(vals[max(0, min(k, len(vals) - 1))], 3)


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


def build_source_index(source_folder: Path | None) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    if not source_folder or not source_folder.exists():
        return index
    exts = VIDEO_EXTS | AUDIO_EXTS | IMAGE_EXTS
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

    if end <= start and src_out <= src_in:
        return None

    resolved_path, resolve_status, size_bytes = resolve_source_path(pathurl, file_name, source_index)
    filename = Path(resolved_path).name if resolved_path else Path(file_name).name

    if video_only and Path(filename).suffix.lower() in AUDIO_EXTS:
        return None

    return {
        "index": idx,
        "sequence_name": sequence_name,
        "clip_name": name,
        "file_id": fid,
        "filename": filename,
        "basename": Path(filename).name.lower(),
        "stem": Path(filename).stem.lower(),
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
        "timebase": timebase,
    }


def parse_xml(xml_path: Path, source_folder: Path | None, default_timebase: int = 25, video_only: bool = True) -> dict[str, Any]:
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
        "source_folder": str(source_folder) if source_folder else "",
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


def section_for_pos(pos: float) -> str:
    if pos < 0.12:
        return "intro"
    if pos < 0.42:
        return "story"
    if pos < 0.58:
        return "build"
    if pos < 0.82:
        return "climax"
    return "ending"


def infer_style_type(profile_name: str, avg_duration_sec: float, avg_clip_count: float) -> str:
    s = profile_name.lower()
    if "intro" in s:
        return "intro_20_30s"
    if "highlight" in s or "1min" in s or "1_min" in s:
        return "highlight_1min"
    if "traditional" in s or "truyen" in s or "30_60" in s:
        return "traditional_30_60min"
    if "intimate" in s and ("7_12" in s or "full" in s):
        return "full_story_intimate_7_12min"
    if "intimate" in s:
        return "intimate_7_8min"
    if "report" in s or "phong" in s or "ps" in s:
        return "wedding_report"
    if avg_duration_sec <= 40:
        return "intro_20_30s"
    if avg_duration_sec <= 90:
        return "highlight_1min"
    if avg_duration_sec <= 300:
        return "wedding_report_3_4min"
    if avg_duration_sec <= 540:
        return "intimate_7_8min"
    if avg_duration_sec <= 900:
        return "full_story_intimate_7_12min"
    return "traditional_30_60min"


def find_source_folder(project_dir: Path) -> Path | None:
    names = ["source", "souce", "SOURCE", "SOUCE", "Source", "Souce", "footage", "Footage", "media", "Media"]
    for name in names:
        p = project_dir / name
        if p.exists() and p.is_dir():
            return p
    return None


def find_final_xml(project_dir: Path) -> Path | None:
    preferred = [
        "final.xml",
        "final_by_user.xml",
        "final_user.xml",
        "finished.xml",
        "done.xml",
        "timeline.xml",
    ]
    for name in preferred:
        p = project_dir / name
        if p.exists():
            return p

    xmls = sorted(project_dir.glob("*.xml"))
    if len(xmls) == 1:
        return xmls[0]
    if xmls:
        # prefer file names with final/done/user
        scored = []
        for p in xmls:
            n = p.name.lower()
            score = 0
            for key in ["final", "done", "user", "finished", "timeline"]:
                if key in n:
                    score += 10
            scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], str(x[1]).lower()))
        return scored[0][1]
    return None


def read_note(project_dir: Path) -> str:
    for name in ["note.txt", "notes.txt", "style.txt", "README.txt"]:
        p = project_dir / name
        if p.exists():
            return read_text_safe(p).strip()
    return ""


def discover_dataset(dataset_root: Path) -> list[dict[str, Any]]:
    jobs = []
    if not dataset_root.exists():
        return jobs

    for profile_dir in sorted([p for p in dataset_root.iterdir() if p.is_dir()]):
        profile_name = profile_dir.name

        # profile/project/final.xml/source
        project_dirs = [p for p in profile_dir.iterdir() if p.is_dir()]
        direct_xml = find_final_xml(profile_dir)
        if direct_xml:
            project_dirs = [profile_dir]

        for project_dir in project_dirs:
            xml = find_final_xml(project_dir)
            if not xml:
                continue
            src = find_source_folder(project_dir)
            jobs.append({
                "profile_name": profile_name,
                "project_name": project_dir.name,
                "project_dir": str(project_dir),
                "final_xml": str(xml),
                "source_folder": str(src) if src else "",
                "note": read_note(project_dir),
            })
    return jobs


def summarize_project(parsed: dict[str, Any], profile_name: str, project_name: str, note: str) -> dict[str, Any]:
    clips = list(parsed.get("clips") or [])
    total_end = max([fnum(c.get("timeline_end_sec"), 0) for c in clips] + [0])
    total_duration = sum(fnum(c.get("timeline_duration_sec"), 0) for c in clips)
    # For one finished XML, timeline end is usually more meaningful than sum when tracks overlap.
    project_duration = max(total_end, total_duration if len(clips) < 5 else 0)

    section_counts = Counter()
    section_durs: dict[str, list[float]] = defaultdict(list)
    ext_counts = Counter()
    filename_counts = Counter()

    for c in clips:
        pos = fnum(c.get("timeline_start_sec"), 0) / max(1.0, total_end)
        sec = section_for_pos(pos)
        dur = fnum(c.get("timeline_duration_sec"), 0)
        section_counts[sec] += 1
        section_durs[sec].append(dur)
        filename = str(c.get("filename") or "")
        filename_counts[filename] += 1
        ext_counts[Path(filename).suffix.lower() or "no_ext"] += 1

    section_rules = {}
    for sec in ["intro", "story", "build", "climax", "ending"]:
        vals = section_durs.get(sec, [])
        section_rules[sec] = {
            "clip_count": section_counts.get(sec, 0),
            "clip_ratio": round(section_counts.get(sec, 0) / max(1, len(clips)), 4),
            "avg_duration_sec": safe_avg(vals, 0),
            "p25_duration_sec": percentile(vals, 0.25, 0),
            "p50_duration_sec": percentile(vals, 0.50, 0),
            "p75_duration_sec": percentile(vals, 0.75, 0),
        }

    return {
        "profile_name": profile_name,
        "project_name": project_name,
        "note": note,
        "xml": parsed.get("xml"),
        "source_folder": parsed.get("source_folder"),
        "sequence_name": parsed.get("sequence_name"),
        "parse_mode": parsed.get("parse_mode"),
        "parse_error": parsed.get("parse_error"),
        "clip_count": parsed.get("clip_count"),
        "used_file_count": parsed.get("used_file_count"),
        "unresolved_count": parsed.get("unresolved_count"),
        "timeline_duration_sec": round(total_end, 3),
        "sum_clip_duration_sec": round(total_duration, 3),
        "avg_clip_duration_sec": round(total_duration / max(1, len(clips)), 3),
        "section_rules": section_rules,
        "section_counts": dict(section_counts),
        "extension_counts": dict(ext_counts),
        "most_used_filenames": [{"filename": k, "uses": v} for k, v in filename_counts.most_common(50)],
        "final_order_examples": [
            {
                "index": c.get("index"),
                "filename": c.get("filename"),
                "timeline_start_sec": c.get("timeline_start_sec"),
                "duration_sec": c.get("timeline_duration_sec"),
                "source_in_sec": c.get("source_in_sec"),
                "file": c.get("file"),
            }
            for c in clips[:120]
        ],
    }


def aggregate_profile(profile_name: str, projects: list[dict[str, Any]]) -> dict[str, Any]:
    clip_counts = [fnum(p.get("clip_count"), 0) for p in projects]
    durations = [fnum(p.get("timeline_duration_sec"), 0) for p in projects]
    avg_clip_durs = [fnum(p.get("avg_clip_duration_sec"), 0) for p in projects]

    ext_counter = Counter()
    file_counter = Counter()
    notes = []

    section_acc: dict[str, dict[str, list[float]]] = {
        sec: {"clip_ratio": [], "avg_duration_sec": [], "p50_duration_sec": []}
        for sec in ["intro", "story", "build", "climax", "ending"]
    }

    for p in projects:
        if p.get("note"):
            notes.append(str(p.get("note")))
        ext_counter.update(p.get("extension_counts") or {})
        for item in p.get("most_used_filenames") or []:
            file_counter[str(item.get("filename"))] += int(item.get("uses") or 0)
        for sec, rules in (p.get("section_rules") or {}).items():
            if sec in section_acc:
                section_acc[sec]["clip_ratio"].append(fnum(rules.get("clip_ratio"), 0))
                section_acc[sec]["avg_duration_sec"].append(fnum(rules.get("avg_duration_sec"), 0))
                section_acc[sec]["p50_duration_sec"].append(fnum(rules.get("p50_duration_sec"), 0))

    section_rules = {}
    for sec, vals in section_acc.items():
        section_rules[sec] = {
            "avg_clip_ratio": safe_avg(vals["clip_ratio"], 0),
            "avg_duration_sec": safe_avg(vals["avg_duration_sec"], 0),
            "avg_p50_duration_sec": safe_avg(vals["p50_duration_sec"], 0),
        }

    avg_duration = safe_avg(durations, 0)
    avg_clip_count = safe_avg(clip_counts, 0)

    return {
        "profile_name": profile_name,
        "profile_type_inferred": infer_style_type(profile_name, avg_duration, avg_clip_count),
        "project_count": len(projects),
        "confidence": "good" if len(projects) >= 8 else ("medium" if len(projects) >= 3 else "starter"),
        "target_duration_avg_sec": avg_duration,
        "target_duration_p25_sec": percentile(durations, 0.25, 0),
        "target_duration_p50_sec": percentile(durations, 0.50, 0),
        "target_duration_p75_sec": percentile(durations, 0.75, 0),
        "target_clip_count_avg": avg_clip_count,
        "target_clip_count_p50": percentile(clip_counts, 0.50, 0),
        "avg_clip_duration_sec": safe_avg(avg_clip_durs, 0),
        "section_rules": section_rules,
        "extension_counts": dict(ext_counter),
        "most_used_filenames": [{"filename": k, "uses": v} for k, v in file_counter.most_common(80)],
        "notes": notes[:30],
        "projects": projects,
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


def create_multi_style_profile_learner(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    dataset_root = Path(dataset_root)
    out = outdir(project_root, "multi_style_profile_dataset_learner_093b")
    style_dir = project_root / "stt_style_profiles_v1"
    style_dir.mkdir(parents=True, exist_ok=True)

    jobs = discover_dataset(dataset_root)
    if not jobs:
        res = {
            "ok": False,
            "error": "NO_DATASET_PROJECTS_FOUND",
            "dataset_root": str(dataset_root),
            "message": "Create folders like D:/STT Learning Dataset/highlight_1min/project_01/final.xml and source/",
        }
        write_json(out / "multi_style_profile_error.json", res)
        if open_folder:
            open_path(out)
        return res

    projects_by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    job_rows = []

    for job in jobs:
        xml = Path(str(job["final_xml"]))
        src = Path(str(job["source_folder"])) if job.get("source_folder") else None
        parsed = parse_xml(xml, src, default_timebase=25, video_only=True)
        proj = summarize_project(parsed, str(job["profile_name"]), str(job["project_name"]), str(job.get("note") or ""))
        projects_by_profile[str(job["profile_name"])].append(proj)
        job_rows.append({
            "profile": job["profile_name"],
            "project": job["project_name"],
            "clip_count": proj["clip_count"],
            "duration_sec": proj["timeline_duration_sec"],
            "avg_clip_duration_sec": proj["avg_clip_duration_sec"],
            "used_file_count": proj["used_file_count"],
            "unresolved_count": proj["unresolved_count"],
            "xml": job["final_xml"],
            "source_folder": job["source_folder"],
        })

    profiles: dict[str, Any] = {}
    profile_rows = []

    for profile_name, projects in sorted(projects_by_profile.items()):
        profile = aggregate_profile(profile_name, projects)
        profiles[profile_name] = profile
        write_json(style_dir / f"{profile_name}.json", profile)
        write_json(out / "stt_style_profiles_v1" / f"{profile_name}.json", profile)

        profile_rows.append({
            "profile_name": profile_name,
            "profile_type_inferred": profile["profile_type_inferred"],
            "project_count": profile["project_count"],
            "confidence": profile["confidence"],
            "target_duration_avg_sec": profile["target_duration_avg_sec"],
            "target_clip_count_avg": profile["target_clip_count_avg"],
            "avg_clip_duration_sec": profile["avg_clip_duration_sec"],
        })

    memory = {
        "ok": True,
        "module": "093B_multi_style_profile_dataset_learner",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "dataset_root": str(dataset_root),
        "profile_count": len(profiles),
        "project_count": len(jobs),
        "profiles": profiles,
        "usage": {
            "next_step": "Use --style-profile <profile_name> when building a new timeline.",
            "profile_files_dir": str(style_dir),
        },
    }

    write_json(project_root / "stt_multi_style_profile_memory_v1.json", memory)
    write_json(appdata_dir() / "stt_multi_style_profile_memory_v1.json", memory)
    write_json(out / "stt_multi_style_profile_memory_v1.json", memory)

    write_csv(out / "DATASET_PROJECTS_FOUND.csv", job_rows, [
        "profile", "project", "clip_count", "duration_sec", "avg_clip_duration_sec", "used_file_count", "unresolved_count", "xml", "source_folder",
    ])
    write_csv(out / "STYLE_PROFILE_SUMMARY.csv", profile_rows, [
        "profile_name", "profile_type_inferred", "project_count", "confidence", "target_duration_avg_sec", "target_clip_count_avg", "avg_clip_duration_sec",
    ])

    (out / "STYLE_PROFILE_REPORT.html").write_text(
        make_html(
            "093B Multi Style Profile Dataset Learner",
            profile_rows,
            ["profile_name", "profile_type_inferred", "project_count", "confidence", "target_duration_avg_sec", "target_clip_count_avg", "avg_clip_duration_sec"],
            f"Dataset: {dataset_root}",
        ),
        encoding="utf-8",
    )

    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "dataset_root": str(dataset_root),
        "profile_count": len(profiles),
        "project_count": len(jobs),
        "profiles": {k: {
            "project_count": v["project_count"],
            "confidence": v["confidence"],
            "profile_type_inferred": v["profile_type_inferred"],
            "target_duration_avg_sec": v["target_duration_avg_sec"],
            "target_clip_count_avg": v["target_clip_count_avg"],
            "avg_clip_duration_sec": v["avg_clip_duration_sec"],
        } for k, v in profiles.items()},
        "memory_file": str(project_root / "stt_multi_style_profile_memory_v1.json"),
        "profile_files_dir": str(style_dir),
        "fix": "093B_multi_style_profile_dataset_learner",
    }
