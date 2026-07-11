from __future__ import annotations

import csv
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.sax.saxutils import escape

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/27thang6pschh/souce"
DEFAULT_PROFILE = "intimate_7_8min"
VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".ogg", ".wma", ".flac"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def appdata_dir() -> Path:
    p = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p


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


def outdir(project_root: str | Path, name: str) -> Path:
    p = Path(project_root) / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def safe_avg(vals: list[float], default: float = 0.0) -> float:
    vals = [float(v) for v in vals if v is not None]
    if not vals:
        return default
    return round(sum(vals) / len(vals), 3)


def pathurl_for(path: str | Path) -> str:
    p = str(path).replace("\\", "/")
    return "file://localhost/" + quote(p, safe="/:")


def make_html(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    th = "".join(f"<th>{escape(str(c))}</th>" for c in cols)
    trs = []
    for r in rows[:1000]:
        trs.append("<tr>" + "".join(f"<td>{escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Arial;background:#111;color:#eee;margin:32px}"
        ".card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}</style></head>"
        f"<body><div class='card'><h1>{escape(title)}</h1><p>{escape(note)}</p>"
        f"<table><tr>{th}</tr>{''.join(trs)}</table></div></body></html>"
    )


def load_style_profile(project_root: str | Path, profile_name: str) -> dict[str, Any]:
    project_root = Path(project_root)
    profile_name = profile_name.strip()
    direct = project_root / "stt_style_profiles_v1" / f"{profile_name}.json"
    if direct.exists():
        return read_json(direct)
    memory = read_json(project_root / "stt_multi_style_profile_memory_v1.json") or read_json(appdata_dir() / "stt_multi_style_profile_memory_v1.json")
    profiles = memory.get("profiles") or {}
    return profiles.get(profile_name) or profiles.get(profile_name.lower()) or {}


def scan_source(source_folder: str | Path) -> list[dict[str, Any]]:
    source_folder = Path(source_folder)
    rows: list[dict[str, Any]] = []
    if not source_folder.exists():
        return rows
    for p in source_folder.rglob("*"):
        try:
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext not in VIDEO_EXTS and ext not in IMAGE_EXTS:
                continue
            rel = str(p.relative_to(source_folder)).replace("\\", "/")
            rows.append({
                "file": str(p),
                "filename": p.name,
                "basename": p.name.lower(),
                "stem": p.stem.lower(),
                "ext": ext,
                "relpath": rel,
                "folder_hint": rel.lower(),
                "size_bytes": p.stat().st_size,
            })
        except Exception:
            pass
    rows.sort(key=lambda r: str(r.get("relpath", "")).lower())
    return rows


def profile_examples(profile: dict[str, Any]) -> dict[str, Any]:
    preferred = Counter()
    avoid = Counter()
    durations: list[float] = []
    starts: list[float] = []
    for item in profile.get("most_used_filenames") or []:
        name = str(item.get("filename") or "").lower()
        if name:
            preferred[name] += int(item.get("uses") or 1)
    for proj in profile.get("projects") or []:
        for ex in proj.get("final_order_examples") or []:
            name = str(ex.get("filename") or "").lower()
            if name:
                preferred[name] += 2
            durations.append(fnum(ex.get("duration_sec"), 0))
            starts.append(fnum(ex.get("source_in_sec"), 0))
    rules = profile.get("rules") or {}
    for ex in rules.get("prefer_final_added_examples") or []:
        name = str(ex.get("filename") or "").lower()
        if name:
            preferred[name] += 4
    for ex in rules.get("avoid_removed_ai_examples") or []:
        name = str(ex.get("filename") or "").lower()
        if name:
            avoid[name] += 5
    return {"preferred": preferred, "avoid": avoid, "durations": [d for d in durations if d > 0], "starts": [s for s in starts if s >= 0]}


def infer_section(row: dict[str, Any]) -> str:
    s = f"{row.get('folder_hint','')} {row.get('filename','')}".lower()
    if any(k in s for k in ["intro", "teaser", "hook", "opening", "decor", "detail", "ring", "dress", "makeup", "make-up"]):
        return "intro"
    if any(k in s for k in ["bride", "groom", "prep", "getting", "nha gai", "nha trai", "chuan bi", "chuẩn bị"]):
        return "story"
    if any(k in s for k in ["gia tien", "gia_tien", "gia-tien", "ruoc dau", "ruoc_dau", "rước", "le ", "lễ", "ceremony", "church", "nha tho", "nhà thờ"]):
        return "build"
    if any(k in s for k in ["vow", "speech", "toast", "first dance", "dance", "party", "climax", "intimate", "couple"]):
        return "climax"
    if any(k in s for k in ["ending", "end", "thank", "cam on", "cảm ơn", "outro"]):
        return "ending"
    return "story"


def section_for_pos(pos: float) -> str:
    if pos < 0.12:
        return "intro"
    if pos < 0.42:
        return "story"
    if pos < 0.58:
        return "build"
    if pos < 0.82:
        return "climax"
    return "ending"


def section_rules(profile: dict[str, Any]) -> dict[str, dict[str, float]]:
    raw = profile.get("section_rules") or (profile.get("rules") or {}).get("section_rules") or {}
    out: dict[str, dict[str, float]] = {}
    for sec in ["intro", "story", "build", "climax", "ending"]:
        r = raw.get(sec) or {}
        out[sec] = {
            "ratio": fnum(r.get("avg_clip_ratio", r.get("clip_ratio", 0)), 0),
            "duration": fnum(r.get("avg_duration_sec", r.get("avg_p50_duration_sec", r.get("p50_duration_sec", 2.0))), 2.0),
            "p50": fnum(r.get("avg_p50_duration_sec", r.get("p50_duration_sec", r.get("avg_duration_sec", 2.0))), 2.0),
        }
    total = sum(v["ratio"] for v in out.values())
    if total <= 0:
        defaults = {"intro": 0.12, "story": 0.30, "build": 0.16, "climax": 0.24, "ending": 0.18}
        for k, v in defaults.items():
            out[k]["ratio"] = v
    else:
        for k in out:
            out[k]["ratio"] = round(out[k]["ratio"] / total, 4)
    return out


def target_seconds_from_profile(profile: dict[str, Any], target_seconds: int | None) -> int:
    if target_seconds and target_seconds > 0:
        return int(target_seconds)
    val = fnum(profile.get("target_duration_avg_sec"), 0)
    if val <= 0:
        val = fnum((profile.get("final_style_summary") or {}).get("final_total_duration_sec"), 0)
    return max(20, int(round(val or 480)))


def target_shots_from_profile(profile: dict[str, Any], target_shots: int | None) -> int:
    if target_shots and target_shots > 0:
        return int(target_shots)
    val = fnum(profile.get("target_clip_count_avg"), 0)
    if val <= 0:
        val = fnum((profile.get("rules") or {}).get("target_clip_count_hint"), 0)
    return max(5, int(round(val or 160)))


def distribute_counts(total: int, ratios: dict[str, float]) -> dict[str, int]:
    counts = {k: max(0, int(round(total * ratios.get(k, 0)))) for k in ["intro", "story", "build", "climax", "ending"]}
    diff = total - sum(counts.values())
    order = ["climax", "story", "ending", "build", "intro"]
    i = 0
    while diff != 0 and i < 10000:
        k = order[i % len(order)]
        if diff > 0:
            counts[k] += 1
            diff -= 1
        elif counts[k] > 0:
            counts[k] -= 1
            diff += 1
        i += 1
    return counts


# 094
def create_apply_style_profile(project_root=DEFAULT_PROJECT_ROOT, source_folder=DEFAULT_SOURCE_FOLDER, style_profile=DEFAULT_PROFILE, target_seconds: int | None = None, target_shots: int | None = None, open_folder=True, **kwargs):
    project_root = Path(project_root)
    out = outdir(project_root, "apply_style_profile_094")
    profile = load_style_profile(project_root, style_profile)
    if not profile:
        res = {"ok": False, "error": "STYLE_PROFILE_NOT_FOUND", "style_profile": style_profile}
        write_json(out / "apply_style_profile_error.json", res)
        if open_folder: open_path(out)
        return res
    rules = section_rules(profile)
    seconds = target_seconds_from_profile(profile, target_seconds)
    shots = target_shots_from_profile(profile, target_shots)
    ratios = {k: v["ratio"] for k, v in rules.items()}
    counts = distribute_counts(shots, ratios)
    rows = [{"section": k, "target_count": counts[k], "target_seconds": round(seconds * ratios[k], 3), **rules[k]} for k in counts]
    data = {
        "ok": True, "module": "094_apply_style_profile", "updated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root), "source_folder": str(source_folder), "style_profile": style_profile,
        "profile_type_inferred": profile.get("profile_type_inferred"), "profile_project_count": profile.get("project_count"),
        "target_seconds": seconds, "target_shots": shots, "section_rules": rules,
        "section_target_counts": counts, "section_target_seconds": {r["section"]: r["target_seconds"] for r in rows},
    }
    write_json(project_root / "stt_applied_style_profile_v1.json", data)
    write_json(out / "stt_applied_style_profile_v1.json", data)
    write_csv(out / "APPLIED_STYLE_PROFILE.csv", rows, ["section", "target_count", "target_seconds", "ratio", "duration", "p50"])
    (out / "APPLIED_STYLE_PROFILE_REPORT.html").write_text(make_html("094 Apply Style Profile", rows, ["section", "target_count", "target_seconds", "ratio", "duration", "p50"], f"profile={style_profile}"), encoding="utf-8")
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "style_profile": style_profile, "target_seconds": seconds, "target_shots": shots, "section_target_counts": counts, "fix": "094_apply_style_profile"}


# 095
def create_learned_source_scorer(project_root=DEFAULT_PROJECT_ROOT, source_folder=DEFAULT_SOURCE_FOLDER, style_profile=DEFAULT_PROFILE, open_folder=True, **kwargs):
    project_root = Path(project_root)
    source_folder = Path(source_folder)
    out = outdir(project_root, "learned_source_scorer_095")
    profile = load_style_profile(project_root, style_profile)
    if not profile:
        res = {"ok": False, "error": "STYLE_PROFILE_NOT_FOUND", "style_profile": style_profile}
        write_json(out / "learned_source_scorer_error.json", res)
        if open_folder: open_path(out)
        return res
    ex = profile_examples(profile)
    rows = scan_source(source_folder)
    scored = []
    for r in rows:
        name = str(r.get("basename") or "")
        score = 10.0
        reasons = []
        if name in ex["preferred"]:
            boost = min(80, ex["preferred"][name] * 8)
            score += boost
            reasons.append(f"profile_preferred:+{boost}")
        if name in ex["avoid"]:
            penalty = min(80, ex["avoid"][name] * 10)
            score -= penalty
            reasons.append(f"profile_avoid:-{penalty}")
        ext = str(r.get("ext") or "")
        if ext in [".braw", ".mov", ".mp4", ".mxf"]:
            score += 5
            reasons.append("video_ext:+5")
        if fnum(r.get("size_bytes"), 0) > 500_000_000:
            score += 3
            reasons.append("large_source:+3")
        if any(k in str(r.get("folder_hint", "")).lower() for k in ["proxy", "preview", "render", "cache"]):
            score -= 50
            reasons.append("proxy_cache:-50")
        if ext in IMAGE_EXTS:
            score -= 15
            reasons.append("image:-15")
        rr = dict(r)
        rr.update({"score": round(score, 3), "learned_section": infer_section(r), "reasons": "; ".join(reasons)})
        scored.append(rr)
    scored.sort(key=lambda x: (-fnum(x.get("score"), 0), str(x.get("relpath", "")).lower()))
    for i, r in enumerate(scored, start=1):
        r["rank"] = i
    data = {"ok": True, "module": "095_learned_source_scorer", "updated_at": datetime.now().isoformat(timespec="seconds"), "project_root": str(project_root), "source_folder": str(source_folder), "style_profile": style_profile, "source_count": len(rows), "scored_count": len(scored), "items": scored}
    write_json(project_root / "stt_learned_source_scores_v1.json", data)
    write_json(out / "stt_learned_source_scores_v1.json", data)
    write_csv(out / "LEARNED_SOURCE_SCORES.csv", scored, ["rank", "score", "learned_section", "filename", "ext", "size_bytes", "reasons", "file"])
    (out / "LEARNED_SOURCE_SCORE_REPORT.html").write_text(make_html("095 Learned Source Scorer", scored, ["rank", "score", "learned_section", "filename", "ext", "reasons", "file"], f"profile={style_profile}"), encoding="utf-8")
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "source_count": len(rows), "scored_count": len(scored), "top_file": scored[0]["filename"] if scored else "", "fix": "095_learned_source_scorer"}


