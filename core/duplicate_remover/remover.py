from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

from core.project import ProjectManager, STTProject


@dataclass
class DuplicateShotRemoverConfig:
    output_prefix: str = "duplicate_removed"
    target_duration_seconds: float = 60.0
    same_video_gap_seconds: float = 12.0
    hash_similarity_threshold: float = 0.90
    color_similarity_threshold: float = 0.92
    fill_after_remove: bool = True
    max_segments_per_video: int = 2


class DuplicateShotRemover:
    # Build 023.
    # Removes repeated / near-repeated clips after story timeline.
    #
    # It checks:
    # - same source file with close timestamps
    # - same thumbnail visual hash
    # - similar color histogram
    # - same wedding_scene labels
    #
    # If clips are removed and a larger wedding_scene pool is available,
    # it fills back up to target duration with unused non-duplicate clips.

    def __init__(
        self,
        project: STTProject,
        input_json: str | Path | None = None,
        fill_pool_json: str | Path | None = None,
        config: DuplicateShotRemoverConfig | None = None,
    ) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.fill_pool_json = Path(fill_pool_json) if fill_pool_json else self._find_latest_fill_pool_json()
        self.config = config or DuplicateShotRemoverConfig()

    def remove_duplicates(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Input json not found: {self.input_json}")

        rows = self._load_rows(self.input_json)
        fill_rows = self._load_rows(self.fill_pool_json) if self.fill_pool_json and self.fill_pool_json.exists() else []

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_json = output_dir / "roughcut_no_duplicates.json"
        output_csv = output_dir / "roughcut_no_duplicates.csv"
        roughcut_plan_json = output_dir / "roughcut_plan.json"
        removed_csv = output_dir / "duplicate_removed.csv"
        summary_txt = output_dir / "duplicate_removed_summary.txt"

        print("STT AI Duplicate Shot Remover")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"Input rows: {len(rows)}")
        print(f"Fill pool: {self.fill_pool_json if self.fill_pool_json else ''}")
        print(f"Fill pool rows: {len(fill_rows)}")
        print(f"Output: {output_dir}")
        print("-" * 60)

        prepared = self._prepare_rows(rows, self.input_json.parent)
        selected, removed = self._dedupe(prepared)

        if self.config.fill_after_remove:
            prepared_fill = self._prepare_rows(fill_rows, self.fill_pool_json.parent if self.fill_pool_json else self.input_json.parent)
            self._fill_to_target(selected, removed, prepared_fill)

        self._retimeline(selected)

        output_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        roughcut_plan_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(output_csv, selected)
        self._write_csv(removed_csv, removed)
        self._write_summary(summary_txt, rows, selected, removed)

        total_duration = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        print("DUPLICATE REMOVAL COMPLETE")
        print(f"Input rows: {len(rows)}")
        print(f"Selected rows: {len(selected)}")
        print(f"Removed rows: {len(removed)}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"JSON: {output_json}")
        print(f"Removed CSV: {removed_csv}")
        print("-" * 60)

        return {
            "output_dir": str(output_dir),
            "no_duplicates_json": str(output_json),
            "no_duplicates_csv": str(output_csv),
            "roughcut_plan_json": str(roughcut_plan_json),
            "removed_csv": str(removed_csv),
            "summary": str(summary_txt),
            "input_json": str(self.input_json),
            "fill_pool_json": str(self.fill_pool_json) if self.fill_pool_json else "",
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            "story_timeline_v2_*/roughcut_story_v2.json",
            "story_timeline_v2_*/roughcut_plan.json",
            "story_timeline_*/roughcut_story.json",
            "story_timeline_*/roughcut_plan.json",
            "manual_final_*/manual_roughcut.json",
            "manual_final_*/roughcut_plan.json",
            "final_roughcut_*/roughcut_final.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan.json"

        return candidates[0]

    def _find_latest_fill_pool_json(self) -> Path | None:
        patterns = [
            "wedding_scene_*/roughcut_wedding_scene.json",
            "wedding_scene_*/roughcut_plan.json",
            "expanded_candidates_*/roughcut_plan_people_composition.json",
            "expanded_candidates_*/roughcut_plan_best_moments.json",
            "expanded_candidates_*/expanded_candidates.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return None

        return candidates[0]

    @staticmethod
    def _load_rows(path: Path) -> list[dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(payload, list):
            return [dict(x) for x in payload if isinstance(x, dict)]

        if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
            return [dict(x) for x in payload["segments"] if isinstance(x, dict)]

        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            return [dict(x) for x in payload["items"] if isinstance(x, dict)]

        raise RuntimeError(f"Unsupported json format: {path}")

    def _prepare_rows(self, rows: list[dict[str, Any]], base_dir: Path) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []

        for index, row in enumerate(rows, start=1):
            item = dict(row)
            item["order"] = int(float(item.get("order", index)))
            item["_base_dir"] = str(base_dir)
            item["_dedupe_score"] = round(self._score(item), 2)

            img = self._find_image_path(item, base_dir)
            item["_image_path"] = str(img) if img else ""
            item["_visual"] = self._visual_signature(img) if img else {
                "available": False,
                "reason": "thumbnail_not_found",
            }

            prepared.append(item)

        prepared.sort(
            key=lambda r: (
                float(r.get("_dedupe_score", 0.0)),
                float(r.get("story_v2_score", r.get("story_score", 0.0))),
                float(r.get("final_wedding_score", r.get("expansion_score", r.get("ai_keep_score", 0.0)))),
            ),
            reverse=True,
        )

        return prepared

    def _score(self, row: dict[str, Any]) -> float:
        final = self._num(row, "final_wedding_score", self._num(row, "expansion_score", self._num(row, "ai_keep_score", 0.0)))
        story_v2 = self._num(row, "story_v2_score", self._num(row, "story_score", 0.0))
        ai = self._num(row, "ai_keep_score", 0.0)
        scene_conf = self._num(row, "wedding_scene_confidence", 0.5)
        beauty = self._num(row, "beauty_score", 0.0)
        moment = self._num(row, "best_moment_score", 0.0)

        return (
            final * 0.34
            + story_v2 * 0.20
            + ai * 0.16
            + moment * 0.12
            + beauty * 0.08
            + scene_conf * 100.0 * 0.10
        )

    def _find_image_path(self, row: dict[str, Any], base_dir: Path) -> Path | None:
        thumb = str(row.get("thumbnail", "")).strip()
        if thumb:
            p = Path(thumb)
            if p.is_absolute() and p.exists():
                return p

            candidate = base_dir / p
            if candidate.exists():
                return candidate

        order = int(float(row.get("order", 0) or 0))
        if order > 0:
            candidate = base_dir / "preview_thumbnails" / f"thumb_{order:03d}.jpg"
            if candidate.exists():
                return candidate

        return None

    @staticmethod
    def _visual_signature(image_path: Path | None) -> dict[str, Any]:
        if cv2 is None:
            return {"available": False, "reason": "cv2_unavailable"}

        if not image_path or not image_path.exists():
            return {"available": False, "reason": "image_missing"}

        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return {"available": False, "reason": "imread_failed"}

            img_small = cv2.resize(img, (64, 36), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)

            # dHash-like binary signature.
            tiny = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
            diff = tiny[:, 1:] > tiny[:, :-1]
            bits = diff.astype(np.uint8).flatten().tolist()

            hsv = cv2.cvtColor(img_small, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [12, 8], [0, 180, 0, 256])
            hist = cv2.normalize(hist, hist).flatten().astype(float).tolist()

            return {
                "available": True,
                "bits": bits,
                "hist": [round(float(x), 6) for x in hist],
            }

        except Exception as exc:
            return {"available": False, "reason": f"visual_error:{exc}"}

    def _dedupe(self, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        selected: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        per_video: dict[str, int] = {}

        for row in rows:
            video_path = str(row.get("video_path", ""))
            if per_video.get(video_path, 0) >= self.config.max_segments_per_video:
                removed_row = dict(row)
                removed_row["duplicate_reason"] = "max_segments_per_video"
                removed.append(self._clean_internal(removed_row))
                continue

            duplicate_of = None
            reason = ""

            for kept in selected:
                is_dup, why = self._is_duplicate(row, kept)
                if is_dup:
                    duplicate_of = kept
                    reason = why
                    break

            if duplicate_of is not None:
                removed_row = dict(row)
                removed_row["duplicate_reason"] = reason
                removed_row["duplicate_of_order"] = duplicate_of.get("order", "")
                removed_row["duplicate_of_video"] = duplicate_of.get("video_filename", "")
                removed.append(self._clean_internal(removed_row))
            else:
                selected.append(dict(row))
                per_video[video_path] = per_video.get(video_path, 0) + 1

        # Restore timeline preference. We selected by quality; final order should follow wedding story if available.
        selected.sort(key=lambda r: int(float(r.get("order", 0))))
        return [self._clean_internal(x) for x in selected], removed

    def _fill_to_target(
        self,
        selected: list[dict[str, Any]],
        removed: list[dict[str, Any]],
        fill_pool: list[dict[str, Any]],
    ) -> None:
        total = sum(float(r.get("duration_seconds", 0.0)) for r in selected)
        if total >= self.config.target_duration_seconds:
            return

        already = {self._identity(r) for r in selected}
        per_video: dict[str, int] = {}
        for r in selected:
            path = str(r.get("video_path", ""))
            per_video[path] = per_video.get(path, 0) + 1

        fill_candidates = sorted(
            fill_pool,
            key=lambda r: float(r.get("_dedupe_score", 0.0)),
            reverse=True,
        )

        for row in fill_candidates:
            if total >= self.config.target_duration_seconds:
                break

            identity = self._identity(row)
            if identity in already:
                continue

            video_path = str(row.get("video_path", ""))
            if per_video.get(video_path, 0) >= self.config.max_segments_per_video:
                continue

            duplicate = False
            reason = ""

            for kept in selected:
                duplicate, reason = self._is_duplicate(row, kept)
                if duplicate:
                    break

            if duplicate:
                removed_row = dict(row)
                removed_row["duplicate_reason"] = "fill_skip_" + reason
                removed.append(self._clean_internal(removed_row))
                continue

            item = self._clean_internal(dict(row))
            item["story_section"] = str(item.get("story_section", "fill_replacement"))
            item["duplicate_fill_added"] = True
            selected.append(item)
            already.add(identity)
            per_video[video_path] = per_video.get(video_path, 0) + 1
            total += float(item.get("duration_seconds", 0.0))

    def _is_duplicate(self, a: dict[str, Any], b: dict[str, Any]) -> tuple[bool, str]:
        a_path = str(a.get("video_path", ""))
        b_path = str(b.get("video_path", ""))

        a_start = self._num(a, "source_start_seconds", 0.0)
        b_start = self._num(b, "source_start_seconds", 0.0)

        if a_path and a_path == b_path and abs(a_start - b_start) <= self.config.same_video_gap_seconds:
            return True, "same_video_close_time"

        a_scene = str(a.get("wedding_scene", a.get("content_label", ""))).lower()
        b_scene = str(b.get("wedding_scene", b.get("content_label", ""))).lower()

        hash_sim = self._hash_similarity(a.get("_visual", {}), b.get("_visual", {}))
        color_sim = self._color_similarity(a.get("_visual", {}), b.get("_visual", {}))

        if a_path and a_path == b_path and hash_sim >= 0.82:
            return True, f"same_video_visual_sim_{hash_sim:.2f}"

        if hash_sim >= self.config.hash_similarity_threshold and color_sim >= self.config.color_similarity_threshold:
            if not a_scene or not b_scene or a_scene == b_scene:
                return True, f"visual_duplicate_hash_{hash_sim:.2f}_color_{color_sim:.2f}"

        if a_scene and a_scene == b_scene and hash_sim >= 0.86 and color_sim >= 0.95:
            return True, f"same_scene_similar_visual_{hash_sim:.2f}_{color_sim:.2f}"

        return False, ""

    @staticmethod
    def _hash_similarity(a_visual: dict[str, Any], b_visual: dict[str, Any]) -> float:
        if not a_visual.get("available") or not b_visual.get("available"):
            return 0.0

        a_bits = a_visual.get("bits", [])
        b_bits = b_visual.get("bits", [])

        if not a_bits or not b_bits or len(a_bits) != len(b_bits):
            return 0.0

        same = sum(1 for a, b in zip(a_bits, b_bits) if int(a) == int(b))
        return same / max(1, len(a_bits))

    @staticmethod
    def _color_similarity(a_visual: dict[str, Any], b_visual: dict[str, Any]) -> float:
        if not a_visual.get("available") or not b_visual.get("available"):
            return 0.0

        a_hist = np.array(a_visual.get("hist", []), dtype=np.float32)
        b_hist = np.array(b_visual.get("hist", []), dtype=np.float32)

        if a_hist.size == 0 or b_hist.size == 0 or a_hist.size != b_hist.size:
            return 0.0

        denom = float(np.linalg.norm(a_hist) * np.linalg.norm(b_hist))
        if denom <= 0:
            return 0.0

        sim = float(np.dot(a_hist, b_hist) / denom)
        return max(0.0, min(sim, 1.0))

    @staticmethod
    def _identity(row: dict[str, Any]) -> tuple:
        return (
            str(row.get("video_path", "")),
            round(float(row.get("source_start_seconds", 0.0)), 3),
            round(float(row.get("source_end_seconds", 0.0)), 3),
        )

    @staticmethod
    def _retimeline(rows: list[dict[str, Any]]) -> None:
        cursor = 0.0

        for idx, row in enumerate(rows, start=1):
            start = DuplicateShotRemover._num(row, "source_start_seconds", 0.0)
            end = DuplicateShotRemover._num(row, "source_end_seconds", start)
            duration = DuplicateShotRemover._num(row, "duration_seconds", end - start)

            if end <= start and duration > 0:
                end = start + duration

            duration = max(0.0, end - start)

            row["order"] = idx
            row["source_start_seconds"] = round(start, 3)
            row["source_end_seconds"] = round(end, 3)
            row["duration_seconds"] = round(duration, 3)
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + duration, 3)

            cursor += duration

    @staticmethod
    def _clean_internal(row: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(row)
        for key in list(cleaned.keys()):
            if key.startswith("_"):
                del cleaned[key]
        return cleaned

    @staticmethod
    def _num(row: dict[str, Any], key: str, default: float = 0.0) -> float:
        try:
            value = row.get(key, default)
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return

        flat_rows: list[dict[str, Any]] = []

        for row in rows:
            out = dict(row)
            features = out.pop("wedding_scene_features", {})
            if isinstance(features, dict):
                for k, v in features.items():
                    out[f"feature_{k}"] = v
            flat_rows.append(out)

        keys: list[str] = []
        for row in flat_rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(flat_rows)

    @staticmethod
    def _write_summary(path: Path, original_rows: list[dict[str, Any]], selected: list[dict[str, Any]], removed: list[dict[str, Any]]) -> None:
        total = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        reason_counts: dict[str, int] = {}
        for row in removed:
            reason = str(row.get("duplicate_reason", "unknown"))
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        scene_counts: dict[str, int] = {}
        for row in selected:
            scene = str(row.get("wedding_scene", "unknown"))
            scene_counts[scene] = scene_counts.get(scene, 0) + 1

        lines = [
            "STT AI Editor - Duplicate Shot Remover Summary",
            "=" * 65,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Original rows: {len(original_rows)}",
            f"Selected rows: {len(selected)}",
            f"Removed rows: {len(removed)}",
            f"Final duration: {total:.2f}s",
            "",
            "Selected scene counts:",
        ]

        for scene, count in sorted(scene_counts.items()):
            lines.append(f"- {scene}: {count}")

        lines.append("")
        lines.append("Remove reasons:")

        if reason_counts:
            for reason, count in sorted(reason_counts.items()):
                lines.append(f"- {reason}: {count}")
        else:
            lines.append("- none")

        lines.append("")
        lines.append("Final timeline:")

        for row in selected:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"[{row.get('wedding_scene', row.get('content_label', ''))}] "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def remove_duplicate_shots_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
    fill_pool_json: str | Path | None = None,
    target_duration_seconds: float = 60.0,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    remover = DuplicateShotRemover(
        project=project,
        input_json=input_json,
        fill_pool_json=fill_pool_json,
        config=DuplicateShotRemoverConfig(target_duration_seconds=target_duration_seconds),
    )

    return remover.remove_duplicates()
