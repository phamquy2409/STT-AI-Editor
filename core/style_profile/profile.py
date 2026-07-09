
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


@dataclass
class WeddingStyleProfileConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    profile_name: str = "STT Wedding Highlight Style"


class WeddingStyleProfile:
    # Module 044.
    # This is the first real "editing style memory" layer.
    #
    # It does not edit video by itself yet.
    # It stores the user's preferred wedding editing rules so future AI modules
    # can use them consistently.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.profile_path = self.project_root / "stt_wedding_style_profile.json"
        self.appdata_dir = self.get_appdata_dir()
        self.appdata_profile_path = self.appdata_dir / "stt_wedding_style_profile.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    def create_or_update(self, notes: str | None = None) -> dict[str, Any]:
        existing = self.load_existing()

        profile = self.default_profile()

        if existing:
            profile = self.merge_profile(profile, existing)

        if notes:
            profile.setdefault("user_notes", [])
            profile["user_notes"].append(
                {
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "note": notes,
                }
            )

        learned = self.read_learning_sources()
        profile["learning_sources"] = learned

        profile["updated_at"] = datetime.now().isoformat(timespec="seconds")
        profile["project_root"] = str(self.project_root)

        self.project_root.mkdir(parents=True, exist_ok=True)
        self.appdata_dir.mkdir(parents=True, exist_ok=True)

        self.profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        self.appdata_profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

        report_dir = self.project_root / "exports" / f"style_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_json = report_dir / "stt_wedding_style_profile.json"
        report_txt = report_dir / "STYLE_PROFILE_SUMMARY.txt"
        report_html = report_dir / "STYLE_PROFILE_SUMMARY.html"

        report_json.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        report_txt.write_text(self.render_text(profile), encoding="utf-8")
        report_html.write_text(self.render_html(profile), encoding="utf-8")

        result = {
            "ok": True,
            "profile": str(self.profile_path),
            "appdata_profile": str(self.appdata_profile_path),
            "report_dir": str(report_dir),
            "report_json": str(report_json),
            "report_txt": str(report_txt),
            "report_html": str(report_html),
            "updated_at": profile["updated_at"],
        }

        (report_dir / "style_profile_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        try:
            os.startfile(report_dir)
        except Exception:
            pass

        return result

    def load_existing(self) -> dict[str, Any]:
        for path in [self.profile_path, self.appdata_profile_path]:
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return {}

    @staticmethod
    def merge_profile(default: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
        # Preserve user_notes and custom fields, but refresh module/default rules.
        merged = dict(default)

        for key, value in existing.items():
            if key in {"created_at", "version", "module"}:
                continue
            if key == "rules":
                # Keep existing custom rule overrides by section.
                merged_rules = merged.get("rules", {})
                if isinstance(value, dict):
                    for section, section_value in value.items():
                        if isinstance(section_value, dict) and isinstance(merged_rules.get(section), dict):
                            merged_rules[section].update(section_value)
                        else:
                            merged_rules[section] = section_value
                merged["rules"] = merged_rules
            elif key == "user_notes":
                merged["user_notes"] = value
            elif key.startswith("custom_"):
                merged[key] = value

        return merged

    def read_learning_sources(self) -> dict[str, Any]:
        sources: dict[str, Any] = {
            "manual_selection": None,
            "feedback_profile": None,
            "workflow_preset": None,
            "xml_settings": None,
        }

        manual_path = self.project_root / "manual_selection.json"
        feedback_path = self.project_root / "stt_feedback_profile.json"
        preset_path = self.project_root / "stt_workflow_preset.json"
        xml_settings_path = self.project_root / "stt_xml_export_settings.json"

        if manual_path.exists():
            try:
                data = json.loads(manual_path.read_text(encoding="utf-8"))
                items = data.get("items", [])
                keep = sum(1 for x in items if str(x.get("status", "")).lower() == "keep")
                maybe = sum(1 for x in items if str(x.get("status", "")).lower() == "maybe")
                reject = sum(1 for x in items if str(x.get("status", "")).lower() == "reject")
                liked = sum(1 for x in items if x.get("liked"))
                sources["manual_selection"] = {
                    "path": str(manual_path),
                    "items": len(items),
                    "keep": keep,
                    "maybe": maybe,
                    "reject": reject,
                    "liked": liked,
                }
            except Exception as exc:
                sources["manual_selection"] = {"path": str(manual_path), "error": repr(exc)}

        if feedback_path.exists():
            try:
                data = json.loads(feedback_path.read_text(encoding="utf-8"))
                sources["feedback_profile"] = {
                    "path": str(feedback_path),
                    "keys": sorted(list(data.keys()))[:50],
                }
            except Exception as exc:
                sources["feedback_profile"] = {"path": str(feedback_path), "error": repr(exc)}

        if preset_path.exists():
            try:
                sources["workflow_preset"] = json.loads(preset_path.read_text(encoding="utf-8"))
            except Exception as exc:
                sources["workflow_preset"] = {"path": str(preset_path), "error": repr(exc)}

        if xml_settings_path.exists():
            try:
                sources["xml_settings"] = json.loads(xml_settings_path.read_text(encoding="utf-8"))
            except Exception as exc:
                sources["xml_settings"] = {"path": str(xml_settings_path), "error": repr(exc)}

        return sources

    @staticmethod
    def default_profile() -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        return {
            "module": "044_wedding_style_profile",
            "version": "0.44",
            "created_at": now,
            "updated_at": now,
            "profile_name": "STT Wedding Highlight Style",
            "language": "vi",
            "purpose": (
                "Lưu gu dựng cưới của STT để các module AI sau dùng khi chọn shot, dựng timeline, "
                "cắt theo nhạc và xuất Premiere XML."
            ),
            "rules": {
                "overall_style": {
                    "tone": "cinematic, emotional, modern, not boring",
                    "pace": "giữ cảm xúc nhưng không kéo dài cảnh tĩnh quá lâu",
                    "skin_priority": "ưu tiên khoảnh khắc cô dâu/chú rể đẹp, cảm xúc, tự nhiên",
                    "avoid": [
                        "rung lắc mạnh",
                        "out nét",
                        "đầu đuôi clip chưa vào hành động",
                        "cảnh không có nội dung",
                        "gia tiên quá dài và tĩnh",
                    ],
                },
                "story_structure": {
                    "opening": [
                        "mở đầu bằng shot cinematic hoặc khoảnh khắc cảm xúc mạnh",
                        "có thể dùng vow/voice-off để kéo cảm xúc",
                        "tránh mở đầu quá chậm nếu là teaser 60s",
                    ],
                    "middle": [
                        "xen lễ gia tiên với reception để không bị dài và tĩnh",
                        "trộn rước dâu buổi sáng với reception nếu hợp cảm xúc",
                        "ưu tiên reaction của ba mẹ, cô dâu chú rể, khách thân",
                    ],
                    "ending": [
                        "kết bằng thank you / kiss / walking / dance party tùy clip",
                        "dance party nên là final reception section sau thank you nếu có nguồn đẹp",
                    ],
                },
                "wedding_scene_preferences": {
                    "bride_groom": "ưu tiên cao",
                    "vows": "ưu tiên cao nếu âm thanh dùng được",
                    "gia_tien": "cần có nhưng không kéo dài tĩnh, nên xen với cảnh khác",
                    "ruoc_dau": "dùng làm bối cảnh câu chuyện, xen với reception",
                    "reception": "dùng để tăng nhịp và cảm xúc",
                    "dance_party": "dùng cuối clip nếu có nguồn đẹp",
                    "details": "dùng làm breathing shots hoặc transition",
                },
                "cutting_rules": {
                    "shot_length_seconds": {
                        "teaser_60s": "1.2-3.5s đa số shot, dài hơn cho vow/emotional moment",
                        "highlight_3min": "2-5s đa số shot, có đoạn thở cho cảm xúc",
                        "highlight_5min": "3-6s đa số shot, giữ ceremony vừa đủ",
                    },
                    "duplicate_handling": "tránh dùng nhiều shot giống nhau liên tiếp",
                    "motion": "ưu tiên shot có chuyển động camera mượt hoặc chủ thể có hành động rõ",
                    "transitions": "ưu tiên cut/zoom/pan/mask mượt, không wipe thô",
                },
                "music_sfx_future": {
                    "music_mood": [
                        "piano",
                        "violin",
                        "cinematic",
                        "ambient",
                        "emotional build",
                    ],
                    "sfx_style": [
                        "soft whoosh",
                        "riser nhẹ",
                        "hit nhẹ ở beat/highlight",
                        "tránh SFX quá game/trailer nếu không hợp cưới",
                    ],
                    "beat_cutting": "cut theo beat ở đoạn reception/dance party, giữ hơi thở ở vow/emotional.",
                },
                "premiere_export": {
                    "audio": "giữ dual mono an toàn A1=Left, A2=Right",
                    "xml": "xuất XML để import hoặc dùng Premiere panel",
                    "sequence_presets": [
                        "uhd_4k_25p",
                        "uhd_4k_50p",
                        "fhd_1080_25p",
                        "vertical_1080_25p",
                    ],
                },
                "prompt_examples": [
                    "Dựng teaser 60s nhanh, cảm xúc, ưu tiên cô dâu chú rể, ít lễ, nhiều reaction đẹp.",
                    "Dựng highlight 3 phút, mở đầu bằng vow, xen gia tiên với reception, cuối dance party.",
                    "Lọc source cưới truyền thống, bỏ rung/out nét/đoạn chưa có hành động, giữ shot đẹp.",
                ],
            },
            "future_ai_targets": {
                "050": "AI học chọn shot theo KEEP/REJECT/LIKE",
                "055": "AI học cấu trúc dựng highlight cưới",
                "060": "AI dựng theo lệnh chữ",
                "070": "AI thêm nhạc/SFX/beat cut",
                "080": "AI editor assistant hoàn chỉnh hơn",
            },
            "user_notes": [],
        }

    @staticmethod
    def render_text(profile: dict[str, Any]) -> str:
        rules = profile.get("rules", {})
        lines = [
            "STT AI Editor - Wedding Style Profile",
            "=" * 72,
            f"Profile: {profile.get('profile_name')}",
            f"Version: {profile.get('version')}",
            f"Updated: {profile.get('updated_at')}",
            "",
            "Purpose:",
            str(profile.get("purpose", "")),
            "",
            "Overall style:",
        ]

        overall = rules.get("overall_style", {})
        for key, value in overall.items():
            lines.append(f"- {key}: {value}")

        lines += ["", "Story structure:"]
        story = rules.get("story_structure", {})
        for key, value in story.items():
            lines.append(f"- {key}:")
            if isinstance(value, list):
                lines += [f"  + {x}" for x in value]
            else:
                lines.append(f"  + {value}")

        lines += ["", "Scene preferences:"]
        scenes = rules.get("wedding_scene_preferences", {})
        for key, value in scenes.items():
            lines.append(f"- {key}: {value}")

        lines += ["", "Prompt examples:"]
        for prompt in rules.get("prompt_examples", []):
            lines.append(f"- {prompt}")

        return "\n".join(lines)

    @staticmethod
    def render_html(profile: dict[str, Any]) -> str:
        import html

        rules = profile.get("rules", {})
        title = html.escape(str(profile.get("profile_name", "Wedding Style Profile")))
        updated = html.escape(str(profile.get("updated_at", "")))
        purpose = html.escape(str(profile.get("purpose", "")))

        def list_items(items: list[Any]) -> str:
            if not items:
                return "<li>None</li>"
            return "\n".join(f"<li>{html.escape(str(x))}</li>" for x in items)

        story = rules.get("story_structure", {})
        scenes = rules.get("wedding_scene_preferences", {})
        prompts = rules.get("prompt_examples", [])

        story_html = ""
        for key, value in story.items():
            if isinstance(value, list):
                story_html += f"<h3>{html.escape(str(key))}</h3><ul>{list_items(value)}</ul>"
            else:
                story_html += f"<h3>{html.escape(str(key))}</h3><p>{html.escape(str(value))}</p>"

        scenes_html = "\n".join(
            f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in scenes.items()
        )

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT Wedding Style Profile</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1000px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; }}
td {{ border-bottom: 1px solid #333; padding: 8px; vertical-align: top; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 044</div>
  <h1>{title}</h1>
  <p>Updated: {updated}</p>
  <p>{purpose}</p>

  <h2>Story Structure</h2>
  {story_html}

  <h2>Scene Preferences</h2>
  <table>{scenes_html}</table>

  <h2>Prompt Examples</h2>
  <ul>{list_items(prompts)}</ul>
</div>
</body>
</html>
'''


def create_wedding_style_profile(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    notes: str | None = None,
) -> dict[str, Any]:
    return WeddingStyleProfile(project_root=project_root).create_or_update(notes=notes)
