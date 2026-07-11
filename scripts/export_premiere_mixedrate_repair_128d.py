from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.dom import minidom


# ============================================================
# Helpers
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


def parse_rate(value: Any) -> float:
    s = str(value or "").strip()
    if not s or s in {"0/0", "N/A"}:
        return 0.0
    try:
        if "/" in s:
            return float(Fraction(s))
        return float(s)
    except Exception:
        return 0.0


def xml_rate_parts(fps: float) -> tuple[int, str]:
    for real, base in [
        (24000 / 1001, 24),
        (30000 / 1001, 30),
        (60000 / 1001, 60),
        (120000 / 1001, 120),
    ]:
        if abs(fps - real) < 0.03:
            return base, "TRUE"
    return max(1, int(round(fps))), "FALSE"


def add_text(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = str(value)
    return el


def add_rate(parent: ET.Element, fps: float) -> None:
    timebase, ntsc = xml_rate_parts(fps)
    rate = ET.SubElement(parent, "rate")
    add_text(rate, "timebase", timebase)
    add_text(rate, "ntsc", ntsc)


def add_timecode(parent: ET.Element, fps: float) -> None:
    tc = ET.SubElement(parent, "timecode")
    add_rate(tc, fps)
    add_text(tc, "string", "00:00:00:00")
    add_text(tc, "frame", 0)
    add_text(tc, "displayformat", "NDF")


def pretty_xml(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="utf-8")
    body = minidom.parseString(raw).toprettyxml(
        indent="  ", encoding="utf-8"
    ).decode("utf-8")
    # Premiere/FCP XML compatibility.
    lines = body.splitlines()
    if lines and lines[0].startswith("<?xml"):
        lines.insert(1, "<!DOCTYPE xmeml>")
    return "\n".join(lines) + "\n"


def seq_frames(sec: float, fps: float) -> int:
    return max(0, int(round(sec * fps)))


def src_frames(sec: float, fps: float) -> int:
    return max(0, int(round(sec * fps)))


def stable_file_id(path: str) -> str:
    digest = hashlib.sha1(path.lower().encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"file-{digest}"


# ============================================================
# Media metadata
# ============================================================

_META_CACHE: dict[str, dict[str, Any]] = {}


def probe_media(path: str | Path, default_fps: float) -> dict[str, Any]:
    key = str(path)
    if key in _META_CACHE:
        return _META_CACHE[key]

    result = {
        "exists": Path(path).exists(),
        "duration_sec": 0.0,
        "fps": default_fps,
        "width": 0,
        "height": 0,
        "fps_source": "default",
    }

    if not result["exists"]:
        _META_CACHE[key] = result
        return result

    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-print_format", "json",
                "-show_entries",
                "stream=codec_type,avg_frame_rate,r_frame_rate,duration,width,height:"
                "format=duration",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if r.returncode == 0 and (r.stdout or "").strip():
            data = json.loads(r.stdout)
            format_duration = fnum((data.get("format") or {}).get("duration"), 0)
            streams = list(data.get("streams") or [])
            video = next((x for x in streams if x.get("codec_type") == "video"), None)
            audio = next((x for x in streams if x.get("codec_type") == "audio"), None)
            stream = video or audio or {}

            result["duration_sec"] = max(
                format_duration,
                fnum(stream.get("duration"), 0),
            )

            if video:
                avg = parse_rate(video.get("avg_frame_rate"))
                raw = parse_rate(video.get("r_frame_rate"))
                fps = avg if avg > 0 else raw
                if fps > 0:
                    result["fps"] = fps
                    result["fps_source"] = "ffprobe"
                result["width"] = inum(video.get("width"), 0)
                result["height"] = inum(video.get("height"), 0)
    except Exception:
        pass

    _META_CACHE[key] = result
    return result


# ============================================================
# Input and final beat snap
# ============================================================

def load_timeline(project: Path) -> tuple[str, dict[str, Any]]:
    for name in [
        "stt_multicam_directed_timeline_v1.json",
        "stt_climax_directed_timeline_v1.json",
        "stt_multicam_selected_timeline_v1.json",
        "stt_quality_moment_timeline_v1.json",
        "stt_beat_snapped_beauty_timeline_v1.json",
        "stt_final_repaired_timeline_v1.json",
    ]:
        data = read_json(project / name)
        if data.get("items"):
            return name, data
    return "", {}


def load_beats(project: Path) -> list[dict[str, Any]]:
    data = read_json(project / "stt_precise_beat_grid_v2.json")
    output = []
    for row in data.get("beats") or data.get("markers") or []:
        sec = fnum(row.get("time_sec"), fnum(row.get("sec"), -1))
        if sec >= 0:
            output.append({
                "time_sec": sec,
                "strength": fnum(row.get("strength"), 0.5),
                "type": str(row.get("type") or row.get("kind") or "beat"),
            })
    return sorted(output, key=lambda x: x["time_sec"])


def music_edges(music: dict[str, Any]) -> list[float]:
    edges = set()
    for sec in music.get("sections") or []:
        for key in ["start_sec", "end_sec"]:
            value = fnum(sec.get(key), -1)
            if value >= 0:
                edges.add(round(value, 6))
    return sorted(edges)


def nearest_snap(
    desired: float,
    beats: list[dict[str, Any]],
    edges: list[float],
    max_shift: float,
) -> tuple[float, str, float]:
    candidates = []

    for edge in edges:
        delta = abs(edge - desired)
        if delta <= max_shift:
            candidates.append((delta - 0.04, edge, "section_edge", 1.0))

    for beat in beats:
        sec = fnum(beat.get("time_sec"), -1)
        delta = abs(sec - desired)
        if delta <= max_shift:
            strength = fnum(beat.get("strength"), 0.5)
            candidates.append((
                delta - min(0.03, strength * 0.025),
                sec,
                str(beat.get("type") or "beat"),
                strength,
            ))

    if not candidates:
        return desired, "original", 0.0

    candidates.sort(key=lambda x: x[0])
    _, sec, kind, strength = candidates[0]
    return sec, kind, strength


def repair_timeline(
    rows: list[dict[str, Any]],
    music: dict[str, Any],
    beats: list[dict[str, Any]],
    sequence_fps: float,
    default_source_fps: float,
    max_beat_shift: float,
    min_shot: float,
    safety_frames: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    durations = [
        max(
            min_shot,
            fnum(
                row.get("duration_sec"),
                fnum(row.get("timeline_end_sec"), 0) -
                fnum(row.get("timeline_start_sec"), 0),
            ),
        )
        for row in rows
    ]

    boundaries = [0.0]
    for duration in durations:
        boundaries.append(boundaries[-1] + duration)

    total = boundaries[-1]
    music_target = fnum(music.get("target_seconds"), 0)
    if music_target > 0 and abs(total - music_target) <= 1.5:
        total = music_target
        boundaries[-1] = total

    snapped = list(boundaries)
    edges = music_edges(music)
    snap_changes = []

    for i in range(1, len(boundaries) - 1):
        desired = boundaries[i]
        target, kind, strength = nearest_snap(
            desired,
            beats,
            edges,
            max_beat_shift,
        )
        lo = snapped[i - 1] + min_shot
        hi = boundaries[i + 1] - min_shot

        if lo <= target <= hi:
            snapped[i] = target
            if abs(target - desired) >= 0.5 / sequence_fps:
                snap_changes.append({
                    "cut_index": i,
                    "original_sec": round(desired, 6),
                    "snapped_sec": round(target, 6),
                    "shift_sec": round(target - desired, 6),
                    "target_type": kind,
                    "strength": round(strength, 5),
                })

    snapped[-1] = total

    output = []
    missing = 0
    unknown_duration = 0
    source_clamped = 0
    fps_counts: Counter[str] = Counter()

    for i, original in enumerate(rows):
        row = dict(original)
        start = snapped[i]
        end = snapped[i + 1]
        duration = max(min_shot, end - start)

        path = str(row.get("file") or "")
        meta = probe_media(path, default_source_fps)
        source_fps = fnum(meta.get("fps"), default_source_fps)
        media_duration = fnum(meta.get("duration_sec"), 0)

        if not meta.get("exists"):
            missing += 1

        if media_duration <= 0:
            media_duration = fnum(
                row.get("media_duration_sec"),
                max(
                    fnum(row.get("source_out_sec"), 0),
                    fnum(row.get("source_in_sec"), 0) + duration,
                ),
            )
        if media_duration <= 0:
            unknown_duration += 1

        fps_counts[f"{source_fps:.3f}"] += 1

        safety_sec = max(1, safety_frames) / max(1.0, source_fps)
        effective_end = max(0.0, media_duration - safety_sec)

        old_in = max(0.0, fnum(row.get("source_in_sec"), 0))
        old_out = max(old_in, fnum(row.get("source_out_sec"), old_in + duration))
        center = (old_in + old_out) / 2.0

        new_in = center - duration / 2.0
        max_in = max(0.0, effective_end - duration)
        clamped_in = clamp(new_in, 0.0, max_in)
        new_out = clamped_in + duration

        if (
            abs(clamped_in - new_in) > 0.001
            or old_out > effective_end + 0.001
        ):
            source_clamped += 1

        row.update({
            "index": i + 1,
            "timeline_start_sec": round(start, 6),
            "timeline_end_sec": round(end, 6),
            "duration_sec": round(duration, 6),
            "source_in_sec": round(clamped_in, 6),
            "source_out_sec": round(new_out, 6),
            "source_media_duration_sec": round(media_duration, 6),
            "source_media_fps": round(source_fps, 6),
            "source_media_width": inum(meta.get("width"), 0),
            "source_media_height": inum(meta.get("height"), 0),
            "source_fps_detected_by": meta.get("fps_source"),
            "file_exists": bool(meta.get("exists")),
        })
        output.append(row)

    return output, {
        "timeline_seconds": round(total, 6),
        "snapped_cut_count": len(snap_changes),
        "snap_changes": snap_changes,
        "source_clamped_count": source_clamped,
        "missing_file_count": missing,
        "unknown_duration_count": unknown_duration,
        "source_fps_counts": dict(fps_counts),
    }


# ============================================================
# Segment preparation
# ============================================================

def normal_segment(item: dict[str, Any], kind: str) -> dict[str, Any]:
    duration = fnum(item.get("duration_sec"), 0)
    source_in = fnum(item.get("source_in_sec"), 0)
    return {
        **item,
        "segment_kind": kind,
        "speed_percent": 100,
        "duration_sec": duration,
        "source_in_sec": source_in,
        "source_out_sec": source_in + duration,
        "source_consumed_sec": duration,
    }


def split_slow(item: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    duration = fnum(item.get("duration_sec"), 0)
    if not item.get("slow_recommended") or duration < 3.2:
        return [normal_segment(item, "normal")], False

    source_fps = fnum(item.get("source_media_fps"), 50)
    media_duration = fnum(item.get("source_media_duration_sec"), 0)
    safety_sec = 5 / max(1.0, source_fps)
    media_end = max(0.0, media_duration - safety_sec)

    slow_output = clamp(duration * 0.42, 1.2, 2.5)
    pre_output = max(0.60, (duration - slow_output) * 0.52)
    post_output = duration - pre_output - slow_output

    if post_output < 0.55:
        shift = 0.55 - post_output
        pre_output = max(0.55, pre_output - shift)
        post_output = duration - pre_output - slow_output

    slow_source = slow_output * 0.50
    source_needed = pre_output + slow_source + post_output
    source_start = fnum(item.get("source_in_sec"), 0)

    if source_start + source_needed > media_end:
        source_start = max(0.0, media_end - source_needed)

    if source_start + source_needed > media_end + 0.001:
        return [normal_segment(item, "slow_disabled_media_limit")], True

    output = []
    src = source_start

    output.append({
        **item,
        "segment_kind": "normal_before_slow",
        "speed_percent": 100,
        "duration_sec": round(pre_output, 6),
        "source_in_sec": round(src, 6),
        "source_out_sec": round(src + pre_output, 6),
        "source_consumed_sec": round(pre_output, 6),
    })
    src += pre_output

    output.append({
        **item,
        "segment_kind": "slow_emphasis",
        "speed_percent": 50,
        "duration_sec": round(slow_output, 6),
        "source_in_sec": round(src, 6),
        "source_out_sec": round(src + slow_source, 6),
        "source_consumed_sec": round(slow_source, 6),
    })
    src += slow_source

    output.append({
        **item,
        "segment_kind": "normal_after_slow",
        "speed_percent": 100,
        "duration_sec": round(post_output, 6),
        "source_in_sec": round(src, 6),
        "source_out_sec": round(src + post_output, 6),
        "source_consumed_sec": round(post_output, 6),
    })

    return output, False


def build_segments(
    rows: list[dict[str, Any]],
    enable_slow: bool,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    output = []
    cursor = 0.0
    slow_applied = 0
    slow_disabled = 0

    for shot_index, item in enumerate(rows, 1):
        if enable_slow:
            parts, disabled = split_slow(item)
            if disabled:
                slow_disabled += 1
            if any(inum(x.get("speed_percent"), 100) == 50 for x in parts):
                slow_applied += 1
        else:
            parts = [normal_segment(item, "safe_no_speed")]

        for part_index, part in enumerate(parts, 1):
            row = dict(part)
            duration = fnum(row.get("duration_sec"), 0)
            row["shot_index"] = shot_index
            row["part_index"] = part_index
            row["timeline_start_sec"] = round(cursor, 6)
            row["timeline_end_sec"] = round(cursor + duration, 6)
            cursor += duration
            output.append(row)

    return output, {
        "slow_applied_count": slow_applied,
        "slow_disabled_count": slow_disabled,
    }


# ============================================================
# Premiere-compatible mixed-rate XMEML
# ============================================================

def mixed_rate_values(
    source_in_sec: float,
    source_consumed_sec: float,
    sequence_fps: float,
    source_fps: float,
) -> tuple[int, int, int]:
    source_in_frame = src_frames(source_in_sec, source_fps)

    # XMEML mixed-rate In points are represented at sequence rate.
    clip_in = int(math.floor(source_in_frame * sequence_fps / source_fps))
    reconstructed_source_frame = int(math.floor(clip_in * source_fps / sequence_fps))
    mixed_offset = source_in_frame - reconstructed_source_frame

    source_consumed_frames = max(1, src_frames(source_consumed_sec, source_fps))
    source_out_frame = source_in_frame + source_consumed_frames
    clip_out = int(math.ceil(source_out_frame * sequence_fps / source_fps))

    if clip_out <= clip_in:
        clip_out = clip_in + 1

    return clip_in, clip_out, mixed_offset


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

    param = ET.SubElement(effect, "parameter", {"authoringApp": "PremierePro"})
    add_text(param, "parameterid", "speed")
    add_text(param, "name", "speed")
    add_text(param, "value", speed_percent)

    reverse = ET.SubElement(effect, "parameter", {"authoringApp": "PremierePro"})
    add_text(reverse, "parameterid", "reverse")
    add_text(reverse, "name", "reverse")
    add_text(reverse, "value", "FALSE")

    blend = ET.SubElement(effect, "parameter", {"authoringApp": "PremierePro"})
    add_text(blend, "parameterid", "frameblending")
    add_text(blend, "name", "frameblending")
    add_text(blend, "value", "TRUE")


def add_full_file_definition(
    clip: ET.Element,
    file_id: str,
    row: dict[str, Any],
    fallback_width: int,
    fallback_height: int,
) -> None:
    path = str(row.get("file") or "")
    source_fps = fnum(row.get("source_media_fps"), 50)
    media_duration = fnum(row.get("source_media_duration_sec"), 0)
    media_frames = max(1, src_frames(media_duration, source_fps))

    width = inum(row.get("source_media_width"), fallback_width) or fallback_width
    height = inum(row.get("source_media_height"), fallback_height) or fallback_height

    file_el = ET.SubElement(clip, "file", {"id": file_id})
    add_text(file_el, "name", Path(path).name)
    add_text(file_el, "pathurl", file_url(path))
    add_rate(file_el, source_fps)
    add_text(file_el, "duration", media_frames)

    media = ET.SubElement(file_el, "media")
    video = ET.SubElement(media, "video")
    add_text(video, "duration", media_frames)
    sc = ET.SubElement(video, "samplecharacteristics")
    add_rate(sc, source_fps)
    add_text(sc, "width", width)
    add_text(sc, "height", height)
    add_text(sc, "anamorphic", "FALSE")
    add_text(sc, "pixelaspectratio", "square")
    add_text(sc, "fielddominance", "none")


def add_video_clip(
    track: ET.Element,
    row: dict[str, Any],
    clip_index: int,
    sequence_fps: float,
    width: int,
    height: int,
    emitted_files: set[str],
) -> None:
    path = str(row.get("file") or "")
    source_fps = fnum(row.get("source_media_fps"), 50)
    media_duration = fnum(row.get("source_media_duration_sec"), 0)

    tl_start = seq_frames(fnum(row.get("timeline_start_sec"), 0), sequence_fps)
    tl_end = seq_frames(fnum(row.get("timeline_end_sec"), 0), sequence_fps)
    output_frames = max(1, tl_end - tl_start)

    source_in_sec = fnum(row.get("source_in_sec"), 0)
    source_consumed_sec = fnum(
        row.get("source_consumed_sec"),
        fnum(row.get("source_out_sec"), 0) - source_in_sec,
    )

    clip_in, clip_out, mixed_offset = mixed_rate_values(
        source_in_sec,
        source_consumed_sec,
        sequence_fps,
        source_fps,
    )

    # Clip duration/rate are sequence-rate values.
    clip_media_duration = max(1, seq_frames(media_duration, sequence_fps))

    clip = ET.SubElement(track, "clipitem", {"id": f"clipitem-{clip_index}"})
    add_text(clip, "name", str(row.get("filename") or Path(path).name))
    add_text(clip, "enabled", "TRUE")
    add_text(clip, "duration", clip_media_duration)
    add_rate(clip, sequence_fps)
    add_text(clip, "start", tl_start)
    add_text(clip, "end", tl_start + output_frames)
    add_text(clip, "in", clip_in)
    add_text(clip, "out", clip_out)

    if abs(source_fps - sequence_fps) > 0.01:
        add_text(clip, "mixedratesoffset", mixed_offset)

    file_id = stable_file_id(path)
    if file_id in emitted_files:
        ET.SubElement(clip, "file", {"id": file_id})
    else:
        add_full_file_definition(
            clip,
            file_id,
            row,
            width,
            height,
        )
        emitted_files.add(file_id)

    sourcetrack = ET.SubElement(clip, "sourcetrack")
    add_text(sourcetrack, "mediatype", "video")
    add_text(sourcetrack, "trackindex", 1)
    add_text(clip, "fielddominance", "none")

    add_speed_filter(clip, inum(row.get("speed_percent"), 100))


def add_music_track(
    media: ET.Element,
    music_file: str,
    total_frames: int,
    sequence_fps: float,
) -> dict[str, Any]:
    path = Path(music_file)
    if not music_file or not path.exists():
        return {
            "music_added": False,
            "music_duration_sec": 0.0,
            "music_end_sec": 0.0,
            "audio_tail_silence_sec": round(total_frames / sequence_fps, 6),
        }

    meta = probe_media(path, sequence_fps)
    duration = fnum(meta.get("duration_sec"), 0)
    source_frames_total = seq_frames(duration, sequence_fps)
    play_frames = min(total_frames, source_frames_total)

    if source_frames_total <= 0:
        return {
            "music_added": False,
            "music_duration_sec": duration,
            "music_end_sec": 0.0,
            "audio_tail_silence_sec": round(total_frames / sequence_fps, 6),
        }

    audio = ET.SubElement(media, "audio")
    add_text(audio, "numOutputChannels", 2)
    track = ET.SubElement(audio, "track")

    clip = ET.SubElement(track, "clipitem", {"id": "music-clip-1"})
    add_text(clip, "name", path.name)
    add_text(clip, "enabled", "TRUE")
    add_text(clip, "duration", source_frames_total)
    add_rate(clip, sequence_fps)
    add_text(clip, "start", 0)
    add_text(clip, "end", play_frames)
    add_text(clip, "in", 0)
    add_text(clip, "out", play_frames)

    file_el = ET.SubElement(clip, "file", {"id": "music-file-1"})
    add_text(file_el, "name", path.name)
    add_text(file_el, "pathurl", file_url(path))
    add_rate(file_el, sequence_fps)
    add_text(file_el, "duration", source_frames_total)

    file_media = ET.SubElement(file_el, "media")
    file_audio = ET.SubElement(file_media, "audio")
    sc = ET.SubElement(file_audio, "samplecharacteristics")
    add_text(sc, "depth", 16)
    add_text(sc, "samplerate", 48000)
    add_text(file_audio, "channelcount", 2)

    sourcetrack = ET.SubElement(clip, "sourcetrack")
    add_text(sourcetrack, "mediatype", "audio")
    add_text(sourcetrack, "trackindex", 1)

    return {
        "music_added": True,
        "music_duration_sec": round(duration, 6),
        "music_end_sec": round(play_frames / sequence_fps, 6),
        "audio_tail_silence_sec": round(
            max(0, total_frames - play_frames) / sequence_fps,
            6,
        ),
    }


def build_xml(
    segments: list[dict[str, Any]],
    music: dict[str, Any],
    sequence_fps: float,
    width: int,
    height: int,
    sequence_name: str,
    include_music: bool,
) -> tuple[str, dict[str, Any]]:
    total_frames = max(
        [
            seq_frames(
                fnum(row.get("timeline_end_sec"), 0),
                sequence_fps,
            )
            for row in segments
        ] + [1]
    )

    root = ET.Element("xmeml", {"version": "4"})
    sequence = ET.SubElement(root, "sequence", {"id": "sequence-1"})
    add_text(sequence, "name", sequence_name)
    add_text(sequence, "duration", total_frames)
    add_rate(sequence, sequence_fps)
    add_timecode(sequence, sequence_fps)

    media = ET.SubElement(sequence, "media")
    video = ET.SubElement(media, "video")
    fmt = ET.SubElement(video, "format")
    sc = ET.SubElement(fmt, "samplecharacteristics")
    add_rate(sc, sequence_fps)
    add_text(sc, "width", width)
    add_text(sc, "height", height)
    add_text(sc, "anamorphic", "FALSE")
    add_text(sc, "pixelaspectratio", "square")
    add_text(sc, "fielddominance", "none")

    track = ET.SubElement(video, "track")
    add_text(track, "enabled", "TRUE")
    add_text(track, "locked", "FALSE")

    emitted_files: set[str] = set()
    for index, row in enumerate(segments, 1):
        add_video_clip(
            track,
            row,
            index,
            sequence_fps,
            width,
            height,
            emitted_files,
        )

    if include_music:
        music_stats = add_music_track(
            media,
            str(music.get("music_file") or ""),
            total_frames,
            sequence_fps,
        )
    else:
        music_stats = {
            "music_added": False,
            "music_duration_sec": 0.0,
            "music_end_sec": 0.0,
            "audio_tail_silence_sec": 0.0,
        }

    for sec in music.get("sections") or []:
        marker = ET.SubElement(sequence, "marker")
        add_text(marker, "name", str(sec.get("label") or "SECTION").upper())
        add_text(marker, "comment", str(sec.get("rhythm") or ""))
        pos = min(
            total_frames - 1,
            seq_frames(fnum(sec.get("start_sec"), 0), sequence_fps),
        )
        add_text(marker, "in", max(0, pos))
        add_text(marker, "out", max(1, pos + 1))

    return pretty_xml(root), music_stats


# ============================================================
# Main
# ============================================================

def main() -> None:
    p = argparse.ArgumentParser(
        description="128D Premiere mixed-rate XMEML repair."
    )
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--sequence-fps", type=float, default=30.0)
    p.add_argument("--default-source-fps", type=float, default=50.0)
    p.add_argument("--max-beat-shift", type=float, default=0.24)
    p.add_argument("--min-shot", type=float, default=0.45)
    p.add_argument("--source-safety-frames", type=int, default=5)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "premiere_mixedrate_repair_128d")

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

    repaired, repair_stats = repair_timeline(
        rows,
        music,
        beats,
        sequence_fps=a.sequence_fps,
        default_source_fps=a.default_source_fps,
        max_beat_shift=max(0.0, a.max_beat_shift),
        min_shot=max(0.2, a.min_shot),
        safety_frames=max(1, a.source_safety_frames),
    )

    safe_segments, _ = build_segments(repaired, enable_slow=False)
    slow_segments, slow_stats = build_segments(repaired, enable_slow=True)
    width, height = preset_size(a.preset)

    video_only_xml, _ = build_xml(
        safe_segments,
        music,
        a.sequence_fps,
        width,
        height,
        "STT 128D VIDEO ONLY SAFE",
        include_music=False,
    )

    safe_music_xml, safe_music_stats = build_xml(
        safe_segments,
        music,
        a.sequence_fps,
        width,
        height,
        "STT 128D SAFE WITH MUSIC",
        include_music=True,
    )

    slow_music_xml, slow_music_stats = build_xml(
        slow_segments,
        music,
        a.sequence_fps,
        width,
        height,
        "STT 128D SLOW50 WITH MUSIC",
        include_music=True,
    )

    video_only_path = project / "stt_128d_VIDEO_ONLY_SAFE.xml"
    safe_music_path = project / "stt_128d_SAFE_WITH_MUSIC.xml"
    slow_music_path = project / "stt_128d_SLOW50_WITH_MUSIC.xml"
    timeline_path = project / "stt_128d_repaired_timeline_v1.json"

    for path, content in [
        (video_only_path, video_only_xml),
        (safe_music_path, safe_music_xml),
        (slow_music_path, slow_music_xml),
    ]:
        path.write_text(content, encoding="utf-8")
        ET.parse(str(path))
        (out / path.name).write_text(content, encoding="utf-8")

    report = {
        "ok": True,
        "module": "128d_premiere_mixedrate_repair",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "input_timeline": input_name,
        "sequence_fps": a.sequence_fps,
        "default_source_fps": a.default_source_fps,
        "timeline_count": len(repaired),
        **{k: v for k, v in repair_stats.items() if k != "snap_changes"},
        **slow_stats,
        "music": safe_music_stats,
        "video_only_xml": str(video_only_path),
        "safe_music_xml": str(safe_music_path),
        "slow_music_xml": str(slow_music_path),
        "items": repaired,
    }

    write_json(timeline_path, report)
    write_json(out / "FINAL_128D_REPORT.json", report)
    write_json(out / timeline_path.name, report)

    write_csv(
        out / "MIXEDRATE_SOURCE_REPORT.csv",
        repaired,
        [
            "index", "filename", "source_media_fps",
            "source_fps_detected_by", "source_media_duration_sec",
            "source_in_sec", "source_out_sec",
            "timeline_start_sec", "duration_sec", "timeline_end_sec",
            "file_exists", "file",
        ],
    )
    write_csv(
        out / "BEAT_SNAP_128D.csv",
        repair_stats.get("snap_changes") or [],
        [
            "cut_index", "original_sec", "snapped_sec",
            "shift_sec", "target_type", "strength",
        ],
    )

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "input_timeline": input_name,
        "video_only_xml": str(video_only_path),
        "safe_music_xml": str(safe_music_path),
        "slow_music_xml": str(slow_music_path),
        "timeline_count": len(repaired),
        "timeline_seconds": repair_stats.get("timeline_seconds"),
        "sequence_fps": a.sequence_fps,
        "source_fps_counts": repair_stats.get("source_fps_counts"),
        "snapped_cut_count": repair_stats.get("snapped_cut_count"),
        "source_clamped_count": repair_stats.get("source_clamped_count"),
        "missing_file_count": repair_stats.get("missing_file_count"),
        "unknown_duration_count": repair_stats.get("unknown_duration_count"),
        "slow_applied_count": slow_stats.get("slow_applied_count"),
        "slow_disabled_count": slow_stats.get("slow_disabled_count"),
        "music_duration_sec": safe_music_stats.get("music_duration_sec"),
        "music_end_sec": safe_music_stats.get("music_end_sec"),
        "audio_tail_silence_sec": safe_music_stats.get("audio_tail_silence_sec"),
        "fix": "128d_premiere_mixedrate_repair",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
