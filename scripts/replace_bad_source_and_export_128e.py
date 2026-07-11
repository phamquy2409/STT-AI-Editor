from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from collections import defaultdict
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


def norm_path(v: Any) -> str:
    return str(v or "").replace("\\", "/").strip().lower()


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


def locate_timeline(project: Path) -> tuple[Path | None, dict[str, Any]]:
    for name in [
        "stt_multicam_directed_timeline_v1.json",
        "stt_climax_directed_timeline_v1.json",
        "stt_multicam_selected_timeline_v1.json",
        "stt_quality_moment_timeline_v1.json",
        "stt_beat_snapped_beauty_timeline_v1.json",
    ]:
        p = project / name
        d = read_json(p)
        if d.get("items"):
            return p, d
    return None, {}


def build_event_index(project: Path) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
    data = read_json(project / "stt_multicam_event_groups_v1.json")
    by_path: dict[str, str] = {}
    by_event: dict[str, list[dict[str, Any]]] = {}
    for event in data.get("events") or []:
        eid = str(event.get("event_id") or "")
        rows = list(event.get("items") or [])
        by_event[eid] = rows
        for row in rows:
            p = norm_path(row.get("file"))
            if p:
                by_path[p] = eid
    return by_path, by_event


def candidate_score(
    candidate: dict[str, Any],
    target: dict[str, Any],
    same_event: bool,
) -> float:
    target_tag = str(target.get("scene_tag") or "other")
    target_family = semantic_family(target_tag)
    target_camera = str(target.get("camera_group") or "")
    target_order = inum(target.get("source_order"), inum(target.get("_source_order"), 0))

    tag = str(candidate.get("scene_tag") or "other")
    family = str(candidate.get("semantic_family") or semantic_family(tag))
    camera = str(candidate.get("camera_group") or "")
    source_order = inum(candidate.get("source_order"), 0)

    quality = fnum(candidate.get("quality_score"), 45)
    beauty = fnum(candidate.get("beauty_score"), 55)

    score = quality * 0.55 + beauty * 0.35

    if same_event:
        score += 45
    if tag == target_tag:
        score += 35
    elif family == target_family:
        score += 18
    else:
        score -= 35

    if target_camera and camera and camera != target_camera:
        score += 8

    score -= min(20.0, abs(source_order - target_order) * 0.12)

    if candidate.get("is_drone"):
        section = str(target.get("music_section") or target.get("story_part") or "")
        if section not in {"intro", "release", "ending"}:
            score -= 40

    return score


def choose_replacement(
    target: dict[str, Any],
    all_sources: list[dict[str, Any]],
    event_by_path: dict[str, str],
    sources_by_event: dict[str, list[dict[str, Any]]],
    excluded_names: set[str],
    used_paths: set[str],
) -> tuple[dict[str, Any] | None, str]:
    target_path = norm_path(target.get("file"))
    target_name = str(target.get("filename") or Path(target_path).name).lower()
    target_duration = fnum(target.get("duration_sec"), 0)
    target_tag = str(target.get("scene_tag") or "other")
    target_family = semantic_family(target_tag)

    event_id = str(target.get("multicam_event_id") or event_by_path.get(target_path, ""))
    event_candidates = list(sources_by_event.get(event_id, [])) if event_id else []

    def valid(c: dict[str, Any]) -> bool:
        cp = norm_path(c.get("file"))
        name = str(c.get("filename") or Path(cp).name).lower()
        duration = fnum(c.get("duration_sec"), 0)

        if not cp or cp == target_path:
            return False
        if name in excluded_names:
            return False
        if cp in used_paths:
            return False
        if not Path(str(c.get("file") or "")).exists():
            return False
        if duration > 0 and duration < target_duration + 0.25:
            return False
        return True

    ranked = []
    for c in event_candidates:
        if not valid(c):
            continue
        tag = str(c.get("scene_tag") or "other")
        family = str(c.get("semantic_family") or semantic_family(tag))
        if tag != target_tag and family != target_family:
            continue
        ranked.append((candidate_score(c, target, True), c, "same_event"))

    if not ranked:
        for c in all_sources:
            if not valid(c):
                continue
            tag = str(c.get("scene_tag") or "other")
            family = str(c.get("semantic_family") or semantic_family(tag))
            if tag != target_tag and family != target_family:
                continue
            ranked.append((candidate_score(c, target, False), c, "same_semantic"))

    if not ranked:
        return None, "no_candidate"

    ranked.sort(key=lambda x: x[0], reverse=True)
    _, chosen, reason = ranked[0]
    return chosen, reason


