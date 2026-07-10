
from __future__ import annotations

import csv
import json
import os
import statistics
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
                "fps": round(fps, 3),
                "frames": frames,
                "duration_sec": round(max(1.0, dur), 3),
                "width": width,
                "height": height,
                "ok": True,
            })
        cap.release()
    except Exception:
        pass
    return info


def classify_by_name_and_order(path: Path, index: int, total: int) -> tuple[str, str]:
    low = path.name.lower()
    hints = {
        "getting_ready": ["makeup", "getting", "prep", "ready", "dress", "suit", "shoe", "hair"],
        "details": ["detail", "ring", "flower", "decor", "bouquet", "invite", "invitation", "shoe"],
        "gia_tien": ["gia", "tien", "altar", "family", "tea", "ceremony", "traditional"],
        "ruoc_dau": ["ruoc", "dau", "gate", "car", "arrival", "procession"],
        "vow_speech": ["vow", "speech", "voice", "toast", "mc"],
        "reception": ["reception", "stage", "cake", "champagne", "party", "banquet"],
        "dance_party": ["dance", "dj", "club"],
    }
    for event, keys in hints.items():
        if any(k in low for k in keys):
            return event, "filename_hint"

    # Generic camera filenames: approximate by shooting order.
    pos = index / max(1, total)
    if pos < 0.12:
        return "getting_ready", "chronological_hint"
    if pos < 0.22:
        return "details", "chronological_hint"
    if pos < 0.45:
        return "gia_tien", "chronological_hint"
    if pos < 0.58:
        return "ruoc_dau", "chronological_hint"
    if pos < 0.75:
        return "reception", "chronological_hint"
    if pos < 0.88:
        return "vow_speech", "chronological_hint"
    return "dance_party", "chronological_hint"


def sample_visual_metrics(path: Path, quick: bool = True) -> dict[str, Any]:
    metrics = {
        "visual_ok": False,
        "blur_score": None,
        "brightness": None,
        "contrast": None,
        "motion_score": None,
        "quality_flags": [],
    }
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            metrics["quality_flags"] = ["cannot_open"]
            return metrics

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total < 3:
            metrics["quality_flags"] = ["too_few_frames"]
            cap.release()
            return metrics

        positions = [0.45, 0.55] if quick else [0.25, 0.5, 0.75]
        grays = []
        blur_vals = []
        bright_vals = []
        contrast_vals = []

        for pos in positions:
            frame_no = max(0, min(total - 1, int(total * pos)))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            grays.append(gray)
            blur_vals.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            bright_vals.append(float(np.mean(gray)))
            contrast_vals.append(float(np.std(gray)))

        cap.release()

        flags: list[str] = []
        if not blur_vals:
            flags.append("no_sample_frame")
        else:
            blur = statistics.mean(blur_vals)
            bright = statistics.mean(bright_vals)
            contrast = statistics.mean(contrast_vals)
            motion = None
            if len(grays) >= 2:
                # Approx motion between sample frames. High can mean camera move or scene action.
                small_a = cv2.resize(grays[0], (160, 90))
                small_b = cv2.resize(grays[1], (160, 90))
                motion = float(np.mean(cv2.absdiff(small_a, small_b)))

            if blur < 28:
                flags.append("possible_out_focus")
            elif blur < 60:
                flags.append("soft_focus")

            if bright < 22:
                flags.append("too_dark")
            elif bright > 235:
                flags.append("too_bright")

            if contrast < 18:
                flags.append("low_contrast")

            metrics.update({
                "visual_ok": True,
                "blur_score": round(blur, 3),
                "brightness": round(bright, 3),
                "contrast": round(contrast, 3),
                "motion_score": round(motion, 3) if motion is not None else None,
                "quality_flags": flags,
            })
    except Exception as exc:
        metrics["quality_flags"] = [f"visual_check_failed:{type(exc).__name__}"]
    return metrics


def event_score(event: str) -> float:
    return {
        "getting_ready": 64,
        "details": 60,
        "gia_tien": 86,
        "ruoc_dau": 78,
        "reception": 74,
        "vow_speech": 88,
        "dance_party": 68,
        "general": 55,
    }.get(event, 55)


def quality_score(metrics: dict[str, Any], duration_sec: float, size_mb: float) -> tuple[float, str]:
    score = 0.0
    reasons = []

    if duration_sec < 1.5:
        score -= 60
        reasons.append("too_short")
    elif duration_sec < 4:
        score -= 12
        reasons.append("short_clip")
    elif duration_sec > 8:
        score += 8
        reasons.append("enough_duration")

    if size_mb > 100:
        score += 8
        reasons.append("large_file")
    elif size_mb > 30:
        score += 4

    blur = metrics.get("blur_score")
    bright = metrics.get("brightness")
    contrast = metrics.get("contrast")
    motion = metrics.get("motion_score")
    flags = metrics.get("quality_flags") or []

    if blur is not None:
        if blur >= 120:
            score += 16
            reasons.append("sharp")
        elif blur >= 60:
            score += 8
            reasons.append("usable_sharpness")
        elif blur < 28:
            score -= 35
            reasons.append("possible_out_focus")
        else:
            score -= 10
            reasons.append("soft_focus")

    if bright is not None:
        if 45 <= bright <= 205:
            score += 8
            reasons.append("good_brightness")
        elif bright < 22 or bright > 235:
            score -= 25
            reasons.append("bad_exposure")
        else:
            score -= 6

    if contrast is not None:
        if contrast >= 35:
            score += 6
        elif contrast < 18:
            score -= 12
            reasons.append("low_contrast")

    if motion is not None:
        if motion < 2:
            score -= 8
            reasons.append("static_or_no_action")
        elif motion <= 35:
            score += 6
            reasons.append("usable_motion")
        else:
            score -= 8
            reasons.append("heavy_motion_possible_shake")

    for f in flags:
        if f in {"possible_out_focus", "too_dark", "too_bright", "low_contrast"}:
            score -= 10

    return round(score, 3), "|".join(reasons)


