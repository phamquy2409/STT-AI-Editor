from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_134_136_common import *


def get_media_duration(row: dict[str, Any]) -> float:
    return fnum(
        row.get("media_duration_sec"),
        fnum(
            row.get("source_media_duration_sec"),
            fnum(row.get("validated_media_duration_sec"), 0),
        ),
    )


def safe_source_window(
    row: dict[str, Any],
    duration: float,
    safety_sec: float,
) -> tuple[float, float, bool]:
    total = get_media_duration(row)
    old_in = max(0.0, fnum(row.get("source_in_sec"), 0))
    old_out = fnum(row.get("source_out_sec"), old_in + duration)

    if total <= 0:
        return old_in, old_in + duration, False

    effective_end = max(0.0, total - max(0.02, safety_sec))
    max_in = max(0.0, effective_end - duration)
    new_in = clamp(old_in, 0.0, max_in)
    new_out = new_in + duration

    changed = (
        abs(new_in - old_in) > 0.001
        or old_out > effective_end + 0.001
    )
    return new_in, new_out, changed


def can_fit(row: dict[str, Any], duration: float, safety_sec: float) -> bool:
    total = get_media_duration(row)
    return total <= 0 or total >= duration + safety_sec + 0.02


def preserve_slot(
    source_row: dict[str, Any],
    slot_row: dict[str, Any],
    safety_sec: float,
) -> dict[str, Any]:
    row = dict(source_row)

    start = fnum(slot_row.get("timeline_start_sec"), 0)
    end = fnum(slot_row.get("timeline_end_sec"), start)
    duration = max(0.25, end - start)

    center = fnum(
        row.get("selected_center_sec"),
        fnum(row.get("source_in_sec"), 0)
        + fnum(row.get("duration_sec"), duration) / 2,
    )
    total = get_media_duration(row)

    source_in = center - duration / 2
    if total > 0:
        source_in = clamp(
            source_in,
            0.0,
            max(0.0, total - duration - safety_sec),
        )
    else:
        source_in = max(0.0, source_in)

    row.update({
        "index": slot_row.get("index"),
        "timeline_start_sec": round(start, 6),
        "timeline_end_sec": round(end, 6),
        "duration_sec": round(duration, 6),
        "source_in_sec": round(source_in, 6),
        "source_out_sec": round(source_in + duration, 6),
        "source_duration_sec": round(duration, 6),
        "music_section": slot_row.get("music_section"),
        "story_part": slot_row.get("story_part"),
        "rhythm_mode_v2": slot_row.get("rhythm_mode_v2"),
        "beats_skipped_v2": slot_row.get("beats_skipped_v2"),
        "end_beat_strength_v2": slot_row.get("end_beat_strength_v2"),
        "module_136c_balanced": True,
    })
    return row


def camera_of(row: dict[str, Any]) -> str:
    return str(row.get("camera_group") or "CAM_UNKNOWN")


def max_camera_run(rows: list[dict[str, Any]]) -> int:
    maximum = 0
    run = 0
    previous = None

    for row in rows:
        camera = camera_of(row)
        if camera == previous:
            run += 1
        else:
            run = 1
        previous = camera
        maximum = max(maximum, run)

    return maximum


def run_length_ending_at(rows: list[dict[str, Any]], index: int) -> int:
    camera = camera_of(rows[index])
    run = 1
    cursor = index - 1

    while cursor >= 0 and camera_of(rows[cursor]) == camera:
        run += 1
        cursor -= 1

    return run


def local_run_if_inserted(
    rows: list[dict[str, Any]],
    index: int,
    camera: str,
) -> int:
    left = 0
    cursor = index - 1
    while cursor >= 0 and camera_of(rows[cursor]) == camera:
        left += 1
        cursor -= 1

    right = 0
    cursor = index + 1
    while cursor < len(rows) and camera_of(rows[cursor]) == camera:
        right += 1
        cursor += 1

    return left + 1 + right


