from __future__ import annotations
import argparse, json
from pathlib import Path
from quality_moment_common import *

def list_targets(project: Path, source: Path, analyze_all: bool) -> list[Path]:
    targets: list[Path] = []
    visual = read_json(project / "stt_visual_ai_scene_tags_v1.json")
    timeline = read_json(project / "stt_beat_snapped_beauty_timeline_v1.json")

    rows = list(visual.get("items") or []) if analyze_all else list(timeline.get("items") or [])
    for r in rows:
        p = Path(str(r.get("file") or ""))
        if p.exists() and p.suffix.lower() in VIDEO_EXTS and p.suffix.lower() != ".braw":
            targets.append(p)

    if analyze_all and not targets and source.exists():
        for ext in VIDEO_EXTS:
            targets.extend(source.rglob(f"*{ext}"))

    return sorted(set(targets), key=lambda p: str(p).lower())

def frame_metrics(frames):
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    if not frames:
        return {}
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    blur_vals = [float(cv2.Laplacian(g, cv2.CV_64F).var()) for g in grays]
    bright_vals = [float(g.mean()) for g in grays]
    contrast_vals = [float(g.std()) for g in grays]

    motion_vals = []
    for a, b in zip(grays[:-1], grays[1:]):
        aa = cv2.resize(a, (320, 180))
        bb = cv2.resize(b, (320, 180))
        motion_vals.append(float(cv2.absdiff(aa, bb).mean()))

    blur = sum(blur_vals) / len(blur_vals)
    brightness = sum(bright_vals) / len(bright_vals)
    contrast = sum(contrast_vals) / len(contrast_vals)
    motion = sum(motion_vals) / max(1, len(motion_vals))
    motion_peak = max(motion_vals) if motion_vals else 0.0

    # Quality score intentionally conservative.
    focus_score = min(100.0, max(0.0, (blur / 220.0) * 100.0))
    exposure_score = max(0.0, 100.0 - abs(brightness - 118.0) * 0.9)
    contrast_score = min(100.0, max(0.0, contrast * 2.2))
    stability_score = max(0.0, 100.0 - motion * 4.3 - max(0.0, motion_peak - 18.0) * 2.5)

    score = (
        focus_score * 0.30
        + exposure_score * 0.18
        + contrast_score * 0.12
        + stability_score * 0.40
    )

    severe_shake = motion_peak > 30.0 or motion > 21.0
    likely_blur = blur < 45.0
    too_dark = brightness < 28.0
    too_bright = brightness > 235.0

    if severe_shake:
        score -= 25
    if likely_blur:
        score -= 22
    if too_dark or too_bright:
        score -= 15

    return {
        "quality_score": round(max(0.0, min(100.0, score)), 3),
        "focus_score": round(focus_score, 3),
        "stability_score": round(stability_score, 3),
        "exposure_score": round(exposure_score, 3),
        "contrast_score": round(contrast_score, 3),
        "blur_laplacian": round(blur, 3),
        "brightness": round(brightness, 3),
        "contrast": round(contrast, 3),
        "motion_avg": round(motion, 3),
        "motion_peak": round(motion_peak, 3),
        "severe_shake": severe_shake,
        "likely_blur": likely_blur,
        "too_dark": too_dark,
        "too_bright": too_bright,
    }