# 096
def create_profile_story_timeline_builder(project_root=DEFAULT_PROJECT_ROOT, source_folder=DEFAULT_SOURCE_FOLDER, style_profile=DEFAULT_PROFILE, target_seconds: int | None = None, target_shots: int | None = None, open_folder=True, **kwargs):
    project_root = Path(project_root)
    out = outdir(project_root, "profile_story_timeline_builder_096")
    profile = load_style_profile(project_root, style_profile)
    plan = read_json(project_root / "stt_applied_style_profile_v1.json")
    scores = read_json(project_root / "stt_learned_source_scores_v1.json")
    if not scores:
        res = {"ok": False, "error": "NO_SOURCE_SCORES", "message": "Run 095 first."}
        write_json(out / "profile_story_builder_error.json", res)
        if open_folder: open_path(out)
        return res
    seconds = int(target_seconds or plan.get("target_seconds") or target_seconds_from_profile(profile, None))
    shots = int(target_shots or plan.get("target_shots") or target_shots_from_profile(profile, None))
    rules = plan.get("section_rules") or section_rules(profile)
    counts = plan.get("section_target_counts") or distribute_counts(shots, {k: fnum(v.get("ratio"), 0) for k, v in rules.items()})
    pools = {s: [] for s in ["intro", "story", "build", "climax", "ending"]}
    for it in scores.get("items") or []:
        pools.setdefault(str(it.get("learned_section") or "story"), []).append(it)
    selected = []
    used = set()
    for sec in ["intro", "story", "build", "climax", "ending"]:
        got = 0
        for it in pools.get(sec, []):
            f = str(it.get("file") or "")
            if f and f not in used:
                row = dict(it)
                row["target_section"] = sec
                selected.append(row)
                used.add(f)
                got += 1
                if got >= int(counts.get(sec, 0)):
                    break
    for it in scores.get("items") or []:
        if len(selected) >= shots:
            break
        f = str(it.get("file") or "")
        if f and f not in used:
            row = dict(it)
            row["target_section"] = section_for_pos(len(selected) / max(1, shots))
            selected.append(row)
            used.add(f)
    t = 0.0
    timeline = []
    for i, it in enumerate(selected[:shots], start=1):
        sec = str(it.get("target_section") or "story")
        rr = rules.get(sec) or {}
        dur = max(0.35, min(8.0, fnum(rr.get("p50", rr.get("duration", 2.0)), 2.0)))
        row = {"index": i, "file": it.get("file"), "filename": it.get("filename"), "score": it.get("score"), "target_section": sec, "timeline_start_sec": round(t, 3), "duration_sec": round(dur, 3), "timeline_end_sec": round(t + dur, 3), "source_in_sec": 0.0, "source_out_sec": round(dur, 3), "source_duration_sec": round(dur, 3), "reasons": it.get("reasons")}
        timeline.append(row)
        t += dur
    data = {"ok": True, "module": "096_profile_story_timeline_builder", "updated_at": datetime.now().isoformat(timespec="seconds"), "project_root": str(project_root), "source_folder": str(source_folder), "style_profile": style_profile, "target_seconds": seconds, "target_shots": shots, "timeline_count": len(timeline), "rough_duration_sec": round(t, 3), "items": timeline}
    write_json(project_root / "stt_profile_story_timeline_v1.json", data)
    write_json(out / "stt_profile_story_timeline_v1.json", data)
    write_csv(out / "PROFILE_STORY_TIMELINE.csv", timeline, ["index", "target_section", "filename", "score", "timeline_start_sec", "duration_sec", "source_in_sec", "file", "reasons"])
    (out / "PROFILE_STORY_TIMELINE_REPORT.html").write_text(make_html("096 Profile Story Timeline Builder", timeline, ["index", "target_section", "filename", "score", "duration_sec", "file"], f"profile={style_profile}"), encoding="utf-8")
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "timeline_count": len(timeline), "rough_duration_sec": round(t, 3), "fix": "096_profile_story_timeline_builder"}


