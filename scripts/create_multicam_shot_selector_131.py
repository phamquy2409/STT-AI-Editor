from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from multicam_common import *

def build_event_index(events: list[dict[str, Any]]):
    by_path = {}
    event_items = {}
    for event in events:
        eid = str(event.get("event_id"))
        rows = list(event.get("items") or [])
        event_items[eid] = rows
        for row in rows:
            p = norm_path(row.get("file"))
            if p:
                by_path[p] = eid
    return by_path, event_items

def replacement_score(
    cand: dict[str, Any],
    base: dict[str, Any],
    prev_camera: str,
    prev_scale: str,
    current_run: int,
) -> float:
    score = fnum(cand.get("quality_score"), 45) * 0.48 + fnum(cand.get("beauty_score"), 55) * 0.42
    tag = str(cand.get("scene_tag") or "other")
    base_tag = str(base.get("scene_tag") or "other")
    family = str(cand.get("semantic_family") or "other")
    base_family = semantic_family(base_tag)
    cam = str(cand.get("camera_group") or "CAM_UNKNOWN")
    scale = str(cand.get("shot_scale") or "unknown")

    if tag == base_tag:
        score += 24
    elif family == base_family:
        score += 12
    else:
        score -= 28

    if cam != prev_camera:
        score += 7
    elif current_run >= 3:
        score -= 22

    # Prefer meaningful scale progression, not same framing repeatedly.
    if prev_scale in {"wide", "wide_or_detail"} and scale in {"medium", "close"}:
        score += 9
    elif prev_scale == "medium" and scale in {"close", "wide"}:
        score += 8
    elif prev_scale == "close" and scale in {"medium", "wide"}:
        score += 8
    elif scale == prev_scale and scale not in {"unknown"}:
        score -= 6

    if cand.get("is_drone"):
        section = str(base.get("music_section") or base.get("story_part") or "")
        if section in {"intro", "ending", "release"}:
            score += 18
        else:
            score -= 35

    return score

def main() -> None:
    p = argparse.ArgumentParser(description="131 Multi-camera Shot Selector.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--replace-threshold", type=float, default=12.0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "multicam_shot_selector_131")
    timeline_data = current_timeline(project)
    timeline = list(timeline_data.get("items") or [])
    events_data = read_json(project / "stt_multicam_event_groups_v1.json")
    events = list(events_data.get("events") or [])

    if not timeline:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 127 first."}
        write_json(out / "SELECTOR_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not events:
        res = {"ok": False, "error": "NO_EVENT_GROUPS", "message": "Run 130 first."}
        write_json(out / "SELECTOR_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    by_path, event_items = build_event_index(events)
    selected = []
    used_paths = set()
    prev_camera = ""
    prev_scale = ""
    camera_run = 0
    replaced_count = 0
    kept_count = 0

    for i, base in enumerate(timeline):
        row = dict(base)
        base_path = norm_path(row.get("file"))
        event_id = by_path.get(base_path, "")
        candidates = list(event_items.get(event_id, [])) if event_id else []

        # Preserve baseline as default.
        chosen = None
        base_camera = camera_group(str(row.get("filename") or Path(base_path).name), str(row.get("file") or ""))
        base_scale = str(row.get("shot_scale") or "unknown")
        base_score = fnum(row.get("quality_window_score"), fnum(row.get("moment_quality_score"), 45))
        if base_camera == prev_camera:
            next_run = camera_run + 1
        else:
            next_run = 1

        ranked = []
        for cand in candidates:
            cp = norm_path(cand.get("file"))
            if not cp or cp in used_paths:
                continue
            score = replacement_score(cand, row, prev_camera, prev_scale, camera_run)
            ranked.append((score, cand))

        if ranked:
            ranked.sort(key=lambda x: x[0], reverse=True)
            best_score, best = ranked[0]
            baseline_compare = base_score + fnum(row.get("beauty_score"), 55) * 0.25
            if best_score >= baseline_compare + a.replace_threshold:
                chosen = best

        if chosen:
            original_file = str(row.get("file") or "")
            duration = fnum(row.get("duration_sec"), 0)
            src_in = fnum(chosen.get("best_source_in_sec"), 0)
            media_dur = fnum(chosen.get("duration_sec"), media_duration(str(chosen.get("file") or "")))
            if media_dur > 0:
                src_in = clamp(src_in, 0, max(0, media_dur - duration))
            row.update({
                "original_file_before_multicam": original_file,
                "original_filename_before_multicam": row.get("filename"),
                "file": chosen.get("file"),
                "filename": chosen.get("filename"),
                "scene_tag": chosen.get("scene_tag"),
                "camera_group": chosen.get("camera_group"),
                "shot_scale": chosen.get("shot_scale"),
                "face_count": chosen.get("face_count"),
                "face_ratio": chosen.get("face_ratio"),
                "source_in_sec": round(src_in, 4),
                "source_out_sec": round(src_in + duration, 4),
                "source_duration_sec": round(duration, 4),
                "multicam_event_id": event_id,
                "multicam_reason": "better_angle_same_event",
                "multicam_replaced": True,
            })
            replaced_count += 1
            current_camera = str(chosen.get("camera_group") or "CAM_UNKNOWN")
            current_scale = str(chosen.get("shot_scale") or "unknown")
        else:
            row["camera_group"] = base_camera
            row["shot_scale"] = base_scale
            row["multicam_event_id"] = event_id
            row["multicam_reason"] = "keep_taste_baseline"
            row["multicam_replaced"] = False
            kept_count += 1
            current_camera = base_camera
            current_scale = base_scale

        if current_camera == prev_camera:
            camera_run += 1
        else:
            camera_run = 1
        prev_camera = current_camera
        prev_scale = current_scale
        used_paths.add(norm_path(row.get("file")))
        selected.append(row)

    data = dict(timeline_data)
    data["module_before_131"] = timeline_data.get("module")
    data["module"] = "131_multicam_shot_selector"
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    data["items"] = selected
    data["timeline_count"] = len(selected)
    data["duration_stats"] = duration_stats(selected)
    data["multicam_summary"] = {
        "replaced_count": replaced_count,
        "kept_count": kept_count,
        "camera_counts": dict(Counter(str(x.get("camera_group") or "CAM_UNKNOWN") for x in selected)),
        "scale_counts": dict(Counter(str(x.get("shot_scale") or "unknown") for x in selected)),
    }

    write_json(project / "stt_multicam_selected_timeline_v1.json", data)
    write_json(out / "stt_multicam_selected_timeline_v1.json", data)
    write_csv(out / "MULTICAM_SELECTED_TIMELINE.csv", selected, [
        "index", "music_section", "story_part", "multicam_event_id",
        "camera_group", "shot_scale", "multicam_replaced", "multicam_reason",
        "filename", "original_filename_before_multicam",
        "timeline_start_sec", "duration_sec", "source_in_sec",
        "scene_tag", "slow_recommended", "file", "original_file_before_multicam"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(selected),
        "replaced_count": replaced_count,
        "kept_count": kept_count,
        "camera_counts": data["multicam_summary"]["camera_counts"],
        "scale_counts": data["multicam_summary"]["scale_counts"],
        "fix": "131_multicam_shot_selector",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
