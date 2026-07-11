from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
import csv


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


def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def outdir(project: Path) -> Path:
    p = project / "exports" / f"safe_learned_inout_picker_098b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def safe_avg(vals: list[float], default: float = 0.0) -> float:
    vals = [v for v in vals if v is not None]
    if not vals:
        return default
    return round(sum(vals) / len(vals), 3)


def load_profile(project: Path, profile_name: str) -> dict[str, Any]:
    direct = project / "stt_style_profiles_v1" / f"{profile_name}.json"
    if direct.exists():
        return read_json(direct)
    memory = read_json(project / "stt_multi_style_profile_memory_v1.json")
    return (memory.get("profiles") or {}).get(profile_name) or {}


def build_filename_source_map(profile: dict[str, Any]) -> dict[str, float]:
    bucket: dict[str, list[float]] = defaultdict(list)
    for proj in profile.get("projects") or []:
        for ex in proj.get("final_order_examples") or []:
            name = str(ex.get("filename") or "").lower()
            src = fnum(ex.get("source_in_sec"), -1)
            if name and src >= 0:
                bucket[name].append(src)

    # Also support 093 single-profile memory style if present.
    rules = profile.get("rules") or {}
    for ex in rules.get("prefer_final_added_examples") or []:
        name = str(ex.get("filename") or "").lower()
        src = fnum(ex.get("source_in_sec"), -1)
        if name and src >= 0:
            bucket[name].append(src)

    return {k: safe_avg(v, 0) for k, v in bucket.items()}


def fallback_source_in(section: str, index: int) -> float:
    base = {
        "intro": 0.35,
        "story": 0.85,
        "build": 1.25,
        "climax": 1.60,
        "ending": 0.90,
    }.get(section, 0.85)
    jitter = ((index * 1.37) % 4.0) * 0.25
    return round(base + jitter, 3)


def main() -> None:
    p = argparse.ArgumentParser(description="098B safe learned in/out picker.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project)

    rhythm = read_json(project / "stt_profile_rhythm_timeline_v1.json")
    if not rhythm:
        res = {"ok": False, "error": "NO_RHYTHM_TIMELINE", "message": "Run 097 first."}
        write_json(out / "safe_learned_inout_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    profile = load_profile(project, a.style_profile)
    learned_map = build_filename_source_map(profile)

    items = []
    used_exact = 0
    used_safe = 0

    for i, it in enumerate(rhythm.get("items") or [], start=1):
        filename = str(it.get("filename") or "").lower()
        section = str(it.get("target_section") or "story")
        dur = max(0.25, fnum(it.get("duration_sec"), 2.0))

        if filename in learned_map:
            source_in = learned_map[filename]
            reason = "exact_filename_learned_source_in"
            used_exact += 1
        else:
            source_in = fallback_source_in(section, i)
            reason = "safe_fallback_source_in"
            used_safe += 1

        row = dict(it)
        row["index"] = i
        row["source_in_sec"] = round(source_in, 3)
        row["source_duration_sec"] = round(dur, 3)
        row["source_out_sec"] = round(source_in + dur, 3)
        row["inout_reason"] = reason
        items.append(row)

    data = {
        "ok": True,
        "module": "098B_safe_learned_inout_picker",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project),
        "style_profile": a.style_profile,
        "timeline_count": len(items),
        "timeline_seconds": rhythm.get("timeline_seconds"),
        "learned_filename_source_map_count": len(learned_map),
        "used_exact_learned_count": used_exact,
        "used_safe_fallback_count": used_safe,
        "items": items,
    }

    # overwrite same file used by 099/100
    write_json(project / "stt_learned_inout_timeline_v1.json", data)
    write_json(out / "stt_learned_inout_timeline_v1.json", data)
    write_csv(out / "SAFE_LEARNED_INOUT_TIMELINE.csv", items, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec",
        "source_in_sec", "source_out_sec", "inout_reason", "file"
    ])

    res = {
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(items),
        "learned_filename_source_map_count": len(learned_map),
        "used_exact_learned_count": used_exact,
        "used_safe_fallback_count": used_safe,
        "fix": "098B_safe_learned_inout_picker",
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
