from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from multicam_common import *

def main() -> None:
    p = argparse.ArgumentParser(description="129 Camera Source Map.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "camera_source_map_129")
    rows = current_source_rows(project)

    if not rows:
        res = {"ok": False, "error": "NO_SOURCE_ROWS"}
        write_json(out / "CAMERA_MAP_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    q_by_path, q_by_name = load_quality(project)
    b_by_path, b_by_name = load_beauty(project)

    items = []
    for i, r in enumerate(rows):
        path = str(r.get("file") or "")
        if not path or not Path(path).exists():
            continue
        name = str(r.get("filename") or Path(path).name)
        pkey = norm_path(path)
        q = q_by_path.get(pkey)
        if not q:
            qs = q_by_name.get(name.lower(), [])
            q = qs[0] if qs else {}
        b = b_by_path.get(pkey) or b_by_name.get(name.lower()) or {}

        group = camera_group(name, path)
        tag = str(r.get("scene_tag") or "other")
        best_in = fnum(
            r.get("source_in_sec"),
            fnum(b.get("best_source_in_sec"), fnum(q.get("best_center_sec"), 0))
        )
        scale = face_scale(path, best_in)

        items.append({
            "index": len(items),
            "filename": name,
            "file": path,
            "camera_group": group,
            "is_drone": group == "DRONE",
            "scene_tag": tag,
            "semantic_family": semantic_family(tag),
            "source_order": inum(r.get("_source_order"), i),
            "creation_time": media_creation_time(path),
            "duration_sec": fnum(r.get("media_duration_sec"), fnum(q.get("duration_sec"), media_duration(path))),
            "quality_score": fnum(
                r.get("moment_quality_score"),
                fnum(q.get("best_quality_score"), fnum(q.get("average_quality_score"), 45))
            ),
            "beauty_score": fnum(r.get("beauty_score"), fnum(b.get("beauty_score"), 55)),
            "best_source_in_sec": best_in,
            **scale,
        })

    counts = Counter(x["camera_group"] for x in items)
    scale_counts = Counter(x["shot_scale"] for x in items)
    data = {
        "ok": True,
        "module": "129_camera_source_map",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "file_count": len(items),
        "camera_count": len(counts),
        "camera_counts": dict(counts),
        "shot_scale_counts": dict(scale_counts),
        "drone_count": sum(1 for x in items if x.get("is_drone")),
        "items": items,
    }

    write_json(project / "stt_camera_source_map_v1.json", data)
    write_json(out / "stt_camera_source_map_v1.json", data)
    write_csv(out / "CAMERA_SOURCE_MAP.csv", items, [
        "index", "camera_group", "is_drone", "shot_scale", "face_count", "face_ratio",
        "scene_tag", "semantic_family", "filename", "source_order", "creation_time",
        "duration_sec", "quality_score", "beauty_score", "best_source_in_sec", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "file_count": len(items),
        "camera_count": len(counts),
        "camera_counts": dict(counts),
        "shot_scale_counts": dict(scale_counts),
        "drone_count": data["drone_count"],
        "fix": "129_camera_source_map",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