# 097
def create_profile_rhythm_retimer(project_root=DEFAULT_PROJECT_ROOT, style_profile=DEFAULT_PROFILE, target_seconds: int | None = None, open_folder=True, **kwargs):
    project_root = Path(project_root)
    out = outdir(project_root, "profile_rhythm_retimer_097")
    profile = load_style_profile(project_root, style_profile)
    plan = read_json(project_root / "stt_applied_style_profile_v1.json")
    story = read_json(project_root / "stt_profile_story_timeline_v1.json")
    if not story:
        res = {"ok": False, "error": "NO_STORY_TIMELINE", "message": "Run 096 first."}
        write_json(out / "profile_rhythm_error.json", res)
        if open_folder: open_path(out)
        return res
    seconds = int(target_seconds or story.get("target_seconds") or plan.get("target_seconds") or target_seconds_from_profile(profile, None))
    items = list(story.get("items") or [])
    rules = plan.get("section_rules") or section_rules(profile)
    base = []
    for it in items:
        sec = str(it.get("target_section") or "story")
        d = fnum((rules.get(sec) or {}).get("p50", (rules.get(sec) or {}).get("duration", it.get("duration_sec", 2.0))), 2.0)
        if sec == "intro":
            d *= 0.75
        elif sec == "climax":
            d *= 0.85
        elif sec == "ending":
            d *= 1.10
        base.append(max(0.30, min(8.0, d)))
    scale = seconds / (sum(base) or 1.0)
    t = 0.0
    final = []
    for i, (it, d) in enumerate(zip(items, base), start=1):
        dur = max(0.25, d * scale)
        row = dict(it)
        row["index"] = i
        row["timeline_start_sec"] = round(t, 3)
        row["duration_sec"] = round(dur, 3)
        row["timeline_end_sec"] = round(t + dur, 3)
        t += dur
        final.append(row)
    data = {"ok": True, "module": "097_profile_rhythm_retimer", "updated_at": datetime.now().isoformat(timespec="seconds"), "project_root": str(project_root), "style_profile": style_profile, "target_seconds": seconds, "timeline_count": len(final), "timeline_seconds": round(t, 3), "items": final}
    write_json(project_root / "stt_profile_rhythm_timeline_v1.json", data)
    write_json(out / "stt_profile_rhythm_timeline_v1.json", data)
    write_csv(out / "PROFILE_RHYTHM_TIMELINE.csv", final, ["index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec", "file"])
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "timeline_count": len(final), "timeline_seconds": round(t, 3), "fix": "097_profile_rhythm_retimer"}


