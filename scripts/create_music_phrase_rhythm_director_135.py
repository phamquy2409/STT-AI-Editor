from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_134_136_common import *


WEIGHT_PATTERNS = {
    "intro": [3.8, 2.8, 4.4, 2.6],
    "story": [2.5, 1.8, 2.8, 2.0, 1.5],
    "build": [2.5, 2.0, 1.6, 1.2, 1.0],
    "pre_climax": [1.4, 1.0, 0.8, 1.2, 0.9],
    "climax": [0.8, 0.9, 1.2, 0.7, 2.8, 0.9, 1.5],
    "release": [2.4, 3.0, 2.0, 2.7],
    "ending": [3.8, 4.8, 3.0, 4.2],
}

MIN_DURATION = {
    "intro": 1.2,
    "story": 0.9,
    "build": 0.7,
    "pre_climax": 0.5,
    "climax": 0.5,
    "release": 1.0,
    "ending": 1.5,
}


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


def load_sections(project: Path, target_seconds: float) -> list[dict[str, Any]]:
    music = read_json(project / "stt_music_structure_climax_v3.json")
    sections = []

    for row in music.get("sections") or []:
        start = fnum(row.get("start_sec"), 0)
        end = min(target_seconds, fnum(row.get("end_sec"), start))
        if end <= start:
            continue
        sections.append({
            "label": section_name({"music_section": row.get("label")}),
            "start_sec": start,
            "end_sec": end,
        })

    if sections:
        sections[0]["start_sec"] = 0.0
        sections[-1]["end_sec"] = target_seconds
        return sections

    fractions = [
        ("intro", 0.00, 0.09),
        ("story", 0.09, 0.34),
        ("build", 0.34, 0.55),
        ("pre_climax", 0.55, 0.64),
        ("climax", 0.64, 0.78),
        ("release", 0.78, 0.91),
        ("ending", 0.91, 1.00),
    ]
    return [
        {
            "label": label,
            "start_sec": target_seconds * a,
            "end_sec": target_seconds * b,
        }
        for label, a, b in fractions
    ]


def nearest_beat(
    desired: float,
    beats: list[dict[str, Any]],
    low: float,
    high: float,
    max_shift: float,
) -> tuple[float, str, float]:
    candidates = []
    for beat in beats:
        sec = fnum(beat.get("time_sec"), -1)
        if sec < low or sec > high:
            continue
        delta = abs(sec - desired)
        if delta <= max_shift:
            strength = fnum(beat.get("strength"), 0.5)
            candidates.append((
                delta - min(0.04, strength * 0.025),
                sec,
                str(beat.get("type") or "beat"),
                strength,
            ))

    if not candidates:
        return desired, "weighted", 0.0

    candidates.sort(key=lambda item: item[0])
    _, sec, kind, strength = candidates[0]
    return sec, kind, strength


def repeat_pattern(pattern: list[float], count: int) -> list[float]:
    return [pattern[i % len(pattern)] for i in range(max(0, count))]


def normalize_weights(
    count: int,
    duration: float,
    section: str,
) -> list[float]:
    if count <= 0:
        return []

    minimum = MIN_DURATION.get(section, 0.8)
    pattern = repeat_pattern(
        WEIGHT_PATTERNS.get(section, WEIGHT_PATTERNS["story"]),
        count,
    )

    total = sum(pattern)
    values = [duration * value / total for value in pattern]

    # Iteratively enforce minimum while preserving total.
    for _ in range(12):
        too_small = [i for i, value in enumerate(values) if value < minimum]
        if not too_small:
            break

        deficit = sum(minimum - values[i] for i in too_small)
        for i in too_small:
            values[i] = minimum

        donors = [i for i, value in enumerate(values) if value > minimum + 0.05]
        donor_room = sum(values[i] - minimum for i in donors)
        if donor_room <= 0:
            break

        for i in donors:
            room = values[i] - minimum
            values[i] -= deficit * (room / donor_room)

    scale = duration / max(0.001, sum(values))
    return [max(0.25, value * scale) for value in values]


