from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================
# Helpers
# ============================================================

def read_json(path: str | Path) -> dict[str, Any]:
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def inum(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def norm_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def semantic_family(tag: str) -> str:
    tag = str(tag or "other")
    mapping = {
        "decor": "establishing",
        "detail_beauty": "detail",
        "getting_ready": "preparation",
        "first_look": "couple",
        "cdcr_portrait": "couple",
        "ceremony_giatien": "ceremony",
        "church_ceremony": "ceremony",
        "vow": "ceremony",
        "ruoc_dau": "procession",
        "reception_stage": "reception",
        "wedding_game": "reception",
        "family_photo": "family",
        "family_emotion": "family",
        "guest_food": "guest",
        "party": "party",
        "ending": "couple",
        "other": "other",
    }
    return mapping.get(tag, "other")


def timeline_duration(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return max(
        fnum(row.get("timeline_end_sec"), 0.0)
        for row in rows
    )


def duration_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        fnum(row.get("duration_sec"), 0)
        for row in rows
        if fnum(row.get("duration_sec"), 0) > 0
    ]
    if not values:
        return {}

    values = sorted(values)

    def percentile(p: float) -> float:
        index = int(round((len(values) - 1) * p))
        return round(values[index], 3)

    return {
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "avg": round(sum(values) / len(values), 3),
        "p10": percentile(0.10),
        "p50": percentile(0.50),
        "p90": percentile(0.90),
        "under_0_7s": sum(1 for value in values if value < 0.7),
        "over_3s": sum(1 for value in values if value > 3.0),
        "over_5s": sum(1 for value in values if value > 5.0),
    }


# ============================================================
# Input
# ============================================================

def locate_timeline(project: Path) -> tuple[Path | None, dict[str, Any]]:
    names = [
        "stt_128e_bad_source_replaced_timeline_v1.json",
        "stt_multicam_directed_timeline_v1.json",
        "stt_climax_directed_timeline_v1.json",
        "stt_multicam_selected_timeline_v1.json",
        "stt_quality_moment_timeline_v1.json",
        "stt_beat_snapped_beauty_timeline_v1.json",
    ]
    for name in names:
        path = project / name
        data = read_json(path)
        if data.get("items"):
            return path, data
    return None, {}


def load_beats(project: Path) -> list[dict[str, Any]]:
    data = read_json(project / "stt_precise_beat_grid_v2.json")
    output = []
    for row in data.get("beats") or data.get("markers") or []:
        sec = fnum(row.get("time_sec"), fnum(row.get("sec"), -1))
        if sec < 0:
            continue
        output.append({
            "time_sec": sec,
            "strength": fnum(row.get("strength"), 0.5),
            "type": str(row.get("type") or row.get("kind") or "beat"),
        })
    return sorted(output, key=lambda row: row["time_sec"])


def enrich_rows(project: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    camera_map = read_json(project / "stt_camera_source_map_v1.json")
    metadata_by_path = {
        norm_path(row.get("file")): row
        for row in camera_map.get("items") or []
        if norm_path(row.get("file"))
    }

    output = []
    for index, original in enumerate(rows):
        row = dict(original)
        metadata = metadata_by_path.get(norm_path(row.get("file")), {})

        tag = str(row.get("scene_tag") or metadata.get("scene_tag") or "other")
        camera = str(
            row.get("camera_group")
            or metadata.get("camera_group")
            or "CAM_UNKNOWN"
        )
        scale = str(
            row.get("shot_scale")
            or metadata.get("shot_scale")
            or "unknown"
        )

        row["_original_index"] = index
        row["_semantic_family"] = semantic_family(tag)
        row["_camera"] = camera
        row["_scale"] = scale
        row["_quality"] = fnum(
            row.get("quality_window_score"),
            fnum(
                row.get("moment_quality_score"),
                fnum(metadata.get("quality_score"), 45),
            ),
        )
        row["_beauty"] = fnum(
            row.get("beauty_score"),
            fnum(metadata.get("beauty_score"), 55),
        )
        row["_hero"] = fnum(row.get("hero_score"), 0)
        row["_taste"] = fnum(row.get("taste_score"), 0)
        row["_section"] = str(
            row.get("music_section")
            or row.get("story_part")
            or "story"
        )
        output.append(row)

    return output


# ============================================================
# Scoring
# ============================================================

def base_score(row: dict[str, Any]) -> float:
    score = (
        fnum(row.get("_quality"), 45) * 0.42
        + fnum(row.get("_beauty"), 55) * 0.36
        + fnum(row.get("_hero"), 0) * 0.28
        + fnum(row.get("_taste"), 0) * 0.12
    )

    tag = str(row.get("scene_tag") or "other")
    section = str(row.get("_section") or "story")

    if section == "intro":
        if tag in {"decor", "detail_beauty", "cdcr_portrait", "first_look"}:
            score += 18
    elif section == "climax":
        if tag in {
            "cdcr_portrait", "first_look", "vow",
            "family_emotion", "reception_stage",
            "party", "wedding_game", "ending",
        }:
            score += 24
        if tag in {"guest_food", "other"}:
            score -= 16
    elif section == "ending":
        if tag in {"ending", "cdcr_portrait", "first_look", "family_emotion"}:
            score += 28
        if tag in {"guest_food", "wedding_game", "getting_ready"}:
            score -= 24

    if row.get("is_main_climax_shot"):
        score += 30
    if row.get("reservation_role"):
        score += 16

    return score


def transition_penalty(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    camera_run: int,
    family_run: int,
    used_recent_files: list[str],
) -> float:
    if previous is None:
        return 0.0

    penalty = 0.0
    previous_camera = str(previous.get("_camera") or "")
    current_camera = str(current.get("_camera") or "")
    previous_family = str(previous.get("_semantic_family") or "other")
    current_family = str(current.get("_semantic_family") or "other")
    previous_scale = str(previous.get("_scale") or "unknown")
    current_scale = str(current.get("_scale") or "unknown")
    current_file = norm_path(current.get("file"))

    if current_camera == previous_camera:
        penalty += 4.0
        if camera_run >= 3:
            penalty += 18.0
        elif camera_run == 2:
            penalty += 8.0

    if current_family == previous_family:
        penalty += 2.5
        if family_run >= 3:
            penalty += 10.0

    if current_file and current_file in used_recent_files:
        penalty += 30.0

    # Unknown scale must not force a false decision.
    if previous_scale != "unknown" and current_scale != "unknown":
        if previous_scale == current_scale:
            penalty += 5.0
        elif previous_scale in {"wide", "wide_or_detail"} and current_scale in {"medium", "close"}:
            penalty -= 4.0
        elif previous_scale == "medium" and current_scale in {"wide", "close"}:
            penalty -= 3.0
        elif previous_scale == "close" and current_scale in {"medium", "wide"}:
            penalty -= 3.0

    return penalty


# ============================================================
# Local order optimization
# ============================================================

def optimize_section_order(
    section_rows: list[dict[str, Any]],
    window_size: int,
) -> tuple[list[dict[str, Any]], int]:
    remaining = [dict(row) for row in section_rows]
    output = []
    reordered = 0
    previous = None
    camera_run = 0
    family_run = 0
    used_recent_files: list[str] = []

    while remaining:
        window = remaining[:max(1, window_size)]
        scored = []

        for local_index, candidate in enumerate(window):
            score = base_score(candidate)
            score -= transition_penalty(
                previous,
                candidate,
                camera_run,
                family_run,
                used_recent_files[-4:],
            )

            # Preserve story order. The farther the move, the larger the penalty.
            score -= local_index * 3.5

            # Strongly protect explicit story anchors.
            if candidate.get("is_main_climax_shot"):
                score += 12
            if candidate.get("reservation_role"):
                score += 8

            scored.append((score, local_index, candidate))

        scored.sort(key=lambda item: item[0], reverse=True)
        _, chosen_local_index, chosen = scored[0]
        remaining.pop(chosen_local_index)

        if chosen_local_index != 0:
            reordered += 1

        current_camera = str(chosen.get("_camera") or "")
        current_family = str(chosen.get("_semantic_family") or "other")

        if previous is not None and current_camera == str(previous.get("_camera") or ""):
            camera_run += 1
        else:
            camera_run = 1

        if previous is not None and current_family == str(previous.get("_semantic_family") or "other"):
            family_run += 1
        else:
            family_run = 1

        previous = chosen
        used_recent_files.append(norm_path(chosen.get("file")))
        output.append(chosen)

    return output, reordered


def optimize_order(
    rows: list[dict[str, Any]],
    window_size: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: list[tuple[str, list[dict[str, Any]]]] = []

    current_section = None
    current_rows: list[dict[str, Any]] = []

    for row in rows:
        section = str(row.get("_section") or "story")
        if current_section is None:
            current_section = section

        if section != current_section:
            grouped.append((current_section, current_rows))
            current_section = section
            current_rows = []

        current_rows.append(row)

    if current_rows:
        grouped.append((str(current_section), current_rows))

    output = []
    reordered_total = 0
    section_reports = []

    for section, section_rows in grouped:
        # Ending and climax can move slightly more; story stays conservative.
        local_window = window_size
        if section in {"climax", "ending", "intro"}:
            local_window = min(window_size + 1, 6)

        optimized, reordered = optimize_section_order(
            section_rows,
            local_window,
        )
        output.extend(optimized)
        reordered_total += reordered
        section_reports.append({
            "section": section,
            "shot_count": len(section_rows),
            "reordered_count": reordered,
        })

    return output, {
        "reordered_count": reordered_total,
        "section_reports": section_reports,
    }


# ============================================================
# Duration director
# ============================================================

def target_duration(row: dict[str, Any]) -> float:
    section = str(row.get("_section") or "story")
    tag = str(row.get("scene_tag") or "other")
    score = base_score(row)

    if section == "intro":
        base = 2.7
    elif section == "build":
        base = 1.6
    elif section == "pre_climax":
        base = 0.85
    elif section == "climax":
        base = 1.4
    elif section == "release":
        base = 2.5
    elif section == "ending":
        base = 4.0
    else:
        base = 2.2

    if row.get("is_main_climax_shot"):
        base = max(base, 4.2)
    elif row.get("reservation_role"):
        base += 1.0
    elif score >= 90:
        base += 1.1
    elif score >= 75:
        base += 0.45
    elif score < 50:
        base -= 0.45

    if tag in {"vow", "family_emotion", "first_look", "ending"}:
        base += 0.8
    elif tag in {"decor", "detail_beauty", "guest_food"}:
        base -= 0.25

    return clamp(base, 0.5, 6.0)


def redistribute_section_durations(
    section_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    if not section_rows:
        return [], 0

    original_total = sum(
        max(0.4, fnum(row.get("duration_sec"), 0))
        for row in section_rows
    )

    desired = [target_duration(row) for row in section_rows]
    desired_total = sum(desired)

    if desired_total <= 0:
        return section_rows, 0

    scale = original_total / desired_total
    adjusted = [clamp(value * scale, 0.45, 6.5) for value in desired]

    # Correct total after clamping.
    delta = original_total - sum(adjusted)
    passes = 0
    while abs(delta) > 0.001 and passes < 20:
        passes += 1
        candidates = [
            i for i, value in enumerate(adjusted)
            if (
                delta > 0 and value < 6.5
            ) or (
                delta < 0 and value > 0.45
            )
        ]
        if not candidates:
            break

        share = delta / len(candidates)
        for i in candidates:
            old = adjusted[i]
            adjusted[i] = clamp(old + share, 0.45, 6.5)
        delta = original_total - sum(adjusted)

    output = []
    changed = 0

    for row, duration in zip(section_rows, adjusted):
        copy = dict(row)
        old_duration = fnum(copy.get("duration_sec"), 0)
        new_duration = round(duration, 6)

        if abs(new_duration - old_duration) >= 0.08:
            changed += 1

        copy["duration_before_133"] = round(old_duration, 6)
        copy["duration_sec"] = new_duration
        copy["director_duration_target"] = round(target_duration(copy), 6)
        output.append(copy)

    return output, changed


def optimize_durations(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output = []
    changed_total = 0
    section_report = []

    start = 0
    while start < len(rows):
        section = str(rows[start].get("_section") or "story")
        end = start + 1
        while end < len(rows) and str(rows[end].get("_section") or "story") == section:
            end += 1

        part, changed = redistribute_section_durations(rows[start:end])
        output.extend(part)
        changed_total += changed
        section_report.append({
            "section": section,
            "shot_count": len(part),
            "duration_changed_count": changed,
            "section_seconds": round(
                sum(fnum(row.get("duration_sec"), 0) for row in part),
                3,
            ),
        })
        start = end

    return output, {
        "duration_changed_count": changed_total,
        "section_reports": section_report,
    }


# ============================================================
# Beat snap + source validation
# ============================================================

def nearest_beat(
    desired: float,
    beats: list[dict[str, Any]],
    max_shift: float,
) -> tuple[float, str, float]:
    candidates = []

    for beat in beats:
        sec = fnum(beat.get("time_sec"), -1)
        delta = abs(sec - desired)
        if delta <= max_shift:
            strength = fnum(beat.get("strength"), 0.5)
            rank = delta - min(0.04, strength * 0.03)
            candidates.append((
                rank,
                sec,
                str(beat.get("type") or "beat"),
                strength,
            ))

    if not candidates:
        return desired, "original", 0.0

    candidates.sort(key=lambda item: item[0])
    _, sec, kind, strength = candidates[0]
    return sec, kind, strength


def rebuild_and_snap(
    rows: list[dict[str, Any]],
    beats: list[dict[str, Any]],
    max_shift: float,
    minimum_shot: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    boundaries = [0.0]
    for row in rows:
        boundaries.append(
            boundaries[-1] + max(
                minimum_shot,
                fnum(row.get("duration_sec"), minimum_shot),
            )
        )

    snapped = list(boundaries)
    changes = []

    for i in range(1, len(boundaries) - 1):
        desired = boundaries[i]
        target, kind, strength = nearest_beat(
            desired,
            beats,
            max_shift,
        )

        lo = snapped[i - 1] + minimum_shot
        hi = boundaries[i + 1] - minimum_shot

        if lo <= target <= hi:
            snapped[i] = target
            if abs(target - desired) >= 0.015:
                changes.append({
                    "cut_index": i,
                    "original_sec": round(desired, 6),
                    "snapped_sec": round(target, 6),
                    "shift_sec": round(target - desired, 6),
                    "target_type": kind,
                    "strength": round(strength, 5),
                })

    output = []
    source_clamped = 0
    gap_count = 0
    overlap_count = 0

    for i, original in enumerate(rows):
        row = dict(original)
        start = snapped[i]
        end = snapped[i + 1]
        duration = max(minimum_shot, end - start)

        source_in = max(0.0, fnum(row.get("source_in_sec"), 0))
        media_duration = fnum(
            row.get("source_media_duration_sec"),
            fnum(
                row.get("media_duration_sec"),
                fnum(row.get("validated_media_duration_sec"), 0),
            ),
        )

        if media_duration > 0:
            max_in = max(0.0, media_duration - duration - 0.10)
            clamped_in = clamp(source_in, 0.0, max_in)
            if abs(clamped_in - source_in) > 0.001:
                source_clamped += 1
            source_in = clamped_in

        row.update({
            "index": i + 1,
            "timeline_start_sec": round(start, 6),
            "timeline_end_sec": round(end, 6),
            "duration_sec": round(duration, 6),
            "source_in_sec": round(source_in, 6),
            "source_out_sec": round(source_in + duration, 6),
            "source_duration_sec": round(duration, 6),
            "director_optimized_133": True,
        })
        output.append(row)

    for previous, current in zip(output, output[1:]):
        delta = fnum(current.get("timeline_start_sec"), 0) - fnum(previous.get("timeline_end_sec"), 0)
        if delta > 0.001:
            gap_count += 1
        elif delta < -0.001:
            overlap_count += 1

    return output, {
        "snapped_cut_count": len(changes),
        "beat_snap_changes": changes,
        "source_clamped_count": source_clamped,
        "gap_count": gap_count,
        "overlap_count": overlap_count,
    }


# ============================================================
# Diagnostics
# ============================================================

def diagnose(rows: list[dict[str, Any]]) -> dict[str, Any]:
    same_camera_runs = []
    same_family_runs = []
    repeated_adjacent_files = 0

    camera_run = 0
    family_run = 0
    previous_camera = None
    previous_family = None
    previous_file = None

    for row in rows:
        camera = str(row.get("_camera") or row.get("camera_group") or "CAM_UNKNOWN")
        family = str(row.get("_semantic_family") or semantic_family(row.get("scene_tag")))
        file_path = norm_path(row.get("file"))

        if camera == previous_camera:
            camera_run += 1
        else:
            if camera_run:
                same_camera_runs.append(camera_run)
            camera_run = 1

        if family == previous_family:
            family_run += 1
        else:
            if family_run:
                same_family_runs.append(family_run)
            family_run = 1

        if file_path and file_path == previous_file:
            repeated_adjacent_files += 1

        previous_camera = camera
        previous_family = family
        previous_file = file_path

    if camera_run:
        same_camera_runs.append(camera_run)
    if family_run:
        same_family_runs.append(family_run)

    return {
        "max_same_camera_run": max(same_camera_runs + [0]),
        "max_same_family_run": max(same_family_runs + [0]),
        "adjacent_duplicate_file_count": repeated_adjacent_files,
        "camera_counts": dict(
            Counter(
                str(row.get("_camera") or row.get("camera_group") or "CAM_UNKNOWN")
                for row in rows
            )
        ),
        "section_counts": dict(
            Counter(
                str(row.get("_section") or row.get("music_section") or "story")
                for row in rows
            )
        ),
    }


def clean_internal_fields(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        copy = {
            key: value
            for key, value in row.items()
            if not key.startswith("_")
        }
        output.append(copy)
    return output


# ============================================================
# Optional export orchestration
# ============================================================

def run_exports(
    project: Path,
    excludes: list[str],
    music_file: str,
    preset: str,
    sequence_fps: float,
    default_source_fps: float,
) -> dict[str, Any]:
    scripts_dir = Path(__file__).resolve().parent
    root_dir = scripts_dir.parent

    replacer = scripts_dir / "replace_bad_source_and_export_128e.py"
    injector = scripts_dir / "inject_music_into_fixed_xml_128f.py"

    results: dict[str, Any] = {
        "128e_run": False,
        "128f_run": False,
    }

    if not replacer.exists():
        results["128e_error"] = f"Missing {replacer.name}"
        return results

    command = [
        os.sys.executable,
        str(replacer),
        "--project", str(project),
        "--preset", preset,
        "--sequence-fps", str(sequence_fps),
        "--default-source-fps", str(default_source_fps),
        "--no-open",
    ]

    for filename in excludes:
        command.extend(["--exclude", filename])

    run_128e = subprocess.run(
        command,
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )

    results["128e_run"] = True
    results["128e_returncode"] = run_128e.returncode
    results["128e_stdout"] = run_128e.stdout
    results["128e_stderr"] = run_128e.stderr

    if run_128e.returncode != 0:
        return results

    if not music_file:
        results["128f_error"] = "No music file found."
        return results

    if not injector.exists():
        results["128f_error"] = f"Missing {injector.name}"
        return results

    run_128f = subprocess.run(
        [
            os.sys.executable,
            str(injector),
            "--project", str(project),
            "--music", music_file,
            "--no-open",
        ],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )

    results["128f_run"] = True
    results["128f_returncode"] = run_128f.returncode
    results["128f_stdout"] = run_128f.stdout
    results["128f_stderr"] = run_128f.stderr

    return results


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="133 Director Timeline Optimizer."
    )
    parser.add_argument(
        "--project",
        default="D:/STT Projects/Wedding_Test_001",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=4,
    )
    parser.add_argument(
        "--max-beat-shift",
        type=float,
        default=0.18,
    )
    parser.add_argument(
        "--min-shot",
        type=float,
        default=0.45,
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--export",
        action="store_true",
    )
    parser.add_argument(
        "--music",
        default="",
    )
    parser.add_argument(
        "--preset",
        default="horizontal_4k",
    )
    parser.add_argument(
        "--sequence-fps",
        type=float,
        default=30.0,
    )
    parser.add_argument(
        "--default-source-fps",
        type=float,
        default=50.0,
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
    )
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = (
        project
        / "exports"
        / f"director_timeline_optimizer_133_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    input_path, timeline = locate_timeline(project)
    rows = list(timeline.get("items") or [])

    if not input_path or not rows:
        result = {
            "ok": False,
            "error": "NO_TIMELINE",
        }
        write_json(report_dir / "FINAL_133_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    beats = load_beats(project)
    music = read_json(project / "stt_music_structure_climax_v3.json")

    enriched = enrich_rows(project, rows)
    before_diagnostics = diagnose(enriched)

    ordered, order_report = optimize_order(
        enriched,
        max(2, min(6, args.window_size)),
    )

    duration_optimized, duration_report = optimize_durations(ordered)

    repaired, repair_report = rebuild_and_snap(
        duration_optimized,
        beats,
        max_shift=max(0.0, args.max_beat_shift),
        minimum_shot=max(0.2, args.min_shot),
    )

    after_diagnostics = diagnose(repaired)
    cleaned = clean_internal_fields(repaired)

    output_data = dict(timeline)
    output_data.update({
        "ok": True,
        "module_before_133": timeline.get("module"),
        "module": "133_director_timeline_optimizer",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "input_timeline": str(input_path),
        "timeline_count": len(cleaned),
        "timeline_seconds": round(timeline_duration(cleaned), 6),
        "duration_stats": duration_stats(cleaned),
        "director_summary": {
            "before": before_diagnostics,
            "after": after_diagnostics,
            **order_report,
            **duration_report,
            **{
                key: value
                for key, value in repair_report.items()
                if key != "beat_snap_changes"
            },
        },
        "items": cleaned,
    })

    output_path = project / "stt_director_optimized_timeline_v1.json"
    canonical_path = project / "stt_multicam_directed_timeline_v1.json"
    backup_path = project / "stt_multicam_directed_before_133_backup.json"

    if canonical_path.exists() and not backup_path.exists():
        shutil.copy2(canonical_path, backup_path)

    write_json(output_path, output_data)
    write_json(canonical_path, output_data)
    write_json(report_dir / output_path.name, output_data)
    write_json(
        report_dir / "BEAT_SNAP_CHANGES_133.json",
        {
            "items": repair_report.get("beat_snap_changes") or [],
        },
    )

    music_file = args.music or str(music.get("music_file") or "")
    export_results = {}

    if args.export:
        excludes = list(args.exclude)
        if not excludes:
            excludes = ["STT0043.MP4"]

        export_results = run_exports(
            project,
            excludes,
            music_file,
            args.preset,
            args.sequence_fps,
            args.default_source_fps,
        )

    result = {
        "ok": True,
        "report_dir": str(report_dir),
        "input_timeline": str(input_path),
        "output_timeline": str(output_path),
        "canonical_timeline": str(canonical_path),
        "backup_timeline": str(backup_path),
        "timeline_count": len(cleaned),
        "timeline_seconds": round(timeline_duration(cleaned), 3),
        "duration_stats": duration_stats(cleaned),
        "reordered_count": order_report["reordered_count"],
        "duration_changed_count": duration_report["duration_changed_count"],
        "snapped_cut_count": repair_report["snapped_cut_count"],
        "source_clamped_count": repair_report["source_clamped_count"],
        "gap_count": repair_report["gap_count"],
        "overlap_count": repair_report["overlap_count"],
        "max_same_camera_run_before": before_diagnostics["max_same_camera_run"],
        "max_same_camera_run_after": after_diagnostics["max_same_camera_run"],
        "adjacent_duplicate_before": before_diagnostics["adjacent_duplicate_file_count"],
        "adjacent_duplicate_after": after_diagnostics["adjacent_duplicate_file_count"],
        "export_requested": bool(args.export),
        "export_results": export_results,
        "fix": "133_director_timeline_optimizer",
    }

    write_json(report_dir / "FINAL_133_REPORT.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
