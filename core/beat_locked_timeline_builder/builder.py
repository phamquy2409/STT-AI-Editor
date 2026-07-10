
from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


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


def load_base_timeline(project_root: Path) -> list[dict[str, Any]]:
    # IMPORTANT: avoid loading previous beat-locked timeline first, otherwise 119B reuses short 112s result.
    for name in [
        "stt_smart_wedding_timeline_v1.json",
        "stt_wedding_documentary_timeline_v1.json",
        "stt_story_builder_v4_timeline.json",
        "stt_prewedding_refined_v1.json",
    ]:
        d = read_json(project_root / name)
        if isinstance(d.get("timeline"), list):
            tl = list(d["timeline"])
            if tl:
                return tl
    return []


def load_cut_points(project_root: Path) -> list[dict[str, Any]]:
    d = read_json(project_root / "stt_real_audio_beat_energy_v1.json") or read_json(appdata_dir() / "stt_real_audio_beat_energy_v1.json")
    pts = list(d.get("cut_points") or [])
    clean = []
    for p in pts:
        t = fnum(p.get("time_sec"), -1)
        if t >= 0:
            q = dict(p)
            q["time_sec"] = t
            clean.append(q)
    clean.sort(key=lambda x: fnum(x.get("time_sec"), 0))
    return clean


def nearest_cut(points: list[dict[str, Any]], target: float, min_time: float, max_time: float) -> float:
    candidates = [fnum(p.get("time_sec"), 0) for p in points if min_time <= fnum(p.get("time_sec"), 0) <= max_time]
    if not candidates:
        return target
    return min(candidates, key=lambda x: abs(x - target))


def build_full_length_spans(points: list[dict[str, Any]], clip_count: int, target_seconds: float, min_clip_sec: float, max_clip_sec: float) -> list[dict[str, Any]]:
    if clip_count <= 0:
        return []

    # Always cover the whole requested timeline. Use real cut points near ideal boundaries.
    boundaries = [0.0]
    avg = target_seconds / clip_count

    for i in range(1, clip_count):
        ideal = i * avg
        min_time = max(boundaries[-1] + min_clip_sec, ideal - avg * 0.45)
        max_time = min(target_seconds - (clip_count - i) * min_clip_sec, ideal + avg * 0.45)
        if max_time < min_time:
            chosen = ideal
        else:
            chosen = nearest_cut(points, ideal, min_time, max_time)
        # Safety clamp
        chosen = max(boundaries[-1] + min_clip_sec, min(chosen, target_seconds - (clip_count - i) * min_clip_sec))
        # If chosen creates too long previous span, split by ideal.
        if chosen - boundaries[-1] > max_clip_sec:
            chosen = boundaries[-1] + max_clip_sec
        boundaries.append(round(chosen, 3))

    boundaries.append(round(target_seconds, 3))

    spans = []
    for i in range(clip_count):
        s = boundaries[i]
        e = boundaries[i+1]
        if e <= s:
            e = s + min_clip_sec
        spans.append({
            "index": i + 1,
            "start_sec": round(s, 3),
            "end_sec": round(e, 3),
            "duration_sec": round(e - s, 3),
            "section": section_for_pos(s, target_seconds),
            "source": "119B_nearest_real_cut_full_length",
        })
    return spans


def section_for_pos(t: float, duration: float) -> str:
    if t < duration * 0.12:
        return "intro"
    if duration * 0.42 <= t < duration * 0.58:
        return "build"
    if duration * 0.58 <= t < duration * 0.82:
        return "climax"
    if t >= duration * 0.88:
        return "ending"
    return "story"


