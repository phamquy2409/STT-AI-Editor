
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/27thang6pschh/souce"


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


def load_story_roles(project_root: Path) -> list[dict[str, Any]]:
    d = read_json(project_root / "stt_wedding_story_roles_v1.json") or read_json(appdata_dir() / "stt_wedding_story_roles_v1.json")
    return list(d.get("items") or [])


def hard_bad(item: dict[str, Any]) -> bool:
    flags = str(item.get("quality_flags") or "")
    decision = str(item.get("decision") or "").lower()
    if decision == "reject":
        return True
    if "cannot_open" in flags or "too_few_frames" in flags:
        return True
    if fnum(item.get("duration_sec"), 0) < 1.2:
        return True
    return False


def strict_story_counts(target_shots: int) -> list[tuple[str, int]]:
    plan = [
        ("intro_hook", 0.10),
        ("getting_ready", 0.12),
        ("gia_tien_story", 0.28),
        ("ruoc_dau_story", 0.12),
        ("reception_story", 0.16),
        ("emotion_climax", 0.15),
        ("ending_release", 0.07),
    ]
    rows = []
    used = 0
    for i, (chapter, frac) in enumerate(plan):
        if i == len(plan) - 1:
            count = target_shots - used
        else:
            count = max(1, int(round(target_shots * frac)))
            used += count
        rows.append((chapter, max(1, count)))
    total = sum(c for _, c in rows)
    while total > target_shots:
        for i in range(len(rows)):
            ch, c = rows[i]
            if c > 1 and total > target_shots:
                rows[i] = (ch, c - 1)
                total -= 1
    while total < target_shots:
        rows[2] = (rows[2][0], rows[2][1] + 1)
        total += 1
    return rows


def chapter_section(chapter: str) -> str:
    if chapter == "intro_hook":
        return "intro"
    if chapter in {"emotion_climax"}:
        return "climax"
    if chapter == "ending_release":
        return "ending"
    return "story"


def pick_chapter_items(items: list[dict[str, Any]], chapter: str, count: int, used: set[str]) -> list[dict[str, Any]]:
    pool = [
        x for x in items
        if str(x.get("story_chapter") or "") == chapter
        and str(x.get("file") or "") not in used
        and not hard_bad(x)
    ]
    # strict chapter order, but choose better clips inside same chapter.
    pool.sort(key=lambda x: (inum(x.get("story_order"), 999999), -fnum(x.get("rank_score"), 0), inum(x.get("source_order"), 999999)))
    chosen = pool[:count]
    for c in chosen:
        used.add(str(c.get("file") or ""))

    # If chapter lacks enough clips, borrow adjacent but keep chapter label.
    if len(chosen) < count:
        fallback = [
            x for x in items
            if str(x.get("file") or "") not in used
            and not hard_bad(x)
        ]
        fallback.sort(key=lambda x: (abs(inum(x.get("story_chapter_order"), 999) - chapter_order(chapter)), inum(x.get("story_order"), 999999), -fnum(x.get("rank_score"), 0)))
        for f in fallback:
            if len(chosen) >= count:
                break
            used.add(str(f.get("file") or ""))
            b = dict(f)
            b["borrowed_for_chapter"] = chapter
            chosen.append(b)
    return chosen


def chapter_order(chapter: str) -> int:
    return {
        "intro_hook": 10,
        "getting_ready": 20,
        "gia_tien_story": 30,
        "ruoc_dau_story": 40,
        "reception_story": 50,
        "emotion_climax": 60,
        "ending_release": 70,
    }.get(chapter, 999)


def create_strict_story_spans(target_seconds: float, counts: list[tuple[str, int]]) -> list[dict[str, Any]]:
    fractions = {
        "intro_hook": 0.10,
        "getting_ready": 0.12,
        "gia_tien_story": 0.28,
        "ruoc_dau_story": 0.12,
        "reception_story": 0.16,
        "emotion_climax": 0.15,
        "ending_release": 0.07,
    }
    spans = []
    cursor = 0.0
    for idx, (chapter, count) in enumerate(counts):
        total_dur = target_seconds * fractions.get(chapter, 0.1)
        if idx == len(counts) - 1:
            total_dur = target_seconds - cursor
        avg = total_dur / max(1, count)
        for i in range(count):
            # intro/climax slightly faster, gia_tien/reception slightly held
            dur = avg
            if chapter in {"intro_hook", "emotion_climax"}:
                dur = max(0.8, avg * 0.88)
            elif chapter in {"gia_tien_story", "reception_story"}:
                dur = avg * 1.05
            if i == count - 1:
                # close chapter duration
                chapter_end = cursor + (target_seconds * fractions.get(chapter, 0.1) if idx != len(counts)-1 else target_seconds - cursor)
            spans.append({
                "chapter": chapter,
                "section": chapter_section(chapter),
                "start_sec": cursor,
                "duration_sec": dur,
                "end_sec": cursor + dur,
            })
            cursor += dur
    # Rescale to target_seconds exactly.
    if spans:
        total = spans[-1]["end_sec"]
        scale = target_seconds / max(1.0, total)
        cursor = 0.0
        for s in spans:
            dur = fnum(s.get("duration_sec"), 1) * scale
            s["start_sec"] = cursor
            s["duration_sec"] = dur
            s["end_sec"] = cursor + dur
            cursor += dur
    return spans


