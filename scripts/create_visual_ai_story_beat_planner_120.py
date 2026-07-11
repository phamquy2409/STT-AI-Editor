from visual_ai_common import *


def load_ai_rows(project: Path) -> list[dict[str, Any]]:
    d = read_json(project / "stt_visual_ai_scene_tags_v1.json")
    return list(d.get("items") or [])


def load_beauty(project: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path, by_name = {}, {}
    for r in d.get("items", []):
        p = str(r.get("file") or "").replace("\\", "/").lower()
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name.setdefault(n, r)
    return by_path, by_name


def load_cut_blocks(project: Path) -> list[dict[str, Any]]:
    rows = []
    p = project / "stt_music_cut_map_manual.csv"
    if p.exists():
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                st, en = fnum(r.get("start_sec"), -1), fnum(r.get("end_sec"), -1)
                if st >= 0 and en > st:
                    rows.append({
                        "block": r.get("block", ""),
                        "start_sec": st,
                        "end_sec": en,
                        "story_part": str(r.get("story_part") or ""),
                        "rhythm": str(r.get("rhythm") or "medium").lower(),
                        "scene_need": str(r.get("scene_need") or "other"),
                        "allow_fallback": str(r.get("allow_fallback") or "").lower() == "true",
                        "notes": r.get("notes", ""),
                    })
    if rows:
        return rows

    music_dur = load_music_duration(project)
    target = int(max(90, min(240, music_dur - 2))) if music_dur > 0 else 210
    ratios = [
        (0.00, 0.09, "intro_beauty", "hold", "intro_beauty", False),
        (0.09, 0.24, "cdcr_intro", "medium", "cdcr|makeup", False),
        (0.24, 0.46, "ceremony_story", "hold", "ceremony_giatien|ruoc_dau|cdcr", True),
        (0.46, 0.64, "reception_build", "medium", "reception_stage|family|cdcr", True),
        (0.64, 0.84, "climax", "fast", "party|reception_stage|cdcr", True),
        (0.84, 1.00, "ending", "hold", "ending|family|cdcr", True),
    ]
    return [{"block": i+1, "start_sec": target*a, "end_sec": target*b, "story_part": part, "rhythm": rhythm, "scene_need": need, "allow_fallback": fallback, "notes": "auto"} for i,(a,b,part,rhythm,need,fallback) in enumerate(ratios)]


def rhythm_pattern(rhythm: str) -> list[float]:
    if rhythm == "hold":
        return [4.8, 6.4, 3.2, 7.2, 5.0]
    if rhythm == "fast":
        return [0.42, 0.58, 0.72, 0.48, 0.95, 0.55, 1.25]
    if rhythm == "impact":
        return [0.22, 0.34, 0.48, 0.28, 0.65]
    return [1.4, 2.2, 1.0, 3.1, 1.7, 2.8]


def nearest_cut_beat(beats: list[dict[str, Any]], t: float, raw_end: float, block_end: float, rhythm: str) -> tuple[float, bool, str]:
    if not beats:
        return raw_end, False, "no_beat_grid"
    if rhythm in {"fast", "impact"}:
        min_gap, max_extra, strength_need = 0.25, 0.32, 0.50
    elif rhythm == "hold":
        min_gap, max_extra, strength_need = 1.20, 0.90, 0.76
    else:
        min_gap, max_extra, strength_need = 0.55, 0.55, 0.60

    min_t = t + min_gap
    max_t = min(block_end, raw_end + max_extra)
    candidates = []
    for b in beats:
        bt = fnum(b.get("time_sec"), 0)
        if bt < min_t:
            continue
        if bt > max_t:
            break
        strength = fnum(b.get("strength"), 0.5)
        if strength >= strength_need:
            candidates.append((abs(bt - raw_end), -strength, bt, str(b.get("type", ""))))
    if not candidates:
        for b in beats:
            bt = fnum(b.get("time_sec"), 0)
            if min_t <= bt <= max_t:
                candidates.append((abs(bt - raw_end), -fnum(b.get("strength"), 0.5), bt, str(b.get("type", ""))))
    if not candidates:
        return raw_end, False, "no_candidate"
    candidates.sort()
    return round(candidates[0][2], 4), True, candidates[0][3]


def build_pools(ai_rows: list[dict[str, Any]], project: Path) -> dict[str, list[dict[str, Any]]]:
    beauty_path, beauty_name = load_beauty(project)
    pools = {t: [] for t in SCENE_TAGS}

    for i, r in enumerate(ai_rows):
        path = str(r.get("file") or "")
        if not path or not Path(path).exists():
            continue
        tag = str(r.get("scene_tag") or "other")
        if tag not in pools:
            tag = "other"

        keyp = path.replace("\\", "/").lower()
        b = beauty_path.get(keyp) or beauty_name.get(str(r.get("filename") or Path(path).name).lower()) or {}

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
        # semantic pools preserve rough shooting order, but confidence helps inside same order.
        pools[tag] = sorted(pools[tag], key=lambda x: (int(x.get("_source_order", 0)), -fnum(x.get("confidence"), 0)))
    return pools


def pop_scene(pools: dict[str, list[dict[str, Any]]], needs: list[str], duration: float, allow_fallback: bool) -> dict[str, Any] | None:
    for need in needs:
        arr = pools.get(need, [])
        for i, item in enumerate(arr):
            motion = str(item.get("motion_class") or "")
            conf = fnum(item.get("confidence"), 0)
            if duration >= 3.0:
                if motion not in {"active", "shaky_or_whip"} and conf >= 0.05:
                    return arr.pop(i)
            else:
                if motion != "shaky_or_whip" or duration <= 0.55:
                    return arr.pop(i)

    if not allow_fallback:
        return None

    forbidden = set()
    if any(n in {"intro_beauty", "cdcr", "makeup"} for n in needs):
        forbidden.add("guest_food")
    if any(n in {"intro_beauty"} for n in needs):
        forbidden.update({"reception_stage", "party"})

    for tag in SCENE_TAGS:
        if tag in forbidden:
            continue
        arr = pools.get(tag, [])
        if arr:
            return arr.pop(0)
    return None


def main() -> None:
    p = argparse.ArgumentParser(description="120 Visual AI story beat planner.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="single_song_report_3_4min")
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "visual_ai_story_beat_planner_120")

    ai_rows = load_ai_rows(project)
    blocks = load_cut_blocks(project)
    beats = load_beats(project)
    if not ai_rows:
        res = {"ok": False, "error": "NO_VISUAL_AI_SCENE_TAGS", "message": "Run 119 first."}
        write_json(out / "visual_ai_story_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    pools = build_pools(ai_rows, project)
    timeline = []
    missing = []

    for block in blocks:
        if len(timeline) >= a.target_shots:
            break
        st, en = fnum(block.get("start_sec"), 0), fnum(block.get("end_sec"), 0)
        rhythm = str(block.get("rhythm") or "medium").lower()
        needs = [x.strip() for x in str(block.get("scene_need") or "other").split("|") if x.strip()]
        allow_fallback = bool(block.get("allow_fallback", False))
        t, k = st, 0
        pat = rhythm_pattern(rhythm)

        while t < en - 0.18 and len(timeline) < a.target_shots:
            raw_d = pat[k % len(pat)]
            raw_end = min(en, t + raw_d)
            cut_end, snapped, beat_type = nearest_cut_beat(beats, t, raw_end, en, rhythm)
            d = cut_end - t
            if d < 0.20:
                break

            item = pop_scene(pools, needs, d, allow_fallback)
            if item is None:
                missing.append({"story_part": block.get("story_part"), "scene_need": "|".join(needs), "time_sec": round(t, 3)})
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
                "story_part": block.get("story_part"),
                "story_chapter": needs[0] if needs else "other",
                "target_section": needs[0] if needs else "other",
                "music_mode": rhythm,
                "rhythm_reason": f"120_visual_ai_{block.get('story_part')}_{rhythm}",
                "beat_snapped": bool(snapped),
                "beat_type": beat_type,
                "director_note": block.get("notes", ""),
            })
            timeline.append(row)
            t += d
            k += 1

    data = {
        "ok": True,
        "module": "120_visual_ai_story_beat_planner",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style_profile": a.style_profile,
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": duration_stats(timeline),
        "beat_snap_count": sum(1 for x in timeline if x.get("beat_snapped")),
        "scene_counts": {s: sum(1 for x in timeline if x.get("scene_tag") == s) for s in SCENE_TAGS},
        "missing_count": len(missing),
        "missing": missing,
        "items": timeline,
    }

    # Exporter 115 uses this file.
    write_json(project / "stt_beat_snapped_beauty_timeline_v1.json", data)
    write_json(project / "stt_visual_ai_story_beat_timeline_v1.json", data)
    write_json(out / "stt_visual_ai_story_beat_timeline_v1.json", data)
    write_csv(out / "VISUAL_AI_STORY_BEAT_TIMELINE.csv", timeline, [
        "index", "story_part", "scene_tag", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "source_in_sec", "music_mode", "beat_snapped", "beat_type", "confidence", "top_tags", "beauty_score", "motion_class", "file"
    ])
    write_csv(out / "MISSING_VISUAL_AI_SCENES.csv", missing, ["story_part", "scene_need", "time_sec"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": duration_stats(timeline),
        "beat_snap_count": data["beat_snap_count"],
        "scene_counts": data["scene_counts"],
        "missing_count": len(missing),
        "fix": "120_visual_ai_story_beat_planner",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
