
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
    return int(round(max(0.04, sec) * timebase))


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


def event_order(event: str) -> int:
    return {
        "getting_ready": 0,
        "details": 1,
        "gia_tien": 2,
        "ruoc_dau": 3,
        "reception": 4,
        "vow_speech": 5,
        "dance_party": 6,
        "general": 9,
    }.get(norm_event(event), 9)


def load_analyzer(project_root: Path) -> dict[str, Any]:
    for p in [
        project_root / "stt_wedding_source_analyzer_v2.json",
        appdata_dir() / "stt_wedding_source_analyzer_v2.json",
    ]:
        d = read_json(p)
        if isinstance(d.get("items"), list):
            return d
    return {}


def target_count(intent: str, target_seconds: float) -> int:
    if intent == "wedding_teaser_60s":
        return 28
    if intent == "wedding_highlight_3min":
        return 58
    if intent in {"gia_tien_story", "reception_story"}:
        return 45
    return 48


def quota(intent: str) -> dict[str, int]:
    if intent == "wedding_teaser_60s":
        return {"getting_ready": 3, "details": 4, "gia_tien": 6, "ruoc_dau": 3, "reception": 4, "vow_speech": 5, "dance_party": 3}
    if intent == "wedding_highlight_3min":
        return {"getting_ready": 7, "details": 7, "gia_tien": 15, "ruoc_dau": 7, "reception": 10, "vow_speech": 8, "dance_party": 4}
    if intent == "gia_tien_story":
        return {"getting_ready": 4, "details": 5, "gia_tien": 24, "ruoc_dau": 6, "reception": 2, "vow_speech": 4, "dance_party": 0}
    if intent == "reception_story":
        return {"getting_ready": 2, "details": 4, "gia_tien": 2, "ruoc_dau": 2, "reception": 20, "vow_speech": 10, "dance_party": 7}
    return {"getting_ready": 5, "details": 5, "gia_tien": 13, "ruoc_dau": 6, "reception": 8, "vow_speech": 7, "dance_party": 4}


def rank_item(item: dict[str, Any]) -> float:
    score = fnum(item.get("score"), 0)
    decision = str(item.get("decision") or "").lower()
    flags = str(item.get("quality_flags") or "")
    reason = str(item.get("reason") or "")

    if decision == "strong_pick":
        score += 25
    elif decision == "keep":
        score += 14
    elif decision == "review":
        score += 0
    elif decision == "reject":
        score -= 100

    # 111B không loại quá gắt, chỉ trừ điểm để vẫn đủ clip.
    if "possible_out_focus" in flags:
        score -= 30
    if "too_dark" in flags or "too_bright" in flags:
        score -= 25
    if "low_contrast" in flags:
        score -= 8
    if "heavy_motion_possible_shake" in reason:
        score -= 20

    blur = fnum(item.get("blur_score"), 0)
    motion = fnum(item.get("motion_score"), 0)
    bright = fnum(item.get("brightness"), 0)

    if blur >= 120:
        score += 7
    elif 0 < blur < 35:
        score -= 16

    if 45 <= bright <= 210:
        score += 5
    elif bright > 0:
        score -= 6

    if 4 <= motion <= 35:
        score += 4
    elif motion > 55:
        score -= 16

    dur = fnum(item.get("duration_sec"), 0)
    if dur < 1.2:
        score -= 80
    elif dur >= 5:
        score += 4

    return round(score, 3)


def hard_skip(item: dict[str, Any], no_review: bool = False) -> bool:
    decision = str(item.get("decision") or "").lower()
    flags = str(item.get("quality_flags") or "")
    if decision == "reject":
        return True
    if no_review and decision == "review":
        return True
    if "cannot_open" in flags or "too_few_frames" in flags:
        return True
    if fnum(item.get("duration_sec"), 0) < 1.2:
        return True
    return False