def create_strict_story_order_builder(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    target_seconds: float = 180.0,
    target_shots: int = 76,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "strict_story_order_builder_126b")

    items = load_story_roles(project_root)
    if not items:
        res = {"ok": False, "error": "NO_STORY_ROLES", "message": "Run 127 first."}
        write_json(out / "strict_story_error.json", res)
        if open_folder:
            open_path(out)
        return res

    target_shots = max(24, min(target_shots, len(items)))
    counts = strict_story_counts(target_shots)
    spans = create_strict_story_spans(target_seconds, counts)

    used: set[str] = set()
    ordered_items: list[dict[str, Any]] = []
    for chapter, count in counts:
        ordered_items.extend(pick_chapter_items(items, chapter, count, used))

    n = min(len(spans), len(ordered_items))
    timeline = []
    for idx in range(n):
        item = ordered_items[idx]
        span = spans[idx]
        chapter = str(span.get("chapter") or item.get("story_chapter") or "story")
        dur = fnum(span.get("duration_sec"), 2.0)
        src_dur = max(1.0, fnum(item.get("duration_sec"), dur + 0.5))

        # avoid beginning/end of raw clip
        ratios = [0.12, 0.18, 0.25, 0.33, 0.42, 0.52, 0.62]
        if src_dur <= dur + 0.3:
            src_in_sec = 0.0
        else:
            src_in_sec = min(src_dur - dur - 0.1, src_dur * ratios[idx % len(ratios)])
            src_in_sec = max(0.0, src_in_sec)
        src_out_sec = min(src_dur, src_in_sec + dur)
        real_dur = max(0.1, src_out_sec - src_in_sec)
        start_sec = fnum(span.get("start_sec"), 0)
        end_sec = start_sec + real_dur

        timeline.append({
            "index": idx + 1,
            "file": str(item.get("file") or ""),
            "filename": str(item.get("filename") or Path(str(item.get("file") or "")).name),
            "event": str(item.get("event") or "general"),
            "role": str(item.get("event") or "general"),
            "chapter": chapter,
            "story_chapter": chapter,
            "section": str(span.get("section") or chapter_section(chapter)),
            "music_section": str(span.get("section") or chapter_section(chapter)),
            "energy": "strict_story_order",
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
            "story_order": inum(item.get("story_order"), 0),
            "strict_story_locked": True,
            "borrowed_for_chapter": str(item.get("borrowed_for_chapter") or ""),
            "reason": f"126B_STRICT_STORY_ORDER chapter={chapter} story_order={item.get('story_order')}",
        })

    chapter_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    for item in timeline:
        chapter_counts[str(item.get("chapter") or "")] = chapter_counts.get(str(item.get("chapter") or ""), 0) + 1
        event_counts[str(item.get("event") or "")] = event_counts.get(str(item.get("event") or ""), 0) + 1

    data = {
        "ok": True,
        "module": "126B_strict_story_order_builder",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source_folder": str(source_folder),
        "target_seconds": target_seconds,
        "target_shots": target_shots,
        "timeline_count": len(timeline),
        "timeline_seconds": round(max([frames_to_sec(inum(x.get("timeline_end"), 0), timebase) for x in timeline] + [0]), 3),
        "chapter_counts": chapter_counts,
        "event_counts": event_counts,
        "story_counts_plan": [{"chapter": c, "count": n} for c, n in counts],
        "timeline": timeline,
    }

    for name in [
        "stt_strict_story_order_timeline_v1.json",
        "stt_wedding_story_structure_timeline_v2.json",
        "stt_music_section_aware_timeline_v1.json",
        "stt_emotion_rhythm_timeline_v1.json",
        "stt_beat_sync_v2_timeline_v1.json",
        "stt_beat_locked_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        write_json(project_root / name, data)
    write_json(appdata_dir() / "stt_prewedding_refined_v1.json", data)

    write_json(out / "stt_strict_story_order_timeline_v1.json", data)
    write_csv(out / "STRICT_STORY_ORDER_TIMELINE.csv", timeline, [
        "index", "filename", "chapter", "event", "timeline_start", "timeline_end", "duration", "story_order", "source_order", "borrowed_for_chapter", "file",
    ])
    (out / "STRICT_STORY_ORDER_REPORT.html").write_text(
        make_html(
            "Strict Story Order Builder 126B",
            timeline,
            ["index", "filename", "chapter", "event", "duration", "story_order", "borrowed_for_chapter"],
            "126B ép thứ tự chapter cố định, không cho intro/story/climax nhảy lung tung.",
        ),
        encoding="utf-8",
    )

    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(timeline),
        "timeline_seconds": data["timeline_seconds"],
        "chapter_counts": chapter_counts,
        "event_counts": event_counts,
        "fix": "126B_strict_story_order_builder",
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
