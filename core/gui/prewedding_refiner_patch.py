
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_prewedding_refiner_patch_applied"


def apply_prewedding_refiner_patch(window_class) -> None:
    # Module 050.
    # Adds Prewedding Smart Refiner panel to GUI.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1400, lambda: _install_prewedding_refiner_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_prewedding_refiner_ui(window) -> None:
    if getattr(window, "_stt_prewedding_refiner_ui_installed", False):
        return

    try:
        window._stt_prewedding_refiner_ui_installed = True

        from core.prewedding_refiner import REFINER_RULES

        combo = QComboBox()
        combo.setObjectName("sttPreweddingRefinerIntentCombo")
        combo.addItem("auto")
        for intent in sorted(REFINER_RULES):
            combo.addItem(intent)

        preferred = combo.findText("prewedding_reel_60s")
        if preferred >= 0:
            combo.setCurrentIndex(preferred)

        btn = QPushButton("Refine Prewedding Roughcut")
        btn.setObjectName("sttProductionButton_primary_RefinePreweddingRoughcut")
        btn.setMinimumHeight(34)
        btn.clicked.connect(lambda: _run_refiner(window, combo.currentText(), show_popup=True))

        box = QGroupBox("Prewedding Smart Refiner")
        box.setObjectName("sttPreweddingRefinerPanel")
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
            _log(window, "PREWEDDING SMART REFINER UI LOADED")
            return

        central = window.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().insertWidget(0, box)
            _log(window, "PREWEDDING SMART REFINER PANEL LOADED")

    except Exception:
        _log(window, "PREWEDDING SMART REFINER PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_refiner(window, intent_text: str, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)
        intent = None if intent_text == "auto" else intent_text

        from core.prewedding_refiner import refine_prewedding_roughcut

        result = refine_prewedding_roughcut(
            project_root=project_root,
            intent=intent,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "PREWEDDING SMART REFINE DONE")
        _log(window, f"Intent: {result['intent']}")
        _log(window, f"Duration: {result['actual_duration']} / {result['target_duration']}")
        _log(window, f"Selected: {result['selected_count']}")
        _log(window, f"Replacements: {result['replacement_count']}")
        _log(window, f"Warnings: {result['warning_count']}")
        _log(window, f"Report: {result['report_dir']}")

        if show_popup:
            QMessageBox.information(
                window,
                "Prewedding Smart Refiner",
                "Đã refine roughcut prewedding.\n\n"
                f"Intent: {result['intent']}\n"
                f"Selected: {result['selected_count']}\n"
                f"Replacements: {result['replacement_count']}\n"
                f"Duration: {result['actual_duration']}s\n\n"
                "Module 049 sẽ export XML từ bản refined này.",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREWEDDING SMART REFINE ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Prewedding Smart Refiner Error", msg[-4000:])


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
