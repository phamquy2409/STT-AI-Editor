
from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


PREWEDDING_INTENTS: dict[str, dict[str, Any]] = {
    "prewedding_cinematic": {
        "label": "Prewedding Cinematic",
        "target_duration_seconds": 120,
        "aspect": "16:9",
        "pace": "cinematic, emotional, smooth",
        "prefer": [
            "couple",
            "bride_groom",
            "walking",
            "holding_hands",
            "hug",
            "look_at_each_other",
            "dress_motion",
            "slow_motion",
            "location_beauty",
            "sunset",
            "close_up",
            "soft_emotion",
            "stable_motion",
            "beautiful_light",
        ],
        "avoid": [
            "ceremony",
            "gia_tien",
            "reception",
            "mc",
            "stage",
            "banquet",
            "static_long",
            "shaky",
            "out_focus",
            "empty",
        ],
        "structure": [
            "location_hook",
            "couple_walking",
            "closeup_emotion",
            "dress_or_motion",
            "wide_location",
            "ending_romantic",
        ],
    },
    "prewedding_reel_30s": {
        "label": "Prewedding Reel 30s",
        "target_duration_seconds": 30,
        "aspect": "9:16",
        "pace": "fast hook, beat cut, beautiful-first",
        "prefer": [
            "best_shot",
            "hook",
            "couple",
            "walking",
            "pose",
            "fashion",
            "dress_motion",
            "spin",
            "close_up",
            "look_at_camera",
            "look_at_each_other",
            "location_beauty",
            "stable_motion",
            "beat",
            "vertical_safe",
        ],
        "avoid": [
            "long_story",
            "ceremony",
            "gia_tien",
            "reception",
            "static_long",
            "empty",
            "shaky",
            "out_focus",
        ],
        "structure": [
            "best_hook_1_3s",
            "fast_couple_motion",
            "fashion_pose",
            "location_flash",
            "emotional_closeup",
            "strong_end",
        ],
    },
    "prewedding_reel_60s": {
        "label": "Prewedding Reel 60s",
        "target_duration_seconds": 60,
        "aspect": "9:16",
        "pace": "fast but emotional reel",
        "prefer": [
            "hook",
            "couple",
            "walking",
            "holding_hands",
            "pose",
            "dress_motion",
            "location_beauty",
            "slow_motion",
            "close_up",
            "emotion",
            "stable_motion",
            "beautiful_light",
            "vertical_safe",
        ],
        "avoid": [
            "ceremony",
            "gia_tien",
            "reception",
            "static_long",
            "empty",
            "shaky",
            "out_focus",
            "duplicate",
        ],
        "structure": [
            "hook",
            "couple_motion",
            "emotion",
            "location",
            "fashion",
            "romantic_end",
        ],
    },
    "prewedding_fashion": {
        "label": "Prewedding Fashion",
        "target_duration_seconds": 45,
        "aspect": "9:16",
        "pace": "fashion, clean, confident",
        "prefer": [
            "fashion",
            "pose",
            "look_at_camera",
            "dress",
            "makeup",
            "detail",
            "walking",
            "spin",
            "close_up",
            "medium_shot",
            "stable_motion",
            "beautiful_light",
        ],
        "avoid": [
            "ceremony",
            "gia_tien",
            "reception",
            "too_emotional_slow",
            "static_long",
            "shaky",
            "out_focus",
        ],
        "structure": [
            "fashion_hook",
            "pose_series",
            "walk",
            "dress_motion",
            "closeup",
            "signature_end",
        ],
    },
    "prewedding_location_film": {
        "label": "Prewedding Location Film",
        "target_duration_seconds": 90,
        "aspect": "16:9",
        "pace": "location beauty + couple story",
        "prefer": [
            "wide",
            "location",
            "landscape",
            "architecture",
            "beach",
            "forest",
            "city",
            "sunset",
            "couple_small_in_frame",
            "walking",
            "stable_motion",
            "drone_like",
        ],
        "avoid": [
            "ceremony",
            "gia_tien",
            "reception",
            "banquet",
            "random_people",
            "shaky",
            "out_focus",
            "empty_bad",
        ],
        "structure": [
            "wide_location",
            "couple_enters",
            "location_motion",
            "couple_closeup",
            "wide_end",
        ],
    },
}


