
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/5thang5test"
MEDIA_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi"}


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


def open_path(path: Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def outdir(project_root: Path, name: str) -> Path:
    p = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def source_files(source_folder: str | Path) -> list[Path]:
    root = Path(source_folder)
    if not root.exists():
        return []
    return sorted(
        [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXTS],
        key=lambda p: str(p).lower(),
    )


def probe_media(path: Path) -> dict[str, Any]:
    info = {"fps": 25.0, "frames": 250, "duration_sec": 10.0, "width": 0, "height": 0, "ok": False}
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(path))
        if cap.isOpened():
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            dur = frames / fps if fps > 0 and frames > 0 else 10.0
            info.update({
                "fps": fps,
                "frames": frames,
                "duration_sec": max(1.0, dur),
                "width": width,
                "height": height,
                "ok": True,
            })
        cap.release()
    except Exception:
        pass
    return info


def sec_to_frames(sec: float, timebase: int = 25) -> int:
    return int(round(max(0.04, sec) * timebase))


def classify_wedding_event(path: Path, index: int, total: int) -> str:
    low = path.name.lower()

    # Filename hints first, but most camera sources have no descriptive names.
    if any(x in low for x in ["makeup", "getting", "prep", "ready", "dress", "suit", "shoe"]):
        return "getting_ready"
    if any(x in low for x in ["detail", "ring", "flower", "decor", "bouquet", "invite", "invitation"]):
        return "details"
    if any(x in low for x in ["gia", "tien", "altar", "family", "tea", "ceremony"]):
        return "gia_tien"
    if any(x in low for x in ["ruoc", "dau", "gate", "car", "arrival", "procession"]):
        return "ruoc_dau"
    if any(x in low for x in ["vow", "speech", "voice", "toast"]):
        return "vow_speech"
    if any(x in low for x in ["reception", "stage", "cake", "champagne", "party"]):
        return "reception"
    if any(x in low for x in ["dance", "dj"]):
        return "dance_party"

    # If filenames are generic, use chronological camera order as documentary approximation.
    pos = index / max(1, total)
    if pos < 0.12:
        return "getting_ready"
    if pos < 0.22:
        return "details"
    if pos < 0.45:
        return "gia_tien"
    if pos < 0.58:
        return "ruoc_dau"
    if pos < 0.75:
        return "reception"
    if pos < 0.88:
        return "vow_speech"
    return "dance_party"


def event_weight(event: str) -> float:
    return {
        "getting_ready": 66,
        "details": 62,
        "gia_tien": 82,
        "ruoc_dau": 76,
        "reception": 74,
        "vow_speech": 86,
        "dance_party": 70,
        "general": 55,
    }.get(event, 55)


def clip_duration(event: str, pos: float, style: str) -> tuple[float, str]:
    # Wedding documentary giữ cảm xúc lâu hơn prewedding reel.
    if style == "wedding_teaser_60s":
        if pos < 0.12:
            return 1.0, "hook_fast"
        if 0.72 <= pos <= 0.88:
            return 0.9, "climax_fast"
        if event in {"gia_tien", "vow_speech"}:
            return 2.6, "emotion_hold"
        return 1.6, "teaser_pace"

    if style == "wedding_highlight_3min":
        if event in {"gia_tien", "vow_speech"}:
            return 4.8, "emotion_hold"
        if event in {"getting_ready", "reception"}:
            return 3.4, "story_pace"
        return 2.6, "visual_bridge"

    # wedding_documentary / phóng sự: hơi dài hơn, giữ nghi lễ.
    if event in {"gia_tien", "vow_speech"}:
        return 5.2, "documentary_emotion"
    if event in {"ruoc_dau", "reception"}:
        return 3.8, "documentary_story"
    if event in {"getting_ready", "details"}:
        return 2.8, "documentary_context"
    if event == "dance_party":
        return 2.2, "party_energy"
    return 3.0, "documentary_general"


