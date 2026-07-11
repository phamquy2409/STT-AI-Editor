from __future__ import annotations
import argparse, json
from pathlib import Path
from semantic_sequence_common import *

def load_ai(project: Path) -> list[dict[str, Any]]:
    return list(read_json(project / "stt_visual_ai_scene_tags_v1.json").get("items") or [])

def load_blocks(project: Path) -> list[dict[str, Any]]:
    # Strict product structure for single-song report. Do not let fallback pull wrong era scenes.
    rows = read_csv(project / "stt_music_cut_map_manual.csv")
    if rows:
        # Use existing timing, but replace scene needs with stricter semantic V3 needs.
        blocks = []
        for r in rows:
            st, en = fnum(r.get("start_sec"), -1), fnum(r.get("end_sec"), -1)
            if st < 0 or en <= st:
                continue
            story = str(r.get("story_part") or "")
            rhythm = str(r.get("rhythm") or "medium").lower()
            if story == "intro_beauty":
                need = "decor|detail_beauty"
                fallback = False
            elif story == "cdcr_intro":
                need = "getting_ready|first_look|cdcr_portrait"
                fallback = True
            elif story == "ceremony_story":
                need = "ceremony_giatien|church_ceremony|vow|ruoc_dau|family_emotion"
                fallback = True
            elif story == "reception_build":
                need = "reception_stage|wedding_game|family_photo|family_emotion"
                fallback = True
            elif story == "climax":
                need = "party|wedding_game|reception_stage"
                fallback = True
            elif story == "ending":
                need = "ending|family_emotion|family_photo|cdcr_portrait|detail_beauty"
                fallback = True
            else:
                need = str(r.get("scene_need") or "other")
                fallback = boolish(r.get("allow_fallback", ""))
            blocks.append({
                "start_sec": st, "end_sec": en, "story_part": story,
                "rhythm": rhythm, "scene_need": need, "allow_fallback": fallback,
                "notes": r.get("notes", ""),
            })
        if blocks:
            return blocks

    # Fallback blocks if no manual map.
    target = 210
    ratios = [
        (0.00, 0.10, "intro_beauty", "hold", "decor|detail_beauty", False),
        (0.10, 0.25, "getting_ready_firstlook", "medium", "getting_ready|first_look|cdcr_portrait", True),
        (0.25, 0.50, "ceremony_vow", "hold", "ceremony_giatien|church_ceremony|vow|ruoc_dau|family_emotion", True),
        (0.50, 0.67, "reception_story", "medium", "reception_stage|wedding_game|family_photo|family_emotion", True),
        (0.67, 0.84, "climax", "fast", "party|wedding_game|reception_stage", True),
        (0.84, 1.00, "ending", "hold", "ending|family_emotion|family_photo|cdcr_portrait|detail_beauty", True),
    ]
    return [{"start_sec": target*a, "end_sec": target*b, "story_part": part, "rhythm": rhythm, "scene_need": need, "allow_fallback": fb, "notes": "auto_120d"} for a,b,part,rhythm,need,fb in ratios]

def rhythm_pattern(rhythm: str) -> list[float]:
    if rhythm == "hold":
        return [4.8, 6.4, 3.2, 7.2, 5.0]
    if rhythm == "fast":
        return [0.42, 0.58, 0.72, 0.48, 0.95, 0.55, 1.25]
    return [1.4, 2.2, 1.0, 3.1, 1.7, 2.8]

def nearest_cut_beat(beats, t, raw_end, block_end, rhythm):
    if not beats:
        return raw_end, False, "no_beat_grid"
    if rhythm == "fast":
        min_gap, max_extra, strength_need = 0.25, 0.34, 0.50
    elif rhythm == "hold":
        min_gap, max_extra, strength_need = 1.20, 0.95, 0.74
    else:
        min_gap, max_extra, strength_need = 0.55, 0.60, 0.58
    min_t, max_t = t + min_gap, min(block_end, raw_end + max_extra)
    cand = []
    for b in beats:
        bt = fnum(b.get("time_sec"), 0)
        if bt < min_t:
            continue
        if bt > max_t:
            break
        strength = fnum(b.get("strength"), 0.5)
        if strength >= strength_need:
            cand.append((abs(bt - raw_end), -strength, bt, str(b.get("type", ""))))
    if not cand:
        for b in beats:
            bt = fnum(b.get("time_sec"), 0)
            if min_t <= bt <= max_t:
                cand.append((abs(bt - raw_end), -fnum(b.get("strength"), 0.5), bt, str(b.get("type", ""))))
    if not cand:
        return raw_end, False, "no_candidate"
    cand.sort()
    return round(cand[0][2], 4), True, cand[0][3]

