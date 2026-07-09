from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project import ProjectManager, STTProject


@dataclass
class FeedbackLearningConfig:
    output_prefix: str = "feedback_learning"
    learned_output_prefix: str = "learned_candidates"
    profile_filename: str = "stt_feedback_profile.json"
    target_duration_seconds: float = 60.0
    max_segments_per_video: int = 1


class FeedbackLearningEngine:
    # Module 032.
    # Learns from manual_selection.json:
    # - KEEP = user likes this kind of shot
    # - MAYBE = weak positive
    # - REJECT = user dislikes this kind of shot
    # - liked/star = extra positive
    #
    # It creates a small feedback profile:
    #   <project_root>/stt_feedback_profile.json
    #
    # Then it can apply learned_score to future candidates/timelines.

    def __init__(
        self,
        project: STTProject,
        config: FeedbackLearningConfig | None = None,
    ) -> None:
        self.project = project
        self.config = config or FeedbackLearningConfig()
        self.profile_path = self.project.root / self.config.profile_filename

    def learn(
        self,
        selection_json: str | Path | None = None,
        source_json: str | Path | None = None,
    ) -> dict[str, Any]:
        selection_path = Path(selection_json) if selection_json else self._find_latest_selection_json()
        if not selection_path.exists():
            raise FileNotFoundError(f"manual_selection.json not found: {selection_path}")

        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        selection_items = self._selection_items(selection)

        if source_json:
            source_path = Path(source_json)
        else:
            source_text = str(selection.get("source", "")).strip() if isinstance(selection, dict) else ""
            source_path = Path(source_text) if source_text else self._find_latest_source_json()

        source_rows: list[dict[str, Any]] = []
        if source_path.exists():
            source_rows = self._load_rows(source_path)

        source_by_key = {self._identity(row): row for row in source_rows}

        examples: list[dict[str, Any]] = []

        for item in selection_items:
            key = self._identity(item)
            source_row = source_by_key.get(key, {})
            merged = dict(source_row)
            merged.update(item)

            status = str(item.get("status", "unset")).lower()
            liked = bool(item.get("liked", False))

            if status not in {"keep", "maybe", "reject"} and not liked:
                continue

            merged["_feedback_weight"] = self._feedback_weight(status, liked)
            merged["_feedback_status"] = status
            merged["_feedback_liked"] = liked
            examples.append(merged)

        profile = self._build_profile(
            examples=examples,
            selection_path=selection_path,
            source_path=source_path if source_path.exists() else None,
        )

        self.profile_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        profile_copy = output_dir / "stt_feedback_profile.json"
        report_txt = output_dir / "feedback_learning_summary.txt"
        examples_csv = output_dir / "feedback_examples.csv"

        profile_copy.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_examples_csv(examples_csv, examples)
        self._write_profile_summary(report_txt, profile, examples)

        print("FEEDBACK LEARNING COMPLETE")
        print(f"Selection: {selection_path}")
        print(f"Source: {source_path if source_path.exists() else ''}")
        print(f"Examples used: {len(examples)}")
        print(f"Profile: {self.profile_path}")
        print(f"Output: {output_dir}")

        return {
            "output_dir": str(output_dir),
            "profile": str(self.profile_path),
            "profile_copy": str(profile_copy),
            "summary": str(report_txt),
            "examples_csv": str(examples_csv),
            "selection_json": str(selection_path),
            "source_json": str(source_path) if source_path.exists() else "",
            "examples_used": len(examples),
        }

    def apply(
        self,
        input_json: str | Path | None = None,
        target_duration_seconds: float | None = None,
        max_segments_per_video: int | None = None,
    ) -> dict[str, Any]:
        if not self.profile_path.exists():
            raise FileNotFoundError(
                f"Feedback profile not found: {self.profile_path}. Run feedback learning first."
            )

        profile = json.loads(self.profile_path.read_text(encoding="utf-8"))

        input_path = Path(input_json) if input_json else self._find_latest_apply_input_json()
        if not input_path.exists():
            raise FileNotFoundError(f"Input json not found: {input_path}")

        rows = self._load_rows(input_path)
        learned = [self._apply_score(row, profile) for row in rows]

        target_duration = float(target_duration_seconds or self.config.target_duration_seconds)
        max_per_video = int(max_segments_per_video or self.config.max_segments_per_video)

        selected = self._select_learned_timeline(
            learned,
            target_duration_seconds=target_duration,
            max_segments_per_video=max_per_video,
        )

        self._retimeline(selected)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.learned_output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        learned_json = output_dir / "roughcut_learned_candidates.json"
        roughcut_plan = output_dir / "roughcut_plan.json"
        learned_csv = output_dir / "roughcut_learned_candidates.csv"
        summary_txt = output_dir / "learned_candidates_summary.txt"

        learned_json.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        roughcut_plan.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_rows_csv(learned_csv, selected)
        self._write_apply_summary(summary_txt, profile, input_path, learned, selected)

        total_duration = sum(float(x.get("duration_seconds", 0.0)) for x in selected)

        print("FEEDBACK SCORE APPLIED")
        print(f"Input: {input_path}")
        print(f"Rows: {len(rows)}")
        print(f"Selected: {len(selected)}")
        print(f"Duration: {total_duration:.2f}s")
        print(f"Output: {output_dir}")

        return {
            "output_dir": str(output_dir),
            "learned_json": str(learned_json),
            "roughcut_plan_json": str(roughcut_plan),
            "learned_csv": str(learned_csv),
            "summary": str(summary_txt),
            "profile": str(self.profile_path),
            "input_json": str(input_path),
            "selected_count": len(selected),
            "duration_seconds": total_duration,
        }

    def _find_latest_selection_json(self) -> Path:
        candidates = []

        root_selection = self.project.root / "manual_selection.json"
        if root_selection.exists():
            candidates.append(root_selection)

        candidates.extend(self.project.paths.exports_dir.glob("**/manual_selection.json"))
        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if candidates:
            return candidates[0]

        return self.project.root / "manual_selection.json"

    def _find_latest_source_json(self) -> Path:
        patterns = [
            "duplicate_removed_*/roughcut_no_duplicates.json",
            "duplicate_removed_*/roughcut_plan.json",
            "learned_candidates_*/roughcut_learned_candidates.json",
            "story_timeline_v2_*/roughcut_story_v2.json",
            "story_timeline_v2_*/roughcut_plan.json",
            "wedding_scene_*/roughcut_wedding_scene.json",
            "wedding_scene_*/roughcut_plan.json",
            "expanded_candidates_*/roughcut_plan_people_composition.json",
            "expanded_candidates_*/roughcut_plan_best_moments.json",
            "final_roughcut_*/roughcut_final.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if candidates:
            return candidates[0]

        return self.project.paths.exports_dir / "roughcut_plan.json"

    def _find_latest_apply_input_json(self) -> Path:
        # Prefer large/candidate pool instead of final 1-shot manual file.
        patterns = [
            "wedding_scene_*/roughcut_wedding_scene.json",
            "wedding_scene_*/roughcut_plan.json",
            "expanded_candidates_*/roughcut_plan_people_composition.json",
            "expanded_candidates_*/roughcut_plan_best_moments.json",
            "story_timeline_v2_*/roughcut_story_v2.json",
            "duplicate_removed_*/roughcut_no_duplicates.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if candidates:
            return candidates[0]

        return self._find_latest_source_json()

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

    @staticmethod
    def _selection_items(selection: Any) -> list[dict[str, Any]]:
        if isinstance(selection, list):
            return [dict(x) for x in selection if isinstance(x, dict)]
        if isinstance(selection, dict) and isinstance(selection.get("items"), list):
            return [dict(x) for x in selection["items"] if isinstance(x, dict)]
        raise RuntimeError("Unsupported manual_selection.json format")

    @staticmethod
    def _feedback_weight(status: str, liked: bool) -> float:
        weight = 0.0

        if status == "keep":
            weight += 1.0
        elif status == "maybe":
            weight += 0.45
        elif status == "reject":
            weight -= 1.0

        if liked:
            weight += 0.45

        return weight

    def _build_profile(
        self,
        examples: list[dict[str, Any]],
        selection_path: Path,
        source_path: Path | None,
    ) -> dict[str, Any]:
        status_counts = {"keep": 0, "maybe": 0, "reject": 0, "unset": 0, "liked": 0}
        scene_stats: dict[str, dict[str, float]] = {}
        section_stats: dict[str, dict[str, float]] = {}
        filename_token_stats: dict[str, dict[str, float]] = {}
        score_stats: dict[str, dict[str, float]] = {}

        for row in examples:
            status = str(row.get("_feedback_status", "unset")).lower()
            liked = bool(row.get("_feedback_liked", False))
            weight = float(row.get("_feedback_weight", 0.0))

            status_counts[status] = status_counts.get(status, 0) + 1
            if liked:
                status_counts["liked"] += 1

            scene = str(row.get("wedding_scene") or row.get("scene") or row.get("content_label") or "unknown").lower()
            section = str(row.get("story_section") or row.get("section") or row.get("story_v2_bucket") or "unknown").lower()

            self._add_stat(scene_stats, scene, weight)
            self._add_stat(section_stats, section, weight)

            for token in self._filename_tokens(str(row.get("video_filename") or row.get("video_path") or "")):
                self._add_stat(filename_token_stats, token, weight)

            for key in [
                "ai_keep_score",
                "story_v2_score",
                "final_wedding_score",
                "expansion_score",
                "beauty_score",
                "motion_score",
                "wedding_scene_confidence",
            ]:
                if row.get(key) is not None:
                    self._add_score_stat(score_stats, key, self._num(row, key, 0.0), weight)

        profile = {
            "version": "032",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(self.project.root),
            "selection_json": str(selection_path),
            "source_json": str(source_path) if source_path else "",
            "status_counts": status_counts,
            "example_count": len(examples),
            "scene_weights": self._final_weights(scene_stats),
            "section_weights": self._final_weights(section_stats),
            "filename_token_weights": self._final_weights(filename_token_stats, min_count=2),
            "score_preferences": self._final_score_preferences(score_stats),
        }

        return profile

    @staticmethod
    def _add_stat(stats: dict[str, dict[str, float]], key: str, weight: float) -> None:
        if not key:
            key = "unknown"

        row = stats.setdefault(key, {"sum": 0.0, "count": 0.0, "pos": 0.0, "neg": 0.0})
        row["sum"] += weight
        row["count"] += 1
        if weight > 0:
            row["pos"] += weight
        elif weight < 0:
            row["neg"] += abs(weight)

    @staticmethod
    def _add_score_stat(stats: dict[str, dict[str, float]], key: str, value: float, weight: float) -> None:
        row = stats.setdefault(
            key,
            {
                "keep_sum": 0.0,
                "keep_count": 0.0,
                "reject_sum": 0.0,
                "reject_count": 0.0,
            },
        )

        if weight > 0:
            row["keep_sum"] += value * weight
            row["keep_count"] += weight
        elif weight < 0:
            row["reject_sum"] += value * abs(weight)
            row["reject_count"] += abs(weight)

    @staticmethod
    def _final_weights(stats: dict[str, dict[str, float]], min_count: int = 1) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}

        for key, row in stats.items():
            count = max(float(row.get("count", 0.0)), 1.0)
            if count < min_count:
                continue

            raw = float(row.get("sum", 0.0)) / count
            weight = max(-1.0, min(1.0, raw))

            out[key] = {
                "weight": round(weight, 4),
                "count": int(count),
                "positive": round(float(row.get("pos", 0.0)), 4),
                "negative": round(float(row.get("neg", 0.0)), 4),
            }

        return dict(sorted(out.items(), key=lambda kv: abs(kv[1]["weight"]), reverse=True))

    @staticmethod
    def _final_score_preferences(stats: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}

        for key, row in stats.items():
            keep_count = float(row.get("keep_count", 0.0))
            reject_count = float(row.get("reject_count", 0.0))

            keep_avg = float(row.get("keep_sum", 0.0)) / keep_count if keep_count > 0 else 0.0
            reject_avg = float(row.get("reject_sum", 0.0)) / reject_count if reject_count > 0 else 0.0

            out[key] = {
                "keep_avg": round(keep_avg, 4),
                "reject_avg": round(reject_avg, 4),
                "difference": round(keep_avg - reject_avg, 4),
                "keep_weight": round(keep_count, 4),
                "reject_weight": round(reject_count, 4),
            }

        return out

    @staticmethod
    def _filename_tokens(text: str) -> list[str]:
        name = Path(text).stem.lower()
        parts = re.split(r"[^a-z0-9]+", name)
        return [p for p in parts if len(p) >= 3 and not p.isdigit()]

    def _apply_score(self, row: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        item = dict(row)

        base = self._base_score(item)
        learned_bonus = 0.0
        reasons: list[str] = []

        scene = str(item.get("wedding_scene") or item.get("scene") or item.get("content_label") or "unknown").lower()
        section = str(item.get("story_section") or item.get("section") or item.get("story_v2_bucket") or "unknown").lower()

        scene_info = profile.get("scene_weights", {}).get(scene)
        if scene_info:
            w = float(scene_info.get("weight", 0.0))
            bonus = w * 18.0
            learned_bonus += bonus
            reasons.append(f"scene:{scene}:{bonus:+.1f}")

        section_info = profile.get("section_weights", {}).get(section)
        if section_info:
            w = float(section_info.get("weight", 0.0))
            bonus = w * 12.0
            learned_bonus += bonus
            reasons.append(f"section:{section}:{bonus:+.1f}")

        filename_text = str(item.get("video_filename") or item.get("video_path") or "")
        for token in self._filename_tokens(filename_text):
            token_info = profile.get("filename_token_weights", {}).get(token)
            if token_info:
                w = float(token_info.get("weight", 0.0))
                bonus = w * 4.0
                learned_bonus += bonus
                reasons.append(f"token:{token}:{bonus:+.1f}")

        # Specific rejected/kept segment memory.
        current_key = self._identity(item)
        selection_path = Path(str(profile.get("selection_json", "")))
        if selection_path.exists():
            try:
                selection = json.loads(selection_path.read_text(encoding="utf-8"))
                for sel in self._selection_items(selection):
                    if self._identity(sel) == current_key:
                        status = str(sel.get("status", "unset")).lower()
                        liked = bool(sel.get("liked", False))
                        if status == "reject":
                            learned_bonus -= 100.0
                            reasons.append("exact_previous_reject:-100")
                        elif status == "keep":
                            learned_bonus += 25.0
                            reasons.append("exact_previous_keep:+25")
                        if liked:
                            learned_bonus += 12.0
                            reasons.append("exact_previous_like:+12")
                        break
            except Exception:
                pass

        learned_score = max(0.0, min(100.0, base + learned_bonus))

        item["base_score_before_learning"] = round(base, 3)
        item["learned_bonus"] = round(learned_bonus, 3)
        item["learned_score"] = round(learned_score, 3)
        item["learned_reason"] = "; ".join(reasons)

        return item

    def _select_learned_timeline(
        self,
        rows: list[dict[str, Any]],
        target_duration_seconds: float,
        max_segments_per_video: int,
    ) -> list[dict[str, Any]]:
        candidates = sorted(
            rows,
            key=lambda r: (
                float(r.get("learned_score", 0.0)),
                float(r.get("base_score_before_learning", 0.0)),
            ),
            reverse=True,
        )

        selected: list[dict[str, Any]] = []
        per_video: dict[str, int] = {}
        total = 0.0

        for row in candidates:
            if total >= target_duration_seconds:
                break

            video_path = str(row.get("video_path", ""))
            if per_video.get(video_path, 0) >= max_segments_per_video:
                continue

            if float(row.get("learned_score", 0.0)) <= 0.0:
                continue

            selected.append(dict(row))
            per_video[video_path] = per_video.get(video_path, 0) + 1
            total += self._duration(row)

        # Keep final order story-like if present, otherwise by learned score.
        selected.sort(key=lambda r: int(float(r.get("order", 9999))))

        return selected

    @staticmethod
    def _base_score(row: dict[str, Any]) -> float:
        for key in [
            "story_v2_score",
            "final_wedding_score",
            "expansion_score",
            "ai_keep_score",
            "score",
        ]:
            if row.get(key) is not None:
                try:
                    return float(row.get(key))
                except Exception:
                    pass
        return 0.0

    @staticmethod
    def _duration(row: dict[str, Any]) -> float:
        duration = FeedbackLearningEngine._num(row, "duration_seconds", 0.0)
        if duration > 0:
            return duration

        start = FeedbackLearningEngine._num(row, "source_start_seconds", 0.0)
        end = FeedbackLearningEngine._num(row, "source_end_seconds", start)
        return max(0.0, end - start)

    @staticmethod
    def _retimeline(rows: list[dict[str, Any]]) -> None:
        cursor = 0.0

        for idx, row in enumerate(rows, start=1):
            start = FeedbackLearningEngine._num(row, "source_start_seconds", 0.0)
            end = FeedbackLearningEngine._num(row, "source_end_seconds", start)
            duration = FeedbackLearningEngine._duration(row)

            if end <= start and duration > 0:
                end = start + duration

            row["order"] = idx
            row["source_start_seconds"] = round(start, 3)
            row["source_end_seconds"] = round(end, 3)
            row["duration_seconds"] = round(duration, 3)
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + duration, 3)
            cursor += duration

    @staticmethod
    def _identity(row: dict[str, Any]) -> tuple:
        video_path = str(row.get("video_path", ""))
        start = FeedbackLearningEngine._num(row, "source_start_seconds", 0.0)
        end = FeedbackLearningEngine._num(row, "source_end_seconds", 0.0)
        return (video_path, round(start, 3), round(end, 3))

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
    def _write_examples_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        keys = [
            "_feedback_status",
            "_feedback_liked",
            "_feedback_weight",
            "video_filename",
            "video_path",
            "source_start_seconds",
            "source_end_seconds",
            "duration_seconds",
            "wedding_scene",
            "story_section",
            "scene",
            "section",
            "ai_keep_score",
            "story_v2_score",
            "final_wedding_score",
            "expansion_score",
            "beauty_score",
            "motion_score",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in keys})

    @staticmethod
    def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return

        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys and not key.startswith("_"):
                    keys.append(key)

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in keys})

    @staticmethod
    def _write_profile_summary(path: Path, profile: dict[str, Any], examples: list[dict[str, Any]]) -> None:
        lines = [
            "STT AI Editor - Feedback Learning Summary",
            "=" * 65,
            f"Created: {profile.get('created_at')}",
            f"Examples used: {len(examples)}",
            "",
            "Status counts:",
        ]

        for key, value in profile.get("status_counts", {}).items():
            lines.append(f"- {key}: {value}")

        lines.append("")
        lines.append("Scene weights:")
        for key, value in profile.get("scene_weights", {}).items():
            lines.append(f"- {key}: {value}")

        lines.append("")
        lines.append("Section weights:")
        for key, value in profile.get("section_weights", {}).items():
            lines.append(f"- {key}: {value}")

        lines.append("")
        lines.append("Profile file:")
        lines.append(str(profile.get("project_root", "")))

        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _write_apply_summary(
        path: Path,
        profile: dict[str, Any],
        input_path: Path,
        learned: list[dict[str, Any]],
        selected: list[dict[str, Any]],
    ) -> None:
        total = sum(float(x.get("duration_seconds", 0.0)) for x in selected)

        lines = [
            "STT AI Editor - Learned Candidates Summary",
            "=" * 65,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Input: {input_path}",
            f"Rows scored: {len(learned)}",
            f"Selected: {len(selected)}",
            f"Total duration: {total:.2f}s",
            "",
            "Selected timeline:",
        ]

        for row in selected:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s "
                f"learned={float(row.get('learned_score', 0.0)):.1f} "
                f"bonus={float(row.get('learned_bonus', 0.0)):+.1f} "
                f"{row.get('learned_reason', '')}"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def learn_feedback_existing_project(
    project_root: str | Path,
    selection_json: str | Path | None = None,
    source_json: str | Path | None = None,
) -> dict[str, Any]:
    project = ProjectManager().open_project(project_root)
    return FeedbackLearningEngine(project).learn(selection_json=selection_json, source_json=source_json)


def apply_feedback_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
    target_duration_seconds: float = 60.0,
    max_segments_per_video: int = 1,
) -> dict[str, Any]:
    project = ProjectManager().open_project(project_root)
    return FeedbackLearningEngine(project).apply(
        input_json=input_json,
        target_duration_seconds=target_duration_seconds,
        max_segments_per_video=max_segments_per_video,
    )
