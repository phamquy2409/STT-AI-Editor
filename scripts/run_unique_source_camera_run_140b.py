from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_140_common import *


KNOWN_BAD = {"stt0043.mp4", "stt0008.mp4"}


def locate_input(project: Path) -> tuple[Path | None, dict[str, Any]]:
    # Start from the actual latest 140/136E timeline.
    for name in [
        "stt_final_cut_beat_timeline_v2.json",
        "stt_camera_run_balanced_timeline_v2.json",
        "stt_event_aware_timeline_v2.json",
    ]:
        path = project / name
        data = read_json(path)
        if data.get("items"):
            return path, data
    return None, {}


def load_catalog(project: Path) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
]:
    event_data = read_json(project / "stt_event_context_map_v2.json")
    camera_data = read_json(project / "stt_camera_source_map_v1.json")

    event_by_path: dict[str, dict[str, Any]] = {}
    event_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    catalog_by_path: dict[str, dict[str, Any]] = {}

    for row in event_data.get("items") or []:
        item = dict(row)
        key = norm_path(item.get("file"))
        event_id = str(item.get("event_id_v2") or "")

        if key and key not in event_by_path:
            event_by_path[key] = item
        if event_id:
            event_by_id[event_id].append(item)
        if key and key not in catalog_by_path:
            catalog_by_path[key] = item

    for row in camera_data.get("items") or []:
        item = dict(row)
        key = norm_path(item.get("file"))
        if not key:
            continue

        if key in event_by_path:
            merged = dict(item)
            merged.update(event_by_path[key])
            catalog_by_path[key] = merged
        elif key not in catalog_by_path:
            catalog_by_path[key] = item

    return event_by_path, event_by_id, list(catalog_by_path.values())


def source_total_duration(row: dict[str, Any]) -> float:
    # Timeline rows store source duration in media_duration_sec.
    # Catalog rows commonly use duration_sec as the full source duration.
    return fnum(
        row.get("media_duration_sec"),
        fnum(
            row.get("source_media_duration_sec"),
            fnum(row.get("duration_sec"), 0),
        ),
    )


def can_fit(candidate: dict[str, Any], slot: dict[str, Any], safety: float) -> bool:
    total = source_total_duration(candidate)
    duration = fnum(slot.get("duration_sec"), 0)
    return total > 0 and total >= duration + safety * 2 + 0.10


def protected_score(row: dict[str, Any]) -> float:
    score = quality_score(row)
    section = section_name(row)
    tag = str(row.get("scene_tag") or "other")

    if row.get("is_main_climax_shot"):
        score += 500
    if row.get("reservation_role"):
        score += 350
    if row.get("hook_reserved") or row.get("climax_reserved") or row.get("ending_reserved"):
        score += 300
    if section in {"climax", "ending"}:
        score += 80
    if tag in {"vow", "family_emotion", "first_look", "ending"}:
        score += 70
    if row.get("slow_recommended"):
        score += 35

    return score


