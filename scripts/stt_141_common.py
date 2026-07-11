from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


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


def outdir(project: Path, name: str) -> Path:
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def norm_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def filename_of(row: dict[str, Any]) -> str:
    return str(row.get("filename") or Path(str(row.get("file") or "")).name)


def camera_of(row: dict[str, Any]) -> str:
    value = str(row.get("camera_group") or "").strip()
    if value:
        return value

    name = filename_of(row).upper()
    if name.startswith("STTA"):
        return "STTA"
    if name.startswith("STT"):
        return "STT"
    return "CAM_UNKNOWN"


def semantic_family(tag: str) -> str:
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
    return mapping.get(str(tag or "other"), "other")


def section_name(row: dict[str, Any]) -> str:
    value = str(
        row.get("music_section")
        or row.get("story_part")
        or row.get("story_chapter")
        or "story"
    ).lower()

    value = {
        "pre-climax": "pre_climax",
        "pre climax": "pre_climax",
        "hero": "climax",
        "final": "ending",
    }.get(value, value)

    for name in [
        "intro", "story", "build", "pre_climax",
        "climax", "release", "ending",
    ]:
        if name in value:
            return name
    return "story"


def quality_score(row: dict[str, Any]) -> float:
    return (
        fnum(
            row.get("moment_combined_score_v2"),
            fnum(row.get("quality_score"), 50),
        ) * 0.48
        + fnum(
            row.get("moment_quality_score_v2"),
            fnum(row.get("quality_score"), 50),
        ) * 0.20
        + fnum(row.get("beauty_score"), 55) * 0.20
        + fnum(row.get("hero_score"), 0) * 0.18
    )


def protected_shot(row: dict[str, Any]) -> bool:
    section = section_name(row)
    tag = str(row.get("scene_tag") or "other")
    duration = fnum(row.get("duration_sec"), 0)
    score = quality_score(row)

    if row.get("is_main_climax_shot"):
        return True
    if row.get("reservation_role"):
        return True
    if row.get("hook_reserved") or row.get("climax_reserved") or row.get("ending_reserved"):
        return True

    if section in {"climax", "ending"} and (
        score >= 78
        or tag in {"vow", "family_emotion", "first_look", "ending"}
        or (row.get("slow_recommended") and duration >= 3.0)
    ):
        return True

    return False


def validate_timeline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gap_count = 0
    overlap_count = 0
    duplicate_count = 0
    seen = set()

    for previous, current in zip(rows, rows[1:]):
        delta = (
            fnum(current.get("timeline_start_sec"), 0)
            - fnum(previous.get("timeline_end_sec"), 0)
        )
        if delta > 0.001:
            gap_count += 1
        elif delta < -0.001:
            overlap_count += 1

    for row in rows:
        key = norm_path(row.get("file"))
        if key and key in seen:
            duplicate_count += 1
        if key:
            seen.add(key)

    return {
        "gap_count": gap_count,
        "overlap_count": overlap_count,
        "duplicate_source_count": duplicate_count,
        "camera_counts": dict(Counter(camera_of(row) for row in rows)),
    }