# 098
def create_learned_inout_picker(project_root=DEFAULT_PROJECT_ROOT, style_profile=DEFAULT_PROFILE, open_folder=True, **kwargs):
    project_root = Path(project_root)
    out = outdir(project_root, "learned_inout_picker_098")
    profile = load_style_profile(project_root, style_profile)
    rhythm = read_json(project_root / "stt_profile_rhythm_timeline_v1.json")
    if not rhythm:
        res = {"ok": False, "error": "NO_RHYTHM_TIMELINE", "message": "Run 097 first."}
        write_json(out / "learned_inout_error.json", res)
        if open_folder: open_path(out)
        return res
    starts = profile_examples(profile).get("starts") or []
    avg_start = safe_avg(starts, 0.0)
    items = []
    for i, it in enumerate(rhythm.get("items") or [], start=1):
        sec = str(it.get("target_section") or "story")
        dur = fnum(it.get("duration_sec"), 2.0)
        base = {"intro": 0.1, "story": 0.5, "build": 0.8, "climax": 1.0, "ending": 0.5}.get(sec, 0.5)
        source_in = round(max(base, avg_start * 0.35) + ((i * 1.37) % 5.0) * 0.20, 3)
        row = dict(it)
        row["index"] = i
        row["source_in_sec"] = source_in
        row["source_duration_sec"] = round(dur, 3)
        row["source_out_sec"] = round(source_in + dur, 3)
        items.append(row)
    data = {"ok": True, "module": "098_learned_inout_picker", "updated_at": datetime.now().isoformat(timespec="seconds"), "project_root": str(project_root), "style_profile": style_profile, "timeline_count": len(items), "timeline_seconds": rhythm.get("timeline_seconds"), "avg_learned_source_start_sec": avg_start, "items": items}
    write_json(project_root / "stt_learned_inout_timeline_v1.json", data)
    write_json(out / "stt_learned_inout_timeline_v1.json", data)
    write_csv(out / "LEARNED_INOUT_TIMELINE.csv", items, ["index", "target_section", "filename", "timeline_start_sec", "duration_sec", "source_in_sec", "source_out_sec", "file"])
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "timeline_count": len(items), "avg_learned_source_start_sec": avg_start, "fix": "098_learned_inout_picker"}


