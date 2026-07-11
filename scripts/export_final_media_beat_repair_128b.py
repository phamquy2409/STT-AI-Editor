from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.dom import minidom


# ============================================================
# Basic helpers
# ============================================================

def read_json(path: str | Path) -> dict[str, Any]:
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: str | Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})


def outdir(project: Path, name: str) -> Path:
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_path(path: str | Path) -> None:
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


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def frames(sec: float, fps: int) -> int:
    return max(0, int(round(sec * max(1, fps))))


def file_url(path: str | Path) -> str:
    p = str(Path(path).resolve()).replace("\\", "/")
    return "file://localhost/" + quote(p, safe="/:")


def preset_size(preset: str) -> tuple[int, int]:
    low = preset.lower()
    if "vertical" in low:
        return 1080, 1920
    if "4k" in low:
        return 3840, 2160
    return 1920, 1080


_DURATION_CACHE: dict[str, float] = {}


def media_duration(path: str | Path, fallback: float = 0.0) -> float:
    key = str(path)
    if key in _DURATION_CACHE:
        return _DURATION_CACHE[key]

    result = 0.0
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode == 0 and (r.stdout or "").strip():
            result = float((r.stdout or "").strip())
    except Exception:
        result = 0.0

    if result <= 0:
        result = max(0.0, fallback)

    _DURATION_CACHE[key] = result
    return result


