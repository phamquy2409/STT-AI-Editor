
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


@dataclass
class AIStyleMemoryConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    intent: str = "wedding_highlight"
    notes: str | None = None
    open_folder: bool = True


class AIStyleMemoryV2:
    # Module 045.
    # Builds the first consolidated "AI editing memory" from:
    # - Wedding Style Profile from Module 044
    # - Manual selection KEEP/MAYBE/REJECT/LIKE
    # - Feedback profile from Module 032
    # - Workflow preset from Module 030
    #
    # This does not auto-edit yet.
    # It creates the memory that upcoming AI modules can use to choose shots
    # and follow the user's wedding editing style.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()

        self.project_memory_path = self.project_root / "stt_ai_style_memory_v2.json"
        self.appdata_memory_path = self.appdata_dir / "stt_ai_style_memory_v2.json"

        self.style_profile_path = self.project_root / "stt_wedding_style_profile.json"
        self.appdata_style_profile_path = self.appdata_dir / "stt_wedding_style_profile.json"

        self.manual_selection_path = self.project_root / "manual_selection.json"
        self.feedback_profile_path = self.project_root / "stt_feedback_profile.json"
        self.workflow_preset_path = self.project_root / "stt_workflow_preset.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    def build(
        self,
        intent: str = "wedding_highlight",
        notes: str | None = None,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")

        style_profile = self.load_json_first([
            self.style_profile_path,
            self.appdata_style_profile_path,
        ])

        manual_selection = self.load_json(self.manual_selection_path)
        feedback_profile = self.load_json(self.feedback_profile_path)
        workflow_preset = self.load_json(self.workflow_preset_path)

        manual_summary = self.summarize_manual_selection(manual_selection)
        learned_bias = self.build_learned_bias(manual_summary, feedback_profile, style_profile)
        intent_map = self.build_intent_map(style_profile)

        memory = {
            "module": "045_ai_style_memory_v2",
            "version": "0.45",
            "created_at": now,
            "updated_at": now,
            "project_root": str(self.project_root),
            "intent": intent,
            "purpose": (
                "AI Style Memory V2 là bộ nhớ dựng cưới tổng hợp. "
                "Các module sau dùng file này để chọn shot, xếp timeline, hiểu gu dựng, "
                "và sau này gợi ý nhạc/SFX."
            ),
            "source_files": {
                "style_profile": str(self.style_profile_path),
                "appdata_style_profile": str(self.appdata_style_profile_path),
                "manual_selection": str(self.manual_selection_path),
                "feedback_profile": str(self.feedback_profile_path),
                "workflow_preset": str(self.workflow_preset_path),
            },
            "source_available": {
                "style_profile": bool(style_profile),
                "manual_selection": bool(manual_selection),
                "feedback_profile": bool(feedback_profile),
                "workflow_preset": bool(workflow_preset),
            },
            "style_profile": style_profile,
            "manual_summary": manual_summary,
            "feedback_summary": self.summarize_feedback_profile(feedback_profile),
            "workflow_preset": workflow_preset,
            "learned_bias": learned_bias,
            "intent_map": intent_map,
            "ai_editor_rules": self.build_ai_editor_rules(style_profile, learned_bias, intent_map),
            "shot_selection_weights": self.build_shot_selection_weights(learned_bias),
            "timeline_rules": self.build_timeline_rules(style_profile),
            "music_sfx_rules_future": self.build_music_sfx_rules(style_profile),
            "prompt_pack": self.build_prompt_pack(style_profile, learned_bias, intent_map),
            "next_module_usage": {
                "046": "Dùng memory này để chấm điểm shot theo gu dựng cưới.",
                "047": "Tạo AI shot selector dùng KEEP/REJECT/LIKE + style profile.",
                "050": "Học sâu hơn từ nhiều project khác nhau.",
                "055": "Dựng timeline theo style memory.",
                "060": "Nhận lệnh chữ và map vào intent_map.",
            },
            "user_notes": [],
        }

        if notes:
            memory["user_notes"].append({
                "created_at": now,
                "note": notes,
            })

        self.project_root.mkdir(parents=True, exist_ok=True)
        self.appdata_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        self.project_memory_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
        self.appdata_memory_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")

        report_dir = self.exports_dir / f"ai_style_memory_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_json = report_dir / "stt_ai_style_memory_v2.json"
        report_txt = report_dir / "AI_STYLE_MEMORY_SUMMARY.txt"
        report_html = report_dir / "AI_STYLE_MEMORY_SUMMARY.html"
        prompt_txt = report_dir / "AI_EDITOR_PROMPT_PACK.txt"

        report_json.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
        report_txt.write_text(self.render_text(memory), encoding="utf-8")
        report_html.write_text(self.render_html(memory), encoding="utf-8")
        prompt_txt.write_text(memory["prompt_pack"]["full_prompt"], encoding="utf-8")

        result = {
            "ok": True,
            "project_root": str(self.project_root),
            "memory": str(self.project_memory_path),
            "appdata_memory": str(self.appdata_memory_path),
            "report_dir": str(report_dir),
            "report_json": str(report_json),
            "report_txt": str(report_txt),
            "report_html": str(report_html),
            "prompt_txt": str(prompt_txt),
            "manual_keep": manual_summary.get("status_counts", {}).get("keep", 0),
            "manual_maybe": manual_summary.get("status_counts", {}).get("maybe", 0),
            "manual_reject": manual_summary.get("status_counts", {}).get("reject", 0),
            "manual_liked": manual_summary.get("liked_count", 0),
            "updated_at": now,
        }

        (report_dir / "ai_style_memory_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(report_dir)
            except Exception:
                pass

        return result

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
    def _iter_manual_items(manual_selection: dict[str, Any]) -> list[dict[str, Any]]:
        if not manual_selection:
            return []

        for key in ["items", "segments", "clips", "selection", "selected"]:
            value = manual_selection.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

        if isinstance(manual_selection, list):
            return [x for x in manual_selection if isinstance(x, dict)]  # type: ignore[arg-type]

        return []

    def summarize_manual_selection(self, manual_selection: dict[str, Any]) -> dict[str, Any]:
        items = self._iter_manual_items(manual_selection)

        status_counts = Counter()
        scene_counts = Counter()
        liked_count = 0
        note_terms = Counter()
        keep_examples: list[dict[str, Any]] = []
        reject_examples: list[dict[str, Any]] = []
        liked_examples: list[dict[str, Any]] = []
        durations_by_status: dict[str, list[float]] = defaultdict(list)

        for item in items:
            status = str(item.get("status") or item.get("decision") or item.get("label") or "").strip().lower()
            if not status:
                status = "unknown"

            if status in {"kept", "yes", "accept", "accepted"}:
                status = "keep"
            elif status in {"no", "remove", "deleted", "trash"}:
                status = "reject"

            status_counts[status] += 1

            liked = bool(item.get("liked") or item.get("like") or item.get("favorite") or item.get("starred"))
            if liked:
                liked_count += 1

            scene = (
                item.get("scene")
                or item.get("scene_type")
                or item.get("wedding_scene")
                or item.get("category")
                or item.get("tag")
                or "unknown"
            )
            scene_counts[str(scene).strip().lower()] += 1

            duration = self._extract_duration(item)
            if duration is not None:
                durations_by_status[status].append(duration)

            note = str(item.get("note") or item.get("notes") or "").strip().lower()
            if note:
                for word in note.replace(",", " ").replace(".", " ").split():
                    if len(word) >= 3:
                        note_terms[word] += 1

            slim = self._slim_item(item)

            if status == "keep" and len(keep_examples) < 12:
                keep_examples.append(slim)

            if status == "reject" and len(reject_examples) < 12:
                reject_examples.append(slim)

            if liked and len(liked_examples) < 12:
                liked_examples.append(slim)

        duration_summary: dict[str, dict[str, float]] = {}
        for status, values in durations_by_status.items():
            if values:
                duration_summary[status] = {
                    "count": len(values),
                    "avg": round(sum(values) / len(values), 3),
                    "min": round(min(values), 3),
                    "max": round(max(values), 3),
                }

        total = len(items)
        keep = status_counts.get("keep", 0)
        reject = status_counts.get("reject", 0)
        maybe = status_counts.get("maybe", 0)

        return {
            "total_items": total,
            "status_counts": dict(status_counts),
            "keep_ratio": round(keep / total, 4) if total else 0,
            "maybe_ratio": round(maybe / total, 4) if total else 0,
            "reject_ratio": round(reject / total, 4) if total else 0,
            "liked_count": liked_count,
            "liked_ratio": round(liked_count / total, 4) if total else 0,
            "scene_counts": dict(scene_counts.most_common(40)),
            "duration_by_status_seconds": duration_summary,
            "common_note_terms": dict(note_terms.most_common(40)),
            "keep_examples": keep_examples,
            "reject_examples": reject_examples,
            "liked_examples": liked_examples,
        }

    @staticmethod
    def _extract_duration(item: dict[str, Any]) -> float | None:
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

    @staticmethod
    def _slim_item(item: dict[str, Any]) -> dict[str, Any]:
        keys = [
            "file", "filename", "path", "clip", "video", "segment_id",
            "start", "end", "duration", "scene", "scene_type", "wedding_scene",
            "status", "liked", "note", "score",
        ]
        slim: dict[str, Any] = {}
        for key in keys:
            if key in item:
                slim[key] = item[key]
        return slim

    @staticmethod
    def summarize_feedback_profile(feedback_profile: dict[str, Any]) -> dict[str, Any]:
        if not feedback_profile:
            return {"available": False}

        summary: dict[str, Any] = {
            "available": True,
            "top_level_keys": sorted(list(feedback_profile.keys()))[:80],
        }

        for key in [
            "scene_weights",
            "status_weights",
            "liked_weights",
            "learned_weights",
            "feature_weights",
            "preferences",
            "keep_patterns",
            "reject_patterns",
        ]:
            if key in feedback_profile:
                summary[key] = feedback_profile[key]

        return summary

    @staticmethod
    def build_learned_bias(
        manual_summary: dict[str, Any],
        feedback_profile: dict[str, Any],
        style_profile: dict[str, Any],
    ) -> dict[str, Any]:
        scene_counts = manual_summary.get("scene_counts", {})
        status_counts = manual_summary.get("status_counts", {})

        strong_keep = manual_summary.get("keep_ratio", 0) >= 0.25
        many_rejects = manual_summary.get("reject_ratio", 0) >= 0.35
        liked_ratio = manual_summary.get("liked_ratio", 0)

        preferred_scenes = []
        avoided_scenes = []

        # If actual manual scene labels exist, use their relative frequency as weak bias.
        if isinstance(scene_counts, dict):
            for scene, count in sorted(scene_counts.items(), key=lambda x: x[1], reverse=True):
                if scene and scene != "unknown" and len(preferred_scenes) < 12:
                    preferred_scenes.append(scene)

        rules = ((style_profile or {}).get("rules") or {})
        scene_pref = rules.get("wedding_scene_preferences", {})

        if isinstance(scene_pref, dict):
            for key, value in scene_pref.items():
                text = str(value).lower()
                if "ưu tiên" in text or "cao" in text or "high" in text:
                    if key not in preferred_scenes:
                        preferred_scenes.append(key)

        avoid = rules.get("overall_style", {}).get("avoid", [])
        if isinstance(avoid, list):
            avoided_scenes.extend([str(x) for x in avoid])

        return {
            "confidence": AIStyleMemoryV2.estimate_confidence(manual_summary, style_profile, feedback_profile),
            "manual_has_enough_data": manual_summary.get("total_items", 0) >= 50,
            "strong_keep_signal": strong_keep,
            "many_rejects_signal": many_rejects,
            "liked_ratio": liked_ratio,
            "preferred_scenes": preferred_scenes[:20],
            "avoid_patterns": avoided_scenes[:30],
            "status_counts": status_counts,
            "rule_bias": {
                "prefer_emotional_moments": True,
                "prefer_bride_groom": True,
                "prefer_vow_if_audio_good": True,
                "do_not_overuse_gia_tien_static": True,
                "mix_gia_tien_with_reception": True,
                "use_dance_party_as_final_if_available": True,
                "reject_shaky_outfocus_empty": True,
            },
        }

    @staticmethod
    def estimate_confidence(
        manual_summary: dict[str, Any],
        style_profile: dict[str, Any],
        feedback_profile: dict[str, Any],
    ) -> str:
        score = 0

        if style_profile:
            score += 30

        total = manual_summary.get("total_items", 0)
        if total >= 200:
            score += 40
        elif total >= 50:
            score += 25
        elif total >= 10:
            score += 10

        if feedback_profile:
            score += 20

        if manual_summary.get("liked_count", 0) >= 10:
            score += 10

        if score >= 75:
            return "high"
        if score >= 45:
            return "medium"
        return "low"

    @staticmethod
    def build_intent_map(style_profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "teaser_60s": {
                "target_duration_seconds": 60,
                "pace": "fast emotional teaser",
                "shot_length": "1.2-3.5s mostly",
                "priority": [
                    "bride_groom",
                    "emotional reaction",
                    "vow if strong",
                    "beautiful motion",
                    "reception energy",
                ],
                "avoid": [
                    "long static gia tien",
                    "too many similar ceremony shots",
                    "empty head/tail source",
                ],
            },
            "highlight_3min": {
                "target_duration_seconds": 180,
                "pace": "cinematic emotional highlight",
                "shot_length": "2-5s mostly",
                "priority": [
                    "opening emotional hook",
                    "vow/voice-off",
                    "mix gia tien with reception",
                    "family reaction",
                    "dance party final if good",
                ],
                "avoid": [
                    "boring long ceremony block",
                    "random details without story",
                ],
            },
            "highlight_5min": {
                "target_duration_seconds": 300,
                "pace": "complete but not slow wedding story",
                "shot_length": "3-6s mostly",
                "priority": [
                    "fuller story",
                    "ruoc dau",
                    "gia tien",
                    "reception",
                    "thank you",
                    "dance party ending",
                ],
                "avoid": [
                    "too long static family rite section",
                    "duplicate shots",
                ],
            },
            "review_culling": {
                "target_duration_seconds": None,
                "pace": "not an edit, only select usable footage",
                "priority": [
                    "sharp",
                    "stable",
                    "content/action",
                    "good expression",
                    "good camera movement",
                ],
                "avoid": [
                    "shaky",
                    "out of focus",
                    "no content",
                    "bad head/tail",
                ],
            },
        }

    @staticmethod
    def build_ai_editor_rules(
        style_profile: dict[str, Any],
        learned_bias: dict[str, Any],
        intent_map: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "global_instruction": (
                "Dựng theo style cưới STT: cinematic, cảm xúc, hiện đại, không lê thê. "
                "Ưu tiên cô dâu chú rể, vow, reaction gia đình, chuyển động đẹp. "
                "Lễ gia tiên phải có nhưng không để thành một đoạn dài tĩnh; hãy xen với reception/rước dâu. "
                "Nếu có dance party đẹp, dùng như đoạn kết năng lượng."
            ),
            "selection_order": [
                "reject unusable first: shaky/out-focus/empty/no-action",
                "find emotional hook",
                "select bride/groom moments",
                "select family/reaction",
                "select gia tien/ruoc dau but keep concise",
                "select reception and dance party for energy",
                "add detail shots only as breathing/transition",
            ],
            "preferred_scenes": learned_bias.get("preferred_scenes", []),
            "avoid_patterns": learned_bias.get("avoid_patterns", []),
            "intent_map_keys": list(intent_map.keys()),
        }

    @staticmethod
    def build_shot_selection_weights(learned_bias: dict[str, Any]) -> dict[str, Any]:
        # These are starting values for Module 046.
        return {
            "bride_groom": 1.35,
            "vow_audio_good": 1.30,
            "emotional_reaction": 1.25,
            "stable_motion": 1.18,
            "sharp_focus": 1.20,
            "dance_party_final": 1.15,
            "details_transition": 0.92,
            "gia_tien_static_long": 0.72,
            "duplicate_similar": 0.60,
            "shaky": 0.15,
            "out_of_focus": 0.15,
            "empty_head_tail": 0.20,
            "no_content": 0.25,
            "liked_bonus": 1.25 if learned_bias.get("liked_ratio", 0) > 0 else 1.10,
            "manual_keep_bonus": 1.20,
            "manual_reject_penalty": 0.25,
        }

    @staticmethod
    def build_timeline_rules(style_profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "default_structure": [
                "hook",
                "bride_groom_emotion",
                "vow_or_voice_off",
                "ruoc_dau_gia_tien_mixed",
                "reception_energy",
                "thank_you_or_kiss",
                "dance_party_final_if_available",
            ],
            "mixing_rule": "Không để gia tiên thành block dài tĩnh; xen với reaction/reception/rước dâu.",
            "pacing_rule": "Teaser nhanh hơn, highlight 3 phút cân bằng, highlight 5 phút kể chuyện đầy đủ hơn.",
            "ending_rule": "Nếu có dance party đẹp, để thành đoạn cuối sau thank you.",
            "duplicate_rule": "Không đặt nhiều shot giống nhau liên tiếp.",
        }

    @staticmethod
    def build_music_sfx_rules(style_profile: dict[str, Any]) -> dict[str, Any]:
        rules = ((style_profile or {}).get("rules") or {})
        future = rules.get("music_sfx_future", {})

        return {
            "available_now": False,
            "note": "Module này chỉ lưu rule. Nhạc/SFX thật sẽ làm ở 065-075.",
            "music_mood": future.get("music_mood", ["piano", "violin", "cinematic", "ambient"]),
            "sfx_style": future.get("sfx_style", ["soft whoosh", "riser nhẹ", "hit nhẹ"]),
            "beat_cutting": future.get(
                "beat_cutting",
                "Cut theo beat ở đoạn reception/dance party, giữ hơi thở ở vow/emotional.",
            ),
        }

    @staticmethod
    def build_prompt_pack(
        style_profile: dict[str, Any],
        learned_bias: dict[str, Any],
        intent_map: dict[str, Any],
    ) -> dict[str, Any]:
        global_prompt = (
            "Bạn là AI dựng phim cưới cho STT Presents. "
            "Hãy dựng theo gu: cinematic, emotional, modern, not boring. "
            "Ưu tiên cô dâu/chú rể, vow, reaction gia đình, khoảnh khắc đẹp, chuyển động mượt. "
            "Bỏ rung, out nét, đoạn đầu/đuôi chưa có hành động, cảnh không nội dung. "
            "Lễ gia tiên phải có nhưng không kéo dài tĩnh; hãy xen với rước dâu/reception. "
            "Nếu có dance party đẹp, dùng làm đoạn cuối sau thank you."
        )

        intent_prompts = {
            "teaser_60s": (
                "Dựng teaser 60 giây nhanh, cảm xúc, nhiều bride/groom/reaction, ít lễ, "
                "không để gia tiên dài, ưu tiên shot đẹp và có chuyển động."
            ),
            "highlight_3min": (
                "Dựng highlight 3 phút, mở đầu bằng hook/vow, xen gia tiên với reception, "
                "giữ cảm xúc nhưng không chậm, cuối có dance party nếu nguồn đẹp."
            ),
            "highlight_5min": (
                "Dựng highlight 5 phút đầy đủ câu chuyện hơn: rước dâu, gia tiên, reception, thank you, "
                "dance party cuối; vẫn tránh cảnh tĩnh kéo dài."
            ),
            "review_culling": (
                "Chỉ lọc source: giữ shot sắc nét, ổn định, có nội dung/hành động; bỏ rung/out nét/đầu đuôi thừa."
            ),
        }

        full = "\n\n".join([
            "GLOBAL STYLE:",
            global_prompt,
            "",
            "LEARNED BIAS:",
            json.dumps(learned_bias, ensure_ascii=False, indent=2),
            "",
            "INTENT PROMPTS:",
            json.dumps(intent_prompts, ensure_ascii=False, indent=2),
        ])

        return {
            "global_prompt": global_prompt,
            "intent_prompts": intent_prompts,
            "full_prompt": full,
        }

    @staticmethod
    def render_text(memory: dict[str, Any]) -> str:
        manual = memory.get("manual_summary", {})
        bias = memory.get("learned_bias", {})
        weights = memory.get("shot_selection_weights", {})

        lines = [
            "STT AI Editor - AI Style Memory V2",
            "=" * 72,
            f"Version: {memory.get('version')}",
            f"Updated: {memory.get('updated_at')}",
            f"Project: {memory.get('project_root')}",
            f"Confidence: {bias.get('confidence')}",
            "",
            "Manual selection:",
            f"- total: {manual.get('total_items', 0)}",
            f"- status: {manual.get('status_counts', {})}",
            f"- liked: {manual.get('liked_count', 0)}",
            "",
            "Preferred scenes:",
        ]

        for item in bias.get("preferred_scenes", []):
            lines.append(f"- {item}")

        lines += ["", "Shot selection weights:"]
        for key, value in weights.items():
            lines.append(f"- {key}: {value}")

        lines += ["", "AI global instruction:"]
        lines.append(memory.get("ai_editor_rules", {}).get("global_instruction", ""))

        return "\n".join(lines)

    @staticmethod
    def render_html(memory: dict[str, Any]) -> str:
        import html

        bias = memory.get("learned_bias", {})
        manual = memory.get("manual_summary", {})
        weights = memory.get("shot_selection_weights", {})
        updated = html.escape(str(memory.get("updated_at", "")))
        confidence = html.escape(str(bias.get("confidence", "")))

        def rows(d: dict[str, Any]) -> str:
            if not d:
                return "<tr><td>None</td><td></td></tr>"
            return "\n".join(
                f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
                for k, v in d.items()
            )

        def list_items(items: list[Any]) -> str:
            if not items:
                return "<li>None</li>"
            return "\n".join(f"<li>{html.escape(str(x))}</li>" for x in items)

        instruction = html.escape(str(memory.get("ai_editor_rules", {}).get("global_instruction", "")))

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT AI Style Memory V2</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1100px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; }}
td {{ border-bottom: 1px solid #333; padding: 8px; vertical-align: top; }}
code {{ display:block; background:#000; padding:12px; border-radius:10px; white-space:pre-wrap; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 045</div>
  <h1>AI Style Memory V2</h1>
  <p>Updated: {updated}</p>
  <p>Confidence: <b>{confidence}</b></p>

  <h2>Manual Summary</h2>
  <table>{rows(manual.get("status_counts", {}))}</table>
  <p>Total: {html.escape(str(manual.get("total_items", 0)))}</p>
  <p>Liked: {html.escape(str(manual.get("liked_count", 0)))}</p>

  <h2>Preferred Scenes</h2>
  <ul>{list_items(bias.get("preferred_scenes", []))}</ul>

  <h2>Shot Weights</h2>
  <table>{rows(weights)}</table>

  <h2>AI Global Instruction</h2>
  <code>{instruction}</code>
</div>
</body>
</html>
'''


def build_ai_style_memory(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str = "wedding_highlight",
    notes: str | None = None,
    open_folder: bool = True,
) -> dict[str, Any]:
    return AIStyleMemoryV2(project_root=project_root).build(
        intent=intent,
        notes=notes,
        open_folder=open_folder,
    )