def create_beat_locked_timeline_builder(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    target_seconds: float = 180.0,
    timebase: int = 25,
    min_clip_sec: float = 0.9,
    max_clip_sec: float = 6.0,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "beat_locked_timeline_builder_119b")

    timeline = load_base_timeline(project_root)
    points = load_cut_points(project_root)

    if not timeline:
        res = {"ok": False, "error": "NO_BASE_TIMELINE", "message": "Run 111B first."}
        write_json(out / "beat_locked_timeline_119b_error.json", res)
        if open_folder:
            open_path(out)
        return res

    if len(points) < 3:
        res = {"ok": False, "error": "NO_REAL_CUT_POINTS", "message": "Run 118 first."}
        write_json(out / "beat_locked_timeline_119b_error.json", res)
        if open_folder:
            open_path(out)
        return res

    clip_count = len(timeline)
    spans = build_full_length_spans(points, clip_count, target_seconds, min_clip_sec, max_clip_sec)

    locked = []
    for idx, (item, span) in enumerate(zip(timeline, spans), start=1):
        new = dict(item)
        dur = fnum(span.get("duration_sec"), target_seconds / clip_count)
        src_dur = max(1.0, fnum(new.get("source_duration_sec"), fnum(new.get("duration_sec"), 10.0)))

        # Preserve existing source_in where possible, but adjust if duration longer.
        src_in_sec = frames_to_sec(inum(new.get("source_in"), 0), timebase)
        if src_in_sec + dur > src_dur:
            src_in_sec = max(0.0, src_dur - dur - 0.1)
        src_out_sec = min(src_dur, src_in_sec + dur)
        real_dur = max(0.1, src_out_sec - src_in_sec)

        # If source clip is shorter than beat span, timeline span must use real source duration.
        # Keep timeline_start aligned to beat; timeline_end may be slightly earlier for short clips.
        start_sec = fnum(span.get("start_sec"), 0)
        end_sec = start_sec + real_dur

        new.update({
            "index": idx,
            "timeline_start": sec_to_frames(start_sec, timebase),
            "timeline_end": sec_to_frames(end_sec, timebase),
            "source_in": sec_to_frames(src_in_sec, timebase),
            "source_out": sec_to_frames(src_out_sec, timebase),
            "duration": round(real_dur, 3),
            "duration_sec": round(real_dur, 3),
            "beat_locked": True,
            "beat_section": span.get("section"),
            "beat_source": span.get("source"),
            "beat_target_start_sec": round(start_sec, 3),
            "beat_target_end_sec": round(fnum(span.get("end_sec"), end_sec), 3),
            "reason": str(new.get("reason", "")) + f"__119B_FULL_LENGTH_BEAT_LOCK start={start_sec} target_end={span.get('end_sec')}",
        })
        locked.append(new)

    timeline_seconds = max([frames_to_sec(inum(x.get("timeline_end"), 0), timebase) for x in locked] + [0])

    data = {
        "ok": True,
        "module": "119B_full_length_beat_locked_timeline",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "target_seconds": target_seconds,
        "timeline_count": len(locked),
        "timeline_seconds": round(timeline_seconds, 3),
        "cut_point_count": len(points),
        "span_count": len(spans),
        "base_clip_count": clip_count,
        "timeline": locked,
    }

    for name in [
        "stt_beat_locked_timeline_v1.json",
        "stt_music_synced_timeline_v1.json",
        "stt_smart_wedding_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        write_json(project_root / name, data)
    write_json(appdata_dir() / "stt_prewedding_refined_v1.json", data)

    write_json(out / "stt_beat_locked_timeline_v1.json", data)
    write_csv(out / "BEAT_LOCKED_TIMELINE_119B.csv", locked, [
        "index", "filename", "event", "beat_section", "beat_target_start_sec", "beat_target_end_sec",
        "timeline_start", "timeline_end", "source_in", "source_out", "duration", "beat_locked", "file",
    ])

    html = html_table(
        "Beat Locked Timeline Builder 119B",
        locked,
        ["index", "filename", "event", "beat_section", "beat_target_start_sec", "beat_target_end_sec", "duration"],
        "119B phân bố clip trên toàn bộ target_seconds, không chỉ lấy 48 cut đầu.",
    )
    (out / "BEAT_LOCKED_TIMELINE_119B_REPORT.html").write_text(html, encoding="utf-8")

    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(locked),
        "timeline_seconds": round(timeline_seconds, 3),
        "cut_point_count": len(points),
        "span_count": len(spans),
        "fix": "119B_full_length_beat_locked_timeline",
    }


def html_table(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
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
