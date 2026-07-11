
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


def appdata_dir() -> Path:
    p = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def outdir(project_root: Path, name: str) -> Path:
    p = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_path(path: Path) -> None:
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


def section_for_pos(pos: float) -> str:
    if pos < 0.12:
        return "intro"
    if pos < 0.42:
        return "story"
    if pos < 0.58:
        return "build"
    if pos < 0.82:
        return "climax"
    return "ending"


def load_comparison(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / "stt_ai_vs_final_comparison_v1.json") or read_json(appdata_dir() / "stt_ai_vs_final_comparison_v1.json")


def load_finished_xml(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / "stt_finished_project_xml_v1.json") or read_json(appdata_dir() / "stt_finished_project_xml_v1.json")


def load_story_roles(project_root: Path) -> dict[str, Any]:
    d = read_json(project_root / "stt_wedding_story_roles_v1.json") or read_json(appdata_dir() / "stt_wedding_story_roles_v1.json")
    index = {}
    for item in list(d.get("items") or []):
        key = Path(str(item.get("filename") or item.get("file") or "")).name.lower()
        if key and key not in index:
            index[key] = item
    return index


def safe_avg(vals: list[float], default: float = 0.0) -> float:
    vals = [v for v in vals if v is not None]
    if not vals:
        return default
    return round(sum(vals) / len(vals), 3)


def percentile(vals: list[float], p: float, default: float = 0.0) -> float:
    vals = sorted([float(v) for v in vals])
    if not vals:
        return default
    k = int(round((len(vals) - 1) * p))
    return round(vals[max(0, min(k, len(vals)-1))], 3)


def summarize_final_order(final_order: list[dict[str, Any]], story_index: dict[str, Any]) -> dict[str, Any]:
    section_count = Counter()
    section_durs: dict[str, list[float]] = defaultdict(list)
    ext_count = Counter()
    chapter_count = Counter()
    selected_files = Counter()

    total_duration = 0.0
    for c in final_order:
        sec = str(c.get("learned_section") or section_for_pos(fnum(c.get("timeline_pos"), 0)))
        dur = fnum(c.get("timeline_duration_sec"), 0)
        filename = Path(str(c.get("filename") or "")).name
        ext = Path(filename).suffix.lower() or "no_ext"
        selected_files[filename] += 1
        ext_count[ext] += 1
        section_count[sec] += 1
        section_durs[sec].append(dur)
        total_duration += dur

        role = story_index.get(filename.lower())
        if role:
            chapter = str(role.get("story_chapter") or "unknown")
            chapter_count[chapter] += 1

    total_clips = max(1, len(final_order))
    section_ratios = {k: round(v / total_clips, 4) for k, v in section_count.items()}

    section_rules = {}
    for sec in ["intro", "story", "build", "climax", "ending"]:
        vals = section_durs.get(sec, [])
        section_rules[sec] = {
            "clip_count": section_count.get(sec, 0),
            "clip_ratio": section_ratios.get(sec, 0.0),
            "avg_duration_sec": safe_avg(vals, 0),
            "p25_duration_sec": percentile(vals, 0.25, 0),
            "p50_duration_sec": percentile(vals, 0.50, 0),
            "p75_duration_sec": percentile(vals, 0.75, 0),
        }

    return {
        "final_clip_count": len(final_order),
        "final_total_duration_sec": round(total_duration, 3),
        "final_avg_clip_duration_sec": round(total_duration / total_clips, 3),
        "section_ratios": section_ratios,
        "section_rules": section_rules,
        "extension_counts": dict(ext_count),
        "chapter_counts": dict(chapter_count),
        "most_used_filenames": [{"filename": k, "uses": v} for k, v in selected_files.most_common(50)],
    }


def summarize_user_changes(comparison: dict[str, Any]) -> dict[str, Any]:
    added = list(comparison.get("user_added_clips") or [])
    removed = list(comparison.get("user_removed_ai_clips") or [])
    common = list(comparison.get("common_clip_comparisons") or [])

    added_sections = Counter(str(x.get("learned_section") or "unknown") for x in added)
    removed_sections = Counter(str(x.get("learned_section") or "unknown") for x in removed)
    adjusted = [x for x in common if str(x.get("learn_action")) == "kept_but_adjusted"]

    duration_delta_vals = [fnum(x.get("duration_delta_sec"), 0) for x in common]
    source_in_delta_vals = [fnum(x.get("source_in_delta_sec"), 0) for x in common]
    order_delta_vals = [abs(fnum(x.get("order_delta"), 0)) for x in common]

    return {
        "ai_clip_count": comparison.get("ai_clip_count"),
        "final_clip_count": comparison.get("final_clip_count"),
        "common_file_count": comparison.get("common_file_count"),
        "user_added_file_count": comparison.get("user_added_file_count"),
        "user_removed_file_count": comparison.get("user_removed_file_count"),
        "added_section_counts": dict(added_sections),
        "removed_section_counts": dict(removed_sections),
        "adjusted_common_clip_count": len(adjusted),
        "avg_duration_delta_sec": safe_avg(duration_delta_vals, 0),
        "avg_abs_order_delta": safe_avg(order_delta_vals, 0),
        "avg_source_in_delta_sec": safe_avg(source_in_delta_vals, 0),
        "top_user_added_files": [
            {
                "filename": x.get("filename"),
                "section": x.get("learned_section"),
                "duration_sec": x.get("timeline_duration_sec"),
                "source_in_sec": x.get("source_in_sec"),
                "file": x.get("file"),
            }
            for x in added[:80]
        ],
        "top_user_removed_ai_files": [
            {
                "filename": x.get("filename"),
                "section": x.get("learned_section"),
                "duration_sec": x.get("timeline_duration_sec"),
                "file": x.get("file"),
            }
            for x in removed[:80]
        ],
    }


