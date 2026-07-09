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
    max_segments_per_video: int = 2
    output_prefix: str = "story_timeline"


class StoryTimelineBuilder:
    """Module 013: arrange selected candidates into a simple wedding-story timeline."""

    def __init__(self, project: STTProject, input_json: str | Path | None = None, config: StoryTimelineConfig | None = None) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.config = config or StoryTimelineConfig()

    def build(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Story input json not found: {self.input_json}")

        pool = json.loads(self.input_json.read_text(encoding="utf-8"))
        prepared = self._prepare(pool)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        story_json = out_dir / "roughcut_story.json"
        story_csv = out_dir / "roughcut_story.csv"
        plan_json = out_dir / "roughcut_plan.json"
        summary = out_dir / "story_timeline_summary.txt"

        print("STT AI Story Timeline Builder")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"Input candidates: {len(pool)}")
        print(f"Target duration: {self.config.target_duration_seconds}s")
        print(f"Output: {out_dir}")
        print("-" * 60)

        selected = self._build_story(prepared)
        self._retimeline(selected)

        story_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        plan_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(story_csv, selected)
        self._write_summary(summary, prepared, selected)

        total = sum(float(r.get("duration_seconds", 0.0)) for r in selected)
        print("STORY TIMELINE COMPLETE")
        print(f"Selected segments: {len(selected)}")
        print(f"Total duration: {total:.2f}s")
        print(f"Story JSON: {story_json}")
        print(f"Premiere-compatible plan: {plan_json}")
        print("-" * 60)

        return {
            "output_dir": str(out_dir),
            "story_json": str(story_json),
            "story_csv": str(story_csv),
            "roughcut_plan_json": str(plan_json),
            "summary": str(summary),
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
        for pat in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pat))
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan_people_composition.json"
        return candidates[0]

    def _prepare(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in rows:
            dur = self._num(row, "duration_seconds", 0.0)
            if dur <= 0:
                continue
            item = dict(row)
            item["story_role"] = self._role(item)
            item["story_score"] = round(self._score(item), 2)
            item["story_source"] = "module_013"
            out.append(item)
        out.sort(key=lambda r: (float(r.get("story_score", 0)), float(r.get("final_wedding_score", r.get("expansion_score", 0)))), reverse=True)
        return out

    def _role(self, row: dict[str, Any]) -> str:
        label = str(row.get("content_label", "")).lower()
        motion = self._num(row, "motion_score", 0.0)
        people_score = self._num(row, "people_score", 0.0)
        regions = self._num(row, "face_count", 0.0)
        subject = self._num(row, "subject_score", 0.0)

        if label in ("skin_people", "face_people", "wide_people") or people_score >= 38 or regions >= 1:
            return "people_action" if motion >= 52 else "people"
        if subject >= 55 or label == "possible_people_or_detail":
            return "motion_detail" if motion >= 50 else "detail"
        if motion >= 65:
            return "motion"
        return "detail"

    def _score(self, row: dict[str, Any]) -> float:
        final = self._num(row, "final_wedding_score", self._num(row, "expansion_score", self._num(row, "ai_keep_score", 0)))
        moment = self._num(row, "best_moment_score", 0.0)
        ai = self._num(row, "ai_keep_score", 0.0)
        beauty = self._num(row, "beauty_score", 0.0)
        motion = min(self._num(row, "motion_score", 0.0), 80.0)
        role = str(row.get("story_role", ""))
        score = final * 0.46 + moment * 0.22 + ai * 0.16 + beauty * 0.10 + motion * 0.06
        if role in ("people", "people_action"):
            score *= 1.08
        if role == "detail":
            score *= 0.96
        return max(0.0, min(100.0, score))

    def _build_story(self, pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sections = [
            ("opening", 8.0, ["detail", "motion_detail", "people"]),
            ("intro_people", 14.0, ["people", "people_action", "motion_detail"]),
            ("detail_break", 8.0, ["detail", "motion_detail", "people"]),
            ("main_people", 22.0, ["people_action", "people", "motion"]),
            ("closing", 8.0, ["people_action", "people", "motion_detail", "detail"]),
        ]

        selected: list[dict[str, Any]] = []
        used: set[tuple] = set()
        per_video: dict[str, int] = {}

        for name, sec, roles in sections:
            current = 0.0
            while current < sec:
                picked = self._pick(pool, roles, used, per_video, name, selected[-1] if selected else None)
                if picked is None:
                    break
                selected.append(picked)
                used.add(self._identity(picked))
                video = str(picked.get("video_path", ""))
                per_video[video] = per_video.get(video, 0) + 1
                current += float(picked.get("duration_seconds", 0.0))

        total = sum(float(r.get("duration_seconds", 0.0)) for r in selected)
        while total < self.config.target_duration_seconds:
            picked = self._pick(pool, ["people_action", "people", "motion_detail", "detail", "motion"], used, per_video, "fill", selected[-1] if selected else None)
            if picked is None:
                break
            selected.append(picked)
            used.add(self._identity(picked))
            video = str(picked.get("video_path", ""))
            per_video[video] = per_video.get(video, 0) + 1
            total += float(picked.get("duration_seconds", 0.0))

        trimmed: list[dict[str, Any]] = []
        total = 0.0
        for row in selected:
            trimmed.append(row)
            total += float(row.get("duration_seconds", 0.0))
            if total >= self.config.target_duration_seconds:
                break
        return trimmed

    def _pick(self, pool: list[dict[str, Any]], roles: list[str], used: set[tuple], per_video: dict[str, int], section: str, prev: dict[str, Any] | None) -> dict[str, Any] | None:
        best = None
        best_score = -999999.0
        role_set = set(roles)
        for relax in (False, True):
            for row in pool:
                if self._identity(row) in used:
                    continue
                if str(row.get("story_role", "")) not in role_set:
                    continue
                video = str(row.get("video_path", ""))
                if not relax and per_video.get(video, 0) >= self.config.max_segments_per_video:
                    continue
                score = float(row.get("story_score", 0.0)) + self._section_bonus(section, row) + self._transition_bonus(prev, row)
                if score > best_score:
                    best = dict(row)
                    best_score = score
            if best is not None:
                break
        if best is not None:
            best["story_section"] = section
            best["story_pick_score"] = round(best_score, 2)
        return best

    def _section_bonus(self, section: str, row: dict[str, Any]) -> float:
        role = str(row.get("story_role", ""))
        final = self._num(row, "final_wedding_score", self._num(row, "expansion_score", 0.0))
        motion = self._num(row, "motion_score", 0.0)
        b = 0.0
        if section == "opening" and role in ("detail", "motion_detail"):
            b += 8
        if section == "intro_people" and role in ("people", "people_action"):
            b += 8
        if section == "detail_break" and role in ("detail", "motion_detail"):
            b += 9
        if section == "main_people" and role == "people_action":
            b += 10
        if section == "main_people" and role == "people":
            b += 7
        if section == "closing" and role in ("people_action", "people"):
            b += 7
        if section in ("main_people", "closing") and motion >= 55:
            b += 3
        if section in ("opening", "closing") and final >= 55:
            b += 3
        return b

    @staticmethod
    def _transition_bonus(prev: dict[str, Any] | None, row: dict[str, Any]) -> float:
        if prev is None:
            return 0.0
        b = 0.0
        if str(prev.get("video_path", "")) == str(row.get("video_path", "")):
            b -= 6.0
        if str(prev.get("story_role", "")) != str(row.get("story_role", "")):
            b += 2.5
        else:
            b -= 1.0
        return b

    @staticmethod
    def _retimeline(rows: list[dict[str, Any]]) -> None:
        cursor = 0.0
        for i, row in enumerate(rows, start=1):
            dur = float(row.get("duration_seconds", 0.0))
            row["order"] = i
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + dur, 3)
            cursor += dur

    @staticmethod
    def _identity(row: dict[str, Any]) -> tuple:
        return (str(row.get("video_path", "")), round(float(row.get("source_start_seconds", 0.0)), 3), round(float(row.get("source_end_seconds", 0.0)), 3))

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
            for k in row.keys():
                if k not in keys:
                    keys.append(k)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_summary(path: Path, pool: list[dict[str, Any]], selected: list[dict[str, Any]]) -> None:
        total = sum(float(r.get("duration_seconds", 0.0)) for r in selected)
        role_counts: dict[str, int] = {}
        section_counts: dict[str, int] = {}
        for row in selected:
            role = str(row.get("story_role", "unknown"))
            section = str(row.get("story_section", "unknown"))
            role_counts[role] = role_counts.get(role, 0) + 1
            section_counts[section] = section_counts.get(section, 0) + 1
        avg = sum(float(r.get("story_score", 0.0)) for r in selected) / len(selected) if selected else 0.0
        lines = [
            "STT AI Editor - Story Timeline Summary",
            "=" * 55,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Input pool: {len(pool)}",
            f"Selected: {len(selected)}",
            f"Total duration: {total:.2f}s",
            f"Average story score: {avg:.2f}",
            "",
            "Story roles:",
        ]
        for role, count in sorted(role_counts.items()):
            lines.append(f"- {role}: {count}")
        lines += ["", "Story sections:"]
        for sec, count in sorted(section_counts.items()):
            lines.append(f"- {sec}: {count}")
        lines += ["", "Timeline:"]
        for row in selected:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"[{row.get('story_section')}/{row.get('story_role')}] "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-{float(row.get('source_end_seconds', 0.0)):.2f}s "
                f"story={float(row.get('story_score', 0.0)):.1f}"
            )
        path.write_text("\n".join(lines), encoding="utf-8")


def build_story_timeline_existing_project(project_root: str | Path, input_json: str | Path | None = None, target_duration_seconds: float = 60.0, max_segments_per_video: int = 2) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)
    builder = StoryTimelineBuilder(
        project=project,
        input_json=input_json,
        config=StoryTimelineConfig(target_duration_seconds=target_duration_seconds, max_segments_per_video=max_segments_per_video),
    )
    return builder.build()
