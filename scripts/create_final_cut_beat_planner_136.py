from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_134_136_common import *


NEIGHBORS = {
    "intro": ["story"],
    "story": ["intro", "build", "release"],
    "build": ["story", "pre_climax", "climax"],
    "pre_climax": ["build", "climax"],
    "climax": ["pre_climax", "build", "release"],
    "release": ["climax", "story", "ending"],
    "ending": ["release", "story"],
}


def base_score(row: dict[str, Any], interval: dict[str, Any]) -> float:
    target = str(interval.get("section") or "story")
    tag = str(row.get("scene_tag") or "other")

    score = (
        fnum(row.get("moment_combined_score_v2"), 50) * 0.58
        + fnum(row.get("moment_quality_score_v2"), 45) * 0.16
        + fnum(row.get("hero_score"), 0) * 0.18
        + fnum(row.get("beauty_score"), 55) * 0.12
    )

    if target == "intro" and tag in {
        "decor", "detail_beauty", "cdcr_portrait", "first_look"
    }:
        score += 18
    elif target == "climax" and tag in {
        "cdcr_portrait", "first_look", "vow", "family_emotion",
        "reception_stage", "party", "wedding_game", "ending",
    }:
        score += 24
    elif target == "ending" and tag in {
        "ending", "cdcr_portrait", "first_look", "family_emotion"
    }:
        score += 28

    if fnum(interval.get("duration_sec"), 0) >= 3.2 and (
        row.get("is_main_climax_shot")
        or row.get("reservation_role")
        or tag in {"vow", "family_emotion", "first_look", "ending"}
    ):
        score += 20

    return score


