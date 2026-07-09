from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.exporter import export_premiere_xml_existing_project


@dataclass
class SequencePreset:
    name: str
    label: str
    fps: int
    width: int
    height: int
    description: str
    recommended: bool = False


SEQUENCE_PRESETS: dict[str, SequencePreset] = {
    "uhd_4k_25p": SequencePreset(
        name="uhd_4k_25p",
        label="UHD 4K 25p",
        fps=25,
        width=3840,
        height=2160,
        description="Preset chính đang dùng cho source cưới 4K/Premiere.",
        recommended=True,
    ),
    "uhd_4k_50p": SequencePreset(
        name="uhd_4k_50p",
        label="UHD 4K 50p",
        fps=50,
        width=3840,
        height=2160,
        description="Dùng nếu muốn timeline 50fps cho source 50p/slow motion.",
    ),
    "fhd_1080_25p": SequencePreset(
        name="fhd_1080_25p",
        label="Full HD 1080p 25p",
        fps=25,
        width=1920,
        height=1080,
        description="Dùng cho máy yếu hoặc test nhanh.",
    ),
    "dci_4k_24p": SequencePreset(
        name="dci_4k_24p",
        label="DCI 4K 24p",
        fps=24,
        width=4096,
        height=2160,
        description="Dùng nếu muốn timeline DCI 4K 24p.",
    ),
    "vertical_1080_25p": SequencePreset(
        name="vertical_1080_25p",
        label="Vertical 1080x1920 25p",
        fps=25,
        width=1080,
        height=1920,
        description="Dùng cho reels/TikTok/shorts.",
    ),
}


class XMLExportOptions:
    # Module 033.
    # Sequence preset + convenience exporter.
    #
    # It does not change the low-level Premiere XML exporter.
    # It wraps existing export_premiere_xml_existing_project with chosen sequence settings.

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.settings_path = self.project_root / "stt_xml_export_settings.json"

    def list_presets(self) -> list[dict[str, Any]]:
        return [asdict(p) for p in SEQUENCE_PRESETS.values()]

    def get_preset(self, name: str | None = None) -> SequencePreset:
        if name:
            if name not in SEQUENCE_PRESETS:
                raise KeyError(f"Unknown sequence preset: {name}")
            return SEQUENCE_PRESETS[name]

        settings = self.load_settings()
        current = str(settings.get("sequence_preset", "")).strip()
        if current in SEQUENCE_PRESETS:
            return SEQUENCE_PRESETS[current]

        for preset in SEQUENCE_PRESETS.values():
            if preset.recommended:
                return preset

        return next(iter(SEQUENCE_PRESETS.values()))

    def save_settings(
        self,
        sequence_preset: str = "uhd_4k_25p",
        include_audio: bool = True,
        xml_name: str = "stt_ai_premiere_import.xml",
    ) -> dict[str, Any]:
        preset = self.get_preset(sequence_preset)

        payload = {
            "version": "033",
            "project_root": str(self.project_root),
            "sequence_preset": preset.name,
            "label": preset.label,
            "sequence_fps": preset.fps,
            "sequence_width": preset.width,
            "sequence_height": preset.height,
            "include_audio": bool(include_audio),
            "xml_name": xml_name,
            "settings_file": str(self.settings_path),
        }

        self.settings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def load_settings(self) -> dict[str, Any]:
        if not self.settings_path.exists():
            return self.save_settings("uhd_4k_25p")

        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        return self.save_settings("uhd_4k_25p")

    def find_latest_roughcut_json(self) -> Path:
        patterns = [
            "learned_candidates_*/roughcut_learned_candidates.json",
            "learned_candidates_*/roughcut_plan.json",
            "manual_final_*/manual_roughcut.json",
            "manual_final_*/roughcut_plan.json",
            "duplicate_removed_*/roughcut_no_duplicates.json",
            "duplicate_removed_*/roughcut_plan.json",
            "story_timeline_v2_*/roughcut_story_v2.json",
            "story_timeline_v2_*/roughcut_plan.json",
            "final_roughcut_*/roughcut_final.json",
            "roughcut_*/roughcut_plan.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.exports_dir.glob(pattern))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            raise FileNotFoundError(f"No roughcut json found in {self.exports_dir}")

        return candidates[0]

    def export(
        self,
        roughcut_json: str | Path | None = None,
        sequence_preset: str | None = None,
    ) -> dict[str, Any]:
        preset = self.get_preset(sequence_preset)
        input_json = Path(roughcut_json) if roughcut_json else self.find_latest_roughcut_json()

        result = export_premiere_xml_existing_project(
            project_root=self.project_root,
            roughcut_json=input_json,
            sequence_fps=preset.fps,
            sequence_width=preset.width,
            sequence_height=preset.height,
        )

        payload = {
            "project_root": str(self.project_root),
            "roughcut_json": str(input_json),
            "sequence_preset": preset.name,
            "sequence_label": preset.label,
            "sequence_fps": preset.fps,
            "sequence_width": preset.width,
            "sequence_height": preset.height,
            "xml": result.get("xml", ""),
            "output_dir": result.get("output_dir", ""),
            "raw_result": result,
        }

        output_dir = Path(str(result.get("output_dir", "")))
        if output_dir.exists():
            report = output_dir / "xml_export_options_033.json"
            report.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            payload["report"] = str(report)

        return payload


def list_sequence_presets() -> list[dict[str, Any]]:
    return [asdict(p) for p in SEQUENCE_PRESETS.values()]


def save_xml_export_settings_existing_project(
    project_root: str | Path,
    sequence_preset: str = "uhd_4k_25p",
) -> dict[str, Any]:
    return XMLExportOptions(project_root).save_settings(sequence_preset=sequence_preset)


def load_xml_export_settings_existing_project(project_root: str | Path) -> dict[str, Any]:
    return XMLExportOptions(project_root).load_settings()


def export_xml_with_options_existing_project(
    project_root: str | Path,
    roughcut_json: str | Path | None = None,
    sequence_preset: str | None = None,
) -> dict[str, Any]:
    return XMLExportOptions(project_root).export(
        roughcut_json=roughcut_json,
        sequence_preset=sequence_preset,
    )
