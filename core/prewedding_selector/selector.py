
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


PREWEDDING_TARGETS: dict[str, dict[str, Any]] = {
    "prewedding_reel_30s": {
        "label": "Prewedding Reel 30s",
        "target_duration": 30.0,
        "default_clip_duration": 2.2,
        "min_score": 58.0,
        "max_per_source_file": 2,
        "max_static_in_row": 1,
        "aspect": "9:16",
        "opening_keywords": ["hook", "best_shot", "fashion", "motion", "dress", "walking", "close"],
        "section_plan": [
            {"name": "hook", "target": 3.0, "prefer": ["hook", "best_shot", "fashion", "motion"]},
            {"name": "couple_motion", "target": 9.0, "prefer": ["couple", "walking", "holding_hands", "dress_motion"]},
            {"name": "fashion_location", "target": 9.0, "prefer": ["fashion", "pose", "location", "wide"]},
            {"name": "emotion_end", "target": 9.0, "prefer": ["close_up", "emotion", "look_at_each_other", "strong_end"]},
        ],
    },
    "prewedding_reel_60s": {
        "label": "Prewedding Reel 60s",
        "target_duration": 60.0,
        "default_clip_duration": 2.8,
        "min_score": 55.0,
        "max_per_source_file": 3,
        "max_static_in_row": 1,
        "aspect": "9:16",
        "opening_keywords": ["hook", "best_shot", "fashion", "motion", "dress", "walking", "close"],
        "section_plan": [
            {"name": "hook", "target": 4.0, "prefer": ["hook", "best_shot", "motion"]},
            {"name": "couple_story", "target": 16.0, "prefer": ["couple", "walking", "holding_hands", "look_at_each_other"]},
            {"name": "fashion_motion", "target": 14.0, "prefer": ["fashion", "pose", "dress_motion", "spin"]},
            {"name": "location_beauty", "target": 14.0, "prefer": ["location", "wide", "sunset", "beach", "forest", "city"]},
            {"name": "romantic_end", "target": 12.0, "prefer": ["close_up", "hug", "kiss", "emotion", "strong_end"]},
        ],
    },
    "prewedding_cinematic": {
        "label": "Prewedding Cinematic",
        "target_duration": 120.0,
        "default_clip_duration": 4.0,
        "min_score": 52.0,
        "max_per_source_file": 4,
        "max_static_in_row": 2,
        "aspect": "16:9",
        "opening_keywords": ["location", "wide", "couple", "walking", "sunset", "slow_motion"],
        "section_plan": [
            {"name": "location_hook", "target": 14.0, "prefer": ["location", "wide", "sunset", "beautiful_light"]},
            {"name": "couple_walk", "target": 26.0, "prefer": ["couple", "walking", "holding_hands"]},
            {"name": "emotion_closeup", "target": 24.0, "prefer": ["close_up", "emotion", "look_at_each_other", "hug"]},
            {"name": "dress_motion", "target": 20.0, "prefer": ["dress_motion", "spin", "slow_motion"]},
            {"name": "location_beauty", "target": 22.0, "prefer": ["location", "wide", "landscape", "architecture"]},
            {"name": "romantic_end", "target": 14.0, "prefer": ["kiss", "hug", "walking", "wide_end"]},
        ],
    },
    "prewedding_fashion": {
        "label": "Prewedding Fashion",
        "target_duration": 45.0,
        "default_clip_duration": 2.5,
        "min_score": 55.0,
        "max_per_source_file": 3,
        "max_static_in_row": 1,
        "aspect": "9:16",
        "opening_keywords": ["fashion", "pose", "look_at_camera", "dress", "motion"],
        "section_plan": [
            {"name": "fashion_hook", "target": 5.0, "prefer": ["fashion", "pose", "look_at_camera"]},
            {"name": "pose_series", "target": 15.0, "prefer": ["pose", "fashion", "medium_shot"]},
            {"name": "walk_motion", "target": 10.0, "prefer": ["walking", "dress_motion", "spin"]},
            {"name": "closeup_detail", "target": 8.0, "prefer": ["close_up", "makeup", "detail"]},
            {"name": "signature_end", "target": 7.0, "prefer": ["strong_end", "look_at_camera", "dress"]},
        ],
    },
    "prewedding_location_film": {
        "label": "Prewedding Location Film",
        "target_duration": 90.0,
        "default_clip_duration": 4.0,
        "min_score": 52.0,
        "max_per_source_file": 4,
        "max_static_in_row": 2,
        "aspect": "16:9",
        "opening_keywords": ["wide", "location", "landscape", "sunset", "beach", "forest", "city"],
        "section_plan": [
            {"name": "wide_location", "target": 18.0, "prefer": ["wide", "location", "landscape"]},
            {"name": "couple_enters", "target": 18.0, "prefer": ["couple", "walking", "holding_hands"]},
            {"name": "location_motion", "target": 22.0, "prefer": ["stable_motion", "drone_like", "architecture", "city"]},
            {"name": "couple_closeup", "target": 18.0, "prefer": ["close_up", "emotion", "look_at_each_other"]},
            {"name": "wide_end", "target": 14.0, "prefer": ["wide_end", "sunset", "wide", "location"]},
        ],
    },
}