def choose_candidate(
    pool: list[dict[str, Any]],
    interval: dict[str, Any],
    previous: dict[str, Any] | None,
    recent_files: list[str],
    camera_run: int,
    family_run: int,
) -> tuple[int, dict[str, Any]]:
    scored = []

    for index, candidate in enumerate(pool):
        score = base_score(candidate, interval)
        camera = str(candidate.get("camera_group") or "CAM_UNKNOWN")
        family = semantic_family(str(candidate.get("scene_tag") or "other"))
        file_key = norm_path(candidate.get("file"))

        if previous is not None:
            previous_camera = str(previous.get("camera_group") or "CAM_UNKNOWN")
            previous_family = semantic_family(
                str(previous.get("scene_tag") or "other")
            )

            if camera == previous_camera:
                score -= 8
                if camera_run >= 2:
                    score -= 24

            if family == previous_family:
                score -= 5
                if family_run >= 3:
                    score -= 14

        if file_key in recent_files[-5:]:
            score -= 40

        # Preserve section source order, but not too rigidly.
        score -= min(18.0, index * 1.25)
        scored.append((score, index, candidate))

    scored.sort(key=lambda item: item[0], reverse=True)
    _, index, candidate = scored[0]
    return index, candidate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="136B Safe Final Cut Planner."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "safe_final_cut_planner_136b")

    moment = read_json(project / "stt_smart_moment_timeline_v2.json")
    phrase = read_json(project / "stt_music_phrase_rhythm_v2.json")

    rows = [dict(row) for row in (moment.get("items") or [])]
    intervals = [dict(row) for row in (phrase.get("intervals") or [])]

    if not rows or not intervals:
        result = {
            "ok": False,
            "error": "MISSING_134_OR_135B",
        }
        write_json(report_dir / "FINAL_136B_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        pools[section_name(row)].append(row)

    output = []
    previous = None
    recent_files: list[str] = []
    camera_run = 0
    family_run = 0
    mismatch_count = 0
    borrowed_count = 0

    for index, interval in enumerate(intervals, 1):
        target = str(interval.get("section") or "story")
        source_section = target
        pool = pools.get(target, [])

        if not pool:
            for neighbor in NEIGHBORS.get(target, []):
                if pools.get(neighbor):
                    source_section = neighbor
                    pool = pools[neighbor]
                    borrowed_count += 1
                    break

        if not pool:
            # Last-resort: choose any remaining source, never reuse.
            non_empty = [
                (label, section_pool)
                for label, section_pool in pools.items()
                if section_pool
            ]
            if not non_empty:
                break
            source_section, pool = max(
                non_empty,
                key=lambda item: len(item[1]),
            )
            borrowed_count += 1

        chosen_index, chosen = choose_candidate(
            pool,
            interval,
            previous,
            recent_files,
            camera_run,
            family_run,
        )
        pool.pop(chosen_index)

        if source_section != target:
            mismatch_count += 1

        duration = fnum(interval.get("duration_sec"), 1.5)
        media_duration = fnum(
            chosen.get("media_duration_sec"),
            fnum(chosen.get("source_media_duration_sec"), 0),
        )
        center = fnum(
            chosen.get("selected_center_sec"),
            fnum(chosen.get("source_in_sec"), 0)
            + fnum(chosen.get("duration_sec"), duration) / 2,
        )
        source_in = center - duration / 2

        if media_duration > 0:
            source_in = clamp(
                source_in,
                0.0,
                max(0.0, media_duration - duration - 0.10),
            )
        else:
            source_in = max(0.0, source_in)

        row = dict(chosen)
        row.update({
            "index": index,
            "timeline_start_sec": round(
                fnum(interval.get("start_sec"), 0),
                6,
            ),
            "timeline_end_sec": round(
                fnum(interval.get("end_sec"), 0),
                6,
            ),
            "duration_sec": round(duration, 6),
            "source_in_sec": round(source_in, 6),
            "source_out_sec": round(source_in + duration, 6),
            "source_duration_sec": round(duration, 6),
            "music_section": target,
            "story_part": target,
            "source_section_before_136b": source_section,
            "section_borrowed_136b": source_section != target,
            "rhythm_mode_v2": interval.get("rhythm_mode"),
            "module_136_planned": True,
        })

        if (
            duration >= 3.2
            and target in {"climax", "ending"}
            and (
                row.get("is_main_climax_shot")
                or fnum(row.get("moment_combined_score_v2"), 0) >= 74
            )
        ):
            row["slow_recommended"] = True
            row["slow_percent"] = 50

        current_camera = str(row.get("camera_group") or "CAM_UNKNOWN")
        current_family = semantic_family(str(row.get("scene_tag") or "other"))

        if previous is not None and current_camera == str(
            previous.get("camera_group") or "CAM_UNKNOWN"
        ):
            camera_run += 1
        else:
            camera_run = 1

        if previous is not None and current_family == semantic_family(
            str(previous.get("scene_tag") or "other")
        ):
            family_run += 1
        else:
            family_run = 1

        previous = row
        recent_files.append(norm_path(row.get("file")))
        output.append(row)

    gap_count = 0
    overlap_count = 0
    source_overflow_count = 0
    same_camera_runs = []
    run = 0
    previous_camera = None

    for previous_row, current_row in zip(output, output[1:]):
        delta = (
            fnum(current_row.get("timeline_start_sec"), 0)
            - fnum(previous_row.get("timeline_end_sec"), 0)
        )
        if delta > 0.001:
            gap_count += 1
        elif delta < -0.001:
            overlap_count += 1

    for row in output:
        media_duration = fnum(
            row.get("media_duration_sec"),
            fnum(row.get("source_media_duration_sec"), 0),
        )
        if (
            media_duration > 0
            and fnum(row.get("source_out_sec"), 0) > media_duration + 0.001
        ):
            source_overflow_count += 1

        camera = str(row.get("camera_group") or "CAM_UNKNOWN")
        if camera == previous_camera:
            run += 1
        else:
            if run:
                same_camera_runs.append(run)
            run = 1
        previous_camera = camera

    if run:
        same_camera_runs.append(run)

    timeline_seconds = max(
        [fnum(row.get("timeline_end_sec"), 0) for row in output] + [0]
    )

    output_data = {
        "ok": True,
        "module": "136b_safe_final_cut_planner",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "timeline_count": len(output),
        "timeline_seconds": round(timeline_seconds, 6),
        "duration_stats": duration_stats(output),
        "selection_summary": {
            "reused_source_count": 0,
            "section_mismatch_count": mismatch_count,
            "borrowed_source_count": borrowed_count,
        },
        "validation_summary": {
            "gap_count": gap_count,
            "overlap_count": overlap_count,
            "source_overflow_count": source_overflow_count,
            "max_same_camera_run": max(same_camera_runs + [0]),
            "camera_counts": dict(Counter(
                str(row.get("camera_group") or "CAM_UNKNOWN")
                for row in output
            )),
            "section_counts": dict(Counter(
                str(row.get("music_section") or "story")
                for row in output
            )),
        },
        "items": output,
    }

    output_path = project / "stt_final_cut_beat_timeline_v2.json"
    canonical_path = project / "stt_multicam_directed_timeline_v1.json"
    backup_path = project / "stt_multicam_directed_before_136b_backup.json"

    if canonical_path.exists() and not backup_path.exists():
        shutil.copy2(canonical_path, backup_path)

    write_json(output_path, output_data)
    write_json(canonical_path, output_data)
    write_json(report_dir / output_path.name, output_data)

    summary = {
        "ok": True,
        "report_dir": str(report_dir),
        "output_timeline": str(output_path),
        "canonical_timeline": str(canonical_path),
        "backup_timeline": str(backup_path),
        "timeline_count": len(output),
        "timeline_seconds": round(timeline_seconds, 3),
        "duration_stats": duration_stats(output),
        "reused_source_count": 0,
        "section_mismatch_count": mismatch_count,
        "borrowed_source_count": borrowed_count,
        "gap_count": gap_count,
        "overlap_count": overlap_count,
        "source_overflow_count": source_overflow_count,
        "max_same_camera_run": max(same_camera_runs + [0]),
        "camera_counts": output_data["validation_summary"]["camera_counts"],
        "section_counts": output_data["validation_summary"]["section_counts"],
        "fix": "136b_safe_final_cut_planner",
    }
    write_json(report_dir / "FINAL_136B_REPORT.json", summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