def duration_for(event: str, idx: int, total: int, target_seconds: float, intent: str) -> tuple[float, str, str]:
    event = norm_event(event)
    avg = max(0.9, target_seconds / max(1, total))

    if intent == "wedding_teaser_60s":
        if idx <= 3:
            return 0.9 + (idx % 3) * 0.12, "opening_hook", "hook_fast"
        if 0.72 < idx / max(1, total) < 0.88:
            return 0.8 + (idx % 3) * 0.12, "climax", "fast_climax"
        if event in {"gia_tien", "vow_speech"}:
            return 2.0 + (idx % 2) * 0.25, event, "emotion_hold"
        return 1.35 + (idx % 3) * 0.15, event, "teaser_pace"

    # Documentary/highlight 3 phút: đủ số shot trước, duration không quá dài.
    if event in {"gia_tien", "vow_speech"}:
        return min(4.6, avg + 0.8 + (idx % 3) * 0.12), event, "emotion_hold"
    if event in {"ruoc_dau", "reception"}:
        return min(3.8, avg + 0.35 + (idx % 3) * 0.10), event, "story_pace"
    if event in {"details", "getting_ready"}:
        return max(1.4, min(3.2, avg - 0.15 + (idx % 3) * 0.10)), event, "context_bridge"
    if event == "dance_party":
        return max(1.2, min(2.4, avg - 0.7)), event, "party_energy"
    return avg, event, "general"


def source_in_out(item: dict[str, Any], dur: float, idx: int, timebase: int) -> tuple[int, int, float]:
    src_dur = max(1.0, fnum(item.get("duration_sec"), fnum(item.get("source_duration_sec"), 10.0)))
    if src_dur <= dur + 0.3:
        start = 0.0
    else:
        ratios = [0.12, 0.18, 0.25, 0.33, 0.42, 0.52, 0.62]
        start = min(src_dur - dur - 0.1, src_dur * ratios[idx % len(ratios)])
        start = max(0.0, start)
    end = min(src_dur, start + dur)
    return sec_to_frames(start, timebase), sec_to_frames(end, timebase), round(end - start, 3)


