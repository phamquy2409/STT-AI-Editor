from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.dom import minidom

from music_climax_common import *

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
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

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

def split_slow_segments(item: dict[str, Any]) -> list[dict[str, Any]]:
    duration = fnum(item.get("duration_sec"), 0)
    start_tl = fnum(item.get("timeline_start_sec"), 0)
    src_start = fnum(item.get("source_in_sec"), 0)
    media_dur = media_duration(str(item.get("file") or ""))

    if not item.get("slow_recommended") or duration < 3.2:
        return [{
            **item,
            "segment_kind": "normal",
            "speed_percent": 100,
            "timeline_start_sec": start_tl,
            "timeline_end_sec": start_tl + duration,
            "duration_sec": duration,
            "source_in_sec": src_start,
            "source_out_sec": src_start + duration,
        }]

    slow_out = clamp(duration * 0.48, 1.2, 2.8)
    anchor_global = fnum(item.get("emphasis_time_sec"), 0)
    if anchor_global <= start_tl or anchor_global >= start_tl + duration:
        anchor_offset = duration * 0.56
    else:
        anchor_offset = anchor_global - start_tl

    pre_out = clamp(anchor_offset - slow_out / 2, 0.65, max(0.65, duration - slow_out - 0.65))
    post_out = duration - pre_out - slow_out
    if post_out < 0.55:
        shift = 0.55 - post_out
        pre_out = max(0.55, pre_out - shift)
        post_out = duration - pre_out - slow_out

    slow_speed = 50
    source_consumed = pre_out + slow_out * 0.50 + post_out
    if media_dur > 0 and src_start + source_consumed > media_dur:
        src_start = max(0.0, media_dur - source_consumed - 0.05)

    segments = []
    tl = start_tl
    src = src_start

    if pre_out > 0.02:
        segments.append({
            **item,
            "segment_kind": "normal_before_slow",
            "speed_percent": 100,
            "timeline_start_sec": tl,
            "timeline_end_sec": tl + pre_out,
            "duration_sec": pre_out,
            "source_in_sec": src,
            "source_out_sec": src + pre_out,
        })
        tl += pre_out
        src += pre_out

    segments.append({
        **item,
        "segment_kind": "slow_emphasis",
        "speed_percent": slow_speed,
        "timeline_start_sec": tl,
        "timeline_end_sec": tl + slow_out,
        "duration_sec": slow_out,
        "source_in_sec": src,
        "source_out_sec": src + slow_out * 0.50,
    })
    tl += slow_out
    src += slow_out * 0.50

    if post_out > 0.02:
        segments.append({
            **item,
            "segment_kind": "normal_after_slow",
            "speed_percent": 100,
            "timeline_start_sec": tl,
            "timeline_end_sec": tl + post_out,
            "duration_sec": post_out,
            "source_in_sec": src,
            "source_out_sec": src + post_out,
        })

    return segments

def build_segments(rows: list[dict[str, Any]], enable_slow: bool) -> list[dict[str, Any]]:
    out = []
    cursor = 0.0
    for shot_index, item in enumerate(rows, 1):
        parts = split_slow_segments(item) if enable_slow else [{
            **item,
            "segment_kind": "safe_normal",
            "speed_percent": 100,
            "duration_sec": fnum(item.get("duration_sec"), 0),
            "source_in_sec": fnum(item.get("source_in_sec"), 0),
            "source_out_sec": fnum(item.get("source_in_sec"), 0) + fnum(item.get("duration_sec"), 0),
        }]
        for part_index, part in enumerate(parts, 1):
            row = dict(part)
            dur = fnum(row.get("duration_sec"), 0)
            row["shot_index"] = shot_index
            row["part_index"] = part_index
            row["timeline_start_sec"] = round(cursor, 4)
            row["timeline_end_sec"] = round(cursor + dur, 4)
            cursor += dur
            out.append(row)
    return out

def add_file_block(
    clip: ET.Element,
    file_id: str,
    path: str,
    fps: int,
    width: int,
    height: int,
    file_duration_frames: int,
) -> None:
    file_el = ET.SubElement(clip, "file", {"id": file_id})
    add_text(file_el, "name", Path(path).name)
    add_text(file_el, "pathurl", file_url(path))
    add_rate(file_el, fps)
    add_text(file_el, "duration", max(1, file_duration_frames))
    media = ET.SubElement(file_el, "media")
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
    output_start = frames(fnum(row.get("timeline_start_sec"), 0), fps)
    output_end = frames(fnum(row.get("timeline_end_sec"), 0), fps)
    src_in = frames(fnum(row.get("source_in_sec"), 0), fps)
    src_out = frames(fnum(row.get("source_out_sec"), 0), fps)
    real_duration = media_duration(path)
    file_duration_frames = frames(real_duration, fps) if real_duration > 0 else max(src_out + fps * 10, fps * 3600)

    clip = ET.SubElement(track, "clipitem", {"id": f"clipitem-{idx}"})
    add_text(clip, "name", str(row.get("filename") or Path(path).name))
    add_text(clip, "enabled", "TRUE")
    add_text(clip, "duration", max(file_duration_frames, src_out + fps))
    add_rate(clip, fps)
    add_text(clip, "start", output_start)
    add_text(clip, "end", output_end)
    add_text(clip, "in", src_in)
    add_text(clip, "out", max(src_in + 1, src_out))
    add_file_block(clip, f"file-{idx}", path, fps, width, height, file_duration_frames)

    source_track = ET.SubElement(clip, "sourcetrack")
    add_text(source_track, "mediatype", "video")
    add_text(source_track, "trackindex", 1)
    add_text(clip, "fielddominance", "none")
    add_speed_filter(clip, inum(row.get("speed_percent"), 100))

