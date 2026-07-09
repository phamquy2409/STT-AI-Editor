from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project import ProjectManager, STTProject


@dataclass
class StoryTimelineV2Config:
    target_duration_seconds: float = 60.0
    max_segments_per_video: int = 1
    output_prefix: str = "story_timeline_v2"
    allow_unknown: bool = True


class WeddingSceneStoryTimelineBuilder:
    # Build 022.
    # Uses Module 021 wedding_scene labels to build a more wedding-like timeline.
    #
    # Sequence idea:
    # opening: decor / wide / detail
    # ceremony build: ceremony / family
    # people core: bride_groom / family / guest
    # cutaway: detail / decor / stage
    # ending: stage / party / bride_groom

    def __init__(
        self,
        project: STTProject,
        input_json: str | Path | None = None,
        config: StoryTimelineV2Config | None = None,
    ) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.config = config or StoryTimelineV2Config()

    def build(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Input json not found: {self.input_json}")

        rows = self._load_rows(self.input_json)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        story_json = output_dir / "roughcut_story_v2.json"
        story_csv = output_dir / "roughcut_story_v2.csv"
        roughcut_plan_json = output_dir / "roughcut_plan.json"
        summary_txt = output_dir / "story_timeline_v2_summary.txt"

        print("STT AI Story Timeline V2 - Wedding Scene")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"Input rows: {len(rows)}")
        print(f"Target duration: {self.config.target_duration_seconds}s")
        print(f"Output: {output_dir}")
        print("-" * 60)

        prepared = self._prepare_rows(rows)
        selected = self._build_timeline(prepared)
        self._retimeline(selected)

        story_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        roughcut_plan_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(story_csv, selected)
        self._write_summary(summary_txt, prepared, selected)

        total_duration = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        print("STORY TIMELINE V2 COMPLETE")
        print(f"Selected segments: {len(selected)}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Story JSON: {story_json}")
        print(f"Premiere-compatible plan: {roughcut_plan_json}")
        print("-" * 60)

        return {
            "output_dir": str(output_dir),
            "story_json": str(story_json),
            "story_csv": str(story_csv),
            "roughcut_plan_json": str(roughcut_plan_json),
            "summary": str(summary_txt),
            "input_json": str(self.input_json),
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            "wedding_scene_*/roughcut_wedding_scene.json",
            "wedding_scene_*/roughcut_plan.json",
            "expanded_candidates_*/roughcut_plan_people_composition.json",
            "story_timeline_*/roughcut_story.json",
            "story_timeline_*/roughcut_plan.json",
            "manual_final_*/manual_roughcut.json",
            "final_roughcut_*/roughcut_final.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_wedding_scene.json"

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

    def _prepare_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []

        for index, row in enumerate(rows, start=1):
            item = dict(row)
            scene = str(item.get("wedding_scene", "")).strip().lower() or self._fallback_scene(item)
            item["wedding_scene"] = scene

            item["story_v2_score"] = round(self._story_score(item), 2)
            item["story_v2_bucket"] = self._bucket(scene)
            item["story_v2_source"] = "module_022_wedding_scene"

            # keep original rough order as secondary signal
            item["_original_order"] = int(float(item.get("order", index)))

            prepared.append(item)

        prepared.sort(
            key=lambda r: (
                float(r.get("story_v2_score", 0.0)),
                float(r.get("wedding_scene_confidence", 0.0)),
                float(r.get("final_wedding_score", r.get("expansion_score", r.get("ai_keep_score", 0.0)))),
            ),
            reverse=True,
        )

        return prepared

    def _fallback_scene(self, row: dict[str, Any]) -> str:
        label = str(row.get("content_label", "")).lower()
        role = str(row.get("story_role", "")).lower()
        motion = self._num(row, "motion_score", 0.0)

        if "people" in label or "people" in role:
            return "bride_groom"
        if motion >= 65:
            return "party"
        if "detail" in role:
            return "detail"
        if "decor" in label:
            return "decor"
        return "unknown"

    @staticmethod
    def _bucket(scene: str) -> str:
        if scene in {"decor", "wide_establishing", "detail"}:
            return "context"
        if scene in {"ceremony", "family"}:
            return "ceremony_family"
        if scene in {"bride_groom", "guest"}:
            return "people"
        if scene in {"stage", "party"}:
            return "energy"
        return "unknown"

    def _story_score(self, row: dict[str, Any]) -> float:
        scene = str(row.get("wedding_scene", "unknown"))
        final = self._num(row, "final_wedding_score", self._num(row, "expansion_score", self._num(row, "ai_keep_score", 0.0)))
        ai = self._num(row, "ai_keep_score", 0.0)
        moment = self._num(row, "best_moment_score", 0.0)
        scene_conf = self._num(row, "wedding_scene_confidence", 0.45)
        story = self._num(row, "story_score", 0.0)
        motion = min(self._num(row, "motion_score", 0.0), 85.0)
        beauty = self._num(row, "beauty_score", 0.0)

        score = (
            final * 0.34
            + ai * 0.18
            + moment * 0.16
            + story * 0.10
            + beauty * 0.08
            + motion * 0.06
            + scene_conf * 100.0 * 0.08
        )

        # Wedding importance boosts.
        if scene == "bride_groom":
            score *= 1.12
        elif scene in {"ceremony", "family"}:
            score *= 1.08
        elif scene in {"decor", "detail", "wide_establishing"}:
            score *= 1.00
        elif scene in {"stage", "party"}:
            score *= 1.04
        elif scene == "unknown":
            score *= 0.78

        return max(0.0, min(score, 100.0))

    def _build_timeline(self, pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        used = set()
        per_video: dict[str, int] = {}

        # Pattern intentionally repeats bride_groom/family but inserts context/cutaway.
        pattern = [
            ("opening_wide", ["wide_establishing", "decor", "detail"], "mid"),
            ("opening_detail", ["decor", "detail", "ceremony"], "top"),
            ("ceremony_context", ["ceremony", "family", "decor"], "top"),
            ("people_intro", ["bride_groom", "family"], "top"),
            ("guest_family", ["family", "guest", "bride_groom"], "mid"),
            ("detail_cutaway", ["detail", "decor", "stage"], "mid"),
            ("main_people", ["bride_groom", "family"], "top"),
            ("stage_or_ceremony", ["stage", "ceremony", "guest"], "mid"),
            ("energy", ["party", "stage", "guest", "bride_groom"], "top"),
            ("closing", ["bride_groom", "party", "stage", "detail"], "top"),
        ]

        total = 0.0
        pattern_index = 0

        while total < self.config.target_duration_seconds:
            section_name, scenes, band = pattern[pattern_index % len(pattern)]

            candidate = self._pick_candidate(
                pool=pool,
                scenes=scenes,
                band=band,
                section_name=section_name,
                used=used,
                per_video=per_video,
                previous=selected[-1] if selected else None,
            )

            if candidate is None and self.config.allow_unknown:
                candidate = self._pick_candidate(
                    pool=pool,
                    scenes=["bride_groom", "family", "ceremony", "detail", "decor", "stage", "party", "guest", "wide_establishing", "unknown"],
                    band=band,
                    section_name="fill",
                    used=used,
                    per_video=per_video,
                    previous=selected[-1] if selected else None,
                )

            if candidate is None:
                break

            candidate["story_section"] = section_name
            candidate["story_v2_band"] = band
            candidate["story_v2_pick_score"] = round(float(candidate.get("_pick_score", candidate.get("story_v2_score", 0.0))), 2)

            selected.append(candidate)
            used.add(self._identity(candidate))

            video_path = str(candidate.get("video_path", ""))
            per_video[video_path] = per_video.get(video_path, 0) + 1

            total += float(candidate.get("duration_seconds", 0.0))
            pattern_index += 1

        return selected

    def _pick_candidate(
        self,
        pool: list[dict[str, Any]],
        scenes: list[str],
        band: str,
        section_name: str,
        used: set[tuple],
        per_video: dict[str, int],
        previous: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        scene_set = {s.lower() for s in scenes}

        candidates = [
            r for r in pool
            if str(r.get("wedding_scene", "unknown")).lower() in scene_set
        ]

        if not candidates:
            return None

        candidates = self._slice_band(candidates, band)

        best: dict[str, Any] | None = None
        best_score = -999999.0

        for row in candidates:
            identity = self._identity(row)
            if identity in used:
                continue

            video_path = str(row.get("video_path", ""))
            if per_video.get(video_path, 0) >= self.config.max_segments_per_video:
                continue

            score = float(row.get("story_v2_score", 0.0))
            score += self._section_bonus(section_name, row)
            score += self._transition_bonus(previous, row)
            score += self._diversity_bonus(row, per_video)

            if score > best_score:
                best = dict(row)
                best_score = score

        # Relax max per video if the target section has no remaining candidate.
        if best is None:
            for row in candidates:
                identity = self._identity(row)
                if identity in used:
                    continue

                score = float(row.get("story_v2_score", 0.0))
                score += self._section_bonus(section_name, row) * 0.5
                score += self._transition_bonus(previous, row) * 0.5

                if score > best_score:
                    best = dict(row)
                    best_score = score

        if best is not None:
            best["_pick_score"] = best_score

        return best

    @staticmethod
    def _slice_band(rows: list[dict[str, Any]], band: str) -> list[dict[str, Any]]:
        rows = sorted(rows, key=lambda r: float(r.get("story_v2_score", 0.0)), reverse=True)
        n = len(rows)

        if n <= 8:
            return rows

        if band == "top":
            return rows[: max(8, n // 2)]

        if band == "mid":
            start = max(0, n // 5)
            end = max(start + 8, n * 4 // 5)
            return rows[start:end]

        if band == "low":
            return rows[n // 2:]

        return rows

    @staticmethod
    def _section_bonus(section_name: str, row: dict[str, Any]) -> float:
        scene = str(row.get("wedding_scene", "unknown"))
        bonus = 0.0

        if section_name.startswith("opening") and scene in {"wide_establishing", "decor", "detail"}:
            bonus += 10.0
        elif section_name == "ceremony_context" and scene in {"ceremony", "family"}:
            bonus += 10.0
        elif section_name in {"people_intro", "main_people"} and scene == "bride_groom":
            bonus += 11.0
        elif section_name == "guest_family" and scene in {"family", "guest"}:
            bonus += 9.0
        elif section_name == "detail_cutaway" and scene in {"detail", "decor", "stage"}:
            bonus += 8.0
        elif section_name == "energy" and scene in {"party", "stage"}:
            bonus += 10.0
        elif section_name == "closing" and scene in {"bride_groom", "party", "stage"}:
            bonus += 8.0

        conf = float(row.get("wedding_scene_confidence", 0.0) or 0.0)
        if conf >= 0.65:
            bonus += 2.0

        return bonus

    @staticmethod
    def _transition_bonus(previous: dict[str, Any] | None, row: dict[str, Any]) -> float:
        if previous is None:
            return 0.0

        bonus = 0.0
        prev_scene = str(previous.get("wedding_scene", "unknown"))
        cur_scene = str(row.get("wedding_scene", "unknown"))
        prev_bucket = str(previous.get("story_v2_bucket", ""))
        cur_bucket = str(row.get("story_v2_bucket", ""))
        prev_video = str(previous.get("video_path", ""))
        cur_video = str(row.get("video_path", ""))

        if prev_video == cur_video:
            bonus -= 16.0

        if prev_scene != cur_scene:
            bonus += 5.0
        else:
            bonus -= 3.0

        if prev_bucket != cur_bucket:
            bonus += 3.5

        return bonus

    @staticmethod
    def _diversity_bonus(row: dict[str, Any], per_video: dict[str, int]) -> float:
        video_path = str(row.get("video_path", ""))
        if video_path not in per_video:
            return 6.0
        return -12.0 * per_video.get(video_path, 0)

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
            start = float(row.get("source_start_seconds", 0.0))
            end = float(row.get("source_end_seconds", start))
            duration = float(row.get("duration_seconds", end - start))

            if end <= start and duration > 0:
                end = start + duration

            duration = max(0.0, end - start)

            row["order"] = idx
            row["source_start_seconds"] = round(start, 3)
            row["source_end_seconds"] = round(end, 3)
            row["duration_seconds"] = round(duration, 3)
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + duration, 3)

            if "_pick_score" in row:
                del row["_pick_score"]
            if "_original_order" in row:
                del row["_original_order"]

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
    def _write_summary(path: Path, pool: list[dict[str, Any]], selected: list[dict[str, Any]]) -> None:
        pool_counts: dict[str, int] = {}
        selected_counts: dict[str, int] = {}

        for row in pool:
            scene = str(row.get("wedding_scene", "unknown"))
            pool_counts[scene] = pool_counts.get(scene, 0) + 1

        for row in selected:
            scene = str(row.get("wedding_scene", "unknown"))
            selected_counts[scene] = selected_counts.get(scene, 0) + 1

        total = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        lines = [
            "STT AI Editor - Story Timeline V2 Wedding Scene Summary",
            "=" * 70,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Input pool: {len(pool)}",
            f"Selected: {len(selected)}",
            f"Total duration: {total:.2f}s",
            "",
            "Input scene counts:",
        ]

        for scene, count in sorted(pool_counts.items()):
            lines.append(f"- {scene}: {count}")

        lines.append("")
        lines.append("Selected scene counts:")

        for scene, count in sorted(selected_counts.items()):
            lines.append(f"- {scene}: {count}")

        lines.append("")
        lines.append("Timeline:")

        for row in selected:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"[{row.get('story_section')}/{row.get('wedding_scene')}] "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s "
                f"score={float(row.get('story_v2_score', 0.0)):.1f} "
                f"conf={float(row.get('wedding_scene_confidence', 0.0)):.2f}"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def build_story_timeline_v2_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
    target_duration_seconds: float = 60.0,
    max_segments_per_video: int = 1,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    builder = WeddingSceneStoryTimelineBuilder(
        project=project,
        input_json=input_json,
        config=StoryTimelineV2Config(
            target_duration_seconds=target_duration_seconds,
            max_segments_per_video=max_segments_per_video,
        ),
    )

    return builder.build()