def build_pools(project: Path, rows):
    by_path, by_name = load_beauty(project)
    pools = {t: [] for t in SCENE_TAGS}
    for i, r in enumerate(rows):
        p = str(r.get("file") or "")
        if not p or not Path(p).exists():
            continue
        tag = str(r.get("scene_tag") or "other")
        if tag not in pools:
            tag = "other"
        keyp = p.replace("\\", "/").lower()
        b = by_path.get(keyp) or by_name.get(str(r.get("filename") or Path(p).name).lower()) or {}
        row = dict(r)
        row.update({
            "_source_order": int(row.get("_source_order", i)),
            "beauty_score": fnum(b.get("beauty_score"), 55),
            "beauty_class": b.get("beauty_class", ""),
            "motion_class": b.get("motion_class", "unknown"),
            "best_source_in_sec": fnum(b.get("best_source_in_sec"), 0),
            "media_duration_sec": fnum(b.get("duration_sec"), fnum(r.get("media_duration_sec"), 0)),
        })
        pools[tag].append(row)
    for tag in pools:
        pools[tag] = sorted(pools[tag], key=lambda x: (int(x.get("_source_order", 0)), -fnum(x.get("confidence"), 0)))
    return pools

FORBID_BY_STORY = {
    "intro_beauty": {"getting_ready", "first_look", "cdcr_portrait", "reception_stage", "wedding_game", "family_photo", "family_emotion", "guest_food", "party", "vow", "ruoc_dau"},
    "cdcr_intro": {"guest_food", "party", "wedding_game", "reception_stage", "ending"},
    "ceremony_story": {"guest_food", "party", "wedding_game", "decor", "detail_beauty"},
    "reception_build": {"decor", "detail_beauty", "getting_ready", "first_look", "guest_food", "ending"},
    "climax": {"decor", "detail_beauty", "getting_ready", "first_look", "guest_food", "vow", "ruoc_dau"},
    "ending": {"getting_ready", "first_look", "vow", "ruoc_dau", "guest_food", "wedding_game"},
}

def story_key(story_part: str) -> str:
    s = str(story_part or "")
    if "intro" in s:
        return "intro_beauty"
    if "cdcr" in s or "getting_ready" in s:
        return "cdcr_intro"
    if "ceremony" in s or "vow" in s:
        return "ceremony_story"
    if "reception" in s:
        return "reception_build"
    if "climax" in s:
        return "climax"
    if "ending" in s:
        return "ending"
    return s

def pop_scene(pools, needs, duration, allow_fallback, story_part):
    s_key = story_key(story_part)
    forbidden = FORBID_BY_STORY.get(s_key, set())

    for need in needs:
        if need in forbidden:
            continue
        arr = pools.get(need, [])
        for i, item in enumerate(arr):
            motion = str(item.get("motion_class") or "")
            if duration >= 3 and motion in {"active", "shaky_or_whip"}:
                continue
            return arr.pop(i)

    if not allow_fallback:
        return None

    # Fallback only inside allowed story-safe tags.
    safe_order = {
        "intro_beauty": ["decor", "detail_beauty", "other"],
        "cdcr_intro": ["getting_ready", "first_look", "cdcr_portrait", "family_photo", "other"],
        "ceremony_story": ["ceremony_giatien", "church_ceremony", "vow", "family_emotion", "family_photo", "cdcr_portrait", "other"],
        "reception_build": ["reception_stage", "wedding_game", "family_photo", "family_emotion", "party", "other"],
        "climax": ["party", "wedding_game", "reception_stage", "family_photo", "other"],
        "ending": ["ending", "family_emotion", "family_photo", "cdcr_portrait", "detail_beauty", "decor", "other"],
    }.get(s_key, SCENE_TAGS)

    for tag in safe_order:
        if tag in forbidden:
            continue
        arr = pools.get(tag, [])
        if arr:
            return arr.pop(0)
    return None

