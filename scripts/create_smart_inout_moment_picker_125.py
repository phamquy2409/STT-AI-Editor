from __future__ import annotations
import argparse, json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from quality_moment_common import *

SECTION_SAFE_TAGS = {
    "intro": {"decor","detail_beauty","cdcr_portrait","first_look","ending"},
    "story": {"getting_ready","first_look","cdcr_portrait","detail_beauty","ceremony_giatien","church_ceremony","vow","ruoc_dau","family_emotion"},
    "build": {"ceremony_giatien","church_ceremony","vow","ruoc_dau","family_emotion","family_photo","reception_stage","cdcr_portrait"},
    "climax": {"reception_stage","wedding_game","party","cdcr_portrait","vow","family_emotion"},
    "ending": {"ending","cdcr_portrait","first_look","family_emotion","detail_beauty","decor"},
}

def load_quality(project: Path):
    d = read_json(project / "stt_shot_quality_windows_v3.json")
    by_path, by_name = {}, defaultdict(list)
    for r in d.get("items", []):
        p = norm_path(r.get("file"))
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name[n].append(r)
    return by_path, by_name

def section_of(item: dict[str, Any]) -> str:
    s = str(item.get("story_part") or item.get("story_chapter") or item.get("target_section") or "").lower()
    for key in ["intro","story","build","climax","ending"]:
        if key in s:
            return key
    pos = fnum(item.get("timeline_start_sec"), 0)
    total = max(fnum(item.get("timeline_end_sec"), 0), 1)
    r = pos / total
    if r < 0.12: return "intro"
    if r < 0.35: return "story"
    if r < 0.58: return "build"
    if r < 0.82: return "climax"
    return "ending"

def best_window(q: dict[str, Any], duration: float, min_quality: float):
    media_dur = fnum(q.get("duration_sec"), 0)
    windows = list(q.get("windows") or [])
    candidates = []

    for w in windows:
        score = fnum(w.get("quality_score"), 0)
        if w.get("severe_shake"):
            score -= 40
        if w.get("likely_blur"):
            score -= 25
        if w.get("too_dark") or w.get("too_bright"):
            score -= 12

        center = fnum(w.get("center_sec"), 0)
        start = center - duration / 2
        if media_dur > 0:
            start = max(0.0, min(start, max(0.0, media_dur - duration)))
        end = start + duration

        # Penalize head/tail.
        if media_dur > 0:
            if start < media_dur * 0.06:
                score -= 8
            if end > media_dur * 0.94:
                score -= 8

        candidates.append((score, start, end, w))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    score, start, end, w = candidates[0]
    return {
        "score": round(score, 3),
        "source_in_sec": round(max(0.0, start), 3),
        "source_out_sec": round(max(start, end), 3),
        "window": w,
        "acceptable": score >= min_quality,
    }

def build_replacement_pool(project: Path, quality_by_path):
    visual = read_json(project / "stt_visual_ai_scene_tags_v1.json")
    taste = read_json(project / "stt_taste_profile_v1.json")
    beauty_by_path, beauty_by_name = load_beauty(project)

    pref = {}
    for x in taste.get("file_preferences") or []:
        p = norm_path(x.get("file"))
        n = str(x.get("filename") or "").lower()
        w = fnum(x.get("preference_weight"), 1.0)
        if p:
            pref[p] = max(pref.get(p, 1.0), w)
        if n:
            pref[n] = max(pref.get(n, 1.0), w)

    pool = []
    for r in visual.get("items") or []:
        p = norm_path(r.get("file"))
        name = str(r.get("filename") or Path(p).name).lower()
        if not p or not Path(str(r.get("file") or "")).exists():
            continue
        q = quality_by_path.get(p)
        if not q:
            continue
        b = beauty_by_path.get(p) or beauty_by_name.get(name) or {}
        row = dict(r)
        row["_quality"] = q
        row["_taste_weight"] = max(pref.get(p, 1.0), pref.get(name, 1.0))
        row["_beauty"] = fnum(b.get("beauty_score"), 55)
        row["_best_source_in"] = fnum(b.get("best_source_in_sec"), 0)
        pool.append(row)
    return pool

def replacement_score(item: dict[str, Any], section: str, wanted_tag: str, duration: float):
    q = item.get("_quality") or {}
    bw = best_window(q, duration, 0)
    if not bw:
        return -9999, None

    tag = str(item.get("scene_tag") or "other")
    safe = SECTION_SAFE_TAGS.get(section, set())
    score = fnum(bw.get("score"), 0)
    score += fnum(item.get("_beauty"), 55) * 0.35
    score += fnum(item.get("_taste_weight"), 1.0) * 12

    if tag == wanted_tag:
        score += 28
    elif tag in safe:
        score += 8
    else:
        score -= 45

    if section == "ending" and tag not in {"ending","cdcr_portrait","first_look","family_emotion","detail_beauty"}:
        score -= 35
    if section == "intro" and tag in {"guest_food","wedding_game","party","reception_stage"}:
        score -= 45

    return score, bw

