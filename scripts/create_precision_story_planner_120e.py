from __future__ import annotations
import argparse, json
from pathlib import Path
from precision_v4_common import *

def load_ai(project: Path) -> list[dict[str, Any]]:
    return list(read_json(project / "stt_visual_ai_scene_tags_v1.json").get("items") or [])

def load_blocks(project: Path):
    rows = read_csv(project / "stt_music_cut_map_manual.csv")
    blocks = []
    for r in rows:
        st, en = fnum(r.get("start_sec"), -1), fnum(r.get("end_sec"), -1)
        if st < 0 or en <= st:
            continue
        story = str(r.get("story_part") or "")
        rhythm = str(r.get("rhythm") or "medium").lower()
        if story == "intro_beauty":
            need, fallback = "decor|detail_beauty", False
        elif story == "cdcr_intro":
            need, fallback = "getting_ready|first_look|cdcr_portrait|detail_beauty", True
        elif story == "ceremony_story":
            need, fallback = "ceremony_giatien|church_ceremony|vow|ruoc_dau|family_emotion", True
        elif story == "reception_build":
            need, fallback = "reception_stage|wedding_game|family_photo|family_emotion", True
        elif story == "climax":
            need, fallback = "party|wedding_game|reception_stage", True
        elif story == "ending":
            need, fallback = "ending|cdcr_portrait|first_look", False
        else:
            need, fallback = str(r.get("scene_need") or "other"), boolish(r.get("allow_fallback", ""))
        blocks.append({"start_sec": st, "end_sec": en, "story_part": story, "rhythm": rhythm, "scene_need": need, "allow_fallback": fallback, "notes": r.get("notes", "")})
    return blocks

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

FORBID = {
    "intro_beauty": {"getting_ready","first_look","cdcr_portrait","reception_stage","wedding_game","family_photo","family_emotion","guest_food","party","vow","ruoc_dau","ending"},
    "ending": {"getting_ready","vow","ruoc_dau","guest_food","wedding_game","reception_stage","party","family_photo"},
}

def story_key(story: str):
    s = str(story or "")
    if "intro" in s: return "intro_beauty"
    if "ending" in s: return "ending"
    return s

def pop_scene(pools, needs, duration, allow_fallback, story):
    sk = story_key(story)
    forbidden = FORBID.get(sk, set())
    for need in needs:
        if need in forbidden:
            continue
        arr = pools.get(need, [])
        for i, item in enumerate(arr):
            motion = str(item.get("motion_class") or "")
            if duration >= 3 and motion in {"active", "shaky_or_whip"}:
                continue
            # Ending couple-only gate.
            if sk == "ending":
                scores = parse_top_tags(str(item.get("top_tags") or ""))
                couple = max(scores.get("ending",0), scores.get("cdcr_portrait",0), scores.get("first_look",0))
                bad = max(scores.get("reception_stage",0), scores.get("wedding_game",0), scores.get("party",0), scores.get("family_photo",0))
                if bad >= couple * 0.58 and bad >= 0.028:
                    continue
            return arr.pop(i)
    if not allow_fallback:
        return None
    safe = {
        "cdcr_intro": ["getting_ready","first_look","cdcr_portrait","detail_beauty","other"],
        "ceremony_story": ["ceremony_giatien","church_ceremony","vow","family_emotion","cdcr_portrait","other"],
        "reception_build": ["reception_stage","wedding_game","family_photo","family_emotion","party","other"],
        "climax": ["party","wedding_game","reception_stage","family_photo","other"],
    }.get(sk, ["other"])
    for tag in safe:
        arr = pools.get(tag, [])
        if arr:
            return arr.pop(0)
    return None

def main():
    p = argparse.ArgumentParser(description="120E Precision story planner.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="single_song_report_3_4min")
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "precision_story_planner_120e")
    rows = load_ai(project)
    if not rows:
        res = {"ok": False, "error": "NO_VISUAL_AI_SCENE_TAGS", "message": "Run 119H first."}
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
        story = str(block.get("story_part") or "")
        t, k = st, 0
        pat = rhythm_pattern(rhythm)
        while t < en - 0.18 and len(timeline) < a.target_shots:
            raw_end = min(en, t + pat[k % len(pat)])
            cut_end, snapped, beat_type = nearest_cut_beat(beats, t, raw_end, en, rhythm)
            d = cut_end - t
            if d < 0.20:
                break
            item = pop_scene(pools, needs, d, allow_fallback, story)
            if item is None:
                missing.append({"story_part": story, "scene_need": "|".join(needs), "time_sec": round(t, 3)})
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
                "story_part": story,
                "story_chapter": needs[0] if needs else "other",
                "target_section": needs[0] if needs else "other",
                "music_mode": rhythm,
                "rhythm_reason": f"120E_precision_story_{story}_{rhythm}",
                "beat_snapped": bool(snapped),
                "beat_type": beat_type,
                "director_note": block.get("notes", ""),
            })
            timeline.append(row)
            t += d
            k += 1

    data = {
        "ok": True, "module": "120E_precision_story_planner",
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
    write_json(project / "stt_precision_story_timeline_v1.json", data)
    write_json(out / "stt_precision_story_timeline_v1.json", data)
    write_csv(out / "PRECISION_STORY_TIMELINE_120E.csv", timeline, [
        "index","story_part","scene_tag","raw_scene_tag","filename","timeline_start_sec","duration_sec","timeline_end_sec",
        "source_in_sec","music_mode","beat_snapped","beat_type","confidence","margin","semantic_reason","top_tags","beauty_score","motion_class","file"
    ])
    write_csv(out / "MISSING_SCENE_NEEDS.csv", missing, ["story_part","scene_need","time_sec"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": duration_stats(timeline),
        "beat_snap_count": data["beat_snap_count"],
        "scene_counts": data["scene_counts"],
        "missing_count": len(missing),
        "fix": "120E_precision_story_planner",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