def patch_timeline(
    project: Path,
    timeline: dict[str, Any],
    exclude_names: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    camera_map = read_json(project / "stt_camera_source_map_v1.json")
    all_sources = list(camera_map.get("items") or [])
    event_by_path, sources_by_event = build_event_index(project)

    rows = [dict(x) for x in (timeline.get("items") or [])]
    used_paths = {
        norm_path(x.get("file"))
        for x in rows
        if str(x.get("filename") or "").lower() not in exclude_names
    }

    replaced = 0
    failed = 0
    changes = []

    for index, row in enumerate(rows):
        filename = str(row.get("filename") or Path(str(row.get("file") or "")).name).lower()
        if filename not in exclude_names:
            continue

        chosen, reason = choose_replacement(
            row,
            all_sources,
            event_by_path,
            sources_by_event,
            exclude_names,
            used_paths,
        )

        if not chosen:
            failed += 1
            changes.append({
                "timeline_index": index + 1,
                "bad_filename": filename,
                "replaced": False,
                "reason": reason,
            })
            continue

        duration = fnum(row.get("duration_sec"), 0)
        media_duration = fnum(chosen.get("duration_sec"), 0)
        source_in = fnum(chosen.get("best_source_in_sec"), 0)

        if media_duration > 0:
            source_in = clamp(
                source_in,
                0.0,
                max(0.0, media_duration - duration - 0.10),
            )

        old_file = str(row.get("file") or "")
        old_filename = str(row.get("filename") or Path(old_file).name)

        row.update({
            "bad_source_replaced": True,
            "bad_source_original_file": old_file,
            "bad_source_original_filename": old_filename,
            "bad_source_replacement_reason": reason,
            "file": chosen.get("file"),
            "filename": chosen.get("filename"),
            "scene_tag": chosen.get("scene_tag", row.get("scene_tag")),
            "camera_group": chosen.get("camera_group", row.get("camera_group")),
            "shot_scale": chosen.get("shot_scale", row.get("shot_scale")),
            "source_in_sec": round(source_in, 6),
            "source_out_sec": round(source_in + duration, 6),
            "source_duration_sec": round(duration, 6),
            "media_duration_sec": media_duration,
        })

        used_paths.add(norm_path(chosen.get("file")))
        rows[index] = row
        replaced += 1

        changes.append({
            "timeline_index": index + 1,
            "bad_filename": old_filename,
            "replacement_filename": chosen.get("filename"),
            "replacement_file": chosen.get("file"),
            "replaced": True,
            "reason": reason,
            "duration_sec": duration,
            "source_in_sec": round(source_in, 6),
        })

    patched = dict(timeline)
    patched["module_before_128e"] = timeline.get("module")
    patched["module"] = "128e_bad_source_replacer"
    patched["updated_at"] = datetime.now().isoformat(timespec="seconds")
    patched["items"] = rows
    patched["bad_source_summary"] = {
        "excluded_names": sorted(exclude_names),
        "replaced_count": replaced,
        "failed_count": failed,
        "changes": changes,
    }

    return patched, patched["bad_source_summary"]


def main() -> None:
    p = argparse.ArgumentParser(
        description="128E blacklist bad source and replace it before 128D export."
    )
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument(
        "--exclude",
        action="append",
        required=True,
        help="Bad filename. Can repeat, e.g. --exclude STT0043.MP4",
    )
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--sequence-fps", type=float, default=30.0)
    p.add_argument("--default-source-fps", type=float, default=50.0)
    p.add_argument("--max-beat-shift", type=float, default=0.24)
    p.add_argument("--source-safety-frames", type=int, default=10)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    scripts_dir = Path(__file__).resolve().parent
    exporter_128d = scripts_dir / "export_premiere_mixedrate_repair_128d.py"

    if not exporter_128d.exists():
        result = {
            "ok": False,
            "error": "MISSING_128D_EXPORTER",
            "expected": str(exporter_128d),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    source_timeline_path, timeline = locate_timeline(project)
    if not source_timeline_path or not timeline.get("items"):
        result = {
            "ok": False,
            "error": "NO_TIMELINE",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    excluded_names = {
        Path(str(name)).name.lower().strip()
        for name in a.exclude
        if str(name).strip()
    }

    patched, summary = patch_timeline(
        project,
        timeline,
        excluded_names,
    )

    report_dir = (
        project
        / "exports"
        / f"bad_source_replacer_128e_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    patched_path = project / "stt_128e_bad_source_replaced_timeline_v1.json"
    write_json(patched_path, patched)
    write_json(report_dir / patched_path.name, patched)

    if summary["failed_count"] > 0:
        result = {
            "ok": False,
            "error": "REPLACEMENT_NOT_FOUND",
            "report_dir": str(report_dir),
            **summary,
        }
        write_json(report_dir / "FINAL_128E_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 128D always checks stt_multicam_directed_timeline_v1.json first.
    canonical_path = project / "stt_multicam_directed_timeline_v1.json"
    canonical_existed = canonical_path.exists()
    canonical_bytes = canonical_path.read_bytes() if canonical_existed else b""

    try:
        write_json(canonical_path, patched)

        command = [
            os.sys.executable,
            str(exporter_128d),
            "--project", str(project),
            "--preset", a.preset,
            "--sequence-fps", str(a.sequence_fps),
            "--default-source-fps", str(a.default_source_fps),
            "--max-beat-shift", str(a.max_beat_shift),
            "--source-safety-frames", str(a.source_safety_frames),
            "--no-open",
        ]

        run = subprocess.run(
            command,
            cwd=str(scripts_dir.parent),
            capture_output=True,
            text=True,
        )

        if run.returncode != 0:
            result = {
                "ok": False,
                "error": "128D_EXPORT_FAILED",
                "stdout": run.stdout,
                "stderr": run.stderr,
                "report_dir": str(report_dir),
                **summary,
            }
            write_json(report_dir / "FINAL_128E_REPORT.json", result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        generated = {
            "video_only": project / "stt_128d_VIDEO_ONLY_SAFE.xml",
            "safe_music": project / "stt_128d_SAFE_WITH_MUSIC.xml",
            "slow_music": project / "stt_128d_SLOW50_WITH_MUSIC.xml",
        }
        final_paths = {
            "video_only": project / "stt_128e_VIDEO_ONLY_BAD_SOURCE_REPLACED.xml",
            "safe_music": project / "stt_128e_SAFE_WITH_MUSIC_BAD_SOURCE_REPLACED.xml",
            "slow_music": project / "stt_128e_SLOW50_WITH_MUSIC_BAD_SOURCE_REPLACED.xml",
        }

        for key, source in generated.items():
            if source.exists():
                shutil.copy2(source, final_paths[key])
                shutil.copy2(source, report_dir / final_paths[key].name)

        result = {
            "ok": True,
            "report_dir": str(report_dir),
            "input_timeline": str(source_timeline_path),
            "patched_timeline": str(patched_path),
            "video_only_xml": str(final_paths["video_only"]),
            "safe_music_xml": str(final_paths["safe_music"]),
            "slow_music_xml": str(final_paths["slow_music"]),
            "replaced_count": summary["replaced_count"],
            "failed_count": summary["failed_count"],
            "changes": summary["changes"],
            "fix": "128e_bad_source_replacer",
        }
        write_json(report_dir / "FINAL_128E_REPORT.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if not a.no_open:
            try:
                os.startfile(str(report_dir))  # type: ignore[attr-defined]
            except Exception:
                pass

    finally:
        if canonical_existed:
            canonical_path.write_bytes(canonical_bytes)
        elif canonical_path.exists():
            canonical_path.unlink()


if __name__ == "__main__":
    main()
