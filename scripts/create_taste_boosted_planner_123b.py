from __future__ import annotations
import argparse, json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from taste_ai_common import *

def load_ai(project: Path) -> list[dict[str, Any]]:
    return list(read_json(project / "stt_visual_ai_scene_tags_v1.json").get("items") or [])

def load_profile(project: Path) -> dict[str, Any]:
    return read_json(project / "stt_taste_profile_v1.json")

def camera_group(name: str, path: str) -> str:
    import re
    s = f"{name} {path}".lower()
    if any(x in s for x in ["drone", "dji", "mavic", "flycam", "air 2", "air3", "mini 3", "mini3", "mini 4"]):
        return "drone"
    stem = Path(name).stem.lower()
    m = re.match(r"([a-z]+)[-_ ]?(\d{1,3})", stem)
    if m:
        return m.group(1).upper()
    m = re.match(r"([a-z]+)", stem)
    if m:
        return m.group(1).upper()
    parent = Path(path).parent.name.strip()
    return parent or "unknown"

def section_name(pos: float) -> str:
    if pos < 0.12:
        return "intro"
    if pos < 0.35:
        return "story"
    if pos < 0.58:
        return "build"
    if pos < 0.82:
        return "climax"
    return "ending"

def target_duration(profile: dict[str, Any], section: str, fallback: float) -> float:
    sec = dict(profile.get("section_profiles") or {}).get(section, {})
    val = fnum(sec.get("duration_median"), 0)
    if val <= 0:
        val = fnum(sec.get("duration_avg"), 0)
    if val <= 0:
        val = fallback
    if section in {"intro", "climax", "ending"}:
        return max(0.7, min(6.5, val))
    return max(0.5, min(5.0, val))

def nearest_beat(beats, t: float, desired_end: float, max_end: float) -> tuple[float, bool]:
    if not beats:
        return min(desired_end, max_end), False
    candidates = []
    for b in beats:
        bt = fnum(b.get("time_sec"), 0)
        if bt <= t + 0.35:
            continue
        if bt > min(max_end, desired_end + 0.65):
            break
        candidates.append((abs(bt - desired_end), -fnum(b.get("strength"), 0.5), bt))
    if not candidates:
        return min(desired_end, max_end), False
    candidates.sort()
    return round(candidates[0][2], 4), True

def preference_maps(profile: dict[str, Any]):
    used = {}
    for x in profile.get("file_preferences") or []:
        p = norm_path(x.get("file"))
        n = str(x.get("filename") or "").lower()
        w = fnum(x.get("preference_weight"), 1.0)
        if p:
            used[p] = max(used.get(p, 0), w)
        if n:
            used[n] = max(used.get(n, 0), w)
    return used

def build_candidates(project: Path, rows: list[dict[str, Any]], profile: dict[str, Any]):
    beauty_by_path, beauty_by_name = load_beauty(project)
    used_map = preference_maps(profile)
    out = []
    n = max(1, len(rows))
    for i, r in enumerate(rows):
        p = norm_path(r.get("file"))
        name = str(r.get("filename") or filename(p)).lower()
        b = beauty_by_path.get(p) or beauty_by_name.get(name) or {}
        cam = camera_group(name, p)
        row = dict(r)
        row["_source_order"] = int(row.get("_source_order", i))
        row["_source_pos"] = i / n
        row["camera_group"] = cam
        row["beauty_score"] = fnum(b.get("beauty_score"), 55)
        row["best_source_in_sec"] = fnum(b.get("best_source_in_sec"), 0)
        row["media_duration_sec"] = fnum(b.get("duration_sec"), fnum(r.get("media_duration_sec"), 0))
        row["taste_used_weight"] = max(used_map.get(p, 0), used_map.get(name, 0), 1.0)
        out.append(row)
    return out

def candidate_score(item: dict[str, Any], section: str, profile: dict[str, Any], used_counts: dict[str, int]) -> float:
    sec = dict(profile.get("section_profiles") or {}).get(section, {})
    tag_pref = dict(sec.get("preferred_tags") or {})
    cam_pref = dict(sec.get("preferred_cameras") or {})
    tag = str(item.get("scene_tag") or "other")
    cam = str(item.get("camera_group") or "unknown")
    beauty = fnum(item.get("beauty_score"), 55)
    taste = fnum(item.get("taste_used_weight"), 1.0)
    key = norm_path(item.get("file")) or str(item.get("filename") or "").lower()
    reused = used_counts.get(key, 0)

    score = beauty * 0.45
    score += taste * 18.0
    score += math.log2(1 + fnum(tag_pref.get(tag), 0)) * 9.0
    score += math.log2(1 + fnum(cam_pref.get(cam), 0)) * 5.0

    if section == "intro":
        if tag in {"decor", "detail_beauty", "cdcr_portrait", "first_look"}:
            score += 20
        if cam == "drone":
            score += 18
    elif section == "climax":
        if tag in {"cdcr_portrait", "vow", "reception_stage", "party", "wedding_game", "family_emotion"}:
            score += 24
        score += max(0, beauty - 70) * 0.8
    elif section == "ending":
        if tag in {"ending", "cdcr_portrait", "first_look", "family_emotion"}:
            score += 28
        if tag in {"getting_ready", "guest_food", "wedding_game"}:
            score -= 35

    score -= reused * 28.0
    return score

