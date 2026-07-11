from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_134_136_common import *


KNOWN_BAD_DEFAULT = {
    "stt0043.mp4",
    "stt0008.mp4",
}


def get_json_duration(row: dict[str, Any]) -> float:
    return fnum(
        row.get("media_duration_sec"),
        fnum(
            row.get("source_media_duration_sec"),
            fnum(row.get("validated_media_duration_sec"), 0),
        ),
    )


def camera_of(row: dict[str, Any]) -> str:
    return str(row.get("camera_group") or "CAM_UNKNOWN")


def filename_of(row: dict[str, Any]) -> str:
    return str(
        row.get("filename")
        or Path(str(row.get("file") or "")).name
    )


def resolve_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found

    env_value = os.environ.get("FFMPEG_BINARY", "").strip()
    if env_value and Path(env_value).exists():
        return env_value

    try:
        import imageio_ffmpeg  # type: ignore
        candidate = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if candidate.exists():
            return str(candidate)
    except Exception:
        pass

    here = Path(__file__).resolve()
    root = here.parent.parent

    candidates = [
        root / "ffmpeg.exe",
        root / "tools" / "ffmpeg.exe",
        root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe",
        root / ".venv" / "Scripts" / "ffmpeg.exe",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    for directory in [
        root / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries",
        Path(sys.executable).resolve().parent.parent
        / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries",
    ]:
        if directory.exists():
            matches = sorted(directory.glob("ffmpeg-*.exe"))
            if matches:
                return str(matches[0])

    local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
    winget = local_appdata / "Microsoft" / "WinGet" / "Packages"
    if winget.exists():
        matches = list(winget.glob("**/ffmpeg.exe"))
        if matches:
            return str(matches[0])

    raise FileNotFoundError(
        "FFmpeg not found. Run: python -m pip install imageio-ffmpeg"
    )


def open_capture(path: str):
    try:
        import cv2  # type: ignore
        capture = cv2.VideoCapture(path)
        return cv2, capture
    except Exception:
        return None, None


def probe_with_cv2(path: str) -> dict[str, Any]:
    cv2, capture = open_capture(path)
    if cv2 is None or capture is None or not capture.isOpened():
        return {
            "ok": False,
            "duration_sec": 0.0,
            "fps": 0.0,
            "frame_count": 0,
        }

    fps = fnum(capture.get(cv2.CAP_PROP_FPS), 0)
    frame_count = inum(capture.get(cv2.CAP_PROP_FRAME_COUNT), 0)
    duration = frame_count / fps if fps > 0 and frame_count > 0 else 0.0
    capture.release()

    return {
        "ok": fps > 0 and frame_count > 0,
        "duration_sec": duration,
        "fps": fps,
        "frame_count": frame_count,
    }


def conservative_duration(
    row: dict[str, Any],
    probe: dict[str, Any],
) -> float:
    values = [
        value
        for value in [
            get_json_duration(row),
            fnum(probe.get("duration_sec"), 0),
        ]
        if value > 0
    ]
    return min(values) if values else 0.0


def validate_decode_window(
    file_path: str,
    source_in: float,
    duration: float,
    sample_count: int,
) -> dict[str, Any]:
    cv2, capture = open_capture(file_path)

    if cv2 is None or capture is None or not capture.isOpened():
        return {
            "ok": False,
            "decoded_count": 0,
            "requested_count": sample_count,
            "failed_samples": [],
            "reason": "capture_open_failed",
        }

    sample_count = max(3, sample_count)
    sample_times = []

    if duration <= 0.08:
        sample_times = [source_in]
    else:
        left = source_in + min(0.06, duration * 0.10)
        right = source_in + max(0.01, duration - min(0.10, duration * 0.12))

        for index in range(sample_count):
            ratio = index / max(1, sample_count - 1)
            sample_times.append(left + (right - left) * ratio)

    decoded = 0
    failed_samples = []
    suspicious_samples = []

    for sec in sample_times:
        capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, sec) * 1000.0)
        ok, frame = capture.read()

        if not ok or frame is None or getattr(frame, "size", 0) <= 0:
            failed_samples.append(round(sec, 4))
            continue

        decoded += 1

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_value = float(gray.mean())
            variance = float(gray.var())

            if mean_value < 0.15 and variance < 0.15:
                suspicious_samples.append(round(sec, 4))
        except Exception:
            pass

    capture.release()

    required = max(2, sample_count - 1)
    valid = decoded >= required and not failed_samples

    return {
        "ok": valid,
        "decoded_count": decoded,
        "requested_count": sample_count,
        "failed_samples": failed_samples,
        "suspicious_samples": suspicious_samples,
        "reason": "ok" if valid else "decode_sample_failed",
    }


