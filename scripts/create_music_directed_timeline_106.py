from music_director_common import *


SECTION_ORDER = ["intro", "story", "build", "climax", "ending"]


def load_director_blocks(project: Path) -> list[dict[str, Any]]:
    manual = project / "stt_music_director_manual.csv"
    rows = read_csv(manual)
    good = []
    allowed = {"quiet_hold", "emotion_long", "story_medium", "build_fast", "climax_fast", "impact_cut", "ending_hold"}
    for r in rows:
        st = fnum(r.get("start_sec"), -1)
        en = fnum(r.get("end_sec"), -1)
        mode = str(r.get("mode") or "").strip()
        if st >= 0 and en > st and mode in allowed:
            good.append({
                "start_sec": round(st, 3),
                "end_sec": round(en, 3),
                "mode": mode,
                "energy": r.get("energy", ""),
                "flux": r.get("flux", ""),
                "note": (r.get("note") or "manual").strip(),
            })
    if good:
        return sorted(good, key=lambda x: fnum(x["start_sec"]))

    d = read_json(project / "stt_music_director_map_v1.json")
    return list(d.get("director_blocks") or [])


def item_section(it: dict[str, Any]) -> str:
    s = str(it.get("target_section") or it.get("section") or "").lower()
    if s in SECTION_ORDER:
        return s
    return "story"


def build_queues(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    q = {s: [] for s in SECTION_ORDER}
    for i, it in enumerate(items):
        row = dict(it)
        row["_source_order"] = i
        q[item_section(row)].append(row)
    for s in q:
        q[s] = sorted(q[s], key=lambda x: int(x.get("_source_order", 0)))
    return q


def preferred_sections(mode: str, global_pos: float) -> list[str]:
    if mode == "quiet_hold":
        return ["intro", "story", "ending"]
    if mode == "emotion_long":
        return ["story", "build", "ending"]
    if mode == "story_medium":
        return ["story", "build", "intro"]
    if mode == "build_fast":
        return ["build", "story", "climax"]
    if mode in {"climax_fast", "impact_cut"}:
        return ["climax", "build", "story"]
    if mode == "ending_hold":
        return ["ending", "story", "build"]
    if global_pos < 0.15:
        return ["intro", "story", "build"]
    if global_pos > 0.82:
        return ["ending", "story", "build"]
    return ["story", "build", "climax"]


def pop_next(queues: dict[str, list[dict[str, Any]]], prefs: list[str]) -> dict[str, Any] | None:
    for s in prefs:
        if queues.get(s):
            return queues[s].pop(0)
    for s in SECTION_ORDER:
        if queues.get(s):
            return queues[s].pop(0)
    return None


def mode_pattern(mode: str) -> list[float]:
    if mode == "quiet_hold":
        return [3.8, 5.6, 2.7, 7.2, 4.4]
    if mode == "emotion_long":
        return [4.8, 7.5, 3.2, 6.2, 9.0, 2.8]
    if mode == "story_medium":
        return [1.4, 2.4, 0.9, 3.6, 1.8, 4.8, 1.1]
    if mode == "build_fast":
        return [0.85, 1.25, 0.55, 1.8, 0.72, 2.6, 1.05, 3.4]
    if mode == "climax_fast":
        return [0.32, 0.45, 0.65, 0.38, 0.95, 0.52, 1.4, 0.35, 2.2]
    if mode == "impact_cut":
        return [0.22, 0.35, 0.50, 0.28, 0.75, 0.40, 1.10]
    if mode == "ending_hold":
        return [3.2, 5.8, 2.4, 7.8, 4.5, 9.0]
    return [1.2, 2.4, 0.8, 3.6]


def fill_block(block: dict[str, Any], queues: dict[str, list[dict[str, Any]]], target_seconds: float) -> list[dict[str, Any]]:
    st = fnum(block["start_sec"])
    en = min(fnum(block["end_sec"]), target_seconds)
    mode = str(block["mode"])
    if en <= st:
        return []

    total = en - st
    pat = mode_pattern(mode)
    items = []
    t = st
    i = 0
    while t < en - 0.15:
        global_pos = t / max(1, target_seconds)
        prefs = preferred_sections(mode, global_pos)
        src = pop_next(queues, prefs)
        if src is None:
            break
        desired = pat[i % len(pat)]
        if i == 0 and mode in {"quiet_hold", "emotion_long", "ending_hold"}:
            desired = max(desired, total * 0.18)
        if t + desired > en:
            desired = en - t
        if desired < 0.22:
            break

        row = dict(src)
        row.update({
            "timeline_start_sec": round(t, 3),
            "timeline_end_sec": round(t + desired, 3),
            "duration_sec": round(desired, 3),
            "source_in_sec": 0.0,
            "source_out_sec": round(desired, 3),
            "source_duration_sec": round(desired, 3),
            "music_mode": mode,
            "music_block_start": st,
            "music_block_end": en,
            "rhythm_reason": f"music_director_{mode}",
            "director_note": block.get("note", ""),
        })
        items.append(row)
        t += desired
        i += 1
    return items


def main() -> None:
    p = argparse.ArgumentParser(description="106 build timeline from music director map.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "music_directed_timeline_106")

    base = load_source_timeline(project)
    blocks = load_director_blocks(project)

    if not base:
        res = {"ok": False, "error": "NO_SOURCE_TIMELINE", "message": "Run 096 first."}
        write_json(out / "music_directed_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return
    if not blocks:
        res = {"ok": False, "error": "NO_DIRECTOR_MAP", "message": "Run 105 first."}
        write_json(out / "music_directed_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    source_items = list(base.get("items") or [])[:max(a.target_shots, 1)]
    queues = build_queues(source_items)

    items = []
    for b in blocks:
        if fnum(b["start_sec"]) >= a.target_seconds:
            continue
        items.extend(fill_block(b, queues, a.target_seconds))

    for i, it in enumerate(items, start=1):
        it["index"] = i

    stats = duration_stats(items)
    mode_counts = {m: sum(1 for it in items if it.get("music_mode") == m) for m in sorted({str(it.get("music_mode")) for it in items})}

    data = {
        "ok": True,
        "module": "106_music_directed_timeline",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style_profile": a.style_profile,
        "target_seconds": a.target_seconds,
        "target_shots": a.target_shots,
        "timeline_count": len(items),
        "timeline_seconds": items[-1]["timeline_end_sec"] if items else 0,
        "duration_stats": stats,
        "mode_counts": mode_counts,
        "items": items,
    }
    write_json(project / "stt_music_directed_timeline_v1.json", data)
    write_json(out / "stt_music_directed_timeline_v1.json", data)
    write_csv(out / "MUSIC_DIRECTED_TIMELINE.csv", items, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "music_mode", "rhythm_reason", "director_note", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(items),
        "timeline_seconds": items[-1]["timeline_end_sec"] if items else 0,
        "duration_stats": stats,
        "mode_counts": mode_counts,
        "fix": "106_music_directed_timeline",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