def duplicate_groups(rows: list[dict[str, Any]]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        key = norm_path(row.get("file"))
        if key:
            groups[key].append(index)
    return {
        key: indices
        for key, indices in groups.items()
        if len(indices) > 1
    }


def event_id_for(
    row: dict[str, Any],
    event_by_path: dict[str, dict[str, Any]],
) -> str:
    value = str(row.get("event_id_v2") or "")
    if value:
        return value
    mapped = event_by_path.get(norm_path(row.get("file")), {})
    return str(mapped.get("event_id_v2") or "")


def event_section(candidate: dict[str, Any]) -> str:
    value = str(candidate.get("event_section_v2") or "")
    if value:
        return section_name({"music_section": value})
    return section_name(candidate)


def candidate_score(
    candidate: dict[str, Any],
    slot: dict[str, Any],
    event_match: bool,
    previous: dict[str, Any] | None,
    following: dict[str, Any] | None,
) -> float:
    score = quality_score(candidate)

    candidate_tag = str(candidate.get("scene_tag") or "other")
    slot_tag = str(slot.get("scene_tag") or "other")
    candidate_family = semantic_family(candidate_tag)
    slot_family = semantic_family(slot_tag)

    if event_match:
        score += 85

    if candidate_tag == slot_tag:
        score += 55
    elif candidate_family == slot_family:
        score += 28
    else:
        score -= 65

    if event_section(candidate) == section_name(slot):
        score += 36
    else:
        score -= 22

    candidate_camera = camera_of(candidate)
    slot_camera = camera_of(slot)

    if candidate_camera != slot_camera:
        score += 12

    if previous is not None:
        if candidate_camera != camera_of(previous):
            score += 10
        else:
            score -= 14

    if following is not None:
        if candidate_camera != camera_of(following):
            score += 6
        else:
            score -= 8

    candidate_scale = str(candidate.get("shot_scale") or "unknown")
    slot_scale = str(slot.get("shot_scale") or "unknown")
    if (
        candidate_scale != "unknown"
        and slot_scale != "unknown"
        and candidate_scale != slot_scale
    ):
        score += 5

    # Preserve source quality: weak candidates must not win just because they are unique.
    score -= max(0.0, quality_score(slot) - quality_score(candidate)) * 0.45
    return score


def build_replacement(
    candidate: dict[str, Any],
    slot: dict[str, Any],
    safety: float,
    reason: str,
) -> dict[str, Any]:
    row = dict(slot)
    duration = fnum(slot.get("duration_sec"), 0)
    total = source_total_duration(candidate)
    best_in = fnum(
        candidate.get("best_source_in_sec"),
        fnum(candidate.get("source_in_sec"), 0),
    )

    best_in = clamp(
        best_in,
        safety,
        max(safety, total - safety - duration),
    )

    row.update({
        "unique_source_original_file_140b": slot.get("file"),
        "unique_source_original_filename_140b": filename_of(slot),
        "unique_source_replaced_140b": True,
        "unique_source_reason_140b": reason,
        "file": candidate.get("file"),
        "filename": candidate.get("filename"),
        "scene_tag": candidate.get("scene_tag", slot.get("scene_tag")),
        "camera_group": candidate.get("camera_group", slot.get("camera_group")),
        "shot_scale": candidate.get("shot_scale", slot.get("shot_scale")),
        "source_in_sec": round(best_in, 6),
        "source_out_sec": round(best_in + duration, 6),
        "source_duration_sec": round(duration, 6),
        "media_duration_sec": round(total, 6),
        "source_media_duration_sec": round(total, 6),
        "selected_center_sec": round(best_in + duration / 2, 6),
        "event_id_v2": candidate.get("event_id_v2", slot.get("event_id_v2")),
        "event_section_v2": candidate.get(
            "event_section_v2",
            slot.get("event_section_v2"),
        ),
        "event_family_v2": candidate.get(
            "event_family_v2",
            slot.get("event_family_v2"),
        ),
        "module_140b_unique_source": True,
    })
    return row


def choose_unique_candidate(
    rows: list[dict[str, Any]],
    slot_index: int,
    event_by_path: dict[str, dict[str, Any]],
    event_by_id: dict[str, list[dict[str, Any]]],
    catalog: list[dict[str, Any]],
    used_paths: set[str],
    excluded_names: set[str],
    safety: float,
) -> tuple[dict[str, Any] | None, str, float]:
    slot = rows[slot_index]
    previous = rows[slot_index - 1] if slot_index > 0 else None
    following = rows[slot_index + 1] if slot_index + 1 < len(rows) else None
    target_event = event_id_for(slot, event_by_path)

    ranked = []
    candidate_seen = set()

    # Same event is always searched first.
    ordered_pools = [
        ("same_event", event_by_id.get(target_event, []) if target_event else []),
        ("catalog", catalog),
    ]

    for pool_name, pool in ordered_pools:
        for candidate in pool:
            key = norm_path(candidate.get("file"))
            name = filename_of(candidate).lower()

            if not key or key in candidate_seen:
                continue
            candidate_seen.add(key)

            if key in used_paths:
                continue
            if name in excluded_names:
                continue
            if "proxy" in name or "/proxy" in key or "\\proxy" in str(candidate.get("file") or "").lower():
                continue
            if not Path(str(candidate.get("file") or "")).exists():
                continue
            if not can_fit(candidate, slot, safety):
                continue

            candidate_event = str(candidate.get("event_id_v2") or "")
            event_match = bool(target_event and candidate_event == target_event)
            score = candidate_score(
                candidate,
                slot,
                event_match,
                previous,
                following,
            )

            # A catalog fallback must still be semantically close.
            candidate_tag = str(candidate.get("scene_tag") or "other")
            slot_tag = str(slot.get("scene_tag") or "other")
            same_family = (
                semantic_family(candidate_tag)
                == semantic_family(slot_tag)
            )
            if not event_match and candidate_tag != slot_tag and not same_family:
                continue

            ranked.append((score, pool_name, candidate))

    if not ranked:
        return None, "", 0.0

    ranked.sort(key=lambda item: item[0], reverse=True)
    score, pool_name, candidate = ranked[0]
    return candidate, pool_name, score


def deduplicate_timeline(
    rows: list[dict[str, Any]],
    event_by_path: dict[str, dict[str, Any]],
    event_by_id: dict[str, list[dict[str, Any]]],
    catalog: list[dict[str, Any]],
    excluded_names: set[str],
    safety: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output = [dict(row) for row in rows]
    groups = duplicate_groups(output)

    # Keep exactly one occurrence from every repeated source.
    keep_indices = set()
    replacement_indices = []

    for path_key, indices in groups.items():
        keeper = max(indices, key=lambda index: protected_score(output[index]))
        keep_indices.add(keeper)

        for index in indices:
            if index != keeper:
                replacement_indices.append(index)

    # Every path stays reserved if it has a kept occurrence.
    used_paths = set()
    for index, row in enumerate(output):
        key = norm_path(row.get("file"))
        if not key:
            continue
        if key not in groups or index in keep_indices:
            used_paths.add(key)

    changes = []
    unresolved = []

    # Replace lower-importance duplicate occurrences first.
    replacement_indices.sort(key=lambda index: protected_score(output[index]))

    for index in replacement_indices:
        slot = output[index]
        old_key = norm_path(slot.get("file"))

        candidate, source_pool, score = choose_unique_candidate(
            output,
            index,
            event_by_path,
            event_by_id,
            catalog,
            used_paths,
            excluded_names,
            safety,
        )

        if candidate is None:
            unresolved.append({
                "timeline_index": index + 1,
                "filename": filename_of(slot),
                "file": slot.get("file"),
            })
            continue

        new_row = build_replacement(
            candidate,
            slot,
            safety,
            f"deduplicate_{source_pool}",
        )
        output[index] = new_row
        new_key = norm_path(candidate.get("file"))
        used_paths.add(new_key)

        changes.append({
            "timeline_index": index + 1,
            "action": "replace_duplicate_source",
            "old_filename": filename_of(slot),
            "new_filename": filename_of(candidate),
            "old_camera": camera_of(slot),
            "new_camera": camera_of(candidate),
            "candidate_pool": source_pool,
            "score": round(score, 3),
        })

    return output, {
        "duplicate_group_count_before": len(groups),
        "duplicate_occurrence_count_before": sum(
            len(indices) - 1 for indices in groups.values()
        ),
        "replacement_count": len(changes),
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
        "changes": changes,
    }


def protected_shot(row: dict[str, Any]) -> bool:
    return protected_score(row) >= quality_score(row) + 250


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


def conservative_camera_break(
    rows: list[dict[str, Any]],
    event_by_path: dict[str, dict[str, Any]],
    event_by_id: dict[str, list[dict[str, Any]]],
    catalog: list[dict[str, Any]],
    excluded_names: set[str],
    safety: float,
    max_run: int,
    max_changes: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output = [dict(row) for row in rows]
    used_paths = {
        norm_path(row.get("file"))
        for row in output
        if norm_path(row.get("file"))
    }
    changes = []

    for _ in range(5):
        changed_this_pass = False

        start = 0
        while start < len(output):
            camera = camera_of(output[start])
            end = start + 1
            while end < len(output) and camera_of(output[end]) == camera:
                end += 1

            length = end - start
            if length > max_run and len(changes) < max_changes:
                preferred = min(end - 2, start + max_run)
                slot_candidates = [
                    index
                    for index in range(start + 1, end - 1)
                    if not protected_shot(output[index])
                ]
                slot_candidates.sort(
                    key=lambda index: (
                        abs(index - preferred),
                        protected_score(output[index]),
                    )
                )

                for slot_index in slot_candidates:
                    slot = output[slot_index]
                    candidate, pool_name, score = choose_unique_candidate(
                        output,
                        slot_index,
                        event_by_path,
                        event_by_id,
                        catalog,
                        used_paths,
                        excluded_names,
                        safety,
                    )

                    if candidate is None:
                        continue
                    if camera_of(candidate) == camera:
                        continue

                    candidate_camera = camera_of(candidate)
                    projected_run = local_run_if_camera(
                        output,
                        slot_index,
                        candidate_camera,
                    )
                    if projected_run > max_run + 1:
                        continue

                    old = output[slot_index]
                    output[slot_index] = build_replacement(
                        candidate,
                        old,
                        safety,
                        f"camera_break_{pool_name}",
                    )
                    used_paths.add(norm_path(candidate.get("file")))

                    changes.append({
                        "timeline_index": slot_index + 1,
                        "action": "break_camera_run",
                        "old_filename": filename_of(old),
                        "new_filename": filename_of(candidate),
                        "old_camera": camera_of(old),
                        "new_camera": camera_of(candidate),
                        "run_length_before": length,
                        "score": round(score, 3),
                    })
                    changed_this_pass = True
                    break

            start = end

        if max_camera_run(output) <= max_run:
            break
        if not changed_this_pass:
            break

    return output, changes


def run_hard_fit(
    project: Path,
    music_root: str,
    safety: float,
    excluded_names: list[str],
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
    for name in excluded_names:
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


def write_pipeline_timeline(
    project: Path,
    data: dict[str, Any],
    rows: list[dict[str, Any]],
    module_name: str,
    summary: dict[str, Any],
) -> None:
    output = dict(data)
    output.update({
        "module_before_140b": data.get("module"),
        "module": module_name,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "timeline_count": len(rows),
        "timeline_seconds": max(
            [fnum(row.get("timeline_end_sec"), 0) for row in rows] + [0]
        ),
        "unique_source_summary": summary,
        "items": rows,
    })

    write_json(project / "stt_camera_run_balanced_timeline_v2.json", output)
    write_json(project / "stt_final_cut_beat_timeline_v2.json", output)
    write_json(project / "stt_multicam_directed_timeline_v1.json", output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="140B unique source resolver and safe camera run breaker."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--max-camera-run", type=int, default=6)
    parser.add_argument("--max-camera-changes", type=int, default=10)
    parser.add_argument("--source-safety-sec", type=float, default=1.0)
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "unique_source_camera_run_140b")

    input_path, data = locate_input(project)
    rows = [dict(row) for row in (data.get("items") or [])]

    if not input_path or not rows:
        result = {"ok": False, "error": "NO_INPUT_TIMELINE"}
        write_json(report_dir / "FINAL_140B_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    event_by_path, event_by_id, catalog = load_catalog(project)

    excluded_names = set(KNOWN_BAD)
    excluded_names.update(
        Path(str(value)).name.lower()
        for value in args.exclude
        if str(value).strip()
    )
    safety = max(0.25, args.source_safety_sec)

    before = validate_timeline(rows)

    unique_rows, dedupe_summary = deduplicate_timeline(
        rows,
        event_by_path,
        event_by_id,
        catalog,
        excluded_names,
        safety,
    )
    after_dedupe = validate_timeline(unique_rows)

    balanced_rows, camera_changes = conservative_camera_break(
        unique_rows,
        event_by_path,
        event_by_id,
        catalog,
        excluded_names,
        safety,
        max(4, args.max_camera_run),
        max(0, args.max_camera_changes),
    )
    after_balance = validate_timeline(balanced_rows)

    backup = project / "stt_final_cut_before_140b_backup.json"
    if not backup.exists():
        shutil.copy2(input_path, backup)

    prebuild_summary = {
        "before": before,
        "after_dedupe": after_dedupe,
        "after_balance": after_balance,
        "dedupe": dedupe_summary,
        "camera_change_count": len(camera_changes),
    }

    write_pipeline_timeline(
        project,
        data,
        balanced_rows,
        "140b_unique_source_camera_run",
        prebuild_summary,
    )

    write_json(
        report_dir / "DEDUPLICATE_CHANGES_140B.json",
        {"items": dedupe_summary.get("changes") or []},
    )
    write_json(
        report_dir / "CAMERA_RUN_CHANGES_140B.json",
        {"items": camera_changes},
    )

    hard_fit_result = None

    if (
        dedupe_summary["unresolved_count"] == 0
        and after_balance["duplicate_source_count"] == 0
    ):
        hard_fit_result = run_hard_fit(
            project,
            args.music_root,
            safety,
            sorted(excluded_names),
        )

    # Hard-fit can alter sources, so validate the actual final timeline.
    final_data = read_json(project / "stt_final_cut_beat_timeline_v2.json")
    final_rows = [dict(row) for row in (final_data.get("items") or [])]
    final_validation = validate_timeline(final_rows)

    # One post-build repair pass if an older 136E behavior reintroduced a duplicate.
    postbuild_dedupe = None
    second_hard_fit = None

    if final_validation["duplicate_source_count"] > 0:
        repaired_rows, postbuild_dedupe = deduplicate_timeline(
            final_rows,
            event_by_path,
            event_by_id,
            catalog,
            excluded_names,
            safety,
        )
        repaired_validation = validate_timeline(repaired_rows)

        if (
            postbuild_dedupe["unresolved_count"] == 0
            and repaired_validation["duplicate_source_count"] == 0
        ):
            write_pipeline_timeline(
                project,
                final_data,
                repaired_rows,
                "140b_postbuild_unique_source_repair",
                {
                    "postbuild_dedupe": postbuild_dedupe,
                    "validation": repaired_validation,
                },
            )
            second_hard_fit = run_hard_fit(
                project,
                args.music_root,
                safety,
                sorted(excluded_names),
            )

            final_data = read_json(
                project / "stt_final_cut_beat_timeline_v2.json"
            )
            final_rows = [dict(row) for row in (final_data.get("items") or [])]
            final_validation = validate_timeline(final_rows)

    result = {
        "ok": (
            dedupe_summary["unresolved_count"] == 0
            and final_validation["duplicate_source_count"] == 0
            and final_validation["gap_count"] == 0
            and final_validation["overlap_count"] == 0
            and bool(
                (second_hard_fit and second_hard_fit.get("ok"))
                or (hard_fit_result and hard_fit_result.get("ok"))
            )
        ),
        "report_dir": str(report_dir),
        "input_timeline": str(input_path),
        "backup_timeline": str(backup),
        "timeline_count": len(final_rows),
        "duplicate_source_before": before["duplicate_source_count"],
        "duplicate_source_after_dedupe": after_dedupe["duplicate_source_count"],
        "duplicate_source_final": final_validation["duplicate_source_count"],
        "duplicate_replacement_count": dedupe_summary["replacement_count"],
        "dedupe_unresolved_count": dedupe_summary["unresolved_count"],
        "camera_change_count": len(camera_changes),
        "max_camera_run_before": before["max_same_camera_run"],
        "max_camera_run_after_dedupe": after_dedupe["max_same_camera_run"],
        "max_camera_run_after_balance": after_balance["max_same_camera_run"],
        "max_camera_run_final": final_validation["max_same_camera_run"],
        "gap_count": final_validation["gap_count"],
        "overlap_count": final_validation["overlap_count"],
        "camera_counts": final_validation["camera_counts"],
        "hard_fit_build": hard_fit_result,
        "postbuild_dedupe": postbuild_dedupe,
        "second_hard_fit_build": second_hard_fit,
        "video_only_xml": str(project / "stt_128h_VIDEO_ONLY_FINAL.xml"),
        "stereo_wav": str(project / "stt_128h_music_STEREO_48K.wav"),
        "fix": "140b_unique_source_camera_run",
    }

    write_json(report_dir / "FINAL_140B_REPORT.json", result)
    print(json.dumps(result, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
