
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/5thang5test"


def appdata_dir() -> Path:
    p = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def outdir(project_root: Path, name: str) -> Path:
    p = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_path(path: Path) -> None:
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


def inum(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def sec_to_frames(sec: float, timebase: int = 25) -> int:
    return int(round(max(0.0, sec) * timebase))


def frames_to_sec(frames: int, timebase: int = 25) -> float:
    return max(0.0, frames / max(1, timebase))


def norm_event(event: str) -> str:
    event = str(event or "general")
    aliases = {
        "family": "gia_tien",
        "ceremony": "gia_tien",
        "traditional": "gia_tien",
        "speech": "vow_speech",
        "vow": "vow_speech",
        "party": "dance_party",
        "dance": "dance_party",
    }
    return aliases.get(event, event)


def load_analyzer_items(project_root: Path) -> list[dict[str, Any]]:
    d = read_json(project_root / "stt_wedding_source_analyzer_v2.json") or read_json(appdata_dir() / "stt_wedding_source_analyzer_v2.json")
    items = []
    for item in list(d.get("items") or []):
        if not str(item.get("file") or ""):
            continue
        n = dict(item)
        n["event"] = norm_event(str(n.get("event") or "general"))
        n["source_order"] = inum(n.get("source_order"), inum(n.get("index"), 0))
        n["rank_score"] = quality_rank(n)
        items.append(n)
    items.sort(key=lambda x: inum(x.get("source_order"), 0))
    return items


def load_timing_template(project_root: Path) -> list[dict[str, Any]]:
    # Prefer beat-sync timeline for timing, but ignore its chosen source.
    for name in [
        "stt_beat_sync_v2_timeline_v1.json",
        "stt_beat_locked_timeline_v1.json",
        "stt_music_synced_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        d = read_json(project_root / name)
        if isinstance(d.get("timeline"), list):
            return list(d["timeline"])
    return []


def quality_rank(item: dict[str, Any]) -> float:
    score = fnum(item.get("score"), 0)
    decision = str(item.get("decision") or "").lower()
    flags = str(item.get("quality_flags") or "")
    motion = fnum(item.get("motion_score"), 0)
    blur = fnum(item.get("blur_score"), 0)
    bright = fnum(item.get("brightness"), 0)

    if decision == "strong_pick":
        score += 25
    elif decision == "keep":
        score += 12
    elif decision == "review":
        score -= 2
    elif decision == "reject":
        score -= 100

    if "possible_out_focus" in flags:
        score -= 25
    if "too_dark" in flags or "too_bright" in flags:
        score -= 22
    if "low_contrast" in flags:
        score -= 8
    if motion > 55:
        score -= 18
    elif 4 <= motion <= 35:
        score += 5
    if blur >= 120:
        score += 7
    elif 0 < blur < 35:
        score -= 14
    if 45 <= bright <= 210:
        score += 4
    return round(score, 3)


def hard_bad(item: dict[str, Any]) -> bool:
    flags = str(item.get("quality_flags") or "")
    decision = str(item.get("decision") or "").lower()
    if decision == "reject":
        return True
    if "cannot_open" in flags or "too_few_frames" in flags:
        return True
    if fnum(item.get("duration_sec"), 0) < 1.2:
        return True
    # Do not hard skip review clips, because source may have many review.
    return False


def story_plan(target_shots: int) -> list[dict[str, Any]]:
    # Fractions tuned for 3-minute wedding documentary/highlight.
    spec = [
        ("intro_hook", ["details", "getting_ready", "gia_tien", "reception"], 0.10),
        ("getting_ready", ["getting_ready", "details"], 0.12),
        ("gia_tien_story", ["gia_tien", "details", "vow_speech"], 0.26),
        ("ruoc_dau_story", ["ruoc_dau", "gia_tien", "reception"], 0.12),
        ("reception_story", ["reception", "details", "vow_speech"], 0.16),
        ("emotion_climax", ["vow_speech", "gia_tien", "reception", "dance_party"], 0.16),
        ("ending_release", ["dance_party", "reception", "vow_speech", "details"], 0.08),
    ]
    counts = []
    used = 0
    for idx, (chapter, events, frac) in enumerate(spec):
        if idx == len(spec) - 1:
            count = max(1, target_shots - used)
        else:
            count = max(1, int(round(target_shots * frac)))
            used += count
        counts.append({"chapter": chapter, "events": events, "count": count})
    # adjust exact total
    total = sum(x["count"] for x in counts)
    while total > target_shots and counts[2]["count"] > 1:
        counts[2]["count"] -= 1
        total -= 1
    while total < target_shots:
        counts[2]["count"] += 1
        total += 1
    return counts


def chapter_section(chapter: str) -> str:
    if chapter == "intro_hook":
        return "intro"
    if chapter in {"getting_ready", "gia_tien_story", "ruoc_dau_story", "reception_story"}:
        return "story"
    if chapter == "emotion_climax":
        return "climax"
    return "ending"


def pick_from_chapter(
    items: list[dict[str, Any]],
    events: list[str],
    used_files: set[str],
    prefer_order_after: int | None = None,
) -> dict[str, Any] | None:
    pool = []
    for item in items:
        file = str(item.get("file") or "")
        if not file or file in used_files or hard_bad(item):
            continue
        event = norm_event(str(item.get("event") or "general"))
        if event not in events:
            continue
        order = inum(item.get("source_order"), 0)
        # Prefer chronological flow inside the whole wedding story.
        chronological_bonus = 0
        if prefer_order_after is not None:
            chronological_bonus = -abs(order - prefer_order_after) * 0.02
            if order >= prefer_order_after:
                chronological_bonus += 3
        pool.append((events.index(event), -fnum(item.get("rank_score"), 0) - chronological_bonus, order, item))

    if not pool:
        # fallback: any not used, but still chronological and not bad
        for item in items:
            file = str(item.get("file") or "")
            if file and file not in used_files and not hard_bad(item):
                order = inum(item.get("source_order"), 0)
                pool.append((99, -fnum(item.get("rank_score"), 0), order, item))
    if not pool:
        return None
    pool.sort(key=lambda x: (x[0], x[1], x[2]))
    return pool[0][3]


def create_time_spans_from_template(template: list[dict[str, Any]], target_shots: int, target_seconds: float, timebase: int) -> list[dict[str, Any]]:
    spans = []
    if template:
        # Use first target_shots timings from beat sync V2 if available.
        sorted_tpl = sorted(template, key=lambda x: inum(x.get("timeline_start"), 0))
        for idx, item in enumerate(sorted_tpl[:target_shots], start=1):
            start = frames_to_sec(inum(item.get("timeline_start"), 0), timebase)
            end = frames_to_sec(inum(item.get("timeline_end"), 0), timebase)
            dur = fnum(item.get("duration"), fnum(item.get("duration_sec"), max(0.8, end-start)))
            if end <= start:
                end = start + dur
            spans.append({"index": idx, "start_sec": start, "end_sec": end, "duration_sec": max(0.65, end-start)})
    if len(spans) >= target_shots:
        return spans[:target_shots]

    # fallback evenly spaced.
    spans = []
    avg = target_seconds / target_shots
    cursor = 0.0
    for i in range(target_shots):
        dur = avg
        spans.append({"index": i+1, "start_sec": cursor, "end_sec": cursor+dur, "duration_sec": dur})
        cursor += dur
    return spans


def create_wedding_story_structure_builder_v2(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    target_seconds: float = 180.0,
    target_shots: int = 76,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "wedding_story_structure_builder_v2")

    items = load_analyzer_items(project_root)
    template = load_timing_template(project_root)

    if not items:
        res = {"ok": False, "error": "NO_ANALYZER_ITEMS", "message": "Run 110 first."}
        write_json(out / "story_structure_error.json", res)
        if open_folder:
            open_path(out)
        return res

    target_shots = max(24, min(target_shots, len(items)))
    plan = story_plan(target_shots)
    spans = create_time_spans_from_template(template, target_shots, target_seconds, timebase)

    chosen: list[dict[str, Any]] = []
    used_files: set[str] = set()
    last_order = None

    span_index = 0
    for chapter in plan:
        chapter_name = chapter["chapter"]
        events = list(chapter["events"])
        count = int(chapter["count"])
        for _ in range(count):
            if span_index >= len(spans):
                break
            item = pick_from_chapter(items, events, used_files, prefer_order_after=last_order)
            if item is None:
                break
            used_files.add(str(item.get("file") or ""))
            last_order = inum(item.get("source_order"), last_order or 0)

            span = spans[span_index]
            span_index += 1

            dur = fnum(span.get("duration_sec"), 1.5)
            src_dur = max(1.0, fnum(item.get("duration_sec"), dur + 0.5))
            # avoid first/last part of source
            ratios = [0.15, 0.22, 0.30, 0.38, 0.48, 0.58]
            ratio = ratios[(len(chosen) + 1) % len(ratios)]
            if src_dur <= dur + 0.3:
                src_in_sec = 0.0
            else:
                src_in_sec = min(src_dur - dur - 0.1, src_dur * ratio)
                src_in_sec = max(0.0, src_in_sec)
            src_out_sec = min(src_dur, src_in_sec + dur)
            real_dur = max(0.1, src_out_sec - src_in_sec)
            start_sec = fnum(span.get("start_sec"), 0)
            end_sec = start_sec + real_dur

            chosen.append({
                "index": len(chosen) + 1,
                "file": str(item.get("file") or ""),
                "filename": str(item.get("filename") or Path(str(item.get("file") or "")).name),
                "event": norm_event(str(item.get("event") or "general")),
                "role": norm_event(str(item.get("event") or "general")),
                "chapter": chapter_name,
                "section": chapter_section(chapter_name),
                "music_section": chapter_section(chapter_name),
                "energy": "story_structure_v2",
                "decision": str(item.get("decision") or ""),
                "score": fnum(item.get("score"), 0),
                "rank_score": fnum(item.get("rank_score"), 0),
                "quality_flags": str(item.get("quality_flags") or ""),
                "timeline_start": sec_to_frames(start_sec, timebase),
                "timeline_end": sec_to_frames(end_sec, timebase),
                "source_in": sec_to_frames(src_in_sec, timebase),
                "source_out": sec_to_frames(src_out_sec, timebase),
                "duration": round(real_dur, 3),
                "duration_sec": round(real_dur, 3),
                "source_duration_sec": src_dur,
                "source_order": inum(item.get("source_order"), 0),
                "story_locked": True,
                "reason": f"126_story_structure chapter={chapter_name} event={norm_event(str(item.get('event') or 'general'))}",
            })

    chapter_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    for item in chosen:
        chapter_counts[str(item["chapter"])] = chapter_counts.get(str(item["chapter"]), 0) + 1
        event_counts[str(item["event"])] = event_counts.get(str(item["event"]), 0) + 1

    data = {
        "ok": True,
        "module": "126_wedding_story_structure_builder_v2",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "target_seconds": target_seconds,
        "target_shots": target_shots,
        "timeline_count": len(chosen),
        "timeline_seconds": round(max([frames_to_sec(inum(x.get("timeline_end"), 0), timebase) for x in chosen] + [0]), 3),
        "chapter_counts": chapter_counts,
        "event_counts": event_counts,
        "story_plan": plan,
        "timeline": chosen,
    }

    for name in [
        "stt_wedding_story_structure_timeline_v2.json",
        "stt_beat_sync_v2_timeline_v1.json",
        "stt_music_section_aware_timeline_v1.json",
        "stt_emotion_rhythm_timeline_v1.json",
        "stt_beat_locked_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        write_json(project_root / name, data)
    write_json(appdata_dir() / "stt_prewedding_refined_v1.json", data)

    write_json(out / "stt_wedding_story_structure_timeline_v2.json", data)
    write_csv(out / "WEDDING_STORY_STRUCTURE_TIMELINE.csv", chosen, [
        "index", "filename", "chapter", "event", "section", "timeline_start", "timeline_end", "duration", "source_order", "decision", "rank_score", "file",
    ])
    (out / "WEDDING_STORY_STRUCTURE_REPORT.html").write_text(
        make_html(
            "Wedding Story Structure Builder V2",
            chosen,
            ["index", "filename", "chapter", "event", "section", "duration", "source_order"],
            "126 ép timeline theo mạch intro/getting ready/gia tiên/rước dâu/reception/climax/ending, tránh cảm giác chọn đại.",
        ),
        encoding="utf-8",
    )

    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(chosen),
        "timeline_seconds": data["timeline_seconds"],
        "chapter_counts": chapter_counts,
        "event_counts": event_counts,
        "fix": "126_wedding_story_structure_builder_v2",
    }


def make_html(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    import html
    th = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    tr = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>"
        for r in rows
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Arial;background:#111;color:#eee;margin:32px}"
        ".card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}</style></head>"
        f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{th}</tr>{tr}</table></div></body></html>"
    )