def infer_profile_type(final_clip_count: int, duration_sec: float) -> str:
    if duration_sec <= 75:
        return "reel_60s"
    if duration_sec <= 360:
        return "highlight_3_5_min"
    if final_clip_count >= 250 or duration_sec > 600:
        return "full_documentary"
    return "wedding_documentary"


def create_editing_style_memory_builder(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    profile_name: str = "user_wedding_style",
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "editing_style_memory_builder_093")

    comparison = load_comparison(project_root)
    finished = load_finished_xml(project_root)
    story_index = load_story_roles(project_root)

    if not comparison:
        res = {"ok": False, "error": "NO_COMPARISON_DATA", "message": "Run 092 first."}
        write_json(out / "style_memory_error.json", res)
        if open_folder:
            open_path(out)
        return res

    final_order = list(comparison.get("final_order") or [])
    if not final_order:
        final_order = list(finished.get("clips") or [])

    final_summary = summarize_final_order(final_order, story_index)
    change_summary = summarize_user_changes(comparison)
    profile_type = infer_profile_type(final_summary["final_clip_count"], final_summary["final_total_duration_sec"])

    memory = {
        "ok": True,
        "module": "093_editing_style_memory_builder",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "profile_name": profile_name,
        "profile_type_inferred": profile_type,
        "project_root": str(project_root),
        "source_folder": comparison.get("source_folder"),
        "ai_xml": comparison.get("ai_xml"),
        "final_xml": comparison.get("final_xml"),
        "learning_strength": {
            "project_count": 1,
            "confidence": "starter",
            "note": "One finished XML is enough to start learning tempo/source choices, but 5-10 XMLs are needed for a stable personal style.",
        },
        "final_style_summary": final_summary,
        "user_change_summary": change_summary,
        "rules": {
            "target_clip_count_hint": final_summary["final_clip_count"],
            "avg_clip_duration_hint_sec": final_summary["final_avg_clip_duration_sec"],
            "section_rules": final_summary["section_rules"],
            "section_ratios": final_summary["section_ratios"],
            "prefer_final_added_examples": change_summary["top_user_added_files"],
            "avoid_removed_ai_examples": change_summary["top_user_removed_ai_files"],
            "story_chapter_counts": final_summary["chapter_counts"],
        },
    }

    write_json(project_root / "stt_user_editing_style_memory_v1.json", memory)
    write_json(appdata_dir() / "stt_user_editing_style_memory_v1.json", memory)
    write_json(out / "stt_user_editing_style_memory_v1.json", memory)

    # Small readable CSVs
    section_rows = []
    for sec, rule in memory["rules"]["section_rules"].items():
        row = {"section": sec, **rule}
        section_rows.append(row)
    write_csv(out / "STYLE_SECTION_RULES.csv", section_rows, [
        "section", "clip_count", "clip_ratio", "avg_duration_sec", "p25_duration_sec", "p50_duration_sec", "p75_duration_sec",
    ])

    added_rows = change_summary["top_user_added_files"]
    removed_rows = change_summary["top_user_removed_ai_files"]
    write_csv(out / "STYLE_PREFER_ADDED_EXAMPLES.csv", added_rows, ["filename", "section", "duration_sec", "source_in_sec", "file"])
    write_csv(out / "STYLE_AVOID_REMOVED_AI_EXAMPLES.csv", removed_rows, ["filename", "section", "duration_sec", "file"])

    summary_rows = [
        {"key": "profile_type_inferred", "value": profile_type},
        {"key": "final_clip_count", "value": final_summary["final_clip_count"]},
        {"key": "final_total_duration_sec", "value": final_summary["final_total_duration_sec"]},
        {"key": "final_avg_clip_duration_sec", "value": final_summary["final_avg_clip_duration_sec"]},
        {"key": "common_file_count", "value": change_summary.get("common_file_count")},
        {"key": "user_added_file_count", "value": change_summary.get("user_added_file_count")},
        {"key": "user_removed_file_count", "value": change_summary.get("user_removed_file_count")},
        {"key": "section_ratios", "value": json.dumps(final_summary["section_ratios"], ensure_ascii=False)},
        {"key": "chapter_counts", "value": json.dumps(final_summary["chapter_counts"], ensure_ascii=False)},
    ]
    write_csv(out / "STYLE_MEMORY_SUMMARY.csv", summary_rows, ["key", "value"])

    html = make_html(
        "093 Editing Style Memory Builder",
        section_rows,
        ["section", "clip_count", "clip_ratio", "avg_duration_sec", "p25_duration_sec", "p50_duration_sec", "p75_duration_sec"],
        f"profile={profile_name} | inferred={profile_type}",
    )
    (out / "STYLE_MEMORY_REPORT.html").write_text(html, encoding="utf-8")

    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "profile_name": profile_name,
        "profile_type_inferred": profile_type,
        "final_clip_count": final_summary["final_clip_count"],
        "final_total_duration_sec": final_summary["final_total_duration_sec"],
        "final_avg_clip_duration_sec": final_summary["final_avg_clip_duration_sec"],
        "section_ratios": final_summary["section_ratios"],
        "user_added_file_count": change_summary.get("user_added_file_count"),
        "user_removed_file_count": change_summary.get("user_removed_file_count"),
        "memory_file": str(project_root / "stt_user_editing_style_memory_v1.json"),
        "fix": "093_editing_style_memory_builder",
    }


def make_html(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    import html
    th = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    tr = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>"
        for r in rows
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Arial;background:#111;color:#eee;margin:32px}"
        ".card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}</style></head>"
        f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{th}</tr>{tr}</table></div></body></html>"
    )
