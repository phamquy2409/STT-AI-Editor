from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
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


def run_step(label: str, cmd: list[str], cwd: Path, report: list[dict[str, Any]]) -> bool:
    print("\n" + "=" * 80)
    print(f"[122] {label}")
    print(" ".join([f'"{x}"' if " " in str(x) else str(x) for x in cmd]))
    print("=" * 80, flush=True)

    start = datetime.now()
    p = subprocess.run(cmd, cwd=str(cwd), text=True)
    sec = (datetime.now() - start).total_seconds()

    item = {
        "label": label,
        "cmd": cmd,
        "returncode": p.returncode,
        "seconds": round(sec, 2),
        "ok": p.returncode == 0,
    }
    report.append(item)

    if p.returncode != 0:
        print(f"[122] FAILED: {label} returncode={p.returncode}", flush=True)
        return False
    return True


def has_fresh_tags(project: Path) -> bool:
    p = project / "stt_visual_ai_scene_tags_v1.json"
    d = read_json(p)
    return bool(d.get("ok") and d.get("items"))


def summary_from_project(project: Path) -> dict[str, Any]:
    visual = read_json(project / "stt_visual_ai_scene_tags_v1.json")
    timeline = read_json(project / "stt_beat_snapped_beauty_timeline_v1.json")
    xmlj = read_json(project / "stt_beat_snapped_beauty_xml_v1.json")
    return {
        "visual_module": visual.get("module"),
        "visual_file_count": visual.get("file_count"),
        "visual_scene_counts": visual.get("scene_counts"),
        "timeline_module": timeline.get("module"),
        "timeline_count": timeline.get("timeline_count"),
        "timeline_seconds": timeline.get("timeline_seconds"),
        "timeline_scene_counts": timeline.get("scene_counts"),
        "duration_stats": timeline.get("duration_stats"),
        "xml_output": str(project / "stt_beat_snapped_beauty_premiere_import.xml"),
        "xml_timeline_count": xmlj.get("timeline_count"),
        "xml_timeline_seconds": xmlj.get("timeline_seconds"),
        "xml_gap_count": xmlj.get("gap_count"),
        "xml_unknown_duration_count": xmlj.get("unknown_duration_count"),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="122 Wedding AI Export V1 controller: source + style + music prep -> Premiere XML.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--style-profile", default="single_song_report_3_4min")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--target-shots", type=int, default=220)
    p.add_argument("--frame-samples", type=int, default=7)
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--recognizer", default="119h", choices=["119h", "119g", "119e", "skip"])
    p.add_argument("--planner", default="120e", choices=["120e", "120d", "120c"])
    p.add_argument("--review", action="store_true", help="also create contact sheets after export")
    p.add_argument("--force-recognize", action="store_true", help="run visual recognizer even if tags already exist")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    root = Path.cwd()
    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "wedding_ai_export_v1_122")
    steps: list[dict[str, Any]] = []

    if not project.exists():
        res = {"ok": False, "error": "PROJECT_NOT_FOUND", "project": str(project)}
        write_json(out / "AI_EXPORT_V1_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    if not source.exists() and a.recognizer != "skip":
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "AI_EXPORT_V1_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    recognizer_map = {
        "119h": "scripts/create_precision_semantic_recognizer_119h.py",
        "119g": "scripts/create_strong_visual_ai_recognizer_119g.py",
        "119e": "scripts/create_wedding_semantic_recognizer_119e.py",
    }
    planner_map = {
        "120e": "scripts/create_precision_story_planner_120e.py",
        "120d": "scripts/create_strict_semantic_story_planner_120d.py",
        "120c": "scripts/create_wedding_semantic_story_planner_120c.py",
    }

    # Step 1: visual recognition, unless skipped and existing tags are present.
    if a.recognizer != "skip":
        need_recognize = a.force_recognize or not has_fresh_tags(project)
        if need_recognize:
            script = root / recognizer_map[a.recognizer]
            if not script.exists():
                res = {
                    "ok": False,
                    "error": "RECOGNIZER_SCRIPT_NOT_FOUND",
                    "script": str(script),
                    "hint": "Copy/install the corresponding 119E/119G/119H module first.",
                }
                write_json(out / "AI_EXPORT_V1_ERROR.json", res)
                print(json.dumps(res, ensure_ascii=False, indent=2))
                return

            ok = run_step(
                f"Visual AI recognizer {a.recognizer}",
                [
                    sys.executable, str(script),
                    "--project", str(project),
                    "--source", str(source),
                    "--frame-samples", str(a.frame_samples),
                    "--max-files", str(a.max_files),
                    "--no-open",
                ],
                root,
                steps,
            )
            if not ok:
                write_json(out / "AI_EXPORT_V1_FAILED.json", {"ok": False, "failed_at": "recognizer", "steps": steps})
                return
        else:
            steps.append({"label": "Visual AI recognizer", "ok": True, "skipped": True, "reason": "existing stt_visual_ai_scene_tags_v1.json"})
            print("[122] Skip recognizer: existing visual tags found. Use --force-recognize to rerun.", flush=True)
    else:
        if not has_fresh_tags(project):
            res = {"ok": False, "error": "NO_EXISTING_VISUAL_TAGS", "hint": "Run recognizer first or remove --recognizer skip."}
            write_json(out / "AI_EXPORT_V1_ERROR.json", res)
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return
        steps.append({"label": "Visual AI recognizer", "ok": True, "skipped": True, "reason": "user selected skip"})

    # Step 2: planner
    planner_script = root / planner_map[a.planner]
    if not planner_script.exists():
        res = {
            "ok": False,
            "error": "PLANNER_SCRIPT_NOT_FOUND",
            "script": str(planner_script),
            "hint": "Copy/install the corresponding 120C/120D/120E module first.",
        }
        write_json(out / "AI_EXPORT_V1_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    ok = run_step(
        f"Story planner {a.planner}",
        [
            sys.executable, str(planner_script),
            "--project", str(project),
            "--style-profile", a.style_profile,
            "--target-shots", str(a.target_shots),
            "--no-open",
        ],
        root,
        steps,
    )
    if not ok:
        write_json(out / "AI_EXPORT_V1_FAILED.json", {"ok": False, "failed_at": "planner", "steps": steps})
        return

    # Step 3: XML export
    exporter_script = root / "scripts/export_beat_snapped_beauty_xml_115.py"
    if not exporter_script.exists():
        res = {
            "ok": False,
            "error": "EXPORTER_115_NOT_FOUND",
            "script": str(exporter_script),
            "hint": "Copy/install module 115 first.",
        }
        write_json(out / "AI_EXPORT_V1_ERROR.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    ok = run_step(
        "Premiere XML export 115",
        [
            sys.executable, str(exporter_script),
            "--project", str(project),
            "--style-profile", a.style_profile,
            "--preset", a.preset,
            "--fps", str(a.fps),
        ],
        root,
        steps,
    )
    if not ok:
        write_json(out / "AI_EXPORT_V1_FAILED.json", {"ok": False, "failed_at": "xml_export", "steps": steps})
        return

    # Optional review sheets
    if a.review:
        review_script = root / "scripts/create_scene_review_contact_sheets_121.py"
        if review_script.exists():
            run_step(
                "Scene review contact sheets 121",
                [
                    sys.executable, str(review_script),
                    "--project", str(project),
                    "--max-per-tag", "80",
                    "--no-open",
                ],
                root,
                steps,
            )
        else:
            steps.append({"label": "Scene review contact sheets 121", "ok": False, "skipped": True, "reason": "script not found"})

    summary = summary_from_project(project)
    result = {
        "ok": True,
        "module": "122_wedding_ai_export_v1",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "source": str(source),
        "style_profile": a.style_profile,
        "recognizer": a.recognizer,
        "planner": a.planner,
        "steps": steps,
        **summary,
        "report_dir": str(out),
        "fix": "122_wedding_ai_export_v1",
    }

    write_json(out / "AI_EXPORT_V1_RESULT.json", result)
    write_json(project / "stt_wedding_ai_export_v1_result.json", result)

    print("\n" + "=" * 80)
    print("[122] AI EXPORT V1 DONE")
    print("=" * 80)
    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "xml_output": result["xml_output"],
        "visual_scene_counts": result.get("visual_scene_counts"),
        "timeline_count": result.get("xml_timeline_count"),
        "timeline_seconds": result.get("xml_timeline_seconds"),
        "gap_count": result.get("xml_gap_count"),
        "unknown_duration_count": result.get("xml_unknown_duration_count"),
        "fix": "122_wedding_ai_export_v1",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