def choose_safe_window(
    row: dict[str, Any],
    safety_sec: float,
    sample_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = dict(row)
    file_path = str(row.get("file") or "")
    duration = max(0.25, fnum(row.get("duration_sec"), 0))

    probe = probe_with_cv2(file_path)
    total = conservative_duration(row, probe)

    old_in = max(0.0, fnum(row.get("source_in_sec"), 0))
    old_out = fnum(row.get("source_out_sec"), old_in + duration)

    if total <= 0:
        validation = validate_decode_window(
            file_path,
            old_in,
            duration,
            sample_count,
        )
        return result, {
            "ok": validation.get("ok", False),
            "shifted": False,
            "probe": probe,
            "validation": validation,
            "total_duration": total,
            "reason": "unknown_duration",
        }

    margin = max(0.20, safety_sec)
    usable_start = min(margin, max(0.0, total * 0.12))
    usable_end = max(usable_start, total - margin)
    max_in = max(usable_start, usable_end - duration)

    candidate_centers = [
        old_in + duration / 2,
        fnum(row.get("selected_center_sec"), old_in + duration / 2),
        total * 0.40,
        total * 0.50,
        total * 0.60,
    ]

    tried = []
    seen = set()

    for center in candidate_centers:
        source_in = clamp(
            center - duration / 2,
            usable_start,
            max_in,
        )
        key = round(source_in, 3)

        if key in seen:
            continue
        seen.add(key)

        validation = validate_decode_window(
            file_path,
            source_in,
            duration,
            sample_count,
        )
        tried.append({
            "source_in": round(source_in, 4),
            "validation": validation,
        })

        if validation.get("ok"):
            result["source_in_sec"] = round(source_in, 6)
            result["source_out_sec"] = round(source_in + duration, 6)
            result["source_duration_sec"] = round(duration, 6)
            result["media_duration_sec"] = round(total, 6)
            result["source_media_duration_sec"] = round(total, 6)
            result["decode_validated_136d"] = True

            shifted = (
                abs(source_in - old_in) > 0.02
                or old_out > usable_end + 0.001
            )

            return result, {
                "ok": True,
                "shifted": shifted,
                "probe": probe,
                "validation": validation,
                "total_duration": total,
                "usable_start": usable_start,
                "usable_end": usable_end,
                "tried": tried,
                "reason": "validated",
            }

    return result, {
        "ok": False,
        "shifted": False,
        "probe": probe,
        "total_duration": total,
        "usable_start": usable_start,
        "usable_end": usable_end,
        "tried": tried,
        "reason": "no_decodable_window",
    }


def candidate_score(
    candidate: dict[str, Any],
    target: dict[str, Any],
) -> float:
    target_tag = str(target.get("scene_tag") or "other")
    target_family = semantic_family(target_tag)
    target_camera = camera_of(target)

    tag = str(candidate.get("scene_tag") or "other")
    family = semantic_family(tag)
    camera = camera_of(candidate)

    score = (
        fnum(candidate.get("quality_score"), 45) * 0.52
        + fnum(candidate.get("beauty_score"), 55) * 0.34
    )

    if tag == target_tag:
        score += 34
    elif family == target_family:
        score += 18
    else:
        score -= 36

    if camera != target_camera:
        score += 8

    if candidate.get("is_drone") and section_name(target) not in {
        "intro", "release", "ending"
    }:
        score -= 40

    return score


def build_candidate_pool(
    project: Path,
    used_paths: set[str],
    excluded_names: set[str],
) -> list[dict[str, Any]]:
    camera_map = read_json(project / "stt_camera_source_map_v1.json")
    candidates = []

    for row in camera_map.get("items") or []:
        path_key = norm_path(row.get("file"))
        name_key = filename_of(row).lower()

        if not path_key or path_key in used_paths:
            continue
        if name_key in excluded_names:
            continue
        if not Path(str(row.get("file") or "")).exists():
            continue

        candidates.append(dict(row))

    return candidates


def replacement_row(
    candidate: dict[str, Any],
    target: dict[str, Any],
    validated_candidate: dict[str, Any],
) -> dict[str, Any]:
    row = dict(target)
    duration = fnum(target.get("duration_sec"), 0)

    row.update({
        "bad_source_original_file_136d": target.get("file"),
        "bad_source_original_filename_136d": filename_of(target),
        "bad_source_replaced_136d": True,
        "file": candidate.get("file"),
        "filename": candidate.get("filename"),
        "scene_tag": candidate.get("scene_tag", target.get("scene_tag")),
        "camera_group": candidate.get(
            "camera_group",
            target.get("camera_group"),
        ),
        "shot_scale": candidate.get("shot_scale", target.get("shot_scale")),
        "source_in_sec": validated_candidate.get("source_in_sec"),
        "source_out_sec": validated_candidate.get("source_out_sec"),
        "source_duration_sec": round(duration, 6),
        "media_duration_sec": validated_candidate.get("media_duration_sec"),
        "source_media_duration_sec": validated_candidate.get(
            "source_media_duration_sec"
        ),
        "decode_validated_136d": True,
    })
    return row


def resolve_and_validate_timeline(
    project: Path,
    rows: list[dict[str, Any]],
    safety_sec: float,
    sample_count: int,
    excluded_names: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    used_paths = {
        norm_path(row.get("file"))
        for row in rows
        if norm_path(row.get("file"))
    }
    candidate_pool = build_candidate_pool(
        project,
        used_paths,
        excluded_names,
    )

    output = []
    shifted_count = 0
    replaced_count = 0
    bad_detected = 0
    unresolved = []
    changes = []

    for index, original in enumerate(rows, 1):
        row = dict(original)
        name_key = filename_of(row).lower()

        if name_key in excluded_names:
            validation_info = {
                "ok": False,
                "reason": "known_bad_filename",
            }
            safe_row = row
        else:
            safe_row, validation_info = choose_safe_window(
                row,
                safety_sec,
                sample_count,
            )

        if validation_info.get("ok"):
            if validation_info.get("shifted"):
                shifted_count += 1
                changes.append({
                    "index": index,
                    "filename": filename_of(row),
                    "action": "shifted_inward",
                    "old_in": row.get("source_in_sec"),
                    "new_in": safe_row.get("source_in_sec"),
                })
            output.append(safe_row)
            print(
                f"[136D] {index}/{len(rows)} OK: "
                f"{filename_of(row)}"
            )
            continue

        bad_detected += 1
        target_duration = fnum(row.get("duration_sec"), 0)
        ranked = sorted(
            candidate_pool,
            key=lambda candidate: candidate_score(candidate, row),
            reverse=True,
        )

        replacement = None
        replacement_validation = None
        replacement_index = None

        for candidate_index, candidate in enumerate(ranked[:80]):
            candidate_copy = dict(candidate)
            candidate_copy.update({
                "duration_sec": target_duration,
                "source_in_sec": fnum(
                    candidate.get("best_source_in_sec"),
                    0,
                ),
                "source_out_sec": fnum(
                    candidate.get("best_source_in_sec"),
                    0,
                ) + target_duration,
                "selected_center_sec": fnum(
                    candidate.get("best_source_in_sec"),
                    0,
                ) + target_duration / 2,
            })

            validated, info = choose_safe_window(
                candidate_copy,
                safety_sec,
                sample_count,
            )

            if info.get("ok"):
                replacement = candidate
                replacement_validation = validated
                replacement_index = candidate_index
                break

        if replacement is None or replacement_validation is None:
            unresolved.append({
                "index": index,
                "filename": filename_of(row),
                "file": row.get("file"),
                "reason": validation_info.get("reason"),
            })
            output.append(row)
            print(
                f"[136D] {index}/{len(rows)} UNRESOLVED: "
                f"{filename_of(row)}"
            )
            continue

        new_row = replacement_row(
            replacement,
            row,
            replacement_validation,
        )
        output.append(new_row)
        replaced_count += 1

        replacement_path = norm_path(replacement.get("file"))
        used_paths.add(replacement_path)
        candidate_pool = [
            candidate
            for candidate in candidate_pool
            if norm_path(candidate.get("file")) != replacement_path
        ]

        changes.append({
            "index": index,
            "filename": filename_of(row),
            "action": "replaced_bad_source",
            "replacement_filename": filename_of(replacement),
            "replacement_file": replacement.get("file"),
            "reason": validation_info.get("reason"),
        })

        print(
            f"[136D] {index}/{len(rows)} REPLACED: "
            f"{filename_of(row)} -> {filename_of(replacement)}"
        )

    return output, {
        "validated_count": len(rows) - bad_detected,
        "shifted_inward_count": shifted_count,
        "bad_detected_count": bad_detected,
        "replaced_count": replaced_count,
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
        "changes": changes,
    }


def validate_final(
    rows: list[dict[str, Any]],
    safety_sec: float,
) -> dict[str, Any]:
    overflow = 0
    gap = 0
    overlap = 0

    for previous, current in zip(rows, rows[1:]):
        delta = (
            fnum(current.get("timeline_start_sec"), 0)
            - fnum(previous.get("timeline_end_sec"), 0)
        )
        if delta > 0.001:
            gap += 1
        elif delta < -0.001:
            overlap += 1

    for row in rows:
        total = get_json_duration(row)
        if total > 0:
            effective_end = total - max(0.20, safety_sec)
            if fnum(row.get("source_out_sec"), 0) > effective_end + 0.001:
                overflow += 1

    return {
        "gap_count": gap,
        "overlap_count": overlap,
        "source_overflow_count": overflow,
        "camera_counts": dict(Counter(
            camera_of(row) for row in rows
        )),
    }


def run_128d(
    project: Path,
    sequence_fps: float,
    source_fps: float,
    safety_frames: int,
) -> dict[str, Any]:
    scripts = Path(__file__).resolve().parent
    exporter = scripts / "export_premiere_mixedrate_repair_128d.py"

    command = [
        sys.executable,
        str(exporter),
        "--project", str(project),
        "--preset", "horizontal_4k",
        "--sequence-fps", str(sequence_fps),
        "--default-source-fps", str(source_fps),
        "--source-safety-frames", str(safety_frames),
        "--no-open",
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        command,
        cwd=str(scripts.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def locate_music(project: Path, music_root: str) -> Path | None:
    music_map = read_json(project / "stt_music_structure_climax_v3.json")
    remembered = str(music_map.get("music_file") or "").strip()

    if remembered and Path(remembered).exists():
        return Path(remembered)

    root = Path(music_root)
    if not root.exists():
        return None

    candidates = sorted([
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {
            ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"
        }
    ])

    enemy = [
        path
        for path in candidates
        if "enemy of truth" in path.stem.lower()
    ]
    if enemy:
        return enemy[0]

    return candidates[0] if len(candidates) == 1 else None


def convert_music_to_wav(
    project: Path,
    music_root: str,
) -> tuple[bool, str, str]:
    music = locate_music(project, music_root)
    if music is None:
        return False, "", "music_not_resolved"

    ffmpeg = resolve_ffmpeg()
    output = project / "stt_128h_music_STEREO_48K.wav"

    result = subprocess.run(
        [
            ffmpeg,
            "-v", "error",
            "-y",
            "-i", str(music),
            "-vn",
            "-ac", "2",
            "-ar", "48000",
            "-c:a", "pcm_s16le",
            str(output),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )

    return (
        result.returncode == 0 and output.exists(),
        str(output),
        result.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="136D validate exact decode windows and replace bad source."
    )
    parser.add_argument(
        "--project",
        default="D:/STT Projects/Wedding_Test_001",
    )
    parser.add_argument(
        "--source-safety-sec",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=6,
    )
    parser.add_argument(
        "--music-root",
        default="D:/27thang6pschh",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--sequence-fps",
        type=float,
        default=30.0,
    )
    parser.add_argument(
        "--default-source-fps",
        type=float,
        default=50.0,
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
    )
    args = parser.parse_args()

    project = Path(args.project)
    report_dir = outdir(project, "decode_validator_136d")

    source_path = project / "stt_final_cut_beat_timeline_v2.json"
    data = read_json(source_path)
    rows = [dict(row) for row in (data.get("items") or [])]

    if not rows:
        result = {
            "ok": False,
            "error": "NO_FINAL_TIMELINE",
            "expected": str(source_path),
        }
        write_json(report_dir / "FINAL_136D_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return

    excluded_names = set(KNOWN_BAD_DEFAULT)
    excluded_names.update(
        Path(str(value)).name.lower()
        for value in args.exclude
        if str(value).strip()
    )

    validated_rows, scan_summary = resolve_and_validate_timeline(
        project,
        rows,
        max(0.25, args.source_safety_sec),
        max(3, args.sample_count),
        excluded_names,
    )

    validation = validate_final(
        validated_rows,
        max(0.25, args.source_safety_sec),
    )

    output_data = dict(data)
    output_data.update({
        "module_before_136d": data.get("module"),
        "module": "136d_decode_validator",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "timeline_count": len(validated_rows),
        "timeline_seconds": max(
            [
                fnum(row.get("timeline_end_sec"), 0)
                for row in validated_rows
            ] + [0]
        ),
        "decode_summary": scan_summary,
        "validation_summary": validation,
        "items": validated_rows,
    })

    canonical = project / "stt_multicam_directed_timeline_v1.json"
    backup = project / "stt_final_cut_before_136d_backup.json"

    if not backup.exists():
        shutil.copy2(source_path, backup)

    write_json(source_path, output_data)
    write_json(canonical, output_data)
    write_json(report_dir / source_path.name, output_data)
    write_json(
        report_dir / "DECODE_CHANGES_136D.json",
        {"items": scan_summary.get("changes") or []},
    )

    build_128d = None
    video_only = project / "stt_128h_VIDEO_ONLY_FINAL.xml"

    if scan_summary["unresolved_count"] == 0:
        build_128d = run_128d(
            project,
            args.sequence_fps,
            args.default_source_fps,
            safety_frames=max(
                10,
                int(round(args.source_safety_sec * args.default_source_fps)),
            ),
        )

        generated = project / "stt_128d_VIDEO_ONLY_SAFE.xml"
        if build_128d.get("ok") and generated.exists():
            shutil.copy2(generated, video_only)
            shutil.copy2(video_only, report_dir / video_only.name)

    music_ok, stereo_wav, music_error = convert_music_to_wav(
        project,
        args.music_root,
    )

    result = {
        "ok": (
            scan_summary["unresolved_count"] == 0
            and bool(build_128d and build_128d.get("ok"))
            and music_ok
        ),
        "report_dir": str(report_dir),
        "output_timeline": str(source_path),
        "canonical_timeline": str(canonical),
        "backup_timeline": str(backup),
        "timeline_count": len(validated_rows),
        "validated_count": scan_summary["validated_count"],
        "shifted_inward_count": scan_summary["shifted_inward_count"],
        "bad_detected_count": scan_summary["bad_detected_count"],
        "replaced_count": scan_summary["replaced_count"],
        "unresolved_count": scan_summary["unresolved_count"],
        "source_overflow_count": validation["source_overflow_count"],
        "gap_count": validation["gap_count"],
        "overlap_count": validation["overlap_count"],
        "build_128d": build_128d,
        "video_only_xml": str(video_only),
        "music_ok": music_ok,
        "stereo_wav": stereo_wav,
        "music_error": music_error,
        "fix": "136d_decode_validator",
    }

    write_json(report_dir / "FINAL_136D_REPORT.json", result)
    print(json.dumps(result, ensure_ascii=True, indent=2))

    if not args.no_open:
        open_path(report_dir)


if __name__ == "__main__":
    main()
