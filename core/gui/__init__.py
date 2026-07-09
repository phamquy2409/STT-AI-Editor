
from .simple_gui import STTAIEditorWindow, run_gui

try:
    from .exe_live_patch import apply_live_server_patch
    apply_live_server_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI live server patch skipped: {exc!r}")

try:
    from .production_patch import apply_production_gui_patch
    apply_production_gui_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI production patch skipped: {exc!r}")

try:
    from .premiere_bridge_patch import apply_premiere_bridge_patch
    apply_premiere_bridge_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere bridge patch skipped: {exc!r}")

try:
    from .premiere_xml_validator_patch import apply_premiere_xml_validator_patch
    apply_premiere_xml_validator_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere XML validator patch skipped: {exc!r}")

try:
    from .premiere_jsx_helper_patch import apply_premiere_jsx_helper_patch
    apply_premiere_jsx_helper_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere JSX helper patch skipped: {exc!r}")

try:
    from .premiere_script_installer_patch import apply_premiere_script_installer_patch
    apply_premiere_script_installer_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere script installer patch skipped: {exc!r}")

try:
    from .premiere_panel_patch import apply_premiere_panel_patch
    apply_premiere_panel_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere panel patch skipped: {exc!r}")

try:
    from .premiere_pointer_patch import apply_premiere_pointer_patch
    apply_premiere_pointer_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere pointer patch skipped: {exc!r}")

try:
    from .premiere_panel_sync_patch import apply_premiere_panel_sync_patch
    apply_premiere_panel_sync_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere panel sync patch skipped: {exc!r}")

try:
    from .style_profile_patch import apply_style_profile_patch
    apply_style_profile_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI style profile patch skipped: {exc!r}")

try:
    from .ai_style_memory_patch import apply_ai_style_memory_patch
    apply_ai_style_memory_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI AI style memory patch skipped: {exc!r}")

try:
    from .ai_shot_scorer_patch import apply_ai_shot_scorer_patch
    apply_ai_shot_scorer_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI AI shot scorer patch skipped: {exc!r}")

try:
    from .prewedding_selector_patch import apply_prewedding_selector_patch
    apply_prewedding_selector_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding selector patch skipped: {exc!r}")

try:
    from .prewedding_xml_patch import apply_prewedding_xml_patch
    apply_prewedding_xml_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding XML patch skipped: {exc!r}")

try:
    from .compact_scroll_patch import apply_compact_scroll_patch
    apply_compact_scroll_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI compact scroll patch skipped: {exc!r}")

__all__ = ["STTAIEditorWindow", "run_gui"]
