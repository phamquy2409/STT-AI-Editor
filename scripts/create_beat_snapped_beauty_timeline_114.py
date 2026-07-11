from precise_beat_beauty_common import *


def beauty_maps(project: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path = {}
    by_name = {}
    for row in d.get("items", []):
        p = norm_path(row.get("file", ""))
        n = str(row.get("filename") or "").lower()
        if p:
            by_path[p] = row
        if n:
            by_name.setdefault(n, row)
    return by_path, by_name


def find_all_sources(source: Path, beauty_by_path: dict[str, dict[str, Any]], beauty_by_name: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    files = []
    for ext in VIDEO_EXTS:
        files.extend(source.rglob(f"*{ext}"))
    rows = []
    total = max(1, len(files))
    for i, p in enumerate(sorted(set(files), key=lambda x: str(x).lower())):
        b = beauty_by_path.get(norm_path(p)) or beauty_by_name.get(p.name.lower()) or {}
        score = fnum(b.get("beauty_score"), 45)
        pos = i / total
        sec_name = "intro" if pos < 0.16 else "story" if pos < 0.48 else "build" if pos < 0.70 else "climax" if pos < 0.86 else "ending"
        rows.append({
            "filename": p.name,
            "file": str(p),
            "target_section": sec_name,
            "beauty_score": score,
            "beauty_class": b.get("beauty_class", "not_analyzed"),
            "best_source_in_sec": fnum(b.get("best_source_in_sec"), 0),
            "best_window_sec": fnum(b.get("best_window_sec"), 1.0),
            "usable_for_long": bool(b.get("usable_for_long", score >= 65)),
            "usable_for_fast": bool(b.get("usable_for_fast", score >= 50)),
            "motion_class": b.get("motion_class", "unknown"),
            "reject_reasons": b.get("reject_reasons", ""),
            "duration_sec": fnum(b.get("duration_sec"), 0),
            "_order": i,
        })
    return rows


def visual_bucket(it: dict[str, Any]) -> str:
    score = fnum(it.get("beauty_score"), 45)
    motion = str(it.get("motion_class") or "unknown")
    if score >= 78 and motion in {"stable", "static", "unknown"}:
        return "beautiful_stable"
    if score >= 65 and motion != "shaky_or_whip":
        return "good"
    if score >= 50 and motion in {"active", "unknown"}:
        return "fast_only"
    return "weak"


def section_from_item(it: dict[str, Any]) -> str:
    s = str(it.get("target_section") or "story")
    return s if s in SECTION_ORDER else "story"


def make_pools(rows: list[dict[str, Any]], min_beauty: float) -> dict[str, list[dict[str, Any]]]:
    pools = {s: [] for s in SECTION_ORDER}
    for r in rows:
        if fnum(r.get("beauty_score"), 0) < min_beauty:
            continue
        if "shaky_or_whip" in str(r.get("motion_class")) and fnum(r.get("beauty_score"), 0) < 70:
            continue
        pools[section_from_item(r)].append(dict(r))
    for s in pools:
        pools[s] = sorted(pools[s], key=lambda x: (-fnum(x.get("beauty_score"), 0), int(x.get("_order", 0))))
    return pools


def pattern(mode: str) -> list[float]:
    if mode == "quiet_hold":
        return [4.8, 6.8, 3.2, 7.5]
    if mode == "emotion_long":
        return [6.4, 4.2, 8.2, 3.6, 7.0]
    if mode == "story_medium":
        return [2.1, 1.15, 3.3, 0.9, 4.0, 1.55]
    if mode == "build_fast":
        return [0.9, 1.25, 0.55, 1.8, 0.72, 2.6]
    if mode == "climax_fast":
        return [0.34, 0.46, 0.62, 0.42, 0.90, 0.55, 1.20]
    if mode == "impact_cut":
        return [0.22, 0.32, 0.44, 0.28, 0.62]
    if mode == "ending_hold":
        return [5.6, 4.0, 8.0, 3.4, 7.0]
    return [1.5, 2.5, 1.0, 3.5]


def prefs(mode: str) -> list[str]:
    if mode == "quiet_hold":
        return ["intro", "story", "ending"]
    if mode == "emotion_long":
        return ["story", "ending", "build"]
    if mode == "story_medium":
        return ["story", "intro", "build"]
    if mode == "build_fast":
        return ["build", "story", "climax"]
    if mode in {"climax_fast", "impact_cut"}:
        return ["climax", "build", "story"]
    if mode == "ending_hold":
        return ["ending", "story", "build"]
    return ["story", "build", "climax"]


def pop_for_duration(pools: dict[str, list[dict[str, Any]]], wanted_sections: list[str], duration: float) -> dict[str, Any] | None:
    all_secs = wanted_sections + [s for s in SECTION_ORDER if s not in wanted_sections]
    for sec_name in all_secs:
        arr = pools.get(sec_name, [])
        for i, item in enumerate(arr):
            b = visual_bucket(item)
            if duration >= 3.0:
                if b in {"beautiful_stable", "good"} and bool(item.get("usable_for_long")):
                    return arr.pop(i)
            elif duration <= 1.0:
                if b in {"beautiful_stable", "good", "fast_only"} and bool(item.get("usable_for_fast")):
                    return arr.pop(i)
            else:
                if b in {"beautiful_stable", "good"}:
                    return arr.pop(i)
    # fallback
    for sec_name in all_secs:
        arr = pools.get(sec_name, [])
        if arr:
            return arr.pop(0)
    return None


def nearest_strong_beat(beats: list[dict[str, Any]], target: float, mode: str, min_t: float, max_t: float) -> tuple[float, bool, str]:
    if not beats:
        return target, False, "no_beat_grid"

    strong_min = 0.76 if mode in {"quiet_hold", "emotion_long", "ending_hold"} else 0.55
    candidates = []
    for b in beats:
        t = fnum(b.get("time_sec"), 0)
        if t < min_t or t > max_t:
            continue
        strength = fnum(b.get("strength"), 0.5)
        if strength >= strong_min:
            candidates.append((abs(t - target), t, strength, str(b.get("type", ""))))

    if not candidates:
        for b in beats:
            t = fnum(b.get("time_sec"), 0)
            if min_t <= t <= max_t:
                candidates.append((abs(t - target), t, fnum(b.get("strength"), 0.5), str(b.get("type", ""))))

    if not candidates:
        return target, False, "no_candidate_in_range"
    candidates.sort(key=lambda x: (x[0], -x[2]))
    return round(candidates[0][1], 4), True, candidates[0][3]


def main() -> None:
    p = argparse.ArgumentParser(description="114 Beat-snapped beauty timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--min-beauty", type=float, default=50)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "beat_snapped_beauty_timeline_114")

    beat = read_json(project / "stt_precise_beat_grid_v2.json")
    beats = list(beat.get("beats") or [])
    blocks = load_blocks(project, a.target_seconds)
    by_path, by_name = beauty_maps(project)
    rows = find_all_sources(source, by_path, by_name)
    pools = make_pools(rows, a.min_beauty)

    timeline = []
    for block in blocks:
        if len(timeline) >= a.target_shots:
            break
        st = fnum(block.get("start_sec"), 0)
        en = min(fnum(block.get("end_sec"), st), a.target_seconds)
        mode = str(block.get("mode") or "story_medium")
        if en <= st:
            continue

        t = st
        k = 0
        pat = pattern(mode)
        while t < en - 0.18 and len(timeline) < a.target_shots:
            raw_d = pat[k % len(pat)]
            target_end = min(en, t + raw_d)

            # Snap cut end to beat, but keep duration type.
            min_gap = 0.22 if mode == "impact_cut" else 0.30 if mode == "climax_fast" else 0.55 if mode == "build_fast" else 0.85
            max_gap = 1.25 if mode in {"impact_cut", "climax_fast"} else 2.8 if mode in {"build_fast", "story_medium"} else 8.8
            min_t = t + min_gap
            max_t = min(en, t + max_gap, target_end + max(0.18, raw_d * 0.45))
            snapped_end, snapped, beat_type = nearest_strong_beat(beats, target_end, mode, min_t, max_t)
            if snapped_end <= t + 0.18:
                snapped_end = target_end
                snapped = False
            d = snapped_end - t
            if d < 0.22:
                break

            item = pop_for_duration(pools, prefs(mode), d)
            if item is None:
                break

            # active/shaky never hold long
            motion = str(item.get("motion_class") or "")
            if motion == "active" and d > 1.4:
                d = 1.4
                snapped_end = t + d
            if motion == "shaky_or_whip" and d > 0.48:
                d = 0.48
                snapped_end = t + d

            src_in = fnum(item.get("best_source_in_sec"), 0)
            real_dur = fnum(item.get("duration_sec"), 0)
            if real_dur > 0 and src_in + d > real_dur - 0.05:
                src_in = max(0.0, real_dur - d - 0.08)

            row = dict(item)
            row.update({
                "index": len(timeline) + 1,
                "timeline_start_sec": round(t, 3),
                "timeline_end_sec": round(t + d, 3),
                "duration_sec": round(d, 3),
                "source_in_sec": round(src_in, 3),
                "source_out_sec": round(src_in + d, 3),
                "source_duration_sec": round(d, 3),
                "music_mode": mode,
                "rhythm_reason": f"beat_snapped_beauty_{mode}",
                "beat_snapped": bool(snapped),
                "beat_type": beat_type,
                "visual_bucket": visual_bucket(item),
                "director_note": block.get("note", ""),
            })
            timeline.append(row)
            t = t + d
            k += 1

    stats = duration_stats(timeline)
    data = {
        "ok": True,
        "module": "114_beat_snapped_beauty_timeline",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "style_profile": a.style_profile,
        "target_seconds": a.target_seconds,
        "target_shots": a.target_shots,
        "source_candidate_count": len(rows),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": stats,
        "beat_snap_count": sum(1 for x in timeline if x.get("beat_snapped")),
        "beauty_class_counts": {c: sum(1 for x in timeline if x.get("beauty_class") == c) for c in sorted({str(x.get("beauty_class")) for x in timeline})},
        "mode_counts": {m: sum(1 for x in timeline if x.get("music_mode") == m) for m in sorted({str(x.get("music_mode")) for x in timeline})},
        "items": timeline,
    }
    write_json(project / "stt_beat_snapped_beauty_timeline_v1.json", data)
    write_json(out / "stt_beat_snapped_beauty_timeline_v1.json", data)
    write_csv(out / "BEAT_SNAPPED_BEAUTY_TIMELINE.csv", timeline, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "source_in_sec", "music_mode", "beat_snapped", "beat_type", "beauty_score", "beauty_class",
        "visual_bucket", "motion_class", "rhythm_reason", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "source_candidate_count": len(rows),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": stats,
        "beat_snap_count": data["beat_snap_count"],
        "beauty_class_counts": data["beauty_class_counts"],
        "mode_counts": data["mode_counts"],
        "fix": "114_beat_snapped_beauty_timeline",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
