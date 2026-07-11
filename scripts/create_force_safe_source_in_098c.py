from __future__ import annotations

import argparse
import csv
import json
import os
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


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def outdir(project: Path) -> Path:
    p = project / "exports" / f"force_safe_source_in_098c_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_source_in(section: str, index: int) -> float:
    # Very conservative. Avoids Premiere striped/error regions from out-of-range source in.
    base = {
        "intro": 0.10,
        "story": 0.25,
        "build": 0.35,
        "climax": 0.45,
        "ending": 0.25,
    }.get(section, 0.25)
    jitter = ((index * 0.37) % 1.0) * 0.35
    return round(base + jitter, 3)


def main() -> None:
    p = argparse.ArgumentParser(description="098C force safe source-in to avoid Premiere striped clips.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project)

    rhythm = read_json(project / "stt_profile_rhythm_timeline_v1.json")
    if not rhythm:
        res = {
            "ok": False,
            "error": "NO_RHYTHM_TIMELINE",
            "message": "Run 097 first.",
        }
        write_json(out / "force_safe_source_in_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    items = []
    for i, it in enumerate(rhythm.get("items") or [], start=1):
        section = str(it.get("target_section") or "story")
        dur = max(0.25, fnum(it.get("duration_sec"), 2.0))
        source_in = safe_source_in(section, i)

        row = dict(it)
        row["index"] = i
        row["source_in_sec"] = source_in
        row["source_duration_sec"] = round(dur, 3)
        row["source_out_sec"] = round(source_in + dur, 3)
        row["inout_reason"] = "098C_force_safe_source_in"
        items.append(row)

    data = {
        "ok": True,
        "module": "098C_force_safe_source_in",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project),
        "style_profile": a.style_profile,
        "timeline_count": len(items),
        "timeline_seconds": rhythm.get("timeline_seconds"),
        "items": items,
    }

    # overwrite file used by 099/100
    write_json(project / "stt_learned_inout_timeline_v1.json", data)
    write_json(out / "stt_learned_inout_timeline_v1.json", data)
    write_csv(out / "FORCE_SAFE_SOURCE_IN_TIMELINE.csv", items, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec",
        "source_in_sec", "source_out_sec", "inout_reason", "file"
    ])

    res = {
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(items),
        "timeline_seconds": rhythm.get("timeline_seconds"),
        "max_source_in_sec": max([fnum(x.get("source_in_sec"), 0) for x in items] or [0]),
        "fix": "098C_force_safe_source_in",
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
