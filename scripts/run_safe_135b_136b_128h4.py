from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path) -> dict:
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
        description="Run safe 135B-136B and rebuild 128H."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--target-seconds", type=float, default=210.0)
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    scripts = Path(__file__).resolve().parent
    root = scripts.parent
    project = Path(args.project)

    steps = []

    steps.append(run([
        sys.executable,
        str(scripts / "create_music_phrase_rhythm_director_135.py"),
        "--project", str(project),
        "--target-seconds", str(args.target_seconds),
        "--no-open",
    ], root))

    if steps[-1]["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "failed_module": "135B",
            "steps": steps,
        }, ensure_ascii=True, indent=2))
        return

    steps.append(run([
        sys.executable,
        str(scripts / "create_final_cut_beat_planner_136.py"),
        "--project", str(project),
        "--no-open",
    ], root))

    if steps[-1]["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "failed_module": "136B",
            "steps": steps,
        }, ensure_ascii=True, indent=2))
        return

    builder = scripts / "build_premiere_audio_bridge_128h.py"
    excludes = args.exclude or ["STT0043.MP4", "STT0008.MP4"]

    command = [
        sys.executable,
        str(builder),
        "--project", str(project),
        "--music-root", args.music_root,
        "--preset", "horizontal_4k",
        "--sequence-fps", "30",
        "--default-source-fps", "50",
        "--no-open",
    ]
    for name in excludes:
        command.extend(["--exclude", name])

    build = run(command, root)

    print(json.dumps({
        "ok": build["returncode"] == 0,
        "modules": ["135B", "136B", "128H4"],
        "final_timeline": str(project / "stt_final_cut_beat_timeline_v2.json"),
        "video_only_xml": str(project / "stt_128h_VIDEO_ONLY_FINAL.xml"),
        "stereo_wav": str(project / "stt_128h_music_STEREO_48K.wav"),
        "build_returncode": build["returncode"],
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