def build_exact_intervals(
    section: dict[str, Any],
    count: int,
    beats: list[dict[str, Any]],
    max_shift: float,
) -> list[dict[str, Any]]:
    if count <= 0:
        return []

    label = str(section.get("label") or "story")
    start = fnum(section.get("start_sec"), 0)
    end = fnum(section.get("end_sec"), start)
    duration = max(0.0, end - start)

    weights = normalize_weights(count, duration, label)
    raw_boundaries = [start]
    for value in weights[:-1]:
        raw_boundaries.append(raw_boundaries[-1] + value)
    raw_boundaries.append(end)

    min_duration = MIN_DURATION.get(label, 0.8)
    boundaries = [start]
    snap_meta = []

    for i in range(1, len(raw_boundaries) - 1):
        desired = raw_boundaries[i]
        remaining_slots = count - i
        low = boundaries[-1] + min_duration
        high = end - remaining_slots * min_duration

        snapped, kind, strength = nearest_beat(
            desired,
            beats,
            low,
            high,
            max_shift,
        )
        snapped = clamp(snapped, low, high)
        boundaries.append(snapped)
        snap_meta.append((kind, strength))

    boundaries.append(end)

    intervals = []
    for i in range(count):
        a = boundaries[i]
        b = boundaries[i + 1]
        kind, strength = (
            snap_meta[i - 1] if i > 0 and i - 1 < len(snap_meta)
            else ("section_edge", 1.0)
        )
        intervals.append({
            "section": label,
            "rhythm_mode": label,
            "start_sec": round(a, 6),
            "end_sec": round(b, 6),
            "duration_sec": round(b - a, 6),
            "beats_skipped": 0,
            "end_beat_type": kind,
            "end_beat_strength": round(strength, 4),
        })

    return intervals


def rebalance_counts(
    counts: dict[str, int],
    sections: list[dict[str, Any]],
    total_shots: int,
) -> dict[str, int]:
    labels = [str(section.get("label") or "story") for section in sections]
    output = {label: max(0, counts.get(label, 0)) for label in labels}

    current = sum(output.values())
    if current == total_shots:
        return output

    if current < total_shots:
        order = ["story", "build", "climax", "release", "intro", "ending", "pre_climax"]
        index = 0
        while current < total_shots:
            label = order[index % len(order)]
            if label in output:
                output[label] += 1
                current += 1
            index += 1
    else:
        order = ["release", "story", "build", "pre_climax", "climax", "intro", "ending"]
        index = 0
        while current > total_shots:
            label = order[index % len(order)]
            if label in output and output[label] > 1:
                output[label] -= 1
                current -= 1
            index += 1
            if index > 10000:
                break

    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="135B Safe Music Phrase Director."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--target-seconds", type=float, default=210.0)
    parser.add_argument("--max-beat-shift", type=float, default=0.22)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "safe_music_phrase_director_135b")

    moment = read_json(project / "stt_smart_moment_timeline_v2.json")
    rows = list(moment.get("items") or [])
    if not rows:
        result = {
            "ok": False,
            "error": "NO_134_TIMELINE",
            "message": "Run 134 first.",
        }
        write_json(report_dir / "FINAL_135B_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    target_seconds = args.target_seconds
    beats = load_beats(project)
    sections = load_sections(project, target_seconds)

    available_counts = Counter(section_name(row) for row in rows)
    planned_counts = rebalance_counts(
        dict(available_counts),
        sections,
        len(rows),
    )

    intervals = []
    for section in sections:
        label = str(section.get("label") or "story")
        intervals.extend(
            build_exact_intervals(
                section,
                planned_counts.get(label, 0),
                beats,
                args.max_beat_shift,
            )
        )

    # Exact contiguous timeline.
    cursor = 0.0
    for index, interval in enumerate(intervals, 1):
        duration = fnum(interval.get("duration_sec"), 0)
        interval["index"] = index
        interval["start_sec"] = round(cursor, 6)
        interval["end_sec"] = round(cursor + duration, 6)
        cursor += duration

    if intervals:
        intervals[-1]["end_sec"] = round(target_seconds, 6)
        intervals[-1]["duration_sec"] = round(
            target_seconds - fnum(intervals[-1].get("start_sec"), 0),
            6,
        )
        cursor = target_seconds

    data = {
        "ok": True,
        "module": "135b_safe_music_phrase_director",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "target_seconds": round(target_seconds, 6),
        "source_shot_count": len(rows),
        "interval_count": len(intervals),
        "available_section_counts": dict(available_counts),
        "planned_section_counts": planned_counts,
        "duration_stats": duration_stats(intervals),
        "sections": sections,
        "intervals": intervals,
    }

    output_path = project / "stt_music_phrase_rhythm_v2.json"
    write_json(output_path, data)
    write_json(report_dir / output_path.name, data)

    summary = {
        "ok": True,
        "report_dir": str(report_dir),
        "output_map": str(output_path),
        "target_seconds": round(target_seconds, 3),
        "source_shot_count": len(rows),
        "interval_count": len(intervals),
        "available_section_counts": dict(available_counts),
        "planned_section_counts": planned_counts,
        "duration_stats": duration_stats(intervals),
        "fix": "135b_safe_music_phrase_director",
    }
    write_json(report_dir / "FINAL_135B_REPORT.json", summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