def target_clip_count(intent: str, target_seconds: float) -> tuple[int, int]:
    if intent == "wedding_teaser_60s":
        return 24, 36
    if intent == "wedding_highlight_3min":
        return 45, 80
    if intent in {"wedding_documentary", "gia_tien_story", "reception_story"}:
        # For test, not full 30-60 min documentary. This creates a meaningful XML sample.
        return 28, 70
    return 24, 40


def select_by_event(files: list[Path], intent: str, target_seconds: float) -> list[dict[str, Any]]:
    min_count, max_count = target_clip_count(intent, target_seconds)
    total_files = len(files)
    candidates: list[dict[str, Any]] = []

    for idx, p in enumerate(files, start=1):
        info = probe_media(p)
        dur = float(info.get("duration_sec", 10.0))
        if dur < 1.2:
            continue
        event = classify_wedding_event(p, idx, total_files)
        candidates.append({
            "path": p,
            "filename": p.name,
            "event": event,
            "score": event_weight(event) + (4 if p.stat().st_size > 30 * 1024 * 1024 else 0),
            "source_duration_sec": round(dur, 3),
            "fps": info.get("fps", 25.0),
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "source_order": idx,
        })

    buckets: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        buckets.setdefault(str(c["event"]), []).append(c)

    for event in buckets:
        # giữ thứ tự thời gian trong từng phần cưới, không sort score quá mạnh
        buckets[event].sort(key=lambda x: int(x["source_order"]))

    if intent == "gia_tien_story":
        cycle = ["details", "getting_ready", "gia_tien", "gia_tien", "ruoc_dau", "vow_speech"]
    elif intent == "reception_story":
        cycle = ["reception", "details", "vow_speech", "reception", "dance_party", "dance_party"]
    elif intent == "wedding_teaser_60s":
        cycle = ["getting_ready", "details", "gia_tien", "ruoc_dau", "reception", "vow_speech", "dance_party"]
    else:
        cycle = ["getting_ready", "details", "gia_tien", "gia_tien", "ruoc_dau", "reception", "vow_speech", "reception", "dance_party"]

    picked: list[dict[str, Any]] = []
    used: set[str] = set()
    pos = {k: 0 for k in buckets}

    # Lấy theo event cycle để đủ mạch, không bị vài clip cô dâu ngoài trời.
    while len(picked) < min(max_count, len(candidates)):
        added = False
        for event in cycle:
            bucket = buckets.get(event, [])
            while pos.get(event, 0) < len(bucket) and str(bucket[pos[event]]["path"]) in used:
                pos[event] += 1
            if pos.get(event, 0) < len(bucket):
                item = bucket[pos[event]]
                pos[event] += 1
                picked.append(item)
                used.add(str(item["path"]))
                added = True
                if len(picked) >= max_count:
                    break
        if not added:
            # Fill remaining by chronological order.
            for c in sorted(candidates, key=lambda x: int(x["source_order"])):
                if str(c["path"]) not in used:
                    picked.append(c)
                    used.add(str(c["path"]))
                    if len(picked) >= max_count:
                        break
            break

        # Nếu teaser 60s, chỉ cần khoảng 24-36 shot. Highlight/doc giữ nhiều hơn.
        if len(picked) >= min_count and intent == "wedding_teaser_60s":
            break

    if len(picked) < min_count:
        for c in sorted(candidates, key=lambda x: int(x["source_order"])):
            if str(c["path"]) not in used:
                picked.append(c)
                used.add(str(c["path"]))
                if len(picked) >= min_count:
                    break

    return picked


