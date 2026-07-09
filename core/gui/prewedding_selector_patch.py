
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_prewedding_selector_patch_applied"


def apply_prewedding_selector_patch(window_class) -> None:
    # Module 047.
    # Adds Prewedding Learned Selector panel to GUI.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1250, lambda: _install_prewedding_selector_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_prewedding_selector_ui(window) -> None:
    if getattr(window, "_stt_prewedding_selector_ui_installed", False):
        return

    try:
        window._stt_prewedding_selector_ui_installed = True

        from core.prewedding_selector import PREWEDDING_TARGETS

        combo = QComboBox()
        combo.setObjectName("sttPreweddingSelectorIntentCombo")
        for intent in sorted(PREWEDDING_TARGETS):
            combo.addItem(intent)

        preferred = "prewedding_reel_60s"
        index = combo.findText(preferred)
        if index >= 0:
            combo.setCurrentIndex(index)

        btn = QPushButton("Build Prewedding Selection")
        btn.setObjectName("sttProductionButton_primary_BuildPreweddingSelection")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _run_selector(window, combo.currentText(), show_popup=True))

        box = QGroupBox("Prewedding Learned Selector")
        box.setObjectName("sttPreweddingSelectorPanel")
        layout = QVBoxLayout(box)
        layout.addWidget(combo)
        layout.addWidget(btn)

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(box)
            _log(window, "PREWEDDING LEARNED SELECTOR UI LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            root_layout.insertWidget(0, box)
            _log(window, "PREWEDDING LEARNED SELECTOR PANEL LOADED")

    except Exception:
        _log(window, "PREWEDDING SELECTOR PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_selector(window, intent: str, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.prewedding_selector import build_prewedding_selection

        result = build_prewedding_selection(
            project_root=project_root,
            intent=intent,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "PREWEDDING SELECTION BUILT")
        _log(window, f"Intent: {result['intent']}")
        _log(window, f"Duration: {result['actual_duration']} / {result['target_duration']}")
        _log(window, f"Selected: {result['selected_count']}")
        _log(window, f"Report: {result['report_dir']}")

        if show_popup:
            QMessageBox.information(
                window,
                "Prewedding Selection",
                "Đã build prewedding selection.\n\n"
                f"Intent: {result['intent']}\n"
                f"Selected: {result['selected_count']}\n"
                f"Duration: {result['actual_duration']}s\n\n"
                "Mở report để xem timeline đã chọn.",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREWEDDING SELECTION ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Prewedding Selection Error", msg[-4000:])


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
