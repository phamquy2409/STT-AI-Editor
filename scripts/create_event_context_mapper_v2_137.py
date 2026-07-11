from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_137_139_common import *


def normalize_order(items: list[dict[str, Any]]) -> None:
    by_camera: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        by_camera[camera_of(row)].append(row)

    for camera, rows in by_camera.items():
        rows.sort(key=lambda row: source_number(row))
        count = len(rows)
        for index, row in enumerate(rows):
            row["_source_order_norm"] = (
                index / max(1, count - 1)
            )
            row["_camera_local_index"] = index


def build_used_anchors(
    all_items: list[dict[str, Any]],
    timeline_rows: list[dict[str, Any]],
    total_seconds: float,
) -> dict[str, list[tuple[float, float, str, str]]]:
    item_by_path = {
        norm_path(row.get("file")): row
        for row in all_items
        if norm_path(row.get("file"))
    }

    anchors: dict[str, list[tuple[float, float, str, str]]] = defaultdict(list)

    for timeline_row in timeline_rows:
        path_key = norm_path(timeline_row.get("file"))
        source_row = item_by_path.get(path_key)
        if not source_row:
            continue

        camera = camera_of(source_row)
        order_norm = fnum(source_row.get("_source_order_norm"), 0)
        story_pos = timeline_position(timeline_row, total_seconds)
        section = section_name(timeline_row)
        family = semantic_family(str(timeline_row.get("scene_tag") or "other"))

        anchors[camera].append((
            order_norm,
            story_pos,
            section,
            family,
        ))

    for camera in anchors:
        anchors[camera].sort(key=lambda value: value[0])

    return anchors


def interpolate_story_position(
    order_norm: float,
    anchors: list[tuple[float, float, str, str]],
) -> float:
    if not anchors:
        return order_norm

    xs = [value[0] for value in anchors]
    index = bisect.bisect_left(xs, order_norm)

    if index <= 0:
        return anchors[0][1]
    if index >= len(anchors):
        return anchors[-1][1]

    left = anchors[index - 1]
    right = anchors[index]

    if abs(right[0] - left[0]) < 1e-6:
        return (left[1] + right[1]) / 2

    ratio = (order_norm - left[0]) / (right[0] - left[0])
    return left[1] + (right[1] - left[1]) * ratio


def nearest_anchor_labels(
    order_norm: float,
    anchors: list[tuple[float, float, str, str]],
    fallback_section: str,
    fallback_family: str,
) -> tuple[str, str]:
    if not anchors:
        return fallback_section, fallback_family

    nearest = min(
        anchors,
        key=lambda value: abs(value[0] - order_norm),
    )
    return nearest[2], nearest[3]


def event_key(
    row: dict[str, Any],
    bin_width: float,
) -> tuple[str, str, int]:
    section = str(row.get("_estimated_section") or "story")
    family = str(row.get("_estimated_family") or "other")
    story_pos = fnum(row.get("_estimated_story_pos"), 0)
    bin_index = int(round(story_pos / max(0.005, bin_width)))
    return section, family, bin_index