def main():
    p = argparse.ArgumentParser(description="125 Smart In/Out Moment Picker + quality rescue.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--min-quality", type=float, default=46.0)
    p.add_argument("--replace-weak", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "smart_inout_moment_picker_125")
    timeline_data = read_json(project / "stt_beat_snapped_beauty_timeline_v1.json")
    timeline = list(timeline_data.get("items") or [])

    if not timeline:
        res = {"ok": False, "error": "NO_CURRENT_TIMELINE", "message": "Run 123B first."}
        write_json(out / "MOMENT_PICKER_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    quality_by_path, quality_by_name = load_quality(project)
    replacement_pool = build_replacement_pool(project, quality_by_path) if a.replace_weak else []
    used_paths = set()
    result = []
    replaced_count = 0
    adjusted_count = 0
    fallback_count = 0
    weak_kept_count = 0

    for item in timeline:
        row = dict(item)
        p = norm_path(row.get("file"))
        name = str(row.get("filename") or Path(p).name).lower()
        dur = fnum(row.get("duration_sec"), 0)
        section = section_of(row)
        wanted_tag = str(row.get("scene_tag") or "other")

        q = quality_by_path.get(p)
        if not q:
            lst = quality_by_name.get(name, [])
            q = lst[0] if lst else None

        selected = best_window(q, dur, a.min_quality) if q else None
        original_file = str(row.get("file") or "")
        original_in = fnum(row.get("source_in_sec"), 0)

        if selected and selected.get("acceptable"):
            row["source_in_sec"] = selected["source_in_sec"]
            row["source_out_sec"] = selected["source_out_sec"]
            row["source_duration_sec"] = round(dur, 3)
            row["moment_quality_score"] = selected["score"]
            row["moment_picker_reason"] = "best_stable_window_same_source"
            adjusted_count += 1
            used_paths.add(p)
        else:
            replacement = None
            if a.replace_weak:
                ranked = []
                for cand in replacement_pool:
                    cp = norm_path(cand.get("file"))
                    if cp in used_paths or cp == p:
                        continue
                    sc, bw = replacement_score(cand, section, wanted_tag, dur)
                    if bw:
                        ranked.append((sc, cand, bw))
                if ranked:
                    ranked.sort(key=lambda x: x[0], reverse=True)
                    sc, cand, bw = ranked[0]
                    if sc >= a.min_quality + 20:
                        replacement = (cand, bw, sc)

            if replacement:
                cand, bw, sc = replacement
                row["original_file_before_quality_rescue"] = original_file
                row["original_source_in_before_quality_rescue"] = original_in
                row["file"] = cand.get("file")
                row["filename"] = cand.get("filename") or Path(str(cand.get("file"))).name
                row["scene_tag"] = cand.get("scene_tag") or wanted_tag
                row["source_in_sec"] = bw["source_in_sec"]
                row["source_out_sec"] = bw["source_out_sec"]
                row["source_duration_sec"] = round(dur, 3)
                row["moment_quality_score"] = bw["score"]
                row["moment_picker_reason"] = "replaced_weak_source_with_better_candidate"
                row["replacement_score"] = round(sc, 3)
                replaced_count += 1
                used_paths.add(norm_path(cand.get("file")))
            else:
                # Conservative fallback: clamp old in/out.
                media_dur = fnum(q.get("duration_sec"), 0) if q else 0
                src_in = max(0.0, original_in)
                if media_dur > 0:
                    src_in = min(src_in, max(0.0, media_dur - dur))
                row["source_in_sec"] = round(src_in, 3)
                row["source_out_sec"] = round(src_in + dur, 3)
                row["source_duration_sec"] = round(dur, 3)
                row["moment_quality_score"] = fnum(selected.get("score"), 0) if selected else 0
                row["moment_picker_reason"] = "weak_kept_no_safe_replacement"
                weak_kept_count += 1
                fallback_count += 1
                used_paths.add(p)

        result.append(row)

    data = dict(timeline_data)
    data["module_before_125"] = timeline_data.get("module")
    data["module"] = "125_smart_inout_moment_picker"
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    data["items"] = result
    data["timeline_count"] = len(result)
    data["timeline_seconds"] = result[-1].get("timeline_end_sec", 0) if result else 0
    data["duration_stats"] = duration_stats(result)
    data["quality_moment_summary"] = {
        "adjusted_same_source_count": adjusted_count,
        "replaced_weak_source_count": replaced_count,
        "weak_kept_count": weak_kept_count,
        "fallback_count": fallback_count,
        "min_quality": a.min_quality,
        "replace_weak": bool(a.replace_weak),
    }

    write_json(project / "stt_beat_snapped_beauty_timeline_v1.json", data)
    write_json(project / "stt_quality_moment_timeline_v1.json", data)
    write_json(out / "stt_quality_moment_timeline_v1.json", data)
    write_csv(out / "QUALITY_MOMENT_TIMELINE_125.csv", result, [
        "index","story_part","scene_tag","filename","timeline_start_sec","duration_sec",
        "source_in_sec","source_out_sec","moment_quality_score","moment_picker_reason",
        "replacement_score","original_file_before_quality_rescue","file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(result),
        "timeline_seconds": data["timeline_seconds"],
        "adjusted_same_source_count": adjusted_count,
        "replaced_weak_source_count": replaced_count,
        "weak_kept_count": weak_kept_count,
        "fallback_count": fallback_count,
        "fix": "125_smart_inout_moment_picker",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
