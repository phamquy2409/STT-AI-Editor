from quality_music_common import *


SECTION_ORDER = ["intro", "story", "build", "climax", "ending"]


def item_section(it: dict[str, Any]) -> str:
    s = str(it.get("target_section") or it.get("section") or "").lower()
    return s if s in SECTION_ORDER else "story"


def visual_bucket(it: dict[str, Any]) -> str:
    motion = str(it.get("motion_class") or "").lower()
    score = fnum(it.get("quality_score"), 50)
    if score >= 76 and motion in {"stable", "static"}:
        return "stable_good"
    if motion in {"active"}:
        return "active_ok"
    if motion in {"shaky_or_whip"}:
        return "fast_only"
    if score >= 65:
        return "usable"
    return "weak"


def build_pools(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    pools = {s: [] for s in SECTION_ORDER}
    for idx, it in enumerate(items):
        row = dict(it)
        row["_order"] = idx
        pools[item_section(row)].append(row)

    # best quality first within chapter, but keep rough order as secondary
    for s in pools:
        pools[s] = sorted(pools[s], key=lambda x: (-fnum(x.get("quality_score"), 0), int(x.get("_order", 0))))
    return pools


def preferred_sections(mode: str, pos: float) -> list[str]:
    if mode == "quiet_hold":
        return ["intro", "story", "ending"]
    if mode == "emotion_long":
        return ["story", "build", "ending"]
    if mode == "story_medium":
        return ["story", "intro", "build"]
    if mode == "build_fast":
        return ["build", "story", "climax"]
    if mode in {"climax_fast", "impact_cut"}:
        return ["climax", "build", "story"]
    if mode == "ending_hold":
        return ["ending", "story", "build"]
    return ["story", "build", "climax"]


def accept_for_mode(it: dict[str, Any], mode: str, desired_duration: float) -> bool:
    bucket = visual_bucket(it)
    if desired_duration >= 3.0:
        return bucket in {"stable_good", "usable"} and str(it.get("motion_class")) not in {"active", "shaky_or_whip"}
    if mode in {"climax_fast", "impact_cut", "build_fast"}:
        return bucket in {"stable_good", "active_ok", "usable"}
    return bucket != "weak"


def pop_item(pools: dict[str, list[dict[str, Any]]], prefs: list[str], mode: str, desired_duration: float) -> dict[str, Any] | None:
    # first pass: quality + visual duration fit
    for sec_name in prefs:
        arr = pools.get(sec_name, [])
        for i, it in enumerate(arr):
            if accept_for_mode(it, mode, desired_duration):
                return arr.pop(i)
    # second pass: anything except weak/shaky long
    for sec_name in prefs + SECTION_ORDER:
        arr = pools.get(sec_name, [])
        for i, it in enumerate(arr):
            if desired_duration >= 3.0 and str(it.get("motion_class")) in {"active", "shaky_or_whip"}:
                continue
            if visual_bucket(it) != "weak":
                return arr.pop(i)
    return None


def mode_pattern(mode: str) -> list[float]:
    # more decisive. Long blocks really hold, fast blocks really cut.
    if mode == "quiet_hold":
        return [5.5, 3.8, 7.0, 4.6]
    if mode == "emotion_long":
        return [7.2, 4.8, 9.0, 3.6, 6.2]
    if mode == "story_medium":
        return [2.2, 1.1, 3.4, 1.6, 4.5, 0.9]
    if mode == "build_fast":
        return [1.0, 0.62, 1.45, 0.55, 2.2, 0.80, 3.0]
    if mode == "climax_fast":
        return [0.35, 0.48, 0.62, 0.42, 0.90, 0.55, 1.25, 0.38]
    if mode == "impact_cut":
        return [0.22, 0.32, 0.44, 0.28, 0.60, 0.36]
    if mode == "ending_hold":
        return [6.2, 4.4, 8.5, 3.6, 7.2]
    return [1.5, 2.5, 1.0, 3.5]


def fill_block(block: dict[str, Any], pools: dict[str, list[dict[str, Any]]], target_seconds: float) -> list[dict[str, Any]]:
    st = fnum(block.get("start_sec"), 0)
    en = min(fnum(block.get("end_sec"), st), target_seconds)
    mode = str(block.get("mode") or "story_medium")
    if en <= st:
        return []

    pat = mode_pattern(mode)
    t = st
    out: list[dict[str, Any]] = []
    i = 0
    while t < en - 0.15:
        d = pat[i % len(pat)]
        if t + d > en:
            d = en - t
        if d < 0.22:
            break

        pos = t / max(1.0, target_seconds)
        prefs = preferred_sections(mode, pos)
        src = pop_item(pools, prefs, mode, d)
        if src is None:
            break

        # If chosen shot is active, shorten it even in medium modes.
        if str(src.get("motion_class")) == "active" and d > 1.4:
            d = min(d, 1.4)
        if str(src.get("motion_class")) == "shaky_or_whip":
            d = min(d, 0.6)

        row = dict(src)
        row.update({
            "timeline_start_sec": round(t, 3),
            "timeline_end_sec": round(t + d, 3),
            "duration_sec": round(d, 3),
            "source_in_sec": 0.0,
            "source_out_sec": round(d, 3),
            "source_duration_sec": round(d, 3),
            "music_mode": mode,
            "music_block_start": st,
            "music_block_end": en,
            "rhythm_reason": f"quality_music_v2_{mode}",
            "director_note": block.get("note", ""),
            "visual_bucket": visual_bucket(src),
        })
        out.append(row)
        t += d
        i += 1
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="110 Music Directed Timeline V2 with source quality gate.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "music_directed_quality_timeline_110")

    base = read_json(project / "stt_quality_filtered_source_timeline_v1.json") or load_base_timeline(project)
    blocks = load_director_blocks(project)

    if not base:
        res = {"ok": False, "error": "NO_QUALITY_FILTERED_TIMELINE", "message": "Run 109 first."}
        write_json(out / "quality_music_timeline_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not blocks:
        res = {"ok": False, "error": "NO_DIRECTOR_BLOCKS", "message": "Run 105 first."}
        write_json(out / "quality_music_timeline_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    items = list(base.get("items") or [])[:max(1, a.target_shots)]
    pools = build_pools(items)

    timeline = []
    for block in blocks:
        if fnum(block.get("start_sec"), 0) >= a.target_seconds:
            continue
        timeline.extend(fill_block(block, pools, float(a.target_seconds)))

    for i, it in enumerate(timeline, start=1):
        it["index"] = i

    stats = duration_stats(timeline)
    mode_counts = {m: sum(1 for it in timeline if it.get("music_mode") == m) for m in sorted({str(it.get("music_mode")) for it in timeline})}
    motion_counts = {m: sum(1 for it in timeline if it.get("motion_class") == m) for m in sorted({str(it.get("motion_class")) for it in timeline})}

    data = {
        "ok": True,
        "module": "110_music_directed_quality_timeline_v2",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style_profile": a.style_profile,
        "target_seconds": a.target_seconds,
        "target_shots": a.target_shots,
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": stats,
        "mode_counts": mode_counts,
        "motion_counts": motion_counts,
        "items": timeline,
    }
    write_json(project / "stt_music_directed_quality_timeline_v2.json", data)
    write_json(out / "stt_music_directed_quality_timeline_v2.json", data)
    write_csv(out / "MUSIC_DIRECTED_QUALITY_TIMELINE_V2.csv", timeline, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "music_mode", "visual_bucket", "quality_score", "quality_class", "motion_class",
        "quality_reject_reasons", "rhythm_reason", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": stats,
        "mode_counts": mode_counts,
        "motion_counts": motion_counts,
        "fix": "110_music_directed_quality_timeline_v2",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