def analyze_file(path: Path, windows: int, sample_span: float, frames_per_window: int):
    import cv2  # type: ignore

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"ok": False, "error": "OPEN_FAILED"}

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if fps > 0 and frame_count > 0 else 0.0

    if duration <= 0.5:
        cap.release()
        return {"ok": False, "error": "DURATION_UNKNOWN_OR_TOO_SHORT", "duration_sec": duration}

    margin = min(1.0, duration * 0.08)
    usable_start = margin
    usable_end = max(usable_start + 0.1, duration - margin)

    centers = []
    if windows <= 1:
        centers = [(usable_start + usable_end) / 2]
    else:
        for i in range(windows):
            alpha = i / (windows - 1)
            centers.append(usable_start + (usable_end - usable_start) * alpha)

    result_windows = []
    for idx, center in enumerate(centers):
        start = max(0.0, center - sample_span / 2)
        end = min(duration, center + sample_span / 2)
        frames = []
        for j in range(frames_per_window):
            alpha = j / max(1, frames_per_window - 1)
            sec = start + (end - start) * alpha
            cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
            ok, frame = cap.read()
            if ok and frame is not None:
                frames.append(frame)
        metrics = frame_metrics(frames)
        result_windows.append({
            "window_index": idx,
            "center_sec": round(center, 3),
            "sample_start_sec": round(start, 3),
            "sample_end_sec": round(end, 3),
            "frame_count": len(frames),
            **metrics,
        })
    cap.release()

    valid = [w for w in result_windows if w.get("frame_count", 0) >= 2]
    best = max(valid, key=lambda w: fnum(w.get("quality_score"), 0), default={})
    avg_score = sum(fnum(w.get("quality_score"), 0) for w in valid) / max(1, len(valid))
    severe_count = sum(1 for w in valid if w.get("severe_shake"))
    blur_count = sum(1 for w in valid if w.get("likely_blur"))

    return {
        "ok": bool(valid),
        "fps": round(fps, 3),
        "duration_sec": round(duration, 3),
        "window_count": len(valid),
        "average_quality_score": round(avg_score, 3),
        "best_quality_score": fnum(best.get("quality_score"), 0),
        "best_center_sec": fnum(best.get("center_sec"), 0),
        "severe_window_count": severe_count,
        "blur_window_count": blur_count,
        "quality_class": (
            "strong" if fnum(best.get("quality_score"), 0) >= 68
            else "usable" if fnum(best.get("quality_score"), 0) >= 48
            else "weak"
        ),
        "windows": result_windows,
    }

def main():
    p = argparse.ArgumentParser(description="124 Shot Quality Gate V3.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--windows", type=int, default=10)
    p.add_argument("--sample-span", type=float, default=1.1)
    p.add_argument("--frames-per-window", type=int, default=5)
    p.add_argument("--analyze-all", action="store_true")
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "shot_quality_gate_v3_124")

    targets = list_targets(project, source, a.analyze_all)
    if a.max_files > 0:
        targets = targets[:a.max_files]

    if not targets:
        res = {"ok": False, "error": "NO_VIDEO_TARGETS"}
        write_json(out / "QUALITY_GATE_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    items = []
    total = len(targets)
    for i, path in enumerate(targets, 1):
        if i == 1 or i % 10 == 0 or i == total:
            print(f"[124] quality {i}/{total}: {path.name}", flush=True)
        result = analyze_file(path, a.windows, a.sample_span, a.frames_per_window)
        items.append({
            "filename": path.name,
            "file": str(path),
            **result,
        })

    data = {
        "ok": True,
        "module": "124_shot_quality_gate_v3",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "file_count": len(items),
        "strong_count": sum(1 for x in items if x.get("quality_class") == "strong"),
        "usable_count": sum(1 for x in items if x.get("quality_class") == "usable"),
        "weak_count": sum(1 for x in items if x.get("quality_class") == "weak"),
        "items": items,
    }

    write_json(project / "stt_shot_quality_windows_v3.json", data)
    write_json(out / "stt_shot_quality_windows_v3.json", data)

    flat = []
    for item in items:
        for w in item.get("windows", []):
            flat.append({
                "filename": item.get("filename"),
                "file": item.get("file"),
                "duration_sec": item.get("duration_sec"),
                "quality_class": item.get("quality_class"),
                **w,
            })
    write_csv(out / "SHOT_QUALITY_WINDOWS_V3.csv", flat, [
        "filename","quality_class","duration_sec","window_index","center_sec",
        "sample_start_sec","sample_end_sec","quality_score","focus_score",
        "stability_score","exposure_score","contrast_score","blur_laplacian",
        "brightness","motion_avg","motion_peak","severe_shake","likely_blur",
        "too_dark","too_bright","file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "file_count": len(items),
        "strong_count": data["strong_count"],
        "usable_count": data["usable_count"],
        "weak_count": data["weak_count"],
        "fix": "124_shot_quality_gate_v3",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