def add_text(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = str(value)
    return el


def add_rate(parent: ET.Element, fps: int) -> None:
    rate = ET.SubElement(parent, "rate")
    add_text(rate, "timebase", fps)
    add_text(rate, "ntsc", "FALSE")


def add_timecode(parent: ET.Element, fps: int) -> None:
    tc = ET.SubElement(parent, "timecode")
    add_rate(tc, fps)
    add_text(tc, "string", "00:00:00:00")
    add_text(tc, "frame", 0)
    add_text(tc, "displayformat", "NDF")


def pretty_xml(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(raw).toprettyxml(
        indent="  ", encoding="utf-8"
    ).decode("utf-8")


# ============================================================
# Input
# ============================================================

def load_timeline(project: Path) -> tuple[str, dict[str, Any]]:
    for name in [
        "stt_multicam_directed_timeline_v1.json",
        "stt_climax_directed_timeline_v1.json",
        "stt_multicam_selected_timeline_v1.json",
        "stt_quality_moment_timeline_v1.json",
        "stt_beat_snapped_beauty_timeline_v1.json",
    ]:
        data = read_json(project / name)
        if data.get("items"):
            return name, data
    return "", {}


def load_beats(project: Path) -> list[dict[str, Any]]:
    data = read_json(project / "stt_precise_beat_grid_v2.json")
    beats = list(data.get("beats") or data.get("markers") or [])
    out = []
    for row in beats:
        t = fnum(row.get("time_sec"), fnum(row.get("sec"), -1))
        if t < 0:
            continue
        out.append({
            "time_sec": t,
            "strength": fnum(row.get("strength"), 0.5),
            "type": str(row.get("type") or row.get("kind") or "beat"),
        })
    return sorted(out, key=lambda x: x["time_sec"])


def section_boundaries(music: dict[str, Any]) -> list[float]:
    vals = []
    for sec in music.get("sections") or []:
        vals.append(fnum(sec.get("start_sec"), -1))
        vals.append(fnum(sec.get("end_sec"), -1))
    return sorted({round(x, 4) for x in vals if x >= 0})


# ============================================================
# Final beat snap
# ============================================================

def nearest_target(
    desired: float,
    beats: list[dict[str, Any]],
    section_edges: list[float],
    max_shift: float,
) -> tuple[float, str, float]:
    candidates: list[tuple[float, float, str, float]] = []

    for edge in section_edges:
        shift = abs(edge - desired)
        if shift <= max_shift:
            candidates.append((shift - 0.03, edge, "section_edge", 1.0))

    for beat in beats:
        t = fnum(beat.get("time_sec"), -1)
        shift = abs(t - desired)
        if shift <= max_shift:
            strength = fnum(beat.get("strength"), 0.5)
            rank = shift - min(0.04, strength * 0.03)
            candidates.append((rank, t, str(beat.get("type") or "beat"), strength))

    if not candidates:
        return desired, "original", 0.0

    candidates.sort(key=lambda x: x[0])
    _, target, kind, strength = candidates[0]
    return target, kind, strength


def repair_and_snap_timeline(
    rows: list[dict[str, Any]],
    beats: list[dict[str, Any]],
    music: dict[str, Any],
    max_shift: float,
    min_shot: float,
    fps: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not rows:
        return [], {}

    clean = [dict(x) for x in rows]
    durations = [
        max(min_shot, fnum(x.get("duration_sec"),
                           fnum(x.get("timeline_end_sec"), 0) -
                           fnum(x.get("timeline_start_sec"), 0)))
        for x in clean
    ]

    boundaries = [0.0]
    for d in durations:
        boundaries.append(boundaries[-1] + d)

    target_total = boundaries[-1]
    music_target = fnum(music.get("target_seconds"), 0)
    if music_target > 0 and abs(music_target - target_total) <= 1.2:
        target_total = music_target
        boundaries[-1] = target_total

    edges = section_boundaries(music)
    snapped = list(boundaries)
    snap_count = 0
    snap_rows = []

    for i in range(1, len(boundaries) - 1):
        desired = boundaries[i]
        target, kind, strength = nearest_target(
            desired, beats, edges, max_shift
        )

        lo = snapped[i - 1] + min_shot
        original_next = boundaries[i + 1]
        hi = original_next - min_shot

        if lo <= target <= hi:
            snapped[i] = round(target, 4)
            shift = target - desired
            if abs(shift) >= (0.5 / max(1, fps)):
                snap_count += 1
                snap_rows.append({
                    "cut_index": i,
                    "original_sec": round(desired, 4),
                    "snapped_sec": round(target, 4),
                    "shift_sec": round(shift, 4),
                    "target_type": kind,
                    "strength": round(strength, 4),
                })
        else:
            snapped[i] = round(desired, 4)

    snapped[-1] = round(target_total, 4)

    source_clamped = 0
    missing_files = 0
    unknown_duration = 0
    repaired = []

    for i, row in enumerate(clean):
        start = snapped[i]
        end = snapped[i + 1]
        duration = max(min_shot, end - start)

        path = Path(str(row.get("file") or ""))
        if not path.exists():
            missing_files += 1

        fallback_media = fnum(
            row.get("media_duration_sec"),
            max(
                fnum(row.get("source_out_sec"), 0),
                fnum(row.get("source_in_sec"), 0) + duration,
            ),
        )
        media_dur = media_duration(path, fallback_media)
        if media_dur <= 0:
            unknown_duration += 1

        old_in = max(0.0, fnum(row.get("source_in_sec"), 0))
        old_out = fnum(row.get("source_out_sec"), old_in + duration)
        old_center = (old_in + max(old_in, old_out)) / 2.0

        new_in = old_center - duration / 2.0
        if media_dur > 0:
            max_in = max(0.0, media_dur - duration - 0.001)
            clamped = clamp(new_in, 0.0, max_in)
            if abs(clamped - new_in) > 0.001 or old_out > media_dur + 0.001:
                source_clamped += 1
            new_in = clamped
            new_out = min(media_dur, new_in + duration)
            if new_out - new_in < duration - 0.002:
                new_in = max(0.0, media_dur - duration)
                new_out = media_dur
        else:
            new_in = max(0.0, new_in)
            new_out = new_in + duration

        row.update({
            "index": i + 1,
            "timeline_start_sec": round(start, 4),
            "timeline_end_sec": round(end, 4),
            "duration_sec": round(duration, 4),
            "source_in_sec": round(new_in, 4),
            "source_out_sec": round(new_out, 4),
            "source_duration_sec": round(max(0.0, new_out - new_in), 4),
            "validated_media_duration_sec": round(media_dur, 4),
            "file_exists": path.exists(),
            "final_beat_repaired": True,
        })
        repaired.append(row)

    return repaired, {
        "snapped_cut_count": snap_count,
        "source_clamped_count": source_clamped,
        "missing_file_count": missing_files,
        "unknown_duration_count": unknown_duration,
        "timeline_seconds": round(snapped[-1], 4),
        "snap_rows": snap_rows,
    }


# ============================================================
# Safe slow segmentation
# ============================================================

def normal_segment(item: dict[str, Any], kind: str = "normal") -> dict[str, Any]:
    duration = fnum(item.get("duration_sec"), 0)
    src_in = fnum(item.get("source_in_sec"), 0)
    return {
        **item,
        "segment_kind": kind,
        "speed_percent": 100,
        "duration_sec": duration,
        "source_in_sec": src_in,
        "source_out_sec": src_in + duration,
    }


def split_slow_safe(
    item: dict[str, Any],
    min_speed_percent: int = 50,
) -> tuple[list[dict[str, Any]], bool, str]:
    duration = fnum(item.get("duration_sec"), 0)
    src_start = fnum(item.get("source_in_sec"), 0)
    media_dur = fnum(item.get("validated_media_duration_sec"), 0)

    if not item.get("slow_recommended") or duration < 3.2:
        return [normal_segment(item)], False, "not_requested"

    slow_output = clamp(duration * 0.42, 1.2, 2.5)
    pre_output = max(0.65, (duration - slow_output) * 0.52)
    post_output = duration - pre_output - slow_output

    if post_output < 0.55:
        shift = 0.55 - post_output
        pre_output = max(0.55, pre_output - shift)
        post_output = duration - pre_output - slow_output

    speed = max(50, min(100, int(min_speed_percent)))
    slow_source = slow_output * speed / 100.0
    source_needed = pre_output + slow_source + post_output
    source_available = max(0.0, media_dur - src_start) if media_dur > 0 else source_needed

    if media_dur > 0 and source_available + 0.001 < source_needed:
        # Shift left once. If still impossible, disable slow.
        src_start = max(0.0, media_dur - source_needed - 0.001)
        source_available = max(0.0, media_dur - src_start)

    if source_available + 0.001 < source_needed:
        return [normal_segment(item, "slow_disabled_media_limit")], True, "insufficient_source"

    parts = []
    src = src_start

    parts.append({
        **item,
        "segment_kind": "normal_before_slow",
        "speed_percent": 100,
        "duration_sec": round(pre_output, 4),
        "source_in_sec": round(src, 4),
        "source_out_sec": round(src + pre_output, 4),
    })
    src += pre_output

    parts.append({
        **item,
        "segment_kind": "slow_emphasis",
        "speed_percent": speed,
        "duration_sec": round(slow_output, 4),
        "source_in_sec": round(src, 4),
        "source_out_sec": round(src + slow_source, 4),
    })
    src += slow_source

    parts.append({
        **item,
        "segment_kind": "normal_after_slow",
        "speed_percent": 100,
        "duration_sec": round(post_output, 4),
        "source_in_sec": round(src, 4),
        "source_out_sec": round(src + post_output, 4),
    })

    return parts, False, "slow_applied"


def build_segments(
    rows: list[dict[str, Any]],
    enable_slow: bool,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    output = []
    cursor = 0.0
    slow_disabled = 0
    slow_applied = 0

    for shot_idx, item in enumerate(rows, 1):
        if enable_slow:
            parts, disabled, reason = split_slow_safe(item, 50)
            if disabled:
                slow_disabled += 1
            if reason == "slow_applied":
                slow_applied += 1
        else:
            parts = [normal_segment(item, "safe_no_speed")]

        for part_idx, part in enumerate(parts, 1):
            row = dict(part)
            duration = max(1 / 30, fnum(row.get("duration_sec"), 0))
            row["shot_index"] = shot_idx
            row["part_index"] = part_idx
            row["timeline_start_sec"] = round(cursor, 4)
            row["timeline_end_sec"] = round(cursor + duration, 4)
            cursor += duration
            output.append(row)

    return output, {
        "slow_applied_count": slow_applied,
        "slow_disabled_count": slow_disabled,
    }


# ============================================================
# XML
# ============================================================

def add_speed_filter(clip: ET.Element, speed_percent: int) -> None:
    if speed_percent >= 100:
        return

    filt = ET.SubElement(clip, "filter")
    effect = ET.SubElement(filt, "effect")
    add_text(effect, "name", "Time Remap")
    add_text(effect, "effectid", "timeremap")
    add_text(effect, "effectcategory", "motion")
    add_text(effect, "effecttype", "motion")
    add_text(effect, "mediatype", "video")

    p1 = ET.SubElement(effect, "parameter", {"authoringApp": "PremierePro"})
    add_text(p1, "parameterid", "speed")
    add_text(p1, "name", "speed")
    add_text(p1, "value", speed_percent)

    p2 = ET.SubElement(effect, "parameter", {"authoringApp": "PremierePro"})
    add_text(p2, "parameterid", "reverse")
    add_text(p2, "name", "reverse")
    add_text(p2, "value", "FALSE")

    p3 = ET.SubElement(effect, "parameter", {"authoringApp": "PremierePro"})
    add_text(p3, "parameterid", "frameblending")
    add_text(p3, "name", "frameblending")
    add_text(p3, "value", "TRUE")


def add_video_file(
    clip: ET.Element,
    file_id: str,
    path: str,
    fps: int,
    width: int,
    height: int,
    duration_frames: int,
) -> None:
    f = ET.SubElement(clip, "file", {"id": file_id})
    add_text(f, "name", Path(path).name)
    add_text(f, "pathurl", file_url(path))
    add_rate(f, fps)
    add_text(f, "duration", max(1, duration_frames))

    media = ET.SubElement(f, "media")
    video = ET.SubElement(media, "video")
    sc = ET.SubElement(video, "samplecharacteristics")
    add_rate(sc, fps)
    add_text(sc, "width", width)
    add_text(sc, "height", height)
    add_text(sc, "anamorphic", "FALSE")
    add_text(sc, "pixelaspectratio", "square")
    add_text(sc, "fielddominance", "none")


def add_video_clip(
    track: ET.Element,
    row: dict[str, Any],
    idx: int,
    fps: int,
    width: int,
    height: int,
) -> None:
    path = str(row.get("file") or "")
    tl_start = frames(fnum(row.get("timeline_start_sec"), 0), fps)
    tl_end = frames(fnum(row.get("timeline_end_sec"), 0), fps)

    media_dur = fnum(row.get("validated_media_duration_sec"), 0)
    src_in = frames(fnum(row.get("source_in_sec"), 0), fps)
    src_out = frames(fnum(row.get("source_out_sec"), 0), fps)
    file_frames = frames(media_dur, fps) if media_dur > 0 else max(src_out, src_in + 1)

    src_in = clamp(src_in, 0, max(0, file_frames - 1))
    src_out = clamp(src_out, src_in + 1, max(src_in + 1, file_frames))

    clip = ET.SubElement(track, "clipitem", {"id": f"clipitem-{idx}"})
    add_text(clip, "name", str(row.get("filename") or Path(path).name))
    add_text(clip, "enabled", "TRUE")

    # Critical fix: never lie that the source is longer than the real file.
    add_text(clip, "duration", max(1, file_frames))
    add_rate(clip, fps)
    add_text(clip, "start", tl_start)
    add_text(clip, "end", max(tl_start + 1, tl_end))
    add_text(clip, "in", int(src_in))
    add_text(clip, "out", int(src_out))

    add_video_file(
        clip,
        f"file-{idx}",
        path,
        fps,
        width,
        height,
        file_frames,
    )

    source_track = ET.SubElement(clip, "sourcetrack")
    add_text(source_track, "mediatype", "video")
    add_text(source_track, "trackindex", 1)
    add_text(clip, "fielddominance", "none")
    add_speed_filter(clip, inum(row.get("speed_percent"), 100))


def add_music_track(
    media: ET.Element,
    music_file: str,
    total_frames: int,
    fps: int,
) -> dict[str, Any]:
    if not music_file or not Path(music_file).exists():
        return {
            "music_added": False,
            "music_duration_sec": 0.0,
            "music_end_sec": 0.0,
            "audio_tail_silence_sec": 0.0,
        }

    actual_duration = media_duration(music_file, 0)
    actual_frames = frames(actual_duration, fps)
    play_frames = min(total_frames, actual_frames)

    if actual_frames <= 0 or play_frames <= 0:
        return {
            "music_added": False,
            "music_duration_sec": actual_duration,
            "music_end_sec": 0.0,
            "audio_tail_silence_sec": total_frames / fps,
        }

    audio = ET.SubElement(media, "audio")
    add_text(audio, "numOutputChannels", 2)
    track = ET.SubElement(audio, "track")

    clip = ET.SubElement(track, "clipitem", {"id": "music-clip-1"})
    add_text(clip, "name", Path(music_file).name)

    # Critical fix: real source duration only.
    add_text(clip, "duration", actual_frames)
    add_rate(clip, fps)
    add_text(clip, "start", 0)
    add_text(clip, "end", play_frames)
    add_text(clip, "in", 0)
    add_text(clip, "out", play_frames)

    f = ET.SubElement(clip, "file", {"id": "music-file-1"})
    add_text(f, "name", Path(music_file).name)
    add_text(f, "pathurl", file_url(music_file))
    add_rate(f, fps)
    add_text(f, "duration", actual_frames)

    fm = ET.SubElement(f, "media")
    fa = ET.SubElement(fm, "audio")
    add_text(fa, "channelcount", 2)

    return {
        "music_added": True,
        "music_duration_sec": round(actual_duration, 4),
        "music_end_sec": round(play_frames / fps, 4),
        "audio_tail_silence_sec": round(max(0, total_frames - play_frames) / fps, 4),
    }


def build_xml(
    segments: list[dict[str, Any]],
    music: dict[str, Any],
    fps: int,
    width: int,
    height: int,
    sequence_name: str,
) -> tuple[str, dict[str, Any]]:
    total_frames = max(
        [frames(fnum(x.get("timeline_end_sec"), 0), fps) for x in segments] + [1]
    )

    root = ET.Element("xmeml", {"version": "4"})
    seq = ET.SubElement(root, "sequence", {"id": "sequence-1"})
    add_text(seq, "name", sequence_name)
    add_text(seq, "duration", total_frames)
    add_rate(seq, fps)
    add_timecode(seq, fps)

    media = ET.SubElement(seq, "media")
    video = ET.SubElement(media, "video")
    fmt = ET.SubElement(video, "format")
    sc = ET.SubElement(fmt, "samplecharacteristics")
    add_rate(sc, fps)
    add_text(sc, "width", width)
    add_text(sc, "height", height)
    add_text(sc, "anamorphic", "FALSE")
    add_text(sc, "pixelaspectratio", "square")
    add_text(sc, "fielddominance", "none")

    vtrack = ET.SubElement(video, "track")
    for i, row in enumerate(segments, 1):
        add_video_clip(vtrack, row, i, fps, width, height)

    music_file = str(music.get("music_file") or "")
    music_stats = add_music_track(media, music_file, total_frames, fps)

    for sec in music.get("sections") or []:
        marker = ET.SubElement(seq, "marker")
        add_text(marker, "name", str(sec.get("label") or "SECTION").upper())
        add_text(marker, "comment", str(sec.get("rhythm") or ""))
        pos = min(total_frames - 1, frames(fnum(sec.get("start_sec"), 0), fps))
        add_text(marker, "in", max(0, pos))
        add_text(marker, "out", max(1, pos + 1))

    for i, point in enumerate(music.get("emphasis_points") or [], 1):
        marker = ET.SubElement(seq, "marker")
        add_text(marker, "name", f"EMPHASIS_{i}")
        add_text(marker, "comment", str(point.get("beat_type") or "music_peak"))
        pos = min(total_frames - 1, frames(fnum(point.get("time_sec"), 0), fps))
        add_text(marker, "in", max(0, pos))
        add_text(marker, "out", max(1, pos + 1))

    return pretty_xml(root), music_stats


# ============================================================
# Main
# ============================================================

def main() -> None:
    p = argparse.ArgumentParser(
        description="128B Final media-boundary repair + final beat snap + safe XML."
    )
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--max-beat-shift", type=float, default=0.24)
    p.add_argument("--min-shot", type=float, default=0.45)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "final_media_beat_repair_128b")

    input_name, timeline_data = load_timeline(project)
    rows = list(timeline_data.get("items") or [])
    music = read_json(project / "stt_music_structure_climax_v3.json")
    beats = load_beats(project)

    if not rows:
        result = {
            "ok": False,
            "error": "NO_TIMELINE",
            "message": "Run 127 or 132B first.",
        }
        write_json(out / "ERROR.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    repaired, validation = repair_and_snap_timeline(
        rows,
        beats,
        music,
        max_shift=max(0.0, a.max_beat_shift),
        min_shot=max(0.2, a.min_shot),
        fps=a.fps,
    )

    slow_segments, slow_stats = build_segments(repaired, enable_slow=True)
    safe_segments, _ = build_segments(repaired, enable_slow=False)

    width, height = preset_size(a.preset)

    slow_xml, slow_music_stats = build_xml(
        slow_segments,
        music,
        a.fps,
        width,
        height,
        "STT FINAL REPAIRED SLOW 50",
    )
    safe_xml, safe_music_stats = build_xml(
        safe_segments,
        music,
        a.fps,
        width,
        height,
        "STT FINAL REPAIRED SAFE NO SPEED",
    )

    slow_path = project / "stt_final_repaired_slow50_premiere_import.xml"
    safe_path = project / "stt_final_repaired_SAFE_NO_SPEED.xml"
    timeline_path = project / "stt_final_repaired_timeline_v1.json"

    slow_path.write_text(slow_xml, encoding="utf-8")
    safe_path.write_text(safe_xml, encoding="utf-8")
    ET.parse(str(slow_path))
    ET.parse(str(safe_path))

    repaired_data = dict(timeline_data)
    repaired_data.update({
        "ok": True,
        "module_before_128b": timeline_data.get("module"),
        "module": "128b_final_media_beat_repair",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "input_timeline": input_name,
        "timeline_count": len(repaired),
        "timeline_seconds": validation.get("timeline_seconds"),
        "validation_summary": {
            k: v for k, v in validation.items() if k != "snap_rows"
        },
        "slow_summary": slow_stats,
        "music_summary": slow_music_stats,
        "items": repaired,
    })
    write_json(timeline_path, repaired_data)

    (out / slow_path.name).write_text(slow_xml, encoding="utf-8")
    (out / safe_path.name).write_text(safe_xml, encoding="utf-8")
    write_json(out / timeline_path.name, repaired_data)
    write_json(out / "FINAL_128B_REPORT.json", {
        "ok": True,
        "input_timeline": input_name,
        "output_xml": str(slow_path),
        "safe_xml": str(safe_path),
        "timeline_json": str(timeline_path),
        "timeline_count": len(repaired),
        **{k: v for k, v in validation.items() if k != "snap_rows"},
        **slow_stats,
        "music": slow_music_stats,
    })
    write_csv(
        out / "FINAL_BEAT_SNAP_CHANGES.csv",
        validation.get("snap_rows") or [],
        [
            "cut_index", "original_sec", "snapped_sec",
            "shift_sec", "target_type", "strength",
        ],
    )
    write_csv(
        out / "FINAL_REPAIRED_TIMELINE.csv",
        repaired,
        [
            "index", "music_section", "story_part", "filename",
            "timeline_start_sec", "duration_sec", "timeline_end_sec",
            "source_in_sec", "source_out_sec",
            "validated_media_duration_sec", "file_exists",
            "slow_recommended", "camera_group", "scene_tag", "file",
        ],
    )

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "input_timeline": input_name,
        "output_xml": str(slow_path),
        "safe_xml": str(safe_path),
        "timeline_count": len(repaired),
        "timeline_seconds": validation.get("timeline_seconds"),
        "snapped_cut_count": validation.get("snapped_cut_count"),
        "source_clamped_count": validation.get("source_clamped_count"),
        "missing_file_count": validation.get("missing_file_count"),
        "unknown_duration_count": validation.get("unknown_duration_count"),
        "slow_applied_count": slow_stats.get("slow_applied_count"),
        "slow_disabled_count": slow_stats.get("slow_disabled_count"),
        "music_duration_sec": slow_music_stats.get("music_duration_sec"),
        "music_end_sec": slow_music_stats.get("music_end_sec"),
        "audio_tail_silence_sec": slow_music_stats.get("audio_tail_silence_sec"),
        "fix": "128b_final_media_beat_repair",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
