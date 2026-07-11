from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".aiff", ".aif"}


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


def resolve_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found

    env_value = os.environ.get("FFMPEG_BINARY", "").strip()
    if env_value and Path(env_value).exists():
        return env_value

    try:
        import imageio_ffmpeg  # type: ignore
        bundled = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if bundled.exists():
            return str(bundled)
    except Exception:
        pass

    here = Path(__file__).resolve()
    root = here.parent.parent

    direct = [
        root / "ffmpeg.exe",
        root / "tools" / "ffmpeg.exe",
        root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe",
        root / ".venv" / "Scripts" / "ffmpeg.exe",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
    ]
    for candidate in direct:
        if candidate.exists():
            return str(candidate)

    for directory in [
        root / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries",
        Path(sys.executable).resolve().parent.parent / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries",
    ]:
        if directory.exists():
            matches = sorted(directory.glob("ffmpeg-*.exe"))
            if matches:
                return str(matches[0])

    local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
    winget = local_appdata / "Microsoft" / "WinGet" / "Packages"
    if winget.exists():
        matches = list(winget.glob("**/ffmpeg.exe"))
        if matches:
            return str(matches[0])

    raise FileNotFoundError(
        "Không tìm thấy FFmpeg. Chạy: python -m pip install imageio-ffmpeg"
    )


def collect_music(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        [
            p for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS
        ],
        key=lambda p: str(p).lower(),
    )


def locate_music(project: Path, explicit: str, music_root: str) -> tuple[Path | None, list[str]]:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p, [str(p)]

    music_map = read_json(project / "stt_music_structure_climax_v3.json")
    remembered = str(music_map.get("music_file") or "").strip()
    if remembered and Path(remembered).exists():
        return Path(remembered), [remembered]

    candidates = collect_music(Path(music_root))
    enemy = [p for p in candidates if "enemy of truth" in p.stem.lower()]
    if enemy:
        return enemy[0], [str(p) for p in enemy]

    if remembered:
        tokens = [
            token
            for token in Path(remembered).stem.lower().replace("-", " ").replace("_", " ").split()
            if len(token) >= 3
        ]
        ranked = []
        for p in candidates:
            name = p.stem.lower()
            score = sum(1 for token in tokens if token in name)
            ranked.append((score, p))
        ranked.sort(key=lambda x: (-x[0], str(x[1]).lower()))
        if ranked and ranked[0][0] > 0:
            return ranked[0][1], [str(p) for _, p in ranked[:20]]

    if len(candidates) == 1:
        return candidates[0], [str(candidates[0])]

    return None, [str(p) for p in candidates[:50]]


def convert_music(ffmpeg: str, source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(
        [
            ffmpeg, "-v", "error", "-y",
            "-i", str(source),
            "-vn",
            "-ac", "2",
            "-ar", "48000",
            "-c:a", "pcm_s16le",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if run.returncode != 0 or not output.exists():
        raise RuntimeError(run.stderr or "FFmpeg conversion failed")


def run_128e(
    project: Path,
    excludes: list[str],
    preset: str,
    sequence_fps: float,
    source_fps: float,
) -> dict[str, Any]:
    script_dir = Path(__file__).resolve().parent
    script_128e = script_dir / "replace_bad_source_and_export_128e.py"

    if not script_128e.exists():
        return {
            "ok": False,
            "error": "MISSING_128E",
            "expected": str(script_128e),
        }

    command = [
        sys.executable,
        str(script_128e),
        "--project", str(project),
        "--preset", preset,
        "--sequence-fps", str(sequence_fps),
        "--default-source-fps", str(source_fps),
        "--no-open",
    ]
    for name in excludes:
        command.extend(["--exclude", name])

    run = subprocess.run(
        command,
        cwd=str(script_dir.parent),
        capture_output=True,
        text=True,
    )
    return {
        "ok": run.returncode == 0,
        "returncode": run.returncode,
        "stdout": run.stdout,
        "stderr": run.stderr,
        "command": command,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="128H: build clean video-only XML and stereo WAV for Premiere Audio Bridge."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--music", default="")
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--preset", default="horizontal_4k")
    parser.add_argument("--sequence-fps", type=float, default=30.0)
    parser.add_argument("--default-source-fps", type=float, default=50.0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = (
        project / "exports" /
        f"premiere_audio_bridge_128h_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    excludes = list(args.exclude) or ["STT0043.MP4", "STT0008.MP4"]

    result_128e = run_128e(
        project,
        excludes,
        args.preset,
        args.sequence_fps,
        args.default_source_fps,
    )
    if not result_128e.get("ok"):
        result = {
            "ok": False,
            "error": "128E_FAILED",
            "details": result_128e,
        }
        write_json(report_dir / "FINAL_128H_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    source_xml = project / "stt_128e_VIDEO_ONLY_BAD_SOURCE_REPLACED.xml"
    final_xml = project / "stt_128h_VIDEO_ONLY_FINAL.xml"

    if not source_xml.exists():
        result = {
            "ok": False,
            "error": "VIDEO_ONLY_XML_NOT_FOUND",
            "expected": str(source_xml),
            "details": result_128e,
        }
        write_json(report_dir / "FINAL_128H_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    shutil.copy2(source_xml, final_xml)
    shutil.copy2(final_xml, report_dir / final_xml.name)

    music, candidates = locate_music(
        project,
        args.music,
        args.music_root,
    )
    if music is None:
        result = {
            "ok": False,
            "error": "MUSIC_NOT_RESOLVED",
            "video_only_xml": str(final_xml),
            "candidates": candidates,
        }
        write_json(report_dir / "FINAL_128H_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    try:
        ffmpeg = resolve_ffmpeg()
        stereo_wav = project / "stt_128h_music_STEREO_48K.wav"
        convert_music(ffmpeg, music, stereo_wav)
    except Exception as exc:
        result = {
            "ok": False,
            "error": "MUSIC_CONVERSION_FAILED",
            "video_only_xml": str(final_xml),
            "music_file": str(music),
            "details": str(exc),
            "fix_hint": "python -m pip install imageio-ffmpeg",
        }
        write_json(report_dir / "FINAL_128H_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    shutil.copy2(stereo_wav, report_dir / stereo_wav.name)

    config = {
        "project": str(project),
        "video_only_xml": str(final_xml),
        "stereo_wav": str(stereo_wav),
        "original_music": str(music),
        "excluded_sources": excludes,
    }
    write_json(project / "stt_128h_audio_bridge_config.json", config)
    write_json(report_dir / "stt_128h_audio_bridge_config.json", config)

    result = {
        "ok": True,
        "report_dir": str(report_dir),
        "video_only_xml": str(final_xml),
        "stereo_wav": str(stereo_wav),
        "original_music": str(music),
        "excluded_sources": excludes,
        "next_step": "Import video-only XML, then use STT Audio Bridge panel.",
        "fix": "128h_premiere_audio_bridge",
    }
    write_json(report_dir / "FINAL_128H_REPORT.json", result)
    print(json.dumps(result, ensure_ascii=True, indent=2))

    if not args.no_open:
        try:
            os.startfile(str(report_dir))  # type: ignore[attr-defined]
        except Exception:
            pass


if __name__ == "__main__":
    main()
