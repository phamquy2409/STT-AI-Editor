from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_134_136_common import *


def quality_windows_for(
    row: dict[str, Any],
    by_path: dict[str, dict[str, Any]],
    by_name: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], float]:
    path_key = norm_path(row.get("file"))
    name_key = str(
        row.get("filename")
        or Path(str(row.get("file") or "")).name
    ).lower()

    quality_row = by_path.get(path_key)
    if not quality_row:
        matches = by_name.get(name_key, [])
        quality_row = matches[0] if matches else {}

    windows = list(
        quality_row.get("windows")
        or quality_row.get("quality_windows")
        or []
    )

    media_duration = fnum(
        row.get("media_duration_sec"),
        fnum(
            quality_row.get("duration_sec"),
            max(
                fnum(row.get("source_out_sec"), 0),
                fnum(row.get("source_in_sec"), 0)
                + fnum(row.get("duration_sec"), 0),
            ),
        ),
    )
    return windows, media_duration


def candidate_center(window: dict[str, Any]) -> float:
    return fnum(
        window.get("center_sec"),
        (
            fnum(window.get("start_sec"), 0)
            + fnum(window.get("end_sec"), 0)
        ) / 2.0,
    )


def base_window_score(window: dict[str, Any]) -> float:
    score = fnum(
        window.get("quality_score"),
        fnum(window.get("score"), 45),
    )

    if window.get("severe_shake"):
        score -= 32
    if window.get("likely_blur"):
        score -= 22

    focus = fnum(window.get("focus_score"), fnum(window.get("focus"), 0))
    stability = fnum(window.get("stability_score"), fnum(window.get("stability"), 0))
    exposure = fnum(window.get("exposure_score"), fnum(window.get("exposure"), 0))
    contrast = fnum(window.get("contrast_score"), fnum(window.get("contrast"), 0))

    if focus > 0:
        score += clamp(focus / 100.0, 0, 1) * 7
    if stability > 0:
        score += clamp(stability / 100.0, 0, 1) * 8
    if exposure > 0:
        score += clamp(exposure / 100.0, 0, 1) * 4
    if contrast > 0:
        score += clamp(contrast / 100.0, 0, 1) * 3

    return score


def motion_target(tag: str) -> tuple[float, float]:
    tag = str(tag or "other")

    if tag in {"decor", "detail_beauty", "family_photo"}:
        return 3.5, 4.5
    if tag in {
        "first_look", "cdcr_portrait", "vow",
        "family_emotion", "ending",
    }:
        return 5.5, 5.5
    if tag in {"party", "wedding_game", "reception_stage"}:
        return 10.0, 8.0
    return 7.0, 6.5


def analyze_action_window(
    file_path: str,
    center_sec: float,
    sample_span: float,
    frames_count: int,
) -> dict[str, Any]:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return {"ok": False, "reason": "decode_open_failed"}

        times = []
        if frames_count <= 1:
            times = [center_sec]
        else:
            for i in range(frames_count):
                ratio = i / (frames_count - 1)
                times.append(
                    max(0.0, center_sec - sample_span / 2 + ratio * sample_span)
                )

        grays = []
        brightness_values = []
        focus_values = []

        for sec in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue

            height, width = frame.shape[:2]
            if width > 384:
                scale = 384.0 / width
                frame = cv2.resize(
                    frame,
                    (384, max(1, int(height * scale))),
                    interpolation=cv2.INTER_AREA,
                )

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            grays.append(gray)
            brightness_values.append(float(gray.mean()))
            focus_values.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))

        cap.release()

        if len(grays) < 2:
            return {"ok": False, "reason": "not_enough_frames"}

        motions = []
        for previous, current in zip(grays, grays[1:]):
            diff = cv2.absdiff(previous, current)
            motions.append(float(diff.mean()))

        motion_mean = mean(motions)
        motion_std = float(np.std(motions)) if motions else 0.0
        motion_peak = max(motions) if motions else 0.0
        brightness_std = float(np.std(brightness_values))
        focus_median = median(focus_values)

        return {
            "ok": True,
            "motion_mean": round(motion_mean, 4),
            "motion_std": round(motion_std, 4),
            "motion_peak": round(motion_peak, 4),
            "brightness_std": round(brightness_std, 4),
            "focus_median": round(focus_median, 4),
        }
    except Exception as exc:
        return {
            "ok": False,
            "reason": "analysis_exception",
            "details": str(exc),
        }


def action_score(
    analysis: dict[str, Any],
    tag: str,
) -> float:
    if not analysis.get("ok"):
        return 50.0

    target, width = motion_target(tag)
    motion = fnum(analysis.get("motion_mean"), 0)
    motion_std = fnum(analysis.get("motion_std"), 0)
    motion_peak = fnum(analysis.get("motion_peak"), 0)
    brightness_std = fnum(analysis.get("brightness_std"), 0)
    focus = fnum(analysis.get("focus_median"), 0)

    gaussian = math.exp(-((motion - target) ** 2) / max(1.0, 2 * width * width))
    score = gaussian * 68.0

    score += clamp(math.log1p(max(0.0, focus)) / math.log(401), 0, 1) * 20
    score += clamp(1.0 - motion_std / 10.0, 0, 1) * 8

    if motion_peak > 30:
        score -= 22
    elif motion_peak > 20:
        score -= 10

    if brightness_std > 22:
        score -= 18
    elif brightness_std > 12:
        score -= 8

    return clamp(score, 0, 100)