@dataclass
class PreweddingSelectorConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    intent: str = "prewedding_reel_60s"
    target_duration: float | None = None
    open_folder: bool = True


class PreweddingLearnedSelector:
    # Module 047.
    #
    # Uses Module 046 scored shots to build a rough prewedding/reel selection.
    # Output is a timeline-style JSON/CSV/report for upcoming XML builder modules.
    #
    # This module starts the real "AI chooses shots" step for prewedding.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()

        self.score_path = self.project_root / "stt_ai_shot_scores_v1.json"
        self.appdata_score_path = self.appdata_dir / "stt_ai_shot_scores_v1.json"

        self.memory_path = self.project_root / "stt_ai_style_memory_v2.json"
        self.style_profile_path = self.project_root / "stt_wedding_style_profile.json"

        self.project_selection_path = self.project_root / "stt_prewedding_selection_v1.json"
        self.appdata_selection_path = self.appdata_dir / "stt_prewedding_selection_v1.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    def build(
        self,
        intent: str = "prewedding_reel_60s",
        target_duration: float | None = None,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        if intent not in PREWEDDING_TARGETS:
            raise ValueError(
                f"Unknown prewedding intent: {intent}. Available: {', '.join(sorted(PREWEDDING_TARGETS))}"
            )

        score_data = self.load_or_generate_scores(intent=intent)
        candidates = self.extract_scored_items(score_data)

        if not candidates:
            raise RuntimeError(
                "Không có scored_items để chọn shot.\n"
                "Hãy chạy trước: python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s"
            )

        target = dict(PREWEDDING_TARGETS[intent])
        if target_duration is not None:
            target["target_duration"] = float(target_duration)

        selected_timeline = self.select_timeline(candidates, target, intent)
        selection = self.build_selection_document(score_data, selected_timeline, target, intent)

        self.project_root.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.appdata_dir.mkdir(parents=True, exist_ok=True)

        self.project_selection_path.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")
        self.appdata_selection_path.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")

        report_dir = self.exports_dir / f"prewedding_selector_v1_{intent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_json = report_dir / "stt_prewedding_selection_v1.json"
        timeline_csv = report_dir / "PREWEDDING_TIMELINE.csv"
        selected_csv = report_dir / "PREWEDDING_SELECTED_SHOTS.csv"
        report_txt = report_dir / "PREWEDDING_SELECTOR_SUMMARY.txt"
        report_html = report_dir / "PREWEDDING_SELECTOR_SUMMARY.html"
        prompt_txt = report_dir / "PREWEDDING_EDIT_PROMPT.txt"

        report_json.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")
        self.write_timeline_csv(timeline_csv, selected_timeline)
        self.write_selected_csv(selected_csv, selected_timeline)
        report_txt.write_text(self.render_text(selection), encoding="utf-8")
        report_html.write_text(self.render_html(selection), encoding="utf-8")
        prompt_txt.write_text(selection["edit_prompt"], encoding="utf-8")

        result = {
            "ok": True,
            "intent": intent,
            "label": target.get("label"),
            "target_duration": selection["target_duration_seconds"],
            "actual_duration": selection["actual_duration_seconds"],
            "selected_count": selection["selected_count"],
            "project_selection": str(self.project_selection_path),
            "appdata_selection": str(self.appdata_selection_path),
            "report_dir": str(report_dir),
            "report_json": str(report_json),
            "timeline_csv": str(timeline_csv),
            "selected_csv": str(selected_csv),
            "report_txt": str(report_txt),
            "report_html": str(report_html),
            "prompt_txt": str(prompt_txt),
        }

        (report_dir / "prewedding_selector_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(report_dir)
            except Exception:
                pass

        return result

    def load_or_generate_scores(self, intent: str) -> dict[str, Any]:
        score_data = self.load_json_first([self.score_path, self.appdata_score_path])

        if score_data and score_data.get("intent") == intent and score_data.get("scored_items"):
            return score_data

        # Try latest score export matching this intent.
        latest = self.find_latest_score_export(intent)
        if latest:
            score_data = self.load_json(latest)
            if score_data.get("scored_items"):
                return score_data

        # Auto-run Module 046 if available.
        try:
            from core.ai_shot_scorer import run_ai_shot_scorer

            run_ai_shot_scorer(
                project_root=self.project_root,
                intent=intent,
                top_n=180,
                open_folder=False,
            )
            score_data = self.load_json_first([self.score_path, self.appdata_score_path])
            if score_data.get("scored_items"):
                return score_data
        except Exception:
            pass

        return score_data or {}

    def find_latest_score_export(self, intent: str) -> Path | None:
        if not self.exports_dir.exists():
            return None

        files = [
            p for p in self.exports_dir.glob("**/stt_ai_shot_scores_v1.json")
            if p.is_file()
            and "_archive" not in p.parts
            and intent in str(p.parent)
        ]

        if not files:
            files = [
                p for p in self.exports_dir.glob("**/stt_ai_shot_scores_v1.json")
                if p.is_file() and "_archive" not in p.parts
            ]

        if files:
            return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        return None

    @staticmethod
    def load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"_error": repr(exc), "_path": str(path)}

    def load_json_first(self, paths: list[Path]) -> dict[str, Any]:
        for path in paths:
            data = self.load_json(path)
            if data and "_error" not in data:
                return data
        return {}

    @staticmethod
    def extract_scored_items(score_data: dict[str, Any]) -> list[dict[str, Any]]:
        for key in ["scored_items", "selected_items", "items", "candidates"]:
            value = score_data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return []

    def select_timeline(
        self,
        candidates: list[dict[str, Any]],
        target: dict[str, Any],
        intent: str,
    ) -> list[dict[str, Any]]:
        target_duration = float(target["target_duration"])
        default_clip_duration = float(target["default_clip_duration"])
        min_score = float(target["min_score"])
        max_per_source_file = int(target["max_per_source_file"])

        usable = [
            dict(x)
            for x in candidates
            if float(x.get("ai_score", 0) or 0) >= min_score
            and str(x.get("ai_rank_hint", "")).lower() not in {"e_reject"}
        ]

        if not usable:
            usable = sorted(candidates, key=lambda x: float(x.get("ai_score", 0) or 0), reverse=True)[:60]

        usable = sorted(usable, key=lambda x: float(x.get("ai_score", 0) or 0), reverse=True)

        selected: list[dict[str, Any]] = []
        used_ids: set[str] = set()
        source_counts: dict[str, int] = {}
        current_time = 0.0

        # Pick opening first.
        opening = self.pick_opening(usable, target)
        if opening:
            clip = self.make_timeline_clip(opening, current_time, default_clip_duration, "hook")
            selected.append(clip)
            used_ids.add(self.item_id(opening))
            source_counts[self.source_key(opening)] = source_counts.get(self.source_key(opening), 0) + 1
            current_time += clip["timeline_duration"]

        # Fill by section plan.
        for section in target.get("section_plan", []):
            section_name = str(section.get("name", "section"))
            section_target = float(section.get("target", 10.0))
            prefer = section.get("prefer", [])

            if section_name == "hook" and selected:
                continue

            section_start_duration = current_time

            ranked = self.rank_for_section(usable, prefer)

            for item in ranked:
                if current_time >= target_duration:
                    break

                if current_time - section_start_duration >= section_target:
                    break

                item_key = self.item_id(item)
                if item_key in used_ids:
                    continue

                src = self.source_key(item)
                if source_counts.get(src, 0) >= max_per_source_file:
                    continue

                if self.too_similar_to_previous(item, selected):
                    continue

                clip = self.make_timeline_clip(item, current_time, default_clip_duration, section_name)

                if current_time + clip["timeline_duration"] > target_duration + 1.0:
                    remaining = target_duration - current_time
                    if remaining >= 1.0:
                        clip["timeline_duration"] = round(remaining, 3)
                    else:
                        continue

                selected.append(clip)
                used_ids.add(item_key)
                source_counts[src] = source_counts.get(src, 0) + 1
                current_time += clip["timeline_duration"]

        # If still short, fill with best remaining.
        for item in usable:
            if current_time >= target_duration:
                break

            item_key = self.item_id(item)
            if item_key in used_ids:
                continue

            src = self.source_key(item)
            if source_counts.get(src, 0) >= max_per_source_file + 1:
                continue

            if self.too_similar_to_previous(item, selected):
                continue

            clip = self.make_timeline_clip(item, current_time, default_clip_duration, "fill_best")
            if current_time + clip["timeline_duration"] > target_duration + 1.0:
                remaining = target_duration - current_time
                if remaining >= 1.0:
                    clip["timeline_duration"] = round(remaining, 3)
                else:
                    continue

            selected.append(clip)
            used_ids.add(item_key)
            source_counts[src] = source_counts.get(src, 0) + 1
            current_time += clip["timeline_duration"]

        # Recalculate timeline start/end exactly.
        cursor = 0.0
        for idx, clip in enumerate(selected, start=1):
            clip["timeline_index"] = idx
            clip["timeline_start"] = round(cursor, 3)
            cursor += float(clip["timeline_duration"])
            clip["timeline_end"] = round(cursor, 3)

        return selected

    def pick_opening(self, usable: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any] | None:
        opening_keywords = target.get("opening_keywords", [])
        best = None
        best_score = -1.0

        for item in usable[:80]:
            text = self.item_text(item)
            score = float(item.get("ai_score", 0) or 0)

            for kw in opening_keywords:
                if self.keyword_match(text, str(kw)):
                    score += 12
                    break

            # Manual like/keep makes a good hook.
            if item.get("_liked") or "liked_by_user" in item.get("ai_reasons", []):
                score += 8

            if score > best_score:
                best = item
                best_score = score

        return best

    @staticmethod
    def rank_for_section(usable: list[dict[str, Any]], prefer: list[str]) -> list[dict[str, Any]]:
        ranked = []

        for item in usable:
            text = PreweddingLearnedSelector.item_text(item)
            score = float(item.get("ai_score", 0) or 0)

            for kw in prefer:
                if PreweddingLearnedSelector.keyword_match(text, str(kw)):
                    score += 10

            # Prefer already-explained AI reasons.
            reasons = " ".join(str(x) for x in item.get("ai_reasons", [])).lower()
            for kw in prefer:
                if PreweddingLearnedSelector.keyword_match(reasons, str(kw)):
                    score += 5

            ranked.append((score, item))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in ranked]

    @staticmethod
    def make_timeline_clip(
        item: dict[str, Any],
        timeline_start: float,
        default_clip_duration: float,
        section: str,
    ) -> dict[str, Any]:
        duration = PreweddingLearnedSelector.item_duration(item)

        if duration is None or duration <= 0:
            timeline_duration = default_clip_duration
        else:
            # Use short pieces for reel, but don't exceed source segment.
            timeline_duration = min(duration, default_clip_duration)
            if timeline_duration < 1.0:
                timeline_duration = min(duration, 1.0)

        source_start = PreweddingLearnedSelector.item_start(item)
        source_end = source_start + timeline_duration

        return {
            "timeline_index": 0,
            "section": section,
            "timeline_start": round(timeline_start, 3),
            "timeline_end": round(timeline_start + timeline_duration, 3),
            "timeline_duration": round(timeline_duration, 3),
            "source_start": round(source_start, 3),
            "source_end": round(source_end, 3),
            "source_duration": duration,
            "file": item.get("_filename") or item.get("file") or item.get("filename") or item.get("path") or "",
            "source_key": PreweddingLearnedSelector.source_key(item),
            "ai_score": float(item.get("ai_score", 0) or 0),
            "ai_rank_hint": item.get("ai_rank_hint", ""),
            "ai_reasons": item.get("ai_reasons", []),
            "ai_penalties": item.get("ai_penalties", []),
            "manual_status": item.get("_status") or item.get("status") or "",
            "liked": bool(item.get("_liked") or item.get("liked")),
            "raw_item": item,
        }

    @staticmethod
    def item_text(item: dict[str, Any]) -> str:
        parts = []
        for key in [
            "_search_text",
            "_filename",
            "file",
            "filename",
            "path",
            "scene",
            "scene_type",
            "wedding_scene",
            "category",
            "tag",
            "tags",
            "note",
            "ai_reasons",
        ]:
            value = item.get(key)
            if isinstance(value, list):
                parts.extend(str(x) for x in value)
            elif value is not None:
                parts.append(str(value))
        return " ".join(parts).lower()

    @staticmethod
    def keyword_match(text: str, keyword: str) -> bool:
        kw = keyword.lower().strip()
        variants = {
            kw,
            kw.replace("_", " "),
            kw.replace("-", " "),
        }
        return any(v and v in text for v in variants)

    @staticmethod
    def item_id(item: dict[str, Any]) -> str:
        file_value = str(item.get("_filename") or item.get("file") or item.get("filename") or item.get("path") or "")
        start = str(item.get("start") or item.get("source_start") or item.get("start_sec") or item.get("in") or "")
        end = str(item.get("end") or item.get("source_end") or item.get("end_sec") or item.get("out") or "")
        seg = str(item.get("segment_id") or item.get("id") or "")
        return f"{file_value}|{start}|{end}|{seg}"

    @staticmethod
    def source_key(item: dict[str, Any]) -> str:
        file_value = str(item.get("_filename") or item.get("file") or item.get("filename") or item.get("path") or "")
        if not file_value:
            return "unknown"
        try:
            return Path(file_value).name.lower()
        except Exception:
            return file_value.lower()

    @staticmethod
    def item_start(item: dict[str, Any]) -> float:
        for key in ["start", "source_start", "start_sec", "start_seconds", "in", "in_sec"]:
            if key in item:
                try:
                    return max(0.0, float(item[key]))
                except Exception:
                    pass
        return 0.0

    @staticmethod
    def item_duration(item: dict[str, Any]) -> float | None:
        for key in ["ai_duration_seconds", "_duration", "duration", "duration_sec", "duration_seconds", "length"]:
            if key in item and item[key] is not None:
                try:
                    return max(0.0, float(item[key]))
                except Exception:
                    pass

        start = None
        end = None

        for key in ["start", "source_start", "start_sec", "start_seconds", "in", "in_sec"]:
            if key in item:
                try:
                    start = float(item[key])
                    break
                except Exception:
                    pass

        for key in ["end", "source_end", "end_sec", "end_seconds", "out", "out_sec"]:
            if key in item:
                try:
                    end = float(item[key])
                    break
                except Exception:
                    pass

        if start is not None and end is not None and end > start:
            return end - start

        return None

    @staticmethod
    def too_similar_to_previous(item: dict[str, Any], selected: list[dict[str, Any]]) -> bool:
        if not selected:
            return False

        prev = selected[-1]
        this_src = PreweddingLearnedSelector.source_key(item)
        prev_src = str(prev.get("source_key", ""))

        if this_src and this_src == prev_src:
            return True

        this_text = set(PreweddingLearnedSelector.item_text(item).split())
        prev_text = set(str(prev.get("file", "") + " " + " ".join(prev.get("ai_reasons", []))).lower().split())

        if not this_text or not prev_text:
            return False

        overlap = len(this_text & prev_text)
        if overlap >= 8:
            return True

        return False

    def build_selection_document(
        self,
        score_data: dict[str, Any],
        timeline: list[dict[str, Any]],
        target: dict[str, Any],
        intent: str,
    ) -> dict[str, Any]:
        actual_duration = round(sum(float(x.get("timeline_duration", 0)) for x in timeline), 3)
        now = datetime.now().isoformat(timespec="seconds")

        return {
            "ok": True,
            "module": "047_prewedding_learned_selector",
            "version": "0.47",
            "created_at": now,
            "updated_at": now,
            "project_root": str(self.project_root),
            "intent": intent,
            "label": target.get("label"),
            "aspect": target.get("aspect"),
            "target_duration_seconds": float(target.get("target_duration", 0)),
            "actual_duration_seconds": actual_duration,
            "selected_count": len(timeline),
            "source_score_intent": score_data.get("intent"),
            "score_summary": score_data.get("summary", {}),
            "selection_rules": {
                "min_score": target.get("min_score"),
                "default_clip_duration": target.get("default_clip_duration"),
                "max_per_source_file": target.get("max_per_source_file"),
                "section_plan": target.get("section_plan"),
            },
            "timeline": timeline,
            "manual_review_items": self.to_manual_review_items(timeline),
            "edit_prompt": self.build_edit_prompt(intent, target, timeline),
            "next_steps": [
                "Module 048 sẽ dùng timeline này để tạo roughcut prewedding/reel rõ hơn.",
                "Module 049 sẽ xuất XML 9:16/16:9 tối ưu cho Premiere.",
                "Mở PREWEDDING_SELECTOR_SUMMARY.html để xem shot đã chọn.",
            ],
        }

    @staticmethod
    def to_manual_review_items(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items = []
        for clip in timeline:
            items.append({
                "status": "keep",
                "liked": bool(clip.get("liked")),
                "file": clip.get("file"),
                "start": clip.get("source_start"),
                "end": clip.get("source_end"),
                "duration": clip.get("timeline_duration"),
                "section": clip.get("section"),
                "ai_score": clip.get("ai_score"),
                "note": f"Module047 selected for {clip.get('section')}",
            })
        return items

    @staticmethod
    def build_edit_prompt(intent: str, target: dict[str, Any], timeline: list[dict[str, Any]]) -> str:
        lines = [
            "STT AI Editor - Prewedding Edit Prompt",
            "=" * 72,
            f"Intent: {intent}",
            f"Label: {target.get('label')}",
            f"Aspect: {target.get('aspect')}",
            f"Target duration: {target.get('target_duration')}s",
            "",
            "Dựng theo hướng:",
        ]

        if "reel" in intent:
            lines += [
                "- Reel prewedding 9:16.",
                "- Hook 1-3 giây đầu phải đẹp.",
                "- Cut nhanh theo beat.",
                "- Ưu tiên couple, pose, motion, váy bay, close-up, location đẹp.",
                "- Không kể chuyện dài như wedding highlight.",
            ]
        else:
            lines += [
                "- Prewedding cinematic.",
                "- Smooth, romantic, location đẹp.",
                "- Ưu tiên couple walking / nắm tay / nhìn nhau / close-up / wide location.",
                "- Ít nghi lễ, không reception, không gia tiên.",
            ]

        lines += ["", "Timeline sections:"]
        for clip in timeline:
            lines.append(
                f"- {clip.get('timeline_start')}s-{clip.get('timeline_end')}s | "
                f"{clip.get('section')} | score {clip.get('ai_score')} | {clip.get('file')}"
            )

        return "\n".join(lines)

    @staticmethod
    def write_timeline_csv(path: Path, timeline: list[dict[str, Any]]) -> None:
        fieldnames = [
            "timeline_index",
            "section",
            "timeline_start",
            "timeline_end",
            "timeline_duration",
            "source_start",
            "source_end",
            "file",
            "ai_score",
            "ai_rank_hint",
            "liked",
            "manual_status",
            "ai_reasons",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for clip in timeline:
                row = {}
                for key in fieldnames:
                    value = clip.get(key, "")
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value, ensure_ascii=False)
                    row[key] = value
                writer.writerow(row)

    @staticmethod
    def write_selected_csv(path: Path, timeline: list[dict[str, Any]]) -> None:
        PreweddingLearnedSelector.write_timeline_csv(path, timeline)

    @staticmethod
    def render_text(selection: dict[str, Any]) -> str:
        lines = [
            "STT AI Editor - Prewedding Learned Selector",
            "=" * 72,
            f"Intent: {selection.get('intent')}",
            f"Label: {selection.get('label')}",
            f"Aspect: {selection.get('aspect')}",
            f"Target: {selection.get('target_duration_seconds')}s",
            f"Actual: {selection.get('actual_duration_seconds')}s",
            f"Selected: {selection.get('selected_count')}",
            "",
            "Timeline:",
        ]

        for clip in selection.get("timeline", []):
            lines.append(
                f"{clip.get('timeline_index'):>3}. "
                f"{clip.get('timeline_start')} - {clip.get('timeline_end')} | "
                f"{clip.get('section')} | "
                f"{clip.get('ai_score')} | "
                f"{clip.get('file')}"
            )

        return "\n".join(lines)

    @staticmethod
    def render_html(selection: dict[str, Any]) -> str:
        import html

        intent = html.escape(str(selection.get("intent", "")))
        label = html.escape(str(selection.get("label", "")))
        aspect = html.escape(str(selection.get("aspect", "")))
        target = html.escape(str(selection.get("target_duration_seconds", "")))
        actual = html.escape(str(selection.get("actual_duration_seconds", "")))
        selected = html.escape(str(selection.get("selected_count", "")))

        rows = []
        for clip in selection.get("timeline", []):
            reasons = ", ".join(str(x) for x in clip.get("ai_reasons", [])[:5])
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(clip.get('timeline_index', '')))}</td>"
                f"<td>{html.escape(str(clip.get('timeline_start', '')))} - {html.escape(str(clip.get('timeline_end', '')))}</td>"
                f"<td>{html.escape(str(clip.get('section', '')))}</td>"
                f"<td>{html.escape(str(clip.get('ai_score', '')))}</td>"
                f"<td>{html.escape(str(clip.get('file', '')))}</td>"
                f"<td>{html.escape(reasons)}</td>"
                "</tr>"
            )

        if not rows:
            rows.append("<tr><td colspan='6'>No selected shots</td></tr>")

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT Prewedding Learned Selector</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1300px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid #333; padding: 8px; vertical-align: top; }}
th {{ text-align: left; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 047</div>
  <h1>Prewedding Learned Selector</h1>
  <p>Intent: <b>{intent}</b> / {label}</p>
  <p>Aspect: {aspect} | Target: {target}s | Actual: {actual}s | Selected: {selected}</p>

  <h2>Timeline</h2>
  <table>
    <tr><th>#</th><th>Time</th><th>Section</th><th>Score</th><th>File</th><th>Reasons</th></tr>
    {''.join(rows)}
  </table>
</div>
</body>
</html>
'''


def build_prewedding_selection(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str = "prewedding_reel_60s",
    target_duration: float | None = None,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PreweddingLearnedSelector(project_root=project_root).build(
        intent=intent,
        target_duration=target_duration,
        open_folder=open_folder,
    )
