from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from music_climax_common import *

SECTION_TO_STORY = {
    "intro": ["intro"],
    "story": ["story", "intro"],
    "build": ["build", "story"],
    "pre_climax": ["build", "climax", "story"],
    "climax": ["climax", "build"],
    "release": ["story", "build", "climax"],
    "ending": ["ending", "intro", "story"],
}

RHYTHM_PATTERNS = {
    "hold": [3.8, 2.6, 4.8, 1.6, 3.2],
    "medium": [2.4, 1.5, 3.2, 2.0, 1.1, 2.8],
    "rising": [2.1, 1.5, 1.1, 2.5, 0.9, 1.7],
    "fast": [0.55, 0.75, 0.45, 1.0, 0.65, 1.25, 0.50],
    "hero_mix": [3.8, 0.55, 0.75, 1.1, 0.50, 2.1, 0.65, 1.4],
    "medium_hold": [2.0, 3.4, 1.3, 2.6, 4.0],
    "emotional_hold": [4.6, 3.2, 5.8, 2.4, 4.2],
}

def story_key(item: dict[str, Any]) -> str:
    s = str(item.get("story_part") or item.get("story_chapter") or item.get("target_section") or "").lower()
    for key in ["intro", "story", "build", "climax", "ending"]:
        if key in s:
            return key
    return "story"

