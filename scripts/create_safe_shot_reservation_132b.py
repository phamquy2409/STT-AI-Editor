from __future__ import annotations
import argparse, json
from collections import Counter
from datetime import datetime
from pathlib import Path
from safe_multicam_common import *

def reserve_score(item, role):
    tag = str(item.get("scene_tag") or "other")
    q = fnum(item.get("quality_window_score"), fnum(item.get("moment_quality_score"), 45))
    beauty = fnum(item.get("beauty_score"), 55)
    hero = fnum(item.get("hero_score"), 0)
    score = q * 0.45 + beauty * 0.40 + hero * 0.25
    if role == "hook" and tag in {"decor","detail_beauty","cdcr_portrait","first_look","ending"}:
        score += 20
    if role == "climax" and tag in {"cdcr_portrait","first_look","vow","family_emotion","reception_stage","party","wedding_game"}:
        score += 28
    if role == "ending" and tag in {"ending","cdcr_portrait","first_look","family_emotion"}:
        score += 32
    return score

def mark_best(rows, indices, role, label):
    valid = [i for i in indices if 0 <= i < len(rows)]
    if not valid:
        return None
    idx = max(valid, key=lambda i: reserve_score(rows[i], role))
    rows[idx]["reservation_role"] = label
    if role == "climax":
        rows[idx]["is_main_climax_shot"] = True
        if fnum(rows[idx].get("duration_sec"), 0) >= 3.2:
            rows[idx]["slow_recommended"] = True
            rows[idx]["slow_percent"] = 50
    return idx

def main():
    p = argparse.ArgumentParser(description="132B safe reservation without reordering story")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "safe_shot_reservation_132b")
    data = read_json(project / "stt_multicam_selected_timeline_v1.json")
    rows = [dict(x) for x in (data.get("items") or [])]
    if not rows:
        res = {"ok": False, "error": "NO_SAFE_MULTICAM_TIMELINE"}
        write_json(out / "ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    n = len(rows)
    hook_indices = list(range(0, max(1, round(n * 0.10))))
    climax_indices = [
        i for i, x in enumerate(rows)
        if str(x.get("music_section") or "") == "climax"
    ]
    ending_indices = [
        i for i, x in enumerate(rows)
        if str(x.get("music_section") or "") == "ending"
    ]
    if not climax_indices:
        climax_indices = list(range(round(n * 0.62), min(n, round(n * 0.78))))
    if not ending_indices:
        ending_indices = list(range(max(0, round(n * 0.86)), n))

    hook_idx = mark_best(rows, hook_indices, "hook", "HOOK_BEST_IN_SECTION")
    climax_idx = mark_best(rows, climax_indices, "climax", "MAIN_CLIMAX_BEST_IN_SECTION")
    ending_idx = mark_best(rows, ending_indices, "ending", "ENDING_BEST_IN_SECTION")

    cursor = 0.0
    for i, row in enumerate(rows, 1):
        dur = fnum(row.get("duration_sec"), 0.4)
        row["index"] = i
        row["timeline_start_sec"] = round(cursor, 4)
        row["timeline_end_sec"] = round(cursor + dur, 4)
        cursor += dur

    result = dict(data)
    result["module_before_132b"] = data.get("module")
    result["module"] = "132b_safe_reservation_no_story_reorder"
    result["updated_at"] = datetime.now().isoformat(timespec="seconds")
    result["items"] = rows
    result["timeline_count"] = len(rows)
    result["timeline_seconds"] = round(cursor, 4)
    result["reservation_summary"] = {
        "hook_index": hook_idx,
        "climax_index": climax_idx,
        "ending_index": ending_idx,
        "story_reordered": False,
        "drone_moved_count": 0,
        "slow_minimum_speed_percent": 50,
        "camera_counts": dict(Counter(str(x.get("camera_group") or "CAM_UNKNOWN") for x in rows)),
    }

    write_json(project / "stt_multicam_directed_timeline_v1.json", result)
    write_json(project / "stt_climax_directed_timeline_v1.json", result)
    write_json(out / "stt_multicam_directed_timeline_v1.json", result)
    write_csv(out / "SAFE_RESERVED_TIMELINE_132B.csv", rows, [
        "index","reservation_role","music_section","story_part","camera_group",
        "multicam_event_id","multicam_replaced","filename","timeline_start_sec",
        "duration_sec","scene_tag","is_main_climax_shot","slow_recommended",
        "slow_percent","file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(rows),
        "timeline_seconds": round(cursor, 3),
        "hook_reserved": hook_idx is not None,
        "climax_reserved": climax_idx is not None,
        "ending_reserved": ending_idx is not None,
        "story_reordered": False,
        "fix": "132b_safe_reservation_no_story_reorder"
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
