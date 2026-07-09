from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class WorkflowPreset:
    name: str
    label: str
    description: str
    target_duration_seconds: int
    top_candidates: int
    max_segments_per_video: int
    sequence_fps: int
    sequence_width: int
    sequence_height: int
    recommended: bool = False


DEFAULT_PRESETS: dict[str, WorkflowPreset] = {
    "wedding_highlight_60s": WorkflowPreset(
        name="wedding_highlight_60s",
        label="Wedding Highlight 60s",
        description="Bản test nhanh / teaser ngắn. Dùng để review nhanh footage và chọn shot tốt.",
        target_duration_seconds=60,
        top_candidates=120,
        max_segments_per_video=1,
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
        recommended=True,
    ),
    "wedding_highlight_3min": WorkflowPreset(
        name="wedding_highlight_3min",
        label="Wedding Highlight 3min",
        description="Bản highlight cưới ngắn 3 phút, nhiều cảnh hơn, phù hợp dựng teaser/short highlight.",
        target_duration_seconds=180,
        top_candidates=220,
        max_segments_per_video=2,
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
    ),
    "wedding_highlight_5min": WorkflowPreset(
        name="wedding_highlight_5min",
        label="Wedding Highlight 5min",
        description="Bản highlight cưới 5 phút, giữ nhiều khoảnh khắc gia đình/nghi lễ/sân khấu hơn.",
        target_duration_seconds=300,
        top_candidates=320,
        max_segments_per_video=3,
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
    ),
    "review_culling_30s": WorkflowPreset(
        name="review_culling_30s",
        label="Review Culling 30s",
        description="Bản rất ngắn để test thuật toán chọn source nhanh, không dùng làm final.",
        target_duration_seconds=30,
        top_candidates=80,
        max_segments_per_video=1,
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
    ),
}


class ProjectPresetManager:
    # Build 030.
    # Manage workflow presets per project.
    #
    # Project preset file:
    #   <project_root>/stt_workflow_preset.json
    #
    # It does not modify media/source files.

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.preset_path = self.project_root / "stt_workflow_preset.json"

    def list_presets(self) -> list[dict[str, Any]]:
        return [asdict(p) for p in DEFAULT_PRESETS.values()]

    def get_preset(self, name: str | None = None) -> WorkflowPreset:
        if name:
            if name not in DEFAULT_PRESETS:
                raise KeyError(f"Unknown preset: {name}")
            return DEFAULT_PRESETS[name]

        current = self.load_current_preset()
        current_name = str(current.get("name", ""))

        if current_name in DEFAULT_PRESETS:
            return DEFAULT_PRESETS[current_name]

        for preset in DEFAULT_PRESETS.values():
            if preset.recommended:
                return preset

        return next(iter(DEFAULT_PRESETS.values()))

    def load_current_preset(self) -> dict[str, Any]:
        if not self.preset_path.exists():
            return asdict(self.get_recommended_preset())

        try:
            payload = json.loads(self.preset_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        return asdict(self.get_recommended_preset())

    def get_recommended_preset(self) -> WorkflowPreset:
        for preset in DEFAULT_PRESETS.values():
            if preset.recommended:
                return preset
        return next(iter(DEFAULT_PRESETS.values()))

    def save_preset(self, name: str) -> dict[str, Any]:
        preset = self.get_preset(name)
        payload = asdict(preset)
        payload["project_root"] = str(self.project_root)
        payload["preset_file"] = str(self.preset_path)

        self.project_root.mkdir(parents=True, exist_ok=True)
        self.preset_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return payload

    def apply_to_gui_values(self, name: str | None = None) -> dict[str, Any]:
        preset = self.get_preset(name)
        return {
            "target_duration": int(preset.target_duration_seconds),
            "top_candidates": int(preset.top_candidates),
            "max_segments_per_video": int(preset.max_segments_per_video),
            "sequence_fps": int(preset.sequence_fps),
            "sequence_width": int(preset.sequence_width),
            "sequence_height": int(preset.sequence_height),
            "label": preset.label,
            "name": preset.name,
            "description": preset.description,
        }


def list_workflow_presets() -> list[dict[str, Any]]:
    return [asdict(p) for p in DEFAULT_PRESETS.values()]


def save_project_workflow_preset(project_root: str | Path, preset_name: str) -> dict[str, Any]:
    return ProjectPresetManager(project_root).save_preset(preset_name)


def load_project_workflow_preset(project_root: str | Path) -> dict[str, Any]:
    return ProjectPresetManager(project_root).load_current_preset()


def get_project_workflow_values(project_root: str | Path, preset_name: str | None = None) -> dict[str, Any]:
    return ProjectPresetManager(project_root).apply_to_gui_values(preset_name)