def create_smart_wedding_timeline_selector(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    intent: str = "wedding_documentary",
    target_seconds: float = 180.0,
    timebase: int = 25,
    min_order_gap: int = 0,
    allow_review: bool = True,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "smart_wedding_timeline_selector_111b")
    analyzer = load_analyzer(project_root)

    if not analyzer:
        res = {"ok": False, "error": "NO_ANALYZER_REPORT", "message": "Run module 110 first."}
        write_json(out / "smart_wedding_timeline_selector_111b_error.json", res)
        if open_folder:
            open_path(out)
        return res

    raw_items = list(analyzer.get("items") or [])
    items: list[dict[str, Any]] = []

    for item in raw_items:
        if hard_skip(item, no_review=not allow_review):
            continue
        new = dict(item)
        new["event"] = norm_event(str(new.get("event") or "general"))
        new["rank_score"] = rank_item(new)
        items.append(new)

    # Nếu --no-review quá gắt làm thiếu shot, tự fallback review nhưng trừ điểm.
    if len(items) < 12 and not allow_review:
        for item in raw_items:
            if hard_skip(item, no_review=False):
                continue
            new = dict(item)
            new["event"] = norm_event(str(new.get("event") or "general"))
            new["rank_score"] = rank_item(new) - 10
            new["fallback_review_used"] = True
            items.append(new)

    target_n = min(target_count(intent, target_seconds), len(items))
    quotas = quota(intent)

    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        buckets.setdefault(str(item["event"]), []).append(item)
    for event in buckets:
        buckets[event].sort(key=lambda r: (-fnum(r.get("rank_score"), 0), inum(r.get("source_order"), 999999)))

    selected: list[dict[str, Any]] = []
    used_files: set[str] = set()
    used_orders: list[int] = []

    def take_event(event: str, avoid_near: bool = True) -> dict[str, Any] | None:
        for item in buckets.get(event, []):
            f = str(item.get("file") or "")
            if not f or f in used_files:
                continue
            order = inum(item.get("source_order"), 0)
            if avoid_near and min_order_gap > 0 and any(abs(order - x) <= min_order_gap for x in used_orders):
                continue
            return item
        if avoid_near:
            return take_event(event, avoid_near=False)
        return None

    # Pass 1: lấy đủ quota từng phần cưới.
    for event in ["getting_ready", "details", "gia_tien", "ruoc_dau", "reception", "vow_speech", "dance_party"]:
        for _ in range(quotas.get(event, 0)):
            if len(selected) >= target_n:
                break
            item = take_event(event)
            if item is None:
                break
            selected.append(item)
            used_files.add(str(item.get("file") or ""))
            used_orders.append(inum(item.get("source_order"), 0))

    # Pass 2: fill bằng source điểm cao còn lại.
    if len(selected) < target_n:
        remaining = sorted(
            [x for x in items if str(x.get("file") or "") not in used_files],
            key=lambda r: (-fnum(r.get("rank_score"), 0), event_order(str(r.get("event"))), inum(r.get("source_order"), 999999)),
        )
        for item in remaining:
            if len(selected) >= target_n:
                break
            selected.append(item)
            used_files.add(str(item.get("file") or ""))
            used_orders.append(inum(item.get("source_order"), 0))

    # Pass 3: sort theo mạch cưới rồi thứ tự quay.
    selected.sort(key=lambda r: (event_order(str(r.get("event"))), inum(r.get("source_order"), 999999)))

    timeline: list[dict[str, Any]] = []
    total = 0.0
    n = len(selected)

    for idx, item in enumerate(selected, start=1):
        event = str(item.get("event") or "general")
        dur, section, energy = duration_for(event, idx, max(1, n), target_seconds, intent)

        # 111B: co duration chứ không bỏ clip, để không còn 5 source.
        remain_clips = max(1, n - idx + 1)
        remain_time = max(0.75 * remain_clips, target_seconds - total)
        max_now = max(0.75, remain_time / remain_clips)
        if total + dur > target_seconds and idx < n:
            dur = max(0.75, min(dur, max_now))

        si, so, real_dur = source_in_out(item, dur, idx, timebase)
        if real_dur <= 0.25:
            continue

        timeline.append({
            "index": len(timeline) + 1,
            "file": str(item.get("file") or ""),
            "filename": str(item.get("filename") or Path(str(item.get("file") or "")).name),
            "event": event,
            "role": event,
            "section": section,
            "energy": energy,
            "decision": str(item.get("decision") or ""),
            "score": fnum(item.get("score"), 0),
            "rank_score": fnum(item.get("rank_score"), 0),
            "quality_flags": str(item.get("quality_flags") or ""),
            "source_in": si,
            "source_out": so,
            "duration": real_dur,
            "duration_sec": real_dur,
            "source_duration_sec": fnum(item.get("duration_sec"), fnum(item.get("source_duration_sec"), 10.0)),
            "source_order": inum(item.get("source_order"), 0),
            "reason": f"111B_min_count_safe event={event} decision={item.get('decision')} rank={item.get('rank_score')}",
        })
        total += real_dur

    event_counts: dict[str, int] = {}
    decision_counts: dict[str, int] = {}
    for item in timeline:
        event_counts[str(item["event"])] = event_counts.get(str(item["event"]), 0) + 1
        decision_counts[str(item["decision"])] = decision_counts.get(str(item["decision"]), 0) + 1

    data = {
        "ok": True,
        "module": "111B_smart_wedding_selector_min_count_fix",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "intent": intent,
        "target_seconds": target_seconds,
        "timeline_count": len(timeline),
        "timeline_seconds": round(sum(float(x["duration"]) for x in timeline), 3),
        "event_counts": event_counts,
        "decision_counts": decision_counts,
        "allow_review": allow_review,
        "min_order_gap": min_order_gap,
        "timeline": timeline,
    }

    for name in [
        "stt_smart_wedding_timeline_v1.json",
        "stt_wedding_documentary_timeline_v1.json",
        "stt_beat_climax_timeline_v1.json",
        "stt_story_builder_v4_timeline.json",
        "stt_smart_inout_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        write_json(project_root / name, data)
    write_json(appdata_dir() / "stt_prewedding_refined_v1.json", data)

    write_json(out / "stt_smart_wedding_timeline_v1.json", data)
    write_csv(out / "SMART_WEDDING_TIMELINE_111B.csv", timeline, [
        "index", "filename", "event", "section", "energy", "decision", "score", "rank_score",
        "quality_flags", "source_in", "source_out", "duration", "source_order", "reason", "file",
    ])
    (out / "SMART_WEDDING_TIMELINE_111B_REPORT.html").write_text(
        make_html(
            "Smart Wedding Timeline Selector 111B",
            timeline,
            ["index", "filename", "event", "section", "energy", "decision", "rank_score", "quality_flags", "duration", "source_order"],
            "111B fix lỗi 111 còn 5 source: giữ đủ clip count, co duration thay vì bỏ clip.",
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
        "event_counts": event_counts,
        "decision_counts": decision_counts,
        "refined_json": str(project_root / "stt_prewedding_refined_v1.json"),
        "fix": "111B_smart_wedding_selector_min_count_fix",
    }


def make_html(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    import html
    th = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    tr = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>"
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