def balance_cameras(
    rows: list[dict[str, Any]],
    max_run: int,
    lookahead: int,
    safety_sec: float,
    max_passes: int = 8,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output = [dict(row) for row in rows]
    changes: list[dict[str, Any]] = []

    for pass_index in range(max_passes):
        changed_this_pass = False

        for index in range(len(output)):
            current_run = run_length_ending_at(output, index)
            if current_run <= max_run:
                continue

            current = output[index]
            current_camera = camera_of(current)
            current_section = section_name(current)
            current_duration = fnum(current.get("duration_sec"), 0)

            candidate_index = None
            candidate_score = None
            search_end = min(len(output), index + max(2, lookahead) + 1)

            for j in range(index + 1, search_end):
                candidate = output[j]
                candidate_camera = camera_of(candidate)

                if candidate_camera == current_camera:
                    continue
                if section_name(candidate) != current_section:
                    continue
                if not can_fit(candidate, current_duration, safety_sec):
                    continue

                candidate_duration = fnum(candidate.get("duration_sec"), 0)
                if not can_fit(current, candidate_duration, safety_sec):
                    continue

                # Prefer a swap that fixes both positions.
                run_at_current = local_run_if_inserted(
                    output,
                    index,
                    candidate_camera,
                )
                run_at_candidate = local_run_if_inserted(
                    output,
                    j,
                    current_camera,
                )

                score = (
                    run_at_current * 10
                    + run_at_candidate * 6
                    + (j - index) * 0.15
                )

                if candidate_score is None or score < candidate_score:
                    candidate_score = score
                    candidate_index = j

            if candidate_index is None:
                continue

            slot_a = output[index]
            slot_b = output[candidate_index]

            output[index] = preserve_slot(
                slot_b,
                slot_a,
                safety_sec,
            )
            output[candidate_index] = preserve_slot(
                slot_a,
                slot_b,
                safety_sec,
            )

            changes.append({
                "pass": pass_index + 1,
                "slot_index": index + 1,
                "candidate_index": candidate_index + 1,
                "section": current_section,
                "camera_before": current_camera,
                "camera_after": camera_of(output[index]),
                "slot_filename_before": slot_a.get("filename"),
                "slot_filename_after": slot_b.get("filename"),
            })
            changed_this_pass = True

        if not changed_this_pass:
            break

        if max_camera_run(output) <= max_run:
            break

    return output, changes


def clamp_all_sources(
    rows: list[dict[str, Any]],
    safety_sec: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output = []
    changes = []

    for index, original in enumerate(rows, 1):
        row = dict(original)
        duration = fnum(row.get("duration_sec"), 0)
        new_in, new_out, changed = safe_source_window(
            row,
            duration,
            safety_sec,
        )

        if changed:
            changes.append({
                "index": index,
                "filename": row.get("filename"),
                "old_in": round(fnum(row.get("source_in_sec"), 0), 6),
                "old_out": round(fnum(row.get("source_out_sec"), 0), 6),
                "new_in": round(new_in, 6),
                "new_out": round(new_out, 6),
                "media_duration": round(get_media_duration(row), 6),
            })

        row["source_in_sec"] = round(new_in, 6)
        row["source_out_sec"] = round(new_out, 6)
        row["source_duration_sec"] = round(duration, 6)
        row["module_136c_clamped"] = True
        output.append(row)

    return output, changes


def validate(rows: list[dict[str, Any]], safety_sec: float) -> dict[str, Any]:
    gap_count = 0
    overlap_count = 0
    overflow_count = 0

    for previous, current in zip(rows, rows[1:]):
        delta = (
            fnum(current.get("timeline_start_sec"), 0)
            - fnum(previous.get("timeline_end_sec"), 0)
        )
        if delta > 0.001:
            gap_count += 1
        elif delta < -0.001:
            overlap_count += 1

    for row in rows:
        total = get_media_duration(row)
        if total > 0:
            effective_end = total - max(0.02, safety_sec)
            if fnum(row.get("source_out_sec"), 0) > effective_end + 0.001:
                overflow_count += 1

    return {
        "gap_count": gap_count,
        "overlap_count": overlap_count,
        "source_overflow_count": overflow_count,
        "max_same_camera_run": max_camera_run(rows),
        "camera_counts": dict(Counter(
            camera_of(row) for row in rows
        )),
        "section_counts": dict(Counter(
            str(row.get("music_section") or "story")
            for row in rows
        )),
    }


def rebuild_128h(
    project: Path,
    music_root: str,
    excludes: list[str],
) -> dict[str, Any]:
    scripts_dir = Path(__file__).resolve().parent
    builder = scripts_dir / "build_premiere_audio_bridge_128h.py"

    if not builder.exists():
        return {
            "ok": False,
            "error": "MISSING_128H_BUILDER",
            "expected": str(builder),
        }

    command = [
        sys.executable,
        str(builder),
        "--project", str(project),
        "--music-root", music_root,
        "--preset", "horizontal_4k",
        "--sequence-fps", "30",
        "--default-source-fps", "50",
        "--no-open",
    ]
    for name in excludes:
        command.extend(["--exclude", name])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        command,
        cwd=str(scripts_dir.parent),
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
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="136C source overflow clamp and camera balance."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--max-camera-run", type=int, default=4)
    parser.add_argument("--lookahead", type=int, default=24)
    parser.add_argument("--source-safety-sec", type=float, default=0.15)
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "overflow_camera_balance_136c")

    source_path = project / "stt_final_cut_beat_timeline_v2.json"
    data = read_json(source_path)
    rows = [dict(row) for row in (data.get("items") or [])]

    if not rows:
        result = {
            "ok": False,
            "error": "NO_136B_TIMELINE",
            "expected": str(source_path),
        }
        write_json(report_dir / "FINAL_136C_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    safety_sec = max(0.02, args.source_safety_sec)
    before = validate(rows, safety_sec)

    balanced, camera_changes = balance_cameras(
        rows,
        max(2, args.max_camera_run),
        max(4, args.lookahead),
        safety_sec,
    )

    clamped, overflow_changes = clamp_all_sources(
        balanced,
        safety_sec,
    )

    after = validate(clamped, safety_sec)

    output_data = dict(data)
    output_data.update({
        "module_before_136c": data.get("module"),
        "module": "136c_overflow_camera_balance",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "timeline_count": len(clamped),
        "timeline_seconds": max(
            [fnum(row.get("timeline_end_sec"), 0) for row in clamped] + [0]
        ),
        "duration_stats": duration_stats(clamped),
        "balance_summary": {
            "before": before,
            "after": after,
            "camera_swap_count": len(camera_changes),
            "overflow_clamp_count": len(overflow_changes),
        },
        "items": clamped,
    })

    canonical = project / "stt_multicam_directed_timeline_v1.json"
    backup = project / "stt_final_cut_before_136c_backup.json"

    if not backup.exists():
        shutil.copy2(source_path, backup)

    write_json(source_path, output_data)
    write_json(canonical, output_data)
    write_json(report_dir / source_path.name, output_data)
    write_json(report_dir / "CAMERA_SWAPS_136C.json", {"items": camera_changes})
    write_json(report_dir / "SOURCE_CLAMPS_136C.json", {"items": overflow_changes})

    build_result = None
    if not args.no_build:
        build_result = rebuild_128h(
            project,
            args.music_root,
            args.exclude or ["STT0043.MP4", "STT0008.MP4"],
        )

    result = {
        "ok": True,
        "report_dir": str(report_dir),
        "output_timeline": str(source_path),
        "canonical_timeline": str(canonical),
        "backup_timeline": str(backup),
        "timeline_count": len(clamped),
        "timeline_seconds": round(
            max([fnum(row.get("timeline_end_sec"), 0) for row in clamped] + [0]),
            3,
        ),
        "source_overflow_before": before["source_overflow_count"],
        "source_overflow_after": after["source_overflow_count"],
        "max_same_camera_run_before": before["max_same_camera_run"],
        "max_same_camera_run_after": after["max_same_camera_run"],
        "camera_swap_count": len(camera_changes),
        "overflow_clamp_count": len(overflow_changes),
        "gap_count": after["gap_count"],
        "overlap_count": after["overlap_count"],
        "camera_counts": after["camera_counts"],
        "build_128h": build_result,
        "video_only_xml": str(project / "stt_128h_VIDEO_ONLY_FINAL.xml"),
        "stereo_wav": str(project / "stt_128h_music_STEREO_48K.wav"),
        "fix": "136c_overflow_camera_balance",
    }

    write_json(report_dir / "FINAL_136C_REPORT.json", result)
    print(json.dumps(result, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
