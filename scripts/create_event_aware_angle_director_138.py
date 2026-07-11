from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_137_139_common import *


def event_index(data: dict[str, Any]) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
]:
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


def quality_score(row: dict[str, Any]) -> float:
    return (
        fnum(
            row.get("moment_combined_score_v2"),
            fnum(row.get("quality_score"), 45),
        ) * 0.52
        + fnum(
            row.get("moment_quality_score_v2"),
            fnum(row.get("quality_score"), 45),
        ) * 0.18
        + fnum(row.get("beauty_score"), 55) * 0.20
        + fnum(row.get("hero_score"), 0) * 0.16
    )


def scale_of(row: dict[str, Any]) -> str:
    value = str(row.get("shot_scale") or "unknown").lower()
    return value


def score_candidate(
    candidate: dict[str, Any],
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    next_row: dict[str, Any] | None,
    camera_run: int,
    recent_files: list[str],
) -> float:
    score = quality_score(candidate)
    current_score = quality_score(current)

    candidate_tag = str(candidate.get("scene_tag") or "other")
    current_tag = str(current.get("scene_tag") or "other")
    candidate_family = semantic_family(candidate_tag)
    current_family = semantic_family(current_tag)

    if candidate_tag == current_tag:
        score += 28
    elif candidate_family == current_family:
        score += 16
    else:
        score -= 30

    if section_name(candidate) == section_name(current):
        score += 12

    candidate_camera = camera_of(candidate)
    current_camera = camera_of(current)

    if previous is not None:
        previous_camera = camera_of(previous)
        if candidate_camera != previous_camera:
            score += 10
        elif camera_run >= 3:
            score -= 28
        elif camera_run == 2:
            score -= 12

        previous_scale = scale_of(previous)
        candidate_scale = scale_of(candidate)
        if (
            previous_scale != "unknown"
            and candidate_scale != "unknown"
            and previous_scale != candidate_scale
        ):
            score += 7
        elif previous_scale == candidate_scale and candidate_scale != "unknown":
            score -= 5

    if next_row is not None:
        next_camera = camera_of(next_row)
        if candidate_camera != next_camera:
            score += 5
        else:
            score -= 4

    file_key = norm_path(candidate.get("file"))
    if file_key in recent_files[-5:]:
        score -= 45

    if candidate_camera != current_camera:
        score += 3

    # Do not replace a visibly stronger current source without a real gain.
    score -= max(0.0, current_score - quality_score(candidate)) * 0.35

    return score


