from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_step(command: list[str], cwd: Path) -> dict:
    run = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )

    if run.stdout:
        print(run.stdout, end="")
    if run.stderr:
        print(run.stderr, end="", file=sys.stderr)

    return {
        "command": command,
        "returncode": run.returncode,
        "stdout": run.stdout,
        "stderr": run.stderr,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run modules 134-136, optionally rebuild 128H output."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--target-seconds", type=float, default=210.0)
    parser.add_argument("--analyze-action", action="store_true")
    parser.add_argument("--build-128h", action="store_true")
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--preset", default="horizontal_4k")
    parser.add_argument("--sequence-fps", type=float, default=30.0)
    parser.add_argument("--default-source-fps", type=float, default=50.0)
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root_dir = scripts_dir.parent
    project = Path(args.project)

    steps = []

    command_134 = [
        sys.executable,
        str(scripts_dir / "create_smart_moment_selector_v2_134.py"),
        "--project", str(project),
        "--max-candidates", "3",
        "--sample-span", "0.9",
        "--frames-per-candidate", "4",
        "--no-open",
    ]
    if args.analyze_action:
        command_134.append("--analyze-action")

    steps.append(run_step(command_134, root_dir))
    if steps[-1]["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "failed_module": 134,
            "steps": steps,
        }, ensure_ascii=False, indent=2))
        return

    command_135 = [
        sys.executable,
        str(scripts_dir / "create_music_phrase_rhythm_director_135.py"),
        "--project", str(project),
        "--target-seconds", str(args.target_seconds),
        "--no-open",
    ]
    steps.append(run_step(command_135, root_dir))
    if steps[-1]["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "failed_module": 135,
            "steps": steps,
        }, ensure_ascii=False, indent=2))
        return

    command_136 = [
        sys.executable,
        str(scripts_dir / "create_final_cut_beat_planner_136.py"),
        "--project", str(project),
        "--lookahead", "10",
        "--no-open",
    ]
    steps.append(run_step(command_136, root_dir))
    if steps[-1]["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "failed_module": 136,
            "steps": steps,
        }, ensure_ascii=False, indent=2))
        return

    build_result = None

    if args.build_128h:
        builder = scripts_dir / "build_premiere_audio_bridge_128h.py"
        if not builder.exists():
            build_result = {
                "ok": False,
                "error": "MISSING_128H_BUILDER",
                "expected": str(builder),
            }
        else:
            excludes = args.exclude or ["STT0043.MP4", "STT0008.MP4"]
            command = [
                sys.executable,
                str(builder),
                "--project", str(project),
                "--music-root", args.music_root,
                "--preset", args.preset,
                "--sequence-fps", str(args.sequence_fps),
                "--default-source-fps", str(args.default_source_fps),
                "--no-open",
            ]
            for name in excludes:
                command.extend(["--exclude", name])

            result = run_step(command, root_dir)
            build_result = {
                "ok": result["returncode"] == 0,
                **result,
            }

    final = {
        "ok": True,
        "modules": [134, 135, 136],
        "project": str(project),
        "build_128h_requested": bool(args.build_128h),
        "build_128h_result": build_result,
        "final_timeline": str(
            project / "stt_final_cut_beat_timeline_v2.json"
        ),
        "video_only_xml": str(
            project / "stt_128h_VIDEO_ONLY_FINAL.xml"
        ) if args.build_128h else "",
        "stereo_wav": str(
            project / "stt_128h_music_STEREO_48K.wav"
        ) if args.build_128h else "",
    }
    print(json.dumps(final, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
