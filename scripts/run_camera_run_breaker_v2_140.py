from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_140_common import *


KNOWN_BAD = {"stt0043.mp4", "stt0008.mp4"}


def locate_input(project: Path) -> tuple[Path | None, dict[str, Any]]:
    # Critical propagation fix:
    # Prefer the 138 result instead of silently falling back to the older 136 timeline.
    for name in [
        "stt_event_aware_timeline_v2.json",
        "stt_final_cut_beat_timeline_v2.json",
        "stt_multicam_directed_timeline_v1.json",
    ]:
        path = project / name
        data = read_json(path)
        if data.get("items"):
            return path, data
    return None, {}


def event_maps(project: Path) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
]:
    data = read_json(project / "stt_event_context_map_v2.json")
    by_path = {}
    by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in data.get("items") or []:
        path_key = norm_path(row.get("file"))
        event_id = str(row.get("event_id_v2") or "")
        if path_key:
            by_path[path_key] = row
        if event_id:
            by_event[event_id].append(row)

    return by_path, by_event


def protected_shot(row: dict[str, Any]) -> bool:
    section = section_name(row)
    tag = str(row.get("scene_tag") or "other")
    duration = fnum(row.get("duration_sec"), 0)
    score = quality_score(row)

    if row.get("is_main_climax_shot"):
        return True
    if row.get("reservation_role"):
        return True
    if row.get("hook_reserved") or row.get("climax_reserved") or row.get("ending_reserved"):
        return True

    if section in {"climax", "ending"} and (
        score >= 78
        or tag in {"vow", "family_emotion", "first_look", "ending"}
        or (row.get("slow_recommended") and duration >= 3.0)
    ):
        return True

    return False


def source_duration(row: dict[str, Any]) -> float:
    return fnum(
        row.get("duration_sec"),
        fnum(
            row.get("media_duration_sec"),
            fnum(row.get("source_media_duration_sec"), 0),
        ),
    )


def media_duration(row: dict[str, Any]) -> float:
    return fnum(
        row.get("media_duration_sec"),
        fnum(
            row.get("source_media_duration_sec"),
            fnum(row.get("duration_sec"), 0),
        ),
    )


def can_fit(candidate: dict[str, Any], slot: dict[str, Any], safety: float) -> bool:
    slot_duration = fnum(slot.get("duration_sec"), 0)
    total = media_duration(candidate)

    if total <= 0:
        total = source_duration(candidate)

    return total <= 0 or total >= slot_duration + safety * 2 + 0.10


def event_id_for(
    row: dict[str, Any],
    by_path: dict[str, dict[str, Any]],
) -> str:
    direct = str(row.get("event_id_v2") or "")
    if direct:
        return direct

    mapped = by_path.get(norm_path(row.get("file")), {})
    return str(mapped.get("event_id_v2") or "")


def candidate_score(
    candidate: dict[str, Any],
    slot: dict[str, Any],
    previous: dict[str, Any] | None,
    following: dict[str, Any] | None,
) -> float:
    score = quality_score(candidate)

    slot_tag = str(slot.get("scene_tag") or "other")
    candidate_tag = str(candidate.get("scene_tag") or "other")
    slot_family = semantic_family(slot_tag)
    candidate_family = semantic_family(candidate_tag)

    if candidate_tag == slot_tag:
        score += 34
    elif candidate_family == slot_family:
        score += 18
    else:
        score -= 42

    if section_name(candidate) == section_name(slot):
        score += 18

    candidate_camera = camera_of(candidate)
    slot_camera = camera_of(slot)

    if candidate_camera != slot_camera:
        score += 12

    if previous is not None:
        if candidate_camera != camera_of(previous):
            score += 10
        else:
            score -= 18

    if following is not None:
        if candidate_camera != camera_of(following):
            score += 6
        else:
            score -= 10

    candidate_scale = str(candidate.get("shot_scale") or "unknown")
    slot_scale = str(slot.get("shot_scale") or "unknown")
    if (
        candidate_scale != "unknown"
        and slot_scale != "unknown"
        and candidate_scale != slot_scale
    ):
        score += 5

    # Avoid replacing a strong slot with a visibly weaker angle.
    score -= max(0.0, quality_score(slot) - quality_score(candidate)) * 0.55
    return score