def decision_from_score(score: float, flags: list[str]) -> str:
    bad_flags = {"cannot_open", "too_few_frames", "possible_out_focus", "too_dark", "too_bright"}
    if any(f in bad_flags for f in flags):
        if score < 70:
            return "review"
    if score >= 95:
        return "strong_pick"
    if score >= 76:
        return "keep"
    if score >= 55:
        return "review"
    return "reject"


def create_wedding_source_analyzer_v2(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    max_files: int = 252,
    quick: bool = True,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    source_folder = Path(source_folder)
    out = outdir(project_root, "wedding_source_analyzer_v2")
    files = source_files(source_folder)
    if max_files and max_files > 0:
        files = files[:max_files]

    rows: list[dict[str, Any]] = []
    total = len(files)

    for idx, p in enumerate(files, start=1):
        info = probe_media(p)
        visual = sample_visual_metrics(p, quick=quick)
        event, method = classify_by_name_and_order(p, idx, total)
        duration_sec = float(info.get("duration_sec") or 0)
        size_mb = round(p.stat().st_size / (1024 * 1024), 2)
        q_score, reason = quality_score(visual, duration_sec, size_mb)
        total_score = round(event_score(event) + q_score, 3)
        flags = list(visual.get("quality_flags") or [])
        decision = decision_from_score(total_score, flags)

        rows.append({
            "index": idx,
            "file": str(p),
            "filename": p.name,
            "event": event,
            "classification_method": method,
            "decision": decision,
            "score": total_score,
            "event_score": event_score(event),
            "quality_score": q_score,
            "reason": reason,
            "quality_flags": "|".join(flags),
            "duration_sec": duration_sec,
            "fps": info.get("fps"),
            "width": info.get("width"),
            "height": info.get("height"),
            "size_mb": size_mb,
            "blur_score": visual.get("blur_score"),
            "brightness": visual.get("brightness"),
            "contrast": visual.get("contrast"),
            "motion_score": visual.get("motion_score"),
            "source_order": idx,
        })

    event_counts: dict[str, int] = {}
    decision_counts: dict[str, int] = {}
    for r in rows:
        event_counts[str(r["event"])] = event_counts.get(str(r["event"]), 0) + 1
        decision_counts[str(r["decision"])] = decision_counts.get(str(r["decision"]), 0) + 1

    # Suggested picks: keep the order documentary-friendly, but strong/keep first within each event.
    suggested = sorted(
        [r for r in rows if r["decision"] in {"strong_pick", "keep", "review"}],
        key=lambda r: (
            {"getting_ready":0, "details":1, "gia_tien":2, "ruoc_dau":3, "reception":4, "vow_speech":5, "dance_party":6}.get(str(r["event"]), 9),
            -float(r["score"]),
            int(r["source_order"]),
        ),
    )

    data = {
        "ok": True,
        "module": "110_wedding_source_analyzer_v2",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source_folder": str(source_folder),
        "checked_count": len(rows),
        "event_counts": event_counts,
        "decision_counts": decision_counts,
        "items": rows,
        "suggested_items": suggested[:120],
    }

    write_json(project_root / "stt_wedding_source_analyzer_v2.json", data)
    write_json(appdata_dir() / "stt_wedding_source_analyzer_v2.json", data)
    write_json(out / "stt_wedding_source_analyzer_v2.json", data)
    write_csv(out / "WEDDING_SOURCE_ANALYZER_V2.csv", rows, [
        "index", "filename", "event", "decision", "score", "quality_flags",
        "duration_sec", "blur_score", "brightness", "contrast", "motion_score",
        "reason", "file",
    ])
    write_csv(out / "WEDDING_SOURCE_SUGGESTED_PICKS.csv", suggested, [
        "index", "filename", "event", "decision", "score", "duration_sec", "reason", "file",
    ])

    (out / "WEDDING_SOURCE_ANALYZER_V2_REPORT.html").write_text(
        make_html(
            "Wedding Source Analyzer V2",
            rows,
            ["index", "filename", "event", "decision", "score", "quality_flags", "duration_sec", "blur_score", "brightness", "motion_score"],
            "Phân tích source cưới: event, độ nét, sáng tối, motion, điểm chọn/bỏ. 111 sẽ dùng report này để chọn timeline tốt hơn.",
        ),
        encoding="utf-8",
    )

    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "checked_count": len(rows),
        "event_counts": event_counts,
        "decision_counts": decision_counts,
        "analyzer_json": str(project_root / "stt_wedding_source_analyzer_v2.json"),
        "fix": "110_wedding_source_analyzer_v2",
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
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}"
        ".strong_pick{color:#8f8}.reject{color:#f88}</style></head>"
        f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{th}</tr>{tr}</table></div></body></html>"
    )
