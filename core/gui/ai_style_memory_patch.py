
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_ai_style_memory_patch_applied"


def apply_ai_style_memory_patch(window_class) -> None:
    # Module 045.
    # Adds Build AI Style Memory V2 button to GUI.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1050, lambda: _install_ai_style_memory_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_ai_style_memory_ui(window) -> None:
    if getattr(window, "_stt_ai_style_memory_ui_installed", False):
        return

    try:
        window._stt_ai_style_memory_ui_installed = True

        btn = QPushButton("Build AI Style Memory V2")
        btn.setObjectName("sttProductionButton_primary_BuildAIStyleMemoryV2")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _build_memory(window, show_popup=True))

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(btn)
            _log(window, "AI STYLE MEMORY V2 BUTTON LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            box = QGroupBox("AI Style Memory")
            layout = QVBoxLayout(box)
            layout.addWidget(btn)
            root_layout.insertWidget(0, box)
            _log(window, "AI STYLE MEMORY V2 PANEL LOADED")

    except Exception:
        _log(window, "AI STYLE MEMORY PATCH ERROR")
        _log(window, traceback.format_exc())


def _build_memory(window, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.ai_style_memory import build_ai_style_memory

        result = build_ai_style_memory(project_root=project_root, open_folder=True)

        _log(window, "")
        _log(window, "AI STYLE MEMORY V2 BUILT")
        _log(window, f"Memory: {result['memory']}")
        _log(window, f"Report: {result['report_dir']}")
        _log(window, f"KEEP: {result['manual_keep']} | MAYBE: {result['manual_maybe']} | REJECT: {result['manual_reject']} | LIKE: {result['manual_liked']}")

        if show_popup:
            QMessageBox.information(
                window,
                "AI Style Memory V2",
                "Đã build AI Style Memory V2.\n\n"
                "Đây là bộ nhớ để module 046+ bắt đầu chấm điểm shot theo gu dựng của anh.",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "AI STYLE MEMORY V2 ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "AI Style Memory V2 Error", msg[-4000:])


def _get_project_root_from_window(window) -> Path:
    edit = getattr(window, "project_edit", None)
    if edit is not None:
        text = edit.text().strip()
        if text:
            return Path(text)

    return Path("D:/STT Projects/Wedding_Test_001")


def _log(window, message: str) -> None:
    try:
        if hasattr(window, "append_log") and callable(window.append_log):
            window.append_log(str(message))
            return
    except Exception:
        pass

    print(message)
