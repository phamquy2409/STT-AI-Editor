from __future__ import annotations

import csv
import json
import math
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}

def read_json(path: str | Path) -> dict[str, Any]:
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def write_csv(path: str | Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

def outdir(project: Path, name: str) -> Path:
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def open_path(path: str | Path) -> None:
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

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def mean(vals: list[float], default: float = 0.0) -> float:
    return sum(vals) / len(vals) if vals else default

def norm_path(v: Any) -> str:
    return str(v or "").replace("\\", "/").strip().lower()

def media_duration(path: str | Path) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and (r.stdout or "").strip():
            return float((r.stdout or "").strip())
    except Exception:
        pass
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(path))
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            if fps > 0 and frames > 0:
                return float(frames / fps)
    except Exception:
        pass
    return 0.0

def media_creation_time(path: str | Path) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format_tags=creation_time",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        s = (r.stdout or "").strip()
        if r.returncode == 0 and s:
            from datetime import datetime, timezone
            value = s.replace("Z", "+00:00")
            return datetime.fromisoformat(value).timestamp()
    except Exception:
        pass
    try:
        return Path(path).stat().st_mtime
    except Exception:
        return 0.0

def camera_group(name: str, path: str) -> str:
    s = f"{name} {path}".lower()
    if any(x in s for x in ["drone", "dji", "mavic", "flycam", "air2", "air 2", "air3", "mini3", "mini 3", "mini4", "mini 4"]):
        return "DRONE"

    stem = Path(name).stem
    # Keep practical prefixes such as STT and STTA.
    m = re.match(r"([A-Za-z]+)", stem)
    if m:
        prefix = m.group(1).upper()
        if len(prefix) >= 2:
            return prefix

    parent = Path(path).parent.name.strip()
    if parent:
        low = parent.lower()
        if any(x in low for x in ["cam", "camera", "sony", "fx3", "a7", "blackmagic"]):
            return parent.upper()
    return "CAM_UNKNOWN"

def semantic_family(tag: str) -> str:
    tag = str(tag or "other")
    mapping = {
        "decor": "establishing",
        "detail_beauty": "detail",
        "getting_ready": "preparation",
        "first_look": "couple",
        "cdcr_portrait": "couple",
        "ceremony_giatien": "ceremony",
        "church_ceremony": "ceremony",
        "vow": "ceremony",
        "ruoc_dau": "procession",
        "reception_stage": "reception",
        "wedding_game": "reception",
        "family_photo": "family",
        "family_emotion": "family",
        "guest_food": "guest",
        "party": "party",
        "ending": "couple",
        "other": "other",
    }
    return mapping.get(tag, "other")

def current_source_rows(project: Path) -> list[dict[str, Any]]:
    visual = read_json(project / "stt_visual_ai_scene_tags_v1.json")
    rows = list(visual.get("items") or [])
    if rows:
        return rows

    tl = current_timeline(project)
    return list(tl.get("items") or [])

def current_timeline(project: Path) -> dict[str, Any]:
    for name in [
        "stt_multicam_directed_timeline_v1.json",
        "stt_climax_directed_timeline_v1.json",
        "stt_quality_moment_timeline_v1.json",
        "stt_taste_boosted_timeline_v1.json",
        "stt_beat_snapped_beauty_timeline_v1.json",
    ]:
        d = read_json(project / name)
        if d.get("items"):
            return d
    return {}

def load_quality(project: Path):
    d = read_json(project / "stt_shot_quality_windows_v3.json")
    by_path, by_name = {}, defaultdict(list)
    for r in d.get("items") or []:
        p = norm_path(r.get("file"))
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name[n].append(r)
    return by_path, by_name

def load_beauty(project: Path):
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path, by_name = {}, {}
    for r in d.get("items") or []:
        p = norm_path(r.get("file"))
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name.setdefault(n, r)
    return by_path, by_name

def face_scale(path: str | Path, sec: float = 0.0) -> dict[str, Any]:
    try:
        import cv2  # type: ignore
        p = str(path)
        if Path(p).suffix.lower() == ".braw":
            return {"shot_scale": "unknown", "face_count": 0, "face_ratio": 0.0}

        cap = cv2.VideoCapture(p)
        if not cap.isOpened():
            return {"shot_scale": "unknown", "face_count": 0, "face_ratio": 0.0}

        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        if sec <= 0 and fps > 0 and frames > 0:
            sec = (frames / fps) * 0.48
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, sec) * 1000)
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return {"shot_scale": "unknown", "face_count": 0, "face_ratio": 0.0}

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cascade_path = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        detector = cv2.CascadeClassifier(cascade_path)
        faces = detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(30, 30))
        ratios = [(fw * fh) / max(1.0, w * h) for (_, _, fw, fh) in faces]
        max_ratio = max(ratios) if ratios else 0.0

        if max_ratio >= 0.10:
            scale = "close"
        elif max_ratio >= 0.025:
            scale = "medium"
        elif faces:
            scale = "wide"
        else:
            scale = "wide_or_detail"

        return {
            "shot_scale": scale,
            "face_count": int(len(faces)),
            "face_ratio": round(float(max_ratio), 5),
        }
    except Exception:
        return {"shot_scale": "unknown", "face_count": 0, "face_ratio": 0.0}

def duration_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [fnum(x.get("duration_sec"), 0) for x in items if fnum(x.get("duration_sec"), 0) > 0]
    if not vals:
        return {}
    xs = sorted(vals)
    def pct(p: float) -> float:
        return round(xs[int(round((len(xs)-1)*p))], 3)
    return {
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(mean(vals), 3),
        "p10": pct(0.10),
        "p50": pct(0.50),
        "p90": pct(0.90),
        "under_0_7s": sum(1 for v in vals if v < 0.7),
        "over_3s": sum(1 for v in vals if v > 3.0),
        "over_5s": sum(1 for v in vals if v > 5.0),
    }
