from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from multicam_common import *

def cluster_by_time(items: list[dict[str, Any]], gap_sec: float) -> list[list[dict[str, Any]]]:
    valid = [x for x in items if fnum(x.get("creation_time"), 0) > 0]
    if len(valid) < max(3, len(items) // 3):
        return []

    sorted_items = sorted(items, key=lambda x: (fnum(x.get("creation_time"), 0), inum(x.get("source_order"), 0)))
    groups = []
    current = []
    last_time = None
    last_family = None

    for item in sorted_items:
        t = fnum(item.get("creation_time"), 0)
        family = str(item.get("semantic_family") or "other")
        split = False
        if last_time is not None:
            if t - last_time > gap_sec:
                split = True
            elif family != last_family and family not in {"other", "detail"} and last_family not in {"other", "detail"}:
                if t - last_time > min(20.0, gap_sec * 0.35):
                    split = True
        if split and current:
            groups.append(current)
            current = []
        current.append(item)
        last_time = t
        last_family = family

    if current:
        groups.append(current)
    return groups

def cluster_by_progress(items: list[dict[str, Any]], bucket_size: int) -> list[list[dict[str, Any]]]:
    by_camera = defaultdict(list)
    for item in items:
        by_camera[str(item.get("camera_group") or "CAM_UNKNOWN")].append(item)

    normalized = []
    for cam, rows in by_camera.items():
        rows = sorted(rows, key=lambda x: inum(x.get("source_order"), 0))
        n = max(1, len(rows))
        for i, row in enumerate(rows):
            copy = dict(row)
            copy["_camera_progress"] = i / n
            normalized.append(copy)

    bucket_count = max(1, math.ceil(len(items) / max(1, bucket_size)))
    groups = [[] for _ in range(bucket_count)]
    for item in normalized:
        idx = min(bucket_count - 1, int(fnum(item.get("_camera_progress"), 0) * bucket_count))
        groups[idx].append(item)

    result = []
    for group in groups:
        if not group:
            continue
        # Split bucket by semantic family when there is a clear family.
        by_family = defaultdict(list)
        for item in group:
            family = str(item.get("semantic_family") or "other")
            by_family[family].append(item)
        meaningful = [(k, v) for k, v in by_family.items() if k not in {"other", "detail"} and len(v) >= 2]
        if meaningful:
            used = set()
            for k, rows in meaningful:
                result.append(rows)
                used.update(id(x) for x in rows)
            leftovers = [x for x in group if id(x) not in used]
            if leftovers:
                result.append(leftovers)
        else:
            result.append(group)
    return result

def main() -> None:
    p = argparse.ArgumentParser(description="130 Multi-camera Event Grouper.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--time-gap-sec", type=float, default=90.0)
    p.add_argument("--fallback-bucket-size", type=int, default=14)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "multicam_event_groups_130")
    camera_map = read_json(project / "stt_camera_source_map_v1.json")
    items = list(camera_map.get("items") or [])

    if not items:
        res = {"ok": False, "error": "NO_CAMERA_SOURCE_MAP", "message": "Run 129 first."}
        write_json(out / "EVENT_GROUP_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    groups = cluster_by_time(items, a.time_gap_sec)
    method = "creation_time"
    if not groups or len(groups) <= 1:
        groups = cluster_by_progress(items, a.fallback_bucket_size)
        method = "camera_progress_semantic"

    events = []
    membership = []
    for i, rows in enumerate(groups, 1):
        cameras = Counter(str(x.get("camera_group") or "CAM_UNKNOWN") for x in rows)
        families = Counter(str(x.get("semantic_family") or "other") for x in rows)
        tags = Counter(str(x.get("scene_tag") or "other") for x in rows)
        event = {
            "event_id": f"EVENT_{i:03d}",
            "group_method": method,
            "clip_count": len(rows),
            "camera_count": len(cameras),
            "camera_counts": dict(cameras),
            "semantic_families": dict(families),
            "scene_tags": dict(tags),
            "dominant_family": families.most_common(1)[0][0] if families else "other",
            "start_creation_time": min([fnum(x.get("creation_time"), 0) for x in rows] + [0]),
            "end_creation_time": max([fnum(x.get("creation_time"), 0) for x in rows] + [0]),
            "items": rows,
        }
        events.append(event)
        for row in rows:
            membership.append({
                "event_id": event["event_id"],
                "camera_group": row.get("camera_group"),
                "scene_tag": row.get("scene_tag"),
                "semantic_family": row.get("semantic_family"),
                "shot_scale": row.get("shot_scale"),
                "filename": row.get("filename"),
                "file": row.get("file"),
            })

    data = {
        "ok": True,
        "module": "130_multicam_event_grouper",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "group_method": method,
        "event_count": len(events),
        "multi_camera_event_count": sum(1 for x in events if x.get("camera_count", 0) >= 2),
        "events": events,
    }

    write_json(project / "stt_multicam_event_groups_v1.json", data)
    write_json(out / "stt_multicam_event_groups_v1.json", data)
    write_csv(out / "MULTICAM_EVENT_MEMBERSHIP.csv", membership, [
        "event_id", "camera_group", "scene_tag", "semantic_family",
        "shot_scale", "filename", "file"
    ])
    write_csv(out / "MULTICAM_EVENT_SUMMARY.csv", [
        {
            "event_id": x["event_id"],
            "clip_count": x["clip_count"],
            "camera_count": x["camera_count"],
            "dominant_family": x["dominant_family"],
            "camera_counts": json.dumps(x["camera_counts"], ensure_ascii=False),
            "scene_tags": json.dumps(x["scene_tags"], ensure_ascii=False),
        } for x in events
    ], ["event_id", "clip_count", "camera_count", "dominant_family", "camera_counts", "scene_tags"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "group_method": method,
        "event_count": len(events),
        "multi_camera_event_count": data["multi_camera_event_count"],
        "fix": "130_multicam_event_grouper",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