# 099
def find_music_file(project_root: Path, music_folder: str | Path, explicit_music: str = "") -> str:
    if explicit_music and Path(explicit_music).exists():
        return str(Path(explicit_music))
    for name in ["stt_auto_music_picker_v1.json", "stt_music_picker_v1.json", "stt_music_sync_timeline_v1.json", "stt_final_music_sync_xml_polish_v1.json", "stt_final_wedding_music_cut_v1.json"]:
        d = read_json(project_root / name)
        for k in ["music_file", "selected_music", "file", "path"]:
            v = d.get(k)
            if isinstance(v, str) and Path(v).exists():
                return str(Path(v))
    mf = Path(music_folder)
    if mf.exists():
        files = []
        for ext in ["*.mp3", "*.wav", "*.m4a", "*.aac"]:
            files += list(mf.rglob(ext))
        files = sorted(files)
        if files:
            return str(files[0])
    return ""


def create_profile_music_sync_bridge(project_root=DEFAULT_PROJECT_ROOT, style_profile=DEFAULT_PROFILE, music: str = "", music_folder: str | Path = "D:/STT Music", open_folder=True, **kwargs):
    project_root = Path(project_root)
    out = outdir(project_root, "profile_music_sync_bridge_099")
    tl = read_json(project_root / "stt_learned_inout_timeline_v1.json")
    if not tl:
        res = {"ok": False, "error": "NO_LEARNED_INOUT_TIMELINE", "message": "Run 098 first."}
        write_json(out / "profile_music_bridge_error.json", res)
        if open_folder: open_path(out)
        return res
    music_file = find_music_file(project_root, music_folder, music)
    items = list(tl.get("items") or [])
    markers = [{"time_sec": it.get("timeline_start_sec"), "section": it.get("target_section"), "filename": it.get("filename")} for it in items]
    data = {"ok": True, "module": "099_profile_music_sync_bridge", "updated_at": datetime.now().isoformat(timespec="seconds"), "project_root": str(project_root), "style_profile": style_profile, "music_file": music_file, "has_music": bool(music_file), "timeline_count": len(items), "timeline_seconds": tl.get("timeline_seconds"), "items": items, "markers": markers}
    write_json(project_root / "stt_profile_music_sync_bridge_v1.json", data)
    write_json(out / "stt_profile_music_sync_bridge_v1.json", data)
    write_csv(out / "PROFILE_MUSIC_MARKERS.csv", markers, ["time_sec", "section", "filename"])
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "has_music": bool(music_file), "music_file": music_file, "timeline_count": len(items), "fix": "099_profile_music_sync_bridge"}


