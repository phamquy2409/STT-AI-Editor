from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from multicam_common import *

def reserve_score(item: dict[str, Any], purpose: str) -> float:
    tag = str(item.get("scene_tag") or "other")
    quality = fnum(item.get("quality_window_score"), fnum(item.get("moment_quality_score"), 45))
    beauty = fnum(item.get("beauty_score"), 55)
    hero = fnum(item.get("hero_score"), 0)
    score = quality * 0.42 + beauty * 0.42 + hero * 0.30

    if purpose == "hook":
        if tag in {"decor", "detail_beauty", "cdcr_portrait", "first_look", "ending"}:
            score += 24
        if item.get("camera_group") == "DRONE":
            score += 16
    elif purpose == "climax":
        if tag in {"cdcr_portrait", "first_look", "vow", "family_emotion", "reception_stage", "party", "wedding_game"}:
            score += 32
        if tag in {"guest_food", "other"}:
            score -= 22
    elif purpose == "ending":
        if tag in {"ending", "cdcr_portrait", "first_look", "family_emotion"}:
            score += 36
        if tag in {"getting_ready", "guest_food", "wedding_game"}:
            score -= 35
        if item.get("camera_group") == "DRONE":
            score += 12
    return score

def best_index(rows: list[dict[str, Any]], purpose: str, allowed: set[int], exclude: set[int]) -> int | None:
    candidates = [(reserve_score(rows[i], purpose), i) for i in allowed if i not in exclude]
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]

def swap_rows(rows: list[dict[str, Any]], a: int, b: int) -> None:
    if a == b:
        return
    keep_a = {k: rows[a].get(k) for k in ["timeline_start_sec", "timeline_end_sec", "duration_sec"]}
    keep_b = {k: rows[b].get(k) for k in ["timeline_start_sec", "timeline_end_sec", "duration_sec"]}
    rows[a], rows[b] = rows[b], rows[a]
    rows[a].update(keep_a)
    rows[b].update(keep_b)

def main() -> None:
    p = argparse.ArgumentParser(description="132 Shot Reservation + Drone Director.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "shot_reservation_drone_132")
    data = read_json(project / "stt_multicam_selected_timeline_v1.json")
    rows = [dict(x) for x in (data.get("items") or [])]

    if not rows:
        res = {"ok": False, "error": "NO_MULTICAM_TIMELINE", "message": "Run 131 first."}
        write_json(out / "RESERVATION_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    n = len(rows)
    hook_slots = set(range(0, max(1, min(n, round(n * 0.10)))))
    climax_slots = {
        i for i, x in enumerate(rows)
        if str(x.get("music_section") or "") == "climax" or x.get("is_main_climax_shot")
    }
    if not climax_slots:
        climax_slots = set(range(max(0, round(n * 0.62)), min(n, round(n * 0.78))))
    ending_slots = set(range(max(0, round(n * 0.86)), n))

    all_indices = set(range(n))
    reserved = set()

    hook_best = best_index(rows, "hook", all_indices, reserved)
    if hook_best is not None:
        target = min(hook_slots, key=lambda i: abs(i - 1))
        swap_rows(rows, hook_best, target)
        reserved.add(target)
        rows[target]["reservation_role"] = "HOOK_BEST"

    climax_best = best_index(rows, "climax", all_indices, reserved)
    if climax_best is not None and climax_slots:
        target = min(climax_slots, key=lambda i: abs(i - round(n * 0.70)))
        swap_rows(rows, climax_best, target)
        reserved.add(target)
        rows[target]["reservation_role"] = "MAIN_CLIMAX_BEST"
        rows[target]["is_main_climax_shot"] = True
        if fnum(rows[target].get("duration_sec"), 0) >= 3.2:
            rows[target]["slow_recommended"] = True
            rows[target]["slow_percent"] = 50

    ending_best = best_index(rows, "ending", all_indices, reserved)
    if ending_best is not None and ending_slots:
        target = max(ending_slots)
        swap_rows(rows, ending_best, target)
        reserved.add(target)
        rows[target]["reservation_role"] = "ENDING_BEST"

    # Drone restriction: only intro, release/transition, ending.
    drone_moved = 0
    illegal_drone = [
        i for i, x in enumerate(rows)
        if x.get("camera_group") == "DRONE"
        and str(x.get("music_section") or x.get("story_part") or "") not in {"intro", "release", "ending"}
    ]
    legal_slots = [
        i for i, x in enumerate(rows)
        if str(x.get("music_section") or x.get("story_part") or "") in {"intro", "release", "ending"}
        and x.get("camera_group") != "DRONE"
        and i not in reserved
    ]
    for src, dst in zip(illegal_drone, legal_slots):
        swap_rows(rows, src, dst)
        rows[dst]["drone_director_reason"] = "moved_drone_to_establishing_transition_or_ending"
        drone_moved += 1

    # Rebuild exact contiguous timing while preserving durations.
    cursor = 0.0
    for i, row in enumerate(rows, 1):
        dur = fnum(row.get("duration_sec"), 0.4)
        row["index"] = i
        row["timeline_start_sec"] = round(cursor, 4)
        row["timeline_end_sec"] = round(cursor + dur, 4)
        cursor += dur

    result = dict(data)
    result["module_before_132"] = data.get("module")
    result["module"] = "132_shot_reservation_drone_director"
    result["updated_at"] = datetime.now().isoformat(timespec="seconds")
    result["items"] = rows
    result["timeline_count"] = len(rows)
    result["timeline_seconds"] = round(cursor, 4)
    result["duration_stats"] = duration_stats(rows)
    result["reservation_summary"] = {
        "hook_reserved": hook_best is not None,
        "climax_reserved": climax_best is not None,
        "ending_reserved": ending_best is not None,
        "drone_moved_count": drone_moved,
        "camera_counts": dict(Counter(str(x.get("camera_group") or "CAM_UNKNOWN") for x in rows)),
        "slow_minimum_speed_percent": 50,
    }

    # Exporter 128 reads this path.
    write_json(project / "stt_multicam_directed_timeline_v1.json", result)
    write_json(project / "stt_climax_directed_timeline_v1.json", result)
    write_json(out / "stt_multicam_directed_timeline_v1.json", result)
    write_csv(out / "MULTICAM_RESERVED_TIMELINE.csv", rows, [
        "index", "reservation_role", "music_section", "story_part",
        "camera_group", "shot_scale", "multicam_event_id",
        "filename", "timeline_start_sec", "duration_sec",
        "scene_tag", "is_main_climax_shot", "slow_recommended",
        "slow_percent", "drone_director_reason", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(rows),
        "timeline_seconds": round(cursor, 3),
        "hook_reserved": hook_best is not None,
        "climax_reserved": climax_best is not None,
        "ending_reserved": ending_best is not None,
        "drone_moved_count": drone_moved,
        "camera_counts": result["reservation_summary"]["camera_counts"],
        "fix": "132_shot_reservation_drone_director",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
