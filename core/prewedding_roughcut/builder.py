
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


ROUGHCUT_RULES: dict[str, dict[str, Any]] = {
    "prewedding_reel_30s": {
        "label": "Prewedding Reel 30s Roughcut",
        "target_duration": 30.0,
        "aspect": "9:16",
        "min_clip": 1.0,
        "max_clip": 2.8,
        "default_clip": 2.0,
        "pace": "fast_hook_beat_cut",
        "hook_seconds": 3.0,
        "transition_style": "quick_cut_soft_whoosh",
        "crop_hint": "vertical_center_couple",
        "music_hint": "fast romantic reel / beat cut",
        "sections": ["hook", "couple_motion", "fashion_location", "emotion_end"],
    },
    "prewedding_reel_60s": {
        "label": "Prewedding Reel 60s Roughcut",
        "target_duration": 60.0,
        "aspect": "9:16",
        "min_clip": 1.2,
        "max_clip": 3.5,
        "default_clip": 2.6,
        "pace": "fast_but_emotional",
        "hook_seconds": 4.0,
        "transition_style": "beat_cut_soft_whoosh",
        "crop_hint": "vertical_center_couple",
        "music_hint": "emotional build with beat",
        "sections": ["hook", "couple_story", "fashion_motion", "location_beauty", "romantic_end"],
    },
    "prewedding_cinematic": {
        "label": "Prewedding Cinematic Roughcut",
        "target_duration": 120.0,
        "aspect": "16:9",
        "min_clip": 2.0,
        "max_clip": 6.0,
        "default_clip": 4.0,
        "pace": "smooth_cinematic",
        "hook_seconds": 8.0,
        "transition_style": "clean_cut_slow_push",
        "crop_hint": "keep_original_16x9",
        "music_hint": "cinematic ambient piano/violin",
        "sections": ["location_hook", "couple_walk", "emotion_closeup", "dress_motion", "location_beauty", "romantic_end"],
    },
    "prewedding_fashion": {
        "label": "Prewedding Fashion Roughcut",
        "target_duration": 45.0,
        "aspect": "9:16",
        "min_clip": 1.0,
        "max_clip": 3.0,
        "default_clip": 2.3,
        "pace": "fashion_clean_beat",
        "hook_seconds": 4.0,
        "transition_style": "sharp_cut_light_hit",
        "crop_hint": "vertical_full_body_or_face",
        "music_hint": "modern fashion beat",
        "sections": ["fashion_hook", "pose_series", "walk_motion", "closeup_detail", "signature_end"],
    },
    "prewedding_location_film": {
        "label": "Prewedding Location Film Roughcut",
        "target_duration": 90.0,
        "aspect": "16:9",
        "min_clip": 2.5,
        "max_clip": 6.0,
        "default_clip": 4.0,
        "pace": "location_story_smooth",
        "hook_seconds": 8.0,
        "transition_style": "clean_cut_slow_dissolve_optional",
        "crop_hint": "keep_wide_location",
        "music_hint": "cinematic ambient location film",
        "sections": ["wide_location", "couple_enters", "location_motion", "couple_closeup", "wide_end"],
    },
}


@dataclass
class PreweddingRoughcutConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    intent: str | None = None
    target_duration: float | None = None
    write_selection_compat: bool = True
    open_folder: bool = True


