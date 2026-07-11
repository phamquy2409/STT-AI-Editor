from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_step(
    command: list[str],
    cwd: Path,
) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="139 Wedding Director Build V2."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--event-bin-width", type=float, default=0.035)
    parser.add_argument("--max-camera-run", type=int, default=4)
    parser.add_argument("--max-replacements", type=int, default=24)
    parser.add_argument("--minimum-improvement", type=float, default=7.0)
    parser.add_argument("--source-safety-sec", type=float, default=1.0)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    scripts = Path(__file__).resolve().parent
    root = scripts.parent
    project = Path(args.project)
    steps = []

    command_137 = [
        sys.executable,
        str(scripts / "create_event_context_mapper_v2_137.py"),
        "--project", str(project),
        "--event-bin-width", str(args.event_bin_width),
        "--no-open",
    ]
    steps.append(run_step(command_137, root))
    if steps[-1]["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "failed_module": 137,
            "steps": steps,
        }, ensure_ascii=True, indent=2))
        return

    command_138 = [
        sys.executable,
        str(scripts / "create_event_aware_angle_director_138.py"),
        "--project", str(project),
        "--max-camera-run", str(args.max_camera_run),
        "--max-replacements", str(args.max_replacements),
        "--minimum-improvement", str(args.minimum_improvement),
        "--no-open",
    ]
    for name in args.exclude or ["STT0043.MP4", "STT0008.MP4"]:
        command_138.extend(["--exclude", name])

    steps.append(run_step(command_138, root))
    if steps[-1]["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "failed_module": 138,
            "steps": steps,
        }, ensure_ascii=True, indent=2))
        return

    hard_fit = scripts / "fix_hard_fit_source_and_export_136e.py"
    if not hard_fit.exists():
        print(json.dumps({
            "ok": False,
            "failed_module": "136E",
            "error": "MISSING_HARD_FIT_EXPORTER",
            "expected": str(hard_fit),
        }, ensure_ascii=True, indent=2))
        return

    command_136e = [
        sys.executable,
        str(hard_fit),
        "--project", str(project),
        "--source-safety-sec", str(args.source_safety_sec),
        "--music-root", args.music_root,
        "--no-open",
    ]
    for name in args.exclude or ["STT0043.MP4", "STT0008.MP4"]:
        command_136e.extend(["--exclude", name])

    steps.append(run_step(command_136e, root))
    if steps[-1]["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "failed_module": "136E",
            "steps": steps,
        }, ensure_ascii=True, indent=2))
        return

    final = {
        "ok": True,
        "modules": [137, 138, 139],
        "project": str(project),
        "event_map": str(project / "stt_event_context_map_v2.json"),
        "event_aware_timeline": str(
            project / "stt_event_aware_timeline_v2.json"
        ),
        "final_timeline": str(
            project / "stt_final_cut_beat_timeline_v2.json"
        ),
        "video_only_xml": str(
            project / "stt_128h_VIDEO_ONLY_FINAL.xml"
        ),
        "stereo_wav": str(
            project / "stt_128h_music_STEREO_48K.wav"
        ),
        "steps": [
            {
                "returncode": step["returncode"],
                "command": step["command"],
            }
            for step in steps
        ],
        "fix": "139_wedding_director_build_v2",
    }
    print(json.dumps(final, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