def main() -> None:
    p = argparse.ArgumentParser(description="120D Strict semantic story planner after 119F.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="single_song_report_3_4min")
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "strict_semantic_story_planner_120d")
    rows = load_ai(project)
    if not rows:
        res = {"ok": False, "error": "NO_VISUAL_AI_SCENE_TAGS", "message": "Run 119E then 119F first."}
        write_json(out / "planner_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    pools = build_pools(project, rows)
    blocks = load_blocks(project)
    beats = load_beats(project)
    timeline, missing = [], []
    for block in blocks:
        if len(timeline) >= a.target_shots:
            break
        st, en = fnum(block.get("start_sec"), 0), fnum(block.get("end_sec"), 0)
        rhythm = str(block.get("rhythm") or "medium").lower()
        needs = [x.strip() for x in str(block.get("scene_need") or "other").split("|") if x.strip()]
        allow_fallback = bool(block.get("allow_fallback", False))
        story_part = str(block.get("story_part") or "")
        t, k = st, 0
        pat = rhythm_pattern(rhythm)
        while t < en - 0.18 and len(timeline) < a.target_shots:
            raw_end = min(en, t + pat[k % len(pat)])
            cut_end, snapped, beat_type = nearest_cut_beat(beats, t, raw_end, en, rhythm)
            d = cut_end - t
            if d < 0.20:
                break
            item = pop_scene(pools, needs, d, allow_fallback, story_part)
            if item is None:
                missing.append({"story_part": story_part, "scene_need": "|".join(needs), "time_sec": round(t, 3)})
                break
            src_in = fnum(item.get("best_source_in_sec"), 0)
            real_dur = fnum(item.get("media_duration_sec"), 0)
            if real_dur > 0 and src_in + d > real_dur - 0.05:
                src_in = max(0, real_dur - d - 0.08)
            row = dict(item)
            row.update({
                "index": len(timeline) + 1,
                "timeline_start_sec": round(t, 3),
                "timeline_end_sec": round(t + d, 3),
                "duration_sec": round(d, 3),
                "source_in_sec": round(src_in, 3),
                "source_out_sec": round(src_in + d, 3),
                "source_duration_sec": round(d, 3),
                "story_part": story_part,
                "story_chapter": needs[0] if needs else "other",
                "target_section": needs[0] if needs else "other",
                "music_mode": rhythm,
                "rhythm_reason": f"120D_strict_semantic_{story_part}_{rhythm}",
                "beat_snapped": bool(snapped),
                "beat_type": beat_type,
                "director_note": block.get("notes", ""),
            })
            timeline.append(row)
            t += d
            k += 1

    data = {
        "ok": True,
        "module": "120D_strict_semantic_story_planner",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style_profile": a.style_profile,
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": duration_stats(timeline),
        "beat_snap_count": sum(1 for x in timeline if x.get("beat_snapped")),
        "scene_counts": count_tags(timeline),
        "missing_count": len(missing),
        "missing": missing,
        "items": timeline,
    }
    write_json(project / "stt_beat_snapped_beauty_timeline_v1.json", data)
    write_json(project / "stt_strict_semantic_story_timeline_v1.json", data)
    write_json(out / "stt_strict_semantic_story_timeline_v1.json", data)
    write_csv(out / "STRICT_SEMANTIC_TIMELINE_120D.csv", timeline, [
        "index", "story_part", "scene_tag", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "source_in_sec", "music_mode", "beat_snapped", "beat_type", "confidence", "margin", "top_tags", "sequence_fix_reason", "beauty_score", "motion_class", "file"
    ])
    write_csv(out / "MISSING_SCENE_NEEDS.csv", missing, ["story_part", "scene_need", "time_sec"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": duration_stats(timeline),
        "beat_snap_count": data["beat_snap_count"],
        "scene_counts": data["scene_counts"],
        "missing_count": len(missing),
        "fix": "120D_strict_semantic_story_planner",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
