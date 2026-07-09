
from .simple_gui import STTAIEditorWindow, run_gui
from .exe_live_patch import apply_live_server_patch

apply_live_server_patch(STTAIEditorWindow)

__all__ = ["STTAIEditorWindow", "run_gui"]