def enrich_items(project: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q_by_path, q_by_name = load_quality(project)
    b_by_path, b_by_name = load_beauty(project)
    out = []
    for i, item in enumerate(rows):
        row = dict(item)
        p = norm_path(row.get("file"))
        n = str(row.get("filename") or Path(p).name).lower()
        q = q_by_path.get(p)
        if not q:
            qs = q_by_name.get(n, [])
            q = qs[0] if qs else {}
        b = b_by_path.get(p) or b_by_name.get(n) or {}
        row["_source_order"] = i
        row["_story_key"] = story_key(row)
        row["_quality_score"] = fnum(
            row.get("moment_quality_score"),
            fnum(q.get("best_quality_score"), fnum(q.get("average_quality_score"), 45))
        )
        row["_beauty_score"] = fnum(row.get("beauty_score"), fnum(b.get("beauty_score"), 55))
        row["_taste_score"] = fnum(row.get("taste_score"), fnum(row.get("taste_used_weight"), 1) * 15)
        row["_media_duration"] = fnum(
            row.get("media_duration_sec"),
            fnum(q.get("duration_sec"), media_duration(str(row.get("file") or "")))
        )
        row["_quality_windows"] = list(q.get("windows") or [])
        out.append(row)
    return out

def hero_score(item: dict[str, Any], music_label: str) -> float:
    tag = str(item.get("scene_tag") or "other")
    score = (
        fnum(item.get("_quality_score"), 45) * 0.48
        + fnum(item.get("_beauty_score"), 55) * 0.38
        + fnum(item.get("_taste_score"), 15) * 0.28
    )
    if music_label == "climax":
        if tag in {
            "cdcr_portrait", "first_look", "vow", "family_emotion",
            "reception_stage", "party", "wedding_game", "ending"
        }:
            score += 24
        if tag in {"guest_food", "other"}:
            score -= 18
    elif music_label == "ending":
        if tag in {"ending", "cdcr_portrait", "first_look", "family_emotion"}:
            score += 32
        if tag in {"guest_food", "wedding_game", "getting_ready"}:
            score -= 28
    elif music_label == "intro":
        if tag in {"decor", "detail_beauty", "cdcr_portrait", "first_look"}:
            score += 18
    return score

def nearest_beat_end(
    beats: list[dict[str, Any]],
    start: float,
    desired_end: float,
    section_end: float,
    rhythm: str,
) -> float:
    if not beats:
        return min(desired_end, section_end)
    max_extra = 0.30 if rhythm in {"fast", "hero_mix"} else 0.65
    min_len = 0.40 if rhythm in {"fast", "hero_mix"} else 0.75
    cand = []
    for b in beats:
        t = fnum(b.get("time_sec"), 0)
        if t < start + min_len:
            continue
        if t > min(section_end, desired_end + max_extra):
            break
        strength = fnum(b.get("strength"), 0.5)
        cand.append((abs(t - desired_end), -strength, t))
    if not cand:
        return min(desired_end, section_end)
    cand.sort()
    return min(section_end, cand[0][2])

def best_source_window(item: dict[str, Any], desired_duration: float) -> tuple[float, float, float]:
    media_dur = fnum(item.get("_media_duration"), 0)
    windows = list(item.get("_quality_windows") or [])
    ranked = []
    for w in windows:
        score = fnum(w.get("quality_score"), 0)
        if w.get("severe_shake"):
            score -= 38
        if w.get("likely_blur"):
            score -= 22
        center = fnum(w.get("center_sec"), 0)
        start = center - desired_duration / 2
        if media_dur > 0:
            start = clamp(start, 0, max(0, media_dur - desired_duration))
        ranked.append((score, start))
    if ranked:
        ranked.sort(key=lambda x: x[0], reverse=True)
        qscore, start = ranked[0]
    else:
        qscore = fnum(item.get("_quality_score"), 45)
        start = fnum(item.get("source_in_sec"), 0)
        if media_dur > 0:
            start = clamp(start, 0, max(0, media_dur - desired_duration))
    return round(max(0, start), 4), round(max(0, start + desired_duration), 4), round(qscore, 3)

def select_candidate(
    items: list[dict[str, Any]],
    used: set[int],
    allowed_story: list[str],
    label: str,
    hero: bool,
    order_cursor: int,
) -> dict[str, Any] | None:
    eligible = [
        x for x in items
        if int(x.get("_source_order", -1)) not in used
        and str(x.get("_story_key")) in allowed_story
    ]
    if not eligible:
        eligible = [x for x in items if int(x.get("_source_order", -1)) not in used]
    if not eligible:
        return None

    if hero:
        return max(eligible, key=lambda x: hero_score(x, label))

    # Preserve taste/story order while still preferring quality.
    def score(x: dict[str, Any]) -> float:
        order = int(x.get("_source_order", 0))
        distance_penalty = abs(order - order_cursor) * 0.18
        return hero_score(x, label) - distance_penalty

    window = sorted(eligible, key=lambda x: int(x.get("_source_order", 0)))[:14]
    return max(window, key=score)

def emphasis_in_range(points: list[dict[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    return [x for x in points if start <= fnum(x.get("time_sec"), -1) < end]

def main() -> None:
    p = argparse.ArgumentParser(description="127 Climax Shot Director + varied rhythm.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--target-shots", type=int, default=150)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "climax_shot_director_127")
    tl = current_timeline(project)
    rows = list(tl.get("items") or [])
    music = read_json(project / "stt_music_structure_climax_v3.json")
    beat_data = read_json(project / "stt_precise_beat_grid_v2.json")
    beats = list(beat_data.get("beats") or [])

    if not rows:
        res = {"ok": False, "error": "NO_QUALITY_TASTE_TIMELINE", "message": "Run 123B and 125 first."}
        write_json(out / "CLIMAX_DIRECTOR_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not music.get("sections"):
        res = {"ok": False, "error": "NO_MUSIC_STRUCTURE", "message": "Run 126 first."}
        write_json(out / "CLIMAX_DIRECTOR_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    items = enrich_items(project, rows)
    sections = list(music.get("sections") or [])
    emphasis_points = list(music.get("emphasis_points") or [])
    main_climax = fnum(music.get("main_climax_sec"), 0)

    used: set[int] = set()
    timeline = []
    order_cursor = 0
    hero_count = 0
    slow_recommended_count = 0

    for sec in sections:
        label = str(sec.get("label") or "story")
        st = fnum(sec.get("start_sec"), 0)
        en = fnum(sec.get("end_sec"), 0)
        rhythm = str(sec.get("rhythm") or "medium")
        pattern = RHYTHM_PATTERNS.get(rhythm, RHYTHM_PATTERNS["medium"])
        allowed = SECTION_TO_STORY.get(label, ["story"])
        local_emphasis = emphasis_in_range(emphasis_points, st, en)
        t = st
        k = 0

        while t < en - 0.25 and len(timeline) < a.target_shots:
            desired = pattern[k % len(pattern)]
            desired_end = min(en, t + desired)
            cut_end = nearest_beat_end(beats, t, desired_end, en, rhythm)
            duration = max(0.40, cut_end - t)

            # Main climax/strong emphasis receives the best remaining shot.
            anchor = None
            for e in local_emphasis:
                et = fnum(e.get("time_sec"), -1)
                if t <= et < cut_end:
                    anchor = e
                    break
            is_main_hero = label == "climax" and t <= main_climax < cut_end
            is_hero = is_main_hero or (anchor is not None and fnum(anchor.get("score"), 0) >= 0.72)

            item = select_candidate(items, used, allowed, label, is_hero, order_cursor)
            if item is None:
                break

            idx = int(item.get("_source_order", -1))
            used.add(idx)
            order_cursor = max(order_cursor, idx + 1)

            # Hero shots need room to breathe; normal shots keep music-driven duration.
            if is_main_hero:
                duration = clamp(max(duration, 4.2), 4.2, min(6.5, en - t))
                cut_end = min(en, t + duration)
            elif label == "ending" and duration < 3.0:
                duration = min(en - t, 3.5)
                cut_end = t + duration

            source_in, source_out, window_quality = best_source_window(item, duration)
            row = dict(item)
            emphasis_sec = fnum(anchor.get("time_sec"), 0) if anchor else (main_climax if is_main_hero else 0)
            slow_recommended = bool(
                label in {"climax", "ending"}
                and duration >= 3.2
                and (
                    is_main_hero
                    or is_hero
                    or hero_score(item, label) >= 70
                )
            )

            row.update({
                "index": len(timeline) + 1,
                "timeline_start_sec": round(t, 4),
                "timeline_end_sec": round(cut_end, 4),
                "duration_sec": round(cut_end - t, 4),
                "source_in_sec": source_in,
                "source_out_sec": source_out,
                "source_duration_sec": round(cut_end - t, 4),
                "music_section": label,
                "music_mode": rhythm,
                "story_part": item.get("_story_key"),
                "rhythm_reason": f"127_{label}_{rhythm}",
                "hero_score": round(hero_score(item, label), 3),
                "is_hero_shot": bool(is_hero),
                "is_main_climax_shot": bool(is_main_hero),
                "emphasis_time_sec": round(emphasis_sec, 4),
                "slow_recommended": slow_recommended,
                "slow_percent": 50 if slow_recommended else 100,
                "quality_window_score": window_quality,
                "beat_snapped": True,
            })
            timeline.append(row)
            if is_hero:
                hero_count += 1
            if slow_recommended:
                slow_recommended_count += 1

            t = cut_end
            k += 1

        # Fill final fractional gap with the previous shot duration corrected later.
        if timeline and timeline[-1]["timeline_end_sec"] < en - 0.02:
            gap = en - fnum(timeline[-1].get("timeline_end_sec"), 0)
            if gap <= 0.80:
                timeline[-1]["timeline_end_sec"] = round(en, 4)
                timeline[-1]["duration_sec"] = round(
                    fnum(timeline[-1].get("duration_sec"), 0) + gap, 4
                )
                timeline[-1]["source_out_sec"] = round(
                    fnum(timeline[-1].get("source_out_sec"), 0) + gap, 4
                )
                timeline[-1]["source_duration_sec"] = timeline[-1]["duration_sec"]

    # Force exact contiguous timeline from zero.
    cursor = 0.0
    for i, row in enumerate(timeline, 1):
        dur = fnum(row.get("duration_sec"), 0.4)
        row["index"] = i
        row["timeline_start_sec"] = round(cursor, 4)
        row["timeline_end_sec"] = round(cursor + dur, 4)
        cursor += dur

    target = fnum(music.get("target_seconds"), cursor)
    if timeline and abs(cursor - target) <= 2.0:
        delta = target - cursor
        timeline[-1]["duration_sec"] = round(max(0.4, fnum(timeline[-1].get("duration_sec"), 0) + delta), 4)
        timeline[-1]["timeline_end_sec"] = round(target, 4)
        timeline[-1]["source_out_sec"] = round(
            fnum(timeline[-1].get("source_in_sec"), 0) + fnum(timeline[-1].get("duration_sec"), 0),
            4,
        )
        cursor = target

    data = {
        "ok": True,
        "module": "127_climax_shot_director_v1",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "music_file": music.get("music_file"),
        "main_climax_sec": main_climax,
        "timeline_count": len(timeline),
        "timeline_seconds": round(cursor, 4),
        "duration_stats": duration_stats(timeline),
        "hero_shot_count": hero_count,
        "slow_recommended_count": slow_recommended_count,
        "unused_source_count": len(items) - len(used),
        "items": timeline,
    }

    write_json(project / "stt_climax_directed_timeline_v1.json", data)
    write_json(project / "stt_beat_snapped_beauty_timeline_v1.json", data)
    write_json(out / "stt_climax_directed_timeline_v1.json", data)
    write_csv(out / "CLIMAX_DIRECTED_TIMELINE.csv", timeline, [
        "index", "music_section", "story_part", "filename",
        "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "source_in_sec", "source_out_sec", "hero_score",
        "is_hero_shot", "is_main_climax_shot", "emphasis_time_sec",
        "slow_recommended", "slow_percent", "quality_window_score",
        "scene_tag", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(timeline),
        "timeline_seconds": round(cursor, 3),
        "duration_stats": data["duration_stats"],
        "hero_shot_count": hero_count,
        "slow_recommended_count": slow_recommended_count,
        "main_climax_sec": round(main_climax, 3),
        "fix": "127_climax_shot_director_v1",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
