from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project import ProjectManager, STTProject


@dataclass
class StoryTimelineConfig:
    target_duration_seconds: float = 60.0
    max_segments_per_video: int = 1
    output_prefix: str = "story_timeline"
    strong_diversity: bool = True


class StoryTimelineBuilder:
    # Build 013B.
    # Strong diversity version:
    # - avoids repeating the same source file
    # - avoids picking only top shots that look the same
    # - alternates roles: detail -> people -> motion -> people -> detail
    # - pulls from top/mid candidate bands to create more visual variety

    def __init__(
        self,
        project: STTProject,
        input_json: str | Path | None = None,
        config: StoryTimelineConfig | None = None,
    ) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.config = config or StoryTimelineConfig()

    def build(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Story input json not found: {self.input_json}")

        pool = json.loads(self.input_json.read_text(encoding="utf-8"))

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        story_json = output_dir / "roughcut_story.json"
        story_csv = output_dir / "roughcut_story.csv"
        roughcut_plan_json = output_dir / "roughcut_plan.json"
        summary_txt = output_dir / "story_timeline_summary.txt"

        print("STT AI Story Timeline Builder - Strong Diversity")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"Input candidates: {len(pool)}")
        print(f"Target duration: {self.config.target_duration_seconds}s")
        print(f"Max segments/video: {self.config.max_segments_per_video}")
        print(f"Output: {output_dir}")
        print("-" * 60)

        prepared = self._prepare_pool(pool)
        selected = self._build_diverse_story(prepared)
        self._retimeline(selected)

        story_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        roughcut_plan_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(story_csv, selected)
        self._write_summary(summary_txt, prepared, selected)

        total = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        print("STORY TIMELINE COMPLETE")
        print(f"Selected segments: {len(selected)}")
        print(f"Total duration: {total:.2f}s")
        print(f"Story JSON: {story_json}")
        print(f"Premiere-compatible plan: {roughcut_plan_json}")
        print("-" * 60)

        return {
            "output_dir": str(output_dir),
            "story_json": str(story_json),
            "story_csv": str(story_csv),
            "roughcut_plan_json": str(roughcut_plan_json),
            "summary": str(summary_txt),
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            "expanded_candidates_*/roughcut_plan_people_composition.json",
            "expanded_candidates_*/roughcut_plan_best_moments.json",
            "expanded_candidates_*/expanded_candidates.json",
            "final_roughcut_*/roughcut_final.json",
            "roughcut_*/roughcut_plan_people_composition.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan_people_composition.json"

        return candidates[0]

    def _prepare_pool(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []

        for row in rows:
            duration = self._num(row, "duration_seconds", 0.0)
            if duration <= 0:
                continue

            item = dict(row)
            item["story_role"] = self._story_role(item)
            item["story_score"] = round(self._story_score(item), 2)
            item["story_source"] = "module_013b_strong_diversity"
            prepared.append(item)

        prepared.sort(key=lambda r: float(r.get("story_score", 0.0)), reverse=True)
        return prepared

    def _story_role(self, row: dict[str, Any]) -> str:
        label = str(row.get("content_label", "")).lower()
        motion = self._num(row, "motion_score", 0.0)
        skin_regions = int(self._num(row, "face_count", 0.0))
        subject = self._num(row, "subject_score", 0.0)

        if label in ("skin_people", "face_people", "wide_people") or skin_regions > 0:
            if motion >= 55:
                return "people_motion"
            return "people"

        if subject >= 60 and motion >= 50:
            return "motion_detail"

        if subject >= 50:
            return "detail"

        if motion >= 60:
            return "motion"

        return "detail"

    def _story_score(self, row: dict[str, Any]) -> float:
        final = self._num(row, "final_wedding_score", self._num(row, "expansion_score", self._num(row, "ai_keep_score", 0.0)))
        moment = self._num(row, "best_moment_score", 0.0)
        ai = self._num(row, "ai_keep_score", 0.0)
        beauty = self._num(row, "beauty_score", 0.0)
        subject = self._num(row, "subject_score", 0.0)
        motion = min(self._num(row, "motion_score", 0.0), 85.0)

        score = final * 0.38 + moment * 0.22 + ai * 0.15 + beauty * 0.10 + subject * 0.10 + motion * 0.05

        role = str(row.get("story_role", ""))
        if role in ("people", "people_motion"):
            score *= 1.05
        elif role in ("detail", "motion_detail"):
            score *= 0.98

        return max(0.0, min(100.0, score))

    def _build_diverse_story(self, pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        used = set()
        used_videos: dict[str, int] = {}
        total = 0.0

        # Strong pattern: intentionally alternates visual purpose.
        # This makes the result visibly different from pure score ranking.
        pattern = [
            ("opening_detail", ["detail", "motion_detail"], "mid"),
            ("opening_people", ["people", "people_motion"], "top"),
            ("context_motion", ["motion_detail", "motion", "detail"], "mid"),
            ("people_main", ["people_motion", "people"], "top"),
            ("detail_break", ["detail", "motion_detail"], "mid"),
            ("people_main", ["people", "people_motion"], "top"),
            ("motion_cutaway", ["motion_detail", "motion", "detail"], "low"),
            ("people_main", ["people_motion", "people"], "top"),
            ("closing_detail", ["detail", "motion_detail", "people"], "mid"),
            ("closing_people", ["people_motion", "people"], "top"),
        ]

        pattern_index = 0

        while total < self.config.target_duration_seconds:
            section_name, roles, band = pattern[pattern_index % len(pattern)]
            candidate = self._pick_from_band(
                pool=pool,
                roles=roles,
                band=band,
                used=used,
                used_videos=used_videos,
                previous=selected[-1] if selected else None,
            )

            # fallback wider roles
            if candidate is None:
                candidate = self._pick_from_band(
                    pool=pool,
                    roles=["people_motion", "people", "motion_detail", "detail", "motion"],
                    band=band,
                    used=used,
                    used_videos=used_videos,
                    previous=selected[-1] if selected else None,
                )

            if candidate is None:
                break

            candidate["story_section"] = section_name
            candidate["story_band"] = band

            selected.append(candidate)
            used.add(self._identity(candidate))
            video_path = str(candidate.get("video_path", ""))
            used_videos[video_path] = used_videos.get(video_path, 0) + 1
            total += float(candidate.get("duration_seconds", 0.0))

            pattern_index += 1

        return selected

    def _pick_from_band(
        self,
        pool: list[dict[str, Any]],
        roles: list[str],
        band: str,
        used: set[tuple],
        used_videos: dict[str, int],
        previous: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        role_set = set(roles)
        candidates = [r for r in pool if str(r.get("story_role", "")) in role_set]

        if not candidates:
            candidates = list(pool)

        candidates = self._slice_band(candidates, band)

        best = None
        best_score = -999999.0

        for row in candidates:
            identity = self._identity(row)
            if identity in used:
                continue

            video_path = str(row.get("video_path", ""))
            if used_videos.get(video_path, 0) >= self.config.max_segments_per_video:
                continue

            score = float(row.get("story_score", 0.0))
            score += self._transition_bonus(previous, row)
            score += self._diversity_bonus(row, used_videos)

            if score > best_score:
                best = dict(row)
                best_score = score

        # Relax video limit only if necessary.
        if best is None:
            for row in candidates:
                identity = self._identity(row)
                if identity in used:
                    continue

                score = float(row.get("story_score", 0.0))
                score += self._transition_bonus(previous, row) * 0.5

                if score > best_score:
                    best = dict(row)
                    best_score = score

        if best is not None:
            best["story_pick_score"] = round(best_score, 2)

        return best

    @staticmethod
    def _slice_band(rows: list[dict[str, Any]], band: str) -> list[dict[str, Any]]:
        rows = sorted(rows, key=lambda r: float(r.get("story_score", 0.0)), reverse=True)
        n = len(rows)

        if n <= 8:
            return rows

        if band == "top":
            return rows[: max(8, n // 3)]

        if band == "mid":
            start = max(0, n // 4)
            end = max(start + 8, n * 3 // 4)
            return rows[start:end]

        if band == "low":
            start = max(0, n // 2)
            return rows[start:]

        return rows

    @staticmethod
    def _transition_bonus(previous: dict[str, Any] | None, row: dict[str, Any]) -> float:
        if previous is None:
            return 0.0

        bonus = 0.0
        prev_video = str(previous.get("video_path", ""))
        cur_video = str(row.get("video_path", ""))
        prev_role = str(previous.get("story_role", ""))
        cur_role = str(row.get("story_role", ""))

        if prev_video == cur_video:
            bonus -= 18.0

        if prev_role != cur_role:
            bonus += 8.0
        else:
            bonus -= 4.0

        return bonus

    @staticmethod
    def _diversity_bonus(row: dict[str, Any], used_videos: dict[str, int]) -> float:
        video_path = str(row.get("video_path", ""))
        if video_path not in used_videos:
            return 7.0
        return -10.0 * used_videos.get(video_path, 0)

    @staticmethod
    def _retimeline(rows: list[dict[str, Any]]) -> None:
        cursor = 0.0
        for index, row in enumerate(rows, start=1):
            duration = float(row.get("duration_seconds", 0.0))
            row["order"] = index
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + duration, 3)
            cursor += duration

    @staticmethod
    def _identity(row: dict[str, Any]) -> tuple:
        return (
            str(row.get("video_path", "")),
            round(float(row.get("source_start_seconds", 0.0)), 3),
            round(float(row.get("source_end_seconds", 0.0)), 3),
        )

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

        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_summary(path: Path, pool: list[dict[str, Any]], selected: list[dict[str, Any]]) -> None:
        total = sum(float(r.get("duration_seconds", 0.0)) for r in selected)

        role_counts: dict[str, int] = {}
        section_counts: dict[str, int] = {}
        video_counts: dict[str, int] = {}

        for row in selected:
            role = str(row.get("story_role", "unknown"))
            section = str(row.get("story_section", "unknown"))
            video = str(row.get("video_filename", "unknown"))

            role_counts[role] = role_counts.get(role, 0) + 1
            section_counts[section] = section_counts.get(section, 0) + 1
            video_counts[video] = video_counts.get(video, 0) + 1

        lines = [
            "STT AI Editor - Story Timeline Strong Diversity Summary",
            "=" * 65,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Input pool: {len(pool)}",
            f"Selected: {len(selected)}",
            f"Total duration: {total:.2f}s",
            "",
            "Story roles:",
        ]

        for role, count in sorted(role_counts.items()):
            lines.append(f"- {role}: {count}")

        lines.append("")
        lines.append("Story sections:")

        for section, count in sorted(section_counts.items()):
            lines.append(f"- {section}: {count}")

        lines.append("")
        lines.append("Repeated source files:")

        repeated = {k: v for k, v in video_counts.items() if v > 1}
        if repeated:
            for name, count in sorted(repeated.items()):
                lines.append(f"- {name}: {count}")
        else:
            lines.append("- none")

        lines.append("")
        lines.append("Timeline:")

        for row in selected:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"[{row.get('story_section')}/{row.get('story_role')}/{row.get('story_band')}] "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s "
                f"story={float(row.get('story_score', 0.0)):.1f} "
                f"final={float(row.get('final_wedding_score', row.get('expansion_score', 0.0))):.1f}"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def build_story_timeline_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
    target_duration_seconds: float = 60.0,
    max_segments_per_video: int = 1,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    builder = StoryTimelineBuilder(
        project=project,
        input_json=input_json,
        config=StoryTimelineConfig(
            target_duration_seconds=target_duration_seconds,
            max_segments_per_video=max_segments_per_video,
        ),
    )

    return builder.build()
