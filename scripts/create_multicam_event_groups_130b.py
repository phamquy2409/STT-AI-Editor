from __future__ import annotations
import argparse, json, math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from safe_multicam_common import *

def main():
    p = argparse.ArgumentParser(description="130B safe cross-camera progress event grouper")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--event-count", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "safe_multicam_event_groups_130b")
    camera_map = read_json(project / "stt_camera_source_map_v1.json")
    items = list(camera_map.get("items") or [])
    if not items:
        res = {"ok": False, "error": "NO_CAMERA_SOURCE_MAP", "message": "Run 129 first."}
        write_json(out / "ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    by_camera = defaultdict(list)
    for item in items:
        by_camera[str(item.get("camera_group") or "CAM_UNKNOWN")].append(dict(item))

    cameras = sorted(by_camera)
    camera_count = max(1, len(cameras))
    if a.event_count > 0:
        event_count = a.event_count
    else:
        event_count = int(round(len(items) / max(1, camera_count * 5)))
        event_count = max(14, min(30, event_count))

    normalized = []
    for cam, rows in by_camera.items():
        rows.sort(key=lambda x: inum(x.get("source_order"), 0))
        denom = max(1, len(rows) - 1)
        for i, row in enumerate(rows):
            row["camera_progress"] = i / denom
            row["progress_bucket"] = min(event_count - 1, int(row["camera_progress"] * event_count))
            normalized.append(row)

    buckets = defaultdict(list)
    for row in normalized:
        buckets[inum(row.get("progress_bucket"), 0)].append(row)

    events = []
    membership = []
    for bucket in sorted(buckets):
        rows = buckets[bucket]
        cams = Counter(str(x.get("camera_group") or "CAM_UNKNOWN") for x in rows)
        families = Counter(str(x.get("semantic_family") or semantic_family(x.get("scene_tag"))) for x in rows)
        tags = Counter(str(x.get("scene_tag") or "other") for x in rows)
        eid = f"EVENT_{bucket+1:03d}"
        event = {
            "event_id": eid,
            "group_method": "cross_camera_progress_bucket",
            "progress_bucket": bucket,
            "progress_start": round(bucket / event_count, 4),
            "progress_end": round((bucket + 1) / event_count, 4),
            "clip_count": len(rows),
            "camera_count": len(cams),
            "camera_counts": dict(cams),
            "dominant_family": families.most_common(1)[0][0] if families else "other",
            "semantic_families": dict(families),
            "scene_tags": dict(tags),
            "items": rows,
        }
        events.append(event)
        for row in rows:
            membership.append({
                "event_id": eid,
                "camera_group": row.get("camera_group"),
                "camera_progress": round(fnum(row.get("camera_progress"), 0), 4),
                "progress_bucket": bucket,
                "scene_tag": row.get("scene_tag"),
                "semantic_family": row.get("semantic_family"),
                "filename": row.get("filename"),
                "file": row.get("file"),
            })

    data = {
        "ok": True,
        "module": "130b_safe_cross_camera_event_grouper",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "group_method": "cross_camera_progress_bucket",
        "event_count": len(events),
        "multi_camera_event_count": sum(1 for x in events if x["camera_count"] >= 2),
        "camera_count": camera_count,
        "events": events,
    }
    write_json(project / "stt_multicam_event_groups_v1.json", data)
    write_json(project / "stt_multicam_event_groups_130b.json", data)
    write_json(out / "stt_multicam_event_groups_130b.json", data)
    write_csv(out / "EVENT_MEMBERSHIP_130B.csv", membership, [
        "event_id","camera_group","camera_progress","progress_bucket",
        "scene_tag","semantic_family","filename","file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "group_method": data["group_method"],
        "event_count": data["event_count"],
        "multi_camera_event_count": data["multi_camera_event_count"],
        "camera_count": camera_count,
        "fix": "130b_safe_cross_camera_event_grouper"
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