def source_identity_from_candidate(
    candidate: dict[str, Any],
    slot: dict[str, Any],
    safety: float,
) -> dict[str, Any]:
    row = dict(slot)
    duration = fnum(slot.get("duration_sec"), 0)
    total = media_duration(candidate)
    best_in = fnum(candidate.get("best_source_in_sec"), 0)

    if total > 0:
        best_in = clamp(
            best_in,
            safety,
            max(safety, total - safety - duration),
        )
    else:
        best_in = max(0.0, best_in)

    row.update({
        "camera_run_original_file_140": slot.get("file"),
        "camera_run_original_filename_140": filename_of(slot),
        "camera_run_replaced_140": True,
        "file": candidate.get("file"),
        "filename": candidate.get("filename"),
        "scene_tag": candidate.get("scene_tag", slot.get("scene_tag")),
        "camera_group": candidate.get("camera_group", slot.get("camera_group")),
        "shot_scale": candidate.get("shot_scale", slot.get("shot_scale")),
        "source_in_sec": round(best_in, 6),
        "source_out_sec": round(best_in + duration, 6),
        "source_duration_sec": round(duration, 6),
        "media_duration_sec": total,
        "source_media_duration_sec": total,
        "selected_center_sec": round(best_in + duration / 2, 6),
        "event_id_v2": candidate.get("event_id_v2", slot.get("event_id_v2")),
        "module_140_camera_run_breaker": True,
    })
    return row


def copy_source_to_slot(
    source_row: dict[str, Any],
    slot_row: dict[str, Any],
    safety: float,
) -> dict[str, Any]:
    # Used for a conservative selected-shot swap.
    candidate = dict(source_row)
    candidate.setdefault("best_source_in_sec", source_row.get("source_in_sec"))
    candidate.setdefault("media_duration_sec", media_duration(source_row))
    return source_identity_from_candidate(candidate, slot_row, safety)


