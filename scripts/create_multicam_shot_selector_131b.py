from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from safe_multicam_common import *

def timeline_input(project):
    for name in [
        "stt_climax_directed_timeline_v1.json",
        "stt_quality_moment_timeline_v1.json",
        "stt_taste_boosted_timeline_v1.json",
        "stt_beat_snapped_beauty_timeline_v1.json",
    ]:
        d = read_json(project / name)
        if d.get("items"):
            return d
    return {}

def build_indices(events):
    by_path = {}
    event_items = {}
    for e in events:
        eid = str(e.get("event_id"))
        rows = list(e.get("items") or [])
        event_items[eid] = rows
        for r in rows:
            p = norm_path(r.get("file"))
            if p:
                by_path[p] = eid
    return by_path, event_items

def score_item(item):
    return fnum(item.get("quality_score"), 45) * 0.58 + fnum(item.get("beauty_score"), 55) * 0.42

def main():
    p = argparse.ArgumentParser(description="131B safe cross-camera selector")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--replace-threshold", type=float, default=18.0)
    p.add_argument("--max-replace-ratio", type=float, default=0.25)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "safe_multicam_selector_131b")
    tl = timeline_input(project)
    rows = [dict(x) for x in (tl.get("items") or [])]
    events = list(read_json(project / "stt_multicam_event_groups_v1.json").get("events") or [])
    camera_map = list(read_json(project / "stt_camera_source_map_v1.json").get("items") or [])

    if not rows or not events:
        res = {"ok": False, "error": "MISSING_TIMELINE_OR_EVENTS"}
        write_json(out / "ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    meta_by_path = {norm_path(x.get("file")): x for x in camera_map}
    event_by_path, event_items = build_indices(events)

    max_replacements = max(0, int(len(rows) * clamp(a.max_replace_ratio, 0.0, 0.5)))
    replaced = 0
    used_candidate_paths = set()
    output = []
    prev_camera = ""
    camera_run = 0

    for base in rows:
        row = dict(base)
        base_path = norm_path(row.get("file"))
        base_meta = meta_by_path.get(base_path, {})
        base_camera = str(base_meta.get("camera_group") or row.get("camera_group") or "CAM_UNKNOWN")
        base_tag = str(row.get("scene_tag") or base_meta.get("scene_tag") or "other")
        base_family = semantic_family(base_tag)
        base_score = score_item(base_meta) if base_meta else (
            fnum(row.get("quality_window_score"), 45) * 0.58 +
            fnum(row.get("beauty_score"), 55) * 0.42
        )
        eid = event_by_path.get(base_path, "")
        candidates = []

        if eid and replaced < max_replacements:
            event = next((x for x in events if str(x.get("event_id")) == eid), {})
            if inum(event.get("camera_count"), 0) >= 2:
                for cand in event_items.get(eid, []):
                    cp = norm_path(cand.get("file"))
                    cam = str(cand.get("camera_group") or "CAM_UNKNOWN")
                    tag = str(cand.get("scene_tag") or "other")
                    fam = str(cand.get("semantic_family") or semantic_family(tag))

                    if not cp or cp == base_path or cp in used_candidate_paths:
                        continue
                    if cam == base_camera:
                        continue
                    if not (tag == base_tag or fam == base_family):
                        continue

                    s = score_item(cand)
                    if tag == base_tag:
                        s += 10
                    elif fam == base_family:
                        s += 4
                    if base_camera == prev_camera and camera_run >= 3:
                        s += 7
                    if cand.get("is_drone") and str(row.get("music_section") or "") not in {"intro","release","ending"}:
                        s -= 30
                    candidates.append((s, cand))

        chosen = None
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best = candidates[0]
            threshold = a.replace_threshold
            if row.get("is_main_climax_shot") or row.get("slow_recommended"):
                threshold += 10
            if best_score >= base_score + threshold:
                chosen = best

        if chosen:
            duration = fnum(row.get("duration_sec"), 0)
            src_in = fnum(chosen.get("best_source_in_sec"), 0)
            media_dur = fnum(chosen.get("duration_sec"), 0)
            if media_dur > 0:
                src_in = clamp(src_in, 0, max(0, media_dur - duration))
            row.update({
                "original_file_before_multicam": row.get("file"),
                "original_filename_before_multicam": row.get("filename"),
                "file": chosen.get("file"),
                "filename": chosen.get("filename"),
                "scene_tag": chosen.get("scene_tag"),
                "camera_group": chosen.get("camera_group"),
                "shot_scale": chosen.get("shot_scale"),
                "source_in_sec": round(src_in, 4),
                "source_out_sec": round(src_in + duration, 4),
                "source_duration_sec": round(duration, 4),
                "multicam_event_id": eid,
                "multicam_replaced": True,
                "multicam_reason": "same_event_other_camera_clearly_better",
            })
            replaced += 1
            used_candidate_paths.add(norm_path(chosen.get("file")))
            current_camera = str(chosen.get("camera_group") or "CAM_UNKNOWN")
        else:
            row.update({
                "camera_group": base_camera,
                "multicam_event_id": eid,
                "multicam_replaced": False,
                "multicam_reason": "keep_taste_baseline",
            })
            current_camera = base_camera

        if current_camera == prev_camera:
            camera_run += 1
        else:
            camera_run = 1
        prev_camera = current_camera
        output.append(row)

    result = dict(tl)
    result["module_before_131b"] = tl.get("module")
    result["module"] = "131b_safe_cross_camera_selector"
    result["updated_at"] = datetime.now().isoformat(timespec="seconds")
    result["items"] = output
    result["timeline_count"] = len(output)
    result["multicam_summary"] = {
        "replaced_count": replaced,
        "kept_count": len(output) - replaced,
        "max_replacements": max_replacements,
        "replace_ratio": round(replaced / max(1, len(output)), 4),
        "camera_counts": dict(Counter(str(x.get("camera_group") or "CAM_UNKNOWN") for x in output)),
    }

    write_json(project / "stt_multicam_selected_timeline_v1.json", result)
    write_json(out / "stt_multicam_selected_timeline_v1.json", result)
    write_csv(out / "SAFE_MULTICAM_TIMELINE_131B.csv", output, [
        "index","music_section","story_part","multicam_event_id","camera_group",
        "multicam_replaced","multicam_reason","filename",
        "original_filename_before_multicam","timeline_start_sec","duration_sec",
        "source_in_sec","scene_tag","slow_recommended","file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(output),
        "replaced_count": replaced,
        "kept_count": len(output) - replaced,
        "max_replacements": max_replacements,
        "replace_ratio": round(replaced / max(1, len(output)), 4),
        "camera_counts": result["multicam_summary"]["camera_counts"],
        "fix": "131b_safe_cross_camera_selector"
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
