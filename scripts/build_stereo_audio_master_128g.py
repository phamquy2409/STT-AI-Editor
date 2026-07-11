from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.dom import minidom


AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".aiff", ".aif"}


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


def add_text(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    element = ET.SubElement(parent, tag)
    element.text = str(value)
    return element


def file_url(path: str | Path) -> str:
    value = str(Path(path).resolve()).replace("\\", "/")
    return "file://localhost/" + quote(value, safe="/:")


def read_sequence_fps(sequence: ET.Element) -> float:
    rate = sequence.find("rate")
    if rate is None:
        return 30.0

    timebase = fnum(rate.findtext("timebase"), 30.0)
    ntsc = str(rate.findtext("ntsc") or "FALSE").upper() == "TRUE"

    if not ntsc:
        return timebase

    rounded = int(round(timebase))
    if rounded == 24:
        return 24000 / 1001
    if rounded == 30:
        return 30000 / 1001
    if rounded == 60:
        return 60000 / 1001
    return timebase


def xml_rate_parts(fps: float) -> tuple[int, str]:
    for real, base in [
        (24000 / 1001, 24),
        (30000 / 1001, 30),
        (60000 / 1001, 60),
    ]:
        if abs(fps - real) < 0.03:
            return base, "TRUE"
    return max(1, int(round(fps))), "FALSE"


def add_rate(parent: ET.Element, fps: float) -> None:
    timebase, ntsc = xml_rate_parts(fps)
    rate = ET.SubElement(parent, "rate")
    add_text(rate, "timebase", timebase)
    add_text(rate, "ntsc", ntsc)


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



def resolve_ffmpeg() -> str:
    candidates: list[Path] = []

    # 1. PATH
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 2. Environment variable
    env_value = os.environ.get("FFMPEG_BINARY", "").strip()
    if env_value and Path(env_value).exists():
        return env_value

    # 3. Project / virtualenv common locations
    here = Path(__file__).resolve()
    project_root = here.parent.parent
    candidates.extend([
        project_root / "ffmpeg.exe",
        project_root / "tools" / "ffmpeg.exe",
        project_root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe",
        project_root / ".venv" / "Scripts" / "ffmpeg.exe",
        project_root / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries",
    ])

    # 4. imageio-ffmpeg package
    try:
        import imageio_ffmpeg  # type: ignore
        bundled = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if bundled.exists():
            return str(bundled)
    except Exception:
        pass

    # 5. Search imageio_ffmpeg binaries folder
    binary_dirs = [
        project_root / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries",
        Path(sys.executable).resolve().parent.parent / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries",
    ]
    for directory in binary_dirs:
        if directory.exists():
            for candidate in directory.glob("ffmpeg-*.exe"):
                if candidate.exists():
                    return str(candidate)

    # 6. Common Windows install locations
    common = [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe"),
    ]
    for candidate in common:
        if candidate.exists():
            return str(candidate)

    # 7. WinGet package cache
    local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
    winget_root = local_appdata / "Microsoft" / "WinGet" / "Packages"
    if winget_root.exists():
        for candidate in winget_root.glob("**/ffmpeg.exe"):
            if candidate.exists():
                return str(candidate)

    raise FileNotFoundError(
        "Không tìm thấy ffmpeg.exe. Chạy lệnh sau trong PowerShell:\n"
        "python -m pip install imageio-ffmpeg\n"
        "Sau đó chạy lại 128G2."
    )


def resolve_ffprobe() -> str | None:
    found = shutil.which("ffprobe")
    if found:
        return found

    ffmpeg_path = Path(resolve_ffmpeg())
    sibling = ffmpeg_path.with_name("ffprobe.exe")
    if sibling.exists():
        return str(sibling)

    return None


def probe_audio(path: str | Path) -> dict[str, Any]:
    result = {
        "duration_sec": 0.0,
        "sample_rate": 48000,
        "channels": 2,
        "codec_name": "",
    }

    try:
        ffprobe_path = resolve_ffprobe()
        if not ffprobe_path:
            raise FileNotFoundError("ffprobe.exe not found")
        run = subprocess.run(
            [
                ffprobe_path, "-v", "error",
                "-print_format", "json",
                "-show_entries",
                "stream=codec_type,codec_name,duration,sample_rate,channels:"
                "format=duration",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if run.returncode == 0 and (run.stdout or "").strip():
            data = json.loads(run.stdout)
            streams = list(data.get("streams") or [])
            audio = next(
                (row for row in streams if row.get("codec_type") == "audio"),
                {},
            )

            result["duration_sec"] = max(
                fnum((data.get("format") or {}).get("duration"), 0),
                fnum(audio.get("duration"), 0),
            )
            result["sample_rate"] = inum(audio.get("sample_rate"), 48000)
            result["channels"] = max(1, inum(audio.get("channels"), 2))
            result["codec_name"] = str(audio.get("codec_name") or "")
    except Exception:
        pass

    return result


def collect_audio_candidates(root: Path) -> list[Path]:
    if not root.exists():
        return []

    return sorted(
        [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
        ],
        key=lambda path: str(path).lower(),
    )


def locate_music(
    project: Path,
    explicit_music: str,
    music_root: str,
) -> tuple[Path | None, list[str]]:
    candidates: list[Path] = []

    if explicit_music:
        explicit = Path(explicit_music)
        if explicit.exists():
            return explicit, [str(explicit)]

    music_data = read_json(project / "stt_music_structure_climax_v3.json")
    remembered = str(music_data.get("music_file") or "").strip()

    if remembered:
        remembered_path = Path(remembered)
        if remembered_path.exists():
            return remembered_path, [str(remembered_path)]

    search_root = Path(music_root) if music_root else project.parent
    candidates = collect_audio_candidates(search_root)

    if remembered:
        remembered_name = Path(remembered).stem.lower()
        remembered_tokens = [
            token
            for token in remembered_name.replace("-", " ").replace("_", " ").split()
            if len(token) >= 3
        ]

        scored: list[tuple[int, Path]] = []
        for candidate in candidates:
            name = candidate.stem.lower()
            score = sum(1 for token in remembered_tokens if token in name)
            if "enemy of truth" in name:
                score += 10
            scored.append((score, candidate))

        scored.sort(key=lambda item: (-item[0], str(item[1]).lower()))
        if scored and scored[0][0] > 0:
            return scored[0][1], [str(path) for _, path in scored[:20]]

    enemy_matches = [
        path for path in candidates
        if "enemy of truth" in path.stem.lower()
    ]
    if enemy_matches:
        return enemy_matches[0], [str(path) for path in enemy_matches]

    if len(candidates) == 1:
        return candidates[0], [str(candidates[0])]

    return None, [str(path) for path in candidates[:50]]


def convert_to_stereo_wav(
    music_file: Path,
    output_wav: Path,
) -> dict[str, Any]:
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = resolve_ffmpeg()

    command = [
        ffmpeg_path, "-v", "error", "-y",
        "-i", str(music_file),
        "-vn",
        "-ac", "2",
        "-ar", "48000",
        "-c:a", "pcm_s16le",
        str(output_wav),
    ]

    run = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if run.returncode != 0 or not output_wav.exists():
        raise RuntimeError(
            "FFmpeg không tạo được WAV stereo.\n"
            f"Command: {' '.join(command)}\n"
            f"Error: {run.stderr}"
        )

    info = probe_audio(output_wav)
    if info["channels"] != 2:
        raise RuntimeError(
            f"WAV sau chuyển đổi không phải stereo: {info['channels']} channel."
        )
    if abs(info["sample_rate"] - 48000) > 1:
        raise RuntimeError(
            f"WAV sau chuyển đổi không phải 48 kHz: {info['sample_rate']}."
        )

    return info


def remove_existing_audio(media: ET.Element) -> int:
    removed = 0
    for child in list(media):
        if child.tag == "audio":
            media.remove(child)
            removed += 1
    return removed


def add_audio_outputs(audio: ET.Element) -> None:
    outputs = ET.SubElement(audio, "outputs")

    group = ET.SubElement(outputs, "group")
    add_text(group, "index", 1)
    add_text(group, "numchannels", 2)
    add_text(group, "downmix", 0)

    channel_1 = ET.SubElement(group, "channel")
    add_text(channel_1, "index", 1)

    channel_2 = ET.SubElement(group, "channel")
    add_text(channel_2, "index", 2)


def inject_stereo_track(
    input_xml: Path,
    output_xml: Path,
    stereo_wav: Path,
) -> dict[str, Any]:
    tree = ET.parse(str(input_xml))
    root = tree.getroot()

    sequence = root.find(".//sequence")
    if sequence is None:
        raise RuntimeError(f"Không tìm thấy sequence trong {input_xml}")

    media = sequence.find("media")
    if media is None:
        media = ET.SubElement(sequence, "media")

    sequence_fps = read_sequence_fps(sequence)
    sequence_frames = inum(sequence.findtext("duration"), 0)

    if sequence_frames <= 0:
        sequence_frames = max(
            [
                inum(end.text, 0)
                for end in sequence.findall("./media/video/track/clipitem/end")
            ] + [1]
        )

    wav_info = probe_audio(stereo_wav)
    audio_frames = max(
        1,
        int(round(wav_info["duration_sec"] * sequence_fps)),
    )
    play_frames = min(sequence_frames, audio_frames)

    removed_audio_nodes = remove_existing_audio(media)

    audio = ET.SubElement(media, "audio")
    add_text(audio, "numOutputChannels", 2)

    audio_format = ET.SubElement(audio, "format")
    sample = ET.SubElement(audio_format, "samplecharacteristics")
    add_text(sample, "depth", 16)
    add_text(sample, "samplerate", 48000)

    add_audio_outputs(audio)

    track = ET.SubElement(
        audio,
        "track",
        {
            "premiereTrackType": "Stereo",
            "MZ.TrackName": "Music Stereo",
            "MZ.TrackTargeted": "1",
        },
    )
    add_text(track, "enabled", "TRUE")
    add_text(track, "locked", "FALSE")
    add_text(track, "outputchannelindex", 1)

    clip = ET.SubElement(
        track,
        "clipitem",
        {
            "id": "stt-music-stereo-clip-128g",
            "premiereChannelType": "stereo",
        },
    )
    add_text(clip, "name", stereo_wav.name)
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
        {"id": "stt-music-stereo-file-128g"},
    )
    add_text(file_element, "name", stereo_wav.name)
    add_text(file_element, "pathurl", file_url(stereo_wav))
    add_rate(file_element, sequence_fps)
    add_text(file_element, "duration", audio_frames)

    file_media = ET.SubElement(file_element, "media")
    file_audio = ET.SubElement(file_media, "audio")

    file_sample = ET.SubElement(file_audio, "samplecharacteristics")
    add_text(file_sample, "depth", 16)
    add_text(file_sample, "samplerate", 48000)

    add_text(file_audio, "channelcount", 2)

    source_channel_1 = ET.SubElement(file_audio, "audiochannel")
    add_text(source_channel_1, "sourcechannel", 1)

    source_channel_2 = ET.SubElement(file_audio, "audiochannel")
    add_text(source_channel_2, "sourcechannel", 2)

    source_track = ET.SubElement(clip, "sourcetrack")
    add_text(source_track, "mediatype", "audio")
    add_text(source_track, "trackindex", 1)

    labels = ET.SubElement(clip, "labels")
    add_text(labels, "label2", "Caribbean")

    output_xml.write_text(pretty_xml(root), encoding="utf-8")
    ET.parse(str(output_xml))

    return {
        "input_xml": str(input_xml),
        "output_xml": str(output_xml),
        "sequence_fps": round(sequence_fps, 6),
        "sequence_frames": sequence_frames,
        "sequence_seconds": round(sequence_frames / sequence_fps, 6),
        "audio_frames": audio_frames,
        "music_duration_sec": round(wav_info["duration_sec"], 6),
        "music_end_sec": round(play_frames / sequence_fps, 6),
        "audio_tail_silence_sec": round(
            max(0, sequence_frames - play_frames) / sequence_fps,
            6,
        ),
        "removed_audio_nodes": removed_audio_nodes,
        "track_type": "Stereo",
        "channels": wav_info["channels"],
        "sample_rate": wav_info["sample_rate"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="128G: convert music to stereo 48 kHz WAV and inject one Premiere Stereo track."
    )
    parser.add_argument(
        "--project",
        default="D:/STT Projects/Wedding_Test_001",
    )
    parser.add_argument(
        "--music",
        default="",
        help="Đường dẫn đầy đủ file nhạc. Có thể bỏ trống để tự tìm.",
    )
    parser.add_argument(
        "--music-root",
        default="D:/27thang6pschh",
        help="Thư mục tìm nhạc khi --music bỏ trống.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
    )
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = (
        project
        / "exports"
        / f"stereo_audio_master_128g_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    music_file, candidates = locate_music(
        project,
        args.music,
        args.music_root,
    )

    if music_file is None:
        result = {
            "ok": False,
            "error": "MUSIC_NOT_RESOLVED",
            "music_root": args.music_root,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "message": "Chạy lại với --music và đường dẫn FullName chính xác.",
        }
        write_json(report_dir / "FINAL_128G_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    stereo_wav = project / "stt_128g_music_stereo_48k.wav"

    try:
        wav_info = convert_to_stereo_wav(
            music_file,
            stereo_wav,
        )
    except Exception as exc:
        result = {
            "ok": False,
            "error": "STEREO_WAV_CONVERSION_FAILED",
            "music_file": str(music_file),
            "details": str(exc),
            "fix_hint": "Chạy: python -m pip install imageio-ffmpeg",
        }
        write_json(report_dir / "FINAL_128G_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    input_candidates = [
        (
            project / "stt_128e_VIDEO_ONLY_BAD_SOURCE_REPLACED.xml",
            project / "stt_128g_SAFE_STEREO_MUSIC.xml",
            "safe",
        ),
        (
            project / "stt_128e_SLOW50_WITH_MUSIC_BAD_SOURCE_REPLACED.xml",
            project / "stt_128g_SLOW50_STEREO_MUSIC.xml",
            "slow50",
        ),
    ]

    fallback_candidates = {
        "safe": [
            project / "stt_128d_VIDEO_ONLY_SAFE.xml",
            project / "stt_128f_SAFE_WITH_MUSIC.xml",
        ],
        "slow50": [
            project / "stt_128d_SLOW50_WITH_MUSIC.xml",
            project / "stt_128f_SLOW50_WITH_MUSIC.xml",
        ],
    }

    results = []
    missing_modes = []

    for preferred_input, output_xml, mode in input_candidates:
        input_xml = preferred_input

        if not input_xml.exists():
            input_xml = next(
                (
                    candidate
                    for candidate in fallback_candidates[mode]
                    if candidate.exists()
                ),
                preferred_input,
            )

        if not input_xml.exists():
            missing_modes.append({
                "mode": mode,
                "expected": str(preferred_input),
                "fallbacks": [
                    str(path) for path in fallback_candidates[mode]
                ],
            })
            continue

        result = inject_stereo_track(
            input_xml,
            output_xml,
            stereo_wav,
        )
        result["mode"] = mode
        results.append(result)

        shutil.copy2(output_xml, report_dir / output_xml.name)

    if stereo_wav.exists():
        shutil.copy2(stereo_wav, report_dir / stereo_wav.name)

    final = {
        "ok": bool(results),
        "module": "128g_stereo_audio_master",
        "report_dir": str(report_dir),
        "original_music_file": str(music_file),
        "stereo_wav": str(stereo_wav),
        "stereo_wav_channels": wav_info["channels"],
        "stereo_wav_sample_rate": wav_info["sample_rate"],
        "generated_count": len(results),
        "missing_modes": missing_modes,
        "results": results,
        "fix": "128g_stereo_audio_master",
    }

    write_json(report_dir / "FINAL_128G_REPORT.json", final)
    print(json.dumps(final, ensure_ascii=False, indent=2))

    if results and not args.no_open:
        try:
            os.startfile(str(report_dir))  # type: ignore[attr-defined]
        except Exception:
            pass


if __name__ == "__main__":
    main()
