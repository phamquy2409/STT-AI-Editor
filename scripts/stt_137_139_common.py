from __future__ import annotations

import json
import math
import os
import re
from collections import Counter, defaultdict
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


def inum(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def norm_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def filename_of(row: dict[str, Any]) -> str:
    return str(
        row.get("filename")
        or Path(str(row.get("file") or "")).name
    )


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


def section_name(row: dict[str, Any]) -> str:
    value = str(
        row.get("music_section")
        or row.get("story_part")
        or row.get("story_chapter")
        or "story"
    ).lower()

    aliases = {
        "pre-climax": "pre_climax",
        "pre climax": "pre_climax",
        "hero": "climax",
        "final": "ending",
    }
    value = aliases.get(value, value)

    for name in [
        "intro", "story", "build", "pre_climax",
        "climax", "release", "ending",
    ]:
        if name in value:
            return name
    return "story"


def source_number(row: dict[str, Any], fallback: int = 0) -> int:
    for key in ["source_order", "_source_order", "scanner_index", "index"]:
        value = inum(row.get(key), -1)
        if value >= 0:
            return value

    name = Path(filename_of(row)).stem
    matches = re.findall(r"(\d+)", name)
    if matches:
        return int(matches[-1])
    return fallback


def timeline_position(row: dict[str, Any], total_seconds: float) -> float:
    start = fnum(row.get("timeline_start_sec"), 0)
    end = fnum(row.get("timeline_end_sec"), start)
    center = (start + end) / 2
    return clamp(center / max(0.001, total_seconds), 0.0, 1.0)


def duration_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted([
        fnum(row.get("duration_sec"), 0)
        for row in rows
        if fnum(row.get("duration_sec"), 0) > 0
    ])
    if not values:
        return {}

    def percentile(p: float) -> float:
        index = int(round((len(values) - 1) * p))
        return round(values[index], 3)

    return {
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "avg": round(sum(values) / len(values), 3),
        "p10": percentile(0.10),
        "p50": percentile(0.50),
        "p90": percentile(0.90),
    }


def locate_final_timeline(project: Path) -> tuple[Path | None, dict[str, Any]]:
    for name in [
        "stt_final_cut_beat_timeline_v2.json",
        "stt_multicam_directed_timeline_v1.json",
        "stt_event_aware_timeline_v2.json",
    ]:
        path = project / name
        data = read_json(path)
        if data.get("items"):
            return path, data
    return None, {}
