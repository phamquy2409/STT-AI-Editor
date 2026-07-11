from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from taste_ai_common import *

def find_finished_json(project: Path, explicit: str = "") -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None

    candidates = [
        project / "stt_finished_project_xml_v1.json",
        project / "stt_finished_project_xml_recovery_v1.json",
        project / "stt_final_timeline_recovery_v1.json",
    ]
    for p in candidates:
        if p.exists():
            d = read_json(p)
            if d.get("clips") or d.get("items"):
                return p

    export_candidates = sorted(
        project.glob("exports/**/*finished*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    for p in export_candidates:
        d = read_json(p)
        if d.get("clips") or d.get("items"):
            return p
    return None

def load_finished_clips(path: Path) -> list[dict[str, Any]]:
    d = read_json(path)
    clips = list(d.get("clips") or d.get("items") or d.get("timeline") or [])
    out = []
    for i, c in enumerate(clips):
        p = str(
            c.get("resolved_file")
            or c.get("file")
            or c.get("path")
            or c.get("pathurl")
            or c.get("source_file")
            or ""
        )
        name = str(c.get("filename") or c.get("name") or Path(p).name)
        st = fnum(c.get("timeline_start_sec"), fnum(c.get("start_sec"), fnum(c.get("start"), 0)))
        en = fnum(c.get("timeline_end_sec"), fnum(c.get("end_sec"), fnum(c.get("end"), 0)))
        dur = fnum(c.get("duration_sec"), en - st)
        src_in = fnum(c.get("source_in_sec"), fnum(c.get("in_sec"), fnum(c.get("in"), 0)))
        src_out = fnum(c.get("source_out_sec"), fnum(c.get("out_sec"), fnum(c.get("out"), src_in + dur)))
        if dur <= 0 and en > st:
            dur = en - st
        if en <= st and dur > 0:
            en = st + dur
        if not p and not name:
            continue
        out.append({
            "index": i,
            "file": p,
            "filename": name,
            "timeline_start_sec": st,
            "timeline_end_sec": en,
            "duration_sec": dur,
            "source_in_sec": src_in,
            "source_out_sec": src_out,
            "raw": c,
        })
    return out

def camera_group(name: str, path: str) -> str:
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

def main() -> None:
    p = argparse.ArgumentParser(description="123 Taste AI learner from finished user edit.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--finished-json", default="")
    p.add_argument("--profile-name", default="single_song_report_3_4min")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "taste_ai_learner_123")
    finished_json = find_finished_json(project, a.finished_json)

    if not finished_json:
        res = {
            "ok": False,
            "error": "NO_FINISHED_PROJECT_JSON",
            "message": "Run module 091D first to create stt_finished_project_xml_v1.json.",
            "expected": str(project / "stt_finished_project_xml_v1.json"),
        }
        write_json(out / "TASTE_AI_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    clips = load_finished_clips(finished_json)
    if not clips:
        res = {"ok": False, "error": "NO_FINISHED_CLIPS", "finished_json": str(finished_json)}
        write_json(out / "TASTE_AI_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    visual = read_json(project / "stt_visual_ai_scene_tags_v1.json")
    visual_items = list(visual.get("items") or [])
    visual_by_path = {norm_path(x.get("file")): x for x in visual_items if x.get("file")}
    visual_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for x in visual_items:
        visual_by_name[str(x.get("filename") or filename(x.get("file"))).lower()].append(x)

    beauty_by_path, beauty_by_name = load_beauty(project)

    total_end = max((fnum(c.get("timeline_end_sec"), 0) for c in clips), default=0)
    total_end = max(total_end, 1.0)

    file_use = Counter()
    camera_use = Counter()
    tag_use = Counter()
    section_tag_use: dict[str, Counter] = defaultdict(Counter)
    section_camera_use: dict[str, Counter] = defaultdict(Counter)
    section_durations: dict[str, list[float]] = defaultdict(list)
    source_in_values: list[float] = []
    learned_rows = []

    for c in clips:
        pth = norm_path(c.get("file"))
        nam = str(c.get("filename") or filename(pth)).lower()
        pos = fnum(c.get("timeline_start_sec"), 0) / total_end
        sec = section_name(pos)
        dur = fnum(c.get("duration_sec"), 0)
        cam = camera_group(nam, pth)

        vi = visual_by_path.get(pth)
        if not vi:
            candidates = visual_by_name.get(nam, [])
            vi = candidates[0] if candidates else {}
        tag = str((vi or {}).get("scene_tag") or "other")

        bi = beauty_by_path.get(pth) or beauty_by_name.get(nam) or {}
        beauty = fnum(bi.get("beauty_score"), 55)

        file_use[pth or nam] += 1
        camera_use[cam] += 1
        tag_use[tag] += 1
        section_tag_use[sec][tag] += 1
        section_camera_use[sec][cam] += 1
        if dur > 0:
            section_durations[sec].append(dur)
        source_in_values.append(fnum(c.get("source_in_sec"), 0))

        learned_rows.append({
            "index": c.get("index"),
            "filename": nam,
            "file": c.get("file"),
            "camera_group": cam,
            "scene_tag": tag,
            "timeline_section": sec,
            "timeline_start_sec": round(fnum(c.get("timeline_start_sec"), 0), 3),
            "duration_sec": round(dur, 3),
            "source_in_sec": round(fnum(c.get("source_in_sec"), 0), 3),
            "beauty_score": round(beauty, 2),
            "use_count": file_use[pth or nam],
        })

    section_profiles = {}
    for sec in ["intro", "story", "build", "climax", "ending"]:
        durs = section_durations.get(sec, [])
        section_profiles[sec] = {
            "clip_count": len(durs),
            "duration_avg": round(mean(durs), 3),
            "duration_median": round(median(durs), 3),
            "duration_p10": round(pct(durs, 0.10), 3),
            "duration_p90": round(pct(durs, 0.90), 3),
            "preferred_tags": dict(section_tag_use.get(sec, Counter()).most_common()),
            "preferred_cameras": dict(section_camera_use.get(sec, Counter()).most_common()),
        }

    file_preferences = []
    for key, count in file_use.most_common():
        row = next((x for x in learned_rows if norm_path(x.get("file")) == key or x.get("filename") == key), None)
        file_preferences.append({
            "key": key,
            "filename": row.get("filename") if row else Path(key).name,
            "file": row.get("file") if row else key,
            "camera_group": row.get("camera_group") if row else "unknown",
            "scene_tag": row.get("scene_tag") if row else "other",
            "use_count": count,
            "preference_weight": round(1.0 + min(2.0, math.log2(1 + count)), 4),
        })

    profile = {
        "ok": True,
        "module": "123_taste_ai_learner",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "profile_name": a.profile_name,
        "finished_json": str(finished_json),
        "finished_clip_count": len(clips),
        "finished_seconds": round(total_end, 3),
        "unique_used_file_count": len(file_use),
        "camera_usage": dict(camera_use.most_common()),
        "scene_tag_usage": dict(tag_use.most_common()),
        "source_in_stats": {
            "avg": round(mean(source_in_values), 3),
            "median": round(median(source_in_values), 3),
            "p90": round(pct(source_in_values, 0.90), 3),
        },
        "section_profiles": section_profiles,
        "file_preferences": file_preferences,
        "learning_rules": {
            "boost_used_files": True,
            "boost_section_tag_match": True,
            "boost_section_camera_match": True,
            "prefer_user_duration_by_section": True,
            "reserve_high_beauty_for_intro_climax_ending": True,
            "slow_minimum_speed_percent": 50,
        },
    }

    write_json(project / "stt_taste_profile_v1.json", profile)
    write_json(out / "stt_taste_profile_v1.json", profile)
    write_csv(out / "TASTE_AI_FINISHED_TIMELINE.csv", learned_rows, [
        "index", "timeline_section", "scene_tag", "camera_group", "filename",
        "timeline_start_sec", "duration_sec", "source_in_sec", "beauty_score",
        "use_count", "file"
    ])
    write_csv(out / "TASTE_AI_FILE_PREFERENCES.csv", file_preferences, [
        "filename", "camera_group", "scene_tag", "use_count", "preference_weight", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "profile_output": str(project / "stt_taste_profile_v1.json"),
        "finished_json": str(finished_json),
        "finished_clip_count": len(clips),
        "finished_seconds": round(total_end, 3),
        "unique_used_file_count": len(file_use),
        "camera_usage": dict(camera_use.most_common()),
        "scene_tag_usage": dict(tag_use.most_common()),
        "fix": "123_taste_ai_learner",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