WEDDING_INTENTS: dict[str, dict[str, Any]] = {
    "wedding_teaser_60s": {
        "label": "Wedding Teaser 60s",
        "target_duration_seconds": 60,
        "aspect": "16:9",
        "pace": "fast emotional wedding teaser",
        "prefer": [
            "bride_groom",
            "vow",
            "emotion",
            "reaction",
            "reception",
            "dance_party",
            "beautiful_motion",
        ],
        "avoid": [
            "static_long",
            "duplicate",
            "shaky",
            "out_focus",
            "empty",
        ],
    },
    "wedding_highlight_3min": {
        "label": "Wedding Highlight 3min",
        "target_duration_seconds": 180,
        "aspect": "16:9",
        "pace": "cinematic emotional wedding highlight",
        "prefer": [
            "bride_groom",
            "vow",
            "gia_tien",
            "ruoc_dau",
            "reception",
            "family_reaction",
            "dance_party",
        ],
        "avoid": [
            "gia_tien_static_long",
            "duplicate",
            "shaky",
            "out_focus",
            "empty",
        ],
    },
    "review_culling": {
        "label": "Review Culling",
        "target_duration_seconds": None,
        "aspect": "any",
        "pace": "select usable footage only",
        "prefer": [
            "sharp",
            "stable",
            "action",
            "content",
            "good_expression",
            "camera_motion",
        ],
        "avoid": [
            "shaky",
            "out_focus",
            "empty",
            "bad_head_tail",
            "no_content",
        ],
    },
}


ALL_INTENTS: dict[str, dict[str, Any]] = {}
ALL_INTENTS.update(PREWEDDING_INTENTS)
ALL_INTENTS.update(WEDDING_INTENTS)


@dataclass
class AIShotScorerConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    intent: str = "prewedding_reel_60s"
    top_n: int = 120
    open_folder: bool = True