# 100
def preset_size(preset: str) -> tuple[int, int]:
    p = preset.lower()
    if "vertical" in p or "9x16" in p:
        return 1080, 1920
    if "1080" in p:
        return 1920, 1080
    return 3840, 2160


def fr(sec: float, fps: int) -> int:
    return max(0, int(round(sec * fps)))


def file_block(file_id: str, path: str, fps: int, width: int, height: int, is_audio: bool = False) -> str:
    name = Path(path).name
    pathurl = pathurl_for(path)
    if is_audio:
        media = "<media><audio><channelcount>2</channelcount></audio></media>"
    else:
        media = f"<media><video><samplecharacteristics><width>{width}</width><height>{height}</height></samplecharacteristics></video></media>"
    return (
        f'<file id="{escape(file_id)}">'
        f"<name>{escape(name)}</name>"
        f"<pathurl>{escape(pathurl)}</pathurl>"
        f"<rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>"
        f"<duration>10000000</duration>{media}</file>"
    )


def clip_xml(it: dict[str, Any], idx: int, fps: int, width: int, height: int) -> str:
    path = str(it.get("file") or "")
    name = str(it.get("filename") or Path(path).name or f"clip_{idx}")
    start = fr(fnum(it.get("timeline_start_sec"), 0), fps)
    dur = max(1, fr(fnum(it.get("duration_sec"), fnum(it.get("source_duration_sec"), 2)), fps))
    end = start + dur
    src_in = fr(fnum(it.get("source_in_sec"), 0), fps)
    src_out = src_in + dur
    return (
        f'<clipitem id="clipitem-{idx}"><name>{escape(name)}</name><enabled>TRUE</enabled>'
        f"<duration>{dur}</duration><rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>"
        f"<start>{start}</start><end>{end}</end><in>{src_in}</in><out>{src_out}</out>"
        f"{file_block(f'file-{idx}', path, fps, width, height, False)}</clipitem>"
    )