def choose_moment(
    row: dict[str, Any],
    windows: list[dict[str, Any]],
    media_duration: float,
    analyze_action: bool,
    max_candidates: int,
    sample_span: float,
    frames_count: int,
    edge_margin: float,
) -> tuple[float, dict[str, Any], list[dict[str, Any]]]:
    duration = max(0.45, fnum(row.get("duration_sec"), 1.5))
    file_path = str(row.get("file") or "")
    tag = str(row.get("scene_tag") or "other")

    if not windows:
        old_in = fnum(row.get("source_in_sec"), 0)
        center = old_in + duration / 2
        return center, {
            "quality_score": fnum(row.get("quality_window_score"), 45),
            "action_score": 50.0,
            "combined_score": fnum(row.get("quality_window_score"), 45),
            "fallback": True,
        }, []

    ranked = sorted(
        windows,
        key=base_window_score,
        reverse=True,
    )[:max(1, max_candidates)]

    evaluated = []

    for window in ranked:
        center = candidate_center(window)
        score = base_window_score(window)

        if media_duration > 0:
            distance_to_edge = min(center, max(0.0, media_duration - center))
            if distance_to_edge < edge_margin:
                score -= (edge_margin - distance_to_edge) * 18

        analysis = {}
        a_score = 50.0

        if analyze_action and Path(file_path).exists():
            analysis = analyze_action_window(
                file_path,
                center,
                sample_span,
                frames_count,
            )
            a_score = action_score(analysis, tag)

        combined = score * 0.68 + a_score * 0.32

        evaluated.append({
            "center_sec": round(center, 4),
            "quality_score": round(score, 3),
            "action_score": round(a_score, 3),
            "combined_score": round(combined, 3),
            "analysis": analysis,
            "window": window,
        })

    evaluated.sort(
        key=lambda item: fnum(item.get("combined_score"), 0),
        reverse=True,
    )
    best = evaluated[0]
    return fnum(best.get("center_sec"), 0), best, evaluated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="134 Smart Moment Selector V2."
    )
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--analyze-action", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--sample-span", type=float, default=0.9)
    parser.add_argument("--frames-per-candidate", type=int, default=4)
    parser.add_argument("--edge-margin", type=float, default=0.85)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "smart_moment_selector_v2_134")

    input_path, timeline = locate_timeline(project)
    rows = [dict(row) for row in (timeline.get("items") or [])]

    if not input_path or not rows:
        result = {"ok": False, "error": "NO_TIMELINE"}
        write_json(report_dir / "FINAL_134_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    quality_by_path, quality_by_name = load_quality(project)
    camera_map = load_camera_map(project)

    output = []
    changed_count = 0
    decoded_count = 0
    fallback_count = 0

    for index, row in enumerate(rows, 1):
        windows, media_duration = quality_windows_for(
            row,
            quality_by_path,
            quality_by_name,
        )

        center, best, evaluated = choose_moment(
            row,
            windows,
            media_duration,
            args.analyze_action,
            args.max_candidates,
            args.sample_span,
            args.frames_per_candidate,
            args.edge_margin,
        )

        duration = max(0.45, fnum(row.get("duration_sec"), 1.5))
        source_in = center - duration / 2

        if media_duration > 0:
            source_in = clamp(
                source_in,
                0.0,
                max(0.0, media_duration - duration - 0.08),
            )
        else:
            source_in = max(0.0, source_in)

        old_in = fnum(row.get("source_in_sec"), 0)
        if abs(source_in - old_in) >= 0.08:
            changed_count += 1

        if best.get("fallback"):
            fallback_count += 1

        if (best.get("analysis") or {}).get("ok"):
            decoded_count += 1

        metadata = camera_map.get(norm_path(row.get("file")), {})

        row.update({
            "source_in_before_134": round(old_in, 4),
            "source_in_sec": round(source_in, 4),
            "source_out_sec": round(source_in + duration, 4),
            "source_duration_sec": round(duration, 4),
            "selected_center_sec": round(center, 4),
            "moment_quality_score_v2": round(
                fnum(best.get("quality_score"), 45),
                3,
            ),
            "moment_action_score_v2": round(
                fnum(best.get("action_score"), 50),
                3,
            ),
            "moment_combined_score_v2": round(
                fnum(best.get("combined_score"), 45),
                3,
            ),
            "moment_candidate_count": len(evaluated),
            "media_duration_sec": media_duration,
            "camera_group": row.get("camera_group") or metadata.get("camera_group"),
            "shot_scale": row.get("shot_scale") or metadata.get("shot_scale"),
            "module_134_selected": True,
        })
        output.append(row)

        print(
            f"[134] moment {index}/{len(rows)}: "
            f"{row.get('filename')} | "
            f"in={source_in:.2f}s | "
            f"score={fnum(best.get('combined_score'), 0):.1f}"
        )

    result_data = dict(timeline)
    result_data.update({
        "ok": True,
        "module_before_134": timeline.get("module"),
        "module": "134_smart_moment_selector_v2",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "input_timeline": str(input_path),
        "timeline_count": len(output),
        "moment_summary": {
            "changed_source_in_count": changed_count,
            "decoded_action_count": decoded_count,
            "fallback_count": fallback_count,
            "analyze_action": bool(args.analyze_action),
        },
        "items": output,
    })

    output_path = project / "stt_smart_moment_timeline_v2.json"
    write_json(output_path, result_data)
    write_json(report_dir / output_path.name, result_data)

    summary = {
        "ok": True,
        "report_dir": str(report_dir),
        "input_timeline": str(input_path),
        "output_timeline": str(output_path),
        "timeline_count": len(output),
        "changed_source_in_count": changed_count,
        "decoded_action_count": decoded_count,
        "fallback_count": fallback_count,
        "analyze_action": bool(args.analyze_action),
        "fix": "134_smart_moment_selector_v2",
    }
    write_json(report_dir / "FINAL_134_REPORT.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