class AIShotScorerV1:
    # Module 046.
    # Scores shots for wedding/prewedding/reel intents.
    #
    # This is not yet the final auto-editor.
    # It creates scored candidate lists that Module 047+ can use to pick shots.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()

        self.memory_path = self.project_root / "stt_ai_style_memory_v2.json"
        self.appdata_memory_path = self.appdata_dir / "stt_ai_style_memory_v2.json"
        self.style_profile_path = self.project_root / "stt_wedding_style_profile.json"
        self.manual_selection_path = self.project_root / "manual_selection.json"
        self.feedback_profile_path = self.project_root / "stt_feedback_profile.json"

        self.project_score_path = self.project_root / "stt_ai_shot_scores_v1.json"
        self.appdata_score_path = self.appdata_dir / "stt_ai_shot_scores_v1.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    def score(
        self,
        intent: str = "prewedding_reel_60s",
        top_n: int = 120,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        if intent not in ALL_INTENTS:
            raise ValueError(
                f"Unknown intent: {intent}. Available: {', '.join(sorted(ALL_INTENTS))}"
            )

        memory = self.load_json_first([self.memory_path, self.appdata_memory_path])
        style_profile = self.load_json(self.style_profile_path)
        feedback_profile = self.load_json(self.feedback_profile_path)

        candidates = self.collect_candidates()

        scored = []
        for index, item in enumerate(candidates):
            scored_item = self.score_item(
                item=item,
                index=index,
                intent=intent,
                memory=memory,
                style_profile=style_profile,
                feedback_profile=feedback_profile,
            )
            scored.append(scored_item)

        scored.sort(key=lambda x: x["ai_score"], reverse=True)

        selected = scored[: max(1, top_n)]

        now = datetime.now().isoformat(timespec="seconds")
        intent_rules = ALL_INTENTS[intent]

        result = {
            "ok": True,
            "module": "046_ai_shot_scorer_v1",
            "version": "0.46",
            "created_at": now,
            "updated_at": now,
            "project_root": str(self.project_root),
            "intent": intent,
            "intent_rules": intent_rules,
            "candidate_count": len(candidates),
            "scored_count": len(scored),
            "selected_count": len(selected),
            "source_files": self.describe_sources(),
            "memory_available": bool(memory),
            "style_profile_available": bool(style_profile),
            "feedback_profile_available": bool(feedback_profile),
            "summary": self.build_summary(scored, selected, intent),
            "scored_items": scored,
            "selected_items": selected,
            "next_steps": [
                "Module 047 sẽ dùng selected_items để chọn shot tự động theo intent.",
                "Với prewedding reel, dùng intent prewedding_reel_30s hoặc prewedding_reel_60s.",
                "Với prewedding cinematic, dùng intent prewedding_cinematic.",
            ],
        }

        self.project_root.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.appdata_dir.mkdir(parents=True, exist_ok=True)

        self.project_score_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        self.appdata_score_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        report_dir = self.exports_dir / f"ai_shot_scorer_v1_{intent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_json = report_dir / "stt_ai_shot_scores_v1.json"
        report_csv = report_dir / "AI_SHOT_SCORES.csv"
        selected_csv = report_dir / "AI_SELECTED_TOP_SHOTS.csv"
        report_txt = report_dir / "AI_SHOT_SCORER_SUMMARY.txt"
        report_html = report_dir / "AI_SHOT_SCORER_SUMMARY.html"

        report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        self.write_csv(report_csv, scored)
        self.write_csv(selected_csv, selected)
        report_txt.write_text(self.render_text(result), encoding="utf-8")
        report_html.write_text(self.render_html(result), encoding="utf-8")

        result_paths = {
            "report_dir": str(report_dir),
            "report_json": str(report_json),
            "report_csv": str(report_csv),
            "selected_csv": str(selected_csv),
            "report_txt": str(report_txt),
            "report_html": str(report_html),
            "project_score_path": str(self.project_score_path),
            "appdata_score_path": str(self.appdata_score_path),
        }

        result["paths"] = result_paths

        (report_dir / "ai_shot_scorer_result.json").write_text(
            json.dumps(result_paths | {"ok": True}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(report_dir)
            except Exception:
                pass

        return result_paths | {
            "ok": True,
            "intent": intent,
            "candidate_count": len(candidates),
            "scored_count": len(scored),
            "selected_count": len(selected),
            "top_score": selected[0]["ai_score"] if selected else 0,
        }


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

    def describe_sources(self) -> dict[str, str]:
        return {
            "manual_selection": str(self.manual_selection_path),
            "ai_style_memory_v2": str(self.memory_path),
            "appdata_ai_style_memory_v2": str(self.appdata_memory_path),
            "style_profile": str(self.style_profile_path),
            "feedback_profile": str(self.feedback_profile_path),
        }

    def collect_candidates(self) -> list[dict[str, Any]]:
        # Priority:
        # 1. manual_selection.json because it has user decisions.
        # 2. latest candidate/scored JSON in exports.
        # 3. fallback from XML-ish report JSONs if any.
        manual = self.load_json(self.manual_selection_path)
        manual_items = self.extract_items(manual, source="manual_selection")
        if manual_items:
            return manual_items

        export_items = self.collect_from_exports()
        if export_items:
            return export_items

        return []

    def collect_from_exports(self) -> list[dict[str, Any]]:
        if not self.exports_dir.exists():
            return []

        keywords = [
            "candidate",
            "learned",
            "roughcut",
            "manual",
            "selection",
            "timeline",
            "segments",
        ]

        json_files = [
            p for p in self.exports_dir.glob("**/*.json")
            if p.is_file()
            and "_archive" not in p.parts
            and any(k in p.name.lower() or k in str(p.parent).lower() for k in keywords)
        ]

        json_files = sorted(json_files, key=lambda p: p.stat().st_mtime, reverse=True)

        for path in json_files[:30]:
            data = self.load_json(path)
            items = self.extract_items(data, source=str(path))
            if len(items) >= 3:
                return items

        return []

    @staticmethod
    def extract_items(data: Any, source: str = "") -> list[dict[str, Any]]:
        if not data:
            return []

        if isinstance(data, list):
            return [AIShotScorerV1.normalize_item(x, source) for x in data if isinstance(x, dict)]

        if not isinstance(data, dict):
            return []

        for key in [
            "items",
            "segments",
            "clips",
            "candidates",
            "selected_items",
            "scored_items",
            "timeline",
            "shots",
            "results",
        ]:
            value = data.get(key)
            if isinstance(value, list):
                return [AIShotScorerV1.normalize_item(x, source) for x in value if isinstance(x, dict)]

        # Some reports may nest data under result/data.
        for key in ["result", "data", "payload"]:
            value = data.get(key)
            items = AIShotScorerV1.extract_items(value, source=source)
            if items:
                return items

        return []

    @staticmethod
    def normalize_item(item: dict[str, Any], source: str = "") -> dict[str, Any]:
        normalized = dict(item)
        normalized["_source"] = source

        filename = (
            item.get("filename")
            or item.get("file")
            or item.get("clip")
            or item.get("video")
            or item.get("path")
            or item.get("source_path")
            or item.get("media_path")
            or ""
        )
        normalized["_filename"] = str(filename)

        text_parts = []
        for key in [
            "filename",
            "file",
            "clip",
            "video",
            "path",
            "source_path",
            "scene",
            "scene_type",
            "wedding_scene",
            "category",
            "tag",
            "tags",
            "note",
            "notes",
            "description",
            "label",
        ]:
            value = item.get(key)
            if isinstance(value, list):
                text_parts.extend(str(x) for x in value)
            elif value is not None:
                text_parts.append(str(value))

        normalized["_search_text"] = " ".join(text_parts).lower()
        normalized["_status"] = AIShotScorerV1.normalize_status(item)
        normalized["_liked"] = bool(item.get("liked") or item.get("like") or item.get("favorite") or item.get("starred"))
        normalized["_duration"] = AIShotScorerV1.extract_duration(item)

        return normalized

    @staticmethod
    def normalize_status(item: dict[str, Any]) -> str:
        status = str(
            item.get("status")
            or item.get("decision")
            or item.get("manual_status")
            or item.get("label")
            or ""
        ).strip().lower()

        mapping = {
            "kept": "keep",
            "yes": "keep",
            "accept": "keep",
            "accepted": "keep",
            "selected": "keep",
            "no": "reject",
            "remove": "reject",
            "deleted": "reject",
            "trash": "reject",
            "bad": "reject",
        }

        return mapping.get(status, status or "unknown")

    @staticmethod
    def extract_duration(item: dict[str, Any]) -> float | None:
        for key in ["duration", "duration_sec", "duration_seconds", "length", "len"]:
            if key in item:
                try:
                    return float(item[key])
                except Exception:
                    pass

        start = None
        end = None

        for key in ["start", "start_sec", "start_seconds", "in", "in_sec"]:
            if key in item:
                try:
                    start = float(item[key])
                    break
                except Exception:
                    pass

        for key in ["end", "end_sec", "end_seconds", "out", "out_sec"]:
            if key in item:
                try:
                    end = float(item[key])
                    break
                except Exception:
                    pass

        if start is not None and end is not None and end > start:
            return end - start

        return None

    def score_item(
        self,
        item: dict[str, Any],
        index: int,
        intent: str,
        memory: dict[str, Any],
        style_profile: dict[str, Any],
        feedback_profile: dict[str, Any],
    ) -> dict[str, Any]:
        rules = ALL_INTENTS[intent]
        text = item.get("_search_text", "")
        status = item.get("_status", "unknown")
        liked = bool(item.get("_liked"))
        duration = item.get("_duration")

        score = 50.0
        reasons: list[str] = []
        penalties: list[str] = []

        # Manual user decision has highest importance.
        if status == "keep":
            score += 20
            reasons.append("manual_keep")
        elif status == "maybe":
            score += 8
            reasons.append("manual_maybe")
        elif status == "reject":
            score -= 35
            penalties.append("manual_reject")

        if liked:
            score += 18
            reasons.append("liked_by_user")

        # Intent keyword scoring.
        prefer_matches = self.match_keywords(text, rules.get("prefer", []))
        avoid_matches = self.match_keywords(text, rules.get("avoid", []))

        if prefer_matches:
            add = min(24, 4 * len(prefer_matches))
            score += add
            reasons.extend([f"prefer:{x}" for x in prefer_matches[:8]])

        if avoid_matches:
            sub = min(35, 7 * len(avoid_matches))
            score -= sub
            penalties.extend([f"avoid:{x}" for x in avoid_matches[:8]])

        # Prewedding-specific bias.
        if intent.startswith("prewedding"):
            pre_add, pre_reasons, pre_penalties = self.score_prewedding_text(text, intent)
            score += pre_add
            reasons.extend(pre_reasons)
            penalties.extend(pre_penalties)

        # Wedding-specific bias.
        if intent.startswith("wedding"):
            wed_add, wed_reasons, wed_penalties = self.score_wedding_text(text)
            score += wed_add
            reasons.extend(wed_reasons)
            penalties.extend(wed_penalties)

        # Duration preference.
        dur_add, dur_reason = self.score_duration(duration, intent)
        score += dur_add
        if dur_reason:
            if dur_add >= 0:
                reasons.append(dur_reason)
            else:
                penalties.append(dur_reason)

        # Existing numeric score from older modules.
        old_score = self.extract_existing_score(item)
        if old_score is not None:
            score += max(-10, min(15, (old_score - 50) * 0.18))
            reasons.append(f"old_score:{round(old_score, 2)}")

        # Memory weights from 045.
        memory_weights = ((memory or {}).get("shot_selection_weights") or {})
        if memory_weights:
            score += self.apply_memory_weights(text, memory_weights, reasons, penalties)

        # Stable deterministic small tie-breaker.
        score += max(0, 3 - (index % 7) * 0.15)

        score = round(max(0.0, min(100.0, score)), 3)

        out = dict(item)
        out["ai_score"] = score
        out["ai_intent"] = intent
        out["ai_reasons"] = reasons[:30]
        out["ai_penalties"] = penalties[:30]
        out["ai_rank_hint"] = self.rank_hint(score)
        out["ai_use_for_prewedding"] = intent.startswith("prewedding") and score >= 60
        out["ai_use_for_reel"] = intent.startswith("prewedding_reel") and score >= 62
        out["ai_duration_seconds"] = duration

        return out

    @staticmethod
    def match_keywords(text: str, keywords: list[str]) -> list[str]:
        matches = []

        for kw in keywords:
            normalized_kw = str(kw).lower().strip()
            if not normalized_kw:
                continue

            variants = {
                normalized_kw,
                normalized_kw.replace("_", " "),
                normalized_kw.replace("-", " "),
            }

            for variant in variants:
                if variant and variant in text:
                    matches.append(normalized_kw)
                    break

        return matches

    @staticmethod
    def score_prewedding_text(text: str, intent: str) -> tuple[float, list[str], list[str]]:
        score = 0.0
        reasons: list[str] = []
        penalties: list[str] = []

        positive_groups = {
            "couple_moment": ["couple", "prewedding", "bride groom", "bride_groom", "cdcr", "co dau", "chu re"],
            "romantic_action": ["holding hand", "holding_hands", "nam tay", "nắm tay", "hug", "om", "ôm", "kiss", "look at each other", "nhin nhau", "nhìn nhau"],
            "motion": ["walk", "walking", "di bo", "đi bộ", "spin", "xoay", "dress motion", "vay bay", "váy bay", "slow motion", "slowmo"],
            "fashion_pose": ["fashion", "pose", "posing", "look at camera", "nhin may", "nhìn máy"],
            "location": ["location", "wide", "sunset", "beach", "forest", "city", "dalat", "da lat", "nha trang", "hotel", "street", "architecture"],
            "beauty": ["close up", "closeup", "detail", "makeup", "dress", "veil", "light", "flare", "golden"],
        }

        for name, words in positive_groups.items():
            if any(w in text for w in words):
                score += 5.5
                reasons.append(f"prewedding_{name}")

        ceremony_bad = ["gia tien", "gia_tien", "lễ", "le gia tien", "ceremony", "reception", "banquet", "stage", "mc", "table", "speech"]
        if any(w in text for w in ceremony_bad):
            score -= 18
            penalties.append("prewedding_avoid_wedding_ceremony_content")

        if intent.startswith("prewedding_reel"):
            reel_good = ["vertical", "reel", "short", "hook", "beat", "fast", "fashion", "motion"]
            if any(w in text for w in reel_good):
                score += 6
                reasons.append("reel_friendly")

        return score, reasons, penalties

    @staticmethod
    def score_wedding_text(text: str) -> tuple[float, list[str], list[str]]:
        score = 0.0
        reasons: list[str] = []
        penalties: list[str] = []

        wedding_good = ["vow", "ceremony", "gia tien", "gia_tien", "ruoc dau", "rước dâu", "reception", "dance", "family", "reaction"]
        if any(w in text for w in wedding_good):
            score += 8
            reasons.append("wedding_story_content")

        return score, reasons, penalties

    @staticmethod
    def score_duration(duration: float | None, intent: str) -> tuple[float, str]:
        if duration is None:
            return 0.0, ""

        if intent == "prewedding_reel_30s":
            if 1.0 <= duration <= 4.0:
                return 5.0, "duration_good_for_30s_reel"
            if duration > 8.0:
                return -4.0, "duration_long_for_30s_reel"

        if intent == "prewedding_reel_60s":
            if 1.2 <= duration <= 5.5:
                return 4.0, "duration_good_for_60s_reel"
            if duration > 10.0:
                return -3.5, "duration_long_for_reel"

        if intent == "prewedding_cinematic":
            if 2.0 <= duration <= 8.0:
                return 4.0, "duration_good_for_cinematic"
            if duration < 0.7:
                return -2.5, "duration_too_short"

        if intent == "review_culling":
            if duration >= 1.0:
                return 2.0, "duration_usable"

        return 0.0, ""

    @staticmethod
    def extract_existing_score(item: dict[str, Any]) -> float | None:
        for key in ["score", "ai_score", "quality_score", "final_score", "learned_score"]:
            if key in item:
                try:
                    return float(item[key])
                except Exception:
                    pass
        return None

    @staticmethod
    def apply_memory_weights(
        text: str,
        weights: dict[str, Any],
        reasons: list[str],
        penalties: list[str],
    ) -> float:
        delta = 0.0

        positive_keys = [
            "bride_groom",
            "vow_audio_good",
            "emotional_reaction",
            "stable_motion",
            "sharp_focus",
            "dance_party_final",
            "liked_bonus",
            "manual_keep_bonus",
        ]

        negative_keys = [
            "gia_tien_static_long",
            "duplicate_similar",
            "shaky",
            "out_of_focus",
            "empty_head_tail",
            "no_content",
        ]

        for key in positive_keys:
            if key.replace("_", " ") in text or key in text:
                try:
                    value = float(weights.get(key, 1.0))
                    add = max(0.0, (value - 1.0) * 10)
                    delta += add
                    if add:
                        reasons.append(f"memory_weight:{key}")
                except Exception:
                    pass

        for key in negative_keys:
            if key.replace("_", " ") in text or key in text:
                try:
                    value = float(weights.get(key, 1.0))
                    sub = max(0.0, (1.0 - value) * 18)
                    delta -= sub
                    if sub:
                        penalties.append(f"memory_penalty:{key}")
                except Exception:
                    pass

        return delta

    @staticmethod
    def rank_hint(score: float) -> str:
        if score >= 85:
            return "A_keep_priority"
        if score >= 72:
            return "B_good_candidate"
        if score >= 58:
            return "C_maybe"
        if score >= 40:
            return "D_low_priority"
        return "E_reject"

    @staticmethod
    def build_summary(scored: list[dict[str, Any]], selected: list[dict[str, Any]], intent: str) -> dict[str, Any]:
        if not scored:
            return {
                "intent": intent,
                "message": "Không có candidate để chấm điểm. Hãy chạy pipeline/manual review trước.",
            }

        scores = [float(x["ai_score"]) for x in scored]
        rank_counts: dict[str, int] = {}
        for item in scored:
            rank = item.get("ai_rank_hint", "unknown")
            rank_counts[rank] = rank_counts.get(rank, 0) + 1

        return {
            "intent": intent,
            "score_avg": round(sum(scores) / len(scores), 3),
            "score_min": round(min(scores), 3),
            "score_max": round(max(scores), 3),
            "rank_counts": rank_counts,
            "top_10": [
                {
                    "score": x["ai_score"],
                    "rank": x["ai_rank_hint"],
                    "file": x.get("_filename", ""),
                    "reasons": x.get("ai_reasons", [])[:6],
                }
                for x in selected[:10]
            ],
        }

    @staticmethod
    def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
        fieldnames = [
            "ai_score",
            "ai_rank_hint",
            "ai_intent",
            "_filename",
            "_status",
            "_liked",
            "ai_duration_seconds",
            "ai_reasons",
            "ai_penalties",
            "_source",
        ]

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in items:
                row = {}
                for key in fieldnames:
                    value = item.get(key, "")
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value, ensure_ascii=False)
                    row[key] = value
                writer.writerow(row)

    @staticmethod
    def render_text(result: dict[str, Any]) -> str:
        summary = result.get("summary", {})
        intent_rules = result.get("intent_rules", {})

        lines = [
            "STT AI Editor - AI Shot Scorer V1",
            "=" * 72,
            f"Intent: {result.get('intent')}",
            f"Label: {intent_rules.get('label')}",
            f"Aspect: {intent_rules.get('aspect')}",
            f"Target duration: {intent_rules.get('target_duration_seconds')}",
            f"Candidates: {result.get('candidate_count')}",
            f"Selected: {result.get('selected_count')}",
            "",
            "Summary:",
            json.dumps(summary, ensure_ascii=False, indent=2),
            "",
            "Top shots:",
        ]

        for item in result.get("selected_items", [])[:20]:
            lines.append(
                f"- {item.get('ai_score')} | {item.get('ai_rank_hint')} | {item.get('_filename')} | {item.get('ai_reasons', [])[:5]}"
            )

        return "\n".join(lines)

    @staticmethod
    def render_html(result: dict[str, Any]) -> str:
        import html

        intent = html.escape(str(result.get("intent", "")))
        intent_rules = result.get("intent_rules", {})
        label = html.escape(str(intent_rules.get("label", "")))
        aspect = html.escape(str(intent_rules.get("aspect", "")))
        candidates = html.escape(str(result.get("candidate_count", 0)))
        selected = html.escape(str(result.get("selected_count", 0)))

        rows = []
        for item in result.get("selected_items", [])[:80]:
            reasons = ", ".join(str(x) for x in item.get("ai_reasons", [])[:6])
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(item.get('ai_score', '')))}</td>"
                f"<td>{html.escape(str(item.get('ai_rank_hint', '')))}</td>"
                f"<td>{html.escape(str(item.get('_filename', '')))}</td>"
                f"<td>{html.escape(reasons)}</td>"
                "</tr>"
            )

        if not rows:
            rows.append("<tr><td colspan='4'>No candidates</td></tr>")

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT AI Shot Scorer V1</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1200px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid #333; padding: 8px; vertical-align: top; }}
th {{ text-align: left; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 046</div>
  <h1>AI Shot Scorer V1</h1>
  <p>Intent: <b>{intent}</b> / {label}</p>
  <p>Aspect: {aspect}</p>
  <p>Candidates: {candidates} | Selected: {selected}</p>

  <h2>Top selected shots</h2>
  <table>
    <tr><th>Score</th><th>Rank</th><th>File</th><th>Reasons</th></tr>
    {''.join(rows)}
  </table>
</div>
</body>
</html>
'''


def run_ai_shot_scorer(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str = "prewedding_reel_60s",
    top_n: int = 120,
    open_folder: bool = True,
) -> dict[str, Any]:
    return AIShotScorerV1(project_root=project_root).score(
        intent=intent,
        top_n=top_n,
        open_folder=open_folder,
    )