def build_xml(
    segments: list[dict[str, Any]],
    music: dict[str, Any],
    fps: int,
    width: int,
    height: int,
    sequence_name: str,
) -> str:
    total_frames = max([frames(fnum(x.get("timeline_end_sec"), 0), fps) for x in segments] + [1])
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

    track = ET.SubElement(video, "track")
    for i, row in enumerate(segments, 1):
        add_video_clip(track, row, i, fps, width, height)

    music_file = str(music.get("music_file") or "")
    if music_file and Path(music_file).exists():
        audio = ET.SubElement(media, "audio")
        add_text(audio, "numOutputChannels", 2)
        atrack = ET.SubElement(audio, "track")
        mclip = ET.SubElement(atrack, "clipitem", {"id": "music-clip-1"})
        add_text(mclip, "name", Path(music_file).name)
        add_text(mclip, "duration", total_frames)
        add_rate(mclip, fps)
        add_text(mclip, "start", 0)
        add_text(mclip, "end", total_frames)
        add_text(mclip, "in", 0)
        add_text(mclip, "out", total_frames)

        mf = ET.SubElement(mclip, "file", {"id": "music-file-1"})
        add_text(mf, "name", Path(music_file).name)
        add_text(mf, "pathurl", file_url(music_file))
        add_rate(mf, fps)
        add_text(mf, "duration", max(total_frames, frames(media_duration(music_file), fps)))
        mm = ET.SubElement(mf, "media")
        ma = ET.SubElement(mm, "audio")
        add_text(ma, "channelcount", 2)

    for sec in music.get("sections") or []:
        marker = ET.SubElement(seq, "marker")
        add_text(marker, "name", str(sec.get("label") or "SECTION").upper())
        add_text(marker, "comment", str(sec.get("rhythm") or ""))
        st = frames(fnum(sec.get("start_sec"), 0), fps)
        add_text(marker, "in", st)
        add_text(marker, "out", st + 1)

    for i, point in enumerate(music.get("emphasis_points") or [], 1):
        marker = ET.SubElement(seq, "marker")
        add_text(marker, "name", f"EMPHASIS_{i}")
        add_text(marker, "comment", str(point.get("beat_type") or "music_peak"))
        st = frames(fnum(point.get("time_sec"), 0), fps)
        add_text(marker, "in", st)
        add_text(marker, "out", st + 1)

    return pretty_xml(root)

def main() -> None:
    p = argparse.ArgumentParser(description="128 Slow 50% plan + Premiere XML exporter.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "slow_climax_xml_128")
    tl = read_json(project / "stt_climax_directed_timeline_v1.json")
    music = read_json(project / "stt_music_structure_climax_v3.json")
    rows = list(tl.get("items") or [])

    if not rows:
        res = {"ok": False, "error": "NO_CLIMAX_TIMELINE", "message": "Run 127 first."}
        write_json(out / "SLOW_EXPORT_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    width, height = preset_size(a.preset)
    slow_segments = build_segments(rows, True)
    safe_segments = build_segments(rows, False)

    slow_xml = build_xml(
        slow_segments, music, a.fps, width, height,
        "STT MUSIC CLIMAX SLOW 50"
    )
    safe_xml = build_xml(
        safe_segments, music, a.fps, width, height,
        "STT MUSIC CLIMAX SAFE"
    )

    slow_path = project / "stt_climax_slow_premiere_import.xml"
    safe_path = project / "stt_climax_directed_SAFE_NO_SPEED.xml"
    slow_path.write_text(slow_xml, encoding="utf-8")
    safe_path.write_text(safe_xml, encoding="utf-8")
    (out / slow_path.name).write_text(slow_xml, encoding="utf-8")
    (out / safe_path.name).write_text(safe_xml, encoding="utf-8")

    ET.parse(str(slow_path))
    ET.parse(str(safe_path))

    plan = {
        "ok": True,
        "module": "128_slow_climax_xml",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "output_xml": str(slow_path),
        "safe_xml": str(safe_path),
        "shot_count": len(rows),
        "segment_count": len(slow_segments),
        "slow_shot_count": sum(1 for x in rows if x.get("slow_recommended")),
        "slow_segment_count": sum(1 for x in slow_segments if inum(x.get("speed_percent"), 100) == 50),
        "minimum_speed_percent": 50,
        "timeline_seconds": slow_segments[-1]["timeline_end_sec"] if slow_segments else 0,
        "music_file": music.get("music_file"),
        "segments": slow_segments,
        "note": "V1 splits a shot into 100%-50%-100% segments. Smooth bezier ramp will be added in Premiere Extension.",
    }

    write_json(project / "stt_speed_ramp_plan_v1.json", plan)
    write_json(out / "stt_speed_ramp_plan_v1.json", plan)
    write_csv(out / "SPEED_RAMP_SEGMENTS.csv", slow_segments, [
        "shot_index", "part_index", "segment_kind", "speed_percent",
        "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "source_in_sec", "source_out_sec", "music_section",
        "is_main_climax_shot", "emphasis_time_sec", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "output_xml": str(slow_path),
        "safe_xml": str(safe_path),
        "shot_count": len(rows),
        "segment_count": len(slow_segments),
        "slow_shot_count": plan["slow_shot_count"],
        "slow_segment_count": plan["slow_segment_count"],
        "minimum_speed_percent": 50,
        "timeline_seconds": plan["timeline_seconds"],
        "fix": "128_slow_climax_xml",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
