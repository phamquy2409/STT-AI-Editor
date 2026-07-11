from __future__ import annotations

import argparse, csv, json, os, subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}
SECTION_ORDER = ["intro", "story", "build", "climax", "ending"]


def read_json(path: str | Path) -> dict[str, Any]:
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: str | Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def outdir(project: Path, name: str) -> Path:
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def norm(path: str | Path) -> str:
    return str(path).replace("\\", "/").lower()


def media_duration(path: str | Path) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and (r.stdout or "").strip():
            return float((r.stdout or "").strip())
    except Exception:
        pass
    return 0.0


def load_beats(project: Path) -> list[dict[str, Any]]:
    d = read_json(project / "stt_precise_beat_grid_v2.json")
    return list(d.get("beats") or [])


def load_music_duration(project: Path) -> float:
    for name in ["stt_precise_beat_grid_v2.json", "stt_music_director_map_v1.json", "stt_music_beat_map_v1.json"]:
        d = read_json(project / name)
        p = str(d.get("music_file") or "")
        if p and Path(p).exists():
            return media_duration(p)
    return 0.0


def beauty_maps(project: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path, by_name = {}, {}
    for row in d.get("items", []):
        p = norm(row.get("file", ""))
        n = str(row.get("filename") or "").lower()
        if p:
            by_path[p] = row
        if n:
            by_name.setdefault(n, row)
    return by_path, by_name


def infer_story_section(path: Path, order_pos: float) -> str:
    s = str(path).replace("\\", "/").lower()
    if any(k in s for k in ["decor", "detail", "ring", "dress", "shoes", "flower", "venue", "location", "hotel"]):
        return "intro"
    if any(k in s for k in ["makeup", "prep", "bride", "groom", "portrait", "couple", "firstlook", "first look"]):
        return "story"
    if any(k in s for k in ["gia tien", "gia_tien", "ruoc dau", "ruoc_dau", "ceremony", "church", "nha tho", "altar", "le gia"]):
        return "build"
    if any(k in s for k in ["stage", "reception", "toast", "cake", "champagne", "dance", "party", "kiss", "confetti"]):
        return "climax"
    if any(k in s for k in ["ending", "thank", "family", "guest", "bye"]):
        return "ending"
    if order_pos < 0.12:
        return "intro"
    if order_pos < 0.38:
        return "story"
    if order_pos < 0.64:
        return "build"
    if order_pos < 0.86:
        return "climax"
    return "ending"


def list_sources(source: Path, project: Path, min_beauty: float, allow_review: bool) -> list[dict[str, Any]]:
    by_path, by_name = beauty_maps(project)
    files = []
    for ext in VIDEO_EXTS:
        files.extend(source.rglob(f"*{ext}"))
    files = sorted(set(files), key=lambda p: str(p).lower())
    total = max(1, len(files))
    rows = []
    for i, p in enumerate(files):
        b = by_path.get(norm(p)) or by_name.get(p.name.lower()) or {}
        score = fnum(b.get("beauty_score"), 48 if allow_review else 0)
        cls = str(b.get("beauty_class") or ("not_analyzed" if not b else ""))
        motion = str(b.get("motion_class") or "unknown")
        if p.suffix.lower() == ".braw":
            score = max(score, 42)
            cls = cls or "braw_review"
        if score < min_beauty:
            continue
        if motion == "shaky_or_whip" and score < 78:
            continue
        if (not allow_review) and cls in {"review", "bad", "not_analyzed", "braw_not_analyzed"}:
            continue
        pos = i / total
        rows.append({
            "filename": p.name,
            "file": str(p),
            "_source_order": i,
            "target_section": infer_story_section(p, pos),
            "beauty_score": score,
            "beauty_class": cls,
            "best_source_in_sec": fnum(b.get("best_source_in_sec"), 0),
            "best_window_sec": fnum(b.get("best_window_sec"), 1.0),
            "usable_for_long": bool(b.get("usable_for_long", score >= 68 and motion != "active")),
            "usable_for_fast": bool(b.get("usable_for_fast", score >= 50 and motion != "shaky_or_whip")),
            "motion_class": motion,
            "reject_reasons": str(b.get("reject_reasons") or ""),
            "media_duration_sec": fnum(b.get("duration_sec"), 0),
        })
    if len(rows) < 60 and min_beauty > 0:
        return list_sources(source, project, min_beauty=0, allow_review=True)
    return rows


def build_chapter_pools(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    pools = {s: [] for s in SECTION_ORDER}
    for r in rows:
        sec = str(r.get("target_section") or "story")
        if sec not in pools:
            sec = "story"
        pools[sec].append(dict(r))
    for sec in pools:
        pools[sec] = sorted(pools[sec], key=lambda x: int(x.get("_source_order", 0)))
    return pools


def product_chapters(target_seconds: int) -> list[dict[str, Any]]:
    ratios = [
        ("intro", 0.00, 0.10, "quiet_hold"),
        ("story", 0.10, 0.34, "story_medium"),
        ("build", 0.34, 0.62, "emotion_long"),
        ("climax", 0.62, 0.86, "climax_fast"),
        ("ending", 0.86, 1.00, "ending_hold"),
    ]
    return [{"section": s, "start_sec": round(target_seconds*a,3), "end_sec": round(target_seconds*b,3), "mode": m, "note": "single_song_story_order"} for s,a,b,m in ratios]


def pattern_for_mode(mode: str) -> list[float]:
    if mode == "quiet_hold":
        return [3.2, 4.8, 2.4, 5.6]
    if mode == "story_medium":
        return [1.6, 2.4, 1.1, 3.2, 0.9, 2.8]
    if mode == "emotion_long":
        return [4.8, 3.2, 6.2, 2.6, 5.5]
    if mode == "climax_fast":
        return [0.42, 0.58, 0.75, 0.48, 1.05, 0.62, 1.4]
    if mode == "ending_hold":
        return [4.2, 3.0, 5.8, 2.4, 6.8]
    return [1.5, 2.5, 1.0, 3.0]


def nearest_beat(beats: list[dict[str, Any]], target: float, min_t: float, max_t: float, mode: str) -> tuple[float, bool, str]:
    if not beats:
        return target, False, "no_grid"
    need_strength = 0.78 if mode in {"quiet_hold", "emotion_long", "ending_hold"} else 0.55
    candidates = []
    for b in beats:
        t = fnum(b.get("time_sec"), 0)
        if t < min_t:
            continue
        if t > max_t:
            break
        strength = fnum(b.get("strength"), 0.5)
        if strength >= need_strength:
            candidates.append((abs(t - target), -strength, t, str(b.get("type", ""))))
    if not candidates:
        for b in beats:
            t = fnum(b.get("time_sec"), 0)
            if min_t <= t <= max_t:
                candidates.append((abs(t - target), -fnum(b.get("strength"), 0.5), t, str(b.get("type", ""))))
    if not candidates:
        return target, False, "no_candidate"
    candidates.sort()
    return round(candidates[0][2], 4), True, candidates[0][3]


def pop_ordered(pools: dict[str, list[dict[str, Any]]], section: str, duration: float) -> dict[str, Any] | None:
    section_order = [section] + [s for s in SECTION_ORDER if s != section]
    for sec in section_order:
        arr = pools.get(sec, [])
        for i, item in enumerate(arr):
            motion = str(item.get("motion_class") or "")
            score = fnum(item.get("beauty_score"), 0)
            if duration >= 3.0:
                if motion not in {"active", "shaky_or_whip"} and score >= 42:
                    return arr.pop(i)
            else:
                if motion != "shaky_or_whip" or duration <= 0.55:
                    return arr.pop(i)
    return None


def duration_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [fnum(x.get("duration_sec"), 0) for x in items if fnum(x.get("duration_sec"), 0) > 0]
    if not vals:
        return {}
    xs = sorted(vals)
    def pct(p: float) -> float:
        return round(xs[int(round((len(xs)-1)*p))], 3)
    return {
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(sum(vals)/len(vals), 3),
        "p10": pct(0.10),
        "p50": pct(0.50),
        "p90": pct(0.90),
        "under_0_7s": sum(1 for v in vals if v < 0.7),
        "over_3s": sum(1 for v in vals if v > 3.0),
        "over_5s": sum(1 for v in vals if v > 5.0),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="114B Story-ordered single-song beat beauty timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--style-profile", default="single_song_report_3_4min")
    p.add_argument("--target-seconds", type=int, default=0, help="0 = use music duration, capped to 240s")
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--min-beauty", type=float, default=42)
    p.add_argument("--allow-review", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "story_ordered_single_song_114b")
    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "story_order_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    music_dur = load_music_duration(project)
    target = int(a.target_seconds)
    if target <= 0:
        target = int(max(90, min(240, music_dur - 2))) if music_dur > 0 else 210

    beats = load_beats(project)
    rows = list_sources(source, project, min_beauty=a.min_beauty, allow_review=a.allow_review)
    pools = build_chapter_pools(rows)
    chapters = product_chapters(target)

    timeline = []
    for ch in chapters:
        if len(timeline) >= a.target_shots:
            break
        section, mode = ch["section"], ch["mode"]
        st, en = fnum(ch["start_sec"], 0), fnum(ch["end_sec"], 0)
        pat = pattern_for_mode(mode)
        t, k = st, 0
        while t < en - 0.15 and len(timeline) < a.target_shots:
            raw_d = pat[k % len(pat)]
            target_end = min(en, t + raw_d)
            min_gap = 0.30 if mode == "climax_fast" else 0.70
            max_gap = 1.4 if mode == "climax_fast" else 6.5
            snap_end, snapped, beat_type = nearest_beat(
                beats, target_end, t + min_gap, min(en, t + max_gap, target_end + max(0.20, raw_d * 0.35)), mode
            )
            if snap_end <= t + 0.18:
                snap_end, snapped = target_end, False
            d = snap_end - t
            if d < 0.20:
                break
            item = pop_ordered(pools, section, d)
            if item is None:
                break
            motion = str(item.get("motion_class") or "")
            if motion == "active" and d > 1.4:
                d, snap_end, snapped = 1.4, t + 1.4, False
            if motion == "shaky_or_whip" and d > 0.5:
                d, snap_end, snapped = 0.5, t + 0.5, False
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
                "music_mode": mode,
                "story_chapter": section,
                "rhythm_reason": f"114B_story_ordered_{section}_{mode}",
                "beat_snapped": bool(snapped),
                "beat_type": beat_type,
                "director_note": ch["note"],
            })
            timeline.append(row)
            t += d
            k += 1

    stats = duration_stats(timeline)
    data = {
        "ok": True,
        "module": "114B_story_ordered_single_song",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "style_profile": a.style_profile,
        "target_seconds": target,
        "music_duration_sec": round(music_dur, 3),
        "source_candidate_count": len(rows),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": stats,
        "beat_snap_count": sum(1 for x in timeline if x.get("beat_snapped")),
        "chapter_counts": {s: sum(1 for x in timeline if x.get("story_chapter") == s) for s in SECTION_ORDER},
        "items": timeline,
    }
    write_json(project / "stt_beat_snapped_beauty_timeline_v1.json", data)
    write_json(project / "stt_story_ordered_single_song_timeline_v1.json", data)
    write_json(out / "stt_story_ordered_single_song_timeline_v1.json", data)
    write_csv(out / "STORY_ORDERED_SINGLE_SONG_TIMELINE_114B.csv", timeline, [
        "index", "story_chapter", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "source_in_sec", "music_mode", "beat_snapped", "beat_type", "beauty_score", "beauty_class", "motion_class", "file"
    ])
    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "target_seconds": target,
        "music_duration_sec": round(music_dur, 3),
        "source_candidate_count": len(rows),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": stats,
        "beat_snap_count": data["beat_snap_count"],
        "chapter_counts": data["chapter_counts"],
        "fix": "114B_story_ordered_single_song",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
