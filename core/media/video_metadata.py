from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass
class VideoMetadata:
    filename: str
    filepath: str
    folder: str
    extension: str
    filesize_mb: float
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
    scan_status: str = "ok"
    error_message: str = ""


def read_video_metadata(video_path: str | Path) -> VideoMetadata:
    path = Path(video_path)
    filesize_mb = round(path.stat().st_size / 1024 / 1024, 2)

    width = 0
    height = 0
    fps = 0.0
    frame_count = 0
    duration_seconds = 0.0
    scan_status = "ok"
    error_message = ""

    cap = cv2.VideoCapture(str(path))

    try:
        if not cap.isOpened():
            scan_status = "error"
            error_message = "OpenCV cannot open this video file."
        else:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

            if fps > 0 and frame_count > 0:
                duration_seconds = round(frame_count / fps, 3)
    except Exception as exc:
        scan_status = "error"
        error_message = str(exc)
    finally:
        cap.release()

    return VideoMetadata(
        filename=path.name,
        filepath=str(path.resolve()),
        folder=str(path.parent.resolve()),
        extension=path.suffix.lower(),
        filesize_mb=filesize_mb,
        width=width,
        height=height,
        fps=round(fps, 3),
        frame_count=frame_count,
        duration_seconds=duration_seconds,
        scan_status=scan_status,
        error_message=error_message,
    )
