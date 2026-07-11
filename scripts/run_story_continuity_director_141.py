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

from stt_141_common import *


KNOWN_BAD = {"stt0043.mp4", "stt0008.mp4"}

ALLOWED_FAMILY_TRANSITIONS = {
    "establishing": {"detail", "preparation", "couple", "ceremony"},
    "detail": {"establishing", "preparation", "couple", "ceremony", "reception"},
    "preparation": {"detail", "couple", "family", "ceremony"},
    "couple": {"detail", "family", "ceremony", "reception", "party"},
    "family": {"couple", "ceremony", "reception"},
    "ceremony": {"family", "couple", "reception", "procession"},
    "procession": {"ceremony", "couple", "reception"},
    "reception": {"family", "couple", "guest", "party", "ceremony"},
    "guest": {"reception", "party", "family"},
    "party": {"reception", "couple", "guest"},
    "other": {
        "establishing", "detail", "preparation", "couple", "family",
        "ceremony", "procession", "reception", "guest", "party", "other",
    },
}


def locate_input(project: Path) -> tuple[Path | None, dict[str, Any]]:
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


def event_metadata(
    project: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
    data = read_json(project / "stt_event_context_map_v2.json")
    by_path: dict[str, dict[str, Any]] = {}
    event_positions: dict[str, list[float]] = {}

    for row in data.get("items") or []:
        key = norm_path(row.get("file"))
        event_id = str(row.get("event_id_v2") or "")
        position = fnum(row.get("estimated_story_position_v2"), -1)

        if key and key not in by_path:
            by_path[key] = dict(row)

        if event_id and position >= 0:
            event_positions.setdefault(event_id, []).append(position)

    averaged = {
        event_id: sum(values) / len(values)
        for event_id, values in event_positions.items()
        if values
    }
    return by_path, averaged


def enrich_rows(
    rows: list[dict[str, Any]],
    by_path: dict[str, dict[str, Any]],
    event_positions: dict[str, float],
) -> list[dict[str, Any]]:
    output = []
    total_seconds = max(
        [fnum(row.get("timeline_end_sec"), 0) for row in rows] + [1.0]
    )

    for row in rows:
        item = dict(row)
        mapped = by_path.get(norm_path(item.get("file")), {})

        event_id = str(
            item.get("event_id_v2")
            or mapped.get("event_id_v2")
            or ""
        )
        story_position = fnum(
            item.get("estimated_story_position_v2"),
            fnum(
                mapped.get("estimated_story_position_v2"),
                event_positions.get(event_id, -1),
            ),
        )

        if story_position < 0:
            center = (
                fnum(item.get("timeline_start_sec"), 0)
                + fnum(item.get("timeline_end_sec"), 0)
            ) / 2
            story_position = clamp(center / total_seconds, 0.0, 1.0)

        item["_event_id_141"] = event_id
        item["_story_position_141"] = story_position
        item["_family_141"] = semantic_family(
            str(item.get("scene_tag") or mapped.get("scene_tag") or "other")
        )
        item["_scale_141"] = str(
            item.get("shot_scale")
            or mapped.get("shot_scale")
            or "unknown"
        ).lower()
        output.append(item)

    return output


def source_total_duration(row: dict[str, Any]) -> float:
    return fnum(
        row.get("media_duration_sec"),
        fnum(
            row.get("source_media_duration_sec"),
            fnum(row.get("duration_sec"), 0),
        ),
    )


def can_fit(source: dict[str, Any], slot: dict[str, Any], safety: float) -> bool:
    total = source_total_duration(source)
    duration = fnum(slot.get("duration_sec"), 0)
    return total > 0 and total >= duration + safety * 2 + 0.10


def family_transition_cost(left: str, right: str) -> float:
    if left == right:
        return 0.8
    if right in ALLOWED_FAMILY_TRANSITIONS.get(left, set()):
        return 1.5
    return 11.0


def scale_transition_cost(left: str, right: str) -> float:
    if left == "unknown" or right == "unknown":
        return 0.5
    if left == right:
        return 2.5

    good = {
        ("wide", "medium"),
        ("medium", "close"),
        ("close", "medium"),
        ("medium", "wide"),
        ("wide", "close"),
    }
    if (left, right) in good:
        return 0.4
    return 2.0


def pair_cost(left: dict[str, Any], right: dict[str, Any]) -> float:
    if section_name(left) != section_name(right):
        return 0.0

    left_position = fnum(left.get("_story_position_141"), 0)
    right_position = fnum(right.get("_story_position_141"), 0)
    delta = right_position - left_position

    cost = 0.0

    # Strong penalty for visibly going backward in the event progression.
    if delta < -0.08:
        cost += 34.0 + abs(delta) * 55.0
    elif delta < -0.035:
        cost += 15.0 + abs(delta) * 30.0
    else:
        cost += min(5.0, abs(delta) * 8.0)

    left_event = str(left.get("_event_id_141") or "")
    right_event = str(right.get("_event_id_141") or "")
    if left_event and right_event and left_event == right_event:
        cost -= 3.0

    left_family = str(left.get("_family_141") or "other")
    right_family = str(right.get("_family_141") or "other")
    cost += family_transition_cost(left_family, right_family)

    cost += scale_transition_cost(
        str(left.get("_scale_141") or "unknown"),
        str(right.get("_scale_141") or "unknown"),
    )

    if camera_of(left) == camera_of(right):
        cost += 1.2

    return cost


def slot_position_cost(
    row: dict[str, Any],
    index: int,
    rows: list[dict[str, Any]],
) -> float:
    start = fnum(rows[index].get("timeline_start_sec"), 0)
    end = fnum(rows[index].get("timeline_end_sec"), start)
    total = max(
        [fnum(item.get("timeline_end_sec"), 0) for item in rows] + [1.0]
    )
    expected = ((start + end) / 2) / total
    actual = fnum(row.get("_story_position_141"), expected)
    return abs(actual - expected) * 9.0


def indices_cost(rows: list[dict[str, Any]], indices: set[int]) -> float:
    cost = 0.0
    visited_pairs = set()

    for index in indices:
        if 0 <= index < len(rows):
            cost += slot_position_cost(rows[index], index, rows)

        if 0 <= index - 1 < len(rows) and 0 <= index < len(rows):
            pair = (index - 1, index)
            if pair not in visited_pairs:
                cost += pair_cost(rows[index - 1], rows[index])
                visited_pairs.add(pair)

        if 0 <= index < len(rows) - 1:
            pair = (index, index + 1)
            if pair not in visited_pairs:
                cost += pair_cost(rows[index], rows[index + 1])
                visited_pairs.add(pair)

    return cost


def continuity_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    backward = 0
    severe_backward = 0
    abrupt_family = 0
    same_event_pairs = 0
    total_cost = 0.0

    for left, right in zip(rows, rows[1:]):
        if section_name(left) != section_name(right):
            continue

        delta = (
            fnum(right.get("_story_position_141"), 0)
            - fnum(left.get("_story_position_141"), 0)
        )
        if delta < -0.035:
            backward += 1
        if delta < -0.08:
            severe_backward += 1

        left_family = str(left.get("_family_141") or "other")
        right_family = str(right.get("_family_141") or "other")
        if (
            left_family != right_family
            and right_family not in ALLOWED_FAMILY_TRANSITIONS.get(
                left_family,
                set(),
            )
        ):
            abrupt_family += 1

        left_event = str(left.get("_event_id_141") or "")
        right_event = str(right.get("_event_id_141") or "")
        if left_event and left_event == right_event:
            same_event_pairs += 1

        total_cost += pair_cost(left, right)

    return {
        "continuity_cost": round(total_cost, 3),
        "backward_jump_count": backward,
        "severe_backward_jump_count": severe_backward,
        "abrupt_family_jump_count": abrupt_family,
        "same_event_pair_count": same_event_pairs,
    }


def source_in_for_slot(
    source: dict[str, Any],
    slot: dict[str, Any],
    safety: float,
) -> float:
    duration = fnum(slot.get("duration_sec"), 0)
    total = source_total_duration(source)

    center = fnum(
        source.get("selected_center_sec"),
        fnum(source.get("source_in_sec"), 0)
        + fnum(source.get("duration_sec"), duration) / 2,
    )

    return clamp(
        center - duration / 2,
        safety,
        max(safety, total - safety - duration),
    )


def place_source_in_slot(
    source: dict[str, Any],
    slot: dict[str, Any],
    safety: float,
    source_index: int,
) -> dict[str, Any]:
    row = dict(source)
    duration = fnum(slot.get("duration_sec"), 0)
    source_in = source_in_for_slot(source, slot, safety)

    # Preserve all timeline-slot properties.
    for key in [
        "index",
        "timeline_start_sec",
        "timeline_end_sec",
        "duration_sec",
        "music_section",
        "story_part",
        "story_chapter",
        "rhythm_mode_v2",
        "beats_skipped_v2",
        "end_beat_strength_v2",
    ]:
        if key in slot:
            row[key] = slot[key]

    row.update({
        "source_in_sec": round(source_in, 6),
        "source_out_sec": round(source_in + duration, 6),
        "source_duration_sec": round(duration, 6),
        "story_continuity_source_index_141": source_index + 1,
        "story_continuity_moved_141": True,
        "module_141_story_continuity": True,
    })
    return row


def simulate_swap(
    rows: list[dict[str, Any]],
    left_index: int,
    right_index: int,
    safety: float,
) -> list[dict[str, Any]]:
    output = list(rows)
    left_source = rows[left_index]
    right_source = rows[right_index]

    output[left_index] = place_source_in_slot(
        right_source,
        rows[left_index],
        safety,
        right_index,
    )
    output[right_index] = place_source_in_slot(
        left_source,
        rows[right_index],
        safety,
        left_index,
    )
    return output


def allowed_swap(
    rows: list[dict[str, Any]],
    left_index: int,
    right_index: int,
    safety: float,
) -> bool:
    left = rows[left_index]
    right = rows[right_index]

    if section_name(left) != section_name(right):
        return False
    if protected_shot(left) or protected_shot(right):
        return False
    if filename_of(left).lower() in KNOWN_BAD:
        return False
    if filename_of(right).lower() in KNOWN_BAD:
        return False
    if not can_fit(left, right, safety):
        return False
    if not can_fit(right, left, safety):
        return False

    # Do not swap completely unrelated content.
    left_family = str(left.get("_family_141") or "other")
    right_family = str(right.get("_family_141") or "other")
    left_event = str(left.get("_event_id_141") or "")
    right_event = str(right.get("_event_id_141") or "")

    same_event = bool(left_event and left_event == right_event)
    same_family = left_family == right_family
    compatible_family = (
        right_family in ALLOWED_FAMILY_TRANSITIONS.get(left_family, set())
        or left_family in ALLOWED_FAMILY_TRANSITIONS.get(right_family, set())
    )

    return same_event or same_family or compatible_family


def optimize_continuity(
    rows: list[dict[str, Any]],
    lookahead: int,
    max_swaps: int,
    minimum_improvement: float,
    safety: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output = [dict(row) for row in rows]
    swaps = []

    for pass_index in range(max_swaps):
        best = None

        for left_index in range(len(output) - 1):
            max_right = min(
                len(output),
                left_index + max(2, lookahead) + 1,
            )

            for right_index in range(left_index + 1, max_right):
                if not allowed_swap(
                    output,
                    left_index,
                    right_index,
                    safety,
                ):
                    continue

                affected = {
                    left_index - 1,
                    left_index,
                    left_index + 1,
                    right_index - 1,
                    right_index,
                    right_index + 1,
                }

                before_cost = indices_cost(output, affected)
                simulated = simulate_swap(
                    output,
                    left_index,
                    right_index,
                    safety,
                )
                after_cost = indices_cost(simulated, affected)
                improvement = before_cost - after_cost

                if improvement < minimum_improvement:
                    continue

                if best is None or improvement > best["improvement"]:
                    best = {
                        "left_index": left_index,
                        "right_index": right_index,
                        "before_cost": before_cost,
                        "after_cost": after_cost,
                        "improvement": improvement,
                        "simulated": simulated,
                    }

        if best is None:
            break

        left_index = best["left_index"]
        right_index = best["right_index"]
        left_before = output[left_index]
        right_before = output[right_index]

        output = best["simulated"]
        swaps.append({
            "pass": pass_index + 1,
            "left_timeline_index": left_index + 1,
            "right_timeline_index": right_index + 1,
            "left_filename_before": filename_of(left_before),
            "right_filename_before": filename_of(right_before),
            "left_family": left_before.get("_family_141"),
            "right_family": right_before.get("_family_141"),
            "left_event": left_before.get("_event_id_141"),
            "right_event": right_before.get("_event_id_141"),
            "improvement": round(best["improvement"], 3),
            "cost_before": round(best["before_cost"], 3),
            "cost_after": round(best["after_cost"], 3),
        })

    return output, swaps


def clean_internal_fields(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: value
            for key, value in row.items()
            if not key.startswith("_")
        }
        for row in rows
    ]


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
        description="141 Story Continuity Director."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--lookahead", type=int, default=5)
    parser.add_argument("--max-swaps", type=int, default=12)
    parser.add_argument("--minimum-improvement", type=float, default=5.0)
    parser.add_argument("--source-safety-sec", type=float, default=1.0)
    parser.add_argument("--music-root", default="D:/27thang6pschh")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "story_continuity_director_141")

    input_path, data = locate_input(project)
    rows = [dict(row) for row in (data.get("items") or [])]

    if not input_path or not rows:
        result = {"ok": False, "error": "NO_FINAL_TIMELINE"}
        write_json(report_dir / "FINAL_141_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    by_path, event_positions = event_metadata(project)
    enriched = enrich_rows(rows, by_path, event_positions)

    before_metrics = continuity_metrics(enriched)
    before_validation = validate_timeline(enriched)

    optimized, swaps = optimize_continuity(
        enriched,
        max(2, args.lookahead),
        max(0, args.max_swaps),
        max(0.1, args.minimum_improvement),
        max(0.25, args.source_safety_sec),
    )

    after_metrics = continuity_metrics(optimized)
    cleaned = clean_internal_fields(optimized)
    after_validation = validate_timeline(cleaned)

    output_data = dict(data)
    output_data.update({
        "module_before_141": data.get("module"),
        "module": "141_story_continuity_director",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "input_timeline": str(input_path),
        "timeline_count": len(cleaned),
        "continuity_summary": {
            "before": before_metrics,
            "after": after_metrics,
            "swap_count": len(swaps),
        },
        "items": cleaned,
    })

    output_path = project / "stt_story_continuity_timeline_v1.json"
    final_path = project / "stt_final_cut_beat_timeline_v2.json"
    canonical_path = project / "stt_multicam_directed_timeline_v1.json"
    backup_path = project / "stt_final_cut_before_141_backup.json"

    if final_path.exists() and not backup_path.exists():
        shutil.copy2(final_path, backup_path)

    write_json(output_path, output_data)
    write_json(final_path, output_data)
    write_json(canonical_path, output_data)
    write_json(report_dir / output_path.name, output_data)
    write_json(report_dir / "CONTINUITY_SWAPS_141.json", {"items": swaps})

    hard_fit_result = None
    final_validation = after_validation
    final_metrics = after_metrics

    excluded = sorted(
        KNOWN_BAD.union({
            Path(str(value)).name.lower()
            for value in args.exclude
            if str(value).strip()
        })
    )

    if not args.no_build:
        hard_fit_result = run_hard_fit(
            project,
            args.music_root,
            max(0.25, args.source_safety_sec),
            excluded,
        )

        final_data = read_json(final_path)
        final_rows = [dict(row) for row in (final_data.get("items") or [])]
        final_validation = validate_timeline(final_rows)
        final_enriched = enrich_rows(final_rows, by_path, event_positions)
        final_metrics = continuity_metrics(final_enriched)

    result = {
        "ok": (
            final_validation["duplicate_source_count"] == 0
            and final_validation["gap_count"] == 0
            and final_validation["overlap_count"] == 0
            and (
                args.no_build
                or bool(hard_fit_result and hard_fit_result.get("ok"))
            )
        ),
        "report_dir": str(report_dir),
        "input_timeline": str(input_path),
        "output_timeline": str(output_path),
        "final_timeline": str(final_path),
        "backup_timeline": str(backup_path),
        "timeline_count": len(cleaned),
        "swap_count": len(swaps),
        "continuity_cost_before": before_metrics["continuity_cost"],
        "continuity_cost_after": after_metrics["continuity_cost"],
        "continuity_cost_final": final_metrics["continuity_cost"],
        "backward_jump_before": before_metrics["backward_jump_count"],
        "backward_jump_after": after_metrics["backward_jump_count"],
        "backward_jump_final": final_metrics["backward_jump_count"],
        "severe_backward_before": before_metrics["severe_backward_jump_count"],
        "severe_backward_after": after_metrics["severe_backward_jump_count"],
        "abrupt_family_before": before_metrics["abrupt_family_jump_count"],
        "abrupt_family_after": after_metrics["abrupt_family_jump_count"],
        "duplicate_source_count": final_validation["duplicate_source_count"],
        "gap_count": final_validation["gap_count"],
        "overlap_count": final_validation["overlap_count"],
        "hard_fit_build": hard_fit_result,
        "video_only_xml": str(project / "stt_128h_VIDEO_ONLY_FINAL.xml"),
        "stereo_wav": str(project / "stt_128h_music_STEREO_48K.wav"),
        "fix": "141_story_continuity_director",
    }

    write_json(report_dir / "FINAL_141_REPORT.json", result)
    print(json.dumps(result, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