def local_run_if_camera(
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


def find_break_slot(
    rows: list[dict[str, Any]],
    run: dict[str, Any],
    max_run: int,
) -> int | None:
    start = inum(run.get("start"), 0)
    end = inum(run.get("end"), start)
    preferred = min(end - 1, start + max_run)

    candidates = []
    for index in range(start + 1, end - 1):
        if protected_shot(rows[index]):
            continue
        distance = abs(index - preferred)
        candidates.append((
            distance,
            quality_score(rows[index]),
            index,
        ))

    if not candidates:
        return None

    # Prefer the intended break point, then the weaker replaceable shot.
    candidates.sort(key=lambda value: (value[0], value[1]))
    return candidates[0][2]


def unused_event_candidate(
    rows: list[dict[str, Any]],
    slot_index: int,
    by_path: dict[str, dict[str, Any]],
    by_event: dict[str, list[dict[str, Any]]],
    used_paths: set[str],
    excluded: set[str],
    safety: float,
    minimum_improvement: float,
) -> tuple[dict[str, Any] | None, float]:
    slot = rows[slot_index]
    event_id = event_id_for(slot, by_path)
    if not event_id:
        return None, 0.0

    previous = rows[slot_index - 1] if slot_index > 0 else None
    following = rows[slot_index + 1] if slot_index + 1 < len(rows) else None
    slot_camera = camera_of(slot)
    current_score = quality_score(slot)

    ranked = []
    for candidate in by_event.get(event_id, []):
        path_key = norm_path(candidate.get("file"))
        name_key = filename_of(candidate).lower()

        if not path_key or path_key in used_paths:
            continue
        if name_key in excluded:
            continue
        if camera_of(candidate) == slot_camera:
            continue
        if not Path(str(candidate.get("file") or "")).exists():
            continue
        if not can_fit(candidate, slot, safety):
            continue

        score = candidate_score(candidate, slot, previous, following)
        ranked.append((score, candidate))

    if not ranked:
        return None, 0.0

    ranked.sort(key=lambda value: value[0], reverse=True)
    best_score, candidate = ranked[0]
    improvement = best_score - current_score

    if improvement < minimum_improvement:
        return None, improvement

    return candidate, improvement


def selected_swap_candidate(
    rows: list[dict[str, Any]],
    slot_index: int,
    run: dict[str, Any],
    search_radius: int,
    safety: float,
) -> int | None:
    slot = rows[slot_index]
    slot_camera = camera_of(slot)
    slot_section = section_name(slot)
    slot_family = semantic_family(str(slot.get("scene_tag") or "other"))
    run_start = inum(run.get("start"), 0)
    run_end = inum(run.get("end"), run_start)

    best = None
    low = max(0, slot_index - search_radius)
    high = min(len(rows), slot_index + search_radius + 1)

    for index in range(low, high):
        if run_start <= index < run_end:
            continue

        donor = rows[index]
        if protected_shot(donor):
            continue
        if camera_of(donor) == slot_camera:
            continue
        if section_name(donor) != slot_section:
            continue
        if semantic_family(str(donor.get("scene_tag") or "other")) != slot_family:
            continue
        if not can_fit(donor, slot, safety):
            continue
        if not can_fit(slot, donor, safety):
            continue

        donor_camera = camera_of(donor)
        slot_at_donor_run = local_run_if_camera(rows, index, slot_camera)
        donor_at_slot_run = local_run_if_camera(rows, slot_index, donor_camera)

        score = (
            donor_at_slot_run * 12
            + slot_at_donor_run * 8
            + abs(index - slot_index) * 0.18
            + max(0.0, quality_score(slot) - quality_score(donor)) * 0.25
        )

        if best is None or score < best[0]:
            best = (score, index)

    return best[1] if best else None


def break_camera_runs(
    rows: list[dict[str, Any]],
    by_path: dict[str, dict[str, Any]],
    by_event: dict[str, list[dict[str, Any]]],
    max_run: int,
    max_changes: int,
    minimum_improvement: float,
    search_radius: int,
    safety: float,
    excluded: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output = [dict(row) for row in rows]
    used_paths = {
        norm_path(row.get("file"))
        for row in output
        if norm_path(row.get("file"))
    }
    changes = []

    for pass_index in range(6):
        changed_this_pass = False
        runs = camera_runs(output)

        for run in runs:
            if inum(run.get("length"), 0) <= max_run:
                continue
            if len(changes) >= max_changes:
                return output, changes

            slot_index = find_break_slot(output, run, max_run)
            if slot_index is None:
                continue

            slot = output[slot_index]
            candidate, improvement = unused_event_candidate(
                output,
                slot_index,
                by_path,
                by_event,
                used_paths,
                excluded,
                safety,
                minimum_improvement,
            )

            if candidate is not None:
                old = output[slot_index]
                output[slot_index] = source_identity_from_candidate(
                    candidate,
                    old,
                    safety,
                )
                used_paths.add(norm_path(candidate.get("file")))
                changes.append({
                    "pass": pass_index + 1,
                    "action": "same_event_unused_angle",
                    "timeline_index": slot_index + 1,
                    "event_id": event_id_for(old, by_path),
                    "old_filename": filename_of(old),
                    "new_filename": filename_of(candidate),
                    "old_camera": camera_of(old),
                    "new_camera": camera_of(candidate),
                    "improvement": round(improvement, 3),
                })
                changed_this_pass = True
                continue

            donor_index = selected_swap_candidate(
                output,
                slot_index,
                run,
                search_radius,
                safety,
            )

            if donor_index is None:
                continue

            slot_before = output[slot_index]
            donor_before = output[donor_index]

            output[slot_index] = copy_source_to_slot(
                donor_before,
                slot_before,
                safety,
            )
            output[donor_index] = copy_source_to_slot(
                slot_before,
                donor_before,
                safety,
            )

            changes.append({
                "pass": pass_index + 1,
                "action": "selected_source_swap",
                "timeline_index": slot_index + 1,
                "donor_index": donor_index + 1,
                "old_filename": filename_of(slot_before),
                "new_filename": filename_of(donor_before),
                "old_camera": camera_of(slot_before),
                "new_camera": camera_of(donor_before),
            })
            changed_this_pass = True

        if max_camera_run(output) <= max_run:
            break
        if not changed_this_pass:
            break

    return output, changes


def run_hard_fit(
    project: Path,
    music_root: str,
    safety: float,
    excluded: list[str],
) -> dict[str, Any]:
    scripts = Path(__file__).resolve().parent
    hard_fit = scripts / "fix_hard_fit_source_and_export_136e.py"

    command = [
        sys.executable,
        str(hard_fit),
        "--project", str(project),
        "--source-safety-sec", str(safety),
        "--music-root", music_root,
        "--no-open",
    ]
    for name in excluded:
        command.extend(["--exclude", name])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        command,
        cwd=str(scripts.parent),
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
        description="140 Camera Run Breaker V2."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--max-camera-run", type=int, default=5)
    parser.add_argument("--max-changes", type=int, default=16)
    parser.add_argument("--minimum-improvement", type=float, default=-4.0)
    parser.add_argument("--search-radius", type=int, default=24)
    parser.add_argument("--source-safety-sec", type=float, default=1.0)
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "camera_run_breaker_v2_140")

    input_path, data = locate_input(project)
    rows = [dict(row) for row in (data.get("items") or [])]

    if not input_path or not rows:
        result = {"ok": False, "error": "NO_INPUT_TIMELINE"}
        write_json(report_dir / "FINAL_140_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    by_path, by_event = event_maps(project)
    if not by_event:
        result = {
            "ok": False,
            "error": "NO_EVENT_MAP",
            "message": "Run 137 first.",
        }
        write_json(report_dir / "FINAL_140_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    excluded = set(KNOWN_BAD)
    excluded.update(
        Path(str(value)).name.lower()
        for value in args.exclude
        if str(value).strip()
    )

    before = validate_timeline(rows)

    balanced, changes = break_camera_runs(
        rows,
        by_path,
        by_event,
        max(3, args.max_camera_run),
        max(0, args.max_changes),
        args.minimum_improvement,
        max(8, args.search_radius),
        max(0.25, args.source_safety_sec),
        excluded,
    )

    after_balance = validate_timeline(balanced)

    output_data = dict(data)
    output_data.update({
        "module_before_140": data.get("module"),
        "module": "140_camera_run_breaker_v2",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "input_timeline": str(input_path),
        "timeline_count": len(balanced),
        "camera_run_summary": {
            "before": before,
            "after_balance": after_balance,
            "change_count": len(changes),
        },
        "items": balanced,
    })

    output_path = project / "stt_camera_run_balanced_timeline_v2.json"
    final_path = project / "stt_final_cut_beat_timeline_v2.json"
    canonical_path = project / "stt_multicam_directed_timeline_v1.json"
    backup_path = project / "stt_final_cut_before_140_backup.json"

    if final_path.exists() and not backup_path.exists():
        shutil.copy2(final_path, backup_path)

    # Propagation fix: write the 138/140 result into the real input used by 136E.
    write_json(output_path, output_data)
    write_json(final_path, output_data)
    write_json(canonical_path, output_data)
    write_json(report_dir / output_path.name, output_data)
    write_json(report_dir / "CAMERA_RUN_CHANGES_140.json", {"items": changes})

    hard_fit_result = None
    final_validation = after_balance

    if not args.no_build:
        hard_fit_result = run_hard_fit(
            project,
            args.music_root,
            max(0.25, args.source_safety_sec),
            sorted(excluded),
        )

        final_data = read_json(final_path)
        final_rows = [dict(row) for row in (final_data.get("items") or [])]
        if final_rows:
            final_validation = validate_timeline(final_rows)

    result = {
        "ok": (
            after_balance["gap_count"] == 0
            and after_balance["overlap_count"] == 0
            and after_balance["duplicate_source_count"] == 0
            and (
                args.no_build
                or bool(hard_fit_result and hard_fit_result.get("ok"))
            )
        ),
        "report_dir": str(report_dir),
        "input_timeline": str(input_path),
        "output_timeline": str(output_path),
        "final_timeline": str(final_path),
        "canonical_timeline": str(canonical_path),
        "backup_timeline": str(backup_path),
        "timeline_count": len(balanced),
        "change_count": len(changes),
        "max_camera_run_before": before["max_same_camera_run"],
        "max_camera_run_after_balance": after_balance["max_same_camera_run"],
        "max_camera_run_final": final_validation["max_same_camera_run"],
        "duplicate_source_count": final_validation["duplicate_source_count"],
        "gap_count": final_validation["gap_count"],
        "overlap_count": final_validation["overlap_count"],
        "camera_counts": final_validation["camera_counts"],
        "hard_fit_build": hard_fit_result,
        "video_only_xml": str(project / "stt_128h_VIDEO_ONLY_FINAL.xml"),
        "stereo_wav": str(project / "stt_128h_music_STEREO_48K.wav"),
        "fix": "140_camera_run_breaker_v2",
    }

    write_json(report_dir / "FINAL_140_REPORT.json", result)
    print(json.dumps(result, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
