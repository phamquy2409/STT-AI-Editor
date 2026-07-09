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
class WeddingSceneClassifierConfig:
    output_prefix: str = "wedding_scene"
    use_image_features: bool = True


class WeddingSceneClassifier:
    # Build 021.
    # Lightweight wedding-scene classifier.
    #
    # No heavy model yet. It uses:
    # - existing STT AI scores: people/composition/motion/beauty
    # - thumbnail/frame color features if available
    # - wedding-specific heuristic labels
    #
    # Output labels:
    # - bride_groom
    # - family
    # - ceremony
    # - stage
    # - guest
    # - decor
    # - wide_establishing
    # - detail
    # - party
    # - unknown

    def __init__(
        self,
        project: STTProject,
        input_json: str | Path | None = None,
        config: WeddingSceneClassifierConfig | None = None,
    ) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.config = config or WeddingSceneClassifierConfig()

    def classify(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Input json not found: {self.input_json}")

        rows = self._load_rows(self.input_json)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_json = output_dir / "roughcut_wedding_scene.json"
        output_csv = output_dir / "roughcut_wedding_scene.csv"
        roughcut_plan_json = output_dir / "roughcut_plan.json"
        summary_txt = output_dir / "wedding_scene_summary.txt"

        print("STT AI Wedding Scene Classifier")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"Rows: {len(rows)}")
        print(f"Output: {output_dir}")
        print("-" * 60)

        classified: list[dict[str, Any]] = []

        for index, row in enumerate(rows, start=1):
            item = dict(row)
            item["order"] = int(item.get("order", index))
            features = self._extract_image_features(item)
            scene = self._classify_row(item, features)
            confidence = self._confidence(item, features, scene)

            item["wedding_scene"] = scene
            item["wedding_scene_confidence"] = round(confidence, 3)
            item["wedding_scene_features"] = features
            item["scene_priority"] = self._scene_priority(scene)
            classified.append(item)

        self._retimeline(classified)

        output_json.write_text(
            json.dumps(classified, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        roughcut_plan_json.write_text(
            json.dumps(classified, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._write_csv(output_csv, classified)
        self._write_summary(summary_txt, classified)

        print("WEDDING SCENE CLASSIFICATION COMPLETE")
        print(f"Classified rows: {len(classified)}")
        print(f"JSON: {output_json}")
        print(f"CSV: {output_csv}")
        print("-" * 60)

        return {
            "output_dir": str(output_dir),
            "scene_json": str(output_json),
            "scene_csv": str(output_csv),
            "roughcut_plan_json": str(roughcut_plan_json),
            "summary": str(summary_txt),
            "input_json": str(self.input_json),
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            # best input: candidate pool after people/composition
            "expanded_candidates_*/roughcut_plan_people_composition.json",
            # or latest story/manual outputs
            "story_timeline_*/roughcut_story.json",
            "story_timeline_*/roughcut_plan.json",
            "manual_final_*/manual_roughcut.json",
            "manual_final_*/roughcut_plan.json",
            "final_roughcut_*/roughcut_final.json",
            "final_roughcut_*/roughcut_plan.json",
            "roughcut_*/roughcut_plan_people_composition.json",
            "roughcut_*/roughcut_plan_best_moments.json",
            "roughcut_*/roughcut_plan.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan.json"

        return candidates[0]

    @staticmethod
    def _load_rows(path: Path) -> list[dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(payload, list):
            rows = [dict(x) for x in payload if isinstance(x, dict)]
        elif isinstance(payload, dict) and isinstance(payload.get("segments"), list):
            rows = [dict(x) for x in payload["segments"] if isinstance(x, dict)]
        elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
            rows = [dict(x) for x in payload["items"] if isinstance(x, dict)]
        else:
            raise RuntimeError(f"Unsupported json format: {path}")

        return rows

    def _extract_image_features(self, row: dict[str, Any]) -> dict[str, Any]:
        if not self.config.use_image_features or cv2 is None:
            return {
                "image_available": False,
                "reason": "cv2_unavailable_or_disabled",
            }

        image_path = self._find_image_path(row)
        if not image_path or not image_path.exists():
            return {
                "image_available": False,
                "reason": "thumbnail_not_found",
            }

        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return {
                    "image_available": False,
                    "reason": "imread_failed",
                }

            # Resize for speed.
            img = cv2.resize(img, (320, 180), interpolation=cv2.INTER_AREA)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            h = hsv[:, :, 0].astype(np.float32)
            s = hsv[:, :, 1].astype(np.float32)
            v = hsv[:, :, 2].astype(np.float32)

            brightness = float(np.mean(v) / 255.0)
            saturation = float(np.mean(s) / 255.0)
            contrast = float(np.std(gray) / 255.0)

            # Very rough color-zone ratios.
            bright_ratio = float(np.mean(v > 190))
            dark_ratio = float(np.mean(v < 55))
            red_ratio = float(np.mean(((h < 10) | (h > 170)) & (s > 60) & (v > 70)))
            green_ratio = float(np.mean((h > 35) & (h < 85) & (s > 40) & (v > 60)))
            blue_ratio = float(np.mean((h > 90) & (h < 130) & (s > 40) & (v > 60)))
            warm_ratio = float(np.mean(((h < 25) | (h > 165)) & (s > 35) & (v > 70)))
            white_ratio = float(np.mean((s < 38) & (v > 170)))
            skin_ratio = float(np.mean(((h > 0) & (h < 25)) & (s > 35) & (s < 170) & (v > 60)))

            # Edge density: detail/decor/stage often has many edges.
            edges = cv2.Canny(gray, 80, 160)
            edge_ratio = float(np.mean(edges > 0))

            return {
                "image_available": True,
                "image_path": str(image_path),
                "brightness": round(brightness, 4),
                "saturation": round(saturation, 4),
                "contrast": round(contrast, 4),
                "bright_ratio": round(bright_ratio, 4),
                "dark_ratio": round(dark_ratio, 4),
                "red_ratio": round(red_ratio, 4),
                "green_ratio": round(green_ratio, 4),
                "blue_ratio": round(blue_ratio, 4),
                "warm_ratio": round(warm_ratio, 4),
                "white_ratio": round(white_ratio, 4),
                "skin_ratio": round(skin_ratio, 4),
                "edge_ratio": round(edge_ratio, 4),
            }

        except Exception as exc:
            return {
                "image_available": False,
                "reason": f"feature_error:{exc}",
            }

    def _find_image_path(self, row: dict[str, Any]) -> Path | None:
        thumb = str(row.get("thumbnail", "")).strip()
        if thumb:
            p = Path(thumb)
            if p.is_absolute() and p.exists():
                return p

            candidate = self.input_json.parent / p
            if candidate.exists():
                return candidate

        order = int(float(row.get("order", 0) or 0))
        if order > 0:
            candidate = self.input_json.parent / "preview_thumbnails" / f"thumb_{order:03d}.jpg"
            if candidate.exists():
                return candidate

        return None

    def _classify_row(self, row: dict[str, Any], features: dict[str, Any]) -> str:
        label = str(row.get("content_label", "")).lower()
        role = str(row.get("story_role", "")).lower()
        section = str(row.get("story_section", "")).lower()

        motion = self._num(row, "motion_score", 0.0)
        ai_keep = self._num(row, "ai_keep_score", 0.0)
        final = self._num(row, "final_wedding_score", self._num(row, "expansion_score", ai_keep))
        subject = self._num(row, "subject_score", 0.0)
        face_count = self._num(row, "face_count", 0.0)
        composition = self._num(row, "composition_score", 0.0)

        brightness = self._f(features, "brightness")
        saturation = self._f(features, "saturation")
        red_ratio = self._f(features, "red_ratio")
        warm_ratio = self._f(features, "warm_ratio")
        white_ratio = self._f(features, "white_ratio")
        skin_ratio = self._f(features, "skin_ratio")
        edge_ratio = self._f(features, "edge_ratio")
        bright_ratio = self._f(features, "bright_ratio")
        dark_ratio = self._f(features, "dark_ratio")

        has_people = (
            label in {"skin_people", "wide_people", "face_people"}
            or "people" in role
            or face_count >= 1
            or skin_ratio >= 0.10
        )

        # Party: dark + saturated/warm/red + motion.
        if motion >= 60 and saturation >= 0.22 and (dark_ratio >= 0.12 or red_ratio >= 0.06 or warm_ratio >= 0.16):
            return "party"

        # Stage: high contrast / high edges / bright lighting, often not close people.
        if (edge_ratio >= 0.18 and bright_ratio >= 0.22 and composition >= 45) or ("stage" in section):
            return "stage"

        # Bride/groom: people + white/warm/skin + high final score.
        if has_people and (white_ratio >= 0.10 or skin_ratio >= 0.13) and final >= 38:
            return "bride_groom"

        # Family / guests: people but less strong bride/groom signal.
        if has_people:
            if face_count >= 3 or skin_ratio >= 0.18:
                return "family"
            if motion >= 42:
                return "guest"
            return "bride_groom"

        # Ceremony: warm/red/white decor, moderate edges, low motion.
        if (warm_ratio >= 0.15 or red_ratio >= 0.05 or white_ratio >= 0.14) and motion < 55 and edge_ratio >= 0.10:
            return "ceremony"

        # Decor/detail/establishing.
        if label in {"empty_or_decor", "possible_people_or_detail"} or "detail" in role:
            if edge_ratio >= 0.16 or subject >= 55:
                return "detail"
            return "decor"

        # Wide establishing: stable, not too many subjects, good technical score.
        if motion < 40 and composition >= 45 and final >= 35:
            return "wide_establishing"

        if subject >= 50 or edge_ratio >= 0.15:
            return "detail"

        if ai_keep >= 45:
            return "decor"

        return "unknown"

    def _confidence(self, row: dict[str, Any], features: dict[str, Any], scene: str) -> float:
        # Basic confidence from feature availability and class signal.
        conf = 0.42

        if features.get("image_available"):
            conf += 0.16

        label = str(row.get("content_label", "")).lower()
        role = str(row.get("story_role", "")).lower()

        if scene in {"bride_groom", "family", "guest"} and (label in {"skin_people", "wide_people"} or "people" in role):
            conf += 0.18

        if scene in {"decor", "detail", "ceremony", "stage"} and label in {"empty_or_decor", "possible_people_or_detail"}:
            conf += 0.12

        if scene == "party" and self._num(row, "motion_score", 0.0) >= 60:
            conf += 0.16

        final = self._num(row, "final_wedding_score", self._num(row, "expansion_score", self._num(row, "ai_keep_score", 0.0)))
        if final >= 50:
            conf += 0.08

        if scene == "unknown":
            conf = min(conf, 0.35)

        return max(0.05, min(conf, 0.95))

    @staticmethod
    def _scene_priority(scene: str) -> int:
        priorities = {
            "wide_establishing": 10,
            "decor": 20,
            "detail": 30,
            "ceremony": 40,
            "family": 50,
            "bride_groom": 60,
            "guest": 70,
            "stage": 80,
            "party": 90,
            "unknown": 99,
        }
        return priorities.get(scene, 99)

    @staticmethod
    def _retimeline(rows: list[dict[str, Any]]) -> None:
        cursor = 0.0
        for idx, row in enumerate(rows, start=1):
            start = WeddingSceneClassifier._num(row, "source_start_seconds", 0.0)
            end = WeddingSceneClassifier._num(row, "source_end_seconds", start)
            duration = WeddingSceneClassifier._num(row, "duration_seconds", end - start)

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
    def _num(row: dict[str, Any], key: str, default: float = 0.0) -> float:
        try:
            value = row.get(key, default)
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _f(features: dict[str, Any], key: str, default: float = 0.0) -> float:
        try:
            value = features.get(key, default)
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
    def _write_summary(path: Path, rows: list[dict[str, Any]]) -> None:
        counts: dict[str, int] = {}
        for row in rows:
            scene = str(row.get("wedding_scene", "unknown"))
            counts[scene] = counts.get(scene, 0) + 1

        lines = [
            "STT AI Editor - Wedding Scene Classifier Summary",
            "=" * 65,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Rows: {len(rows)}",
            "",
            "Scene counts:",
        ]

        for scene, count in sorted(counts.items(), key=lambda x: WeddingSceneClassifier._scene_priority(x[0])):
            lines.append(f"- {scene}: {count}")

        lines.append("")
        lines.append("Timeline:")

        for row in rows:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"[{row.get('wedding_scene')} {float(row.get('wedding_scene_confidence', 0.0)):.2f}] "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def classify_wedding_scenes_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    classifier = WeddingSceneClassifier(project=project, input_json=input_json)
    return classifier.classify()
