
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


REFINER_RULES: dict[str, dict[str, Any]] = {
    "prewedding_reel_30s": {
        "label": "Prewedding Reel 30s Smart Refine",
        "target_duration": 30.0,
        "aspect": "9:16",
        "min_clip": 1.0,
        "max_clip": 2.6,
        "default_clip": 2.0,
        "min_keep_score": 56.0,
        "strong_score": 72.0,
        "hook_seconds": 3.0,
        "section_plan": ["hook", "couple_motion", "fashion_location", "emotion_end"],
        "prefer_roles": ["hook", "couple_motion", "fashion_motion", "location_beauty", "emotion"],
        "opening_keywords": ["hook", "best", "fashion", "motion", "walking", "dress", "close"],
    },
    "prewedding_reel_60s": {
        "label": "Prewedding Reel 60s Smart Refine",
        "target_duration": 60.0,
        "aspect": "9:16",
        "min_clip": 1.2,
        "max_clip": 3.3,
        "default_clip": 2.6,
        "min_keep_score": 54.0,
        "strong_score": 70.0,
        "hook_seconds": 4.0,
        "section_plan": ["hook", "couple_story", "fashion_motion", "location_beauty", "romantic_end"],
        "prefer_roles": ["hook", "couple_motion", "fashion_motion", "location_beauty", "emotion"],
        "opening_keywords": ["hook", "best", "fashion", "motion", "walking", "dress", "close"],
    },
    "prewedding_cinematic": {
        "label": "Prewedding Cinematic Smart Refine",
        "target_duration": 120.0,
        "aspect": "16:9",
        "min_clip": 2.0,
        "max_clip": 6.0,
        "default_clip": 4.0,
        "min_keep_score": 50.0,
        "strong_score": 68.0,
        "hook_seconds": 8.0,
        "section_plan": ["location_hook", "couple_walk", "emotion_closeup", "dress_motion", "location_beauty", "romantic_end"],
        "prefer_roles": ["location_beauty", "couple_motion", "emotion", "fashion_motion", "hook"],
        "opening_keywords": ["location", "wide", "sunset", "walking", "slow", "couple"],
    },
    "prewedding_fashion": {
        "label": "Prewedding Fashion Smart Refine",
        "target_duration": 45.0,
        "aspect": "9:16",
        "min_clip": 1.0,
        "max_clip": 2.8,
        "default_clip": 2.3,
        "min_keep_score": 54.0,
        "strong_score": 70.0,
        "hook_seconds": 4.0,
        "section_plan": ["fashion_hook", "pose_series", "walk_motion", "closeup_detail", "signature_end"],
        "prefer_roles": ["hook", "fashion_motion", "couple_motion", "emotion", "location_beauty"],
        "opening_keywords": ["fashion", "pose", "dress", "look", "motion"],
    },
    "prewedding_location_film": {
        "label": "Prewedding Location Film Smart Refine",
        "target_duration": 90.0,
        "aspect": "16:9",
        "min_clip": 2.2,
        "max_clip": 6.0,
        "default_clip": 4.0,
        "min_keep_score": 50.0,
        "strong_score": 68.0,
        "hook_seconds": 8.0,
        "section_plan": ["wide_location", "couple_enters", "location_motion", "couple_closeup", "wide_end"],
        "prefer_roles": ["location_beauty", "couple_motion", "emotion", "hook"],
        "opening_keywords": ["wide", "location", "landscape", "sunset", "beach", "forest", "city"],
    },
}


@dataclass
class PreweddingRefinerConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    intent: str | None = None
    target_duration: float | None = None
    write_selection_compat: bool = True
    open_folder: bool = True


