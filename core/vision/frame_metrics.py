from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class FrameMetrics:
    sharpness_score: float
    exposure_score: float
    brightness_mean: float
    motion_score: float
    stability_score: float
    beauty_score: float
    ai_keep_score: float
    note: str = ""


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def read_frame_at_second(cap: cv2.VideoCapture, fps: float, second: float):
    frame_index = max(0, int(second * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    if not ok or frame is None:
        return None
    return frame


def resize_for_analysis(frame, max_width: int = 640):
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame

    scale = max_width / float(w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)


def sharpness_from_frame(frame) -> float:
    small = resize_for_analysis(frame)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Convert raw Laplacian variance to a practical 0-100 score.
    # Higher = sharper / less out-of-focus.
    return round(clamp(lap_var / 4.0), 2)


def exposure_from_frame(frame) -> tuple[float, float]:
    small = resize_for_analysis(frame)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    mean = float(np.mean(gray))

    # Ideal middle exposure around 120-135.
    distance = abs(mean - 128.0)
    score = 100.0 - (distance / 128.0 * 100.0)
    return round(clamp(score), 2), round(mean, 2)


def motion_and_stability(frames: list) -> tuple[float, float, str]:
    if len(frames) < 2:
        return 0.0, 50.0, "Not enough frames for motion."

    diffs = []
    flow_stds = []

    prev_gray = None

    for frame in frames:
        small = resize_for_analysis(frame, max_width=480)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            diffs.append(float(np.mean(diff)))

            points = cv2.goodFeaturesToTrack(
                prev_gray,
                maxCorners=120,
                qualityLevel=0.01,
                minDistance=8,
                blockSize=7,
            )

            if points is not None:
                next_points, status, _ = cv2.calcOpticalFlowPyrLK(
                    prev_gray,
                    gray,
                    points,
                    None,
                    winSize=(21, 21),
                    maxLevel=3,
                )

                if next_points is not None and status is not None:
                    good_new = next_points[status.flatten() == 1]
                    good_old = points[status.flatten() == 1]

                    if len(good_new) >= 8:
                        movement = good_new - good_old.reshape(-1, 2)
                        magnitude = np.linalg.norm(movement, axis=1)
                        flow_stds.append(float(np.std(magnitude)))

        prev_gray = gray

    motion_raw = float(np.mean(diffs)) if diffs else 0.0
    motion_score = clamp(motion_raw * 3.0)

    shake_raw = float(np.mean(flow_stds)) if flow_stds else 8.0

    # Higher stability_score = less shaky.
    stability_score = clamp(100.0 - shake_raw * 8.0)

    return round(motion_score, 2), round(stability_score, 2), ""


def analyze_segment_frames(
    video_path: str | Path,
    start_seconds: float,
    end_seconds: float,
) -> FrameMetrics:
    path = Path(video_path)

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {path}")

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps <= 0:
            raise RuntimeError("Invalid FPS.")

        duration = max(0.0, end_seconds - start_seconds)

        if duration <= 0:
            raise RuntimeError("Invalid segment duration.")

        # Sample 3 frames inside the segment.
        if duration < 1.5:
            sample_times = [start_seconds + duration * 0.5]
        else:
            sample_times = [
                start_seconds + duration * 0.25,
                start_seconds + duration * 0.50,
                start_seconds + duration * 0.75,
            ]

        frames = []
        for second in sample_times:
            frame = read_frame_at_second(cap, fps, second)
            if frame is not None:
                frames.append(frame)

        if not frames:
            raise RuntimeError("Cannot read any frame in this segment.")

        sharpness_scores = [sharpness_from_frame(f) for f in frames]
        exposure_pairs = [exposure_from_frame(f) for f in frames]

        sharpness = float(np.mean(sharpness_scores))
        exposure = float(np.mean([p[0] for p in exposure_pairs]))
        brightness = float(np.mean([p[1] for p in exposure_pairs]))

        motion, stability, note = motion_and_stability(frames)

        # Beauty = technically usable image quality.
        beauty = (
            sharpness * 0.40
            + exposure * 0.25
            + stability * 0.25
            + min(motion, 65.0) * 0.10
        )

        # AI keep score = early practical score for rough cut candidate.
        keep = (
            sharpness * 0.45
            + exposure * 0.20
            + stability * 0.25
            + min(motion, 55.0) * 0.10
        )

        return FrameMetrics(
            sharpness_score=round(clamp(beauty if sharpness > 100 else sharpness), 2),
            exposure_score=round(clamp(exposure), 2),
            brightness_mean=round(brightness, 2),
            motion_score=round(clamp(motion), 2),
            stability_score=round(clamp(stability), 2),
            beauty_score=round(clamp(beauty), 2),
            ai_keep_score=round(clamp(keep), 2),
            note=note,
        )
    finally:
        cap.release()
