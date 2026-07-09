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

__all__ = ["STTAIEditorWindow", "run_gui"]