def main() -> None:
    p = argparse.ArgumentParser(description="123B Taste boosted wedding planner.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="single_song_report_3_4min")
    p.add_argument("--target-seconds", type=float, default=210.0)
    p.add_argument("--target-shots", type=int, default=180)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "taste_boosted_planner_123b")
    profile = load_profile(project)
    rows = load_ai(project)

    if not profile.get("ok"):
        res = {"ok": False, "error": "NO_TASTE_PROFILE", "message": "Run 123 learner first."}
        write_json(out / "TASTE_PLANNER_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not rows:
        res = {"ok": False, "error": "NO_VISUAL_AI_TAGS", "message": "Run visual recognizer first."}
        write_json(out / "TASTE_PLANNER_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    candidates = build_candidates(project, rows, profile)
    beats = load_beats(project)
    used_counts: dict[str, int] = defaultdict(int)
    timeline = []
    t = 0.0
    while t < a.target_seconds - 0.3 and len(timeline) < a.target_shots:
        pos = t / max(1.0, a.target_seconds)
        section = section_name(pos)
        fallback = 1.0 if section in {"intro", "climax"} else 1.8
        desired = target_duration(profile, section, fallback)
        end, snapped = nearest_beat(beats, t, t + desired, a.target_seconds)
        dur = max(0.4, end - t)

        ranked = []
        for item in candidates:
            key = norm_path(item.get("file")) or str(item.get("filename") or "").lower()
            if used_counts.get(key, 0) >= 1:
                continue
            sc = candidate_score(item, section, profile, used_counts)
            ranked.append((sc, item))
        if not ranked:
            break
        ranked.sort(key=lambda x: x[0], reverse=True)
        score, item = ranked[0]
        key = norm_path(item.get("file")) or str(item.get("filename") or "").lower()
        used_counts[key] += 1

        src_in = fnum(item.get("best_source_in_sec"), 0)
        media_dur = fnum(item.get("media_duration_sec"), 0)
        if media_dur > 0 and src_in + dur > media_dur - 0.05:
            src_in = max(0.0, media_dur - dur - 0.08)

        row = dict(item)
        row.update({
            "index": len(timeline) + 1,
            "timeline_start_sec": round(t, 3),
            "timeline_end_sec": round(t + dur, 3),
            "duration_sec": round(dur, 3),
            "source_in_sec": round(src_in, 3),
            "source_out_sec": round(src_in + dur, 3),
            "source_duration_sec": round(dur, 3),
            "story_part": section,
            "story_chapter": section,
            "target_section": section,
            "music_mode": "taste_ai",
            "rhythm_reason": f"123B_taste_ai_{section}",
            "beat_snapped": bool(snapped),
            "taste_score": round(score, 3),
            "taste_profile": profile.get("profile_name"),
        })
        timeline.append(row)
        t += dur

    data = {
        "ok": True,
        "module": "123B_taste_boosted_planner",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style_profile": a.style_profile,
        "taste_profile": profile.get("profile_name"),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": duration_stats(timeline),
        "scene_counts": count_tags(timeline),
        "camera_counts": dict(__import__("collections").Counter(str(x.get("camera_group") or "unknown") for x in timeline)),
        "items": timeline,
    }
    write_json(project / "stt_beat_snapped_beauty_timeline_v1.json", data)
    write_json(project / "stt_taste_boosted_timeline_v1.json", data)
    write_json(out / "stt_taste_boosted_timeline_v1.json", data)
    write_csv(out / "TASTE_BOOSTED_TIMELINE.csv", timeline, [
        "index", "story_part", "scene_tag", "camera_group", "filename",
        "timeline_start_sec", "duration_sec", "source_in_sec",
        "taste_score", "taste_used_weight", "beauty_score",
        "beat_snapped", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(timeline),
        "timeline_seconds": data["timeline_seconds"],
        "duration_stats": data["duration_stats"],
        "scene_counts": data["scene_counts"],
        "camera_counts": data["camera_counts"],
        "fix": "123B_taste_boosted_planner",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