def audio_xml(music_file: str, total_frames: int, fps: int) -> str:
    if not music_file:
        return ""
    name = Path(music_file).name
    return (
        '<clipitem id="music-clipitem-1">'
        f"<name>{escape(name)}</name><enabled>TRUE</enabled><duration>{total_frames}</duration>"
        f"<rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate><start>0</start><end>{total_frames}</end><in>0</in><out>{total_frames}</out>"
        f"{file_block('music-file-1', music_file, fps, 0, 0, True)}</clipitem>"
    )


def build_xml(items: list[dict[str, Any]], music_file: str, sequence_name: str, fps: int, width: int, height: int) -> str:
    total_sec = max([fnum(x.get("timeline_end_sec"), fnum(x.get("timeline_start_sec"), 0) + fnum(x.get("duration_sec"), 0)) for x in items] + [1])
    total_frames = max(1, fr(total_sec, fps))
    video = "\n".join(clip_xml(it, i, fps, width, height) for i, it in enumerate(items, start=1) if it.get("file"))
    audio = audio_xml(music_file, total_frames, fps)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4">'
        f'<sequence id="sequence-1"><name>{escape(sequence_name)}</name><duration>{total_frames}</duration>'
        f'<rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate><media>'
        f'<video><format><samplecharacteristics><width>{width}</width><height>{height}</height><anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></format><track>{video}</track></video>'
        f'<audio><track>{audio}</track></audio></media></sequence></xmeml>'
    )


def create_learned_profile_xml_exporter(project_root=DEFAULT_PROJECT_ROOT, style_profile=DEFAULT_PROFILE, preset: str = "horizontal_4k", fps: int = 30, output_xml: str | Path | None = None, open_folder=True, **kwargs):
    project_root = Path(project_root)
    out = outdir(project_root, "learned_profile_xml_exporter_100")
    bridge = read_json(project_root / "stt_profile_music_sync_bridge_v1.json")
    tl = bridge or read_json(project_root / "stt_learned_inout_timeline_v1.json")
    if not tl:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 098 or 099 first."}
        write_json(out / "xml_export_error.json", res)
        if open_folder: open_path(out)
        return res
    items = list(tl.get("items") or [])
    music_file = str(bridge.get("music_file") or "") if bridge else ""
    width, height = preset_size(preset)
    xml_text = build_xml(items, music_file, f"STT Learned {style_profile}", fps, width, height)
    xml_path = Path(output_xml) if output_xml else project_root / "stt_learned_profile_premiere_import.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(xml_text, encoding="utf-8")
    (out / "stt_learned_profile_premiere_import.xml").write_text(xml_text, encoding="utf-8")
    summary = {"ok": True, "module": "100_learned_profile_xml_exporter", "updated_at": datetime.now().isoformat(timespec="seconds"), "project_root": str(project_root), "style_profile": style_profile, "preset": preset, "fps": fps, "width": width, "height": height, "timeline_count": len(items), "music_file": music_file, "output_xml": str(xml_path)}
    write_json(project_root / "stt_learned_profile_xml_export_v1.json", summary)
    write_json(out / "stt_learned_profile_xml_export_v1.json", summary)
    write_csv(out / "XML_EXPORT_TIMELINE.csv", items, ["index", "target_section", "filename", "timeline_start_sec", "duration_sec", "source_in_sec", "source_out_sec", "file"])
    if open_folder: open_path(out)
    return {**summary, "report_dir": str(out), "fix": "100_learned_profile_xml_exporter"}