def merge_sparse_neighbor_events(
    groups: dict[tuple[str, str, int], list[dict[str, Any]]],
) -> dict[tuple[str, str, int], list[dict[str, Any]]]:
    keys = sorted(groups.keys(), key=lambda key: (key[0], key[1], key[2]))
    output = {key: list(groups[key]) for key in keys}

    for key in keys:
        rows = output.get(key, [])
        if not rows:
            continue

        cameras = {camera_of(row) for row in rows}
        if len(cameras) >= 2:
            continue

        section, family, index = key
        candidates = [
            (section, family, index - 1),
            (section, family, index + 1),
        ]

        best_key = None
        for candidate_key in candidates:
            candidate_rows = output.get(candidate_key, [])
            if not candidate_rows:
                continue

            candidate_cameras = {camera_of(row) for row in candidate_rows}
            if cameras.isdisjoint(candidate_cameras):
                best_key = candidate_key
                break

        if best_key is None:
            continue

        output[best_key].extend(rows)
        output[key] = []

    return {
        key: rows
        for key, rows in output.items()
        if rows
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="137 Event Context Mapper V2."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--event-bin-width", type=float, default=0.035)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "event_context_mapper_v2_137")

    camera_map = read_json(project / "stt_camera_source_map_v1.json")
    items = [dict(row) for row in (camera_map.get("items") or [])]
    timeline_path, timeline = locate_final_timeline(project)
    timeline_rows = [dict(row) for row in (timeline.get("items") or [])]

    if not items:
        result = {
            "ok": False,
            "error": "NO_CAMERA_SOURCE_MAP",
            "expected": str(project / "stt_camera_source_map_v1.json"),
        }
        write_json(report_dir / "FINAL_137_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    if not timeline_rows:
        result = {
            "ok": False,
            "error": "NO_FINAL_TIMELINE",
        }
        write_json(report_dir / "FINAL_137_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    total_seconds = max(
        [fnum(row.get("timeline_end_sec"), 0) for row in timeline_rows] + [210.0]
    )

    for index, row in enumerate(items):
        row["camera_group"] = camera_of(row)
        row["_source_order"] = source_number(row, index)
        row["_original_index"] = index

    normalize_order(items)
    anchors = build_used_anchors(items, timeline_rows, total_seconds)

    for row in items:
        camera = camera_of(row)
        order_norm = fnum(row.get("_source_order_norm"), 0)
        story_pos = interpolate_story_position(
            order_norm,
            anchors.get(camera, []),
        )

        fallback_section = section_name(row)
        fallback_family = semantic_family(str(row.get("scene_tag") or "other"))
        estimated_section, nearest_family = nearest_anchor_labels(
            order_norm,
            anchors.get(camera, []),
            fallback_section,
            fallback_family,
        )

        real_family = semantic_family(str(row.get("scene_tag") or "other"))
        estimated_family = (
            real_family
            if real_family != "other"
            else nearest_family
        )

        row["_estimated_story_pos"] = round(story_pos, 6)
        row["_estimated_section"] = estimated_section
        row["_estimated_family"] = estimated_family

    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        groups[event_key(row, args.event_bin_width)].append(row)

    groups = merge_sparse_neighbor_events(groups)

    events = []
    item_output = []
    multi_camera_count = 0

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: (
            min(fnum(row.get("_estimated_story_pos"), 0) for row in item[1]),
            item[0][0],
            item[0][1],
        ),
    )

    for event_index, (key, rows) in enumerate(ordered_groups, 1):
        section, family, _ = key
        event_id = f"EVT137_{event_index:04d}"
        cameras = sorted({camera_of(row) for row in rows})
        if len(cameras) >= 2:
            multi_camera_count += 1

        rows.sort(key=lambda row: (
            fnum(row.get("_estimated_story_pos"), 0),
            camera_of(row),
            source_number(row),
        ))

        event_items = []
        for row in rows:
            clean = {
                key_name: value
                for key_name, value in row.items()
                if not key_name.startswith("_")
            }
            clean.update({
                "event_id_v2": event_id,
                "event_section_v2": section,
                "event_family_v2": family,
                "estimated_story_position_v2": round(
                    fnum(row.get("_estimated_story_pos"), 0),
                    6,
                ),
            })
            event_items.append(clean)
            item_output.append(clean)

        events.append({
            "event_id": event_id,
            "section": section,
            "semantic_family": family,
            "story_position": round(
                sum(
                    fnum(row.get("_estimated_story_pos"), 0)
                    for row in rows
                ) / max(1, len(rows)),
                6,
            ),
            "camera_count": len(cameras),
            "cameras": cameras,
            "item_count": len(rows),
            "multi_camera": len(cameras) >= 2,
            "items": event_items,
        })

    data = {
        "ok": True,
        "module": "137_event_context_mapper_v2",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "input_timeline": str(timeline_path),
        "file_count": len(item_output),
        "camera_count": len({camera_of(row) for row in item_output}),
        "event_count": len(events),
        "multi_camera_event_count": multi_camera_count,
        "event_bin_width": args.event_bin_width,
        "camera_anchor_counts": {
            camera: len(values)
            for camera, values in anchors.items()
        },
        "events": events,
        "items": item_output,
    }

    output_path = project / "stt_event_context_map_v2.json"
    write_json(output_path, data)
    write_json(report_dir / output_path.name, data)

    summary = {
        "ok": True,
        "report_dir": str(report_dir),
        "output_map": str(output_path),
        "file_count": len(item_output),
        "event_count": len(events),
        "multi_camera_event_count": multi_camera_count,
        "camera_anchor_counts": data["camera_anchor_counts"],
        "fix": "137_event_context_mapper_v2",
    }
    write_json(report_dir / "FINAL_137_REPORT.json", summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
