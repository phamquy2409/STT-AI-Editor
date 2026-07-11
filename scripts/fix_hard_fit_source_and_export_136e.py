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
from fix_decode_source_and_export_136d import (
    KNOWN_BAD_DEFAULT,
    camera_of,
    candidate_score,
    choose_safe_window,
    conservative_duration,
    convert_music_to_wav,
    filename_of,
    probe_with_cv2,
    run_128d,
)


def row_total_duration(row: dict[str, Any]) -> float:
    probe = probe_with_cv2(str(row.get("file") or ""))
    return conservative_duration(row, probe)


def hard_fit_status(
    row: dict[str, Any],
    safety_sec: float,
) -> dict[str, Any]:
    duration = max(0.0, fnum(row.get("duration_sec"), 0))
    total = row_total_duration(row)
    source_in = max(0.0, fnum(row.get("source_in_sec"), 0))
    source_out = fnum(row.get("source_out_sec"), source_in + duration)

    usable_start = max(0.0, safety_sec)
    usable_end = max(0.0, total - safety_sec)
    usable_duration = max(0.0, usable_end - usable_start)

    fits_duration = total > 0 and usable_duration >= duration + 0.02
    fits_window = (
        fits_duration
        and source_in >= usable_start - 0.001
        and source_out <= usable_end + 0.001
    )

    return {
        "ok": fits_window,
        "total_duration": total,
        "duration_sec": duration,
        "usable_start": usable_start,
        "usable_end": usable_end,
        "usable_duration": usable_duration,
        "source_in": source_in,
        "source_out": source_out,
        "fits_duration": fits_duration,
        "fits_window": fits_window,
    }


def candidate_score_136e(
    candidate: dict[str, Any],
    target: dict[str, Any],
    total_duration: float,
    required_duration: float,
) -> float:
    score = candidate_score(candidate, target)

    target_section = section_name(target)
    candidate_section = section_name(candidate)

    if candidate_section == target_section:
        score += 42
    elif candidate_section in {"story", "release"} and target_section in {"story", "release"}:
        score += 12
    else:
        score -= 20

    headroom = max(0.0, total_duration - required_duration)
    score += min(24.0, headroom * 3.0)

    if camera_of(candidate) != camera_of(target):
        score += 6

    return score


def build_candidate_pool(
    project: Path,
    used_paths: set[str],
    excluded_names: set[str],
) -> list[dict[str, Any]]:
    camera_map = read_json(project / "stt_camera_source_map_v1.json")
    output = []
    seen_paths = set()

    for row in camera_map.get("items") or []:
        path = str(row.get("file") or "")
        path_key = norm_path(path)
        name_key = filename_of(row).lower()

        if not path_key or path_key in used_paths or path_key in seen_paths:
            continue
        if name_key in excluded_names:
            continue
        if not Path(path).exists():
            continue

        seen_paths.add(path_key)
        output.append(dict(row))

    return output


def prepare_candidate_for_slot(
    candidate: dict[str, Any],
    slot: dict[str, Any],
) -> dict[str, Any]:
    duration = fnum(slot.get("duration_sec"), 0)
    best_in = fnum(candidate.get("best_source_in_sec"), 0)

    prepared = dict(candidate)
    prepared.update({
        "duration_sec": duration,
        "source_in_sec": best_in,
        "source_out_sec": best_in + duration,
        "selected_center_sec": best_in + duration / 2,
        "music_section": slot.get("music_section"),
        "story_part": slot.get("story_part"),
    })
    return prepared


def merge_replacement(
    target: dict[str, Any],
    candidate: dict[str, Any],
    validated: dict[str, Any],
) -> dict[str, Any]:
    row = dict(target)

    row.update({
        "hard_fit_original_file_136e": target.get("file"),
        "hard_fit_original_filename_136e": filename_of(target),
        "hard_fit_replaced_136e": True,
        "file": candidate.get("file"),
        "filename": candidate.get("filename"),
        "scene_tag": candidate.get("scene_tag", target.get("scene_tag")),
        "camera_group": candidate.get("camera_group", target.get("camera_group")),
        "shot_scale": candidate.get("shot_scale", target.get("shot_scale")),
        "source_in_sec": validated.get("source_in_sec"),
        "source_out_sec": validated.get("source_out_sec"),
        "source_duration_sec": target.get("duration_sec"),
        "media_duration_sec": validated.get("media_duration_sec"),
        "source_media_duration_sec": validated.get("source_media_duration_sec"),
        "selected_center_sec": (
            fnum(validated.get("source_in_sec"), 0)
            + fnum(target.get("duration_sec"), 0) / 2
        ),
        "decode_validated_136d": True,
        "hard_fit_validated_136e": True,
    })

    return row


