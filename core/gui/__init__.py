
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

__all__ = ["STTAIEditorWindow", "run_gui"]