class PreweddingSmartRefiner:
    # Module 050.
    #
    # This module refines Module 048 roughcut before Module 049 XML export.
    #
    # It:
    # - moves strongest hook to the beginning
    # - removes adjacent duplicate source shots
    # - replaces weak shots using Module 046 score pool
    # - balances prewedding roles/sections
    # - writes compatibility output back to stt_prewedding_selection_v1.json
    #
    # Correct workflow:
    # 046 score -> 047 selection -> 048 roughcut -> 050 refine -> 049 XML

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()

        self.project_roughcut_path = self.project_root / "stt_prewedding_roughcut_v1.json"
        self.appdata_roughcut_path = self.appdata_dir / "stt_prewedding_roughcut_v1.json"

        self.project_selection_path = self.project_root / "stt_prewedding_selection_v1.json"
        self.appdata_selection_path = self.appdata_dir / "stt_prewedding_selection_v1.json"

        self.project_score_path = self.project_root / "stt_ai_shot_scores_v1.json"
        self.appdata_score_path = self.appdata_dir / "stt_ai_shot_scores_v1.json"

        self.project_refined_path = self.project_root / "stt_prewedding_refined_v1.json"
        self.appdata_refined_path = self.appdata_dir / "stt_prewedding_refined_v1.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    def refine(
        self,
        intent: str | None = None,
        target_duration: float | None = None,
        write_selection_compat: bool = True,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        input_file = self.find_input_file()

        if not input_file or not input_file.exists():
            raise FileNotFoundError(
                "Không tìm thấy roughcut/selection.\n"
                "Hãy chạy trước:\n"
                "python scripts/build_prewedding_selection.py --intent prewedding_reel_60s\n"
                "python scripts/build_prewedding_roughcut.py --intent prewedding_reel_60s"
            )

        input_doc = self.load_json(input_file)
        timeline = input_doc.get("timeline") or []

        if not timeline:
            raise RuntimeError("Input không có timeline để refine.")

        selected_intent = intent or str(input_doc.get("intent") or "prewedding_reel_60s")
        selected_intent = self.normalize_intent(selected_intent)

        rules = dict(REFINER_RULES[selected_intent])
        if target_duration is not None:
            rules["target_duration"] = float(target_duration)

        score_pool_doc = self.load_score_pool()
        score_pool = self.extract_score_pool(score_pool_doc)

        refined_timeline, replacements, warnings = self.refine_timeline(
            timeline=timeline,
            score_pool=score_pool,
            rules=rules,
            intent=selected_intent,
        )

        refined_doc = self.build_document(
            input_doc=input_doc,
            input_file=input_file,
            refined_timeline=refined_timeline,
            replacements=replacements,
            warnings=warnings,
            rules=rules,
            intent=selected_intent,
            score_pool_doc=score_pool_doc,
        )

        self.project_root.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.appdata_dir.mkdir(parents=True, exist_ok=True)

        self.project_refined_path.write_text(json.dumps(refined_doc, ensure_ascii=False, indent=2), encoding="utf-8")
        self.appdata_refined_path.write_text(json.dumps(refined_doc, ensure_ascii=False, indent=2), encoding="utf-8")

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.exports_dir / f"prewedding_refiner_v1_{selected_intent}_{stamp}"
        report_dir.mkdir(parents=True, exist_ok=True)

        backup_input = report_dir / "BACKUP_input_before_refine.json"
        backup_input.write_text(json.dumps(input_doc, ensure_ascii=False, indent=2), encoding="utf-8")

        refined_json = report_dir / "stt_prewedding_refined_v1.json"
        timeline_csv = report_dir / "PREWEDDING_REFINED_TIMELINE.csv"
        replacements_csv = report_dir / "PREWEDDING_REPLACEMENT_SUGGESTIONS.csv"
        report_txt = report_dir / "PREWEDDING_REFINER_SUMMARY.txt"
        report_html = report_dir / "PREWEDDING_REFINER_SUMMARY.html"
        edit_prompt = report_dir / "PREWEDDING_REFINED_EDIT_PROMPT.txt"

        refined_json.write_text(json.dumps(refined_doc, ensure_ascii=False, indent=2), encoding="utf-8")
        self.write_timeline_csv(timeline_csv, refined_timeline)
        self.write_replacements_csv(replacements_csv, replacements)
        report_txt.write_text(self.render_text(refined_doc), encoding="utf-8")
        report_html.write_text(self.render_html(refined_doc), encoding="utf-8")
        edit_prompt.write_text(refined_doc["edit_prompt"], encoding="utf-8")

        selection_compat_written = False

        if write_selection_compat:
            compat = dict(input_doc)
            compat["module"] = "050_prewedding_smart_refiner_compat_selection"
            compat["refiner_applied"] = True
            compat["refiner_source"] = str(self.project_refined_path)
            compat["intent"] = selected_intent
            compat["label"] = rules.get("label")
            compat["aspect"] = rules.get("aspect")
            compat["target_duration_seconds"] = refined_doc["target_duration_seconds"]
            compat["actual_duration_seconds"] = refined_doc["actual_duration_seconds"]
            compat["selected_count"] = refined_doc["selected_count"]
            compat["timeline"] = refined_timeline
            compat["manual_review_items"] = refined_doc["manual_review_items"]
            compat["edit_prompt"] = refined_doc["edit_prompt"]
            compat["refiner_replacements"] = replacements
            compat["refiner_warnings"] = warnings

            self.project_selection_path.write_text(json.dumps(compat, ensure_ascii=False, indent=2), encoding="utf-8")
            self.appdata_selection_path.write_text(json.dumps(compat, ensure_ascii=False, indent=2), encoding="utf-8")
            selection_compat_written = True

        result = {
            "ok": True,
            "intent": selected_intent,
            "label": rules.get("label"),
            "aspect": rules.get("aspect"),
            "target_duration": refined_doc["target_duration_seconds"],
            "actual_duration": refined_doc["actual_duration_seconds"],
            "selected_count": refined_doc["selected_count"],
            "replacement_count": len(replacements),
            "warning_count": len(warnings),
            "project_refined": str(self.project_refined_path),
            "appdata_refined": str(self.appdata_refined_path),
            "selection_compat_written": selection_compat_written,
            "project_selection_compat": str(self.project_selection_path) if selection_compat_written else None,
            "report_dir": str(report_dir),
            "refined_json": str(refined_json),
            "timeline_csv": str(timeline_csv),
            "replacements_csv": str(replacements_csv),
            "report_txt": str(report_txt),
            "report_html": str(report_html),
            "edit_prompt": str(edit_prompt),
        }

        (report_dir / "prewedding_refiner_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(report_dir)
            except Exception:
                pass

        return result

    def find_input_file(self) -> Path | None:
        for path in [self.project_roughcut_path, self.appdata_roughcut_path, self.project_selection_path, self.appdata_selection_path]:
            if path.exists():
                return path

        if self.exports_dir.exists():
            candidates = []
            for name in ["stt_prewedding_roughcut_v1.json", "stt_prewedding_selection_v1.json"]:
                candidates.extend([
                    p for p in self.exports_dir.glob(f"**/{name}")
                    if p.is_file() and "_archive" not in p.parts
                ])

            if candidates:
                return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        return None

    def load_score_pool(self) -> dict[str, Any]:
        for path in [self.project_score_path, self.appdata_score_path]:
            if path.exists():
                data = self.load_json(path)
                if data.get("scored_items") or data.get("selected_items"):
                    return data

        if self.exports_dir.exists():
            files = [
                p for p in self.exports_dir.glob("**/stt_ai_shot_scores_v1.json")
                if p.is_file() and "_archive" not in p.parts
            ]
            if files:
                latest = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
                return self.load_json(latest)

        return {}

    @staticmethod
    def load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def normalize_intent(intent: str) -> str:
        if intent in REFINER_RULES:
            return intent
        if "30" in intent and "reel" in intent:
            return "prewedding_reel_30s"
        if "fashion" in intent:
            return "prewedding_fashion"
        if "location" in intent:
            return "prewedding_location_film"
        if "cinematic" in intent:
            return "prewedding_cinematic"
        return "prewedding_reel_60s"

    @staticmethod
    def extract_score_pool(score_pool_doc: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        for key in ["scored_items", "selected_items", "items", "candidates"]:
            value = score_pool_doc.get(key)
            if isinstance(value, list):
                items.extend(x for x in value if isinstance(x, dict))
        items.sort(key=lambda x: float(x.get("ai_score", 0) or 0), reverse=True)
        return items

    def refine_timeline(
        self,
        timeline: list[dict[str, Any]],
        score_pool: list[dict[str, Any]],
        rules: dict[str, Any],
        intent: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        replacements: list[dict[str, Any]] = []

        normalized = [self.normalize_clip(x, i + 1, rules, intent) for i, x in enumerate(timeline)]
        pool = [self.normalize_candidate(x, i + 1, rules, intent) for i, x in enumerate(score_pool)]

        if not pool:
            warnings.append("Không có score pool từ Module 046, chỉ refine dựa trên timeline hiện tại.")

        # Remove exact duplicates.
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in normalized:
            key = self.item_id(item)
            if key in seen:
                replacements.append(self.make_action("remove_duplicate_exact", item, None, "Trùng shot chính xác."))
                continue
            seen.add(key)
            unique.append(item)

        normalized = unique

        # Replace weak or bad items.
        used_ids = {self.item_id(x) for x in normalized}
        refined: list[dict[str, Any]] = []

        for idx, item in enumerate(normalized):
            weak_reasons = self.weak_reasons(item, rules)

            if weak_reasons and pool:
                replacement = self.find_replacement(
                    item=item,
                    pool=pool,
                    used_ids=used_ids,
                    rules=rules,
                    intent=intent,
                )

                if replacement:
                    replacement = self.transfer_timing(
                        replacement,
                        source_clip=item,
                        rules=rules,
                        intent=intent,
                    )
                    replacement["refiner_action"] = "replace_weak_clip"
                    replacement["refiner_reason"] = "; ".join(weak_reasons)
                    refined.append(replacement)
                    used_ids.add(self.item_id(replacement))
                    replacements.append(self.make_action("replace_weak_clip", item, replacement, "; ".join(weak_reasons)))
                    continue

            item["refiner_action"] = "keep"
            item["refiner_reason"] = "usable"
            refined.append(item)

        # Ensure best hook first.
        hook_item = self.find_best_hook(refined + pool, rules, used_ids_for_pool=set())
        if hook_item:
            current_first_id = self.item_id(refined[0]) if refined else ""
            hook_id = self.item_id(hook_item)

            if hook_id != current_first_id:
                # If hook exists inside refined list, move it to front.
                hook_index = None
                for i, item in enumerate(refined):
                    if self.item_id(item) == hook_id:
                        hook_index = i
                        break

                if hook_index is not None:
                    moved = refined.pop(hook_index)
                    moved["refiner_action"] = "move_best_hook_to_start"
                    moved["refiner_reason"] = "hook đẹp hơn cho mở đầu"
                    refined.insert(0, moved)
                    replacements.append(self.make_action("move_best_hook_to_start", moved, moved, "Đưa hook tốt nhất lên đầu."))
                elif pool and self.score_of(hook_item) >= float(rules.get("strong_score", 70)):
                    # Replace first item with better hook from pool.
                    old_first = refined[0] if refined else None
                    new_hook = self.transfer_timing(hook_item, old_first or hook_item, rules, intent)
                    new_hook["refiner_action"] = "replace_first_with_better_hook"
                    new_hook["refiner_reason"] = "hook từ score pool mạnh hơn"
                    if old_first:
                        refined[0] = new_hook
                        replacements.append(self.make_action("replace_first_with_better_hook", old_first, new_hook, "Hook đầu chưa đủ mạnh."))
                    else:
                        refined.insert(0, new_hook)

        # Avoid same source adjacent.
        refined = self.fix_adjacent_duplicates(refined, pool, replacements, rules, intent)

        # Reorder softly by section plan.
        refined = self.reorder_by_section(refined, rules)

        # Fit target duration and final timeline.
        refined = self.fit_duration(refined, rules, intent)

        # Add final refiner metadata.
        quality_notes = self.quality_notes(refined, rules)
        warnings.extend(quality_notes)

        return refined, replacements, warnings

    @staticmethod
    def normalize_clip(item: dict[str, Any], index: int, rules: dict[str, Any], intent: str) -> dict[str, Any]:
        out = dict(item)
        out["source_input_index"] = index
        out["file"] = str(item.get("file") or item.get("path") or item.get("_filename") or "")
        out["source_key"] = str(item.get("source_key") or (Path(out["file"]).name.lower() if out["file"] else "unknown"))
        out["section"] = str(item.get("section") or item.get("roughcut_role") or "best")
        out["roughcut_role"] = str(item.get("roughcut_role") or PreweddingSmartRefiner.guess_role(item, intent))
        out["ai_score"] = PreweddingSmartRefiner.to_float(item.get("ai_score"), 0.0)
        out["ai_rank_hint"] = item.get("ai_rank_hint", "")
        out["ai_reasons"] = item.get("ai_reasons", [])
        out["ai_penalties"] = item.get("ai_penalties", [])
        out["source_start"] = PreweddingSmartRefiner.to_float(item.get("source_start"), 0.0)
        out["source_end"] = PreweddingSmartRefiner.to_float(item.get("source_end"), 0.0)
        out["source_duration"] = PreweddingSmartRefiner.to_float(item.get("source_duration"), 0.0)
        out["timeline_duration"] = PreweddingSmartRefiner.to_float(item.get("timeline_duration"), rules.get("default_clip", 2.5))
        out["transition_hint"] = item.get("transition_hint") or PreweddingSmartRefiner.default_transition(out, intent)
        out["speed_hint"] = item.get("speed_hint") or PreweddingSmartRefiner.default_speed(out, intent)
        out["crop_hint"] = item.get("crop_hint") or PreweddingSmartRefiner.default_crop(out, rules, intent)
        return out

    @staticmethod
    def normalize_candidate(item: dict[str, Any], index: int, rules: dict[str, Any], intent: str) -> dict[str, Any]:
        out = PreweddingSmartRefiner.normalize_clip(item, index, rules, intent)
        out["from_score_pool"] = True
        out["section"] = PreweddingSmartRefiner.guess_section(out, intent)
        out["roughcut_role"] = PreweddingSmartRefiner.guess_role(out, intent)
        return out

    @staticmethod
    def weak_reasons(item: dict[str, Any], rules: dict[str, Any]) -> list[str]:
        reasons = []
        score = float(item.get("ai_score", 0) or 0)
        min_score = float(rules.get("min_keep_score", 54.0))
        text = PreweddingSmartRefiner.item_text(item)

        if score and score < min_score:
            reasons.append(f"score thấp {score} < {min_score}")

        bad_words = ["shaky", "out_focus", "out of focus", "blur", "empty", "no_content", "bad", "reject", "rung", "out nét", "mất nét"]
        if any(w in text for w in bad_words):
            reasons.append("có dấu hiệu shot xấu/rung/out nét/empty")

        if not str(item.get("file") or "").strip():
            reasons.append("thiếu file path")

        return reasons

    def find_replacement(
        self,
        item: dict[str, Any],
        pool: list[dict[str, Any]],
        used_ids: set[str],
        rules: dict[str, Any],
        intent: str,
    ) -> dict[str, Any] | None:
        old_score = self.score_of(item)
        item_text = self.item_text(item)
        desired_role = str(item.get("roughcut_role") or item.get("section") or "")

        best = None
        best_score = -999.0

        for candidate in pool:
            cand_id = self.item_id(candidate)
            if cand_id in used_ids:
                continue

            score = self.score_of(candidate)

            if score < old_score + 4 and score < float(rules.get("strong_score", 70)):
                continue

            cand_text = self.item_text(candidate)

            if desired_role and desired_role in cand_text:
                score += 8

            if self.role_family(desired_role) == self.role_family(str(candidate.get("roughcut_role") or "")):
                score += 6

            if intent.startswith("prewedding_reel") and any(w in cand_text for w in ["motion", "walking", "fashion", "dress", "close", "hook"]):
                score += 5

            if "location" in item_text and "location" in cand_text:
                score += 4

            if score > best_score:
                best = candidate
                best_score = score

        return best

    @staticmethod
    def transfer_timing(candidate: dict[str, Any], source_clip: dict[str, Any], rules: dict[str, Any], intent: str) -> dict[str, Any]:
        out = dict(candidate)
        duration = PreweddingSmartRefiner.to_float(source_clip.get("timeline_duration"), rules.get("default_clip", 2.5))
        duration = max(float(rules.get("min_clip", 1.0)), min(float(rules.get("max_clip", 3.5)), duration))

        source_duration = PreweddingSmartRefiner.to_float(out.get("source_duration"), 0.0)
        if source_duration > 0:
            duration = min(duration, source_duration)

        out["timeline_duration"] = round(duration, 3)
        out["source_start"] = PreweddingSmartRefiner.to_float(out.get("source_start"), 0.0)
        out["source_end"] = round(out["source_start"] + duration, 3)
        out["section"] = source_clip.get("section") or out.get("section")
        out["roughcut_role"] = source_clip.get("roughcut_role") or out.get("roughcut_role")
        out["transition_hint"] = PreweddingSmartRefiner.default_transition(out, intent)
        out["speed_hint"] = PreweddingSmartRefiner.default_speed(out, intent)
        out["crop_hint"] = PreweddingSmartRefiner.default_crop(out, rules, intent)
        return out

    @staticmethod
    def find_best_hook(items: list[dict[str, Any]], rules: dict[str, Any], used_ids_for_pool: set[str] | None = None) -> dict[str, Any] | None:
        best = None
        best_score = -999.0
        opening_keywords = [str(x).lower() for x in rules.get("opening_keywords", [])]

        for item in items:
            text = PreweddingSmartRefiner.item_text(item)
            score = PreweddingSmartRefiner.score_of(item)

            if any(k in text for k in opening_keywords):
                score += 15

            if str(item.get("roughcut_role", "")).lower() == "hook":
                score += 12

            if item.get("liked") or item.get("_liked"):
                score += 8

            if score > best_score:
                best = item
                best_score = score

        return best

    def fix_adjacent_duplicates(
        self,
        timeline: list[dict[str, Any]],
        pool: list[dict[str, Any]],
        replacements: list[dict[str, Any]],
        rules: dict[str, Any],
        intent: str,
    ) -> list[dict[str, Any]]:
        if len(timeline) < 2:
            return timeline

        used_ids = {self.item_id(x) for x in timeline}
        out: list[dict[str, Any]] = []

        for item in timeline:
            if out and str(out[-1].get("source_key")) == str(item.get("source_key")):
                replacement = self.find_replacement(item, pool, used_ids, rules, intent)
                if replacement:
                    replacement = self.transfer_timing(replacement, item, rules, intent)
                    replacement["refiner_action"] = "replace_adjacent_duplicate_source"
                    replacement["refiner_reason"] = "tránh 2 shot liên tiếp cùng file/source"
                    out.append(replacement)
                    used_ids.add(self.item_id(replacement))
                    replacements.append(self.make_action("replace_adjacent_duplicate_source", item, replacement, "Hai shot liên tiếp cùng source."))
                else:
                    item["refiner_action"] = "keep_but_adjacent_duplicate"
                    item["refiner_reason"] = "không tìm được shot thay thế tốt hơn"
                    out.append(item)
                continue

            out.append(item)

        return out

    @staticmethod
    def reorder_by_section(timeline: list[dict[str, Any]], rules: dict[str, Any]) -> list[dict[str, Any]]:
        if not timeline:
            return []

        section_plan = [str(x).lower() for x in rules.get("section_plan", [])]
        if not section_plan:
            return timeline

        hook = timeline[0]
        remaining = timeline[1:]

        ordered = [hook]
        used_ids = {PreweddingSmartRefiner.item_id(hook)}

        for section in section_plan:
            matches = [
                x for x in remaining
                if PreweddingSmartRefiner.item_id(x) not in used_ids
                and PreweddingSmartRefiner.section_matches(x, section)
            ]
            matches.sort(key=lambda x: PreweddingSmartRefiner.score_of(x), reverse=True)

            for item in matches:
                ordered.append(item)
                used_ids.add(PreweddingSmartRefiner.item_id(item))

        leftovers = [x for x in remaining if PreweddingSmartRefiner.item_id(x) not in used_ids]
        leftovers.sort(key=lambda x: PreweddingSmartRefiner.score_of(x), reverse=True)
        ordered.extend(leftovers)

        return ordered

    @staticmethod
    def section_matches(item: dict[str, Any], section: str) -> bool:
        text = PreweddingSmartRefiner.item_text(item)
        s = section.replace("_", " ")

        if section in text or s in text:
            return True

        groups = {
            "hook": ["hook", "best", "fashion", "motion", "close"],
            "couple": ["couple", "walk", "holding", "hug", "look"],
            "fashion": ["fashion", "pose", "dress", "spin"],
            "location": ["location", "wide", "sunset", "beach", "forest", "city", "architecture"],
            "emotion": ["emotion", "close", "hug", "kiss", "look"],
            "end": ["end", "wide", "kiss", "hug", "walking"],
        }

        for group, words in groups.items():
            if group in section:
                return any(w in text for w in words)

        return False

    @staticmethod
    def fit_duration(timeline: list[dict[str, Any]], rules: dict[str, Any], intent: str) -> list[dict[str, Any]]:
        target = float(rules.get("target_duration", 60.0))
        min_clip = float(rules.get("min_clip", 1.0))
        max_clip = float(rules.get("max_clip", 3.5))
        default_clip = float(rules.get("default_clip", 2.5))

        out = []
        cursor = 0.0

        for item in timeline:
            if cursor >= target:
                break

            clip = dict(item)
            duration = PreweddingSmartRefiner.to_float(clip.get("timeline_duration"), default_clip)
            duration = max(min_clip, min(max_clip, duration))

            source_duration = PreweddingSmartRefiner.to_float(clip.get("source_duration"), 0.0)
            if source_duration > 0:
                duration = min(duration, source_duration)

            remaining = target - cursor
            if duration > remaining:
                if remaining >= min_clip:
                    duration = remaining
                else:
                    break

            clip["timeline_index"] = len(out) + 1
            clip["timeline_start"] = round(cursor, 3)
            clip["timeline_duration"] = round(duration, 3)
            clip["timeline_end"] = round(cursor + duration, 3)
            clip["source_start"] = PreweddingSmartRefiner.to_float(clip.get("source_start"), 0.0)
            clip["source_end"] = round(clip["source_start"] + duration, 3)
            clip["refined"] = True

            out.append(clip)
            cursor += duration

        return out

    @staticmethod
    def quality_notes(timeline: list[dict[str, Any]], rules: dict[str, Any]) -> list[str]:
        notes = []

        if not timeline:
            notes.append("Timeline rỗng sau refine.")
            return notes

        target = float(rules.get("target_duration", 0))
        actual = sum(float(x.get("timeline_duration", 0)) for x in timeline)

        if target and actual < target * 0.8:
            notes.append(f"Duration còn thiếu: {round(actual, 2)}s / target {target}s. Cần thêm source tốt hơn.")

        if PreweddingSmartRefiner.score_of(timeline[0]) < float(rules.get("strong_score", 70)):
            notes.append("Hook đầu chưa thật mạnh. Nên review lại shot đầu trong Premiere.")

        sources = [str(x.get("source_key", "")) for x in timeline]
        for i in range(1, len(sources)):
            if sources[i] and sources[i] == sources[i - 1]:
                notes.append(f"Còn 2 shot liền nhau cùng source ở vị trí {i} và {i+1}.")
                break

        return notes

    @staticmethod
    def make_action(action: str, old_item: dict[str, Any] | None, new_item: dict[str, Any] | None, reason: str) -> dict[str, Any]:
        return {
            "action": action,
            "reason": reason,
            "old_file": old_item.get("file") if old_item else None,
            "old_score": old_item.get("ai_score") if old_item else None,
            "old_section": old_item.get("section") if old_item else None,
            "new_file": new_item.get("file") if new_item else None,
            "new_score": new_item.get("ai_score") if new_item else None,
            "new_section": new_item.get("section") if new_item else None,
        }

    @staticmethod
    def guess_section(item: dict[str, Any], intent: str) -> str:
        text = PreweddingSmartRefiner.item_text(item)

        if any(w in text for w in ["hook", "best", "fashion", "motion", "dress", "close"]):
            return "hook"

        if any(w in text for w in ["walk", "walking", "holding", "couple"]):
            return "couple_motion"

        if any(w in text for w in ["fashion", "pose", "dress", "spin"]):
            return "fashion_motion"

        if any(w in text for w in ["location", "wide", "sunset", "beach", "forest", "city"]):
            return "location_beauty"

        if any(w in text for w in ["emotion", "close", "hug", "kiss", "look"]):
            return "romantic_end"

        return "best"

    @staticmethod
    def guess_role(item: dict[str, Any], intent: str) -> str:
        section = PreweddingSmartRefiner.guess_section(item, intent)

        mapping = {
            "hook": "hook",
            "couple_motion": "couple_motion",
            "fashion_motion": "fashion_motion",
            "location_beauty": "location_beauty",
            "romantic_end": "emotion",
        }

        return mapping.get(section, "best_candidate")

    @staticmethod
    def default_transition(item: dict[str, Any], intent: str) -> str:
        text = PreweddingSmartRefiner.item_text(item)

        if intent.startswith("prewedding_reel"):
            if any(w in text for w in ["motion", "walk", "spin", "dress"]):
                return "beat_cut_or_soft_whoosh"
            return "clean_cut_on_beat"

        if any(w in text for w in ["location", "wide"]):
            return "slow_push_or_clean_cut"

        return "clean_cut"

    @staticmethod
    def default_speed(item: dict[str, Any], intent: str) -> str:
        text = PreweddingSmartRefiner.item_text(item)

        if intent.startswith("prewedding_reel"):
            if any(w in text for w in ["motion", "walk", "spin", "dress"]):
                return "normal_or_80_percent_slow_if_smooth"
            return "normal_speed_keep_short"

        if any(w in text for w in ["emotion", "hug", "kiss", "walk", "motion"]):
            return "consider_70_80_percent_slow_motion"

        return "normal_speed"

    @staticmethod
    def default_crop(item: dict[str, Any], rules: dict[str, Any], intent: str) -> str:
        text = PreweddingSmartRefiner.item_text(item)
        if str(rules.get("aspect")) == "9:16":
            if any(w in text for w in ["wide", "location"]):
                return "vertical_crop_keep_couple_and_location"
            if any(w in text for w in ["walk", "motion", "spin"]):
                return "vertical_crop_follow_couple_motion"
            return "vertical_crop_center_face_or_couple"

        return "keep_original_16x9"

    @staticmethod
    def role_family(role: str) -> str:
        role = role.lower()
        if "hook" in role:
            return "hook"
        if "couple" in role or "walk" in role:
            return "couple"
        if "fashion" in role or "pose" in role:
            return "fashion"
        if "location" in role or "wide" in role:
            return "location"
        if "emotion" in role or "close" in role or "romantic" in role:
            return "emotion"
        return "best"

    @staticmethod
    def item_text(item: dict[str, Any]) -> str:
        parts = []
        for key in [
            "file",
            "_filename",
            "_search_text",
            "section",
            "roughcut_role",
            "ai_rank_hint",
            "ai_reasons",
            "ai_penalties",
            "transition_hint",
            "speed_hint",
            "crop_hint",
            "note",
            "review_note",
        ]:
            value = item.get(key)
            if isinstance(value, list):
                parts.extend(str(x) for x in value)
            elif value is not None:
                parts.append(str(value))
        return " ".join(parts).lower()

    @staticmethod
    def score_of(item: dict[str, Any]) -> float:
        return PreweddingSmartRefiner.to_float(item.get("ai_score"), 0.0)

    @staticmethod
    def item_id(item: dict[str, Any]) -> str:
        return f"{item.get('file') or item.get('_filename')}|{item.get('source_start') or item.get('start')}|{item.get('source_end') or item.get('end')}|{item.get('section')}"

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
        input_doc: dict[str, Any],
        input_file: Path,
        refined_timeline: list[dict[str, Any]],
        replacements: list[dict[str, Any]],
        warnings: list[str],
        rules: dict[str, Any],
        intent: str,
        score_pool_doc: dict[str, Any],
    ) -> dict[str, Any]:
        actual = round(sum(float(x.get("timeline_duration", 0)) for x in refined_timeline), 3)
        now = datetime.now().isoformat(timespec="seconds")

        return {
            "ok": True,
            "module": "050_prewedding_smart_refiner",
            "version": "0.50",
            "created_at": now,
            "updated_at": now,
            "project_root": str(self.project_root),
            "input_file": str(input_file),
            "input_module": input_doc.get("module"),
            "intent": intent,
            "label": rules.get("label"),
            "aspect": rules.get("aspect"),
            "target_duration_seconds": float(rules.get("target_duration", 0)),
            "actual_duration_seconds": actual,
            "selected_count": len(refined_timeline),
            "replacement_count": len(replacements),
            "warning_count": len(warnings),
            "score_pool_available": bool(score_pool_doc),
            "source_score_intent": score_pool_doc.get("intent"),
            "refiner_rules": rules,
            "timeline": refined_timeline,
            "replacements": replacements,
            "warnings": warnings,
            "manual_review_items": self.to_manual_review_items(refined_timeline),
            "edit_prompt": self.build_edit_prompt(intent, rules, refined_timeline, replacements, warnings),
            "next_steps": [
                "Module 049: export_prewedding_xml.py để xuất XML Premiere từ timeline refined này.",
                "Nếu là reel, dùng preset vertical_1080_25p.",
                "Trong Premiere, review hook đầu, crop dọc, và nhịp beat.",
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
                "refiner_action": clip.get("refiner_action"),
                "refiner_reason": clip.get("refiner_reason"),
                "transition_hint": clip.get("transition_hint"),
                "speed_hint": clip.get("speed_hint"),
                "crop_hint": clip.get("crop_hint"),
                "note": f"Module050 refined: {clip.get('roughcut_role')} score {clip.get('ai_score')}",
            })
        return items

    @staticmethod
    def build_edit_prompt(
        intent: str,
        rules: dict[str, Any],
        timeline: list[dict[str, Any]],
        replacements: list[dict[str, Any]],
        warnings: list[str],
    ) -> str:
        lines = [
            "STT AI Editor - Prewedding Smart Refined Prompt",
            "=" * 72,
            f"Intent: {intent}",
            f"Label: {rules.get('label')}",
            f"Aspect: {rules.get('aspect')}",
            f"Target duration: {rules.get('target_duration')}s",
            "",
            "Dựng theo hướng:",
        ]

        if "reel" in intent:
            lines += [
                "- Reel prewedding dọc 9:16.",
                "- Hook đầu phải đẹp, mạnh, có chuyển động/cảm xúc.",
                "- Cut theo beat, mỗi clip ngắn và rõ nội dung.",
                "- Ưu tiên couple, fashion pose, váy bay, đi bộ, close-up, location.",
                "- Crop dọc theo mặt/couple, tránh cắt đầu/cắt váy xấu.",
            ]
        else:
            lines += [
                "- Prewedding cinematic ngang 16:9.",
                "- Mượt, romantic, có location hook, couple walking, close-up cảm xúc.",
                "- Giữ nhịp chậm hơn reel, ưu tiên smooth motion.",
            ]

        if replacements:
            lines += ["", "Các thay đổi/refine:"]
            for item in replacements[:20]:
                lines.append(
                    f"- {item.get('action')}: {item.get('reason')} | "
                    f"{item.get('old_file')} -> {item.get('new_file')}"
                )

        if warnings:
            lines += ["", "Cần review thêm:"]
            for warning in warnings:
                lines.append(f"- {warning}")

        lines += ["", "Timeline refined:"]
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
            "refiner_action",
            "refiner_reason",
            "transition_hint",
            "speed_hint",
            "crop_hint",
        ]

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in timeline:
                writer.writerow({key: item.get(key, "") for key in fieldnames})

    @staticmethod
    def write_replacements_csv(path: Path, replacements: list[dict[str, Any]]) -> None:
        fieldnames = ["action", "reason", "old_file", "old_score", "old_section", "new_file", "new_score", "new_section"]

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in replacements:
                writer.writerow({key: item.get(key, "") for key in fieldnames})

    @staticmethod
    def render_text(doc: dict[str, Any]) -> str:
        lines = [
            "STT AI Editor - Prewedding Smart Refiner",
            "=" * 72,
            f"Intent: {doc.get('intent')}",
            f"Label: {doc.get('label')}",
            f"Aspect: {doc.get('aspect')}",
            f"Target: {doc.get('target_duration_seconds')}s",
            f"Actual: {doc.get('actual_duration_seconds')}s",
            f"Selected: {doc.get('selected_count')}",
            f"Replacements: {doc.get('replacement_count')}",
            f"Warnings: {doc.get('warning_count')}",
            "",
            "Warnings:",
        ]

        for warning in doc.get("warnings", []):
            lines.append(f"- {warning}")

        lines += ["", "Replacements:"]
        for item in doc.get("replacements", [])[:30]:
            lines.append(
                f"- {item.get('action')} | {item.get('reason')} | "
                f"{item.get('old_file')} -> {item.get('new_file')}"
            )

        lines += ["", "Timeline:"]
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
        repl_count = html.escape(str(doc.get("replacement_count", "")))

        warning_rows = "".join(f"<li>{html.escape(str(x))}</li>" for x in doc.get("warnings", [])) or "<li>No warnings</li>"

        rows = []
        for clip in doc.get("timeline", []):
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(clip.get('timeline_index', '')))}</td>"
                f"<td>{html.escape(str(clip.get('timeline_start', '')))} - {html.escape(str(clip.get('timeline_end', '')))}</td>"
                f"<td>{html.escape(str(clip.get('roughcut_role', '')))}</td>"
                f"<td>{html.escape(str(clip.get('section', '')))}</td>"
                f"<td>{html.escape(str(clip.get('ai_score', '')))}</td>"
                f"<td>{html.escape(str(clip.get('refiner_action', '')))}</td>"
                f"<td>{html.escape(str(clip.get('file', '')))}</td>"
                f"<td>{html.escape(str(clip.get('crop_hint', '')))}</td>"
                "</tr>"
            )

        if not rows:
            rows.append("<tr><td colspan='8'>No refined clips</td></tr>")

        replacement_rows = []
        for item in doc.get("replacements", []):
            replacement_rows.append(
                "<tr>"
                f"<td>{html.escape(str(item.get('action', '')))}</td>"
                f"<td>{html.escape(str(item.get('reason', '')))}</td>"
                f"<td>{html.escape(str(item.get('old_file', '')))}</td>"
                f"<td>{html.escape(str(item.get('new_file', '')))}</td>"
                "</tr>"
            )

        if not replacement_rows:
            replacement_rows.append("<tr><td colspan='4'>No replacements</td></tr>")

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT Prewedding Smart Refiner</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1500px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
th, td {{ border-bottom: 1px solid #333; padding: 8px; vertical-align: top; }}
th {{ text-align: left; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 050</div>
  <h1>Prewedding Smart Refiner</h1>
  <p>Intent: <b>{intent}</b> / {label}</p>
  <p>Aspect: {aspect} | Target: {target}s | Actual: {actual}s | Selected: {selected} | Replacements: {repl_count}</p>

  <h2>Warnings</h2>
  <ul>{warning_rows}</ul>

  <h2>Replacements</h2>
  <table>
    <tr><th>Action</th><th>Reason</th><th>Old</th><th>New</th></tr>
    {''.join(replacement_rows)}
  </table>

  <h2>Refined Timeline</h2>
  <table>
    <tr>
      <th>#</th><th>Time</th><th>Role</th><th>Section</th><th>Score</th><th>Action</th><th>File</th><th>Crop</th>
    </tr>
    {''.join(rows)}
  </table>
</div>
</body>
</html>
'''


def refine_prewedding_roughcut(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str | None = None,
    target_duration: float | None = None,
    write_selection_compat: bool = True,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PreweddingSmartRefiner(project_root=project_root).refine(
        intent=intent,
        target_duration=target_duration,
        write_selection_compat=write_selection_compat,
        open_folder=open_folder,
    )