def hard_fit_timeline(
    project: Path,
    rows: list[dict[str, Any]],
    safety_sec: float,
    sample_count: int,
    excluded_names: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    used_paths = {
        norm_path(row.get("file"))
        for row in rows
        if norm_path(row.get("file"))
    }
    candidate_pool = build_candidate_pool(
        project,
        used_paths,
        excluded_names,
    )

    output = []
    replaced_count = 0
    shifted_count = 0
    unresolved = []
    changes = []

    for index, original in enumerate(rows, 1):
        row = dict(original)
        status = hard_fit_status(row, safety_sec)

        if status["ok"]:
            row["hard_fit_validated_136e"] = True
            output.append(row)
            continue

        # First try to reposition the same source only if its usable duration is enough.
        if status["fits_duration"]:
            validated, info = choose_safe_window(
                row,
                safety_sec,
                sample_count,
            )
            new_status = hard_fit_status(validated, safety_sec)

            if info.get("ok") and new_status["ok"]:
                validated["hard_fit_validated_136e"] = True
                output.append(validated)
                shifted_count += 1
                changes.append({
                    "index": index,
                    "action": "shift_same_source",
                    "filename": filename_of(row),
                    "old_in": status["source_in"],
                    "new_in": validated.get("source_in_sec"),
                })
                continue

        required_duration = (
            fnum(row.get("duration_sec"), 0)
            + 2 * safety_sec
            + 0.05
        )

        ranked = []
        for candidate in candidate_pool:
            prepared = prepare_candidate_for_slot(candidate, row)
            total = row_total_duration(prepared)

            if total < required_duration:
                continue

            score = candidate_score_136e(
                prepared,
                row,
                total,
                required_duration,
            )
            ranked.append((score, candidate, prepared, total))

        ranked.sort(key=lambda item: item[0], reverse=True)

        replacement = None
        replacement_candidate = None

        for _, candidate, prepared, _ in ranked[:100]:
            validated, info = choose_safe_window(
                prepared,
                safety_sec,
                sample_count,
            )
            final_status = hard_fit_status(validated, safety_sec)

            if info.get("ok") and final_status["ok"]:
                replacement = validated
                replacement_candidate = candidate
                break

        if replacement is None or replacement_candidate is None:
            unresolved.append({
                "index": index,
                "filename": filename_of(row),
                "file": row.get("file"),
                "status": status,
            })
            output.append(row)
            print(
                f"[136E] {index}/{len(rows)} UNRESOLVED: "
                f"{filename_of(row)}"
            )
            continue

        merged = merge_replacement(
            row,
            replacement_candidate,
            replacement,
        )
        output.append(merged)
        replaced_count += 1

        replacement_path = norm_path(replacement_candidate.get("file"))
        candidate_pool = [
            candidate
            for candidate in candidate_pool
            if norm_path(candidate.get("file")) != replacement_path
        ]

        changes.append({
            "index": index,
            "action": "replace_short_source",
            "filename": filename_of(row),
            "replacement_filename": filename_of(replacement_candidate),
            "replacement_file": replacement_candidate.get("file"),
            "required_duration": round(required_duration, 4),
            "replacement_total_duration": round(
                row_total_duration(replacement),
                4,
            ),
        })

        print(
            f"[136E] {index}/{len(rows)} REPLACED: "
            f"{filename_of(row)} -> {filename_of(replacement_candidate)}"
        )

    return output, {
        "shifted_same_source_count": shifted_count,
        "replaced_count": replaced_count,
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
        "changes": changes,
    }


def validate_final(
    rows: list[dict[str, Any]],
    safety_sec: float,
) -> dict[str, Any]:
    hard_fit_failures = []
    gap_count = 0
    overlap_count = 0

    for index, row in enumerate(rows, 1):
        status = hard_fit_status(row, safety_sec)
        if not status["ok"]:
            hard_fit_failures.append({
                "index": index,
                "filename": filename_of(row),
                "status": status,
            })

    for previous, current in zip(rows, rows[1:]):
        delta = (
            fnum(current.get("timeline_start_sec"), 0)
            - fnum(previous.get("timeline_end_sec"), 0)
        )
        if delta > 0.001:
            gap_count += 1
        elif delta < -0.001:
            overlap_count += 1

    return {
        "hard_fit_failure_count": len(hard_fit_failures),
        "hard_fit_failures": hard_fit_failures,
        "source_overflow_count": len(hard_fit_failures),
        "gap_count": gap_count,
        "overlap_count": overlap_count,
        "camera_counts": dict(Counter(
            camera_of(row) for row in rows
        )),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="136E replace any source that cannot physically fit the timeline slot."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--source-safety-sec", type=float, default=1.0)
    parser.add_argument("--sample-count", type=int, default=6)
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--sequence-fps", type=float, default=30.0)
    parser.add_argument("--default-source-fps", type=float, default=50.0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "hard_fit_replacer_136e")

    timeline_path = project / "stt_final_cut_beat_timeline_v2.json"
    data = read_json(timeline_path)
    rows = [dict(row) for row in (data.get("items") or [])]

    if not rows:
        result = {
            "ok": False,
            "error": "NO_FINAL_TIMELINE",
            "expected": str(timeline_path),
        }
        write_json(report_dir / "FINAL_136E_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    excluded_names = set(KNOWN_BAD_DEFAULT)
    excluded_names.update(
        Path(str(value)).name.lower()
        for value in args.exclude
        if str(value).strip()
    )

    fixed_rows, fix_summary = hard_fit_timeline(
        project,
        rows,
        max(0.25, args.source_safety_sec),
        max(3, args.sample_count),
        excluded_names,
    )

    validation = validate_final(
        fixed_rows,
        max(0.25, args.source_safety_sec),
    )

    output_data = dict(data)
    output_data.update({
        "module_before_136e": data.get("module"),
        "module": "136e_hard_fit_replacer",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "timeline_count": len(fixed_rows),
        "hard_fit_summary": fix_summary,
        "validation_summary": validation,
        "items": fixed_rows,
    })

    canonical = project / "stt_multicam_directed_timeline_v1.json"
    backup = project / "stt_final_cut_before_136e_backup.json"

    if not backup.exists():
        shutil.copy2(timeline_path, backup)

    write_json(timeline_path, output_data)
    write_json(canonical, output_data)
    write_json(report_dir / timeline_path.name, output_data)
    write_json(
        report_dir / "HARD_FIT_CHANGES_136E.json",
        {"items": fix_summary.get("changes") or []},
    )

    build_result = None
    video_only = project / "stt_128h_VIDEO_ONLY_FINAL.xml"

    if (
        fix_summary["unresolved_count"] == 0
        and validation["hard_fit_failure_count"] == 0
    ):
        build_result = run_128d(
            project,
            args.sequence_fps,
            args.default_source_fps,
            safety_frames=max(
                10,
                int(round(args.source_safety_sec * args.default_source_fps)),
            ),
        )

        generated = project / "stt_128d_VIDEO_ONLY_SAFE.xml"
        if build_result.get("ok") and generated.exists():
            shutil.copy2(generated, video_only)
            shutil.copy2(video_only, report_dir / video_only.name)

    music_ok, stereo_wav, music_error = convert_music_to_wav(
        project,
        args.music_root,
    )

    result = {
        "ok": (
            fix_summary["unresolved_count"] == 0
            and validation["hard_fit_failure_count"] == 0
            and bool(build_result and build_result.get("ok"))
            and music_ok
        ),
        "report_dir": str(report_dir),
        "output_timeline": str(timeline_path),
        "canonical_timeline": str(canonical),
        "backup_timeline": str(backup),
        "timeline_count": len(fixed_rows),
        "shifted_same_source_count": fix_summary["shifted_same_source_count"],
        "replaced_count": fix_summary["replaced_count"],
        "unresolved_count": fix_summary["unresolved_count"],
        "hard_fit_failure_count": validation["hard_fit_failure_count"],
        "source_overflow_count": validation["source_overflow_count"],
        "gap_count": validation["gap_count"],
        "overlap_count": validation["overlap_count"],
        "build_128d": build_result,
        "video_only_xml": str(video_only),
        "music_ok": music_ok,
        "stereo_wav": stereo_wav,
        "music_error": music_error,
        "fix": "136e_hard_fit_replacer",
    }

    write_json(report_dir / "FINAL_136E_REPORT.json", result)
    print(json.dumps(result, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
