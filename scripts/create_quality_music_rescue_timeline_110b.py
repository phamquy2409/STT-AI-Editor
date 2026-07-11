from __future__ import annotations

import argparse
import csv
import json
import os
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


def read_csv(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


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


def find_source_file_index(source: Path) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    if not source.exists():
        return idx
    for ext in VIDEO_EXTS:
        for p in source.rglob(f"*{ext}"):
            idx.setdefault(p.name.lower(), []).append(str(p))
    return idx


def resolve_path(row: dict[str, Any], file_index: dict[str, list[str]]) -> str:
    p = str(row.get("file") or "")
    if p and Path(p).exists():
        return p
    n = str(row.get("filename") or Path(p).name).lower()
    if n in file_index and file_index[n]:
        return file_index[n][0]
    return ""


def infer_section(row: dict[str, Any], order_pos: float) -> str:
    s = f"{row.get('filename','')} {row.get('file','')}".lower()
    if any(k in s for k in ["intro", "decor", "detail", "dress", "ring", "flower", "venue", "location"]):
        return "intro"
    if any(k in s for k in ["bride", "groom", "makeup", "prep", "couple", "portrait", "walk", "hand", "prewedding"]):
        return "story"
    if any(k in s for k in ["gia", "tien", "ruoc", "dau", "ceremony", "le ", "stage", "church", "nha tho", "altar"]):
        return "build"
    if any(k in s for k in ["kiss", "dance", "party", "fire", "climax", "champagne", "confetti"]):
        return "climax"
    if any(k in s for k in ["ending", "thank", "family", "guest", "bye"]):
        return "ending"

    if order_pos < 0.16:
        return "intro"
    if order_pos < 0.48:
        return "story"
    if order_pos < 0.70:
        return "build"
    if order_pos < 0.86:
        return "climax"
    return "ending"


def load_quality_items(project: Path, source: Path, min_score: float, allow_braw: bool) -> list[dict[str, Any]]:
    q = read_json(project / "stt_source_quality_v3.json")
    file_index = find_source_file_index(source)
    rows = list(q.get("items") or [])

    if not rows and source.exists():
        files = []
        for ext in VIDEO_EXTS:
            files.extend(source.rglob(f"*{ext}"))
        rows = [{
            "filename": p.name,
            "file": str(p),
            "quality_score": 60,
            "quality_class": "unscored_rescue",
            "usable": True,
            "motion_class": "unknown",
            "reject_reasons": "",
            "duration_sec": 0,
        } for p in sorted(set(files), key=lambda x: str(x).lower())]

    out = []
    total = max(1, len(rows))
    for i, row in enumerate(rows):
        path = resolve_path(row, file_index)
        if not path:
            continue
        ext = Path(path).suffix.lower()
        if ext not in VIDEO_EXTS:
            continue
        if ext == ".braw" and not allow_braw:
            continue

        score = fnum(row.get("quality_score"), 50)
        rr = str(row.get("reject_reasons") or "")
        motion = str(row.get("motion_class") or "unknown")
        qclass = str(row.get("quality_class") or "")

        # keep rescue, but remove obvious trash if possible
        if score < min_score:
            continue
        if any(x in rr for x in ["too_dark", "too_bright", "empty_or_low_detail", "whip_pan_or_shaky"]) and score < 65:
            continue

        pos = i / total
        item = {
            "index": len(out) + 1,
            "filename": Path(path).name,
            "file": path,
            "target_section": infer_section(row, pos),
            "quality_score": score,
            "quality_class": qclass,
            "quality_usable": bool(row.get("usable", False)),
            "quality_reject_reasons": rr,
            "motion_class": motion,
            "media_duration_sec": fnum(row.get("duration_sec"), 0),
            "_source_order": i,
        }
        out.append(item)

    # if still too low, relax and include the best existing files
    if len(out) < 40:
        out = []
        for i, row in enumerate(rows):
            path = resolve_path(row, file_index)
            if not path:
                continue
            ext = Path(path).suffix.lower()
            if ext not in VIDEO_EXTS:
                continue
            if ext == ".braw" and not allow_braw:
                continue
            pos = i / total
            score = fnum(row.get("quality_score"), 45)
            item = {
                "index": len(out) + 1,
                "filename": Path(path).name,
                "file": path,
                "target_section": infer_section(row, pos),
                "quality_score": score,
                "quality_class": str(row.get("quality_class") or "relaxed_rescue"),
                "quality_usable": bool(row.get("usable", False)),
                "quality_reject_reasons": str(row.get("reject_reasons") or ""),
                "motion_class": str(row.get("motion_class") or "unknown"),
                "media_duration_sec": fnum(row.get("duration_sec"), 0),
                "_source_order": i,
            }
            out.append(item)
    return out


def load_blocks(project: Path, target_seconds: int) -> list[dict[str, Any]]:
    manual = project / "stt_music_director_manual.csv"
    rows = read_csv(manual)
    allowed = {"quiet_hold", "emotion_long", "story_medium", "build_fast", "climax_fast", "impact_cut", "ending_hold"}
    blocks = []
    for r in rows:
        st = fnum(r.get("start_sec"), -1)
        en = fnum(r.get("end_sec"), -1)
        mode = str(r.get("mode") or "").strip()
        if st >= 0 and en > st and mode in allowed:
            blocks.append({"start_sec": st, "end_sec": min(en, target_seconds), "mode": mode, "note": r.get("note", "manual")})
    if blocks:
        return sorted(blocks, key=lambda x: fnum(x.get("start_sec"), 0))

    d = read_json(project / "stt_music_director_map_v1.json")
    blocks = list(d.get("director_blocks") or [])
    if blocks:
        return blocks

    return [
        {"start_sec": 0, "end_sec": 24, "mode": "quiet_hold", "note": "fallback"},
        {"start_sec": 24, "end_sec": 110, "mode": "story_medium", "note": "fallback"},
        {"start_sec": 110, "end_sec": 190, "mode": "emotion_long", "note": "fallback"},
        {"start_sec": 190, "end_sec": 285, "mode": "build_fast", "note": "fallback"},
        {"start_sec": 285, "end_sec": 375, "mode": "climax_fast", "note": "fallback"},
        {"start_sec": 375, "end_sec": target_seconds, "mode": "ending_hold", "note": "fallback"},
    ]


def visual_bucket(item: dict[str, Any]) -> str:
    score = fnum(item.get("quality_score"), 50)
    motion = str(item.get("motion_class") or "").lower()
    if score >= 72 and motion in {"stable", "static", "unknown"}:
        return "stable_good"
    if motion in {"active"} and score >= 50:
        return "active_short"
    if motion in {"shaky_or_whip"}:
        return "only_fast_if_needed"
    if score >= 55:
        return "usable"
    return "weak"


def make_pools(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    pools = {s: [] for s in SECTION_ORDER}
    for it in items:
        sec = str(it.get("target_section") or "story")
        if sec not in pools:
            sec = "story"
        pools[sec].append(dict(it))
    for s in pools:
        pools[s] = sorted(pools[s], key=lambda x: (-fnum(x.get("quality_score"), 0), int(x.get("_source_order", 0))))
    return pools


def prefs_for_mode(mode: str, pos: float) -> list[str]:
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


def pattern_for_mode(mode: str) -> list[float]:
    if mode == "quiet_hold":
        return [4.8, 6.5, 3.2, 7.8]
    if mode == "emotion_long":
        return [6.5, 4.2, 8.5, 3.4, 7.0]
    if mode == "story_medium":
        return [2.2, 1.2, 3.2, 0.9, 4.2, 1.6]
    if mode == "build_fast":
        return [0.9, 1.3, 0.55, 1.9, 0.7, 2.7]
    if mode == "climax_fast":
        return [0.35, 0.48, 0.62, 0.42, 0.95, 0.55, 1.25]
    if mode == "impact_cut":
        return [0.22, 0.32, 0.45, 0.28, 0.65]
    if mode == "ending_hold":
        return [5.8, 4.0, 8.0, 3.4, 7.2]
    return [1.5, 2.5, 1.0, 3.5]


def pop_best(pools: dict[str, list[dict[str, Any]]], prefs: list[str], mode: str, duration: float) -> dict[str, Any] | None:
    all_secs = prefs + [s for s in SECTION_ORDER if s not in prefs]

    # Long hold must be stable/usable, not active/shaky.
    for sec in all_secs:
        arr = pools.get(sec, [])
        for i, it in enumerate(arr):
            b = visual_bucket(it)
            motion = str(it.get("motion_class") or "")
            if duration >= 3.0:
                if b in {"stable_good", "usable"} and motion not in {"active", "shaky_or_whip"}:
                    return arr.pop(i)
            else:
                if b != "weak":
                    return arr.pop(i)

    # Last resort, any source.
    for sec in all_secs:
        arr = pools.get(sec, [])
        if arr:
            return arr.pop(0)
    return None


def build_timeline(items: list[dict[str, Any]], blocks: list[dict[str, Any]], target_seconds: int, target_shots: int) -> list[dict[str, Any]]:
    pools = make_pools(items)
    timeline = []

    for block in blocks:
        if len(timeline) >= target_shots:
            break
        st = fnum(block.get("start_sec"), 0)
        en = min(fnum(block.get("end_sec"), st), target_seconds)
        mode = str(block.get("mode") or "story_medium")
        if en <= st:
            continue
        pat = pattern_for_mode(mode)
        t = st
        k = 0
        while t < en - 0.15 and len(timeline) < target_shots:
            d = pat[k % len(pat)]
            if t + d > en:
                d = en - t
            if d < 0.22:
                break

            prefs = prefs_for_mode(mode, t / max(1, target_seconds))
            src = pop_best(pools, prefs, mode, d)
            if not src:
                break

            motion = str(src.get("motion_class") or "")
            if motion == "active" and d > 1.5:
                d = 1.5
            if motion == "shaky_or_whip" and d > 0.5:
                d = 0.5

            row = dict(src)
            row.update({
                "index": len(timeline) + 1,
                "timeline_start_sec": round(t, 3),
                "timeline_end_sec": round(t + d, 3),
                "duration_sec": round(d, 3),
                "source_in_sec": 0.0,
                "source_out_sec": round(d, 3),
                "source_duration_sec": round(d, 3),
                "music_mode": mode,
                "visual_bucket": visual_bucket(src),
                "rhythm_reason": f"110B_rescue_quality_music_{mode}",
                "director_note": block.get("note", ""),
            })
            timeline.append(row)
            t += d
            k += 1

    return timeline


def main() -> None:
    p = argparse.ArgumentParser(description="110B Rescue non-zero quality music timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--min-score", type=float, default=30)
    p.add_argument("--allow-braw", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "quality_music_rescue_timeline_110b")

    items = load_quality_items(project, source, a.min_score, a.allow_braw)
    blocks = load_blocks(project, a.target_seconds)
    timeline = build_timeline(items, blocks, a.target_seconds, a.target_shots)

    data = {
        "ok": True,
        "module": "110B_quality_music_rescue_timeline",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "style_profile": a.style_profile,
        "source_candidate_count": len(items),
        "director_block_count": len(blocks),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": duration_stats(timeline),
        "mode_counts": {m: sum(1 for x in timeline if x.get("music_mode") == m) for m in sorted({str(x.get("music_mode")) for x in timeline})},
        "motion_counts": {m: sum(1 for x in timeline if x.get("motion_class") == m) for m in sorted({str(x.get("motion_class")) for x in timeline})},
        "items": timeline,
    }
    write_json(project / "stt_quality_music_rescue_timeline_v2.json", data)
    # overwrite old empty timeline too, so 111 can use it if needed
    write_json(project / "stt_music_directed_quality_timeline_v2.json", data)
    write_json(out / "stt_quality_music_rescue_timeline_v2.json", data)
    write_csv(out / "QUALITY_MUSIC_RESCUE_TIMELINE_110B.csv", timeline, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "music_mode", "visual_bucket", "quality_score", "quality_class", "motion_class",
        "quality_reject_reasons", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "source_candidate_count": len(items),
        "director_block_count": len(blocks),
        "timeline_count": len(timeline),
        "timeline_seconds": timeline[-1]["timeline_end_sec"] if timeline else 0,
        "duration_stats": duration_stats(timeline),
        "mode_counts": data["mode_counts"],
        "motion_counts": data["motion_counts"],
        "fix": "110B_quality_music_rescue_timeline",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
