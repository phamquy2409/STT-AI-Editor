from __future__ import annotations

import argparse
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.dom import minidom


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def inum(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def file_url(path: str | Path) -> str:
    value = str(Path(path).resolve()).replace("\\", "/")
    return "file://localhost/" + quote(value, safe="/:")


def xml_rate_parts(fps: float) -> tuple[int, str]:
    for real, base in [
        (24000 / 1001, 24),
        (30000 / 1001, 30),
        (60000 / 1001, 60),
    ]:
        if abs(fps - real) < 0.03:
            return base, "TRUE"
    return max(1, int(round(fps))), "FALSE"


def read_rate(rate_element: ET.Element | None, default: float = 30.0) -> float:
    if rate_element is None:
        return default

    timebase = fnum(rate_element.findtext("timebase"), default)
    ntsc = str(rate_element.findtext("ntsc") or "FALSE").upper() == "TRUE"

    if not ntsc:
        return timebase

    if int(round(timebase)) == 24:
        return 24000 / 1001
    if int(round(timebase)) == 30:
        return 30000 / 1001
    if int(round(timebase)) == 60:
        return 60000 / 1001
    return timebase


def add_text(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    element = ET.SubElement(parent, tag)
    element.text = str(value)
    return element


def add_rate(parent: ET.Element, fps: float) -> None:
    timebase, ntsc = xml_rate_parts(fps)
    rate = ET.SubElement(parent, "rate")
    add_text(rate, "timebase", timebase)
    add_text(rate, "ntsc", ntsc)


def probe_audio(path: str | Path) -> dict[str, Any]:
    result = {
        "duration_sec": 0.0,
        "sample_rate": 48000,
        "channels": 2,
    }

    try:
        run = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-print_format", "json",
                "-show_entries",
                "stream=codec_type,duration,sample_rate,channels:"
                "format=duration",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )

        if run.returncode == 0 and (run.stdout or "").strip():
            data = json.loads(run.stdout)
            format_duration = fnum(
                (data.get("format") or {}).get("duration"),
                0,
            )
            streams = list(data.get("streams") or [])
            audio = next(
                (row for row in streams if row.get("codec_type") == "audio"),
                {},
            )

            result["duration_sec"] = max(
                format_duration,
                fnum(audio.get("duration"), 0),
            )
            result["sample_rate"] = inum(
                audio.get("sample_rate"),
                48000,
            )
            result["channels"] = max(
                1,
                inum(audio.get("channels"), 2),
            )
    except Exception:
        pass

    return result


def pretty_xml(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="utf-8")
    output = minidom.parseString(raw).toprettyxml(
        indent="  ",
        encoding="utf-8",
    ).decode("utf-8")

    lines = output.splitlines()
    if lines and lines[0].startswith("<?xml"):
        lines.insert(1, "<!DOCTYPE xmeml>")
    return "\n".join(lines) + "\n"


def remove_existing_audio(media: ET.Element) -> int:
    removed = 0
    for child in list(media):
        if child.tag == "audio":
            media.remove(child)
            removed += 1
    return removed


def inject_music(
    input_xml: Path,
    output_xml: Path,
    music_file: Path,
) -> dict[str, Any]:
    tree = ET.parse(str(input_xml))
    root = tree.getroot()

    sequence = root.find(".//sequence")
    if sequence is None:
        raise RuntimeError("Không tìm thấy sequence trong XML.")

    media = sequence.find("media")
    if media is None:
        media = ET.SubElement(sequence, "media")

    sequence_fps = read_rate(sequence.find("rate"), 30.0)
    sequence_frames = inum(sequence.findtext("duration"), 0)

    if sequence_frames <= 0:
        video_ends = [
            inum(value.text, 0)
            for value in sequence.findall("./media/video/track/clipitem/end")
        ]
        sequence_frames = max(video_ends + [1])
        duration_element = sequence.find("duration")
        if duration_element is None:
            duration_element = ET.SubElement(sequence, "duration")
        duration_element.text = str(sequence_frames)

    audio_meta = probe_audio(music_file)
    audio_duration_sec = fnum(audio_meta.get("duration_sec"), 0)
    audio_frames = max(
        1,
        int(round(audio_duration_sec * sequence_fps)),
    )
    play_frames = min(sequence_frames, audio_frames)

    removed_audio_tracks = remove_existing_audio(media)

    audio = ET.SubElement(media, "audio")
    add_text(audio, "numOutputChannels", 2)

    track = ET.SubElement(audio, "track")
    add_text(track, "enabled", "TRUE")
    add_text(track, "locked", "FALSE")

    clip = ET.SubElement(
        track,
        "clipitem",
        {"id": "stt-music-clip-128f"},
    )
    add_text(clip, "name", music_file.name)
    add_text(clip, "enabled", "TRUE")
    add_text(clip, "duration", audio_frames)
    add_rate(clip, sequence_fps)
    add_text(clip, "start", 0)
    add_text(clip, "end", play_frames)
    add_text(clip, "in", 0)
    add_text(clip, "out", play_frames)

    file_element = ET.SubElement(
        clip,
        "file",
        {"id": "stt-music-file-128f"},
    )
    add_text(file_element, "name", music_file.name)
    add_text(file_element, "pathurl", file_url(music_file))
    add_rate(file_element, sequence_fps)
    add_text(file_element, "duration", audio_frames)

    file_media = ET.SubElement(file_element, "media")
    file_audio = ET.SubElement(file_media, "audio")
    add_text(file_audio, "channelcount", max(1, audio_meta["channels"]))

    sample = ET.SubElement(file_audio, "samplecharacteristics")
    add_text(sample, "depth", 16)
    add_text(sample, "samplerate", audio_meta["sample_rate"])

    source_track = ET.SubElement(clip, "sourcetrack")
    add_text(source_track, "mediatype", "audio")
    add_text(source_track, "trackindex", 1)

    output_xml.write_text(
        pretty_xml(root),
        encoding="utf-8",
    )
    ET.parse(str(output_xml))

    return {
        "input_xml": str(input_xml),
        "output_xml": str(output_xml),
        "music_file": str(music_file),
        "sequence_fps": round(sequence_fps, 6),
        "sequence_frames": sequence_frames,
        "sequence_seconds": round(sequence_frames / sequence_fps, 6),
        "music_duration_sec": round(audio_duration_sec, 6),
        "music_frames": audio_frames,
        "music_end_sec": round(play_frames / sequence_fps, 6),
        "audio_tail_silence_sec": round(
            max(0, sequence_frames - play_frames) / sequence_fps,
            6,
        ),
        "removed_existing_audio_tracks": removed_audio_tracks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="128F inject music into the already-fixed 128E XML."
    )
    parser.add_argument(
        "--project",
        default="D:/STT Projects/Wedding_Test_001",
    )
    parser.add_argument(
        "--music",
        required=True,
        help="Đường dẫn đầy đủ tới file nhạc.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
    )
    args = parser.parse_args()

    project = Path(args.project)
    music_file = Path(args.music)

    if not music_file.exists():
        print(json.dumps({
            "ok": False,
            "error": "MUSIC_FILE_NOT_FOUND",
            "music_file": str(music_file),
        }, ensure_ascii=False, indent=2))
        return

    candidates = [
        (
            project / "stt_128e_VIDEO_ONLY_BAD_SOURCE_REPLACED.xml",
            project / "stt_128f_SAFE_WITH_MUSIC.xml",
            "safe",
        ),
        (
            project / "stt_128e_SLOW50_WITH_MUSIC_BAD_SOURCE_REPLACED.xml",
            project / "stt_128f_SLOW50_WITH_MUSIC.xml",
            "slow50",
        ),
    ]

    report_dir = (
        project
        / "exports"
        / f"music_injector_128f_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    results = []
    missing_inputs = []

    for input_xml, output_xml, mode in candidates:
        if not input_xml.exists():
            missing_inputs.append(str(input_xml))
            continue

        result = inject_music(
            input_xml,
            output_xml,
            music_file,
        )
        result["mode"] = mode
        results.append(result)

        copy_path = report_dir / output_xml.name
        copy_path.write_bytes(output_xml.read_bytes())

    final = {
        "ok": bool(results),
        "module": "128f_music_injector",
        "report_dir": str(report_dir),
        "music_file": str(music_file),
        "generated_count": len(results),
        "missing_inputs": missing_inputs,
        "results": results,
        "fix": "128f_music_injector",
    }

    (report_dir / "FINAL_128F_REPORT.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(final, ensure_ascii=False, indent=2))

    if results and not args.no_open:
        try:
            os.startfile(str(report_dir))  # type: ignore[attr-defined]
        except Exception:
            pass


if __name__ == "__main__":
    main()
