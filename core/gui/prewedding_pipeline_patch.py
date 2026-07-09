
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_prewedding_pipeline_patch_applied"


def apply_prewedding_pipeline_patch(window_class) -> None:
    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1500, lambda: _install_pipeline_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_pipeline_ui(window) -> None:
    if getattr(window, "_stt_prewedding_pipeline_ui_installed", False):
        return

    try:
        window._stt_prewedding_pipeline_ui_installed = True

        from core.prewedding_pipeline import PIPELINE_INTENTS

        combo = QComboBox()
        combo.setObjectName("sttPreweddingPipelineIntentCombo")
        for intent in PIPELINE_INTENTS:
            combo.addItem(intent)

        preferred = combo.findText("prewedding_reel_60s")
        if preferred >= 0:
            combo.setCurrentIndex(preferred)

        btn = QPushButton("Run Full Prewedding Pipeline")
        btn.setObjectName("sttProductionButton_primary_RunFullPreweddingPipeline")
        btn.setMinimumHeight(36)
        btn.clicked.connect(lambda: _run_pipeline(window, combo.currentText(), show_popup=True))

        box = QGroupBox("Prewedding One-Click Pipeline")
        box.setObjectName("sttPreweddingPipelinePanel")
        layout = QVBoxLayout(box)
        layout.addWidget(combo)
        layout.addWidget(btn)

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().insertWidget(0, box)
            _log(window, "PREWEDDING ONE-CLICK PIPELINE UI LOADED")
            return

        central = window.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().insertWidget(0, box)
            _log(window, "PREWEDDING ONE-CLICK PIPELINE PANEL LOADED")

    except Exception:
        _log(window, "PREWEDDING ONE-CLICK PIPELINE PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_pipeline(window, intent: str, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.prewedding_pipeline import run_prewedding_pipeline

        _log(window, "")
        _log(window, "PREWEDDING PIPELINE START")
        _log(window, f"Intent: {intent}")

        result = run_prewedding_pipeline(
            project_root=project_root,
            intent=intent,
            open_folder=True,
            stop_on_error=True,
        )

        _log(window, "")
        _log(window, "PREWEDDING PIPELINE DONE")
        _log(window, f"OK: {result['ok']}")
        _log(window, f"Steps: {result['steps_ok']} / {result['steps_total']}")
        _log(window, f"XML: {result.get('xml')}")
        _log(window, f"Report: {result['report_dir']}")

        if show_popup:
            if result["ok"]:
                QMessageBox.information(
                    window,
                    "Prewedding Pipeline",
                    "Đã chạy full pipeline prewedding.\n\n"
                    f"Intent: {intent}\n"
                    f"Steps: {result['steps_ok']} / {result['steps_total']}\n\n"
                    "Qua Premiere panel bấm Refresh Latest XML rồi Import.",
                )
            else:
                QMessageBox.warning(
                    window,
                    "Prewedding Pipeline",
                    "Pipeline có lỗi.\n\n"
                    f"Steps: {result['steps_ok']} / {result['steps_total']}\n"
                    f"Report: {result['report_dir']}",
                )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREWEDDING PIPELINE ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Prewedding Pipeline Error", msg[-4000:])


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