class PreweddingRoughcutBuilder:
    # Module 048.
    #
    # Turns Module 047 prewedding selection into a cleaner roughcut timeline.
    #
    # Important:
    # - It also writes compatibility output to stt_prewedding_selection_v1.json,
    #   so Module 049 XML exporter can use the roughcut timeline automatically.
    # - Original Module 047 selection is backed up inside the report folder.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()

        self.project_selection_path = self.project_root / "stt_prewedding_selection_v1.json"
        self.appdata_selection_path = self.appdata_dir / "stt_prewedding_selection_v1.json"

        self.project_roughcut_path = self.project_root / "stt_prewedding_roughcut_v1.json"
        self.appdata_roughcut_path = self.appdata_dir / "stt_prewedding_roughcut_v1.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    def build(
        self,
        intent: str | None = None,
        target_duration: float | None = None,
        write_selection_compat: bool = True,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        selection_file = self.find_selection_file()

        if not selection_file or not selection_file.exists():
            raise FileNotFoundError(
                "Không tìm thấy stt_prewedding_selection_v1.json.\n"
                "Hãy chạy trước: python scripts/build_prewedding_selection.py --intent prewedding_reel_60s"
            )

        selection = self.load_json(selection_file)
        timeline = selection.get("timeline") or []

        if not timeline:
            raise RuntimeError(
                "Selection không có timeline.\n"
                "Hãy chạy lại Module 047: build_prewedding_selection.py"
            )

        selected_intent = intent or str(selection.get("intent") or "prewedding_reel_60s")

        if selected_intent not in ROUGHCUT_RULES:
            if selected_intent.startswith("prewedding_reel"):
                selected_intent = "prewedding_reel_60s"
            elif selected_intent.startswith("prewedding"):
                selected_intent = "prewedding_cinematic"
            else:
                selected_intent = "prewedding_reel_60s"

        rules = dict(ROUGHCUT_RULES[selected_intent])

        if target_duration is not None:
            rules["target_duration"] = float(target_duration)

        rough_timeline = self.make_roughcut_timeline(timeline, rules, selected_intent)

        roughcut_doc = self.build_document(selection, rough_timeline, rules, selected_intent, selection_file)

        self.project_root.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.appdata_dir.mkdir(parents=True, exist_ok=True)

        self.project_roughcut_path.write_text(json.dumps(roughcut_doc, ensure_ascii=False, indent=2), encoding="utf-8")
        self.appdata_roughcut_path.write_text(json.dumps(roughcut_doc, ensure_ascii=False, indent=2), encoding="utf-8")

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.exports_dir / f"prewedding_roughcut_v1_{selected_intent}_{stamp}"
        report_dir.mkdir(parents=True, exist_ok=True)

        backup_selection = report_dir / "BACKUP_original_stt_prewedding_selection_v1.json"
        backup_selection.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")

        roughcut_json = report_dir / "stt_prewedding_roughcut_v1.json"
        timeline_csv = report_dir / "PREWEDDING_ROUGHCUT_TIMELINE.csv"
        report_txt = report_dir / "PREWEDDING_ROUGHCUT_SUMMARY.txt"
        report_html = report_dir / "PREWEDDING_ROUGHCUT_SUMMARY.html"
        edit_prompt = report_dir / "PREWEDDING_ROUGHCUT_EDIT_PROMPT.txt"

        roughcut_json.write_text(json.dumps(roughcut_doc, ensure_ascii=False, indent=2), encoding="utf-8")
        self.write_timeline_csv(timeline_csv, rough_timeline)
        report_txt.write_text(self.render_text(roughcut_doc), encoding="utf-8")
        report_html.write_text(self.render_html(roughcut_doc), encoding="utf-8")
        edit_prompt.write_text(roughcut_doc["edit_prompt"], encoding="utf-8")

        selection_compat_written = False

        if write_selection_compat:
            compat = dict(selection)
            compat["module"] = "048_prewedding_roughcut_builder_compat_selection"
            compat["roughcut_applied"] = True
            compat["roughcut_source"] = str(self.project_roughcut_path)
            compat["intent"] = selected_intent
            compat["label"] = rules.get("label")
            compat["aspect"] = rules.get("aspect")
            compat["target_duration_seconds"] = roughcut_doc["target_duration_seconds"]
            compat["actual_duration_seconds"] = roughcut_doc["actual_duration_seconds"]
            compat["selected_count"] = roughcut_doc["selected_count"]
            compat["timeline"] = rough_timeline
            compat["manual_review_items"] = roughcut_doc["manual_review_items"]
            compat["edit_prompt"] = roughcut_doc["edit_prompt"]

            self.project_selection_path.write_text(json.dumps(compat, ensure_ascii=False, indent=2), encoding="utf-8")
            self.appdata_selection_path.write_text(json.dumps(compat, ensure_ascii=False, indent=2), encoding="utf-8")
            selection_compat_written = True

        result = {
            "ok": True,
            "intent": selected_intent,
            "label": rules.get("label"),
            "aspect": rules.get("aspect"),
            "target_duration": roughcut_doc["target_duration_seconds"],
            "actual_duration": roughcut_doc["actual_duration_seconds"],
            "selected_count": roughcut_doc["selected_count"],
            "project_roughcut": str(self.project_roughcut_path),
            "appdata_roughcut": str(self.appdata_roughcut_path),
            "selection_compat_written": selection_compat_written,
            "project_selection_compat": str(self.project_selection_path) if selection_compat_written else None,
            "report_dir": str(report_dir),
            "roughcut_json": str(roughcut_json),
            "timeline_csv": str(timeline_csv),
            "report_txt": str(report_txt),
            "report_html": str(report_html),
            "edit_prompt": str(edit_prompt),
        }

        (report_dir / "prewedding_roughcut_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(report_dir)
            except Exception:
                pass

        return result

    def find_selection_file(self) -> Path | None:
        for path in [self.project_selection_path, self.appdata_selection_path]:
            if path.exists():
                return path

        if self.exports_dir.exists():
            files = [
                p for p in self.exports_dir.glob("**/stt_prewedding_selection_v1.json")
                if p.is_file() and "_archive" not in p.parts
            ]
            if files:
                return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        return None

    @staticmethod
    def load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def make_roughcut_timeline(
        self,
        timeline: list[dict[str, Any]],
        rules: dict[str, Any],
        intent: str,
    ) -> list[dict[str, Any]]:
        target_duration = float(rules.get("target_duration", 60.0))
        min_clip = float(rules.get("min_clip", 1.0))
        max_clip = float(rules.get("max_clip", 3.5))
        default_clip = float(rules.get("default_clip", 2.5))
        sections = [str(x) for x in rules.get("sections", [])]

        cleaned = [self.clean_clip(x, index=i + 1, rules=rules, intent=intent) for i, x in enumerate(timeline)]
        cleaned = [x for x in cleaned if x.get("file")]

        if not cleaned:
            cleaned = [self.clean_clip(x, index=i + 1, rules=rules, intent=intent) for i, x in enumerate(timeline)]

        # Re-order by target section plan while keeping score order inside each section.
        ordered: list[dict[str, Any]] = []
        used: set[int] = set()

        for section in sections:
            section_items = [
                (i, x) for i, x in enumerate(cleaned)
                if str(x.get("section", "")).lower() == section.lower()
            ]

            if not section_items:
                section_items = [
                    (i, x) for i, x in enumerate(cleaned)
                    if self.section_related(section, x)
                ]

            section_items.sort(key=lambda pair: float(pair[1].get("ai_score", 0) or 0), reverse=True)

            for i, item in section_items:
                if i not in used:
                    ordered.append(item)
                    used.add(i)

        # Add remaining top score items.
        remaining = [(i, x) for i, x in enumerate(cleaned) if i not in used]
        remaining.sort(key=lambda pair: float(pair[1].get("ai_score", 0) or 0), reverse=True)

        for i, item in remaining:
            ordered.append(item)
            used.add(i)

        rough: list[dict[str, Any]] = []
        cursor = 0.0
        last_source = ""

        for item in ordered:
            if cursor >= target_duration:
                break

            item = dict(item)
            source = str(item.get("source_key") or item.get("file") or "")

            if source and source == last_source and len(rough) >= 1:
                # Avoid same source twice in row if possible.
                continue

            source_duration = self.to_float(item.get("source_duration"), 0.0)
            original_duration = self.to_float(item.get("timeline_duration"), default_clip)

            desired = original_duration if original_duration > 0 else default_clip

            if intent.startswith("prewedding_reel"):
                # Reel should be tighter.
                if item.get("is_hook"):
                    desired = min(desired, rules.get("hook_seconds", 3.0))
                desired = max(min_clip, min(max_clip, desired))
            else:
                desired = max(min_clip, min(max_clip, desired))

            if source_duration > 0:
                desired = min(desired, source_duration)

            remaining = target_duration - cursor
            if remaining <= 0:
                break

            if desired > remaining:
                if remaining >= min_clip:
                    desired = remaining
                else:
                    break

            item["timeline_index"] = len(rough) + 1
            item["timeline_start"] = round(cursor, 3)
            item["timeline_duration"] = round(desired, 3)
            item["timeline_end"] = round(cursor + desired, 3)
            item["source_start"] = round(self.to_float(item.get("source_start"), 0.0), 3)
            item["source_end"] = round(item["source_start"] + desired, 3)
            item["roughcut_role"] = self.role_for_clip(item, rules, intent)
            item["transition_hint"] = self.transition_hint(item, rules, intent)
            item["speed_hint"] = self.speed_hint(item, intent)
            item["crop_hint"] = self.crop_hint(item, rules, intent)
            item["music_hint"] = rules.get("music_hint")
            item["review_note"] = self.review_note(item, intent)

            rough.append(item)
            cursor += desired
            last_source = source

        # If final duration is short, allow repeated source but not exact duplicate.
        if cursor < target_duration * 0.75:
            used_ids = {self.item_id(x) for x in rough}
            for item in ordered:
                if cursor >= target_duration:
                    break
                if self.item_id(item) in used_ids:
                    continue

                item = dict(item)
                desired = max(min_clip, min(max_clip, self.to_float(item.get("timeline_duration"), default_clip)))
                remaining = target_duration - cursor
                if desired > remaining:
                    desired = remaining
                if desired < min_clip:
                    break

                item["timeline_index"] = len(rough) + 1
                item["timeline_start"] = round(cursor, 3)
                item["timeline_duration"] = round(desired, 3)
                item["timeline_end"] = round(cursor + desired, 3)
                item["source_start"] = round(self.to_float(item.get("source_start"), 0.0), 3)
                item["source_end"] = round(item["source_start"] + desired, 3)
                item["roughcut_role"] = self.role_for_clip(item, rules, intent)
                item["transition_hint"] = self.transition_hint(item, rules, intent)
                item["speed_hint"] = self.speed_hint(item, intent)
                item["crop_hint"] = self.crop_hint(item, rules, intent)
                item["music_hint"] = rules.get("music_hint")
                item["review_note"] = self.review_note(item, intent)

                rough.append(item)
                used_ids.add(self.item_id(item))
                cursor += desired

        # Re-index exactly.
        cursor = 0.0
        for idx, item in enumerate(rough, start=1):
            item["timeline_index"] = idx
            item["timeline_start"] = round(cursor, 3)
            cursor += float(item.get("timeline_duration", 0))
            item["timeline_end"] = round(cursor, 3)

        return rough

    @staticmethod
    def clean_clip(item: dict[str, Any], index: int, rules: dict[str, Any], intent: str) -> dict[str, Any]:
        out = dict(item)
        out["source_selection_index"] = index
        out["file"] = str(item.get("file") or item.get("path") or item.get("_filename") or "")
        out["source_key"] = str(item.get("source_key") or Path(out["file"]).name.lower() if out["file"] else "")
        out["section"] = str(item.get("section") or "best")
        out["ai_score"] = PreweddingRoughcutBuilder.to_float(item.get("ai_score"), 0.0)
        out["ai_rank_hint"] = item.get("ai_rank_hint", "")
        out["ai_reasons"] = item.get("ai_reasons", [])
        out["ai_penalties"] = item.get("ai_penalties", [])
        out["source_start"] = PreweddingRoughcutBuilder.to_float(item.get("source_start"), 0.0)
        out["source_end"] = PreweddingRoughcutBuilder.to_float(item.get("source_end"), 0.0)
        out["source_duration"] = PreweddingRoughcutBuilder.to_float(item.get("source_duration"), 0.0)
        out["timeline_duration"] = PreweddingRoughcutBuilder.to_float(
            item.get("timeline_duration"),
            float(rules.get("default_clip", 2.5)),
        )

        text = PreweddingRoughcutBuilder.item_text(out)
        out["is_hook"] = any(k in text for k in ["hook", "best", "fashion", "motion", "walking", "close", "dress"])
        out["is_motion"] = any(k in text for k in ["motion", "walking", "walk", "spin", "dress", "slow", "stable"])
        out["is_emotion"] = any(k in text for k in ["emotion", "hug", "kiss", "look", "close", "reaction"])
        out["is_location"] = any(k in text for k in ["location", "wide", "sunset", "beach", "forest", "city", "architecture"])

        return out

    @staticmethod
    def section_related(section: str, item: dict[str, Any]) -> bool:
        text = PreweddingRoughcutBuilder.item_text(item)
        section_text = section.replace("_", " ")

        if section_text in text:
            return True

        mapping = {
            "hook": ["hook", "best", "fashion", "motion"],
            "couple": ["couple", "walking", "holding", "hug", "look"],
            "fashion": ["fashion", "pose", "dress", "look"],
            "location": ["location", "wide", "sunset", "beach", "forest", "city"],
            "emotion": ["emotion", "close", "hug", "kiss", "look"],
            "end": ["end", "kiss", "hug", "wide", "walking"],
        }

        for key, words in mapping.items():
            if key in section.lower():
                return any(w in text for w in words)

        return False

    @staticmethod
    def item_text(item: dict[str, Any]) -> str:
        parts = []
        for key in ["file", "section", "roughcut_role", "ai_rank_hint", "ai_reasons", "review_note"]:
            value = item.get(key)
            if isinstance(value, list):
                parts.extend(str(x) for x in value)
            elif value is not None:
                parts.append(str(value))
        return " ".join(parts).lower()

    @staticmethod
    def role_for_clip(item: dict[str, Any], rules: dict[str, Any], intent: str) -> str:
        text = PreweddingRoughcutBuilder.item_text(item)

        if item.get("timeline_start", 999) <= float(rules.get("hook_seconds", 3.0)):
            return "hook"

        if any(k in text for k in ["fashion", "pose", "dress"]):
            return "fashion_motion"

        if any(k in text for k in ["wide", "location", "sunset", "beach", "forest", "city"]):
            return "location_beauty"

        if any(k in text for k in ["close", "emotion", "hug", "kiss", "look"]):
            return "emotion"

        if any(k in text for k in ["walk", "walking", "holding"]):
            return "couple_motion"

        return "best_candidate"

    @staticmethod
    def transition_hint(item: dict[str, Any], rules: dict[str, Any], intent: str) -> str:
        if item.get("timeline_index") == 1:
            return "start_on_best_frame"

        if intent.startswith("prewedding_reel"):
            if item.get("is_motion"):
                return "beat_cut_or_soft_whoosh"
            return "clean_cut_on_beat"

        if item.get("is_location"):
            return "slow_push_or_clean_cut"

        return str(rules.get("transition_style", "clean_cut"))

    @staticmethod
    def speed_hint(item: dict[str, Any], intent: str) -> str:
        if intent.startswith("prewedding_reel"):
            if item.get("is_motion"):
                return "normal_or_80_percent_slow_if_smooth"
            return "normal_speed_keep_short"

        if item.get("is_motion") or item.get("is_emotion"):
            return "consider_70_80_percent_slow_motion"

        return "normal_speed"

    @staticmethod
    def crop_hint(item: dict[str, Any], rules: dict[str, Any], intent: str) -> str:
        if str(rules.get("aspect")) == "9:16":
            if item.get("is_location"):
                return "vertical_crop_keep_couple_and_location"
            if item.get("is_motion"):
                return "vertical_crop_follow_couple_motion"
            return "vertical_crop_center_face_or_couple"

        return str(rules.get("crop_hint", "keep_original_16x9"))

    @staticmethod
    def review_note(item: dict[str, Any], intent: str) -> str:
        role = item.get("roughcut_role", "shot")
        score = item.get("ai_score", "")
        return f"Module048 roughcut {intent}: {role}, score {score}"

    @staticmethod
    def item_id(item: dict[str, Any]) -> str:
        return f"{item.get('file')}|{item.get('source_start')}|{item.get('source_end')}|{item.get('section')}"

    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def build_document(
        self,
        original_selection: dict[str, Any],
        rough_timeline: list[dict[str, Any]],
        rules: dict[str, Any],
        intent: str,
        selection_file: Path,
    ) -> dict[str, Any]:
        actual = round(sum(float(x.get("timeline_duration", 0)) for x in rough_timeline), 3)
        now = datetime.now().isoformat(timespec="seconds")

        return {
            "ok": True,
            "module": "048_prewedding_roughcut_builder",
            "version": "0.48",
            "created_at": now,
            "updated_at": now,
            "project_root": str(self.project_root),
            "input_selection": str(selection_file),
            "original_selection_module": original_selection.get("module"),
            "intent": intent,
            "label": rules.get("label"),
            "aspect": rules.get("aspect"),
            "target_duration_seconds": float(rules.get("target_duration", 0)),
            "actual_duration_seconds": actual,
            "selected_count": len(rough_timeline),
            "pace": rules.get("pace"),
            "music_hint": rules.get("music_hint"),
            "transition_style": rules.get("transition_style"),
            "crop_hint": rules.get("crop_hint"),
            "roughcut_rules": rules,
            "timeline": rough_timeline,
            "manual_review_items": self.to_manual_review_items(rough_timeline),
            "edit_prompt": self.build_edit_prompt(intent, rules, rough_timeline),
            "next_steps": [
                "Module 049: export_prewedding_xml.py để xuất XML Premiere.",
                "Trong Premiere import XML rồi chỉnh lại fine cut.",
                "Nếu là reel, dùng preset vertical_1080_25p.",
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
                "roughcut_role": clip.get("roughcut_role"),
                "ai_score": clip.get("ai_score"),
                "transition_hint": clip.get("transition_hint"),
                "speed_hint": clip.get("speed_hint"),
                "crop_hint": clip.get("crop_hint"),
                "note": clip.get("review_note"),
            })
        return items

    @staticmethod
    def build_edit_prompt(intent: str, rules: dict[str, Any], timeline: list[dict[str, Any]]) -> str:
        lines = [
            "STT AI Editor - Prewedding Roughcut Prompt",
            "=" * 72,
            f"Intent: {intent}",
            f"Label: {rules.get('label')}",
            f"Aspect: {rules.get('aspect')}",
            f"Target duration: {rules.get('target_duration')}s",
            f"Pace: {rules.get('pace')}",
            f"Music hint: {rules.get('music_hint')}",
            "",
            "Dựng theo hướng:",
        ]

        if "reel" in intent:
            lines += [
                "- Reel prewedding dọc 9:16.",
                "- Hook 1-3 giây đầu phải đẹp nhất.",
                "- Cut theo beat, nhịp nhanh nhưng vẫn romantic.",
                "- Ưu tiên couple, pose, váy bay, đi bộ, close-up, location đẹp.",
                "- Không dựng như wedding ceremony, không gia tiên/reception.",
            ]
        else:
            lines += [
                "- Prewedding cinematic.",
                "- Mượt, romantic, ưu tiên location đẹp và couple story.",
                "- Có shot rộng, couple walking, close-up cảm xúc, váy chuyển động.",
                "- Không dùng logic lễ cưới/gia tiên/reception.",
            ]

        lines += ["", "Roughcut timeline:"]
        for clip in timeline:
            lines.append(
                f"- {clip.get('timeline_start')}s-{clip.get('timeline_end')}s | "
                f"{clip.get('roughcut_role')} | {clip.get('section')} | "
                f"score {clip.get('ai_score')} | {clip.get('file')}"
            )

        return "\n".join(lines)

    @staticmethod
    def write_timeline_csv(path: Path, timeline: list[dict[str, Any]]) -> None:
        fieldnames = [
            "timeline_index",
            "timeline_start",
            "timeline_end",
            "timeline_duration",
            "section",
            "roughcut_role",
            "source_start",
            "source_end",
            "file",
            "ai_score",
            "transition_hint",
            "speed_hint",
            "crop_hint",
            "music_hint",
            "review_note",
        ]

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in timeline:
                writer.writerow({key: item.get(key, "") for key in fieldnames})

    @staticmethod
    def render_text(doc: dict[str, Any]) -> str:
        lines = [
            "STT AI Editor - Prewedding Roughcut Builder",
            "=" * 72,
            f"Intent: {doc.get('intent')}",
            f"Label: {doc.get('label')}",
            f"Aspect: {doc.get('aspect')}",
            f"Target: {doc.get('target_duration_seconds')}s",
            f"Actual: {doc.get('actual_duration_seconds')}s",
            f"Selected: {doc.get('selected_count')}",
            f"Music hint: {doc.get('music_hint')}",
            "",
            "Timeline:",
        ]

        for clip in doc.get("timeline", []):
            lines.append(
                f"{clip.get('timeline_index'):>3}. "
                f"{clip.get('timeline_start')} - {clip.get('timeline_end')} | "
                f"{clip.get('roughcut_role')} | {clip.get('section')} | "
                f"{clip.get('ai_score')} | {clip.get('file')}"
            )

        return "\n".join(lines)

    @staticmethod
    def render_html(doc: dict[str, Any]) -> str:
        import html

        intent = html.escape(str(doc.get("intent", "")))
        label = html.escape(str(doc.get("label", "")))
        aspect = html.escape(str(doc.get("aspect", "")))
        target = html.escape(str(doc.get("target_duration_seconds", "")))
        actual = html.escape(str(doc.get("actual_duration_seconds", "")))
        selected = html.escape(str(doc.get("selected_count", "")))
        music = html.escape(str(doc.get("music_hint", "")))

        rows = []
        for clip in doc.get("timeline", []):
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(clip.get('timeline_index', '')))}</td>"
                f"<td>{html.escape(str(clip.get('timeline_start', '')))} - {html.escape(str(clip.get('timeline_end', '')))}</td>"
                f"<td>{html.escape(str(clip.get('roughcut_role', '')))}</td>"
                f"<td>{html.escape(str(clip.get('section', '')))}</td>"
                f"<td>{html.escape(str(clip.get('ai_score', '')))}</td>"
                f"<td>{html.escape(str(clip.get('file', '')))}</td>"
                f"<td>{html.escape(str(clip.get('transition_hint', '')))}</td>"
                f"<td>{html.escape(str(clip.get('crop_hint', '')))}</td>"
                "</tr>"
            )

        if not rows:
            rows.append("<tr><td colspan='8'>No roughcut clips</td></tr>")

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT Prewedding Roughcut Builder</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1400px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid #333; padding: 8px; vertical-align: top; }}
th {{ text-align: left; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 048</div>
  <h1>Prewedding Roughcut Builder</h1>
  <p>Intent: <b>{intent}</b> / {label}</p>
  <p>Aspect: {aspect} | Target: {target}s | Actual: {actual}s | Selected: {selected}</p>
  <p>Music hint: {music}</p>

  <h2>Roughcut Timeline</h2>
  <table>
    <tr>
      <th>#</th><th>Time</th><th>Role</th><th>Section</th><th>Score</th><th>File</th><th>Transition</th><th>Crop</th>
    </tr>
    {''.join(rows)}
  </table>
</div>
</body>
</html>
'''


def build_prewedding_roughcut(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str | None = None,
    target_duration: float | None = None,
    write_selection_compat: bool = True,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PreweddingRoughcutBuilder(project_root=project_root).build(
        intent=intent,
        target_duration=target_duration,
        write_selection_compat=write_selection_compat,
        open_folder=open_folder,
    )