def create_wedding_documentary_intent_timeline(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    intent: str = "wedding_documentary",
    target_seconds: float = 180.0,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    source_folder = Path(source_folder)
    out = outdir(project_root, "wedding_documentary_intent_router")
    files = source_files(source_folder)

    if not files:
        res = {"ok": False, "error": "NO_SOURCE_FILES", "source_folder": str(source_folder)}
        write_json(out / "wedding_documentary_intent_error.json", res)
        if open_folder:
            open_path(out)
        return res

    picked = select_by_event(files, intent=intent, target_seconds=target_seconds)
    timeline: list[dict[str, Any]] = []
    total = 0.0
    n = len(picked)

    for i, item in enumerate(picked, start=1):
        event = str(item["event"])
        pos = i / max(1, n)
        dur, energy = clip_duration(event, pos, intent)
        # biến thiên nhẹ để không đều máy
        dur += ((i % 5) - 2) * 0.18
        dur = max(0.75, dur)

        if total + dur > target_seconds:
            # Đừng cắt quá bé nếu đã đủ hơn 60% clip; còn thiếu thì cho phép vượt nhẹ.
            remaining = target_seconds - total
            if remaining <= 0.7 and len(timeline) >= 8:
                break
            dur = max(0.75, remaining)

        source_dur = max(1.0, float(item["source_duration_sec"]))
        # Với phóng sự cưới, tránh lấy đầu source nếu đầu cú máy hay rung.
        start_ratio = 0.08 + ((i % 8) * 0.035)
        start_sec = min(max(0.0, source_dur * start_ratio), max(0.0, source_dur - dur - 0.1))
        end_sec = min(source_dur, start_sec + dur)

        if end_sec <= start_sec + 0.2:
            continue

        section = event
        if i <= 3:
            section = "opening_hook"
        elif i >= max(1, n - 2):
            section = "ending"

        timeline.append({
            "index": len(timeline) + 1,
            "file": str(item["path"]),
            "filename": item["filename"],
            "event": event,
            "role": event,
            "section": section,
            "energy": energy,
            "score": round(float(item["score"]), 3),
            "source_in": sec_to_frames(start_sec, timebase),
            "source_out": sec_to_frames(end_sec, timebase),
            "duration": round(end_sec - start_sec, 3),
            "duration_sec": round(end_sec - start_sec, 3),
            "source_duration_sec": item["source_duration_sec"],
            "source_order": item["source_order"],
            "reason": f"109_{intent}_{event}_{energy}",
        })
        total += max(0.1, end_sec - start_sec)

        if total >= target_seconds and len(timeline) >= 8:
            break

    event_counts: dict[str, int] = {}
    for item in timeline:
        event_counts[item["event"]] = event_counts.get(item["event"], 0) + 1

    data = {
        "ok": True,
        "module": "109_wedding_documentary_intent_router",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "intent": intent,
        "source_folder": str(source_folder),
        "source_media_count": len(files),
        "target_seconds": target_seconds,
        "timeline_count": len(timeline),
        "timeline_seconds": round(sum(float(x["duration"]) for x in timeline), 3),
        "event_counts": event_counts,
        "timeline": timeline,
    }

    # Ghi vào refined để exporter 101E đọc, dù tên script exporter còn là prewedding.
    for name in [
        "stt_wedding_documentary_timeline_v1.json",
        "stt_beat_climax_timeline_v1.json",
        "stt_story_builder_v4_timeline.json",
        "stt_smart_inout_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        write_json(project_root / name, data)
    write_json(appdata_dir() / "stt_prewedding_refined_v1.json", data)

    write_json(out / "stt_wedding_documentary_timeline_v1.json", data)
    write_csv(out / "WEDDING_DOCUMENTARY_TIMELINE.csv", timeline, [
        "index", "filename", "event", "section", "energy", "score",
        "source_in", "source_out", "duration", "source_order", "reason", "file",
    ])

    (out / "WEDDING_DOCUMENTARY_REPORT.html").write_text(
        make_html(
            "Wedding Documentary Intent Router",
            timeline,
            ["index", "filename", "event", "section", "energy", "duration", "source_order", "reason"],
            "Timeline theo mạch phóng sự cưới/gia tiên/rước dâu/reception, không dùng logic prewedding reel.",
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
        "source_media_count": len(files),
        "refined_json": str(project_root / "stt_prewedding_refined_v1.json"),
        "fix": "109_wedding_documentary_intent_router",
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
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left}</style></head>"
        f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{th}</tr>{tr}</table></div></body></html>"
    )