def prepare_candidate_for_slot(
    candidate: dict[str, Any],
    slot: dict[str, Any],
) -> dict[str, Any]:
    row = dict(slot)
    duration = fnum(slot.get("duration_sec"), 0)
    media_duration = fnum(
        candidate.get("duration_sec"),
        fnum(candidate.get("media_duration_sec"), 0),
    )
    best_in = fnum(candidate.get("best_source_in_sec"), 0)

    if media_duration > 0:
        best_in = clamp(
            best_in,
            0.0,
            max(0.0, media_duration - duration - 0.15),
        )

    row.update({
        "event_angle_original_file_138": slot.get("file"),
        "event_angle_original_filename_138": filename_of(slot),
        "event_angle_replaced_138": True,
        "file": candidate.get("file"),
        "filename": candidate.get("filename"),
        "scene_tag": candidate.get("scene_tag", slot.get("scene_tag")),
        "camera_group": candidate.get("camera_group", slot.get("camera_group")),
        "shot_scale": candidate.get("shot_scale", slot.get("shot_scale")),
        "source_in_sec": round(best_in, 6),
        "source_out_sec": round(best_in + duration, 6),
        "source_duration_sec": round(duration, 6),
        "media_duration_sec": media_duration,
        "source_media_duration_sec": media_duration,
        "selected_center_sec": round(best_in + duration / 2, 6),
        "event_id_v2": candidate.get("event_id_v2"),
        "event_section_v2": candidate.get("event_section_v2"),
        "event_family_v2": candidate.get("event_family_v2"),
    })
    return row


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="138 Event-Aware Angle Director."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--max-camera-run", type=int, default=4)
    parser.add_argument("--max-replacements", type=int, default=24)
    parser.add_argument("--minimum-improvement", type=float, default=7.0)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "event_aware_angle_director_138")

    timeline_path, timeline = locate_final_timeline(project)
    rows = [dict(row) for row in (timeline.get("items") or [])]
    event_data = read_json(project / "stt_event_context_map_v2.json")

    if not rows:
        result = {"ok": False, "error": "NO_FINAL_TIMELINE"}
        write_json(report_dir / "FINAL_138_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    if not event_data.get("items"):
        result = {
            "ok": False,
            "error": "NO_EVENT_CONTEXT_MAP",
            "message": "Run 137 first.",
        }
        write_json(report_dir / "FINAL_138_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    by_path, by_event = event_index(event_data)
    excluded_names = {
        Path(str(value)).name.lower()
        for value in args.exclude
        if str(value).strip()
    }
    excluded_names.update({"stt0043.mp4", "stt0008.mp4"})

    used_paths = {
        norm_path(row.get("file"))
        for row in rows
        if norm_path(row.get("file"))
    }

    output = []
    replacements = []
    recent_files: list[str] = []
    previous = None
    camera_run = 0
    replacement_count = 0

    before_max_run = max_camera_run(rows)

    for index, current in enumerate(rows):
        current = dict(current)
        current_path = norm_path(current.get("file"))
        event_row = by_path.get(current_path, {})
        event_id = str(event_row.get("event_id_v2") or "")
        candidates = list(by_event.get(event_id, []))

        next_row = rows[index + 1] if index + 1 < len(rows) else None

        current_camera = camera_of(current)
        if previous is not None and current_camera == camera_of(previous):
            projected_run = camera_run + 1
        else:
            projected_run = 1

        force_break = projected_run > max(2, args.max_camera_run)

        ranked = []
        for candidate in candidates:
            candidate_path = norm_path(candidate.get("file"))
            candidate_name = filename_of(candidate).lower()

            if not candidate_path or candidate_path == current_path:
                continue
            if candidate_path in used_paths:
                continue
            if candidate_name in excluded_names:
                continue
            if not Path(str(candidate.get("file") or "")).exists():
                continue

            duration = fnum(candidate.get("duration_sec"), 0)
            slot_duration = fnum(current.get("duration_sec"), 0)
            if duration > 0 and duration < slot_duration + 0.35:
                continue

            score = score_candidate(
                candidate,
                current,
                previous,
                next_row,
                camera_run,
                recent_files,
            )
            ranked.append((score, candidate))

        ranked.sort(key=lambda item: item[0], reverse=True)

        current_score = score_candidate(
            {
                **current,
                "event_id_v2": event_id,
            },
            current,
            previous,
            next_row,
            camera_run,
            recent_files,
        )

        chosen = current
        replaced = False

        if (
            ranked
            and replacement_count < max(0, args.max_replacements)
        ):
            best_score, best_candidate = ranked[0]
            improvement = best_score - current_score

            if improvement >= args.minimum_improvement or force_break:
                chosen = prepare_candidate_for_slot(
                    best_candidate,
                    current,
                )
                used_paths.add(norm_path(best_candidate.get("file")))
                replacement_count += 1
                replaced = True

                replacements.append({
                    "timeline_index": index + 1,
                    "event_id": event_id,
                    "reason": (
                        "break_camera_run"
                        if force_break
                        else "quality_improvement"
                    ),
                    "improvement": round(improvement, 3),
                    "old_filename": filename_of(current),
                    "new_filename": filename_of(best_candidate),
                    "old_camera": camera_of(current),
                    "new_camera": camera_of(best_candidate),
                })

        chosen["event_id_v2"] = (
            chosen.get("event_id_v2")
            or event_id
        )
        chosen["module_138_event_angle"] = True
        output.append(chosen)

        chosen_camera = camera_of(chosen)
        if previous is not None and chosen_camera == camera_of(previous):
            camera_run += 1
        else:
            camera_run = 1

        previous = chosen
        recent_files.append(norm_path(chosen.get("file")))

        print(
            f"[138] {index + 1}/{len(rows)} "
            f"{'REPLACED' if replaced else 'KEEP'}: "
            f"{filename_of(chosen)}"
        )

    after_max_run = max_camera_run(output)

    output_data = dict(timeline)
    output_data.update({
        "module_before_138": timeline.get("module"),
        "module": "138_event_aware_angle_director",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "timeline_count": len(output),
        "timeline_seconds": max(
            [fnum(row.get("timeline_end_sec"), 0) for row in output] + [0]
        ),
        "angle_summary": {
            "replacement_count": replacement_count,
            "max_camera_run_before": before_max_run,
            "max_camera_run_after": after_max_run,
            "camera_counts": dict(Counter(
                camera_of(row) for row in output
            )),
        },
        "items": output,
    })

    output_path = project / "stt_event_aware_timeline_v2.json"
    canonical_path = project / "stt_multicam_directed_timeline_v1.json"
    backup_path = project / "stt_multicam_directed_before_138_backup.json"

    if canonical_path.exists() and not backup_path.exists():
        shutil.copy2(canonical_path, backup_path)

    write_json(output_path, output_data)
    write_json(canonical_path, output_data)
    write_json(report_dir / output_path.name, output_data)
    write_json(
        report_dir / "ANGLE_REPLACEMENTS_138.json",
        {"items": replacements},
    )

    summary = {
        "ok": True,
        "report_dir": str(report_dir),
        "input_timeline": str(timeline_path),
        "output_timeline": str(output_path),
        "canonical_timeline": str(canonical_path),
        "backup_timeline": str(backup_path),
        "timeline_count": len(output),
        "replacement_count": replacement_count,
        "max_camera_run_before": before_max_run,
        "max_camera_run_after": after_max_run,
        "camera_counts": output_data["angle_summary"]["camera_counts"],
        "fix": "138_event_aware_angle_director",
    }
    write_json(report_dir / "FINAL_138_REPORT.json", summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
